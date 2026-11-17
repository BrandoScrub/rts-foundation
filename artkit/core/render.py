"""artkit.core.render: the one renderer. Geometry in, an anti-aliased RGBA sprite out.

Two stages:
  raster(geom, mats, canvas)  z-buffered triangles into supersampled buffers (colour, coverage, depth, flags)
  finish(buffers, ...)        ambient occlusion (flat look), the line pass from core.ink, exact box downsample

Each triangle is drawn in its own look (core.light): FLAT triangles keep isokit's rules (face light, bilinear
tiles, wear, grain, holes where a texture is transparent), SMOOTH triangles keep unitkit's (corner light, nearest
texel, back faces culled). One picture can mix both: a flat-shaded hull on a smooth-shaded figure.

A Canvas says where the picture is: W x H raster pixels, s raster pixels per unit, and the screen origin.
Screen x of a world point is ((x - y) - cx) * s + ox; screen y is (((x + y) / 2 - z) - cy) * s + oy.

camera (core.space.Camera, optional everywhere): the view the geometry was modelled for. Under the default (None or
Camera.ISO) nothing is converted. Under another view the geometry is carried into the engine frame first; ground
plates and wear are judged on the model's own height above the camera's ground, and hair-thin faces on its own sizes.
"""
import math
import numpy as np

from . import ink as inklib
from . import light
from .geom import FLAT, SMOOTH

THIN = 4.5            # a face with a side shorter than this (units) is hair-thin: it reads as a line already
LOW = 8.0             # a face entirely below this height is a ground plate: no outline against empty ground


class Canvas:
    def __init__(s, W, H, s_, cx=0.0, cy=0.0, ox=0.0, oy=0.0, dtype=np.float64):
        s.W, s.H, s.s, s.cx, s.cy, s.ox, s.oy, s.dtype = W, H, s_, cx, cy, ox, oy, dtype

    @staticmethod
    def around(geom, scale, ss=5, pad=24, extra=None, dtype=np.float32, camera=None):
        """A canvas fitted to the geometry (plus optional extra world points), as isokit frames buildings.
        Returns (canvas, (minx, miny), (output width, output height)). camera: the view geom was modelled for."""
        P = geom.P.reshape(-1, 3)
        if camera is not None:
            P = camera.to_engine(P)
            if extra is not None and len(extra): extra = camera.to_engine(extra)
        sx = P[:, 0] - P[:, 1]; sy = (P[:, 0] + P[:, 1]) / 2 - P[:, 2]
        if extra is not None and len(extra):
            E = np.asarray(extra, float)
            sx = np.concatenate([sx, E[:, 0] - E[:, 1]]); sy = np.concatenate([sy, (E[:, 0] + E[:, 1]) / 2 - E[:, 2]])
        minx, maxx = math.floor(sx.min()) - pad, math.ceil(sx.max()) + pad
        miny, maxy = math.floor(sy.min()) - pad, math.ceil(sy.max()) + pad
        OW, OH = math.ceil((maxx - minx) * scale), math.ceil((maxy - miny) * scale)
        return Canvas(OW * ss, OH * ss, scale * ss, cx=minx, cy=miny, dtype=dtype), (minx, miny), (OW, OH)


class Buffers:
    def __init__(s, cv):
        H, W, dt = cv.H, cv.W, cv.dtype
        s.color = np.zeros((H, W, 3), dt); s.alpha = np.zeros((H, W), dt)
        s.zbuf = np.full((H, W), -1e9, dt)
        s.emit = np.zeros((H, W), bool); s.thin = np.zeros((H, W), bool); s.low = np.zeros((H, W), bool)
        s.flat = np.zeros((H, W), bool)
        s.part = np.full((H, W), -1, np.int32)
        s.team = None         # bool (H, W) when raster is asked to record team-coloured pixels (artkit.team)
        s.tri = None; s.FN = None   # triangle per pixel and face normals, when asked (crease lines, core.ink.creases)


def grain_field(out_w, out_h, ss, seed=7, amount=light.GRAIN):
    """Per output pixel brightness jitter for the flat look, repeated over the supersampled pixels."""
    rng = np.random.default_rng(seed)
    return ((rng.random((out_h, out_w)).astype(np.float32) - 0.5) * amount).repeat(ss, 0).repeat(ss, 1)


def _viewed(geom, camera):
    """(geometry in the engine frame, per-corner height above ground) for a camera; the geometry itself and its z
    under the default camera."""
    if camera is None or camera.iso: return geom, geom.P[..., 2]
    hz = camera.height(geom.P)
    if (geom.thin < 0).any():                # hair-thin is a matter of the model's own sizes, not of the view
        P = geom.P
        side = np.linalg.norm(np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 1], P[:, 0] - P[:, 2]], 1), axis=2).min(1)
        wire = np.array([str(m).split('@')[0] == 'wire' for m in geom.mat], bool)
        geom = geom._new(thin=np.where(geom.thin < 0, wire | (side < THIN), geom.thin).astype(np.int8))
    return camera.view(geom), hz


def raster(geom, mats, cv, grain=None, cull=True, buf=None, camera=None, team=None, faces=False):
    """team: a callable material name -> bool (artkit.team.Team), or None. With it, B.team marks every pixel whose
    visible face wears a team-coloured material; nothing else in the picture changes.
    faces: also record which triangle shows at each pixel (B.tri, B.FN), for crease lines."""
    geom, HZ = _viewed(geom, camera)
    W, H, sc = cv.W, cv.H, cv.s
    B = buf or Buffers(cv)
    if team is not None and getattr(B, 'team', None) is None: B.team = np.zeros((H, W), bool)
    if faces:
        B.tri = np.full((H, W), -1, np.int32); B.FN = np.asarray(geom.FN, float)
    tflag = None if team is None else np.array([bool(team(str(m))) for m in geom.mat], bool)
    color, alpha, zbuf = B.color, B.alpha, B.zbuf
    P = geom.P
    SX = ((P[..., 0] - P[..., 1]) - cv.cx) * sc + cv.ox
    SY = (((P[..., 0] + P[..., 1]) / 2 - P[..., 2]) - cv.cy) * sc + cv.oy
    D = P[..., 0] + P[..., 1] + P[..., 2] + geom.bias[:, None]
    sm = geom.look == SMOOTH
    keep = np.ones(len(geom), bool)
    SH = np.zeros((len(geom), 3))
    if sm.any():
        if cull: keep[sm] = (geom.N[sm].mean(1) @ light.VIEW) > -0.3
        SH[sm] = light.smooth_shade(geom.N[sm])
    low = geom.low
    if camera is not None and not getattr(camera, 'plates', True):
        low = np.where(low < 0, 0, low)      # the camera says no face is a ground plate (a unit's tracks and feet)
    if (low < 0).any():                      # ground plates are judged per source polygon, as isokit did
        _, inv = np.unique(geom.face, return_inverse=True)
        zmax = np.full(inv.max() + 1, -np.inf); np.maximum.at(zmax, inv, HZ.max(1))
        low = np.where(low < 0, zmax[inv] < LOW, low)
    for i in np.nonzero(keep)[0]:
        mat = mats.get(geom.mat[i])
        if geom.look[i] == SMOOTH:
            _tri_smooth(B, i, SX[i], SY[i], D[i], geom, mat, SH[i], W, H, None if tflag is None else tflag[i])
        else:
            _tri_flat(B, i, SX[i], SY[i], D[i], geom, mat, grain, W, H, low[i], HZ[i], None if tflag is None else tflag[i])
    return B


def _tri_flat(B, i, sxv, syv, d, geom, mat, grain, W, H, lo_, zz, tm=None):
    """isokit's rules, unchanged. The same arithmetic as before, done only on the pixels the triangle covers (and,
    after the depth test, only on those it shows on) rather than its whole bounding box: byte-identical, faster."""
    color, alpha, zbuf = B.color, B.alpha, B.zbuf
    n = geom.FN[i]
    shade = geom.shade[i] if not np.isnan(geom.shade[i]) else light.flat_shade(n)
    Pt = geom.P[i]
    th_ = geom.thin[i]
    if th_ < 0:
        th_ = mat.name.split('@')[0] == 'wire' or min(np.linalg.norm(Pt[j] - Pt[j - 1]) for j in range(3)) < THIN
    tex = mat.tex; tiled = mat.mode != 'stretch'; tpu = mat.tpu
    th, tw = tex.shape[:2]
    s = np.stack([sxv, syv], 1); uv = geom.UV[i]
    x0, x1 = max(int(np.floor(s[:, 0].min())), 0), min(int(np.ceil(s[:, 0].max())) + 1, W)
    y0, y1 = max(int(np.floor(s[:, 1].min())), 0), min(int(np.ceil(s[:, 1].max())) + 1, H)
    if x1 <= x0 or y1 <= y0: return
    (ax, ay), (bx, by), (cx, cy) = s
    den = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    if abs(den) < 1e-9: return
    gx = (np.arange(x0, x1) + 0.5)[None, :]; gy = (np.arange(y0, y1) + 0.5)[:, None]
    dn = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    dx = gx - cx; dy = gy - cy
    la = ((by - cy) * dx + (cx - bx) * dy) / dn
    lb = ((cy - ay) * dx + (ax - cx) * dy) / dn
    lc = 1 - la - lb
    eps = -1e-3
    inside = (la >= eps) & (lb >= eps) & (lc >= eps)
    ys, xs = np.nonzero(inside)
    if not len(ys): return
    la = la[ys, xs]; lb = lb[ys, xs]; lc = lc[ys, xs]
    z = la * d[0] + lb * d[1] + lc * d[2]
    sub = zbuf[y0:y1, x0:x1]
    k = z > sub[ys, xs]
    if not k.any(): return
    ys = ys[k]; xs = xs[k]; la = la[k]; lb = lb[k]; lc = lc[k]; z = z[k]
    u = la * uv[0, 0] + lb * uv[1, 0] + lc * uv[2, 0]
    v = la * uv[0, 1] + lb * uv[1, 1] + lc * uv[2, 1]
    if tiled:
        if mat.mode == 'nearest':
            c = tex[(v * tpu).astype(int) % th, (u * tpu).astype(int) % tw]
            if c.shape[-1] == 3: c = np.concatenate([c, np.ones(c.shape[:-1] + (1,), c.dtype)], -1)
        else:
            tx = np.mod(u * tpu, tw); ty = np.mod(v * tpu, th)
    else:
        umin, umax, vmin, vmax = geom.box[i]
        tx = np.clip((u - umin) / max(umax - umin, 1e-6) * (tw - 1), 0, tw - 1.001)
        ty = np.clip((v - vmin) / max(vmax - vmin, 1e-6) * (th - 1), 0, th - 1.001)
    if mat.mode != 'nearest':
        xi = np.floor(tx).astype(int); yi = np.floor(ty).astype(int); fx = tx - xi; fy = ty - yi
        xi %= tw; yi %= th
        xi1 = (xi + 1) % tw; yi1 = (yi + 1) % th
        c = (tex[yi, xi] * ((1 - fx) * (1 - fy))[..., None] + tex[yi, xi1] * (fx * (1 - fy))[..., None]
             + tex[yi1, xi] * ((1 - fx) * fy)[..., None] + tex[yi1, xi1] * (fx * fy)[..., None])
        if c.shape[-1] == 3: c = np.concatenate([c, np.ones(c.shape[:-1] + (1,), c.dtype)], -1)
    k = c[..., 3] > 0.5
    if not k.any(): return
    if not k.all():
        ys = ys[k]; xs = xs[k]; la = la[k]; lb = lb[k]; lc = lc[k]; z = z[k]; c = c[k]
    rgb = c[..., :3] * shade
    em = bool(geom.emit[i]) or mat.emissive
    if not em:
        if geom.wear[i] and abs(n[2]) < 0.6:
            hz = la * zz[0] + lb * zz[1] + lc * zz[2]
            rgb = rgb * (1 - light.WEAR * np.exp(-np.clip(hz, 0, None) / light.WEAR_FALLOFF))[..., None]
        if grain is not None:
            rgb = rgb * (1 + grain[y0:y1, x0:x1][ys, xs])[..., None]
    Y = ys + y0; X = xs + x0
    color[Y, X] = rgb
    alpha[Y, X] = 1
    B.thin[Y, X] = th_; B.low[Y, X] = lo_; B.emit[Y, X] = em
    B.flat[Y, X] = True; B.part[Y, X] = geom.part[i]
    if tm is not None: B.team[Y, X] = tm
    if B.tri is not None: B.tri[Y, X] = i
    sub[ys, xs] = z


def _tri_smooth(B, i, SX, SY, D, geom, mat, SH, W, H, tm=None):
    """unitkit's rules, unchanged."""
    zb, col = B.zbuf, B.color
    x0, x1, x2 = SX; y0, y1, y2 = SY
    ax = max(int(math.floor(min(x0, x1, x2))), 0); bx = min(int(math.ceil(max(x0, x1, x2))), W - 1)
    ay = max(int(math.floor(min(y0, y1, y2))), 0); by = min(int(math.ceil(max(y0, y1, y2))), H - 1)
    if ax > bx or ay > by: return
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(area) < 1e-9: return
    px = np.arange(ax, bx + 1) + .5; py = (np.arange(ay, by + 1) + .5)[:, None]
    w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area
    w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area
    w2 = 1 - w0 - w1
    ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not ins.any(): return
    d = w0 * D[0] + w1 * D[1] + w2 * D[2]
    zs = zb[ay:by + 1, ax:bx + 1]
    m = ins & (d > zs)
    if not m.any(): return
    tex = mat.tex; k = mat.tpu; UV = geom.UV[i]
    u = (w0 * UV[0, 0] + w1 * UV[1, 0] + w2 * UV[2, 0])[m]
    v = (w0 * UV[0, 1] + w1 * UV[1, 1] + w2 * UV[2, 1])[m]
    c = tex[(v * k).astype(int) % tex.shape[0], (u * k).astype(int) % tex.shape[1]]
    if c.shape[-1] == 4:
        hole = c[:, 3] <= 0.5
        if hole.any():
            m2 = m.copy(); m2[m] = ~hole; m = m2; c = c[~hole]; u = u[~hole]
            if not m.any(): return
        c = c[:, :3]
    em = bool(geom.emit[i]) or mat.emissive
    if not em:
        c = c * (w0 * SH[0] + w1 * SH[1] + w2 * SH[2])[m][:, None]
    zs[m] = d[m]
    col[ay:by + 1, ax:bx + 1][m] = c
    B.alpha[ay:by + 1, ax:bx + 1][m] = 1
    B.emit[ay:by + 1, ax:bx + 1][m] = em
    B.part[ay:by + 1, ax:bx + 1][m] = geom.part[i]
    if tm is not None: B.team[ay:by + 1, ax:bx + 1][m] = tm
    if getattr(B, 'tri', None) is not None: B.tri[ay:by + 1, ax:bx + 1][m] = i


def _boxblur(a, r):
    p = np.pad(a, r, mode='edge'); c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def ambient(B, px, rules=None):
    """Screen-space ambient occlusion on flat-look pixels (isokit's rule). rules: core.light.Rules or None (defaults)."""
    radii, depth, strength = (light.AO, light.AO_DEPTH, light.AO_STRENGTH) if rules is None else \
        (rules.ao_radii, rules.ao_depth, rules.ao_strength)
    alpha, zbuf = B.alpha, B.zbuf
    zfill = np.where(alpha > 0, zbuf, 0.0)
    ao = np.zeros_like(alpha)
    for r, w in radii:
        r = max(1, int(round(r * px)))
        m = _boxblur(zfill, r) / np.maximum(_boxblur(alpha, r), 1e-6)
        ao += w * np.clip((m - zfill) / depth, 0, 1)
    ao = np.clip(ao, 0, 1) * alpha
    if not B.flat.all():
        ao = np.where(B.flat | (alpha == 0), ao, 0)
    B.color *= (1 - strength * ao)[..., None]


def relief(B, strength, span, ref=1.0):
    """Darken by depth behind the picture's nearest point, or the `ref` quantile of its depths (core.light.Rules,
    "relief"). Emissive pixels untouched."""
    solid = B.alpha > 0
    if strength <= 0 or not solid.any(): return
    top = B.zbuf[solid].max() if ref >= 1 else float(np.quantile(B.zbuf[solid], ref))
    t = np.clip((top - B.zbuf) / max(span, 1e-6), 0, 1)
    f = np.where(solid & ~B.emit, 1 - strength * t, 1.0)
    B.color *= f[..., None]


def finish(B, ss, line_px, edge_step, ao_px=None, no_seed=None, no_rim=None, full=None, ink_emit=False, rules=None):
    """Lines and downsample. line_px: line width in raster pixels (core.ink.radius). ao_px: raster pixels per unit
    for ambient occlusion, None for none. full: coverage of the whole figure when this picture is one layer of it, so
    no outside line falls where another layer will sit. rules: core.light.Rules from the style's "light" section
    (relief, ambient occlusion and ink constants), None for the engine defaults. Returns uint8 RGBA at 1/ss size."""
    if ao_px is not None: ambient(B, ao_px, rules)
    if rules is not None: relief(B, rules.relief_strength, rules.relief_span, rules.relief_ref)
    solid = B.alpha > 0
    seedless = B.emit if no_seed is None else no_seed
    if rules is not None and getattr(rules, 'weighted', False):
        r = line_px * (1.0 if rules.ink_width is None else rules.ink_width)
        step = edge_step if rules.ink_step is None else rules.ink_step
        ri = r * (1.0 if rules.ink_inner is None else rules.ink_inner)
        cs = rc = None
        if rules.ink_crease is not None and getattr(B, 'tri', None) is not None:
            cs = inklib.creases(B.tri, B.FN, B.flat, rules.ink_crease, no_seed=seedless)
            rc = r * (rules.ink_crease_width if rules.ink_crease_width is not None else (rules.ink_inner if rules.ink_inner is not None else 0.5))
        ink = inklib.lines_weighted(B.zbuf, solid, r, step, no_seed=seedless, no_rim=no_rim, r_inner=ri, crease_seed=cs, r_crease=rc)
    else:
        ink = inklib.lines(B.zbuf, solid, line_px, edge_step, no_seed=seedless, no_rim=no_rim)
    color = np.clip(B.color, 0, 1)
    paint = ink & solid & (~B.emit | ink_emit)
    cover = inklib.INK_COVER if rules is None or rules.ink_cover is None else rules.ink_cover
    color[paint] += (inklib.INK - color[paint]) * cover
    alpha = B.alpha.copy()
    rim = ink & ~(solid if full is None else full)
    color[rim] = inklib.INK; alpha[rim] = cover
    h, w = solid.shape
    pm = np.concatenate([color * alpha[..., None], alpha[..., None]], 2).reshape(h // ss, ss, w // ss, ss, 4).mean((1, 3))
    a_ = pm[..., 3:]
    pm[..., :3] = np.where(a_ > 1e-6, pm[..., :3] / np.maximum(a_, 1e-6), 0)
    return (np.clip(pm, 0, 1) * 255 + 0.5).astype(np.uint8)
