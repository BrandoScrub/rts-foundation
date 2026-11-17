"""artkit.export: every kind of asset out through one door, into one manifest a game loads.

  ex = Exporter(style, 'out/art')
  ex.static('hab', Asset(recipe))          # still sprites: one per stage, plus a strip per turning part
  ex.rig('rover', rig, clips)               # animated strips (unitkit's manifest format: same game runtime)
  ex.save()                                 # writes assets.json, then packs animated strips into tight pages

assets.json:
  {"<key>": {"kind": "static", "footprint": [w, d], "states": {"normal": {"src", "size", "near_corner", "centre", "origin"}, ...},
             "turning": {"<pivot>": {"src", "headings", "frame": [w, h], "anchor": [x, y], "at": [x, y]}}},
   "<key>": {"kind": "unit", ...unitkit manifest..., "pack": [...]}}
Anchors are in sprite pixels. near_corner is where the footprint's nearest corner falls (isokit's placement rule).

Optional, only when the style pack has the section (or the call asks): "team" -> a grey mask beside each picture
(state "team": "<file>", turning "team": "<file>", unit clips "team": {layer: file} / "team_pack" after packing, and
"team_gain" on the record); "shadow" -> a shadow picture per still stage (state "shadow": {src, size, near_corner,
origin}) and a shadow layer "S" for units. See artkit/team.py and artkit/shadow.py.
"""
import json, math, os
import numpy as np
from PIL import Image

from .core import render as R
from .core import ink
from .core.geom import FLAT, SMOOTH
from .core.materials import Materials
from .sprite import picture, AA, EDGE_FLAT, EDGE_SMOOTH
from . import pack as _pack
from . import shadow as _shadow


def _crop_box(imgs):
    b = [10 ** 9, 10 ** 9, -1, -1]
    for im in imgs:
        ys, xs = np.nonzero(im[..., 3])
        if len(xs): b = [min(b[0], xs.min()), min(b[1], ys.min()), max(b[2], xs.max()), max(b[3], ys.max())]
    return b


class Exporter:
    def __init__(s, style, out, scale=0.4, log=print):
        s.style, s.out, s.scale, s.log = style, out, scale, log
        os.makedirs(out, exist_ok=True)
        s.assets = {}

    # ---- still assets
    def _opt(s, given, attr):
        """A per-call option: None -> the style's own (style.team / style.shadow), False -> off, else as given."""
        if given is False: return None
        return getattr(s.style, attr, None) if given is None else given

    def static(s, key, asset, headings=16, facings=1, finish=None, critique=False, team=None, shadow=None, camera=None):
        """A still asset with its stages and turning parts. facings: 1, 2 or 4 views of it, a quarter turn apart
        (asset.facing): the record of facing 0 is the asset's own, the others are in rec['facings'] with their own
        footprint, stages, turning strips and anchors, so a game can let the player rotate anything.
        finish: True (the style pack's 'finish' section) or a rules dict: run the finishing pass on every stage
        (feathered plate edges, lifted dark yards, translucent earth yards; see finish_still). The plate colour
        goes into the stage's record as 'g'.
        critique: run the design critic (artkit.design.critique) while the geometry is at hand and keep its verdict
        in rec['design'] (score, rank, metrics, findings), one per facing, for the Art Director's report. Rank and
        height class come from the asset's spec ('rank', 'height_class'); a composed building's brief wins.
        team / shadow: an artkit.team.Team / artkit.shadow.Shadow, False for none; default the style pack's sections
        (absent: nothing extra is written). camera: a core.space.Camera for this asset instead of the style's (a vehicle
        exported as a still: the same view with ground None keeps the outline along its tracks)."""
        s._team = s._opt(team, 'team'); s._shadow = s._opt(shadow, 'shadow')
        s._cam = camera                              # None: the style's camera (sprite.picture's own default)
        s._finish = None if not finish else dict(FINISH, **(s.style.section('finish') if finish is True else finish))
        s._fkey = key                                # the finish rules name buildings by their key, whichever facing
        rec = s._static(key, asset, headings)
        if facings > 1:
            step = 4 // facings
            rec['facings'] = [dict(turn=0, **{k: rec[k] for k in ('footprint', 'states', 'turning', 'anchors') if k in rec})]
            for i in range(1, facings):
                r = s._static(f'{key}_f{i * step}', asset.facing(i * step), headings)
                rec['facings'].append(dict(turn=i * step, **{k: r[k] for k in ('footprint', 'states', 'turning', 'anchors') if k in r}))
        if critique:
            rec['design'] = _verdict(asset, s.style)
            if facings > 1:
                for f in rec['facings'][1:]: f['design'] = _verdict(asset, s.style, turn=f['turn'])
        if s._team is not None: rec['team_gain'] = s._team.gain
        s.assets[key] = rec
        s.log(f'{key}: {len(rec["states"])} stages' + (f', turning {list(rec.get("turning", {}))}' if asset.pivots else '') + (f', {facings} facings' if facings > 1 else ''))
        return rec

    def _static(s, key, asset, headings):
        rec = {'kind': 'static', 'name': asset.name, 'footprint': list(asset.footprint), 'states': {}}
        if asset.anchors: rec['anchors'] = asset.anchor_tiles()
        team, shad = getattr(s, '_team', None), getattr(s, '_shadow', None)
        for st, g in asset.states().items():
            cam = getattr(s, '_cam', None)
            img, meta = picture(g, s.style, footprint=asset.footprint, scale=s.scale, team=team, camera=cam)
            tm = meta.pop('team_mask', None)
            if getattr(s, '_finish', None): img = s._finished(s._fkey, g, img, meta, asset.footprint)
            fn = f'{key}.png' if st == 'normal' else f'{key}_{st}.png'
            img.save(os.path.join(s.out, fn)); meta['src'] = fn; rec['states'][st] = meta
            if tm is not None and tm.any():
                tf = fn[:-4] + '_team.png'; Image.fromarray(tm, 'L').save(os.path.join(s.out, tf)); meta['team'] = tf
            if shad is not None:
                sim, smeta = _shadow.picture(g, shad, s.scale, asset.footprint, cam if cam is not None else getattr(s.style, 'camera', None))
                if sim is not None:
                    sf = fn[:-4] + '_shadow.png'; sim.save(os.path.join(s.out, sf)); smeta['src'] = sf; meta['shadow'] = smeta
        base = rec['states']['normal']
        if asset.pivots:
            rec['turning'] = {}
            for pv, spec in asset.pivots.items():
                frames = [picture(asset.turning(pv, h), s.style, footprint=asset.footprint, scale=s.scale, team=team, camera=cam)
                          for h in np.arange(headings) * 360 / headings]
                tms = [m.pop('team_mask', None) for _, m in frames]
                # every frame shares the footprint, so align them on the near corner, then crop to the union
                cw = max(int(m['near_corner'][0]) for _, m in frames) + max(im.size[0] - int(m['near_corner'][0]) for im, m in frames)
                ch = max(int(m['near_corner'][1]) for _, m in frames) + max(im.size[1] - int(m['near_corner'][1]) for im, m in frames)
                nx = max(int(m['near_corner'][0]) for _, m in frames); ny = max(int(m['near_corner'][1]) for _, m in frames)
                arr = []; marr = []
                for (im, m), tm in zip(frames, tms):
                    c = np.zeros((ch, cw, 4), np.uint8)
                    x, y = nx - int(m['near_corner'][0]), ny - int(m['near_corner'][1])
                    c[y:y + im.size[1], x:x + im.size[0]] = np.asarray(im)
                    arr.append(c)
                    if tm is not None:
                        mc = np.zeros((ch, cw), np.uint8); mc[y:y + im.size[1], x:x + im.size[0]] = tm; marr.append(mc)
                x0, y0, x1, y1 = _crop_box(arr); x1 += 1; y1 += 1
                strip = np.concatenate([a[y0:y1, x0:x1] for a in arr], 1)
                fn = f'{key}_{pv}.png'; Image.fromarray(strip, 'RGBA').save(os.path.join(s.out, fn))
                tf = None
                if marr:
                    mstrip = np.concatenate([a[y0:y1, x0:x1] for a in marr], 1)
                    if mstrip.any(): tf = f'{key}_{pv}_team.png'; Image.fromarray(mstrip, 'L').save(os.path.join(s.out, tf))
                rec['turning'][pv] = dict(src=fn, headings=headings, frame=[int(x1 - x0), int(y1 - y0)],
                                          near_corner=[nx - x0 + (frames[0][1]['near_corner'][0] % 1), ny - y0 + (frames[0][1]['near_corner'][1] % 1)],
                                          heading_world_deg=[float(h) for h in np.arange(headings) * 360 / headings])
                if tf: rec['turning'][pv]['team'] = tf
        return rec

    def _finished(s, key, g, img, meta, footprint):
        R_ = s._finish
        if key in R_['no_plate']: return img
        plate = plate_faces(g, footprint); yard = None
        if plate.any():
            km = Materials(tiles={k: Image.new('RGBA', (8, 8), v) for k, v in KEY_TILES.items()})
            kim, _ = picture(keyed(g, plate), s.style, footprint=footprint, scale=s.scale, ink_emit=True, mats=km, camera=getattr(s, '_cam', None))
            yard = np.asarray(plate_mask(kim)) > 127
        im = np.asarray(img).astype(np.float32).copy()
        r = finish_still(im, meta['near_corner'], (footprint[0] * s.scale, footprint[1] * s.scale), yard,
                         keep_dark=key in R_['keep_dark'], solid_yard=key in R_['solid_yards'], rules=R_)
        if r['plate']: meta['g'] = r['g']
        return Image.fromarray(im.clip(0, 255).astype(np.uint8))

    # ---- animated
    def rig(s, key, rig, clips, ss=AA, scale=None, headings=None, manifest=None, line_k=None, team=None, shadow=None, camera=None):
        """Animated strips for anything that moves: an artkit.rig.Rig (machines, walkers, wheels) or a humanoid figure
        (artkit.figure.Biped, Tripod). Rows are headings, columns frames; layered units get a legs strip and a torso
        strip plus the waist socket per frame. Figures are drawn exactly as unitkit drew them (figure materials,
        their own line pass), so strips made here are byte-identical to unitkit's. scale: strip pixels per unit
        (default the unit's export_scale). headings: default the unit's. manifest: also write <dir>/manifest.json
        (unitkit's single-unit file) into this folder. line_k: game pixels per strip pixel at scale 0.4 (line width;
        default the style's figure_k). team / shadow: as for static (default the style pack's sections): team masks
        for every layer (clip "team": {layer: file}, packed into "team_pack" pages in the same layout) and a shadow
        layer "S" (the whole body's shadow, following the legs' clip, frame and heading). camera: a core.space.Camera
        for these strips; default the pack's "unit_camera" if it has one, else its "camera" (as before)."""
        from .rig import Rig
        src = (_RigFrames if isinstance(rig, Rig) else _FigureFrames)(rig, s, scale, ss, line_k)
        src.team = s._opt(team, 'team'); src.shadow = s._opt(shadow, 'shadow')
        ucam = camera if camera is not None else getattr(s.style, 'unit_camera', None)
        if ucam is not None: src.cam = ucam
        if src.shadow is not None: src.names = tuple(src.names) + ('S',)
        heads = headings or src.headings; angs = [i * 360.0 / heads for i in range(heads)]
        names = src.names; W, H, ox, oy, sc = src.W, src.H, src.ox, src.oy, src.sc
        rendered = {}; allimg = {n: [] for n in names}
        def wants(c, n):                 # the shadow layer goes with whichever clips draw the legs (or the whole body)
            if not c.layers: return True
            return n in c.layers or (n == 'S' and ('L' in c.layers or 'F' in c.layers))
        for c in clips:
            rows = []
            for a in angs:
                row = []
                for p in c.poses():
                    imgs, mk = src.layers(p, a)
                    for n, im in imgs.items():
                        if n in allimg and wants(c, n): allimg[n].append(im)
                    row.append((imgs, mk))
                rows.append(row)
            rendered[c.name] = rows
            s.log(f'  {c.name}: {c.frames} frames x {heads} headings' if src.figure else f'  {key} {c.name}: {c.frames} frames x {heads} headings')
        man = dict(unit=rig.name, kind='unit', scale=sc, headings=heads, heading_world_deg=angs,
                   layout='row = heading, column = frame', layers={}, clips={})
        if src.free_torso: man['free_torso'] = True   # legs keep the heading they last walked on
        if src.team is not None: man['team_gain'] = src.team.gain
        crop = {}
        for n in names:
            x0, y0, x1, y1 = _crop_box(allimg[n]); x0, y0 = max(x0 - 1, 0), max(y0 - 1, 0); x1, y1 = min(x1 + 2, W), min(y1 + 2, H)
            crop[n] = (int(x0), int(y0), int(x1), int(y1))
            man['layers'][n] = dict(frame=[int(x1 - x0), int(y1 - y0)], anchor=[round(float(ox - x0), 2), round(float(oy - y0), 2)])
        dec = src.decimals
        for c in clips:
            rows = rendered[c.name]
            e = dict(files={}, frames=c.frames, fps=c.fps, loop=c.loop, events=c.events)
            for n in names:
                if not wants(c, n): continue
                x0, y0, x1, y1 = crop[n]; fw, fh = x1 - x0, y1 - y0
                sheet = np.zeros((fh * len(rows), fw * c.frames, 4), np.uint8)
                msheet = np.zeros((fh * len(rows), fw * c.frames), np.uint8) if src.team is not None and n != 'S' else None
                for r, row in enumerate(rows):
                    for f, (imgs, _) in enumerate(row):
                        sheet[r * fh:(r + 1) * fh, f * fw:(f + 1) * fw] = imgs[n][y0:y1, x0:x1]
                        if msheet is not None: msheet[r * fh:(r + 1) * fh, f * fw:(f + 1) * fw] = imgs[n + '#'][y0:y1, x0:x1]
                fn = f'{key}_{c.name}' + ('' if n == 'F' else '_' + n) + '.png'
                Image.fromarray(sheet, 'RGBA').save(os.path.join(s.out, fn)); e['files'][n] = fn
                if msheet is not None and msheet.any():
                    tf = fn[:-4] + '_team.png'; Image.fromarray(msheet, 'L').save(os.path.join(s.out, tf))
                    e.setdefault('team', {})[n] = tf
            rel = lambda mk, nm, d=2: [round(float(mk[nm][0] - ox), d), round(float(mk[nm][1] - oy), d)]
            if src.layered: e['socket'] = [[rel(mk, 'socket') for _, mk in row] for row in rows]
            if c.stride: e['stride_units'] = round(c.stride, 3)
            if c.loop: e['cycle_s'] = round(c.frames / c.fps, 4)
            if c.events: e['muzzle'] = [[rel(mk, 'muzzle', dec) for _, mk in row] for row in rows]
            extra = src.marks(c)
            if extra: e['marks'] = {m: [[rel(mk, m, dec) for _, mk in row] for row in rows] for m in extra}
            man['clips'][c.name] = e
        s.assets[key] = man
        if manifest:
            with open(os.path.join(s.out, 'manifest.json'), 'w') as f:
                json.dump({k: v for k, v in man.items() if k != 'kind'}, f, separators=(',', ':'))
        return man

    def save(s, pack=True):
        path = os.path.join(s.out, 'assets.json')
        if pack:
            units = {k: v for k, v in s.assets.items() if v.get('kind') == 'unit'}
            _pack.pack_all(s.out, units, log=s.log)
        json.dump(s.assets, open(path, 'w'), separators=(',', ':'))
        return path


# ================================================================ finishing still sprites (was isokit/sprites.py)
# The renderer bakes no shadows and keeps its dark line edges. A building standing on a ground plate (a yard, an apron)
# then needs three touches so it sits on the land: the plate's two near edges are feathered out, a near-black plate is
# lifted toward trodden earth, and an earth-coloured plate becomes a translucent wash so the land underneath shows
# through. Which buildings get which touch is the style pack's call: its "finish" section (Style.section('finish')).
FINISH = {'feather_px': 6.0, 'ground_tol': 46, 'lift_below': 46, 'lift_to': 50.0, 'lift_tint': [1.04, 1.0, 0.9],
          'trodden_below': 72, 'keep_dark': [], 'no_plate': [], 'solid_yards': [], 'trodden': True}


def plate_faces(geom, footprint, share=0.7, top=3.5):
    """Which triangles are the ground plate a building stands on: per source polygon, lying within z -0.5..top and
    spanning at least share of the footprint's shorter side."""
    if not len(geom): return np.zeros(0, bool)
    _, inv = np.unique(geom.face, return_inverse=True); nf = inv.max() + 1
    lo = np.full((nf, 3), np.inf); hi = np.full((nf, 3), -np.inf)
    np.minimum.at(lo, inv, geom.P.min(1)); np.maximum.at(hi, inv, geom.P.max(1))
    ext = hi - lo
    return ((hi[:, 2] <= top) & (lo[:, 2] >= -.5) & (np.maximum(ext[:, 0], ext[:, 1]) >= share * min(footprint)))[inv]


def keyed(geom, plate):
    """The geometry in two flat key colours (plate magenta, the rest green), unlit, for rendering a plate mask. Lines
    on the plate are not plate; wire keeps its thin flag, so it casts no line here either."""
    n = len(geom)
    return geom._new(mat=np.where(plate, 'kyard', 'krest').astype(object), shade=np.ones(n), emit=np.ones(n, bool), wear=np.zeros(n, bool))


KEY_TILES = {'kyard': (255, 0, 255, 255), 'krest': (0, 255, 0, 255)}


def plate_mask(rgba):
    """Pixels of a keyed render (see keyed) that are plate, as an 'L' image (255 = plate)."""
    a = np.asarray(rgba).astype(int)
    return Image.fromarray((((a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 3] > 0)) * 255).astype('uint8'), 'L')


def finish_still(im, near, fp_px, yard=None, plate=None, colour=None, keep_dark=False, solid_yard=False, rules=None):
    """Finish one building sprite in place. im: float32 (H, W, 4). near: the footprint's near corner in the image
    (x, y). fp_px: the footprint's two sides in image pixels (along x, along y). yard: bool (H, W) plate mask, needed
    when the plate turns translucent. plate / colour: force the plate decision and its colour (a game keeping what
    it already ships); None measures them. Returns a dict: plate (bool), g (plate colour), trodden (pixels washed)."""
    R_ = dict(FINISH); R_.update(rules or {})
    H, W = im.shape[:2]; mx = im[..., :3].max(2)
    Wg, Hg = fp_px; near = np.asarray(near, float)
    far = near - np.array([Wg - Hg, (Wg + Hg) / 2])
    right = far + np.array([Wg, Wg / 2]); left = far + np.array([-Hg, Hg / 2])
    def op(p):
        x, y = int(round(p[0])), int(round(p[1])); return 0 <= x < W and 0 <= y < H and im[y, x, 3] > 240
    cen = (left + right) / 2
    pl = op(left + (cen - left) * .07) and op(right + (cen - right) * .07) and op(near + (cen - near) * .07)
    # a flat plate has nothing standing above its left and right corners; a building that fills the footprint does
    pl = pl and not (op(left + np.array([10, -16])) and op(right + np.array([-10, -16])))
    if plate is not None: pl = plate
    if not pl: return {'plate': False}
    cols = []                                     # plate colour: samples just inside the two near edges
    for A, B_ in ((left, near), (near, right)):
        for t in np.linspace(.08, .92, 40):
            p = A + (B_ - A) * t; p = p + (cen - p) * .05; x, y = int(p[0]), int(p[1])
            if 0 <= x < W and 0 <= y < H and im[y, x, 3] > 240: cols.append(im[y, x, :3])
    g = np.median(np.array(cols), 0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def dist(A, B_):
        d = B_ - A; n = np.array([-d[1], d[0]]); n /= np.linalg.norm(n)
        if np.dot(cen - A, n) < 0: n = -n
        return (xx - A[0]) * n[0] + (yy - A[1]) * n[1]
    d1 = dist(left, near); d2 = dist(near, right); d = np.minimum(d1, d2)
    F = R_['feather_px']                          # feather the two near edges (inside distance to each edge line)
    k = np.clip(d / F, 0, 1); k = k * k * (3 - 2 * k)
    near_col = (np.abs(im[..., :3] - g).max(2) < R_['ground_tol'])   # only ground-coloured pixels fade
    band = (d < F) & (d > -3) & (near_col | (d < 3.5) | (mx < 40))
    im[..., 3] = np.where(band, im[..., 3] * k, im[..., 3])
    lum = float(g.mean())
    if lum < R_['lift_below']:                    # near-black mud yards: lift toward trodden earth so they sit on the land
        f = R_['lift_to'] / max(lum, 1); diff = np.abs(im[..., :3] - g).max(2); wgt = np.clip((44 - diff) / 14, 0, 1)
        inside = (d1 > -1) & (d2 > -1) & (dist(far, left) > -1) & (dist(right, far) > -1)
        wgt = np.where(inside, wgt, 0)[..., None]
        tint = np.array(R_['lift_tint'], np.float32)
        if not keep_dark: im[..., :3] = im[..., :3] * (1 + (f - 1) * wgt) * (1 + (tint - 1) * wgt)
        g = g * f * tint
    if colour is not None: g = np.array(colour, np.float32)
    out = {'plate': True}
    if R_['trodden'] and not solid_yard and float(g @ [.299, .587, .114]) < R_['trodden_below']:
        # earth yards (mud, cinder) become trodden ground: a translucent dark wash that keeps the painted mottling as
        # shade, so the land the building stands on shows through and gives the yard its colour. Built floors
        # (planks, concrete: brighter than trodden_below) stay solid.
        if yard is None: raise ValueError('an earth yard needs its plate mask (see plate_mask)')
        gl = float(g @ [.299, .587, .114]); l = im[..., :3] @ np.array([.299, .587, .114], np.float32)
        yard = yard & (im[..., 3] > 0)            # the plate, as the renderer saw it
        k = np.clip(.18 + .5 * (gl - l) / gl, .06, .5)
        im[..., 3] = np.where(yard, im[..., 3] * k, im[..., 3])
        wash = g * .6
        for c in range(3): im[..., c] = np.where(yard, wash[c], im[..., c])
        out['trodden'] = int(yard.sum())
    out['g'] = [int(v) for v in g]
    return out


def finish_art(src, dst, footprints, prev=None, rules=None, log=print):
    """The finishing pass over an exported folder in the game's art.json format (src: <key>.png, masks/<key>.png,
    art.json with 'scale' and 'dy' per record), written to dst with each plate's colour recorded as 'g'.
    footprints: building name -> (w, d) tiles; records not in it (wall pieces) are copied through. prev: a game's
    current art.json, whose plate decisions and colours are kept as they are. rules: the style pack's finish section."""
    R_ = dict(FINISH); R_.update(rules or {}); prev = prev or {}; tile_px = R_.get('tile_px', 32)
    os.makedirs(dst, exist_ok=True)
    art = json.load(open(os.path.join(src, 'art.json'))); rep = []
    for key, rec in art.items():
        fn = os.path.basename(rec['src']); im = np.array(Image.open(os.path.join(src, fn)).convert('RGBA')).astype(np.float32)
        H, W = im.shape[:2]; name = key.split(':')[1]; info = ''
        if key.count(':') == 1 and name in footprints and name not in R_['no_plate']:
            w, h = footprints[name]; rr = W / ((w + h) * tile_px * rec['scale'])   # image px per game px
            Wg, Hg = w * tile_px * rr, h * tile_px * rr
            near = np.array([W / 2 + (Wg - Hg) / 2, H + rec['dy'] * rr])
            mp = os.path.join(src, 'masks', fn)
            yard = (np.asarray(Image.open(mp).convert('L')) > 127) if os.path.exists(mp) else None
            try:
                r = finish_still(im, near, (Wg, Hg), yard, plate=('g' in prev[key]) if key in prev else None,
                                 colour=prev[key]['g'] if key in prev and 'g' in prev[key] else None,
                                 keep_dark=name in R_['keep_dark'], solid_yard=name in R_['solid_yards'], rules=R_)
            except ValueError:
                raise SystemExit('no yard mask for %s: export it first (masks/<key>.png)' % name)
            if r['plate']:
                rec['g'] = r['g']; info = 'plate %s' % rec['g'] + (', trodden yard px %d' % r['trodden'] if 'trodden' in r else '')
            else: info = 'no plate'
        Image.fromarray(im.clip(0, 255).astype(np.uint8)).save(os.path.join(dst, fn), optimize=True)
        if info: rep.append(f'{name}: {info}')
    json.dump(art, open(os.path.join(dst, 'art.json'), 'w'), separators=(',', ':'))
    log('\n'.join(rep))
    return art


# ---------------------------------------------------------------- frame sources for Exporter.rig
class _RigFrames:
    """An artkit Rig, drawn with the style's materials."""
    figure = False; decimals = 2; team = None; shadow = None

    def __init__(s, rig, ex, scale, ss, line_k=None):
        s.rig, s.ss = rig, ss
        s.headings = rig.headings; s.layered = rig.layered; s.free_torso = rig.layered
        s.names = ('L', 'U') if rig.layered else ('F',)
        hw, up, down = rig.canvas(); s.sc = sc = scale or getattr(rig, 'export_scale', ex.scale)
        s.W = int(math.ceil(2 * hw * sc)); s.H = int(math.ceil((up + down) * sc)); s.ox, s.oy = s.W / 2.0, up * sc
        s.k = (ex.style.figure_k if line_k is None else line_k) * (0.4 / sc) * rig.draw_scale
        s.mats = ex.style.materials()
        s.cam = getattr(ex.style, 'camera', None)

    def marks(s, clip):
        return [m for m in s.rig.points] + [m for m in s.rig.muzzles if m != 'muzzle']

    def layers(s, pose, a):
        W, H, ox, oy, sc, ss = s.W, s.H, s.ox, s.oy, s.sc, s.ss
        bufs = {}; mk = None
        for n in s.names:
            if n == 'S': continue
            g, mk = s.rig.build(pose, a, None if n == 'F' else n)
            cv = R.Canvas(W * ss, H * ss, sc * ss, ox=ox * ss, oy=oy * ss)
            flat = (g.look == FLAT).any() if len(g) else False
            bufs[n] = (R.raster(g, s.mats, cv, grain=R.grain_field(W, H, ss).astype(np.float64) if flat else None, camera=s.cam,
                                team=s.team), cv, g)
        full = None
        for B, _, _ in bufs.values():
            a_ = B.alpha > 0; full = a_ if full is None else (full | a_)
        out = {}
        for n, (B, cv, g) in bufs.items():
            step = EDGE_SMOOTH if len(g) and (g.look == SMOOTH).mean() > .5 else EDGE_FLAT
            out[n] = R.finish(B, ss, ink.radius(s.k / ss), step, ao_px=cv.s if len(g) and (g.look == FLAT).any() else None,
                              no_seed=B.thin | (B.emit & ~B.flat), no_rim=B.low, full=full)
            if s.team is not None:
                from .team import mask
                out[n + '#'] = mask(B, ss)
        if s.shadow is not None:
            g = s.rig.shadow_geometry(pose, a) if hasattr(s.rig, 'shadow_geometry') else s.rig.build(pose, a, None)[0]
            out['S'] = _shadow.frame(g, s.shadow, W, H, sc, ox, oy, s.cam)
        mk = _marks(mk, sc, ox, oy, s.cam)
        return out, mk


class _FigureFrames:
    """A humanoid figure (artkit.figure.Biped or Tripod), drawn as unitkit drew it: the figure material registry,
    back faces culled, no grain, lines kept off glowing parts, a 5-unit depth edge."""
    figure = True; decimals = 1; team = None; shadow = None
    EDGE = 5.0

    def __init__(s, unit, ex, scale, ss, line_k=None):
        from . import figure as _fig
        s.u, s.ss = unit, ss
        s.headings = getattr(unit, 'headings', 16); s.layered = bool(unit.layered); s.free_torso = bool(getattr(unit, 'free_torso', False))
        s.names = ('L', 'U') if unit.layered else ('F',)
        hw, up, down = getattr(unit, 'canvas', (125, 125, 70)); s.sc = sc = scale or getattr(unit, 'export_scale', 0.4)
        s.W = int(math.ceil(2 * hw * sc)); s.H = int(math.ceil((up + down) * sc)); s.ox, s.oy = s.W / 2.0, up * sc
        s.k = (ex.style.figure_k if line_k is None else line_k) * (0.4 / sc) * getattr(unit, 'draw_scale', 1.0)
        s.mats = _fig.registry()
        s.cam = getattr(ex.style, 'camera', None)

    def marks(s, clip):
        return list(getattr(s.u, 'marks', {}).get(clip.name, ()))

    def layers(s, pose, a):
        W, H, ox, oy, sc, ss = s.W, s.H, s.ox, s.oy, s.sc, s.ss
        parts = {}; mk = None; teams = {}
        for n in s.names:
            if n == 'S': continue
            g, mk = s.u.build(pose, a, None if n == 'F' else n)
            B = R.raster(g, s.mats, R.Canvas(W * ss, H * ss, sc * ss, ox=ox * ss, oy=oy * ss), cull=True, camera=s.cam, team=s.team)
            parts[n] = (B.color, B.zbuf, B.emit)
            if s.team is not None:
                from .team import mask
                teams[n + '#'] = mask(B, ss)
        full = None
        for _, zb, _ in parts.values():
            a_ = zb > -1e8; full = a_ if full is None else (full | a_)
        out = {}
        for n, (col, zb, em) in parts.items():
            B = R.Buffers.__new__(R.Buffers)
            B.color, B.zbuf, B.emit = col, zb, em
            B.alpha = (zb > -1e8).astype(np.float64)
            B.thin = np.zeros(zb.shape, bool); B.low = B.thin; B.flat = B.thin
            out[n] = R.finish(B, ss, ink.radius(s.k / ss), s.EDGE, no_seed=em, full=full)
        out.update(teams)
        if s.shadow is not None:
            out['S'] = _shadow.frame(s.u.build(pose, a, None)[0], s.shadow, W, H, sc, ox, oy, s.cam)
        mk = _marks(mk, sc, ox, oy, s.cam)
        return out, mk


def _marks(mk, sc, ox, oy, cam):
    """Named points (world) -> frame pixels, through the style's camera."""
    if cam is None or cam.M is None:
        return {kk: ((v[0] - v[1]) * sc + ox, ((v[0] + v[1]) / 2 - v[2]) * sc + oy) for kk, v in mk.items()}
    out = {}
    for kk, v in mk.items():
        sx, sy = cam.screen(np.asarray(v, float)); out[kk] = (float(sx) * sc + ox, float(sy) * sc + oy)
    return out


def _verdict(asset, style, turn=0):
    """The design critic's report on an asset, as plain JSON. A composed building is judged as its assembly (tags and
    brief known); anything else as bare geometry, with the rank, footprint and height class from its spec."""
    from . import design
    asm = asset.assembly
    if asm is not None and getattr(asm, 'brief', None) is not None:
        rep = design.critique(asm, style, turn=turn)
    else:
        sp = asset.spec; fp = sp.get('footprint', [1, 1])
        rep = design.critique(asset.base(), style, rank=sp.get('rank', 'minor'), key=asset.name, turn=turn,
                              footprint=tuple(fp), height=sp.get('height_class'))
    num = lambda v: float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v
    return {'score': round(float(rep.score), 1), 'rank': rep.rank, 'metrics': {k: num(v) for k, v in rep.metrics.items()},
            'findings': [[bool(ok), what, fix] for ok, what, fix in rep.findings] + [[False, i, 'fix the assembly'] for i in rep.issues]}
