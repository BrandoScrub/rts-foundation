"""Rock outcrops rendered from heightfields, in the artkit camera and light (was terrainkit/rocks.py).
Rock, soil, moss and snow colours per land and the ore colours come from the style pack's terrain section.
  python3 -m artkit.terrain rocks <art dir> [--style <pack>]   -> rocks_<land>.png atlases + rocks.json"""
import json,os,numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from .noise import *
from ..core.ink import lines,INK,INK_COVER,radius
from . import terrain_section
SS=3;PX=SCALE*SS;CELL=.75;SIZE=int(290/CELL);S=SIZE
STR=band(512,3,26,77)[:,256];CL=band(512,2,10,78)
ORE_STAIN=ORE_SEAM=ORE_GLINT=None;LAND=None   # from the style pack: set by configure()
def configure(style=None):
    """Rock colours per land and the ore colours, from the style pack's terrain section ("rocks")."""
    global ORE_STAIN,ORE_SEAM,ORE_GLINT,LAND
    R=terrain_section(style)['rocks'];o=R['ore'];ORE_STAIN,ORE_SEAM,ORE_GLINT=tuple(o['stain']),tuple(o['seam']),tuple(o['glint'])
    LAND={k:{a:(tuple(b) if isinstance(b,list) else b) for a,b in v.items()} for k,v in R['lands'].items()}
def field(seed,big,wide):
    """Broken blocks, not noise: Voronoi cells over the footprint, each a tilted slab on a shared bedding plane."""
    r=np.random.default_rng(seed);n=S
    Y,X=np.mgrid[0:n,0:n];cx=cy=n*.5;R=(.40 if big else .33)*n*wide
    wx=(spectral(n,3,seed+5)-.5)*34;wy=(spectral(n,3,seed+6)-.5)*34
    # footprint: a long lump with a couple of shoulders
    th=r.uniform(0,3.14);ca,sa=np.cos(th),np.sin(th);el=r.uniform(.62,.82)
    lumps=[(0,0,1.0,1.0)]
    for k in range(3):
        t=r.uniform(0,6.28);d=r.uniform(.3,.6);lumps.append((np.cos(t)*d,np.sin(t)*d*.7,r.uniform(.34,.56),r.uniform(.4,.75)))
    def mass(px,py):
        u=((px-cx)*ca+(py-cy)*sa)/R;v=(-(px-cx)*sa+(py-cy)*ca)/(R*el);m=0*u
        for ox,oy,q,hh in lumps:m=np.maximum(m,hh*smooth(1.04,.3,np.sqrt((u-ox)**2+(v-oy)**2)/q))
        return m
    sp=(46 if big else 40)/CELL
    nn=int((n/sp)**2*1.4);pts=r.uniform(0,n,(nn,2))
    # relax once so slabs are of similar size
    tr=cKDTree(pts);_,i=tr.query(np.stack([(X[::4,::4]).ravel()+0.,(Y[::4,::4]).ravel()+0.],1));cnt=np.bincount(i,minlength=nn)[:,None]+1e-9
    sumx=np.bincount(i,X[::4,::4].ravel(),minlength=nn);sumy=np.bincount(i,Y[::4,::4].ravel(),minlength=nn);pts=np.stack([sumx,sumy],1)/cnt
    tr=cKDTree(pts);d,i=tr.query(np.stack([(X+wx).ravel(),(Y+wy).ravel()],1),k=2);d=d.reshape(n,n,2);i=i[:,0].reshape(n,n)
    A=(112 if big else 70)*r.uniform(.92,1.08);mc=mass(pts[:,0],pts[:,1])
    step=r.uniform(15,22);dip=np.array([r.uniform(-.2,.2),r.uniform(-.2,.2)])*CELL
    h0=A*mc*(.62+.55*r.random(nn))
    h0=np.round(h0/step+.0)*step               # slabs sit on shared beds
    tilt=r.normal(0,.09,(nn,2))*CELL+dip
    H=h0[i]+tilt[i,0]*(X-pts[i,0])+tilt[i,1]*(Y-pts[i,1])
    gap=(d[...,1]-d[...,0])*CELL
    H-=smooth(9,0,gap)*5                       # chamfer and open the joints
    H[(mc[i]<.1)|(h0[i]<=0)]=0
    H=ndi.gaussian_filter(np.maximum(H,0),.9)
    lo=spectral(n,2.8,seed+2);fine=band(n,4,16,seed+3)
    H+=(lo-.5)*7*(H>2)+(fine-.5)*1.6*(H>2)
    m=mass(X+wx,Y+wy)
    # rubble: small blocks spilled round the foot
    rp=r.uniform(0,n,(int(120*wide*wide),2));keep=(mass(rp[:,0],rp[:,1])<.42)&(np.hypot(rp[:,0]-cx,rp[:,1]-cy)<R*(1.0+.32*r.random(len(rp))));rp=rp[keep]
    if len(rp):
        d2,j=cKDTree(rp).query(np.stack([X.ravel(),Y.ravel()],1));d2=d2.reshape(n,n);j=j.reshape(n,n);sz=2.5+r.power(.5,len(rp))*9;ht=sz*r.uniform(.6,1.1,len(rp))
        rub=ht[j]*smooth(1,.55,d2*CELL/sz[j]);H=np.maximum(H,rub)
    return np.maximum(H,0),fine,lo,m
def colour(H,fine,a,m,L,seed,ore):
    n=S;gy,gx=np.gradient(H,CELL);nz=1/np.sqrt(gx*gx+gy*gy+1);nx=-gx*nz;ny=-gy*nz
    # the kits' face rule: weight each lit face by the normal's squared components
    sh=(np.clip(nx,0,1)**2*.62+np.clip(ny,0,1)**2*1.06+nz*nz*.92)
    sh+=.22*np.clip(ny-nx,-1,1)              # catch the light on the lit side, more than the flat rule
    sh-=.34*np.clip(-nx*.5-ny*.5,0,1)
    ao=np.clip((ndi.gaussian_filter(H,9)-H)/14,-.2,1);ao2=np.clip((ndi.gaussian_filter(H,3)-H)/5,-.2,1)
    sh*=1-.42*np.clip(ao,0,1)-.3*np.clip(ao2,0,1)
    r=np.random.default_rng(seed)
    bands=band(512,3,40,seed+9)[:,256];ib=np.clip((H*2.4).astype(int),0,511);bk=bands[ib]
    mott=band(n,6,70,seed+7);spk=band(n,1.6,4,seed+8);c=mix(L['dark'],L['rock'],np.clip(.5+.75*(mott-.5)+L['band']*2.6*(bk-.5),0,1))
    c=c*(1+.2*(spk-.5))[...,None]
    # weathering runs down the faces
    streak=spectral(n,1.2,seed+11,aspect=(.3,3));slope=1-nz;c=c*(1-.13*smooth(.55,.85,streak)*smooth(.3,.7,slope))[...,None]
    if ore:
        # ore (Nov 9 second pass): the first pass was a faint rust that read as plain rock at game zoom. Now: wide
        # oxide stains bleeding down the faces, bright copper-orange seams, and metal glints on the lit tops.
        seam=1-np.abs(2*band(n,10,70,seed+13)-1);s=smooth(.86,.965,seam)*smooth(.1,.3,m)
        stain=ndi.gaussian_filter(s,6)+L.get('ore_bleed',.35)*smooth(.3,.7,streak)*smooth(.05,.25,m)*slope
        if L.get('ore_host') is not None:c=mix(c,L['ore_host'],.75)   # on red rock, ore sits in dark host rock so it still reads
        sk=L.get('ore_stain',(2.6,.82));c=mix(c,ORE_STAIN,np.clip(stain*sk[0],0,sk[1]));c=mix(c,ORE_SEAM,np.clip(s*(.75+spk),0,.95))
        glint=smooth(.74,.86,band(n,1.4,5,seed+17))*smooth(.2,.4,m)*smooth(.55,.8,nz)
        c=mix(c,ORE_GLINT,np.clip(glint,0,.95))
    flat=smooth(.76,.93,nz)*smooth(.03,.2,m)
    if L['moss'] is not None:
        mm=smooth(.5,.75,band(n,14,60,seed+15))*flat;c=mix(c,np.array(L['moss'])*1.0,np.clip(mm*.8,0,.8))
    if L['snow']:
        sn=smooth(.38,.56,mott*.4+a*.3+nz*.5)*smooth(.58,.84,nz)*smooth(.03,.2,m);c=mix(c,(206,212,220),np.clip(sn,0,.96));sh=sh*(1-.0*sn)
    out=c*np.clip(sh,.18,1.28)[...,None]
    # a cliff only spans a cell or two of the field, so soften it across and let render() add strata by height
    bl=np.stack([ndi.gaussian_filter(out[...,i],2.6) for i in range(3)],-1);out=mix(out,bl,smooth(.45,.8,slope))
    # sink into the land: the foot takes the colour of the ground
    base=smooth(9,1,H);out=mix(out,np.array(L['soil'])*.72,np.clip(base*.72,0,.72))
    return out,slope
def render(H,C,alpha,slope=None):
    """Heightfield to pixels, near to far per screen column."""
    n=S;ext=n*CELL;wpx=int((ext*2)*PX)+4;hpx=int((ext+170)*PX)+4;img=np.zeros((hpx,wpx,4));dep=np.zeros((hpx,wpx))
    ox=wpx/2;oy=170*PX
    sxs=(np.arange(wpx)+.5-ox)/PX;smax=2*ext;sv=np.arange(smax,0,-.35)
    for col,sx in enumerate(sxs):
        xs=(sv+sx)/2;ys=(sv-sx)/2;ok=(xs>=0)&(ys>=0)&(xs<ext-CELL)&(ys<ext-CELL)
        if not ok.any():continue
        xi=xs[ok]/CELL;yi=ys[ok]/CELL;ix=xi.astype(int);iy=yi.astype(int);fx=xi-ix;fy=yi-iy
        h=H[iy,ix]*(1-fx)*(1-fy)+H[iy,ix+1]*fx*(1-fy)+H[iy+1,ix]*(1-fx)*fy+H[iy+1,ix+1]*fx*fy
        sy=((sv[ok]/2-h)*PX+oy);mn=np.minimum.accumulate(sy)
        r0=int(np.ceil(mn[-1]));r1=min(int(mn[0])+1,hpx)
        if r1<=r0:continue
        rows=np.arange(max(r0,0),r1);idx=np.searchsorted(-mn,-rows.astype(float),side='left');idx=np.clip(idx,0,len(mn)-1)
        a=alpha[iy[idx],ix[idx]];cc=C[iy[idx],ix[idx]]
        if slope is not None:
            z=(sv[ok][idx]/2-(rows+.5-oy)/PX);zb=z+(col*.09);sl=np.clip((slope[iy[idx],ix[idx]]-.3)*2,0,1)
            k=1+sl*((STR[(zb*1.7).astype(int)%512]-.5)*.5+(CL[(z*2.2).astype(int)%512,int(col*1.1)%512]-.5)*.34);cc=cc*k[...,None]
        img[rows,col,:3]=cc;img[rows,col,3]=a;dep[rows,col]=sv[ok][idx]+h[idx]
    return img,dep,ox,oy
def finish(img,dep,Hgt):
    a=img[...,3];solid=a>.5;rgb=img[...,:3].copy()
    # the same line as buildings and units (isokit/inkline.py); low rock melts into the ground, with no line against it
    a=a.copy();ink=lines(dep,solid,radius(.48/SS),34.0,no_rim=~(Hgt>10))
    rgb[ink&solid]+=(INK*255-rgb[ink&solid])*INK_COVER
    rim=ink&~solid;rgb[rim]=INK*255;a[rim]=INK_COVER
    h,w=a.shape;hh,ww=h//SS,w//SS;ac=a[:hh*SS,:ww*SS];rc=rgb[:hh*SS,:ww*SS]
    A=ac.reshape(hh,SS,ww,SS).mean((1,3));P=(rc*ac[...,None]).reshape(hh,SS,ww,SS,3).mean((1,3))
    out=np.zeros((hh,ww,4));nz=A>0;out[nz,:3]=P[nz]/A[nz][...,None];out[...,3]=A*255
    return out
def make(land,seed,big=False,wide=1.0,ore=False):
    L=LAND[land];H,fine,a,m=field(seed,big,wide);C,slope=colour(H,fine,a,m,L,seed+50,ore)
    alpha=smooth(.5,3.2,H)
    img,dep,ox,oy=render(H,C,alpha,slope)
    # second render carries height instead of colour, so the outline can skip the ground contact
    im2,_,_,_=render(H,np.repeat(np.clip(H,0,255)[...,None],3,2),alpha);tall=im2[...,0]
    out=finish(img,dep,tall)
    # anchor: map centre, in strip pixels
    ax=ox/SS;ay=(oy+(S*CELL/2)*PX)/SS
    return out,ax,ay
def write(out,style=None):
    """rocks_<land>.png atlases (six rocks, four ore outcrops each) and rocks.json into out."""
    configure(style);meta={};os.makedirs(out,exist_ok=True)
    for land in LAND:
        cells=[]
        for v in range(6):cells.append(('rock',)+make(land,100+v*17+list(LAND).index(land)*1000,big=v>=4,wide=1.0+(v%3)*.08))
        for v in range(4):cells.append(('ore',)+make(land,900+v*23+list(LAND).index(land)*1000,big=v==3,wide=1.0,ore=True))
        # crop each, shelf-pack
        ims=[];
        for k,o,ax,ay in cells:
            ys,xs=np.where(o[...,3]>2);x0,x1,y0,y1=xs.min(),xs.max()+1,ys.min(),ys.max()+1
            ims.append((k,o[y0:y1,x0:x1],ax-x0,ay-y0))
        W=max(sum(i[1].shape[1] for i in ims[:5])+12,sum(i[1].shape[1] for i in ims[5:])+12);H=max(i[1].shape[0] for i in ims[:5])+max(i[1].shape[0] for i in ims[5:])+6
        at=np.zeros((H,W,4),'uint8');x=2;y=2;rec=[];row=0
        for i,(k,o,ax,ay) in enumerate(ims):
            if i==5:x=2;y+=row+2;row=0
            h,w=o.shape[:2];at[y:y+h,x:x+w]=o.astype('uint8');rec.append(dict(k=k,x=x,y=y,w=w,h=h,ax=round(float(ax),1),ay=round(float(ay),1)));x+=w+2;row=max(row,h)
        Image.fromarray(at,'RGBA').save(f'{out}/rocks_{land}.png',optimize=True);meta[land]=rec
    json.dump(meta,open(f'{out}/rocks.json','w'));return meta
