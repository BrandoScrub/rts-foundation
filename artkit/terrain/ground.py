"""Procedural ground tiles (was terrainkit/tiles.py): seamless, 1024 px = 16 game tiles (2 px per game world pixel, the
density of the sprites). Stand-ins for painted tiles: a painted tile with the same name replaces any of them.
Lit from the upper left; on the ground that is the world's -x side. Blades are drawn along -x-y, which reads as
vertical on screen. What each tile is made of comes from the style pack's terrain section ("ground": {"procedural"}),
as a small tree of operations:
  {"op": "soil", "lo": rgb, "hi": rgb, "seed": s}
  {"op": "grassy", "seed": s, "soil": [rgb, rgb], "grass": rgb, "dark": rgb, "light": rgb, "density": d}
  {"op": "pebbles", "of": op, "n": count, "seed": s, "r": [min, max], "lo": rgb, "hi": rgb, "alpha": a}
  {"op": "cracks", "of": op, "seed": s, "pts": count, "width": px, "col": rgb, "amt": a}
  {"op": "grit", "of": op, "seed": s, "amt": [fine, mid, macro]}          (amt optional: .09, .13, .18)
  {"op": "blend", "of": op, "with": rgb or op, "noise": [beta, seed], "edge": [lo, hi], "k": k}
  {"op": "wind", "of": op, "noise": [beta, seed], "aspect": [ax, ay], "base": b, "amp": a}
  python3 -m artkit.terrain ground <out dir> [--style <pack>] [--force]
Never write these over a game's painted tiles: without --force an existing ground_*.jpg is not overwritten."""
import os,numpy as np
from PIL import Image,ImageDraw
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from .noise import *
from . import terrain_section
N=1024
def strokes(n,seed,lmin,lmax,jit,widths=(1,)):
    r=np.random.default_rng(seed);x=r.uniform(0,N,n);y=r.uniform(0,N,n);L=r.uniform(lmin,lmax,n);a=np.pi*1.25+r.normal(0,jit,n);w=r.choice(widths,n)
    return x,y,x+np.cos(a)*L,y+np.sin(a)*L,w
def layer(paint):
    """2x canvas, tiles by drawing every mark at the wrap offsets it reaches, downsampled to a (rgb, alpha) pair."""
    S=N;im=Image.new('RGBA',(S,S),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA');paint(d,S);a=np.asarray(im,float);return a[...,:3],a[...,3]/255
def over(base,c,a,k=1):return base+(c-base)*(a*k)[...,None]
OFFS=[(0,0),(-1,0),(1,0),(0,-1),(0,1),(1,1),(-1,-1),(1,-1),(-1,1)]
def draw_strokes(d,S,xs,cols,widths):
    x0,y0,x1,y1=xs;sc=S/N
    for i in range(len(x0)):
        for dx,dy in OFFS:
            X0,Y0=(x0[i]+dx*N)*sc,(y0[i]+dy*N)*sc;X1,Y1=(x1[i]+dx*N)*sc,(y1[i]+dy*N)*sc
            if max(X0,X1)<-4 or min(X0,X1)>S+4 or max(Y0,Y1)<-4 or min(Y0,Y1)>S+4:continue
            d.line((X0,Y0,X1,Y1),fill=tuple(int(v) for v in cols[i]),width=int(widths[i]))
def pebbles(base,n,seed,rmin,rmax,lo,hi,alpha=1.):
    """Small flat stones: an uneven outline, a little shade on the +x side, no highlight."""
    r=np.random.default_rng(seed);xs=r.uniform(0,N,n);ys=r.uniform(0,N,n);rad=rmin+(rmax-rmin)*r.power(.45,n)*.8;t=r.uniform(0,1,n)
    lo=np.array(lo,float);hi=np.array(hi,float);out=base.copy()
    for i in range(n):
        R=int(rad[i]*1.8)+2;px=int(xs[i]);py=int(ys[i]);yy,xx=np.mgrid[-R:R+1,-R:R+1];dx=xx+px-xs[i];dy=yy+py-ys[i]
        ang=np.arctan2(dy,dx);ph=r.uniform(0,6.28,3);w=1+.22*np.sin(2*ang+ph[0])+.16*np.sin(3*ang+ph[1])+.1*np.sin(5*ang+ph[2]);d=np.sqrt(dx*dx+dy*dy)/(rad[i]*w)
        m=np.clip((1-d)*rad[i]*1.2,0,1)*alpha;col=lo+(hi-lo)*t[i]
        gy=(yy+py)%N;gx=(xx+px)%N
        sdx=dx-rad[i]*.45;sd=np.sqrt(sdx*sdx+dy*dy)/(rad[i]*w);smk=np.clip((1-sd)*rad[i],0,1)*.3
        out[gy,gx]=out[gy,gx]*(1-smk[...,None])
        sh=1.05-.1*dx/rad[i]
        out[gy,gx]=out[gy,gx]*(1-m[...,None])+(col[None,None]*sh[...,None])*m[...,None]
    return out
def grit(rgb,seed,fine=.09,mid=.13,macro=.18):
    k=1+(band(N,1.2,3,seed)-.5)*fine*2+(band(N,3,14,seed+1)-.5)*mid*2+(band(N,30,240,seed+2)-.5)*macro*2
    return rgb*k[...,None]
def soil(lo,hi,seed):
    n=spectral(N,1.7,seed);return mix(lo,hi,n)
def grassy(seed,soilc,grass,dark,light,density,dry=None):
    base=soil(soilc[0],soilc[1],seed)
    cov=spectral(N,2.0,seed+1);cov2=band(N,6,40,seed+2)
    g=mix(dark,grass,smooth(.25,.8,cov))
    a=smooth(.2,.6,cov*.75+cov2*.4)
    base=over(base,g,a,.9)
    r=np.random.default_rng(seed+3);n=int(118000*density);xs=strokes(n,seed+4,4,11,.45,(1,2));pick=r.uniform(0,1,n)
    # mark density follows cover, so bare earth stays bare
    ix=xs[0].astype(int)%N;iy=xs[1].astype(int)%N;keep=r.uniform(0,1,n)<(a[iy,ix]*.92+.08)
    xs=tuple(v[keep] for v in xs);pick=pick[keep]
    cols=np.zeros((len(pick),4));cols[...,3]=235
    hi=np.array(light,float);lo=np.array(dark,float);mid=np.array(grass,float)
    for c in range(3):cols[...,c]=np.where(pick<.42,lo[c]*(.8+.3*pick),np.where(pick<.86,mid[c]*(.85+.3*pick),hi[c]))
    def paint(d,S):draw_strokes(d,S,xs[:4],cols,xs[4])
    c,al=layer(paint);base=over(base,c,al)
    return base
def cracks(rgb,seed,pts,width,col,amt):
    r=np.random.default_rng(seed);P=r.uniform(0,N,(pts,2));Q=np.concatenate([P+np.array([dx*N,dy*N]) for dx in(-1,0,1) for dy in(-1,0,1)])
    Y,X=np.mgrid[0:N,0:N];wx=(spectral(N,2.4,seed+1)-.5)*26;wy=(spectral(N,2.4,seed+2)-.5)*26
    d,_=cKDTree(Q).query(np.stack([(X+wx).ravel(),(Y+wy).ravel()],1),k=2);d=d.reshape(N,N,2);e=d[...,1]-d[...,0]
    m=smooth(width,width*.25,e)*amt;out=mix(rgb,col,m);
    hl=smooth(width*2.4,width,e)*(1-smooth(width,width*.4,e))*.12
    return out*(1+hl)[...,None]
def build(op):
    """Evaluate one recipe tree from the style pack to an rgb array (N x N x 3, 0..255 floats)."""
    if not isinstance(op,dict):return op                     # a plain colour
    k=op['op']
    if k=='soil':return soil(op['lo'],op['hi'],op['seed'])
    if k=='grassy':return grassy(op['seed'],op['soil'],op['grass'],op['dark'],op['light'],op['density'])
    of=build(op['of'])
    if k=='pebbles':return pebbles(of,op['n'],op['seed'],op['r'][0],op['r'][1],op['lo'],op['hi'],op['alpha'])
    if k=='cracks':return cracks(of,op['seed'],op['pts'],op['width'],op['col'],op['amt'])
    if k=='grit':return grit(of,op['seed'],*op.get('amt',(.09,.13,.18)))
    if k=='blend':return mix(of,build(op['with']),smooth(op['edge'][0],op['edge'][1],spectral(N,op['noise'][0],op['noise'][1]))*op['k'])
    if k=='wind':return of*(op['base']+op['amp']*spectral(N,op['noise'][0],op['noise'][1],aspect=tuple(op['aspect'])))[...,None]
    raise KeyError(k)
def write(out,style=None,force=False):
    """ground_<land>_<material>.jpg for every tile in the style's procedural ground table."""
    G=terrain_section(style)['ground']['procedural'];n=0;os.makedirs(out,exist_ok=True)
    for land,mats in G['lands'].items():
        for k,op in mats.items():
            p=f'{out}/ground_{land}_{k}.jpg'
            if os.path.exists(p) and not force:
                print('kept',p,'(exists; painted tiles are never overwritten without --force)');continue
            Image.fromarray(np.clip(build(op),0,255).astype('uint8')).save(p,quality=G.get('quality',78),subsampling=0);n+=1
    return n
