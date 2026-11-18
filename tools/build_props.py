"""Render the map's props (trees, ore, stone, berries, relics, camp dressing) through the art engine:
  python3 tools/build_props.py [--only tree,stone]   -> game/art/p_<key>.png, p_<key>_s.png, game/art/props.json
Geometry and briefs: styles/fantasy_realm/props.py. Same materials, scale (0.4 px a unit, drawn at half) and light as
the buildings; each prop also gets its cast shadow as its own picture (pack section "shadow"), drawn under everything."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from artkit.style import Style
from artkit.sprite import picture
from artkit import shadow as SH
from build_buildings import materials, OUT, shadow_meta
from styles.fantasy_realm.props import CATALOG


def main():
    st = Style.load('fantasy_realm'); rules = SH.Shadow.from_pack(st.cfg.get('shadow'))
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    mf = os.path.join(OUT, 'props.json'); meta = json.load(open(mf)) if only and os.path.exists(mf) else {}
    mats = materials(st, (120, 120, 120))
    for key, (fn, fp) in CATALOG.items():
        if only and not any(key.startswith(o) for o in only): continue
        g = fn()
        im, m = picture(g, st, footprint=fp, scale=0.4, mats=mats)
        im.save(os.path.join(OUT, f'p_{key}.png'), optimize=True)
        meta[key] = {'w': im.size[0], 'h': im.size[1], 'cx': m['centre'][0], 'cy': m['centre'][1]}
        s = shadow_meta(g, rules, fp, m, os.path.join(OUT, f'p_{key}_s.png'))
        if s: meta[key]['s'] = s
        print(key, im.size, flush=True)
    json.dump(meta, open(mf, 'w'), indent=1)
    return 0


if __name__ == '__main__': sys.exit(main())
