"""Cache helper."""

import json
from pathlib import Path


class CacheHelper:
    """Cache helper."""

    def __init__(self, location, namespace='', write_through=True):
        """
        Constructor.

        @param string location
        @param string namespace (optional)
        @param boolean write_through (optional)
        """
        # Determine cache location
        self.location = location

        # Set namespace
        self.namespace = namespace

        # Set write mode
        self.write_through = write_through

        # Read cache to variable
        self.cache = self.read()

    def set_write_through(self, status):
        """
        Update write through status.

        @param boolean status
        """
        self.write_through = status

    def read(self):
        """
        Read and return cache file.

        @return dict
        """
        try:
            # Load cache
            with open(self.location, 'r') as fin:
                return json.load(fin)
        except:
            Path(self.location).resolve().parent.mkdir(
                parents=True, exist_ok=True)
            # Return empty cache
            return {}

    def exists(self, path=''):
        """
        Check if key exists in entry.

        @param string key (optional)
        @return boolean
        """
        obj = self.get(path)

        return obj is not None

    def get(self, path='', default=None):
        """
        Get cache object at path.

        @param string path (optional)
        @param string default (optional)
        @return any
        """
        obj = self.cache

        # Get path as list
        path_list = self.__get_absolute_path(path)

        # Get first list element
        elem = path_list.pop(0) if len(path_list) > 0 else None

        while elem:
            try:
                elem = int(elem) if elem.isnumeric() else elem
                obj = obj[elem]
                elem = path_list.pop(0) if len(path_list) > 0 else None
            except Exception:
                return default

        return obj

    def __get_absolute_path(self, path):
        """
        Return absolute path including any namespace.

        @param string path
        @return list
        """
        # Determine absolute path
        abs_path = '.'.join((self.namespace, path)).lstrip('.')

        # Convert to list
        path_list = abs_path.split('.')

        # Remove empty elements
        return list(filter(None, path_list))

    def __create_path(self, path):
        """
        Create path in cache.

        @param string path
        """
        # Get absolute path
        path_list = self.__get_absolute_path(path)

        cache = self.cache

        for part in path_list:
            if part not in cache:
                cache[part] = {}
                cache = cache[part]

    def add(self, path, value):
        """
        Add value to list

        @param string path
        @param string value
        """
        path_list = path.split('.')

        self.__create_path('.'.join(path_list))

        obj = self.get('.'.join(path_list))

        if obj is not None and isinstance(obj, list):
            obj.append(value)

            if self.write_through:
                self.write()

    def set(self, path, value):
        """
        Set valu at path.

        @param string path
        @param string value
        """
        path_list = path.split('.')
        last = path_list.pop()

        self.__create_path('.'.join(path_list))

        obj = self.get('.'.join(path_list))

        if obj is not None:
            obj[last] = value

            if self.write_through:
                self.write()

    def write(self):
        """Write cache to file."""
        with open(self.location, 'w+') as fout:
            fout.write(json.dumps(self.cache, indent=4))

    def delete(self, path):
        """
        Delete entry from cache.

        @param string path
        """
        path_list = path.split('.')
        last = path_list.pop()

        obj = self.get('.'.join(path_list))

        if obj is not None:
            del obj[last]
            self.write()
