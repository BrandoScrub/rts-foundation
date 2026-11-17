"""artkit.style: a style pack is everything that makes one game look like itself, kept out of the engine.

A pack is a folder:
  style.json   name, tile size, role colours, ground colour, palette, game scale, proportions, figure materials
  tiles/       flat seamless material tiles (<name>.png or .jpg), painted by an image model or made by code
  decals/      optional RGBA pictures stretched over a face (signs, emblems)
style.json may also list "procedural": {name: [rgb, kind]} for tiles nobody has painted yet; a painted tile with the
same name replaces it. Kinds: plain wool wrap leather wood metal canvas panel rock foliage.
style.json may also give "camera": the view the game's models are built for ("top_down", or {"view": ..., "ground":
0 | null}, or {"matrix": ...}); see core.space.Camera. Without it everything is 2:1 isometric, as always.
Optional "light" (core.light.Rules), "team" (artkit.team) and "shadow" (artkit.shadow) sections, and "unit_camera" (the
camera for animated unit strips, same format as "camera"): each absent = no change.

  st = Style.load('frontier_outpost')     # by name, or a folder path
  mats = st.materials()          # for the renderer

Packs are found by name in: the folders in ARTKIT_STYLES (separated by os.pathsep), a game's own styles/ folder beside
artkit/ (a game keeps its pack there, outside the engine), then artkit/styles/ (the engine's demo packs).
Style.load(None) is the default pack: ARTKIT_STYLE if set, else the game's pack when its styles/ folder holds one.
"""
import json, os
import numpy as np
from PIL import Image

from .core.materials import Materials, Material, procedural
from .core.space import Camera
from .core import light
from .team import Team
from .shadow import Shadow
from . import decals as _decals

HERE = os.path.dirname(os.path.abspath(__file__))


def search_path():
    """Folders searched for a pack by name, in order: ARTKIT_STYLES, the game's styles/ beside artkit/, artkit/styles."""
    env = [p for p in os.environ.get('ARTKIT_STYLES', '').split(os.pathsep) if p]
    return env + [os.path.join(os.path.dirname(HERE), 'styles'), os.path.join(HERE, 'styles')]


def default_name():
    """The pack used when none is named: ARTKIT_STYLE, else the only pack in the game's own folders."""
    if os.environ.get('ARTKIT_STYLE'): return os.environ['ARTKIT_STYLE']
    packs = sorted({n for d in search_path()[:-1] if os.path.isdir(d) for n in os.listdir(d) if os.path.isfile(os.path.join(d, n, 'style.json'))})
    if len(packs) == 1: return packs[0]
    raise ValueError('which style pack? pass one (--style <pack>) or set ARTKIT_STYLE' + (f'; found {packs}' if packs else ''))


class Style:
    def __init__(s, root, cfg):
        s.root = root; s.cfg = cfg; s.name = cfg.get('name', os.path.basename(root))
        s.ground = tuple(cfg.get('ground', (90, 90, 80)))
        s.palette = cfg.get('palette', {})
        g = cfg.get('game', {})
        s.tile_px = g.get('tile_px', 32)
        s.building_px_per_out = g.get('building_px_per_out', 0.5)
        s.figure_k = g.get('figure_k', 0.62)
        s.proportions = cfg.get('proportions', {})
        s.camera = Camera.from_pack(cfg.get('camera'))     # the view this game's models are built for (default isometric)
        # optional: the camera for animated unit strips (Exporter.rig), same format as "camera"; None = use s.camera.
        # Usually the same view with "plates": false, so tracks and feet keep their outline (no ground plates on units)
        # while shadows stay on the ground ("ground": null would make them float, as for flying things).
        s.unit_camera = None if cfg.get('unit_camera') is None else Camera.from_pack(cfg['unit_camera'])
        s.lighting = light.Rules.from_pack(cfg.get('light'))  # optional finishing rules (relief, ao, ink); None = defaults
        s.team = Team.from_pack(cfg.get('team'))           # optional team-coloured materials (artkit.team); None = none
        s.shadow = Shadow.from_pack(cfg.get('shadow'))     # optional cast-shadow layer (artkit.shadow); None = none
        s._mats = None

    @staticmethod
    def load(path=None):
        if path is None: path = default_name()
        if not os.path.isdir(path):
            hits = [os.path.join(d, path) for d in search_path() if os.path.isfile(os.path.join(d, path, 'style.json'))]
            if not hits: raise FileNotFoundError(f'no style pack named {path!r} in {search_path()}')
            path = hits[0]
        return Style(path, json.load(open(os.path.join(path, 'style.json'))))

    def section(s, name):
        """A section of the pack for one module (terrain, hud, maps...): inline in style.json, or the name of a JSON
        file in the pack ("terrain": "terrain.json"). Missing sections give {}."""
        v = s.cfg.get(name, {})
        if isinstance(v, str): v = json.load(open(s.path(v)))
        return v

    def path(s, rel):
        """A file or folder inside the pack."""
        return os.path.join(s.root, rel)

    def tiles(s):
        out = {}
        tp = s.cfg.get('tile_px', 256)
        for name, (rgb, kind) in s.cfg.get('procedural', {}).items():
            arr = procedural(rgb, kind, seed=sum(map(ord, name)), n=tp)
            out[name] = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), 'RGB')
        d = os.path.join(s.root, s.cfg.get('tiles', 'tiles'))
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                n, ext = os.path.splitext(f)
                if ext.lower() in ('.png', '.jpg', '.jpeg'):
                    im = Image.open(os.path.join(d, f)).convert('RGB')
                    if im.size != (tp, tp): im = im.resize((tp, tp), Image.LANCZOS)
                    out[n] = im
        return out

    def decals(s):
        out = _decals.generic()
        d = os.path.join(s.root, s.cfg.get('decals', 'decals'))
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.png'): out[f[:-4]] = Image.open(os.path.join(d, f)).convert('RGBA')
        return out

    def materials(s):
        if s._mats is None:
            figs = {k: v for k, v in s.cfg.get('figures', {}).items() if not k.startswith('_')}
            def fallback(name):
                base = name.partition('@')[0]
                if base in figs:
                    rgb, kind = figs[base]
                    return Material(procedural(rgb, kind, seed=sum(map(ord, base))), 'nearest', 3.0, base == 'glow')
                from . import figure                     # the stock figure materials (cloth, skin, leather...)
                if name in figure.MAT_ID:
                    m = figure.MATS[figure.MAT_ID[name]]
                    return Material(m['tex'], 'nearest', figure.TEX_PX_PER_UNIT, m['emissive'])
                return None
            s._mats = Materials(tiles=s.tiles(), tile_units=s.cfg.get('tile_units', 128), tile_scale=s.cfg.get('tile_scale', {}),
                                roles={k: tuple(v) for k, v in s.cfg.get('roles', {}).items()}, decals=s.decals(),
                                fallback=fallback, tile_px=s.cfg.get('tile_px'))
        return s._mats

    def role(s, name): return tuple(s.cfg.get('roles', {})[name])
