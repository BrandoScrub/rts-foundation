"""artkit.motifs: the vocabulary a theme builds with. Each motif is a recognisable, reusable piece of a visual
language (a finned tower, a banner, a blast door, a sandbag berm, a ribbed dome) that takes its materials from the
theme, so the same motif reads as one game in one style pack and as another game in another.

A theme (the "design" section of style.json) says which motifs it uses and where; the composer (artkit/design.py)
and hand-written structures both call them. Every motif adds named, tagged parts to an Assembly.

Call shape: motif(c, ...) where c is a Site: c.asm (Assembly), c.m(role) (theme material for a role such as
'base', 'body', 'roof', 'trim', 'metal', 'dark', 'stack', 'bags', 'wood', 'faction', 'glow'), c.rng.
Visible faces are +y ('y', lit, front) and +x ('x', shaded, right).
"""
import math
import numpy as np

from .core.geom import Geometry
from . import shapes as sh
from . import library as lib
from .parts import building as B

J = Geometry.join
MOTIFS = {}


def motif(fn):
    MOTIFS[fn.__name__] = fn
    return fn


def _on(vol, side, f, z, out=0.0):
    """Point on a visible wall: f along it (0..1), z up from the volume's foot, out from the wall."""
    if side == 'y': return (vol.x + f * vol.w, vol.y + vol.d + out, vol.z + z)
    return (vol.x + vol.w + out, vol.y + f * vol.d, vol.z + z)


# ---------------------------------------------------------------- bases
@motif
def casemate(c, vol, h, name='casemate'):
    """Armour poured round the foot of an older building: a proud concrete band, a low glacis, a drip ledge."""
    m = c.m('base')
    c.asm.add(f'{name}.band', sh.box(vol.w + 14, vol.d + 14, h, m).move(vol.x - 7, vol.y - 7, vol.z), grounded=True, tag='base')
    if vol.z < 4:
        c.asm.add(f'{name}.glacis', B.frustum(vol.x - 22, vol.y - 22, vol.x + vol.w + 22, vol.y + vol.d + 22, 15, 26, m), grounded=True, tag='base')
    c.asm.add(f'{name}.ledge', sh.box(vol.w + 22, 10, 10, m).move(vol.x - 11, vol.y + vol.d + 2, vol.z + h)
              + sh.box(10, vol.d + 22, 10, m).move(vol.x + vol.w + 2, vol.y - 11, vol.z + h), grounded=True, tag='trim')


@motif
def plinth(c, vol, h, name='plinth'):
    """A plain footing a little wider than the wall."""
    c.asm.add(name, sh.box(vol.w + 12, vol.d + 12, min(h, 18), c.m('base')).move(vol.x - 6, vol.y - 6, vol.z), grounded=True, tag='base')


@motif
def skirt(c, vol, h, name='skirt'):
    """A battered (sloping) foot: the wall leans out to the ground."""
    c.asm.add(name, B.frustum(vol.x - 18, vol.y - 18, vol.x + vol.w + 18, vol.y + vol.d + 18, 18, h, c.m('base')), grounded=True, tag='base')


# ---------------------------------------------------------------- roofs
@motif
def parapet(c, vol, name='roof'):
    c.asm.add(f'{name}.parapet', B.parapet(vol.w + 8, vol.d + 8, c.m('base'), rim=13, h=16).move(vol.x - 4, vol.y - 4, vol.top()), tag='roof')


@motif
def gable(c, vol, rise=None, name='roof'):
    rise = rise or min(vol.d * .32, 70)
    c.asm.add(f'{name}.ends', B.gable_ends(vol.w, vol.d, rise, c.m('body')).move(vol.x, vol.y, vol.top()), tag='body')
    c.asm.add(f'{name}.gable', sh.gable(vol.w, vol.d, rise, c.m('roof2'), cap=c.m('trim')).move(vol.x, vol.y, vol.top()), tag='roof')
    return rise


@motif
def shed(c, vol, rise=None, name='roof'):
    rise = rise or min(vol.d * .22, 46)
    c.asm.add(f'{name}.shed', B.shed_roof(vol.w, vol.d, rise, c.m('roof2'), c.m('body'), cap=c.m('trim')).move(vol.x, vol.y, vol.top()), tag='roof')
    return rise


@motif
def deck(c, vol, name='roof'):
    """A flat technical roof: thin rim and a walkway grating."""
    c.asm.add(f'{name}.rim', B.parapet(vol.w + 6, vol.d + 6, c.m('trim'), rim=7, h=7).move(vol.x - 3, vol.y - 3, vol.top()), tag='roof')


@motif
def dome(c, vol, name='roof', ribs=True):
    r = min(vol.w, vol.d) / 2 * .96; cx, cy = vol.x + vol.w / 2, vol.y + vol.d / 2
    c.asm.add(f'{name}.dome', sh.dome(r, c.m('roof'), n=16, rings=5).rz(11.25).move(cx, cy, vol.top()), tag='roof')
    return r * .98


# ---------------------------------------------------------------- wall rhythm, openings, accents
@motif
def fins(c, vol, side, n, z0, z1, name='fins', proud=12, w=14):
    """Vertical fins standing proud of a wall at every bay line: the 1920s dam and radio-palace look."""
    out = []
    for i in range(n + 1):
        f = i / n
        x, y, z = _on(vol, side, f, z0)
        out.append(sh.box(w, proud, z1 - z0, c.m('trim')).move(x - w / 2, y, z) if side == 'y' else sh.box(proud, w, z1 - z0, c.m('trim')).move(x, y - w / 2, z))
    c.asm.add(f'{name}.{side}', J(out), grounded=True, tag='trim')


@motif
def ribs(c, vol, side, n, z0, z1, name='ribs'):
    """Slim structural ribs: a lighter, engineered rhythm."""
    fins(c, vol, side, n, z0, z1, name=name, proud=6, w=8)


def opening(c, vol, side, f, z, w, h, kind):
    lit = kind in ('window_lit',) or kind == c.th.get('values', {}).get('glow')
    x, y, zz = _on(vol, side, f, z)
    c.asm.extra(B.decal(x, y, zz, w, h, kind, side, emit=lit, bias=3), 'opening')


@motif
def banner(c, vol, side, f, z0, z1, w=64, name='banner'):
    """The faction's colours hung full height from a rail: the one colour that carries at play size."""
    x, y, _ = _on(vol, side, f, 0); h = z1 - z0; cloth, hem, rail = c.m('faction'), c.m('dark'), c.m('metal')
    zz0, zz1 = vol.z + z0, vol.z + z1
    em = c.th.get('values', {}).get('emblem')
    if side == 'y':
        g = sh.quad((x - w / 2, y + 1.4, zz0), (w, 0, 0), (0, 0, h), cloth, bias=2) + sh.quad((x - w / 2, y + 1.8, zz0), (w, 0, 0), (0, 0, 7), hem, bias=3, wear=False)
        r = sh.box(w + 14, 6, 6, rail, wear=False).move(x - w / 2 - 7, y, zz1 - 2)
    else:
        g = sh.quad((x + 1.4, y + w / 2, zz0), (0, -w, 0), (0, 0, h), cloth, bias=2) + sh.quad((x + 1.8, y + w / 2, zz0), (0, -w, 0), (0, 0, 7), hem, bias=3, wear=False)
        r = sh.box(6, w + 14, 6, rail, wear=False).move(x, y - w / 2 - 7, zz1 - 2)
    c.asm.add(f'{name}.cloth', g, grounded=True, tag='accent'); c.asm.add(f'{name}.rail', r, grounded=True, tag='trim')
    if em and h > w + 24:
        ex, ey, ez = _on(vol, side, f, z1 - w - 10, out=0.6)
        c.asm.extra(B.decal(ex, ey, ez, w - 10, w - 10, em, side, bias=4), 'accent')


@motif
def band(c, vol, z, h=16, name='band', mat=None):
    """A band of the accent colour round the faces you can see."""
    m = mat or c.m('accent')
    g = sh.box(vol.w + 6, 4, h, m, wear=False).move(vol.x - 3, vol.y + vol.d - 1, vol.z + z) + sh.box(4, vol.d + 6, h, m, wear=False).move(vol.x + vol.w - 1, vol.y - 3, vol.z + z)
    c.asm.add(name, g, grounded=True, tag='accent')


@motif
def light_strip(c, vol, side, z, f0=.12, f1=.88, h=9, name='lights'):
    a = _on(vol, side, f0, z, .7); b = _on(vol, side, f1, z, .7)
    g = sh.quad(a, (b[0] - a[0], 0, 0), (0, 0, h), c.m('glow'), emit=True, bias=3, wear=False) if side == 'y' else \
        sh.quad((a[0], b[1], a[2]), (0, a[1] - b[1], 0), (0, 0, h), c.m('glow'), emit=True, bias=3, wear=False)
    c.asm.add(f'{name}.{side}', g, grounded=True, tag='opening')


# ---------------------------------------------------------------- doors
@motif
def blast_door(c, vol, f, depth=50, name='door'):
    """A concrete blockhouse through the wall, steel doors, a hazard-striped frame and a lamp over it."""
    x, y, _ = _on(vol, 'y', f, 0); pw, ph = 112, 118; base = c.m('base'); steel = c.m('metal')
    c.asm.add(f'{name}.portal', sh.box(pw, depth + 10, ph, base).move(x - pw / 2, y - 10, 0), grounded=True, tag='base')
    c.asm.add(f'{name}.lintel', sh.box(pw + 14, depth + 16, 9, base).move(x - pw / 2 - 7, y - 13, ph), tag='trim')
    fy = y + depth
    c.asm.add(f'{name}.leaves', sh.box(56, 3, 90, steel, wear=False).move(x - 28, fy, 0) + sh.box(3, 3.4, 90, c.m('dark'), wear=False).move(x - 1.5, fy, 0), grounded=True, tag='opening')
    for dx in (-36, 36): c.asm.extra(B.decal(x + dx, fy + .9, 0, 12, 102, 'hazard_v', 'y', bias=3), 'accent')
    c.asm.extra(B.decal(x, fy + .9, 96, 84, 12, 'hazard_h', 'y', bias=3), 'accent')
    c.asm.add(f'{name}.lamp', sh.box(12, 9, 9, c.m('glow'), emit=True).move(x - 6, fy, 110), grounded=True)
    return x, fy


@motif
def airlock(c, vol, f, depth=44, name='door'):
    """A pressure lock: a small module with a lit lintel and a ramp."""
    x, y, _ = _on(vol, 'y', f, 0); pw, ph = 66, 64
    c.asm.add(f'{name}.lock', sh.box(pw, depth, ph, c.m('base')).move(x - pw / 2, y, 0), grounded=True, tag='base')
    c.asm.add(f'{name}.cap', sh.box(pw + 8, depth + 4, 6, c.m('accent'), wear=False).move(x - pw / 2 - 4, y, ph), tag='accent')
    fy = y + depth
    c.asm.extra(B.decal(x, fy, 4, 30, 46, 'door', 'y', bias=3), 'opening')
    c.asm.add(f'{name}.lamp', sh.quad((x - 22, fy + .7, 52), (44, 0, 0), (0, 0, 7), c.m('glow'), emit=True, bias=3, wear=False), grounded=True)
    return x, fy


@motif
def plain_door(c, vol, f, depth=0, name='door'):
    x, y, _ = _on(vol, 'y', f, 0)
    c.asm.door(name, x, y, 0, 'y', 52, 96)
    c.asm.add(f'{name}.hood', sh.box(72, 22, 6, c.m('metal')).move(x - 36, y, 102), grounded=True, tag='trim')
    return x, y


# ---------------------------------------------------------------- signatures (the silhouette)
@motif
def stepped_tower(c, x, y, z, size, height, tiers=3, name='tower'):
    """A stepped, finned command tower: each tier smaller than the one below, cornices between, strip windows
    between the fins. Stands with its back corner at (x, y). Returns (centre x, centre y, top z, top width)."""
    ws = [size * k for k in (1.0, .71, .44, .30)][:tiers]; hs = [.43, .33, .24, .18][:tiers]; hs = [height * h / sum(hs) for h in hs]
    off = 0.0; zz = z; body, trim = c.m('base'), c.m('trim')
    for n, (tw, th) in enumerate(zip(ws, hs)):
        ox, oy = x + off, y + off
        c.asm.add(f'{name}.tier{n}', sh.box(tw, tw, th, body).move(ox, oy, zz), grounded=(n == 0 and z < 4), tag='signature')
        nf = max(2, 5 - n); fl = []
        for i in range(nf):
            f = (i + .5) * tw / nf
            fl += [sh.box(14, 12, th + 12, trim).move(ox + f - 7, oy + tw, zz), sh.box(12, 14, th + 12, trim).move(ox + tw, oy + f - 7, zz)]
            if i < nf - 1 and th > 60:
                g = (i + 1) * tw / nf; lit_y = (n + i) % 2 == 0; lit_x = (n + i) % 3 == 1
                c.asm.extra(B.decal(ox + g, oy + tw, zz + 18, 18, th - 40, c.m('glow') if lit_y else c.m('glass'), 'y', emit=lit_y, bias=3), 'opening')
                c.asm.extra(B.decal(ox + tw, oy + g, zz + 18, 18, th - 40, c.m('glow') if lit_x else c.m('glass'), 'x', emit=lit_x, bias=3), 'opening')
        c.asm.add(f'{name}.fins{n}', J(fl), grounded=True, tag='trim')
        c.asm.add(f'{name}.cornice{n}', sh.box(tw + 16, tw + 16, 10, trim).move(ox - 8, oy - 8, zz + th), tag='trim')
        zz += th + 10
        if n < tiers - 1: off += (tw - ws[n + 1]) / 2
    return x + off + ws[-1] / 2, y + off + ws[-1] / 2, zz, ws[-1]


@motif
def drum_tower(c, x, y, z, size, height, tiers=3, name='tower'):
    """Stacked drums, each narrower: a control tower. Centre at (x + size/2, y + size/2)."""
    cx, cy = x + size / 2, y + size / 2; zz = z; r = size / 2
    hs = [.5, .3, .2][:tiers]; hs = [height * h / sum(hs) for h in hs]
    for n, th in enumerate(hs):
        c.asm.add(f'{name}.drum{n}', sh.prism(r, th, c.m('body'), n=12, top=c.m('roof')).move(cx, cy, zz), grounded=(n == 0 and z < 4), tag='signature')
        c.asm.add(f'{name}.ring{n}', sh.prism(r + 2, 7, c.m('accent') if n == 0 else c.m('trim'), n=12).move(cx, cy, zz + th - 9), grounded=True, tag='accent' if n == 0 else 'trim')
        if n == tiers - 1:
            c.asm.add(f'{name}.glass', sh.prism(r + 1, th * .4, c.m('glow'), n=12, emit=True).move(cx, cy, zz + th * .3), grounded=True, tag='opening')
        zz += th; r *= .68
    return cx, cy, zz, r * 2


@motif
def stacks(c, x, y, z, height, n=2, r=13, name='stacks'):
    """Tall exhaust stacks with steel bands, stepped in height."""
    top = z
    for k in range(n):
        hh = height * (1 - .16 * k); sx, sy = x + k * (r * 1.7), y + k * (r * 2.3)
        g = sh.lathe([(r, 0), (r, hh), (r + 4, hh + 4), (r + 4, hh + 14), (r, hh + 14)], c.m('stack'), n=10, wear=False).move(sx, sy, z)
        for zz in (hh * .3, hh * .65): g = g + sh.lathe([(r + 1.5, 0), (r + 1.5, 6)], c.m('metal'), n=10, wear=False).move(sx, sy, z + zz)
        c.asm.add(f'{name}.{k}', g, grounded=True, tag='signature'); top = max(top, z + hh + 14)
    return x, y, top, r * 2


@motif
def mast(c, x, y, z, height, name='mast'):
    """A lattice radio mast with cross arms and a lamp."""
    b = max(26, height * .15)
    c.asm.add(f'{name}.lattice', sh.lattice(b, 8, height, max(3, int(height // 45)), c.m('metal'), t=4).move(x, y, z), grounded=True, tag='signature')
    c.asm.extra(sh.strut((x - b * .9, y, z + height * .86), (x + b * .9, y, z + height * .86), 3, c.m('metal')) + sh.strut((x, y - b * .7, z + height * .74), (x, y + b * .7, z + height * .74), 3, c.m('metal')), 'signature')
    c.asm.add(f'{name}.lamp', sh.box(8, 8, 8, c.m('glow'), emit=True).move(x - 4, y - 4, z + height - 6), grounded=True)
    return x, y, z + height, 8


@motif
def searchlight(c, x, y, z, r=30, name='searchlight'):
    """A big searchlight drum on a yoke, facing the viewer."""
    k = r / 30
    c.asm.add(f'{name}.table', sh.lathe([(0, 0), (40 * k, 0), (40 * k, 14 * k), (0, 14 * k)], c.m('metal'), n=14, wear=False).move(x, y, z), tag='signature')
    c.asm.add(f'{name}.yoke', sh.box(60 * k, 10 * k, 46 * k, c.m('metal'), wear=False).move(x - 30 * k, y - 5 * k, z + 14 * k), tag='signature')
    lamp = sh.lathe([(0, 0), (30 * k, 0), (34 * k, 44 * k), (0, 46 * k)], c.m('dark'), n=16, wear=False) + sh.lathe([(0, 0), (28 * k, 0), (0, .5)], c.m('glow'), n=16, emit=True).move(0, 0, 46.2 * k)
    c.asm.add(f'{name}.lamp', lamp.ry(70).rz(45).move(x, y, z + 52 * k), grounded=True, tag='signature')
    return x, y, z + 90 * k, 60 * k


@motif
def water_tower(c, x, y, z, height, r=44, name='tank'):
    c.asm.add(name, B.water_tank(z + 6, r=r, h=height * .55, legs=height * .4, mat=c.m('body2'), leg=c.m('metal')).move(x, y, 0), grounded=True, tag='signature')
    return x, y, z + height, r * 2


@motif
def vault_drum(c, x, y, z, r, height, name='vault'):
    """A round strongroom: thick drum, steel hoops, a shallow cap."""
    c.asm.add(f'{name}.drum', sh.lathe([(r, 0), (r, height), (r + 6, height + 4), (r + 6, height + 12), (r * .8, height + 20), (0, height + 26)], c.m('base'), n=16).move(x, y, z), grounded=z < 4, tag='signature')
    for zz in (height * .25, height * .7):
        c.asm.add(f'{name}.hoop', sh.lathe([(r + 2, 0), (r + 2, 9)], c.m('metal'), n=16, wear=False).move(x, y, z + zz), grounded=True, tag='trim')
    return x, y, z + height + 26, r * 2


@motif
def derrick(c, x, y, z, height, reach=None, name='derrick'):
    """A hoisting derrick: braced mast, a jib leaning out toward the viewer, a hook on a cable."""
    reach = reach or height * .6; m = c.m('metal')
    c.asm.add(f'{name}.mast', sh.lattice(30, 12, height, max(3, int(height // 50)), m, t=4).move(x, y, z), grounded=True, tag='signature')
    tip = (x + reach * .7, y + reach * .7, z + height * .82)
    c.asm.strut(f'{name}.jib', (x, y, z + height * .35), tip, 6, m, tag='signature')
    c.asm.strut(f'{name}.stay', (x, y, z + height), tip, 2.5, c.m('dark'), tag='signature')
    c.asm.strut(f'{name}.cable', tip, (tip[0], tip[1], z + height * .3), 2, c.m('dark'), free=True, tag='signature')
    c.asm.add(f'{name}.hook', sh.box(12, 12, 14, c.m('accent'), wear=False).move(tip[0] - 6, tip[1] - 6, z + height * .3 - 14), grounded=True, tag='accent')
    return x, y, z + height, 12


@motif
def dish(c, x, y, z, r=44, name='dish'):
    c.asm.add(f'{name}.post', sh.prism(r * .2, r * .9, c.m('metal'), n=8).move(x, y, z), tag='signature')
    c.asm.add(f'{name}.bowl', sh.lathe([(0, 0), (r * .65, r * .15), (r, r * .42), (r * .96, r * .46), (r * .6, r * .22), (0, r * .08)], c.m('body'), n=14).ry(55).rz(45).move(x, y, z + r * 1.3), grounded=True, tag='signature')
    return x, y, z + r * 2.3, r


@motif
def vent(c, x, y, z, name='vent'):
    c.asm.add(name, sh.box(26, 26, 18, c.m('metal')).move(x - 13, y - 13, z) + sh.lathe([(0, 0), (10, 0), (10, 22), (16, 26), (0, 30)], c.m('metal'), n=8, wear=False).move(x, y, z + 18), tag='detail')


# ---------------------------------------------------------------- siege works and ground
@motif
def berm(c, x0, y0, x1, y1, name='berm'):
    """A sandbag course from (x0, y0) to (x1, y1); it must run along x or along y."""
    g = B.sandbags_x(min(x0, x1), y0, 0, abs(x1 - x0), c.m('bags')) if abs(x1 - x0) >= abs(y1 - y0) else B.sandbags_y(x0, min(y0, y1), 0, abs(y1 - y0), c.m('bags'))
    c.asm.add(name, g, grounded=True, tag='siege')


@motif
def wire(c, p0, p1, name='wire', post=40):
    """Barbed wire on stakes: pickets and three loose strands."""
    (ax, ay), (bx, by) = p0, p1; L = math.hypot(bx - ax, by - ay); n = max(1, int(L // post))
    pts = [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n + 1)]
    out = [sh.box(6, 6, 36, c.m('dark')).move(px - 3, py - 3, 0) for px, py in pts]
    for zz, sag in ((12, 3), (24, 4), (34, 5)):
        for (qx, qy), (rx, ry) in zip(pts, pts[1:]):
            mx, my = (qx + rx) / 2, (qy + ry) / 2
            out += [sh.strut((qx, qy, zz), (mx, my, zz - sag), 2.4, c.m('dark')), sh.strut((mx, my, zz - sag), (rx, ry, zz), 2.4, c.m('dark'))]
    c.asm.add(name, J(out), grounded=True, tag='siege')


@motif
def hedgehog(c, x, y, s=1.45, rot=0, name='hedgehog'):
    """A steel anti-tank hedgehog: three angles crossed. Reads as an X at any size."""
    L = 56 * s; h = 22 * s; out = []
    for ang in (0, 60, 120):
        a = math.radians(ang + rot); dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2; t = 1 if ang != 60 else -1
        out.append(sh.strut((x - dx, y - dy, h - t * h), (x + dx, y + dy, h + t * h), 4.5 * s, c.m('dark')))
    c.asm.add(name, J(out), grounded=True, tag='siege')


@motif
def beacons(c, pts, name='beacons'):
    """Low marker lights on the ground."""
    c.asm.add(name, J([sh.prism(5, 7, c.m('accent'), n=6, emit=True).move(x, y, 0) for x, y in pts]), grounded=True, tag='accent')


# ---------------------------------------------------------------- yard: what the building does, shown on the ground
YARD = {}


def yard(w, d):
    """Register a yard prop with the ground it needs (w along the edge, d out from it)."""
    def deco(fn):
        YARD[fn.__name__] = (fn, w, d); return fn
    return deco


@yard(96, 44)
def crates(c):
    g = B.crate(44, 32, 30, mat=c.m('wood')) + B.crate(44, 32, 30, mat=c.m('wood'), lid=c.m('metal')).move(48, 4, 0) + B.crate(40, 30, 26, mat=c.m('wood')).rz(14).move(22, 4, 30)
    return g


@yard(70, 40)
def barrels(c):
    return B.barrel(c.m('stack'), hoop=c.m('metal')).move(14, 14, 0) + B.barrel(c.m('accent'), hoop=c.m('metal')).move(42, 16, 0) + B.barrel(c.m('stack'), hoop=c.m('metal')).move(28, 34, 0)


@yard(64, 64)
def tank(c):
    return lib.tank(r=26, h=44, mat=c.m('body2'))


@yard(150, 70)
def logs(c):
    return B.log_pile(0, 36, length=140, r=12, mat=c.m('log'))


@yard(120, 56)
def nest(c):
    """A sandbagged machine-gun position."""
    g = B.sandbags_x(0, 0, 0, 116, c.m('bags')) + B.sandbags_x(8, 0, 40, 100, c.m('bags')).scaled(1, .8, .6).move(0, 4, 16)
    return g + sh.strut((58, -18, 30), (100, 30, 46), 5, c.m('dark')) + sh.box(22, 14, 14, c.m('dark'), wear=False).move(46, -26, 24)


@yard(80, 46)
def fuel(c):
    return (sh.lathe([(15, 0), (15, 60)], c.m('accent'), n=10, wear=False).ry(90).move(6, 22, 24) + sh.box(8, 34, 10, c.m('metal')).move(14, 5, 0) + sh.box(8, 34, 10, c.m('metal')).move(50, 5, 0))


@yard(110, 60)
def cart(c):
    g = sh.box(84, 44, 6, c.m('wood')).move(10, 8, 20) + sh.box(84, 4, 14, c.m('wood')).move(10, 8, 26) + sh.box(84, 4, 14, c.m('wood')).move(10, 48, 26)
    for x in (30, 76):
        for y in (4, 52): g = g + B.wheel(15, 5, c.m('stack')).rz(90).move(x, y, 15)
    return g + sh.strut((94, 30, 22), (118, 30, 8), 4, c.m('wood'))


@yard(90, 50)
def ore(c):
    return sh.scatter(lambda i, rng: sh.rock(20 + 16 * rng.random(), c.m('rock'), seed=int(rng.integers(1e6)), detail=1), area=(10, 8, 80, 42), n=6, seed=3, spacing=16)


@yard(30, 30)
def lamp(c):
    return lib.lamp_post(h=96, mat=c.m('metal'), glass=c.m('glow'))


@yard(140, 26)
def rack(c):
    """A drying or storage rack: posts, rails and hanging cloth."""
    return B.fence([(4, 12), (70, 12), (136, 12)], h=52, mat=c.m('wood')) + B.washing_line((6, 12, 50), (134, 12, 50), n=6, line=c.m('dark'), cloth=(c.m('cloth'), c.m('faction')))


@yard(60, 60)
def pump(c):
    return sh.prism(18, 30, c.m('metal'), n=8).move(30, 30, 0) + sh.strut((30, 30, 30), (30, 30, 64), 6, c.m('metal')) + sh.strut((30, 30, 60), (58, 30, 48), 5, c.m('dark')) + sh.box(30, 20, 12, c.m('base')).move(40, 20, 0)
