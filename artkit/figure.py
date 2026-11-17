"""artkit.figure: jointed figures (people, creatures, walking machines) and their animation.
Moved here from unitkit (rig.py, tripod.py, the material list of mesh.py); unitkit re-exports it.

Figure materials: parts name the cloth, leather and steel they are made of with material(name, colour, weave).
That gives every part a default look; a style pack overrides any of them by listing the same name under "figures",
and a painted tile materials/<name>.png overrides both.

A jointed biped that parts are attached to, plus clips (cycles and keyframed animations).

Bones and their local frames (x forward, y left, z up):
  pelvis   origin at the hip centre
  chest    origin at the waist; shoulders at z=24, neck at z=28
  head     origin at the neck base
  thigh_L/R, shin_L/R, upper_arm_L/R, fore_arm_L/R   hang down -z from their joint
  foot_L/R origin on the ground under the ankle
  hand_L/R origin at the hand centre
  prop     the held object, modelled along +x (muzzle forward)

Limbs are solved by IK: a pose says where the feet stand and what the hands hold,
and knees and elbows follow. That keeps feet planted and both hands on the weapon.
"""
import math, os

import numpy as np

from .core.geom import T, RY, RZ, R3, aim, ik2, xf, Geometry
from .core.materials import Materials, Material, procedural

# ---------------------------------------------------------------- figure materials
MATS = []          # list of dicts: name, tex (h, w, 3 float 0..1), emissive
MAT_ID = {}
TEX_PX_PER_UNIT = 3.0


def material(name, color, kind='plain', emissive=False, seed=None):
    if seed is None: seed = sum(map(ord, name))
    d = dict(name=name, tex=procedural(color, kind, seed), emissive=emissive, color=tuple(color), kind=kind)
    if name in MAT_ID: MATS[MAT_ID[name]] = d
    else: MAT_ID[name] = len(MATS); MATS.append(d)
    return name


def load_painted(folder):
    """materials/<name>.png (flat seamless tile) replaces a procedural tile."""
    from PIL import Image
    used = []
    if not os.path.isdir(folder): return used
    for name, i in MAT_ID.items():
        p = os.path.join(folder, name + '.png')
        if os.path.exists(p):
            im = Image.open(p).convert('RGB').resize((96, 96), Image.LANCZOS)
            MATS[i]['tex'] = np.asarray(im, float) / 255.0; used.append(name)
    return used


def registry():
    """The figure materials as a renderer registry (nearest texel, TEX_PX_PER_UNIT texels per unit)."""
    return Materials(fallback=lambda n: Material(MATS[MAT_ID[n]]['tex'], 'nearest', TEX_PX_PER_UNIT, MATS[MAT_ID[n]]['emissive']) if n in MAT_ID else None)



def _arr(d): return {k: np.atleast_1d(np.asarray(v, float)) for k, v in d.items()}

def merge(a, b):
    o = dict(a); o.update(_arr(b)); return o


class Biped:
    DIMS = dict(thigh=24.0, shin=22.0, ankle=5.0, hip_w=5.5, spine=6.0,
                shoulder=(0.0, 12.0, 24.0), upper_arm=15.0, fore_arm=14.0, neck=(0.0, 0.0, 28.0))
    # every channel a pose can set
    BASE = dict(
        pelvis=(0, 0, 0),            # offset from standing straight
        pelvis_rot=(0, 0, 0),        # yaw, pitch (lean forward), roll
        chest_rot=(0, 0, 0),         # relative to pelvis
        head_rot=(0, 0, 0),          # relative to chest
        foot_L=(0, 5.5, 0, 0, 0),    # x, y, z of the sole, pitch (toe down), yaw
        foot_R=(0, -5.5, 0, 0, 0),
        prop=(10, 0, 13, 0, 0, 0),   # in the chest frame: x, y, z, yaw, elevation, roll
        hand_L=(4, 14, 6),           # free hand targets, chest frame
        hand_R=(4, -14, 6),
        grip_L=(0,), grip_R=(0,),    # 1 = hand is on the prop's grip point
        elbow_L=(-.5, .8, -.6), elbow_R=(-.5, -.8, -.6),   # elbow direction, chest frame
        knee_L=(1, 0, .15), knee_R=(1, 0, .15),              # knee direction, pelvis frame (down-forward to kneel)
        flash=(0,),
    )

    def __init__(s, name, **dims):
        s.name = name
        s.d = dict(s.DIMS); s.d.update(dims)
        s.parts = []                 # (bone, mesh, name, when)
        s.grips = {'L': (9, 0, -1), 'R': (-6, 0, -1)}
        s.muzzle = (24, 0, 0)
        s.sole = dict(heel=-3.6, ball=8.2)   # contact points along the foot, foot frame
        s.base = _arr(s.BASE)

    # ---- assembly
    def attach(s, bone, mesh, name=None, when=None):
        s.parts.append((bone, mesh.group(len(s.parts)), name or bone, when)); return s

    def attach_pair(s, bone, mesh, name=None):
        """Same part on the left and, mirrored, on the right."""
        s.attach(bone + '_L', mesh, name and name + '_L')
        s.attach(bone + '_R', mesh.mirror_y(), name and name + '_R'); return s

    def pose(s, **ch): return merge(s.base, ch)

    @staticmethod
    def prop_matrix(p):
        return T(p[0], p[1], p[2]) @ RZ(p[3]) @ RY(-p[4]) @ R3(0, 0, p[5])

    def prop_point(s, pose, local):
        """A point on the prop, in chest coordinates (for hands that reach to a bolt, a magazine...)."""
        return xf(s.prop_matrix(np.asarray(pose['prop'], float)), local)

    # ---- solve
    def solve(s, p):
        d = s.d; M = {}
        hip_h = d['thigh'] + d['shin'] + d['ankle']
        pe = p['pelvis']
        Mp = T(pe[0], pe[1], pe[2] + hip_h) @ R3(*p['pelvis_rot'])
        Mc = Mp @ T(0, 0, d['spine']) @ R3(*p['chest_rot'])
        Mh = Mc @ T(*d['neck']) @ R3(*p['head_rot'])
        Mr = Mc @ s.prop_matrix(p['prop'])
        M.update(pelvis=Mp, chest=Mc, head=Mh, prop=Mr)
        fwd = Mp[:3, :3] @ np.array([1.0, 0, 0.15])
        for side, sg in (('L', 1), ('R', -1)):
            f = p['foot_' + side]
            hip = xf(Mp, (0, sg * d['hip_w'], 0))
            Mf0 = T(f[0], f[1], f[2]) @ RZ(f[4]) @ RY(f[3])          # foot yaw is absolute: a planted foot does not turn with the hips
            ankle = xf(Mf0, (0, 0, d['ankle']))
            kd = Mp[:3, :3] @ p['knee_' + side]
            knee, end = ik2(hip, ankle, d['thigh'], d['shin'], kd)
            M['thigh_' + side] = aim(hip, knee, fwd)
            M['shin_' + side] = aim(knee, end, fwd)
            miss = end - ankle                                      # leg too short to reach: the foot follows the leg
            M['foot_' + side] = T(*miss) @ Mf0
            M['_miss_' + side] = float(np.linalg.norm(miss))
            sh = xf(Mc, (d['shoulder'][0], sg * d['shoulder'][1], d['shoulder'][2]))
            free = xf(Mc, p['hand_' + side]); held = xf(Mr, s.grips[side])
            g = float(np.clip(p['grip_' + side][0], 0, 1))
            tgt = free * (1 - g) + held * g
            pole = Mc[:3, :3] @ p['elbow_' + side]
            elbow, hand = ik2(sh, tgt, d['upper_arm'], d['fore_arm'], pole)
            cf = Mc[:3, 0]
            M['upper_arm_' + side] = aim(sh, elbow, cf)
            Mf = aim(elbow, hand, cf); M['fore_arm_' + side] = Mf
            Mhd = Mf.copy(); Mhd[:3, 3] = hand; M['hand_' + side] = Mhd
        return M

    UPPER = ('chest', 'head', 'upper_arm', 'fore_arm', 'hand', 'prop')   # bones of the torso layer; the rest is legs
    layered = False          # True: strips are exported as a legs layer and a torso layer the game can mix

    def layer_of(s, bone):
        return 'U' if bone.rstrip('_LR') in s.UPPER or bone in s.UPPER else 'L'

    def build(s, pose, heading=0.0, layer=None):
        """World mesh for one pose at one heading (degrees, 0 = +x), plus markers. layer 'L' or 'U' builds
        only the legs or only the torso."""
        M = s.solve(pose); H = RZ(heading); out = []
        for bone, mesh, _, when in s.parts:
            if when and float(pose[when][0]) < 0.5: continue
            if layer and s.layer_of(bone) != layer: continue
            out.append(mesh.at(H @ M[bone]))
        mk = dict(muzzle=xf(H @ M['prop'], s.muzzle), socket=xf(H @ M['chest'], (0, 0, 0)))
        return (sum(out[1:], out[0]) if out else None), mk

    def describe(s):
        return [(n, b, len(m)) for b, m, n, _ in s.parts]


# ---------------------------------------------------------------- clips
class Clip:
    """fn(t) -> pose for t in 0..1. A loop samples t = i/frames; a one-shot samples both ends."""
    def __init__(s, name, fn, frames, fps, loop=True, events=None, stride=None, drag_ok=False, layers=None):
        s.name, s.fn, s.frames, s.fps, s.loop = name, fn, frames, fps, loop
        s.events = events or {}; s.stride = stride; s.drag_ok = drag_ok
        s.layers = layers            # None = every layer; 'U' = torso strip only (the legs stand on their idle frame)
    def times(s):
        n = s.frames
        return [i / n for i in range(n)] if s.loop else [i / (n - 1) for i in range(n)]
    def poses(s): return [s.fn(t) for t in s.times()]


def keyframes(base, keys, loop=False, ease=True):
    """keys = [(t, {channel: value, ...}), ...]. Each key carries the previous key's channels forward."""
    ks = []; cur = dict(base)
    for t, ch in sorted(keys, key=lambda k: k[0]):
        cur = merge(cur, ch); ks.append((t, cur))
    if loop and ks[-1][0] < 1.0: ks.append((1.0, ks[0][1]))
    def fn(t):
        if t <= ks[0][0]: return ks[0][1]
        for (t0, a), (t1, b) in zip(ks, ks[1:]):
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-9)
                if ease: u = u * u * (3 - 2 * u)
                return {k: a[k] * (1 - u) + b[k] * u for k in a}
        return ks[-1][1]
    return fn


LOWER_CH = ('pelvis', 'pelvis_rot', 'foot_L', 'foot_R')

def overlay(lower, upper):
    """Legs from one pose, torso from another: what the game does when it mixes the two layers.
    The torso keeps the direction it had in its own pose, whatever the new hips are doing."""
    o = dict(upper)
    for k in LOWER_CH: o[k] = lower[k]
    cr = np.array(upper['chest_rot'], float); cr[0] += upper['pelvis_rot'][0] - lower['pelvis_rot'][0]
    cr[1] += upper['pelvis_rot'][1] - lower['pelvis_rot'][1]
    o['chest_rot'] = cr
    return o


def cycle(base, fn):
    """Wrap a procedural function t -> {channels} into a full pose function."""
    return lambda t: merge(base, fn(t))


# ---------------------------------------------------------------- helpers for dynamic motion
import math as _m

def blend(a, b, u):
    """Mix two full poses (u = 0 gives a, 1 gives b)."""
    return {k: a[k] * (1 - u) + b[k] * u for k in a}

class Gait:
    """A gait set by where the foot touches down (front) and where it leaves (back), in units ahead of the hip,
    and the share of the cycle it spends on the ground (stance). Ground covered per cycle is exact:
    stride = (front - back) / stance. While planted the foot rolls heel -> flat -> ball about a point that stays
    fixed on the ground, so a unit moved stride units per cycle cannot slide. Under 0.5 stance there is a flight phase."""
    def __init__(s, unit, front, back, stance, lift, strike=-14.0, toe=32.0, kick=0.0):
        s.front, s.back, s.stance, s.lift, s.strike, s.toe, s.kick = front, back, stance, lift, strike, toe, kick
        s.heel, s.ball = unit.sole['heel'], unit.sole['ball']
        s.stride = (front - back) / stance

    def foot(s, ph, y, yaw=0.0, lift=None):
        """Foot channel (x, y, z, pitch, yaw) at phase ph; phase 0 is touch-down."""
        ph %= 1.0; lift = s.lift if lift is None else lift; lz = 0.0
        if ph < s.stance:
            a = ph / s.stance
            ref = s.front + (s.back - s.front) * a                  # constant speed: this is the ground going by
            pitch = s.strike * max(0.0, 1 - a / .22) + s.toe * max(0.0, (a - .6) / .4) ** 1.5
        else:
            a = (ph - s.stance) / (1 - s.stance); e = (1 - _m.cos(_m.pi * a)) / 2
            ref = s.back + (s.front - s.back) * e
            fl = _m.sin(_m.pi * min(a * 1.7, 1.0)) * (1 - a)        # heel flick early in the swing
            pitch = s.toe * (1 - a) ** 1.3 + s.strike * a ** 2 + s.kick * 3 * fl
            lz = lift * _m.sin(_m.pi * a) ** .8 + s.kick * fl
        piv = s.ball if pitch > 0 else s.heel                       # roll about the ball going off, the heel coming on
        r = _m.radians(pitch); off = piv * (1 - _m.cos(r)); cy, sy = _m.cos(_m.radians(yaw)), _m.sin(_m.radians(yaw))
        return (ref + off * cy, y + off * sy, piv * _m.sin(r) + lz, pitch, yaw)


def check_clip(unit, clip, n=120, contact=.35):
    """Measure what would show as sliding. Returns dict(slide, float, sink, flight):
    slide  = farthest a planted contact point (heel or ball) drifts over the ground, in units, with the unit
             moving clip.stride per cycle (0 for clips that stand still)
    float  = worst gap between where a foot was asked to be and where the leg could put it
    sink   = deepest a contact point goes below the ground
    flight = share of the clip with neither foot down"""
    stride = clip.stride or 0.0
    ts = [i / n for i in range(n + 1)]
    Ms = [unit.solve(clip.fn(t % 1.0 if clip.loop else t)) for t in ts]
    slide = flt = sink = 0.0; down = np.zeros(n + 1, bool)
    for side in getattr(unit, 'FEET', 'LR'):
        flt = max(flt, max(M['_miss_' + side] for M in Ms))
        for name, lx in unit.sole.items():
            P = np.array([xf(M['foot_' + side], (lx, 0, 0)) for M in Ms])
            c = P[:, 2] < contact; down |= c; sink = max(sink, -P[:, 2].min())
            acc = np.zeros(2)
            for i in range(n):
                if c[i] and c[i + 1]:
                    acc += (P[i + 1, 0] - P[i, 0] + stride * (ts[i + 1] - ts[i]), P[i + 1, 1] - P[i, 1])
                    slide = max(slide, float(np.linalg.norm(acc)))
                else: acc[:] = 0
    return dict(slide=slide, float=flt, sink=sink, flight=float(1 - down.mean()))


def _prop_from_world(s, pose, Mw):
    """Prop channel that puts the prop at a world-space matrix (unit facing +x), whatever the torso is doing."""
    L = np.linalg.inv(s.solve(pose)['chest']) @ Mw; R = L[:3, :3]
    e = _m.degrees(_m.asin(float(np.clip(R[2, 0], -1, 1))))
    return np.array([L[0, 3], L[1, 3], L[2, 3], _m.degrees(_m.atan2(R[1, 0], R[0, 0])), e,
                     _m.degrees(_m.atan2(R[2, 1], R[2, 2]))])

def _point(s, pose, bone, local):
    return xf(s.solve(pose)[bone], local)

Biped.prop_from_world = _prop_from_world
Biped.point = _point


# ---------------------------------------------------------------- three-legged walking machine
class Tripod:
    FEET = 'ABC'
    UPPER = ('hull', 'gun_L', 'gun_R')
    layered = True
    free_torso = True            # manifest flag: the legs keep their heading while the hull turns
    LEG_ANG = dict(A=0.0, B=125.0, C=-125.0)

    def __init__(s, name, hub_z=215.0, hip_r=34.0, femur=190.0, tibia=235.0, ankle=18.0, reach=150.0,
                 gun_at=(26.0, 66.0, 34.0), marks=None):
        s.name = name; s.parts = []
        s.hub_z, s.hip_r, s.femur, s.tibia, s.ankle = hub_z, hip_r, femur, tibia, ankle
        s.gun_at = gun_at
        s.home = {k: (reach * math.cos(math.radians(a)), reach * math.sin(math.radians(a))) for k, a in s.LEG_ANG.items()}
        s.sole = dict(heel=-14.0, ball=14.0)
        s.muzzle = (90.0, 0.0, 0.0)
        s.points = marks or {}           # name -> (bone, local point): reported per frame in the export
        s.base = _arr(dict(hub=(0, 0, 0), hub_rot=(0, 0, 0), hull_rot=(0, 0, 0), gun=(0, 0, 0), flash_L=(0,), flash_R=(0,),
                           **{'foot_' + k: (h[0], h[1], 0, 0, 0) for k, h in s.home.items()}))

    def attach(s, bone, mesh, name=None, when=None):
        s.parts.append((bone, mesh.group(len(s.parts)), name or bone, when)); return s

    def pose(s, **ch): return merge(s.base, ch)

    def solve(s, p):
        M = {}; h = p['hub']
        Mh = T(h[0], h[1], h[2] + s.hub_z) @ R3(*p['hub_rot'])
        Mu = Mh @ T(0, 0, 20) @ R3(*p['hull_rot'])
        M.update(hub=Mh, hull=Mu)
        g = p['gun']; gx, gy, gz = s.gun_at
        M['gun_L'] = Mu @ T(gx, gy, gz) @ RY(-g[0]) @ T(-g[1], 0, 0)
        M['gun_R'] = Mu @ T(gx, -gy, gz) @ RY(-g[0]) @ T(-g[2], 0, 0)
        for k, a in s.LEG_ANG.items():
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            hip = xf(Mh, (s.hip_r * ca, s.hip_r * sa, 0))
            f = p['foot_' + k]
            Mf0 = T(f[0], f[1], f[2]) @ RZ(f[4]) @ RY(f[3])
            ankle = xf(Mf0, (0, 0, s.ankle))
            out = Mh[:3, :3] @ np.array([ca, sa, 0.0])
            pole = out * .55 + np.array([0, 0, 1.0])
            knee, end = ik2(hip, ankle, s.femur, s.tibia, pole)
            M['femur_' + k] = aim(hip, knee, out)
            M['tibia_' + k] = aim(knee, end, out)
            miss = end - ankle
            M['foot_' + k] = T(*miss) @ Mf0
            M['_miss_' + k] = float(np.linalg.norm(miss))
        return M

    def layer_of(s, bone): return 'U' if bone in s.UPPER else 'L'

    def build(s, pose, heading=0.0, layer=None):
        M = s.solve(pose); H = RZ(heading); out = []
        for bone, mesh, _, when in s.parts:
            if when and float(pose[when][0]) < 0.5: continue
            if layer and s.layer_of(bone) != layer: continue
            out.append(mesh.at(H @ M[bone]))
        mk = dict(muzzle=xf(H @ M['gun_L'], s.muzzle), muzzle_R=xf(H @ M['gun_R'], s.muzzle), socket=xf(H @ M['hull'], (0, 0, 0)))
        for n, (bone, local) in s.points.items(): mk[n] = xf(H @ M[bone], local)
        for k in s.FEET: mk['foot_' + k] = xf(H @ M['foot_' + k], (0, 0, 0))
        return (sum(out[1:], out[0]) if out else None), mk

    def describe(s):
        return [(n, b, len(m)) for b, m, n, _ in s.parts]
