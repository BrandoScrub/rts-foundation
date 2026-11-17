"""Grey review sheets for the blockouts here (artkit/DESIGN_METHOD.md, step 7): flat grey surfaces, darker for the
mechanism (steel) and darkest for rubber, at play size and close, from several headings, with the engine's lines
now and with the line weight hierarchy (light.ink width / inner / step / crease).

  python3 -m artkit.demo.blockouts.render <out folder>
"""
import os, sys
import numpy as np

from artkit.style import Style
from artkit.recipe import Asset
from artkit.core.materials import Materials, Material
from artkit.core.light import Rules
from artkit.core.geom import RZ
from artkit.core.space import Camera
from artkit.sprite import picture, sheet
from artkit.demo.blockouts import m4_medium_tank as tank

HERE = os.path.dirname(os.path.abspath(__file__))
VEHICLE = Camera.from_pack({'view': 'iso', 'plates': False})   # nothing on it is a ground plate: the track's ground run keeps its outline
LINES = Rules(ink_width=0.75, ink_inner=0.5, ink_step=4, ink_crease=35, ink_crease_width=0.35)


def grey_materials():
    g = lambda v: Material(np.full((8, 8, 3), v / 255, np.float32), 'tile', 0.05)
    G, D, K = g(170), g(110), g(70)
    return Materials(fallback=lambda n: D if n.split('@')[0] in ('steel', 'dark') else K if n.split('@')[0] == 'rubber' else G)


def main(out):
    os.makedirs(out, exist_ok=True)
    st, mats = Style.load('frontier_outpost'), grey_materials()
    shots = lambda geoms, scale, cam=None: [(picture(g, st, scale=scale, mats=mats, lighting=r, camera=cam)[0], f'{tag}, {lab}')
                                            for r, tag in ((None, 'lines now'), (LINES, 'line hierarchy')) for g, lab in geoms]
    tur = Asset.load(os.path.join(HERE, 'point_defence_turret.json'))
    tg = [(tur.base() + tur.turning('head', h), f'aim {h}') for h in (0, 135, 250)]
    c = np.array(tank.P(2.97, 0, 0))
    kg = [(tank.geometry(tu).about(c, RZ(hd)), f'hull {hd}') for hd, tu in ((90, 0), (0, 0), (200, 160), (300, 30))]
    for name, geoms, cols, cam in (('turret', tg, 3, None), ('tank', kg, 4, VEHICLE)):
        for scale, tag in ((0.4, 'play'), (1.0, 'close')):
            ims = shots(geoms if scale == 0.4 else geoms[:2], scale, cam)
            sheet([i for i, _ in ims], [l for _, l in ims], cols=cols if scale == 0.4 else 2).save(os.path.join(out, f'{name}_{tag}.png'))
    print('wrote', sorted(os.listdir(out)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'blockout_sheets')
