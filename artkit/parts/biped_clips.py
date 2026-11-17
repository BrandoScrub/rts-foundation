"""Shared clips for a melee figure on two legs (a brawler, a creature, the dead): a walk gait given as a function, a
flinch, a strike and the fall. A unit file picks parts, a base pose, a gait and the shape of its attack; everything
else comes from here. `artkit.parts.infected` is the older name for this module and stays.
"""
import math
from ..figure import Clip, keyframes, cycle, Gait, merge
from ..core.geom import T, RX, RY, RZ, R3, xf

s2 = lambda t: math.sin(2 * math.pi * t)
c2 = lambda t: math.cos(2 * math.pi * t)


def build_clips(u, base, gait, walk, attack, frames=10, fps=14, extra=()):
    """base: pose channels held throughout. gait: Gait kwargs. walk(t, G): channels for phase t. attack: list of
    (t, channels) keyframes after the walk's first frame."""
    BASE = u.pose(**base); G = Gait(u, **gait)
    wf = cycle(BASE, lambda t: walk(t, G)); w0 = wf(0)
    hit = keyframes(w0, [
        (0.0, {}),
        (0.22, dict(pelvis=w0['pelvis'] + (-3, 0, -1), pelvis_rot=(w0['pelvis_rot'][0] + 10, w0['pelvis_rot'][1] - 14, 0),
                    chest_rot=(30, -16, -6), head_rot=(-10, -44, 0), hand_L=(6, 18, 30), hand_R=(2, -20, 20))),
        (0.55, dict(pelvis=w0['pelvis'] + (-1, 0, -1), chest_rot=(6, 30, 0), head_rot=(0, -10, 10))),
        (1.0, w0)])
    atk = keyframes(w0, [(0.0, {})] + attack + [(1.0, w0)])
    die = keyframes(w0, [
        (0.0, {}),
        (0.13, dict(pelvis=(-4, 0, -3), pelvis_rot=(-12, -14, 0), chest_rot=(-26, -24, 6), head_rot=(0, -46, 0),
                    hand_L=(2, 21, 32), hand_R=(0, -22, 30), foot_L=(4, 6, 0, -10, 6), foot_R=(-2, -6.5, 0, 0, -20))),
        (0.38, dict(pelvis=(-10, 0, -15), pelvis_rot=(-8, -44, 0), chest_rot=(-10, -16, 0), head_rot=(0, -20, 0),
                    hand_L=(-2, 22, 34), hand_R=(-3, -23, 34), foot_L=(7, 6, 5, -30, 6), foot_R=(1, -6.5, 0, -20, -20))),
        (0.66, dict(pelvis=(-18, 0, -38), pelvis_rot=(0, -76, 0), chest_rot=(0, -6, 0), head_rot=(0, -4, 0),
                    hand_L=(-4, 22, 26), hand_R=(-4, -21, 36), foot_L=(16, 6.5, 9, -50, 20), foot_R=(13, -7, 3, -40, -30))),
        (0.80, dict(pelvis=(-20, 0, -45), pelvis_rot=(0, -90, 0), chest_rot=(0, 9, 0), head_rot=(16, 16, 0),
                    hand_L=(-6, 20, 13), hand_R=(-6, -18, 31), foot_L=(21, 6.5, 0, 0, 50), foot_R=(19, -7, 0, 0, -50))),
        (1.0, dict(pelvis=(-20, 0, -43.5), pelvis_rot=(0, -88, 0), chest_rot=(0, 3, 0), head_rot=(24, 4, 0)))])
    out = [Clip('walk', wf, frames=frames, fps=fps, loop=True, stride=G.stride),
           Clip('hit', hit, frames=4, fps=12, loop=False),
           Clip('attack', atk, frames=5, fps=13, loop=False, events={'hit': 2}),
           Clip('die', die, frames=8, fps=11, loop=False, drag_ok=True)] + list(extra)
    return out, dict(base=w0), dict(stride=G.stride)
