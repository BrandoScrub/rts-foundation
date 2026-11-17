"""The clearance check (artkit/clearance.py) finds what it says it finds.

  python3 artkit/tests/clearance_check.py      prints PASS (a second)

A wheel beside a hull is clear; pushed into the hull it is a clash of the depth it was pushed; the same pair listed
in `allow` is clear again; a part below the ground is a clash with 'ground', unless ground=None; the worst clash
comes first; a part is never tested against itself.
"""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
from artkit import shapes as S, clearance

bad = []
def expect(what, ok):
    if not ok: bad.append(what); print('FAIL', what)

hull = S.block(0, 100, 0, 60, 10, 50, 'steel')
wheel = lambda x, z=0: S.block(x, x + 20, 20, 40, z, z + 20, 'rubber')

r = clearance.check({'hull': hull, 'wheel': wheel(110)}, solids=['hull'], movers=['wheel'])
expect('a part beside a solid is clear', r == [])

r = clearance.check({'hull': hull, 'wheel': wheel(92, 20)}, solids=['hull'], movers=['wheel'])
expect('a part pushed 8 units into a solid is a clash of 8', len(r) == 1 and r[0][:2] == ('wheel', 'hull') and abs(r[0][2] - 8) < 0.01)

r = clearance.check({'hull': hull, 'wheel': wheel(92, 20)}, solids=['hull'], movers=['wheel'], allow={('hull', 'wheel')})
expect('an allowed pair is clear (either order)', r == [])

r = clearance.check({'hull': hull, 'wheel': wheel(99.8, 20)}, solids=['hull'], movers=['wheel'])
expect('a touch inside the tolerance is clear', r == [])

r = clearance.check({'hull': hull, 'wheel': wheel(110, -6)}, solids=['hull'], movers=['wheel'])
expect('a part 6 units below the ground clashes with the ground', len(r) == 1 and r[0][1] == 'ground' and abs(r[0][2] - 6) < 0.01)

r = clearance.check({'hull': hull, 'wheel': wheel(110, -6)}, solids=['hull'], movers=['wheel'], ground=None)
expect('ground=None: nothing is below the ground', r == [])

r = clearance.check({'hull': hull, 'a': wheel(97, 20), 'b': wheel(88, 20)}, solids=['hull'], movers=['a', 'b'])
expect('the worst clash comes first', [x[0] for x in r] == ['b', 'a'])

r = clearance.check({'hull': hull}, solids=['hull'], movers=['hull'])
expect('a part is not tested against itself', r == [])

print('PASS' if not bad else f'{len(bad)} FAILED')
sys.exit(1 if bad else 0)
