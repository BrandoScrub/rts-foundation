"""RTS Foundation's first figures, built on artkit's jointed biped (artkit/DESIGN_METHOD.md: brief first, every part
with a reason; the reason is each attach's label). A person stands 100 units. Parts are in the local frame of the
bone they go on (x forward, y left, z up; limbs hang down -z).

Look (user, Nov 17): darker, more fantasy, realistic; figures drawn oversized for visibility.

PEASANT. Is: a farmhand of the realm. Does: gathers, builds, repairs. Gameplay: the most numerous unit; must read
as "worker" at 30 px: a wide straw hat (the lightest shape on it), a tunic in the player colour, a tool in the hand.
References: AoE2 Villager (task shown by what is carried); labourers in the Luttrell Psalter (short tunic, hose,
straw hat). Moves: walks; swings the tool from the shoulder (the same swing chops, mines and hammers).

MILITIA. Is: a levy with a sword and a round shield. Does: front-line infantry; carries artifacts. Gameplay: must
read as "armed" against the Peasant: the shield disc on the left arm is the biggest shape, an iron cap, the
quilted coat in the player colour. References: AoE2 Militia; the fyrd in the Bayeux Tapestry.

MAN-AT-ARMS (the Militia after its upgrade). The player must SEE the research: mail (a dark steel value block
instead of cloth), a taller helm with a nasal, a kite shield in the player colour. References: AoE2 Man-at-Arms;
Norman foot in the Bayeux Tapestry.
"""
import math
from artkit.figure import Biped, material
from artkit.parts.biped_clips import build_clips, s2, c2
from artkit.shapes import blob_lathe as lathe, slab as box, sphere, ellipsoid, cyl

# ---- materials: dark, earthy; 'fr_team' is replaced with each player's colour by tools/build_units.py
material('fr_team', (70, 96, 150), 'wool')
material('fr_team_dark', (50, 70, 110), 'wool')
material('fr_hose', (74, 60, 44), 'wool')
material('fr_skin', (188, 142, 108))
material('fr_hair', (52, 38, 28))
material('fr_leather', (78, 52, 34), 'leather')
material('fr_boot', (40, 32, 28), 'leather')
material('fr_wood', (104, 72, 44), 'wood')
material('fr_steel', (150, 154, 160), 'metal')
material('fr_iron', (84, 88, 96), 'metal')
material('fr_mail', (104, 108, 116), 'wrap')
material('fr_straw', (196, 170, 104), 'canvas')
material('fr_linen', (176, 164, 138), 'canvas')


# ---- body parts shared by every person of the realm
def head(beard=False):
    m = lathe([(3.0, -1), (3.0, 4)], 'fr_skin', 8) + ellipsoid(5.6, 5.4, 6.4, 'fr_skin', (0.5, 0, 8.5)) + ellipsoid(5.0, 5.5, 5.0, 'fr_hair', (-1.8, 0, 8.0))
    m += sphere(1.25, 'fr_skin', 6, 4).move(6.0, 0, 7.6)
    if beard: m += ellipsoid(3.2, 4.4, 3.4, 'fr_hair', (3.6, 0, 4.2))
    return m

def torso(mat, belt='fr_leather'):
    m = lathe([(8.3, 0), (8.8, 8), (9.6, 16), (9.4, 21), (7.4, 24.6), (3.9, 26.6), (3.7, 28.6)], mat).scaled(.80, 1.18, 1)
    return m + lathe([(8.6, 0.5), (8.6, 3.4)], belt).scaled(.82, 1.2, 1)

def skirt(mat, long=0.0):
    return lathe([(10.4 + long * .3, -14 - long), (9.8, -6), (9.0, 1), (8.4, 6)], mat).scaled(.86, 1.1, 1)

def thigh(mat='fr_hose'):   return lathe([(4.6, -24.5), (5.0, -20), (6.3, -9), (6.1, -2), (5.0, 1.5)], mat, 10)
def shin(mat='fr_hose'):    return lathe([(3.6, -22.5), (3.8, -17), (4.7, -9), (4.5, -2), (4.3, 1)], mat, 10)
def shoe(mat='fr_boot'):    return lathe([(3.8, 2.6), (4.0, 7.2)], mat, 8) + ellipsoid(6.6, 3.6, 3.0, mat, (2.8, 0, 3.0)) + box(-3.6, -0.6, -2.6, 2.6, 0, 2.2, mat)
def upper_arm(mat):         return lathe([(3.4, -15.5), (3.9, -8), (4.3, -1), (3.6, 2.2)], mat, 10)
def fore_arm(mat):          return lathe([(3.0, -14), (3.5, -6), (3.5, 0.5)], mat, 10)
def hand():                 return ellipsoid(2.5, 2.3, 2.9, 'fr_skin', (0, 0, -.6), 8, 5)

def straw_hat():
    return lathe([(13.5, 11.2), (6.4, 12.6), (5.6, 16.6), (0, 17.6)], 'fr_straw', 12).move(.3, 0, 0)

def iron_cap():
    return lathe([(6.9, 9.6), (6.6, 13.5), (5.0, 16.6), (0, 17.8)], 'fr_iron', 12).move(.3, 0, 0) + lathe([(7.4, 9.2), (7.4, 10.4)], 'fr_iron', 12).move(.3, 0, 0)

def nasal_helm():
    m = lathe([(6.9, 8.6), (6.7, 13.5), (4.6, 18.4), (0, 21.4)], 'fr_steel', 12).move(.3, 0, 0)
    return m + box(5.9, 7.3, -1.0, 1.0, 4.6, 10.0, 'fr_steel') + lathe([(7.0, 2.5), (7.4, 8.8)], 'fr_mail', 10).move(-1.2, 0, 0)   # nasal bar; mail coif over the neck

# tools and weapons: held in the right fist, modelled in the hand's frame (the forearm runs along z)
def axe():
    return cyl((0, 0, -1), (22, 0, 6), 1.0, 'fr_wood', seg=6) + box(17, 24, -.9, .9, 2, 11, 'fr_iron')

def blade(length=30):
    """Sword along the fist's forward axis, tipped a little up."""
    m = cyl((-3, 0, -1.4), (3, 0, 0), 1.0, 'fr_leather', seg=6) + box(2.6, 4.0, -4.4, 4.4, -1.0, 1.0, 'fr_iron')
    return m + cyl((4, 0, 0), (4 + length, 0, length * .25), 1.5, 'fr_steel', r1=.5, seg=4)

def round_shield():
    """On the left forearm, face outward (+y)."""
    m = cyl((0, 3.2, -8), (0, 5.0, -8), 12.5, 'fr_wood', seg=12) + cyl((0, 5.0, -8), (0, 5.6, -8), 10.5, 'fr_team', seg=12)
    return m + sphere(2.6, 'fr_iron', 8, 5).move(0, 6.0, -8)

def kite_shield():
    m = box(-8.5, 8.5, 3.4, 5.0, -4, 6, 'fr_team') + box(-6.5, 6.5, 3.4, 5.0, -14, -4, 'fr_team') + box(-3.5, 3.5, 3.4, 5.0, -22, -14, 'fr_team')
    return m + box(-1.2, 1.2, 5.0, 5.7, -20, 5, 'fr_steel') + box(-7.5, 7.5, 5.0, 5.7, -1.2, 1.2, 'fr_steel')


def person(name, tunic, sleeve, bare_forearm, headgear, long_skirt=0.0, legs='fr_hose', beard=False):
    u = Biped(name)
    u.attach('pelvis', skirt(tunic, long_skirt), 'skirt of the tunic: hides the hip joint, carries the body colour down')
    u.attach('chest', torso(tunic), 'the body: the largest block of colour, so it carries who owns the unit')
    u.attach('head', head(beard), 'head: skin tone tells a person from a monster')
    u.attach('head', headgear[0], headgear[1])
    u.attach_pair('thigh', thigh(legs), 'thigh'); u.attach_pair('shin', shin(legs), 'shin'); u.attach_pair('foot', shoe(), 'shoe: dark feet anchor the figure on the ground')
    u.attach_pair('upper_arm', upper_arm(sleeve), 'sleeve')
    u.attach_pair('fore_arm', fore_arm('fr_skin' if bare_forearm else sleeve), 'forearm')
    u.attach_pair('hand', hand(), 'hand')
    return u


def peasant():
    u = person('peasant', 'fr_team', 'fr_team', True, (straw_hat(), 'wide straw hat: the lightest, widest shape, the mark of a worker at any size'))
    u.attach('hand_R', axe(), 'the tool: what a peasant does is shown by what is in the hand')
    return u

def militia():
    u = person('militia', 'fr_team', 'fr_team', False, (iron_cap(), 'iron cap: a soldier, but a poor one'), long_skirt=3)
    u.attach('hand_R', blade(26), 'short sword: armed')
    u.attach('fore_arm_L', round_shield(), 'round shield on the left arm: the biggest shape, in the player colour, tells it from a peasant')
    return u

def man_at_arms():
    u = person('man_at_arms', 'fr_mail', 'fr_mail', False, (nasal_helm(), 'tall helm with a nasal and a mail coif: the upgrade is visible in the outline'), long_skirt=6, beard=True)
    u.attach('chest', lathe([(8.9, 14), (9.9, 17), (9.6, 21.5), (7.6, 24.8)], 'fr_team').scaled(.80, 1.18, 1), 'a short mantle in the player colour over the mail: mail alone would hide whose soldier it is')
    u.attach('hand_R', blade(32), 'long sword')
    u.attach('fore_arm_L', kite_shield(), 'kite shield in the player colour: longer than the round shield, covers the leg')
    return u


def clips(u, heavy=False):
    """Walk, strike and idle. The same strike serves a soldier's cut and a peasant's chop."""
    sway = 1.6 if heavy else 2.2
    def walk(t, G):
        return dict(pelvis=(0, sway * s2(t), -2.0 + 1.0 * c2(2 * t)), pelvis_rot=(5 * c2(t), 4, 3 * s2(t)),
                    chest_rot=(-7 * c2(t), 6, 3 * s2(t + .15)), head_rot=(3 * s2(t), -4, 0),
                    foot_L=G.foot(t, 6), foot_R=G.foot(t + .5, -6),
                    hand_L=(6 + 7 * c2(t), 15, 4 + 2 * s2(t)), hand_R=(12 - 7 * c2(t), -15, 6 + 2 * s2(t)))
    cl, poses, info = build_clips(u, dict(elbow_L=(-.4, 1, -.6), elbow_R=(-.4, -1, -.6), hand_L=(8, 14, 6), hand_R=(12, -14, 8)),
                       dict(front=14, back=-20, stance=.56, lift=5.5, strike=-12, toe=26), walk,
                       [(.40, dict(pelvis=(-2, 0, -2), chest_rot=(-24, -10, 0), hand_R=(-2, -17, 40), hand_L=(12, 14, 12))),
                        (.62, dict(pelvis=(5, 0, -6), chest_rot=(20, 22, 0), hand_R=(26, -8, 2)))], frames=8, fps=10)
    return {c.name: c for c in cl}, poses['base']


CATALOG = {'villager': (peasant, False), 'militia': (militia, False), 'militia_maa': (man_at_arms, True)}
