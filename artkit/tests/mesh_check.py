"""artkit's mesh check: models out as OBJ, paint back in, nothing else changed.

  python3 artkit/tests/mesh_check.py

1. Round trip: a model wearing its own baked atlas draws the same as the model (alpha exact, colour within a few
   levels: the atlas resamples each tile once), for flat and smooth faces, decals, every facing and every stage.
2. OBJ: the file parses back to the same triangle count, every texture coordinate inside 0..1, Y-up.
3. Projection: paint drawn over a view lands on the faces seen in it and changes them in later renders, faces hidden
   in that view stay as they were, and a layer with transparency and a flattened image give the same result.
4. A layout refuses a different model.
About 40 seconds.
"""
import os, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit.style import Style
from artkit.recipe import Asset
from artkit import mesh, sprite

fails = []
check = lambda ok, what: (print(('ok   ' if ok else 'FAIL ') + what), ok or fails.append(what))
st = Style.load('frontier_outpost'); mats = st.materials()
R = lambda n: os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', n)
tmp = tempfile.mkdtemp(prefix='artkit_mesh_')


def same(a, b, tol=4):
    A, B = np.asarray(a).astype(int), np.asarray(b).astype(int)
    if A.shape != B.shape: return False, 'size'
    solid = A[..., 3] > 0
    d = np.abs(A[..., :3] - B[..., :3]).max(-1)[solid]
    return (A[..., 3] == B[..., 3]).all() and np.percentile(d, 99) <= tol and d.mean() < 1, f'mean {d.mean():.2f}, p99 {np.percentile(d, 99):.0f}'


# 1. round trip
for name in ('laser_turret.json', 'landing_pad.json'):            # smooth faces + turning part; decals
    a = Asset.load(R(name)); lay = mesh.unwrap(a.geom, mats=mats); atlas = mesh.bake(a.geom, lay, mats)
    pa = mesh.paint_asset(a, lay, atlas, mats, name='paint:' + name)
    for q in (0, 1, 2, 3):
        f, g = a.facing(q), pa.facing(q)
        ok, why = same(sprite.picture(f.geom, st, footprint=f.footprint)[0], sprite.picture(g.geom, st, footprint=g.footprint)[0])
        check(ok, f'{name} facing {q}: painted with its own bake draws the same ({why})')
    s0, s1 = a.states(), pa.states()
    for k in s0:
        ok, why = same(sprite.picture(s0[k], st, footprint=a.footprint)[0], sprite.picture(s1[k], st, footprint=a.footprint)[0], tol=6)
        check(ok and set(s0) == set(s1), f'{name} stage {k} follows the paint ({why})')
    for pv in a.pivots:
        ok, why = same(sprite.picture(a.turning(pv, 70), st, footprint=a.footprint)[0], sprite.picture(pa.turning(pv, 70), st, footprint=a.footprint)[0])
        check(ok, f'{name} turning part {pv} follows the paint ({why})')

# 2. OBJ
a = Asset.load(R('refinery.json')); lay = mesh.unwrap(a.geom, mats=mats); atlas = mesh.bake(a.geom, lay, mats)
obj, mtl = mesh.write_obj(os.path.join(tmp, 'refinery.obj'), a.geom, lay, 'refinery_paint.png')
V, VT, F = [], [], 0
for line in open(obj):
    k = line.split()
    if not k: continue
    if k[0] == 'v': V.append([float(x) for x in k[1:]])
    elif k[0] == 'vt': VT.append([float(x) for x in k[1:]])
    elif k[0] == 'f': F += 1
V, VT = np.array(V), np.array(VT)
check(F == len(a.geom), f'OBJ has every triangle ({F})')
check((VT >= 0).all() and (VT <= 1).all(), 'OBJ texture coordinates inside 0..1')
lo, hi = a.geom.bounds()
check(abs(V[:, 1].max() - hi[2] / 160) < 1e-4 and abs(V[:, 1].min() - lo[2] / 160) < 1e-4, 'OBJ is Y-up, one tile = 1 unit')
check('map_Kd refinery_paint.png' in open(mtl).read(), 'MTL names the atlas')
check(lay.used.sum() > 0.25 * lay.size[0] * lay.size[1], f'atlas {lay.size[0]}x{lay.size[1]} is {lay.used.mean():.0%} used')

# 3. projection
img, v = mesh.view(a.geom, st, scale=1.0, footprint=a.footprint)
W, H = img.size
layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
d.rectangle([0, int(H * .40), W, int(H * .55)], fill=(200, 40, 30, 255))
at1 = atlas.copy(); n1 = mesh.project(a.geom, lay, at1, layer, v, st)
flat = Image.new('RGBA', (W, H), (128, 128, 128, 255)); flat.alpha_composite(img); flat.alpha_composite(layer)
ref = Image.new('RGBA', (W, H), (128, 128, 128, 255)); ref.alpha_composite(img)
at2 = atlas.copy(); n2 = mesh.project(a.geom, lay, at2, flat, v, st, reference=ref)
check(n1 > 1000, f'a paint layer reaches the model ({n1} texels)')
check(abs(n1 - n2) / n1 < 0.03 and np.abs(at1 - at2)[..., :3].max(-1).mean() < 0.01,
      f'a flattened painting gives the same as a layer ({n2} texels)')
g1 = mesh.painted(a.geom, lay, at1, mats, name='paint:proj')
p0 = np.asarray(sprite.picture(a.geom, st, scale=1.0, footprint=a.footprint)[0]).astype(int)
p1 = np.asarray(sprite.picture(g1, st, scale=1.0, footprint=a.footprint)[0]).astype(int)
band = np.zeros(p0.shape[:2], bool); band[int(H * .42):int(H * .53)] = True
solid = p0[..., 3] > 0
red = lambda p: (p[..., 0] - p[..., 1:3].max(-1)) > 60
check(red(p1)[band & solid].mean() > 0.5, f'the painted band shows in the same view ({red(p1)[band & solid].mean():.0%} red)')
far = solid & (np.abs(np.arange(p0.shape[0]) - H * .475) > H * .15)[:, None]
check(red(p1)[far].mean() <= red(p0)[far].mean() + 0.001, 'nothing far from the band turned red')
back = Asset(a.spec, geom=g1, names=a.names).facing(2)
pb = np.asarray(sprite.picture(back.geom, st, footprint=back.footprint)[0]).astype(int)
ob = np.asarray(sprite.picture(a.facing(2).geom, st, footprint=back.footprint)[0]).astype(int)
moved = (np.abs(pb[..., :3] - ob[..., :3]).max(-1) > 40) & (ob[..., 3] > 0)
check(moved.mean() < red(p1)[solid].mean(), f'from behind, less of it changed ({moved.mean():.1%} vs {red(p1)[solid].mean():.1%} in front)')

# 4. layouts belong to one model
try:
    mesh.bake(Asset.load(R('hab_dome.json')).geom, lay, mats); check(False, 'a layout refuses another model')
except ValueError:
    check(True, 'a layout refuses another model')
check(mesh.signature(a.facing(1).geom) == lay.sig, 'every facing shares the layout of facing 0')

print('PASS' if not fails else f'FAIL ({len(fails)})')
sys.exit(1 if fails else 0)
