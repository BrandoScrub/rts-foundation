"""Render the building blockouts into the game, through the art engine:
  python3 tools/build_buildings.py     -> game/art/b_<key>_<player>.png and game/art/buildings.json
Geometry: styles/fantasy_realm/blockouts/buildings.py (a brief and a reason per part). Materials: the pack's
"procedural" stand-ins; the 'roof' and 'team' materials take each player's colour (pack "team_colors").
0.4 px a unit = twice the game's 64 px tile (the game draws them at half size, so zooming in stays sharp). buildings.json gives each picture's size and where the footprint centre is."""
import json, os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from artkit.style import Style
from artkit.core.materials import Materials, Material, procedural
from artkit.sprite import picture
from artkit import shadow as SH
from styles.fantasy_realm.blockouts.buildings import CATALOG

OUT = os.path.join(ROOT, 'game', 'art')


def materials(st, team_rgb):
    P = st.cfg['procedural']; t = np.array(team_rgb, float)
    def fb(name):
        base = name.split('@')[0]
        if base not in P: base = 'stone'
        rgb, kind = P[base]
        if base == 'roof': rgb, kind = list(t * 0.52 + 16), 'wood'       # roofs: the player colour, dark and muted (slate with a tint)
        if base == 'team': rgb, kind = list(t * 0.82 + 8), 'plain'
        return Material(procedural(rgb, kind, seed=sum(map(ord, base))).astype(np.float32), 'tile', 48 / 128, base in ('ember', 'glow', 'bane', 'relic'))
    return Materials(fallback=fb)


def shadow_meta(g, rules, fp, m, path):
    """The cast shadow as its own picture (artkit.shadow), and where the footprint centre is in it: the sprite and
    its shadow share the footprint's near corner, so the centre is that corner minus the sprite's own offset."""
    if rules is None: return None
    im, sm = SH.picture(g, rules, scale=0.4, footprint=fp)
    if im is None: return None
    im.convert('LA').save(path, optimize=True)      # one colour and alpha: a few kB
    return {'w': im.size[0], 'h': im.size[1], 'cx': round(sm['near_corner'][0] - (m['near_corner'][0] - m['centre'][0]), 2), 'cy': round(sm['near_corner'][1] - (m['near_corner'][1] - m['centre'][1]), 2)}


def main():
    st = Style.load('fantasy_realm'); os.makedirs(OUT, exist_ok=True); bad = 0; rules = SH.Shadow.from_pack(st.cfg.get('shadow'))
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None      # --only key,key or a prefix: palisade
    mf = os.path.join(OUT, 'buildings.json'); meta = json.load(open(mf))['buildings'] if only and os.path.exists(mf) else {}
    for key, fn in CATALOG.items():
        if only and not any(key == o or key.startswith(o + '_') for o in only): continue
        b, fp = fn(); f = b.findings()
        if f: print(key, 'FINDINGS', f); bad += 1; continue
        g = b.geometry()
        for p, rgb in sorted(st.cfg['team_colors'].items()):
            im, m = picture(g, st, footprint=fp, scale=0.4, mats=materials(st, rgb))
            im.save(os.path.join(OUT, f'b_{key}_{p}.png'))
        meta[key] = {'w': im.size[0], 'h': im.size[1], 'cx': m['centre'][0], 'cy': m['centre'][1], 'parts': len(b.why)}
        s = shadow_meta(g, rules, fp, m, os.path.join(OUT, f'b_{key}_s.png'))
        if s: meta[key]['s'] = s
        print(key, im.size, m['centre'])
    json.dump({'players': sorted(st.cfg['team_colors']), 'buildings': meta}, open(os.path.join(OUT, 'buildings.json'), 'w'), indent=1)
    return 1 if bad else 0


if __name__ == '__main__': sys.exit(main())
