import sys
import requests   
import configparser
from mysql.connector import connect, Error

MIN_CAT_NUM = 9
MAX_QUESTIONS = 50

trivia_categories = {}


# Get database credentials from config file
config = configparser.ConfigParser()
config.read("appconfig.ini")

if not "dbconfig" in config:
    print("Unable to access database credentials.")
    sys.exit()


def update_trivia_categories():

    global trivia_categories

    req_details = {
        'callback': lambda api_data: api_data['trivia_categories'],
        'endpoint': 'api_category.php'
    }

    latest_categories =  api_request(req_details, False)

    for category in latest_categories:
        # Populate trivia_categories with category number/name pairs
        trivia_categories[category['id']] = category['name']


def get_category(category_id):

    """ Add a new category to the local database

        :param category_id: the id number for the new category
        :return: False or the id number for the new category
    """
    if not category_id in trivia_categories:
        # Category doesn't exist - we're done
        return False

    cat_name =  trivia_categories[category_id]

    category_exists = db_query([{
        'query': "SELECT COUNT(*) FROM categories WHERE id = %s", 
        'values': (category_id,)
    }])[0]

    if not category_exists:
        # Make the category
        db_query([{
            'query': "INSERT INTO categories (id, category) VALUES (%s, %s)", 
            'values': (category_id, cat_name)
        }])

    return category_id


def next_category(category_id = MIN_CAT_NUM):

    """ Get dictionary for the given category

        :return: False or dict with category id and question counts for each difficulty level 
    """

    if category_id:

        category = category_status(category_id)

        if category['completed']:
            print(f"Category {category_id}: no new questions available")
            return next_category(get_category(category_id + 1))

        print(f"Category {category_id}: new questions available. Processing...")
        return category['next']

    return False


def category_status(category_id = False):

    """ Get category status - helper for next_category()

        :return: dict containing
            - 'completed' boolean
            - 'next' dict with question breakdown for next category to process
    """
    
    if not category_id:
        category_id = current_category()

    source_questions = question_breakdown(category_id)
    category = source_questions['category']
    category_questions_done = questions_done(category_id)['category']

    return {
        'completed': category_questions_done == category['total_question_count'],
        'next': category
    }


def current_category():

    """ Return id number of current category or None
    """
    # Get highest numbered category from local database
    curr_cat_id = db_query(["SELECT MAX(id) FROM categories"])[0]

    return curr_cat_id


def process_category(to_do):

    """ Add outstanding questions for this category to local database

        :param to_do: Dictionary with category number, total question count and levels dictionary eg {'easy': 100, ...}
    """

    category = to_do['category']

    print(f"Updating category {category}")

    levels_to_do = to_do['levels']

    if not levels_to_do:
        # Add all questions for given category to database
        process_level(category, {'level': "all", 'count': to_do['total']})
    else:
        for level, count in levels_to_do.items():
            # Add all questions for given levels to local database
            process_level(category, {'level': level, 'count': count})


def process_level(category_id, to_do):

    """ Add questions to local database - restrict to difficulty level if provided

        :param category_id: Id number of current category
        :param to_do: Dictionary with difficulty level and question count eg {'level': 'all', 'count': 100'}
    """
    req_details = {
        'callback': process_questions,
        'endpoint': 'api.php',
        'parameters': {
            'category': category_id,
            'amount': MAX_QUESTIONS
        }
    }

    difficulty_level = to_do['level']

    if not difficulty_level == "all":
        req_details['parameters']['difficulty'] = difficulty_level

    total = to_do['count']
    
    for i in range(MAX_QUESTIONS, total + 1, MAX_QUESTIONS):
        # API will return unique questions because we're using a token
        api_request(req_details)

    remaining = total % MAX_QUESTIONS

    if remaining:
         # Add any stragglers
        req_details['parameters']['amount'] = remaining
        api_request(req_details)


def process_questions(questions, req_details):

    """ Add the given questions to the local database

        :param questions: A list of question dictionaries, each containing the details of a single question
        :param: req_details: The url segments used for the api request
    """
    if len(questions):
        category_id = req_details[ 'parameters']['category']
        category_name = questions[0]['category']

        db_query([{
            # Make sure category exists
            'query': "INSERT INTO categories (id, category) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id=id", 
            'values': (category_id, category_name)
        }])

        db_queries = []

        for question_details in questions:
            # Prepare requests for all questions
            db_queries.append({
                'query': "INSERT INTO questions (category_id, type, difficulty, question_text) VALUES (%s, %s, %s, %s)", 
                'values': (category_id, question_details['type'], question_details['difficulty'], question_details['question'])
            })

            if question_details['type'] == 'boolean':
                db_queries.append({
                    'query': "INSERT INTO answers (question_id, correct) VALUES (LAST_INSERT_ID(), %s)", 
                    'values': (question_details['correct_answer'] == "True",)
                })
            else:
                for incorrect_answer in question_details['incorrect_answers']:
                    db_queries.append({
                        'query': "INSERT INTO answers (question_id, answer, correct) VALUES (LAST_INSERT_ID(), %s, 0);", 
                        'values': (incorrect_answer,)
                    })
                # Add correct answer
                db_queries.append({
                        'query': "INSERT INTO answers (question_id, answer, correct) VALUES (LAST_INSERT_ID(), %s, 1);", 
                        'values': (question_details['correct_answer'],)
                    })

        db_query(db_queries)

    else:
        # No questions were provided - print a warning so it can be looked into if necessary
        print(f"WARNING: No questions provided to process_questions() for category {category_id}")


def questions_done(category_id = False):

    """ Get the number of questions added to the local database for the given category

        :param category_id: False or category id number
        :return: dict of question counts - global and category if category_id provided
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


def session_token(expired = False):

    """ Retrieve a session token

        :param expired: Do not read from config - get new from API
        :return: Session cookie string
    """

    config.read('appconfig.ini')
    token = config.get('tokenconfig', 'api_token')

    if expired or (not token) or len(token) == 0:
        # Token rejected or not set - request new one from api
        req_details = {
            'callback': set_token,
            'endpoint': 'api_token.php',
            'parameters': {
                'command': 'request'
            }
        }
        token = api_request(req_details, False)

    return token


def set_token(token, req_details):

    """ Store new session token in config file

        :param token: String returned by API
        :return: the token
    """ 

    if not token.isalnum():
        print("Error: expected alphanumeric token")
        sys.exit(1)

    config.set('tokenconfig', 'api_token', token)
    with open('appconfig.ini', 'w') as configfile:
        config.write(configfile)

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


def api_request(req_details, use_token = True):

    """ Make api calls and parse response

        :param req_details: Dictionary containing the url fragments
        :param use_token: required when retrieving unique questions
        :return: Processed data
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
          'Cookie': "PHPSESSID=1b01789fb2d1898c5d3358944fec0590"
        }
        response = requests.get(req_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        return

    if response.status_code != 204:
        return process_response(req_details, response.json(), req_url)


def process_response(req_details, api_response, req_url):
    
    """" React to API response codes

        :param req_details: Dictionary containing the url fragments
        :param api_response: Data from api
        :param req_url: The assembled url that was used for the api call
        :return: Processed data or None
    """

    try:
        if not 'response_code'in api_response.keys():
            # This must be a lookup. Lookup callbacks are passed in with req_details
            return req_details['callback'](api_response)

        response_code = api_response['response_code']

        if response_code == 0:
            # Successfully retrived token or questions
            if req_details['endpoint'] == 'api_token.php':
                # Pass the token string to the callback
                api_data = api_response['token']
            else:
                # Use the questions in the results list to the callback
                api_data = api_response['results']
                # NOTE: this was api_response['results'][0], but assuming I want ALL the returned questions, the whole list has got to be better

            return req_details['callback'](api_data, req_details)

        elif response_code == 1:
            print(f"\nError (Response code 1): Quantity unavailable - API unable to return data for the query {req_url}")
            sys.exit(1)
       
        elif response_code == 2: 
            print(f"\nError (Response code 2): Invalid parameter passed to Open Trivia API:\n{req_url}\n")
            sys.exit(1)

        elif response_code == 3:
            # Token not found. Attempt to recover - duplicate questions will trigger an SQL error as the question_text field is UNIQUE.
            # get new token to ensure api returns unique questions (going forward - they're only unique to the new token)
            session_token(True)

            # Make the request again
            return api_request(req_details, True)

        elif response_code == 4:
            # We've processed all questions in the current category
            print("\nNotification: (Response code 4): All requested questions have been returned for the given query")
            return
            
        else:
            # Response code does not match expected values - assume question data is unviable
            print(f"\nError {response_code}: Open Trivia API returned an unknown error code:\n{req_url}\n")
            sys.exit(1)

    except (KeyError, TypeError, ValueError):
        return


def db_query(db_queries):

    """ Execute the provided list of MySQL queries

        :param db_queries: List of parameterised request dictionaries/SQL query strings
        :return: Query results
    """

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

                   
                    # query_results will be overwritten on every iteration.

                    # This is OK, because the db_queries argument will contain 
                    # only a single item when performing a SELECT operation
                   
                    query_results = cursor.fetchall()
                    connection.commit()
            return  query_results[0] if len(query_results) else 0

    except Error as e:
        print(e)

