import sys
import argparse
import configparser
from mysql.connector import connect, Error

# Parse command line args
parser = argparse.ArgumentParser(description='Get MySQL credentials')
parser.add_argument('-c', '--config', help='name of config file containing MySQL credentials', required=True)
args = parser.parse_args()

# Config file to read for database credentials
configfilename = getattr(args, 'config')

# Name of section to parse from config file
configname = 'dbconfig'
config = configparser.ConfigParser()
config.read(configfilename)

if not configname in config:
    print("Unable to access database credentials.")
    sys.exit()

try:
    with connect(

        # Use database credentials from .ini
        host=config[configname]['Host'],
        user=config[configname]['User'],
        password=config[configname]['Pass']

    ) as connection:
        
        db_query = "CREATE DATABASE IF NOT EXISTS opentriviata"
        with connection.cursor() as cursor:
            cursor.execute(db_query)

except Error as e:
    print(e)

# Add tables
try:
    with connect(
        # Use database credentials from .ini
        host=config[configname]['Host'],
        user=config[configname]['User'],
        password=config[configname]['Pass'],
        database="opentriviata",
    ) as connection:
        # SQL varchar usually holds 1 byte per character and 2 more bytes for the length information. It is recommended to use varchar as the data type when columns have variable length and the actual data is way less than the given capacity.
        db_queries = [
            "CREATE TABLE categories (id INTEGER PRIMARY KEY NOT NULL, category VARCHAR(255) NOT NULL UNIQUE)",
            "CREATE TABLE questions (id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL, category_id INTEGER NOT NULL, type VARCHAR(16) NOT NULL, difficulty VARCHAR(16) NOT NULL, question_text VARCHAR(1024) NOT NULL UNIQUE, FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE)",
            "CREATE TABLE answers (question_id INTEGER NOT NULL, answer VARCHAR(1024), correct BOOLEAN NOT NULL, FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE)"
        ]
        with connection.cursor() as cursor:
            for db_query in db_queries:
                cursor.execute(db_query)

except Error as e:
    print(e)
