"""artkit: one art engine for strategy games, isometric by default (top-down and other views are options). Flat painted tiles + code-built geometry -> sprites, for any game.

  from artkit import Style, shapes, picture
  st = Style.load('frontier_outpost')
  img, meta = picture(shapes.box(160, 160, 120, 'brick@home'), st, footprint=(160, 160))

See README.md for the layers and how to start a new game.
"""
from .core.geom import Geometry, FLAT, SMOOTH, T, RX, RY, RZ, R3, S, xf, aim, ik2
from .style import Style
from .sprite import picture, frame, sheet
from . import shapes
