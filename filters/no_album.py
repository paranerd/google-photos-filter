import datetime
from pathlib import Path

from util.google_api import GoogleApi
from util.cache import CacheHelper


class NoAlbumFilter():
    name = 'no-album'

    def __init__(self):
        self.api = GoogleApi("https://photoslibrary.googleapis.com/v1",
                             "https://www.googleapis.com/auth/photoslibrary.readonly")
        filtered_path = (Path(__file__).resolve().parent.parent).joinpath(
            "results", datetime.datetime.now().strftime("%Y%m%d_%H%M%S.json"))
        self.filtered = CacheHelper(location=filtered_path)
        self.filtered.set('filtered', [])

    def filter(self):
        """Fetch all photos not part of an album."""
        # Get all photos
        print("Fetching all photos", end='', flush=True)
        self.cache = self.get_all_photos()
        print()

        # Get all albums
        print("Fetching all albums", end='', flush=True)
        albums = self.get_albums()
        print()

        # Remove photos in albums
        print("Filtering photos in albums", end='', flush=True)
        for album in albums:
            self.remove_photos_in_albums(album['id'])
        print()

        # Save URLs of photos without an album
        for id, url in self.cache.items():
            self.filtered.add('filtered', url)

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

        res = self.api.get("albums", {}, params)

        albums = []

        if 'albums' in res['body']:
            albums = res['body']['albums']

            if 'nextPageToken' in res['body']:
                albums.extend(self.get_albums(res['body']['nextPageToken']))
        elif res['status'] != 200:
            print("An error occurred")
            print(res)

        return albums

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

        res = self.api.get("mediaItems", {}, params)

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

        res = self.api.post("mediaItems:search", {}, params)

        if 'mediaItems' in res['body']:
            items = res['body']['mediaItems']

            for item in items:
                if item['id'] in self.cache:
                    del self.cache[item['id']]

        if 'nextPageToken' in res['body']:
            self.remove_photos_in_albums(id, res['body']['nextPageToken'])
