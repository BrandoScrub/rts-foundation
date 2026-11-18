"""Render the figures into sprite sheets for the game, through the art engine:
  python3 tools/build_units.py [--sheet out.png]   -> game/art/u_<key>_<player>.png and game/art/units.json
Figures: styles/fantasy_realm/units.py. One sheet per unit and player (creeps: one neutral sheet, player 2): 8 rows (headings 0, 45, ... 315 degrees, 0 =
the game's +x) by 22 columns (idle, 8 walk frames, 5 attack frames, 8 death frames). 0.6 px a unit (the ogre 0.4): figures are drawn oversized
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
CAM = Camera.from_pack({'view': 'iso', 'plates': False})
ORDER = ('idle', 'walk', 'attack', 'die')


def main():
    st = Style.load('fantasy_realm'); os.makedirs(OUT, exist_ok=True)
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    mf = os.path.join(OUT, 'units.json'); meta = json.load(open(mf)).get('units', {}) if os.path.exists(mf) else {}
    teams = dict(st.cfg['team_colors'])
    for key, (fn, kind, k, who, box, scale) in U.CATALOG.items():
        if only and key not in only: continue
        u = fn()
        C = U.quad_clips(u, bite=kind == 'quad') if kind in ('quad', 'graze') else U.figure_clips(u, kind)
        P = [p for n in ORDER for p in C[n]]
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
                    im, (ox, oy) = frame(g, st, box, scale=scale, camera=CAM)
                    cells.append(im)
                rows.append(np.concatenate(cells, axis=1))
            # 255 colours and alpha: a fifth of the file, no visible change on flat-shaded figures
            Image.fromarray(np.concatenate(rows, axis=0), 'RGBA').quantize(255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(os.path.join(OUT, f'u_{key}_{p}.png'), optimize=True)
        ch, cw = cells[0].shape[:2]
        meta[key] = {'parts': len(u.parts), 'players': players, 'cell': [cw, ch], 'origin': [ox, oy], 'draw': round(0.575 * 0.6 / scale, 4)}
        print(key, players, [cw * len(P), ch * 8], flush=True)
    n = {k: len(C[k]) for k in ORDER}
    json.dump({'clips': {'idle': [0, 1, 1], 'walk': [1, n['walk'], 10], 'attack': [1 + n['walk'], n['attack'], 13], 'die': [1 + n['walk'] + n['attack'], n['die'], 11]}, 'units': meta}, open(mf, 'w'), indent=1)
    return 0


if __name__ == '__main__': sys.exit(main())
