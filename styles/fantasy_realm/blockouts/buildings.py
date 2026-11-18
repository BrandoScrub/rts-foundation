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

    def shed(s, name, why, x0, x1, y0, y1, z, rise, mat='thatch', t=9):
        """An open lean-to: four posts and a roof sloping down to the front (+y)."""
        s.part(name + '_roof', why, sh.wedge(x1 - x0 + 16, y1 - y0 + 16, rise, mat).move(x0 - 8, y0 - 8, z), 'roof')
        for i, (x, y, top) in enumerate(((x0, y0, z + rise * 0.8), (x1, y0, z + rise * 0.8), (x0, y1, z + 4), (x1, y1, z + 4))):
            s.post(f'{name}_post{i}', 'holds the shed roof up', (x, y, 0), (x, y, top), t)

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
    b.part('hall_roof', 'steep pitched roof (sheds rain); the largest upward face, so it carries the player colour', sh.gable(370, 300, 170, 'roof', overhang=14).move(140, 210, 204), 'roof')
    b.part('keep', 'stone keep at the back corner: the refuge and lookout; at the back so its height shows above the hall', sh.block(60, 220, 60, 220, 14, 330, 'stone'), 'signature')
    b.part('keep_gallery', 'a wider fighting gallery at the top: the overhang says "defended" and lets defenders see the foot of the wall', sh.block(50, 230, 50, 230, 330, 356, 'timber'), 'signature')
    b.part('keep_roof', 'pointed cap over the gallery; second player-colour face, makes the keep a spire in outline', sh.pyramid(200, 200, 210, 'roof').move(40, 40, 356), 'roof')
    b.part('porch_roof', 'lean-to shed along the front: where peasants unload, so the player sees the drop-off side', sh.wedge(300, 92, 40, 'thatch').move(175, 520, 100), 'accent')
    for i, x in enumerate((185, 325, 465)):
        b.post(f'porch_post{i}', 'holds the porch roof up', (x, 604, 14), (x, 604, 104), 10)
    b.part('door', 'the one way in, in the gable end where it is not hidden by the porch: a double door a cart could pass (a person is 100 tall)', sh.block(518, 525, 320, 400, 14, 114, 'dark'), 'opening')
    b.part('door_frame', 'a heavy timber frame round the door in the player colour: marks the entrance', sh.block(518, 523, 308, 412, 14, 126, 'team'), 'accent')
    b.mark_door('door', 521, 360, 14, 'x')
    b.part('steps', 'a stone step from the ground up to the plinth at the door', sh.block(610, 632, 310, 410, 0, 7, 'stone'), 'base', True)
    b.part('keep_course', 'a projecting stone course half way up the keep: breaks the plain box and marks its upper floor', sh.block(54, 226, 54, 226, 196, 208, 'stone'), 'signature', True)
    b.part('keep_loop', 'loophole in the keep facing the front', sh.block(128, 142, 218, 224, 236, 290, 'dark'), 'opening', True)
    b.part('chimney', 'the hall hearth: people live here; its stack marks the back of the hall', sh.block(455, 490, 225, 260, 204, 400, 'stone'), 'detail')
    b.post('flagstaff', 'a flag on the highest point shows whose town this is', (140, 140, 566), (140, 140, 640), 5, free=True, tag='accent')
    b.part('flag', 'the player colour against the sky', sh.block(142, 190, 138, 142, 606, 638, 'team'), 'accent', True)
    b.part('loophole_x', 'arrow loop in the undercroft: where its arrows come from', sh.block(518, 524, 452, 464, 50, 96, 'dark'), 'opening')
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
    b.part('roof', 'long low pitched roof; carries the player colour', sh.gable(400, 200, 104, 'roof', overhang=12).move(40, 40, 100), 'roof')
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
    b.part('cookhouse_stack', 'the cookhouse hearth at the far end: soldiers are fed here; gives the back of the hall a mark', sh.block(60, 96, 56, 92, 100, 196, 'stone'), 'detail')
    b.post('banner_pole', 'a banner on the gate marks it as a military building', (240, 258, 190), (240, 258, 262), 5, free=True, tag='accent')
    b.part('banner', 'the player colour', sh.block(242, 284, 256, 260, 228, 260, 'team'), 'accent', True)
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
    b.part('footing', 'a wide stone foot spreads the weight of a tall shaft', sh.block(14, 146, 14, 146, 0, 6, 'stone'), 'base', True)
    b.part('plinth', 'a stepped base course: thicker at the bottom, which reads as weight and resists blows', sh.block(24, 136, 24, 136, 6, 30, 'stone'))
    b.part('shaft', 'stone shaft that carries the deck high enough to see over trees', sh.block(34, 126, 34, 126, 30, 170, 'stone'))
    b.part('deck', 'timber fighting deck wider than the shaft: the overhang lets archers shoot at the foot of the tower', sh.block(20, 140, 20, 140, 170, 186, 'timber'), 'signature')
    for i, (x, y) in enumerate(((30, 30), (130, 30), (130, 130), (30, 130))):
        b.part(f'merlon{i}', 'corner of the parapet: cover for an archer (about chest high)', sh.block(x - 11, x + 11, y - 11, y + 11, 186, 222, 'timber'), 'signature')
        b.post(f'roof_post{i}', 'carries the roof well clear of the parapet, so the open deck shows as a dark gap', (x, y, 222), (x, y, 284), 7)
    b.part('rail_y', 'parapet between the corners on the front', sh.block(41, 119, 126, 136, 186, 206, 'timber'), 'signature')
    b.part('rail_x', 'parapet between the corners on the right', sh.block(126, 136, 41, 119, 186, 206, 'timber'), 'signature')
    b.part('roof', 'steep pointed roof keeps rain and plunging arrows off; the player colour', sh.pyramid(140, 140, 150, 'roof').move(10, 10, 280), 'roof', True)
    b.part('door', 'door at the foot (a person is 100 tall): the scale cue', sh.block(62, 98, 136, 140, 6, 104, 'dark'), 'opening', True)
    b.mark_door('door', 80, 138, 6, 'y')
    b.part('slit', 'arrow slit half way up: a second place it shoots from', sh.block(126, 130, 74, 86, 96, 140, 'dark'), 'opening', True)
    return b, (160, 160)


def cottage():
    b = Block({'is': 'Cottage: a family home', 'does': '+5 population', 'gameplay': '2x2 tiles, built by the dozen: small, cheap-looking, never mistaken for a work building',
               'built': 'timber frame on a low stone sill, steep thatch', 'serviced': 'one door on the front', 'made_of': 'timber, thatch, a stone chimney',
               'faction': 'the realm: homely', 'references': ['AoE2 House (Dark Age): a single small thatched block', 'English cruck cottages: roof taller than the wall'],
               'read_at_play_size': 'a steep thatched roof that is most of the building, a chimney, a door'})
    b.part('sill', 'stone sill keeps the timber dry', sh.block(52, 268, 72, 248, 0, 8, 'stone'), 'base', True)
    b.part('walls', 'one room; walls lower than a storey so the roof dominates', sh.block(60, 260, 80, 240, 8, 78, 'timber'))
    b.part('thatch', 'steep thatch sheds rain; the big roof is what says "home"', sh.gable(200, 160, 124, 'thatch', overhang=16).move(60, 80, 78), 'roof')
    b.part('chimney', 'the hearth: a home has a fire', sh.block(70, 100, 100, 130, 78, 216, 'stone'), 'detail')
    b.part('door', 'the door, a person high: the scale cue', sh.block(140, 180, 240, 245, 8, 74, 'dark'), 'opening', True)
    b.part('lintel', 'a painted lintel in the player colour: whose village this is', sh.block(132, 188, 240, 246, 74, 84, 'team'), 'accent', True)
    b.mark_door('door', 160, 242, 6, 'y')
    return b, (320, 320)


def mill():
    b = Block({'is': 'Mill: a windmill with a grain store', 'does': 'food drop-off, farm research; Farms need it', 'gameplay': '2x2 tiles; sails make it the one building recognisable from the outline alone',
               'built': 'a round stone tower, a timber cap that carries the windshaft, four sails; a lean-to store where food is brought', 'moves': 'the sails turn on the windshaft',
               'serviced': 'sacks go in at the lean-to', 'made_of': 'stone tower, timber cap and sails, thatch store', 'faction': 'the realm',
               'references': ['AoE2 Mill: sails are the identity', 'English tower mills: tapering round tower, boat-shaped cap, windshaft tilted up'],
               'read_at_play_size': 'a tapering tower with a cross of sails and a low shed beside it'})
    b.part('tower', 'tapering round stone tower: lifts the sails into the wind', sh.lathe([(74, 0), (56, 150)], 'stone', 10).move(130, 130, 0), 'body', True)
    b.part('cap', 'timber cap that carries the windshaft; the player colour', sh.lathe([(62, 150), (48, 176), (0, 214)], 'roof', 10).move(130, 130, 0), 'roof')
    b.post('windshaft', 'the shaft the sails turn on, pointing at the viewer side so the sails face the camera', (130, 178, 172), (130, 226, 176), 12, free=True, tag='signature')
    for i, (dx, dz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        b.post(f'sail_arm{i}', 'a sail arm (stock)', (130, 224, 176), (130 + dx * 84, 224, 176 + dz * 84), 7, free=True, tag='signature')
        b.part(f'sail{i}', 'canvas on the arm: what catches the wind, and the shape that says "mill"', sh.convex([(130 + dx * 24 - dz * 12, 222, 176 + dz * 24 + dx * 12), (130 + dx * 24 + dz * 12, 222, 176 + dz * 24 - dx * 12), (130 + dx * 84 + dz * 12, 222, 176 + dz * 84 - dx * 12), (130 + dx * 84 - dz * 12, 222, 176 + dz * 84 + dx * 12),
                          (130 + dx * 24 - dz * 12, 226, 176 + dz * 24 + dx * 12), (130 + dx * 24 + dz * 12, 226, 176 + dz * 24 - dx * 12), (130 + dx * 84 + dz * 12, 226, 176 + dz * 84 - dx * 12), (130 + dx * 84 - dz * 12, 226, 176 + dz * 84 + dx * 12)], 'canvas'), 'signature', True)
    b.shed('store', 'lean-to grain store: where peasants bring food', 214, 296, 150, 250, 62, 34)
    b.part('sacks', 'grain sacks under the lean-to: a scale cue and the sign of a food store', sh.block(228, 284, 176, 232, 0, 30, 'canvas'), 'detail', True)
    b.part('door', 'door into the tower', sh.block(112, 148, 200, 206, 0, 84, 'dark'), 'opening', True)
    b.mark_door('door', 130, 204, 0, 'y')
    return b, (320, 320)


def lumber_camp():
    b = Block({'is': 'Lumber Camp: a sawyers\' shed', 'does': 'wood drop-off, wood research', 'gameplay': '2x2 tiles, placed against forests: must read as "wood" at a glance',
               'built': 'an open shed on posts, a stack of logs, a sawhorse', 'serviced': 'logs are carried in at the open front', 'made_of': 'rough timber, thatch',
               'faction': 'the realm', 'references': ['AoE2 Lumber Camp: an open shed with stacked logs', 'a sawpit and sawhorse'], 'read_at_play_size': 'a shed roof and a pile of round logs'})
    b.part('floor', 'trodden earth and sawdust', sh.block(30, 290, 30, 290, 0, 3, 'earth'), 'yard', True)
    b.shed('shed', 'open shed keeps cut planks dry; open so logs can be carried straight in', 50, 200, 50, 170, 96, 44)
    b.part('planks', 'a stack of sawn planks under the shed: the product', sh.block(70, 180, 70, 130, 3, 40, 'timber'), 'detail', True)
    for i, (y, z) in enumerate(((216, 16), (246, 16), (231, 42))):
        b.part(f'log{i}', 'felled logs stacked for sawing: the round ends say "wood"', sh.cyl((170, y, z), (290, y, z), 15, 'timber'), 'signature', True)
    b.post('sawhorse_a', 'sawhorse leg', (60, 220, 0), (80, 250, 44), 7, free=True); b.post('sawhorse_b', 'sawhorse leg', (130, 220, 0), (110, 250, 44), 7, free=True)
    b.part('sawlog', 'the log being sawn, at waist height: the human-scale cue', sh.cyl((50, 250, 50), (140, 250, 50), 10, 'timber'), 'detail', True)
    b.post('flag_pole', 'a small flag shows whose camp it is', (50, 50, 131), (50, 50, 190), 5, free=True, tag='accent')
    b.part('flag', 'the player colour', sh.block(52, 86, 48, 52, 164, 188, 'team'), 'accent', True)
    return b, (320, 320)


def mining_camp():
    b = Block({'is': 'Mining Camp: a miners\' shed and ore yard', 'does': 'stone, iron and crystal drop-off; mining research', 'gameplay': '2x2 tiles, placed against ore: must read as "mining" and not be confused with the Lumber Camp',
               'built': 'a stone-walled shed, heaps of ore sorted by kind, a cart', 'serviced': 'ore is tipped onto the heaps', 'made_of': 'stone, timber', 'faction': 'the realm (dwarf-built: squat and square)',
               'references': ['AoE2 Mining Camp: shed, cart and rock piles', 'medieval ore-dressing floors: sorted heaps'], 'read_at_play_size': 'a squat stone hut, three coloured heaps, a cart'})
    b.part('floor', 'gravel working floor', sh.block(30, 290, 30, 290, 0, 3, 'earth'), 'yard', True)
    b.part('hut', 'squat stone hut for tools and the tally: stone because miners build with what they dig', sh.block(50, 190, 50, 170, 3, 80, 'stone'), 'body', True)
    b.part('hut_roof', 'low hipped roof; the player colour', sh.pyramid(164, 144, 56, 'roof').move(38, 38, 80), 'roof')
    b.part('door', 'hut door', sh.block(100, 138, 170, 175, 3, 72, 'dark'), 'opening', True)
    b.mark_door('door', 120, 172, 3, 'y')
    for name, why, x, y, mat in (('stone_heap', 'heap of cut stone', 236, 90, 'stone'), ('iron_heap', 'heap of iron ore', 236, 190, 'iron'), ('crystal_heap', 'heap of crystal: the bright colour is the cue that crystal comes here too', 150, 240, 'crystal')):
        b.part(name, why, sh.lathe([(40, 3), (26, 34), (0, 66)], mat, 7).move(x, y, 0), 'signature', True)
    b.part('cart', 'ore cart: a human-scale cue and the sign of hauling', sh.block(52, 108, 214, 250, 16, 44, 'timber'), 'detail', True)
    for i, x in enumerate((64, 96)):
        b.part(f'wheel{i}', 'cart wheel', sh.cyl((x, 252, 16), (x, 258, 16), 15, 'dark'), 'detail', True)
    return b, (320, 320)


def blacksmith():
    b = Block({'is': 'Blacksmith: a forge and smithy', 'does': 'attack and armour research', 'gameplay': '3x3 tiles; the forge fire and chimney are its identity',
               'built': 'a stone forge house with a tall chimney, an open-fronted smithy beside it with the anvil', 'power': 'charcoal fire, bellows', 'serviced': 'work is done at the open front',
               'made_of': 'stone, timber, slate', 'faction': 'the realm (dwarf craft: heavy stone)', 'references': ['AoE2 Blacksmith: open forge with a glowing fire', 'village smithies: a big hooded hearth and a chimney taller than the roof'],
               'read_at_play_size': 'a heavy stone block, a tall chimney, an orange glow under an open roof'})
    b.part('floor', 'paved yard: sparks and mud do not mix', sh.block(30, 450, 30, 450, 0, 6, 'stone'), 'base', True)
    b.part('forge_house', 'stone house for the hearth and stock: stone because of the fire', sh.block(50, 270, 50, 270, 6, 116, 'stone'))
    b.part('roof', 'slate roof; the player colour', sh.gable(220, 220, 110, 'roof', overhang=10).move(50, 50, 116), 'roof')
    b.part('chimney', 'a chimney much taller than the roof: the forge draws hard, and it is the outline that says "smith"', sh.block(60, 116, 60, 116, 116, 300, 'stone'), 'signature')
    b.shed('smithy', 'open-fronted smithy: the smith works in the light and the player sees the fire', 286, 430, 70, 250, 110, 40, 'roof')
    b.part('hearth', 'the raised hearth', sh.block(300, 380, 80, 130, 6, 52, 'stone'), 'detail', True)
    b.part('fire', 'the forge fire: the one bright colour, the building\'s signal', sh.block(310, 370, 88, 124, 52, 62, 'ember'), 'accent', True)
    b.part('anvil', 'the anvil on its block, at waist height: the scale cue', sh.block(330, 376, 180, 204, 6, 50, 'dark'), 'detail', True)
    b.part('trough', 'quenching trough', sh.block(300, 420, 280, 310, 6, 28, 'timber'), 'detail', True)
    b.part('door', 'door of the forge house', sh.block(140, 184, 270, 275, 6, 100, 'dark'), 'opening', True)
    b.mark_door('door', 160, 272, 6, 'y')
    b.part('sign', 'a hanging sign in the player colour', sh.block(196, 236, 270, 275, 70, 104, 'team'), 'accent', True)
    return b, (480, 480)


def market():
    b = Block({'is': 'Market: a market square', 'does': 'buys and sells food, wood and stone', 'gameplay': '4x4 tiles; open and colourful so it never reads as a hall or a fort',
               'built': 'a paved square, a small stone weigh-house in the middle, canvas stalls round it', 'serviced': 'traders come to the stalls from every side',
               'made_of': 'paving, stone, timber, striped canvas', 'faction': 'the realm', 'references': ['AoE2 Market: open stalls round a central structure', 'medieval market crosses and weigh-houses'],
               'read_at_play_size': 'a ring of bright awnings round a small tower on a pale square'})
    b.part('square', 'paved square: many feet, no mud', sh.block(30, 610, 30, 610, 0, 6, 'stone'), 'base', True)
    b.part('weigh_house', 'the weigh-house where trades are weighed and taxed: the fixed centre of the market', sh.block(250, 390, 250, 390, 6, 130, 'stone'), 'body', True)
    b.part('weigh_roof', 'pointed roof; the player colour', sh.pyramid(170, 170, 170, 'roof').move(235, 235, 130), 'roof')
    b.part('door', 'weigh-house door', sh.block(300, 340, 390, 395, 6, 100, 'dark'), 'opening', True)
    b.mark_door('door', 320, 392, 6, 'y')
    for i, (x, y, mat) in enumerate(((70, 80, 'canvas'), (420, 70, 'team'), (60, 430, 'team'), (430, 440, 'canvas'))):
        b.shed(f'stall{i}', 'a stall awning: shade for goods, and the colour that says "market"', x, x + 130, y, y + 100, 84, 34, mat, 7)
        b.part(f'goods{i}', 'the stall table with goods at waist height: the scale cue', sh.block(x + 14, x + 116, y + 30, y + 80, 6, 46, 'timber'), 'detail', True)
    b.post('pole', 'market flag: the market is open, and whose it is', (320, 320, 300), (320, 320, 370), 5, free=True, tag='accent')
    b.part('flag', 'the player colour', sh.block(322, 366, 318, 322, 338, 368, 'team'), 'accent', True)
    return b, (640, 640)


def archery_range():
    b = Block({'is': 'Archery Range: a shooting ground', 'does': 'trains Elf Archers and Halfling Slingers', 'gameplay': '3x3 tiles; targets are the identity',
               'built': 'a long open shooting shed at the back, straw butts at the far end of a fenced lane', 'serviced': 'archers stand under the shed and shoot along the lane',
               'made_of': 'timber, thatch, straw', 'faction': 'the realm (elf-kept: light and open)', 'references': ['AoE2 Archery Range: targets in a yard', 'English archery butts: round straw targets on stands'],
               'read_at_play_size': 'a long low shed and a row of round targets with dark centres'})
    b.part('lane', 'the mown shooting lane', sh.block(30, 450, 30, 450, 0, 3, 'earth'), 'yard', True)
    b.shed('shed', 'shooting shed along the back: archers shoot from under cover', 50, 430, 50, 150, 100, 40)
    b.part('rack', 'bow rack under the shed: the scale cue', sh.block(70, 170, 62, 76, 3, 70, 'timber'), 'detail', True)
    for i, x in enumerate((110, 240, 370)):
        b.post(f'butt_leg{i}', 'the stand a target leans on', (x, 392, 0), (x, 408, 70), 8, free=True)
        b.part(f'butt{i}', 'a round straw target facing the shed: the shape that says "archery"', sh.cyl((x, 404, 62), (x, 420, 62), 40, 'thatch', seg=12), 'signature', True)
        b.part(f'bull{i}', 'the bullseye in the player colour', sh.cyl((x, 420, 62), (x, 423, 62), 15, 'team', seg=10), 'accent', True)
    for i, (p, q) in enumerate((((50, 150, 40), (50, 450, 40)), ((430, 150, 40), (430, 450, 40)))):
        b.post(f'lane_rail{i}', 'rail along the lane keeps people out of the line of fire', p, q, 6, free=True)
        for j, y in enumerate((300, 450)):
            b.post(f'lane_post{i}{j}', 'rail post', (p[0], y, 0), (p[0], y, 44), 8, free=True)
    return b, (480, 480)


def stable():
    b = Block({'is': 'Stable: stalls and a paddock for mounts', 'does': 'trains Wolf Riders; cavalry research', 'gameplay': '3x3 tiles; a row of stall doors and a paddock tell it from the Barracks',
               'built': 'a long stall block with half-doors, a hay loft, a fenced paddock in front', 'serviced': 'mounts are led out of the stalls into the paddock',
               'made_of': 'timber, thatch', 'faction': 'the realm', 'references': ['AoE2 Stable: a row of stalls', 'livery stables: half-doors, hay loft door in the gable, paddock rails'],
               'read_at_play_size': 'a long roof over three dark stall openings, a haystack, a fenced paddock'})
    b.part('sill', 'stone sill under the stalls', sh.block(30, 450, 30, 230, 0, 8, 'stone'), 'base', True)
    b.part('stalls', 'the stall block: one long row so every stall opens to the paddock', sh.block(40, 440, 40, 220, 8, 96, 'timber'))
    b.part('roof', 'roof with a hay loft under it; the player colour', sh.gable(400, 180, 110, 'roof', overhang=14).move(40, 40, 96), 'roof')
    for i, x in enumerate((100, 240, 380)):
        b.part(f'stall_door{i}', 'a stall opening wide and tall enough for a mount: three of them say "stable"', sh.block(x - 38, x + 38, 220, 225, 8, 84, 'dark'), 'opening', True)
    b.mark_door('stall_door1', 240, 222, 6, 'y')
    b.part('paddock', 'trodden paddock', sh.block(40, 440, 226, 450, 0, 3, 'earth'), 'yard', True)
    for i, (x, y) in enumerate(((40, 450), (240, 450), (440, 450), (440, 240), (40, 240))):
        b.post(f'fence_post{i}', 'paddock post', (x, y, 0), (x, y, 50), 9, free=True)
    for i, (p, q) in enumerate((((40, 450, 44), (240, 450, 44)), ((240, 450, 44), (440, 450, 44)), ((440, 450, 44), (440, 240, 44)), ((40, 450, 44), (40, 240, 44)))):
        b.post(f'fence_rail{i}', 'paddock rail', p, q, 6)
    b.part('haystack', 'a haystack: feed, and the cue that animals live here', sh.lathe([(42, 3), (40, 40), (0, 84)], 'thatch', 10).move(370, 360, 0), 'signature', True)
    b.part('trough', 'water trough at mount height', sh.block(70, 170, 330, 362, 3, 34, 'timber'), 'detail', True)
    b.post('pole', 'banner on the gable', (440, 130, 180), (440, 130, 246), 5, free=True, tag='accent')
    b.part('banner', 'the player colour', sh.block(442, 482, 128, 132, 216, 244, 'team'), 'accent', True)
    return b, (480, 480)


def _logs(b, pts, h=92):
    for i, (x, y) in enumerate(pts):
        b.part(f'log{i}', 'a sharpened log set in the ground; side by side they make the wall, and the points stop climbers', sh.lathe([(15, 0), (15, h - 22), (0, h)], 'timber', 7).move(x, y, 0), 'body', True)


def palisade():
    b = Block({'is': 'Palisade: a wall of sharpened logs', 'does': 'blocks movement; cheap, weak', 'gameplay': '1x1 tile, laid in lines in any direction: the tile must join its neighbours on all four sides and on diagonals',
               'built': 'logs set upright in a trench, lashed', 'made_of': 'timber', 'faction': 'the realm', 'references': ['AoE2 Palisade Wall', 'motte-and-bailey stockades'],
               'read_at_play_size': 'a clump of pointed stakes that runs into the next tile'})
    _logs(b, [(80, 80)] + [(80 + d * 26, 80) for d in (-3, -2, -1, 1, 2, 3)] + [(80, 80 + d * 26) for d in (-3, -2, -1, 1, 2, 3)])
    return b, (160, 160)


def gate():
    b = Block({'is': 'Palisade Gate', 'does': 'lets the owner\'s units through a palisade', 'gameplay': '1x1 tile; must read as an opening, not a wall',
               'built': 'two heavy posts, a lintel, plank doors', 'moves': 'the doors swing on the posts', 'made_of': 'timber', 'faction': 'the realm',
               'references': ['AoE2 Palisade Gate', 'stockade gates with a lintel beam'], 'read_at_play_size': 'two tall posts with a beam across and a dark gap between'})
    _logs(b, [(18, 80), (142, 80), (80, 18), (80, 142)], 120)
    b.part('lintel_x', 'beam tying the gateposts together across the gap', sh.block(8, 152, 70, 90, 120, 138, 'timber'), 'signature', True)
    b.part('lintel_y', 'the same beam for a wall running the other way', sh.block(70, 90, 8, 152, 120, 138, 'timber'), 'signature', True)
    b.part('way', 'the trodden way through: darker ground says "you can pass here"', sh.block(34, 126, 34, 126, 0, 3, 'dark'), 'opening', True)
    b.part('badge', 'the owner\'s colour on the lintel: only their units pass', sh.block(64, 96, 64, 96, 138, 160, 'team'), 'accent', True)
    return b, (160, 160)


def watchpost():
    b = Block({'is': 'Watchpost: a lookout platform', 'does': 'sees far; cannot attack', 'gameplay': '1x1 tile; must look harmless next to the Watch Tower: open, thin, wooden',
               'built': 'four splayed poles, a platform, a ladder', 'serviced': 'climbed by the ladder', 'made_of': 'timber', 'faction': 'the realm',
               'references': ['AoE2 Outpost: an open timber lookout', 'hunting stands and fire-watch platforms'], 'read_at_play_size': 'a spindly frame with a small platform and a flag'})
    b.part('platform', 'the lookout floor, three people high: over the trees', sh.block(40, 120, 40, 120, 196, 206, 'timber'), 'signature', True)
    for i, (x, y) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        b.post(f'leg{i}', 'a splayed leg: wide at the foot so the frame cannot topple', (80 + x * 58, 80 + y * 58, 0), (80 + x * 36, 80 + y * 36, 200), 9)
        b.post(f'rail_post{i}', 'railing post (hand-rail height)', (80 + x * 38, 80 + y * 38, 206), (80 + x * 38, 80 + y * 38, 252), 6, free=True)
    b.post('brace_a', 'cross-brace: stops the legs racking', (136, 136, 20), (48, 116, 180), 6, free=True); b.post('brace_b', 'cross-brace on the other face', (136, 136, 20), (116, 48, 180), 6, free=True)
    b.post('ladder', 'the ladder up: the scale cue', (80, 150, 0), (80, 122, 200), 8)
    b.post('pole', 'signal flag pole', (44, 44, 206), (44, 44, 300), 5, free=True, tag='accent')
    b.part('flag', 'the player colour; a watchpost signals', sh.block(46, 86, 42, 46, 268, 298, 'team'), 'accent', True)
    return b, (160, 160)


def stone_wall():
    b = Block({'is': 'Stone Wall', 'does': 'blocks movement; strong', 'gameplay': '1x1 tile, laid in lines: fills its tile so neighbours join without gaps',
               'built': 'coursed stone with a wall-walk and merlons', 'made_of': 'stone', 'faction': 'the realm', 'references': ['AoE2 Stone Wall', 'curtain walls with crenellations'],
               'read_at_play_size': 'a pale solid block with a toothed top'})
    b.part('wall', 'the wall itself: as wide as the tile so there is no gap to the next piece', sh.block(4, 156, 4, 156, 0, 96, 'stone'), 'body', True)
    for i, (x, y) in enumerate(((26, 26), (134, 26), (134, 134), (26, 134), (80, 80))):
        b.part(f'merlon{i}', 'a merlon: cover on the wall-walk, and the teeth that say "fortification"', sh.block(x - 20, x + 20, y - 20, y + 20, 96, 126, 'stone'), 'signature')
    return b, (160, 160)


def stone_gate():
    b = Block({'is': 'Stone Gate', 'does': 'lets the owner\'s units through a stone wall', 'gameplay': '1x1 tile; an arch with a dark way through, taller than the wall',
               'built': 'two stone piers, an arch, a gallery over it', 'moves': 'a portcullis drops in the arch', 'made_of': 'stone, timber', 'faction': 'the realm',
               'references': ['AoE2 Gate', 'castle gatehouses: passage between two piers with a room over'], 'read_at_play_size': 'a block taller than the wall with a dark doorway and a coloured cap'})
    for i, (x0, x1, y0, y1) in enumerate(((4, 46, 4, 46), (114, 156, 4, 46), (114, 156, 114, 156), (4, 46, 114, 156))):
        b.part(f'pier{i}', 'a stone pier carrying the gallery', sh.block(x0, x1, y0, y1, 0, 110, 'stone'), 'body', True)
    b.part('gallery', 'the room over the gate where the portcullis is worked: makes the gate taller than the wall', sh.block(4, 156, 4, 156, 110, 150, 'stone'), 'signature')
    b.part('cap', 'low roof in the owner\'s colour: only their units pass', sh.pyramid(164, 164, 90, 'roof').move(-2, -2, 150), 'roof')
    b.part('way', 'the way through, dark under the arch', sh.block(46, 114, 46, 114, 0, 3, 'dark'), 'opening', True)
    b.part('shadow_x', 'darkness inside the passage seen from the right', sh.block(150, 154, 48, 112, 0, 104, 'dark'), 'opening', True)
    b.part('shadow_y', 'darkness inside the passage seen from the front', sh.block(48, 112, 150, 154, 0, 104, 'dark'), 'opening', True)
    return b, (160, 160)


CATALOG = {'town_hall': town_hall, 'cottage': cottage, 'mill': mill, 'lumber_camp': lumber_camp, 'mining_camp': mining_camp, 'blacksmith': blacksmith, 'market': market,
           'barracks': barracks, 'archery_range': archery_range, 'stable': stable, 'palisade': palisade, 'gate': gate, 'watchpost': watchpost, 'watch_tower': watch_tower,
           'stone_wall': stone_wall, 'stone_gate': stone_gate}
