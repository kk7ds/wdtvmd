import os
import re
from xml.etree import ElementTree as ET
import urllib

import tmdb3

from wdtvmd import common


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
        raise common.FilenameFormatError(
            'Unable to detect season/episode info')

    return season, episode


def guess_series_name(filename):
    """Expects /foo/Series/Season X/episode.mkv"""
    pieces = filename.split('/')
    top = pieces[-3]
    mid = pieces[-2]

    if 'season' in mid.lower():
        return top
    return mid


def write_tv_xml(target, series, season, episode):
    tree = ET.Element('details')
    elements = {
        'id': episode.id,
        'title': '%02i: %s' % (episode.episode_number,
                               episode.name),
        'season_number': season.season_number,
        'episode_number': episode.episode_number,
        'overview': episode.overview,
        'series_name': series.name,
        'episode_name': episode.name,
        'firstaired': '%i-%02i-%02i' % (
            episode.air_date.year, episode.air_date.month,
            episode.air_date.day),
        'genre': series.genres[0].name,
        'actor': ' / '.join([foo.name for foo in episode.cast]),
    }

    for k,v in elements.items():
        ET.SubElement(tree, k).text = unicode(v)

    for bd in series.backdrops:
        ET.SubElement(tree, 'backdrop').text = bd.geturl()

    with file(target, 'w') as output:
        doc = ET.ElementTree(tree)
        doc.write(output, encoding='utf-8', xml_declaration=True)


def write_thumb(target, episode):
    if episode.still:
        urllib.urlretrieve(episode.still.geturl(), filename=target)


def write_season_poster(filename, season, episode):
    base = os.path.dirname(filename)
    target = os.path.join(base, 'folder.jpg')
    if not os.path.exists(target) and season.poster:
        urllib.urlretrieve(season.poster.geturl(), filename=target)


def lookup_tv_file(filename, force=False):
    series_name = guess_series_name(filename)
    season_num, episode_num = guess_episode(filename)

    base, ext = os.path.splitext(filename)
    target_xml = '%s.%s' % (base, 'xml')
    target_thumb = '%s.%s' % (base, 'metathumb')

    if not force and (os.path.exists(target_xml) and
                      os.path.exists(target_thumb)):
        return

    result = tmdb3.searchSeries(series_name)
    if len(result) == 0:
        print 'Not found: %s' % series_name
        return
    elif len(result) > 1:
        if result[0].name != series_name:
            print '  Guessed name `%s`'  % series_name
            print '  Ambiguous result (%i): %s' % (
                len(result),
                ','.join([series.name for series in result]))
            raise common.AmbiguousResultError()

    series = result[0]
    season = series.seasons[season_num]
    episode = season.episodes[episode_num]
    print 'Processing: %s: S%02i E%02i (%s)' % (
        series_name, season_num, episode_num, episode.name)
    write_season_poster(filename, season, episode)
    write_thumb(target_thumb, episode)
    write_tv_xml(target_xml, series, season, episode)


