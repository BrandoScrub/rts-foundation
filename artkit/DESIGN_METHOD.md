# Designing things that make sense: the method for units, vehicles, turrets and props

Read this before you design or change any asset's geometry: a recipe, a rig, a part, a library prop. It is the
thinking that has to happen before a single shape is placed. `design.py` already does part of this for buildings
(the composer writes its reasons to `asm.notes`); this file is the method for everything, and the standard a
building's hand-finishing is held to as well.

**The failure this prevents.** Shapes picked because they are easy primitives, placed where they look roughly right,
with a colour standing in for meaning: a cube on a plinth with a stick for a barrel, an egg on four tubes. Players
read real objects all day; when nothing explains how a thing turns, moves, is built or is fed, it looks wrong even
at 40 pixels tall, and no amount of finish fixes it.

**The rule.** Every part exists for a reason you can say in one line, sits where that reason puts it, and is the
shape that reason implies. A part with no reason is cut.

The method has seven steps, in order. Steps 1 to 4 happen on paper (in the brief) before any geometry.

---

## 1. Start from function, not shapes: the brief

Write the brief first, inside the recipe file (recipes ignore keys they do not use, so `"brief"` and each part's
`"why"` cost nothing) or in the rig's docstring for code-built things:

```json
"brief": {
  "is": "point-defence laser turret",
  "does": "tracks and burns small fast targets (drones, missiles) near the base",
  "gameplay": "static defence, 1x1 tile, turns 360, the player must read where it is aiming",
  "power": "mains power through a buried cable; heat dumped through radiators",
  "moves": "yaw on a ring bearing; pitch on trunnions, -10 to +70 degrees",
  "built": "factory-made head bolted onto a cast pedestal on a poured pad",
  "serviced": "access panel on the pedestal; head lifts off the ring",
  "made_of": "composite shell, steel mechanism, glass optics",
  "faction": "frontier colonists: practical, modular, a little worn",
  "references": ["Phalanx CIWS: one mount carries gun, radar and drum", "naval gun mounts: trunnions, mantlet, counterweight"],
  "read_at_play_size": "a column with a heavy head and a long barrel that points somewhere"
}
```

Then each part names its reason:

```json
{"name": "ring", "why": "the ring bearing the head turns on; a lip wider than the column says 'this rotates'", ...}
```

If you cannot fill in `moves`, `power` and `serviced`, you do not understand the object yet: go to step 2.

## 2. References before geometry

- Find 3 to 5 references: real machines first (they carry the engineering), then games in the target style (they
  show what survives at play size). Name each and write the one thing taken from it (`references` above).
- Write down the **anatomy they share**: that is the object's grammar. Every turret has foundation, bearing,
  rotating housing, pitch axis, weapon, feed. Every legged machine has body, hip actuators, upper leg, knee, lower
  leg, foot sized to its weight.
- When the user has a look in mind, ask for their references and record them in the brief; their choice beats yours.
- Never copy a protected design (a named franchise's walker, a studio's unit). Take the engineering, not the look.

## 3. Mechanism first, then wrap it

For anything that moves, place the **joints and their axes before any housing**. Then the shell goes round the
mechanism, never the other way.

- **Load path**: trace weight from the top part to the ground. Each part rests on the one below or hangs from a
  joint. Nothing floats; nothing is held up by a thinner part than what it carries.
- **Axes**: every rotation has a visible axis: a ring for yaw (a lip, a gap, a darker band), pin caps or cheeks for
  pitch, hinge pins at knees and doors. The axis is where the rotation actually happens, and the part that turns is
  centred on it.
- **Drives**: something makes each joint move: a motor housing at a ring, a hydraulic ram along a leg, a gearbox at a
  hinge. Rams run from a fixed mount to a mount on the moving part, offset from the hinge so they have leverage.
- **Balance**: a long thing on a pivot has a counterweight or its heavy end at the pivot (a barrel's breech, a
  crane's back end). Put mass where the physics would.
- **Clearance**: nothing passes through anything, and a moving part at the end of its range does not either (barrel
  at full depression clears the deck; a knee at full bend clears the body; a track wrapping a raised sprocket clears
  the glacis). **Measure it, do not judge it by eye**: `artkit.clearance.check(parts, solids, movers, allow=...)`
  lists every part that goes into another (and how far, and where) or below the ground. List the real joints in
  `allow` (a bracket bolted to the hull); everything else must come back clear. The tank blockout's `clashes()` is the
  example; the first tank had its track 8.5 units into the hull and nobody saw it until the user did.
- **Build machines as `artkit.machine.Machine`** (README, Machines): every part with its `why`, the part it is
  mounted `on` and the joint it `turns` on, tracks as `belt`s. `check()` must come back empty before anyone sees it:
  it reports parts with no reason, parts that float off their mount, parts passing through each other (turrets at
  eight headings), wheels off their axles, tracks that do not ride on their wheels, and parts too small to see. It is
  the vehicle version of the building checker. Writing the mount of every part is what finds missing structure: the
  tank's wheels had nothing holding them until it asked (bogie arms), and its hubs ran into their own mounts.
- **Transitions, not placement**: parts on real machines meet through something: a hatch sits in a hood, a turret in
  a ring guard, a sprocket on a final-drive housing, a pedestal on a flange, a wheel on a hub, a pipe through a collar.
  Shapes that just touch or overlap read as "chopped together". For every place two parts meet, name what joins
  them; if nothing does, add it or move the part.
- **Feed**: power, ammunition, fuel or coolant has a route: a cable, a conduit, a feed chute, a hose, a tank.

### Mechanism chains (start every new one of these from its chain)
| Thing | Chain, ground up |
|---|---|
| Turret / gun mount | foundation (pad, bolted flange) -> pedestal or hull roof -> **ring bearing** -> rotating housing (yaw drive, offset back to balance) -> **trunnions** (two cheeks with pin caps) -> cradle -> weapon: heavy breech/shroud at the axis, barrel forward through a mantlet, counterweight or radiator behind -> sensor fixed to the cradle, parallel to the bore -> feed (ammo chute or power cable) |
| Legged walker | body (armoured hull, power plant) -> **hip housings** at the corners (swing + lift motors) -> upper leg (box or I-section, thickest at the hip) with a **ram** from hip to knee -> **knee pin** -> lower leg (narrower) with a second ram or shock -> ankle pivot -> **foot** wider than the leg, flat sole, sized to the weight |
| Wheeled vehicle | chassis rails -> suspension (arm or leaf + damper) per wheel -> hub -> wheel with tyre profile; engine bay over the driven axle, exhaust out of it, fuel tank on the chassis, cab where the driver can see forward |
| Tracked vehicle | hull -> road wheels on swing arms -> drive sprocket (one end) and idler (other end) -> return rollers -> track; turret on a ring in the roof |
| Rotorcraft / drone | body -> pylons or arms (load path to each rotor) -> motor nacelle -> hub -> blades; landing gear under the centre of mass |
| Door, hatch, ramp | frame in the wall -> hinge line on one edge -> leaf -> handle or actuator on the far side from the hinge |
| Mast, antenna, crane | base (guy wires or a wide foot) -> tapering lattice or tube -> equipment at the top fed by a cable down the mast |

## 4. Scale cues

The engine's sizes (the demo pack's `proportions`, shared by most packs): **a person stands 100 units**, a door is
96, a storey 110, a tile 160 across. So for machines and props, **1 metre is about 55 units**. Buildings are
compressed relative to people (a storey of 110 is about 2 m), a normal RTS convention; machines and props are not.

| Feature | Real size | Units | Pixels at export (0.4 px/unit) |
|---|---|---|---|
| Person | 1.8 m | 100 | 40 |
| Hatch you climb through | 0.6-0.8 m | 35-45 | 14-18 |
| Hand rail height | 1.0 m | 55 | 22 |
| Ladder rung spacing | 0.3 m | 16 | 6 |
| Crate | 1.0 m | 55 | 22 |
| Light gun barrel (autocannon) | 0.1 m bore, 2-3 m long | 6, 110-160 | 2.4, 44-64 |
| Main gun barrel | 0.12 m bore, 5 m long | 7, 270 | 3, 108 |
| Wheel (truck) | 1.0 m | 55 | 22 |

Put at least one human-scale cue on every machine (a hatch, rail, ladder, handle, seat): it is what tells the eye
how big the thing is. Size everything from the table, not by eye.

## 5. A shape language: what each primitive means

A shape tells the eye what a part does. Use primitives for what they mean:

| Primitive | Means | Use for | Do not use for |
|---|---|---|---|
| `box`, `prism`, `extrude` with chamfers | a housing, a structure, armour | hulls, housings, cheeks, pads, plates | rotating parts |
| `cyl`, `lathe` | rotation, pressure, flow | bearings, pins, barrels, rams, wheels, pipes, tanks, columns | housings, armour |
| `beam`, `strut`, `lattice` | a load path | legs, arms, frames, masts | volumes |
| `convex` (any corner points) | plates with chamfers, hoods, cast noses, shields | anything with more than 8 corners that is convex | concave shapes (build them from convex pieces) |
| `soften(g)` on a lathe or `convex` | a casting | cast turrets, cast noses, shields: shaded round, real edges kept | welded plate (it stays flat) |
| `sphere`, `ellipsoid`, `blob_lathe` | organic or pressurised | domes, pressure tanks, creatures, joint covers on soft robots | machine bodies (they read as toys) |
| `wedge`, `gable` | shedding (rain, blast, sloped armour) | roofs, glacis plates | flat-topped housings |

- **One bevel size per object**, proportional to its size, on every hard edge: mixed bevels look like kit-bashing.
- **Hard-surface objects are built from planes and cylinders.** A round body on a machine needs a reason (a
  pressure hull, a sensor dome).
- A faction may change the language (organic aliens, rounded consumer tech): write it in the brief's `faction` and,
  when it holds for a whole game, in the pack.

## 6. Big shapes first, checked at play size each time

Build in three passes and look at the play-size render after each:
1. **Primary masses** (two or three): the silhouette. At play size only outline, value blocks and one colour carry
   (the rule `design.py` holds buildings to). Ask: can you tell what it is, which way it faces, and what it will
   do, from the silhouette alone?
2. **Secondary features**: the mechanism and function made visible: ring, trunnions, hip housings, rams, hatch,
   radiator, sensor. Each must be at least 3 output pixels (about 8 units) across or it is not seen.
3. **Tertiary detail**, only where it helps reading: panel breaks along real seams, a conduit, team-colour panel.
   Anything under 8 units is cut unless it is a line that carries (a cable, a rail).

Proportion and weight: legs, columns and arms are thick enough for what they carry (a leg at least a fifth of the
body's width at the hip); heavy parts low and central; the thing looks like it would stand up if you built it.

## 7. Critique before showing, and a blockout before detail

Render at play size (export scale) and close up (2.5x, `mesh view` or `sprite.picture(scale=1)`), from at least two
headings, **and from the same angle as a reference picture, side by side with it**, and go through this list.
Vehicles and units are rendered with a camera without ground plates (`Camera.from_pack({"view": "iso", "plates":
false})`): the ground-plate rule (no outline under 8 units) is for buildings, and on a vehicle it erases the bottom of
the tracks. For the game's own export, give the pack a `"unit_camera"` with `"plates": false` (README, Cameras). Write the answers in the brief as `"checked"`:

- [ ] Every part has a `why`; the parts with none are gone.
- [ ] The mechanism chain is complete: foundation to tip, every joint has an axis and a drive.
- [ ] Load path: nothing floats, nothing thick sits on something thin.
- [ ] Rotating parts are centred on their axes; pitching parts pivot at the trunnion; barrels align with their bore.
- [ ] For a machine: `Machine.check()` is empty.
- [ ] `artkit.clearance.check` comes back empty (only real joints allowed), including moving parts at several
      positions.
- [ ] Every place two parts meet has a named transition (hood, collar, flange, housing, hub, ring guard).
- [ ] A feed route exists (power, ammo, fuel).
- [ ] At least one human-scale cue, sized from the table.
- [ ] Primitives used for what they mean (step 5); one bevel size.
- [ ] At play size: identity, facing and function read from the silhouette; secondary features at least 3 px.
- [ ] Compared side by side with the references: does it belong in the same world?

Then show the user a **blockout** (primary and secondary masses only, flat grey) with the brief, before any
detailing. Blockouts live in `artkit/demo/blockouts/` (or the game's own folder); `python3 -m
artkit.demo.blockouts.render <out>` draws grey review sheets at play size and close, from several headings, with the
engine's lines and with the line weight hierarchy (README, Light: `ink`), which shows a shape's own edges. Detail only after they agree it makes sense. Show what you checked and what still feels off; never
present an asset as finished without saying how it was judged.

---

## Worked examples: the demo turret and walker, redesigned on paper

The demo pack's `laser_turret.json` and `strider` were made before this method and fail it: they show what to avoid.
The turret below is built as a blockout in `demo/blockouts/point_defence_turret.json` (revised after review: the turning
housing became a drum narrower than the ring, the side plates lower than the gun body, the radiator a smaller block).

### Point-defence laser turret (1x1 tile)
Brief as in step 1. Parts, ground up (units; tile 160, centre at 80, 80):

| Part | Shape | Size | Why |
|---|---|---|---|
| pad | chamfered `prism`, 8 sides | 120 across, 8 high | poured foundation spreads the load; octagon fits the tile and reads as built |
| flange | `cyl` | 64 across, 6 high | the cast pedestal is bolted to the pad: a wider foot where they meet |
| pedestal | `lathe`, slight taper | 52 to 46 across, 40 high | holds yaw motor and slip ring; height puts the bore over a wall |
| access panel | inset `box` on the pedestal's camera side | 22 x 28 | servicing; a human-scale cue |
| conduit | `sweep` from pad edge into pedestal base | 6 thick | the buried power cable surfaces here: why it works |
| ring | `cyl`, darker material | 62 across, 4 high | **the ring bearing**: a lip wider than the pedestal says "this turns" |
| yaw housing | chamfered `box`, set 8 back of the axis | 64 x 54 x 20 | power conditioning; mass behind the axis balances the barrel |
| cheeks | two `box` plates either side | 8 x 30 x 30 each | carry the pitch axis; open between them so the cradle can tilt |
| trunnion caps | `cyl` on each cheek, along the pitch axis | 12 across | the visible pivot |
| cradle / emitter body | chamfered `box`, centred on the pitch axis | 50 x 26 x 22 | the laser; its centre sits on the trunnion axis so it balances |
| radiator | `fins`-like plates on the cradle's back | 20 deep | lasers make heat: the back end has to dump it (and counterweights the front) |
| emitter barrel | `lathe`: thick shroud tapering to the lens tube | 18 to 8 across, 70 long | the beam leaves along the bore; the shroud at the axis is the mantlet |
| sensor | small `box` on the left cheek, lens forward (glass, glowing) | 14 x 12 x 10 | tracking optic fixed parallel to the bore, so it pitches with the emitter |
| team panel | top plate of the cradle in the team material | 40 x 20 | the one colour that carries, on the biggest upward face |

Primary masses: pad, pedestal, head with barrel. Secondary: ring, cheeks and caps, radiator, sensor. Tertiary:
panel, conduit. Turning part (pivot `head`): ring and everything above it. At play size it reads as a column with a
heavy head that points along a long barrel.

### Four-legged gun walker (scout)
Brief: carries a light gun over rough ground; diesel-electric pack in the body; legs move by hydraulics; crew of
one under a top hatch; frontier make: boxy, practical, bolted plates. References: hexapod and quadruped robots
(hip actuator blocks, rams along the legs), construction excavators (ram geometry, pins, plates).

| Part | Shape | Size | Why |
|---|---|---|---|
| hull | chamfered `extrude` (hexagonal plan) | 90 long, 64 wide, 30 high; underside 58 off the ground | power pack and crew; flat plates read as armour, not an egg |
| front sensor block | `box` with glass slit | 26 x 18 x 12 | gives it a face, so the player reads which way it walks |
| hatch | `cyl` lid with a hinge block | 36 across | crew access; the human-scale cue |
| exhaust | short `cyl` stacks at the back, angled up | 8 across | the engine has to breathe; marks the rear |
| hip housings (x4) | chamfered `box` at the hull corners, outside the hull line | 22 x 22 x 20 | swing and lift motors: legs come out of something that moves them |
| upper legs | tapered `beam`, box section | 12 thick at hip to 8 at knee, 50 long | carries the body; thickest where the load is largest |
| upper rams | `cyl` (body) + thinner `cyl` (rod) from hip housing top to a lug near the knee | 6 and 4 across | what lifts the knee; offset from the leg so it has leverage |
| knee pins | `cyl` caps on the hinge axis | 10 across | the visible hinge |
| lower legs | tapered `beam` | 8 to 6 thick, 56 long | narrower than the upper leg: less load below the knee |
| lower rams | short `cyl` from mid upper leg to the lower leg | 4 across | drives the knee |
| feet | flat chamfered `box` pads on an ankle pin | 20 x 16 x 5 | spreads the weight; flat sole meets the ground, wider than the leg |
| gun mount | the turret chain, scaled down: ring 30 across, housing, cheeks, gun | barrel 60 long | the gun aims on its own, so it turns on a ring, not on the hull |

Stance: knees up and out (spider stance) because it is wide and stable for a gun platform; feet outside the hull's
footprint by about a third of its width. The walk cycle keeps the body level (the rig's gaits already do).

---

### WW2 American medium tank (M4A3 Sherman)
`demo/blockouts/m4_medium_tank.py`: the full brief is its docstring, every part a `(name, group, why, geometry)`.
Real dimensions x 55. What makes it read as this tank, in order: long low hull with tall vertical sponsons over the
tracks; a 56-degree glacis over a bolted transmission cover (front drive: the raised sprocket is at the FRONT, idler
at the rear); three two-wheel VVSS bogies a side, each with a return roller on top; a turret slightly forward of
centre, the one rounded mass because it is cast, with a bustle behind and a mantlet in front; a 3 m gun along the
bore axis. Hatches ahead of the turret and on its roof are the scale cues. Cut until detail: the bow machine-gun
ball (2.5 px at play size), fenders, engine grilles, tools, periscopes.

## Where this is going (engine support, not yet built)
- A library of mechanism parts so the right structure is the easy path: `ring_bearing`, `trunnion`, `ram`,
  `hip_housing`, `hinge`, `foot_pad`, `wheel_hub`, sized by argument and placed on axes.
- Briefs and `why` checked by tooling: a recipe or rig with a part missing its `why`, a joint with no drive, or a
  feature under 3 px gets a finding, as `design.critique` does for buildings.
- A shape-language section in the pack (bevel size, allowed primitives per faction).
