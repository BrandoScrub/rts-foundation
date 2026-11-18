"""Grey review sheets for this game's blockouts (artkit/DESIGN_METHOD.md, step 7): flat greys only (stone light,
timber mid, roofs darker, openings darkest), at play size (0.4 px a unit: a 64 px tile) and close, from two headings.
Prints each blockout's findings; they must be empty before the sheet is shown.

  python3 -m styles.fantasy_realm.blockouts.render <out folder>
"""
import os, sys
import numpy as np
from artkit.style import Style
from artkit.core.materials import Materials, Material
from artkit.core.geom import RZ
from artkit.sprite import picture, sheet
from styles.fantasy_realm.blockouts.buildings import CATALOG

GREY = {'stone': 186, 'timber': 150, 'roof': 112, 'dark': 52, 'earth': 128}


def mats():
    g = lambda v: Material(np.full((8, 8, 3), v / 255, np.float32), 'tile', 0.05)
    return Materials(fallback=lambda n: g(GREY.get(n.split('@')[0], 160)))


def main(out):
    os.makedirs(out, exist_ok=True)
    st, M, bad = Style.load('frontier_outpost'), mats(), 0
    for key, fn in CATALOG.items():
        b, fp = fn(); f = b.findings(); bad += len(f)
        print(key, 'parts', len(b.why), 'findings', f or 'none')
        g = b.geometry(); c = np.array([fp[0] / 2, fp[1] / 2, 0])
        views = [(g, 'front'), (g.about(c, RZ(180)), 'from behind')]
        for scale, tag in ((0.4, 'play'), (1.0, 'close')):
            ims = [picture(v, st, footprint=fp, scale=scale, mats=M)[0] for v, _ in views]
            sheet(ims, [f'{key}, {l}, {tag} size' for _, l in views], cols=2, zoom=2 if scale == 0.4 else 1).save(os.path.join(out, f'{key}_{tag}.png'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'blockout_sheets'))
