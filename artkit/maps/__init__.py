"""artkit.maps: narrative map generation (was mapkit/). The generator is JavaScript (mapkit.js, no game knowledge, runs
in Node and inlines into a browser game); a game's templates (land, sites, districts, eras, names) are data in its
style pack: styles/<style>/maps/templates.js, named by style.json "maps": {"templates": ...}. See README.md here.

  python3 -m artkit.maps inline <index.html> [--style <pack>]
  node artkit/tests/maps_identity.js artkit/maps/mapkit.js <game>/styles/<pack>/maps/templates.js
"""
import functools, os

HERE = os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(None)
def _style(style):
    from ..style import Style
    return Style.load(style)


def templates_path(style=None):
    st = _style(style)
    return st.path(st.section('maps').get('templates', 'maps/templates.js'))
