"""artkit.card: a place on a square plot, drawn as a framed card with a name box above the art.

For card games, autobattlers, build menus and tooltips: one picture that says what a place is at a glance. The place
is a `Scene` (named parts on a square plot, each with a `why`, like `Machine` and `Assembly`), drawn through the
engine's own cameras in either view:

  iso        the plot as a thick tile (its earth sides showing) on a backdrop; walls, doors and heights read
  top_down   the plot fills the art window; roofs and layout read, height comes from cast shadows

Layers, bottom up: the ground parts, cast shadows of everything else (artkit.shadow), everything else. The frame and
the name box are flat 2D (Pillow), drawn in the colours of the pack's optional "card" section.

    from artkit.card import Scene, render
    sc = Scene('Basic Farm', slab='soil')
    sc.add('plot', shapes.block(0, 400, 0, 400, -4, 0, 'grass'), 'the land', ground=True)
    sc.add('barn walls', shapes.box(130, 90, 64, 'barn').move(50, 55, 0), 'the one shape that says farm')
    sc.add('barn roof', shapes.gable(130, 90, 46, 'barn').move(50, 55, 70), 'all you see from above', cover=True)
    print(sc.check())                              # [] when every part has a reason and stays on the plot
    img, meta = render(sc, style, view='iso')      # PIL RGBA, card['size'] square
    review(sc, style, view='iso').save('x.png')    # grey blockout beside the coloured card, 2x

    python3 -m artkit.card <scene.py | module> [--style <pack>] [--view iso|top_down] [--out <dir>]
        a scene file defines build() -> Scene (or a list of them); writes <name>_<view>.png and a review sheet.

Nothing else in the engine uses this module: packs without a "card" section and games that never import it see no
change. tests/card_check.py proves it works in both views.
"""
import importlib, importlib.util, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import sprite, shadow as _shadow
from . import shapes as _sh
from .core.geom import Geometry
from .core.materials import Materials, procedural
from .core.space import Camera, screen_bounds

DEFAULTS = {
    'size': 256,                # the card is size x size pixels
    'border': 8,                # frame width round everything
    'gap': 4,                   # between the name box and the art window
    'name_h': 24,               # name box height
    'font': None,               # a .ttf path; None: DejaVu Sans Bold if installed, else Pillow's own font
    'font_size': 15,            # largest; a long name shrinks until it fits
    'view': 'iso',              # 'iso' or 'top_down' (per call: render(view=))
    'crop': 0.78,               # iso: share of the tile's width shown (its side corners are only ground); never cuts a part
    'slab': 30,                 # iso: depth of the earth under the plot, in units (0: none)
    'shadow': True,             # cast shadows: the pack's "shadow" section, else artkit.shadow's defaults; False: none
    'iso_relief': False,        # keep the pack's light.relief in iso (relief is for views looking straight down)
    'frame': [46, 40, 34],      # card body
    'trim': [200, 176, 120],    # thin line inside the outer edge
    'line': [20, 18, 16],       # outline of the name box and art window
    'name_fill': [232, 220, 190],
    'name_ink': [40, 32, 24],
    'backdrop': [58, 64, 68],   # behind the tile in iso
}

GREYS = {'card_lo': (120, 120, 120), 'card_mid': (160, 160, 160), 'card_hi': (200, 200, 200)}


class Scene:
    """Named parts on a square plot of `size` units (x right, y down the plan, z up; the plot is 0..size on x and y,
    standing on z = 0). ground=True: part of the land (drawn first, takes shadows, casts none). cover=True: what is
    seen from above (roofs, canopies, a gas bag), lightest in the grey blockout. slab: the material of the earth under
    the plot in iso (default: the first ground part's)."""

    def __init__(s, name, size=400, slab=None):
        s.name, s.size, s.slab = name, float(size), slab
        s.parts = []          # (name, geometry, why, ground, cover)

    def add(s, name, geom, why, ground=False, cover=False):
        s.parts.append((name, geom, why, bool(ground), bool(cover)))
        return s

    def geometry(s, layer=None, blockout=False):
        """layer: None (all), 'ground' or 'things'. blockout: every part in one of three greys."""
        out = []
        for name, g, why, ground, cover in s.parts:
            if (layer == 'ground' and not ground) or (layer == 'things' and ground): continue
            out.append(g.mat_as('card_lo' if ground else 'card_hi' if cover else 'card_mid') if blockout else g)
        return Geometry.join(out) if out else None

    def check(s, margin=4.0):
        """Issues as (kind, part, text). NO REASON: a part without a why. OFF PLOT: a standing part reaching past the
        plot's edge on x or y (more than `margin` units), which reads as cut off. NO GROUND: nothing to stand on."""
        issues = []
        for name, g, why, ground, cover in s.parts:
            if not str(why).strip(): issues.append(('NO REASON', name, 'say what this part is for, or cut it'))
            if not ground and len(g):
                P = g.P.reshape(-1, 3)
                lo, hi = P[:, :2].min(0), P[:, :2].max(0)
                if (lo < -margin).any() or (hi > s.size + margin).any():
                    issues.append(('OFF PLOT', name, f'spans x {lo[0]:.0f}..{hi[0]:.0f}, y {lo[1]:.0f}..{hi[1]:.0f} '
                                                     f'on a 0..{s.size:.0f} plot'))
        if not any(p[3] for p in s.parts): issues.append(('NO GROUND', '-', 'add the land as a part with ground=True'))
        return issues


def options(style):
    """The pack's "card" section over the defaults."""
    o = dict(DEFAULTS); o.update(style.section('card') if style is not None else {})
    return o


def _font(o, size):
    for path in ([o['font']] if o['font'] else []) + ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        try: return ImageFont.truetype(path, size)
        except OSError: pass
    try: return ImageFont.load_default(size=size)
    except TypeError: return ImageFont.load_default()


def _grey_materials(style):
    tp = style.cfg.get('tile_px', 128)
    return Materials(tiles={k: procedural(v, 'plain', seed=1, n=tp) for k, v in GREYS.items()},
                     tile_units=style.cfg.get('tile_units', 128), tile_px=tp)


def _camera(view):
    if view not in ('iso', 'top_down'): raise ValueError(f'card view must be "iso" or "top_down", not {view!r}')
    return Camera.from_pack({'view': view, 'ground': 0})


def _layers(ground, things, style, cam, scale, mats, lighting, shade):
    out = []
    if ground is not None: out.append(sprite.picture(ground, style, scale=scale, pad=4, camera=cam, mats=mats, lighting=lighting))
    if things is not None:
        if shade is not None: out.append(_shadow.picture(things, shade, scale=scale, camera=cam))
        out.append(sprite.picture(things, style, scale=scale, pad=4, camera=cam, mats=mats, lighting=lighting))
    return [(im, m) for im, m in out if im is not None]


def art(scene, style, win, view='iso', blockout=False, o=None):
    """The art window alone: a win x win RGBA picture. Returns (picture, meta); meta['parts_box'] is where the standing
    parts landed (pixels) and meta['clipped'] whether any of them reach past the window."""
    o = options(style) if o is None else o
    cam = _camera(view)
    mats = _grey_materials(style) if blockout else None
    rules = getattr(style, 'lighting', None)
    if view == 'iso' and rules is not None and not o['iso_relief']: rules = rules.with_(relief_strength=0.0)
    shade = None
    if o['shadow']: shade = style.shadow if getattr(style, 'shadow', None) is not None else _shadow.Shadow()
    ground = scene.geometry('ground', blockout)
    things = scene.geometry('things', blockout)
    N = scene.size
    if view == 'iso':
        if o['slab'] and ground is not None:
            mat = 'card_lo' if blockout else (scene.slab or next(p[1].mat[0] for p in scene.parts if p[3]))
            ground = ground + _sh.block(0, N, 0, N, -float(o['slab']) - 4, -4, mat)
        gx0, gy0, gx1, gy1 = screen_bounds((ground if ground is not None else things).P)
        tx0, ty0, tx1, ty1 = screen_bounds(things.P) if things is not None else (gx0, gy0, gx1, gy1)
        y0, y1 = min(gy0, ty0), max(gy1, ty1)
        sc = min(win / ((gx1 - gx0) * o['crop']), win / (tx1 - tx0 + 30) * 0.97, win / (y1 - y0) * 0.97)
        cx = (max(min(gx0, tx0), tx0 - 15) + min(max(gx1, tx1), tx1 + 15)) / 2
        O = (win / 2 - cx * sc, win / 2 - (y0 + y1) / 2 * sc)
        back = tuple(o['backdrop']) + (255,)
    else:
        sc = win / N
        O = (0.0, 0.0)                    # top-down: world (x, y) lands on pixel (x, y) * sc; the plot fills the window
        back = (0, 0, 0, 0)
    out = Image.new('RGBA', (win, win), back)
    for im, m in _layers(ground, things, style, cam, sc, mats, rules, shade):
        layer = Image.new('RGBA', (win, win), (0, 0, 0, 0))
        layer.paste(im, (round(O[0] - m['origin'][0]), round(O[1] - m['origin'][1])))
        out.alpha_composite(layer)
    meta = {'scale': sc, 'origin': [round(O[0], 2), round(O[1], 2)], 'clipped': False, 'parts_box': None}
    if things is not None:
        x0, y0_, x1, y1_ = screen_bounds(things.P, camera=cam if cam.M is not None else None)
        box = [O[0] + x0 * sc, O[1] + y0_ * sc, O[0] + x1 * sc, O[1] + y1_ * sc]
        meta['parts_box'] = [round(v, 1) for v in box]
        meta['clipped'] = box[0] < -0.5 or box[1] < -0.5 or box[2] > win + 0.5 or box[3] > win + 0.5
    return out, meta


def render(scene, style, view=None, blockout=False, name=None):
    """The whole card: frame, name box, art window. Returns (PIL RGBA, meta) with the art's meta plus 'window' (the
    art window's x0, y0, x1, y1 on the card) and 'name_box'."""
    o = options(style)
    view = view or o['view']
    S, B, G, NH = int(o['size']), int(o['border']), int(o['gap']), int(o['name_h'])
    win = S - 2 * B - NH - G
    if win < 16: raise ValueError(f'card size {S} leaves no room for art (border {B}, name box {NH}, gap {G})')
    c = Image.new('RGBA', (S, S), tuple(o['frame']) + (255,))
    d = ImageDraw.Draw(c)
    d.rectangle((2, 2, S - 3, S - 3), outline=tuple(o['trim']) + (255,), width=2)
    nb = (B - 1, B - 1, S - B, B + NH - 1)
    d.rectangle(nb, fill=tuple(o['name_fill']) + (255,), outline=tuple(o['line']) + (255,), width=1)
    text = scene.name if name is None else name
    size = int(o['font_size'])
    while True:
        f = _font(o, size)
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        if r - l <= (nb[2] - nb[0]) - 10 or size <= 7: break
        size -= 1
    d.text(((nb[0] + nb[2]) / 2, (nb[1] + nb[3]) / 2 + 1), text, font=f, fill=tuple(o['name_ink']) + (255,), anchor='mm')
    ax, ay = (S - win) // 2, B + NH + G
    pic, meta = art(scene, style, win, view, blockout, o)
    c.alpha_composite(pic, (ax, ay))
    d.rectangle((ax - 1, ay - 1, ax + win, ay + win), outline=tuple(o['line']) + (255,), width=1)
    meta.update({'window': [ax, ay, ax + win, ay + win], 'name_box': list(nb), 'view': view, 'size': [S, S]})
    return c, meta


def review(scene, style, view=None, zoom=2):
    """The grey blockout beside the coloured card, on one sheet (the DESIGN_METHOD review picture for a card)."""
    a, _ = render(scene, style, view, blockout=True)
    b, _ = render(scene, style, view)
    S = a.size[0]
    s = Image.new('RGBA', (S * 2 + 24, S + 16), (70, 72, 68, 255))
    s.alpha_composite(a, (8, 8)); s.alpha_composite(b, (S + 16, 8))
    return s.resize((s.width * zoom, s.height * zoom), Image.NEAREST) if zoom != 1 else s


def load_scenes(target):
    """A scene file (path) or module name whose build() returns a Scene or a list of them."""
    if os.path.isfile(target):
        sys.path.insert(0, os.path.dirname(os.path.abspath(target)))
        spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(target))[0], target)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    else:
        mod = importlib.import_module(target)
    out = mod.build()
    return list(out) if isinstance(out, (list, tuple)) else [out]


def _slug(name):
    return ''.join(ch if ch.isalnum() else '_' for ch in name.lower()).strip('_')


def main(argv=None):
    import argparse
    from .style import Style
    ap = argparse.ArgumentParser(prog='python3 -m artkit.card', description='Render scenes as framed cards.')
    ap.add_argument('scenes', nargs='+', help='scene files or modules defining build()')
    ap.add_argument('--style', default=None, help='style pack (default: the game\'s one pack or ARTKIT_STYLE)')
    ap.add_argument('--view', choices=('iso', 'top_down'), default=None)
    ap.add_argument('--out', default='cards')
    a = ap.parse_args(argv)
    st = Style.load(a.style)
    os.makedirs(a.out, exist_ok=True)
    bad = 0
    for target in a.scenes:
        for sc in load_scenes(target):
            for kind, part, text in sc.check():
                print(f'{sc.name}: {kind} {part}: {text}'); bad += 1
            img, meta = render(sc, st, a.view)
            v = meta['view']
            img.save(os.path.join(a.out, f'{_slug(sc.name)}_{v}.png'))
            review(sc, st, v).save(os.path.join(a.out, f'{_slug(sc.name)}_{v}_review.png'))
            print(f'{sc.name}: {v} card {meta["size"][0]} px' + ('  (parts reach past the window)' if meta['clipped'] else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
