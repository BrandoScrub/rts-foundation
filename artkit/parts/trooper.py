"""Trooper: the shared base for every soldier on foot. A new troop is a short file that picks parts, a weapon
and a way of firing; the body, the stances, the footwork (walk, run, backward) and the death come from here.

  build_trooper(name, weapon, headgear, chest=[...], pelvis=[...])  -> the assembled unit
  trooper_clips(u, fire='bolt' | 'auto', gaits={...}, stance={...}) -> clips, stances, scene pieces
"""
import math
import numpy as np
from ..figure import Biped, Clip, keyframes, cycle, merge, blend, overlay, Gait
from ..core.geom import T, RX, RY, RZ, R3, xf
from . import soldier as P

EYE = (4.6, -2.3, 9.2)        # right eye, head frame
HEAD = (0, 7, 11)             # head in the firing stance, in the world: yaw, nose down, tilt toward the stock

GAITS = dict(                  # Gait(front, back, stance, lift, strike, toe, kick): stride = (front - back) / stance
    walk=dict(front=16, back=-24, stance=.58, lift=6.5, strike=-16, toe=30),
    run=dict(front=13, back=-29, stance=.30, lift=9, strike=-8, toe=38, kick=9),
    back=dict(front=-22, back=14, stance=.36, lift=5, strike=18, toe=-6),
)
FPS = dict(walk=14, run=18, back=16)


def build_trooper(name, weapon, headgear, chest=(), pelvis=()):
    """weapon: dict(mesh, grips, muzzle, sight, butt[, bolt, port]) from parts. chest / pelvis: (mesh, label) extras."""
    u = Biped(name)
    u.layered = True              # legs and torso are separate strips: any action over any footwork
    u.weapon = weapon
    u.attach('pelvis', P.pelvis_skirt(), 'tunic skirt and belt')
    for mesh, label in pelvis: u.attach('pelvis', mesh, label)
    u.attach('chest', P.tunic(), 'tunic')
    for mesh, label in chest: u.attach('chest', mesh, label)
    u.attach('head', P.head(), 'head')
    u.attach('head', headgear[0], headgear[1])
    u.attach_pair('thigh', P.thigh(), 'thigh')
    u.attach_pair('shin', P.shin(), 'puttee')
    u.attach_pair('foot', P.boot(), 'boot')
    u.attach_pair('upper_arm', P.upper_arm(), 'upper arm')
    u.attach_pair('fore_arm', P.fore_arm(), 'forearm')
    u.attach_pair('hand', P.hand(), 'hand')
    u.grips, u.muzzle = weapon['grips'], weapon['muzzle']
    u.attach('prop', weapon['mesh'], weapon.get('name', 'weapon'))
    u.attach('prop', P.muzzle_flash(u.muzzle, weapon.get('flash', 1.0)), 'muzzle flash', when='flash')
    return u


def head_at(pelvis_rot, chest_rot, yaw, pitch, roll):
    """The head_rot that leaves the head at this orientation in the world, however the body under it is turned."""
    m = (R3(*pelvis_rot) @ R3(*chest_rot))[:3, :3].T @ R3(yaw, pitch, roll)[:3, :3]
    return (math.degrees(math.atan2(m[1, 0], m[0, 0])), math.degrees(math.asin(-m[2, 0])), math.degrees(math.atan2(m[2, 1], m[2, 2])))


def sighted(u, body, recoil=0.0, kick=0.0, drop=0.0, roll=0.0, **extra):
    """A full pose with the weapon laid along +x so its sights pass through the right eye and its butt
    sits at the right shoulder. recoil pushes it back, kick lifts the muzzle about the butt, drop lowers it."""
    w = u.weapon
    pose = merge(u.pose(grip_L=1, grip_R=1, **body), extra)
    M = u.solve(pose)
    eye = xf(M['head'], EYE); sh = xf(M['chest'], (0, -12, 24))
    butt = (sh[0] + 3.0 - recoil, eye[1], eye[2] - w['sight'] - drop)
    pose['prop'] = u.prop_from_world(pose, T(*butt) @ RY(-kick) @ RX(roll) @ T(-w['butt'], 0, 0))
    return pose


def trooper_clips(u, fire='bolt', gaits=None, stance=None, weight=1.0, head=HEAD):
    """fire: 'bolt' (one shot, recoil, work the bolt) or 'auto' (a looping burst). gaits overrides GAITS per gait.
    stance overrides channels of the firing stance. weight scales how much the body is thrown about (heavier = less)."""
    W = u.weapon; BOLT = W.get('bolt'); PORT = W.get('port', (10.8, 0.5, 13, 72, 38, 0))
    G = {k: {**GAITS[k], **((gaits or {}).get(k, {}))} for k in GAITS}
    wt = weight
    s2 = lambda t: math.sin(2 * math.pi * t)
    c2 = lambda t: math.cos(2 * math.pi * t)

    # ---- stances
    READY = u.pose(                                   # port arms: carbine across the chest, muzzle up-left
        pelvis=(0, 0, -1.2), chest_rot=(0, 3, 0),
        foot_L=(1.5, 5.8, 0, 0, 8), foot_R=(-1.5, -5.8, 0, 0, -8),
        prop=PORT, grip_L=1, grip_R=1)
    BODY = dict(                                      # firing stance: left side to the target, weight forward
        pelvis=(1.5, 0, -5.0), pelvis_rot=(-34, 7, 0), chest_rot=(-24, 10, 3),
        foot_L=(11, 3.0, 0, 0, -8), foot_R=(-10, -6.5, 0, 0, -62),
        elbow_R=(-.3, -1, .35), elbow_L=(.2, .35, -1))
    BODY.update(stance or {})
    BODY['head_rot'] = head_at(BODY['pelvis_rot'], BODY['chest_rot'], *head)
    body = lambda **k: {**BODY, **k}
    # offsets from the firing stance, so recoil and settling work for any stance (standing, braced, kneeling)
    pv = lambda dx=0, dz=0: (BODY['pelvis'][0] + dx, BODY['pelvis'][1], BODY['pelvis'][2] + dz)
    pr = lambda dy=0, dp=0: (BODY['pelvis_rot'][0] + dy, BODY['pelvis_rot'][1] + dp, BODY['pelvis_rot'][2])
    cr = lambda dy=0, dp=0: (BODY['chest_rot'][0] + dy, BODY['chest_rot'][1] + dp, BODY['chest_rot'][2])
    hw = lambda b, dy=0, dp=0, dr=0: head_at(b['pelvis_rot'], b['chest_rot'], head[0] + dy, head[1] + dp, head[2] + dr)   # head held in the world
    port = lambda dx=0, dy=0, dz=0, dyaw=0, delev=0: (PORT[0] + dx, PORT[1] + dy, PORT[2] + dz, PORT[3] + dyaw, PORT[4] + delev, PORT[5])
    AIM = sighted(u, BODY)

    # ---- idle
    def idle(t):
        b = s2(t)
        return dict(pelvis=(0, .5 * s2(t / 2 + .1), -1.2 - .4 * b), pelvis_rot=(0, 0, 1.2 * s2(t + .2)),
                    chest_rot=(3 * s2(t + .3), 3 + 1.2 * b, 0), head_rot=(14 * s2(t + .15), -2, 0),
                    prop=port(0, 0, .6 * b, 2 * b, 2 * b))

    # ---- walk: a brisk march. Gait(front, back, stance): ground per cycle = (front - back) / stance, exactly
    WALK = Gait(u, **G['walk'])
    def walk(t):
        c4 = math.cos(4 * math.pi * t)
        return dict(pelvis=(0, 1.4 * s2(t - .1), -5.2 - 1.6 * c4), pelvis_rot=(-9 * c2(t), 6, 3.5 * s2(t - .1)),
                    chest_rot=(17 * c2(t), 5 + 1.5 * c4, -3.5 * s2(t - .1)), head_rot=(-8 * c2(t), -6, 0),
                    foot_L=WALK.foot(t, 5.6, 4), foot_R=WALK.foot(t + .5, -5.6, -4),
                    prop=port(1.0 * c2(t), 0, 1.2 * c4, 5 * c2(t), 4 * s2(t)))

    # ---- run: on the ground under a third of the time, a long flight between, deep lean, carbine pumping
    RUN = Gait(u, **G['run'])
    def run(t):
        bob = -3.0 * wt * math.cos(4 * math.pi * (t - RUN.stance / 2))
        return dict(pelvis=(0, 1.2 * s2(t - .1), -7.0 + bob), pelvis_rot=(-13 * c2(t - .08), 15, 5 * s2(t - .1)),
                    chest_rot=(27 * c2(t - .08), 9 - .5 * bob, -5 * s2(t - .1)),
                    head_rot=(-14 * c2(t - .08), -18, 0),
                    foot_L=RUN.foot(t, 5.2), foot_R=RUN.foot(t + .5, -5.2),
                    prop=port(.7 + 2.2 * wt * c2(t), -1.5 * wt * c2(t), -.5 - .5 * bob, -2 + 11 * wt * c2(t), -8 + 9 * wt * s2(t)),
                    elbow_L=(-.6, 1, -.2), elbow_R=(-.6, -1, -.2))

    # ---- back: a fast backward shuffle, used with the torso aiming and firing while he gives ground.
    # front is behind the hip (he lands on the ball of the foot) and back is ahead of it: the stride is negative.
    BACK = Gait(u, **G['back'])
    def back_legs(t):
        bob = -2.0 * math.cos(4 * math.pi * (t - BACK.stance / 2))
        return merge(READY, dict(pelvis=(0, 1.0 * s2(t - .1), -8.0 + bob), pelvis_rot=(5 * c2(t), 3, 3 * s2(t - .1)),
                                 foot_L=BACK.foot(t, 5.6, 2), foot_R=BACK.foot(t + .5, -5.6, -2)))
    back = lambda t: overlay(back_legs(t), AIM)

    # ---- raise: skid to a halt, drop into the stance, sights come up past the target and settle
    BRACE = u.pose(pelvis=(4, 0, -11), pelvis_rot=(-18, 20, 0), chest_rot=(-10, 14, 0), head_rot=(26, -16, 0),
                   foot_L=BODY['foot_L'], foot_R=BODY['foot_R'],
                   prop=port(1.2, -1.5, 1, -16, -22), grip_L=1, grip_R=1)
    raise_ = keyframes(BRACE, [
        (0.0, {}),
        (0.5, sighted(u, body(pelvis=pv(1.5, -2.5), pelvis_rot=pr(0, 5)), kick=-5)),
        (0.78, sighted(u, body(pelvis=pv(-.5, .8), pelvis_rot=pr(0, -2)), kick=2.5)),
        (1.0, AIM)])
    # into the stance by stepping: left foot out, then right foot back; a planted foot never moves
    mid = lambda a, b, z, pitch: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, max(a[2], b[2]) + z, pitch, (a[4] + b[4]) / 2)
    stepL = dict(foot_L=mid(READY['foot_L'], AIM['foot_L'], 4.5, -12)); stepR = dict(foot_R=mid(READY['foot_R'], AIM['foot_R'], 4, 12))
    aim = keyframes(READY, [
        (0.0, {}),
        (0.16, {**blend(READY, BRACE, .5), **{k: READY[k] for k in ('foot_R',)}, **stepL}),
        (0.32, {**BRACE, 'foot_L': AIM['foot_L'], 'foot_R': READY['foot_R']}),
        (0.48, stepR),
        (0.64, {**sighted(u, body(pelvis=pv(1, -1.5)), kick=-4)}),
        (1.0, AIM)])
    lower = keyframes(AIM, [
        (0.0, {}),
        (0.25, {**blend(AIM, READY, .3), 'foot_L': AIM['foot_L'], **stepR}),
        (0.5, {**blend(AIM, READY, .6), 'foot_L': AIM['foot_L'], 'foot_R': READY['foot_R']}),
        (0.75, {**blend(AIM, READY, .85), 'foot_R': READY['foot_R'], **stepL}),
        (1.0, READY)])
    hold = lambda t: sighted(u, body(pelvis=pv(0, -.35 * s2(t)), chest_rot=cr(0, .5 * s2(t))))

    if fire == 'auto':
        # a burst: one shot per loop, the gun hammering back into the shoulder, the body braced against it
        def fire_fn(t):
            k = math.exp(-5 * t); sh = math.sin(2 * math.pi * t * 2)
            return sighted(u, body(pelvis=(BODY['pelvis'][0] - 1.0 * k, .3 * sh, BODY['pelvis'][2] - .4 * k),
                                   chest_rot=(BODY['chest_rot'][0] - 2.5 * k, BODY['chest_rot'][1] - 2.0 * k, BODY['chest_rot'][2])),
                           recoil=2.4 * k, kick=3.5 * k, flash=1 if t < .3 else 0)
        fire_clip = Clip('fire', fire_fn, frames=6, fps=20, loop=True, events={'fire': 0})
    else:
        # ---- fire: squeeze, shot, the whole upper body rocks back, settles, works the bolt, back on the sights
        rock = body(pelvis=pv(-2.7, .4), pelvis_rot=pr(-2, -5), chest_rot=cr(-5, -9)); rock['head_rot'] = hw(rock, 0, -5)
        far = body(pelvis=pv(-3.9, .8), pelvis_rot=pr(-3, -8), chest_rot=cr(-7, -14)); far['head_rot'] = hw(far, 0, -8)
        fwd = body(pelvis=pv(.8, -.6), pelvis_rot=pr(0, 2), chest_rot=cr(0, 3))
        up = body(); up['head_rot'] = hw(up, -6, -9, -8)                                  # head off the stock to work the bolt
        b0 = sighted(u, up, drop=3.0, roll=-22, kick=-5)
        fire = keyframes(AIM, [
            (0.00, {}),
            (0.07, sighted(u, body(pelvis=pv(.5, -.3)))),                      # leans into it
            (0.12, sighted(u, rock, recoil=3.2, kick=6, flash=1)),                # shot
            (0.20, sighted(u, far, recoil=4.5, kick=13, flash=0)),                # muzzle climbs, shoulder driven back
            (0.34, sighted(u, fwd, recoil=-.6, kick=-3)),                         # comes back past the rest position
            (0.46, merge(b0, dict(grip_R=0, hand_R=u.prop_point(b0, BOLT)))),     # hand to the bolt
            (0.58, dict(hand_R=u.prop_point(b0, (BOLT[0] - 6, BOLT[1], BOLT[2] + 1.5)))),   # back
            (0.72, dict(hand_R=u.prop_point(b0, BOLT))),                          # home
            (0.86, merge(sighted(u, body(pelvis=pv(0, -.6)), kick=-2), dict(grip_R=1))),
            (1.00, AIM)])

        fire_fn = fire
        fire_clip = Clip('fire', fire, frames=9, fps=12, loop=False, events={'fire': 1})

    # ---- die: staggers, knees go, falls on his face; the carbine lands beside him
    die = keyframes(READY, [
        (0.0, {}),
        (0.14, dict(pelvis=(-1.5, 0, -2), pelvis_rot=(0, -6, 0), chest_rot=(8, -12, 4), head_rot=(0, -24, 0),
                    grip_L=0, hand_L=(8, 19, 22), prop=(11, -3, 10, 60, 20, 10))),
        (0.36, dict(pelvis=(3, 0, -15), pelvis_rot=(0, 18, 0), chest_rot=(6, 22, 0), head_rot=(0, 10, 0),
                    foot_L=(1.5, 6, 0, 10, 12), foot_R=(-3, -6, 0, 20, -12),
                    grip_R=0, hand_L=(12, 17, 14), hand_R=(12, -16, 12), prop=(14, -12, 4, 30, -10, 40))),
        (0.62, dict(pelvis=(11, 0, -33), pelvis_rot=(0, 55, 0), chest_rot=(6, 16, 0), head_rot=(10, -10, 0),
                    foot_L=(-6, 6.5, 0, 40, 30), foot_R=(-9, -7, 0, 45, -30),
                    hand_L=(10, 17, 28), hand_R=(10, -18, 18), prop=(9, -20, 16, -40, 40, 70))),
        (0.84, dict(pelvis=(19, 0, -42.5), pelvis_rot=(0, 84, 0), chest_rot=(8, 4, 0), head_rot=(30, -8, 0),
                    foot_L=(-24, 7, 0, 0, 70), foot_R=(-25, -8, 0, 0, -65),
                    hand_L=(6.5, 17, 35), hand_R=(6.5, -19, 15), prop=(5.5, -22, 30, -90, 72, 90))),
        (1.0, dict(pelvis=(20, 0, -43.5), pelvis_rot=(0, 87, 0), head_rot=(42, -6, 0))),
    ])

    out = [
        Clip('idle', cycle(READY, idle), frames=8, fps=6, loop=True),
        Clip('walk', cycle(READY, walk), frames=10, fps=FPS['walk'], loop=True, stride=WALK.stride),
        Clip('run', cycle(READY, run), frames=10, fps=FPS['run'], loop=True, stride=RUN.stride),
        Clip('back', back, frames=8, fps=FPS['back'], loop=True, stride=BACK.stride),
        Clip('aim', aim, frames=6, fps=14, loop=False),
        fire_clip,
        Clip('die', die, frames=8, fps=10, loop=False, drag_ok=True),
    ]
    extra = dict(raise_=raise_, hold=hold, lower=lower, walk=cycle(READY, walk), walk_stride=WALK.stride,
                 run=cycle(READY, run), idle=cycle(READY, idle), fire=fire_fn, run_stride=RUN.stride,
                 back_legs=back_legs, back_stride=BACK.stride)
    return out, dict(ready=READY, aim=AIM), extra
