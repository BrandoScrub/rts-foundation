"""RTS Foundation's figures, built on artkit's jointed biped (artkit/DESIGN_METHOD.md: brief first, every part with
a reason; the reason is each attach's label). A human stands 100 units. Parts are in the local frame of the bone
they go on (x forward, y left, z up; limbs hang down -z).

Look (user, Nov 17): darker, realistic materials, but FANTASY rather than medieval: each race has its own build and
an exaggerated signature (hat, horns, ears, cape), and the realm's crystal glows on its weapons. Figures are drawn
oversized for visibility.

PEASANT (human). Does: gathers, builds, repairs. Reads as: a tall bent pointed hat with a wide brim (storybook, not
a farm hat), tunic in the player colour, tool in hand. References: AoE2 Villager (the task is what is carried);
fairy-tale woodcutters and gnome hats (the bent point).
MILITIA (human). Reads as: a deep cowl in the player colour, a round shield with a glowing crystal boss, a broad
cleaver-like falchion. References: AoE2 Militia; hooded rangers and town watch of fantasy illustration.
MAN-AT-ARMS (the Militia's upgrade, so the research must show). Reads as: winged helm with a tall plume, cape and
big pauldrons, kite shield with a crystal, long sword. References: AoE2 Man-at-Arms; Warcraft footmen (the idea of
oversized shoulders and one bold colour, not the design).
DWARF PIKEMAN. Does: stops cavalry. Reads as: half as tall again as wide: short legs, barrel body, horned helm, a
huge red beard, and a pike three times its height with a crystal blade. References: AoE2 Spearman; Norse dwarfs.
ELF ARCHER. Reads as: the tallest and thinnest figure, long pale hair and long ears, hooded forest cloak, a bow as
tall as itself with glowing tips, a quiver. References: AoE2 Archer; Tolkien-tradition wood elves.
HALFLING SLINGER. Reads as: the smallest figure, curly head, bare feet, a pack with a cooking pot bigger than its
back, a sling. References: AoE2 Skirmisher; hobbits.
GOBLIN RAIDER (creep). Reads as: small, hunched, green, big ears, a bone-tipped spear, no player colour.
OGRE BRUTE (creep). Reads as: twice a human, huge shoulders and belly, small head with tusks, a tree-trunk club.
"""
import math
from artkit.figure import Biped, material
from artkit.parts.biped_clips import build_clips, s2, c2
from artkit.shapes import blob_lathe as lathe, slab as box, sphere, ellipsoid, cyl

# ---- materials: dark, earthy; 'fr_team*' are replaced with each player's colour by tools/build_units.py
material('fr_team', (70, 96, 150), 'wool')
material('fr_team_dark', (50, 70, 110), 'wool')
material('fr_hose', (66, 54, 40), 'wool')
material('fr_skin', (188, 142, 108))
material('fr_skin_pale', (214, 190, 168))
material('fr_gob', (188, 190, 96))       # sallow yellow-green: a grass-green goblin on grass is camouflage
material('fr_ogre', (132, 128, 96))
material('fr_hair', (52, 38, 28))
material('fr_hair_red', (150, 66, 28))
material('fr_hair_pale', (214, 204, 170))
material('fr_leather', (72, 48, 32), 'leather')
material('fr_fur', (92, 72, 50), 'leather')
material('fr_boot', (36, 30, 26), 'leather')
material('fr_wood', (96, 66, 40), 'wood')
material('fr_steel', (150, 154, 162), 'metal')
material('fr_iron', (78, 82, 92), 'metal')
material('fr_mail', (98, 102, 112), 'wrap')
material('fr_cloak', (44, 70, 46), 'wool')
material('fr_bone', (206, 196, 168))
material('fr_glow', (120, 236, 255), emissive=True)       # the realm's crystal
material('fr_bane', (255, 70, 190), emissive=True)        # the wild's sickly glow: creeps' eyes and stolen shards
material('fr_linen', (170, 158, 132), 'canvas')
material('fr_wool', (206, 200, 184), 'wool')
material('fr_hide', (196, 150, 98), 'leather')        # a pale fawn deer
material('fr_boar', (34, 26, 24), 'leather')          # near black: the boar reads by being darker than the ground
material('fr_wolf', (168, 170, 180), 'leather')      # silver-grey: a mid-grey wolf has the same value as grass and vanishes
material('fr_wolf_dark', (60, 62, 74), 'leather')


# ---- body parts, sized for a human and stretched to each race's bones
def head(skin='fr_skin', hair='fr_hair', beard=0.0, ears=0.0, tusks=False, eyes=None, jaw=0.0, horn=False):
    m = lathe([(3.0, -1), (3.0, 4)], skin, 8) + ellipsoid(5.6, 5.4, 6.4, skin, (0.5, 0, 8.5)) + sphere(1.3, skin, 6, 4).move(6.0, 0, 7.6)
    if hair: m += ellipsoid(5.0, 5.5, 5.0, hair, (-1.8, 0, 8.0))
    if beard: m += ellipsoid(3.4 + beard, 4.8 + beard, 3.6 + beard * 3.2, hair, (3.4, 0, 4.4 - beard * 2.4))
    for sg in ((1, -1) if ears else ()):
        m += cyl((-.5, sg * 5.0, 9), (-4 - ears * .3, sg * (6 + ears), 11 + ears * .7), 1.9, skin, r1=.3, seg=5)
    if jaw: m += ellipsoid(5.4 + jaw, 5.8 + jaw, 3.6 + jaw, skin, (1.6 + jaw, 0, 4.2))
    if tusks: m += cyl((5.2 + jaw, 3.0, 4.4), (6.6 + jaw, 3.6, 10.4), 1.3, 'fr_bone', r1=.2, seg=4) + cyl((5.2 + jaw, -3.0, 4.4), (6.6 + jaw, -3.6, 10.4), 1.3, 'fr_bone', r1=.2, seg=4)
    if eyes: m += sphere(1.15, eyes, 5, 3).move(5.3, 2.2, 9.6) + sphere(1.15, eyes, 5, 3).move(5.3, -2.2, 9.6)
    if horn: m += cyl((2, 0, 14), (7, 0, 23), 2.0, 'fr_bone', r1=.2, seg=5)
    return m

def torso(mat, bx=1.0, by=1.0, belt='fr_leather'):
    m = lathe([(8.3, 0), (8.8, 8), (9.6, 16), (9.4, 21), (7.4, 24.6), (3.9, 26.6), (3.7, 28.6)], mat).scaled(.80 * bx, 1.18 * by, 1)
    return m + lathe([(8.6, 0.5), (8.6, 3.4)], belt).scaled(.82 * bx, 1.2 * by, 1)

def skirt(mat, long=0.0, bx=1.0, by=1.0):
    return lathe([(10.4 + long * .3, -14 - long), (9.8, -6), (9.0, 1), (8.4, 6)], mat).scaled(.86 * bx, 1.1 * by, 1)

def limb(profile, mat, length, base, thick=1.0):
    return lathe(profile, mat, 10).scaled(thick, thick, length / base)

def thigh(mat, L=24.0, t=1.0):     return limb([(4.6, -24.5), (5.0, -20), (6.3, -9), (6.1, -2), (5.0, 1.5)], mat, L, 24.0, t)
def shin(mat, L=22.0, t=1.0):      return limb([(3.6, -22.5), (3.8, -17), (4.7, -9), (4.5, -2), (4.3, 1)], mat, L, 22.0, t)
def shoe(mat='fr_boot', k=1.0):    return (lathe([(3.8, 2.6), (4.0, 7.2)], mat, 8) + ellipsoid(6.6, 3.6, 3.0, mat, (2.8, 0, 3.0)) + box(-3.6, -0.6, -2.6, 2.6, 0, 2.2, mat)).scaled(k, k, 1)
def upper_arm(mat, L=15.0, t=1.0): return limb([(3.4, -15.5), (3.9, -8), (4.3, -1), (3.6, 2.2)], mat, L, 15.0, t)
def fore_arm(mat, L=14.0, t=1.0):  return limb([(3.0, -14), (3.5, -6), (3.5, 0.5)], mat, L, 14.0, t)
def hand(skin='fr_skin', k=1.0):   return ellipsoid(2.5 * k, 2.3 * k, 2.9 * k, skin, (0, 0, -.6), 8, 5)
def pauldron(mat, k=1.0):          return ellipsoid(5.6 * k, 5.8 * k, 4.6 * k, mat, (0, 0, .5))
def cape(mat, length=44, w=10):    return box(-10.6, -8.6, -w, w, 24 - length, 25, mat) + box(-10.6, -6, -w - 1, w + 1, 22, 26.5, mat)

# ---- headgear
def bent_hat(mat='fr_team_dark'):
    return (lathe([(20.5, 10.2), (7.0, 12.4), (5.2, 21), (2.8, 31)], mat, 12) + cyl((0, 0, 30), (-8, 0, 38), 2.8, mat, r1=1.4, seg=6) + cyl((-8, 0, 38), (-15, 0, 33), 1.4, mat, r1=.3, seg=6)
            + lathe([(7.1, 12.3), (7.1, 14.4)], 'fr_leather', 12) + sphere(1.9, 'fr_glow', 6, 4).move(7.2, 0, 13.4)).move(.3, 0, 0)

def cowl(mat='fr_team'):
    return (ellipsoid(7.2, 7.0, 7.8, mat, (-1.4, 0, 9.2)) + cyl((-3, 0, 16), (-10, 0, 19), 3.4, mat, r1=1.6, seg=6) + cyl((-10, 0, 19), (-17, 0, 10), 1.6, mat, r1=.3, seg=6)
            + lathe([(8.6, -1.5), (6.4, 3.5)], mat, 10) + box(4.6, 6.6, -3.4, 3.4, 5.2, 9.6, 'fr_iron'))        # a long liripipe; an iron face-plate with a slit of shadow

def winged_helm():
    m = lathe([(6.9, 8.6), (6.7, 13.5), (4.6, 18.4), (0, 20.6)], 'fr_steel', 12).move(.3, 0, 0) + box(5.9, 7.3, -1.0, 1.0, 4.6, 10.0, 'fr_steel')
    m += lathe([(7.0, 2.5), (7.4, 8.8)], 'fr_mail', 10).move(-1.2, 0, 0)
    for sg in (1, -1):                                                              # swept wings, thick enough to read
        m += cyl((0, sg * 6.6, 12), (-5, sg * 9.5, 27), 2.6, 'fr_steel', r1=1.6, seg=5) + cyl((-5, sg * 9.5, 27), (-12, sg * 11, 34), 1.6, 'fr_steel', r1=.3, seg=5)
        m += cyl((-1, sg * 7.2, 11), (-9, sg * 10.5, 22), 2.0, 'fr_steel', r1=.3, seg=5)
    m += sphere(1.7, 'fr_glow', 6, 4).move(7.0, 0, 13.6)                                # crystal on the brow
    return m + cyl((0, 0, 20), (-6, 0, 38), 3.0, 'fr_team', r1=1.6, seg=6) + cyl((-6, 0, 38), (-16, 0, 30), 2.6, 'fr_team', r1=.4, seg=6)   # tall plume

def horned_helm():
    m = lathe([(7.2, 8.4), (7.0, 13.0), (5.2, 16.4), (0, 17.6)], 'fr_iron', 12).move(.3, 0, 0) + box(5.9, 7.4, -1.1, 1.1, 5.0, 10.0, 'fr_iron')
    for sg in (1, -1):
        m += cyl((0, sg * 6.4, 13), (0, sg * 14.5, 14), 2.8, 'fr_bone', r1=2.0, seg=6) + cyl((0, sg * 14.5, 14), (2, sg * 18, 27), 2.0, 'fr_bone', r1=.2, seg=6)
    return m + sphere(1.8, 'fr_glow', 6, 4).move(7.2, 0, 12.6)                         # a rune-stone set in the brow

def elf_hood():
    m = ellipsoid(6.6, 6.4, 7.0, 'fr_cloak', (-1.6, 0, 9.4)) + cyl((-4, 0, 15), (-11, 0, 15), 2.6, 'fr_cloak', r1=.4, seg=6)
    m += lathe([(6.1, 11.6), (6.1, 12.8)], 'fr_steel', 10).move(1.0, 0, 0) + sphere(1.5, 'fr_glow', 6, 4).move(6.6, 0, 12.4)                     # circlet with a crystal
    for sg in (1, -1): m += cyl((-1, sg * 5.2, 14), (-5, sg * 8.5, 25), 1.1, 'fr_bone', r1=.3, seg=4) + cyl((-3, sg * 6.8, 19.5), (-1, sg * 11, 24), .8, 'fr_bone', r1=.2, seg=4)   # antlers
    return m

# ---- things carried. Tools and one-handed weapons sit in the right fist (hand frame); shields on the left forearm;
# long weapons are fixed to the chest frame and the hands reach to them, so they stay steady as the figure moves.
def axe():
    return cyl((-2, 0, -2), (30, 0, 9), 1.3, 'fr_wood', seg=6) + box(21, 34, -1.1, 1.1, 0, 18, 'fr_iron') + box(33, 34.4, -1.2, 1.2, 1, 17, 'fr_steel')

def falchion():
    m = cyl((-3, 0, -1.4), (3, 0, 0), 1.0, 'fr_leather', seg=6) + box(2.6, 4.0, -4.0, 4.0, -1.0, 1.0, 'fr_iron') + sphere(1.5, 'fr_glow', 6, 4).move(-3.6, 0, -1.6)
    return (m + cyl((4, 0, 0), (26, 0, 7), 1.8, 'fr_steel', r1=4.4, seg=4) + cyl((26, 0, 7), (38, 0, 11), 4.4, 'fr_steel', r1=.5, seg=4) + cyl((8, 0, 2.2), (30, 0, 9), .8, 'fr_glow', seg=4)).ry(-48)   # carried point-up: a blade aimed at the camera vanishes

def long_sword():
    m = cyl((-4, 0, -1.6), (3, 0, 0), 1.0, 'fr_leather', seg=6) + box(2.6, 4.2, -5.2, 5.2, -1.0, 1.0, 'fr_steel') + sphere(1.6, 'fr_glow', 6, 4).move(-4.6, 0, -1.8)
    return (m + cyl((4, 0, 0), (58, 0, 14), 3.0, 'fr_steel', r1=.6, seg=4) + cyl((6, 0, 1.4), (50, 0, 12.4), 1.0, 'fr_glow', seg=4)).ry(-58)      # a greatsword with a glowing fuller, carried upright: the tallest thing on him

def round_shield():
    m = cyl((0, 3.2, -8), (0, 5.0, -8), 16.5, 'fr_wood', seg=12) + cyl((0, 5.0, -8), (0, 5.6, -8), 14.5, 'fr_team', seg=12)
    return m + sphere(3.0, 'fr_glow', 8, 5).move(0, 6.0, -8)

def kite_shield():
    m = box(-9, 9, 3.4, 5.0, -4, 7, 'fr_team') + box(-7, 7, 3.4, 5.0, -15, -4, 'fr_team') + box(-3.8, 3.8, 3.4, 5.0, -24, -15, 'fr_team')
    return m + box(-9.6, 9.6, 3.2, 5.3, 6, 8, 'fr_steel') + sphere(3.0, 'fr_glow', 8, 5).move(0, 5.6, -2)

def pike(length=150, at=(8, -15)):
    x, y = at
    m = cyl((x - 4, y, -34), (x + 4, y, length - 34), 1.3, 'fr_wood', seg=6)
    m += cyl((x + 4, y, length - 34), (x + 5.6, y, length - 2), 3.6, 'fr_glow', r1=.3, seg=4) + lathe([(2.6, 0), (2.6, 4)], 'fr_iron', 6).move(x + 3.9, y, length - 38)
    return m + cyl((x + 3.6, y - 6, length - 30), (x + 4.6, y + 6, length - 30), 1.4, 'fr_iron', seg=4)        # cross-guard under the crystal blade

def bow(at=(13, 9), half=46):
    x, y = at; m = None
    for i in range(8):                       # a recurve drawn as short straight pieces, belly toward the archer
        a0, a1 = -1 + i / 4, -1 + (i + 1) / 4
        p = lambda a: (x - 9 * a * a + 2.5 * a ** 4, y, 16 + half * a)
        seg = cyl(p(a0), p(a1), 1.25 if 1 < i < 6 else .9, 'fr_wood', seg=5); m = seg if m is None else m + seg
    m += sphere(2.0, 'fr_glow', 6, 4).move(x - 6.5, y, 16 + half) + sphere(2.0, 'fr_glow', 6, 4).move(x - 6.5, y, 16 - half)
    m += cyl((x - 6.5, y, 16 - half), (x - 6.5, y, 16 + half), .45, 'fr_glow', seg=3)             # a string of light: the bow reads from every side
    return m + cyl((x - 7, y, 16), (x + 15, y, 16), .7, 'fr_glow', seg=4) + cyl((x + 15, y, 16), (x + 22, y, 16), 2.0, 'fr_glow', r1=.2, seg=4)   # an arrow of light on the string

def quiver():
    return cyl((-9.5, -5, 2), (-11, 3, 27), 3.0, 'fr_leather', seg=6) + cyl((-11, 3, 27), (-11.6, 4.4, 33), 2.4, 'fr_bone', r1=1.2, seg=5)

def sling():
    return cyl((0, 0, -1), (9, 0, -15), .8, 'fr_leather', seg=4) + sphere(3.6, 'fr_glow', 6, 4).move(9.6, 0, -17)      # he slings crystal shards

def pot_helm():
    return lathe([(7.6, 9.2), (8.0, 15.5), (6.6, 18.6), (0, 19.4)], 'fr_iron', 10).move(.3, 0, 0) + cyl((-7.5, 0, 14), (-15, 0, 16), 1.2, 'fr_iron', seg=5)   # the cooking pot, handle behind

def bone_spear():
    return (cyl((-16, 0, -5), (34, 0, 10), 1.1, 'fr_wood', seg=5) + cyl((34, 0, 10), (48, 0, 14), 3.0, 'fr_bane', r1=.2, seg=4)).rz(-62)      # a stolen shard, gone sour

def club():
    return cyl((-4, 0, -1), (16, 0, 4), 2.0, 'fr_wood', seg=6) + cyl((16, 0, 4), (40, 0, 11), 3.0, 'fr_wood', r1=6.5, seg=7) + cyl((34, 3, 12), (37, 9, 19), 2.4, 'fr_bane', r1=.2, seg=4) + cyl((30, -3, 6), (31, -10, 2), 2.4, 'fr_bane', r1=.2, seg=4) + cyl((38, 0, 13), (44, 1, 21), 2.4, 'fr_bane', r1=.2, seg=4)


def person(name, tunic, sleeve, forearm, headgear, dims=None, skin='fr_skin', hair='fr_hair', legs='fr_hose', feet='fr_boot', long=0.0,
           bulk=(1.0, 1.0), limbs=1.0, beard=0.0, ears=0.0, tusks=False, head_k=1.0, foot_k=1.0, eyes=None, jaw=0.0, horn=False, top='same'):
    u = Biped(name, **(dims or {})); d = u.d
    u.attach('pelvis', skirt(tunic, long, *bulk), 'skirt of the tunic: hides the hip joint, carries the body colour down')
    u.attach('chest', torso(tunic if top == 'same' else top, *bulk), 'the body: the largest block of colour, so it carries who owns the unit')
    u.attach('head', head(skin, hair, beard, ears, tusks, eyes, jaw, horn).scaled(head_k), 'head: skin and hair tell the races apart')
    for mesh, why in headgear: u.attach('head', mesh.scaled(head_k), why)
    u.attach_pair('thigh', thigh(legs, d['thigh'], limbs), 'thigh'); u.attach_pair('shin', shin(legs, d['shin'], limbs), 'shin')
    u.attach_pair('foot', shoe(feet, foot_k), 'feet: dark, they anchor the figure on the ground')
    u.attach_pair('upper_arm', upper_arm(sleeve, d['upper_arm'], limbs), 'sleeve')
    u.attach_pair('fore_arm', fore_arm(forearm, d['fore_arm'], limbs), 'forearm')
    u.attach_pair('hand', hand(skin, limbs), 'hand')
    return u


def pick():
    return cyl((-2, 0, -2), (30, 0, 9), 1.3, 'fr_wood', seg=6) + cyl((27, 0, -5), (30, 0, 9), 1.9, 'fr_iron', r1=.4, seg=4).move(0, 0, 0) + cyl((30, 0, 9), (27, 0, 23), 1.9, 'fr_iron', r1=.4, seg=4)

def hammer():
    return cyl((-2, 0, -2), (24, 0, 7), 1.3, 'fr_wood', seg=6) + box(20, 30, -3.4, 3.4, 1, 13, 'fr_iron')

def hoe():
    return cyl((-12, 0, -5), (36, 0, 11), 1.1, 'fr_wood', seg=6) + box(34, 37, -4.5, 4.5, -2, 11, 'fr_iron')

TOOLS = dict(axe=axe, pick=pick, hammer=hammer, hoe=hoe)

def peasant(tool='axe'):
    u = person('peasant', 'fr_team', 'fr_team', 'fr_skin', [(bent_hat(), 'tall bent pointed hat with a wide brim: a storybook worker, the widest and tallest shape on the figure')])
    u.attach('chest', lathe([(7.5, 2), (10.5, 30), (9.5, 33)], 'fr_bone', 9).move(-15.5, 0, 0) + lathe([(10.8, 29), (10.8, 32)], 'fr_wood', 9).move(-15.5, 0, 0), 'a tall wicker pannier on the back, higher than the shoulders: the worker\'s outline, and pale so it shows')
    u.attach('hand_R', TOOLS[tool](), 'the tool: what a peasant does is shown by what is in the hand (axe for wood and meat, pick for ore and stone, hammer to build, hoe for farms and berries)')
    return u

def militia():
    u = person('militia', 'fr_leather', 'fr_leather', 'fr_iron', [(cowl(), 'deep cowl in the player colour: hooded town watch, and the colour sits on the head where it shows from every side')], long=3, top='fr_team')
    u.attach('chest', lathe([(8.9, 15), (10.2, 18), (9.8, 22), (7.6, 25)], 'fr_team').scaled(.82, 1.2, 1), 'the cowl\'s cape over the shoulders: joins hood to body')
    u.attach('hand_R', falchion(), 'a broad falchion with a crystal pommel: a cheap soldier\'s chopper, heavier than a real sword so it reads')
    u.attach('fore_arm_L', round_shield(), 'round shield with a glowing crystal boss: the biggest shape, in the player colour')
    u.idle = dict(hand_L=(10, 19, 12), hand_R=(8, -17, 14))
    return u

def man_at_arms():
    u = person('man_at_arms', 'fr_mail', 'fr_mail', 'fr_iron', [(winged_helm(), 'winged helm with a tall plume in the player colour: the upgrade shows in the outline')], long=6, beard=.6, limbs=1.08, top='fr_team')
    u.attach('chest', cape('fr_team', 54, 15), 'cape in the player colour: mail alone would hide whose soldier it is, and a cape reads from behind')
    for b in ('upper_arm_L', 'upper_arm_R'): u.attach(b, pauldron('fr_steel', 1.5) + cyl((0, 0, 3), (0, 0, 10), 1.6, 'fr_steel', r1=.2, seg=4), 'oversized spiked pauldron: heavier than the Militia at a glance')
    u.attach('hand_R', long_sword(), 'long sword with a crystal pommel')
    u.attach('fore_arm_L', kite_shield(), 'kite shield in the player colour with a crystal: covers the leg')
    u.idle = dict(hand_L=(10, 20, 10), hand_R=(6, -19, 16))
    return u

def dwarf_pikeman():
    u = person('dwarf', 'fr_team', 'fr_mail', 'fr_leather', [(horned_helm(), 'horned iron helm: the dwarf mark, wide in outline')],
               dims=dict(thigh=14.0, shin=13.0, shoulder=(0.0, 15.5, 22.0), upper_arm=13.0, fore_arm=12.0, neck=(0.0, 0.0, 26.0)),
               hair='fr_hair_red', beard=3.0, bulk=(1.3, 1.32), limbs=1.35, head_k=1.12, foot_k=1.2, long=-4)
    for b in ('upper_arm_L', 'upper_arm_R'): u.attach(b, pauldron('fr_iron', 1.5), 'broad iron shoulders: as wide as he is tall')
    u.attach('chest', pike(), 'a pike three times his height with a crystal blade: what stops cavalry, and the tallest line on the field')
    u.attach('chest', box(5, 6.2, -14.4, 4, 84, 104, 'fr_team'), 'a pennon in the player colour under the blade: his colour is high up where nothing hides it')
    u.attach('chest', cyl((-11, 0, 10), (-13, 0, 10), 13, 'fr_team', seg=10), 'a round shield slung on his back in the player colour: reads from behind')
    return u

def elf_archer():
    u = person('elf', 'fr_team', 'fr_cloak', 'fr_leather', [(elf_hood(), 'forest hood thrown back off the brow')],   # tunic in the player colour
               dims=dict(thigh=27.0, shin=25.0, shoulder=(0.0, 10.5, 25.0), upper_arm=16.0, fore_arm=15.0, neck=(0.0, 0.0, 29.0)),
               skin='fr_skin_pale', hair='fr_hair_pale', ears=5.0, bulk=(.86, .84), limbs=.84, legs='fr_cloak', long=-3)
    u.attach('head', ellipsoid(3.4, 5.4, 9.0, 'fr_hair_pale', (-4.6, 0, 3.0)), 'long pale hair down the back: an elf even from behind')
    u.attach('chest', cape('fr_team', 52, 8), 'a long cloak in the player colour: the largest block on the figure, so the archer is known from behind and from far')
    u.attach('chest', quiver(), 'quiver over the shoulder: an archer')
    u.attach('chest', bow().rz(38), 'a bow as tall as the elf with glowing tips, held half across the body so it shows from the front as well as the side: the ranged unit\'s signature')
    return u

def halfling_slinger():
    u = person('halfling', 'fr_team', 'fr_team_dark', 'fr_skin', [(pot_helm(), 'his cooking pot worn as a helmet: the joke and the outline')],
               dims=dict(thigh=20.0, shin=18.0, shoulder=(0.0, 11.5, 22.0), upper_arm=13.0, fore_arm=12.0, neck=(0.0, 0.0, 26.0)),
               hair='fr_hair', bulk=(1.12, 1.08), feet='fr_skin', foot_k=1.45, head_k=1.22, long=-5)
    u.attach('chest', box(-17, -7.5, -9, 9, 2, 26, 'fr_leather') + cyl((-19, -9, 27), (-19, 9, 27), 3.4, 'fr_fur', seg=6) + cyl((-18, 0, 4), (-18, 0, 22), 1.2, 'fr_wood', seg=4), 'a pack and bedroll bigger than his back: the tell of a halfling on the march')
    u.attach('hand_R', sling(), 'the sling and its stone')
    u.attach('fore_arm_L', cyl((0, 3.0, -7), (0, 4.6, -7), 8.5, 'fr_wood', seg=10), 'a small wicker buckler: he shrugs off arrows')
    return u

def goblin():
    u = person('goblin', 'fr_fur', 'fr_gob', 'fr_gob', [], dims=dict(thigh=20.0, shin=19.0, shoulder=(0.0, 11.0, 22.0), neck=(1.5, 0.0, 25.0)),
               skin='fr_gob', hair=None, ears=14.0, tusks=False, eyes='fr_bane', jaw=.6, legs='fr_gob', feet='fr_gob', bulk=(.95, .92), limbs=.9, head_k=1.25, foot_k=1.2, long=-6)
    u.attach('chest', box(-8.6, 8.4, -1.6, 1.6, 2, 24, 'fr_leather').rz(0), 'a strap of scavenged leather: no uniform, no player colour')
    u.attach('hand_R', bone_spear(), 'a spear tipped with a sour shard, carried crossways: a wide, low, ragged outline against the realm\'s upright ones')
    u.idle = dict(hand_R=(8, -16, 4), hand_L=(8, 14, 2), chest_rot=(0, 16, 0))
    return u

def ogre():
    u = person('ogre', 'fr_fur', 'fr_ogre', 'fr_ogre', [], dims=dict(shoulder=(0.0, 18.0, 25.0), upper_arm=17.0, fore_arm=16.0, hip_w=8.0, neck=(2.0, 0.0, 27.0)),
               skin='fr_ogre', hair=None, tusks=True, eyes='fr_bane', jaw=1.6, horn=True, legs='fr_ogre', feet='fr_ogre', bulk=(1.55, 1.6), limbs=1.75, head_k=1.3, foot_k=1.6, long=-2)
    u.attach('chest', ellipsoid(11.5, 13.5, 10, 'fr_ogre', (3.5, 0, 9)), 'the belly: weight low and forward, a brute not an athlete')
    for b in ('upper_arm_L', 'upper_arm_R'): u.attach(b, pauldron('fr_ogre', 1.7), 'slab shoulders, wider than the hips')
    u.attach('hand_R', club().scaled(1.5), 'a tree-trunk club with crystal shards beaten into it')
    return u


def clips(u, kind='strike'):
    """Idle, walk and attack. kind: 'strike' (a cut or a chop from the shoulder), 'thrust' (a long weapon fixed to the
    chest is levelled by leaning in), 'shoot' (bow arm out, string hand drawn back), 'sling' (overhead whirl)."""
    k = (u.d['thigh'] + u.d['shin']) / 46.0; sy = u.d['shoulder'][1]
    fixed = {'thrust': dict(hand_R=(8, -sy - .5, 6), hand_L=(9, -sy + 5, 20)), 'shoot': dict(hand_L=(12, 9, 16), hand_R=(6, -sy, 4))}.get(kind, {})
    def walk(t, G):
        ch = dict(pelvis=(0, 2.0 * k * s2(t), -2.0 * k + 1.0 * c2(2 * t)), pelvis_rot=(5 * c2(t), 4, 3 * s2(t)),
                  chest_rot=(-7 * c2(t) * (0.3 if fixed else 1), 6, 3 * s2(t + .15)), head_rot=(3 * s2(t), -4, 0),
                  foot_L=G.foot(t, u.d['hip_w'] + .5), foot_R=G.foot(t + .5, -u.d['hip_w'] - .5),
                  hand_L=(6 + 7 * c2(t), sy + 3, 4 + 2 * s2(t)), hand_R=(12 - 7 * c2(t), -sy - 3, 6 + 2 * s2(t)))
        ch.update(fixed); return ch
    attack = {
        'strike': [(.40, dict(pelvis=(-2, 0, -2), chest_rot=(-24, -10, 0), hand_R=(-2, -sy - 5, 40), hand_L=(12, sy + 2, 12))),
                   (.62, dict(pelvis=(5, 0, -6 * k), chest_rot=(20, 22, 0), hand_R=(26, -8, 2)))],
        'thrust': [(.35, dict(pelvis=(-3, 0, -2), chest_rot=(-8, -10, 0))), (.62, dict(pelvis=(8, 0, -3 * k), chest_rot=(0, 38, 0)))],
        'shoot':  [(.30, dict(chest_rot=(-50, 0, 0), head_rot=(50, 0, 0), hand_L=(20, 6, 18), hand_R=(14, 0, 18))),
                   (.60, dict(chest_rot=(-62, -4, 0), head_rot=(60, 0, 0), hand_L=(22, 6, 18), hand_R=(-6, -4, 19))),
                   (.72, dict(hand_R=(2, -6, 17)))],
        'sling':  [(.30, dict(chest_rot=(-20, -8, 0), hand_R=(-6, -sy - 4, 42))), (.50, dict(hand_R=(6, -sy - 8, 46))),
                   (.70, dict(pelvis=(4, 0, -4 * k), chest_rot=(16, 16, 0), hand_R=(26, -6, 22)))],
    }[kind]
    base = dict(elbow_L=(-.4, 1, -.6), elbow_R=(-.4, -1, -.6), hand_L=(8, sy + 2, 6), hand_R=(12, -sy - 2, 8)); base.update(fixed)
    cl, poses, info = build_clips(u, base, dict(front=14 * k, back=-20 * k, stance=.56, lift=5.5 * k, strike=-12, toe=26), walk, attack, frames=8, fps=10)
    return {c.name: c for c in cl}, poses['base']

def figure_clips(u, kind):
    cl, base = clips(u, kind)
    if getattr(u, 'idle', None): base = dict(base, **u.idle)        # the standing pose is the one players read: weapon and shield held clear of the body
    return {'idle': [base], 'walk': cl['walk'].poses(), 'attack': cl['attack'].poses(), 'die': cl['die'].poses()}


# ------------------------------------------------------------------ four legs (artkit.rig.Rig)
from artkit.rig import Rig

def quadruped(name, L, H, W, bh, coat, leg_r, head, tail=None, extra=None, leg_mat=None, hoof='fr_boot'):
    """A four-legged animal: a barrel body at shoulder height H, a head on a neck joint, a tail, four IK legs.
    Front knees bend forward and hind hocks back: the two silhouettes that make it read as an animal, not a table."""
    r = Rig(name); r.joint('body', 'root', (0, 0, H))
    body = ellipsoid(L * .5, W * .5, bh, coat) + ellipsoid(L * .26, W * .54, bh * 1.08, coat, (L * .24, 0, bh * .08))     # barrel and a deeper chest
    r.attach('body', body + extra if extra is not None else body)
    leg = (H - bh * .45) * .54; lm = leg_mat or coat
    for n, (sx, sy) in dict(fl=(1, 1), fr=(1, -1), bl=(-1, 1), br=(-1, -1)).items():
        thigh = cyl((0, 0, 0), (0, 0, -leg), leg_r * (1.25 if sx < 0 else 1.05), lm, leg_r * .8, seg=7)
        shin = cyl((0, 0, 0), (0, 0, -leg), leg_r * .75, lm, leg_r * .55, seg=7)
        r.leg(n, 'body', (sx * L * .34, sy * W * .36, -bh * .45), (sx * L * .36 + (-L * .06 if sx < 0 else 0), sy * W * .40), leg, leg,
              knee=((.5 if sx > 0 else -1.0), 0, .25), thigh=thigh, shin=shin, foot=ellipsoid(leg_r * 1.1, leg_r * .95, leg_r * .7, hoof, (leg_r * .3, 0, leg_r * .6)))
    r.joint('neck', 'body', (L * .44, 0, bh * .45)); r.attach('neck', head)
    if tail is not None: r.joint('tail', 'body', (-L * .48, 0, bh * .35)); r.attach('tail', tail)
    r.dims = dict(L=L, H=H, W=W)
    return r

def quad_clips(r, bite=True):
    """idle, walk (8), attack (5: rear the head, lunge, snap), die (8: stagger, fall on the side)."""
    L, H, W = r.dims['L'], r.dims['H'], r.dims['W']
    walk = r.walk(stride=L * .62, frames=8, duty=.6, lift=H * .16, bob=1.6).poses()
    if hasattr(r, 'walk_extra'): walk = [dict(p, **r.walk_extra(i)) for i, p in enumerate(walk)]
    atk = [r.pose(root=(dx, 0, dz, 0, p, 0), neck=(0, n, 0)) for dx, dz, p, n in ((0, 0, 0, 0), (-L * .08, 1, -6, -22), (L * .16, -2, 8, 26), (L * .10, -1, 4, 10), (0, 0, 0, 0))] if bite else [r.pose(neck=(0, n, 0), root=(0, 0, -z, 0, p, 0)) for n, z, p in ((0, 0, 0), (38, 1, 3), (56, 2, 5), (48, 2, 4), (58, 2, 5))]      # grazers do not fight: these frames are the head going down to crop grass
    if hasattr(r, 'atk'): atk = [r.pose(**c) for c in r.atk]
    die = []
    for i in range(8):
        u = i / 7; e = u * u * (3 - 2 * u)
        die.append(r.pose(root=(-L * .05 * e, H * .74 * e, W * .42 * e, 0, 0, 86 * e), neck=(0, 30 * e, 0)))      # the roll turns about the ground point, so slide back under it
    return {'idle': [r.pose()], 'walk': walk, 'attack': atk, 'die': die}

def beast_head(coat, size, snout, ears=1.0, eyes=None, dark=None, tusk=False, antler=False, horn=False):
    """A head that hangs forward of the neck joint: skull, a snout, ears; the eyes can glow."""
    m = cyl((-size * .9, 0, -size * .7), (size * .5, 0, size * .2), size * .95, coat, r1=size * .8, seg=8)                 # neck
    m += ellipsoid(size * 1.05, size * .9, size * .9, coat, (size * 1.0, 0, size * .45))
    m += cyl((size * 1.5, 0, size * .25), (size * (1.5 + snout), 0, size * .05), size * .58, dark or coat, r1=size * .34, seg=7)
    m += sphere(size * .2, 'fr_boot', 5, 3).move(size * (1.55 + snout), 0, size * .12)
    for sg in (1, -1):
        if ears: m += cyl((size * .6, sg * size * .6, size * 1.1), (size * .3, sg * size * (.8 + .25 * ears), size * (1.3 + .7 * ears)), size * .34, dark or coat, r1=.2, seg=4)
        if eyes: m += sphere(size * .17, eyes, 5, 3).move(size * 1.72, sg * size * .5, size * .72)
        if tusk: m += cyl((size * (1.3 + snout * .8), sg * size * .42, size * .0), (size * (1.6 + snout * .8), sg * size * .62, size * .75), size * .15, 'fr_bone', r1=.2, seg=4)
        if antler:
            m += cyl((size * .7, sg * size * .4, size * 1.2), (size * .2, sg * size * 1.3, size * 3.0), size * .14, 'fr_bone', seg=4) + cyl((size * .45, sg * size * .9, size * 2.2), (size * 1.3, sg * size * 1.5, size * 3.0), size * .11, 'fr_bone', r1=.2, seg=4)
            m += cyl((size * .2, sg * size * 1.3, size * 3.0), (-size * .5, sg * size * 1.7, size * 3.9), size * .11, 'fr_bone', r1=.2, seg=4)
        if horn: m += cyl((size * .5, sg * size * .7, size * 1.0), (size * .2, sg * size * 1.5, size * .6), size * .26, 'fr_bone', seg=5) + cyl((size * .2, sg * size * 1.5, size * .6), (size * .9, sg * size * 1.7, size * .3), size * .22, 'fr_bone', r1=.2, seg=5)
    return m

def dire_wolf(saddle=False):
    """DIRE WOLF. Is: a wolf the size of a pony. Reads as: high shoulders, a mane of dark spikes, a long snout, eyes that
    glow. References: WC3 creep wolves (bigger than life, glowing eyes); real wolves (shoulders higher than the rump)."""
    L, H, W, bh = 108, 50, 30, 15
    mane = None
    for i in range(6):
        sp = cyl((L * .34 - i * 9, 0, bh * .8), (L * .30 - i * 9 - 5, 0, bh * 1.0 + 14 - i * 1.5), 4.2, 'fr_wolf_dark', r1=.3, seg=4); mane = sp if mane is None else mane + sp
    extra = mane + ellipsoid(L * .22, W * .5, bh * .9, 'fr_wolf_dark', (L * .26, 0, bh * .5))
    if saddle: extra += box(-14, 12, -W * .56, W * .56, bh * .2, bh * 1.1, 'fr_leather') + box(-30, 22, -W * .62, W * .62, -bh * .5, bh * 1.0, 'fr_team') + box(26, 44, -W * .5, W * .5, -bh * .7, bh * .3, 'fr_team')   # a caparison in the player colour over back and chest
    head = beast_head('fr_wolf', 9.5, 1.5, ears=1.0, eyes='fr_glow' if saddle else 'fr_bane', dark='fr_wolf_dark')
    tail = cyl((0, 0, 0), (-30, 0, -6), 7.5, 'fr_wolf', r1=3.0, seg=6) + cyl((-24, 0, -5), (-40, 0, -10), 5.0, 'fr_wolf_dark', r1=.4, seg=5)      # a long brush of a tail: wolf, not boar
    return quadruped('wolf', L, H, W, bh, 'fr_wolf', 4.6, head, tail, extra, hoof='fr_wolf_dark')

def wolf_rider():
    """WOLF RIDER (the realm's light cavalry). Is: a halfling scout on a tame dire wolf, with a crystal-tipped lance.
    Reads as: the wolf's outline with a small upright rider, a pot helm and a pennon in the player colour.
    References: AoE2 Scout Cavalry (fast, light, a lance); goblin wolf-riders of fantasy, turned to the realm's side."""
    r = dire_wolf(saddle=True); r.name = 'wolf_rider'
    h = halfling_slinger_body(); cl, base = clips(h, 'strike')
    base = dict(base); base['hand_R'] = (10, -14, 10); base['hand_L'] = (12, 8, 6)
    g, _ = h.build(base, 0.0, layer='U')
    rider = g.scaled(.86).move(0, 0, -51 * .86 + 2)                                            # waist at the joint (hips are 51 up on a standing figure)
    for sg in (1, -1): rider += cyl((2, sg * 9, 6), (10, sg * 17, -12), 3.4, 'fr_hose', r1=2.6, seg=6) + ellipsoid(5, 3, 2.6, 'fr_skin', (12, sg * 17.5, -14))   # legs astride, bare feet
    r.joint('rider', 'body', (-2, 0, 15 * 1.1)); r.attach('rider', rider, 'the rider: a small upright shape over the wolf, leaning into the charge')
    r.joint('lance', 'rider', (6, -13, 12))
    r.attach('lance', cyl((0, 0, -22), (0, 0, 78), 1.3, 'fr_wood', seg=5) + cyl((0, 0, 78), (0, 0, 100), 3.2, 'fr_glow', r1=.3, seg=4) + box(.5, 30, -.6, .6, 50, 76, 'fr_team'),
             'crystal lance with a pennon: upright at rest so the outline is tall, couched level to strike')
    L = r.dims['L']                                                                             # lower the lance, lunge, hold, recover
    r.atk = [dict(), dict(root=(-L * .06, 0, 1, 0, 0, 0), rider=(0, -8, 0), lance=(0, 50, 0)), dict(root=(L * .22, 0, -2, 0, 0, 0), rider=(0, 18, 0), lance=(0, 76, 0), neck=(0, 14, 0)),
             dict(root=(L * .14, 0, -1, 0, 0, 0), rider=(0, 12, 0), lance=(0, 70, 0)), dict(lance=(0, 20, 0))]
    walk_extra = lambda i: dict(rider=(0, 5 + 3 * math.sin(i * math.pi / 2), 0), lance=(0, 8, 0))
    r.walk_extra = walk_extra
    return r

def halfling_slinger_body():
    u = person('halfling_rider', 'fr_team', 'fr_team_dark', 'fr_skin', [(pot_helm(), 'pot helm')],
               dims=dict(thigh=20.0, shin=18.0, shoulder=(0.0, 11.5, 22.0), upper_arm=13.0, fore_arm=12.0, neck=(0.0, 0.0, 26.0)),
               bulk=(1.12, 1.08), feet='fr_skin', foot_k=1.45, head_k=1.22, long=-5)
    u.attach('chest', cape('fr_team', 30), 'a short cloak streaming behind: speed')
    return u

def boar():
    """WILD BOAR. Reads as: a low dark wedge, heavy in front, a ridge of bristles, pale tusks. References: AoE2 Wild Boar."""
    L, H, W, bh = 84, 32, 34, 16
    ridge = None
    for i in range(7):
        sp = cyl((L * .36 - i * 7, 0, bh * .9), (L * .34 - i * 7 - 3, 0, bh * 1.0 + 8), 3.0, 'fr_boot', r1=.3, seg=4); ridge = sp if ridge is None else ridge + sp
    head = beast_head('fr_boar', 9.0, 1.3, ears=.5, tusk=True, eyes=None, dark='fr_boar')
    return quadruped('boar', L, H, W, bh, 'fr_boar', 4.0, head, cyl((0, 0, 0), (-8, 0, 4), 1.2, 'fr_boar', r1=.4, seg=4), ridge + ellipsoid(L * .28, W * .56, bh * 1.15, 'fr_boar', (L * .2, 0, bh * .1)))

def deer():
    """DEER (a stag). Reads as: long thin legs, a pale rump, antlers taller than its back. References: AoE2 Deer."""
    L, H, W, bh = 62, 62, 18, 10
    head = beast_head('fr_hide', 6.2, 1.2, ears=.9, antler=True).scaled(1.25)
    head = head.move(6, 0, 24) + cyl((-6, 0, -6), (8, 0, 24), 5.0, 'fr_hide', r1=4.0, seg=7)                                      # a long neck carries the head high
    return quadruped('deer', L, H, W, bh, 'fr_hide', 2.6, head, cyl((0, 0, 0), (-6, 0, 3), 2.6, 'fr_wool', r1=.6, seg=5), ellipsoid(8, W * .5, bh * .8, 'fr_wool', (-L * .42, 0, 2)))

def sheep():
    """SHEEP. Reads as: a pale woolly ball on short dark legs with a dark face and curled horns. References: AoE2 Sheep."""
    L, H, W, bh = 44, 26, 26, 13
    wool = None
    for i, (x, y, z) in enumerate(((12, 8, 5), (12, -8, 5), (-2, 9, 7), (-2, -9, 7), (-14, 6, 5), (-14, -6, 5), (4, 0, 9), (-10, 0, 9))):
        b = sphere(9.5, 'fr_wool', 7, 5).move(x, y, z); wool = b if wool is None else wool + b
    head = beast_head('fr_boot', 5.4, .9, ears=.4, horn=True)
    return quadruped('sheep', L, H, W, bh, 'fr_wool', 2.6, head, None, wool, leg_mat='fr_boot')


# game key -> (builder, attack kind ('quad' / 'graze' = four legs), whole-figure scale, players: both sides or the
# neutral one, cell box in units (half-width, up, down: wide enough for the figure lying dead), px per unit)
BOX = (88, 138, 30)
CATALOG = {
    'villager': (peasant, 'strike', .9, 'both', BOX, .6), 'villager_pick': (lambda: peasant('pick'), 'strike', .9, 'both', BOX, .6),
    'villager_hammer': (lambda: peasant('hammer'), 'strike', .9, 'both', BOX, .6), 'villager_hoe': (lambda: peasant('hoe'), 'strike', .9, 'both', BOX, .6), 'militia': (militia, 'strike', 1.0, 'both', (92, 146, 30), .6), 'militia_maa': (man_at_arms, 'strike', 1.16, 'both', (104, 176, 34), .6),
    'spearman': (dwarf_pikeman, 'thrust', 1.0, 'both', (100, 178, 30), .6), 'archer': (elf_archer, 'shoot', 1.12, 'both', (104, 162, 32), .6), 'skirmisher': (halfling_slinger, 'sling', .8, 'both', (72, 116, 26), .6),
    'scout': (wolf_rider, 'quad', 1.0, 'both', (146, 192, 64), .6),
    'goblin': (goblin, 'strike', 1.0, 'neutral', (96, 136, 30), .6), 'ogre': (ogre, 'strike', 1.65, 'neutral', (176, 226, 52), .4),
    'wolf': (dire_wolf, 'quad', .92, 'neutral', (124, 100, 60), .6), 'boar': (boar, 'quad', 1.0, 'neutral', (96, 72, 48), .6),
    'deer': (deer, 'graze', 1.0, 'neutral', (96, 150, 56), .6), 'sheep': (sheep, 'graze', 1.0, 'neutral', (60, 58, 36), .6),
}
