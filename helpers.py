import sys
import requests   
import configparser
from mysql.connector import connect, Error

# Get database credentials from config file
config = configparser.ConfigParser()
config.read("appconfig.ini")

if not "dbconfig" in config:
    print("Unable to access database credentials.")
    sys.exit()

# Lookup helpers //////////////////////////////////////

def category_lookup():

    def callback(api_data):
        return api_data['trivia_categories']
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_category.php'
    }
    return api_request(req_details)


def category_question_count_lookup(category_id):

    def callback(api_data):
        return api_data['category_question_count']
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_count.php',
        'parameters': {
            'category': category_id
        }
    }
    return api_request(req_details)


def global_question_count_lookup(api_data):

    def callback(api_data):
        # Do I need to access this here to benefit from the try block calling all this in api_request()
        return api_data
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_count_global.php'
    }
    return api_request(req_details)


# Token Empty Session Token has returned all possible questions for the specified query
def category_complete(api_data):

    # Move on to next category
    print ("Category Completed. Resetting the Token is necessary")



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
def success_callback(api_data, req_details):

    if req_details['endpoint'].find('token') < 0:
        # This is a simple success message - I think related to getting questions
         # If we have question data, add to our db, load next batch
         print("Add to database: \n" + repr(api_data))
         return

    else:
        # This is a token operation
        return api_data['token']


# Not enough items in Open Trivia DB to fulfill request
def quantity_callback(api_data):

    print("Quantity unavailable - reduce to [total available] % [qs per request] and try again")
    return


# Used by api_request to route callbacks
response_callbacks = {
    0: success_callback,
    1: quantity_callback,
    4: category_complete
}

# Make api calls and parse responses
def api_request(req_details):

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

    # Append the token to ensure the api returns no questions we've already had
    req_url += f"{pre}token={get_session_token()}"
    print(req_url)

    # Make the call
    try:
        payload={}
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
       
        if response_code == 2: 
            print(f"\nError (2): Invalid parameter passed to Open Trivia API:\n{req_url}\n")
            sys.exit(1)

        elif response_code == 3:
            # Token has expired - need to get new one to ensure api returns unique questions
            return update_token()
            
        elif response_code > 4:
            # Response code does not match expected values - assume question data is unviable
            print(f"\nError {response_code}: Open Trivia API returned an unknown error code:\n{req_url}\n")
            sys.exit(1)

        # Use response_callbacks to route to correct callback
        return response_callbacks[response_code](api_response, req_details)

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
            with connection.cursor() as cursor:
                for db_query in db_queries:
                    cursor.execute(db_query)

    except Error as e:
        print(e)
