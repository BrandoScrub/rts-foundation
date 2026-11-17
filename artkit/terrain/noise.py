"""Seamless noise and colour helpers for terrain (was terrainkit/common.py). Conventions are artkit's: sx = x - y,
sy = (x + y)/2 - z, 160 units a tile, 0.4 strip px per unit, light from the upper left."""
import numpy as np
from PIL import Image
SCALE=.4
def spectral(n,beta,seed,aspect=(1,1)):
    """Seamless noise in 0..1 with a 1/f^beta spectrum."""
    r=np.random.default_rng(seed);fx=np.fft.fftfreq(n)[:,None]*aspect[0];fy=np.fft.rfftfreq(n)[None,:]*aspect[1]
    f=np.sqrt(fx*fx+fy*fy);f[0,0]=1
    z=(r.normal(size=f.shape)+1j*r.normal(size=f.shape))/f**(beta/2);z[0,0]=0
    a=np.fft.irfft2(z,s=(n,n));lo,hi=np.percentile(a,[.5,99.5]);return np.clip((a-lo)/(hi-lo),0,1)
def band(n,lo,hi,seed):
    """Seamless noise containing only features between lo and hi pixels across."""
    r=np.random.default_rng(seed);fx=np.fft.fftfreq(n)[:,None];fy=np.fft.rfftfreq(n)[None,:];f=np.sqrt(fx*fx+fy*fy)
    m=((f>1/hi)&(f<1/lo)).astype(float);z=(r.normal(size=f.shape)+1j*r.normal(size=f.shape))*m
    a=np.fft.irfft2(z,s=(n,n));lo2,hi2=np.percentile(a,[.5,99.5]);return np.clip((a-lo2)/(hi2-lo2),0,1)
def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def mix(a,b,t):
    t=np.asarray(t);a=np.asarray(a,float);b=np.asarray(b,float)
    if t.ndim>=1 and t.shape[-1]!=3:t=t[...,None]
    return a+(b-a)*t
def save(rgb,path,**k):
    Image.fromarray(np.clip(rgb,0,255).astype('uint8')).save(path,**k)
