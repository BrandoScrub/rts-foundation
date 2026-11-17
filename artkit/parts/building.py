"""artkit.parts.building: walls, roofs, openings and yard furniture, native to artkit (from isokit/parts.py).
Every function returns a Geometry. Materials are arguments with plain defaults; a theme passes its own.

Faces you can see are the +y face (lit, "front") and the +x face (shaded, "right"). side='y' or 'x' picks one.
"""
import math
import numpy as np

from ..core.geom import Geometry
from .. import shapes as sh

SANDBAG = [(0, 0), (56, 0), (56, 18), (50, 30), (38, 40), (18, 40), (6, 30), (0, 18)]
J = Geometry.join


def posts(pts, h, mat='planks', t=12, z=0):
    return J([sh.box(t, t, h, mat).move(x - t / 2, y - t / 2, z) for x, y in pts])


def fence(pts, h=40, mat='planks', z=0):
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        out += [sh.strut((x0, y0, z), (x0, y0, z + h), 8, mat), sh.strut((x0, y0, z + h - 6), (x1, y1, z + h - 6), 5, mat),
                sh.strut((x0, y0, z + h / 2), (x1, y1, z + h / 2), 5, mat)]
    x, y = pts[-1]; out.append(sh.strut((x, y, z), (x, y, z + h), 8, mat))
    return J(out)


def shed_roof(w, d, rise, mat, wall, o=8, thick=5, cap=None):
    """Single slope (high at y=0, low at y=d) with the wall fill underneath; place at the wall top."""
    g = sh.wedge(w, d, rise, wall)
    slope = rise / d
    prof = [(-o, rise + o * slope), (-o, rise + o * slope - thick), (d + o, -o * slope - thick), (d + o, -o * slope)]
    g = g + sh.extrude(prof[::-1], w + 2 * o, mat).move(-o, 0, thick)
    if cap: g = g + sh.box(w + 2 * o, 8, 6, cap).move(-o, -o, rise + o * slope)
    return g


def gable_ends(w, d, rise, wall):
    """Triangular wall fills for a gable roof (ridge along x) over w x d."""
    return sh.wedge(w, d / 2, rise, wall).move(0, d / 2, 0) + sh.wedge(w, d / 2, rise, wall).rz(180).move(w, d / 2, 0)


def parapet(w, d, mat='concrete', rim=10, h=None):
    """Low wall round a flat roof; place at the roof level."""
    h = rim if h is None else h
    return J([sh.box(ww, dd, h, mat).move(x, y, 0) for (x, y), ww, dd in
              [((0, 0), w, rim), ((0, d - rim), w, rim), ((0, 0), rim, d), ((w - rim, 0), rim, d)]])


def decal(x, y, z, w, h, name, side='y', emit=False, bias=2, off=0.6):
    """A picture on a wall: centre x (or y) along the wall, bottom at z, standing off the wall by off."""
    if side == 'y': return sh.quad((x - w / 2, y + off, z), (w, 0, 0), (0, 0, h), name, bias=bias, wear=False, emit=emit)
    return sh.quad((x + off, y + w / 2, z), (0, -w, 0), (0, 0, h), name, bias=bias, wear=False, emit=emit)


def windows(wall, count, z, spacing=160, start=80, lit=False, w=48, h=60):
    """A row of window decals. wall = ('y', length, y_pos) for a +y wall or ('x', length, x_pos) for +x."""
    name = 'window_lit' if lit else 'window'; out = []
    for i in range(count):
        c = start + i * spacing
        if wall[0] == 'y': out.append(sh.quad((c - w / 2, wall[2] + 0.6, z), (w, 0, 0), (0, 0, h), name, bias=2, wear=False))
        else: out.append(sh.quad((wall[2] + 0.6, c + w / 2, z), (0, -w, 0), (0, 0, h), name, bias=2, wear=False))
    return J(out)


def patch(x, y, z, w, h, side='y', mat='steel'):
    """A plate bolted over a shell hole, on a +y (or +x) wall at y (or x)."""
    if side == 'y': return sh.box(w, 3, h, mat, wear=False).move(x - w / 2, y, z)
    return sh.box(3, w, h, mat, wear=False).move(x, y - w / 2, z)


def hedgehog(x, y, z=0, s=1.0, rot=0, mat='steel@black'):
    """Czech hedgehog: three steel angles crossed at the middle. Reads as an X at any size."""
    L = 56 * s; h = 22 * s; out = []
    for ang in (0, 60, 120):
        a = math.radians(ang + rot); dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        tilt = 1 if ang != 60 else -1
        out.append(sh.strut((x - dx, y - dy, z + h - tilt * h), (x + dx, y + dy, z + h + tilt * h), 4.5 * s, mat))
    return J(out)


def wire_run(p0, p1, z=0, post=40, stake='planks@black', wire='steel@black'):
    """Barbed wire on stakes from (x, y) p0 to p1: picket posts and three sagging strands, ground to knee height."""
    (ax, ay), (bx, by) = p0, p1; L = math.hypot(bx - ax, by - ay); n = max(1, int(L // post))
    pts = [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n + 1)]
    out = [sh.box(6, 6, 36, stake).move(px - 3, py - 3, z) for px, py in pts]
    for zz, sag in ((12, 3), (24, 4), (34, 5)):
        for (qx, qy), (rx, ry) in zip(pts, pts[1:]):
            mx, my = (qx + rx) / 2, (qy + ry) / 2
            out.append(sh.strut((qx, qy, z + zz), (mx, my, z + zz - sag), 2.4, wire))
            out.append(sh.strut((mx, my, z + zz - sag), (rx, ry, z + zz), 2.4, wire))
    return J(out)


def banner(cx, face_at, z0, z1, side='y', w=64, cloth='canvas@def', hem='tar@black', rail='steel', emblem='emblem'):
    """A hanging banner on a wall face at face_at: cloth from a rail at z1 down to z0, dark hem, emblem near the top."""
    h = z1 - z0
    if side == 'y':
        return J([sh.quad((cx - w / 2, face_at + 1.4, z0), (w, 0, 0), (0, 0, h), cloth, bias=2),
                  sh.quad((cx - w / 2, face_at + 1.8, z0), (w, 0, 0), (0, 0, 7), hem, bias=3, wear=False),
                  sh.box(w + 14, 6, 6, rail, wear=False).move(cx - w / 2 - 7, face_at, z1 - 2),
                  decal(cx, face_at + 1.2, z1 - w - 10, w - 10, w - 10, emblem, 'y', bias=3, off=0.7)])
    return J([sh.quad((face_at + 1.4, cx + w / 2, z0), (0, -w, 0), (0, 0, h), cloth, bias=2),
              sh.quad((face_at + 1.8, cx + w / 2, z0), (0, -w, 0), (0, 0, 7), hem, bias=3, wear=False),
              sh.box(6, w + 14, 6, rail, wear=False).move(face_at, cx - w / 2 - 7, z1 - 2),
              decal(face_at + 1.2, cx, z1 - w - 10, w - 10, w - 10, emblem, 'x', bias=3, off=0.7)])


def window(x, y, z, side='y', w=48, h=60, lit=False):
    return decal(x, y, z, w, h, 'window_lit' if lit else 'window', side, emit=False)


def door(x, y, z=0, side='y', w=52, h=100):
    return decal(x, y, z, w, h, 'door', side)


def sign(x, y, z, w=70, h=18, mat='planks', side='y'):
    if side == 'y': return sh.box(w, 4, h, mat, wear=False).move(x - w / 2, y + 1, z)
    return sh.box(4, w, h, mat, wear=False).move(x + 1, y - w / 2, z)


def plinth(w, d, mat='concrete', h=12):
    return sh.box(w + 8, d + 8, h, mat).move(-4, -4, 0)


def string_course(w, d, z, mat='concrete'):
    return sh.box(w + 6, 8, 8, mat).move(-3, d - 2, z - 4) + sh.box(8, d + 6, 8, mat).move(w - 2, -3, z - 4)


def chimney(zb, mat='brick', cap='concrete', pot='tar'):
    g = sh.box(36, 36, 90, mat).move(-18, -18, zb - 30) + sh.box(46, 46, 9, cap).move(-23, -23, zb + 60)
    for dx, dy in ((-8, -8), (8, 8)):
        g = g + sh.lathe([(0, 0), (7, 0), (7, 18), (0, 18)], pot, n=8, wear=False).move(dx, dy, zb + 69)
    return g


def pipe(zb, h=130, r=11, mat='tar'):
    return (sh.lathe([(r, 0), (r, h + 20)], mat, n=10, wear=False).move(0, 0, zb - 20)
            + sh.lathe([(0, 0), (r + 7, 0), (r + 7, 7), (0, 7)], mat, n=10, wear=False).move(0, 0, zb + h))


def water_tank(zb, r=48, h=120, legs=40, mat='corrugated', leg='tar'):
    g = J([sh.box(10, 10, legs, leg, wear=False).move(dx - 5, dy - 5, zb - 6) for dx, dy in ((-30, -30), (30, -30), (-30, 30), (30, 30))])
    return g + sh.lathe([(r, 0), (r, h), (r + 2, h + 2), (r + 2, h + 8), (r - 4, h + 12), (0, h + 14)], mat, n=14, wear=False).move(0, 0, zb + legs - 10)


def barrel(mat='tar', r=13, h=36, hoop='steel'):
    g = sh.lathe([(r, 0), (r, h)], mat, n=10, wear=False)
    for z in (6, h - 10): g = g + sh.lathe([(r + 1, 0), (r + 1, 4)], hoop, n=10, wear=False).move(0, 0, z)
    return g


def crate(w=44, d=32, h=30, lid=None, mat='planks'):
    g = sh.box(w, d, h, mat, wear=False)
    return g + sh.box(w, d, 4, lid, wear=False).move(0, 0, h) if lid else g


def log_pile(x, y, length=150, r=14, rows=(4, 3, 2), mat='log'):
    out = []; z = 0
    for n in rows:
        for i in range(n):
            off = (i - (n - 1) / 2) * (2 * r + 2)
            out.append(sh.lathe([(r, 0), (r, length)], mat, n=10, wear=False).ry(90).move(x, y + off, z + r))
        z += 2 * r - 4
    return J(out)


def wheel(r, w, mat='tar'):
    return sh.lathe([(0, 0), (r, 0), (r, w), (0, w)], mat, n=12, wear=False).ry(90)


def washing_line(p0, p1, n=5, line='tar', cloth=('canvas', 'canvas@white')):
    out = [sh.strut(p0, p1, 2, line)]
    for i in range(n):
        f = (i + 0.5) / n
        x, y, z = (p0[k] + (p1[k] - p0[k]) * f for k in range(3))
        out.append(sh.quad((x - 8, y, z - 26), (16, 0, 0), (0, 0, 26), cloth[0] if i % 2 else cloth[1], wear=False))
    return J(out)


def flagpole(x, y, h=200, flag='steel@def', pole='steel', knob='brass'):
    return (sh.lathe([(4, 0), (3, h)], pole, n=8, wear=False).move(x, y, 0) + sh.lathe([(0, 0), (6, 0), (6, 2), (0, 4)], knob, n=8, wear=False).move(x, y, h)
            + sh.quad((x, y, h - 36), (0, -44, 0), (0, 0, 30), flag, wear=False))


def stair(p0, p1, w=18, steps=8, mat='steel'):
    """Straight flight from p0 (bottom) to p1 (top): two stringers and treads."""
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = p1 - p0; side = np.cross(d, (0, 0, 1)); side = side / (np.linalg.norm(side) + 1e-9) * w / 2
    out = [sh.strut(tuple(p0 + side), tuple(p1 + side), 5, mat), sh.strut(tuple(p0 - side), tuple(p1 - side), 5, mat)]
    for k in range(steps):
        p = p0 + d * (k + 0.5) / steps
        out.append(sh.strut(tuple(p - side), tuple(p + side), 4, mat))
    return J(out)


def sandbags_x(x, y, z, length, mat='sandbag'):
    """A sandbag course running along x, inner face at y."""
    return sh.extrude(SANDBAG, length, mat).move(x, y, z)


def sandbags_y(x, y, z, length, mat='sandbag'):
    """A sandbag course running along y from y to y + length."""
    return sh.extrude(SANDBAG, length, mat).rz(90).move(x + 56, y, z)


def frustum(x0, y0, x1, y1, e, h, mat):
    """Sloped skirt (glacis, battered base): rectangle (x0, y0)-(x1, y1) at z 0 up to the same inset by e at z h."""
    b = [(x0, y1, 0), (x1, y1, 0), (x1, y0, 0), (x0, y0, 0)]
    t = [(x0 + e, y1 - e, h), (x1 - e, y1 - e, h), (x1 - e, y0 + e, h), (x0 + e, y0 + e, h)]
    return J([sh.polygon([b[i], b[(i + 1) % 4], t[(i + 1) % 4], t[i]], mat) for i in range(4)])
