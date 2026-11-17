"""artkit.team: player colours chosen when the game runs, from one export.

A style pack may name the materials that carry a player's colour:
  "team": {"materials": ["banner", "@faction", "hull@home"], "gain": 1.25}
  - "banner"      every material whose base name is banner (banner, banner@home ...)
  - "@faction"    every material tinted with the role faction (anything@faction)
  - "hull@home"   exactly that name
Without the section nothing changes. With it the exporter writes, beside each still, turning strip and unit strip,
a grey mask (white where a team material shows, soft at its edges) and the runtime recolours a copy of the picture
once per player at load time (ArtKit.teams), so drawing a unit in any colour costs nothing extra per frame.

The recolour is the engine's role-tint rule (core.materials.tint), applied to the finished pixel:
  out = mix(rgb, clip(luminance(rgb) * colour * gain), mask)
Light, wear, grain and lines are all in the luminance, so a recoloured unit keeps its shading and outline.
`recolour` is the reference; runtime/artkit.js (ArtKit.recolourPixels) does the same sum.
"""
import numpy as np

LUM = np.array([0.3, 0.59, 0.11], np.float32)
GAIN = 1.25


class Team:
    """Which material names are team-coloured. Call it with a material name."""

    def __init__(s, materials=(), gain=GAIN):
        s.names, s.bases, s.roles = set(), set(), set()
        for p in materials:
            if p.startswith('@'): s.roles.add(p[1:])
            elif '@' in p: s.names.add(p)
            else: s.bases.add(p)
        s.gain = float(gain)
        s._memo = {}

    @staticmethod
    def from_pack(cfg):
        """The pack's "team" section -> Team, or None when it has none (or names no materials)."""
        if not cfg or not cfg.get('materials'): return None
        return Team(cfg['materials'], cfg.get('gain', GAIN))

    def __call__(s, name):
        r = s._memo.get(name)
        if r is None:
            base, _, role = name.partition('@')
            r = s._memo[name] = name in s.names or base in s.bases or (bool(role) and role in s.roles)
        return r


def mask(B, ss):
    """Grey mask (uint8, output size) from render buffers recorded with a team: the share of each output pixel's
    covered samples that show a team material. Zero where nothing is."""
    H, W = B.alpha.shape
    solid = B.alpha > 0
    t = (B.team & solid).reshape(H // ss, ss, W // ss, ss).mean((1, 3))
    a = solid.reshape(H // ss, ss, W // ss, ss).mean((1, 3))
    m = np.where(a > 0, t / np.maximum(a, 1e-6), 0)
    return (np.clip(m, 0, 1) * 255 + 0.5).astype(np.uint8)


def recolour(rgba, m, colour, gain=GAIN):
    """Reference recolour: uint8 RGBA (H, W, 4), uint8 mask (H, W), colour [r, g, b] 0..255 -> uint8 RGBA."""
    rgb = rgba[..., :3].astype(np.float32) / 255
    w = (m.astype(np.float32) / 255)[..., None]
    lum = rgb @ LUM
    t = np.clip(lum[..., None] * (np.asarray(colour, np.float32) / 255)[None, None, :] * gain, 0, 1)
    out = rgba.copy()
    out[..., :3] = (np.clip(rgb + (t - rgb) * w, 0, 1) * 255 + 0.5).astype(np.uint8)
    return out
