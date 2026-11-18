"""Readability checks on the game's own art, at the size it is played:  python3 tools/readability_check.py [out.png]
The checks (docs/readability.md lists the sources):
  1 SILHOUETTE  each unit as a black shape, facing the camera, at play size: is it told apart from every other?
                Measured: overlap (intersection over union) of every pair of silhouettes standing on the same spot.
  2 SQUINT      the figure blurred on the ground: two or three blocks of colour, and it must not sink into the grass.
                Measured: contrast ratio (WCAG relative luminance) between the figure and the ground it stands on.
  3 VALUE       the same in grey: readability must survive without hue.
  4 PLAYER COLOUR  share of the figure in the owner's colour, and where it sits (a different place on each unit).
Prints a table and FAIL lines; writes a sheet with the four rows for looking at. Exit 1 if anything fails."""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); ART = os.path.join(ROOT, 'game', 'art')
PLAY = 0.575                      # sheet px -> screen px at zoom 1 (render.js draws units at this scale)
IOU_MAX, CONTRAST_MIN, TEAM_MIN = 0.60, 1.5, 0.15   # overlap averaged over three headings; WCAG asks 3:1 for a sign, a figure is many values so its mean is held to half that
SAME_BEAST = {('scout', 'wolf')}
REALM = ['villager', 'militia', 'militia_maa', 'spearman', 'archer', 'skirmisher', 'scout']
WILD = ['goblin', 'ogre', 'wolf', 'boar', 'deer', 'sheep']


def lum(rgb):
    c = np.asarray(rgb, float) / 255; c = np.where(c <= .03928, c / 12.92, ((c + .055) / 1.055) ** 2.4); return c @ np.array([.2126, .7152, .0722])


def frame(key, owner, row=1):
    M = json.load(open(os.path.join(ART, 'units.json')))['units'][key]; cw, ch = M['cell']; k = PLAY * M.get('draw', .575) / .575
    im = Image.open(os.path.join(ART, f'u_{key}_{owner}.png')).convert('RGBA').crop((0, row * ch, cw, (row + 1) * ch))
    im = im.resize((round(cw * k), round(ch * k)), Image.LANCZOS); return im, (M['origin'][0] * k, M['origin'][1] * k)


def place(im, o, W=96, H=96):
    out = Image.new('RGBA', (W, H)); out.alpha_composite(im, (round(W / 2 - o[0]), round(H - 14 - o[1]))); return out


def main():
    ground = np.asarray(Image.open(os.path.join(ART, 'ground_realm_grass.jpg')).convert('RGB')).reshape(-1, 3).mean(0) if os.path.exists(os.path.join(ART, 'ground_realm_grass.jpg')) else np.array([52, 74, 40])
    names = REALM + WILD; cells = {}; rows = []; bad = []
    for k in names:
        own = '0' if k in REALM else '2'; im, o = frame(k, own); c = place(im, o); cells[k] = c
        a = np.asarray(c).astype(float); m = a[..., 3] > 200; rgb = a[m][:, :3]
        L = lum(rgb).mean(); Lg = lum(ground); cr = (max(L, Lg) + .05) / (min(L, Lg) + .05)
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]; team = ((b > r * 1.35) & (b > g * 1.12) & (b > 70)).mean() if k in REALM else float('nan')
        rows.append((k, int(m.sum()), cr, team))
        if cr < CONTRAST_MIN: bad.append(f'FAIL contrast {k}: {cr:.2f} against the grass (min {CONTRAST_MIN})')
        if k in REALM and team < TEAM_MIN: bad.append(f'FAIL player colour {k}: {team:.0%} of the figure (min {TEAM_MIN:.0%})')
    print(f'{"unit":14}{"pixels":>8}{"contrast":>10}{"player colour":>15}')
    for k, n, cr, t in rows: print(f'{k:14}{n:8}{cr:10.2f}{"" if t != t else f"{t:14.0%}"}')
    mask = {k: np.asarray(cells[k])[..., 3] > 128 for k in names}
    M3 = {k: [np.asarray(place(*frame(k, '0' if k in REALM else '2', r)))[..., 3] > 128 for r in (0, 1, 2)] for k in names}; print('\nsilhouette overlap (IoU, mean of three headings), pairs above 0.5:')
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            iou = float(np.mean([(x & y).sum() / max(1, (x | y).sum()) for x, y in zip(M3[a], M3[b])]))
            if iou > .5: print(f'  {a:12} {b:12} {iou:.2f}')
            if (a, b) in SAME_BEAST: continue          # a Wolf Rider sits on a dire wolf: the mount is meant to be the same animal; the rider, lance and owner's colour tell them apart
            if iou > IOU_MAX: bad.append(f'FAIL silhouette {a} / {b}: {iou:.2f} alike (max {IOU_MAX})')
    Z = 3; W = 96; sheet = Image.new('RGB', (W * len(names) * Z // 1, 4 * 96 * Z), tuple(int(v) for v in ground))
    for i, k in enumerate(names):
        c = cells[k]; sil = Image.new('RGBA', c.size, (0, 0, 0, 0)); sil.paste((0, 0, 0, 255), mask=c.split()[3].point(lambda v: 255 if v > 128 else 0))
        on = Image.new('RGB', c.size, tuple(int(v) for v in ground)); on.paste(c, mask=c.split()[3])
        for r, im in enumerate((sil, on.filter(ImageFilter.GaussianBlur(2.2)), on.convert('L').convert('RGB'), on)):
            big = im.resize((W * Z, 96 * Z), Image.NEAREST if r != 1 else Image.BILINEAR)
            if r == 0: bg = Image.new('RGB', big.size, (200, 196, 184)); bg.paste(big, mask=big.split()[3]); big = bg
            sheet.paste(big.convert('RGB'), (i * W * Z, r * 96 * Z))
    # 5 TEXT: every text colour of the HUD against the panels it sits on (WCAG 2.x: 4.5:1 for text, 3:1 for large text and signs)
    import re
    css = open(os.path.join(ROOT, 'game', 'index.html')).read(); var = dict(re.findall(r'--(\w+): (#[0-9a-fA-F]{6})', css))
    hx = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    print('\ntext contrast on the HUD:')
    for name, fg, bg in (('text on panel', var['text'], var['panel']), ('dim text on panel', var['dim'], var['panel']), ('gold headings on panel', var['gold'], var['panel']),
                         ('tooltip text', var['text'], '#120d07'), ('"Strong against"', '#9be28c', '#120d07'), ('"Weak against"', '#ffab94', '#120d07'), ('warning note', '#ffcf8a', '#120d07'),
                         ('hit points on the bar', '#ffffff', '#2e7d32'), ('hotkey letter', '#ffffff', '#000000')):
        a_, b_ = lum(hx(fg)), lum(hx(bg)); cr = (max(a_, b_) + .05) / (min(a_, b_) + .05); print(f'  {name:24}{cr:6.1f}:1')
        if cr < 4.5: bad.append(f'FAIL text {name}: {cr:.1f}:1 (min 4.5:1)')
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs', 'blockouts', 'readability.png'); sheet.save(out)
    print(); print('\n'.join(bad) if bad else 'ALL PASS'); return 1 if bad else 0


if __name__ == '__main__': sys.exit(main())
