"""artkit.core.materials: what a surface looks like before light.

A Material is a small texture plus how it is laid on a face:
  'tile'     repeats across the face at `tpu` texels per unit, sampled bilinear (walls, roofs, ground)
  'stretch'  stretched once across the face, bilinear (decals: windows, doors, emblems)
  'nearest'  repeats at `tpu` texels per unit, nearest texel (figures)
Textures are float arrays 0..1, RGB or RGBA; RGBA texels under half alpha are holes in the face (wire, blades).

A Materials registry maps names to materials. A name may carry a role, 'brick@home': the tile turned to grey and
tinted with that role colour, which is how buildings show what they do. Style packs fill a registry
(see artkit/style.py); the image model only ever paints the flat tiles.
"""
import numpy as np
from PIL import Image


class Material:
    __slots__ = ('tex', 'mode', 'tpu', 'emissive', 'name')

    def __init__(s, tex, mode='tile', tpu=2.0, emissive=False, name=''):
        s.tex = tex; s.mode = mode; s.tpu = tpu; s.emissive = emissive; s.name = name


def tint(arr, rgb, gain=1.25):
    """Greyscale the tile and colour it with a role colour (the isokit rule)."""
    t = np.array(rgb, np.float32) / 255
    lum = arr[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32)
    out = arr.copy(); out[..., :3] = np.clip(lum[..., None] * t[None, None, :] * gain, 0, 1)
    return out


class Materials:
    """name -> Material. Unknown names are resolved by `resolve` (tiles, roles, decals) and cached."""

    def __init__(s, tiles=None, tile_units=128, tile_scale=None, roles=None, decals=None, fallback=None, tile_px=None):
        s.tiles = tiles or {}              # name -> PIL image or float array (flat seamless tile)
        s.tile_units = tile_units          # model units one tile covers
        s.tile_scale = tile_scale or {}    # per-tile multiplier on tile_units
        s.roles = roles or {}              # role -> rgb
        s.decals = decals or {}            # name -> PIL RGBA image, stretched over its face
        s.fallback = fallback              # name -> Material or None, for names nothing else knows
        s.tile_px = tile_px                # texels one tile is taken to span (None: the image width)
        s.cache = {}

    def add(s, name, material):
        material.name = name; s.cache[name] = material; return name

    def __contains__(s, name):
        try: s.get(name); return True
        except KeyError: return False

    def get(s, name):
        m = s.cache.get(name)
        if m is not None: return m
        base, _, role = name.partition('@')
        if base in s.decals:
            arr = np.asarray(s.decals[base].convert('RGBA')).astype(np.float32) / 255
            m = Material(arr, 'stretch', 1.0, name=name)
        elif base in s.tiles:
            t = s.tiles[base]
            arr = (np.asarray(t.convert('RGBA')).astype(np.float32) / 255) if isinstance(t, Image.Image) else t
            if role: arr = tint(arr, s.roles[role])
            k = s.tile_units * s.tile_scale.get(base, 1.0)
            m = Material(arr, 'tile', (s.tile_px or arr.shape[1]) / k, name=name)
        elif s.fallback is not None and s.fallback(name) is not None:
            m = s.fallback(name)
        else:
            raise KeyError(f'no material {name!r}')
        s.cache[name] = m
        return m


def procedural(color, kind='plain', seed=0, n=48):
    """Small flat tile in a colour, with a hint of weave, grain or wear. Stands in until a painted tile exists."""
    import math
    r = np.random.default_rng(seed)
    base = np.ones((n, n))
    if kind == 'wool':
        base += r.normal(0, .035, (n, n))
        base += .03 * np.sin(np.arange(n) * math.pi)[None, :] * np.sin(np.arange(n) * math.pi / 2)[:, None]
    elif kind == 'wrap':
        base += .10 * (np.sin(np.arange(n) * 2 * math.pi / 12)[:, None] > .55) * -1
        base += r.normal(0, .03, (n, n))
    elif kind == 'leather':
        b = r.normal(0, 1, (-(-n // 6), -(-n // 6))); b = np.kron(b, np.ones((6, 6)))[:n, :n]
        base += .05 * b + r.normal(0, .02, (n, n))
    elif kind == 'wood':
        base += .07 * np.sin(np.arange(n) * 2 * math.pi / 8 + r.normal(0, .6, n))[:, None]
        base += r.normal(0, .02, (n, n))
    elif kind == 'metal':
        base += r.normal(0, .025, (n, 1)) + r.normal(0, .015, (n, n))
    elif kind == 'canvas':
        base += r.normal(0, .045, (n, n))
    elif kind == 'panel':          # machined plates with seams
        base += r.normal(0, .015, (n, n))
        base[::16, :] -= .18; base[:, ::24] -= .14
    elif kind == 'rock':
        b = r.normal(0, 1, (-(-n // 4), -(-n // 4))); b = np.kron(b, np.ones((4, 4)))[:n, :n]
        base += .08 * b + r.normal(0, .04, (n, n))
    elif kind == 'solar':          # photovoltaic cells with bright grid lines
        base += r.normal(0, .02, (n, n)); base[::8, :] += .9; base[:, ::8] += .9
    elif kind == 'grate':          # open floor grating
        base += r.normal(0, .02, (n, n)); base[::6, :] -= .35; base[:, ::6] -= .35
    elif kind == 'dust':           # fine wind-blown dust with soft ripples
        x = np.arange(n); base += .05 * np.sin(x * 2 * math.pi / n * 3 + r.normal(0, .4, n))[:, None] + r.normal(0, .035, (n, n))
    elif kind == 'foliage':
        base += r.normal(0, .12, (n, n)) + .1 * (r.random((n, n)) > .8)
    return np.clip(base[..., None] * (np.array(color, float) / 255.0), 0, 1)
