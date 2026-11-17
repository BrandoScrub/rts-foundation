"""artkit.core.ink: the one rule for drawing lines on every sprite (formerly inkline.py, copied in isokit and unitkit).

Run it on the supersampled depth buffer, before downsampling. Every edge where a nearer surface stands in front of
something farther (or of nothing) gets a band of ink of the same width, laid on the far side. The width is measured
as true distance, so it does not change with the direction of the edge, how big the depth step is, or what colour
the surface is. Downsampling then gives even anti-aliasing.
"""
import numpy as np
from scipy import ndimage as ndi

INK = np.array([26, 22, 20], np.float32) / 255.0       # the one line colour
INK_COVER = 0.9                                        # how far a line goes towards INK, inside and outside the figure
LINE_GAME_PX = 1.0                                     # line width in game pixels at zoom 1


def radius(game_px_per_raster_px, width=LINE_GAME_PX):
    """Line width in raster pixels. game_px_per_raster_px is how big one raster pixel ends up on the game's canvas."""
    return width / game_px_per_raster_px


def creases(tri, FN, flat, angle, no_seed=None):
    """Seed pixels where two hard-surface (flat-look) faces meet at more than `angle` degrees. tri: triangle index
    per pixel (-1 none), FN: face normals per triangle. The seed is laid on one side of each meeting."""
    h, w = tri.shape
    seed = np.zeros((h, w), bool); c = np.cos(np.radians(angle))
    for a_sl, b_sl in (((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                       ((slice(None, -1), slice(None)), (slice(1, None), slice(None)))):
        a, b = tri[a_sl], tri[b_sl]
        m = (a != b) & (a >= 0) & (b >= 0) & flat[a_sl] & flat[b_sl]
        ys, xs = np.nonzero(m)
        if not len(ys): continue
        ia, ib = a[ys, xs], b[ys, xs]
        sharp = (FN[ia] * FN[ib]).sum(1) < c
        sub = seed[a_sl]; sub[ys[sharp], xs[sharp]] = True
    if no_seed is not None: seed &= ~no_seed
    return seed


def lines_weighted(depth, solid, r, step, no_seed=None, no_rim=None, r_inner=None, crease_seed=None, r_crease=None):
    """lines() with a weight hierarchy: the outline (onto empty space) r wide, lines inside the figure r_inner wide,
    and lines along crease_seed (core.ink.creases) r_crease wide. With r_inner = r and no creases it is lines()."""
    r_inner = r if r_inner is None else r_inner
    h, w = solid.shape
    out = np.zeros((h, w), bool)
    if r_inner == r:
        out |= lines(depth, solid, r, step, no_seed, no_rim)
    else:
        out |= _band(depth, solid, r, step, no_seed, no_rim, outer=True)
        if r_inner > 0: out |= _band(depth, solid, r_inner, step, no_seed, no_rim, outer=False)
    if crease_seed is not None and crease_seed.any() and r_crease:
        d = ndi.distance_transform_edt(~crease_seed)
        out |= (d <= r_crease) & solid
    return out


def _band(depth, solid, r, step, no_seed, no_rim, outer):
    """One part of lines(): the outline only (outer) or the inner lines only, r wide."""
    full = lines(depth, solid, r, step, no_seed, no_rim)
    return full & (~solid if outer else solid)


def lines(depth, solid, r, step, no_seed=None, no_rim=None):
    """Boolean mask of ink pixels. depth: larger is nearer. solid: covered pixels. r: width in raster pixels.
    step: smallest depth difference that counts as an edge.
    no_seed: pixels that cast no line (hair-thin parts that already read as lines; cut ends of tiling pieces).
    no_rim: pixels that may cast a line on other geometry but not onto empty space (flat ground plates)."""
    h, w = solid.shape
    z = np.where(solid, depth, -1e18).astype(np.float64)    # empty space is infinitely far
    seed = np.zeros((h, w), bool)
    seed[:, 1:] |= z[:, 1:] - z[:, :-1] > step
    seed[:, :-1] |= z[:, :-1] - z[:, 1:] > step
    seed[1:, :] |= z[1:, :] - z[:-1, :] > step
    seed[:-1, :] |= z[:-1, :] - z[1:, :] > step
    # the rim of the canvas counts as an edge too
    seed[0, :] |= solid[0, :]; seed[-1, :] |= solid[-1, :]; seed[:, 0] |= solid[:, 0]; seed[:, -1] |= solid[:, -1]
    if no_seed is not None: seed &= ~no_seed
    if not seed.any(): return np.zeros((h, w), bool)
    ys, xs = np.nonzero(seed); m = int(np.ceil(r)) + 2
    y0, y1, x0, x1 = max(ys.min() - m, 0), min(ys.max() + m + 1, h), max(xs.min() - m, 0), min(xs.max() + m + 1, w)
    d, (iy, ix) = ndi.distance_transform_edt(~seed[y0:y1, x0:x1], return_indices=True)
    sub = z[y0:y1, x0:x1]; near = sub[iy, ix]; empty = ~solid[y0:y1, x0:x1]
    band = (d <= r) & (empty | (near - sub > step))
    if no_rim is not None: band &= ~(empty & no_rim[y0:y1, x0:x1][iy, ix])
    out = np.zeros((h, w), bool); out[y0:y1, x0:x1] = band
    return out
