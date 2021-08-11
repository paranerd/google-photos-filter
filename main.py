import os
import re
import json
import argparse
import requests
import webbrowser
import urllib3
from urllib.parse import urlencode, quote_plus

# Prevent SSL certificate errors
from urllib3.contrib import pyopenssl
pyopenssl.extract_from_urllib3()


class GooglePhotosFilter():
    API_URL = "https://photoslibrary.googleapis.com/v1"
    credentials = ''
    token = ''
    cache = {}

    def __init__(self):
        """
        Constructor
        """
        self.credentials = self.get_credentials()
        self.token = self.get_token()

    def get_credentials(self):
        """Load credentials from file or request it from Google.
        """
        if os.path.isfile('credentials.json'):
            with open('credentials.json', 'r') as f:
                return json.load(f)
        else:
            self.show_instructions()

            credentials_str = input('Paste content of credentials file: ')
            credentials = json.loads(credentials_str)

            with open('credentials.json', 'w+') as f:
                f.write(json.dumps(credentials, indent=4))

            return credentials

    def get_token(self):
        """Load token from file or request it from Google.
        """
        if os.path.isfile('token.json'):
            with open('token.json', 'r') as f:
                return json.load(f)
        else:
            code = self.request_code()
            token = self.request_token(code)

            with open('token.json', 'w+') as f:
                f.write(json.dumps(token, indent=4))

            return token

    def show_instructions(self):
        """Print instructions on how to set up Google Cloud Project."""
        print()
        print('If you already have an OAuth-Client-ID, download the JSON, name it "credentials.json" and place it in the project root')
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
        """Build auth URI for requesting token.

        @return string
        """
        auth_uri = self.credentials['installed']['auth_uri']
        auth_uri += "?response_type=code"
        auth_uri += "&redirect_uri=" + \
            quote_plus(self.credentials['installed']['redirect_uris'][0])
        auth_uri += "&client_id=" + \
            quote_plus(self.credentials['installed']['client_id'])
        auth_uri += "&scope=https://www.googleapis.com/auth/photoslibrary.readonly"
        auth_uri += "&access_type=offline"
        auth_uri += "&approval_prompt=auto"

        return auth_uri

    def request_code(self):
        """Request code from auth URI to obtain token.

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

    def get_missing(self):
        """Fetch all photos not part of an album."""
        # Get all photos
        print("Fetching all photos", end='', flush=True)
        self.cache = self.get_all_photos()
        print()

        # Get all albums
        print("Fetching albums", end='', flush=True)
        albums = self.get_albums()
        print()

        # Remove photos in albums
        print("Filtering photos in albums", end='', flush=True)
        for album in albums:
            self.remove_photos_in_albums(album['id'])
        print()

        # Save URLs of photos without an album
        file = open('missing.json', 'w+')

        for id, url in self.cache.items():
            file.write(url)
            file.write("\n")

        file.close()

    def get_albums(self, pageToken=""):
        """Fetch all albums.

        @param string pageToken (optional)
        @return list
        """
        # Progress indicator
        print(".", end='', flush=True)

        params = {
            "pageSize": "50",
        }

        if pageToken:
            params['pageToken'] = pageToken

        res = self.execute_request(self.API_URL + "/albums", {}, params)

        if 'albums' in res['body']:
            albums = res['body']['albums']

            if 'nextPageToken' in res['body']:
                albums.extend(self.get_albums(res['body']['nextPageToken']))

            return albums
        else:
            print("An error occurred")
            print(res)

    def get_all_photos(self, pageToken=""):
        """Get all photos.

        @param string pageToken (optional)
        @return dict
        """
        # Progress indicator
        print(".", end='', flush=True)

        params = {
            "pageSize": "100",
        }

        if pageToken:
            params['pageToken'] = pageToken

        res = self.execute_request(self.API_URL + "/mediaItems", {}, params)

        items = {}

        if 'mediaItems' in res['body']:
            for item in res['body']['mediaItems']:
                items[item['id']] = item['productUrl']

            if 'nextPageToken' in res['body']:
                items.update(self.get_all_photos(res['body']['nextPageToken']))

        return items

    def remove_photos_in_albums(self, id, pageToken=""):
        """Remove photos from cache which are part of an album.

        @param string pageToken (optional)
        """
        # Progress indicator
        print(".", end='', flush=True)

        params = {
            "pageSize": "50",
            "albumId": id
        }

        if pageToken:
            params['pageToken'] = pageToken

        res = self.execute_request(
            self.API_URL + "/mediaItems:search", {}, params, "POST")

        if 'mediaItems' in res['body']:
            items = res['body']['mediaItems']

            for item in items:
                if item['id'] in self.cache:
                    del self.cache[item['id']]

        if 'nextPageToken' in res['body']:
            self.remove_photos_in_albums(id, res['body']['nextPageToken'])

    def request_token(self, code=""):
        """Request auth token.

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

        res = self.execute_request(
            self.credentials['installed']['token_uri'], headers, params, "POST")

        if res['status'] == 200:
            if self.token:
                res['body']['refresh_token'] = self.token['refresh_token']

            self.token = res['body']
            return res['body']
        else:
            raise Exception("Error getting token: " + str(res['body']))

    def execute_request(self, url, headers={}, params={}, method="GET", is_retry=False):
        """Call Photos API.

        @param string url
        @param dict headers (optional)
        @param dict params (optional)
        @param string method (optional)
        @param bool is_retry (optional)
        """
        if "access_token" in self.token:
            # Set Authorization-Header
            auth_header = {
                'Authorization': 'Bearer {}'.format(self.token['access_token'])
            }
            headers.update(auth_header)

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
                return self.execute_request(url, headers, params, method, True)
            else:
                raise Exception("Failed to refresh token")

        body = res.json() if method != 'HEAD' else None

        return {'status': res.status_code, 'headers': res.headers, 'body': body}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--guide', action='store_true')
    arguments, _ = parser.parse_known_args()

    gp = GooglePhotosFilter()

    if arguments.guide:
        gp.show_instructions()
    else:
        gp.get_missing()
