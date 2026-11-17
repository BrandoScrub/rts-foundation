"""Gates built to the same section, height and materials as the wall sprites they sit in (was terrainkit/gate.py).
Eight sprites: wood/concrete x line/y line, shut/open. The material colours come from the style pack's terrain section.
  python3 -m artkit.terrain gates <art dir> [--style <pack>]"""
import json,os,numpy as np
from PIL import Image
from .noise import *
from ..core.ink import lines,radius,INK,INK_COVER
from . import terrain_section
SS=4;PX=SCALE*SS;W,H,NEAR=134,136,133
n1=spectral(512,1.6,1);n2=band(512,1.5,5,2);n3=spectral(512,2.4,3)
def smp(a,u,v):return a[(np.floor(v).astype(int))%512,(np.floor(u).astype(int))%512]
M=None   # the gate materials of the style in use: set by configure()
def configure(style=None):
    """Take the gate materials from a style pack's terrain section ("gates": {"materials": ...})."""
    global M;M=terrain_section(style)['gates']['materials']
def mat(name,x,y,z,face,seed):
    """face: 0 top, 1 +x, 2 +y. Returns rgb per pixel."""
    u=(y if face==1 else x)+seed*37;v=z if face else (y if face==0 else z)
    if name in('stake','post','rail','beam'):
        along=name in('rail','beam')
        a,b=(u*.5,v*5.5) if along else (u*5.5,v*.5)
        g=smp(n2,a,b);m=smp(n3,u*1.4+seed*11,v*1.4)
        base=M[name]
        k=(.68+.5*g)*(.86+.28*m);return np.stack([base[i]*k for i in range(3)],-1)
    if name=='iron':
        k=.9+.25*smp(n2,u*2,v*2);return np.stack([np.full_like(k,c)*k for c in M['iron']],-1)
    if name=='concrete':
        m=smp(n1,u*1.3+seed,v*1.3);g=smp(n2,u*3,v*3);k=(.78+.32*m)*(.9+.2*g)
        st=np.clip((smp(n3,u*2.5+seed*9,v*.28)-.62)*2.2,0,.34);k*=1-st
        return np.stack([c*k for c in M['concrete']],-1)
    if name=='slate':
        m=smp(n1,u*2+seed,v*2);k=.84+.28*m;return np.stack([c*k for c in M['slate']],-1)
    if name=='steel':
        m=smp(n1,u*2.2+seed*5,v*2.2);g=smp(n2,u*3,v*3);r=smooth(.52,.82,m)
        c=mix(M['steel'][0],M['steel'][1],r)*(.86+.26*g)[...,None]
        return c
    if name=='hazard':
        s=(np.floor((u+v)/18).astype(int)%2).astype(float);return mix(M['hazard'][0],M['hazard'][1],s)*.9
    raise KeyError(name)
class Scene:
    def __init__(s,axis):
        s.axis=axis;w,h=W*SS,H*SS;s.rgb=np.zeros((h,w,3));s.a=np.zeros((h,w));s.dep=np.full((h,w),-1e9)
    def xf(s,u,v,z):return (u,v,z) if s.axis=='x' else (v,u,z)
    def face(s,o,e1,e2,name,shade,face,seed,mask=None):
        o=np.array(o,float);e1=np.array(e1,float);e2=np.array(e2,float)
        pr=lambda p:np.array([(p[0]-p[1])*PX+W*SS/2,((p[0]+p[1])/2-p[2])*PX+(NEAR*SS-160*PX)])
        a=pr(o);b=pr(o+e1)-a;c=pr(o+e2)-a;cs=np.array([a,a+b,a+c,a+b+c])
        x0,y0=np.floor(cs.min(0)).astype(int);x1,y1=np.ceil(cs.max(0)).astype(int);x0,y0=max(x0,0),max(y0,0);x1=min(x1,W*SS);y1=min(y1,H*SS)
        if x1<=x0 or y1<=y0:return
        d=b[0]*c[1]-b[1]*c[0]
        if abs(d)<1e-6:return
        X,Y=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5);rx,ry=X-a[0],Y-a[1]
        p=(rx*c[1]-ry*c[0])/d;q=(ry*b[0]-rx*b[1])/d;ok=(p>=0)&(p<=1)&(q>=0)&(q<=1)
        if mask is not None:ok&=mask(p,q)
        wp=o[...,None,None]*1+e1[...,None,None]*p+e2[...,None,None]*q;dep=wp[0]+wp[1]+wp[2]
        rg=(s.dep[y0:y1,x0:x1]<dep)&ok
        if not rg.any():return
        col=mat(name,wp[0][rg],wp[1][rg],wp[2][rg],face,seed)*shade
        if face:col=col*(1-.26*np.clip(1-wp[2][rg]/34,0,1))[...,None]
        sub=s.rgb[y0:y1,x0:x1];sub[rg]=col;s.a[y0:y1,x0:x1][rg]=1;s.dep[y0:y1,x0:x1][rg]=dep[rg]
    def box(s,u0,u1,v0,v1,z0,z1,name,seed=0,tip=0):
        x=s.xf(u0,v0,0);X=s.xf(u1,v1,0);x0,x1=min(x[0],X[0]),max(x[0],X[0]);y0,y1=min(x[1],X[1]),max(x[1],X[1])
        s.face((x0,y1,z0),(x1-x0,0,0),(0,0,z1-z0),name,1.0,2,seed)
        s.face((x1,y0,z0),(0,y1-y0,0),(0,0,z1-z0),name,.68,1,seed)
        if tip:
            tri=lambda p,q:q<=1-abs(2*p-1)
            s.face((x0,y1,z1),(x1-x0,0,0),(0,-(y1-y0)/2,tip),name,1.0,2,seed,tri);s.face((x1,y0,z1),(0,y1-y0,0),(-(x1-x0)/2,0,tip),name,.68,1,seed,tri)
        else:s.face((x0,y0,z1),(x1-x0,0,0),(0,y1-y0,0),name,.97,0,seed)
    def finish(s,ax,mode):
        a=s.a;d=s.dep.copy();rgb=s.rgb
        # the same line as buildings and units (isokit/inkline.py)
        solid=a>0;ink=lines(d,solid,radius(.5/SS),16.0);rgb=rgb.copy();a=a.copy()
        paint=ink&solid;rgb[paint]+=(INK*255-rgb[paint])*INK_COVER
        rim=ink&~solid;rgb[rim]=INK*255;a[rim]=INK_COVER
        # box-filter down to strip pixels
        h,w=a.shape;pm=rgb*a[...,None];A=a[:h//SS*SS,:w//SS*SS].reshape(h//SS,SS,w//SS,SS).mean((1,3))
        P=pm.reshape(h//SS,SS,w//SS,SS,3).mean((1,3));out=np.zeros((h//SS,w//SS,4));nz=A>0;out[nz,:3]=P[nz]/A[nz][...,None];out[...,3]=A*255
        return Image.fromarray(np.clip(out,0,255).astype('uint8'),'RGBA')
def leaf_wood(s,u0,u1,hinge,opened,seed):
    """A leaf of the same pointed stakes as the barricade, with rails and a brace."""
    n=5;C=80
    if not opened:
        w=(u1-u0)/n
        for i in range(n):
            s.box(u0+i*w+.6,u0+(i+1)*w-.6,C-8,C+8,0,60+(i*7+seed*5)%9,'stake',seed+i,tip=11)
        for z in(16,48):s.box(u0,u1,C+8,C+11,z,z+5,'rail',seed)
        # brace, as steps of short rails
        for k in range(18):
            t=k/18;z=19+t*30;p=u0+(u1-u0)*(t if hinge<0 else 1-t);s.box(p-2.2,p+2.2,C+8.5,C+11,z,z+4,'rail',seed)
    else:
        L=C-8;far=hinge
        for i in range(5):
            v0=C-i*11-24;s.box(far-7,far+7,v0,v0+10,0,60+i*5%9,'stake',seed+i,tip=11)
        for z in(16,48):s.box(far+7,far+10,C-70,C-12,z,z+5,'rail',seed)
def leaf_steel(s,u0,u1,hinge,opened,seed):
    C=80
    if not opened:
        s.box(u0+1,u1-1,C+12,C+20,4,84,'steel',seed)
        for z in(18,44,70):s.box(u0+1,u1-1,C+20,C+22,z,z+4,'iron',seed)
        for p in(u0+8,u1-8):s.box(p-2,p+2,C+20,C+22,6,82,'iron',seed)
    else:
        far=hinge;s.box(far-6,far+6,C-46,C+20,4,84,'steel',seed)
        for z in(18,44,70):s.box(far+6,far+8,C-46,C+20,z,z+4,'iron',seed)
def gate(kind,axis,opened):
    s=Scene(axis);C=80
    if kind=='wood':
        for u,sd in((12,1),(148,2)):
            s.box(u-11,u+11,C-11,C+11,0,92,'post',sd,tip=18)
            for z in(18,70):s.box(u-12,u+12,C+11,C+12,z,z+5,'iron',sd);s.box(u+11,u+12,C-12,C+12,z,z+5,'iron',sd)
        s.box(4,156,C-6,C+6,70,80,'beam',3)
        if opened:leaf_wood(s,23,80,31,True,5);leaf_wood(s,80,137,129,True,6)
        else:leaf_wood(s,23,80,-1,False,5);leaf_wood(s,80,137,1,False,6)
    else:
        for u,sd in((17,1),(143,2)):
            s.box(u-17,u+17,C-23,C+23,0,100,'concrete',sd)
            s.box(u-19,u+19,C-26,C+26,100,107,'slate',sd)
        s.box(34,126,C+12,C+20,86,96,'hazard',3)
        if opened:leaf_steel(s,34,80,42,True,5);leaf_steel(s,80,126,118,True,6)
        else:leaf_steel(s,34,80,-1,False,5);leaf_steel(s,80,126,1,False,6)
    return s.finish(0,kind)
def write(out,style=None):
    """The eight gate sprites and gate_records.json (art.json records) into out."""
    configure(style);rec={};os.makedirs(out,exist_ok=True)
    for kind in('wood','concrete'):
        for axis in('x','y'):
            for o in(0,1):
                im=gate(kind,axis,o);bb=im.getbbox();top=max(bb[1]-2,0);im=im.crop((0,top,W,H))
                k=f'gate_{kind}_{axis}_{o}';im.save(f'{out}/{k}.png')
                rec[f'b:gate:{kind}:{axis}:{o}']={'src':f'art/{k}.png','scale':round((W/2)/64,4),'dy':-(H-NEAR)/2}
    json.dump(rec,open(f'{out}/gate_records.json','w'))
    return rec
