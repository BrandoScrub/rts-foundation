"""The card option (artkit/card.py) and the pyramid fix.

  python3 artkit/tests/card_check.py      prints PASS (about 10 seconds)

1. A small Frontier scene (a demo recipe on a regolith plot, crates) renders as a card in both views: the card is the
   pack's size, the name box is drawn, the art window holds art, no standing part is cut off, the same call twice gives
   the same pixels, and the blockout is grey.
2. A "card" section in the pack changes the card (size, colours); without one the defaults hold.
3. Scene.check finds NO REASON, OFF PLOT and NO GROUND, and a clean scene has none.
4. shapes.pyramid's slopes face up and out (the faces of convex() of its five points), and a clockwise extrude
   profile faces its top up (the order its docstring asks for).
"""
import glob, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit.style import Style
from artkit.recipe import Asset
from artkit import shapes as sh, library as lib
from artkit.card import Scene, render, options, DEFAULTS

bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)

st = Style.load('frontier_outpost')
rec = Asset.load(sorted(glob.glob(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', '*.json')))[0]).base()


def scene(**fault):
    s = Scene('Survey Post', slab='basalt')
    if not fault.get('no_ground'):
        s.add('plot', sh.block(0, 400, 0, 400, -4, 0, 'regolith'), 'the ground', ground=True)
        s.add('pad', sh.block(120, 300, 120, 300, 0, 2, 'concrete'), 'level pad the module stands on', ground=True)
    lo, hi = rec.bounds() if hasattr(rec, 'bounds') else (rec.P.reshape(-1, 3).min(0), rec.P.reshape(-1, 3).max(0))
    lo, hi = np.asarray(lo), np.asarray(hi)
    s.add('module', rec.move(*(np.array([210.0, 210.0, 0.0]) - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])),
          '' if fault.get('no_reason') else 'the building the card is about', cover=True)
    x = 420 if fault.get('off_plot') else 40
    s.add('crates', lib.crate(30, 30, 26).move(x, 330, 0) + lib.crate(30, 30, 26).move(40, 290, 0), 'stores: the human-scale cue')
    return s


# 1. both views
art_pixels = {}
for view in ('iso', 'top_down'):
    img, m = render(scene(), st, view)
    A = np.asarray(img)
    check(img.size == (DEFAULTS['size'], DEFAULTS['size']), f'{view}: card is {DEFAULTS["size"]} px square')
    x0, y0, x1, y1 = m['name_box']
    nb = A[y0 + 2:y1 - 2, x0 + 2:x1 - 2, :3].reshape(-1, 3)
    check((np.abs(nb - DEFAULTS['name_fill']).sum(1) < 4).mean() > 0.6 and (nb.sum(1) < 300).any(),
          f'{view}: name box filled and lettered')
    wx0, wy0, wx1, wy1 = m['window']
    W = A[wy0:wy1, wx0:wx1, :3].astype(int)
    check(W.std() > 10, f'{view}: art window holds art')
    check(not m['clipped'], f'{view}: no standing part cut off ({m["parts_box"]} in a {wx1 - wx0} px window)')
    img2, _ = render(scene(), st, view)
    check(np.array_equal(A, np.asarray(img2)), f'{view}: the same call draws the same pixels')
    g, _ = render(scene(), st, view, blockout=True)
    G = np.asarray(g)[wy0:wy1, wx0:wx1, :3].astype(int)
    check((G.max(-1) - G.min(-1)).mean() < 6, f'{view}: blockout is grey')
    art_pixels[view] = W
check(art_pixels['iso'].shape == art_pixels['top_down'].shape and not np.array_equal(art_pixels['iso'], art_pixels['top_down']),
      'iso and top_down draw different pictures in the same window')

# 2. the pack's "card" section
check(options(st) == DEFAULTS, 'a pack without "card" gets the defaults')
p = Style(st.root, dict(st.cfg, card={'size': 200, 'name_fill': [250, 250, 250], 'view': 'top_down'}))
img, m = render(scene(), p)
check(img.size == (200, 200) and m['view'] == 'top_down', 'card.size and card.view come from the pack')
x0, y0, x1, y1 = m['name_box']
check(tuple(np.asarray(img)[y0 + 3, x0 + 3, :3]) == (250, 250, 250), 'card colours come from the pack')

# 3. Scene.check
check(scene().check() == [], 'a clean scene has no issues')
for fault, kind in (('no_reason', 'NO REASON'), ('off_plot', 'OFF PLOT'), ('no_ground', 'NO GROUND')):
    kinds = [k for k, _, _ in scene(**{fault: True}).check()]
    check(kind in kinds, f'Scene.check finds {kind}')

# 4. shapes
pyr = sh.pyramid(60, 40, 30, 'hull')
hull = sh.convex([(0, 0, 0), (60, 0, 0), (60, 40, 0), (0, 40, 0), (30, 20, 30)], 'hull')
slopes = sorted(map(tuple, np.round(hull.FN[hull.FN[:, 2] > -0.5], 3).tolist()))
check((pyr.FN[:, 2] > 0).all() and sorted(map(tuple, np.round(pyr.FN, 3).tolist())) == slopes,
      'pyramid slopes face up and out, as convex() of its points')
ex = sh.extrude([(-8, 12), (8, 12), (9, 0), (-9, 0)], 50, 'hull')
top = np.abs(ex.P[:, :, 2] - 12).max(1) < 1e-6
check(top.any() and (ex.FN[top, 2] > 0.99).all(), 'a clockwise extrude profile faces its top up')

print('PASS' if not bad else f'FAIL ({len(bad)})')
sys.exit(1 if bad else 0)
