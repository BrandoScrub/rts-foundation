"""artkit.director: checks every exported asset against the style's budget and readability rules.

  python3 -m artkit.director <art dir> <style>          table of every asset, problems listed, exit 1 on any

Checks (limits from style.json "budget", defaults below):
  memory     decoded RGBA the GPU will hold for this asset (pages for packed units, every stage and turning strip)
  size       how tall the asset stands on screen at zoom 1, in game pixels: too small to read means redesign
  contrast   brightness of the asset against the style's ground colour: low contrast hides it in the field
  palette    how far its colours sit from the style palette: high means it will look like it came from another game
  animation  units: moving clips carry a stride (so feet and wheels never slide), firing clips mark their shot
  design     stills exported with critique=True: the design critic's score at play size (artkit.design) and its
             first unmet findings. A prompt to look, not a verdict: it only counts as a problem when the style's
             budget sets min_design_score.
"""
import json, math, os, sys
import numpy as np
from PIL import Image

DEFAULTS = dict(unit_mb=32, static_mb=6, min_unit_px=14, min_static_px=10, min_contrast=14, max_palette_dist=95)


def _lum(rgb): return rgb @ np.array([.299, .587, .114])


def audit(art, style, log=print):
    A = json.load(open(os.path.join(art, 'assets.json')))
    B = dict(DEFAULTS); B.update(style.cfg.get('budget', {}))
    ground = np.array(style.ground, float)
    pal = [c for v in style.palette.values() for c in v] if isinstance(style.palette, dict) else list(style.palette)
    pal = np.array(pal, float) if pal else None
    rows, problems = [], []
    for key, a in A.items():
        files, kind = [], a.get('kind', 'static')
        if kind == 'static':
            files = [m['src'] for m in a['states'].values()] + [t['src'] for t in a.get('turning', {}).values()]
            k = style.building_px_per_out * (0.4 / 0.4)
            main = np.asarray(Image.open(os.path.join(art, a['states']['normal']['src'])).convert('RGBA'))
        else:
            files = a.get('pack') or [f for c in a['clips'].values() for f in c.get('files', {}).values()]
            k = style.figure_k
            main = np.asarray(Image.open(os.path.join(art, files[0])).convert('RGBA'))
        mb = 0
        for f in files:
            with Image.open(os.path.join(art, f)) as im: mb += im.size[0] * im.size[1] * 4 / 1048576
        on = main[..., 3] > 128
        if kind == 'static':
            ys = np.nonzero(on.any(1))[0]; tall = (ys.max() - ys.min() + 1) * k if len(ys) else 0
        else:
            L = a['layers']; tall = max(v['anchor'][1] for v in L.values()) * k
        rgb = main[..., :3][on].astype(float)
        con = abs(_lum(rgb).mean() - _lum(ground)) if len(rgb) else 0
        pd = float(np.sqrt(((rgb[:, None, :] - pal[None]) ** 2).sum(-1)).min(1).mean()) if pal is not None and len(rgb) else 0
        p = []
        if mb > (B['unit_mb'] if kind != 'static' else B['static_mb']): p.append(f'memory {mb:.1f} MB')
        if tall < (B['min_unit_px'] if kind != 'static' else B['min_static_px']): p.append(f'only {tall:.0f} px tall at zoom 1')
        if con < B['min_contrast']: p.append(f'contrast {con:.0f} against the ground')
        if pal is not None and pd > B['max_palette_dist']: p.append(f'colours {pd:.0f} from the palette')
        if kind != 'static':
            for cn, c in a['clips'].items():
                if cn in ('walk', 'run', 'move', 'back') and not c.get('stride_units'): p.append(f'{cn} has no stride')
                if cn == 'fire' and 'fire' not in c.get('events', {}): p.append('fire marks no shot')
        d = a.get('design'); ds = d['score'] if d else None; notes = []
        if d:
            notes = [w.split(':')[0] for ok, w, _ in d['findings'] if not ok]
            if 'min_design_score' in B and ds < B['min_design_score']: p.append(f'design {ds:.0f} (below {B["min_design_score"]})')
            turns = [f['design']['score'] for f in a.get('facings', [])[1:] if 'design' in f]
            if turns: notes.insert(0, 'other sides ' + '/'.join(f'{t:.0f}' for t in turns))
        rows.append((key, kind, mb, tall, con, pd, p, ds, notes))
        problems += [f'{key}: {x}' for x in p]
    log(f"{'asset':16} {'kind':7} {'MB':>6} {'px tall':>8} {'contrast':>9} {'palette':>8} {'design':>7}")
    for key, kind, mb, tall, con, pd, p, ds, notes in rows:
        dcol = f'{ds:7.0f}' if ds is not None else f"{'-':>7}"
        log(f"{key:16} {kind:7} {mb:6.1f} {tall:8.0f} {con:9.0f} {pd:8.0f} {dcol}  {'; '.join(p) or 'ok'}"
            + (f"   design: {', '.join(notes[:4])}" if notes else ''))
    log(f'{len(problems)} problem(s)' if problems else 'all within the style\'s rules')
    return rows, problems


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from artkit.style import Style
    _, pr = audit(sys.argv[1], Style.load(sys.argv[2]))
    sys.exit(1 if pr else 0)
