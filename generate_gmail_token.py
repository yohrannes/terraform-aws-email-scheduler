import os
import sys
import json
import re
from google_auth_oauthlib.flow import InstalledAppFlow

try:
    from dotenv import load_dotenv
    home_env = os.path.expanduser('~/.env')
    if os.path.exists(home_env):
        load_dotenv(dotenv_path=home_env)
    else:
        load_dotenv()
except ImportError:
    pass

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def update_tfvars(tfvars_path: str, token_data: dict):
    if not os.path.exists(tfvars_path):
        print(f"Warning: Target tfvars file '{tfvars_path}' not found. Skipping tfvars update.")
        return

    compact_json = json.dumps(token_data)
    escaped_json = compact_json.replace('"', '\\"')
    new_line = f'google_token_json = "{escaped_json}"'

    with open(tfvars_path, 'r') as f:
        content = f.read()

    pattern = r'^google_token_json\s*=.*$'
    if re.search(pattern, content, flags=re.MULTILINE):
        new_content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        new_content = content.rstrip() + f"\n{new_line}\n"

    with open(tfvars_path, 'w') as f:
        f.write(new_content)

    print(f"Successfully updated google_token_json in '{tfvars_path}'")


def main():
    client_secrets_file = 'client_secret.json'
    tfvars_file = os.environ.get('GCHAT_AUTO_TFVARS')

    if len(sys.argv) > 1:
        client_secrets_file = sys.argv[1]
    if len(sys.argv) > 2:
        tfvars_file = sys.argv[2]

    if not tfvars_file:
        print("Error: Environment variable GCHAT_AUTO_TFVARS not found.")
        print("Please configure GCHAT_AUTO_TFVARS in ~/.env and run 'source ~/.env' before running this script.")
        sys.exit(1)

    if not os.path.exists(client_secrets_file):
        print(f"Error: File '{client_secrets_file}' not found.")
        sys.exit(1)

    with open(client_secrets_file, 'r') as f:
        data = json.load(f)

    if "web" in data:
        flow = InstalledAppFlow.from_client_config(data, SCOPES)
    elif "installed" in data:
        flow = InstalledAppFlow.from_client_config(data, SCOPES)
    elif "client_id" in data and "client_secret" in data:
        config = {
            "installed": {
                "client_id": data["client_id"],
                "client_secret": data["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": data.get("token_uri", "https://oauth2.googleapis.com/token"),
            }
        }
        flow = InstalledAppFlow.from_client_config(config, SCOPES)
    else:
        print("Error: The provided JSON is a Service Account or invalid key file.")
        print("Please provide an OAuth 2.0 Client ID file or an existing token JSON containing client_id and client_secret.")
        sys.exit(1)

    creds = flow.run_local_server(port=0)

    token_json_str = creds.to_json()
    token_dict = json.loads(token_json_str)

    with open('token-google-api.json', 'w') as token_file:
        token_file.write(token_json_str)

    print("Token successfully generated and saved to token-google-api.json")

    update_tfvars(tfvars_file, token_dict)


if __name__ == '__main__':
    main()
