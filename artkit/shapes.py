"""artkit.shapes: every primitive, one geometry type.

Hard-surface (flat look, isokit's set): quad, polygon, box, wedge, gable, prism, lathe, extrude, pyramid, strut,
  lattice, plane.
Rounded (smooth look, unitkit's set): blob_lathe, sphere, ellipsoid, cyl, beam, slab.
New:
  sweep(path, profile)    a profile carried along a 3D path: pipes, cables, rails, hoses, roads, trenches
  ribbon(path, width)     a flat strip lying on the ground along a path: roads, tracks, rivers
  catenary(a, b, sag)     the path a hanging cable takes, for sweep
  heightfield(fn, ...)    terrain: cliffs, craters, mounds, with material chosen by slope and height
  rock(size, seed)        a lumpy faceted boulder
  conifer / broadleaf     trees
  scatter(fn, area, n)    many varied copies in an area or along a path: forests, rubble, crates, debris
All take a material name and optional face flags (emit, wear, bias, shade, part). Units: 160 = one tile.
"""
import math
import numpy as np

from .core.geom import Geometry, FLAT, SMOOTH, T, RX, RY, RZ, R3, S, aim, unit, xf

THIN = 4.5     # a polygon with a side shorter than this is hair-thin: it reads as a line already and casts none


# ---------------------------------------------------------------- building blocks
class Build:
    """Collects polygons (fan-triangulated) and turns them into one Geometry."""

    def __init__(s):
        s.P, s.UV, s.FN, s.N, s.M, s.A, s.BX, s.F, s.TH = [], [], [], [], [], [], [], [], []
        s.nf = 0

    def poly(s, pts, uvs, mat, normals=None, **attrs):
        pts = np.asarray(pts, float); uvs = np.asarray(uvs, float)
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0]); l = np.linalg.norm(n)
        fn = n / l if l > 1e-9 else np.array([0, 0, 1.0])
        bx = (uvs[:, 0].min(), uvs[:, 0].max(), uvs[:, 1].min(), uvs[:, 1].max())
        thin = int(mat.split('@')[0] == 'wire' or min(np.linalg.norm(pts[j] - pts[j - 1]) for j in range(len(pts))) < THIN)
        for i in range(1, len(pts) - 1):
            idx = [0, i, i + 1]
            s.P.append(pts[idx]); s.UV.append(uvs[idx]); s.FN.append(fn); s.M.append(mat); s.A.append(attrs); s.BX.append(bx)
            s.N.append(np.repeat(fn[None], 3, 0) if normals is None else np.asarray(normals, float)[idx])
            s.F.append(s.nf); s.TH.append(thin)
        s.nf += 1
        return s

    def geometry(s, look=FLAT):
        n = len(s.P)
        if not n: return Geometry()
        g = Geometry(P=np.array(s.P), UV=np.array(s.UV), FN=np.array(s.FN), N=np.array(s.N), mat=np.array(s.M, object),
                     box=np.array(s.BX), look=look, face=s.F, thin=s.TH)
        for k in ('emit', 'wear', 'bias', 'shade', 'part', 'thin'):
            vals = [a.get(k) for a in s.A]
            if any(v is not None for v in vals):
                arr = getattr(g, k).copy()
                for i, v in enumerate(vals):
                    if v is not None: arr[i] = v
                setattr(g, k, arr)
        return g


def _flags(kw):
    return {k: kw[k] for k in ('emit', 'wear', 'bias', 'shade', 'part', 'thin') if k in kw}


def convex(points, mat, look=FLAT, **kw):
    """The solid enclosed by a set of points (their convex hull): plates with chamfers, castings rounded by giving
    more points, hoods, wedges, any block with more than eight corners. Coplanar triangles are merged into one face,
    so a flat side is one face (one light, one crease at its edges), and every face points outward."""
    from scipy.spatial import ConvexHull
    P = np.asarray(points, float)
    hull = ConvexHull(P)
    groups = {}
    for simplex, eq in zip(hull.simplices, hull.equations):
        key = tuple(np.round(eq, 5))
        g = groups.setdefault(key, [eq, set()]); g[1].update(simplex.tolist())
    b = Build(); f = _flags(kw)
    for eq, idx in groups.values():
        n = eq[:3]; pts = P[sorted(idx)]
        c = pts.mean(0)
        u = pts[0] - c; u -= n * (u @ n); u /= np.linalg.norm(u) + 1e-12
        v = np.cross(n, u)
        ang = np.arctan2((pts - c) @ v, (pts - c) @ u)
        pts = pts[np.argsort(ang)]                     # counter-clockwise seen from outside (right-handed u, v, n)
        uvs = np.stack([(pts - c) @ u, (pts - c) @ v], 1)
        b.poly(pts, uvs, mat, **f)
    return b.geometry(look)


def soften(g, angle=50.0, look=SMOOTH):
    """Rounded shading for a faceted shape (a casting, a dome made of facets): each corner's normal becomes the
    average of the faces meeting there within `angle` degrees of its own face, so facets blend while real edges (a
    shield's back, a hull's corner) stay sharp. Returns the geometry in the smooth look (no crease lines inside it)."""
    P = np.asarray(g.P, float); FN = np.asarray(g.FN, float)
    key = np.round(P.reshape(-1, 3), 3)
    _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
    fn_c = np.repeat(FN, 3, 0)                                   # each corner's own face normal
    order = np.argsort(inv, kind='stable'); groups = np.split(order, np.nonzero(np.diff(inv[order]))[0] + 1)
    c = np.cos(np.radians(angle)); N = fn_c.copy()
    for grp in groups:
        if len(grp) < 2: continue
        F = fn_c[grp]; near = (F @ F.T) >= c
        avg = near.astype(float) @ F
        N[grp] = avg / np.maximum(np.linalg.norm(avg, axis=1, keepdims=True), 1e-9)
    return g._new(N=N.reshape(P.shape), look=np.full(len(g), look, dtype=np.asarray(g.look).dtype))


def belt_path(circles, step=4.0):
    """The centre line of a belt or track wrapped round circles, in the x-z plane: circles [(x, z, r)] in the order the
    belt meets them going anticlockwise (x right, z up: along the bottom forward, up the front, back along the top,
    down the rear), r measured to the belt's centre line. Straight runs are the true tangents between circles and the
    belt follows each circle's arc between them, so it is one continuous line. Returns a closed list of (x, z), and the
    wrap angle in degrees on each circle (about 0 for a wheel the belt only grazes; a circle the belt cannot reach
    from the outside comes back as None)."""
    C = [tuple(map(float, c)) for c in circles]; n = len(C)
    tang = []                                     # outward normal angle where the belt leaves circle i for circle i+1
    for i in range(n):
        (ax, az, ar), (bx, bz, br) = C[i], C[(i + 1) % n]
        dx, dz = bx - ax, bz - az; L = math.hypot(dx, dz)
        th = math.atan2(dz, dx); ph = math.acos(max(-1.0, min(1.0, (ar - br) / L)))
        tang.append(th - ph)                      # the normal on the right of the travel direction: outside the loop
    pts, wraps = [], []
    for i in range(n):
        x, z, r = C[i]
        a0 = tang[i - 1]; a1 = tang[i]
        span = (a1 - a0) % (2 * math.pi)
        (px, pz, _), (qx, qz, _) = C[i - 1], C[(i + 1) % n]
        turn = (x - px) * (qz - z) - (z - pz) * (qx - x)              # > 0: the belt turns left here, round the outside
        if span > math.radians(300) or (span > math.pi and turn < 0):      # below the run or inside the loop: it misses
            wraps.append(None); span = 0.0
        else: wraps.append(math.degrees(span))
        k = max(1, int(math.ceil(span * r / step)))
        for j in range(k + 1):
            a = a0 + span * j / k; pts.append((x + r * math.cos(a), z + r * math.sin(a)))
    pts.append(pts[0])
    return pts, wraps


def belt(path, y0, y1, thickness, mat, teeth=None, look=FLAT, phase=0.0, **kw):
    """One continuous band along a closed x-z path (belt_path), from y0 to y1, `thickness` thick and centred on the
    path: neighbouring pieces share their edges, so it cannot open gaps. teeth: (pitch, length, height) blocks on the
    outside (a track's end connectors), each standing on the band. phase: shifts the teeth along the path (units, in
    the path's direction), so a running track can be drawn: -distance driven keeps the links on the ground still."""
    P = [np.array(p, float) for p in path[:-1]]; n = len(P)
    N = []
    for i in range(n):                            # outward normal at each point: the mean of its two segments'
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        t = (c - a); t /= np.linalg.norm(t) + 1e-12
        N.append(np.array([t[1], -t[0]]))
    h = thickness / 2.0
    inner = [p - h * q for p, q in zip(P, N)]; outer = [p + h * q for p, q in zip(P, N)]
    X = lambda q, y: (q[0], y, q[1])
    b = Build(); f = _flags(kw); along = 0.0
    for i in range(n):
        j = (i + 1) % n; L = float(np.linalg.norm(P[j] - P[i]))
        u0, u1 = along, along + L
        b.poly([X(outer[i], y0), X(outer[j], y0), X(outer[j], y1), X(outer[i], y1)], [(u0, y0), (u1, y0), (u1, y1), (u0, y1)], mat, **f)
        b.poly([X(inner[i], y1), X(inner[j], y1), X(inner[j], y0), X(inner[i], y0)], [(u0, y1), (u1, y1), (u1, y0), (u0, y0)], mat, **f)
        b.poly([X(inner[i], y0), X(inner[j], y0), X(outer[j], y0), X(outer[i], y0)], [(u0, -h), (u1, -h), (u1, h), (u0, h)], mat, **f)
        b.poly([X(outer[i], y1), X(outer[j], y1), X(inner[j], y1), X(inner[i], y1)], [(u0, h), (u1, h), (u1, -h), (u0, -h)], mat, **f)
        along = u1
    g = b.geometry(look)
    if teeth:
        pitch, length, height = teeth; parts = [g]; run = 0.0; nxt = phase % pitch
        for i in range(n):
            j = (i + 1) % n; seg = outer[j] - outer[i]; L = float(np.linalg.norm(seg))
            while nxt + length <= run + L:
                f0 = (nxt - run) / L; f1 = (nxt + length - run) / L
                p0, p1 = outer[i] + seg * f0, outer[i] + seg * f1
                q = N[i] * 0.5 + N[j] * 0.5; q /= np.linalg.norm(q) + 1e-12
                d = 0.02 * (y1 - y0)
                quad = [p0 - q * 0.2, p1 - q * 0.2, p0 + q * height, p1 + q * height]   # sunk 0.2 into the band
                parts.append(convex([X(c, y) for c in quad for y in (y0 + d, y1 - d)], mat, look, **kw))
                nxt += pitch
            run += L
        g = Geometry.join(parts)
    return g


# ---------------------------------------------------------------- hard surface (isokit's rules for UVs)
def quad(p0, u, v, mat, uv_scale=1.0, **kw):
    p0, u, v = (np.asarray(a, float) for a in (p0, u, v))
    lu, lv = np.linalg.norm(u), np.linalg.norm(v)
    pts = [p0, p0 + u, p0 + u + v, p0 + v]
    uvs = np.array([(0, lv), (lu, lv), (lu, 0), (0, 0)]) * uv_scale
    return Build().poly(pts, uvs, mat, **_flags(kw)).geometry()


def polygon(pts, mat, **kw):
    pts = np.asarray(pts, float)
    n = np.cross(pts[1] - pts[0], pts[2] - pts[0]); n /= np.linalg.norm(n) + 1e-9
    e1 = pts[1] - pts[0]; e1 /= np.linalg.norm(e1) + 1e-9; e2 = np.cross(n, e1)
    uvs = [((p - pts[0]) @ e1, (p - pts[0]) @ e2) for p in pts]
    return Build().poly(pts, uvs, mat, **_flags(kw)).geometry()


def box(w, d, h, mat, top=None, **kw):
    """Box from the origin to (w, d, h). top: a different material for the lid."""
    return Geometry.join([
        quad((0, d, 0), (w, 0, 0), (0, 0, h), mat, **kw), quad((w, d, 0), (0, -d, 0), (0, 0, h), mat, **kw),
        quad((w, 0, 0), (-w, 0, 0), (0, 0, h), mat, **kw), quad((0, 0, 0), (0, d, 0), (0, 0, h), mat, **kw),
        quad((0, 0, h), (w, 0, 0), (0, d, 0), top or mat, **kw), quad((0, d, 0), (w, 0, 0), (0, -d, 0), mat, **kw)])


def block(x0, x1, y0, y1, z0, z1, mat, **kw):
    """Box by its extents."""
    return box(x1 - x0, y1 - y0, z1 - z0, mat, **kw).move(x0, y0, z0)


def wedge(w, d, h, mat, **kw):
    """Slope rising from y=d (low) to y=0 (high), length along x."""
    return Geometry.join([
        polygon([(0, 0, 0), (0, d, 0), (0, 0, h)], mat, **kw), polygon([(w, 0, 0), (w, 0, h), (w, d, 0)], mat, **kw),
        quad((0, d, 0), (w, 0, 0), (0, -d, h), mat, **kw), quad((w, 0, 0), (-w, 0, 0), (0, 0, h), mat, **kw),
        quad((0, d, 0), (w, 0, 0), (0, -d, 0), mat, **kw)])


def extrude(profile, length, mat, **kw):
    """Closed (y, z) profile extruded along +x. List the points clockwise as drawn with y to the right and z up
    (e.g. top-left, top-right, bottom-right, bottom-left); counter-clockwise turns every face inward, so tops take
    underside light and draw dark. gable() passes its profiles this way."""
    b = Build(); n = len(profile); f = _flags(kw)
    for i in range(n):
        (y0, z0), (y1, z1) = profile[i], profile[(i + 1) % n]; L = math.hypot(y1 - y0, z1 - z0)
        b.poly([(0, y0, z0), (length, y0, z0), (length, y1, z1), (0, y1, z1)], [(0, 0), (length, 0), (length, L), (0, L)], mat, **f)
    b.poly([(0, y, z) for y, z in profile][::-1], [(y, z) for y, z in profile][::-1], mat, **f)
    b.poly([(length, y, z) for y, z in profile], [(y, z) for y, z in profile], mat, **f)
    return b.geometry()


def gable(w, d, rise, mat, overhang=8, thick=6, cap=None, **kw):
    """Pitched roof over w x d, ridge along x at y = d/2, eaves at z = 0."""
    o = overhang; slope = rise / (d / 2); ez = -o * slope
    front = [(d / 2, rise), (d / 2, rise - thick), (d + o, ez - thick), (d + o, ez)]
    back = [(d - y, z) for y, z in front]
    g = extrude(front[::-1], w + 2 * o, mat, **kw).move(-o, 0, 0) + extrude(back, w + 2 * o, mat, **kw).move(-o, 0, 0)
    if cap: g = g + box(w + 2 * o, 10, 5, cap).move(-o, d / 2 - 5, rise - 2)
    return g


def prism(r, h, mat, n=12, top=None, **kw):
    b = Build(); f = _flags(kw)
    ang = [2 * math.pi * i / n + math.pi / n for i in range(n)]
    ring = [(r * math.cos(a), r * math.sin(a)) for a in ang]; circ = 2 * math.pi * r
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]; u0, u1 = circ * i / n, circ * (i + 1) / n
        b.poly([(x0, y0, 0), (x1, y1, 0), (x1, y1, h), (x0, y0, h)], [(u0, h), (u1, h), (u1, 0), (u0, 0)], mat, **f)
    b.poly([(x, y, h) for x, y in ring], ring, top or mat, **f)
    b.poly([(x, y, 0) for x, y in ring][::-1], ring[::-1], mat, **f)
    return b.geometry()


def lathe(profile, mat, n=16, **kw):
    """Revolve a (r, z) profile, bottom to top, round z. Flat faces (towers, tanks, domes on buildings)."""
    b = Build(); f = _flags(kw)
    ang = [2 * math.pi * i / n + math.pi / n for i in range(n)]
    for (r0, z0), (r1, z1) in zip(profile[:-1], profile[1:]):
        for i in range(n):
            a0, a1 = ang[i], ang[(i + 1) % n]
            p = [(r0 * math.cos(a0), r0 * math.sin(a0), z0), (r0 * math.cos(a1), r0 * math.sin(a1), z0),
                 (r1 * math.cos(a1), r1 * math.sin(a1), z1), (r1 * math.cos(a0), r1 * math.sin(a0), z1)]
            if r0 < 1e-6: p = [p[0], p[2], p[3]]
            elif r1 < 1e-6: p = [p[0], p[1], p[2]]
            u0, u1 = 2 * math.pi * max(r0, r1) * i / n, 2 * math.pi * max(r0, r1) * (i + 1) / n
            b.poly(p, [(u0, -z0), (u1, -z0), (u1, -z1), (u0, -z1)][:len(p)], mat, **f)
    if profile[0][0] > 1e-6:
        r, z = profile[0]; b.poly([(r * math.cos(a), r * math.sin(a), z) for a in ang][::-1], [(math.cos(a) * 10, math.sin(a) * 10) for a in ang][::-1], mat, **f)
    if profile[-1][0] > 1e-6:
        r, z = profile[-1]; b.poly([(r * math.cos(a), r * math.sin(a), z) for a in ang], [(math.cos(a) * 10, math.sin(a) * 10) for a in ang], mat, **f)
    return b.geometry()


def dome(r, mat, n=16, rings=5, base=0.0, **kw):
    prof = [(r * math.cos(a), base + r * math.sin(a)) for a in np.linspace(0, math.pi / 2, rings + 1)]
    prof[-1] = (0.0, base + r)
    return lathe(prof, mat, n, **kw)


def pyramid(w, d, h, mat, **kw):
    """Four slopes over w x d meeting at (w/2, d/2, h): hipped roofs, spire caps. The slopes face up and out (the same
    faces as convex() of its five points). Before 2026-11-17 they faced down and in, so they took underside light and
    drew nearly black; see CHANGELOG.md."""
    a = (w / 2, d / 2, h)
    return Geometry.join([polygon([a, (w, d, 0), (0, d, 0)], mat, **kw), polygon([a, (w, 0, 0), (w, d, 0)], mat, **kw),
                          polygon([a, (0, 0, 0), (w, 0, 0)], mat, **kw), polygon([a, (0, d, 0), (0, 0, 0)], mat, **kw)])


def strut(p0, p1, t, mat, **kw):
    """Square bar from p0 to p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d)
    if L < 1e-6: return Geometry()
    kw.setdefault('wear', False)
    g = box(L, t, t, mat, **kw).move(0, -t / 2, -t / 2)
    dz = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))); az = math.degrees(math.atan2(d[1], d[0]))
    return g.ry(-dz).rz(az).move(*p0)


def lattice(wb, wt, h, levels, mat, t=5, **kw):
    """Tapering lattice tower, square base wb, top wt, X-braced every level."""
    cb = np.array([(-wb / 2, -wb / 2), (wb / 2, -wb / 2), (wb / 2, wb / 2), (-wb / 2, wb / 2)])
    ct = cb * (wt / wb)
    out = [strut((*cb[i], 0), (*ct[i], h), t, mat, **kw) for i in range(4)]
    for lv in range(levels):
        z0, z1 = h * lv / levels, h * (lv + 1) / levels; f0, f1 = lv / levels, (lv + 1) / levels
        for i in range(4):
            j = (i + 1) % 4
            a0 = cb[i] * (1 - f0) + ct[i] * f0; b0 = cb[j] * (1 - f0) + ct[j] * f0
            a1 = cb[i] * (1 - f1) + ct[i] * f1; b1 = cb[j] * (1 - f1) + ct[j] * f1
            out += [strut((*a0, z0), (*b1, z1), t * .7, mat, **kw), strut((*b0, z0), (*a1, z1), t * .7, mat, **kw),
                    strut((*a1, z1), (*b1, z1), t * .8, mat, **kw)]
    return Geometry.join(out)


def plane(w, h, mat, **kw):
    """Two-sided vertical plane in x-z, for see-through textures (wire, grilles, fences)."""
    kw.setdefault('wear', False)
    return quad((0, 0, 0), (w, 0, 0), (0, 0, h), mat, **kw) + quad((w, 0, 0), (-w, 0, 0), (0, 0, h), mat, **kw)


# ---------------------------------------------------------------- rounded (unitkit's rules, smooth look)
def blob_lathe(profile, mat, seg=12, caps=True, **kw):
    """Revolve (r, z) points round z with smooth normals."""
    pr = np.array(profile, float)
    if pr[-1, 1] < pr[0, 1]: pr = pr[::-1]
    k = len(pr)
    tang = np.array([pr[min(i + 1, k - 1)] - pr[max(i - 1, 0)] for i in range(k)])
    nr, nz = tang[:, 1], -tang[:, 0]
    ln = np.maximum(np.hypot(nr, nz), 1e-9); nr, nz = nr / ln, nz / ln
    ang = np.linspace(0, 2 * math.pi, seg + 1); c, s_ = np.cos(ang), np.sin(ang)
    pos = np.stack([pr[:, 0:1] * c, pr[:, 0:1] * s_, np.repeat(pr[:, 1:2], seg + 1, 1)], -1)
    nrm = np.stack([nr[:, None] * c, nr[:, None] * s_, np.repeat(nz[:, None], seg + 1, 1)], -1)
    rm = pr[:, 0].max()
    uv = np.stack([np.repeat((ang * rm)[None], k, 0), np.repeat(pr[:, 1:2], seg + 1, 1)], -1)
    P, N, UV = [], [], []
    for i in range(k - 1):
        for j in range(seg):
            q = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            for tri in ((0, 1, 2), (0, 2, 3)):
                P.append([pos[q[t]] for t in tri]); N.append([nrm[q[t]] for t in tri]); UV.append([uv[q[t]] for t in tri])
    if caps:
        for i, nzc in ((0, -1.0), (k - 1, 1.0)):
            if pr[i, 0] > 1e-6:
                cen = np.array([0, 0, pr[i, 1]]); n = np.array([0, 0, nzc])
                for j in range(seg):
                    P.append([cen, pos[i, j], pos[i, j + 1]]); N.append([n, n, n]); UV.append([[0, 0], pos[i, j, :2], pos[i, j + 1, :2]])
    return Geometry(P=np.array(P), N=np.array(N), UV=np.array(UV), mat=mat, look=SMOOTH, **_flags(kw))


def sphere(r, mat, seg=10, rings=6, **kw):
    prof = [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, rings + 1)]
    prof[0] = (0.0, -r); prof[-1] = (0.0, r)
    return blob_lathe(prof, mat, seg, caps=False, **kw)


def ellipsoid(rx, ry, rz, mat, at=(0, 0, 0), seg=10, rings=6, **kw):
    return sphere(1.0, mat, seg, rings, **kw).scaled(rx, ry, rz).move(*at)


def cyl(p0, p1, r0, mat, r1=None, seg=8, **kw):
    """Round bar from p0 to p1 (smooth)."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0)); r1 = r0 if r1 is None else r1
    g = blob_lathe([(r0, 0), (r1, L)], mat, seg, **kw)
    F = aim(p1, p0, (1, 0, 0)); F[:3, 3] = p0
    return g.at(F)


_BOXQ = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


def from_quads(verts, quads, mat, look=SMOOTH, **kw):
    """Faces given as corner indices into verts, normals pointed away from the centroid (unitkit's rule)."""
    V = np.array(verts, float); cen = V.mean(0)
    P, N, UV = [], [], []
    for q in quads:
        p = V[list(q)]
        n = unit(np.cross(p[1] - p[0], p[2] - p[0]), (0, 0, 1))
        if n @ (p.mean(0) - cen) < 0: n = -n
        ax = [a for a in range(3) if a != int(np.argmax(np.abs(n)))]
        for tri in ((0, 1, 2), (0, 2, 3)) if len(q) == 4 else ((0, 1, 2),):
            P.append(p[list(tri)]); N.append([n, n, n]); UV.append(p[list(tri)][:, ax])
    N = np.array(N)
    return Geometry(P=np.array(P), N=N, FN=N[:, 0], UV=np.array(UV), mat=mat, look=look, **_flags(kw))


def hull8(verts, mat, look=SMOOTH, **kw):
    """Any eight-cornered block (corners ordered x0/x1, y0/y1, z0/z1), faces pointed outward."""
    return from_quads(verts, _BOXQ, mat, look, **kw)


def slab(x0, x1, y0, y1, z0, z1, mat, look=SMOOTH, **kw):
    return hull8([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], mat, look, **kw)


def beam(x0, w0, a0, b0, x1, w1, a1, b1, mat, look=SMOOTH, **kw):
    """Tapered bar along x: half-width w0, z a0..b0 at x0; likewise at x1."""
    return hull8([(x0, -w0, a0), (x0, -w0, b0), (x0, w0, a0), (x0, w0, b0),
                  (x1, -w1, a1), (x1, -w1, b1), (x1, w1, a1), (x1, w1, b1)], mat, look, **kw)


# ---------------------------------------------------------------- paths
def catenary(a, b, sag, n=16):
    """Points of a cable hung from a to b, dipping `sag` units at the middle."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    t = np.linspace(0, 1, n)[:, None]
    return a + (b - a) * t - np.array([0, 0, 1.0]) * (4 * sag * t * (1 - t))


def bezier(pts, n=24):
    """Smooth path through control points (quadratic B-spline style: corners rounded)."""
    P = np.asarray(pts, float)
    if len(P) < 3: return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a = (P[i - 1] + P[i]) / 2 if i > 1 else P[0]; c = (P[i] + P[i + 1]) / 2 if i < len(P) - 2 else P[-1]
        for t in np.linspace(0, 1, max(3, n // (len(P) - 2)))[1:]:
            out.append((1 - t) ** 2 * a + 2 * (1 - t) * t * P[i] + t * t * c)
    return np.array(out)


def _frames(path, up=(0, 0, 1)):
    """Rotation-minimising frames along a path: tangent, normal, binormal per point."""
    P = np.asarray(path, float); n = len(P)
    Tg = np.gradient(P, axis=0); Tg /= np.maximum(np.linalg.norm(Tg, axis=1, keepdims=True), 1e-9)
    u = np.asarray(up, float)
    N0 = u - (u @ Tg[0]) * Tg[0]
    if np.linalg.norm(N0) < 1e-6: N0 = np.array([1.0, 0, 0]) - Tg[0, 0] * Tg[0]
    Ns = [unit(N0)]
    for i in range(1, n):
        v = Ns[-1] - (Ns[-1] @ Tg[i]) * Tg[i]
        Ns.append(unit(v, Ns[-1]))
    Ns = np.array(Ns); Bs = np.cross(Tg, Ns)
    return Tg, Ns, Bs


def sweep(path, profile, mat, closed_profile=True, caps=True, look=FLAT, **kw):
    """Carry a 2D profile along a 3D path. profile: list of (a, b) offsets along the path's normal (up-ish) and
    binormal, or a number for a round section of that radius. Pipes, hoses, cables, rails, trench walls."""
    P = np.asarray(path, float)
    if np.isscalar(profile):
        r = float(profile); k = 8 if r > 3 else 6
        profile = [(r * math.cos(2 * math.pi * i / k), r * math.sin(2 * math.pi * i / k)) for i in range(k)]
    pr = np.asarray(profile, float); m = len(pr)
    Tg, Ns, Bs = _frames(P)
    ring = P[:, None, :] + pr[None, :, 0:1] * Ns[:, None, :] + pr[None, :, 1:2] * Bs[:, None, :]
    radial = pr[None, :, 0:1] * Ns[:, None, :] + pr[None, :, 1:2] * Bs[:, None, :]
    radial /= np.maximum(np.linalg.norm(radial, axis=-1, keepdims=True), 1e-9)
    along = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    per = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.vstack([pr, pr[:1]]), axis=0), axis=1))])
    b = Build(); f = _flags(kw)
    segs = m if closed_profile else m - 1
    for i in range(len(P) - 1):
        for j in range(segs):
            j1 = (j + 1) % m
            pts = [ring[i, j], ring[i + 1, j], ring[i + 1, j1], ring[i, j1]]
            uvs = [(along[i], per[j]), (along[i + 1], per[j]), (along[i + 1], per[j + 1]), (along[i], per[j + 1])]
            nn = [radial[i, j], radial[i + 1, j], radial[i + 1, j1], radial[i, j1]]
            b.poly(pts, uvs, mat, normals=nn, **f)
    if caps and closed_profile:
        for i, sgn in ((0, -1), (len(P) - 1, 1)):
            pts = ring[i] if sgn > 0 else ring[i][::-1]
            nrm = np.repeat((Tg[i] * sgn)[None], m, 0)
            b.poly(pts, pr if sgn > 0 else pr[::-1], mat, normals=nrm, **f)
    g = b.geometry(look)
    # faces wound the wrong way for this profile direction: turn them so their normals face outward
    flip = np.einsum('ij,ij->i', g.FN, g.N.mean(1)) < 0
    if flip.any():
        g.P[flip] = g.P[flip][:, ::-1]; g.N[flip] = g.N[flip][:, ::-1]; g.UV[flip] = g.UV[flip][:, ::-1]; g.FN[flip] *= -1
    return g


def ribbon(path, width, mat, lift=0.6, **kw):
    """A flat strip on the ground along a path (roads, tracks, ditches seen from above)."""
    P = np.asarray(path, float).copy(); P[:, 2] = lift
    Tg = np.gradient(P[:, :2], axis=0); Tg /= np.maximum(np.linalg.norm(Tg, axis=1, keepdims=True), 1e-9)
    side = np.stack([-Tg[:, 1], Tg[:, 0], np.zeros(len(P))], 1) * (width / 2)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    b = Build(); f = _flags(kw); f.setdefault('wear', False)
    for i in range(len(P) - 1):
        a0, a1, b1, b0 = P[i] - side[i], P[i + 1] - side[i + 1], P[i + 1] + side[i + 1], P[i] + side[i]
        pts = [a0, a1, b1, b0]
        if np.cross(a1 - a0, b0 - a0)[2] < 0: pts = pts[::-1]
        b.poly(pts, [(L[i], 0), (L[i + 1], 0), (L[i + 1], width), (L[i], width)][::(1 if pts[0] is a0 else -1)], mat, **f)
    return b.geometry()


# ---------------------------------------------------------------- terrain and nature
def _noise2(seed):
    rng = np.random.default_rng(seed)
    g = rng.normal(size=(64, 64))
    def f(x, y, period=1.0):
        x = np.asarray(x, float) / period; y = np.asarray(y, float) / period
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
        fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        a = g[y0 % 64, x0 % 64]; b = g[y0 % 64, (x0 + 1) % 64]; c = g[(y0 + 1) % 64, x0 % 64]; d = g[(y0 + 1) % 64, (x0 + 1) % 64]
        return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy
    return f


def heightfield(fn, w, d, cell, mats, steep=0.9, high=None, **kw):
    """Terrain piece: z = fn(x, y) over w x d, one quad per cell (split along its better diagonal).
    mats: {'ground': .., 'steep': .., 'high': ..}; a face uses 'steep' when its slope's rise/run passes `steep`,
    'high' above height `high`. Cliffs, craters, berms, spoil heaps."""
    nx, ny = int(round(w / cell)), int(round(d / cell))
    xs = np.linspace(0, w, nx + 1); ys = np.linspace(0, d, ny + 1)
    X, Y = np.meshgrid(xs, ys, indexing='ij'); Z = np.vectorize(fn)(X, Y) if not callable(getattr(fn, '__array__', None)) else fn(X, Y)
    Z = np.asarray(Z, float)
    b = Build(); f = _flags(kw)
    for i in range(nx):
        for j in range(ny):
            q = [(X[i, j], Y[i, j], Z[i, j]), (X[i + 1, j], Y[i + 1, j], Z[i + 1, j]),
                 (X[i + 1, j + 1], Y[i + 1, j + 1], Z[i + 1, j + 1]), (X[i, j + 1], Y[i, j + 1], Z[i, j + 1])]
            tris = ([q[0], q[1], q[2]], [q[0], q[2], q[3]]) if abs(Z[i, j] - Z[i + 1, j + 1]) <= abs(Z[i + 1, j] - Z[i, j + 1]) \
                else ([q[0], q[1], q[3]], [q[1], q[2], q[3]])
            for t in tris:
                t = np.array(t); n = np.cross(t[1] - t[0], t[2] - t[0]); n = n / (np.linalg.norm(n) + 1e-9)
                slope = math.hypot(n[0], n[1]) / max(abs(n[2]), 1e-6)
                m = mats.get('steep', mats['ground']) if slope > steep else mats['ground']
                if high is not None and t[:, 2].mean() > high and slope <= steep: m = mats.get('high', m)
                b.poly(t, t[:, :2], m, **f)
    return b.geometry()


def crater(r, depth, rim=0.25, seed=0):
    """Height function for a shell crater: a bowl with a raised, broken lip."""
    nz = _noise2(seed)
    def fn(x, y):
        d = math.hypot(x, y) / r
        lip = rim * depth * math.exp(-((d - 1.0) / 0.22) ** 2) * (1 + .5 * float(nz(x, y, r * .35)))
        return -depth * max(0.0, 1 - d * d) ** 1.5 + lip
    return fn


def rock(size, mat, seed=0, detail=2, flatten=0.62, **kw):
    """A faceted boulder: an icosphere pushed in and out by noise, squashed, sitting on the ground."""
    t = (1 + 5 ** .5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [unit(v) for v in V]
    for _ in range(detail):
        cache = {}; nf = []
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache: cache[k] = len(V); V.append(unit((V[a] + V[b]) / 2))
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a); nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    rng = np.random.default_rng(seed); V = np.array(V)
    dirs = rng.normal(size=(5, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    bump = 1 + 0.18 * np.sin(V @ dirs.T * 3.1 + rng.random(5) * 6).sum(1) / 2.2
    cut = rng.normal(size=(3, 3)); cut /= np.linalg.norm(cut, axis=1, keepdims=True)
    for c in cut:                                       # a few flat fracture planes
        V = np.where(((V @ c) > .62)[:, None], V - ((V @ c) - .62)[:, None] * c, V)
    V = V * bump[:, None] * np.array([1.0, 0.85 + 0.3 * rng.random(), flatten]) * size / 2
    V[:, 2] -= V[:, 2].min() + size * 0.06
    b = Build(); f = _flags(kw)
    for a, b_, c in F:
        p = V[[a, b_, c]]
        if np.cross(p[1] - p[0], p[2] - p[0]) @ (p.mean(0) - V.mean(0)) < 0: p = p[::-1]
        b.poly(p, p[:, :2] * 1.0 + p[:, 2:3] * .5, mat, **f)
    return b.geometry()


def conifer(h, mat_leaf, mat_trunk, seed=0, tiers=4):
    rng = np.random.default_rng(seed); out = [cyl((0, 0, 0), (0, 0, h * .3), h * .035, mat_trunk, h * .025, seg=6)]
    r0 = h * .3
    for i in range(tiers):
        z = h * (.18 + .7 * i / tiers); r = r0 * (1 - i / (tiers + .6)) * (0.9 + .2 * rng.random())
        prof = [(r, z), (r * .55, z + h * .12), (0.0, z + h * (.34 if i == tiers - 1 else .26))]
        out.append(blob_lathe(prof, mat_leaf, seg=9).rz(rng.random() * 40))
    return Geometry.join(out)


def broadleaf(h, mat_leaf, mat_trunk, seed=0, clumps=6):
    rng = np.random.default_rng(seed)
    out = [cyl((0, 0, 0), (0, 0, h * .5), h * .05, mat_trunk, h * .03, seg=6)]
    for i in range(clumps):
        a = rng.random() * 2 * math.pi; d = h * (.08 + .17 * rng.random()); z = h * (.55 + .3 * rng.random())
        r = h * (.17 + .08 * rng.random())
        out.append(ellipsoid(r, r, r * .8, mat_leaf, at=(d * math.cos(a), d * math.sin(a), z), seg=9, rings=5))
    return Geometry.join(out)


def scatter(fn, area=None, path=None, n=10, seed=0, spacing=0.0, scale=(1.0, 1.0), turn=True):
    """Many copies of fn(i, rng) -> Geometry. area: (x0, y0, x1, y1) or a callable(x, y) -> bool over that box
    (give box=...); path: points to scatter along. spacing: minimum distance between copies."""
    rng = np.random.default_rng(seed); out = []; placed = []
    tries = 0
    while len(placed) < n and tries < n * 40:
        tries += 1
        if path is not None:
            P = np.asarray(path, float); k = rng.integers(0, len(P) - 1); t = rng.random()
            x, y = (P[k] * (1 - t) + P[k + 1] * t)[:2]
        else:
            x0, y0, x1, y1 = area; x, y = x0 + rng.random() * (x1 - x0), y0 + rng.random() * (y1 - y0)
        if spacing and any((x - a) ** 2 + (y - b) ** 2 < spacing ** 2 for a, b in placed): continue
        placed.append((x, y))
        g = fn(len(out), rng)
        sc = scale[0] + (scale[1] - scale[0]) * rng.random()
        if sc != 1.0: g = g.scaled(sc)
        if turn: g = g.rz(rng.random() * 360)
        out.append(g.move(x, y, 0))
    return Geometry.join(out)
