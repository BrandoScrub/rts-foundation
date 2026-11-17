"""artkit.decals: small RGBA pictures stretched over one face (windows, doors, signs). Style packs add their own
as PNGs in <style>/decals/."""
import math
from PIL import Image, ImageDraw


def generic():
    """Decals any style can use: windows, lit windows, doors, clock, gauge, wire, blade, slit, shutter, boards, hazard stripes."""
    d = {}
    im = Image.new('RGBA', (48, 60), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 47, 59], fill=(78, 74, 66, 255)); dr.rectangle([4, 4, 43, 55], fill=(26, 28, 32, 255))
    dr.rectangle([6, 6, 22, 28], fill=(42, 48, 56, 255)); dr.line([24, 4, 24, 55], fill=(78, 74, 66, 255), width=3)
    dr.line([4, 30, 43, 30], fill=(78, 74, 66, 255), width=3); dr.rectangle([0, 56, 47, 59], fill=(150, 146, 138, 255))
    d['window'] = im
    im = Image.new('RGBA', (48, 60), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rectangle([6, 6, 22, 28], fill=(240, 200, 110, 255)); dr.rectangle([25, 6, 43, 28], fill=(230, 180, 90, 255))
    dr.rectangle([6, 32, 22, 55], fill=(225, 170, 80, 255)); dr.rectangle([25, 32, 43, 55], fill=(235, 190, 100, 255))
    d['window_lit'] = im
    im = Image.new('RGBA', (52, 100), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 51, 99], fill=(70, 66, 58, 255)); dr.rectangle([5, 5, 46, 99], fill=(34, 30, 26, 255))
    dr.rectangle([9, 9, 42, 99], fill=(52, 42, 32, 255)); dr.ellipse([34, 48, 40, 54], fill=(190, 160, 70, 255))
    d['door'] = im
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.ellipse([2, 2, 61, 61], fill=(220, 214, 196, 255), outline=(120, 100, 60, 255), width=3)
    for i in range(12):
        a = i * math.pi / 6; dr.line([32 + 24 * math.sin(a), 32 - 24 * math.cos(a), 32 + 27 * math.sin(a), 32 - 27 * math.cos(a)], fill=(40, 36, 30, 255), width=2)
    dr.line([32, 32, 32, 12], fill=(30, 26, 22, 255), width=3); dr.line([32, 32, 46, 38], fill=(30, 26, 22, 255), width=3)
    d['clock'] = im
    im = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for y in range(8, 256, 24):
        dr.line([0, y, 255, y], fill=(60, 58, 54, 255), width=2)
        for x in range(0, 256, 18): dr.line([x, y - 5, x + 8, y + 5], fill=(60, 58, 54, 255), width=2)
    d['wire'] = im
    im = Image.new('RGBA', (64, 256), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.polygon([(28, 0), (36, 0), (50, 200), (40, 256), (24, 256), (14, 200)], fill=(170, 166, 150, 255))
    d['blade'] = im
    im = Image.new('RGBA', (48, 48), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.ellipse([0, 0, 47, 47], fill=(196, 160, 80, 255)); dr.ellipse([5, 5, 42, 42], fill=(232, 226, 206, 255))
    for i in range(9):
        a = math.radians(-220 + i * 27.5); dr.line([24 + 14 * math.cos(a), 24 + 14 * math.sin(a), 24 + 17 * math.cos(a), 24 + 17 * math.sin(a)], fill=(40, 36, 30, 255), width=2)
    dr.pieslice([5, 5, 42, 42], -10, 20, fill=(200, 60, 40, 255))
    dr.line([24, 24, 24 + 15 * math.cos(math.radians(-120)), 24 + 15 * math.sin(math.radians(-120))], fill=(30, 26, 22, 255), width=2)
    d['gauge'] = im
    # ---- war decals (Nov 9 2026, Command Hall) ----
    im = Image.new('RGBA', (48, 24), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)       # window filled with concrete, one firing slit
    dr.rectangle([0, 0, 47, 23], fill=(118, 116, 108, 255)); dr.rectangle([0, 0, 47, 2], fill=(92, 90, 84, 255))
    dr.rectangle([6, 9, 41, 15], fill=(52, 50, 46, 255)); dr.rectangle([8, 10, 39, 14], fill=(14, 14, 16, 255))
    d['slit'] = im
    im = Image.new('RGBA', (48, 60), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)       # steel blast shutter with a vision slot
    dr.rectangle([0, 0, 47, 59], fill=(46, 46, 44, 255)); dr.rectangle([3, 3, 44, 55], fill=(122, 126, 120, 255))
    dr.rectangle([3, 3, 44, 6], fill=(146, 150, 142, 255)); dr.rectangle([9, 20, 38, 25], fill=(12, 12, 14, 255))
    for x, y in ((7, 9), (40, 9), (7, 50), (40, 50)): dr.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(70, 66, 56, 255))
    dr.rectangle([0, 56, 47, 59], fill=(150, 146, 138, 255))
    d['shutter'] = im
    im = Image.new('RGBA', (48, 60), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)       # boarded-up window
    dr.rectangle([0, 0, 47, 59], fill=(78, 74, 66, 255)); dr.rectangle([4, 4, 43, 55], fill=(20, 20, 22, 255))
    for y0, y1, c in ((10, 4, (112, 88, 62)), (26, 30, (98, 78, 56)), (44, 40, (118, 94, 66))):
        dr.polygon([(0, y0), (47, y1), (47, y1 + 8), (0, y0 + 8)], fill=c + (255,))
    dr.rectangle([0, 56, 47, 59], fill=(150, 146, 138, 255))
    d['boards'] = im
    def hazard(w, h, vertical):
        im = Image.new('RGBA', (w, h), (232, 184, 48, 255)); dr = ImageDraw.Draw(im); k = 10
        for o in range(-max(w, h) * 2, max(w, h) * 2, 2 * k):
            dr.polygon([(o, 0), (o + k, 0), (o + k + h, h), (o + h, h)] if not vertical else [(0, o), (0, o + k), (w, o + k + w), (w, o + w)], fill=(28, 26, 24, 255))
        return im
    d['hazard_v'] = hazard(14, 112, True); d['hazard_h'] = hazard(112, 14, False)
    return d
