"""artkit.assembly: build a structure from named parts, and check that it holds together (from isokit/build.py).

  asm = Assembly()
  asm.add('hall', shapes.box(300, 200, 120, 'brick'), tag='body')
  asm.strut('brace', p0, p1, 5, 'steel')            # both ends must land on something
  asm.door('front', x, y, 0)                         # must have ground or a platform in front
  issues = asm.check()                               # UNSUPPORTED / DANGLING / DOOR TO NOWHERE
  asset = asm.asset('Hall', footprint=(2, 2), states=['build', 'damaged'])

Every part has a name (so stages, turning parts and the critic can find it) and a tag saying what it is for:
base, body, roof, signature, accent, trim, opening, yard, siege, detail. The design critic reads the tags.
Compound parts (walkway, stair_to, awning, ...) place every piece they need, so they cannot be half-built.
"""
import numpy as np

from .core.geom import Geometry
from . import shapes as sh
from .parts import building as B

TAGS = ('ground', 'base', 'body', 'roof', 'signature', 'accent', 'trim', 'opening', 'yard', 'siege', 'detail')


class Assembly:
    def __init__(s, ordered=False):
        """ordered=True: geometry() keeps every piece in the order it was added (parts, struts, doors and loose
        pieces interleaved). Draw order decides which of two coplanar faces shows, so hand-built structures that
        must stay pixel-identical use it; the default groups named parts first, then loose geometry."""
        s.ordered = ordered
        s.seq = []          # ('part', i) / ('loose', i) in the order added
        s.parts = []        # (name, geometry, (lo, hi), grounded, tag)
        s.struts = []       # (name, p0, p1)
        s.free_ends = []
        s.doors = []        # (name, point, normal)
        s.loose = []        # geometry with no name of its own (treads, wire strands)
        s.notes = []        # what the designer (or the composer) decided, in words

    # ---- adding
    def add(s, name, geom, grounded=False, tag='detail'):
        if geom is None or not len(geom): return geom
        lo, hi = geom.bounds()
        s.seq.append(('part', len(s.parts)))
        s.parts.append((name, geom, (lo, hi), grounded, tag))
        return geom

    def strut(s, name, p0, p1, t, mat, free=False, tag='detail'):
        """free=True: p1 is a deliberate free end (a handle, a flag line) and is not checked."""
        s.struts.append((name, np.array(p0, float), np.array(p1, float)))
        if free: s.free_ends.append(len(s.struts) - 1)
        s.extra(sh.strut(p0, p1, t, mat), tag)

    def door(s, name, x, y, z, side='y', w=52, h=100, hatch=False, decal='door'):
        """hatch=True: a loading hatch served by a hoist, so no platform is expected outside it."""
        s.extra(B.decal(x, y, z, w, h, decal, side), 'opening')
        n = (0, 1, 0) if side == 'y' else (1, 0, 0)
        if not hatch: s.doors.append((name, np.array([x, y, z], float), np.array(n, float)))

    def mark_door(s, name, x, y, z, side='y'):
        """Record a door that is drawn some other way (a steel plate, a picture on a raw quad): no geometry is added."""
        s.doors.append((name, np.array([x, y, z], float), np.array((0, 1, 0) if side == 'y' else (1, 0, 0), float)))

    def extra(s, geom, tag='detail'):
        if geom is None or not len(geom): return geom
        s.seq.append(('loose', len(s.loose)))
        s.loose.append((geom, tag))
        return geom

    def shift(s, x=0, y=0, z=0):
        """Move everything already added (parts, struts, doors, anchors) by (x, y, z). Returns the assembly."""
        d = np.array([x, y, z], float)
        s.parts = [(n, g.move(x, y, z), (lo + d, hi + d), gr, t) for n, g, (lo, hi), gr, t in s.parts]
        s.loose = [(g.move(x, y, z), t) for g, t in s.loose]
        s.struts = [(n, a + d, b + d) for n, a, b in s.struts]
        s.doors = [(n, p + d, nn) for n, p, nn in s.doors]
        if getattr(s, 'anchors', None): s.anchors = {k: tuple(np.asarray(v, float) + d) for k, v in s.anchors.items()}
        return s

    def main_door(s):
        """The main door: the first ground-level door, else the first door, else None. ((x, y, z), outward normal)."""
        low = [d for d in s.doors if d[1][2] <= 30]
        d = (low or s.doors or [None])[0]
        return None if d is None else (tuple(float(v) for v in d[1]), tuple(float(v) for v in d[2]))

    def door_anchor(s):
        """The main door's position (x, y, z) in units, or None."""
        d = s.main_door()
        return None if d is None else d[0]

    def note(s, text): s.notes.append(text)

    # ---- result
    def names(s):
        out = {}
        for name, *_ in s.parts: out.setdefault(name, len(out) + 1)
        return out

    def tags(s):
        """part id -> tag (id 0 is loose geometry)."""
        ids = s.names(); out = {0: 'detail'}
        for name, _, _, _, tag in s.parts: out[ids[name]] = tag
        return out

    def geometry(s):
        ids = s.names()
        if s.ordered:
            gs = [s.parts[i][1].as_part(ids[s.parts[i][0]]) if k == 'part' else s.loose[i][0].as_part(0) for k, i in s.seq]
            return Geometry.join(gs)
        gs = [g.as_part(ids[name]) for name, g, _, _, _ in s.parts] + [g.as_part(0) for g, _ in s.loose]
        return Geometry.join(gs)

    @property
    def mesh(s):
        """The whole structure as one Geometry (the name isokit's callers use)."""
        return s.geometry()

    def tagged(s, *tags):
        """All geometry carrying one of these tags."""
        return Geometry.join([g for _, g, _, _, t in s.parts if t in tags] + [g for g, t in s.loose if t in tags])

    def asset(s, name, footprint, pivots=None, states=(), **spec):
        from .recipe import Asset
        d = dict(name=name, footprint=list(footprint), pivots=pivots or {}, states=list(states), **spec)
        md = s.main_door()
        if md and 'door' in d.get('anchors', {}) and 'door' not in d.get('anchor_normals', {}):   # which way the door faces
            d.setdefault('anchor_normals', {})['door'] = list(md[1][:2])
        a = Asset(d, geom=s.geometry(), names=s.names())
        a.assembly = s
        return a

    # ---- validation
    def _touches(s, lo, hi, tol=3):
        for name, _, (plo, phi), _, _ in s.parts:
            if hi[0] <= plo[0] + 1 or lo[0] >= phi[0] - 1 or hi[1] <= plo[1] + 1 or lo[1] >= phi[1] - 1: continue
            if abs(lo[2] - phi[2]) <= tol or (lo[2] >= plo[2] - tol and lo[2] <= phi[2] + tol and hi[2] >= phi[2]): return name
        return None

    def _inside_any(s, p, tol=4):
        for name, _, (lo, hi), _, _ in s.parts:
            if np.all(p >= lo - tol) and np.all(p <= hi + tol): return name
        return None

    def check(s, ground_z=4):
        issues = []
        for name, _, (lo, hi), grounded, _ in s.parts:
            if grounded or lo[2] <= ground_z + 3: continue
            if s._touches(lo, hi) is None:
                held = any(bool(np.all(p >= lo - 4) and np.all(p <= hi + 4)) for _, a, b in s.struts for p in (a, b))
                if not held: issues.append(f'UNSUPPORTED {name}: bottom z={lo[2]:.0f}, nothing beneath')
        for i, (name, a, b) in enumerate(s.struts):
            for p in ((a,) if i in s.free_ends else (a, b)):
                if p[2] <= ground_z + 3 or s._inside_any(p) is not None: continue
                if any(j != i and s._near(p, c, d) for j, (_, c, d) in enumerate(s.struts)): continue
                issues.append(f'DANGLING {name}: end at ({p[0]:.0f},{p[1]:.0f},{p[2]:.0f}) touches nothing')
        for name, p, n in s.doors:
            if p[2] > ground_z + 3 and s._inside_any(p + n * 20 + (0, 0, -2), 6) is None:
                issues.append(f'DOOR TO NOWHERE {name}: nothing to step onto at z={p[2]:.0f}')
        return issues

    @staticmethod
    def _near(p, c, d, tol=6):
        cd = d - c; L2 = float(cd @ cd)
        t = 0.0 if L2 < 1e-9 else float(np.clip((p - c) @ cd / L2, 0, 1))
        return float(np.linalg.norm(p - (c + t * cd))) <= tol


class Volume:
    """A rectangular building volume with attachment helpers. Origin at its min corner."""
    def __init__(s, x, y, z, w, d, h): s.x, s.y, s.z, s.w, s.d, s.h = x, y, z, w, d, h
    def front(s, fx, z): return (s.x + fx * s.w, s.y + s.d, s.z + z)       # +y wall
    def right(s, fy, z): return (s.x + s.w, s.y + fy * s.d, s.z + z)       # +x wall
    def top(s): return s.z + s.h
    def face(s, side, f, z): return s.front(f, z) if side == 'y' else s.right(f, z)
    def span(s, side): return s.w if side == 'y' else s.d
    def box(s, mat, **kw): return sh.box(s.w, s.d, s.h, mat, **kw).move(s.x, s.y, s.z)


# ---------------------------------------------------------------- compound parts
def walkway(asm, vol, side, z, length, start, width=46, name='walkway', mat='steel', door_at=None):
    """Gantry along a wall at height z: slab, brackets and braces to the wall, railing, optional door onto it."""
    def P(a, b, zz):          # a along the wall, b out from it
        return (vol.x + start + a, vol.y + vol.d + b, zz) if side == 'y' else (vol.x + vol.w + b, vol.y + start + a, zz)
    slab = sh.box(length, width, 5, mat) if side == 'y' else sh.box(width, length, 5, mat)
    asm.add(f'{name}.slab', slab.move(*P(0, 0, z)), tag='detail')
    n = max(2, int(length / 70) + 1)
    for i in range(n):
        a = 6 + (length - 12) * i / (n - 1)
        asm.strut(f'{name}.bracket{i}', P(a, 0, z), P(a, width - 4, z), 5, mat)
        asm.strut(f'{name}.brace{i}', P(a, width - 6, z), P(a, 1, z - width * 0.8), 5, mat)
        asm.strut(f'{name}.post{i}', P(a, width - 3, z + 5), P(a, width - 3, z + 44), 3, mat)
    asm.strut(f'{name}.rail', P(6, width - 3, z + 44), P(length - 6, width - 3, z + 44), 3, mat)
    asm.strut(f'{name}.rail2', P(6, width - 3, z + 24), P(length - 6, width - 3, z + 24), 2, mat)
    for e in (6, length - 6):
        asm.strut(f'{name}.endrail', P(e, 2, z + 44), P(e, width - 3, z + 44), 3, mat)
    if door_at is not None:
        p = P(door_at, 0, z + 5); asm.door(f'{name}.door', p[0], p[1], p[2], side, 44, 84)


def stair_to(asm, p_bottom, p_top, name='stair', w=20, mat='steel'):
    """Straight flight; both ends are recorded so the checker confirms they land on something."""
    p0 = np.array(p_bottom, float); p1 = np.array(p_top, float)
    d = p1 - p0; side = np.cross(d, (0, 0, 1)); side = side / (np.linalg.norm(side) + 1e-9) * w / 2
    asm.strut(f'{name}.stringerL', tuple(p0 + side), tuple(p1 + side), 5, mat)
    asm.strut(f'{name}.stringerR', tuple(p0 - side), tuple(p1 - side), 5, mat)
    steps = max(4, int(abs(d[2]) / 14))
    asm.extra(Geometry.join([sh.strut(tuple(p0 + d * (k + 0.5) / steps - side), tuple(p0 + d * (k + 0.5) / steps + side), 4, mat) for k in range(steps)]))
    asm.strut(f'{name}.handrail', tuple(p0 + side + (0, 0, 40)), tuple(p1 + side + (0, 0, 40)), 3, mat)
    asm.strut(f'{name}.hpost0', tuple(p0 + side), tuple(p0 + side + (0, 0, 40)), 3, mat)
    asm.strut(f'{name}.hpost1', tuple(p1 + side), tuple(p1 + side + (0, 0, 40)), 3, mat)


def awning(asm, vol, start, length, z, depth=36, name='awning', mat='canvas', frame='steel', tag='accent'):
    """Sloped canvas on a frame: two posts to the ground, a front bar, canvas between bar and wall."""
    x0, y0 = vol.x + start, vol.y + vol.d; drop = 12
    asm.add(f'{name}.canvas', sh.quad((x0, y0 + depth, z - drop), (length, 0, 0), (0, -depth, drop), mat, wear=False), grounded=True, tag=tag)
    asm.strut(f'{name}.bar', (x0, y0 + depth, z - drop), (x0 + length, y0 + depth, z - drop), 4, frame)
    for e in (x0 + 2, x0 + length - 2):
        asm.strut(f'{name}.post', (e, y0 + depth, 0), (e, y0 + depth, z - drop), 4, frame)


def corner_beams(asm, vol, mat='steel', t=14, name='frame'):
    """Exposed steel frame at the corners and along the top edge."""
    x, y, z, w, d, h = vol.x, vol.y, vol.z, vol.w, vol.d, vol.h
    for cx, cy in ((x - t / 2, y - t / 2), (x + w - t / 2, y - t / 2), (x - t / 2, y + d - t / 2), (x + w - t / 2, y + d - t / 2)):
        asm.add(f'{name}.post', sh.box(t, t, h, mat).move(cx, cy, z), grounded=(z <= 4), tag='trim')
    asm.add(f'{name}.beam_front', sh.box(w + t, t, t, mat).move(x - t / 2, y + d - t / 2, z + h - t), tag='trim')
    asm.add(f'{name}.beam_right', sh.box(t, d + t, t, mat).move(x + w - t / 2, y - t / 2, z + h - t), tag='trim')


def plate_patch(asm, vol, side, f, z, w=50, h=40, name='patch', mat='steel', bolt='brass'):
    """Bolted plate over a shell hole in the wall."""
    p = vol.face(side, f, z)
    if side == 'y':
        g = sh.box(w, 3, h, mat, wear=False).move(p[0] - w / 2, p[1], p[2])
        for dx, dz in ((6, 6), (w - 6, 6), (6, h - 6), (w - 6, h - 6)):
            g = g + sh.lathe([(0, 0), (3, 0), (3, 2), (0, 2)], bolt, n=6, wear=False).rx(-90).move(p[0] - w / 2 + dx, p[1] + 3, p[2] + dz)
    else:
        g = sh.box(3, w, h, mat, wear=False).move(p[0], p[1] - w / 2, p[2])
        for dy, dz in ((6, 6), (w - 6, 6), (6, h - 6), (w - 6, h - 6)):
            g = g + sh.lathe([(0, 0), (3, 0), (3, 2), (0, 2)], bolt, n=6, wear=False).ry(90).move(p[0] + 3, p[1] - w / 2 + dy, p[2] + dz)
    asm.add(name, g, grounded=True)


def shutter_window(asm, vol, side, f, z, name='shutter', w=40, h=50, open_=True, mat='steel@black'):
    """Small window with a blackout shutter hinged open beside it."""
    p = vol.face(side, f, z)
    asm.extra(B.window(p[0], p[1], p[2], side, w, h), 'opening')
    if not open_: return
    if side == 'y': asm.add(name, sh.box(4, 18, h, mat, wear=False).rz(-10).move(p[0] + w / 2 + 2, p[1] + 1, p[2]), grounded=True)
    else: asm.add(name, sh.box(18, 4, h, mat, wear=False).rz(10).move(p[0] + 1, p[1] - w / 2 - 6, p[2]), grounded=True)


def steam_pipes(asm, vol, z, name='steam', mat='steel', stack='tar'):
    """Heating pipe along the front wall at height z, with wall clips, rising to a stack on the roof."""
    a = vol.front(0.05, z); b = vol.front(0.95, z)
    asm.strut(f'{name}.run', (a[0], a[1] + 8, a[2]), (b[0], b[1] + 8, b[2]), 8, mat)
    for f in (0.05, 0.35, 0.65, 0.95):
        p = vol.front(f, z); asm.strut(f'{name}.clip', p, (p[0], p[1] + 8, p[2]), 6, mat)
    asm.strut(f'{name}.riser', (b[0], b[1] + 8, b[2]), (b[0], b[1] + 8, vol.top() + 30), 8, mat)
    asm.strut(f'{name}.top', (b[0], b[1] + 8, vol.top() + 30), (b[0], b[1] - 30, vol.top() + 30), 8, mat)
    asm.add(f'{name}.stack', sh.lathe([(14, 0), (14, 110)], stack, n=10, wear=False).move(b[0], b[1] - 30, vol.top()), grounded=True)
    asm.add(f'{name}.cap', sh.lathe([(0, 0), (22, 0), (22, 7), (0, 7)], stack, n=10, wear=False).move(b[0], b[1] - 30, vol.top() + 110))


def armoured_entrance(asm, vol, f, name='entrance', steps_h=24, mats=None):
    """Steps up to a steel door, sandbag wings either side, a lamp over the door."""
    M = dict(step='concrete', plate='steel', bar='brass', lamp='window_lit', hood='steel', bags='sandbag'); M.update(mats or {})
    x, y, _ = vol.front(f, 0)
    asm.add(f'{name}.steps1', sh.box(110, 36, steps_h / 2, M['step']).move(x - 55, y, 0), grounded=True)
    asm.add(f'{name}.steps2', sh.box(90, 20, steps_h / 2, M['step']).move(x - 45, y, steps_h / 2))
    asm.door(f'{name}.door', x, y, steps_h, 'y', 56, 96)
    asm.add(f'{name}.plate', sh.box(56, 2, 96, M['plate'], wear=False).move(x - 28, y + 0.8, steps_h), grounded=True, tag='opening')
    asm.add(f'{name}.bar', sh.box(44, 2, 6, M['bar'], wear=False).move(x - 22, y + 2.8, steps_h + 50), grounded=True)
    asm.add(f'{name}.lamp', sh.box(12, 10, 10, M['lamp'], emit=True).move(x - 6, y + 1, steps_h + 104), grounded=True)
    asm.add(f'{name}.hood', sh.box(70, 24, 6, M['hood']).move(x - 35, y, steps_h + 116), grounded=True)
    asm.add(f'{name}.bagsL', B.sandbags_x(x - 125, y, 0, 60, M['bags']), grounded=True, tag='siege')
    asm.add(f'{name}.bagsR', B.sandbags_x(x + 65, y, 0, 60, M['bags']), grounded=True, tag='siege')


def lookout(asm, vol, fx, fy, name='lookout', bags='sandbag', metal='steel'):
    """Rooftop sandbagged lookout with a lamp on a post."""
    x, y, z = vol.x + fx * vol.w, vol.y + fy * vol.d, vol.top()
    asm.add(f'{name}.bags', sh.extrude(B.SANDBAG, 90, bags).move(x - 45, y + 10, z), tag='siege')
    asm.add(f'{name}.bags2', sh.extrude(B.SANDBAG, 60, bags).rz(90).move(x + 45, y - 50, z), tag='siege')
    asm.add(f'{name}.post', sh.box(6, 6, 70, metal).move(x - 3, y - 20, z))
    asm.add(f'{name}.lamp', sh.lathe([(0, 0), (10, 0), (12, 16), (0, 18)], metal, n=8, wear=False).rx(-50).move(x, y - 20, z + 70))
