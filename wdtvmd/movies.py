import os
import urllib
from xml.etree import ElementTree as ET

import tmdb3

from wdtvmd import common


def guess_name(filename):
    base, ext = os.path.splitext(os.path.basename(filename))
    return base


def write_movie_xml(filename, movie):
    base, ext = os.path.splitext(filename)
    target = '%s.%s' % (base, 'xml')

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


def write_poster(filename, movie):
    base, ext = os.path.splitext(filename)
    target = '%s.metathumb' % base
    if not os.path.exists(target) and movie.poster:
        urllib.urlretrieve(movie.poster.geturl(), filename=target)


def lookup_movie_file(filename):
    name = guess_name(filename)

    result = tmdb3.searchMovie(name)
    if len(result) != 1:
        if result[0].title != name:
            print '  Guessed name: %s' % name
            print '  Ambiguous result (%i): %s' % (
                len(result),
                ','.join([m.title for m in result]))
            raise common.AmbiguousResultError()

    movie = result[0]
    print 'Processing %s' % movie.title
    write_poster(filename, movie)
    write_movie_xml(filename, movie)