"""artkit.shadow: soft cast shadows as their own pictures, drawn by the game under everything.

The engine bakes no shadows into sprites (a convention that stays the default). A style pack may ask for them as a
separate layer:
  "shadow": {"length": 0.6, "dir": [2, 1], "opacity": 0.35, "blur": 1.5, "color": [16, 14, 20], "lift": 40}
  - length   ground distance the shadow reaches per unit of height (model units / model units)
  - dir      which way shadows fall ON SCREEN (default [2, 1]: down and to the right, away from the upper-left light).
             The ground direction is worked out through the pack's camera, so the same numbers suit top-down too.
  - opacity  darkest the shadow gets (0..1); overlapping parts never darken twice
  - blur     softness, in output pixels
  - color    shadow colour (RGB)
  - lift     for cameras with no ground ("ground": null: flying, floating): the height taken above the ground under the
             lowest point, so an airship's shadow sits apart from it
Every key is optional: "shadow": {} (or true) gives the defaults above. Without the section nothing changes. With it the exporter writes `<sprite>_shadow.png` beside each still stage (its
record gains "shadow": {src, size, near_corner, origin}) and a shadow layer "S" for units (packed with the rest, drawn
with ArtKit.drawUnitShadow). A game draws every shadow first, then every sprite, so a shadow also falls on the
ground under neighbours, never on them.

Cost: shadows are flat 2D polygons filled by Pillow at 4x and blurred, no lighting or lines: a small fraction of a
sprite's render. At runtime one textured quad per thing, in the same batch as everything else.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .core.space import Camera

SS = 4


class Shadow:
    def __init__(s, length=0.6, dir=(2, 1), opacity=0.35, blur=1.5, color=(16, 14, 20), lift=40.0, min_height=1.0):
        s.length, s.dir, s.opacity, s.blur = float(length), tuple(map(float, dir)), float(opacity), float(blur)
        s.color, s.lift, s.min_height = tuple(int(c) for c in color), float(lift), float(min_height)

    @staticmethod
    def from_pack(cfg):
        """The pack's "shadow" section -> Shadow, or None when it has none (or it is false). {} or true: the defaults."""
        if cfg is None or cfg is False: return None
        if cfg is True: cfg = {}
        return Shadow(**{k: v for k, v in cfg.items() if k in ('length', 'dir', 'opacity', 'blur', 'color', 'lift', 'min_height')})


def ground_step(camera, rules):
    """Model ground vector (gx, gy) a shadow moves per unit of height, so that on screen it falls along rules.dir."""
    cam = camera or Camera.ISO
    O = np.zeros(3); ex = np.array([1.0, 0, 0]); ey = np.array([0, 1.0, 0])
    sx0, sy0 = cam.screen(O)
    A = np.array([[cam.screen(ex)[0] - sx0, cam.screen(ey)[0] - sx0], [cam.screen(ex)[1] - sy0, cam.screen(ey)[1] - sy0]], float)
    g = np.linalg.solve(A, np.array(rules.dir, float))
    return g / (np.linalg.norm(g) + 1e-12) * rules.length


def cast(geom, camera, rules):
    """Screen triangles (N, 3, 2), in units before canvas scale, of the geometry's shadow on its ground."""
    cam = camera or Camera.ISO
    P = np.asarray(geom.P, float)
    if not len(P): return np.zeros((0, 3, 2))
    if cam.ground is None:
        z0 = P[..., 2].min() - rules.lift; h = P[..., 2] - z0
    else:
        h = np.clip(cam.height(P), 0, None)
    keep = h.max(1) >= rules.min_height                  # things lying on the ground cast nothing worth drawing
    P, h = P[keep], h[keep]
    gx, gy = ground_step(cam, rules)
    Q = P.copy(); Q[..., 0] += gx * h; Q[..., 1] += gy * h; Q[..., 2] -= h
    sx, sy = cam.screen(Q)
    return np.stack([sx, sy], -1)


def _fill(T, W, H, sc, ox, oy, rules):
    """Fill screen triangles into a W x H picture (sc output px per unit, (ox, oy) where screen (0, 0) lands)."""
    cov = Image.new('L', (W * SS, H * SS), 0); d = ImageDraw.Draw(cov)
    if len(T):
        X = (T[..., 0] * sc + ox) * SS; Y = (T[..., 1] * sc + oy) * SS
        for xs, ys in zip(X.tolist(), Y.tolist()):
            d.polygon([(xs[0], ys[0]), (xs[1], ys[1]), (xs[2], ys[2])], fill=255)
    a = cov.resize((W, H), Image.BOX)
    if rules.blur > 0: a = a.filter(ImageFilter.GaussianBlur(rules.blur))
    a = (np.asarray(a).astype(np.float32) * rules.opacity + 0.5).astype(np.uint8)
    out = np.zeros((H, W, 4), np.uint8); out[..., :3] = rules.color; out[..., 3] = a
    return out


def picture(geom, rules, scale=0.4, footprint=None, camera=None, pad=None):
    """A still's shadow on its own fitted canvas. Returns (PIL RGBA, meta) with size, origin (where world (0, 0, 0)
    lands) and, with a footprint, near_corner, in the same terms as sprite.picture's meta, so a game places it with
    the same point it places the sprite with. None when nothing casts."""
    cam = camera or Camera.ISO
    T = cast(geom, cam, rules)
    if not len(T): return None, None
    pad = pad if pad is not None else 2 + 3 * rules.blur
    sx, sy = T[..., 0], T[..., 1]
    minx = math.floor(sx.min() * scale - pad) / scale; miny = math.floor(sy.min() * scale - pad) / scale
    W = int(math.ceil((sx.max() - minx) * scale + pad)); H = int(math.ceil((sy.max() - miny) * scale + pad))
    arr = _fill(T, W, H, scale, -minx * scale, -miny * scale, rules)
    meta = {'size': [W, H], 'origin': [round(-minx * scale, 2), round(-miny * scale, 2)]}
    if footprint:
        px, py = cam.screen(np.array([float(footprint[0]), float(footprint[1]), 0.0 if cam.ground is None else cam.ground]))
        meta['near_corner'] = [round((float(px) - minx) * scale, 2), round((float(py) - miny) * scale, 2)]
    return Image.fromarray(arr, 'RGBA'), meta


def frame(geom, rules, W, H, sc, ox, oy, camera=None):
    """A shadow on a fixed animation canvas (sc output px per unit, model (0, 0, 0) at (ox, oy)): uint8 RGBA."""
    return _fill(cast(geom, camera, rules), W, H, sc, ox, oy, rules)
