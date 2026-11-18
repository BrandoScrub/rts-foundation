"""Grey blockouts for RTS Foundation's first three buildings (artkit/DESIGN_METHOD.md: brief, references, big shapes,
then a blockout shown to the user before any detail). Units: a tile is 160, a person 100, a door 96, a storey 110.
The camera sees the +x and +y walls, so "front" is +y and the back corner is low x, low y: tall signatures go there
(on screen, height is z minus depth). Every part carries a one-line why; a part with no reason is cut.

  python3 -m styles.fantasy_realm.blockouts.render <out folder>
"""
from artkit import shapes as sh
from artkit.assembly import Assembly


class Block(Assembly):
    """An Assembly whose every part must say why it exists."""
    def __init__(s, brief):
        super().__init__(); s.brief = brief; s.why = {}

    def part(s, name, why, geom, tag='body', grounded=False):
        s.why[name] = why; return s.add(name, geom, grounded=grounded, tag=tag)

    def post(s, name, why, p0, p1, t=8, mat='timber', free=False, tag='detail'):
        s.why[name] = why; s.strut(name, p0, p1, t, mat, free=free, tag=tag)

    def findings(s):
        names = [n for n, *_ in s.parts] + [n for n, *_ in s.struts]
        return [f'NO REASON {n}' for n in names if not s.why.get(n)] + s.check()


def town_hall():
    b = Block({
        'is': 'Town Hall: the seat of a frontier settlement in a fantasy kingdom',
        'does': 'trains Peasants, takes in every resource, shelters 15 people, and shoots from its loopholes when they are inside',
        'gameplay': '4x4 tiles, the biggest and first building; the player must find it at a glance and see where peasants unload',
        'built': 'a stone undercroft (stores, loopholes) carries a timber hall; a stone keep at the back corner is the refuge and lookout',
        'serviced': 'one big door on the front under the unloading porch; the keep is entered from inside the hall',
        'made_of': 'fieldstone below, timber frame above, tiled roofs in the player colour',
        'faction': 'human-led realm of several races: sturdy, storybook, a little crooked; nothing ornate yet',
        'references': ['AoE2 Town Center: a central mass with open sheds where villagers drop resources',
                       'Norman hall-and-keep / medieval moot hall: stone undercroft, timber hall over it, tower for refuge',
                       'Warcraft III Human Town Hall: one tall mass and big player-coloured roofs that read at any zoom (the idea, not the look)'],
        'read_at_play_size': 'a broad hall with a big pitched roof, a square keep rising behind it, and a porch in front',
    })
    b.part('plinth', 'a levelled stone platform: spreads the load and lifts the hall out of the mud', sh.block(30, 610, 30, 626, 0, 14, 'stone'), 'base', True)
    b.part('undercroft', 'stone ground storey: the stores that every resource goes into, with loopholes to shoot from', sh.block(130, 520, 200, 520, 14, 124, 'stone'))
    b.part('hall', 'timber upper storey, set in from the stone: the meeting hall and where the garrison shelters', sh.block(140, 510, 210, 510, 124, 204, 'timber'))
    b.part('hall_roof', 'steep pitched roof (sheds rain); the largest upward face, so it carries the player colour', sh.gable(370, 300, 120, 'roof', overhang=14).move(140, 210, 204), 'roof')
    b.part('keep', 'stone keep at the back corner: the refuge and lookout; at the back so its height shows above the hall', sh.block(60, 220, 60, 220, 14, 330, 'stone'), 'signature')
    b.part('keep_gallery', 'a wider fighting gallery at the top: the overhang says "defended" and lets defenders see the foot of the wall', sh.block(50, 230, 50, 230, 330, 356, 'timber'), 'signature')
    b.part('keep_roof', 'pointed cap over the gallery; second player-colour face, makes the keep a spire in outline', sh.pyramid(200, 200, 110, 'roof').move(40, 40, 356), 'roof')
    b.part('porch_roof', 'lean-to shed along the front: where peasants unload, so the player sees the drop-off side', sh.wedge(300, 92, 40, 'roof').move(175, 520, 100), 'accent')
    for i, x in enumerate((185, 325, 465)):
        b.post(f'porch_post{i}', 'holds the porch roof up', (x, 604, 14), (x, 604, 104), 10)
    b.part('door', 'the one way in: a double door a cart could pass (a person is 100 tall)', sh.block(285, 365, 518, 524, 14, 112, 'dark'), 'opening')
    b.mark_door('door', 325, 520, 14, 'y')
    b.part('steps', 'two stone steps up to the door from the ground', sh.block(265, 385, 626, 640, 0, 7, 'stone'), 'base', True)
    b.part('chimney', 'the hall hearth: people live here; its stack marks the back of the hall', sh.block(455, 490, 225, 260, 204, 350, 'stone'), 'detail')
    b.post('flagstaff', 'a flag on the highest point shows whose town this is', (140, 140, 466), (140, 140, 540), 5, free=True, tag='accent')
    b.part('flag', 'the player colour against the sky', sh.block(142, 190, 138, 142, 506, 538, 'roof'), 'accent', True)
    b.part('loophole_x', 'arrow loop in the undercroft: where its arrows come from', sh.block(518, 524, 330, 342, 50, 96, 'dark'), 'opening')
    return b, (640, 640)


def barracks():
    b = Block({
        'is': 'Barracks: where infantry are mustered, armed and drilled',
        'does': 'trains Militia, Men-at-Arms and Dwarf Pikemen; researches their upgrades',
        'gameplay': '3x3 tiles; must not be mistaken for the Town Hall or a house: long, low and martial',
        'built': 'a long timber dormitory on a stone footing with a stone muster gate in the middle of the front',
        'serviced': 'soldiers leave through the muster gate into a fenced drill yard',
        'made_of': 'timber hall, stone gate, plank fence',
        'faction': 'the same realm: plain and sturdy',
        'references': ['AoE2 Barracks: a long hall with a yard and practice gear in front',
                       'Roman and medieval barrack blocks: one long room, door in the long side',
                       'a quintain and a pell (training post): the props that say "drill" at a glance'],
        'read_at_play_size': 'a long low roof, a blocky gate in front, and a fenced yard with a training post',
    })
    b.part('footing', 'stone footing keeps the timber off the ground', sh.block(30, 450, 30, 250, 0, 12, 'stone'), 'base', True)
    b.part('dormitory', 'one long room of bunks: length says "many men"', sh.block(40, 440, 40, 240, 12, 100, 'timber'))
    b.part('roof', 'long low pitched roof; carries the player colour', sh.gable(400, 200, 74, 'roof', overhang=12).move(40, 40, 100), 'roof')
    b.part('muster_gate', 'stone gate block in the middle of the front: recruits march out here; taller than the eaves so the door reads', sh.block(190, 290, 240, 282, 0, 150, 'stone'), 'signature', True)
    b.part('gate_cap', 'small hipped cap over the gate; second player-colour face', sh.pyramid(120, 62, 40, 'roof').move(180, 230, 150), 'roof')
    b.part('gateway', 'the doorway, a person and a half high so pikes clear it', sh.block(215, 265, 280, 286, 0, 118, 'dark'), 'opening', True)
    b.mark_door('gateway', 240, 284, 0, 'y')
    b.part('yard', 'packed-earth drill yard in front', sh.block(40, 440, 286, 460, 0, 3, 'earth'), 'yard', True)
    for i, (x, y) in enumerate(((40, 460), (240, 460), (440, 460), (440, 290), (40, 290))):
        b.post(f'fence_post{i}', 'yard fence post', (x, y, 0), (x, y, 46), 9, free=True)
    for i, (p, q) in enumerate((((40, 460, 42), (240, 460, 42)), ((240, 460, 42), (440, 460, 42)), ((440, 460, 42), (440, 290, 42)), ((40, 460, 42), (40, 290, 42)))):
        b.post(f'fence_rail{i}', 'rail between the posts: keeps the drill yard clear', p, q, 6)
    b.post('pell', 'a training post to strike at: the prop that says "soldiers train here"', (350, 380, 0), (350, 380, 84), 12)
    b.part('pell_arm', 'cross-arm of the training post (a quintain), at shoulder height', sh.block(316, 384, 375, 385, 76, 86, 'timber'), 'detail')
    b.part('rack', 'weapon rack against the wall beside the gate: a human-scale cue', sh.block(90, 170, 240, 254, 12, 64, 'timber'), 'detail')
    b.post('banner_pole', 'a banner on the gate marks it as a military building', (240, 258, 190), (240, 258, 262), 5, free=True, tag='accent')
    b.part('banner', 'the player colour', sh.block(242, 284, 256, 260, 228, 260, 'roof'), 'accent', True)
    return b, (480, 480)


def watch_tower():
    b = Block({
        'is': 'Watch Tower: a stone tower with a covered fighting deck',
        'does': 'sees far and shoots arrows; garrisoned archers and peasants add more',
        'gameplay': '1x1 tile; the player must see it is a defence and roughly how far up the archers stand',
        'built': 'a battered (wider at the foot) stone shaft, a corbelled timber deck, a light roof on four posts',
        'serviced': 'a door at the foot and a ladder inside; arrows are carried up',
        'made_of': 'stone shaft, timber deck and roof',
        'faction': 'the same realm',
        'references': ['AoE2 Watch Tower: a square stone shaft with a wooden top',
                       'medieval watchtowers with hoardings: the deck overhangs the shaft so defenders can shoot down',
                       'battered castle walls: thicker at the bottom, which reads as weight'],
        'read_at_play_size': 'a tall narrow shaft, a wider head, a pointed roof',
    })
    b.part('footing', 'a wider stone foot spreads the weight of a tall shaft', sh.block(14, 146, 14, 146, 0, 6, 'stone'), 'base', True)
    b.part('shaft', 'stone shaft, thicker at the bottom: carries the deck and shrugs off blows', sh.lathe([(74, 6), (62, 40), (56, 170)], 'stone', 4).move(80, 80, 0))
    b.part('deck', 'timber fighting deck wider than the shaft: the overhang lets archers shoot at the foot of the tower', sh.block(26, 134, 26, 134, 170, 186, 'timber'), 'signature')
    for i, (x, y) in enumerate(((30, 30), (130, 30), (130, 130), (30, 130))):
        b.part(f'merlon{i}', 'corner of the parapet: cover for an archer (about chest high)', sh.block(x - 12, x + 12, y - 12, y + 12, 186, 226, 'timber'), 'signature')
        b.post(f'roof_post{i}', 'carries the roof', (x, y, 226), (x, y, 262), 7)
    b.part('rail_y', 'parapet between the corners on the front', sh.block(42, 118, 124, 134, 186, 208, 'timber'), 'signature')
    b.part('rail_x', 'parapet between the corners on the right', sh.block(124, 134, 42, 118, 186, 208, 'timber'), 'signature')
    b.part('roof', 'light pointed roof keeps rain and plunging arrows off; the player colour', sh.pyramid(132, 132, 62, 'roof').move(14, 14, 262), 'roof', True)
    b.part('door', 'door at the foot (a person is 100 tall): the scale cue', sh.block(62, 98, 128, 134, 6, 102, 'dark'), 'opening', True)
    b.mark_door('door', 80, 131, 6, 'y')
    b.part('slit', 'arrow slit half way up: a second place it shoots from', sh.block(138, 144, 74, 86, 96, 140, 'dark'), 'opening', True)
    return b, (160, 160)


CATALOG = {'town_hall': town_hall, 'barracks': barracks, 'watch_tower': watch_tower}
