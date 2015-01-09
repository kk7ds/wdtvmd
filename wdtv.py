import glob
import os
import re
import sys
from xml.etree import ElementTree as ET
import urllib
import ConfigParser

import tmdb3


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


class FilenameFormatError(Exception):
    pass


class AmbiguousResultError(Exception):
    pass


class NoAPIKey(Exception):
    pass


file_regex = re.compile('.*\.(mkv|mp4|m4v|avi|mpg|mp2)')
combined_regex = re.compile('.*[Ss]([0-9]{1,2})[Ee]([0-9]{1,2}).*')
season_regex = re.compile('.*[Ss]eason ([0-9]{1,2}).*')
numbers_regex = re.compile('.*([0-9]{2}).*')


def guess_episode(filename):
    easy = combined_regex.match(filename)
    if easy:
        return int(easy.group(1)), int(easy.group(2))

    season = episode = None

    season_match = season_regex.match(filename)
    if season_match:
        season = int(season_match.group(1))

    base = os.path.basename(filename)
    episode_match = numbers_regex.match(base)
    if episode_match:
        episode = int(episode_match.group(1))

    if not episode or not season:
        raise FilenameFormatError('Unable to detect season/episode info')

    return season, episode


def guess_series_name(filename):
    """Expects /foo/Series/Season X/episode.mkv"""
    pieces = filename.split('/')
    top = pieces[-3]
    mid = pieces[-2]

    if 'season' in mid.lower():
        return top
    return mid


def write_tv_xml(filename, series, season, episode):
    base, ext = os.path.splitext(filename)
    target = '%s.%s' % (base, 'xml')

    tree = ET.Element('details')
    ET.SubElement(tree, 'id').text = str(episode.id)
    ET.SubElement(tree, 'title').text = '%02i: %s' % (episode.episode_number,
                                                      episode.name)
    ET.SubElement(tree, 'season_number').text = str(season.season_number)
    ET.SubElement(tree, 'episode_number').text = str(episode.episode_number)
    ET.SubElement(tree, 'overview').text = episode.overview
    ET.SubElement(tree, 'series_name').text = series.name
    ET.SubElement(tree, 'episode_name').text = episode.name
    ET.SubElement(tree, 'firstaired').text = '%i-%02i-%02i' % (
        episode.air_date.year, episode.air_date.month, episode.air_date.day)

    ET.SubElement(tree, 'genre').text = series.genres[0].name
    ET.SubElement(tree, 'actor').text = '/'.join([foo.name for foo in episode.cast])
    for bd in series.backdrops:
        ET.SubElement(tree, 'backdrop').text = bd.geturl()

    with file(target, 'w') as output:
        output.write(ET.tostring(tree))


def write_thumb(filename, episode):
    base, ext = os.path.splitext(filename)
    target = '%s.%s' % (base, 'metathumb')
    if not os.path.exists(target) and episode.still:
        urllib.urlretrieve(episode.still.geturl(), filename=target)


def write_season_poster(filename, season, episode):
    base = os.path.dirname(filename)
    target = os.path.join(base, 'folder.jpg')
    if not os.path.exists(target) and season.poster:
        urllib.urlretrieve(season.poster.geturl(), filename=target)


def lookup_tv_file(filename):
    series_name = guess_series_name(filename)
    season_num, episode_num = guess_episode(filename)

    result = tmdb3.searchSeries(series_name)
    if len(result) != 1:
        if result[0].name != series_name:
            print '  Guessed name `%s`'  % series_name
            print '  Ambiguous result (%i): %s' % (
                len(result),
                ','.join([series.name for series in result]))
            raise AmbiguousResultError()

    series = result[0]
    season = series.seasons[season_num]
    episode = season.episodes[episode_num]
    print 'Processing: %s: S%02i E%02i (%s)' % (
        series_name, season_num, episode_num, episode.name)
    write_season_poster(filename, season, episode)
    write_thumb(filename, episode)
    write_tv_xml(filename, series, season, episode)


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
            errors.append(e)
    return errors
