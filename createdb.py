import sys
import configparser
from mysql.connector import connect, Error

config = configparser.ConfigParser()

config.read('opentriviata.ini')

if not 'opentriviata' in config:
    print("Unable to access database credentials.")
    sys.exit()

# Retrieve database credentials
db_host = config['opentriviata']['Host']
db_user = config['opentriviata']['User']
db_pass = config['opentriviata']['Pass']


try:
    with connect(
        host=config['opentriviata']['Host'],
        user=config['opentriviata']['User'],
        password=config['opentriviata']['Pass'],
    ) as connection:
        create_db_query = "CREATE DATABASE opentriviata"
        with connection.cursor() as cursor:
            cursor.execute(create_db_query)
except Error as e:
    print(e)
