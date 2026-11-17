"""Inline the map generator and a style's templates into a game's HTML page, between the markers
/*MAPKIT-INLINE-START*/ and /*MAPKIT-INLINE-END*/. Run after editing artkit/maps/mapkit.js or the style's
maps/templates.js. Do not edit the inlined copy in the page.
  python3 -m artkit.maps inline <index.html> [--style <pack>]"""
import os
from . import HERE, templates_path

A = '/*MAPKIT-INLINE-START*/'; B = '/*MAPKIT-INLINE-END*/'


def code(style=None):
    return (open(os.path.join(HERE, 'mapkit.js'), encoding='utf-8').read() + '\n'
            + open(templates_path(style), encoding='utf-8').read())


def inline(index_html, style=None):
    s = open(index_html, encoding='utf-8').read(); c = code(style)
    if A not in s: raise SystemExit('markers missing')
    a = s.index(A); b = s.index(B) + len(B)
    s = s[:a] + A + '\n' + c + B + s[b:]
    open(index_html, 'w', encoding='utf-8').write(s)
    return len(c)
