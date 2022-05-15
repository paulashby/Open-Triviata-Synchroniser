import sys
import requests   
import configparser
from mysql.connector import connect, Error

MIN_CAT_NUM = 9

"""
category_details stores result of a call to category_question_count_lookup()
{
    "category_id": 9,
    "category_question_count": {
        "total_question_count": 298,
        "total_easy_question_count": 116,
        "total_medium_question_count": 123,
        "total_hard_question_count": 59
    }
}
"""


# Get database credentials from config file
config = configparser.ConfigParser()
config.read("appconfig.ini")

if not "dbconfig" in config:
    print("Unable to access database credentials.")
    sys.exit()




# Lookup helpers //////////////////////////////////////

def get_current_cat_id():
    query_list = ["SELECT MAX(id) FROM categories"]
    return db_query(query_list)[0]


def get_next_cat_id():
    return False


def get_all_cat_details():

    req_details = {
        'callback': lambda api_data: api_data['trivia_categories'],
        'endpoint': 'api_category.php'
    }
    return api_request(req_details)


def get_cat_q_count(category_id):

    req_details = {
        'callback': lambda api_data: api_data,
        'endpoint': 'api_count.php',
        'parameters': {
            'category': category_id
        }
    }
    return api_request(req_details)


def get_curr_cat_q_count():
    curr_cat_id = get_current_cat_id()

    if curr_cat_id == None:
        return make_new_cat(MIN_CAT_NUM)

    return get_cat_q_count(curr_cat_id)


def make_new_cat(category_id):

    # Retrieve sample question to determine category name
    req_details = {
        'callback': lambda api_results, req_details: api_results['category'],
        'endpoint': 'api.php',
        'parameters': {
            'amount': 1,
            'category': category_id
        }
    }

    cat_name = api_request(req_details, False)
    db_query([{'query': "INSERT INTO categories (id, category) VALUES (%s, %s)", 'values': (category_id, cat_name)}])

    return get_cat_q_count(category_id)


# Token helpers //////////////////////////////////////////


def get_session_token(expired = False):

    config.read('appconfig.ini')
    token = config.get('tokenconfig', 'api_token')
    
    if expired or len(token) == 0:
        # Token has expired or has not been set yet - request one from api
        req_details = {
            'endpoint': 'api_token.php',
            'parameters': {
                'command': 'request'
            }
        }
        token = api_request(req_details)
        # The api will return code 3 if the token has expired (Token Not Found Session Token does not exist)
        config.set('tokenconfig', 'api_token', token)
        with open('appconfig.ini', 'w') as configfile:
            config.write(configfile)
        
        return api_request(req_details)

    else:
        return token


def reset_session_token(token):

    print("resetting session token")
    req_details = {
        'endpoint': 'api_token.php',
        'parameters': {
            'command': 'reset',
            'token': token
        }
    }
    return api_request(req_details)



# Callbacks ////////////////////////////////////////////////


# Request was successful
def success_callback(api_response, req_details):

    if req_details['endpoint'].find('token') < 0:
        # This is a simple success message - I think related to getting questions
         # If we have question data, add to our db, load next batch
         print("Add to database: \n" + repr(api_response))
         return

    else:
        # This is a token operation
        return api_response['token']


# Not enough items in Open Trivia DB to fulfill request
def quantity_callback():


    print("Quantity unavailable - reduce to [total available] % [qs per request] and try again")
    return


# Make api calls and parse responses
def api_request(req_details, use_token = True):

    req_url = "https://opentdb.com/"
    
    # Assemble API request
    if 'endpoint' in req_details:
        req_url += req_details['endpoint']

    if 'parameters' in req_details:
        parameters = req_details['parameters']
        pre = "?"

        for key, val in parameters.items():
            req_url += f"{pre}{key}={val}"
            pre = "&"

    if use_token:
        # Append the token to ensure the api returns no questions we've already had
        req_url += f"{pre}token={get_session_token()}"

    # Make the call
    try:
        headers = {
          'Cookie': 'PHPSESSID=1b01789fb2d1898c5d3358944fec0590'
        }
        response = requests.get(req_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        return None

    return process_response(req_details, response.json(), req_url)


def process_response(req_details, api_response, req_url):
    
    # Parse response and return the correct data to the caller
    try:
        # api_response = {
        #     'response_mock': True,
        #     'response_code': 2
        # }
        if not 'response_code'in api_response.keys():
            # This must be a lookup. Lookup callbacks are passed in with req_details
            return req_details['callback'](api_response)

        response_code = api_response['response_code']

        if response_code == 0:
            return req_details['callback'](api_response['results'][0], req_details)

        elif response_code == 1:
            return quantity_callback()
       
        elif response_code == 2: 
            print(f"\nError (2): Invalid parameter passed to Open Trivia API:\n{req_url}\n")
            sys.exit(1)

        elif response_code == 3:
            # Token has expired - need to get new one to ensure api returns unique questions
            return update_token()

        elif response_code == 4:
            # We've processed all questions in the current category
            return process_cat(get_next_cat_id)
            
        else:
            # Response code does not match expected values - assume question data is unviable
            print(f"\nError {response_code}: Open Trivia API returned an unknown error code:\n{req_url}\n")
            sys.exit(1)

    except (KeyError, TypeError, ValueError):
        return None



def update_token():

    # Token has expired - need to get new one to ensure api returns unique questions
    get_session_token(True)

    # If the current category is incomplete, start over to avoid duplicate questions
    return redo_category()


# Execute the provided list of MySQL queries
def db_query(db_queries):

    # Name of database section in config file
    configname = 'dbconfig'

    try:
        with connect(
            
            # Database credentials from config file
            host=config[configname]['Host'],
            user=config[configname]['User'],
            password=config[configname]['Pass'],
            database="opentriviata",
        ) as connection:
            
            for db_query in db_queries:
                print(repr(db_query))
                use_prepared = type(db_query) is dict
                with connection.cursor(prepared=use_prepared) as cursor:
                    if use_prepared:
                        cursor.execute(db_query['query'], db_query['values'])
                    else:
                        cursor.execute(db_query)

                    """
                    query_results will be overwritten on every iteration.

                    This is OK, because the db_queries argument will contain 
                    only a single item when performing a SELECT operation
                    """
                    query_results = cursor.fetchall()
                    connection.commit()

            return  query_results[0] if len(query_results) else 0

    except Error as e:
        print(e)

