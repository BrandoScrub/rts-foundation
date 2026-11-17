"""Frontier Outpost: a second game's art set, built only from a style pack, recipes and rigs, to prove artkit is not
tied to Brass and Bone. Nothing here is special-cased in the engine.

  python3 -m artkit.demo.frontier.build [out dir]     buildings (with stages and turning parts), terrain, units
"""
import glob, math, os, sys, time
import numpy as np

from artkit import Style, Geometry, shapes as sh, library as lib
from artkit.recipe import Asset
from artkit.rig import Rig
from artkit.export import Exporter

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- units
def rover():
    """Six-wheeled survey rover with a small twin-gun turret. Hull and wheels are the bottom layer."""
    r = Rig('rover')
    r.joint('body', 'root', (0, 0, 24))
    hull = (sh.block(-52, 44, -22, 22, 0, 18, 'hull') + sh.block(-52, 44, -23, 23, 2, 6, 'orange', wear=False)
            + sh.wedge(26, 40, 14, 'hull').rz(-90).move(18, 20, 18) + sh.block(-48, 4, -20, 20, 18, 30, 'panel')
            + sh.quad((4.2, -16, 20), (0, 32, 0), (0, 0, 8), 'glass', emit=True) + sh.block(-60, -52, -12, 12, 4, 16, 'plating'))
    r.attach('body', hull)
    for n, (x, y) in dict(f_l=(30, 26), f_r=(30, -26), m_l=(-4, 26), m_r=(-4, -26), b_l=(-38, 26), b_r=(-38, -26)).items():
        r.wheel(n, 'body', (x, y, -6), 15, mat='rubber', hub='plating', width=11, spokes=5)
    r.joint('turret', 'body', (-20, 0, 30), upper=True)
    r.attach('turret', sh.prism(13, 9, 'plating', n=8) + sh.block(-8, 8, -9, 9, 9, 15, 'hull'))
    r.joint('guns', 'turret', (6, 0, 12))
    r.attach('guns', sh.cyl((0, 4, 0), (30, 4, 0), 2.2, 'dark').flat() + sh.cyl((0, -4, 0), (30, -4, 0), 2.2, 'dark').flat())
    r.muzzle('guns', (32, 0, 0))
    return r, [r.idle(frames=4), r.roll(frames=6), r.fire(recoil=('guns', 4))]


def strider():
    """Four-legged walker: a pod on spider legs (knees up and out), gun pod on top that aims on its own."""
    r = Rig('strider')
    r.joint('body', 'root', (0, 0, 58))
    pod = (sh.ellipsoid(34, 28, 16, 'hull', seg=12, rings=7) + sh.ellipsoid(35, 29, 4, 'orange', at=(0, 0, -2), seg=12, rings=3)
           + sh.ellipsoid(8, 18, 6, 'plating', at=(0, 0, -15), seg=8, rings=4))
    r.attach('body', pod)
    for n, (x, y) in dict(fl=(1, 1), fr=(1, -1), bl=(-1, 1), br=(-1, -1)).items():
        hip = (x * 20, y * 16, -4); home = (x * 56, y * 52)
        thigh = sh.cyl((0, 0, 0), (0, 0, -46), 4.2, 'plating', 3.2, seg=8)
        shin = sh.cyl((0, 0, 0), (0, 0, -54), 3.4, 'hull', 2.0, seg=8) + sh.ellipsoid(5, 5, 4, 'dark', at=(0, 0, 0), seg=8, rings=4)
        r.leg(n, 'body', hip, home, 46, 54, knee=(x * .5, y * .7, 1.0), thigh=thigh, shin=shin,
              foot=sh.ellipsoid(6, 6, 3, 'dark', at=(0, 0, 2), seg=8, rings=3))
    r.joint('gun', 'body', (2, 0, 16), upper=True)
    r.attach('gun', sh.ellipsoid(14, 12, 8, 'plating', at=(0, 0, 4), seg=10, rings=5) + sh.cyl((6, 0, 6), (40, 0, 6), 3, 'dark')
             + sh.ellipsoid(4, 4, 4, 'glass', at=(12, 0, 12), seg=8, rings=4).glow())
    r.joint('barrel', 'gun', (0, 0, 0)); r.muzzle('gun', (42, 0, 6))
    walk = r.walk(stride=64, frames=12, duty=.62, lift=14)
    return r, [r.idle(frames=6), walk, r.fire()]


def crawler():
    """Tracked crawler with a heavy turret."""
    r = Rig('crawler')
    r.joint('body', 'root', (0, 0, 0))
    hull = (sh.block(-48, 40, -24, 24, 14, 34, 'hull') + sh.wedge(48, 22, 12, 'hull').rz(-90).move(40, 24, 34).scaled(1, 1, 1)
            + sh.block(-48, 40, -25, 25, 22, 26, 'orange', wear=False) + sh.block(-58, -48, -16, 16, 16, 30, 'plating'))
    r.attach('body', hull)
    for side, y in (('l', 30), ('r', -30)):
        r.track('track_' + side, 'body', (-40, y, 14), (38, y, 14), 13, width=14, mat='rubber', wheel_mat='plating', pitch=8)
        r.attach('body', sh.block(-46, 44, y - 8, y + 8, 26, 29, 'plating', wear=False))
    r.joint('turret', 'body', (-6, 0, 34), upper=True)
    r.attach('turret', sh.prism(20, 12, 'hull', n=8) + sh.block(-14, 14, -16, 16, 12, 18, 'plating') + sh.block(-24, -14, -10, 10, 2, 14, 'panel'))
    r.joint('cannon', 'turret', (16, 0, 8))
    r.attach('cannon', sh.cyl((0, 0, 0), (46, 0, 0), 4, 'dark').flat() + sh.cyl((40, 0, 0), (50, 0, 0), 5.5, 'plating').flat())
    r.muzzle('cannon', (52, 0, 0))
    return r, [r.idle(frames=4), r.roll(frames=4), r.fire(recoil=('cannon', 7))]


def drone():
    """Quad-rotor scout. Hovers; rotors spin in every clip."""
    r = Rig('drone')
    r.joint('body', 'root', (0, 0, 70))
    body = sh.ellipsoid(16, 12, 7, 'hull', seg=10, rings=5) + sh.ellipsoid(6, 6, 4, 'glass', at=(13, 0, -2), seg=8, rings=4).glow()
    for a in (45, 135, 225, 315):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        body = body + sh.cyl((c * 8, s * 8, 0), (c * 30, s * 30, 2), 2, 'plating').flat() + sh.prism(4, 6, 'orange', n=8).move(c * 30, s * 30, 0)
    r.attach('body', body)
    for i, a in enumerate((45, 135, 225, 315)):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        r.rotor(f'rotor{i}', 'body', (c * 30, s * 30, 6), 15, blades=2, mat='dark', hub='plating')
    move = r.roll(frames=4); move.stride = 40.0
    return r, [r.idle(frames=4, bob=3), move]


# ---------------------------------------------------------------- terrain
def terrain():
    out = {}
    out['crater'] = Asset({'name': 'Crater', 'footprint': [2, 2], 'build': lambda: sh.heightfield(
        (lambda f: (lambda x, y: f(x - 160, y - 160)))(sh.crater(120, 44, rim=.35, seed=4)), 320, 320, 12,
        {'ground': 'regolith', 'steep': 'basalt'}, steep=.55)})
    def mesa():
        nz = sh._noise2(9)
        def fn(x, y):
            d = max(abs(x - 160) / 130, abs(y - 160) / 110) + .12 * float(nz(x, y, 60))
            return 70 * (1 / (1 + math.exp((d - .72) * 22)))
        return sh.heightfield(fn, 320, 320, 10, {'ground': 'regolith', 'steep': 'basalt', 'high': 'basalt'}, steep=.8, high=60)
    out['mesa'] = Asset({'name': 'Mesa', 'footprint': [2, 2], 'build': mesa})
    def boulders():
        return sh.scatter(lambda i, rng: sh.rock(26 + 30 * rng.random(), 'basalt', seed=int(rng.integers(1e6))), area=(20, 20, 300, 300), n=7, seed=2, spacing=60)
    out['boulders'] = Asset({'name': 'Boulder field', 'footprint': [2, 2], 'build': boulders})
    def scrub():
        def plant(i, rng):
            h = 30 + 30 * rng.random()
            return sh.broadleaf(h, 'scrub', 'basalt', seed=int(rng.integers(1e6)), clumps=4)
        return sh.scatter(plant, area=(10, 10, 150, 150), n=6, seed=5, spacing=34)
    out['scrub'] = Asset({'name': 'Alien scrub', 'footprint': [1, 1], 'build': scrub})
    return out


def main(out=None):
    out = out or os.path.join(HERE, 'out')
    st = Style.load('frontier_outpost')
    ex = Exporter(st, out)
    t0 = time.time()
    for f in sorted(glob.glob(os.path.join(HERE, 'recipes', '*.json'))):
        ex.static(os.path.basename(f)[:-5], Asset.load(f))
    for k, a in terrain().items():
        ex.static(k, a)
    for fn in (rover, strider, crawler, drone):
        rig, clips = fn()
        for c in clips:
            chk = rig.check(c)
            if chk['slide'] > 1.0 or chk['float'] > 1.0: print(f'  {rig.name} {c.name}: slide {chk["slide"]:.2f} float {chk["float"]:.2f}')
        ex.rig(rig.name, rig, clips)
    ex.save()
    print(f'done in {time.time() - t0:.0f}s -> {out}')
    return out


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
