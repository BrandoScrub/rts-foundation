"""artkit.design: design logic. A building is designed from a brief, in the theme's own language, and then judged
the way a player sees it: small.

  Brief      what the thing is for: role, rank, the mechanic it must show, the mood of its ground, what stands in
             its yard. No shapes.
  compose    brief + theme -> Assembly. The theme (style.json "design") owns the answers: which materials carry
             which value, how a mass is broken up so it is not a box, which signature a role gets, how walls are
             given rhythm, where the one colour goes, what the ground looks like. Decisions are written to
             Assembly.notes so you can read why it looks the way it does.
  critique   measures a design at play size. The rule behind it (from the Command Hall rework): at play size only
             outline, value blocks and one colour carry; anything a few pixels big is wasted.
  search     composes several variants of a brief and keeps the one the critic scores best.
  lineup     checks a whole set: are two buildings the same shape, does each speak the theme's grammar.

  python3 -m artkit.design <style> <briefs.json> <out dir>      sheet of proposals + report

Nothing here knows a particular game: the game's taste lives in its style pack and its briefs.
"""
import json, math, os, sys
from dataclasses import dataclass, field, asdict
import numpy as np
from PIL import Image, ImageDraw

from .core.geom import Geometry
from .core import render as R
from . import shapes as sh
from .assembly import Assembly, Volume, TAGS
from . import motifs as MO
from .parts import building as B

RANKS = ('minor', 'major', 'landmark')
ROOF_ITEMS = ('searchlight', 'dish', 'vent', 'mast', 'water_tower', 'stacks')   # stand on a flat roof at the back (or crown a tower)
TOWERS = ('stepped_tower', 'drum_tower', 'vault_drum')                  # rise from the ground at the back corner
ON_LOW = ('derrick',)                                                   # works over the yard, from the lowest roof

# what a design has to reach, by rank; a theme may override any of it in design.targets
TARGETS = dict(
    box={'minor': .88, 'major': .84, 'landmark': .80},       # most of the outline one plain block allowed to explain
    rise={'minor': .20, 'major': .35, 'landmark': .55},      # how far the signature stands above that block (in block heights)
    levels={'minor': 2, 'major': 2, 'landmark': 3},          # roof levels
    value_spread=.18, block_share=.55,                       # light to dark range; share of the picture in bold blocks
    accent=(.012, .09), accent_blobs=.65,                    # one colour: enough to see, not so much it is the wall colour
    min_px=4,                                                # a part smaller than this at play size cannot be seen
)


@dataclass
class Brief:
    key: str
    name: str = ''
    footprint: tuple = (2, 2)        # tiles
    role: str = 'industry'           # the theme maps roles to signatures and roofs
    rank: str = 'minor'              # minor, major, landmark: how much skyline it may claim
    mechanic: str = ''               # one sentence: what the player uses it for. Shown in the notes and the sheet.
    signature: object = None         # motif name or list, to overrule the theme's choice for the role
    mood: str = 'work'               # a ground mood from the theme: siege, work, calm
    shows: tuple = ()                # yard props that show the job (names from motifs.YARD)
    storeys: float = None
    plan: str = None                 # setback, wing_x, wing_y, block; None lets the seed choose
    seed: int = 0
    all_round: bool = True           # dress the two far walls too, for games where the player can rotate buildings
    height: str = None               # a height class from the theme's design.scale.height.classes (e.g. 'mast'); None: by rank

    @staticmethod
    def load(path):
        return [Brief(**{k: (tuple(v) if isinstance(v, list) and k in ('footprint', 'shows') else v) for k, v in b.items()})
                for b in json.load(open(path))]


class Site:
    """What a motif needs: the assembly it builds into, the theme and a seeded random source."""
    def __init__(s, asm, style, rng):
        s.asm, s.style, s.th, s.rng = asm, style, style.cfg['design'], rng

    def m(s, role):
        v = s.th['values']
        return v.get(role) or v.get({'body2': 'body', 'roof2': 'roof', 'glass': 'dark', 'log': 'wood', 'rock': 'base', 'cloth': 'body'}.get(role, 'body'))


def _sub(vol, side, f0, f1):
    if side == 'y': return Volume(vol.x + f0 * vol.w, vol.y, vol.z, vol.w * (f1 - f0), vol.d, vol.h)
    return Volume(vol.x, vol.y + f0 * vol.d, vol.z, vol.w, vol.d * (f1 - f0), vol.h)


def _rows(zb, zt, storey):
    zone = zt - zb
    if zone < 56: return []
    n = max(1, int(zone // (storey * .85))); cell = zone / n; h = min(58, cell - 26)
    return [(zb + k * cell + (cell - h) / 2, h) for k in range(n)]


def _dress(c, vol, side, z0, z1, name, f0=0., f1=1., clear=(), banners=0, low_h=0, proud=0):
    """Rhythm for one visible wall: fins on the bay lines, one opening per bay and row, the theme's low openings in
    the base, and banners in the bays nearest the middle. clear: (world position along the wall, half width) to keep free."""
    Rh = c.th['rhythm']; storey = c.style.proportions.get('storey', 110)
    w = _sub(vol, side, f0, f1); span = w.span(side)
    n = max(1, int(round(span / Rh.get('bay', 80)))); bay = span / n
    if z1 - z0 >= 30 and Rh.get('wall') and n > 1:
        MO.MOTIFS[Rh['wall']](c, w, side, n, z0, z1 + (8 if Rh['wall'] == 'fins' else 0), name=f'{name}.fins')
    org = w.x if side == 'y' else w.y
    free = [i for i in range(n) if not any(abs(org + (i + .5) * bay - p) < hw + bay * .45 for p, hw in clear)]
    hang = []
    if banners and z1 - z0 >= 70:
        order = sorted(free, key=lambda i: abs(i + .5 - n / 2))
        hang = order[:banners]
        for i in hang:
            MO.banner(c, w, side, (i + .5) / n, z0 + 10, z1 + 4, w=min(64, bay - 16), name=f'{name}.banner{i}')
    rows = _rows(z0, z1, storey); ow = min(46, bay - 30)
    kinds = Rh.get('high', ['window']); placed = 0
    for i in range(n):
        if i in hang: continue
        for k, (zr, hr) in enumerate(rows):
            if ow < 14 or (i not in free and zr < 130): continue
            lit = c.rng.random() < Rh.get('lit', .25)
            MO.opening(c, w, side, (i + .5) / n, zr, ow, hr, Rh.get('glow', 'window_lit') if lit else kinds[int(c.rng.integers(len(kinds)))]); placed += 1
        if low_h >= 60 and Rh.get('low') and i in free:
            x, y, z = MO._on(w, side, (i + .5) / n, min(40, low_h * .4), out=proud)
            c.asm.extra(B.decal(x, y, z, min(54, bay - 24), 26, Rh['low'], side, bias=3), 'opening')
    return len(hang)


# ================================================================ scale rules (the theme's design.scale)
def scale_rules(style):
    """The theme's scale rules, or {} if it has none (then nothing here checks or trims anything)."""
    return style.cfg.get('design', {}).get('scale', {}) or {}


def height_budget(style, rank, footprint, height_class=None):
    """How tall a building may be, in tiles: {'roof': top of the main mass, 'top': highest point, signature included}.
    Either may be None (not limited). footprint in tiles. The theme gives the budget per tile of footprint side (the
    mean of the two sides), by rank, so a building earns height with ground: design.scale.height.<rank>.roof / .top.
    A height class (a mast, a lookout: things whose job is to be tall and thin) has an absolute cap instead."""
    Hc = scale_rules(style).get('height')
    if not Hc: return {'roof': None, 'top': None}
    side = (footprint[0] + footprint[1]) / 2.0
    if height_class:
        c = Hc.get('classes', {}).get(height_class, {}); t = c.get('top_tiles')
        t = t.get(rank) if isinstance(t, dict) else t
        return {'roof': None, 'top': t}
    b = Hc.get(rank, {})
    return {'roof': b['roof'] * side if b.get('roof') else None, 'top': b['top'] * side if b.get('top') else None}


def proportions(thing, footprint, tile=160.0, eaves=0.0):
    """Measure a design against its footprint (tiles). thing: an Assembly or bare Geometry standing on (0, 0)..footprint.
    Returns tiles: roof (top of the main mass: the highest level (8-unit band) whose own flat area is at least 4% of the
    footprint, so a chimney top or a water-tank lid is not a roof), top (highest point), spill (drawn width over footprint width on screen, the worse of the
    two views a quarter turn apart; 1.0 fits; ground plates and anything lying flat do not count), spill_ground (the same
    with them), over (how far it stands past each footprint edge, in tiles), fill (how much of the footprint's width
    the mass uses)."""
    W, D = footprint[0] * tile, footprint[1] * tile
    if isinstance(thing, Assembly):
        mass = [g for _, g, _, _, t in thing.parts if t in ('base', 'body', 'roof')]
        rest = [g for _, g, _, _, t in thing.parts if t != 'ground'] + [g for g, t in thing.loose if t != 'ground']
        Gm = Geometry.join(mass) if mass else None; Ga = Geometry.join(rest)
    else:
        Ga = Gm = thing
    def above(G):
        P = G.P; keep = P[..., 2].max(1) > 6.0
        return P[keep], G.FN[keep]
    Pa, _ = above(Ga)
    if not len(Pa): return {'roof': 0.0, 'top': 0.0, 'spill': 1.0, 'over': {}, 'fill': 0.0}
    top = float(Pa[..., 2].max())
    Pm, Nm = above(Gm) if Gm is not None else (Pa, None)
    roof = top
    if len(Pm):
        ar = np.linalg.norm(np.cross(Pm[:, 1] - Pm[:, 0], Pm[:, 2] - Pm[:, 0]), axis=1) / 2
        up = Nm[:, 2] > .5; zt = Pm[..., 2].max(1)
        if up.any():   # one level at a time (8-unit bands), so a chimney cap, a tank lid and an aerial do not add up to a roof
            zb = np.floor(zt[up] / 8.0); lv = np.unique(zb)[::-1]
            area = np.array([ar[up][zb == q].sum() for q in lv])
            ok = np.nonzero(area >= .04 * W * D)[0]
            roof = float(zt[up][zb == lv[ok[0]]].max()) if len(ok) else float(zt[up].max())
    X, Y = Pa[..., 0], Pa[..., 1]
    over = {'-x': float(-X.min()), '+x': float(X.max() - W), '-y': float(-Y.min()), '+y': float(Y.max() - D)}
    u, v = X - Y, X + Y                      # the screen's horizontal axis in this view and a quarter turn round
    s0 = (max(u.max(), W) - min(u.min(), -D)) / (W + D); s1 = (max(v.max(), W + D) - min(v.min(), 0.0)) / (W + D)
    fill = 0.0
    if len(Pm):
        um = Pm[..., 0] - Pm[..., 1]; fill = float((min(um.max(), W) - max(um.min(), -D)) / (W + D))
    Pg = (Geometry.join([g for _, g, _, _, _ in thing.parts] + [g for g, _ in thing.loose]) if isinstance(thing, Assembly) else thing).P
    ug, vg = Pg[..., 0] - Pg[..., 1], Pg[..., 0] + Pg[..., 1]             # with the ground plate and whatever lies on it
    sg = max((max(ug.max(), W) - min(ug.min(), -D)) / (W + D), (max(vg.max(), W + D) - min(vg.min(), 0.0)) / (W + D))
    return {'roof': roof / tile, 'top': top / tile, 'spill': float(max(s0, s1)), 'spill_ground': float(sg), 'fill': fill,
            'over': {k: round(val / tile, 3) for k, val in over.items()}}


def compose(brief, style, seed=None):
    """Design one building from its brief in the style's theme. Returns an Assembly (asm.notes says why).
    If the theme has scale rules (design.scale), the result is kept inside its height budget: the body and the
    signature are trimmed until the roof and the highest point fit, and the note says by how much."""
    asm = _compose(brief, style, seed)
    rules = scale_rules(style)
    if not rules.get('height'): return asm
    tile = rules.get('tile', 160.0); bud = height_budget(style, brief.rank, brief.footprint, brief.height)
    hk = sk = 1.0
    for _ in range(4):
        m = proportions(asm, brief.footprint, tile); again = False
        if bud['roof'] and m['roof'] > bud['roof'] * 1.001:
            hk *= .985 * bud['roof'] / m['roof']; again = True
        if bud['top'] and m['top'] > bud['top'] * 1.001:
            body = min(m['roof'], bud['roof'] or m['roof'])
            if m['top'] - m['roof'] > .05: sk *= max(.3, .97 * max(.05, bud['top'] - body) / (m['top'] - m['roof']))
            else: hk *= .985 * bud['top'] / m['top']
            again = True
        if not again: break
        asm = _compose(brief, style, seed, hk=hk, sk=sk)
    if hk < 1 or sk < 1:
        asm.note(f'scale: trimmed to the height budget (body x{hk:.2f}, signature x{sk:.2f}): roof {m["roof"]:.2f} tiles'
                 f'{" of " + format(bud["roof"], ".2f") if bud["roof"] else ""}, top {m["top"]:.2f}{" of " + format(bud["top"], ".2f") if bud["top"] else ""}')
    return asm


def _compose(brief, style, seed=None, hk=1.0, sk=1.0):
    """compose without the budget loop. hk, sk: factors on the body height and the signature height."""
    th = style.cfg['design']; Ms = th['massing']
    bay = th.get('units', {}).get('bay', 160); storey = style.proportions.get('storey', 110)
    seed = brief.seed if seed is None else seed
    rng = np.random.default_rng(1000 + seed * 7919 + sum(map(ord, brief.key)))
    asm = Assembly(); c = Site(asm, style, rng); note = asm.note
    fx, fy = brief.footprint; W, D = fx * bay, fy * bay
    rank = brief.rank; rk = RANKS.index(rank)
    note(f'{brief.name or brief.key}: {brief.mechanic}' if brief.mechanic else brief.name or brief.key)

    # ---- ground: how much is yard, and on which of the two edges you can see
    G = th['ground'].get(brief.mood, {}); yd = G.get('yard', 0)
    yd = yd * D if yd < 1 else min(yd, .3 * min(W, D))
    margin = Ms.get('margin', 30)
    both = brief.mood == 'siege' or G.get('both')
    x0 = y0 = margin; y1 = D - max(yd, margin); x1 = W - (max(yd, margin) if both else margin)
    bw, bd = x1 - x0, y1 - y0
    asm.add('ground', sh.box(W, D, 3, c.m('ground')), grounded=True, tag='ground')
    note(f'plot {fx}x{fy} tiles, {brief.mood} ground: {yd:.0f} units of yard on the {"two visible edges" if both else "front edge"}')

    # ---- massing: never one box. The seed chooses among the theme's plans; a brief may fix one.
    plans = [p for p in Ms.get('plans', ['setback', 'wing_x', 'wing_y']) if not (min(bw, bd) < 150 and p == 'setback' and rk == 0)]
    plan = brief.plan or plans[seed % len(plans)]
    st = brief.storeys or Ms.get('storeys', {}).get(rank, (1.15, 1.7, 2.0)[rk]); H = st * storey * hk
    a = .56 + .1 * rng.random(); b = .58 + .14 * rng.random()
    vols = {}     # name -> (Volume, material role, {side: (f0, f1, covered up to z)})
    if plan == 'setback':
        H1 = H * .56; lower = Volume(x0, y0, 0, bw, bd, H1); upper = Volume(x0, y0, H1, bw * (a + .08), bd * (b + .06), H - H1 + .15 * storey)
        vols['lower'] = lower; vols['upper'] = upper; main, low, front = upper, lower, lower
        note(f'massing: setback. A {H1:.0f} high podium fills the plot; the upper block ({upper.w:.0f}x{upper.d:.0f}) is pulled to the back corner so two roof levels show')
    elif plan == 'wing_x':
        main = Volume(x0, y0, 0, bw * a, bd, H); wing = Volume(x0 + bw * a, y0, 0, bw * (1 - a), bd * b, H * .58)
        vols['main'] = main; vols['wing'] = wing; low, front = wing, main
        note(f'massing: main block {main.w:.0f}x{main.d:.0f}x{H:.0f} with a lower wing on its right, set back to leave a court at the near corner')
    elif plan == 'wing_y':
        main = Volume(x0, y0, 0, bw, bd * a, H); wing = Volume(x0, y0 + bd * a, 0, bw * b, bd * (1 - a), H * .58)
        vols['main'] = main; vols['wing'] = wing; low, front = wing, main
        note(f'massing: main block across the back with a lower wing forward on the left; the door sits in the court beside it')
    else:
        main = Volume(x0, y0, 0, bw, bd, H); vols['main'] = main; low = front = main
        note('massing: single block (asked for by the brief); the signature has to carry the outline alone')
    top = max(v.top() for v in vols.values())

    # ---- signature: what the role looks like against the sky, sized by rank
    sig = brief.signature or th['signatures'].get(brief.role) or th['signatures'].get('default', [])
    sig = [sig] if isinstance(sig, str) else list(sig)
    k = th.get('signature_height', {}).get(rank, (.8, 1.25, 1.9)[rk]) * sk
    hosts = set()         # volumes that must keep a flat roof
    primary = sig[0] if sig else None
    crowned = primary in TOWERS and primary != 'vault_drum'
    for i, s_ in enumerate(sig):
        if s_ in ON_LOW: hosts.add(id(low))
        elif s_ in ROOF_ITEMS and not (crowned and (i == 1 or s_ == 'mast')): hosts.add(id(low) if primary in TOWERS else id(main))
    if plan == 'setback': hosts.add(id(vols['lower']))

    # ---- body, base, roof: the theme's value blocks
    bh_share = Ms.get('base_share', .5)
    roofs = th['roofs']; rise_of = {}
    for name, v in vols.items():
        role = 'body2' if name == 'wing' else 'body'
        asm.add(name, v.box(c.m(role), top=c.m('roof')), grounded=True, tag='body')
        if v.z < 4:
            bh = min(storey + 6, v.h * bh_share) if rk == 2 else min(storey * .6, v.h * bh_share)
            MO.MOTIFS[Ms.get('base', 'plinth')](c, v, bh, name=f'{name}.base'); v.base_h = bh
        else: v.base_h = 0
        kind = roofs['flat'] if id(v) in hosts else (roofs.get('wing', roofs['flat']) if name == 'wing' else roofs.get(brief.role, roofs['default']))
        if kind == 'dome' and not (.8 < v.w / v.d < 1.25): kind = roofs['flat']
        rise_of[name] = MO.MOTIFS[kind](c, v, name=f'{name}.roof') or 0
        v.roof = kind
    note(f'values: {c.m("base")} base under {c.m("body")} walls, {c.m("roof")} roofs; the wing in {c.m("body2")}' if 'wing' in vols else
         f'values: {c.m("base")} base under {c.m("body")} walls, {c.m("roof")} roofs')

    # ---- door: on the wall that meets the yard
    doors = th.get('door', {}); dk = doors.get(rank, doors.get('default', 'plain_door')) if isinstance(doors, dict) else doors
    if plan == 'wing_y': df0, df1 = b, 1.0
    else: df0, df1 = 0.0, 1.0
    span = front.w * (df1 - df0)
    if dk == 'blast_door' and span < 250: dk = doors.get('default', 'plain_door') if isinstance(doors, dict) else 'plain_door'
    nb = max(1, int(round(span / th['rhythm'].get('bay', 80))))
    di = nb // 2 if rk == 2 or nb < 3 else int(rng.integers(1, nb - 1)); df = df0 + (df1 - df0) * ((di + .5) / nb if nb % 2 or rk < 2 else .5)
    door_x, door_y = MO.MOTIFS[dk](c, front, df)
    note(f'door: {dk} on the front wall')

    # ---- walls: rhythm, openings, and the one colour
    acc = th['accent']; want = acc.get('count', {}).get(rank, (1, 2, 4)[rk]) if acc.get('motif') == 'banner' else 0
    hung = 0
    for name, v in vols.items():
        proud = 7 if Ms.get('base') == 'casemate' else 0
        for side in ('y', 'x'):
            f0, f1, zc = 0., 1., v.base_h
            if plan == 'wing_x' and name == 'main' and side == 'x': zc = max(zc, vols['wing'].top() + rise_of['wing'] + 10)
            if plan == 'wing_y' and name == 'main' and side == 'y': f0 = b
            if plan == 'wing_y' and name == 'main' and side == 'x': pass
            clear = [(door_x, 62 if dk == 'blast_door' else 40)] if (v is front and side == 'y') else []
            is_main_face = (name in ('main', 'upper')) or (plan == 'setback' and name == 'lower' and rk == 2)
            nban = 0
            if want and is_main_face and name != 'wing':
                nban = (want + 1) // 2 if side == 'y' else want // 2
                if plan == 'setback' and rk == 2 and name == 'upper': nban = 0
            hung += _dress(c, v, side, zc, v.h - 10, f'{name}.{side}', f0, f1, clear, nban, low_h=v.base_h if zc == v.base_h else 0, proud=proud)
    if brief.all_round:
        # the far walls get the same rhythm: dress the near walls of a scratch copy and turn it half round the block
        from .core.geom import RZ
        for name, v in vols.items():
            tmp = Assembly(); ct = Site(tmp, style, rng); proud = 7 if Ms.get('base') == 'casemate' else 0
            for side in ('y', 'x'):
                if (plan == 'wing_x' and name == 'wing' and side == 'x') or (plan == 'wing_y' and name == 'wing' and side == 'y'): continue   # that wall is against the main block
                keep = []
                if primary in TOWERS and abs(v.x - x0) < 1 and abs(v.y - y0) < 1:      # the signature stands in this corner: keep its bays clear
                    sz = float(np.clip(.44 * min(bw, bd), 64, 200)); o_, ln = (v.x, v.w) if side == 'y' else (v.y, v.d)
                    keep = [(2 * (o_ + ln / 2) - (o_ + sz / 2), sz / 2 + 10)]
                _dress(ct, v, side, v.base_h, v.h - 10, f'{name}.far{side}', 0., 1., keep, 1 if (want and name in ('main', 'upper')) else 0, low_h=v.base_h, proud=proud)
            mid = (v.x + v.w / 2, v.y + v.d / 2, 0)
            for pn, g, _, gr, tag in tmp.parts: asm.add(pn, g.about(mid, RZ(180)), grounded=gr, tag=tag)
            for g, tag in tmp.loose: asm.extra(g.about(mid, RZ(180)), tag)
        note('all four walls are dressed, so it can be rotated')
    if acc.get('motif') == 'band' or (want and not hung):
        z = main.h - 34
        MO.band(c, main, z, h=18, name='accent.band', mat=c.m('faction'))
        note(f'colour: a {c.m("faction")} band under the roof line' + (' (walls too low for banners)' if want else ''))
    elif hung:
        note(f'colour: {hung} full-height {c.m("faction")} banner(s) on the main block, nothing else in that colour')

    # ---- signature, built
    cx = cy = None; tz = top; tw = 0
    if primary in TOWERS:
        size = float(np.clip(.44 * min(bw, bd), 64, 200)); height = top + k * storey
        if primary == 'vault_drum': cx, cy, tz, tw = MO.vault_drum(c, x0 + size * .55, y0 + size * .55, 0, size * .62, top + k * storey * .8)
        else: cx, cy, tz, tw = MO.MOTIFS[primary](c, x0 - 8, y0 - 8, 0, size, height, tiers=3 if rk else 2)
        note(f'signature: {primary} at the back corner, {tz:.0f} high ({tz / top:.1f}x the roof), so the outline is not the block')
    elif primary in ON_LOW:
        px, py = low.x + low.w * .3, low.y + low.d * .3
        if plan == 'setback':        # the upper block owns the back corner: stand it on the open podium roof beside it
            up_ = vols['upper']; px, py = up_.x + up_.w + (low.w - up_.w) * .4, low.y + low.d * .22
        hh = (top - low.top()) + k * storey * .9
        cx, cy, tz, tw = MO.derrick(c, px, py, low.top(), hh)
        note(f'signature: {primary} from the lower roof, {tz:.0f} high')
    elif primary in ROOF_ITEMS:
        px, py = main.x + main.w * .3, main.y + main.d * .3          # toward the back corner: on screen, height is z minus depth
        cx, cy, tz, tw = _roof_item(c, primary, px, py, main.top(), k, storey, 1.0 + .3 * rk)
        note(f'signature: {primary} on the main roof, toward the back corner where it stands highest on screen')
    spare = [(main.x + main.w * .72, main.y + main.d * .3), (main.x + main.w * .3, main.y + main.d * .72), (low.x + low.w * .6, low.y + low.d * .4)]
    for n_, s_ in enumerate(sig[1:]):
        if primary in TOWERS and primary != 'vault_drum' and n_ == 0 and s_ in ROOF_ITEMS:
            _roof_item(c, s_, cx, cy, tz, k, storey, max(.45, tw / 68), name=f'crown.{s_}')
            note(f'crown: {s_} on the tower top')
        elif primary in TOWERS and primary != 'vault_drum' and s_ == 'mast':
            MO.mast(c, cx - tw * .32, cy - tw * .32, tz, k * storey * .8, name='crown.mast')
        elif s_ in ON_LOW:
            hh = (top - low.top()) + k * storey * .7
            qx, qy = (low.x + low.w * .62, low.y + low.d * .28) if plan != 'setback' else (vols['upper'].x + vols['upper'].w + (low.w - vols['upper'].w) * .5, low.y + low.d * .5)
            MO.derrick(c, qx, qy, low.top(), hh, name='derrick2')
        elif s_ in ROOF_ITEMS:
            host = low if primary in TOWERS else main
            px, py = (host.x + host.w * (.7 - .4 * (n_ % 2)), host.y + host.d * .32)
            _roof_item(c, s_, px, py, host.top(), k * .8, storey, 1.0, name=f'{s_}{n_}')

    # ---- ground: the yard shows the job; the mood dresses the edges
    fy0 = y1 + (28 if Ms.get('base') in ('casemate', 'skirt') else 12)
    dress = G.get('dress', []); edge = 34 if 'berm' in dress else 8
    cur = 16; placed = []; tcur = x0 + 24
    for p in brief.shows:
        if p not in MO.YARD: note(f'yard: no prop called {p}'); continue
        fn, pw, pd = MO.YARD[p]
        if pd > D - edge - fy0:
            if plan == 'setback' and pd + 30 < bd - vols['upper'].d and tcur + pw < x1 - 20:      # no room on the ground: stand it on the podium's front terrace
                lo_ = vols['lower']
                asm.add(f'terrace.{p}{len(placed)}', fn(c).move(tcur, vols['upper'].y + vols['upper'].d + 12, lo_.top()), grounded=True, tag='yard')
                placed.append((p + ' (on the terrace)', 't')); tcur += pw + 16; continue
            note(f'yard: {p} needs {pd} units of depth, the {brief.mood} yard has {D - edge - fy0:.0f}; left out'); continue
        if cur < door_x + 60 and cur + pw > door_x - 60: cur = door_x + 66
        if cur + pw > W - 10:
            if both and len([q for q in placed if q[1] == 'x']) * 110 + 20 + pw < y1:
                yy = 20 + len([q for q in placed if q[1] == 'x']) * 110
                asm.add(f'yard.{p}{len(placed)}', fn(c).rz(90).move(x1 + 30 + pd, yy, 0), grounded=True, tag='yard'); placed.append((p, 'x')); continue
            note(f'yard: no room left for {p}'); continue
        asm.add(f'yard.{p}{len(placed)}', fn(c).move(cur, fy0 + (D - edge - fy0 - pd) * .35, 0), grounded=True, tag='yard'); placed.append((p, 'y')); cur += pw + 14
    if placed: note('yard shows the job: ' + ', '.join(p for p, _ in placed))
    if 'berm' in dress:
        yb = D - 30
        if door_x - 70 > 30: MO.berm(c, 16, yb, door_x - 70, yb, name='siege.berm0')
        if W - 20 > door_x + 70: MO.berm(c, door_x + 70, yb, W - 20, yb, name='siege.berm1')
    if 'wire' in dress and both: MO.wire(c, (W - 14, 20), (W - 14, y1 - 10), name='siege.wire')
    if 'hedgehogs' in dress:
        MO.hedgehog(c, W - 46, D - 40, rot=20, name='siege.hog0')
        if rk: MO.hedgehog(c, door_x, D - 20, s=1.2, rot=50, name='siege.hog1')
    if 'beacons' in dress: MO.beacons(c, [(10, D - 10), (W - 10, D - 10), (W - 10, 10), (door_x - 40, D - 10), (door_x + 40, D - 10)])
    if 'lamp' in dress and cur + 30 < W - 8:
        asm.add('yard.lamp', MO.YARD['lamp'][0](c).move(W - 34, D - 34, 0), grounded=True, tag='yard')
    if dress: note(f'{brief.mood} dressing: ' + ', '.join(dress))
    asm.brief = brief; asm.footprint = (W, D); asm.plan = plan
    asm.anchors = {'door': (door_x, door_y, 0.0)}
    asm.tiles = (fx, fy)
    return asm


def to_asset(asm, states=('build', 'damaged', 'ruined')):
    """A composed assembly as an exportable Asset: footprint, door anchor, stages. Exporter.static(key, asset,
    facings=4) then renders it from all four sides."""
    b = asm.brief
    return asm.asset(b.name or b.key, asm.tiles, states=states, anchors={k: list(v) for k, v in asm.anchors.items()})


def all_round(asm, style):
    """Scores from the four sides. A building the player may rotate has to read from each of them."""
    return [critique(asm, style, turn=q) for q in range(4)]


def _roof_item(c, kind, x, y, z, k, storey, s=1.0, name=None):
    name = name or kind
    if kind == 'searchlight': return MO.searchlight(c, x, y, z, r=30 * s, name=name)
    if kind == 'dish': return MO.dish(c, x, y, z, r=44 * s, name=name)
    if kind == 'mast': return MO.mast(c, x, y, z, k * storey * 1.25, name=name)
    if kind == 'stacks': return MO.stacks(c, x - 14 * s, y - 20 * s, z, k * storey * 1.15, n=2 + (s > 1.2), r=11 * s, name=name)
    if kind == 'water_tower': return MO.water_tower(c, x, y, z, k * storey * 1.1, r=40 * s, name=name)
    MO.vent(c, x, y, z, name=name); return x, y, z + 48, 26


# ================================================================ the critic
def _tagged_geometry(thing, accent=None):
    """Geometry whose part id is a tag index. An Assembly knows its tags; bare geometry (an older hand-built mesh)
    is sorted by height: ground plate, low yard things, and the rest as body."""
    if isinstance(thing, Assembly):
        gs = [g.as_part(TAGS.index(t)) for _, g, _, _, t in thing.parts] + [g.as_part(TAGS.index(t)) for g, t in thing.loose]
        return Geometry.join(gs), True
    zmax = thing.P[..., 2].max(1)
    part = np.where(zmax <= 4, TAGS.index('ground'), np.where(zmax < 46, TAGS.index('yard'), TAGS.index('body')))
    if accent: part = np.where(thing.mat == accent, TAGS.index('accent'), part)
    return thing.set(part=part), False


def _iso_box_mask(cv, ss, shape, x0, y0, x1, y1, h):
    pts = np.array([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (0, h)], float)
    sx = ((pts[:, 0] - pts[:, 1]) - cv.cx) * cv.s / ss; sy = (((pts[:, 0] + pts[:, 1]) / 2 - pts[:, 2]) - cv.cy) * cv.s / ss
    from scipy.spatial import ConvexHull
    hull = ConvexHull(np.c_[sx, sy]).vertices
    im = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([(float(sx[i]), float(sy[i])) for i in hull], fill=255)
    return np.asarray(im) > 0


@dataclass
class Report:
    key: str = ''
    rank: str = 'minor'
    score: float = 0.0
    metrics: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)     # (ok, what was measured, what to do about it)
    issues: list = field(default_factory=list)       # from the assembly checker
    lost: list = field(default_factory=list)
    silhouette: object = None

    def text(s):
        out = [f'{s.key} ({s.rank}): {s.score:.0f}/100']
        for ok, what, fix in s.findings: out.append(f'  {"ok  " if ok else "FIX "} {what}' + ('' if ok else f' -> {fix}'))
        for i in s.issues: out.append(f'  FIX  {i}')
        return '\n'.join(out)


def critique(thing, style, rank=None, key=None, play=None, turn=0, footprint=None, height=None):
    """Judge a design at the size it is played at. thing: an Assembly (full report) or bare Geometry (outline, value
    and colour only). Returns a Report. footprint (tiles) and height (a height class) are taken from an Assembly's
    brief; give them for bare geometry to have the theme's scale rules (height budget, footprint spill) checked too."""
    from scipy import ndimage as ndi
    th = style.cfg.get('design', {}); Tg = dict(TARGETS); Tg.update(th.get('targets', {}))
    brief = getattr(thing, 'brief', None)
    rank = rank or (brief.rank if brief else 'minor'); key = key or (brief.key if brief else '')
    play = play or style.building_px_per_out * 0.4          # play pixels per unit
    geom, tagged = _tagged_geometry(thing, th.get('values', {}).get('faction'))
    if turn: geom = geom.rz(90.0 * turn)          # judged from another side (see Asset.facing); the light stays put
    ss = 3
    cv, _, (OW, OH) = R.Canvas.around(geom, play, ss, 6, None, np.float32)
    Bf = R.raster(geom, style.materials(), cv)
    part = Bf.part[ss // 2::ss, ss // 2::ss][:OH, :OW]
    a = Bf.alpha.reshape(OH, ss, OW, ss).mean((1, 3))
    rgb = (Bf.color * Bf.alpha[..., None]).reshape(OH, ss, OW, ss, 3).mean((1, 3)) / np.maximum(a, 1e-6)[..., None]
    if rgb.max() > 2: rgb = rgb / 255.0
    T = lambda *names: np.isin(part, [TAGS.index(n) for n in names])
    S = (a > .5) & ~T('ground', 'yard', 'siege')              # the building itself
    rep = Report(key=key, rank=rank); M = rep.metrics; F = rep.findings
    if S.sum() < 30: rep.findings.append((False, 'nothing to see at play size', 'make it bigger')); return rep
    rep.silhouette = S

    # ---- outline: how much of it is one plain block, and what stands above the block
    So = ndi.binary_opening(S, np.ones((3, 3)))                 # what survives at play size: 1-2 px masts do not
    keep = np.isin(geom.part, [TAGS.index(n) for n in TAGS if n not in ('ground', 'yard', 'siege')])
    P = geom.P[keep]; zt = P[..., 2].max(1)
    ar = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    big = ar > np.percentile(ar, 60)
    bx0, by0 = np.percentile(P[big][..., 0], 2), np.percentile(P[big][..., 1], 2)
    bx1, by1 = np.percentile(P[big][..., 0], 98), np.percentile(P[big][..., 1], 98)
    best = (0, 0, None)
    for h in sorted(set(np.round(zt[zt > 40] / 12) * 12)):
        for sx_ in (1.0, .8, .62):
            for sy_ in (1.0, .8, .62):
                m = _iso_box_mask(cv, ss, S.shape, bx0, by0, bx0 + (bx1 - bx0) * sx_, by0 + (by1 - by0) * sy_, h)
                iou = (m & So).sum() / max(1, (m | So).sum())
                if iou > best[0]: best = (iou, h, m)
    box, bh, bm = best
    M['box'] = round(float(box), 3)
    above = So & ~bm; ys = np.nonzero(So.any(1))[0]; yb = np.nonzero(bm.any(1))[0]
    rise = (yb.min() - ys.min()) / max(1.0, bh * play)
    M['rise'] = round(float(rise), 2)
    xs = np.nonzero(So.any(0))[0]; sky = np.argmax(So[:, xs.min():xs.max() + 1], 0).astype(float)
    lean = np.abs(sky - sky[::-1]).mean() / max(1.0, ys.max() - ys.min())       # 0 for a mirror-symmetric skyline
    M['lean'] = round(float(lean), 2)
    # roof levels, seen from above
    up = (geom.FN[keep][:, 2] > .5) & (zt > 40)
    lv = 0
    if up.any():
        Pu = P[up]; n = np.maximum(2, (np.sqrt(ar[up]) / 6).astype(int)); pts = []
        rng = np.random.default_rng(0)
        for tri, k in zip(Pu, n):
            u = rng.random((k * k, 2)); f = u.sum(1) > 1; u[f] = 1 - u[f]
            pts.append(tri[0] + u[:, :1] * (tri[1] - tri[0]) + u[:, 1:] * (tri[2] - tri[0]))
        pts = np.concatenate(pts); gx = (pts[:, 0] // 12).astype(int); gy = (pts[:, 1] // 12).astype(int)
        gx -= gx.min(); gy -= gy.min(); hm = np.zeros((gx.max() + 1, gy.max() + 1)); np.maximum.at(hm, (gx, gy), pts[:, 2])
        cells = hm[hm > 40]; q = np.round(cells / (.3 * style.proportions.get('storey', 110)))
        vals, cnt = np.unique(q, return_counts=True); lv = int((cnt >= .035 * len(cells)).sum())
    M['levels'] = lv
    t_box, t_rise, t_lv = Tg['box'][rank], Tg['rise'][rank], Tg['levels'][rank]
    F.append((box <= t_box, f'outline: {box * 100:.0f}% of it is one plain block (a {rank} building may be {t_box * 100:.0f}%)',
              'break the mass: set an upper storey back, add a lower wing, or enlarge the signature'))
    F.append((rise >= t_rise or box <= t_box - .2, f'skyline: the highest part stands {rise:.2f} block-heights above the main mass (wants {t_rise})',
              'the signature is too small or too thin to survive at play size: make it taller and at least 4 px thick'))
    F.append((lv >= t_lv, f'roof levels: {lv} (wants {t_lv})', 'vary the heights: podium, block and tower should each have their own roof'))

    # ---- scale: height earned by footprint, and nothing standing past the footprint (the theme's design.scale)
    rules = scale_rules(style)
    footprint = footprint or getattr(thing, 'tiles', None); height = height or (brief.height if brief else None)
    if rules and footprint:
        pr = proportions(thing, footprint, rules.get('tile', 160.0)); bud = height_budget(style, rank, footprint, height)
        M['roof_tiles'] = round(pr['roof'], 2); M['top_tiles'] = round(pr['top'], 2); M['spill'] = round(pr['spill'], 3); M['fill'] = round(pr['fill'], 2)
        side = (footprint[0] + footprint[1]) / 2.0
        if rules.get('height'):
            over = [(n, pr[n], bud[n]) for n in ('roof', 'top') if bud[n] and pr[n] > bud[n] * 1.02]
            cls = f'a {height}' if height else f'a {rank} building on {footprint[0]}x{footprint[1]}'
            lim = ', '.join(f'{n} {bud[n]:.2f}' for n in ('roof', 'top') if bud[n])
            F.append((not over, f'height: roof {pr["roof"]:.2f} tiles, top {pr["top"]:.2f} ({pr["roof"] / side:.2f} and {pr["top"] / side:.2f} per tile of width; {cls} may reach {lim})',
                      '; '.join(f'{n} is {v / b * 100 - 100:.0f}% over: lower it to {b:.2f} tiles or give the building more ground' for n, v, b in over)))
        sp = rules.get('spill', {}); mx = sp.get('max', 1.05) if isinstance(sp, dict) else sp
        if mx:
            worst = max(pr['over'].items(), key=lambda t: t[1]) if pr['over'] else ('', 0)
            plate = isinstance(sp, dict) and sp.get('ground', True) and pr['spill'] <= mx + .005 < pr['spill_ground']
            got = max(pr['spill'], pr['spill_ground']) if (isinstance(sp, dict) and sp.get('ground', True)) else pr['spill']
            M['spill_ground'] = round(pr['spill_ground'], 3)
            F.append((got <= mx + .005, f'spill: drawn {got * 100:.0f}% of the footprint\'s width (may be {mx * 100:.0f}%)',
                      'its ground plate or yard reaches past the footprint and will lie over its neighbour: cut it to the plot' if plate else
                      f'it stands {worst[1]:.2f} tiles past the {worst[0]} edge and will overlap its neighbour: pull it inside the plot or give it the tiles'))

    # ---- value: bold blocks of light and dark
    L = rgb @ np.array([.299, .587, .114]); Lb = ndi.uniform_filter(np.where(S, L, 0), 3) / np.maximum(ndi.uniform_filter(S.astype(float), 3), 1e-6)
    v = Lb[S]; p5, p95 = np.percentile(v, [5, 95]); spread = np.percentile(v, 90) - np.percentile(v, 10)
    q = np.clip(((Lb - p5) / max(1e-6, p95 - p5) * 3).astype(int), 0, 2); blocks = 0
    for lev in range(3):
        lab, n = ndi.label(S & (q == lev))
        if n:
            sz = np.bincount(lab.ravel())[1:]; blocks += sz[sz >= .04 * S.sum()].sum()
    bshare = blocks / S.sum()
    M['value_spread'] = round(float(spread), 3); M['block_share'] = round(float(bshare), 2)
    F.append((spread >= Tg['value_spread'], f'value: light to dark range {spread:.2f} (wants {Tg["value_spread"]})',
              'put the theme\'s pale material against its dark one in large areas (base against wall, wall against roof)'))
    F.append((bshare >= Tg['block_share'], f'value blocks: {bshare * 100:.0f}% of the picture is in large even areas (wants {Tg["block_share"] * 100:.0f}%)',
              'too busy: fewer, larger areas of one value; drop small decals'))

    # ---- colour: one accent, in a few large pieces
    A = (a > .5) & T('accent')
    share = A.sum() / S.sum(); lab, n = ndi.label(A); conc = 0.0
    if n: sz = np.sort(np.bincount(lab.ravel())[1:])[::-1]; conc = sz[:4].sum() / A.sum()
    M['accent'] = round(float(share), 3); M['accent_blobs'] = round(float(conc), 2)
    lo, hi = Tg['accent']
    F.append((lo <= share <= hi, f'colour: the accent covers {share * 100:.1f}% (wants {lo * 100:.1f} to {hi * 100:.0f}%)',
              'too little to see: hang it larger' if share < lo else 'too much: it stops being an accent'))
    if share >= lo: F.append((conc >= Tg['accent_blobs'], f'colour: {conc * 100:.0f}% of it is in its four largest pieces (wants {Tg["accent_blobs"] * 100:.0f}%)',
                              'gather the colour into a few large pieces instead of many small ones'))

    # ---- lost work, grammar, and whether everything is held up
    if tagged:
        need = Tg['min_px']; total = 0
        for name, g, (lo_, hi_), _, tag in thing.parts:
            if tag in ('ground',): continue
            total += 1
            c8 = np.array([(x, y, z) for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (lo_[2], hi_[2])])
            w = np.ptp(c8[:, 0] - c8[:, 1]) * play; hgt = np.ptp((c8[:, 0] + c8[:, 1]) / 2 - c8[:, 2]) * play
            if max(w, hgt) < need or (tag in ('signature', 'accent') and min(w, hgt) < 2.5): rep.lost.append(f'{name} ({w:.0f}x{hgt:.0f} px)')
        M['lost'] = len(rep.lost)
        F.append((len(rep.lost) <= .08 * total, f'detail: {len(rep.lost)} of {total} parts are too small to see at play size',
                  'remove or enlarge: ' + ', '.join(rep.lost[:5])))
        have = set(t for *_, t in thing.parts) | set(t for _, t in thing.loose)
        miss = [t for t in th.get('grammar', ('base', 'roof', 'signature', 'accent')) if t not in have]
        F.append((not miss, 'grammar: has ' + ', '.join(t for t in ('base', 'roof', 'signature', 'accent') if t in have), 'missing the theme\'s ' + ', '.join(miss)))
        rep.issues = thing.check()
    wts = {'set': 0, 'height': 14, 'spill': 8, 'outline': 22, 'skyline': 20, 'roof levels': 8, 'balance': 8, 'value': 10, 'value blocks': 10, 'colour': 7, 'detail': 5, 'grammar': 6}
    got = tot = 0
    for ok, what, _ in F:
        w = wts[what.split(':')[0]]; tot += w; got += w * bool(ok)
    rep.score = max(0.0, 100.0 * got / tot - 10 * len(rep.issues))
    return rep


def _norm(S):
    ys, xs = np.nonzero(S); crop = S[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.asarray(Image.fromarray(crop.astype(np.uint8) * 255).resize((48, 48), Image.NEAREST)) > 0


def _same(A, B_): return (A & B_).sum() / max(1, (A | B_).sum())


def search(brief, style, tries=6, avoid=(), same=.80):
    """Compose the brief several ways and keep what the critic likes best. avoid: reports of buildings already in the
    set; a variant whose outline is nearly one of theirs loses 25 points, so a set does not repeat a shape.
    Returns (assembly, report, all reports)."""
    out = []; taken = [_norm(r.silhouette) for r in avoid if r.silhouette is not None]
    for s in range(tries):
        asm = compose(brief, style, seed=brief.seed + s); rep = critique(asm, style)
        clash = max([_same(_norm(rep.silhouette), t) for t in taken], default=0) if rep.silhouette is not None else 0
        if clash > same:
            rep.score -= 25; rep.findings.append((False, f'set: outline is {clash * 100:.0f}% the same as another building in the set', 'choose another plan or signature'))
        out.append((asm, rep))
    best = max(out, key=lambda t: t[1].score)
    best[0].note(f'chosen from {tries} variants: plan {best[0].plan}, score {best[1].score:.0f} (others ' + ', '.join(f'{r.score:.0f}' for _, r in out if r is not best[1]) + ')')
    return best[0], best[1], [r for _, r in out]


def design_set(briefs, style, tries=6, log=None):
    """Design a whole set, most important building first, each one steered away from the outlines already taken."""
    done = {}
    for b in sorted(briefs, key=lambda b: -RANKS.index(b.rank)):
        asm, rep, _ = search(b, style, tries, avoid=[r for _, r in done.values()])
        done[b.key] = (asm, rep)
        if log: log(rep.text()); log('\n'.join('  why  ' + n for n in asm.notes))
    return [done[b.key] for b in briefs]


def lineup(reports, same=.80):
    """Set-level check: any two buildings whose outlines are nearly the same shape will be confused in play."""
    N = [(r.key, _norm(r.silhouette)) for r in reports if r.silhouette is not None]; out = []
    for i in range(len(N)):
        for j in range(i + 1, len(N)):
            iou = _same(N[i][1], N[j][1])
            if iou > same: out.append((N[i][0], N[j][0], round(float(iou), 2)))
    return sorted(out, key=lambda t: -t[2])


# ================================================================ sheets
def card(asm_or_geom, style, rep, footprint=None, title='', notes=()):
    """One proposal: the sprite at 2x, the sprite at play size, the score and what the critic said."""
    from .sprite import picture
    geom = asm_or_geom.geometry() if isinstance(asm_or_geom, Assembly) else asm_or_geom
    big, _ = picture(geom, style, footprint, scale=0.4)
    small = big.resize((max(1, big.width // 2), max(1, big.height // 2)), Image.LANCZOS)
    W = max(560, big.width + small.width + 36); lines = [l for l in rep.text().split('\n')[1:]] + [f'  why  {n}' for n in notes]
    Hh = max(big.height, small.height) + 44 + 15 * len(lines) + 10
    im = Image.new('RGB', (W, Hh), tuple(style.ground)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 30], fill=(24, 24, 22)); d.text((10, 9), f'{title or rep.key}   {rep.score:.0f}/100   ({rep.rank})', fill=(240, 232, 200))
    im.paste(big, (8, 38), big); im.paste(small, (big.width + 24, 38 + big.height - small.height), small)
    d.text((big.width + 24, 38 + big.height - small.height - 14), 'play size', fill=(20, 20, 18))
    y = max(big.height, small.height) + 44
    for l in lines:
        d.text((10, y), l[:int(W / 6.1)], fill=(150, 30, 20) if 'FIX' in l else (20, 20, 18)); y += 15
    return im


def stack(cards, cols=2, bg=(40, 40, 38)):
    rows = [cards[i:i + cols] for i in range(0, len(cards), cols)]
    W = max(sum(c.width for c in r) + 10 * (len(r) + 1) for r in rows); H = sum(max(c.height for c in r) + 10 for r in rows) + 10
    im = Image.new('RGB', (W, H), bg); y = 10
    for r in rows:
        x = 10
        for c in r: im.paste(c, (x, y)); x += c.width + 10
        y += max(c.height for c in r) + 10
    return im


def main(argv):
    from .style import Style
    style = Style.load(argv[0]); briefs = Brief.load(argv[1]); out = argv[2] if len(argv) > 2 else '.'
    os.makedirs(out, exist_ok=True); cards, reps = [], []
    for b, (asm, rep) in zip(briefs, design_set(briefs, style, log=print)):
        cards.append(card(asm, style, rep, footprint=asm.footprint, title=b.name or b.key, notes=asm.notes)); reps.append(rep)
        cards[-1].save(os.path.join(out, f'{b.key}.png'))
    for a, b_, iou in lineup(reps): print(f'SAME SHAPE {a} / {b_}: outlines overlap {iou * 100:.0f}%')
    stack(cards).save(os.path.join(out, 'proposals.png'))


if __name__ == '__main__':
    main(sys.argv[1:])
