import sys
import requests   
import configparser
from mysql.connector import connect, Error

MIN_CAT_NUM = 9


# Get database credentials from config file
config = configparser.ConfigParser()
config.read("appconfig.ini")

if not "dbconfig" in config:
    print("Unable to access database credentials.")
    sys.exit()




# Lookup helpers //////////////////////////////////////


def current_category():

    """ Return id number of current category
    """
    
    # Get highest numbered category from local database
    curr_cat_id = db_query(["SELECT MAX(id) FROM categories"])[0]

    if curr_cat_id == None:
        return make_category(MIN_CAT_NUM)

    return curr_cat_id


def next_category():
    return False


def category_info_all():

    """ Get the entire list of categories and IDs from the API

        :return: Category numbers and titles 
    """
    req_details = {
        'callback': lambda api_data: api_data['trivia_categories'],
        'endpoint': 'api_category.php'
    }

    return api_request(req_details, False)


def question_breakdown(category_id = False):

    """ Get the number of questions in a category, total and by difficulty level

        :param category_id: Global count if False, else count for given category
        :return: The number of questions
    """

    if not category_id:
        req_details = {
            'callback': extract_counts,
            'endpoint': 'api_count_global.php'
        }

    else:
        req_details = {
            'callback': lambda api_data: api_data,
            'endpoint': 'api_count.php',
            'parameters': {
                'category': category_id
            }
        }

    return api_request(req_details, False)


def extract_counts(api_data):

    """ Get dictionary of verified question counts

        :param api_data: Data returned by API
        :Return: Dictionary of question counts
    """

    extracted_counts = {
        'overall': api_data['overall']['total_num_of_verified_questions']
    }

    for cat_key in api_data['categories'].keys():
        extracted_counts[int(cat_key)] = api_data['categories'][cat_key]['total_num_of_verified_questions']

    return extracted_counts


# Local database calls //////////////////////////////////////


def make_category(category_id):

    """ Add a new category to the local database

        :param category_id: the id number for the new category
        :return: the id number for the new category
    """

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
    db_query([{
        'query': "INSERT INTO categories (id, category) VALUES (%s, %s)", 
        'values': (category_id, cat_name)
    }])

    return category_id

def questions_in(category_id):

    """ Get the number of questions added to the local database for the given category

        :param category_id: The id of the category to check
        :return: The number
    """

    return db_query([{
        'query': "SELECT COUNT(*) FROM questions WHERE category_id = %s", 
        'values': (category_id,)
    }])[0]






# Token helpers //////////////////////////////////////////


def get_session_token(expired = False):

    """ Retrieve a session token

        :param expired: Do not read from config - get new from API
        :return: Session cookie string
    """

    config.read('appconfig.ini')
    token = config.get('tokenconfig', 'api_token')
    
    if expired or len(token) == 0:
        # Token rejected or not set - request new one from api
        req_details = {
            'endpoint': 'api_token.php',
            'parameters': {
                'command': 'request'
            }
        }
        token = api_request(req_details)

        if not token.isalnum():
            print("Error: expected alpha numric token")
            sys.exit(1)

        config.set('tokenconfig', 'api_token', token)
        with open('appconfig.ini', 'w') as configfile:
            config.write(configfile)
        
        return api_request(req_details)

    else:
        return token


def reset_session_token(token):

    """ Retrieve a new session cookie from the API

        :param token: The old token
        :return: The new token
    """

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


def success_callback(api_response, req_details):

    """ Process successful api calls

        :param api_response: the returned data
        :param req_details: the dictionary passed to api_request
        :return: Token or True
    """

    if req_details['endpoint'].find('token') < 0:
        # This is a simple success message - I think related to getting questions
         # If we have question data, add to our db, load next batch
         print("Add to database: \n" + repr(api_response))
         return

    else:
        # This is a token operation
        return api_response['token']


def quantity_callback():

    """ Not enough items in Open Trivia DB to fulfill request
    """

    # Need to decide what to do in this case - probably make the call again with the adjusments outlined below

    print("Quantity unavailable - reduce to [total available] % [qs per request] and try again")
    return


def api_request(req_details, use_token = True):

    """ Make api calls and parse response

        :param req_details: Dictionary containing the url fragments
        :param use_token: required when retrieving unique questions
    """

    req_url = "https://opentdb.com/"
    pre = ""
    
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
        # Append the token to ensure the api returns no duplicate questions
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
    
    """" React to API response codes

        :param req_details: Dictionary containing the url fragments
        :param api_response: Data from api
        :param req_url: The assembled url that was used for the api call
    """

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
            # Token not found - get new one to ensure api returns unique questions
            get_session_token(True)

            # Make the request again
            return api_request(req_details, True)

        elif response_code == 4:
            # We've processed all questions in the current category
            return process_cat(get_next_cat_id)
            
        else:
            # Response code does not match expected values - assume question data is unviable
            print(f"\nError {response_code}: Open Trivia API returned an unknown error code:\n{req_url}\n")
            sys.exit(1)

    except (KeyError, TypeError, ValueError):
        return None


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

