"""The machine check (artkit/machine.py) finds what it says it finds, and the demo tank passes it.

  python3 artkit/tests/machine_check.py      prints PASS (about 15 seconds)

A small clean machine (body, an arm, a wheel, a turret) comes back clean; then one fault at a time is put in and the
right kind of issue must come back: NO REASON, NO MOUNT, FLOATING, CLASH (also only when a turret turns), OFF AXIS,
TRACK OFF WHEEL, GROUND, TOO SMALL. Also: shapes.belt_path wraps every circle of a simple loop, the belt is one
closed band, and the M4A3 blockout has no issues.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit import shapes as sh
from artkit.machine import Machine

bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)


def base(**fault):
    """A cart: a body on two wheels each side on arms, a track round the left pair, a turret on top."""
    m = Machine('cart')
    m.add('body', sh.box(120, 60, 30, 'hull').move(0, 0, 30), 'the body' if not fault.get('no_reason') else '')
    for side, y in (('l', -12), ('r', 60)):
        for k, x in enumerate((25, 95)):
            arm = f'arm_{side}{k}'
            m.add(arm, sh.box(8, 12, 24, 'steel').move(x - 4, y if side == 'r' else y, 16), 'holds the wheel', on='body')
            wy = (y - 10 if side == 'l' else y + 12)
            wy -= fault.get('float_wheel', 0) if (side, k) == ('l', 0) else 0
            off = fault.get('off_axis', 0) if (side, k) == ('r', 1) else 0
            m.add(f'wheel_{side}{k}', sh.cyl((x + off, wy, 16), (x + off, wy + 10, 16), 16, 'rubber', seg=16),
                  'rolls', on=arm, turns=((x, wy + 5, 16), (0, 1, 0)))
    m.add('turret', sh.lathe([(24, 0), (24, 16), (0, 16)], 'hull', n=16).move(60, 30, 60), 'turns the gun', on='body',
          turns=((60, 30, 60), (0, 0, 1)))
    m.add('gun', sh.box(60, 8, 8, 'steel').move(84, 26, 64), 'the gun', on='turret')
    return m

clean = base().check()
check(clean == [], f'a clean machine has no issues {clean}')
has = lambda m, kind: any(i.startswith(kind) for i in m.check())
check(has(base(no_reason=True), 'NO REASON'), 'NO REASON: a part with no why')
m = base(); m.add('stray', sh.box(4, 4, 4, 'x'), 'a stray part', on='nothing'); check(has(m, 'NO MOUNT'), 'NO MOUNT: a mount that does not exist')
m = base(); m.add('second_root', sh.box(10, 10, 10, 'x').move(0, 0, 70), 'two roots'); check(has(m, 'NO MOUNT'), 'NO MOUNT: two roots')
check(has(base(float_wheel=12), 'FLOATING'), 'FLOATING: a wheel 12 units out from its arm')
m = base(); m.add('box_in_body', sh.box(30, 30, 30, 'x').move(40, 15, 40), 'a box sunk in the body', on='turret')
check(has(m, 'CLASH'), 'CLASH: a part through another it is not mounted on')
m = base(); m.add('mast', sh.box(6, 6, 50, 'steel').move(10, 27, 60), 'a mast on the body', on='body')
m.parts['gun'].geom = sh.box(70, 8, 8, 'steel').move(84, 26, 64)
iss = m.check(); turned = [i for i in iss if 'turned' in i]
check(not [i for i in iss if i.startswith('CLASH') and 'turned' not in i] and turned, 'CLASH with a turret turned: the gun hits a mast only when it turns')
check(has(base(off_axis=6), 'OFF AXIS'), 'OFF AXIS: a wheel 6 units off its axle')
m = base(); m.add('sunk', sh.box(10, 10, 10, 'x').move(50, 25, -8), 'below ground', on='body', contact=['body'], small_ok=True)
check(has(m, 'GROUND'), 'GROUND: something below the ground')
m = base(); m.add('rivet', sh.box(2, 2, 2, 'steel').move(10, 10, 60), 'a rivet', on='body'); check(has(m, 'TOO SMALL'), 'TOO SMALL: a 2-unit rivet')

# belts
path, wraps = sh.belt_path([(0, 0, 10), (100, 0, 10), (100, 40, 10), (0, 40, 10)])
check(all(w is not None and abs(w - 90) < 1e-6 for w in wraps) and path[0] == path[-1], 'belt_path wraps each corner 90 degrees, closed')
_, wraps = sh.belt_path([(0, 0, 10), (100, 0, 10), (80, 20, 5), (100, 40, 10), (0, 40, 10)])
check(wraps[2] is None, 'belt_path: a circle inside the loop cannot be wrapped (None)')
m = base()
m.belt('track', [(25, 16, 16), (95, 16, 16)], -12, -2, 4, 'rubber', why='the track', on='wheel_l1', wraps=['wheel_l0', 'wheel_l1'])
check(not [i for i in m.check() if i.startswith('TRACK')], f'a track round two wheels rides on both')
m = base()
m.belt('track', [(25, 16, 22), (95, 16, 16)], -12, -2, 4, 'rubber', why='the track', on='wheel_l1', wraps=['wheel_l0', 'wheel_l1'])
check(has(m, 'TRACK OFF WHEEL'), 'TRACK OFF WHEEL: a track sized for a bigger wheel')


# a Machine as a unit: MachineRig through Exporter.rig (the runtime's format, nothing new)
import tempfile
from PIL import Image
from artkit.style import Style
from artkit.export import Exporter
m = base()
m.belt('track', [(25, 16, 16), (95, 16, 16)], -12, -2, 4, 'rubber', why='the track', on='wheel_l1', wraps=['wheel_l0', 'wheel_l1'],
       teeth=(9, 4, 2))
r = m.rig((60, 30, 0), upper=['turret'], muzzle=(144, 30, 68), recoil=['gun'], headings=2)
check(r.layered and 'gun' in r.top and 'body' not in r.top, 'MachineRig: the turret subtree is the top layer')
mv, fi = r.move(frames=4), r.fire()
check(abs(mv.stride - 9) < 1e-9 and fi.layers == ('U',), 'move cycles over one track pitch; fire is top-layer only')
g0, _ = r.build(mv.poses()[0], 0, 'L'); g1, _ = r.build(mv.poses()[1], 0, 'L')
check(not np.allclose(g0.P.mean((0, 1)), g1.P.mean((0, 1))) or len(g0) == len(g1) and not np.allclose(g0.P, g1.P),
      'the track runs between move frames')
_, k0 = r.build(r.pose(), 90, 'U'); _, k1 = r.build(r.pose(turret=90), 0, 'U')
check(np.allclose(k0['muzzle'], k1['muzzle'], atol=1e-6), 'turning the turret 90 = turning the whole unit 90, for the muzzle')
out = tempfile.mkdtemp(prefix='artkit_mrig_')
man = Exporter(Style.load('frontier_outpost'), out, log=lambda *a: None).rig('cart', r, [r.idle(frames=1), mv, fi])
check(set(man['layers']) == {'L', 'U'} and 'socket' in man['clips']['move'] and man['clips']['move']['stride_units'] == 9,
      'Exporter.rig takes it: L and U layers, sockets, stride in the manifest')
a = np.asarray(Image.open(os.path.join(out, man['clips']['move']['files']['L'])))
fw = man['layers']['L']['frame'][0]
check(not np.array_equal(a[:, :fw], a[:, fw:2 * fw]), 'exported move frames differ (the track runs)')

# the demo tank
from artkit.demo.blockouts import m4_medium_tank as tank
iss = tank.check()
check(iss == [], f'the M4A3 blockout passes ({len(iss)} issues)' + ('' if not iss else ': ' + '; '.join(iss[:3])))

print('FAIL' if bad else 'PASS'); sys.exit(1 if bad else 0)
