from helpers import get_session_token, reset_session_token

def main():
    token = get_session_token()
    print(f"token = {token}")

if __name__ == "__main__":
    main()