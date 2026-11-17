"""Team colours are an addition (artkit/team.py): a pack without "team" writes exactly what it wrote before, and a
pack with it gets the same sprites plus grey masks that recolour them at runtime.

  python3 artkit/tests/team_check.py        prints PASS (about 30 seconds)

Checks: the material matcher; no team -> no masks and no new keys; with team -> every sprite and strip byte-identical
to the export without it, masks the same size, white on team material and black off it; masks survive packing in
the same layout as the frames; the browser's recolour (runtime/artkit.js) equals the Python reference.
"""
import json, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
from artkit.style import Style
from artkit.export import Exporter
from artkit.recipe import Asset
from artkit.demo.frontier import build as F
from artkit import team as T
from artkit import pack as _pack

bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)

# the matcher
t = T.Team(['banner', '@faction', 'hull@home'])
check(t('banner') and t('banner@mil') and t('cloth@faction') and t('hull@home'), 'matcher: base names, roles, exact names')
check(not t('hull') and not t('hull@mil') and not t('bannerx') and not t('faction'), 'matcher: nothing else')
check(T.Team.from_pack(None) is None and T.Team.from_pack({}) is None and T.Team.from_pack({'materials': []}) is None,
      'an absent or empty section is no team')

base = Style.load('frontier_outpost')
check(base.team is None, 'the demo pack has no team: nothing changes for it')
teamed = Style(base.root, dict(base.cfg, team={'materials': ['orange', 'hull']}))
turret = os.path.join(ROOT, 'artkit', 'demo', 'frontier', 'recipes', 'laser_turret.json')


def export(style, out):
    ex = Exporter(style, out, log=lambda *a: None)
    rec = ex.static('laser_turret', Asset.load(turret), headings=4)
    rig, clips = F.strider(); rig.headings = 2
    man = ex.rig('strider', rig, [c for c in clips if c.name == 'walk'])
    return ex, rec, man


tmp = tempfile.mkdtemp(prefix='artkit_team_')
A, B = os.path.join(tmp, 'plain'), os.path.join(tmp, 'team')
exa, reca, mana = export(base, A)
exb, recb, manb = export(teamed, B)

check(not any(f.endswith('_team.png') for f in os.listdir(A)), 'no team: no mask files')
check('team_gain' not in reca and 'team_gain' not in mana and all('team' not in m for m in reca['states'].values()),
      'no team: no new keys in assets.json')

same = lambda a, b: np.array_equal(np.asarray(Image.open(a)), np.asarray(Image.open(b)))
pics = [m['src'] for m in reca['states'].values()] + [t_['src'] for t_ in reca['turning'].values()]
pics += [fn for c in mana['clips'].values() for fn in c['files'].values()]
check(all(same(os.path.join(A, p), os.path.join(B, p)) for p in pics), f'team: all {len(pics)} sprites and strips byte-identical')

masks = [(m['src'], m.get('team')) for m in recb['states'].values()] + [(t_['src'], t_.get('team')) for t_ in recb['turning'].values()]
masks += [(c['files'][L], c['team'][L]) for c in manb['clips'].values() for L in c.get('team', {})]
masks = [(p, q) for p, q in masks if q]
check(len(masks) >= 2, f'team: masks written ({len(masks)})')
check(all(Image.open(os.path.join(B, q)).size == Image.open(os.path.join(B, p)).size for p, q in masks), 'masks match their pictures in size')
ok_on = ok_off = True
for p, q in masks:
    im = np.asarray(Image.open(os.path.join(B, p)).convert('RGBA')); mk = np.asarray(Image.open(os.path.join(B, q)))
    if (mk[im[..., 3] == 0] > 0).any(): ok_off = False
    if not (mk == 255).any(): ok_on = False
check(ok_off, 'masks are black wherever nothing is drawn')
check(ok_on, 'masks are white inside team material')
check('S' not in manb['layers'] and manb.get('team_gain') == 1.25, 'unit manifest gains team_gain only')

# packing: masks follow the frames through the same rects (pack_unit proves it cell by cell, or stops)
P = os.path.join(tmp, 'packed'); shutil.copytree(B, P)
units = {'strider': json.loads(json.dumps(manb))}
_pack.pack_all(P, units, log=lambda *a: None)
m = units['strider']
check(len(m.get('team_pack', [])) == len(m['pack']) and all('team' not in c for c in m['clips'].values()),
      'packed: team_pack pages beside pack pages; clips lose "team"')
check(all(Image.open(os.path.join(P, a)).size == Image.open(os.path.join(P, b)).size for a, b in zip(m['pack'], m['team_pack'])),
      'packed: mask pages the same size as colour pages')
plain_units = {'strider': json.loads(json.dumps(mana))}; PA = os.path.join(tmp, 'packed_plain'); shutil.copytree(A, PA)
_pack.pack_all(PA, plain_units, log=lambda *a: None)
check('team_pack' not in plain_units['strider'], 'packed without team: no team_pack')

# runtime recolour = Python reference
rng = np.random.default_rng(3)
px = rng.integers(0, 256, (6, 7, 4), dtype=np.uint8); mk = rng.integers(0, 256, (6, 7), dtype=np.uint8); mk[0, :] = 0
col = [60, 120, 230]
ref = T.recolour(px, mk, col)
node = shutil.which('node')
if node:
    js = ("const A=require(%r);const px=Uint8ClampedArray.from(%s);const mk=new Uint8ClampedArray(%d);const m=%s;"
          "for(let i=0;i<m.length;i++)mk[i*4]=m[i];A.recolourPixels(px,mk,%s);console.log(JSON.stringify(Array.from(px)))") % (
        os.path.join(ROOT, 'artkit', 'runtime', 'artkit.js'), json.dumps(px.ravel().tolist()), px.size, json.dumps(mk.ravel().tolist()), json.dumps(col))
    got = np.array(json.loads(subprocess.check_output([node, '-e', js]).decode()), np.int16).reshape(px.shape)
    check(np.abs(got - ref.astype(np.int16)).max() <= 1, 'runtime recolourPixels equals team.recolour (within 1)')
    check(np.array_equal(got[0], px[0]), 'runtime leaves unmasked pixels untouched')
else:
    print('skip runtime recolour (no node)')

shutil.rmtree(tmp, ignore_errors=True)
print('FAIL' if bad else 'PASS'); sys.exit(1 if bad else 0)
