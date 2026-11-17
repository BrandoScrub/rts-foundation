"""artkit.preview: look at exported art the way a game will draw it, from assets.json alone.

  python3 -m artkit.preview <art dir> [out.png]     contact sheet: every still and stage, every unit at 8 headings
  python3 -m artkit.preview <art dir> --gif <key>   animated preview of one unit, every clip at 8 headings
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

GROUND = (98, 104, 78)


def unit_frame(art, man, clip, heading, frame, imgs={}):
    """One frame of a unit (both layers when layered), as RGBA, with the ground anchor at (ax, ay)."""
    c = man['clips'][clip]; heads = man['headings']; h = int(round(heading / 360 * heads)) % heads
    out = None; anchor = None
    for L in (('L', 'U') if 'L' in man['layers'] else ('F',)):
        ly = man['layers'][L]; fw, fh = ly['frame']; ax, ay = ly['anchor']
        cc = c if (c.get('rects', c.get('files', {})).get(L) is not None) else next(
            (man['clips'][k] for k in man['clips'] if L in man['clips'][k].get('rects', man['clips'][k].get('files', {}))), None)
        if cc is None: continue
        fr = min(frame, cc['frames'] - 1)
        cell = np.zeros((fh, fw, 4), np.uint8)
        if 'rects' in cc:
            a = cc['rects'][L]; i = (h * cc['frames'] + fr) * 7; pg, x, y, w, hh, ox, oy = a[i:i + 7]
            if w:
                key = os.path.join(art, man['pack'][pg])
                if key not in imgs: imgs[key] = np.asarray(Image.open(key).convert('RGBA'))
                cell[oy:oy + hh, ox:ox + w] = imgs[key][y:y + hh, x:x + w]
        else:
            key = os.path.join(art, cc['files'][L])
            if key not in imgs: imgs[key] = np.asarray(Image.open(key).convert('RGBA'))
            cell = imgs[key][h * fh:(h + 1) * fh, fr * fw:(fr + 1) * fw]
        im = Image.fromarray(cell, 'RGBA')
        if out is None:
            out = im; anchor = (ax, ay)
        else:
            base = Image.new('RGBA', out.size); base.alpha_composite(out)
            dx, dy = int(round(anchor[0] - ax)), int(round(anchor[1] - ay))
            big = Image.new('RGBA', (max(out.size[0], dx + fw), max(out.size[1], dy + fh)))
            big.alpha_composite(base); big.alpha_composite(im, (max(dx, 0), max(dy, 0))); out = big
    return out, anchor


def contact(art, out_path, zoom=2):
    A = json.load(open(os.path.join(art, 'assets.json')))
    tiles = []
    for key, rec in A.items():
        if rec.get('kind') == 'static':
            for st, m in rec['states'].items():
                im = Image.open(os.path.join(art, m['src'])).convert('RGBA')
                for pv, t in rec.get('turning', {}).items():
                    if st != 'normal': continue
                    strip = Image.open(os.path.join(art, t['src'])).convert('RGBA'); fw, fh = t['frame']
                    fr = strip.crop((0, 0, fw, fh))
                    x = int(round(m['near_corner'][0] - t['near_corner'][0])); y = int(round(m['near_corner'][1] - t['near_corner'][1]))
                    big = Image.new('RGBA', (max(im.size[0], x + fw) - min(0, x), max(im.size[1], y + fh) - min(0, y)))
                    big.alpha_composite(im, (-min(0, x), -min(0, y))); big.alpha_composite(fr, (max(0, x), max(0, y))); im = big
                tiles.append((im, f'{key} {st}' if st != 'normal' else key))
        else:
            clip = 'move' if 'move' in rec['clips'] else ('walk' if 'walk' in rec['clips'] else next(iter(rec['clips'])))
            row = [unit_frame(art, rec, clip, h * 45, 0)[0] for h in range(8)]
            W = sum(i.size[0] for i in row); H = max(i.size[1] for i in row)
            im = Image.new('RGBA', (W, H)); x = 0
            for i in row: im.alpha_composite(i, (x, H - i.size[1])); x += i.size[0]
            tiles.append((im, f'{key} ({clip}, 8 headings)'))
    from .sprite import sheet
    sheet([t[0] for t in tiles], [t[1] for t in tiles], cols=3, bg=GROUND, zoom=zoom).save(out_path)
    return out_path


def gif(art, key, out_path, zoom=2, fps=12, ticks=36):
    A = json.load(open(os.path.join(art, 'assets.json'))); man = A[key]; names = list(man['clips'])
    cells = {}
    for n in names:
        for h in range(8):
            for f in range(man['clips'][n]['frames']):
                cells[n, h, f] = unit_frame(art, man, n, h * 45, f)
    cw = max(c[0].size[0] for c in cells.values()); ch = max(c[0].size[1] for c in cells.values())
    ax = max(c[1][0] for c in cells.values()); ay = max(c[1][1] for c in cells.values())
    frames = []
    for t in range(ticks):
        bg = Image.new('RGBA', (cw * 8, ch * len(names)), GROUND + (255,))
        for r, n in enumerate(names):
            c = man['clips'][n]; f = int(t * c['fps'] / fps)
            f = f % c['frames'] if c['loop'] else min(f % (c['frames'] + 4), c['frames'] - 1)
            for h in range(8):
                im, (a0, a1) = cells[n, h, f]
                bg.alpha_composite(im, (h * cw + int(ax - a0), r * ch + int(ay - a1)))
        frames.append(bg.resize((bg.size[0] * zoom, bg.size[1] * zoom), Image.NEAREST).convert('RGB'))
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0)
    return out_path


if __name__ == '__main__':
    art = sys.argv[1]
    if '--gif' in sys.argv:
        k = sys.argv[sys.argv.index('--gif') + 1]; print(gif(art, k, os.path.join(art, f'preview_{k}.gif')))
    else:
        print(contact(art, sys.argv[2] if len(sys.argv) > 2 else os.path.join(art, 'preview.png')))
