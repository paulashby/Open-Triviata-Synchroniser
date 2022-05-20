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


def category_info_all():

    """ Get the entire list of categories and IDs from the API

        :return: List containing dicts of category ids and names
    """
    req_details = {
        'callback': lambda api_data: api_data['trivia_categories'],
        'endpoint': 'api_category.php'
    }

    return api_request(req_details, False)


def question_breakdown(category_id = False):

    """ Get category question counts from API

        :param category_id: Global count if False, else count for given category
        :return: dict question counts by category id and additional entry for overall question count
                 Plus, if category_id provided, dict with category id and question counts for each difficulty level
    """

    req_details = {
        'callback': extract_counts,
        'endpoint': 'api_count_global.php'
    }

    questions = {
        'global': api_request(req_details, False)
    }

    if not category_id:
        return questions

    req_details = {
        'callback': lambda api_data: api_data,
        'endpoint': 'api_count.php',
        'parameters': {
            'category': category_id
        }
    }

    # Return a single dict with category number and question counts for each difficulty level
    breakdown = api_request(req_details, False)
    breakdown['category_question_count']['id'] = breakdown['category_id']
    questions['category'] = breakdown['category_question_count']

    return questions


def extract_counts(api_data):

    """ Filter api_data to include only verified question counts

        :param api_data: Data returned by API
        :Return: Dictionary of verified question counts
    """

    extracted_counts = {
        'overall': api_data['overall']['total_num_of_verified_questions']
    }

    for cat_key in api_data['categories'].keys():
        extracted_counts[int(cat_key)] = api_data['categories'][cat_key]['total_num_of_verified_questions']

    return extracted_counts


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


def next_category(category_id = MIN_CAT_NUM):

    """ Get dictionary for the given category

        :return: False or dict with category id and question counts for each difficulty level 
    """
    categories = category_status(category_id)

    if categories['completed']['all']:
        return false

    elif categories['completed']['current']:
        return next_category(make_category(category_id))

    return categories['next']


def category_status(category_id = False):

    """ Get category status - helper for next_category()

        :return: dict containing
            - 'completed' dict with boolean statuses for 'all' and 'current' categories
            - 'next' dict with question breakdown for next category to process
    """
    
    if not category_id:
        category_id = current_category()

    source_questions = question_breakdown(category_id)

    category = source_questions['category']
    global_question_count = source_questions['global']

    total_questions_done = questions_done()
    category_questions_done = questions_done(category_id)

    return {
        'completed': {
            'all': (total_questions_done['global'] >= global_question_count['overall'] 
            or not category_id in global_question_count.keys()),
            'current': category_questions_done == category['total_question_count']
        },
        'next': category
    }


def current_category():

    """ Return id number of current category or None
    """
    # Get highest numbered category from local database
    curr_cat_id = db_query(["SELECT MAX(id) FROM categories"])[0]

    return curr_cat_id


def process_questions(to_do)
    """
    to_do is a dict populated with category id and a dict with the number of validated API questions available for incompletey processed difficulty levels
    eg
    {
        'category': 9
        'levels': {
            'easy': 116,
            'hard': 59
        }
    }
    
    Difficulty levels are only included if they are incomplete

    Plan is that we wipe them out of the data base and start again

    Probably going to need this somewhere along the line: 
    QUERY_MAX = 50
    num_full_calls = floor(current_category_info/QUERY_MAX)
    final_call_qty = current_category_info % QUERY_MAX
    """


def questions_done(category_id = False):

    """ Get the number of questions added to the local database for the given category

        :param category_id: Global count if False, else count for given category
        :return: dict of question counts - global and, if category_id provided, category
    """

    query_details = ["SELECT COUNT(*) FROM questions"]

    questions = {
       'global': db_query(query_details)[0] 
    }

    if not category_id:
        return questions

    query_details = [{
        'query': "SELECT COUNT(*) FROM questions WHERE category_id = %s", 
        'values': (category_id,)
    }]

    questions['category'] = db_query(query_details)[0]

    return questions


def level_counts(category_id):

    """ Get the number of questions added to the local database for each difficulty level

        :param category_id: Category to query
        :return: dict of question counts by level
    """

    counts = {
        'easy': 0,
        'medium': 0,
        'hard': 0
    }

    for level in counts:
        query_details = [{
            'query': "SELECT COUNT(*) FROM questions WHERE category_id = %s AND difficulty = %s", 
            'values': (category_id, level)
        }]

        counts[level] = db_query(query_details)[0]

    return counts


def session_token(expired = False):

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
        req_url += f"{pre}token={session_token()}"

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
            session_token(True)

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

