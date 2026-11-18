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
from styles.fantasy_realm.blockouts.buildings import CATALOG

OUT = os.path.join(ROOT, 'game', 'art')


def materials(st, team_rgb):
    P = st.cfg['procedural']; t = np.array(team_rgb, float)
    def fb(name):
        base = name.split('@')[0]
        if base not in P: base = 'stone'
        rgb, kind = P[base]
        if base == 'roof': rgb, kind = list(t * 0.78 + 20), 'wood'       # roofs: the player colour, a little muted
        if base == 'team': rgb, kind = list(np.minimum(255, t * 1.05 + 12)), 'plain'
        return Material(procedural(rgb, kind, seed=sum(map(ord, base))).astype(np.float32), 'tile', 48 / 128, base == 'ember')
    return Materials(fallback=fb)


def main():
    st = Style.load('fantasy_realm'); os.makedirs(OUT, exist_ok=True); meta = {}; bad = 0
    for key, fn in CATALOG.items():
        b, fp = fn(); f = b.findings()
        if f: print(key, 'FINDINGS', f); bad += 1; continue
        g = b.geometry()
        for p, rgb in sorted(st.cfg['team_colors'].items()):
            im, m = picture(g, st, footprint=fp, scale=0.4, mats=materials(st, rgb))
            im.save(os.path.join(OUT, f'b_{key}_{p}.png'))
        meta[key] = {'w': im.size[0], 'h': im.size[1], 'cx': m['centre'][0], 'cy': m['centre'][1], 'parts': len(b.why)}
        print(key, im.size, m['centre'])
    json.dump({'players': sorted(st.cfg['team_colors']), 'buildings': meta}, open(os.path.join(OUT, 'buildings.json'), 'w'), indent=1)
    return 1 if bad else 0


if __name__ == '__main__': sys.exit(main())
