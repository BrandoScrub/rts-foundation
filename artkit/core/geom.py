"""artkit.core.geom: one geometry type for everything (buildings, props, terrain, figures, machines).

A Geometry is a triangle soup held in arrays, one row per triangle:
  P    (n, 3, 3) corner positions            N   (n, 3, 3) corner normals (smooth look)
  UV   (n, 3, 2) corner texture coordinates  FN  (n, 3)    face normal (flat look, wear)
  mat  (n,) material name, 'tile' or 'tile@role'
  look (n,) FLAT or SMOOTH                   shade (n,) fixed flat brightness, nan = from the normal
  emit (n,) glows: no light, no wear, no line painted over it
  wear (n,) darkens near the ground          bias (n,) depth nudge (decals sit on their wall)
  thin (n,) hair-thin: casts no line         low  (n,) ground plate: no outline against empty ground
  box  (n, 4) uv bounds of the source face, for stretched (decal) materials
  part (n,) integer part id, for picking parts out (states, turning parts)
  face (n,) which source polygon a triangle came from (ground-plate and thin tests are per polygon)
thin and low may be -1 (unknown): the renderer then measures them.

Geometries add with +, and transform with at(4x4) and the short forms below. Nothing is mutated in place.
"""
import math
import numpy as np

FLAT, SMOOTH = 0, 1


def T(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M

def _rot(i, j, a):
    a = math.radians(a); M = np.eye(4); c, s = math.cos(a), math.sin(a)
    M[i, i] = c; M[i, j] = -s; M[j, i] = s; M[j, j] = c; return M

def RX(a): return _rot(1, 2, a)
def RY(a): return _rot(2, 0, a)
def RZ(a): return _rot(0, 1, a)
def R3(yaw, pitch, roll): return RZ(yaw) @ RY(pitch) @ RX(roll)
def S(x, y=None, z=None):
    y = x if y is None else y; z = x if z is None else z
    return np.diag([x, y, z, 1.0])


def xf(M, p):
    return np.asarray(M)[:3, :3] @ np.asarray(p, float) + np.asarray(M)[:3, 3]


def unit(v, alt=(1.0, 0.0, 0.0)):
    n = np.linalg.norm(v)
    return np.asarray(v, float) / n if n > 1e-8 else np.array(alt, float)


def aim(A, B, hint):
    """Frame at A whose -z points at B and whose +x leans toward hint."""
    A = np.asarray(A, float); B = np.asarray(B, float); hint = np.asarray(hint, float)
    z = unit(A - B, (0, 0, 1))
    x = hint - (hint @ z) * z
    if np.linalg.norm(x) < 1e-6:
        x = np.array([0, 1.0, 0]) - z[1] * z
    x = unit(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z; M[:3, 3] = A
    return M


def ik2(A, target, l1, l2, pole):
    """Two-bone IK. Returns (middle joint, reachable end)."""
    A = np.asarray(A, float); d = np.asarray(target, float) - A
    L = np.linalg.norm(d); dirn = unit(d, (0, 0, -1))
    Lc = float(np.clip(L, abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3))
    a = (l1 * l1 - l2 * l2 + Lc * Lc) / (2 * Lc)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = np.asarray(pole, float); p = p - (p @ dirn) * dirn
    p = unit(p, (0, 1, 0))
    return A + dirn * a + p * h, A + dirn * Lc


_FIELDS = ('P', 'N', 'UV', 'FN', 'mat', 'look', 'shade', 'emit', 'wear', 'bias', 'thin', 'low', 'box', 'part', 'face')


class Geometry:
    def __init__(s, **kw):
        n = len(kw['P']) if 'P' in kw else 0
        s.P = np.asarray(kw.get('P', np.zeros((0, 3, 3))), float).reshape(n, 3, 3)
        fn = kw.get('FN')
        if fn is None:
            fn = np.cross(s.P[:, 1] - s.P[:, 0], s.P[:, 2] - s.P[:, 0])
            fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
        s.FN = np.asarray(fn, float).reshape(n, 3)
        N = kw.get('N')
        s.N = np.repeat(s.FN[:, None], 3, 1) if N is None else np.asarray(N, float).reshape(n, 3, 3)
        uv = kw.get('UV')
        s.UV = np.zeros((n, 3, 2)) if uv is None else np.asarray(uv, float).reshape(n, 3, 2)
        def col(k, v, dt):
            x = kw.get(k, v)
            return np.full(n, x, dt) if np.isscalar(x) or x is None else np.asarray(x, dt).reshape(n)
        m = kw.get('mat', '')
        s.mat = np.full(n, m, object) if isinstance(m, str) else np.asarray(m, object).reshape(n)
        s.look = col('look', FLAT, np.int8)
        s.shade = col('shade', np.nan, float)
        s.emit = col('emit', False, bool)
        s.wear = col('wear', True, bool)
        s.bias = col('bias', 0.0, float)
        s.thin = col('thin', -1, np.int8)
        s.low = col('low', -1, np.int8)
        b = kw.get('box')
        s.box = np.zeros((n, 4)) if b is None else np.asarray(b, float).reshape(n, 4)
        s.part = col('part', 0, np.int32)
        f = kw.get('face')
        s.face = np.arange(n, dtype=np.int64) if f is None else np.asarray(f, np.int64).reshape(n)

    def __len__(s): return len(s.P)

    def _new(s, **ch):
        d = {k: getattr(s, k) for k in _FIELDS}; d.update(ch); return Geometry(**d)

    def take(s, idx):
        return Geometry(**{k: getattr(s, k)[idx] for k in _FIELDS})

    def __add__(s, o):
        if o is None or (isinstance(o, int) and o == 0): return s
        if not len(o): return s
        if not len(s): return o
        return Geometry.join([s, o])
    __radd__ = __add__

    @staticmethod
    def join(items):
        items = [g for g in items if g is not None and len(g)]
        if not items: return Geometry()
        d = {k: np.concatenate([getattr(g, k) for g in items]) for k in _FIELDS if k != 'face'}
        faces = []; off = 0                       # polygon ids stay distinct across the pieces
        for g in items:
            faces.append(g.face + off); off += int(g.face.max()) + 1
        d['face'] = np.concatenate(faces)
        return Geometry(**d)

    # ---- transforms
    def at(s, M):
        M = np.asarray(M, float); R = M[:3, :3]
        P = s.P @ R.T + M[:3, 3]
        Ri = np.linalg.inv(R).T
        N = s.N @ Ri.T; N = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-9)
        FN = s.FN @ Ri.T; FN = FN / np.maximum(np.linalg.norm(FN, axis=-1, keepdims=True), 1e-9)
        g = s._new(P=P, N=N, FN=FN)
        if np.linalg.det(R) < 0:      # a mirror turns flat faces inside out: put their corners back in order
            f = g.look == FLAT
            if f.any(): g.P[f] = g.P[f][:, ::-1]; g.N[f] = g.N[f][:, ::-1]; g.UV[f] = g.UV[f][:, ::-1]
        return g

    def move(s, x=0, y=0, z=0): return s.at(T(x, y, z))
    def rx(s, a): return s.at(RX(a))
    def ry(s, a): return s.at(RY(a))
    def rz(s, a): return s.at(RZ(a))
    def scaled(s, x, y=None, z=None): return s.at(S(x, y, z))
    def about(s, pivot, M):
        px, py, pz = pivot
        return s.at(T(px, py, pz) @ M @ T(-px, -py, -pz))
    def mirror_y(s): return s.at(S(1, -1, 1))

    def warp(s, fn, thin_below=4.5):
        """Move every corner by fn(point) -> point (a 3-vector in, a 3-vector out; called once per corner, so
        corners that coincide stay together). Each source polygon gets its face normal again from its first three
        corners, and its hair-thin flag again from its edges (sides shorter than thin_below), as if it had been
        built in the new place. For lumpy rocks, sagging canvas, bent plates."""
        P = np.array([[fn(p) for p in tri] for tri in s.P], float).reshape(len(s), 3, 3)
        g = s._new(P=P)
        if not len(s): return g
        first = np.r_[True, s.face[1:] != s.face[:-1]]          # a polygon's triangles are consecutive (fan order)
        start = np.maximum.accumulate(np.where(first, np.arange(len(s)), 0))
        a, b, c = P[start, 0], P[start, 1], P[start, 2]
        n = np.cross(b - a, c - a); l = np.linalg.norm(n, axis=1, keepdims=True)
        FN = np.where(l > 1e-9, n / np.maximum(l, 1e-300), np.array([0, 0, 1.0]))
        g.FN = FN; g.N = np.where((g.look == FLAT)[:, None, None], np.repeat(FN[:, None], 3, 1), g.N)
        # polygon sides from the fan: v0v1 of the first triangle, v1v2 of every triangle, v2v0 of the last
        last = np.r_[s.face[1:] != s.face[:-1], True]
        e = np.linalg.norm(np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 1], P[:, 0] - P[:, 2]], 1), axis=2)
        side = np.where(np.stack([first, np.ones(len(s), bool), last], 1), e, np.inf).min(1)
        th = np.full(len(s), np.inf)
        np.minimum.at(th, start, side); th = th[start]
        wire = np.array([str(m).split('@')[0] == 'wire' for m in g.mat], bool)
        g.thin = np.where(s.thin >= 0, (th < thin_below) | wire, s.thin).astype(np.int8)   # unknown (-1) stays unknown
        return g

    # ---- attributes
    def set(s, **kw):
        ch = {}
        for k, v in kw.items():
            if k == 'mat':
                ch['mat'] = np.full(len(s), v, object)
            else:
                ch[k] = np.full(len(s), v, getattr(s, k).dtype)
        return s._new(**ch)

    def mat_as(s, name): return s.set(mat=name)
    def smooth(s): return s.set(look=SMOOTH)
    def flat(s): return s.set(look=FLAT)
    def glow(s): return s.set(emit=True)
    def as_part(s, i): return s.set(part=i)
    group = as_part

    def bounds(s):
        if not len(s): return np.zeros(3), np.zeros(3)
        Q = s.P.reshape(-1, 3); return Q.min(0), Q.max(0)

    def where(s, part):
        return s.take(s.part == part)

    def without(s, part):
        return s.take(s.part != part)
