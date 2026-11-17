"""artkit.pack: packs animated sprite strips into tight pages, one set of pages per unit (lossless, checked).

Every frame is cropped to what it draws plus one clear pixel, repeats are stored once, the crops are packed, and
every frame is rebuilt from the pages and compared with its strip before anything is written. A manifest entry gains
  pack: [page paths]   and per clip   rects: {layer: [page, x, y, w, h, offset_x, offset_y, ...]}
(seven numbers per frame at (heading * frames + frame) * 7; w = 0 draws nothing), and loses its `files`.
A unit with team masks (clips with "team": {layer: file}, artkit.team) also gains
  team_pack: [mask page paths]   grey pages in exactly the layout of `pack`, so the same rects cut both
and its clips lose "team". Units without masks pack exactly as before.
"""
import hashlib
import json
import math
import os
import sys

import numpy as np
from PIL import Image

MAX_PAGE = 4096
PAD = 1


def crop(cell):
    """Bounds of what the cell draws, with one clear pixel kept round it. None if the cell is empty."""
    on = cell[..., 3] > 0
    if not on.any():
        return None
    ys = np.where(on.any(1))[0]
    xs = np.where(on.any(0))[0]
    H, W = on.shape
    return max(0, xs[0] - 1), max(0, ys[0] - 1), min(W, xs[-1] + 2), min(H, ys[-1] + 2)


def layout(sizes):
    """sizes: {id: (w, h)}. Rows of tallest first. Returns ({id: (page, x, y)}, [(page_w, page_h), ...])."""
    area = sum((w + PAD) * (h + PAD) for w, h in sizes.values())
    widest = max(w for w, h in sizes.values()) + PAD * 2
    W = min(MAX_PAGE, max(widest, int(math.ceil(math.sqrt(area * 1.12) / 16)) * 16))
    place, pages, page, x, y, row, used = {}, [], 0, PAD, PAD, 0, 0
    for i, (w, h) in sorted(sizes.items(), key=lambda kv: (-kv[1][1], -kv[1][0], kv[0])):
        if x + w + PAD > W:
            x, y, row = PAD, y + row + PAD, 0
        if y + h + PAD > MAX_PAGE:
            pages.append((W, y + row + PAD))
            page, x, y, row = page + 1, PAD, PAD, 0
        place[i] = (page, x, y)
        x += w + PAD
        row = max(row, h)
    pages.append((W, y + row + PAD))
    return place, pages


def pack_unit(art, key, m):
    os.makedirs(os.path.join(art, 'pack'), exist_ok=True)
    heads = m['headings']
    strips, uniq, refs, before = {}, {}, {}, 0
    teamed = any(c.get('team') for c in m['clips'].values())
    masks, muniq = {}, {}
    for cn, c in m['clips'].items():
        for L, fn in c['files'].items():
            mim = None
            if teamed and c.get('team', {}).get(L):
                mim = np.array(Image.open(os.path.join(art, c['team'][L])).convert('L')); masks[cn, L] = mim
            fw, fh = m['layers'][L]['frame']
            im = np.array(Image.open(os.path.join(art, fn)).convert('RGBA'))
            if im.shape[0] != heads * fh or im.shape[1] != c['frames'] * fw:
                raise SystemExit(f'{key} {fn}: {im.shape[1]}x{im.shape[0]} is not {c["frames"]} x {heads} cells of {fw}x{fh}')
            strips[cn, L] = im
            before += im.shape[0] * im.shape[1] * 4
            for h in range(heads):
                for f in range(c['frames']):
                    cell = im[h * fh:(h + 1) * fh, f * fw:(f + 1) * fw]
                    b = crop(cell)
                    if b is None:
                        refs[cn, L, h, f] = None
                        continue
                    x0, y0, x1, y1 = b
                    px = cell[y0:y1, x0:x1]
                    key_bytes = px.tobytes() + bytes(str(px.shape), 'ascii')
                    if teamed:                       # a cell's mask is part of what makes it the same cell
                        mpx = mim[h * fh:(h + 1) * fh, f * fw:(f + 1) * fw][y0:y1, x0:x1] if mim is not None else np.zeros(px.shape[:2], np.uint8)
                        key_bytes += b'#' + mpx.tobytes()
                    d = hashlib.blake2b(key_bytes, digest_size=16).digest()
                    uniq.setdefault(d, px)
                    if teamed: muniq.setdefault(d, mpx)
                    refs[cn, L, h, f] = (d, x0, y0)
    place, pages = layout({d: (p.shape[1], p.shape[0]) for d, p in uniq.items()})
    canv = [np.zeros((h, w, 4), np.uint8) for w, h in pages]
    mcanv = [np.zeros((h, w), np.uint8) for w, h in pages] if teamed else None
    for d, px in uniq.items():
        pg, x, y = place[d]
        canv[pg][y:y + px.shape[0], x:x + px.shape[1]] = px
        if teamed: mcanv[pg][y:y + px.shape[0], x:x + px.shape[1]] = muniq[d]
    rects = {}
    for (cn, L, h, f), r in refs.items():
        n = m['clips'][cn]['frames']
        a = rects.setdefault((cn, L), [0] * (heads * n * 7))
        if r is None:
            continue
        d, ox, oy = r
        pg, x, y = place[d]
        px = uniq[d]
        a[(h * n + f) * 7:(h * n + f + 1) * 7] = [pg, x, y, px.shape[1], px.shape[0], int(ox), int(oy)]
    # proof: rebuild every cell from the pages alone and compare it with the strip
    for (cn, L), im in strips.items():
        fw, fh = m['layers'][L]['frame']
        n = m['clips'][cn]['frames']
        a = rects[cn, L]
        out = np.zeros_like(im)
        for h in range(heads):
            for f in range(n):
                pg, x, y, w, hh, ox, oy = a[(h * n + f) * 7:(h * n + f + 1) * 7]
                if w:
                    out[h * fh + oy:h * fh + oy + hh, f * fw + ox:f * fw + ox + w] = canv[pg][y:y + hh, x:x + w]
        vis_a, vis_b = im[..., 3] > 0, out[..., 3] > 0
        if not (vis_a == vis_b).all() or not (im[vis_a] == out[vis_a]).all():
            raise SystemExit(f'{key} {cn}{L}: packed frames do not match the strip')
        if (cn, L) in masks:                 # and every mask, from the mask pages through the same rects
            mi = masks[cn, L]; mo = np.zeros_like(mi)
            for h in range(heads):
                for f in range(n):
                    pg, x, y, w, hh, ox, oy = a[(h * n + f) * 7:(h * n + f + 1) * 7]
                    if w: mo[h * fh + oy:h * fh + oy + hh, f * fw + ox:f * fw + ox + w] = mcanv[pg][y:y + hh, x:x + w]
            if not (mi[vis_a] == mo[vis_a]).all():
                raise SystemExit(f'{key} {cn}{L}: packed team masks do not match the strip')
    stem = key.replace(':', '_')
    names = []
    for i, c in enumerate(canv):
        names.append(f'pack/{stem}_{i}.png')
        Image.fromarray(c, 'RGBA').save(os.path.join(art, names[-1]), optimize=True)
    if teamed:
        tnames = []
        for i, c in enumerate(mcanv):
            tnames.append(f'pack/{stem}_{i}_team.png')
            Image.fromarray(c, 'L').save(os.path.join(art, tnames[-1]), optimize=True)
        m['team_pack'] = tnames
    files = []
    for cn, c in m['clips'].items():
        files += list(c.pop('files').values())
        if 'team' in c: files += list(c.pop('team').values())
        c['rects'] = {L: rects[cn, L] for (q, L) in rects if q == cn}
    m['pack'] = names
    after = sum(w * h * 4 for w, h in pages)
    return before, after, len(uniq), pages, files

def pack_all(art, units, log=print, keep=False):
    """Pack every unit in `units` (key -> manifest, changed in place) whose strips sit in `art`. Deletes the strips."""
    remove, tb, ta = [], 0, 0
    for key, m in units.items():
        if m.get('pack'): continue
        b, a, n, pages, files = pack_unit(art, key, m)
        remove += files; tb += b; ta += a
        log(f"{key:14} {b / 1048576:7.1f} MB -> {a / 1048576:6.1f} MB   {n:5d} frames kept   pages {' '.join(f'{w}x{h}' for w, h in pages)}")
    if not keep:
        still = {fn for m in units.values() for c in m['clips'].values() for fn in list(c.get('files', {}).values()) + list(c.get('team', {}).values())}
        for fn in set(remove) - still: os.remove(os.path.join(art, fn))
    return tb, ta
