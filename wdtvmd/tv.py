import collections
import os
import re
from xml.etree import ElementTree as ET
import urllib

import tmdb3
import tvdb_api

from wdtvmd import common


combined_regex = re.compile('.*[Ss]([0-9]{1,2})[Ee]([0-9]{1,2}).*')
season_regex = re.compile('.*[Ss]eason ([0-9]{1,2}).*')
numbers_regex = re.compile('.*([0-9]{2}).*')
episode_regex = re.compile('.*[Ee]pisode ([0-9])+.*')


def guess_episode(filename):
    easy = combined_regex.match(filename)
    if easy:
        return int(easy.group(1)), int(easy.group(2))

    season = episode = None

    season_match = season_regex.match(filename)
    if season_match:
        season = int(season_match.group(1))

    base = os.path.basename(filename)
    episode_match = episode_regex.match(base)
    if episode_match:
        episode = int(episode_match.group(1))
    numbers_match = numbers_regex.match(base)
    if not episode and numbers_match:
        episode = int(numbers_match.group(1))

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


def write_tv_xml(target, series, season_num, episode, extra):
    tree = ET.Element('details')
    elements = {
        'id': episode['id'],
        'title': '%02i: %s' % (int(episode['episodenumber']),
                               episode['episodename']),
        'season_number': season_num,
        'episode_number': episode['episodenumber'],
        'overview': episode['overview'],
        'series_name': series['seriesname'],
        'episode_name': episode['episodename'],
        'firstaired': episode['firstaired'],
    }

    if extra.episode:
        elements['actor'] = ' / '.join(
            [foo.name for foo in extra.episode.cast]),

    if extra.series and extra.series.genres:
        elements['genre'] = extra.series.genres[0].name

    for k,v in elements.items():
        ET.SubElement(tree, k).text = unicode(v)

    if extra.series and extra.series.backdrops:
        for bd in extra.series.backdrops:
            ET.SubElement(tree, 'backdrop').text = bd.geturl()

    with file(target, 'w') as output:
        doc = ET.ElementTree(tree)
        doc.write(output, encoding='utf-8', xml_declaration=True)


def _season_banner(season_num, show):
    try:
        for sb in show['_banners']['season']['season']:
            if sb['season'] == str(season_num):
                return sb['_bannerpath']
    except KeyError:
        pass


def write_thumb(target, season_num, show, extra):
    if extra.episode and extra.episode.still:
        thumb = extra.episode.still.geturl()
    else:
        thumb = _season_banner(season_num, show)
    if thumb:
        urllib.urlretrieve(thumb, filename=target)


def write_season_poster(filename, season_num, show, extra):
    base = os.path.dirname(filename)
    target = os.path.join(base, 'folder.jpg')

    if extra.season and extra.season.poster:
        poster = extra.season.poster.geturl()
    else:
        poster = _season_banner(season_num, show)
    if not os.path.exists(target) and poster:
        urllib.urlretrieve(poster, filename=target)


Extra = collections.namedtuple('ExtraInfo',
                               ['series', 'season', 'episode'])


def lookup_extra_info(series_name, season_num, episode_num):
    series = tmdb3.searchSeries(series_name)
    if len(series) == 0:
        return Extra(None, None, None)
    elif len(series) > 1 and series[0].name != series_name:
        return Extra(None, None, None)

    series = series[0]
    season = series.seasons[season_num]
    episode = season.episodes[episode_num]
    return Extra(series, season, episode)


def lookup_tv_file(filename, force=False):
    series_name = guess_series_name(filename)
    season_num, episode_num = guess_episode(filename)

    base, ext = os.path.splitext(filename)
    target_xml = '%s.%s' % (base, 'xml')
    target_thumb = '%s.%s' % (base, 'metathumb')

    if not force and (os.path.exists(target_xml) and
                      os.path.exists(target_thumb)):
        return

    tvdb = tvdb_api.Tvdb(cache=True, actors=True, banners=True)

    result = tvdb.search(series_name)
    if len(result) == 0:
        print 'Not found: %s' % series_name
        return
    elif len(result) > 1:
        if result[0]['seriesname'] != series_name:
            print '  Guessed name `%s`'  % series_name
            print '  Ambiguous result (%i): %s' % (
                len(result),
                ','.join([s['seriesname'] for s in result]))
            raise common.AmbiguousResultError()

    show = result[0]
    series = tvdb[result[0]['seriesname']]
    season = series[season_num]
    episode = season[episode_num]

    extra = lookup_extra_info(series_name, season_num, episode_num)

    print 'Processing: %s: S%02i E%02i (%s) %s' % (
        series_name, season_num, episode_num, episode['episodename'],
        extra.series and '+E' or '')
    write_season_poster(filename, season_num, show, extra)
    write_thumb(target_thumb, season_num, show, extra)
    write_tv_xml(target_xml, series, season_num, episode, extra)


