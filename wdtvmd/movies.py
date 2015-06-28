import datetime
import os
import urllib
import re
from xml.etree import ElementTree as ET

import tmdb3

from wdtvmd import common


year_regex = re.compile('.+(\()([12][0-9]{3})(\)).*')


def guess_year(filename):
    year_match = year_regex.match(os.path.basename(filename))
    if year_match:
        return int(year_match.group(2))
    else:
        return None


def guess_name(filename):
    base, ext = os.path.splitext(os.path.basename(filename))
    return base


def write_movie_xml(target, movie):
    tree = ET.Element('details')
    elements = {
        'id': movie.id,
        'imdb_id': movie.imdb,
        'overview': movie.overview,
        'year': '%04i-%02i-%02i' % (movie.releasedate.year,
                                    movie.releasedate.month,
                                    movie.releasedate.day),
        'runtime': movie.runtime,
        'title': movie.title,
        'cast': ' / '.join([c.name for c in movie.cast]),
        'genre': movie.genres[0].name,
    }

    for k, v in elements.items():
        ET.SubElement(tree, k).text = unicode(v)

    for bd in movie.backdrops:
        ET.SubElement(tree, 'backdrop').text = bd.geturl()

    with file(target, 'w') as output:
        doc = ET.ElementTree(tree)
        doc.write(output, encoding='utf-8', xml_declaration=True)


def write_poster(target, movie):
    if movie.poster:
        urllib.urlretrieve(movie.poster.geturl(), filename=target)


def process_hint(hint):
    year_match = year_regex.match(hint)
    if year_match:
        year = year_match.group(2)
        name = hint.replace(''.join(year_match.groups()), '')
        return name, year
    else:
        return hint, None


def get_options(results):
    options = []
    for result in results:
        if isinstance(result.releasedate, datetime.date):
            options.append('%s (%s)' % (result.title, result.releasedate.year))
        else:
            options.append(result.title)
    return options


def lookup_movie_file(filename, force=False, hint=None):
    if hint:
        name, year = process_hint(hint)
    else:
        name = guess_name(filename)
        year = guess_year(filename)
        if year:
            name = name.replace('(%s)' % year, '').strip()

    base, ext = os.path.splitext(filename)
    target_xml = '%s.%s' % (base, 'xml')
    target_thumb = '%s.%s' % (base, 'metathumb')

    if not force and (os.path.exists(target_xml) and
                      os.path.exists(target_thumb)):
        return

    result = tmdb3.searchMovie(name, year=year)
    if len(result) == 0:
        print 'Not found: %s' % name
        return
    elif len(result) > 1:
        if hint:
            result = [m for m in result if m.title == hint]
        elif result[0].title != name:
            raise common.AmbiguousResultError(
                name, get_options(result))

    movie = result[0]
    print 'Processing %s' % movie.title
    write_poster(target_thumb, movie)
    write_movie_xml(target_xml, movie)
