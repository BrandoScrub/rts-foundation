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
from artkit import shadow as SH
import math
from styles.fantasy_realm import units as U

OUT = os.path.join(ROOT, 'game', 'art')
CAM = Camera.from_pack({'view': 'iso', 'plates': False})
ORDER = ('idle', 'walk', 'attack', 'die')


def readable(a):
    """Two readability steps on a finished sheet (tools/readability_check.py measures them): lift the figure's values
    so it stands off the dark ground (value before hue), and lay a thin pale rim outside the outline so its
    silhouette is cut out of whatever it stands on."""
    rgb = a[..., :3].astype(np.float32) / 255; al = a[..., 3].astype(np.float32) / 255
    rgb = np.clip(rgb ** 0.70 * 1.16, 0, 1)                                        # lift mid-tones, keep the blacks of the ink line
    m = Image.fromarray((al * 255).astype(np.uint8)); from PIL import ImageFilter
    grow = np.asarray(m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    rim = np.clip(grow - al, 0, 1) * 0.62                                          # only outside the figure
    out = np.zeros_like(a); oa = al + rim * (1 - al)
    col = (rgb * al[..., None] + np.array([0.96, 0.92, 0.80]) * (rim * (1 - al))[..., None]) / np.maximum(oa, 1e-6)[..., None]
    out[..., :3] = (np.clip(col, 0, 1) * 255).astype(np.uint8); out[..., 3] = (np.clip(oa, 0, 1) * 255).astype(np.uint8); return out


def main():
    st = Style.load('fantasy_realm'); os.makedirs(OUT, exist_ok=True)
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    mf = os.path.join(OUT, 'units.json'); meta = json.load(open(mf)).get('units', {}) if os.path.exists(mf) else {}
    teams = dict(st.cfg['team_colors']); rules = SH.Shadow.from_pack(st.cfg.get('shadow'))
    for key, (fn, kind, k, who, box, scale) in U.CATALOG.items():
        if only and key not in only: continue
        u = fn()
        C = U.quad_clips(u, bite=kind == 'quad') if kind in ('quad', 'graze') else U.figure_clips(u, kind)
        P = [p for n in ORDER for p in C[n]]
        players = sorted(teams) if who == 'both' else ['2']
        hw, up, down = box; cw, ch = int(math.ceil(2 * hw * scale)), int(math.ceil((up + down) * scale)); ox, oy = cw / 2.0, up * scale
        if rules is not None:                                   # the cast shadow of every frame, one sheet per unit (pack "shadow")
            rows = []
            for h in range(8):
                cells = []
                for pose in P:
                    g, _ = u.build(pose, h * 45.0)
                    if k != 1.0: g = g.scaled(k)
                    cells.append(SH.frame(g, rules, cw, ch, scale, ox, oy, camera=CAM))
                rows.append(np.concatenate(cells, axis=1))
            Image.fromarray(np.concatenate(rows, axis=0), 'RGBA').convert('LA').save(os.path.join(OUT, f'u_{key}_s.png'), optimize=True)
        if '--shadows-only' in sys.argv and key in meta: meta[key]['shadow'] = rules is not None; print(key, 'shadow', flush=True); continue
        for p in players:
            t = np.array(teams.get(p, (120, 120, 120)), float)
            figure.material('fr_team', tuple(np.clip(t * 0.92 + 22, 0, 255)), 'wool'); figure.material('fr_team_dark', tuple(t * 0.58 + 12), 'wool'); st._mats = None   # the owner's colour is the brightest, most saturated thing on a figure
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
            Image.fromarray(readable(np.concatenate(rows, axis=0)), 'RGBA').quantize(255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(os.path.join(OUT, f'u_{key}_{p}.png'), optimize=True)
        ch, cw = cells[0].shape[:2]
        meta[key] = {'parts': len(u.parts), 'players': players, 'cell': [cw, ch], 'origin': [ox, oy], 'draw': round(0.575 * 0.6 / scale, 4), 'shadow': rules is not None}
        print(key, players, [cw * len(P), ch * 8], flush=True)
    n = {k: len(C[k]) for k in ORDER}
    json.dump({'clips': {'idle': [0, 1, 1], 'walk': [1, n['walk'], 10], 'attack': [1 + n['walk'], n['attack'], 13], 'die': [1 + n['walk'] + n['attack'], n['die'], 11]}, 'units': meta}, open(mf, 'w'), indent=1)
    return 0


if __name__ == '__main__': sys.exit(main())
