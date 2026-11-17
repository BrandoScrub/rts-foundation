"""artkit.clearance: does one part pass through another? (DESIGN_METHOD.md step 3, "Clearance", measured instead of
judged by eye.)

  from artkit import clearance
  bad = clearance.check({'track': g1, 'hull': g2, ...}, solids=['hull', ...], movers=['track', ...], allow={('bracket', 'hull')})
  for a, b, depth, at in bad: print(f'{a} goes {depth:.1f} units into {b} near {at}')

`solids` are convex parts (a hull block, a cover, a turret body): a point of another part strictly inside one of them
by more than `tol` units is a clash. `movers` are the parts tested against them (tracks, wheels, guns, doors at the
ends of their range). `allow` lists pairs that are meant to touch or sit inside each other (a bracket bolted to the
hull, an axle in a wheel). `ground` (default 0): any point of any part lower than ground - tol is a clash with the
ground. Points tested: every corner and the middle of every triangle.
"""
import numpy as np
from scipy.spatial import ConvexHull


def _points(g):
    P = np.asarray(g.P, float)
    return np.concatenate([P.reshape(-1, 3), P.mean(1)])


def depth_into(points, solid):
    """For each point, how far it lies inside the convex hull of `solid` (geometry or points); <= 0 means outside."""
    S = _points(solid) if hasattr(solid, 'P') else np.asarray(solid, float)
    eq = ConvexHull(S).equations                    # n . p + d <= 0 inside
    return -(points @ eq[:, :3].T + eq[:, 3]).max(1)


def check(parts, solids, movers, allow=(), tol=0.5, ground=0.0):
    """[(mover, solid, depth in units, where)] for every clash deeper than tol, worst first; [] when clear."""
    allow = {tuple(sorted(p)) for p in allow}
    out = []
    for m in movers:
        pts = _points(parts[m])
        low = pts[:, 2].min()
        if ground is not None and low < ground - tol:
            out.append((m, 'ground', float(ground - low), tuple(np.round(pts[pts[:, 2].argmin()], 1))))
        for sname in solids:
            if sname == m or tuple(sorted((m, sname))) in allow: continue
            d = depth_into(pts, parts[sname])
            if d.max() > tol:
                out.append((m, sname, float(d.max()), tuple(np.round(pts[d.argmax()], 1))))
    return sorted(out, key=lambda r: -r[2])
