"""artkit's light check: the pack's "light" section (core.light.Rules) is an addition, never a change.

  python3 artkit/tests/light_check.py

1. No "light" section -> style.lighting is None and pictures are byte-identical with lighting=None, and with a Rules()
   that sets nothing (relief 0, engine AO and ink constants).
2. relief darkens what lies behind the picture's nearest point and leaves the nearest point alone; it works in the
   top-down camera (a box on a plate: the plate gets darker, the box top does not).
3. ao and ink values are used (a softer ink cover lightens the line pixels).
4. Pack parsing: missing -> None; unknown keys and an ink cover outside 0..1 are refused.
5. The line weight hierarchy (ink width, inner, step, crease): creases draw a box's own edges, thinner inner lines and a
   narrower outline use less ink, width 1 / inner 1 is exactly the old pass, a lower step draws small ledges.
About 10 seconds.
"""
import glob, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit.style import Style
from artkit.recipe import Asset
from artkit import sprite, shapes as sh
from artkit.core.light import Rules
from artkit.core.space import Camera

fails = []
check = lambda ok, what: (print(('ok   ' if ok else 'FAIL ') + what), ok or fails.append(what))

st = Style.load('frontier_outpost')
check(st.lighting is None, 'demo pack has no "light" section -> style.lighting is None')
g = Asset.load(sorted(glob.glob(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', '*.json')))[0]).base()

# 1. untouched by default
a, _ = sprite.picture(g, st, scale=0.4)
b, _ = sprite.picture(g, st, scale=0.4, lighting=Rules())
check(np.array_equal(np.asarray(a), np.asarray(b)), 'Rules() with nothing set draws exactly the default picture')

# 2. relief in the top-down camera: a short box standing on a wide plate
td = Camera.top_down(ground=None)
mat = sorted(st.materials().tiles)[0]
geo = sh.box(80, 80, 4, mat) + sh.box(20, 20, 30, mat).move(30, 30, 4)
p0, m0 = sprite.picture(geo, st, scale=1.0, camera=td, pad=4)
p1, m1 = sprite.picture(geo, st, scale=1.0, camera=td, pad=4, lighting=Rules(relief_strength=0.5, relief_span=30))
A0, A1 = np.asarray(p0).astype(float), np.asarray(p1).astype(float)
ox, oy = m0['origin']
top = (int(oy + 40), int(ox + 40))          # centre of the tall box's top (model 40, 40)
plate = (int(oy + 10), int(ox + 10))        # the plate, 30 units below it
check(abs(A1[top][:3].mean() - A0[top][:3].mean()) < 2, 'relief leaves the nearest point alone')
check(A1[plate][:3].mean() < A0[plate][:3].mean() * 0.65, 'relief darkens what lies one span behind (about by strength)')

# 3. ao and ink are honoured
p2, _ = sprite.picture(g, st, scale=0.4, lighting=Rules(ink_cover=0.3))
check(not np.array_equal(np.asarray(a), np.asarray(p2)) and np.asarray(p2)[..., :3].astype(float).mean() > np.asarray(a)[..., :3].astype(float).mean(),
      'a softer ink cover lightens the lines')
p3, _ = sprite.picture(g, st, scale=0.4, lighting=Rules(ao_strength=0.0))
check(np.asarray(p3)[..., :3].astype(float).mean() >= np.asarray(a)[..., :3].astype(float).mean(), 'ao strength 0 removes occlusion darkening')

# 4. parsing
check(Rules.from_pack(None) is None and Rules.from_pack({}) is None, 'missing section -> None')
r = Rules.from_pack({'relief': {'strength': 0.4, 'span': 50}, 'ao': {'radii': [[2, 1]]}, 'ink': {'cover': 0.7}})
check(r.relief_strength == 0.4 and r.relief_span == 50 and r.ao_radii == ((2.0, 1.0),) and r.ink_cover == 0.7, 'parses relief, ao, ink')
for bad in ({'glow': 1}, {'ink': {'cover': 2}}, 'bright'):
    try: Rules.from_pack(bad); check(False, f'refuses {bad!r}')
    except ValueError: check(True, f'refuses {bad!r}')
check(Rules.from_pack({'relief': {'ref': 0.5}}).relief_ref == 0.5 and r.relief_ref == 1.0, 'relief ref parses, default 1')
try: Rules.from_pack({'relief': {'ref': 0}}); check(False, 'refuses ref 0')
except ValueError: check(True, 'refuses ref 0')
mast = geo + sh.box(2, 2, 200, mat).move(10, 70, 4)          # one thin tall mast
q0, _ = sprite.picture(mast, st, scale=1.0, camera=td, pad=4, lighting=Rules(relief_strength=0.5, relief_span=30))
q1, mq = sprite.picture(mast, st, scale=1.0, camera=td, pad=4, lighting=Rules(relief_strength=0.5, relief_span=30, relief_ref=0.9))
t1 = (int(mq['origin'][1] + 40), int(mq['origin'][0] + 40))
check(np.asarray(q1)[t1][:3].astype(float).mean() > np.asarray(q0)[t1][:3].astype(float).mean() + 10,
      'a quantile ref stops one thin mast from darkening the rest')
check(r.with_(relief_span=90).relief_span == 90 and r.relief_span == 50, 'with_ copies')

# 5. the line weight hierarchy (light.ink: width, inner, step, crease, crease_width)
check(not Rules().weighted and Rules(ink_cover=0.5).weighted is False, 'cover alone keeps the old line pass')
lw = Rules.from_pack({'ink': {'width': 0.8, 'inner': 0.5, 'step': 4, 'crease': 35, 'crease_width': 0.4}})
check(lw.weighted and (lw.ink_width, lw.ink_inner, lw.ink_step, lw.ink_crease, lw.ink_crease_width) == (0.8, 0.5, 4.0, 35.0, 0.4),
      'ink width / inner / step / crease / crease_width parse')
for bad in ({'ink': {'thick': 1}}, {'ink': {'inner': 2}}, {'ink': {'crease': 0}}):
    try: Rules.from_pack(bad); check(False, f'refuses {bad}')
    except ValueError: check(True, f'refuses {bad}')
ink_px = lambda im: int(((np.asarray(im)[..., :3].astype(int).max(2) < 70) & (np.asarray(im)[..., 3] > 128)).sum())
mat = 'hull' if 'hull' in st.materials() else mat          # a light surface, so only lines are dark
cube = sh.box(60, 60, 60, mat)                       # one box: its own edges have no depth step
c0, _ = sprite.picture(cube, st, scale=1.0)
cc, _ = sprite.picture(cube, st, scale=1.0, lighting=Rules(ink_crease=35))
check(ink_px(cc) > ink_px(c0) + 40, f'crease lines draw a box\'s own edges ({ink_px(c0)} -> {ink_px(cc)} ink px)')
steps = sh.box(80, 80, 20, mat) + sh.box(40, 40, 20, mat).move(20, 20, 20)
s0, _ = sprite.picture(steps, st, scale=1.0)
si, _ = sprite.picture(steps, st, scale=1.0, lighting=Rules(ink_inner=0.4))
check(ink_px(si) < ink_px(s0), f'thinner inner lines use less ink ({ink_px(s0)} -> {ink_px(si)})')
sw, _ = sprite.picture(steps, st, scale=1.0, lighting=Rules(ink_width=0.5))
check(ink_px(sw) < ink_px(s0), f'a narrower outline uses less ink ({ink_px(s0)} -> {ink_px(sw)})')
same_w, _ = sprite.picture(steps, st, scale=1.0, lighting=Rules(ink_width=1.0, ink_inner=1.0))
check(np.array_equal(np.asarray(same_w), np.asarray(s0)), 'width 1 and inner 1 draw exactly the old lines')
lip = sh.box(80, 80, 30, mat) + sh.box(84, 84, 3, mat).move(-2, -2, 30)    # a 3-unit ledge
l0, _ = sprite.picture(lip, st, scale=1.0)
l1, _ = sprite.picture(lip, st, scale=1.0, lighting=Rules(ink_step=2))
check(ink_px(l1) > ink_px(l0), 'a lower step draws small ledges')

print('PASS' if not fails else f'FAIL ({len(fails)})')
sys.exit(1 if fails else 0)
