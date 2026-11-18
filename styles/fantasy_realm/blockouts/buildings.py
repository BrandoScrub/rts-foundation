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

    # ---- detail (third pass): what makes a mass a building. All of it sits on the two faces the camera sees:
    # the +x face (at x = x1, running along y) and the +y face (at y = y1, running along x). ----
    def _face(s, axis, wall, a0, a1, z0, z1, proud, mat):
        return sh.block(wall, wall + proud, a0, a1, z0, z1, mat) if axis == 'x' else sh.block(a0, a1, wall, wall + proud, z0, z1, mat)

    def framing(s, name, x0, x1, y0, y1, z0, z1, step=72):
        """Half-timbering on a timber storey: a frame of dark beams with daub panels between (the frame carries the
        house, the daub only fills it: the storybook look of the realm's houses)."""
        for axis, wall, a0, a1 in (('x', x1, y0, y1), ('y', y1, x0, x1)):
            n = f'{name}_{axis}'
            s.part(n + '_daub', 'daub panels between the beams: pale, so the dark frame reads', s._face(axis, wall, a0 + 5, a1 - 5, z0 + 5, z1 - 5, 1.5, 'plaster'), 'detail', True)
            s.part(n + '_sole', 'sole plate: the beam the frame stands on', s._face(axis, wall, a0, a1, z0, z0 + 8, 4, 'beam'), 'detail', True)
            s.part(n + '_top', 'top plate: carries the roof or the floor above', s._face(axis, wall, a0, a1, z1 - 8, z1, 4, 'beam'), 'detail', True)
            k = max(1, round((a1 - a0) / step))
            for i in range(k + 1):
                a = a0 + (a1 - a0 - 8) * i / k
                s.part(f'{n}_stud{i}', 'a stud of the frame', s._face(axis, wall, a, a + 8, z0, z1, 4, 'beam'), 'detail', True)
            for i, (b0, b1) in enumerate(((a0 + 6, a0 + (a1 - a0) / k - 2), (a1 - 6, a1 - (a1 - a0) / k + 2))):       # a brace in each end bay
                p, q = ((wall + 3, b0, z0 + 6), (wall + 3, b1, z1 - 6)) if axis == 'x' else ((b0, wall + 3, z0 + 6), (b1, wall + 3, z1 - 6))
                s.post(f'{n}_brace{i}', 'a corner brace: stops the frame racking in the wind', p, q, 6, 'beam', free=True)

    def windows(s, name, axis, wall, at, z, w=26, h=38, lit=True, shutters=True):
        """Windows on a seen face: a frame, a lit pane (people are inside; warm light against the dark realm), a
        mullion, a stone sill, and shutters."""
        for i, a in enumerate(at):
            n = f'{name}{i}'
            s.part(n + '_frame', 'window frame', s._face(axis, wall, a - w / 2 - 4, a + w / 2 + 4, z - 4, z + h + 4, 5, 'beam'), 'opening', True)
            s.part(n + '_pane', 'a lit window: someone lives or works here' if lit else 'a dark window', s._face(axis, wall, a - w / 2, a + w / 2, z, z + h, 6, 'window' if lit else 'dark'), 'opening', True)
            s.part(n + '_mullion', 'the mullion: small panes, since glass is dear', s._face(axis, wall, a - 1.5, a + 1.5, z, z + h, 7, 'beam'), 'opening', True)
            s.part(n + '_sill', 'a sill to shed rain', s._face(axis, wall, a - w / 2 - 6, a + w / 2 + 6, z - 8, z - 4, 8, 'stone'), 'detail', True)
            if shutters:
                for j, b in enumerate((a - w / 2 - 14, a + w / 2 + 4)):
                    s.part(f'{n}_shutter{j}', 'a shutter, folded back', s._face(axis, wall, b, b + 10, z - 2, z + h + 2, 4, 'timber'), 'detail', True)

    def quoins(s, name, x0, x1, y0, y1, z0, z1, size=20):
        """Dressed corner stones on a stone mass: big pale blocks that tie the corners, alternating long and short."""
        k = int((z1 - z0) // size)
        for i in range(k):
            z = z0 + i * size; L = 26 if i % 2 else 16
            s.part(f'{name}_qa{i}', 'a dressed corner stone: ties the two walls, and its pale colour draws the corner', sh.block(x1 - L, x1 + 3, y1 - (42 - L), y1 + 3, z, z + size - 3, 'quarry'), 'detail', True)
            s.part(f'{name}_qb{i}', 'the same at the right-hand corner', sh.block(x1 - (42 - L), x1 + 3, y0 - 3, y0 + L, z, z + size - 3, 'quarry'), 'detail', True)
            s.part(f'{name}_qc{i}', 'the same at the left-hand corner', sh.block(x0 - 3, x0 + L, y1 - (42 - L), y1 + 3, z, z + size - 3, 'quarry'), 'detail', True)

    def doorway(s, name, axis, wall, c, z, w, h):
        """A door surround: jambs, a heavy lintel and a threshold, round an opening that is already there."""
        s.part(name + '_jamb0', 'door jamb', s._face(axis, wall, c - w / 2 - 8, c - w / 2, z, z + h + 6, 7, 'beam'), 'opening', True)
        s.part(name + '_jamb1', 'door jamb', s._face(axis, wall, c + w / 2, c + w / 2 + 8, z, z + h + 6, 7, 'beam'), 'opening', True)
        s.part(name + '_lintel', 'the lintel over the door', s._face(axis, wall, c - w / 2 - 12, c + w / 2 + 12, z + h, z + h + 10, 9, 'beam'), 'opening', True)
        s.part(name + '_leaf', 'a plank door leaf standing open: the building is in use', s._face(axis, wall, c - w / 2, c - w / 2 + w * .34, z, z + h, 8, 'timber'), 'opening', True)
        s.part(name + '_step', 'a stone threshold', s._face(axis, wall, c - w / 2 - 10, c + w / 2 + 10, z - 4, z + 3, 14, 'stone'), 'detail', True)

    def gable_end(s, name, x, y0, y1, z, rise):
        """Close the gable on the +x end of a roof whose ridge runs along x: a daub triangle, a king post and collar."""
        m = (y0 + y1) / 2
        s.part(name + '_wall', 'the gable wall: closes the roof space against the weather', sh.convex([(x - 4, y0, z), (x - 4, y1, z), (x - 4, m, z + rise), (x, y0, z), (x, y1, z), (x, m, z + rise)], 'plaster'), 'detail', True)
        s.part(name + '_king', 'king post: holds the ridge up', sh.block(x, x + 4, m - 4, m + 4, z, z + rise - 4, 'beam'), 'detail', True)
        s.part(name + '_collar', 'collar beam tying the rafters', sh.block(x, x + 4, y0 + (y1 - y0) * .25, y1 - (y1 - y0) * .25, z + rise * .46, z + rise * .46 + 7, 'beam'), 'detail', True)
        s.post(name + '_barge0', 'barge board: covers the roof edge at the gable', (x + 3, y0, z), (x + 3, m, z + rise), 7, 'beam', free=True)
        s.post(name + '_barge1', 'barge board on the other slope', (x + 3, y1, z), (x + 3, m, z + rise), 7, 'beam', free=True)

    def finial(s, name, x, y, z, glow=True):
        s.part(name, 'a crystal finial on the peak: the realm marks its roofs with its crystal, and the point draws the eye up' if glow else 'an iron finial', sh.cyl((x, y, z - 4), (x, y, z + 34), 6, 'glow' if glow else 'iron', .5, seg=5), 'accent', True)

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
    b.framing('hall', 140, 510, 210, 510, 124, 204)
    b.windows('hall_wy', 'y', 510, (200, 290, 380, 460), 144, 28, 36)
    b.windows('hall_wx', 'x', 510, (260, 460), 144, 28, 36)
    b.gable_end('hall_gable', 510, 210, 510, 204, 170)
    b.windows('gable_w', 'x', 510, (360,), 250, 30, 44, shutters=False)
    b.quoins('under', 130, 520, 200, 520, 14, 124)
    for i, x in enumerate((230, 420)): b.part(f'loophole_y{i}', 'arrow loops along the undercroft front', sh.block(x - 6, x + 6, 518, 524, 50, 96, 'dark'), 'opening', True)
    b.windows('keep_w', 'y', 220, (140,), 268, 26, 40, shutters=False)
    b.windows('keep_wx', 'x', 220, (140,), 268, 26, 40, shutters=False)
    b.part('ridge', 'a ridge beam capping the hall roof where the two slopes meet', sh.block(126, 524, 355, 365, 370, 380, 'beam'), 'detail', True)
    b.finial('keep_finial', 140, 140, 566 - 6)
    b.part('lantern0', 'a crystal lantern by the door: the hall is lit at night, and it marks the entrance', sh.cyl((526, 300, 96), (526, 300, 116), 7, 'glow', 2, seg=5), 'accent', True)
    b.part('lantern1', 'its pair on the other side of the door', sh.cyl((526, 420, 96), (526, 420, 116), 7, 'glow', 2, seg=5), 'accent', True)
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
    b.framing('dorm', 40, 440, 40, 240, 12, 100, step=80)
    b.windows('dorm_w', 'y', 240, (80, 150, 330, 400), 46, 24, 30)
    b.windows('dorm_wx', 'x', 440, (140,), 46, 24, 30)
    b.gable_end('gable', 440, 40, 240, 100, 104)
    b.quoins('gate', 190, 290, 240, 282, 0, 150)
    for i, y in enumerate((80, 200)): b.part(f'shield{i}', 'a shield hung on the gable wall in the owner\'s colour: soldiers live here', sh.cyl((444, y, 70), (449, y, 70), 17, 'team', seg=10), 'accent', True)
    b.part('ridge', 'a ridge beam capping the roof', sh.block(28, 452, 135, 145, 200, 209, 'beam'), 'detail', True)
    b.part('spears', 'spears stood in the rack: an armoury at a glance', sh.block(100, 160, 254, 258, 12, 110, 'beam'), 'detail', True)
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
    b.quoins('shaft', 34, 126, 34, 126, 30, 170)
    b.windows('lit', 'y', 126, (80,), 118, 20, 34, shutters=False)
    b.doorway('door', 'y', 140, 80, 6, 36, 98)
    b.part('course', 'a string course where the plinth meets the shaft', sh.block(22, 138, 22, 138, 28, 36, 'quarry'), 'detail', True)
    b.finial('finial', 80, 80, 426)
    b.part('brazier', 'a signal fire on the deck: the tower warns the town', sh.lathe([(8, 186), (14, 198), (0, 216)], 'ember', 6).move(104, 104, 0), 'accent', True)
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
    b.framing('walls', 60, 260, 80, 240, 8, 78, step=66)
    b.windows('w', 'y', 240, (92, 228), 30, 24, 30)
    b.windows('wx', 'x', 260, (125, 195), 30, 24, 30)
    b.gable_end('gable', 260, 80, 240, 78, 124)
    b.windows('loft', 'x', 260, (160,), 104, 20, 26, shutters=False)
    b.doorway('door', 'y', 245, 160, 8, 40, 66)
    b.part('ridge', 'a twisted straw rope along the ridge: holds the thatch down', sh.block(44, 276, 154, 166, 198, 208, 'beam'), 'detail', True)
    b.part('pot', 'a chimney pot', sh.block(76, 94, 106, 124, 216, 230, 'quarry'), 'detail', True)
    b.part('woodpile', 'split logs stacked by the door for the hearth', sh.block(196, 250, 244, 262, 8, 34, 'timber'), 'detail', True)
    b.part('lantern', 'a crystal lantern by the door', sh.cyl((128, 248, 60), (128, 248, 76), 5, 'glow', 1.5, seg=5), 'accent', True)
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
    for i, z in enumerate((40, 96)): b.part(f'band{i}', 'an iron-bound stone course round the tower: the hoops that hold it against the shake of the sails', sh.lathe([(76 - z * .12, z), (76 - z * .12, z + 9)], 'quarry', 10).move(130, 130, 0), 'detail', True)
    b.part('window', 'a lit window in the tower: the miller is at work', sh.block(190, 196, 118, 142, 96, 132, 'window'), 'opening', True)
    b.doorway('door', 'y', 206, 130, 0, 36, 84)
    b.finial('finial', 130, 130, 214, glow=False)
    b.part('millstone', 'a worn millstone leaned by the door: says "mill" even with the sails still', sh.cyl((70, 216, 26), (70, 226, 26), 26, 'quarry', seg=12), 'signature', True)
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
    b.part('block', 'the chopping block', sh.cyl((230, 110, 3), (230, 110, 34), 22, 'timber', seg=8), 'detail', True)
    b.post('axe_haft', 'an axe left in the block', (230, 110, 34), (252, 110, 74), 4, 'beam', free=True)
    b.part('axe_head', 'the axe head', sh.block(222, 240, 107, 113, 30, 44, 'iron'), 'detail', True)
    b.part('chips', 'a drift of chips and sawdust under the sawhorse', sh.block(50, 150, 215, 262, 3, 6, 'thatch'), 'detail', True)
    b.part('lantern', 'a crystal lantern on the shed post: work goes on at dusk', sh.cyl((204, 172, 70), (204, 172, 88), 6, 'glow', 2, seg=5), 'accent', True)
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
    b.quoins('hut', 50, 190, 50, 170, 3, 80)
    b.windows('w', 'x', 190, (110,), 30, 22, 28)
    b.doorway('door', 'y', 175, 119, 3, 38, 69)
    b.post('pick_haft', 'a pick leaned on the wall', (160, 178, 3), (176, 174, 70), 4, 'beam', free=True)
    b.part('pick_head', 'the pick head', sh.block(160, 192, 172, 177, 64, 72, 'iron'), 'detail', True)
    b.part('lantern', 'a miner\'s crystal lantern over the door', sh.cyl((119, 178, 84), (119, 178, 100), 6, 'glow', 2, seg=5), 'accent', True)
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
    b.quoins('forge', 50, 270, 50, 270, 6, 116)
    b.windows('w', 'y', 270, (90, 232), 50, 26, 34, shutters=False)
    b.windows('wx', 'x', 270, (200,), 50, 26, 34, shutters=False)
    b.gable_end('gable', 270, 50, 270, 116, 110)
    b.doorway('door', 'y', 275, 162, 6, 44, 94)
    b.part('ridge', 'a ridge beam capping the roof', sh.block(38, 282, 155, 165, 222, 231, 'beam'), 'detail', True)
    b.part('cap', 'a corbelled chimney cap: the stack that never stops smoking', sh.block(54, 122, 54, 122, 300, 314, 'quarry'), 'detail', True)
    b.part('glow', 'the fire seen up the flue', sh.block(70, 106, 70, 106, 314, 318, 'ember'), 'accent', True)
    b.part('horn', 'the anvil\'s horn', sh.block(376, 394, 186, 198, 38, 48, 'dark'), 'detail', True)
    b.part('water', 'water in the quenching trough', sh.block(306, 414, 284, 306, 28, 30, 'glow'), 'detail', True)
    b.part('ingots', 'a stack of iron bars waiting for the hammer', sh.block(396, 424, 200, 240, 6, 26, 'iron'), 'detail', True)
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
    b.quoins('weigh', 250, 390, 250, 390, 6, 130)
    b.windows('w', 'x', 390, (290, 350), 62, 24, 34)
    b.windows('wy', 'y', 390, (270, 370), 62, 20, 34, shutters=False)
    b.doorway('door', 'y', 395, 320, 6, 40, 94)
    b.finial('finial', 320, 320, 300)
    for i, (x, y, m) in enumerate(((100, 122, 'berry'), (480, 112, 'crop'), (90, 472, 'iron'), (490, 482, 'quarry'))):
        b.part(f'ware{i}', 'what the stall sells, heaped on the counter: colour that says "trade"', sh.lathe([(22, 46), (14, 60), (0, 68)], m, 7).move(x, y, 0), 'detail', True)
    b.part('well', 'the market well: every square has one', sh.lathe([(34, 6), (34, 36), (26, 36), (26, 6)], 'stone', 10).move(150, 300, 0), 'detail', True)
    b.part('well_water', 'water in the well', sh.lathe([(26, 26), (0, 26)], 'glow', 10).move(150, 300, 0), 'detail', True)
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
    b.part('quiver', 'a barrel of arrows by the shed', sh.cyl((300, 120, 3), (300, 120, 52), 20, 'timber', seg=8), 'detail', True)
    b.part('shafts', 'arrow shafts standing in the barrel', sh.cyl((300, 120, 52), (300, 120, 86), 14, 'thatch', 16, seg=6), 'detail', True)
    b.part('line', 'a pale shooting line across the lane', sh.block(60, 420, 196, 204, 3, 5, 'quarry'), 'detail', True)
    b.part('lantern', 'a crystal lantern on the shed', sh.cyl((434, 152, 80), (434, 152, 98), 6, 'glow', 2, seg=5), 'accent', True)
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
    b.framing('stalls', 40, 440, 40, 220, 8, 96, step=70)
    b.gable_end('gable', 440, 40, 220, 96, 110)
    b.windows('loft', 'x', 440, (130,), 126, 30, 36, lit=False, shutters=False)
    b.windows('wx', 'x', 440, (90, 170), 44, 22, 26, lit=False)
    b.part('ridge', 'a ridge beam capping the roof', sh.block(26, 454, 125, 135, 200, 209, 'beam'), 'detail', True)
    b.part('water', 'water in the trough', sh.block(76, 164, 334, 358, 34, 36, 'glow'), 'detail', True)
    b.part('saddle', 'a saddle on the fence: mounts are fitted here', sh.block(130, 160, 440, 460, 44, 62, 'team'), 'accent', True)
    return b, (480, 480)


def _logs(b, pts, h=92):
    for i, (x, y) in enumerate(pts):
        j = ((int(x) * 7 + int(y) * 13) % 5 - 2) * 4                                   # hand-cut: no two logs the same height
        b.part(f'log{i}', 'a sharpened log set in the ground; side by side they make the wall, and the points stop climbers', sh.lathe([(15, 0), (15, h - 22 + j), (0, h + j)], 'timber', 7).move(x, y, 0), 'body', True)


def _diag(g, d):
    """Turn a piece built along x through the tile centre onto a diagonal: d1 joins the (-1,-1) and (+1,+1)
    neighbours, d2 the (-1,+1) and (+1,-1) ones."""
    return g.move(-80, -80, 0).rz(45 if d == 'd1' else -45).move(80, 80, 0)


def _run(along, n=(-3, -2, -1, 1, 2, 3), step=26):
    """Where a wall piece stands in its tile: 'x' or 'y' = a straight run to its neighbours on that axis, 'c' = a
    corner, a crossing or a piece on its own (arms both ways)."""
    return [(80, 80)] + ([(80 + d * step, 80) for d in n] if along in 'xc' else []) + ([(80, 80 + d * step) for d in n] if along in 'yc' else [])


def palisade(along='c'):
    b = Block({'is': 'Palisade: a wall of sharpened logs', 'does': 'blocks movement; cheap, weak', 'gameplay': '1x1 tile, laid in lines in any direction: the tile must join its neighbours on all four sides and on diagonals',
               'built': 'logs set upright in a trench, lashed', 'made_of': 'timber', 'faction': 'the realm', 'references': ['AoE2 Palisade Wall', 'motte-and-bailey stockades'],
               'read_at_play_size': 'a clump of pointed stakes that runs into the next tile'})
    if along in ('d1', 'd2'):
        k = 1 if along == 'd1' else -1
        _logs(b, [(80 + d * 18.6, 80 + k * d * 18.6) for d in range(-4, 5)])
        for z in (30, 62):
            b.part(f'rail{z}', 'a split rail lashed across the logs: ties the run together so one cut log does not open it', _diag(sh.block(-28, 188, 76, 84, z, z + 7, 'timber'), along), 'detail', True)
        return b, (160, 160)
    _logs(b, _run(along))
    for z in (30, 62):
        if along in 'xc': b.part(f'railx{z}', 'a split rail lashed across the logs: ties the run together so one cut log does not open it', sh.block(0, 160, 92, 99, z, z + 7, 'timber'), 'detail', True)
        if along in 'yc': b.part(f'raily{z}', 'the same rail on a run the other way', sh.block(92, 99, 0, 160, z, z + 7, 'timber'), 'detail', True)
    if along == 'c': b.part('band', 'an iron band round the king post: it carries both runs', sh.lathe([(23, 70), (23, 82)], 'iron', 8).move(80, 80, 0), 'detail', True)
    if along == 'c': b.part('post', 'a taller, thicker corner post: where two runs meet the wall needs a king post, and it marks the turn', sh.lathe([(21, 0), (21, 96), (0, 126)], 'timber', 8).move(80, 80, 0), 'signature', True)
    return b, (160, 160)


def gate(along='c'):
    b = Block({'is': 'Palisade Gate', 'does': 'lets the owner\'s units through a palisade', 'gameplay': '1x1 tile; must read as an opening, not a wall',
               'built': 'two heavy posts, a lintel, plank doors', 'moves': 'the doors swing on the posts', 'made_of': 'timber', 'faction': 'the realm',
               'references': ['AoE2 Palisade Gate', 'stockade gates with a lintel beam'], 'read_at_play_size': 'two tall posts with a beam across and a dark gap between'})
    if along in ('d1', 'd2'):
        k = 1 if along == 'd1' else -1
        _logs(b, [(80 - 62, 80 - 62 * k), (80 + 62, 80 + 62 * k)], 120)
        b.part('lintel', 'beam tying the gateposts together across the gap', _diag(sh.block(-12, 172, 70, 90, 120, 138, 'timber'), along), 'signature', True)
        b.part('way', 'the trodden way through: darker ground says "you can pass here"', sh.block(34, 126, 34, 126, 0, 3, 'dark'), 'opening', True)
        b.part('badge', 'the owner\'s colour on the lintel: only their units pass', sh.block(64, 96, 64, 96, 138, 160, 'team'), 'accent', True)
        return b, (160, 160)
    _logs(b, ([(18, 80), (142, 80)] if along in 'xc' else []) + ([(80, 18), (80, 142)] if along in 'yc' else []), 120)
    if along in 'xc': b.part('lintel_x', 'beam tying the gateposts together across the gap', sh.block(8, 152, 70, 90, 120, 138, 'timber'), 'signature', True)
    if along in 'yc': b.part('lintel_y', 'the same beam for a wall running the other way', sh.block(70, 90, 8, 152, 120, 138, 'timber'), 'signature', True)
    if along == 'x':
        for i in range(2): b.part(f'leaf{i}', 'a plank door leaf, swung open inward so the way reads as open', sh.block(26 if not i else 126, 34 if not i else 134, 84, 132, 4, 112, 'timber'), 'detail', True)
    if along == 'y':
        for i in range(2): b.part(f'leaf{i}', 'a plank door leaf, swung open inward so the way reads as open', sh.block(84, 132, 26 if not i else 126, 34 if not i else 134, 4, 112, 'timber'), 'detail', True)
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


def stone_wall(along='c'):
    b = Block({'is': 'Stone Wall', 'does': 'blocks movement; strong', 'gameplay': '1x1 tile, laid in lines: fills its tile so neighbours join without gaps',
               'built': 'coursed stone with a wall-walk and merlons', 'made_of': 'stone', 'faction': 'the realm', 'references': ['AoE2 Stone Wall', 'curtain walls with crenellations'],
               'read_at_play_size': 'a pale solid block with a toothed top'})
    if along == 'c':                                   # a corner, a crossing or a lone piece: a squat turret the runs butt against
        b.part('wall', 'a square turret a little taller than the curtain: wall runs from either side end against it', sh.block(22, 138, 22, 138, 0, 112, 'stone'), 'body', True)
        b.part('skirt', 'a battered foot: thicker at the ground so it cannot be undermined', sh.block(12, 148, 12, 148, 0, 22, 'stone'), 'base', True)
        for i, (x, y) in enumerate(((40, 40), (120, 40), (120, 120), (40, 120))):
            b.part(f'merlon{i}', 'a merlon: cover on the wall-walk, and the teeth that say "fortification"', sh.block(x - 18, x + 18, y - 18, y + 18, 112, 140, 'stone'), 'signature')
        b.part('course', 'a projecting string course under the parapet: sheds rain off the face and breaks the plain box', sh.block(18, 142, 18, 142, 98, 106, 'stone'), 'detail', True)
        b.part('loop_x', 'an arrow loop on the face the camera sees', sh.block(138, 141, 74, 86, 46, 88, 'dark'), 'opening', True)
        b.part('loop_y', 'an arrow loop on the other seen face', sh.block(74, 86, 138, 141, 46, 88, 'dark'), 'opening', True)
        b.part('brazier', 'an iron fire basket on the turret: the watch keeps a light, and it marks the corners at a glance', sh.lathe([(8, 112), (15, 124), (13, 136)], 'iron', 8).move(80, 80, 0), 'accent', True)
        b.part('fire', 'the watch fire', sh.lathe([(11, 132), (6, 146), (0, 158)], 'ember', 6).move(80, 80, 0), 'accent', True)
        b.post('staff', 'a pennant staff: whose wall this is', (40, 40, 140), (40, 40, 196), 4, free=True, tag='accent')
        b.part('pennant', 'the owner\'s colour', sh.block(42, 74, 38, 42, 172, 194, 'team'), 'accent', True)
        return b, (160, 160)
    if along in ('d1', 'd2'):
        D = lambda g: _diag(g, along)
        b.part('wall', 'the curtain on a diagonal: corner to corner of the tile, so a slanting run has no steps or gaps', D(sh.block(-34, 194, 46, 114, 0, 92, 'stone')), 'body', True)
        b.part('skirt', 'a battered foot: thicker at the ground so it cannot be undermined', D(sh.block(-34, 194, 38, 122, 0, 18, 'stone')), 'base', True)
        b.part('walk', 'timber planks of the wall-walk', D(sh.block(-34, 194, 50, 96, 92, 95, 'timber')), 'detail', True)
        b.part('parapet', 'a low parapet on the outer edge of the wall-walk', D(sh.block(-34, 194, 96, 114, 92, 104, 'stone')), 'detail')
        for i, a in enumerate((-6, 52, 110, 168)):
            b.part(f'merlon{i}', 'a merlon: cover on the wall-walk, and the teeth that say "fortification"', D(sh.block(a - 17, a + 17, 96, 114, 104, 128, 'stone')), 'signature')
        return b, (160, 160)
    R = (lambda a0, a1, b0, b1, z0, z1, m: sh.block(a0, a1, b0, b1, z0, z1, m)) if along == 'x' else (lambda a0, a1, b0, b1, z0, z1, m: sh.block(b0, b1, a0, a1, z0, z1, m))
    b.part('wall', 'the curtain: a thick slab from edge to edge of the tile along its run, so pieces join without a gap', R(0, 160, 44, 116, 0, 92, 'stone'), 'body', True)
    b.part('skirt', 'a battered foot: thicker at the ground so it cannot be undermined', R(0, 160, 36, 124, 0, 18, 'stone'), 'base', True)
    b.part('parapet', 'a low parapet on the outer edge of the wall-walk', R(0, 160, 96, 116, 92, 104, 'stone'), 'detail')
    b.part('walk', 'timber planks of the wall-walk: where the defenders stand', R(0, 160, 48, 96, 92, 95, 'timber'), 'detail', True)
    b.part('course', 'a projecting string course under the parapet: sheds rain off the face and breaks the plain slab', R(0, 160, 116, 120, 78, 86, 'stone'), 'detail', True)
    b.part('buttress', 'a buttress in the middle of the bay: props the curtain and gives the long face a rhythm', R(66, 94, 116, 130, 0, 70, 'stone'), 'detail', True)
    b.part('loop', 'an arrow loop either side of the buttress', R(30, 38, 116, 118, 40, 72, 'dark'), 'opening', True)
    b.part('loop2', 'the second loop', R(122, 130, 116, 118, 40, 72, 'dark'), 'opening', True)
    for i, a in enumerate((26, 80, 134)):
        b.part(f'merlon{i}', 'a merlon: cover on the wall-walk, and the teeth that say "fortification"', R(a - 17, a + 17, 96, 116, 104, 128, 'stone'), 'signature')
    return b, (160, 160)


def stone_gate(along='c'):
    b = Block({'is': 'Stone Gate', 'does': 'lets the owner\'s units through a stone wall', 'gameplay': '1x1 tile; an arch with a dark way through, taller than the wall',
               'built': 'two stone piers, an arch, a gallery over it', 'moves': 'a portcullis drops in the arch', 'made_of': 'stone, timber', 'faction': 'the realm',
               'references': ['AoE2 Gate', 'castle gatehouses: passage between two piers with a room over'], 'read_at_play_size': 'a block taller than the wall with a dark doorway and a coloured cap'})
    if along == 'c':
        for i, (x0, x1, y0, y1) in enumerate(((4, 46, 4, 46), (114, 156, 4, 46), (114, 156, 114, 156), (4, 46, 114, 156))):
            b.part(f'pier{i}', 'a stone pier carrying the gallery', sh.block(x0, x1, y0, y1, 0, 110, 'stone'), 'body', True)
        b.part('gallery', 'the room over the gate where the portcullis is worked: makes the gate taller than the wall', sh.block(4, 156, 4, 156, 110, 150, 'stone'), 'signature')
        b.part('cap', 'low roof in the owner\'s colour: only their units pass', sh.pyramid(164, 164, 90, 'roof').move(-2, -2, 150), 'roof')
        b.part('way', 'the way through, dark under the arch', sh.block(46, 114, 46, 114, 0, 3, 'dark'), 'opening', True)
        b.part('shadow_x', 'darkness inside the passage seen from the right', sh.block(150, 154, 48, 112, 0, 104, 'dark'), 'opening', True)
        b.part('shadow_y', 'darkness inside the passage seen from the front', sh.block(48, 112, 150, 154, 0, 104, 'dark'), 'opening', True)
        return b, (160, 160)
    if along in ('d1', 'd2'):
        D = lambda g: _diag(g, along)
        for i, (a0, a1) in enumerate(((-34, 14), (146, 194))):
            b.part(f'pier{i}', 'a stone pier at each end of the gate: the slanting wall runs into it', D(sh.block(a0, a1, 30, 130, 0, 116, 'stone')), 'body', True)
        b.part('gallery', 'the room over the passage where the portcullis is worked: makes the gate taller than the wall', D(sh.block(-34, 194, 30, 130, 116, 152, 'stone')), 'signature')
        b.part('way', 'the way through, dark under the arch', D(sh.block(14, 146, 30, 130, 0, 3, 'dark')), 'opening', True)
        b.part('shadow', 'darkness inside the passage on the face the camera sees', D(sh.block(16, 144, 124, 128, 0, 112, 'dark')), 'opening', True)
        b.part('portcullis', 'the iron grille, drawn half up: says "gate" and "this opens"', D(sh.block(16, 144, 128, 132, 70, 114, 'iron')), 'detail', True)
        b.part('cap', 'low roof in the owner\'s colour: only their units pass', D(sh.pyramid(236, 108, 70, 'roof').move(-38, 26, 152)), 'roof')
        return b, (160, 160)
    R = (lambda a0, a1, b0, b1, z0, z1, m: sh.block(a0, a1, b0, b1, z0, z1, m)) if along == 'x' else (lambda a0, a1, b0, b1, z0, z1, m: sh.block(b0, b1, a0, a1, z0, z1, m))
    for i, (a0, a1) in enumerate(((0, 42), (118, 160))):
        b.part(f'pier{i}', 'a stone pier at each end of the gate, as deep as the wall is thick and a little more: the wall runs into it', R(a0, a1, 30, 130, 0, 116, 'stone'), 'body', True)
    b.part('gallery', 'the room over the passage where the portcullis is worked: makes the gate taller than the wall', R(0, 160, 30, 130, 116, 152, 'stone'), 'signature')
    b.part('way', 'the way through, dark under the arch', R(42, 118, 30, 130, 0, 3, 'dark'), 'opening', True)
    b.part('shadow', 'darkness inside the passage on the face the camera sees', R(44, 116, 124, 128, 0, 112, 'dark'), 'opening', True)
    b.part('portcullis', 'the iron grille, drawn half up: says "gate" and "this opens"', R(44, 116, 128, 132, 70, 114, 'iron'), 'detail', True)
    cap = sh.pyramid(168, 108, 70, 'roof').move(-4, 26, 152) if along == 'x' else sh.pyramid(108, 168, 70, 'roof').move(26, -4, 152)
    b.part('cap', 'low roof in the owner\'s colour: only their units pass', cap, 'roof')
    return b, (160, 160)


def farm(stage=0):
    b = Block({'is': 'Farm: a tilled field', 'does': 'one farmer works it for food until it is spent, then it is reseeded', 'gameplay': '3x3 tiles, walked over; must read as ground that is worked, not as a building: flat, striped, fenced low',
               'built': 'turf turned to furrows, sown in rows, a wattle fence against deer', 'serviced': 'the farmer walks the rows', 'made_of': 'soil, crops, timber', 'faction': 'the realm',
               'references': ['AoE2 Farm: a square of striped soil', 'medieval ridge-and-furrow strips', 'a scarecrow: the storybook mark of a field'],
               'read_at_play_size': 'a striped brown and gold square with a scarecrow'})
    S = 480
    b.part('soil', 'the tilled plot: dark turned earth the size of the field', sh.block(16, S - 16, 16, S - 16, 0, 5, 'soil'), 'base', True)
    for i in range(9):
        y = 46 + i * 48.5
        cut = stage == 2 or (stage == 1 and i % 2 == 0)                           # harvested rows are stubble: the field shows how much is left
        b.part(f'row{i}', 'a ridge of crops: the stripes that say "farm" from any distance; cut rows are low stubble', sh.block(34, S - 34, y - 13, y + 13, 5, 9 if cut else 22 + (i % 3) * 4, 'thatch' if cut else 'crop'), 'signature', True)
    for i, (x, y) in enumerate(((16, 16), (S - 16, 16), (S - 16, S - 16), (16, S - 16), (S / 2, 16), (16, S / 2))):
        b.post(f'stake{i}', 'a fence stake: the low fence marks the field edge and keeps deer off', (x, y, 0), (x, y, 44), 7, free=True)
    b.post('rail_a', 'the back fence rail (the front is left open so the rows show)', (16, 16, 32), (S - 16, 16, 32), 5)
    b.post('rail_b', 'the back fence rail on the other side', (16, 16, 32), (16, S - 16, 32), 5)
    b.post('pole', 'the scarecrow\'s pole', (120, 120, 0), (120, 120, 150), 6, free=True, tag='signature')
    b.part('arms', 'the scarecrow\'s arms', sh.block(117, 123, 76, 164, 109, 115, 'timber'), 'signature', True)
    b.part('coat', 'a ragged coat in the owner\'s colour: whose field this is', sh.block(112, 128, 96, 144, 62, 118, 'team'), 'accent', True)
    b.part('head', 'a sack head with a hat: a scarecrow, the storybook mark of a field', sh.pyramid(52, 52, 40, 'thatch').move(94, 94, 148), 'signature', True)
    return b, (S, S)


def site(n=2):
    """The building site every foundation starts as (AoE2 uses one construction picture per footprint size)."""
    S = 160 * n
    b = Block({'is': f'Building site, {n}x{n} tiles', 'does': 'shows where a building is going up and how big it will be', 'gameplay': 'must not be mistaken for a finished building: low, open, earth-coloured',
               'built': 'turf cut away, corner stakes, scaffold poles, materials piled ready', 'made_of': 'earth, timber, stone', 'faction': 'the realm',
               'references': ['AoE2 construction sites: a rectangle of bare ground with stakes and a frame', 'medieval building sites: putlog scaffolds of lashed poles'],
               'read_at_play_size': 'a square of bare earth with poles at the corners'})
    m = 14
    b.part('ground', 'turf stripped to bare earth: the exact footprint the building will take', sh.block(m, S - m, m, S - m, 0, 3, 'soil'), 'base', True)
    t = m + 22
    for i, (x0, x1, y0, y1) in enumerate(((t, S - t, t, t + 12), (t, S - t, S - t - 12, S - t), (t, t + 12, t, S - t), (S - t - 12, S - t, t, S - t))):
        b.part(f'trench{i}', 'a foundation trench: where the walls will stand', sh.block(x0, x1, y0, y1, 3, 4, 'dark'), 'base', True)
    b.part('spoil', 'the heap of dug earth beside the trench', sh.rock(34 + 6 * n, 'soil', seed=3 + n, flatten=.5).move(m + 46, S - m - 40, 3), 'detail', True)
    H = 60 if n == 1 else 150
    for i, (x, y) in enumerate(((m + 8, m + 8), (S - m - 8, m + 8), (S - m - 8, S - m - 8), (m + 8, S - m - 8))):
        b.post(f'pole{i}', 'a scaffold pole at each corner: the frame the walls rise inside', (x, y, 0), (x, y, H), 7, free=True)
    if n > 1:
        c = ((m + 8, m + 8), (S - m - 8, m + 8), (S - m - 8, S - m - 8), (m + 8, S - m - 8))
        for i in range(4):
            (x0, y0), (x1, y1) = c[i], c[(i + 1) % 4]
            b.post(f'ledger{i}', 'a ledger lashed between the poles: ties the scaffold and carries the working planks', (x0, y0, H - 46), (x1, y1, H - 46), 5)
        b.part('timber', 'a stack of beams waiting to be raised', sh.block(S * .5 - 50, S * .5 + 50, S - m - 46, S - m - 20, 4, 22, 'timber'), 'detail', True)
        b.part('stone', 'a heap of cut stone waiting for the masons', sh.rock(26, 'stone', seed=n).move(S - m - 50, S * .5, 4), 'detail', True)
    return b, (S, S)


def rubble(n=2):
    """What a destroyed building leaves (AoE2 leaves a rubble picture per footprint size that fades away)."""
    import random
    S = 160 * n; rnd = random.Random(40 + n)
    b = Block({'is': f'Rubble, {n}x{n} tiles', 'does': 'marks where a building stood', 'gameplay': 'flat and dark: units walk over it, so it must not read as an obstacle',
               'built': 'fallen, burnt', 'made_of': 'scorched earth, broken stone, charred beams', 'faction': 'none',
               'references': ['AoE2 rubble'], 'read_at_play_size': 'a dark patch with a few stones and sticks'})
    b.part('scorch', 'burnt ground the size of the footprint: the building\'s ghost', sh.block(26, S - 26, 26, S - 26, 0, 3, 'earth'), 'base', True)
    b.part('ash', 'a darker heart of ash where the fire was hottest', sh.block(S * .3, S * .7, S * .3, S * .7, 3, 4, 'dark'), 'base', True)
    for i in range(3 + 4 * n):
        r = rnd.uniform(10, 16 + 5 * n)
        b.part(f'stone{i}', 'a block from the fallen wall', sh.rock(r, 'stone', seed=i * 7 + n).move(rnd.uniform(34, S - 34), rnd.uniform(34, S - 34), 2), 'detail', True)
    for i in range(1 + 2 * n):
        x, y = rnd.uniform(40, S - 40), rnd.uniform(40, S - 40); a = rnd.uniform(0, 6.28); L = rnd.uniform(40, 40 + 22 * n)
        import math
        b.post(f'beam{i}', 'a charred beam lying where the roof came down', (x, y, 5), (min(S - 20, max(20, x + math.cos(a) * L)), min(S - 20, max(20, y + math.sin(a) * L)), rnd.uniform(5, 14 + 10 * n)), 8, 'dark', free=True)
    return b, (S, S)


CATALOG = {'town_hall': town_hall, 'cottage': cottage, 'mill': mill, 'lumber_camp': lumber_camp, 'mining_camp': mining_camp, 'blacksmith': blacksmith, 'market': market,
           'barracks': barracks, 'archery_range': archery_range, 'stable': stable, 'palisade': palisade, 'gate': gate, 'watchpost': watchpost, 'watch_tower': watch_tower,
           'stone_wall': stone_wall, 'stone_gate': stone_gate, 'farm': farm, 'farm_1': lambda: farm(1), 'farm_2': lambda: farm(2)}
# wall pieces that run straight to their neighbours ('_x', '_y'; the plain key is the corner, crossing or lone piece),
# and the pictures every building shares: its site while it goes up and its rubble after it falls, per footprint size
for _k, _f in (('palisade', palisade), ('gate', gate), ('stone_wall', stone_wall), ('stone_gate', stone_gate)):
    for _a in 'xy': CATALOG[f'{_k}_{_a}'] = (lambda f=_f, a=_a: f(a))
for _k, _f in (('palisade', palisade), ('stone_wall', stone_wall), ('gate', gate), ('stone_gate', stone_gate)):   # slanting runs (AoE2 walls run on diagonals too)
    for _a in ('d1', 'd2'): CATALOG[f'{_k}_{_a}'] = (lambda f=_f, a=_a: f(a))
for _n in (1, 2, 3, 4):
    CATALOG[f'site_{_n}'] = (lambda n=_n: site(n)); CATALOG[f'rubble_{_n}'] = (lambda n=_n: rubble(n))
