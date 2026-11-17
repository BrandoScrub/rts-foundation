"""artkit.hud.skin: a HUD skin built the way the sprites are (was hudkit/hudkit.py). Flat material tiles (a metal plate,
brass) and code-built parts (frames, slots, bezel), one light from the upper left, dark outline, light grain. Output is
2x CSS pixels. The colours and random seeds come from the style pack's hud section; the shapes stay.
  plate.png   256 px seamless plate tile (background-size 128px)
  frame.png   9-slice panel frame, slice 16 (border 8 css px), rivets repeat with `round`
  slot.png / slot_hi.png / slot_on.png   9-slice recessed button, slice 6 (border 3 css px), use `fill`
  bezel.png   diamond bezel for a 2:1 isometric minimap; the map canvas sits inset by 4.1% of the width
  rule.png, rule_v.png   brass rule strips
  cut_{tl,tr,bl,br}.png and _s   corner caps for a panel whose free corner is cut at the 2:1 tile angle
  tab.png     9-slice raised tab, slice 8;  bay_row.png  one row of four empty command slots
  python3 -m artkit.hud <out_dir> [--style <pack>]
"""
import os, numpy as np
from PIL import Image, ImageFilter
from . import hud_section
OUT = 'ui'
C = None   # the style's hud section: set by configure()
R = None   # the random stream every part draws from, in a fixed order

def tnoise(n, cells, rs):
    """seamless value noise, n x n, `cells` lattice cells across"""
    g = rs.rand(cells, cells)
    t = np.arange(n) * cells / n
    i = t.astype(int); f = t - i; f = f * f * (3 - 2 * f)
    i1 = (i + 1) % cells
    a = g[i][:, i] * (1 - f)[None, :] + g[i][:, i1] * f[None, :]
    b = g[i1][:, i] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]

def fbm(n, rs, base=4, octs=4):
    out = np.zeros((n, n)); amp = 1; tot = 0
    for o in range(octs):
        out += amp * tnoise(n, base * 2 ** o, rs); tot += amp; amp *= .5
    return out / tot

def plate_tile(n=256, rs=None):
    """gunmetal plate: blotchy tone, horizontal brushing, pitting, a few scratches"""
    rs = R if rs is None else rs
    tone = fbm(n, rs, 3, 4) - .5
    brush = rs.rand(n, 1).repeat(n, 1) - .5
    brush = (brush + np.roll(brush, 1, 0) + np.roll(brush, -1, 0)) / 3
    streak = (tnoise(n, 64, rs) - .5)
    streak = np.asarray(Image.fromarray(((streak + .5) * 255).astype(np.uint8)).resize((n, n)).filter(ImageFilter.BoxBlur(0)), float) / 255 - .5
    hs = np.zeros((n, n))
    for k in range(-6, 7): hs += np.roll(streak, k, 1)
    hs /= 13
    pit = (rs.rand(n, n) > .994).astype(float)
    pit = pit + .5 * (np.roll(pit, 1, 0) + np.roll(pit, 1, 1))
    v = .5 + .30 * tone + .10 * brush + .22 * hs - .35 * pit + (rs.rand(n, n) - .5) * .05
    for _ in range(9):   # scratches, wrapped
        x0, y0 = rs.randint(n), rs.randint(n); L = rs.randint(20, 70); s = rs.uniform(-.25, .25)
        for t in range(L): v[int(y0 + t * s) % n, (x0 + t) % n] += .10
    v = np.clip(v, 0, 1)
    lo = np.array(C['plate']['lo'], float); hi = np.array(C['plate']['hi'], float)
    rgb = lo + (hi - lo) * v[..., None]
    rust = np.clip((fbm(n, rs, 2, 3) - .62) * 5, 0, 1)[..., None]
    rgb = rgb * (1 - .22 * rust) + np.array(C['plate']['rust'], float) * .22 * rust
    return rgb

def brass(v):
    """brass ramp: v 0 (deep shade) .. 1 (highlight)"""
    stops = np.array(C['brass'], float)
    x = np.clip(v, 0, 1) * (len(stops) - 1); i = np.minimum(x.astype(int), len(stops) - 2); f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f

def save(a, name):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name), optimize=True)

def rivet(img, cx, cy, r=3.2):
    """domed brass rivet lit from the upper left, with a dark seat"""
    h, w = img.shape[:2]
    y, x = np.mgrid[0:h, 0:w]; dx = (x - cx) / r; dy = (y - cy) / r; d = np.hypot(dx, dy)
    seat = np.clip(1.35 - d, 0, 1) * np.clip(d - .9, 0, 1) * 4
    img[..., :3] = img[..., :3] * (1 - .7 * np.clip(seat, 0, 1)[..., None])
    m = np.clip((1 - d) * r, 0, 1)
    nz = np.sqrt(np.clip(1 - d * d, 0, 1)); lit = np.clip(.45 + .55 * (-dx * .6 - dy * .6) + .25 * nz, 0, 1)
    col = brass(lit * .9)
    img[..., :3] = img[..., :3] * (1 - m[..., None]) + col * m[..., None]
    img[..., 3] = np.maximum(img[..., 3], m * 255)

def frame(n=120, b=16, plate=None):
    """9-slice panel frame (2x: border 16 = 8 css px). Outline, brass bevel, groove, steel lip. Centre empty."""
    img = np.zeros((n, n, 4))
    y, x = np.mgrid[0:n, 0:n]
    d = np.minimum(np.minimum(x, n - 1 - x), np.minimum(y, n - 1 - y)).astype(float)
    # which side: upper/left faces catch the light, lower/right are in shade
    tl = (np.minimum(x, y) <= np.minimum(n - 1 - x, n - 1 - y))
    lip = plate[:n, :n] * 1.25 + 6
    rgb = np.zeros((n, n, 3)); a = np.zeros((n, n))
    band = d < b
    rgb[band] = lip[band]; a[band] = 255
    # outer bevel d 2..7 brass
    bev = (d >= 2) & (d < 5)
    t = (d - 2) / 3
    v = np.where(tl, .78 - .25 * t, .30 - .12 * t) + (R.rand(n, n) - .5) * .05
    rgb[bev] = brass(v)[bev]
    hl = (d >= 2) & (d < 3.2); rgb[hl & tl] = brass(np.full((n, n), .98))[hl & tl]
    rgb[d < 2] = C['outline']                                   # outline
    gro = (d >= 5) & (d < 6.5); rgb[gro] = C['groove']       # groove
    inn = (d >= b - 3) & (d < b)                              # inner step down to the panel face
    rgb[inn & tl] = rgb[inn & tl] * .45                       # shadow under the lit lip
    rgb[inn & ~tl] = rgb[inn & ~tl] * 1.5 + 10                # light catching the far step
    edge = (d >= b - 1) & (d < b); rgb[edge] = C['edge']
    img[..., :3] = rgb; img[..., 3] = a
    for cx, cy in [(10.5, 10.5), (n - 11.5, 10.5), (10.5, n - 11.5), (n - 11.5, n - 11.5), (n / 2 - .5, 10.5), (n / 2 - .5, n - 11.5), (10.5, n / 2 - .5), (n - 11.5, n / 2 - .5)]: rivet(img, cx, cy, 2.2)
    return img

def slot(n=44, b=6, mode=0, plate=None):
    """9-slice recessed button slot. mode 0 normal, 1 hover, 2 selected (brass lit)."""
    img = np.zeros((n, n, 4)); img[..., 3] = 255
    y, x = np.mgrid[0:n, 0:n]
    d = np.minimum(np.minimum(x, n - 1 - x), np.minimum(y, n - 1 - y)).astype(float)
    tl = (np.minimum(x, y) <= np.minimum(n - 1 - x, n - 1 - y))
    face = plate[40:40 + n, 60:60 + n] * .55
    cy = (y / n)[..., None]
    face = face * (1.12 - .3 * cy) + np.array(C['slot_tint'], float)     # darker toward the bottom, slight olive
    rgb = face.copy()
    rim = d < 2
    rimv = [.42, .62, .95][mode]
    rgb[rim] = brass(np.where(tl, rimv, rimv * .55) + (R.rand(n, n) - .5) * .04)[rim]
    rgb[d < 1] = rgb[d < 1] * ([.5, .7, 1.][mode])
    sh = (d >= 2) & (d < 5)                                    # recess: upper/left inner wall in shadow
    k = ((5 - d) / 3)[..., None]
    rgb = np.where((sh & tl)[..., None], rgb * (1 - .75 * k), rgb)
    rgb = np.where((sh & ~tl)[..., None], rgb + 16 * k, rgb)
    if mode == 2:
        glow = np.clip(1 - d / 14, 0, 1)[..., None] ** 2
        rgb = rgb + np.array(C['slot_glow'], float) * glow * .55
    img[..., :3] = rgb
    return img

def bezel(w=624, h=312, pad=28, plate=None):
    """diamond bezel for the 2:1 isometric minimap. Canvas sits inset by `pad` (2x px)."""
    W, H = w + 2 * pad, h + 2 * pad
    img = np.zeros((H, W, 4))
    y, x = np.mgrid[0:H, 0:W]
    u = np.abs(x - (W - 1) / 2) / (W / 2); v = np.abs(y - (H - 1) / 2) / (H / 2)
    # distance (px, measured vertically-ish) inside the outer diamond
    d = (1 - (u + v)) * (H / 2) * .894                       # .894 = cos(atan(.5)): perpendicular px
    ring = pad * .894 + 3
    tl = ((y - (H - 1) / 2) < 0)                              # upper edges lit
    left = ((x - (W - 1) / 2) < 0)
    rgb = np.zeros((H, W, 3)); a = np.zeros((H, W))
    pt = np.tile(plate, (H // 256 + 1, W // 256 + 1, 1))[:H, :W] * 1.25 + 6
    band = (d >= 0) & (d < ring)
    rgb[band] = pt[band]; a[band] = 255
    bev = (d >= 2) & (d < 6); t = (d - 2) / 4
    lit = np.where(tl & left, .82, np.where(tl, .62, np.where(left, .40, .24))) - .14 * t + (R.rand(H, W) - .5) * .05
    rgb[bev] = brass(lit)[bev]
    hl = (d >= 2) & (d < 3.3) & tl & left; rgb[hl] = brass(np.full((H, W), .98))[hl]
    rgb[(d >= 0) & (d < 2)] = C['outline']
    gro = (d >= 6) & (d < 7.5); rgb[gro] = C['groove']
    inn = (d >= ring - 4) & (d < ring)
    rgb[inn & tl] = rgb[inn & tl] * .4
    rgb[inn & ~tl] = rgb[inn & ~tl] * 1.5 + 10
    inner = d >= ring                                         # backing behind the map
    rgb[inner] = C['backing']; a[inner] = 255
    # soft edge
    aa = np.clip(d + 1, 0, 1); a = a * aa
    img[..., :3] = rgb; img[..., 3] = a
    # rivets along the steel band, and a boss at each point
    mid = (7.5 + ring - 4) / 2 / .894
    for s in np.linspace(.12, .88, 7):
        for sx in (-1, 1):
            for sy in (-1, 1):
                px = (W - 1) / 2 + sx * s * (W / 2 - mid * 2); py = (H - 1) / 2 + sy * (1 - s) * (H / 2 - mid)
                rivet(img, px, py, 2.4)
    return img

# ---------------------------------------------------------------- console parts (Nov 9 2026, layout pass)
# The HUD's one shape: a docked plate. Edges that touch the screen edge stay square; the free corner is cut at the
# 2:1 isometric angle, the same line as the minimap bezel and every tile in the world. These caps sit over a
# clipped corner of a framed panel and carry the frame's profile round the cut, mitred into both straight edges.
def frame_profile(d, lit, plate, rs):
    """the frame's cross-section as a function of distance d (2x px) from the outer edge. lit: brass value per pixel."""
    h, w = d.shape; b = 16
    rgb = plate[:h, :w] * 1.25 + 6
    bev = (d >= 2) & (d < 5); t = (d - 2) / 3
    v = lit - .2 * t + (rs.rand(h, w) - .5) * .05
    rgb[bev] = brass(v)[bev]
    rgb[d < 2] = C['outline']
    gro = (d >= 5) & (d < 6.5); rgb[gro] = C['groove']
    return rgb, b

def cut_cap(corner='tr', w=96, h=48, plate=None, rs=None):
    """corner cap for a panel whose `corner` is cut at 2:1. w x h is the corner box (2x px). Only the frame band is opaque."""
    y, x = np.mgrid[0:h, 0:w].astype(float) + .5
    fx = corner[1] == 'r'; fy = corner[0] == 'b'
    X = x if fx else w - x                 # X runs toward the cut corner
    Y = y if not fy else h - y             # Y runs away from the cut edge
    # cut line from (0,0) to (w,h) in (X,Y); inside is below it. perpendicular distance:
    dc = (Y * w - X * h) / np.hypot(w, h)
    d = np.minimum(dc, w - X)              # mitre into the vertical edge the cut runs into
    lit_cut = {'tl': .82, 'tr': .62, 'bl': .40, 'br': .24}[corner]
    lit_side = (.30 if fx else .78)        # the vertical edge at X = w: right edge in shade, left edge lit
    on_side = (w - X) < dc
    lit = np.where(on_side, lit_side, lit_cut)
    pt = np.tile(plate, (1, 1, 1))
    rgb, b = frame_profile(d, lit, pt, rs)
    if corner in ('tl', 'tr'):             # bright arris on lit cuts
        hl = (dc >= 2) & (dc < 3.2) & ~on_side; rgb[hl] = brass(np.full((h, w), .95))[hl]
    inn = (d >= b - 3) & (d < b)
    up = corner[0] == 't'
    rgb[inn] = rgb[inn] * (.45 if up else 1.5) + (0 if up else 10)
    edge = (d >= b - 1) & (d < b); rgb[edge] = C['edge']
    a = np.clip(dc + 1, 0, 1) * 255
    a[d >= b] = 0                          # the panel's own face shows through; the band hides the clipped straight frame
    img = np.dstack([rgb, a])
    # one rivet on the steel lip, mid cut
    mx, my = w * .5, h * .5; nx, ny = -h / np.hypot(w, h), w / np.hypot(w, h)
    px, py = mx + nx * 10.5, my + ny * 10.5
    rivet(img, px if fx else w - px, py if not fy else h - py, 2.2)
    return img

def tab_plate(w=40, h=40, plate=None):
    """small raised tab face (9-slice, slice 8): for hanging tabs and minimap tools. Lit top-left, dark outline."""
    img = np.zeros((h, w, 4)); img[..., 3] = 255
    y, x = np.mgrid[0:h, 0:w]
    d = np.minimum(np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y)).astype(float)
    tl = (np.minimum(x, y) <= np.minimum(w - 1 - x, h - 1 - y))
    rgb = plate[100:100 + h, 100:100 + w] * 1.35 + 8
    rgb[d < 1] = C['outline']
    r1 = (d >= 1) & (d < 3)
    rgb[r1 & tl] = rgb[r1 & tl] * 1.7 + 14
    rgb[r1 & ~tl] = rgb[r1 & ~tl] * .5
    img[..., :3] = rgb
    return img

def bay_row(cols=4, sw=124, sh=100, gap=6, plate=None):
    """one row of empty command slots (2x px). Tiled down the command bay so the card keeps its grid when it is
    not full: the slots are places, the buttons are what is in them."""
    W = cols * sw + (cols - 1) * gap; H = sh + gap
    img = np.zeros((H, W, 4))
    for c in range(cols):
        x0 = c * (sw + gap)
        y, x = np.mgrid[0:sh, 0:sw]
        d = np.minimum(np.minimum(x, sw - 1 - x), np.minimum(y, sh - 1 - y)).astype(float)
        tl = (np.minimum(x, y) <= np.minimum(sw - 1 - x, sh - 1 - y))
        rgb = plate[30:30 + sh, 10 + c * 40:10 + c * 40 + sw] * .42 + np.array(C['bay_tint'], float)
        rim = d < 2; rgb[rim & tl] = C['bay_rim'][0]; rgb[rim & ~tl] = C['bay_rim'][1]
        sh_ = (d >= 2) & (d < 5); k = ((5 - d) / 3)[..., None]
        rgb = np.where((sh_ & tl)[..., None], rgb * (1 - .6 * k), rgb)
        img[0:sh, x0:x0 + sw, :3] = rgb; img[0:sh, x0:x0 + sw, 3] = 255
    return img

def parts2(P):
    rs = np.random.RandomState(C['seeds'][1])
    for c in ('tl', 'tr', 'bl', 'br'):
        save(cut_cap(c, 96, 48, P, rs), 'cut_%s.png' % c)
        save(cut_cap(c, 56, 28, P, rs), 'cut_%s_s.png' % c)
    save(tab_plate(plate=P), 'tab.png')
    # keystone drop: the notch under the top rail that carries the clock. Brass rule bent down round a plate.
    n = 64; s = np.zeros((8, n, 4)); s[..., 3] = 255
    for r, vv in enumerate([.03, .2, .34, .5, .62, .78, .95, .05][::-1]): s[r, :, :3] = brass(np.full(n, vv) + (rs.rand(n) - .5) * .05)
    save(np.rot90(s, 1), 'rule_v.png')
    save(bay_row(plate=P), 'bay_row.png')

def configure(style=None):
    """Take the HUD colours and seeds from a style pack's hud section and reset the random stream."""
    global C, R
    C = hud_section(style); R = np.random.RandomState(C['seeds'][0])


def write(out, style=None):
    """Every HUD image into out (see the module docstring). Returns the file names."""
    global OUT
    OUT = out; os.makedirs(OUT, exist_ok=True); configure(style)
    P = plate_tile()
    save(P, 'plate.png')
    save(frame(plate=P), 'frame.png')
    for m, nm in enumerate(['slot.png', 'slot_hi.png', 'slot_on.png']): save(slot(mode=m, plate=P), nm)
    save(bezel(plate=P), 'bezel.png')
    # brass rule strip (tileable horizontally) for bar edges
    n = 64; s = np.zeros((8, n, 4)); s[..., 3] = 255
    for r, vv in enumerate([.05, .95, .78, .62, .5, .34, .2, .03]): s[r, :, :3] = brass(np.full(n, vv) + (R.rand(n) - .5) * .05)
    save(s, 'rule.png')
    parts2(P)
    return sorted(os.listdir(OUT))
