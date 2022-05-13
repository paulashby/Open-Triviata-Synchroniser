from helpers import get_session_token, reset_session_token

"""
    • Should we rename this app.py?
    • Do we need a main()?
        https://realpython.com/python-main-function/
"""
token = get_session_token()
print(f"token = {token}")