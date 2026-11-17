"""artkit.machine: vehicles, turrets and other machines as parts that say why they exist, what they are mounted on and
how they move, and a check that holds the geometry to it. The machine counterpart of assembly.Assembly's checker for
buildings (UNSUPPORTED / DANGLING / DOOR TO NOWHERE); the method behind it is DESIGN_METHOD.md.

  m = Machine('m4')
  m.add('hull', hull_geom, why='crew and engine compartments')                                  # the root: on=None
  m.add('wheel_l1', wheel_geom, why='carries the weight onto the track', on='bracket_l1',
        turns=((x, y, z), (0, 1, 0)))                                                             # an axle across
  m.add('turret', turret_geom, why='...', on='hull', turns=((x, y, z), (0, 0, 1)))              # a ring: it can be posed
  m.belt('track_l', circles, y0, y1, thickness, why='...', on='hull', wraps=['sprocket_l', 'wheel_l1', ...])
  issues = m.check()
  geometry = m.geometry(pose={'turret': 30})

What check() reports (each a line starting with its kind):
  NO REASON       a part with no `why`
  NO MOUNT        `on` names a part that does not exist, or more than one part has no mount (one root only)
  FLOATING        a part does not touch what it says it is mounted on (or a part in `contact`)
  CLASH           two parts that are not mounted on each other pass through each other (convex parts are tested as
                  solids); a part that turns about a vertical axis is tested at eight headings
  OFF AXIS        a part that turns is not centred on its axis
  TRACK OFF WHEEL a belt does not ride on a wheel it wraps (too far from it, or the wheel is inside the band)
  TRACK BROKEN    a belt's path is not closed or jumps
  GROUND          nothing touches the ground, or something is below it
  TOO SMALL       a part narrower than 3 pixels at the export scale (it will not be seen; cut it or make it bigger),
                  unless added with small_ok=True
"""
import math
import numpy as np
from scipy.spatial import ConvexHull, cKDTree

from . import shapes as sh
from .core.geom import Geometry, RZ
from .rig import Rig, Clip


def _rot(axis, deg):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K
    M = np.eye(4); M[:3, :3] = R; return M


def samples(g, step=4.0):
    """Points over a geometry's surface, about `step` units apart (corners, and a grid inside larger triangles)."""
    P = np.asarray(g.P, float)
    if not len(P): return np.zeros((0, 3))
    out = [P.reshape(-1, 3)]
    L = np.linalg.norm(P[:, [1, 2, 0]] - P, axis=2).max(1)
    for k in np.unique(np.clip(np.ceil(L / step), 1, 40).astype(int)):
        if k < 2: continue
        tri = P[np.ceil(L / step).clip(1, 40).astype(int) == k]
        ij = [(i, j) for i in range(k + 1) for j in range(k + 1 - i)]
        w = np.array([(i / k, j / k, 1 - (i + j) / k) for i, j in ij])
        out.append(np.einsum('wk,tkd->twd', w, tri).reshape(-1, 3))
    return np.concatenate(out)


class Part:
    __slots__ = ('name', 'geom', 'why', 'on', 'turns', 'contact', 'convex', 'small_ok', 'belt')

    def __init__(s, name, geom, why, on, turns, contact, convex, small_ok, belt=None):
        s.name, s.geom, s.why, s.on, s.turns = name, geom, why, on, turns
        s.contact, s.convex, s.small_ok, s.belt = tuple(contact), convex, small_ok, belt


class Machine:
    def __init__(s, name, ground=0.0, scale=0.4):
        """ground: the height things stand on (None for things that fly). scale: export pixels per unit (TOO SMALL)."""
        s.name, s.ground, s.scale = name, ground, scale
        s.parts = {}

    def add(s, name, geom, why='', on=None, turns=None, contact=(), convex=True, small_ok=False):
        """A part. on: the part it is mounted on (None only for the root). turns: (point, axis) if it rotates on that
        joint; a vertical axis makes it posable (pose={name: degrees}) and it carries every part mounted on it.
        contact: other parts it bears on besides its mount (a wheel on its track). convex: test it as a solid in
        CLASH (False for shapes with hollows: a track, a frame)."""
        if name in s.parts: raise ValueError(f'two parts named {name!r}')
        s.parts[name] = Part(name, geom, why, on, turns, contact, convex, small_ok)
        return geom

    def belt(s, name, circles, y0, y1, thickness, mat, why='', on=None, wraps=(), teeth=None, convex=False):
        """A track or belt round circles [(x, z, r to the band's inner face)] (shapes.belt_path order), across y0..y1.
        wraps: the parts (wheels) it rides on, one per circle, in the same order."""
        c = [(x, z, r + thickness / 2) for x, z, r in circles]
        path, wrap = sh.belt_path(c)
        g = sh.belt(path, y0, y1, thickness, mat, teeth=teeth)
        s.parts[name] = Part(name, g, why, on, None, tuple(w for w in wraps if w), convex, False,
                             belt=dict(path=path, wrap=wrap, circles=c, wraps=list(wraps), y=(y0, y1), t=thickness,
                                       mat=mat, teeth=teeth))
        return g

    # ---------------------------------------------------------------- structure
    def children(s, name):
        return [p.name for p in s.parts.values() if p.on == name]

    def subtree(s, name):
        out, todo = [], [name]
        while todo:
            n = todo.pop(); out.append(n); todo += s.children(n)
        return out

    def chain(s, name):
        out = []
        while name is not None and name in s.parts: out.append(name); name = s.parts[name].on
        return out

    def related(s, a, b):
        """Mounted one on the other (directly), in contact by declaration, or both on the same mount and touching
        is their job (a hub in its wheel is mounted on the wheel)."""
        A, B = s.parts[a], s.parts[b]
        return A.on == b or B.on == a or b in A.contact or a in B.contact

    # ---------------------------------------------------------------- poses
    def posed(s, pose=None):
        """{name: geometry} with turning parts (vertical axes) turned by pose={name: degrees}, carrying their subtree."""
        G = {n: p.geom for n, p in s.parts.items()}
        for n, deg in (pose or {}).items():
            pt, ax = s.parts[n].turns
            M = _rot(ax, deg)
            for m in s.subtree(n): G[m] = G[m].about(pt, M)
        return G

    def geometry(s, pose=None):
        return Geometry.join(list(s.posed(pose).values()))

    def rig(s, origin, upper=(), muzzle=None, recoil=(), headings=16, export_scale=0.4, draw_scale=1.0, name=None):
        """This machine as an artkit.rig.Rig, so Exporter.rig animates and exports it like any unit (see MachineRig)."""
        return MachineRig(s, origin, upper=upper, muzzle=muzzle, recoil=recoil, headings=headings, export_scale=export_scale,
                          draw_scale=draw_scale, name=name)

    # ---------------------------------------------------------------- the check
    def check(s, tol=1.5):
        issues = []
        P = s.parts
        roots = [n for n, p in P.items() if p.on is None]
        if len(roots) != 1: issues.append(f'NO MOUNT {s.name}: {len(roots)} parts have no mount ({roots}); one root only')
        for n, p in P.items():
            if not (p.why or '').strip(): issues.append(f'NO REASON {n}: say why it is there, or cut it')
            if p.on is not None and p.on not in P: issues.append(f'NO MOUNT {n}: mounted on {p.on!r}, which does not exist')
        S = {n: samples(p.geom) for n, p in P.items()}
        T = {n: cKDTree(v) for n, v in S.items() if len(v)}
        hull = {}
        def inside(pts, n):                       # depth of each point inside part n's convex hull
            if n not in hull: hull[n] = ConvexHull(S[n]).equations
            eq = hull[n]; return -(pts @ eq[:, :3].T + eq[:, 3]).max(1)
        def gap(a, b):
            d, _ = T[b].query(S[a], k=1); return float(d.min())
        def touches(a, b):
            if gap(a, b) <= tol: return True
            return (P[b].convex and inside(S[a], b).max() > 0) or (P[a].convex and inside(S[b], a).max() > 0)
        # FLOATING
        for n, p in P.items():
            for m in ([p.on] if p.on in P else []) + [c for c in p.contact if c in P and not P[n].belt]:
                if not touches(n, m): issues.append(f'FLOATING {n}: does not touch {m} (gap {gap(n, m):.1f} units)')
        # OFF AXIS
        for n, p in P.items():
            if not p.turns: continue
            pt, ax = np.asarray(p.turns[0], float), np.asarray(p.turns[1], float); ax = ax / np.linalg.norm(ax)
            v = S[n] - pt; perp = v - np.outer(v @ ax, ax)
            lo, hi = perp.min(0), perp.max(0); off = float(np.linalg.norm((lo + hi) / 2))
            if off > max(tol, 0.03 * float(np.linalg.norm(hi - lo))):
                issues.append(f'OFF AXIS {n}: its middle is {off:.1f} units off the axis it turns on')
        # TRACK BROKEN / TRACK OFF WHEEL
        for n, p in P.items():
            if not p.belt: continue
            b = p.belt; path = np.asarray(b['path'])
            if np.linalg.norm(path[0] - path[-1]) > 1e-6: issues.append(f'TRACK BROKEN {n}: its path is not closed')
            for w, (x, z, r), wr in zip(b['wraps'], b['circles'], b['wrap']):
                if not w: continue
                if wr is None: issues.append(f'TRACK OFF WHEEL {n}: does not ride on {w} (it is below the run or inside the loop)')
                elif w in P and gap(w, n) > tol: issues.append(f'TRACK OFF WHEEL {n}: {gap(w, n):.1f} units clear of {w}')
        # CLASH (and turning parts at eight headings)
        names = list(P)
        lo = {n: S[n].min(0) for n in names}; hi = {n: S[n].max(0) for n in names}
        def clash_pairs(G, A, B):
            out = []
            for a in A:
                pa = samples(G[a]) if G[a] is not P[a].geom else S[a]
                la, ha = pa.min(0), pa.max(0)
                for b in B:
                    if a == b or s.related(a, b) or not P[b].convex: continue
                    if np.any(la > hi[b] + tol) or np.any(ha < lo[b] - tol): continue
                    d = inside(pa, b).max()
                    if d > tol: out.append((a, b, d))
            return out
        seen = set()
        for a, b, d in clash_pairs({n: P[n].geom for n in names}, names, names):
            key = tuple(sorted((a, b)))
            if key not in seen: seen.add(key); issues.append(f'CLASH {a} goes {d:.1f} units into {b}')
        for n, p in P.items():
            if not p.turns or abs(np.asarray(p.turns[1], float)[2]) < 0.99: continue
            sub = set(s.subtree(n)); rest = [m for m in names if m not in sub]
            for h in range(45, 360, 45):
                G = s.posed({n: h})
                for a, b, d in clash_pairs(G, sorted(sub), rest):
                    key = tuple(sorted((a, b))) + (n,)
                    if key not in seen: seen.add(key); issues.append(f'CLASH {a} goes {d:.1f} units into {b} with {n} turned {h}')
        # GROUND
        if s.ground is not None:
            zmin = min(float(v[:, 2].min()) for v in S.values() if len(v))
            if zmin < s.ground - tol: issues.append(f'GROUND {s.name}: something reaches {s.ground - zmin:.1f} units below the ground')
            if zmin > s.ground + tol: issues.append(f'GROUND {s.name}: nothing touches the ground (lowest point {zmin - s.ground:.1f} above)')
        # TOO SMALL
        for n, p in P.items():
            if p.small_ok or not len(S[n]): continue
            ext = np.sort(S[n].max(0) - S[n].min(0))
            if ext[1] * s.scale < 3.0:
                issues.append(f'TOO SMALL {n}: {ext[1] * s.scale:.1f} px across at export scale (under 3): cut it, or make it bigger')
        return issues


class MachineRig(Rig):
    """A checked Machine driven as a Rig: Exporter.rig exports it, the runtime draws it, nothing new on either side.

      rig = machine.rig(origin=ground_point_under_its_middle, upper=['turret'], muzzle=gun_tip, recoil=['gun', 'muzzle'],
                        headings=8)
      clips = [rig.idle(), rig.move(), rig.fire()]
      Exporter(style, out).rig('tank', rig, clips)

    origin: the model point that becomes the unit's ground anchor (the middle of its footprint, on the ground); the
    machine is modelled facing +x. upper: parts whose subtrees form the top layer (a turret: it aims on its own; the
    runtime stands any top frame on any bottom frame at the socket, the first upper part's joint point). Belts
    (tracks) run: in `move` their teeth travel back along the band by the distance driven, so links on the ground
    stay still and the track never slides. recoil: the parts that slide back along the gun (the machine's +x) in `fire`. Pose channels: 'root' (x, y, z, yaw, pitch, roll) for bob, '<upper part>'
    yaw in degrees (relative to the hull), '#' distance driven (units), '@recoil' units the gun slides back."""

    def __init__(s, machine, origin, upper=(), muzzle=None, recoil=(), headings=16, export_scale=0.4, draw_scale=1.0, name=None):
        Rig.__init__(s, name or machine.name, upper=tuple(upper), draw_scale=draw_scale, export_scale=export_scale,
                     headings=headings)
        s.m = machine; s.origin = np.asarray(origin, float)
        s.top = set()
        for u in upper: s.top |= set(machine.subtree(u))
        s.turner = upper[0] if upper else None
        s.ring = np.asarray(machine.parts[s.turner].turns[0], float) if s.turner and machine.parts[s.turner].turns else s.origin
        s.muzzle_at = None if muzzle is None else np.asarray(muzzle, float)
        s.belts = [n for n, p in machine.parts.items() if p.belt and p.belt.get('teeth')]
        s.recoilers = [r for r in recoil if r in machine.parts]   # parts that slide back along the gun when it fires
        s._cache = {}

    def pose(s, **ch):
        p = {'root': (0, 0, 0, 0, 0, 0)}; p.update(ch); return p

    def _world(s, pts, aim, heading, bob):
        """Model points -> rig frame: the top layer turned by aim about the ring, all moved to the origin, bobbed,
        turned to the heading."""
        P = np.asarray(pts, float).reshape(-1, 3)
        if aim:
            P = (P - s.ring) @ RZ(aim)[:3, :3].T + s.ring
        P = P - s.origin + np.array([0, 0, bob])
        return P @ RZ(heading)[:3, :3].T

    def build(s, pose, heading=0.0, layer=None):
        d = float(pose.get('#', 0.0)); aim = float(pose.get(s.turner, 0.0)) if s.turner else 0.0
        bob = float(pose.get('root', (0, 0, 0))[2]); rec = float(pose.get('@recoil', 0.0))
        out = []
        for n, p in s.m.parts.items():
            top = n in s.top
            if layer and (('U' if top else 'L') != layer): continue
            g = p.geom
            if n in s.belts and d:
                b = p.belt; key = (n, round(d % b['teeth'][0], 4))
                if key not in s._cache:
                    s._cache[key] = sh.belt(b['path'], b['y'][0], b['y'][1], b['t'], b['mat'], teeth=b['teeth'], phase=-d)
                g = s._cache[key]
            if rec and n in s.recoilers:
                g = g.move(-rec, 0, 0)                   # along the gun, before the turret turns it
            M = RZ(heading) @ _T(-s.origin + np.array([0, 0, bob]))
            if top and aim: M = M @ _T(s.ring) @ RZ(aim) @ _T(-s.ring)
            out.append(g.at(M))
        mk = {'socket': s._world([s.ring], 0, heading, bob)[0]}
        mk['muzzle'] = s._world([s.muzzle_at], aim, heading, bob)[0] if s.muzzle_at is not None else mk['socket']
        return Geometry.join(out), mk

    def shadow_geometry(s, pose, heading=0.0, reach=1.3):
        """What casts the unit's shadow layer (Exporter.rig asks for it): the bottom layer, and only those parts of the
        top layer that stay within `reach` times the turning part's own radius of its axis (the turret body, hatches,
        a bustle). The top layer turns on its own in the game, so a part reaching far out (a gun) would cast its
        shadow the wrong way at every aim but one; leaving it out keeps the shadow right at every aim."""
        full, _ = s.build(dict(pose, **{s.turner: 0.0}) if s.turner else pose, heading, None)
        if not s.top: return full
        if not hasattr(s, '_round'):
            ax = np.array([0, 0, 1.0])
            def radius(n):
                v = s.m.parts[n].geom.P.reshape(-1, 3) - s.ring; v -= np.outer(v @ ax, ax); return float(np.linalg.norm(v, axis=1).max())
            lim = radius(s.turner) * reach
            s._round = {n for n in s.top if radius(n) <= lim}
        keep = [n for n in s.m.parts if n not in s.top or n in s._round]
        sub = Machine.__new__(Machine); sub.__dict__.update(s.m.__dict__); sub.parts = {n: s.m.parts[n] for n in keep}
        saved = s.m; s.m = sub
        try: g, _ = s.build(dict(pose, **{s.turner: 0.0}), heading, None)
        finally: s.m = saved
        return g

    def canvas(s):
        if s._canvas: return s._canvas
        # every heading: a point R from the middle reaches R * sqrt(2) across the screen and R / sqrt(2) up or down
        # (2:1 isometric); a cast shadow (artkit.shadow, length up to 1 per unit of height) reaches further out
        P = np.concatenate([p.geom.P.reshape(-1, 3) for p in s.m.parts.values()]) - s.origin
        R = float(np.linalg.norm(P[:, :2], axis=1).max()); Z = float(P[:, 2].max())
        Rs = R + Z                                       # room for the shadow
        return (Rs * 1.42 + 12, Z + R * 0.71 + 12, Rs * 0.71 + 12)

    def move(s, frames=6, fps=12, bob=0.4, name='move'):
        """Driving: one cycle = one track pitch (the picture repeats after it), so the runtime picks frames by
        distance and the track never slides. Without tracks, a 40-unit cycle."""
        stride = max([s.m.parts[b].belt['teeth'][0] for b in s.belts] or [40.0])
        out = [s.pose(root=(0, 0, bob * math.sin(2 * math.pi * i / frames), 0, 0, 0), **{'#': stride * i / frames})
               for i in range(frames)]
        return Clip(name, out, fps, stride=stride)

    def fire(s, frames=6, fps=14, recoil=8.0, name='fire'):
        """Top layer only: the gun (the parts at the muzzle) slides back and returns; a shot leaves on frame 0."""
        out = []
        for i in range(frames):
            k = max(0.0, 1 - i / (frames * .6))
            out.append(s.pose(**{'@recoil': recoil * k, 'flash': 1.0 if i == 0 else 0.0}))
        return Clip(name, out, fps, loop=False, events={'fire': 0}, layers=('U',) if s.layered else None)


def _T(v):
    M = np.eye(4); M[:3, 3] = v; return M
