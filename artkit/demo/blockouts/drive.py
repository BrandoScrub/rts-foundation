"""Drive demo: the M4A3 blockout exported as a unit through the normal exporter (Exporter.rig on a MachineRig), then
drawn the way the browser runtime draws units (runtime/units.js drawFig: shadow layer, legs/hull layer at its anchor,
top layer stood on the socket; frames picked by distance so the tracks never slide), driving north (up the screen),
then north-east, east, south-east, south, south-west, west and north-west. The camera follows the tank over a
scrolling tile grid.

  python3 -m artkit.demo.blockouts.drive <out folder>       writes drive.gif, headings.png and the exported art/

The demo pack is frontier_outpost with three settings a WW2 game's pack would have: an olive-drab hull, a unit camera
with no ground plates ("unit_camera": {"plates": false}: the outline under the tracks is kept and the shadow stays on
the ground) and shadows ("shadow": {}).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from artkit.style import Style
from artkit.export import Exporter
from artkit.demo.blockouts import m4_medium_tank as tank

# screen direction -> world heading (2:1 isometric: +x is down-right on screen, +y down-left)
DIRECTIONS = [('N', 225), ('NE', 270), ('E', 315), ('SE', 0), ('S', 45), ('SW', 90), ('W', 135), ('NW', 180)]
GROUND = (112, 104, 74); GRID = (96, 89, 62)
SCALE = 0.4                    # sprite pixels per unit (the export scale)


def style():
    base = Style.load('frontier_outpost')
    proc = dict(base.cfg['procedural'], hull=[[96, 102, 66], 'metal'], steel=[[74, 78, 62], 'metal'], rubber=[[44, 42, 40], 'leather'])
    return Style(base.root, dict(base.cfg, procedural=proc, unit_camera={'view': 'iso', 'plates': False}, shadow={}))


def export(out):
    rig = tank.rig(headings=8)
    clips = [rig.idle(frames=1), rig.move(frames=6)]
    ex = Exporter(style(), out, log=lambda *a: None)
    man = ex.rig('m4a3', rig, clips)
    ex.save(pack=False)                        # keep strips (the runtime reads packed pages the same way)
    return man


class Unit:
    """Strips + manifest -> cells, placed as runtime/units.js places them."""
    def __init__(s, art, man):
        s.m = man; s.img = {}
        for cn, c in man['clips'].items():
            for L, fn in c['files'].items(): s.img[cn, L] = Image.open(os.path.join(art, fn)).convert('RGBA')

    def cell(s, clip, L, h, f):
        fw, fh = s.m['layers'][L]['frame']
        return s.img[clip, L].crop((f * fw, h * fh, (f + 1) * fw, (h + 1) * fh))

    def draw(s, canvas, clip, h, f, x, y, layer_set=('L', 'U')):
        """drawFig: L at its anchor, U at the legs' socket minus the torso's socket (same clip and frame here)."""
        lay = s.m['layers']; c = s.m['clips'][clip]
        if 'L' in layer_set:
            ax, ay = lay['L']['anchor']; canvas.alpha_composite(s.cell(clip, 'L', h, f), (round(x - ax), round(y - ay)))
        if 'U' in layer_set and 'U' in c['files']:
            a = c['socket'][h][f]; b = a                     # one clip for both layers: the sockets coincide
            ax, ay = lay['U']['anchor']; canvas.alpha_composite(s.cell(clip, 'U', h, f), (round(x + a[0] - b[0] - ax), round(y + a[1] - b[1] - ay)))

    def shadow(s, canvas, clip, h, f, x, y):
        if 'S' not in s.m['layers'] or 'S' not in s.m['clips'][clip]['files']: return
        ax, ay = s.m['layers']['S']['anchor']; canvas.alpha_composite(s.cell(clip, 'S', h, f), (round(x - ax), round(y - ay)))


def ground(W, H, cx, cy, wx, wy):
    """Ground with the tile grid (160 units), the world point (wx, wy) at screen (cx, cy)."""
    im = Image.new('RGBA', (W, H), GROUND + (255,)); d = ImageDraw.Draw(im)
    scr = lambda x, y: (cx + ((x - wx) - (y - wy)) * SCALE, cy + ((x - wx) + (y - wy)) / 2 * SCALE)
    span = 160 * 12; T = 160
    x0 = math.floor((wx - span) / T) * T; y0 = math.floor((wy - span) / T) * T
    for i in range(25):
        x = x0 + i * T; d.line([scr(x, wy - span), scr(x, wy + span)], fill=GRID, width=1)
        y = y0 + i * T; d.line([scr(wx - span, y), scr(wx + span, y)], fill=GRID, width=1)
    return im


def drive(art, man, out_gif, seg_frames=16, speed=7.0, zoom=2):
    u = Unit(art, man); mv = man['clips']['move']; stride = mv['stride_units']; n = mv['frames']
    heads = man['heading_world_deg']
    W, H = 320, 230; cx, cy = W // 2, H // 2 + 16
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
    except OSError: font = ImageFont.load_default()
    frames, wx, wy, dist = [], 0.0, 0.0, 0.0
    for name, deg in DIRECTIONS:
        h = heads.index(float(deg))
        for i in range(seg_frames):
            dist += speed; wx += speed * math.cos(math.radians(deg)); wy += speed * math.sin(math.radians(deg))
            f = int(((dist / stride) % 1) * n) % n                    # by distance: the tracks never slide
            im = ground(W, H, cx, cy, wx, wy)
            u.shadow(im, 'move', h, f, cx, cy); u.draw(im, 'move', h, f, cx, cy)
            ImageDraw.Draw(im).text((8, 6), f'heading {name}', fill=(240, 232, 200, 255), font=font)
            frames.append(im.resize((W * zoom, H * zoom), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=128))
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=1000 // 12, loop=0, optimize=True)
    return len(frames)


def headings_sheet(art, man, out_png, zoom=2):
    """The eight headings standing still, labelled with their screen direction."""
    u = Unit(art, man); heads = man['heading_world_deg']
    cw, ch = 250, 170
    im = Image.new('RGBA', (cw * 4, ch * 2), GROUND + (255,)); d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 12)
    except OSError: font = ImageFont.load_default()
    for k, (name, deg) in enumerate(DIRECTIONS):
        h = heads.index(float(deg)); x, y = (k % 4) * cw + cw // 2, (k // 4) * ch + ch // 2 + 14
        u.shadow(im, 'idle', h, 0, x, y); u.draw(im, 'idle', h, 0, x, y)
        d.text(((k % 4) * cw + 6, (k // 4) * ch + 4), name, fill=(240, 232, 200, 255), font=font)
    im.resize((im.size[0] * zoom, im.size[1] * zoom), Image.NEAREST).save(out_png)


def main(out):
    art = os.path.join(out, 'art'); os.makedirs(art, exist_ok=True)
    man = export(art)
    n = drive(art, man, os.path.join(out, 'drive.gif'))
    headings_sheet(art, man, os.path.join(out, 'headings.png'))
    print(f'wrote {out}/drive.gif ({n} frames), {out}/headings.png, art in {art}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'drive_demo')
