"""artkit.mesh: models out as real 3D files, and paint back in.

Every asset is a full 3D model before it becomes a sprite. This module lets that model leave the engine and come back
painted, so a hand-drawn layer can sit on the code-built geometry and still follow every facing, stage and turning
part. Nothing here changes how existing assets draw: a model is only drawn differently when a game asks for its
painted version.

  layout = unwrap(geom)                         a paint atlas: every source polygon gets its own island, no overlaps
  atlas  = bake(geom, layout, mats)             the model's own materials, unlit, laid into that atlas (a start to paint on)
  write_obj(path, geom, layout, 'x_paint.png')  Wavefront OBJ + MTL with the atlas as its texture (Blender, any 3D tool)
  img, v = view(geom, style)                    a big render to paint over, and the numbers to project it back
  project(geom, layout, atlas, painting, v, style, reference=img)
                                                a paintover of that render projected onto the visible faces
  g2 = painted(geom, layout, atlas, mats)       the model wearing the atlas: draw it like any geometry
  a2 = paint_asset(asset, layout, atlas, mats)  same for an Asset: stages, facings and turning parts follow

The atlas holds colour before light (albedo). The renderer still lights it from the upper left, adds wear, ambient
occlusion and the even line, so painted and unpainted art share one finish. project divides the paintover by the
light the renderer gave each face (unshade), so light painted over a lit render is not applied twice.

Command line (run from the game's folder so its style pack and modules are found):
  python3 -m artkit.mesh export  <asset> <out> [--key K] [--style P] [--density D] [--facings 1|2|4] [--view-scale 1]
  python3 -m artkit.mesh project <out> <key> <painting.png> [--facing q] [--keep-light]
  python3 -m artkit.mesh preview <out> <key> [--scale 0.4]
<asset>: a recipe .json, or module:function[:argument] returning an Asset, Geometry or recipe dict
(e.g. styles.my_pack.buildings:asset:bank).
"""
import argparse, hashlib, importlib, json, math, os, sys
import numpy as np
from PIL import Image

from .core import render as R
from .core import light
from .core.geom import FLAT, SMOOTH
from .core.materials import Material
from .sprite import picture, AA

VIEW = light.VIEW


# ================================================================ layout
def signature(geom):
    """What a layout belongs to: triangle count, polygon ids and materials (not positions, so every facing of the
    same asset shares one layout)."""
    h = hashlib.sha256()
    h.update(np.int64(len(geom)).tobytes()); h.update(np.asarray(geom.face, np.int64).tobytes())
    h.update('\0'.join(str(m) for m in geom.mat).encode())
    return h.hexdigest()[:16]


class Layout:
    """uv (n, 3, 2): each triangle's corners in atlas texels (texel centres at whole numbers, as the renderer
    samples). size (W, H). tri (H, W): which triangle a texel belongs to (-1: padding). bary (H, W, 2): its
    barycentric (a, b) in that triangle (c = 1 - a - b). density: texels per model unit."""

    def __init__(s, uv, size, tri, bary, density, sig):
        s.uv, s.size, s.tri, s.bary, s.density, s.sig = uv, tuple(size), tri, bary, float(density), sig

    @property
    def used(s): return s.tri >= 0

    def save(s, path):
        np.savez_compressed(path, uv=s.uv.astype(np.float32), size=np.array(s.size), tri=s.tri, bary=s.bary.astype(np.float32),
                            density=np.array(s.density), sig=np.array(s.sig))

    @staticmethod
    def load(path):
        d = np.load(path)
        return Layout(d['uv'].astype(float), tuple(int(x) for x in d['size']), d['tri'], d['bary'], float(d['density']), str(d['sig']))


def _bases(n):
    """Per polygon: u (right) and v (down) across its plane. Walls read upright (v = down the wall), tops and
    bottoms read as the screen does (u along x - y, v along x + y)."""
    up = np.abs(n[:, 2]) >= 0.95
    u = np.cross(np.array([0.0, 0.0, 1.0]), n)
    u[up] = np.array([1.0, -1.0, 0.0]) / math.sqrt(2)
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
    v = np.where(up[:, None], np.cross(n, u), np.cross(u, n))
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
    return u, v


def _shelf(ws, hs, pad, max_size):
    """Shelf-pack rectangles (texels, without padding). Returns (offsets (k, 2), W, H) or None if over max_size."""
    W_ = np.ceil(ws).astype(int) + 1 + 2 * pad; H_ = np.ceil(hs).astype(int) + 1 + 2 * pad
    width = max(int(W_.max()), int(math.ceil(math.sqrt(float((W_ * H_).sum()) * 1.12))))
    width = -(-width // 4) * 4
    if width > max_size: return None
    order = np.lexsort((-W_, -H_))
    off = np.zeros((len(ws), 2), int); x = y = row = 0
    for k in order:
        if x + W_[k] > width: x = 0; y += row; row = 0
        off[k] = (x + pad, y + pad); x += W_[k]; row = max(row, H_[k])
    height = -(-(y + row) // 4) * 4
    if height > max_size: return None
    return off, width, height


def texel_density(geom, mats, cap=4.0):
    """The finest texel density (texels per model unit) of the tiled materials on geom: an atlas this fine keeps
    every texel of the tiles. Decals are stretched, so they do not count. At least 1, at most cap."""
    d = [mats.get(m).tpu for m in np.unique(geom.mat) if mats.get(m).mode == 'tile']
    return float(min(max([1.0] + d), cap))


def unwrap(geom, density=None, pad=2, max_size=4096, mats=None):
    """A paint atlas for geom. density: texels per model unit (1 = a 160-unit tile is 160 texels, five times what
    the game shows); None: texel_density(geom, mats) when mats is given (no tile detail lost), else 1. Lowered
    automatically until the atlas fits max_size. pad: empty texels round every island."""
    if density is None: density = texel_density(geom, mats) if mats is not None else 1.0
    n = len(geom)
    if not n: raise ValueError('nothing to unwrap')
    _, inv = np.unique(geom.face, return_inverse=True); nf = inv.max() + 1
    P = geom.P
    cr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ns = np.zeros((nf, 3)); np.add.at(ns, inv, cr)
    l = np.linalg.norm(ns, axis=1)
    fb = np.zeros((nf, 3)); np.add.at(fb, inv, geom.FN)                       # slivers: fall back on the face normals
    ns = np.where((l > 1e-9)[:, None], ns, fb); ns /= np.maximum(np.linalg.norm(ns, axis=1, keepdims=True), 1e-9)
    ns[np.linalg.norm(ns, axis=1) < 0.5] = (0, 0, 1)
    u, v = _bases(ns)
    Q = np.stack([np.einsum('tcj,tj->tc', P, u[inv]), np.einsum('tcj,tj->tc', P, v[inv])], -1)    # (n, 3, 2) units
    lo = np.full((nf, 2), np.inf); hi = np.full((nf, 2), -np.inf)
    np.minimum.at(lo, inv, Q.min(1)); np.maximum.at(hi, inv, Q.max(1))
    d = float(density)
    while True:
        r = _shelf((hi[:, 0] - lo[:, 0]) * d, (hi[:, 1] - lo[:, 1]) * d, pad, max_size)
        if r is not None: break
        d *= 0.85
        if d < 1e-3: raise ValueError('model too large for the atlas')
    off, W, H = r
    uv = (Q - lo[inv][:, None, :]) * d + off[inv][:, None, :]
    tri = np.full((H, W), -1, np.int32); bary = np.zeros((H, W, 2), np.float32)
    missed = []
    for i in range(n):
        a, b, c = uv[i]
        x0, x1 = int(math.floor(uv[i, :, 0].min())), int(math.ceil(uv[i, :, 0].max()))
        y0, y1 = int(math.floor(uv[i, :, 1].min())), int(math.ceil(uv[i, :, 1].max()))
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12: missed.append(i); continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=float), np.arange(y0, y1 + 1, dtype=float))
        la = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        lb = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        ins = (la >= -1e-6) & (lb >= -1e-6) & (1 - la - lb >= -1e-6)
        sub = tri[y0:y1 + 1, x0:x1 + 1]
        put = ins & (sub < 0)
        if not ins.any(): missed.append(i); continue
        sub[put] = i
        bs = bary[y0:y1 + 1, x0:x1 + 1]; bs[put, 0] = la[put]; bs[put, 1] = lb[put]
    for i in missed:                     # slivers thinner than a texel still get the texel under their centre
        x, y = (int(round(q)) for q in uv[i].mean(0))
        if 0 <= y < H and 0 <= x < W and tri[y, x] < 0:
            tri[y, x] = i; bary[y, x] = (1 / 3, 1 / 3)
    return Layout(uv, (W, H), tri, bary, d, signature(geom))


def _texels(layout):
    ys, xs = np.nonzero(layout.tri >= 0)
    t = layout.tri[ys, xs]; ab = layout.bary[ys, xs].astype(float)
    return ys, xs, t, ab[:, 0], ab[:, 1], 1 - ab[:, 0] - ab[:, 1]


def _dilate(atlas, used):
    """Fill padding from the nearest painted texel, so sampling at an island's edge never picks up a neighbour."""
    if used.all() or not used.any(): return atlas
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(~used, return_distances=False, return_indices=True)
    out = atlas[idx[0], idx[1]]
    out[used] = atlas[used]
    return out


# ================================================================ bake
def _sample(mat, u, v, smooth, box):
    """The renderer's own texel lookup (core.render), for many points at once. Returns RGBA."""
    tex = mat.tex; th, tw = tex.shape[:2]; tpu = mat.tpu
    out = np.zeros((len(u), 4), np.float32)
    near = smooth | (mat.mode == 'nearest')
    if near.any():
        c = tex[(v[near] * tpu).astype(int) % th, (u[near] * tpu).astype(int) % tw]
        out[near, :c.shape[-1]] = c
        if c.shape[-1] == 3: out[near, 3] = 1
    bi = ~near
    if bi.any():
        uu, vv = u[bi], v[bi]
        if mat.mode == 'stretch':
            b = box[bi]
            tx = np.clip((uu - b[:, 0]) / np.maximum(b[:, 1] - b[:, 0], 1e-6) * (tw - 1), 0, tw - 1.001)
            ty = np.clip((vv - b[:, 2]) / np.maximum(b[:, 3] - b[:, 2], 1e-6) * (th - 1), 0, th - 1.001)
        else:
            tx = np.mod(uu * tpu, tw); ty = np.mod(vv * tpu, th)
        xi = np.floor(tx).astype(int); yi = np.floor(ty).astype(int); fx = (tx - xi)[:, None]; fy = (ty - yi)[:, None]
        xi %= tw; yi %= th; xi1 = (xi + 1) % tw; yi1 = (yi + 1) % th
        c = (tex[yi, xi] * (1 - fx) * (1 - fy) + tex[yi, xi1] * fx * (1 - fy) + tex[yi1, xi] * (1 - fx) * fy + tex[yi1, xi1] * fx * fy)
        out[bi, :c.shape[-1]] = c
        if c.shape[-1] == 3: out[bi, 3] = 1
    return out


def bake(geom, layout, mats):
    """The model's materials, unlit, in the atlas: float RGBA (H, W, 4). Role tints and decals included; alpha
    keeps the holes (wire, grating) the renderer would cut."""
    _check(geom, layout)
    W, H = layout.size
    atlas = np.zeros((H, W, 4), np.float32)
    ys, xs, t, la, lb, lc = _texels(layout)
    UV = geom.UV[t]
    u = la * UV[:, 0, 0] + lb * UV[:, 1, 0] + lc * UV[:, 2, 0]
    v = la * UV[:, 0, 1] + lb * UV[:, 1, 1] + lc * UV[:, 2, 1]
    names = geom.mat[t]
    for m in np.unique(names):
        sel = names == m
        atlas[ys[sel], xs[sel]] = _sample(mats.get(m), u[sel], v[sel], geom.look[t[sel]] == SMOOTH, geom.box[t[sel]])
    return _dilate(atlas, layout.used)


def _check(geom, layout):
    if signature(geom) != layout.sig:
        raise ValueError('this layout was made for another model (triangles, polygons or materials differ); unwrap again')


# ================================================================ files
def save_atlas(atlas, path):
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(path)


def load_atlas(path, layout=None):
    im = Image.open(path).convert('RGBA')
    if layout is not None and im.size != layout.size:
        im = im.resize(layout.size, Image.LANCZOS)          # painted at another resolution: same layout, rescaled
    return np.asarray(im).astype(np.float32) / 255


def write_obj(path, geom, layout, texture, unit=1 / 160.0, y_up=True, name=None):
    """Wavefront OBJ + MTL beside it. unit: metres (or the tool's unit) per model unit; 1/160 makes a tile one unit.
    y_up: write Y-up (what OBJ importers expect, Blender turns it back to Z-up on import). Corners shared by
    position and texel are written once. Normals are left to the tool."""
    _check(geom, layout)
    base = os.path.splitext(path)[0]; mtl = base + '.mtl'; name = name or os.path.basename(base)
    W, H = layout.size
    P = geom.P.reshape(-1, 3) * unit
    if y_up: P = np.stack([P[:, 0], P[:, 2], -P[:, 1]], 1)
    T_ = layout.uv.reshape(-1, 2)
    T_ = np.stack([(T_[:, 0] + 0.5) / W, 1 - (T_[:, 1] + 0.5) / H], 1)       # texel centres -> 0..1, origin bottom left
    key = np.round(np.concatenate([P, T_], 1), 7)
    uniq, idx = np.unique(key, axis=0, return_inverse=True)
    idx = idx.reshape(-1, 3) + 1
    with open(mtl, 'w') as f:
        f.write(f'# artkit paint atlas\nnewmtl {name}\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nillum 1\nmap_Kd {texture}\nmap_d {texture}\n')
    with open(path, 'w') as f:
        f.write(f'# artkit model {name}: {len(geom)} triangles, {len(uniq)} corners, 1 unit = {1 / unit:g} model units\n')
        f.write(f'mtllib {os.path.basename(mtl)}\no {name}\n')
        f.write(''.join(f'v {a:.6f} {b:.6f} {c:.6f}\n' for a, b, c in uniq[:, :3]))
        f.write(''.join(f'vt {a:.6f} {b:.6f}\n' for a, b in uniq[:, 3:]))
        f.write(f'usemtl {name}\ns off\n')
        f.write(''.join(f'f {a}/{a} {b}/{b} {c}/{c}\n' for a, b, c in idx))
    return path, mtl


# ================================================================ paint back
def view(geom, style, scale=1.0, pad=16, footprint=None, camera=None, ss=AA):
    """A render to paint over (bigger than game size by default) and the numbers project() needs to map it back.
    Returns (PIL RGBA, view dict)."""
    img, meta = picture(geom, style, footprint=footprint, scale=scale, pad=pad, ss=ss, camera=camera)
    extra = None
    if footprint:
        fx, fy = footprint
        extra = np.array([(0, 0, 0), (fx, 0, 0), (0, fy, 0), (fx, fy, 0)], float)
    cam = getattr(style, 'camera', None) if camera is None else camera
    cv, _, _ = R.Canvas.around(geom, scale, ss, pad, extra, np.float32, camera=cam)
    return img, {'canvas': [cv.W, cv.H, cv.s, cv.cx, cv.cy, cv.ox, cv.oy], 'ss': ss, 'size': list(img.size),
                 'scale': scale, 'pad': pad, 'footprint': list(footprint) if footprint else None}


def _bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    xi = np.floor(x).astype(int); yi = np.floor(y).astype(int); fx = (x - xi)[:, None]; fy = (y - yi)[:, None]
    return (img[yi, xi] * (1 - fx) * (1 - fy) + img[yi, xi + 1] * fx * (1 - fy) + img[yi + 1, xi] * (1 - fx) * fy
            + img[yi + 1, xi + 1] * fx * fy)


def _flat_shade(n):
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    return np.minimum(1.0, 0.60 + 0.40 * np.maximum(0, n[:, 1]) + 0.36 * np.maximum(0, n[:, 2])
                      - 0.10 * np.maximum(0, -n[:, 1]) - 0.06 * np.maximum(0, n[:, 0]))


def project(geom, layout, atlas, painting, view_, style, reference=None, unshade=True, camera=None, mats=None,
            edge_on=0.08, tol=None, threshold=6):
    """Paint `painting` (drawn over the render from view()) onto the faces of geom it covers, in place in atlas.

    geom: the model as it was rendered for that view (an asset's facing(q).geom shares the layout of facing 0).
    painting: PIL image the size of the view render, or larger at the same proportions. Which pixels count:
      - an image with transparency (a paint layer saved on its own): its alpha;
      - a flattened image: the pixels that differ from `reference` (the untouched render) by more than threshold.
    Only faces seen in that view are painted; faces nearly edge-on fade out (edge_on: |cos| below which nothing
    lands). unshade: divide by the light the renderer gave each face (face light, wear; not ambient occlusion or
    grain), so the result is colour before light. Returns the number of texels changed."""
    _check(geom, layout)
    cam = getattr(style, 'camera', None) if camera is None else camera
    mats = style.materials() if mats is None else mats
    W, H, s_, cx, cy, ox, oy = view_['canvas']; ss = view_['ss']; OW, OH = view_['size']
    cv = R.Canvas(int(W), int(H), s_, cx, cy, ox, oy, dtype=np.float32)
    zbuf = R.raster(geom, mats, cv, camera=cam).zbuf
    gv, HZ = R._viewed(geom, cam)
    ys, xs, t, la, lb, lc = _texels(layout)
    Pt = gv.P[t]
    p = la[:, None] * Pt[:, 0] + lb[:, None] * Pt[:, 1] + lc[:, None] * Pt[:, 2]
    rx = ((p[:, 0] - p[:, 1]) - cx) * s_ + ox; ry = (((p[:, 0] + p[:, 1]) / 2 - p[:, 2]) - cy) * s_ + oy
    d = p.sum(1) + gv.bias[t]
    inb = (rx >= 0) & (rx < W) & (ry >= 0) & (ry < H)
    zb = np.full(len(t), np.inf); zb[inb] = zbuf[ry[inb].astype(int), rx[inb].astype(int)]
    tol = (2.0 + 4.0 / s_) if tol is None else tol
    vis = inb & (d >= zb - tol)
    sm = gv.look[t] == SMOOTH
    Nc = la[:, None] * gv.N[t, 0] + lb[:, None] * gv.N[t, 1] + lc[:, None] * gv.N[t, 2]
    ndv = np.where(sm, (gv.N[t].mean(1) @ VIEW), np.abs(gv.FN[t] @ VIEW))     # flat faces may be wound either way
    w = np.clip((ndv - edge_on) / 0.25, 0, 1) * vis
    # the painting, at its own resolution
    pim = painting.convert('RGBA'); PW, PH = pim.size
    pa = np.asarray(pim).astype(np.float32) / 255
    k = PW / OW
    if abs(PH / OH - k) > 0.02: raise ValueError(f'painting is {PW}x{PH}; the view was {OW}x{OH} (same proportions needed)')
    qx = (rx / ss) * k - 0.5; qy = (ry / ss) * k - 0.5
    col = _bilinear(pa, qx, qy)
    if (pa[..., 3] < 0.999).any():
        mask = col[:, 3]
    else:
        if reference is None: raise ValueError('a flattened painting needs the untouched render as reference')
        ra = np.asarray(reference.convert('RGBA').resize((PW, PH), Image.LANCZOS) if reference.size != (PW, PH)
                        else reference.convert('RGBA')).astype(np.float32) / 255
        diff = np.abs(col[:, :3] - _bilinear(ra, qx, qy)[:, :3]).max(1) * 255
        mask = np.clip((diff - threshold) / (2 * threshold), 0, 1)
    a = (w * mask).astype(np.float32)
    rgb = col[:, :3]
    if unshade:
        L = np.ones(len(t))
        fl = ~sm
        shade = gv.shade[t]
        L[fl] = np.where(np.isnan(shade[fl]), _flat_shade(gv.FN[t][fl]), shade[fl])
        hz = la * HZ[t, 0] + lb * HZ[t, 1] + lc * HZ[t, 2]
        em = gv.emit[t] | np.array([mats.get(m).emissive for m in gv.mat[t]], bool)
        worn = fl & gv.wear[t] & (np.abs(gv.FN[t][:, 2]) < 0.6) & ~em
        L[worn] *= 1 - light.WEAR * np.exp(-np.clip(hz[worn], 0, None) / light.WEAR_FALLOFF)
        if sm.any():
            SH = light.smooth_shade(gv.N[t][sm])
            L[sm] = la[sm] * SH[:, 0] + lb[sm] * SH[:, 1] + lc[sm] * SH[:, 2]
        L[em] = 1.0
        rgb = np.clip(rgb / np.maximum(L, 0.2)[:, None], 0, 1)
    old = atlas[ys, xs]
    new = old.copy()
    new[:, :3] = old[:, :3] * (1 - a[:, None]) + rgb * a[:, None]
    new[:, 3] = np.maximum(old[:, 3], np.where(a > 0.5, 1.0, 0.0))     # paint may fill a hole; never cuts one
    atlas[ys, xs] = new
    atlas[:] = _dilate(atlas, layout.used)
    return int((a > 0.02).sum())


def painted(geom, layout, atlas, mats, name='paint'):
    """geom wearing the atlas. The atlas becomes material `name` in mats (a Materials registry, e.g.
    style.materials()); glowing materials keep glowing, wire keeps casting no line. Draw it with sprite.picture,
    Exporter.static or anything else."""
    _check(geom, layout)
    mats.add(name, Material(np.ascontiguousarray(atlas, np.float32), 'tile', 1.0))
    base = np.array([str(m).split('@')[0] for m in geom.mat], object)
    em = geom.emit | np.array([mats.get(m).emissive for m in geom.mat], bool)
    thin = np.where((geom.thin < 0) & (base == 'wire'), 1, geom.thin).astype(np.int8)
    return geom._new(UV=layout.uv.copy(), mat=np.full(len(geom), name, object), emit=em, thin=thin)


def paint_asset(asset, layout, atlas, mats, name='paint'):
    """An Asset whose model wears the atlas: its stages, facings and turning parts all show the paint."""
    from .recipe import Asset
    a = Asset(asset.spec, geom=painted(asset.geom, layout, atlas, mats, name), names=asset.names)
    a.assembly = asset.assembly
    return a


# ================================================================ command line
def load_asset(spec, key=None):
    """A recipe .json, or module:function[:argument] returning an Asset, a Geometry or a recipe dict."""
    from .recipe import Asset
    from .core.geom import Geometry
    if spec.endswith('.json'): return Asset.load(spec)
    if os.getcwd() not in sys.path: sys.path.insert(0, os.getcwd())
    mod, _, rest = spec.partition(':'); fn, _, arg = rest.partition(':')
    f = getattr(importlib.import_module(mod), fn)
    r = f(arg) if arg else f()
    if isinstance(r, Asset): return r
    if isinstance(r, Geometry): return Asset({'name': key or fn}, geom=r)
    if isinstance(r, dict): return Asset(r)
    if hasattr(r, 'geometry'): return Asset({'name': key or fn}, geom=r.geometry())
    raise TypeError(f'{spec} gave {type(r).__name__}, not an Asset, Geometry or recipe')


def _style(name):
    from .style import Style
    return Style.load(name)


def cmd_export(a):
    style = _style(a.style); asset = load_asset(a.asset, a.key)
    key = a.key or os.path.splitext(os.path.basename(a.asset.split(':')[-1] or a.asset))[0]
    os.makedirs(a.out, exist_ok=True); mats = style.materials()
    layout = unwrap(asset.geom, density=a.density, max_size=a.max_size, mats=mats)
    atlas = bake(asset.geom, layout, mats)
    j = lambda f: os.path.join(a.out, f)
    layout.save(j(f'{key}_layout.npz')); save_atlas(atlas, j(f'{key}_paint.png')); save_atlas(atlas, j(f'{key}_base.png'))
    write_obj(j(f'{key}.obj'), asset.geom, layout, f'{key}_paint.png', name=key)
    src = os.path.abspath(a.asset) if a.asset.endswith('.json') else a.asset
    views = {'asset': src, 'key': key, 'style': os.path.basename(os.path.normpath(style.root)), 'views': {}}
    step = 4 // a.facings
    for i in range(a.facings):
        q = i * step; f = asset.facing(q)
        img, v = view(f.geom, style, scale=a.view_scale, footprint=f.footprint)
        img.save(j(f'{key}_view{q}.png')); views['views'][str(q)] = v
    json.dump(views, open(j(f'{key}_views.json'), 'w'), indent=1)
    W, H = layout.size
    print(f'{key}: {len(asset.geom)} triangles, atlas {W}x{H} at {layout.density:.3g} texels/unit, '
          f'{int(layout.used.sum())} texels used; views {sorted(views["views"], key=int)} at scale {a.view_scale}')


def _reload(out, key):
    meta = json.load(open(os.path.join(out, f'{key}_views.json')))
    style = _style(meta['style']); asset = load_asset(meta['asset'], key)
    layout = Layout.load(os.path.join(out, f'{key}_layout.npz'))
    return meta, style, asset, layout


def cmd_project(a):
    meta, style, asset, layout = _reload(a.out, a.key)
    path = os.path.join(a.out, f'{a.key}_paint.png')
    atlas = load_atlas(path, layout).copy()
    q = str(a.facing)
    if q not in meta['views']: raise SystemExit(f'no view {q} was exported (have {sorted(meta["views"])})')
    ref = Image.open(os.path.join(a.out, f'{a.key}_view{q}.png'))
    n = project(asset.facing(int(q)).geom, layout, atlas, Image.open(a.painting), meta['views'][q], style, reference=ref,
                unshade=not a.keep_light)
    save_atlas(atlas, path)
    print(f'{a.key}: {n} texels painted from {os.path.basename(a.painting)} (facing {q}) into {os.path.basename(path)}')


def cmd_preview(a):
    meta, style, asset, layout = _reload(a.out, a.key)
    mats = style.materials()
    pa = paint_asset(asset, layout, load_atlas(os.path.join(a.out, f'{a.key}_paint.png'), layout), mats, name=f'paint:{a.key}')
    for q in sorted(meta['views'], key=int):
        f = pa.facing(int(q))
        img, _ = picture(f.geom, style, footprint=f.footprint, scale=a.scale)
        fn = os.path.join(a.out, f'{a.key}_painted{q}.png'); img.save(fn); print(fn)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python3 -m artkit.mesh', description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    e = sp.add_parser('export', help='OBJ + paint atlas + views to paint over')
    e.add_argument('asset'); e.add_argument('out'); e.add_argument('--key'); e.add_argument('--style')
    e.add_argument('--density', type=float, default=None); e.add_argument('--max-size', type=int, default=4096)
    e.add_argument('--facings', type=int, default=1, choices=(1, 2, 4)); e.add_argument('--view-scale', type=float, default=1.0)
    p = sp.add_parser('project', help='project a paintover of a view into the atlas')
    p.add_argument('out'); p.add_argument('key'); p.add_argument('painting'); p.add_argument('--facing', type=int, default=0)
    p.add_argument('--keep-light', action='store_true', help='do not divide out the light (it will be applied again)')
    v = sp.add_parser('preview', help='render the painted model from every exported facing')
    v.add_argument('out'); v.add_argument('key'); v.add_argument('--scale', type=float, default=0.4)
    a = ap.parse_args(argv)
    {'export': cmd_export, 'project': cmd_project, 'preview': cmd_preview}[a.cmd](a)


if __name__ == '__main__':
    main()
