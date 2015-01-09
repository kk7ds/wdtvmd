import ConfigParser
import glob
import os
import re

import tmdb3


file_regex = re.compile('.*\.(mkv|mp4|m4v|avi|mpg|mp2)')


class FilenameFormatError(Exception):
    """Filename was not properly formed.

    This indicates that series, season, or episode information
    was not able to be detected in a filename.
    """
    pass


class AmbiguousResultError(Exception):
    """More than one result was found for the search."""
    pass


class NoAPIKey(Exception):
    """No API key was provided or stored in the config."""
    pass


class AppContext(object):
    def __init__(self, config=None, apikey=None):
        if config is None:
            config = os.path.expanduser('~/.wdtv')
        self.config = ConfigParser.ConfigParser()
        self.config.read(config)

        if not self.config.has_section('api'):
            self.config.add_section('api')

        if apikey is not None:
            self.config.set('api', 'key', apikey)

        if self.config.has_option('api', 'key'):
            tmdb3.set_key(self.config.get('api', 'key'))
        else:
            raise NoAPIKey('An API key is required')

        tmdb3.set_cache(filename='tmdb3.cache')
        with file(config, 'w') as f:
            self.config.write(f)


def handle_recursive(filename, handler):
    errors = []
    if os.path.isdir(filename):
        for subfile in glob.glob(os.path.join(filename, '*')):
            errors += handle_recursive(subfile, handler)
    elif os.path.isfile(filename):
        if not file_regex.match(filename):
            return []
        try:
            handler(filename)
        except Exception, e:
            errors.append((filename, e))
    return errors
