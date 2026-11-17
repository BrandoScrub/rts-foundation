"""artkit.rig: one jointed body for anything that moves: legs (any number), wheels, tracks, rotors, turrets.

A Rig is a tree of joints. Parts (Geometry) hang on joints. A pose sets joint rotations and where feet stand;
legs are solved by two-bone IK so planted feet stay planted. Anything on a joint listed in `upper` is the top
layer (turret, torso, hull that aims), the rest the bottom layer (legs, chassis, wheels): the game can stand any
top frame on any bottom frame, so a tank drives one way and shoots another. Same export format as unitkit, so the
same game runtime draws both.

  r = Rig('rover')
  r.joint('body', 'root', at=(0, 0, 30)); r.attach('body', hull)
  r.wheel('fl', 'body', at=(40, 30, -10), radius=16, geom=wheel_geom)
  r.joint('turret', 'body', at=(0, 0, 20), upper=True); r.attach('turret', gun)
  clips = [r.idle(), r.roll(frames=8), r.fire('turret', recoil=('gun', 6))]

Pose channels: 'root' (x, y, z, yaw, pitch, roll); '<joint>' (yaw, pitch, roll) local to its parent;
'foot_<leg>' (x, y, z) in the root frame; '<joint>@x' etc. for a slide along local axes (recoil, pistons).
"""
import math
import numpy as np

from .core.geom import Geometry, T, RX, RY, RZ, R3, aim, ik2, xf
from . import shapes as sh


class Clip:
    def __init__(s, name, poses, fps=10, loop=True, stride=None, events=None, layers=None, drag_ok=False):
        s.name, s._poses, s.fps, s.loop, s.stride = name, poses, fps, loop, stride
        s.events = events or {}; s.layers = layers; s.drag_ok = drag_ok

    @property
    def frames(s): return len(s._poses)
    def poses(s): return s._poses


class Rig:
    def __init__(s, name, upper=(), draw_scale=1.0, canvas=None, export_scale=0.4, headings=16):
        s.name = name
        s.joints = {'root': (None, np.zeros(3))}
        s.order = ['root']
        s.parts = []                          # (joint, geometry, part id)
        s.legs = {}                           # name -> dict
        s.wheels = {}; s.tracks = {}; s.rotors = {}
        s.upper = set(upper)
        s.points = {}                         # marks: name -> (joint, local point), reported per frame
        s.muzzles = {}
        s.draw_scale = draw_scale; s.export_scale = export_scale; s.headings = headings
        s._canvas = canvas

    @property
    def layered(s): return bool(s.upper)

    # ---- building
    def joint(s, name, parent='root', at=(0, 0, 0), upper=False):
        s.joints[name] = (parent, np.asarray(at, float)); s.order.append(name)
        if upper or parent in s.upper: s.upper.add(name)
        return s

    def attach(s, joint, geom, name=None):
        s.parts.append((joint, geom.as_part(len(s.parts) + 1), name or joint)); return s

    def mark(s, name, joint, local=(0, 0, 0)):
        s.points[name] = (joint, np.asarray(local, float)); return s

    def muzzle(s, joint, local, name='muzzle'):
        s.muzzles[name] = (joint, np.asarray(local, float)); return s

    def leg(s, name, parent, hip, home, l1, l2, knee=(1, 0, .3), thigh=None, shin=None, foot=None, r=4.0, mat='steel'):
        """A two-bone leg from `hip` (in the parent frame) to a foot standing at `home` (x, y on the ground, root frame).
        knee: which way the knee points, in the root frame (forward for a bird or human, outward and up for a spider).
        thigh, shin, foot: geometry modelled along -z from the joint (as unitkit limbs); default round bars."""
        s.legs[name] = dict(parent=parent, hip=np.asarray(hip, float), home=np.asarray(home, float), l1=l1, l2=l2, knee=np.asarray(knee, float))
        s.joints[name + '_thigh'] = (None, None); s.joints[name + '_shin'] = (None, None); s.joints[name + '_foot'] = (None, None)
        s.attach(name + '_thigh', thigh if thigh is not None else sh.cyl((0, 0, 0), (0, 0, -l1), r, mat, r * .85))
        s.attach(name + '_shin', shin if shin is not None else sh.cyl((0, 0, 0), (0, 0, -l2), r * .85, mat, r * .6))
        if foot is not None: s.attach(name + '_foot', foot)
        return s

    def wheel(s, name, parent, at, radius, geom=None, mat='rubber', hub='steel', width=10, spokes=5):
        """A wheel spinning about its local y axis. Ground covered per turn = 2 pi radius."""
        s.joint(name, parent, at)
        if geom is None:
            tyre = sh.blob_lathe([(radius * .62, -width / 2), (radius, -width / 2 + 1.5), (radius, width / 2 - 1.5), (radius * .62, width / 2)], mat, seg=14).rx(90)
            disc = sh.prism(radius * .62, width * .7, hub, n=spokes * 2).rx(90).move(0, width * .35, 0)
            nub = Geometry.join([sh.block(radius * .3, radius * .58, -width * .4, width * .4, -2, 2, hub).ry(i * 360 / spokes) for i in range(spokes)])
            geom = tyre + disc + nub
        s.attach(name, geom); s.wheels[name] = dict(r=radius, sym=360.0 / spokes); return s

    def track(s, name, parent, a, b, r, width=18, pads=None, mat='rubber', wheel_mat='steel', pitch=9.0):
        """A tank track round two sprockets at a and b (x, z in the parent frame, y offset in a[1])."""
        a = np.asarray(a, float); b = np.asarray(b, float)
        s.joint(name, parent, (0, 0, 0))
        s.tracks[name] = dict(a=a, b=b, r=r, w=width, pitch=pitch, mat=mat)
        for k, c in (('a', a), ('b', b)):
            s.wheel(f'{name}_{k}', parent, c, r * .9, mat=wheel_mat, hub=wheel_mat, width=width * .8, spokes=6)
        return s

    def rotor(s, name, parent, at, radius, blades=2, mat='steel', hub='steel'):
        s.joint(name, parent, at)
        g = sh.prism(4, 5, hub, n=8)
        for i in range(blades):
            g = g + sh.block(0, radius, -3, 3, 3, 4.5, mat, wear=False).rz(i * 360 / blades)
        s.attach(name, g); s.rotors[name] = dict(sym=360.0 / blades); return s

    # ---- poses
    def pose(s, **ch):
        p = {'root': (0, 0, 0, 0, 0, 0)}
        for n, L in s.legs.items(): p['foot_' + n] = (L['home'][0], L['home'][1], 0.0)
        p.update(ch); return p

    def solve(s, p):
        M = {}
        r = list(p.get('root', (0, 0, 0, 0, 0, 0))) + [0] * 6
        M['root'] = T(r[0], r[1], r[2]) @ R3(r[3], r[4], r[5])
        for j in s.order[1:]:
            parent, at = s.joints[j]
            if parent is None: continue
            rot = p.get(j, (0, 0, 0))
            slide = [p.get(j + '@' + ax, 0.0) for ax in 'xyz']
            M[j] = M[parent] @ T(*at) @ R3(*rot) @ T(*slide)
        for n, L in s.legs.items():
            hip = xf(M[L['parent']], L['hip'])
            f = np.asarray(p['foot_' + n], float)
            foot = xf(M['root'], f) if len(f) == 3 else xf(M['root'], (*f, 0))
            ankle = foot.copy()
            fwd = M['root'][:3, :3] @ np.array([1.0, 0, 0])
            pole = M['root'][:3, :3] @ L['knee']
            knee, end = ik2(hip, ankle, L['l1'], L['l2'], pole)
            M[n + '_thigh'] = aim(hip, knee, fwd)
            M[n + '_shin'] = aim(knee, end, fwd)
            Mf = np.eye(4); Mf[:3, :3] = M['root'][:3, :3]; Mf[:3, 3] = end
            M[n + '_foot'] = Mf
            M['_miss_' + n] = float(np.linalg.norm(end - ankle))
        return M

    def layer_of(s, joint): return 'U' if joint in s.upper else 'L'

    def build(s, pose, heading=0.0, layer=None):
        M = s.solve(pose); H = RZ(heading); out = []
        for j, g, _ in s.parts:
            if layer and s.layer_of(j) != layer: continue
            out.append(g.at(H @ M[j]))
        for name, t in s.tracks.items():
            if layer and s.layer_of(name) != layer: continue
            out.append(s._track_geom(name, t, pose.get(name + '#', 0.0)).at(H @ M[name]))
        mk = {}
        for n, (j, loc) in list(s.muzzles.items()) + list(s.points.items()): mk[n] = xf(H @ M[j], loc)
        up = [j for j in s.upper if s.joints[j][0] is not None and s.joints[j][0] not in s.upper]
        mk['socket'] = xf(H @ M[up[0]], (0, 0, 0)) if up else xf(H @ M['root'], (0, 0, 0))
        for n in s.legs: mk['foot_' + n] = xf(H @ M[n + '_foot'], (0, 0, 0))
        mk.setdefault('muzzle', mk['socket'])
        return Geometry.join(out), mk

    def _track_geom(s, name, t, dist):
        """Pads laid round the loop, shifted along it by dist, so the belt runs."""
        a, b, r, w, pitch = t['a'], t['b'], t['r'], t['w'], t['pitch']
        (ax, ay, az), (bx, by, bz) = a, b
        L1 = abs(bx - ax); circ = math.pi * r
        total = 2 * L1 + 2 * circ
        out = []
        n = int(total // pitch)
        for i in range(n):
            u = (i * total / n + dist) % total
            if u < L1: x, z, ang = bx - u, az - r, 0.0                     # bottom run, front to back
            elif u < L1 + circ:
                th = (u - L1) / r; x, z, ang = ax - r * math.sin(th), az - r * math.cos(th), math.degrees(th)
            elif u < 2 * L1 + circ: x, z, ang = ax + (u - L1 - circ), az + r, 180.0
            else:
                th = (u - 2 * L1 - circ) / r; x, z, ang = bx + r * math.sin(th), az + r * math.cos(th), 180 + math.degrees(th)
            pad = sh.block(-pitch * .42, pitch * .42, -w / 2, w / 2, -2.4, 1.2, t['mat'], wear=False)
            out.append(pad.ry(-ang).move(x, ay, z))
        return Geometry.join(out)

    def describe(s):
        return [(n, j, len(g)) for j, g, n in s.parts]

    def canvas(s):
        """Fixed frame box (half width, up, down) big enough for every pose."""
        if s._canvas: return s._canvas
        g, _ = s.build(s.pose(), 0)
        lo, hi = g.bounds(); R = max(np.abs(lo[:2]).max(), np.abs(hi[:2]).max()) * 1.25 + 20
        return (R * 1.45, hi[2] + R * .8 + 20, R * .8 + 20)

    # ---- clips
    def idle(s, frames=8, fps=6, bob=1.5, joint=None):
        out = []
        for i in range(frames):
            ph = 2 * math.pi * i / frames
            p = s.pose(root=(0, 0, bob * math.sin(ph), 0, 0, 0))
            for n in s.rotors: p[n] = (s.rotors[n]['sym'] * i / frames, 0, 0)
            out.append(p)
        return Clip('idle', out, fps)

    def walk(s, stride, frames=12, duty=0.6, lift=10.0, phases=None, fps=10, bob=2.0, name='walk'):
        """Legs step so a planted foot never slides: in stance it moves back by stride*duty while the body covers
        stride per cycle. phases: leg -> 0..1 offset (default: diagonal pairs for 4 legs, alternating tripods for 6)."""
        legs = list(s.legs)
        if phases is None:
            if len(legs) == 4: phases = {legs[0]: 0, legs[3]: 0, legs[1]: .5, legs[2]: .5}
            elif len(legs) == 6: phases = {l: (0 if i in (0, 3, 4) else .5) for i, l in enumerate(legs)}
            else: phases = {l: i / max(len(legs), 1) for i, l in enumerate(legs)}
        out = []
        for i in range(frames):
            t = i / frames; p = s.pose()
            for n, L in s.legs.items():
                ph = (t + phases.get(n, 0)) % 1.0
                hx, hy = L['home'][:2]
                if ph < duty:
                    u = ph / duty; x = hx + stride * duty * (.5 - u); z = 0.0
                else:
                    u = (ph - duty) / (1 - duty); x = hx + stride * duty * (u - .5)
                    z = lift * math.sin(math.pi * u)
                p['foot_' + n] = (x, hy, z)
            p['root'] = (0, 0, -bob * abs(math.cos(2 * math.pi * t * (2 if len(legs) % 2 == 0 else 1))), 0, 0, 0)
            out.append(p)
        return Clip(name, out, fps, stride=stride)

    def roll(s, frames=None, fps=12, name='move'):
        """Wheels turn and tracks run as the body moves. One cycle = the shortest distance after which the picture
        repeats (a spoke gap or a track pad), so few frames give smooth motion."""
        cyc = []
        for n, w in s.wheels.items(): cyc.append(w['r'] * math.radians(w['sym']))
        for n, t in s.tracks.items(): cyc.append(t['pitch'])
        stride = max(cyc) if cyc else 40.0
        frames = frames or 6
        out = []
        for i in range(frames):
            d = stride * i / frames; p = s.pose()
            for n, w in s.wheels.items(): p[n] = (0, math.degrees(d / w['r']), 0)
            for n in s.tracks: p[n + '#'] = d
            for n in s.rotors: p[n] = (s.rotors[n]['sym'] * i / frames, 0, 0)
            p['root'] = (0, 0, .6 * math.sin(2 * math.pi * i / frames), 0, 0, 0)
            out.append(p)
        return Clip(name, out, fps, stride=stride)

    def fire(s, frames=6, fps=14, recoil=None, kick=1.5, name='fire'):
        """Top layer only: a shot leaves on frame 0, the barrel slides back recoil[1] units and returns."""
        out = []
        for i in range(frames):
            k = max(0.0, 1 - i / (frames * .6))
            p = s.pose()
            if recoil: p[recoil[0] + '@x'] = -recoil[1] * k
            p['flash'] = 1.0 if i == 0 else 0.0
            out.append(p)
        return Clip(name, out, fps, loop=False, events={'fire': 0}, layers=('U',) if s.layered else None)

    def check(s, clip):
        """Planted-foot drift (units) and how far any foot could not be reached, over a walk clip."""
        if not s.legs or not clip.stride: return dict(slide=0.0, float=0.0)
        slide = 0.0; miss = 0.0; n = clip.frames
        for i in range(n):
            a, b = clip.poses()[i], clip.poses()[(i + 1) % n]
            Ma, Mb = s.solve(a), s.solve(b)
            for l in s.legs:
                miss = max(miss, Ma['_miss_' + l])
                fa = np.asarray(a['foot_' + l]); fb = np.asarray(b['foot_' + l])
                if fa[2] < .01 and fb[2] < .01:
                    ga = fa[0] + clip.stride * i / n; gb = fb[0] + clip.stride * (i + 1) / n
                    if i + 1 == n: gb = fb[0] + clip.stride
                    slide = max(slide, abs(gb - ga))
        return dict(slide=slide, float=miss)
