import os
import json
import requests
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = Path(PROJECT_ROOT).joinpath('secrets')


class GoogleApi():
    credentials = ''
    token = ''

    def __init__(self, api_url, scope):
        """
        Constructor.

        @param string api_url
        @param string scope
        """
        self.api_url = api_url
        self.scope = scope
        self.credentials = self.get_credentials()
        self.token = self.get_token()

        Path(SECRETS_PATH).mkdir(exist_ok=True)

    def get_credentials(self):
        """Load credentials from file or request it from Google."""
        credentials_path = Path(SECRETS_PATH).joinpath('credentials.json')

        if Path(credentials_path).exists():
            with open(credentials_path, 'r') as f:
                return json.load(f)
        else:
            self.show_instructions()

            credentials_str = input('Paste content of credentials file: ')
            credentials = json.loads(credentials_str)

            with open(credentials_path, 'w+') as f:
                f.write(json.dumps(credentials, indent=4))

            return credentials

    def get_token(self):
        """Load token from file or request it from Google."""
        token_path = Path(SECRETS_PATH).joinpath('token.json')

        if Path(token_path).exists():
            with open(token_path, 'r') as f:
                return json.load(f)
        else:
            code = self.request_code()
            token = self.request_token(code)

            with open(token_path, 'w+') as f:
                f.write(json.dumps(token, indent=4))

            return token

    def show_instructions(self):
        """Print instructions on how to set up Google Cloud Project."""
        print()
        print('If you already have an OAuth-Client-ID, download the JSON, copy the content and paste when prompted')
        print('Otherwise, here\'s how to get credentials:')
        print('1. Go to https://console.developers.google.com/')
        print('2. Choose or create a project')
        print('3. Activate Photos API here: https://console.developers.google.com/apis/library/photoslibrary.googleapis.com')
        print('4. Open https://console.developers.google.com/apis/credentials/consent')
        print('5. Choose "External"')
        print('6. Enter a name, support email and contact email')
        print('7. Click "Save and continue"')
        print('8. Click "Add or remove scopes"')
        print('10. Select ".../auth/photoslibrary.readonly"')
        print('11. Click "Save and continue"')
        print('12. Enter yourself as a test user')
        print('13. Click "Save and continue"')
        print(
            '14. [Open credentials page](https://console.developers.google.com/apis/credentials)')
        print('15. Click on "Create Credentials" -> OAuth-Client-ID -> Desktop Application')
        print('16. Download the Client ID JSON')
        print()

    def build_auth_uri(self):
        """
        Build auth URI for requesting token.

        @return string
        """
        auth_uri = self.credentials['installed']['auth_uri']
        auth_uri += "?response_type=code"
        auth_uri += "&redirect_uri=" + \
            quote_plus(self.credentials['installed']['redirect_uris'][0])
        auth_uri += "&client_id=" + \
            quote_plus(self.credentials['installed']['client_id'])
        auth_uri += "&scope={}".format(self.scope)
        auth_uri += "&access_type=offline"
        auth_uri += "&approval_prompt=auto"

        return auth_uri

    def request_code(self):
        """
        Request code from auth URI to obtain token.

        @return string
        """
        # Build auth uri
        auth_uri = self.build_auth_uri()

        # Try opening in browser
        webbrowser.open(auth_uri, new=2)

        print()
        print("If your browser does not open, go to this website:")
        print(auth_uri)
        print()

        # Return code
        return input('Enter code: ')

    def request_token(self, code=""):
        """
        Request auth token.

        @param string code
        @return dict
        """
        if not self.credentials:
            raise Exception('Could not read credentials')

        if not code and not self.token:
            raise Exception('Could not read token')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        params = {
            'client_id': self.credentials['installed']['client_id'],
            'client_secret': self.credentials['installed']['client_secret'],
            'redirect_uri': self.credentials['installed']['redirect_uris'][0],
        }

        if code:
            params['grant_type'] = 'authorization_code'
            params['code'] = code
        else:
            params['grant_type'] = 'refresh_token'
            params['refresh_token'] = self.token['refresh_token']

        res = self.post(
            self.credentials['installed']['token_uri'], headers, params)

        if res['status'] == 200:
            if self.token:
                res['body']['refresh_token'] = self.token['refresh_token']

            self.token = res['body']
            return res['body']
        else:
            raise Exception("Error getting token: " + str(res['body']))

    def execute_request(self, url, headers={}, params={}, is_retry=False, method="GET"):
        """
        Call API.

        @param string url
        @param dict headers (optional)
        @param dict params (optional)
        @param bool is_retry (optional)
        @param string method (optional)
        """
        if "access_token" in self.token:
            # Set Authorization-Header
            auth_header = {
                'Authorization': 'Bearer {}'.format(self.token['access_token'])
            }
            headers.update(auth_header)

        url = url if url.startswith(
            'http') else '{}/{}'.format(self.api_url, url)

        # Execute request
        if method == 'GET':
            res = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            res = requests.post(url, headers=headers, data=params)
        elif method == 'HEAD':
            res = requests.head(url, headers=headers)

        if res.status_code == 401:
            # Token expired
            if not is_retry:
                self.token = self.request_token()
                return self.execute_request(url, headers, params, True, method)
            else:
                raise Exception("Failed to refresh token")

        body = res.json() if method != 'HEAD' else None

        return {'status': res.status_code, 'headers': res.headers, 'body': body}

    def get(self, url, headers={}, params={}, is_retry=False):
        return self.execute_request(url, headers, params, is_retry, method="GET")

    def post(self, url, headers={}, params={}, is_retry=False):
        return self.execute_request(url, headers, params, is_retry, method="POST")
