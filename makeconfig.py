import argparse
import configparser

# Parse command line args
parser = argparse.ArgumentParser(description='Get settings for ini file')
parser.add_argument('-f', '--filename', help='filename for the generated ini file', default='appconfig')
parser.add_argument('-w', '--hostname', help='hostname', default='localhost')
parser.add_argument('-u', '--username', help='username', default='root')
parser.add_argument('-p', '--password', help='password', required=True)
args = parser.parse_args()
configname = getattr(args, 'filename')

config = configparser.ConfigParser()

# Use parsed arguments to create config file named [configname]
config['dbconfig'] = {}
config['dbconfig']['Host'] = getattr(args, 'hostname')
config['dbconfig']['User'] = getattr(args, 'username')
config['dbconfig']['Pass'] = getattr(args, 'password')

config['tokenconfig'] = {}
config['tokenconfig']['api_token'] = ""

with open(configname + '.ini', 'w') as configfile:
  config.write(configfile)