"""artkit's camera check: other views are additions, never changes to the isometric default.

  python3 artkit/tests/camera_check.py

1. The default camera (no "camera" in the pack, Camera.ISO, camera=None) draws exactly the same pixels as before
   cameras existed (engine_check.py proves the whole engine; this proves the three spellings agree).
2. Camera.top_down() puts model x, y on screen x, y and depth on z, keeps handedness, and its pictures match the old
   way of getting a top-down view (warping every model by hand into the isometric frame) to within the shading that
   warp got wrong (wear and ground plates read off a tilted height).
3. Pack parsing: missing/"iso" -> Camera.ISO; "top_down"; {"view", "ground": null}; {"matrix"}; bad names refused.
About 20 seconds.

Also: "unit_camera" (a separate camera for animated unit strips, e.g. ground null) keeps the outline under a tracked
unit and leaves stills untouched; Exporter.rig(camera=) does the same per call.
"""
import glob, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit.style import Style
from artkit.recipe import Asset
from artkit import sprite
from artkit.core.space import Camera, project

fails = []
check = lambda ok, what: (print(('ok   ' if ok else 'FAIL ') + what), ok or fails.append(what))

st = Style.load('frontier_outpost')
g = Asset.load(sorted(glob.glob(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', '*.json')))[0]).base()

# 1. the default is untouched, however it is spelled
a, ma = sprite.picture(g, st, scale=0.4)
b, mb = sprite.picture(g, st, scale=0.4, camera=Camera.ISO)
check(st.camera is Camera.ISO, 'a pack without "camera" is isometric')
check(np.array_equal(np.asarray(a), np.asarray(b)) and ma == mb, 'camera=None and Camera.ISO draw identical pictures')

# 2. top-down geometry
td = Camera.top_down()
P = np.array([[3.0, 5.0, 7.0], [-40.0, 12.5, 0.0]])
sx, sy = td.screen(P)
check(np.allclose(sx, P[:, 0]) and np.allclose(sy, P[:, 1]) and np.allclose(td.depth(P), P[:, 2]), 'top_down: screen = (x, y), depth = z')
check(np.allclose(project(P, camera=td), P[:, :2]), 'space.project honours the camera')
check(np.linalg.det(td.M) > 0, 'top_down keeps handedness')

C = 600.0
def old_warp(p):
    X, Y, Z = p; u = 2 * (Y + Z + C) / 3
    return ((u + X) / 2, (u - X) / 2, (Z + C - 2 * Y) / 3)

for path in sorted(glob.glob(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', '*.json')))[:2]:
    m = Asset.load(path).base()
    w, mw = sprite.picture(m.warp(old_warp), st, scale=0.4, pad=8)
    t, mt = sprite.picture(m, st, scale=0.4, pad=8, camera=Camera.top_down(ground=None))
    W, T = np.asarray(w).astype(int), np.asarray(t).astype(int)
    # the hand warp's canvas can sit a fraction of a pixel off, so compare shape and colour, not pixel by pixel
    dx, dy = (int(round(a - b)) for a, b in zip(mw['origin'], mt['origin']))
    h, wd = min(W.shape[0] - max(dy, 0), T.shape[0] - max(-dy, 0)), min(W.shape[1] - max(dx, 0), T.shape[1] - max(-dx, 0))
    W = W[max(dy, 0):max(dy, 0) + h, max(dx, 0):max(dx, 0) + wd]; T = T[max(-dy, 0):max(-dy, 0) + h, max(-dx, 0):max(-dx, 0) + wd]
    aw, at = W[..., 3] > 127, T[..., 3] > 127
    iou = (aw & at).sum() / max((aw | at).sum(), 1)
    tint = np.abs(W[aw][:, :3].mean(0) - T[at][:, :3].mean(0)).max()
    same = abs(dx) <= 1 and abs(dy) <= 1 and iou > 0.97 and tint < 6
    check(same, f'top_down matches the hand warp: {os.path.basename(path)} (overlap {iou:.3f}, tint {tint:.1f})')
    check(np.isfinite(T).all() and T[..., 3].max() == 255, f'top_down picture is drawn: {os.path.basename(path)}')

# 3. pack parsing
check(Camera.from_pack(None) is Camera.ISO and Camera.from_pack('iso').iso, 'missing or "iso" -> isometric')
c = Camera.from_pack({'view': 'top_down', 'ground': None})
check(c.name == 'top_down' and c.ground is None and not c.iso, '{"view": "top_down", "ground": null}')
check(Camera.from_pack({'matrix': np.eye(3).tolist()}).M is None, 'an identity matrix is the isometric view')
for bad in ({'view': 'fisheye'}, {'matrix': [[1, 0, 0], [0, 1, 0], [0, 0, -1]]}):
    try: Camera.from_pack(bad); check(False, f'refuses {bad}')
    except ValueError: check(True, f'refuses {bad}')


# unit_camera: animated unit strips may use their own camera (usually the same view with no ground), so the ground
# plate rule (no outline on faces under 8 units) does not erase the bottom of tracks and feet. Stills are untouched.
import tempfile
from PIL import Image
from artkit.export import Exporter
from artkit.demo.frontier import build as FB
from artkit.core.space import Camera as _Cam
def _bottom_ink(man, out):
    """Opaque pixels at or below the unit's ground anchor, over every cell: the outline under the tracks lives there."""
    files = man['clips'][next(iter(man['clips']))]['files']          # the lower layer (tracks, legs) or the whole unit
    L = 'L' if 'L' in files else 'F'
    im = np.asarray(Image.open(os.path.join(out, files[L])).convert('RGBA'))
    fw, fh = man['layers'][L]['frame']; ay = man['layers'][L]['anchor'][1]
    cells = [im[r:r + fh, c:c + fw] for r in range(0, im.shape[0], fh) for c in range(0, im.shape[1], fw)]
    return float(sum(int((cell[int(ay):, :, 3] > 128).sum()) for cell in cells))
_st = Style.load('frontier_outpost')
check(getattr(_st, 'unit_camera', 'x') is None, 'no "unit_camera" in a pack -> style.unit_camera is None')
_tmp = tempfile.mkdtemp(prefix='artkit_ucam_')
_rig, _clips = FB.crawler(); _rig.headings = 2
_m0 = Exporter(_st, _tmp + '/a', log=lambda *a: None).rig('crawler', _rig, _clips[:1])
_st2 = Style(_st.root, dict(_st.cfg, unit_camera={'view': 'iso', 'plates': False}))
_m1 = Exporter(_st2, _tmp + '/b', log=lambda *a: None).rig('crawler', _rig, _clips[:1])
_m2 = Exporter(_st, _tmp + '/c', log=lambda *a: None).rig('crawler', _rig, _clips[:1], camera=_Cam.from_pack({'plates': False}))
b0, b1, b2 = _bottom_ink(_m0, _tmp + '/a'), _bottom_ink(_m1, _tmp + '/b'), _bottom_ink(_m2, _tmp + '/c')
_ncell = 2 * _clips[0].frames                       # headings x frames
check(b1 - b0 >= 10 * _ncell, f'unit_camera plates false: a tracked unit keeps the outline under its tracks (+{(b1 - b0) / _ncell:.0f} px a frame below the ground line)')
check(abs(b2 - b1) < 1e-6, 'Exporter.rig(camera=) does the same per call')
_r0 = Exporter(_st, _tmp + '/d', log=lambda *a: None).static('pad', Asset.load(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', 'landing_pad.json')), headings=2)
_r1 = Exporter(_st2, _tmp + '/e', log=lambda *a: None).static('pad', Asset.load(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', 'landing_pad.json')), headings=2)
_same = np.array_equal(np.asarray(Image.open(_tmp + '/d/pad.png')), np.asarray(Image.open(_tmp + '/e/pad.png')))
check(_same, 'unit_camera leaves stills (buildings) exactly as they were')


# plates false keeps the ground (shadows stay under the unit); ground null is for flyers (shadows lifted away)
from artkit.shadow import Shadow, cast
_box = sprite.__dict__.get('sh', None)
from artkit import shapes as _sh
_tower = _sh.box(40, 40, 60, 'hull')
_on = cast(_tower, _Cam.from_pack({'plates': False}), Shadow()); _fly = cast(_tower, _Cam.from_pack({'ground': None}), Shadow())
check(_Cam.from_pack({'plates': False}).ground == 0.0 and not _Cam.from_pack({'plates': False}).plates, 'plates false keeps the ground')
check(_on.reshape(-1, 2)[:, 1].max() < _fly.reshape(-1, 2)[:, 1].max() - 5, 'a unit camera without plates keeps its shadow on the ground; ground null lifts it')

print('PASS' if not fails else f'{len(fails)} FAILED')
sys.exit(1 if fails else 0)
