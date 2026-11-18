"""Render the figures into sprite sheets for the game, through the art engine:
  python3 tools/build_units.py [--sheet out.png]   -> game/art/u_<key>_<player>.png and game/art/units.json
Figures: styles/fantasy_realm/units.py. One sheet per unit and player (creeps: one neutral sheet, player 2): 8 rows (headings 0, 45, ... 315 degrees, 0 =
the game's +x) by 14 columns (idle, 8 walk frames, 5 strike frames). 0.6 px a unit: figures are drawn oversized
for visibility (user's decision) and at twice the game's size so zooming in stays sharp."""
import json, os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from artkit.style import Style
from artkit import figure
from artkit.core.space import Camera
from artkit.sprite import frame
from styles.fantasy_realm import units as U

OUT = os.path.join(ROOT, 'game', 'art')
SCALE = 0.6                                # px per unit
CAM = Camera.from_pack({'view': 'iso', 'plates': False})


def main():
    st = Style.load('fantasy_realm'); os.makedirs(OUT, exist_ok=True)
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    mf = os.path.join(OUT, 'units.json'); meta = json.load(open(mf)).get('units', {}) if os.path.exists(mf) else {}
    teams = dict(st.cfg['team_colors'])
    for key, (fn, kind, k, who, box) in U.CATALOG.items():
        if only and key not in only: continue
        u = fn(); cl, base = U.clips(u, kind); P = [base] + cl['walk'].poses() + cl['attack'].poses()
        players = sorted(teams) if who == 'both' else ['2']
        for p in players:
            t = np.array(teams.get(p, (120, 120, 120)), float)
            figure.material('fr_team', tuple(t * 0.62 + 14), 'wool'); figure.material('fr_team_dark', tuple(t * 0.40 + 8), 'wool'); st._mats = None
            rows = []
            for h in range(8):
                cells = []
                for pose in P:
                    g, _ = u.build(pose, h * 45.0)
                    if k != 1.0: g = g.scaled(k)
                    im, (ox, oy) = frame(g, st, box, scale=SCALE, camera=CAM)
                    cells.append(im)
                rows.append(np.concatenate(cells, axis=1))
            Image.fromarray(np.concatenate(rows, axis=0), 'RGBA').save(os.path.join(OUT, f'u_{key}_{p}.png'))
        ch, cw = cells[0].shape[:2]
        meta[key] = {'parts': len(u.parts), 'players': players, 'cell': [cw, ch], 'origin': [ox, oy]}
        print(key, players, [cw, ch], flush=True)
    json.dump({'draw': 0.575, 'clips': {'idle': [0, 1, 1], 'walk': [1, 8, 10], 'attack': [9, 5, 13]}, 'units': meta}, open(mf, 'w'), indent=1)
    return 0


if __name__ == '__main__': sys.exit(main())
