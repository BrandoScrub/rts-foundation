"""artkit.terrain: ground tiles, rock and ore atlases and in-line gates, on artkit's camera, light and line
(was terrainkit/). Every colour, target and recipe comes from the style pack's terrain section
(styles/<style>/terrain.json); the code here knows no game.

  ground.py    procedural ground tiles from recipes in the pack (stand-ins until tiles are painted)
  painted.py   fit painted ground tiles: seam, size, tone, grain (targets and sources in the pack)
  rocks.py     rock and ore outcrops from heightfields, packed into one atlas per land
  calm.py      the cohesion pass for rock atlases
  gates.py     gates built to the wall section: wood/concrete x line direction x shut/open
  noise.py     seamless noise and colour helpers

  python3 -m artkit.terrain {ground|fit|fit-one|rocks|calm|gates} ... [--style <pack>]
"""
import functools


@functools.lru_cache(None)
def _style(style):
    from ..style import Style
    return Style.load(style)


def terrain_section(style=None):
    """The style pack's terrain section (a dict); `style` is a pack name or folder."""
    return _style(style).section('terrain')


def style_path(style, rel):
    return _style(style).path(rel)
