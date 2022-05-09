import configparser
config = configparser.ConfigParser()

# Using <placeholders> - replace these with live values before creating ini file
config['opentriviata'] = {}
config['opentriviata']['Host'] = '<host>'
config['opentriviata']['User'] = '<username>'
config['opentriviata']['Pass'] = '<password>'
with open('opentriviata.ini', 'w') as configfile:
  config.write(configfile)