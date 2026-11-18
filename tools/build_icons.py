"""The HUD's icons, one atlas: python3 tools/build_icons.py -> game/art/icons.png, game/art/icons.json
AoE2's command panel, queue and selection panel are pictures, not words. Ours are cut from the game's own art
(units from their sheets, buildings and props from their pictures) so the HUD shows exactly what is on the map;
technologies are the thing they improve with a gold chevron; commands and resources are simple drawn signs.
64 px cells; icons.json maps a key to [column, row]. Run after the unit, building and prop builds."""
import json, math, os, sys
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ART = os.path.join(ROOT, 'game', 'art'); C = 64; SS = 4
GOLD, PALE, RED, GREEN, CYAN = (230, 197, 106), (236, 226, 204), (214, 74, 58), (110, 190, 96), (120, 236, 255)


def tile():
    im = Image.new('RGBA', (C, C)); d = ImageDraw.Draw(im)
    for y in range(C): d.line([(0, y), (C, y)], fill=(int(58 - y * .36), int(46 - y * .3), int(34 - y * .24), 255))
    return im


def fit(src, box=56, top=False):
    b = src.getbbox(); src = src.crop(b); k = min(box / src.size[0], box / src.size[1])
    src = src.resize((max(1, round(src.size[0] * k)), max(1, round(src.size[1] * k))), Image.LANCZOS)
    im = tile(); im.alpha_composite(src, ((C - src.size[0]) // 2, (C - src.size[1]) // 2 if not top else C - 4 - src.size[1])); return im


def unit(key, owner):
    M = json.load(open(os.path.join(ART, 'units.json')))['units'][key]; cw, ch = M['cell']
    fr = Image.open(os.path.join(ART, f'u_{key}_{owner}.png')).convert('RGBA').crop((0, ch, cw, 2 * ch))       # idle, facing the camera
    x0, y0, x1, y1 = fr.getbbox(); side = (y1 - y0) * .66; cx = (x0 + x1) / 2     # head and shoulders: a face-sized picture reads; a whole figure in a button does not
    return fit(fr.crop((int(cx - side / 2), y0, int(cx + side / 2), int(y0 + side))), 60)


def glyph(fn):
    im = Image.new('RGBA', (C * SS, C * SS)); d = ImageDraw.Draw(im); fn(d, lambda *p: [v * SS for v in p]); t = tile(); t.alpha_composite(im.resize((C, C), Image.LANCZOS)); return t


def badge(im, fn):
    o = Image.new('RGBA', (C * SS, C * SS)); d = ImageDraw.Draw(o); fn(d, lambda *p: [v * SS for v in p]); im = im.copy(); im.alpha_composite(o.resize((C, C), Image.LANCZOS)); return im


def chevron(d, S):
    for dy in (0, 9): d.line(S(40, 50 - dy, 49, 41 - dy, 58, 50 - dy), fill=(20, 14, 6), width=7 * SS); d.line(S(40, 50 - dy, 49, 41 - dy, 58, 50 - dy), fill=GOLD, width=4 * SS)
def hammer(d, S):
    d.line(S(40, 58, 54, 40), fill=(20, 14, 6), width=7 * SS); d.line(S(40, 58, 54, 40), fill=(150, 110, 70), width=4 * SS); d.rectangle(S(46, 30, 62, 42), fill=(190, 196, 206), outline=(20, 14, 6), width=SS)
def arrow(d, S, x, y, dx, dy, col, w=5):
    d.line(S(x, y, x + dx, y + dy), fill=col, width=w * SS); L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; ex, ey = x + dx, y + dy
    d.polygon(S(ex + ux * 6, ey + uy * 6, ex - uy * 8 - ux * 4, ey + ux * 8 - uy * 4, ex + uy * 8 - ux * 4, ey - ux * 8 - uy * 4), fill=col)
def sword(d, S, col=PALE, x0=16, y0=50, x1=46, y1=14):
    d.line(S(x0, y0, x1, y1), fill=col, width=6 * SS); d.line(S(x0 + 1, y0 - 13, x0 + 13, y0 - 1), fill=GOLD, width=5 * SS); d.ellipse(S(x0 - 5, y0 - 1, x0 + 1, y0 + 5), fill=GOLD)
def shield(d, S, col=(86, 120, 190), x=32, y=32, r=19):
    d.polygon(S(x - r, y - r, x + r, y - r, x + r, y + 2, x, y + r + 4, x - r, y + 2), fill=col, outline=PALE, width=2 * SS)
def dots(d, S, pts): [d.ellipse(S(x - 4, y - 4, x + 4, y + 4), fill=PALE, outline=(20, 14, 6), width=SS) for x, y in pts]
def bell(d, S):
    d.pieslice(S(16, 12, 48, 52), 180, 360, fill=GOLD); d.rectangle(S(16, 32, 48, 44), fill=GOLD); d.rectangle(S(11, 44, 53, 49), fill=GOLD); d.ellipse(S(28, 48, 36, 56), fill=GOLD); d.rectangle(S(30, 8, 34, 14), fill=GOLD)

G = {
    'c_stop': lambda d, S: (d.regular_polygon((32 * SS, 32 * SS, 22 * SS), 8, rotation=22.5, fill=RED, outline=PALE, width=2 * SS), d.rectangle(S(20, 28, 44, 36), fill=PALE)),
    'c_amove': lambda d, S: (sword(d, S), arrow(d, S, 34, 52, 18, 0, RED)),
    'c_patrol': lambda d, S: (arrow(d, S, 12, 24, 36, 0, PALE), arrow(d, S, 52, 42, -36, 0, PALE)),
    'c_stance_aggressive': lambda d, S: (sword(d, S, PALE, 14, 52, 40, 20), sword(d, S, PALE, 50, 52, 24, 20)),
    'c_stance_defensive': lambda d, S: shield(d, S),
    'c_stance_ground': lambda d, S: (shield(d, S, (120, 110, 96)), d.rectangle(S(30, 20, 34, 44), fill=PALE), d.rectangle(S(22, 44, 42, 48), fill=PALE)),
    'c_stance_passive': lambda d, S: (sword(d, S, (150, 150, 150)), d.ellipse(S(8, 8, 56, 56), outline=RED, width=5 * SS), d.line(S(15, 15, 49, 49), fill=RED, width=5 * SS)),
    'c_formation_line': lambda d, S: dots(d, S, [(x, y) for y in (24, 40) for x in (11, 25, 39, 53)]),
    'c_formation_staggered': lambda d, S: dots(d, S, [(11 + i * 14 + (7 if y == 40 else 0) - 3, y) for y in (24, 40) for i in range(4)]),
    'c_formation_box': lambda d, S: dots(d, S, [(x, y) for y in (14, 32, 50) for x in (14, 32, 50) if (x, y) != (32, 32)]),
    'c_formation_flank': lambda d, S: dots(d, S, [(x, y) for y in (24, 40) for x in (9, 21, 43, 55)]),
    'c_garrison': lambda d, S: (d.rectangle(S(14, 30, 50, 56), fill=(120, 118, 112), outline=PALE, width=2 * SS), [d.rectangle(S(x, 22, x + 8, 30), fill=(120, 118, 112), outline=PALE, width=SS) for x in (14, 28, 42)], d.rectangle(S(27, 40, 37, 56), fill=(20, 14, 6)), arrow(d, S, 32, 4, 0, 14, GREEN)),
    'c_ungarrison': lambda d, S: (d.rectangle(S(14, 30, 50, 56), fill=(120, 118, 112), outline=PALE, width=2 * SS), [d.rectangle(S(x, 22, x + 8, 30), fill=(120, 118, 112), outline=PALE, width=SS) for x in (14, 28, 42)], d.rectangle(S(27, 40, 37, 56), fill=(20, 14, 6)), arrow(d, S, 32, 20, 0, -12, GOLD)),
    'c_delete': lambda d, S: (d.line(S(16, 16, 48, 48), fill=RED, width=8 * SS), d.line(S(48, 16, 16, 48), fill=RED, width=8 * SS)),
    'c_bell': bell,
    'c_allclear': lambda d, S: (bell(d, S), d.line(S(34, 44, 42, 54, 58, 30), fill=(20, 14, 6), width=9 * SS), d.line(S(34, 44, 42, 54, 58, 30), fill=GREEN, width=5 * SS)),
    'c_back': lambda d, S: arrow(d, S, 48, 32, -28, 0, PALE, 7),
    'c_more': lambda d, S: arrow(d, S, 16, 32, 28, 0, PALE, 7),
    'r_wood': lambda d, S: [(d.rounded_rectangle(S(8, y, 52, y + 12), radius=6 * SS, fill=c, outline=(40, 26, 14), width=SS), d.ellipse(S(46, y, 58, y + 12), fill=(214, 178, 122), outline=(40, 26, 14), width=SS)) for y, c in ((36, (120, 78, 42)), (22, (138, 92, 50)), (29 - 21, (120, 78, 42)))][0:2],
    'r_food': lambda d, S: (d.ellipse(S(12, 16, 46, 50), fill=(170, 60, 44), outline=(60, 20, 14), width=2 * SS), d.line(S(40, 22, 54, 10), fill=PALE, width=6 * SS), d.ellipse(S(50, 4, 60, 14), fill=PALE)),
    'r_iron': lambda d, S: (d.polygon(S(10, 44, 20, 24, 50, 24, 56, 44), fill=(110, 124, 150), outline=(30, 34, 44), width=2 * SS), d.polygon(S(20, 24, 26, 16, 54, 16, 50, 24), fill=(160, 174, 198), outline=(30, 34, 44), width=SS)),
    'r_stone': lambda d, S: (d.polygon(S(10, 46, 12, 26, 30, 16, 52, 22, 56, 44, 34, 52), fill=(168, 164, 154), outline=(60, 58, 54), width=2 * SS), d.line(S(12, 26, 34, 32, 52, 22), fill=(210, 206, 196), width=2 * SS), d.line(S(34, 32, 34, 52), fill=(110, 108, 100), width=2 * SS)),
    'r_crystal': lambda d, S: (d.polygon(S(32, 6, 46, 30, 32, 58, 18, 30), fill=CYAN, outline=(20, 80, 100), width=2 * SS), d.polygon(S(32, 6, 32, 58, 18, 30), fill=(70, 190, 220))),
    'r_pop': lambda d, S: (d.ellipse(S(22, 10, 42, 30), fill=PALE), d.pieslice(S(10, 30, 54, 76), 180, 360, fill=PALE)),
    's_attack': lambda d, S: sword(d, S),
    's_armor': lambda d, S: shield(d, S),
    's_pierce': lambda d, S: (shield(d, S, (120, 110, 96)), arrow(d, S, 54, 10, -22, 22, PALE, 4)),
    's_range': lambda d, S: (d.arc(S(-6, 8, 42, 56), -70, 70, fill=(170, 120, 70), width=5 * SS), d.line(S(26, 10, 26, 54), fill=PALE, width=SS), arrow(d, S, 22, 32, 30, 0, PALE, 3)),
    's_los': lambda d, S: (d.ellipse(S(8, 18, 56, 46), fill=PALE, outline=(20, 14, 6), width=2 * SS), d.ellipse(S(22, 22, 42, 42), fill=(60, 90, 140)), d.ellipse(S(28, 28, 36, 36), fill=(10, 10, 10))),
    's_speed': lambda d, S: (arrow(d, S, 10, 32, 34, 0, PALE, 6), d.line(S(8, 18, 26, 18), fill=PALE, width=3 * SS), d.line(S(8, 46, 26, 46), fill=PALE, width=3 * SS)),
    's_garrison': lambda d, S: (d.rectangle(S(14, 30, 50, 56), fill=(120, 118, 112), outline=PALE, width=2 * SS), [d.rectangle(S(x, 22, x + 8, 30), fill=(120, 118, 112), outline=PALE, width=SS) for x in (14, 28, 42)], d.rectangle(S(27, 40, 37, 56), fill=(20, 14, 6))),
    'm_techtree': lambda d, S: ([d.line(S(32, 16, x, 44), fill=GOLD, width=3 * SS) for x in (14, 32, 50)], [d.rectangle(S(x - 8, y - 7, x + 8, y + 7), fill=(86, 120, 190), outline=PALE, width=SS) for x, y in ((32, 14), (14, 46), (32, 46), (50, 46))]),
    'm_settings': lambda d, S: ([d.rectangle(S(29, 6, 35, 58), fill=PALE) for _ in (0,)], d.rectangle(S(6, 29, 58, 35), fill=PALE), d.line(S(14, 14, 50, 50), fill=PALE, width=6 * SS), d.line(S(50, 14, 14, 50), fill=PALE, width=6 * SS), d.ellipse(S(14, 14, 50, 50), fill=PALE), d.ellipse(S(24, 24, 40, 40), fill=(40, 30, 22))),
    'm_menu': lambda d, S: [d.rounded_rectangle(S(12, y, 52, y + 8), radius=3 * SS, fill=PALE) for y in (14, 28, 42)],
    'm_mode': lambda d, S: (d.polygon(S(32, 12, 58, 32, 32, 52, 6, 32), fill=(70, 110, 60), outline=PALE, width=2 * SS), d.ellipse(S(18, 28, 26, 36), fill=(90, 140, 240)), d.ellipse(S(38, 28, 46, 36), fill=RED)),
}
for n, num in ((1, 'I'), (2, 'II'), (3, 'III')):
    def age(d, S, num=num):
        shield(d, S, (120, 40, 34) if num == 'I' else (60, 90, 150) if num == 'II' else (150, 120, 40), 32, 30, 22)
        w = 6 * len(num) + 4 * (len(num) - 1); x = 32 - w / 2
        for ch in num: d.rectangle(S(x, 16, x + 6, 44), fill=GOLD); x += 10
        d.rectangle(S(32 - w / 2 - 3, 14, 32 + w / 2 + 3, 18), fill=GOLD); d.rectangle(S(32 - w / 2 - 3, 42, 32 + w / 2 + 3, 46), fill=GOLD)
    G[f'age_{n}'] = age

TECH = {'loom': ('u', 'villager'), 'feudal': 'age_2', 'castle': 'age_3', 'wheelbarrow': ('u', 'villager_hoe'), 'town_watch': ('b', 'watchpost'), 'horse_collar': ('b', 'farm'), 'double_bit_axe': ('p', 'tree_0'),
        'ore_mining': ('p', 'iron_0'), 'stone_mining': ('p', 'stone_0'), 'man_at_arms': ('u', 'militia_maa'), 'supplies': ('u', 'militia'), 'bloodlines': ('u', 'scout'), 'forging': ('g', 's_attack'),
        'scale_mail': ('g', 's_armor'), 'scale_barding': ('u', 'scout'), 'fletching': ('g', 's_range'), 'padded_archer': ('u', 'archer'),
        # Castle Age: stand-ins from what exists until the Castle Age art is made
        'hand_cart': ('u', 'villager_hoe'), 'town_patrol': ('b', 'watchpost'), 'heavy_plow': ('b', 'farm'), 'bow_saw': ('p', 'tree_0'), 'ore_shaft': ('p', 'iron_0'), 'stone_shaft': ('p', 'stone_0'),
        'iron_casting': ('g', 's_attack'), 'chain_mail': ('g', 's_armor'), 'chain_barding': ('u', 'scout'), 'bodkin': ('g', 's_range'), 'leather_archer': ('u', 'archer'),
        'long_swordsman': ('u', 'militia_maa'), 'pikeman': ('u', 'spearman'), 'squires': ('g', 's_speed'), 'arson': ('b', 'barracks'), 'gambesons': ('g', 's_pierce'),
        'crossbow': ('u', 'archer'), 'elite_skirmisher': ('u', 'skirmisher'), 'thumb_ring': ('g', 's_range'), 'light_cavalry': ('u', 'scout'), 'husbandry': ('g', 's_speed'),
        'sanctity': ('u', 'monk'), 'fervor': ('u', 'monk'), 'redemption': ('b', 'monastery'), 'atonement': ('u', 'monk'), 'herbal_medicine': ('g', 's_garrison'), 'heresy': ('g', 'c_delete'),
        'masonry': ('b', 'town_hall'), 'fortified_wall': ('b', 'stone_wall'), 'ballistics': ('g', 's_range'), 'guard_tower': ('b', 'watch_tower'), 'murder_holes': ('b', 'watch_tower'), 'treadmill_crane': ('g', 'c_build_eco')}

STONE, SLATE, WOODC, DARK = (150, 146, 136), (62, 76, 94), (132, 96, 58), (20, 14, 6)
def diamond(col):
    return lambda d, S: d.polygon(S(50, 4, 58, 13, 50, 22, 42, 13), fill=col, outline=DARK, width=2 * SS)
def wheels(d, S, y=48): [d.ellipse(S(x - 7, y - 7, x + 7, y + 7), fill=(74, 51, 32), outline=DARK, width=2 * SS) for x in (18, 46)]
# stand-in pictures for what has no art yet (the Castle Age): simple drawn signs, like the command glyphs
G.update({
    'b_castle': lambda d, S: (d.rectangle(S(12, 26, 52, 54), fill=STONE, outline=DARK, width=2 * SS), [d.rectangle(S(x, 14, x + 12, 54), fill=(168, 164, 154), outline=DARK, width=2 * SS) for x in (6, 46)],
                              [d.polygon(S(x - 2, 14, x + 6, 4, x + 14, 14), fill=SLATE, outline=DARK, width=SS) for x in (6, 46)], d.rectangle(S(27, 38, 37, 54), fill=DARK), d.polygon(S(32, 8, 37, 16, 32, 24, 27, 16), fill=CYAN)),
    'b_monastery': lambda d, S: (d.rectangle(S(10, 32, 54, 54), fill=STONE, outline=DARK, width=2 * SS), d.polygon(S(6, 32, 32, 16, 58, 32), fill=SLATE, outline=DARK, width=2 * SS), d.rectangle(S(26, 12, 38, 34), fill=(168, 164, 154), outline=DARK, width=SS),
                                 d.polygon(S(32, 2, 37, 9, 32, 16, 27, 9), fill=CYAN), d.rectangle(S(28, 40, 36, 54), fill=DARK)),
    'b_university': lambda d, S: (d.rectangle(S(8, 28, 56, 54), fill=STONE, outline=DARK, width=2 * SS), d.pieslice(S(18, 8, 46, 44), 180, 360, fill=SLATE, outline=DARK, width=2 * SS), [d.rectangle(S(x, 32, x + 5, 54), fill=(190, 186, 176)) for x in (13, 24, 35, 46)],
                                  d.ellipse(S(28, 2, 36, 10), fill=CYAN)),
    'b_siege_workshop': lambda d, S: (d.rectangle(S(8, 34, 56, 54), fill=WOODC, outline=DARK, width=2 * SS), d.polygon(S(4, 34, 32, 20, 60, 34), fill=(84, 62, 40), outline=DARK, width=2 * SS), d.line(S(22, 50, 44, 14), fill=DARK, width=6 * SS),
                                      d.line(S(22, 50, 44, 14), fill=(170, 130, 84), width=3 * SS), d.ellipse(S(39, 7, 51, 19), fill=STONE, outline=DARK, width=SS)),
    'u_ram': lambda d, S: (d.polygon(S(8, 42, 32, 14, 56, 42), fill=WOODC, outline=DARK, width=2 * SS), d.line(S(14, 38, 60, 38), fill=DARK, width=8 * SS), d.line(S(14, 38, 58, 38), fill=(96, 68, 40), width=5 * SS),
                           d.ellipse(S(52, 32, 63, 44), fill=(140, 154, 178), outline=DARK, width=SS), wheels(d, S)),
    'u_mangonel': lambda d, S: (d.rectangle(S(10, 38, 54, 46), fill=WOODC, outline=DARK, width=2 * SS), d.line(S(34, 40, 16, 12), fill=DARK, width=7 * SS), d.line(S(34, 40, 16, 12), fill=(170, 130, 84), width=4 * SS),
                                d.ellipse(S(8, 4, 24, 20), fill=STONE, outline=DARK, width=2 * SS), wheels(d, S)),
    'u_scorpion': lambda d, S: (d.rectangle(S(12, 38, 52, 46), fill=WOODC, outline=DARK, width=2 * SS), d.arc(S(24, 6, 64, 46), 110, 250, fill=(170, 130, 84), width=5 * SS), d.line(S(8, 26, 56, 26), fill=CYAN, width=4 * SS),
                                d.polygon(S(56, 20, 63, 26, 56, 32), fill=CYAN), wheels(d, S)),
})
STAND = {'u_knight': ('u_scout', (216, 220, 228)), 'u_cavarcher': ('u_scout', (111, 208, 138)), 'u_monk': ('u_villager', (98, 224, 255))}   # borrowed figures, marked with the diamond the game draws over them


def main():
    icons = {}
    U = json.load(open(os.path.join(ART, 'units.json')))['units']
    for k, m in U.items(): icons['u_' + k] = unit(k, m['players'][0])
    B = json.load(open(os.path.join(ART, 'buildings.json')))['buildings']
    for k in B:
        if not any(k.endswith(s) for s in ('_x', '_y', '_d1', '_d2')) and not k.startswith(('site', 'rubble')): icons['b_' + k] = fit(Image.open(os.path.join(ART, f'b_{k}_0.png')).convert('RGBA'))
    for k in json.load(open(os.path.join(ART, 'props.json'))): icons['p_' + k] = fit(Image.open(os.path.join(ART, f'p_{k}.png')).convert('RGBA'))
    for k, fn in G.items():
        if k not in icons: icons[k] = glyph(fn)   # real art, once it exists, wins over a drawn stand-in
    for k, (src, col) in STAND.items():
        if k not in icons: icons[k] = badge(icons[src], diamond(col))
    icons['c_build_eco'] = badge(icons['b_cottage'], hammer); icons['c_build_mil'] = badge(icons['b_barracks'], hammer); icons['c_pickup'] = icons['p_relic']
    icons['r_idle'] = icons['u_villager']
    for r in ('food', 'wood', 'stone'):
        icons['c_buy_' + r] = badge(icons['r_' + r], lambda d, S: arrow(d, S, 50, 34, 0, 16, GREEN, 6)); icons['c_sell_' + r] = badge(icons['r_' + r], lambda d, S: arrow(d, S, 50, 56, 0, -16, GOLD, 6))
    for t, src in TECH.items():
        base = icons[src] if isinstance(src, str) else icons[{'u': 'u_', 'b': 'b_', 'p': 'p_', 'g': ''}[src[0]] + src[1]]
        icons['t_' + t] = base if isinstance(src, str) else badge(base, chevron)
    keys = sorted(icons); cols = 16; rows = -(-len(keys) // cols)
    atlas = Image.new('RGBA', (cols * C, rows * C)); meta = {}
    for i, k in enumerate(keys): atlas.paste(icons[k], ((i % cols) * C, (i // cols) * C)); meta[k] = [i % cols, i // cols]
    atlas.save(os.path.join(ART, 'icons.png'), optimize=True)
    json.dump({'cell': C, 'cols': cols, 'rows': rows, 'icons': meta}, open(os.path.join(ART, 'icons.json'), 'w'))
    print(len(keys), 'icons', atlas.size); return 0


if __name__ == '__main__': sys.exit(main())
