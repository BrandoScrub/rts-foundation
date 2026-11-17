"""artkit.sprite: geometry -> finished sprites, with every game-facing number taken from the style.

  picture(geom, style, footprint=(w, d))     one still: a building, prop, terrain piece or a pose of anything
  frame(geom, style, box, scale)             one frame on a fixed canvas, for animation strips (all frames align)

Lines are always one game pixel wide at zoom 1: the style says how big an output pixel is in the game.
Both draw through the style's camera (style.camera, the pack's "camera" section; isometric when it has none), so a
model is built in that camera's axes. camera= overrides it for one call.
"""
import math
import numpy as np
from PIL import Image

from .core import render as R
from .core import ink
from .core.geom import FLAT, SMOOTH

AA = 5
EDGE_FLAT, EDGE_SMOOTH = 12.0, 5.0


def _edge(geom):
    return EDGE_SMOOTH if (geom.look == SMOOTH).mean() > 0.5 else EDGE_FLAT


def picture(geom, style, footprint=None, scale=0.4, pad=16, game_px_per_out=None, edge_step=None, ink_emit=False, ss=AA, mats=None,
            camera=None, lighting=None, team=None):
    """Fitted still. Returns (PIL RGBA, meta) where meta has size, scale and, with a footprint, the screen position of
    the footprint's centre and near corner (what a game uses to place it). lighting: core.light.Rules for this call
    (default the style's "light" section, if any). team: an artkit.team.Team; with it meta also holds 'team_mask',
    the picture's team mask (uint8 array, same size), which the exporter saves and takes out of meta."""
    extra = None
    if footprint:
        fx, fy = footprint
        extra = np.array([(0, 0, 0), (fx, 0, 0), (0, fy, 0), (fx, fy, 0)], float)
    cam = getattr(style, 'camera', None) if camera is None else camera
    cv, (minx, miny), (OW, OH) = R.Canvas.around(geom, scale, ss, pad, extra, np.float32, camera=cam)
    mats = style.materials() if mats is None else mats
    rules = getattr(style, 'lighting', None) if lighting is None else lighting
    B = R.raster(geom, mats, cv, grain=R.grain_field(OW, OH, ss), camera=cam, team=team,
                 faces=rules is not None and getattr(rules, 'ink_crease', None) is not None)
    gp = style.building_px_per_out * (0.4 / scale) if game_px_per_out is None else game_px_per_out
    out = R.finish(B, ss, ink.radius(gp / ss), edge_step or _edge(geom), ao_px=cv.s if (geom.look == FLAT).any() else None,
                   no_seed=B.thin | (B.emit & ~B.flat), no_rim=B.low, ink_emit=ink_emit, rules=rules)
    img = Image.fromarray(out, 'RGBA')
    meta = {'size': list(img.size), 'scale': scale}
    if team is not None:
        from .team import mask
        meta['team_mask'] = mask(B, ss)
    if footprint:
        FX, FY = float(footprint[0]), float(footprint[1])
        if cam is None or cam.M is None:
            meta['centre'] = [round(((FX - FY) / 2 - minx) * scale, 2), round(((FX + FY) / 4 - miny) * scale, 2)]
            meta['near_corner'] = [round(((FX - FY) - minx) * scale, 2), round(((FX + FY) / 2 - miny) * scale, 2)]
        else:
            for k, p in (('centre', (FX / 2, FY / 2, 0)), ('near_corner', (FX, FY, 0))):
                sx, sy = cam.screen(np.array(p, float))
                meta[k] = [round((float(sx) - minx) * scale, 2), round((float(sy) - miny) * scale, 2)]
    meta['origin'] = [round(-minx * scale, 2), round(-miny * scale, 2)]      # where world (0, 0, 0) lands (any camera)
    return img, meta


def frame(geom, style, box, scale=0.4, k=None, ss=AA, full=None, edge_step=None, buffers=False, camera=None, lighting=None):
    """box = (half_width, up, down) in units round the origin (0, 0, 0), which lands at (W/2, up*scale).
    Returns (uint8 RGBA, origin). k: game pixels per output pixel (default the style's figure_k)."""
    hw, up, down = box
    W = int(math.ceil(2 * hw * scale)); H = int(math.ceil((up + down) * scale))
    ox, oy = W / 2.0, up * scale
    cv = R.Canvas(W * ss, H * ss, scale * ss, ox=ox * ss, oy=oy * ss)
    cam = getattr(style, 'camera', None) if camera is None else camera
    rules = getattr(style, 'lighting', None) if lighting is None else lighting
    B = R.raster(geom, style.materials(), cv, grain=R.grain_field(W, H, ss).astype(np.float64) if (geom.look == FLAT).any() else None,
                 camera=cam, faces=rules is not None and getattr(rules, 'ink_crease', None) is not None)
    if buffers: return B, cv
    kk = (style.figure_k * 0.4 / scale) if k is None else k
    out = R.finish(B, ss, ink.radius(kk / ss), edge_step or _edge(geom), ao_px=cv.s if (geom.look == FLAT).any() else None,
                   no_seed=B.thin | (B.emit & ~B.flat), no_rim=B.low, full=full, rules=rules)
    return out, (ox, oy)


def sheet(images, labels=None, cols=4, bg=(70, 72, 68), pad=12, zoom=1):
    """Contact sheet of PIL images, labels underneath."""
    from PIL import ImageDraw, ImageFont
    ims = [im.resize((im.size[0] * zoom, im.size[1] * zoom), Image.NEAREST) if zoom != 1 else im for im in images]
    cw = max(i.size[0] for i in ims) + pad * 2; ch = max(i.size[1] for i in ims) + pad * 2 + (22 if labels else 0)
    rows = math.ceil(len(ims) / cols)
    out = Image.new('RGBA', (cw * cols, ch * rows), tuple(bg) + (255,)); d = ImageDraw.Draw(out)
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)
    except OSError: font = None
    for k, im in enumerate(ims):
        x = (k % cols) * cw + (cw - im.size[0]) // 2; y = (k // cols) * ch + (ch - (22 if labels else 0) - pad - im.size[1])
        out.alpha_composite(im, (x, y))
        if labels: d.text(((k % cols) * cw + pad, (k // cols) * ch + ch - 22), labels[k], fill=(230, 220, 190, 255), font=font)
    return out
