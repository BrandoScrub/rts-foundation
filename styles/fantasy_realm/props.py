"""Fantasy Realm: everything on the map that is not a building or a figure: trees, ore, stone, berries, relics and
the dens the wild things guard. Same engine, materials, light and scale as the buildings (160 units a tile, a storey
110), so the ground, the props, the buildings and the figures are one picture.

  python3 tools/build_props.py     -> game/art/p_<key>.png, p_<key>_s.png (cast shadow), game/art/props.json

Direction (user, Nov 17): darker, more fantasy, realistic. The realm's crystal glows cyan ('glow'); what the wild has
touched glows magenta ('bane'). Each prop's brief is its docstring; a part with no job is not there.
Several variants per kind (the game picks one per tile from a hash) so a forest is not one tree repeated.
"""
import math
import numpy as np
from artkit import shapes as sh
from artkit.core.geom import Geometry

C = 80.0          # the middle of a one-tile footprint
J = Geometry.join


def _rng(seed): return np.random.default_rng(1000 + seed)


def oak(seed=0, h=330, glow=False):
    """BROADLEAF. Is: an old forest oak. Reads as: a thick leaning trunk that forks, under a wide dark crown of
    clumps, wider than it is tall. Wood for the lumberjack. References: AoE2 oak forest; Mirkwood-dark storybook
    woods. The trunk shows (a crown sitting on the ground reads as a bush)."""
    r = _rng(seed); lean = r.uniform(-.12, .12, 2) * h
    fork = (lean[0], lean[1], h * .42)
    out = [sh.cyl((0, 0, 0), fork, h * .075, 'bark', h * .052, seg=7),
           sh.lathe([(h * .12, 0), (h * .078, h * .06)], 'bark', 7)]                                   # root flare
    tips = []
    for i in range(3):                                                                               # three boughs
        a = i * 2.1 + r.uniform(0, 1); d = h * r.uniform(.14, .22)
        tip = (fork[0] + d * math.cos(a), fork[1] + d * math.sin(a), h * r.uniform(.62, .74)); tips.append(tip)
        out.append(sh.cyl(fork, tip, h * .045, 'bark', h * .022, seg=6))
    for i in range(8):
        t = tips[i % 3]; a = r.uniform(0, 6.28); d = h * r.uniform(0, .13); rad = h * r.uniform(.15, .21)
        out.append(sh.ellipsoid(rad, rad, rad * .78, 'leaf' if i % 3 else 'leaf_dark', at=(t[0] + d * math.cos(a), t[1] + d * math.sin(a), t[2] + h * r.uniform(-.02, .16)), seg=8, rings=5))
    if glow:                                                                                         # fantasy: lantern fungus on the roots
        for i in range(4):
            a = r.uniform(0, 6.28); d = h * r.uniform(.1, .16)
            out.append(sh.cyl((d * math.cos(a), d * math.sin(a), 0), (d * math.cos(a), d * math.sin(a), 12), 2.2, 'bone', seg=5))
            out.append(sh.lathe([(7, 11), (4.5, 16), (0, 18)], 'glow', 7).move(d * math.cos(a), d * math.sin(a), 0))
    return J(out).move(C, C, 0)


def pine(seed=0, h=420):
    """CONIFER. Is: a tall black pine. Reads as: a spire of drooping tiers, twice as tall as wide, bare trunk at the
    foot. References: AoE2 pine forest; the dark firs of fairy-tale woods."""
    r = _rng(seed + 50); out = [sh.cyl((0, 0, 0), (0, 0, h * .5), h * .04, 'bark', h * .022, seg=6)]
    tiers = 5; r0 = h * r.uniform(.2, .24)
    for i in range(tiers):
        z = h * (.2 + .66 * i / tiers); rad = r0 * (1 - i / (tiers + .5)) * r.uniform(.9, 1.1)
        out.append(sh.blob_lathe([(rad, z - h * .03), (rad * .5, z + h * .1), (0, z + h * (.3 if i == tiers - 1 else .22))], 'pine' if i % 2 else 'pine_dark', seg=8).rz(r.uniform(0, 40)))
    return J(out).move(C, C, 0)


def stone_pile(seed=0):
    """STONE. Is: an outcrop of pale building stone. Reads as: big pale angular blocks, the lightest thing on the
    ground, some already split square by quarrymen. References: AoE2 stone mine (pale grey against grass)."""
    r = _rng(seed + 100); out = []
    for i in range(4):
        a = i * 1.7 + r.uniform(0, 1); d = 0 if i == 0 else r.uniform(30, 46)
        out.append(sh.rock(r.uniform(58, 80) if i == 0 else r.uniform(34, 52), 'quarry', seed=seed * 9 + i, flatten=.8).move(C + d * math.cos(a), C + d * math.sin(a), 0))
    x, y = C + 34, C + 30
    out.append(sh.block(x - 16, x + 16, y - 11, y + 11, 0, 18, 'quarry'))                              # a squared block: this is worked stone
    return J(out)


def iron_pile(seed=0):
    """IRON. Is: an outcrop of iron ore. Reads as: dark blue-black rock streaked with rust, with bright metal
    showing: clearly not stone (dark, not pale) and not crystal (no glow). References: AoE2 gold mine's role;
    real haematite and bog-iron: black and rust-red."""
    r = _rng(seed + 200); out = []
    for i in range(4):
        a = i * 1.7 + r.uniform(0, 1); d = 0 if i == 0 else r.uniform(30, 44)
        out.append(sh.rock(r.uniform(56, 74) if i == 0 else r.uniform(32, 48), 'ore_rock', seed=seed * 7 + i, flatten=.75).move(C + d * math.cos(a), C + d * math.sin(a), 0))
    for i in range(6):
        a = r.uniform(0, 6.28); d = r.uniform(8, 44)
        out.append(sh.rock(r.uniform(20, 32), 'rust' if i % 2 else 'iron', seed=seed * 5 + i + 40, flatten=.9).move(C + d * math.cos(a), C + d * math.sin(a), r.uniform(4, 22)))
    return J(out)


def crystal_pile(seed=0, mat='glow'):
    """CRYSTAL. Is: a growth of the realm's magic crystal. Reads as: a fan of tall glowing cyan spikes out of dark
    rock; the only thing on the ground that shines. References: WC3's glowing resources; quartz clusters."""
    r = _rng(seed + 300); out = [sh.rock(64, 'ore_rock', seed=seed + 3, flatten=.5).move(C, C, 0)]
    for i in range(6):
        a = i * 1.05 + r.uniform(0, .6); d = 0 if i == 0 else r.uniform(12, 32); L = r.uniform(90, 130) if i == 0 else r.uniform(44, 86); tilt = 0 if i == 0 else r.uniform(.2, .5)
        b = (C + d * math.cos(a), C + d * math.sin(a), 4); t = (b[0] + L * tilt * math.cos(a), b[1] + L * tilt * math.sin(a), L)
        m = ((b[0] + t[0]) / 2, (b[1] + t[1]) / 2, L * .78)
        out.append(sh.cyl(b, m, 10 if i == 0 else 7, mat, 9 if i == 0 else 6, seg=5)); out.append(sh.cyl(m, t, 9 if i == 0 else 6, mat, .4, seg=5))
    return J(out)


def berry_bush(seed=0):
    """BERRIES. Is: a forage bush. Reads as: a low round dark bush dotted with red, knee to waist high.
    References: AoE2 forage bush."""
    r = _rng(seed + 400); out = []
    for i in range(4):
        a = i * 1.6; d = 0 if i == 0 else 24
        out.append(sh.ellipsoid(34, 34, 26, 'leaf' if i % 2 else 'leaf_dark', at=(C + d * math.cos(a), C + d * math.sin(a), 24 + (10 if i == 0 else 0)), seg=8, rings=5))
    for i in range(16):
        a = r.uniform(0, 6.28); d = r.uniform(4, 50); z = 30 + 26 * (1 - d / 56) + r.uniform(0, 8)
        out.append(sh.sphere(5.5, 'berry', 6, 4).move(C + d * math.cos(a), C + d * math.sin(a), z))
    return J(out)


def relic():
    """ARTIFACT. Is: a relic of the old realm, dropped by a cleared camp. Reads as: a small carved stone with a
    golden light over it; nothing else is gold. References: AoE2 relic; WC3 item drops."""
    out = [sh.prism(22, 10, 'stone', 6).move(C, C, 0), sh.prism(13, 30, 'stone', 6).move(C, C, 10),
           sh.cyl((C, C, 52), (C, C, 66), 11, 'relic', 11, seg=6), sh.cyl((C, C, 66), (C, C, 80), 11, 'relic', .5, seg=6), sh.cyl((C, C, 52), (C, C, 44), 11, 'relic', .5, seg=6)]
    return J(out)


def _totem(x, y, h=150):
    return J([sh.cyl((x, y, 0), (x, y, h), 7, 'bark', 5, seg=6), sh.sphere(13, 'bone', 7, 5).move(x, y, h + 8),
              sh.cyl((x - 22, y, h - 26), (x + 22, y, h - 26), 4, 'bone', seg=5), sh.cyl((x, y, h + 18), (x + 4, y, h + 52), 8, 'bane', .4, seg=5)])


def wolf_den():
    """WOLF DEN. Is: the lair the dire wolves guard. Reads as: a mound of dark rock with a black mouth, gnawed bones
    and one sour shard. 2x2 tiles, dressing only (walked over). References: WC3 creep camps: a landmark per camp."""
    c = 160; out = [sh.rock(230, 'ore_rock', seed=11, flatten=.62).move(c - 20, c - 20, 0), sh.rock(120, 'ore_rock', seed=12, flatten=.7).move(c + 70, c - 50, 0),
                    sh.rock(100, 'ore_rock', seed=13, flatten=.7).move(c - 60, c + 70, 0),
                    sh.ellipsoid(34, 44, 40, 'dark', at=(c + 62, c + 44, 20), seg=8, rings=5)]                # the mouth, on the faces the camera sees
    for i, (x, y, a) in enumerate(((c + 110, c + 90, .4), (c + 60, c + 120, 2.0), (c + 120, c + 30, 1.1))):
        out.append(sh.cyl((x, y, 4), (x + 30 * math.cos(a), y + 30 * math.sin(a), 6), 3.4, 'bone', seg=5))
    out.append(sh.sphere(10, 'bone', 7, 5).move(c + 96, c + 112, 8))
    out.append(sh.cyl((c - 30, c - 30, 120), (c - 22, c - 26, 190), 12, 'bane', .5, seg=5))
    return J(out)


def goblin_post():
    """GOBLIN OUTPOST. Is: a raiders' camp. Reads as: two crooked hide tents, a ring of stakes, a skull totem with a
    sour shard, a fire. 2x2 tiles, dressing only. References: WC3 creep camps; orc and goblin camps of fantasy."""
    c = 160; out = []
    for x, y, w, h in ((c - 50, c - 40, 120, 130), (c + 50, c - 70, 96, 104)):
        out.append(sh.pyramid(w, w, h, 'hide').move(x - w / 2, y - w / 2, 0))
        out.append(sh.cyl((x, y, h - 14), (x + 6, y - 4, h + 26), 3, 'bark', seg=5)); out.append(sh.block(x + w * .30, x + w * .34, y - 16, y + 16, 0, h * .42, 'dark').move(4, 0, 0))
    for i in range(7):
        a = -.6 + i * .52; x, y = c + 130 * math.cos(a), c + 130 * math.sin(a)
        out.append(sh.lathe([(8, 0), (8, 56), (0, 78)], 'bark', 6).move(x, y, 0))
    out.append(_totem(c + 70, c + 60))
    out.append(sh.rock(34, 'stone', seed=5, flatten=.5).move(c - 10, c + 70, 0)); out.append(sh.cyl((c - 10, c + 70, 8), (c - 10, c + 70, 34), 9, 'ember', .5, seg=5))
    return J(out)


def ogre_lair(k=1.0):
    """OGRE LAIR. Is: an ogre's hall. Reads as: a great hut of giant ribs and hide, twice a man's height, skull
    totems either side, a cauldron glowing in front. 2x2 tiles (the Stronghold: larger), dressing only.
    References: WC3 ogre mounds; mammoth-bone huts."""
    c = 160; out = [sh.dome(120, 'hide', 12, 5).scaled(1, 1, 1.05).move(c - 20, c - 20, 0)]
    for i in range(7):
        a = i * math.pi * 2 / 7; x, y = c - 20 + 124 * math.cos(a), c - 20 + 124 * math.sin(a)
        out.append(sh.cyl((x, y, 0), (c - 20 + 70 * math.cos(a), c - 20 + 70 * math.sin(a), 120), 9, 'bone', 6, seg=6))
        out.append(sh.cyl((c - 20 + 70 * math.cos(a), c - 20 + 70 * math.sin(a), 120), (c - 20 + 20 * math.cos(a), c - 20 + 20 * math.sin(a), 176), 6, 'bone', 2, seg=6))
    out.append(sh.ellipsoid(40, 40, 62, 'dark', at=(c + 66, c + 66, 30), seg=8, rings=5))             # doorway
    out.append(_totem(c + 140, c + 10, 170)); out.append(_totem(c + 10, c + 140, 170))
    out.append(sh.lathe([(20, 0), (30, 16), (26, 34)], 'iron', 8).move(c + 120, c + 120, 0)); out.append(sh.cyl((c + 120, c + 120, 30), (c + 120, c + 120, 40), 22, 'bane', 20, seg=8))
    g = J(out)
    return g if k == 1.0 else g.move(-c, -c, 0).scaled(k).move(c, c, 0)


# key -> (builder, footprint)
T1, T2 = (160, 160), (320, 320)
CATALOG = {
    'tree_0': (lambda: oak(0), T1), 'tree_1': (lambda: oak(1, 300), T1), 'tree_2': (lambda: oak(2, 350, glow=True), T1),
    'tree_3': (lambda: pine(0), T1), 'tree_4': (lambda: pine(1, 380), T1), 'tree_5': (lambda: pine(2, 450), T1),
    'stone_0': (lambda: stone_pile(0), T1), 'stone_1': (lambda: stone_pile(1), T1), 'stone_2': (lambda: stone_pile(2), T1),
    'iron_0': (lambda: iron_pile(0), T1), 'iron_1': (lambda: iron_pile(1), T1), 'iron_2': (lambda: iron_pile(2), T1),
    'crystal_0': (lambda: crystal_pile(0), T1), 'crystal_1': (lambda: crystal_pile(1), T1), 'crystal_2': (lambda: crystal_pile(2), T1),
    'berry_0': (lambda: berry_bush(0), T1), 'berry_1': (lambda: berry_bush(1), T1),
    'relic': (relic, T1),
    'camp_wolf_den': (wolf_den, T2), 'camp_goblin_post': (goblin_post, T2), 'camp_ogre_lair': (ogre_lair, T2), 'camp_ogre_hold': (lambda: ogre_lair(1.25), T2),
}
