"""artkit.library: props any game can use, built from shapes. Every function takes its materials as arguments
with plain defaults, so a style pack decides what they are made of. Recipes call these with "use".

Units: 160 = one tile. Each prop stands on z = 0 with its footprint from (0, 0).
"""
import math
import numpy as np

from .core.geom import Geometry, T, RZ
from . import shapes as sh

REGISTRY = {}


def prop(fn):
    REGISTRY[fn.__name__] = fn
    return fn


@prop
def crate(w=40, d=40, h=34, mat='planks', band='steel', **_):
    g = sh.box(w, d, h, mat)
    for z in (h * .18, h * .78):
        g = g + sh.block(-1, w + 1, -1, d + 1, z, z + 3, band, wear=False)
    return g


@prop
def barrel(r=12, h=34, mat='steel', hoop='rust', **_):
    g = sh.prism(r, h, mat, n=10)
    for z in (h * .22, h * .74):
        g = g + sh.prism(r + 1, 2.5, hoop, n=10).move(0, 0, z)
    return g.move(r, r, 0)


@prop
def sandbags(length=160, rows=3, mat='sandbag', bag=(26, 15, 9), **_):
    out = []
    bl, bd, bh = bag
    for r in range(rows):
        off = (r % 2) * bl / 2
        n = int((length - off) // bl)
        for i in range(n):
            out.append(sh.block(off + i * bl + 1, off + (i + 1) * bl - 1, 0, bd, r * bh, (r + 1) * bh - .5, mat))
    return Geometry.join(out)


@prop
def fence(length=160, h=40, post='planks', rail='planks', posts=4, **_):
    out = []
    for i in range(posts):
        x = i * (length - 6) / (posts - 1)
        out.append(sh.block(x, x + 6, 0, 6, 0, h, post))
    for z in (h * .35, h * .8):
        out.append(sh.block(0, length, 1.5, 4.5, z, z + 5, rail))
    return Geometry.join(out)


@prop
def wire_fence(length=160, h=44, post='steel', wire='wire', posts=3, **_):
    out = [sh.block(i * (length - 4) / (posts - 1), i * (length - 4) / (posts - 1) + 4, 0, 4, 0, h, post) for i in range(posts)]
    out.append(sh.plane(length, h * .9, wire).move(0, 2, 2))
    return Geometry.join(out)


@prop
def lamp_post(h=90, mat='steel', glass='window_lit', **_):
    g = sh.prism(2.5, h, mat, n=6) + sh.block(-2, 16, -2, 2, h - 4, h, mat)
    g = g + sh.block(10, 16, -4, 4, h - 12, h - 4, 'brass') + sh.quad((16.1, -3, h - 11), (0, 6, 0), (0, 0, 6), glass, emit=True)
    return g.move(4, 4, 0)


@prop
def tank(r=30, h=60, mat='steel', legs=True, **_):
    g = sh.lathe([(r, 0), (r, h), (r * .7, h + r * .3), (0, h + r * .38)], mat, n=14)
    if legs:
        g = g.move(0, 0, 14)
        for a in range(0, 360, 90):
            c, s = math.cos(math.radians(a + 45)), math.sin(math.radians(a + 45))
            g = g + sh.strut((c * r * .8, s * r * .8, 0), (c * r * .8, s * r * .8, 16), 5, mat)
    return g.move(r, r, 0)


@prop
def pipe_run(path=((0, 20, 30), (80, 20, 30), (120, 60, 30), (120, 60, 0)), r=4, mat='copper', clamp='steel', **_):
    P = sh.bezier(path, 32)
    g = sh.sweep(P, r, mat)
    for p in np.asarray(path)[1:-1]:
        g = g + sh.block(p[0] - 3, p[0] + 3, p[1] - 3, p[1] + 3, 0, p[2], clamp)
    return g


@prop
def cable(a=(0, 0, 80), b=(160, 0, 80), sag=14, r=1.2, mat='tar', **_):
    return sh.sweep(sh.catenary(a, b, sag), r, mat, thin=1)


@prop
def antenna(h=120, mat='steel', **_):
    g = sh.lattice(16, 6, h, 4, mat, t=3)
    return g + sh.strut((0, 0, h), (0, 0, h + 30), 2, mat)


@prop
def rubble(r=40, n=14, mat='concrete', seed=0, **_):
    rng = np.random.default_rng(seed)
    def piece(i, rng):
        s = 5 + rng.random() * 9
        return sh.rock(s, mat, seed=int(rng.integers(1e6)), detail=1) if i % 3 else sh.block(0, s * 1.6, 0, s, 0, s * .5, mat).ry(rng.random() * 20)
    return sh.scatter(piece, area=(-r, -r, r, r), n=n, seed=seed, spacing=r * .18)


@prop
def boulder(size=60, mat='rock', seed=0, **_):
    return sh.rock(size, mat, seed=seed)


@prop
def conifer(h=110, leaf='foliage', trunk='log', seed=0, **_):
    return sh.conifer(h, leaf, trunk, seed=seed)


@prop
def broadleaf(h=100, leaf='foliage', trunk='log', seed=0, **_):
    return sh.broadleaf(h, leaf, trunk, seed=seed)


@prop
def scaffold(w=160, d=160, h=120, mat='planks', **_):
    """Builders' scaffolding round a footprint, used by the automatic construction stages."""
    out = []
    for x in (-6, w + 2):
        for y in (-6, d + 2):
            out.append(sh.block(x, x + 4, y, y + 4, 0, h, mat))
    lv = max(1, int(h // 40))
    for i in range(1, lv + 1):
        z = min(h, i * 40)
        out += [sh.block(-6, w + 6, -6, -2, z - 3, z, mat), sh.block(-6, w + 6, d + 2, d + 6, z - 3, z, mat),
                sh.block(-6, -2, -6, d + 6, z - 3, z, mat), sh.block(w + 2, w + 6, -6, d + 6, z - 3, z, mat)]
        out.append(sh.strut((-4, d + 4, z - 40), (w + 4, d + 4, z), 2.5, mat))
    return Geometry.join(out)
