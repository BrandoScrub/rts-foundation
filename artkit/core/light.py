"""artkit.core.light: the two shading looks, both lit from the upper left.

FLAT  (buildings, props, terrain pieces): one brightness per face from its normal, plus wear near the ground,
      per-pixel grain and screen-space ambient occlusion. Hard-surface and crisp.
SMOOTH (figures, creatures, anything rounded that moves): brightness per corner, interpolated across the triangle.

The two formulas are numerically different because existing art was made with each. A style pack may override
the constants; changing them re-lights everything made with that style.
"""
import numpy as np

# FLAT
def flat_shade(n):
    n = np.asarray(n, float); n = n / (np.linalg.norm(n) + 1e-9)
    return float(min(1.0, 0.60 + 0.40 * max(0.0, n[1]) + 0.36 * max(0.0, n[2]) - 0.10 * max(0.0, -n[1]) - 0.06 * max(0.0, n[0])))

WEAR = 0.28          # how much darker a wall is at its foot
WEAR_FALLOFF = 45.0  # units over which wear fades going up
GRAIN = 0.05         # per output pixel brightness jitter
AO = ((3, 0.5), (8, 0.35), (16, 0.15))   # (radius in units, weight)
AO_DEPTH = 60.0
AO_STRENGTH = 0.45

# SMOOTH
LIGHT = np.array([0.25, 0.70, 0.67]); LIGHT /= np.linalg.norm(LIGHT)
VIEW = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
AMB, DIF, HEMI = 0.50, 0.58, 0.12


def smooth_shade(N):
    """N: (..., 3) unit normals -> brightness."""
    return AMB + DIF * np.clip(N @ LIGHT, 0, 1) + HEMI * N[..., 2]


def _within(v, lo, hi, name):
    if not lo <= v <= hi: raise ValueError(f'{name} must be within {lo}..{hi}')
    return v


class Rules:
    """Optional finishing rules from a style pack's "light" section (none of it is on by default):

        "light": {"relief": {"strength": 0.4, "span": 40, "ref": 0.9},
                  "ao": {"strength": 0.6, "depth": 15, "radii": [[1.5, 0.5], [4, 0.35], [9, 0.15]]},
                  "ink": {"cover": 0.75, "width": 0.8, "inner": 0.5, "step": 4, "crease": 35, "crease_width": 0.4}}

    relief: darken each pixel by how far it lies behind the nearest point of the picture, up to `strength` at `span`
            model units back (depth = toward the viewer in the pack's camera). It gives height to views that look
            straight at the tops of things (a top-down camera), where every upward face would otherwise get the same
            light. ref (0..1, default 1 = the nearest point) measures from that quantile of the picture's depths
            instead, so a few tall thin parts (masts, stacks) do not darken everything else. Emissive pixels are left
            alone.
    ao:     the ambient occlusion constants (AO_STRENGTH, AO_DEPTH, AO radii in model units) for this style.
    ink:    cover: how far lines go toward the ink colour (INK_COVER, 0..1); lower reads softer.
            A line weight hierarchy, each part optional (core.ink.lines_weighted):
            width: the outline's width as a share of one game pixel (default 1).
            inner: lines inside the figure (where a nearer part stands in front of a farther one) as a share of the
                   outline's width (default 1, the same); 0.5 gives a strong silhouette and lighter inner lines.
            step:  smallest depth step, in model units, that gets a line (default: the engine's 12 for hard surfaces,
                   5 for smooth); lower draws lines at small ledges (a ring lip, a plate on a hull).
            crease: an angle in degrees: also draw a line where two hard-surface faces meet at more than this, even
                   with no depth step (a box's own edges). crease_width: its width as a share of the outline's
                   (default: inner, or 0.5). Rounded (smooth) surfaces never get creases.
    Any key left out keeps the engine default, and a pack without "light" is drawn exactly as before."""

    def __init__(s, relief_strength=0.0, relief_span=40.0, ao_strength=None, ao_depth=None, ao_radii=None, ink_cover=None,
                 relief_ref=1.0, ink_width=None, ink_inner=None, ink_step=None, ink_crease=None, ink_crease_width=None):
        s.relief_strength, s.relief_span, s.relief_ref = float(relief_strength), float(relief_span), float(relief_ref)
        s.ao_strength = AO_STRENGTH if ao_strength is None else float(ao_strength)
        s.ao_depth = AO_DEPTH if ao_depth is None else float(ao_depth)
        s.ao_radii = AO if ao_radii is None else tuple((float(r), float(w)) for r, w in ao_radii)
        s.ink_cover = ink_cover
        s.ink_width, s.ink_inner, s.ink_step = ink_width, ink_inner, ink_step
        s.ink_crease, s.ink_crease_width = ink_crease, ink_crease_width

    @property
    def weighted(s):
        """True when any part of the line hierarchy is set (core.ink.lines_weighted is used instead of lines)."""
        return any(v is not None for v in (s.ink_width, s.ink_inner, s.ink_step, s.ink_crease))

    @staticmethod
    def from_pack(cfg):
        """None when the pack gives no "light" section (the engine's own constants apply, unchanged)."""
        if not cfg: return None
        if not isinstance(cfg, dict): raise ValueError(f'light: expected an object, got {cfg!r}')
        unknown = set(cfg) - {'relief', 'ao', 'ink'}
        if unknown: raise ValueError(f'light: unknown keys {sorted(unknown)}')
        rel, ao, ink = cfg.get('relief') or {}, cfg.get('ao') or {}, cfg.get('ink') or {}
        cover = ink.get('cover')
        if cover is not None and not 0 <= float(cover) <= 1: raise ValueError('light.ink.cover must be within 0..1')
        bad = set(ink) - {'cover', 'width', 'inner', 'step', 'crease', 'crease_width'}
        if bad: raise ValueError(f'light.ink: unknown keys {sorted(bad)}')
        num = lambda k, lo, hi: None if ink.get(k) is None else _within(float(ink[k]), lo, hi, 'light.ink.' + k)
        width, inner, step = num('width', 0.1, 4), num('inner', 0, 1), num('step', 0.5, 200)
        crease, cw = num('crease', 5, 175), num('crease_width', 0.05, 1)
        ref = float(rel.get('ref', 1.0))
        if not 0 < ref <= 1: raise ValueError('light.relief.ref must be within (0, 1]')
        return Rules(rel.get('strength', 0.0), rel.get('span', 40.0), ao.get('strength'), ao.get('depth'), ao.get('radii'),
                     None if cover is None else float(cover), ref, width, inner, step, crease, cw)

    def with_(s, **kw):
        """A copy with some values changed (e.g. a wider relief span for terrain than for ships)."""
        r = Rules.__new__(Rules); r.__dict__.update(s.__dict__)
        for k, v in kw.items():
            if not hasattr(r, k): raise AttributeError(k)
            setattr(r, k, v)
        return r
