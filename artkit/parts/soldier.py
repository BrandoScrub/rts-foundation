"""Soldier parts (first made for one game, usable by any). Each function returns a mesh in the local frame of the bone it goes on.
Other troops reuse these and swap a few (helmet for cap, a different weapon, no pack).
"""
import math
import numpy as np
from ..figure import *
from ..figure import material
from ..core.geom import T, RX, RY, RZ, R3, aim, ik2, xf
from ..shapes import blob_lathe as lathe, from_quads, slab as box, beam, sphere, ellipsoid, cyl

# ---- materials (procedural tiles; a painted materials/<name>.png overrides any of them)
material('tunic',    (146, 146, 104), 'wool')
material('trousers', (114, 114, 90), 'wool')
material('puttee',   (174, 160, 118), 'wrap')
material('boot',     (46, 38, 34),   'leather')
material('leather',  (104, 66, 40),  'leather')
material('canvas',   (180, 164, 120), 'canvas')
material('blanket',  (108, 104, 112), 'wool')
material('skin',     (214, 168, 132))
material('hair',     (58, 42, 32))
material('band',     (150, 46, 40),  'wool')          # oxblood cap band
material('wood',     (122, 76, 42),  'wood')
material('steel',    (70, 74, 82),   'metal')
material('brass',    (204, 162, 72), 'metal')
material('flash',    (255, 232, 150), emissive=True)
material('flash_core', (255, 252, 230), emissive=True)

# ---- body
def pelvis_skirt():
    """Tunic skirt over the hips, belt, buckle."""
    m = lathe([(7.6, -8), (8.8, -4), (8.9, 1), (8.4, 6)], 'tunic').scaled(.84, 1.08, 1)
    m += lathe([(8.9, 3.6), (8.9, 6.6)], 'leather').scaled(.84, 1.08, 1)
    m += box(6.9, 8.1, -1.5, 1.5, 3.9, 6.3, 'brass')
    return m

def ammo_pouches():
    p = box(5.2, 8.9, 3.4, 7.6, 1.6, 6.8, 'leather') + box(8.9, 9.3, 5.0, 6.0, 4.6, 5.6, 'brass')
    return p + p.mirror_y()

def canister():
    """Gas-mask tin on the left hip."""
    return cyl((-2.5, 10.6, -6), (-2.5, 10.6, 3.5), 2.7, 'steel') + cyl((-2.5, 10.6, 3.5), (-2.5, 10.6, 4.3), 2.9, 'brass')

def tunic():
    m = lathe([(8.3, 0), (8.8, 8), (9.6, 16), (9.4, 21), (7.4, 24.6), (3.9, 26.6), (3.7, 28.6)], 'tunic').scaled(.80, 1.18, 1)
    for z, r in ((6, 8.7), (11, 9.1), (16, 9.6), (21, 9.35)):
        m += sphere(.95, 'brass', 6, 4).move(.80 * r + .2, 0, z)
    return m

def pack():
    """Knapsack, bedroll across the top, shoulder straps."""
    m = box(-14.5, -6.8, -7, 7, 5.5, 21.5, 'canvas')
    m += box(-15.3, -14.5, -5.5, 5.5, 7, 14, 'canvas')                      # outer pocket
    m += cyl((-11, -10, 23.6), (-11, 10, 23.6), 3.3, 'blanket')
    for y in (-6, 6):
        m += cyl((-11, y - .7, 23.6), (-11, y + .7, 23.6), 3.6, 'leather')              # roll strap
        m += cyl((-7, y, 21), (0.5, y * 1.1, 26.2), 1.0, 'leather', seg=6)
        m += cyl((0.5, y * 1.1, 26.2), (7.0, y * 1.05, 18), 1.0, 'leather', seg=6)
    return m

def head():
    m = lathe([(3.0, -1), (3.0, 4)], 'skin', 8)
    m += ellipsoid(5.6, 5.4, 6.4, 'skin', (0.5, 0, 8.5))
    m += ellipsoid(5.0, 5.5, 5.0, 'hair', (-1.8, 0, 8.0))
    m += sphere(1.25, 'skin', 6, 4).move(6.0, 0, 7.6)                        # nose
    m += box(5.3, 6.2, -1.8, 1.8, 5.3, 6.2, 'hair')                          # moustache
    return m

def field_cap():
    m = lathe([(5.9, 11.0), (6.0, 13.4)], 'band')
    m += lathe([(6.0, 13.4), (7.4, 15.6), (7.2, 16.8), (0, 17.3)], 'tunic')
    m += ellipsoid(3.3, 4.6, .5, 'leather', (6.9, 0, 11.3)).ry(6)
    m += sphere(1.05, 'brass', 6, 4).move(6.2, 0, 13.9)
    return m.move(.3, 0, 1.3)

def steel_helmet():
    m = lathe([(8.2, 10.2), (7.2, 11.6), (6.6, 14.5), (5.0, 17.0), (0, 18.0)], 'steel', 12)
    return m.move(.3, 0, 0)

# ---- limbs (hang down -z from the joint)
def thigh():      return lathe([(4.6, -24.5), (5.0, -20), (6.3, -9), (6.1, -2), (5.0, 1.5)], 'trousers', 10)
def shin():       return lathe([(3.6, -22.5), (3.8, -17), (4.7, -9), (4.5, -2), (4.3, 1)], 'puttee', 10)
def boot():
    return (lathe([(3.8, 2.6), (4.0, 7.2)], 'boot', 8)
            + ellipsoid(6.6, 3.6, 3.0, 'boot', (2.8, 0, 3.0))
            + box(-3.6, -0.6, -2.6, 2.6, 0, 2.2, 'boot'))
def upper_arm():  return lathe([(3.4, -15.5), (3.9, -8), (4.3, -1), (3.6, 2.2)], 'tunic', 10)
def fore_arm():   return lathe([(3.0, -14), (3.5, -6), (3.5, 0.5)], 'tunic', 10) + lathe([(3.3, -14.4), (3.3, -12.4)], 'tunic', 10)
def hand():       return ellipsoid(2.5, 2.3, 2.9, 'skin', (0, 0, -.6), 8, 5)

# ---- weapons (modelled along +x). Each returns a spec: mesh, grips (hand points), muzzle, sight (height of the
# sight line over the axis), butt (x of the butt plate), bolt (hand point, bolt-actions only), port (carry position)
def carbine():
    m = beam(-16, 1.5, -4.4, 1.1, -5, 1.4, -2.0, 1.2, 'wood')                # butt stock
    m += box(-16.7, -16, -1.5, 1.5, -4.4, 1.1, 'brass')                      # butt plate
    m += box(-5, 3.2, -1.5, 1.5, -1.8, 1.6, 'steel')                         # receiver
    m += box(-1, 2.6, -1.1, 1.1, -4.4, -1.8, 'steel')                        # magazine
    m += beam(3.2, 1.35, -1.6, .5, 15.5, 1.2, -1.1, .4, 'wood')              # fore stock
    m += cyl((3.2, 0, .9), (24, 0, .9), 1.05, 'steel')                       # barrel
    m += cyl((14, 0, .1), (15.3, 0, .1), 1.9, 'brass')                       # barrel band
    m += cyl((-1.5, -1.4, 1.0), (-1.5, -3.8, .3), .6, 'steel', seg=6)        # bolt handle
    m += sphere(1.0, 'brass', 6, 4).move(-1.5, -3.9, .2)
    m += box(22.6, 23.4, -.3, .3, 1.8, 2.9, 'steel')                         # front sight
    k = 1.25                                                                 # oversized so it reads at game scale
    return dict(name='carbine', mesh=m.scaled(k), grips={'R': (-8, 0, -2), 'L': (7.5, 0, -1.5)}, muzzle=(24.5 * k, 0, .9 * k),
                sight=3.9, butt=-20.9, bolt=(-1.9, -5.2, .5), port=(10.8, 0.5, 13, 72, 38, 0))

def light_machine_gun():
    """Pan-fed light machine gun: fat cooling shroud, flat drum on top, folded bipod."""
    m = beam(-17, 1.5, -4.6, 1.0, -6, 1.4, -2.2, 1.3, 'wood')                 # butt stock
    m += box(-17.7, -17, -1.5, 1.5, -4.6, 1.0, 'steel')                       # butt plate
    m += box(-6, 5.5, -1.7, 1.7, -2.2, 1.9, 'steel')                          # receiver
    m += box(-5.4, -3.2, -1.0, 1.0, -5.6, -2.2, 'wood')                       # pistol grip
    m += cyl((1.2, 0, 1.9), (1.2, 0, 3.5), 5.4, 'steel', seg=12)              # pan magazine
    m += cyl((1.2, 0, 3.5), (1.2, 0, 4.0), 1.6, 'brass')
    m += cyl((5.5, 0, .3), (23, 0, .3), 2.3, 'shroud', seg=10)                # cooling shroud
    m += cyl((23, 0, .3), (25.5, 0, .3), 2.3, 'steel', r1=1.5, seg=10)
    m += cyl((6, 0, .3), (7.2, 0, .3), 2.6, 'brass', seg=10)
    for y in (-1.3, 1.3):
        m += cyl((19.5, y, -1.6), (9.5, y * 1.3, -3.4), .55, 'steel', seg=5)  # bipod, folded back
    m += box(21.5, 22.3, -.3, .3, 2.6, 4.2, 'steel')                          # front sight
    k = 1.15
    return dict(name='light machine gun', mesh=m.scaled(k), grips={'R': (-5, 0, -4.2), 'L': (10.5, 0, -2.6)},
                muzzle=(25.5 * k, 0, .3 * k), sight=4.9, butt=-17.7 * k, port=(11.2, 0.5, 11, 66, 26, 0), flash=1.25)

def scoped_rifle():
    """Long bolt-action rifle with a brass telescope, a cheek pad and scrim wound round the barrel."""
    m = beam(-17, 1.5, -4.6, 1.1, -5, 1.4, -2.0, 1.2, 'wood')                 # butt stock
    m += box(-13, -7, -1.6, 1.6, 1.0, 2.0, 'leather')                         # cheek pad
    m += box(-17.7, -17, -1.5, 1.5, -4.6, 1.1, 'steel')                       # butt plate
    m += box(-5, 3.5, -1.5, 1.5, -1.8, 1.6, 'steel')                          # receiver
    m += beam(3.5, 1.35, -1.6, .5, 17, 1.2, -1.1, .4, 'wood')                 # fore stock
    m += cyl((3.5, 0, .9), (32, 0, .9), .95, 'steel')                         # long barrel
    m += cyl((18, 0, .9), (26, 0, .9), 1.6, 'scrim', seg=7)                   # scrim wrap
    m += cyl((-3.5, 0, 3.6), (10, 0, 3.6), 1.15, 'brass', seg=8)              # telescope
    m += cyl((-4.6, 0, 3.6), (-3.5, 0, 3.6), 1.6, 'brass', seg=8) + cyl((10, 0, 3.6), (12, 0, 3.6), 1.7, 'brass', seg=8)
    m += box(-1.5, -.5, -.5, .5, 1.6, 2.6, 'steel') + box(6.5, 7.5, -.5, .5, 1.6, 2.6, 'steel')   # scope rings
    m += cyl((-1.5, -1.4, 1.0), (-1.5, -3.8, .3), .6, 'steel', seg=6) + sphere(1.0, 'brass', 6, 4).move(-1.5, -3.9, .2)
    k = 1.2
    return dict(name='scoped rifle', mesh=m.scaled(k), grips={'R': (-7.6, 0, -2), 'L': (9, 0, -1.6)}, muzzle=(32 * k, 0, .9 * k),
                sight=3.6 * k, butt=-17.7 * k, bolt=(-1.8, -5.0, .5), port=(11.0, 0.5, 13, 74, 42, 0), flash=1.2)

material('scrim', (112, 104, 70), 'canvas')
material('scrim2', (84, 92, 62), 'canvas')

def scrim_helmet():
    """Steel helmet under a scrim net, with ragged strips hanging from the rim."""
    m = lathe([(7.9, 10.8), (7.3, 12.0), (6.9, 14.8), (5.3, 17.3), (0, 18.3)], 'scrim', 12)
    r = np.random.default_rng(7)
    for a in np.linspace(0, 2 * math.pi, 11)[:-1]:
        if abs(a) < .5 or abs(a - 2 * math.pi) < .5: continue                 # keep the face clear
        L = r.uniform(2.5, 5.5); w = r.uniform(1.0, 1.6)
        m += box(-.4, .4, -w, w, -L, .6, 'scrim2' if r.random() < .5 else 'scrim').rz(math.degrees(a)).move(7.6 * math.cos(a), 7.6 * math.sin(a), 11.0)
    for a in (1.1, 2.6, 4.0, 5.3):
        m += ellipsoid(2.2, 1.6, 1.0, 'scrim2', (5.2 * math.cos(a), 5.2 * math.sin(a), 15.6), 6, 4)   # patches on the crown
    return m.move(.3, 0, .6)

def camo_cape():
    """Short scrim cape: a mantle over the shoulders and a panel down the back. Leaves the arms free."""
    m = lathe([(9.9, 20.5), (9.2, 24.3), (5.2, 27.0)], 'scrim').scaled(.86, 1.24, 1)
    m += beam(-9.6, 11.0, 3.0, 25.0, -7.6, 11.5, 2.0, 25.0, 'scrim').move(0, 0, 0)
    r = np.random.default_rng(3)
    for y in np.linspace(-9.5, 9.5, 7):
        m += box(-10.1, -9.4, y - 1.2, y + 1.2, r.uniform(-1.5, 2.5), 4.0, 'scrim2' if r.random() < .5 else 'scrim')  # ragged hem
    for y, z in ((-6, 18), (4, 13), (7, 21), (-2, 9)):
        m += box(-10.2, -9.5, y - 2.2, y + 2.2, z - 1.6, z + 1.6, 'scrim2')
    return m

def field_glasses():
    """Binocular case on the right hip."""
    return box(-3.5, 2.5, -12.6, -9.4, -5.5, 2.0, 'leather') + box(-2.5, 1.5, -12.9, -12.6, -1.5, .5, 'brass')

def muzzle_flash(at, size=1.0):
    f = lathe([(.6, 0), (3.4, 3.2), (0, 10)], 'flash', 7, caps=False).ry(90)
    f += sphere(2.0, 'flash_core', 6, 4)
    return f.scaled(size).move(*at)

# ---- more kit
material('helmet',  (92, 98, 84),  'metal')
material('jerkin',  (126, 92, 58), 'leather')
material('shroud',  (52, 56, 62),  'metal')

def brodie_helmet():
    """Wide-brimmed steel helmet with a chin strap."""
    m = lathe([(9.6, 11.4), (7.2, 12.3), (6.7, 14.8), (5.1, 17.2), (0, 18.2)], 'helmet', 12)
    m += lathe([(9.6, 11.0), (9.6, 11.4)], 'helmet', 12)
    m += cyl((2.5, -5.3, 11.5), (4.6, -3.2, 3.6), .45, 'leather', seg=4) + cyl((2.5, 5.3, 11.5), (4.6, 3.2, 3.6), .45, 'leather', seg=4)
    return m.move(.3, 0, .6)

def jerkin():
    """Sleeveless leather jerkin over the tunic."""
    return lathe([(8.7, 1.5), (9.3, 8), (10.1, 16), (9.9, 21), (8.0, 24.3)], 'jerkin').scaled(.82, 1.16, 1)

def drum_satchel():
    """Canvas satchel on the back with a spare pan drum strapped over it."""
    m = box(-13, -7.0, -6.5, 6.5, 5, 18, 'canvas')
    m += cyl((-13, 0, 12), (-14.8, 0, 12), 5.6, 'steel', seg=12) + cyl((-14.8, 0, 12), (-15.3, 0, 12), 1.7, 'brass')
    for y in (-5.2, 5.2):
        m += cyl((-7.5, y, 19), (0.5, y * 1.2, 26.0), 1.0, 'leather', seg=6)
        m += cyl((0.5, y * 1.2, 26.0), (7.4, y * 1.1, 18), 1.0, 'leather', seg=6)
    return m

def drum_pouch():
    """Round pan-drum pouch on the left hip."""
    return cyl((-1, 9.6, -1), (-1, 12.4, -1), 5.0, 'canvas', seg=10)

# ---- infected
material('deadskin', (158, 170, 140))
material('rags',     (96, 88, 78),  'wool')
material('ragleg',   (74, 70, 66),  'wool')
material('gore',     (122, 30, 26))
material('socket',   (30, 22, 22))
material('tracer',   (255, 244, 200), emissive=True)

def dead_head():
    m = lathe([(2.8, -1), (2.8, 4)], 'deadskin', 8)
    m += ellipsoid(5.5, 5.2, 6.6, 'deadskin', (0.5, 0, 8.8))
    m += ellipsoid(4.6, 5.3, 3.6, 'hair', (-1.8, 0, 11.6))                    # what is left of the hair
    for y in (-2.3, 2.3):
        m += sphere(1.5, 'socket', 6, 4).move(5.0, y, 9.6)                    # eye sockets
    m += box(4.6, 6.2, -2.2, 2.2, 3.6, 5.8, 'socket')                         # hanging jaw
    m += box(3.0, 5.2, -5.4, -3.6, 5.0, 9.5, 'gore')                          # torn cheek
    return m

def rag_tunic():
    m = lathe([(8.0, 0), (8.6, 8), (9.4, 16), (9.2, 21), (7.2, 24.6), (3.6, 26.6), (3.4, 28.2)], 'rags').scaled(.80, 1.15, 1)
    m += box(5.4, 7.9, -5.5, 1.5, 9, 17, 'gore')                              # chest wound
    m += box(-7.9, -5.6, 1, 6, 12, 19, 'gore')
    return m

def rag_skirt():
    return lathe([(7.4, -9), (8.6, -4), (8.6, 1), (8.1, 6)], 'rags').scaled(.84, 1.06, 1)

def claw():      return ellipsoid(2.7, 2.4, 3.8, 'deadskin', (0, 0, -1.6), 8, 5)
def bare_foot(): return ellipsoid(6.0, 3.2, 2.4, 'deadskin', (2.6, 0, 2.4)) + lathe([(3.0, 2.4), (3.3, 7)], 'deadskin', 8)

# ---- flame trooper
material('hazard',  (170, 136, 44), 'metal')
material('hide',    (86, 70, 54),  'leather')
material('tank',    (120, 54, 40), 'metal')
material('lens',    (196, 226, 214), emissive=True)
material('pilot',   (255, 170, 60), emissive=True)
material('mask',    (70, 74, 64),  'leather')

def flame_gun():
    """Flame wand: fat fuel valve, long nozzle with a heat shield and a lit pilot at the tip."""
    m = box(-14, -5, -1.6, 1.6, -4, 1.4, 'hide')                              # shoulder pad
    m += cyl((-5, 0, 0), (3, 0, 0), 2.8, 'brass', seg=10)                     # valve body
    m += cyl((-1, 0, 2.8), (-1, 0, 5.2), 1.7, 'steel', seg=8)                 # valve wheel stem
    m += cyl((-1, 0, 5.2), (-1, 0, 5.9), 3.2, 'brass', seg=10)
    m += cyl((3, 0, 0), (27, 0, 0), 1.25, 'steel', seg=8)                     # nozzle tube
    m += cyl((8, 0, 0), (22, 0, 0), 2.2, 'shroud', seg=10)                    # heat shield
    for x in (9, 15, 21):
        m += cyl((x, 0, 0), (x + .8, 0, 0), 2.6, 'hazard', seg=10)
    m += cyl((27, 0, 0), (30.5, 0, 0), 1.5, 'brass', r1=2.4, seg=8)
    m += sphere(1.8, 'pilot', 6, 4).move(31, 0, -.8)                          # pilot light
    k = 1.2
    return dict(name='flame gun', mesh=m.scaled(k), grips={'R': (-3, 0, -3), 'L': (14, 0, -2.2)}, muzzle=(31.5 * k, 0, 0),
                sight=5.2, butt=-14 * k, port=(11, .5, 11, 62, 18, 0), flash=2.1)

def fuel_tanks():
    """Two tall fuel bottles and a pressure sphere on a back frame, hose over the right hip."""
    m = None
    for y in (-5.6, 5.6):
        p = cyl((-12.5, y, 2), (-12.5, y, 25), 5.2, 'tank', seg=12) + sphere(5.2, 'tank', 10, 5).scaled(1, 1, .7).move(-12.5, y, 25)
        p += cyl((-12.5, y, 13), (-12.5, y, 14.4), 5.6, 'hazard', seg=12)
        m = p if m is None else m + p
    m += sphere(3.6, 'brass', 8, 5).move(-18.5, 0, 11)
    m += box(-9, -7, -10, 10, 3, 5, 'leather') + box(-9, -7, -10, 10, 21, 23, 'leather')
    for y in (-6, 6):
        m += cyl((-7.5, y, 21), (0.5, y * 1.15, 26.2), 1.0, 'leather', seg=6) + cyl((0.5, y * 1.15, 26.2), (7.2, y * 1.05, 18), 1.0, 'leather', seg=6)
    return m

def fuel_hose():
    p = [(-14, -9, 4), (-12, -14, -3), (-3, -14, -2), (4, -11, 5)]
    m = None
    for a, b in zip(p, p[1:]):
        s = cyl(a, b, 1.1, 'hose2', seg=5); m = s if m is None else m + s
    return m
material('hose2', (40, 36, 34), 'leather')

def gas_hood():
    """Leather hood and gas mask with two round lenses and a filter snout, steel skull cap above."""
    m = ellipsoid(6.6, 6.4, 7.6, 'hide', (.4, 0, 8.6))
    m += lathe([(7.4, 11.6), (7, 13), (5.6, 16.6), (0, 18)], 'helmet', 12).move(.3, 0, .2)
    for y in (-2.9, 2.9):
        m += cyl((5.2, y, 9.6), (7.2, y, 9.6), 2.7, 'brass', seg=10)
        m += cyl((7.2, y, 9.6), (7.4, y, 9.6), 2.0, 'lens', seg=10)
    m += cyl((6, 0, 5.4), (11, 0, 3.6), 2.9, 'mask', r1=2.4, seg=8)
    m += cyl((11, 0, 3.6), (12, 0, 3.2), 3.0, 'hazard', seg=8)
    return m

def leather_coat():
    return lathe([(8.9, 0), (9.6, 8), (10.3, 16), (10.1, 21), (8.0, 24.3)], 'hide').scaled(.82, 1.16, 1)

def coat_skirt():
    return lathe([(9.4, -19), (9.1, -10), (9.0, 1), (8.4, 6)], 'hide').scaled(.86, 1.1, 1)

# ---- other infected
material('deadskin2', (136, 150, 118))
material('rawskin',   (170, 126, 108))
material('bloat',     (154, 176, 86))
material('ooze',      (198, 232, 92), emissive=True)
material('oozedark',  (112, 142, 54))
material('flesh',     (112, 110, 92))
material('rust',      (120, 84, 56), 'metal')
material('wire',      (58, 56, 54), 'metal')

def bare_chest(mat='deadskin', sx=.8, sy=1.08):
    m = lathe([(7.4, 0), (8.0, 8), (9.2, 16), (9.0, 21), (7.0, 24.6), (3.4, 26.6), (3.2, 28.2)], mat).scaled(sx, sy, 1)
    return m

def ribs():
    m = box(6.6, 7.8, -5, -1, 8, 15, 'gore') + box(-7.7, -6.4, 1.5, 5.5, 13, 19, 'gore')
    for z in (11, 14, 17):
        m += box(6.9, 7.9, 1, 6, z, z + .9, 'hair')
    return m

def bandage_head():
    m = dead_head()
    m += lathe([(6.1, 8), (6.3, 11.2), (5.9, 12.6)], 'canvas', 10).scaled(1.02, 1.02, 1)
    m += box(-9, -6, -1.2, 1.2, 2.5, 11.6, 'canvas').ry(-20)                  # end of the bandage, flying behind
    return m

def sapper_plates():
    """Trench body armour: overlapping steel plates ringing the chest, a rivet line down the front."""
    m = lathe([(11.0, 21.5), (11.4, 24), (8.4, 27.5)], 'rust', 12).scaled(.98, 1.3, 1)
    for i, z in enumerate((2, 8, 14)):
        r = 10.2 + i * .35
        m += lathe([(r, z), (r + .9, z + 6.6)], 'rust', 14).scaled(.98, 1.3, 1)
        m += box(.98 * (r + .5) - .4, .98 * (r + .5) + .6, -1.4, 1.4, z + 2, z + 4.4, 'brass')
    return m

def big_arm(mat='deadskin2', k=1.5):
    return lathe([(3.4, -15.5), (3.9, -8), (4.3, -1), (3.6, 2.2)], mat, 10).scaled(k, k, 1)

def big_fore(mat='deadskin2', k=1.5):
    return lathe([(3.0, -14), (3.5, -6), (3.5, 0.5)], mat, 10).scaled(k, k, 1)

def sapper_helm():
    m = lathe([(9.4, 10.5), (7.8, 12), (7.1, 14.8), (5.4, 17.5), (0, 18.5)], 'rust', 12)
    m += beam(5.2, 6.5, 9.6, 17, 8.8, 7, 9.2, 15.4, 'steel')                  # bolted brow plate
    m += box(8.4, 9, -1, 1, 11, 13, 'brass')
    return m.move(.3, 0, .4)

def sapper_maul():
    """A pick fused into the right fist, drawn huge."""
    m = cyl((0, 0, -2), (0, 0, -30), 2.2, 'wood', seg=7)
    m += beam(-16, 2.4, -28, -24, 16, 2.4, -28, -24, 'rust') + box(13, 19, -3, 3, -34, -22, 'steel') + box(-19, -13, -3, 3, -34, -22, 'steel')
    m += lathe([(4.6, -6), (5.0, 0), (3.8, 5)], 'deadskin2', 8)
    return m

def gas_helm():
    m = dead_head()
    m += ellipsoid(6.4, 6.1, 5.2, 'mask', (1.5, 0, 6.2))
    for y in (-2.8, 2.8):
        m += cyl((5.6, y, 8.6), (7.6, y, 8.6), 2.9, 'brass', seg=10) + cyl((7.6, y, 8.6), (7.8, y, 8.6), 2.1, 'ooze', seg=10)
    m += cyl((6.4, 0, 4.4), (10.6, 0, 2.6), 2.8, 'mask', r1=2.4, seg=8)
    return m

def gas_sac():
    """A swollen gut of gas pushing out of the back through split canvas, glowing where it is thinnest."""
    m = ellipsoid(12.5, 13.5, 14, 'bloat', (-12, 0, 14), 12, 7)
    m += ellipsoid(6, 7.5, 7, 'ooze', (-20.6, 2, 13), 8, 5)
    m += ellipsoid(3.5, 4, 3.2, 'ooze', (-16, -9.8, 22), 6, 4)
    m += ellipsoid(4, 3, 2.6, 'oozedark', (-20, -6, 7), 6, 4)
    for z in (5, 23):
        m += lathe([(13.6, z), (13.7, z + 1.5)], 'wire', 10).scaled(.95, 1, 1).move(-12, 0, 0)
    return m

def gas_tube():
    p = [(-7, 6, 20), (2, 9, 27), (9, 5, 26), (11, 0, 24)]
    m = None
    for a, b in zip(p, p[1:]):
        s = cyl(a, b, 1.0, 'hose2', seg=5); m = s if m is None else m + s
    return m

def claw_long():
    """Long hooked fingers."""
    m = ellipsoid(2.6, 2.3, 3.4, 'rawskin', (0, 0, -1.4), 8, 5)
    for a in (-30, 0, 30):
        m += cyl((1, 0, -3.5), (5.5, 0, -11), .9, 'socket', r1=.3, seg=4).rz(a)
    return m

def grafted_corpses():
    """The Giant's torso: dead men pressed into the mass, helmets and hands showing, barbed wire round it."""
    rng = np.random.default_rng(11)
    m = None
    for a, z in ((30, 9), (80, 17), (-25, 13), (-85, 8), (150, 18), (-150, 10), (120, 8), (10, 21)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p = dead_head().rz(a).ry(rng.uniform(-14, 10)).scaled(.82).move(9.4 * ca * 1.15, 12.2 * sa * 1.1, z - 6)
        m = p if m is None else m + p
    for a, z in ((60, 13), (-60, 16), (170, 13)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        m += lathe([(5.8, 10.2), (5.1, 11.6), (4.7, 14), (0, 16.6)], 'helmet', 10).scaled(.9).move(9.4 * ca * 1.1, 12.4 * sa * 1.1, z - 4)
    for a, z, L in ((110, 20, 13), (-125, 19, 14), (40, 3, 11), (-40, 23, 12)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a)); b = np.array([10 * ca * 1.1, 13 * sa * 1.1, z])
        e = b + np.array([ca * L, sa * L, rng.uniform(-3, 8)])
        m += cyl(b, e, 2.1, 'deadskin2', r1=1.6, seg=6) + sphere(2.2, 'deadskin', 6, 4).move(*e)
    for z in (4, 10.5, 17):
        m += lathe([(14.5, z), (14.7, z + .8)], 'wire', 18).scaled(.92, 1.08, 1)
    return m

def giant_chest():
    m = lathe([(9, 0), (11, 7), (13.5, 16), (13, 22), (9, 26.4), (4, 28.2), (3.4, 29)], 'flesh', 14).scaled(.98, 1.26, 1)
    return m

def giant_pelvis():
    return lathe([(8.8, -10), (10.5, -4), (10.6, 2), (9.6, 6)], 'flesh').scaled(.96, 1.2, 1)

def thick(mesh, k):
    return mesh.scaled(k, k, 1)

# ---- colonists
material('smock',    (152, 136, 104), 'wool')
material('overalls', (82, 92, 112), 'wool')
material('workcoat', (120, 104, 86), 'wool')
material('dress',    (116, 78, 64), 'wool')
material('apron',    (198, 188, 164), 'canvas')
material('scarf',    (160, 74, 56), 'wool')
material('sacking',  (168, 148, 100), 'canvas')
material('straw',    (182, 152, 92), 'wood')

def flat_cap():
    m = lathe([(6, 11), (6.8, 13.2), (7.3, 14.8), (5, 16.2), (0, 16.7)], 'workcoat', 12)
    m += ellipsoid(4, 5.2, .6, 'leather', (6.4, 0, 11.8)).ry(8)
    return m.move(.3, 0, .8)

def headscarf():
    m = ellipsoid(6.4, 6.4, 7, 'scarf', (.1, 0, 10.0))
    m += box(-8, -5, -1.8, 1.8, 4.4, 11, 'scarf').ry(10)
    return m

def goggle_cap():
    m = lathe([(5.9, 9.8), (6.5, 13.6), (5, 16.5), (0, 17)], 'leather', 12)
    for y in (-2.4, 2.4):
        m += cyl((5.4, y, 12.2), (7.4, y, 12.2), 2.2, 'brass', seg=8)
    return m.move(.3, 0, .6)

def long_skirt():
    return lathe([(13, -46), (12.5, -28), (9.6, -8), (8.2, 3), (8.0, 6)], 'dress', 12).scaled(.92, 1.0, 1)

def apron():
    return beam(8.0, 6.6, -3, 7, 13.2, 7.2, -44, -3, 'apron')

def basket_on_arm():
    m = lathe([(7, -8), (9.6, -4), (10, 2)], 'straw', 10)
    return m.move(2, 0, -2)

def shovel_on_shoulder():
    m = cyl((14, 11.5, 30), (-20, 11.5, 34), 1.0, 'wood', seg=6)
    m += box(-26, -19, 7.5, 15.5, 32, 34.5, 'steel')
    return m

def sack_on_shoulder():
    return ellipsoid(10, 7, 6.5, 'sacking', (-3, 10.5, 32), 10, 6) + lathe([(1.4, 37.5), (1.8, 40)], 'wire', 6).move(-2, 10, 0)

def pick_on_shoulder():
    m = cyl((13, -11.5, 29), (-18, -11.5, 35), 1.0, 'wood', seg=6)
    m += beam(-30, 1.4, 31, 33.5, -8, 1.4, 34, 38, 'steel').at(RZ(0))
    return m

def tool_belt():
    return box(-3, 3, 7.4, 10.6, -7, 1, 'leather') + box(-2.4, 2.4, -10.6, -7.4, -6, 2, 'canvas')
