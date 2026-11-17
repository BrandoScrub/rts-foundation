"""Blockout: a WW2 American medium tank (M4A3 Sherman, 75 mm gun, welded hull, VVSS suspension), designed by
artkit/DESIGN_METHOD.md. Primary and secondary masses only; detail comes after the blockout is agreed.

Brief
  is:        medium tank, 1943-45 American, five crew
  does:      fights in the open and supports infantry: a turret that aims anywhere, a hull that crosses rough ground
  gameplay:  RTS unit, 2 x 1 tiles; the player must read which way the hull drives and which way the gun points
  power:     engine at the rear under the deck; drive shaft forward under the turret to the transmission in the nose;
             FRONT drive sprockets on final-drive housings either side of the nose casting, idlers at the rear
  moves:     tracks round sprocket, three two-wheel VVSS bogies a side (each with a return roller on top) and an idler;
             turret on a ring in the hull roof; gun on trunnions behind a curved cast shield (rotor shield)
  built:     welded hull plates; cast turret and cast nose (castings are rounded: the round masses on the tank, and
             why); driver and bow-gunner hatches in raised hoods where roof meets glacis
  serviced:  hatches in the hoods; commander's cupola and loader's hatch on the turret roof
  made_of:   rolled and cast armour, steel running gear, steel track with end connectors (the toothed edge)
  references: M4A3 drawings and survivors; a printable M4A3 model the user found (proportions; hoods; the nose casting
             between the tracks; sprocket ahead of and below the glacis; brackets visible between wheel pairs with the
             roller on top; toothed track edge; the turret as tall as the hull side)
  read_at_play_size: a long, tall-sided box on toothed tracks, sloped front over a rounded nose, a big rounded turret
             with a gun along the hull

Joints, not placement (DESIGN_METHOD.md step 3): every part meets the next through something real: hoods between
roof and glacis, final drives between nose and sprockets, brackets between hull and wheels, a ring guard round the
turret's foot. Built as an artkit.machine.Machine: every part says why it is there and what it is mounted on, and
`machine().check()` holds the geometry to it (FLOATING, CLASH, OFF AXIS, TRACK OFF WHEEL, ...); it must come back
empty. The track is one continuous band on true tangents round its wheels (shapes.belt).

Scale: real metres x 55. x: rear (0) to front; y: across, centre CY; z: up. Right of the tank (facing +x) is -y.
"""
import math

from artkit import shapes as sh
from artkit.machine import Machine
from artkit.core.geom import Geometry, RZ

M = 55.0                 # units per metre
X0 = -4.0                # rear of the hull in the 2 x 1 footprint (320 x 160 units)
CY = 80.0
TRACK_Y, TRACK_W = 1.055, 0.42           # track centre line (tread 2.11 m) and width
BAND, TOOTH = 0.08, 0.04                 # track plate and end-connector (tooth) thickness, metres
FLOOR = 1.12                             # underside of the sponsons over the tracks
ROOF = 1.88
RX = 2.90                                # turret ring centre, from the rear
SPROCKET = (5.20, 0.66, 0.30)            # x, z, radius: front, raised, below the sponson floor
IDLER = (0.38, 0.50, 0.26)
BOGIES = (1.25, 2.75, 4.25)
WHEEL_R = 0.255
WHEEL_Z = BAND + TOOTH + WHEEL_R         # wheels stand on the track's inner face
ROLLER_R, ROLLER_Z = 0.10, 0.87               # roller tops just above the sprocket's, so the top run rests on every roller


def P(x, y, z):
    """Metres (x from the rear, y from the centre line, z up) -> units in the footprint."""
    return (X0 + x * M, CY + y * M, z * M)


def solid(pts, mat, smooth=False):
    """A block from its corners (metres); smooth: a casting, shaded round with its real edges kept."""
    g = sh.convex([P(*p) for p in pts], mat)
    return sh.soften(g) if smooth else g


def across(xz, y0, y1):
    """Side-outline points (x, z) carried across from y0 to y1."""
    return [(x, y, z) for x, z in xz for y in (y0, y1)]


def axle(x, z, r, y, w, mat, seg=16):
    """Something round turning on an axle across the tank (wheel, roller, sprocket, final drive)."""
    return sh.cyl(P(x, y - w / 2, z), P(x, y + w / 2, z), r * M, mat, seg=seg)


def hub(x, z, r, y, side, out, mat, seg=12):
    """A hub cap on the outer face of a wheel (y = its centre, out = how far past the centre it reaches outward)."""
    return sh.cyl(P(x, y, z), P(x, y + side * out, z), r * M, mat, seg=seg)


# ---------------------------------------------------------------- the machine
def machine():
    """The tank as a Machine: parts, mounts, joints, tracks. check() must be empty."""
    m = Machine('M4A3 medium tank', ground=0.0)
    gz = lambda x: ROOF - (x - 4.25) * (ROOF - FLOOR) / (5.62 - 4.25)      # height of the glacis at x

    # ---- hull: welded plates (flat), castings (rounded)
    m.add('upper_hull', solid(across([(0.0, FLOOR), (0.05, ROOF), (4.25, ROOF), (5.62, FLOOR)], -1.31, 1.31), 'hull'),
          'fighting and engine compartments, full width so it overhangs the tracks as sponsons; a 56-degree glacis in front')
    m.add('lower_hull', solid(across([(0.30, 0.45), (0.10, FLOOR), (5.10, 0.45), (5.10, FLOOR)], -0.80, 0.80), 'hull'),
          'the tub between the tracks that carries the suspension', on='upper_hull')
    nose = [(5.05, 0.45), (5.45, 0.47), (5.72, 0.58), (5.88, 0.78), (5.90, 0.95), (5.80, 1.07), (5.62, FLOOR + 0.01), (5.05, FLOOR + 0.01)]
    m.add('nose', solid([(x, y if x < 5.7 else y * 0.9, z) for x, z in nose for y in (-0.80, 0.80)], 'hull', smooth=True),
          'cast transmission and final-drive housing: rounded because cast, between the tracks, ahead of the glacis',
          on='lower_hull', contact=['upper_hull'])
    for side, nm in ((1, 'driver'), (-1, 'bow_gunner')):
        y0, y1 = sorted((side * 0.16, side * 0.74))
        m.add(f'{nm}_hood', solid(across([(4.02, ROOF), (4.02, 2.00), (4.48, 2.00), (4.80, gz(4.80))], y0, y1), 'hull'),
              'raised hood where roof meets glacis so the hatch clears the crewman\'s head: joins hatch to hull', on='upper_hull')
        m.add(f'{nm}_hatch', sh.cyl(P(4.24, side * 0.45, 2.00), P(4.24, side * 0.45, 2.035), 0.25 * M, 'steel', seg=14),
              'hatch lid on the hood: crew access, and the human-scale cue (0.5 m)', on=f'{nm}_hood')
    m.add('ring_guard', sh.lathe([(1.12 * M, 0), (1.12 * M, 0.07 * M), (0, 0.07 * M)], 'hull', n=28).move(*P(RX, 0, ROOF)),
          'raised collar round the turret ring: the turret sits in it, it does not float', on='upper_hull')

    # ---- running gear
    for side in (1, -1):
        s = 'l' if side > 0 else 'r'; ty = side * TRACK_Y; across_y = (0, 1, 0)
        sx, sz, sr = SPROCKET; ix, iz, ir = IDLER
        m.add(f'final_drive_{s}', axle(sx, sz, 0.17, side * 0.87, 0.16, 'hull'),
              'final-drive housing: carries the drive from the nose casting out to the sprocket', on='nose', contact=['lower_hull'])
        m.add(f'sprocket_{s}', axle(sx, sz, sr, ty, 0.30, 'steel', 18), 'FRONT drive sprocket, ahead of and below the glacis',
              on=f'final_drive_{s}', turns=(P(sx, ty, sz), across_y))
        m.add(f'sprocket_hub_{s}', hub(sx, sz, 0.14, ty, side, 0.21, 'steel'), 'sprocket hub: says it is driven', on=f'sprocket_{s}',
              turns=(P(sx, ty, sz), across_y))
        yb0, yb1 = sorted((side * 0.80, side * 0.93))
        m.add(f'idler_bracket_{s}', solid(across([(0.32, iz - 0.08), (0.32, iz + 0.08), (ix + 0.08, iz - 0.08), (ix + 0.08, iz + 0.08)], yb0, yb1), 'steel'),
              'holds the idler\'s axle out from the hull side', on='lower_hull')
        m.add(f'idler_{s}', axle(ix, iz, ir, ty, 0.28, 'steel'), 'rear idler: guides and tensions the track', on=f'idler_bracket_{s}',
              turns=(P(ix, ty, iz), across_y))
        m.add(f'idler_hub_{s}', hub(ix, iz, 0.10, ty, side, 0.18, 'steel'), 'idler hub: the axle end', on=f'idler_{s}',
              turns=(P(ix, ty, iz), across_y))
        wheels = []
        for k, bx in enumerate(BOGIES):
            y0, y1 = sorted((side * 0.80, side * (TRACK_Y + 0.12)))
            br = f'bracket_{s}{k}'
            m.add(br, solid(across([(bx - 0.08, 0.30), (bx - 0.06, ROLLER_Z - 0.04), (bx + 0.08, 0.30), (bx + 0.06, ROLLER_Z - 0.04)], y0, y1), 'steel'),
                  'VVSS bogie bracket: bolted to the hull side between its wheel pair, spring inside, roller on top', on='lower_hull')
            for dx in (-0.34, 0.34):
                w = f'wheel_{s}{k}{"ab"[dx > 0]}'
                ya0, ya1 = sorted((side * 0.80, side * (TRACK_Y - 0.13)))
                xa0, xa1 = sorted((bx + math.copysign(0.05, dx), bx + dx))
                m.add(f'arm_{w}', solid(across([(xa0, WHEEL_Z - 0.06), (xa0, WHEEL_Z + 0.06), (xa1, WHEEL_Z - 0.06), (xa1, WHEEL_Z + 0.06)], ya0, ya1), 'steel'),
                      'bogie arm from the bracket to the wheel axle (inboard, mostly hidden: kept so the wheel is mounted)',
                      on=br, small_ok=True)
                m.add(w, axle(bx + dx, WHEEL_Z, WHEEL_R, ty, 0.26, 'rubber'), 'road wheel (0.51 m) on the track\'s inner face',
                      on=f'arm_{w}', turns=(P(bx + dx, ty, WHEEL_Z), across_y))
                m.add(f'hub_{w}', hub(bx + dx, WHEEL_Z, 0.11, ty, side, 0.16, 'steel'), 'wheel hub: a wheel, not a puck',
                      on=w, turns=(P(bx + dx, ty, WHEEL_Z), across_y))
                wheels.append((bx + dx, w))
            m.add(f'roller_{s}{k}', axle(bx + 0.05, ROLLER_Z, ROLLER_R, ty, 0.22, 'steel', 12),
                  'return roller on top of the bracket: holds up the top run', on=br, turns=(P(bx + 0.05, ty, ROLLER_Z), across_y))
        circles = ([(P(x, 0, 0)[0], WHEEL_Z * M, WHEEL_R * M) for x, _ in sorted(wheels)]
                   + [(P(sx, 0, 0)[0], sz * M, sr * M)]
                   + [(P(b + 0.05, 0, 0)[0], ROLLER_Z * M, ROLLER_R * M) for b in reversed(BOGIES)]
                   + [(P(ix, 0, 0)[0], iz * M, ir * M)])
        wraps = [w for _, w in sorted(wheels)] + [f'sprocket_{s}'] + [f'roller_{s}{k}' for k in reversed(range(len(BOGIES)))] + [f'idler_{s}']
        yt0, yt1 = sorted((P(0, ty - TRACK_W / 2, 0)[1], P(0, ty + TRACK_W / 2, 0)[1]))
        m.belt(f'track_{s}', circles, yt0, yt1, BAND * M, 'rubber', teeth=(0.17 * M, 0.07 * M, TOOTH * M),
               why='track: one band round wheels, sprocket, rollers and idler; end connectors give it its toothed edge',
               on=f'sprocket_{s}', wraps=wraps)

    # ---- turret: cast (rounded), turns on the ring inside the ring guard
    tz = ROOF + 0.07
    body = sh.lathe([(0.98 * M, 0), (1.05 * M, 0.10 * M), (1.07 * M, 0.38 * M), (1.03 * M, 0.64 * M), (0.90 * M, 0.84 * M),
                     (0.62 * M, 0.94 * M), (0.30 * M, 0.96 * M), (0, 0.97 * M)], 'hull', n=28).scaled(1.06, 1.0, 1.0)
    m.add('turret', sh.soften(body).move(*P(RX, 0, tz)), 'cast turret, as tall as the hull side: rounded because cast',
          on='ring_guard', turns=(P(RX, 0, tz), (0, 0, 1)))
    m.add('bustle', solid([(RX - 0.55, y, tz + z) for y in (-0.66, 0.66) for z in (0.10, 0.74)] +
                          [(RX - 1.28, y, tz + z) for y in (-0.52, 0.52) for z in (0.18, 0.66)] +
                          [(RX - 1.36, y, tz + z) for y in (-0.42, 0.42) for z in (0.26, 0.56)], 'hull', smooth=True),
          'bustle overhanging the deck at the back: radio, and weight behind to balance the gun', on='turret')
    ax, az = RX + 0.95, tz + 0.40                                  # trunnion axis
    shield = [(ax + 0.30 * math.cos(math.radians(a)), y, az + 0.30 * math.sin(math.radians(a)))
              for a in range(-70, 71, 14) for y in (-0.56, 0.56)] + [(ax - 0.12, y, az + z) for y in (-0.56, 0.56) for z in (-0.30, 0.30)]
    m.add('rotor_shield', solid(shield, 'steel', smooth=True), 'curved cast shield round the trunnion axis: the gun pivots behind it',
          on='turret')
    m.add('gun_shield', sh.cyl(P(ax + 0.26, -0.05, az), P(ax + 0.62, -0.05, az), 0.12 * M, 'steel', seg=12),
          'collar where the gun leaves the shield, on its axis', on='rotor_shield')
    m.add('gun', sh.cyl(P(ax + 0.62, -0.05, az), P(RX + 3.55, -0.05, az), 0.065 * M, 'steel', seg=10),
          '75 mm gun, 3 m: the long line that says where it points (thin, but a line that carries)', on='gun_shield', small_ok=True)
    m.add('muzzle', sh.cyl(P(RX + 3.38, -0.05, az), P(RX + 3.58, -0.05, az), 0.085 * M, 'steel', seg=10),
          'thicker muzzle: the barrel\'s end reads', on='gun')
    m.add('cupola', sh.cyl(P(RX - 0.30, -0.40, tz + 0.90), P(RX - 0.30, -0.40, tz + 1.04), 0.30 * M, 'steel', seg=16),
          'commander\'s cupola, roof right-rear: the commander looks out of it; scale cue', on='turret')
    m.add('loader_hatch', sh.cyl(P(RX - 0.20, 0.42, tz + 0.90), P(RX - 0.20, 0.42, tz + 0.96), 0.24 * M, 'steel', seg=14),
          'loader\'s hatch, roof left', on='turret')
    return m


def geometry(turret_heading=0.0):
    """The whole tank, turret turned turret_heading degrees from straight ahead."""
    return machine().geometry(pose={'turret': turret_heading} if turret_heading else None)


def check():
    """The machine check (artkit.machine): [] when every part has a reason, is mounted, and nothing clashes."""
    return machine().check()


def rig(headings=8):
    """The tank as a unit (artkit.machine.MachineRig): hull and tracks below, turret on top, tracks that run."""
    tz = ROOF + 0.07
    return machine().rig(P(2.97, 0, 0), upper=['turret'], muzzle=P(RX + 3.58, -0.05, tz + 0.40), recoil=['gun', 'muzzle'],
                         headings=headings, name='m4a3')
