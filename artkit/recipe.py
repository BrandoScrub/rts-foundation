"""artkit.recipe: an asset written as data (JSON or a Python dict) instead of code.

  {
    "name": "Field radio post",
    "footprint": [2, 2],                         # tiles; 160 units each
    "parts": [
      {"name": "hut",  "shape": "box", "args": [180, 140, 100], "mat": "planks@util", "at": [40, 60, 0]},
      {"name": "roof", "shape": "gable", "args": [180, 140, 40], "mat": "corrugated", "at": [40, 60, 100]},
      {"use": "antenna", "args": {"h": 150}, "at": [260, 80, 0]},
      {"use": "sandbags", "at": [20, 20, 0], "repeat": {"count": 2, "step": [0, 200, 0]}},
      {"shape": "sweep", "args": {"path": [[0,0,0],[50,50,20]], "profile": 3}, "mat": "tar"},
      {"name": "dish", "shape": "dome", "args": [24], "mat": "steel", "at": [260, 80, 150], "turn": 30, "tilt": 70}
    ],
    "pivots": {"dish": {"at": [260, 80, 150], "parts": ["dish"]}},   # parts that turn on their own (turrets)
    "states": ["build", "damaged", "ruined"]                         # stages made automatically
  }

Part fields: shape (any function in artkit.shapes) or use (any prop in artkit.library), args (list or dict), mat,
at [x y z], turn (degrees about z), tilt (degrees about y), roll (about x), scale, name, glow, smooth,
repeat {count, step [dx dy dz], turn, around [x y]} (turn copies round `around`, default the part's own spot). A recipe may also be a Python function returning a Geometry.
"""
import json
import math
import numpy as np

from .core.geom import Geometry, T, RX, RY, RZ, S
from . import shapes as sh
from . import library as lib

TILE = 160.0


def _call(fn, args, mat):
    if isinstance(args, dict):
        a = dict(args)
        if mat is not None and 'mat' not in a and 'mat' in fn.__code__.co_varnames: a['mat'] = mat
        return fn(**a)
    args = list(args or [])
    if mat is not None and 'mat' in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
        names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
        if len(args) < names.index('mat') + 1:
            return fn(*args, mat=mat)
    return fn(*args)


def part(p):
    if 'shape' in p:
        fn = getattr(sh, p['shape'])
    elif 'use' in p:
        fn = lib.REGISTRY[p['use']]
    else:
        raise ValueError(f'part needs "shape" or "use": {p}')
    g = _call(fn, p.get('args', []), p.get('mat'))
    if p.get('smooth'): g = g.smooth()
    if p.get('glow'): g = g.glow()
    if 'scale' in p:
        s = p['scale']; g = g.scaled(*(s if isinstance(s, (list, tuple)) else [s]))
    M = T(*p.get('at', (0, 0, 0))) @ RZ(p.get('turn', 0)) @ RY(-p.get('tilt', 0)) @ RX(p.get('roll', 0))
    g = g.at(M)
    rep = p.get('repeat')
    if rep:
        out = []
        for i in range(rep.get('count', 1)):
            st = np.asarray(rep.get('step', (0, 0, 0)), float) * i
            piv = list(rep['around']) + [0] if 'around' in rep and len(rep['around']) == 2 else rep.get('around', p.get('at', (0, 0, 0)))
            gi = g.about(piv, RZ(rep.get('turn', 0) * i)) if rep.get('turn') else g
            out.append(gi.move(*st))
        g = Geometry.join(out)
    return g


class Asset:
    """A built recipe: the geometry with each named part's triangles tagged, plus footprint, pivots and states."""

    def __init__(s, spec, geom=None, names=None):
        if callable(spec): spec = {'name': spec.__name__, 'build': spec}
        s.spec = spec; s.name = spec.get('name', 'asset')
        fp = spec.get('footprint', [1, 1]); s.footprint = (fp[0] * TILE, fp[1] * TILE)
        s.names = dict(names or {}); s.assembly = None
        if geom is not None:
            s.geom = geom
        elif 'build' in spec:
            s.geom = spec['build']()
        else:
            parts = []
            for i, p in enumerate(spec.get('parts', [])):
                nm = p.get('name', f'part{i}')
                s.names.setdefault(nm, len(s.names) + 1)
                parts.append(part(p).as_part(s.names[nm]))
            s.geom = Geometry.join(parts)
        s.pivots = spec.get('pivots', {})
        s.anchors = {k: tuple(v) for k, v in spec.get('anchors', {}).items()}     # named points in units: door, muzzle, cable
        s.normals = {k: tuple(v) for k, v in spec.get('anchor_normals', {}).items()}   # optional: which way an anchor faces (x, y)
        s.turn = spec.get('turn', 0)                                              # quarter turns from the authored facing

    def facing(s, q):
        """The same asset turned q quarter turns (counter-clockwise seen from above) on its footprint. The light does
        not turn: this is the building seen from another side, lit from the upper left like everything else. The
        footprint swaps for odd q; pivots and anchors turn with it. Every stage and turning part works on the result."""
        q %= 4
        if q == 0: return s
        W, D = s.footprint; M = RZ(90.0 * q)
        c = np.array([(0, 0, 0, 1), (W, 0, 0, 1), (0, D, 0, 1), (W, D, 0, 1)], float) @ M.T
        M = T(-c[:, 0].min(), -c[:, 1].min(), 0) @ M
        pt = lambda v: tuple(float(x) for x in (M @ np.array([v[0], v[1], v[2] if len(v) > 2 else 0.0, 1.0]))[:3])
        spec = dict(s.spec); fp = spec.get('footprint', [1, 1])
        spec['footprint'] = [fp[1], fp[0]] if q % 2 else list(fp)
        spec['pivots'] = {k: dict(v, at=list(pt(v['at'])), rest=v.get('rest', 0.0) + 90.0 * q) for k, v in s.pivots.items()}
        spec['anchors'] = {k: pt(v) for k, v in s.anchors.items()}; spec['turn'] = (s.turn + q) % 4
        R = RZ(90.0 * q)[:2, :2]
        spec['anchor_normals'] = {k: [round(float(c), 9) + 0.0 for c in R @ np.asarray(v, float)] for k, v in s.normals.items()}
        a = Asset(spec, geom=s.geom.at(M), names=s.names); a.assembly = s.assembly
        return a

    def anchor_tiles(s):
        """Anchors for a game: tile coordinates on the footprint, and which edge each faces: the way its normal points
        when it has one (a door on a wall), else the footprint edge it is nearest ('+y' and '+x' face the camera,
        '-y' and '-x' are behind)."""
        W, D = s.footprint; out = {}
        for k, (x, y, z) in s.anchors.items():
            if k in s.normals:
                nx, ny = s.normals[k]
                edge = ('+x' if nx > 0 else '-x') if abs(nx) > abs(ny) else ('+y' if ny > 0 else '-y')
            else:
                d = {'+y': D - y, '+x': W - x, '-y': y, '-x': x}; edge = min(d, key=d.get)
            out[k] = {'at': [round(x / TILE, 3), round(y / TILE, 3), round(z / TILE, 3)], 'edge': edge}
        return out

    @staticmethod
    def load(path):
        return Asset(json.load(open(path)))

    def ids(s, names):
        return [s.names[n] for n in names if n in s.names]

    def base(s):
        """Everything except the turning parts."""
        g = s.geom
        for pv in s.pivots.values():
            for i in s.ids(pv['parts']): g = g.without(i)
        return g

    def turning(s, name, heading):
        """One pivot's parts turned to a heading (degrees, 0 = +x), round its pivot point."""
        pv = s.pivots[name]
        g = Geometry.join([s.geom.where(i) for i in s.ids(pv['parts'])])
        rest = pv.get('rest', 0.0)
        return g.about(pv['at'], RZ(heading - rest))

    # ---- automatic stages
    def construction(s, f, scaffold_mat='planks'):
        """Under construction, f of the way up (0..1): built up to that height, scaffolding round it."""
        g = s.geom
        lo, hi = g.bounds(); H = max(hi[2], 1.0)
        built = Asset._cut(g, np.full(len(g), f * H), H)
        w, d = s.footprint
        return built + lib.scaffold(w - 24, d - 24, max(40.0, f * H + 20), scaffold_mat).move(12, 12, 0)

    def damaged(s, level=0.5, seed=3, rubble_mat='concrete'):
        """Broken: everything above a ragged line at `level` of the height is gone, with rubble on the ground."""
        g = s.geom; rng = np.random.default_rng(seed)
        lo, hi = g.bounds(); H = max(hi[2], 1.0)
        c = g.P.mean(1)
        a = rng.normal(size=2); a /= np.linalg.norm(a)
        rag = np.sin(c[:, 0] * .05 + rng.random() * 6) * .08 + np.sin(c[:, 1] * .07 + rng.random() * 6) * .06
        lim = H * (level + rag + .12 * ((c[:, :2] - (lo[:2] + hi[:2]) / 2) @ a) / max(np.ptp(c[:, :2]), 1.0))
        w, d = s.footprint
        rub = lib.rubble(r=min(w, d) * .38, n=int(8 + 14 * (1 - level)), mat=rubble_mat, seed=seed).move(w / 2, d / 2, 0)
        return Asset._cut(g, lim, H) + rub

    @staticmethod
    def _cut(g, lim, H):
        """Clip every triangle at its height limit (clean edges, no zigzags). Small parts are kept or lost whole,
        ground plates always stay, and parts that were cut open show a dark inside."""
        lim = np.asarray(lim, float).copy()
        lim[g.P[:, :, 2].max(1) < 6] = np.inf
        for pid in np.unique(g.part):
            m = g.part == pid; z = g.P[m][:, :, 2]
            if z.max() - z.min() < 0.3 * H:
                lim[m] = np.inf if (g.P[m].mean(1)[:, 2] <= lim[m]).mean() >= .5 else -np.inf
        rows = {k: [] for k in ('P', 'N', 'UV', 'src')}
        for i in range(len(g)):
            z = g.P[i, :, 2]; L = lim[i]
            if (z <= L).all():
                rows['P'].append(g.P[i]); rows['N'].append(g.N[i]); rows['UV'].append(g.UV[i]); rows['src'].append(i); continue
            if (z > L).all(): continue
            poly = []
            for j in range(3):
                k = (j + 1) % 3; a_in, b_in = z[j] <= L, z[k] <= L
                if a_in: poly.append((g.P[i, j], g.N[i, j], g.UV[i, j]))
                if a_in != b_in:
                    t = (L - z[j]) / (z[k] - z[j])
                    poly.append((g.P[i, j] + t * (g.P[i, k] - g.P[i, j]), g.N[i, j] + t * (g.N[i, k] - g.N[i, j]),
                                 g.UV[i, j] + t * (g.UV[i, k] - g.UV[i, j])))
            for q in range(1, len(poly) - 1):
                tri = [poly[0], poly[q], poly[q + 1]]
                rows['P'].append([v[0] for v in tri]); rows['N'].append([v[1] for v in tri]); rows['UV'].append([v[2] for v in tri])
                rows['src'].append(i)
        src = np.array(rows['src'], int)
        if not len(src): return Geometry()
        out = g.take(src)
        out.P = np.array(rows['P'], float); out.N = np.array(rows['N'], float); out.UV = np.array(rows['UV'], float)
        cut_parts = {int(p) for p in np.unique(g.part) if len(src[np.isin(g.part[src], [p])]) != (g.part == p).sum()
                     or (np.isfinite(lim[g.part == p]) & (g.P[g.part == p][:, :, 2].max(1) > lim[g.part == p])).any()}
        return Asset._open_up(g, out, cut_parts)

    INTERIOR = 0.3      # brightness of the inside of a cut-open part

    @staticmethod
    def _open_up(g, out, parts):
        """Cut-open parts show their insides: faces whose outward side (away from the part's centre) points away
        from the viewer are darkened, so a broken wall reads as a hollow shell."""
        view = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
        shade = out.shade.copy()
        for pid in parts:
            mo = out.part == pid
            if not mo.any(): continue
            cen = g.P[g.part == pid].reshape(-1, 3).mean(0); c = out.P[mo].mean(1); n = out.FN[mo]
            outward = n * np.sign(np.einsum('ij,ij->i', c - cen, n))[:, None]
            sh_ = shade[mo]; sh_[outward @ view < -0.05] = Asset.INTERIOR; shade[mo] = sh_
        out.shade = shade
        return out

    def states(s):
        """name -> Geometry for every stage the recipe asks for."""
        out = {'normal': s.base()}
        want = s.spec.get('states', [])
        mat_s = s.spec.get('scaffold_mat', 'planks'); mat_r = s.spec.get('rubble_mat', 'concrete')
        for st in want:
            if st == 'build':
                for f in (0.33, 0.66):
                    out[f'build{int(f * 100)}'] = Asset._strip(s, s.construction(f, mat_s))
            elif st == 'damaged':
                out['damaged'] = Asset._strip(s, s.damaged(0.62, rubble_mat=mat_r))
            elif st == 'ruined':
                out['ruined'] = Asset._strip(s, s.damaged(0.28, seed=7, rubble_mat=mat_r))
        return out

    def _strip(s, g):
        for pv in s.pivots.values():
            for i in s.ids(pv['parts']): g = g.without(i)
        return g
