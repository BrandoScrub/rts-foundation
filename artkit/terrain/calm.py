"""Cohesion pass for rock atlases (was terrainkit/calm_rocks.py, Nov 9 2026): rocks are scenery, so they must not be the
busiest thing on screen. Keeps the forms, takes the fine striation and the hard black joints down toward the level of
the building sprites. grain, contrast and the pinned atlas means come from the style pack's terrain section ("calm").
  python3 -m artkit.terrain calm <dir with rocks_<land>.png> <out dir> [grain] [contrast] [--style <pack>]
PIN=0 in the environment uses each atlas's own mean instead of the pinned one."""
import os,numpy as np
from PIL import Image
from scipy import ndimage as ndi
from . import terrain_section
def calm(src,dst,style=None,grain=None,con=None):
    C=terrain_section(style)['calm'];grain=C['grain'] if grain is None else grain;con=C['contrast'] if con is None else con
    os.makedirs(dst,exist_ok=True)
    # atlas means from the first calm pass, before the ore was re-coloured; pass PIN=0 to use the atlas's own mean
    MU_FIXED={} if os.environ.get('PIN')=='0' else {k:tuple(v) for k,v in C['pinned_means'].items()}
    for land in C['lands']:
        a=np.asarray(Image.open(os.path.join(src,'rocks_%s.png'%land)).convert('RGBA'),float);rgb,al=a[...,:3],a[...,3:]/255
        w=ndi.gaussian_filter(al,(1.6,1.6,0))+1e-6
        lo=ndi.gaussian_filter(rgb*al,(1.6,1.6,0))/w          # alpha-weighted, so edges do not pull in black
        out=lo+(rgb-lo)*grain
        mu=(rgb*al).sum((0,1))/al.sum()                         # the atlas's own mean rock colour
        if land in MU_FIXED:mu=np.array(MU_FIXED[land])         # pinned, so re-colouring the ore leaves the rocks as they were
        out=mu+(out-mu)*con
        out=np.where(out<mu*.42,out*.6+mu*.42*.4,out)           # lift the deepest joints a little
        keep=np.clip((58-rgb.max(2,keepdims=True))/22,0,1)      # the ink lines (artkit/core/ink.py) stay as drawn
        out=out*(1-keep)+rgb*keep
        Image.fromarray(np.clip(np.dstack([out,a[...,3]]),0,255).astype('uint8'),'RGBA').save(os.path.join(dst,'rocks_%s.png'%land),optimize=True)
        print(land,'mean',mu.round(1))
