"""Fit painted ground tiles for a game (was terrainkit/paint_tile.py and fit_tiles.py): remove the wrap seam, resize to
1024, balance tone, and calm the grain. The sources, the target colour and contrast of every tile, and the grain and
mottle of the cohesion pass come from the style pack's terrain section ("ground": {"painted": ...}).
  python3 -m artkit.terrain fit <art dir> [grain] [mottle] [--style <pack>]    all tiles of the style
  python3 -m artkit.terrain fit-one in.png out.jpg [r g b] [contrast] [grain] [mottle]  one tile
grain: share of the finest detail kept (under about 2 px at 1024). mottle: share of the mid detail kept (2 to 12 px).
Both 1 give the Nov 9 morning fit; Brass and Bone's pack sets the cohesion pass (.4, .85): the ground is the stage, so
its grain is brought down to the level of the building sprites that stand on it."""
import os,numpy as np
from PIL import Image
from . import terrain_section,style_path
def seam(a,m=56):
    """Cross-fade to a half-shifted copy near the edges; weights keep the grain's contrast through the blend."""
    h,w=a.shape[:2];b=np.roll(np.roll(a,h//2,0),w//2,1)
    d=np.minimum.reduce([np.arange(w)[None,:]*np.ones((h,1)),(w-1-np.arange(w))[None,:]*np.ones((h,1)),np.arange(h)[:,None]*np.ones((1,w)),(h-1-np.arange(h))[:,None]*np.ones((1,w))])
    t=np.clip(d/m,0,1);t=t*t*(3-2*t);W=t[...,None];mu=a.mean((0,1))
    n=np.sqrt(W*W+(1-W)**2);return mu+((a-mu)*W+(b-mu)*(1-W))/n
def wrap_resize(a,N=1024,p=24):
    e=np.pad(a,((p,p),(p,p),(0,0)),mode='wrap');s=N/a.shape[0];P=int(round(p*s));im=Image.fromarray(np.clip(e,0,255).astype('uint8')).resize((N+2*P,N+2*P),Image.LANCZOS);return np.asarray(im,float)[P:P+N,P:P+N]
def fit_tile(src,out,target=None,con=1.,grain=1.,mottle=1.):
    a=np.asarray(Image.open(src).convert('RGB'),float)
    b=wrap_resize(seam(a));mu=b.mean((0,1));tg=np.array(target) if target else mu
    b=tg+(b-mu)*con
    if grain!=1 or mottle!=1:
        from scipy import ndimage as ndi
        lo1=ndi.gaussian_filter(b,(2,2,0),mode='wrap');lo2=ndi.gaussian_filter(b,(12,12,0),mode='wrap')
        b=lo2+(lo1-lo2)*mottle+(b-lo1)*grain
    Image.fromarray(np.clip(b,0,255).astype('uint8')).save(out,quality=84,subsampling=0)
    c=np.asarray(Image.open(out).convert('RGB'),float)
    print('wrap x/y',round(np.abs(c[:,0]-c[:,-1]).mean(),2),round(np.abs(c[0]-c[-1]).mean(),2),'inner',round(np.abs(c[:,1:]-c[:,:-1]).mean(),2),round(np.abs(c[1:]-c[:-1]).mean(),2),'mean',c.reshape(-1,3).mean(0).round(1),'std',c.reshape(-1,3).std(0).round(1))
def fit_all(out,style=None,grain=None,mottle=None):
    """Every painted tile the style lists: <sources>/ground_<land>_<material>.png -> out/ground_<land>_<material>.jpg."""
    P=terrain_section(style).get('ground',{}).get('painted')
    if not P:print(f'{style}: no painted ground tiles in this style pack');return []
    src=style_path(style,P['sources']);os.makedirs(out,exist_ok=True)
    grain=P['grain'] if grain is None else grain;mottle=P['mottle'] if mottle is None else mottle
    for land,mats in P['targets'].items():
        for mat,(r,g,b,c) in mats.items():
            n='ground_%s_%s'%(land,mat)
            fit_tile(os.path.join(src,n+'.png'),os.path.join(out,n+'.jpg'),[float(r),float(g),float(b)],float(c),float(grain),float(mottle))
