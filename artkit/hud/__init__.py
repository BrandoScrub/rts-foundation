"""artkit.hud: HUD skins made the same way as the sprites (was hudkit/). The look (plate colours, the brass ramp,
outline, groove and backing colours, slot tint and glow, random seeds) comes from the style pack's hud section
(styles/<style>/hud.json); the shapes and 9-slice sizes are in skin.py and fit any game's CSS.

  python3 -m artkit.hud <out_dir> [--style <pack>]
"""
import functools


@functools.lru_cache(None)
def _style(style):
    from ..style import Style
    return Style.load(style)


def hud_section(style=None):
    return _style(style).section('hud')
