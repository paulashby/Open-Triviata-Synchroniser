# Open Triviata Synchroniser


<img src="./img/open-triviata-logo.svg" width="200" alt="Open Triviata logo"><br />


  [<img src="https://img.shields.io/badge/License-MIT-yellow.svg">](https://opensource.org/licenses/MIT)

## Table of Contents

[Description](#description)<br />[Usage](#usage)<br />[Contributing](#contributing)<br />[License](#license)<br />[Questions](#questions)<br />

## Description
A synchroniser programme to add all validated Open Trivia questions to the Open Triviata Database. The [associated API](https://github.com/paulashby/open-triviata-api) accepts identical requests to those used to access the Open Trivia Database, but differs from the original in two notable ways - firstly, specific questions can be retrieved by providing a comma-separated list of ID numbers and secondly, unencoded text can be requested for use in contexts which output encoded HTML by default, such as Django.

The programme starts by obtaining from the Open Trivia API a list of verified question counts for all available categories. This is checked against the entries already added to the project database to determine whether there are further questions to add. If so, these are processed, with the data being stored across three tables in the project database.

Once all categories have been checked, the programme is complete.

## Usage
You should include an appconfig.ini file in the root directory with the following entries:
```
[dbconfig]
host = HOST_NAME
user = USER_NAME
pass = PASSWORD

[tokenconfig]
api_token = 
```
Create the database:<br />
```python3 createdb.py```<br /><br />
Run the programme with a new token (and synchronise all questions):<br />
```python3 app.py```<br /><br />
Run the programme with an existing token (and synchronise only new questions):<br />
```php app.py -t```

## Contributing

If you feel you could contribute to the synchroniser in some way, simply fork the repository and submit a Pull Request. If I like it, I may include it in the codebase.
  
## License
  
Released under the [MIT](https://opensource.org/licenses/MIT) license.

## Questions

Feel free to [email me](mailto:paul@primitive.co?subject=OpenTriviataSynchroniser%20query%20from%20GitHub) with any queries.


If you are interested in a PHP version of the app, please see the [Open Triviata Synchroniser PHP repository](https://github.com/paulashby/open-triviata-synchroniser-php).

