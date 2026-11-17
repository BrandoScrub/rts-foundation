"""Shadows are an addition (artkit/shadow.py): a pack without "shadow" writes exactly what it wrote before, and a pack
with it gets the same sprites plus shadow pictures and a unit shadow layer "S".

  python3 artkit/tests/shadow_check.py      prints PASS (about 20 seconds)

Checks: no section -> no shadow files or keys; with it -> sprites byte-identical, a shadow per stage placed by the
same near corner, falling down-right on screen in the isometric AND the top-down camera, never darker than its
opacity, overlapping parts not darkened twice; a floating camera ("ground": null) lifts the shadow away; units gain an
"S" layer that packs like the others.
"""
import os, shutil, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
from artkit.style import Style
from artkit.export import Exporter
from artkit.recipe import Asset
from artkit.core.space import Camera
from artkit.demo.frontier import build as F
from artkit import shadow as S
from artkit import shapes as sh

bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)

base = Style.load('frontier_outpost')
check(base.shadow is None and S.Shadow.from_pack(None) is None, 'the demo pack has no shadow: nothing changes for it')
rules = S.Shadow(length=0.6, opacity=0.4)
shad = Style(base.root, dict(base.cfg, shadow={'length': 0.6, 'opacity': 0.4}))
dome = os.path.join(ROOT, 'artkit', 'demo', 'frontier', 'recipes', 'hab_dome.json')

tmp = tempfile.mkdtemp(prefix='artkit_shadow_')
A, B = os.path.join(tmp, 'plain'), os.path.join(tmp, 'shadow')
ra = Exporter(base, A, log=lambda *a: None).static('hab', Asset.load(dome), headings=2)
exb = Exporter(shad, B, log=lambda *a: None); rb = exb.static('hab', Asset.load(dome), headings=2)
check(not any('_shadow' in f for f in os.listdir(A)) and all('shadow' not in m for m in ra['states'].values()),
      'no shadow: no files, no keys')
same = lambda a, b: np.array_equal(np.asarray(Image.open(a)), np.asarray(Image.open(b)))
check(all(same(os.path.join(A, m['src']), os.path.join(B, m['src'])) for m in ra['states'].values()), 'shadow: sprites byte-identical')
check(all('shadow' in m and os.path.exists(os.path.join(B, m['shadow']['src'])) for m in rb['states'].values()), 'shadow: one per stage')
m = rb['states']['normal']; s_ = m['shadow']
a = np.asarray(Image.open(os.path.join(B, s_['src'])))[..., 3].astype(float)
check(a.max() <= 0.4 * 255 + 1, f'never darker than its opacity ({a.max():.0f} <= {0.4 * 255:.0f})')
spr = np.asarray(Image.open(os.path.join(B, m['src'])))[..., 3].astype(float)
cen = lambda w: (np.array([(w.sum(0) * np.arange(w.shape[1])).sum(), (w.sum(1) * np.arange(w.shape[0])).sum()]) / w.sum())
d = (cen(a) - np.array(s_['near_corner'])) - (cen(spr) - np.array(m['near_corner']))
check(d[0] > 2 and d[1] > 0, f'isometric: the shadow falls down and right of the building ({d[0]:.1f}, {d[1]:.1f} px)')

# the same rules in other cameras: a tower in each view's own axes
tower = sh.box(40, 40, 120, 'hull')
def offset(cam):
    T = S.cast(tower, cam, rules); top = T.reshape(-1, 2)
    fx, fy = cam.screen(np.array([20.0, 20.0, 0.0 if cam.ground is None else cam.ground]))
    return top[:, 0].mean() - float(fx), top[:, 1].mean() - float(fy)
dx, dy = offset(Camera.top_down())
check(dx > 0 and dy > 0, f'top-down: the shadow falls down and right on screen too ({dx:.1f}, {dy:.1f} units)')
gx, gy = S.ground_step(Camera.ISO, rules)
check(abs(gx - 0.6) < 1e-9 and abs(gy) < 1e-9, 'isometric default dir [2, 1] is along model +x')
fly = Camera.top_down(ground=None)
check(np.hypot(*offset(fly)) > np.hypot(*offset(Camera.top_down())), 'ground: null lifts the shadow away from the thing')

# overlapping parts: one coverage, not two
two = sh.box(40, 40, 60, 'hull') + sh.box(40, 40, 60, 'hull').move(10, 10)
im, _ = S.picture(two, rules)
check(np.asarray(im)[..., 3].max() <= 0.4 * 255 + 1, 'overlapping parts do not darken twice')

# units: an "S" layer, packed with the rest
rig, clips = F.strider(); rig.headings = 2
man = exb.rig('strider', rig, [c for c in clips if c.name == 'walk'])
check('S' in man['layers'] and 'S' in man['clips']['walk']['files'], 'unit: shadow layer S in the manifest')
sa = np.asarray(Image.open(os.path.join(B, man['clips']['walk']['files']['S'])))
check(sa[..., 3].max() > 0 and sa[..., 3].max() <= 0.4 * 255 + 1, 'unit: the shadow strip draws, within its opacity')
exb.save()
check('rects' in exb.assets['strider']['clips']['walk'] and 'S' in exb.assets['strider']['clips']['walk']['rects'], 'unit: S packs like L and U')

shutil.rmtree(tmp, ignore_errors=True)
print('FAIL' if bad else 'PASS'); sys.exit(1 if bad else 0)
