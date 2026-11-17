"""artkit's own check: renders a fixed set of pictures with nothing but the engine and its demo pack (Frontier Outpost),
so it runs in the engine's repository with no game present. Any change meant to leave the art alone must print the
same lines as expected_engine.txt.

  python3 artkit/tests/engine_check.py              compare with expected_engine.txt (exit 1 on a difference)
  python3 artkit/tests/engine_check.py --write      record the current output as expected (after a deliberate change)

Covers: every Frontier recipe with its stages and turning strips, the finishing pass and the design critic (through
Exporter.static), a Frontier rig and a stock trooper figure through Exporter.rig, the composer on the Frontier briefs
and its critic scores. Hashes are of decoded pixels and of the manifests, not of PNG files. About 2 minutes.
"""
import glob, hashlib, json, os, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from artkit.style import Style
from artkit.export import Exporter
from artkit.recipe import Asset
from artkit import design
from artkit.demo.frontier import build as F
from artkit.parts import soldier as P
from artkit.parts.trooper import build_trooper, trooper_clips

H = lambda b: hashlib.sha256(b).hexdigest()[:16]
out = []
st = Style.load('frontier_outpost')
tmp = tempfile.mkdtemp(prefix='artkit_check_')
ex = Exporter(st, tmp, log=lambda *a: None)


def pixels(fn):
    a = np.asarray(Image.open(os.path.join(tmp, fn)).convert('RGBA'))
    return f'{a.shape[1]}x{a.shape[0]} {H(a.tobytes())}'


# stills: every recipe, its stages and turning strips, finished and critiqued
for path in sorted(glob.glob(os.path.join(HERE, '..', 'demo', 'frontier', 'recipes', '*.json'))):
    key = os.path.basename(path)[:-5]
    rec = ex.static(key, Asset.load(path), headings=4, finish=True, critique=True)
    for s, m in sorted(rec['states'].items()): out.append(f'still {key} {s} {pixels(m["src"])} g {m.get("g")}')
    for pv, t in sorted(rec.get('turning', {}).items()): out.append(f'turning {key} {pv} {pixels(t["src"])}')
    out.append(f'critic {key} {rec["design"]["score"]}')

# animated: a machine rig and a stock trooper figure, two headings
rig, clips = F.strider(); rig.headings = 2
man = ex.rig('strider', rig, clips[:2])
u = build_trooper('trooper', P.carbine(), (P.steel_helmet(), 'helmet'), pelvis=[(P.ammo_pouches(), 'pouches')])
tc = trooper_clips(u, fire='bolt')[0]
man2 = ex.rig('trooper', u, [c for c in tc if c.name in ('idle', 'fire')], headings=2)
for key, m in (('strider', man), ('trooper', man2)):
    for cn, c in sorted(m['clips'].items()):
        for layer, fn in sorted(c['files'].items()): out.append(f'strip {key} {cn} {layer} {pixels(fn)}')
    out.append(f'manifest {key} {H(json.dumps(m, sort_keys=True).encode())}')

# design: the composer and the critic on the Frontier briefs
for b in json.load(open(os.path.join(HERE, '..', 'demo', 'frontier', 'briefs.json')))[:3]:
    br = design.Brief(**b); asm = design.compose(br, st)
    out.append(f'compose {br.key} {H(asm.geometry().P.round(4).tobytes())} critic {design.critique(asm, st).score:.1f} issues {len(asm.check())}')

text = '\n'.join(out) + '\n'
exp = os.path.join(HERE, 'expected_engine.txt')
if '--write' in sys.argv:
    open(exp, 'w').write(text); print(f'wrote {len(out)} lines to {exp}'); sys.exit(0)
old = open(exp).read().splitlines() if os.path.exists(exp) else []
new = text.splitlines(); bad = [(a, b) for a, b in zip(old, new) if a != b] + [(None, b) for b in new[len(old):]] + [(a, None) for a in old[len(new):]]
for a, b in bad: print(f'expected: {a}\n     got: {b}')
print(f'{len(new)} lines, {len(bad)} differ from expected_engine.txt' + ('' if bad else ': PASS'))
sys.exit(1 if bad else 0)
