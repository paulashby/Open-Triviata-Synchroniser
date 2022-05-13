import requests   
import exceptions

"""


What data must we include

Do we need to maintain state somehow?
How do we know where we're at in the process?


If we work through each category, we'd do:
    get the id and the count of the highest-numbered category from opentriviata
    get the number of available entries from the API
    https://opentdb.com/api_count.php?category=9
    Return eg
    {
        "category_id": 9,
        "category_question_count": {
            "total_question_count": 298,
            "total_easy_question_count": 116,
            "total_medium_question_count": 123,
            "total_hard_question_count": 59
        }
    }
    if our count matches total_question_count
        - move on to next category
    elif our count is 0
        - scrape_category(category_id)
    else (our count is lower than total_question_count) either:
        - new questions have been added
        - something has gone wrong and we failed to complete the category on our previous session
       In either case, we need to:
        
        - check the counts for each level of difficulty (LOD), 
            if we're short in all
                - delete all questions for this category, remove it from the categories table and start again 
            else 
                - we're only short in some, delete all questions for each under-populated LOD and redo it - 
                (will also need to delete from answers table AND category if we end up removing all)
                - we are definitely short in at least one, since our category question count is lower than total_question_count


    Get session token

"""


# Lookup helpers //////////////////////////////////////

def category_lookup():

    def callback(api_data):
        return api_data['trivia_categories']
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_category.php'
    }
    return api_request(req_details)


def Category_question_count_lookup(category_id):

    def callback(api_data):
        return api_data['category_question_counts']
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_count.php',
        'parameters': {
            'category': category_id
        }
    }
    return api_request(req_details)


def global_question_count_lookup():

    def callback(api_data):
        # Do I need to access this here to benefit from the try block calling all this in api_request()
        return api_data
    
    req_details = {
        'callback': callback,
        'endpoint': 'api_count_global.php'
    }
    return api_request(req_details)



# Token helpers //////////////////////////////////////////

def get_session_token():
    
    req_details = {
        'endpoint': 'api_token.php',
        'parameters': {
            'command': 'request'
        }
    }
    return api_request(req_details)

def reset_session_token():
    # Token is not defined
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
def success_callback(api_data):
    if req_details['endpoint'].find('token') < 0:
        # This is a simple success message - I think related to getting questions
         # If we have question data, add to our db, load next batch
         print("Add to database: \n" + repr(api_data))
         return

    else:
        # This is a token operation
        return api_response['token']

# Not enough items in Open Trivia DB to fulfill request
def quantity_callback(api_data):
    print("Quantity unavailable - reduce to [total available] % [qs per request] and try again")
    return

# Token Empty Session Token has returned all possible questions for the specified query
def category_complete(api_data):
    # Done - Reset session token and move on to next category
    # Reset session token?
    print ("Category Completed. Resetting the Token is necessary")


def error_callback(response_code):
    try:
        raise(RequestError(response_code))
    except RequestError as Argument:
        print('RequestError: ', Argument)


# Used by api_request to route callbacks
response_callbacks = {
    0: success_callback,
    1: quantity_callback,
    4: category_complete
}


# Make api calls and parse responses
def api_request(req_details):

    req_url = "https://opentdb.com/"
    import pdb; pdb.set_trace()
    # Assemble API request
    if 'endpoint' in req_details:
        req_url += req_details['endpoint']

    if 'parameters' in req_details:
        parameters = req_details['parameters']
        pre = "?"

        for key, val in parameters.items():
            req_url += f"{pre}{key}={val}"
            pre = "&"

    # Make the call
    try:
        response = requests.get(req_url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response and return the correct data to the caller
    try:
        api_response = response.json()
        response_code = api_response["response_code"]

        if not response_code:
            # This is a lookup - callbacks are passed in with req_details
            # Hoping any exceptions will be caught by this containing try block
            return req_details['callback'](api_response)

        # Cap response_code to 5 to trigger our unknown error message if code is greater than 4
        response_code = min(response_code, 5);

        # Pass code to error_callback if listed in error codes in exceptions.py
        if response_code in RequestError.e_by_code.keys():
            return error_callback(response_code)

        # Use response_callbacks to route to correct callback
        return response_callbacks[response_code](api_response)

    except (KeyError, TypeError, ValueError):
        return None
