# artkit: one art engine for strategy games (isometric by default, top-down as an option)

An image model paints only flat, seamless material tiles. Everything else (shape, light, line, animation, damage,
packing) is code, so every sprite in a game shares one camera, one light and one finish, and a new game is a new
**style pack** plus **recipes**, not a new engine.

This is the engine's own repository (BrandoScrub/Game-Engine-System-Design). It depends on Python 3 with NumPy, SciPy
and Pillow (and Node for `maps/`). It is game-agnostic: everything that makes one game look like itself is a **style
pack**, which a game keeps in its own repository (see Using artkit in a game). The first game built on it, Brass and
Bone, renders all its art through it byte-identical to the kits it replaced.

**Designing an asset?** Read [`DESIGN_METHOD.md`](DESIGN_METHOD.md) first: function before shapes, the mechanism
before the shell, a reason for every part, the critique checklist. Code makes the art consistent; that method makes it
make sense.

## Layers
| Path | What it is |
|---|---|
| `core/space.py` | The conventions: 2:1 isometric, 160 units a tile, light from the upper left, headings. Do not change lightly. Also `Camera`: other orthographic views (see Cameras), the isometric one the default. |
| `core/geom.py` | `Geometry`: one triangle-soup type for everything. Transforms, part ids, `+` to join. |
| `core/materials.py` | Materials: tiled (bilinear), stretched (decals), nearest (figures); role tints `brick@home`; procedural stand-in tiles. |
| `core/light.py` | Two looks, both lit from the upper left: FLAT (hard surface: face light, wear, grain, ambient occlusion) and SMOOTH (rounded and moving things). One picture can mix them. |
| `core/render.py` | The one renderer: z-buffered triangles, then lines (`core/ink.py`, one game pixel wide everywhere) and an exact downsample. |
| `shapes.py` | Every primitive: box, wedge, gable, prism, lathe, dome, extrude, pyramid, strut, lattice, plane; rounded blob_lathe, sphere, ellipsoid, cyl, beam, slab; **sweep** (pipes, cables, rails), **ribbon** (roads), **catenary**, **bezier**, **heightfield** + **crater** (terrain, cliffs, mesas), **rock**, **conifer**, **broadleaf**, **scatter** (forests, rubble, debris), **convex** (the solid round any set of points: chamfered plates, hoods, cast noses), **soften** (round shading for a faceted casting, real edges kept). |
| `machine.py` | **Vehicles and machines as checked parts**: `Machine.add(name, geom, why, on=, turns=, contact=)`, `Machine.belt(...)` for tracks, `geometry(pose=)`, and `check()`: NO REASON, NO MOUNT, FLOATING, CLASH (turrets at eight headings), OFF AXIS, TRACK OFF WHEEL, TRACK BROKEN, GROUND, TOO SMALL. The machine counterpart of `assembly.check()` for buildings. See Machines. |
| `card.py` | **Cards**: a place on a square plot (`Scene`: parts with `why`, `ground=`, `cover=`; `check()`: NO REASON, OFF PLOT, NO GROUND) drawn as a framed card with a name box, isometric or top-down. Optional pack section `"card"`. See Cards. |
| `clearance.py` | Does one part pass through another, or below the ground? `check(parts, solids, movers, allow=)` measures it (depth and where), for blockouts and recipes (DESIGN_METHOD.md, step 3). |
| `library.py` | Props any game can use: crate, barrel, sandbags, fence, wire_fence, lamp_post, tank, pipe_run, cable, antenna, rubble, boulder, trees, scaffold. Materials are arguments. |
| `figure.py` | The humanoid figure engine (was unitkit's): `Biped`, `Tripod`, clips, gaits, layered poses, figure materials. |
| `parts/` | The parts libraries, now here: `building.py` (fences, roofs, windows, stairs, sandbags, tanks...), `soldier.py`, `trooper.py` (bodies, kit and weapons for `Biped`), `biped_clips.py` (shared walk, hit, attack and die clips; `infected.py` is its older name and still works). |
| `assembly.py` | `Assembly`: named, **tagged** parts (ground, base, body, roof, signature, accent, trim, opening, yard, siege, detail), a checker (UNSUPPORTED, DANGLING, DOOR TO NOWHERE), `Volume`, and compound parts (walkway, stair_to, awning, lookout...). |
| `motifs.py` | A theme's vocabulary: casemate, skirt, fins, ribs, banner, band, blast_door, airlock, stepped_tower, drum_tower, stacks, mast, searchlight, vault_drum, derrick, dish, berm, wire, hedgehog, beacons, and yard props. Materials come from the theme. |
| `design.py` | **Design logic.** `Brief` (role, rank, mechanic, mood, yard) -> `compose` (in the theme's language, reasons in `asm.notes`) -> `critique` (measured at play size) -> `search` / `design_set` (best of several variants, no two outlines alike). See Design logic below. |
| `recipe.py` | Assets as data (JSON): parts, repeats, **turning parts** (turrets, dishes), automatic **stages** (`build` at 33% and 66% with scaffolding, `damaged`, `ruined` with rubble and dark cut-open insides). |
| `rig.py` | One jointed body for anything that moves: **legs** (any number, IK, gaits that never slide), **wheels**, **tracks**, **rotors**, and a top layer (turret, torso) that aims separately from the bottom. Clips: idle, walk, roll, fire. |
| `style.py` + `styles/` | Style packs: tiles, role colours, ground, palette, game scale, proportions, figure materials, budget, and one section per module (`Style.section('terrain')`, `'hud'`, `'maps'`), inline in `style.json` or in its own file (`terrain.json`, `hud.json`, `maps/templates.js`). A pack may also carry its game's hand-built structures as Python (see Hand-built structures). Packs are found by name in `ARTKIT_STYLES`, the game's `styles/` folder beside `artkit/`, then `artkit/styles/` (the demo pack). |
| `sprite.py` | Geometry to sprite with the style's game numbers (`picture` for stills, `frame` for animation). |
| `export.py` | One exporter for every kind of asset, one `assets.json`; unit strips use the unit manifest format the runtime reads. With `static(..., finish=True)` (or a rules dict) every stage also gets the finishing pass: feathered ground-plate edges, lifted near-black yards, translucent earth yards, plate colour recorded as `g`; `finish_art` runs the same pass over a folder in an `art.json` format (key -> src, scale, dy). The game's choices are the pack's `finish` section (`keep_dark`, `solid_yards`, `no_plate`, `trodden_below`, ...). |
| `pack.py` | Lossless packing of animation strips into tight per-unit pages (each frame checked). |
| `director.py` | Art Director: memory, on-screen size, contrast against the ground, distance from the palette, animation sanity, and the design critic's score and unmet findings for stills exported with `Exporter.static(..., critique=True)` (the critic needs geometry, so the exporter runs it and keeps the verdict in `assets.json`; it is reported, and only fails a check when the style's budget sets `min_design_score`). |
| `team.py` | **Player colours** (optional pack section `"team"`): which materials carry the player's colour, the grey mask the exporter writes beside each picture, and the reference recolour the runtime repeats. See Team colours. |
| `shadow.py` | **Cast shadows** (optional pack section `"shadow"`): a soft shadow picture per still stage and a shadow layer `S` for units, drawn by the game under everything. See Shadows. |
| `mesh.py` | **3D models out, paint back in**: a paint atlas for any model (`unwrap`, `bake`), Wavefront OBJ + MTL (`write_obj`), a big render to paint over (`view`), projecting a paintover back onto the visible faces (`project`), and the model wearing the atlas (`painted`, `paint_asset`). See 3D models and paintovers. |
| `preview.py` | Contact sheets and animated GIFs from `assets.json` alone, the way a game sees them. |
| `terrain/` | **Terrain** (was `terrainkit/`): procedural ground tiles from recipes in the pack (`ground.py`), fitting painted ground tiles (`painted.py`), rock and ore atlases from heightfields (`rocks.py`) and their calm pass (`calm.py`), in-line gates (`gates.py`). `python3 -m artkit.terrain {ground\|fit\|fit-one\|rocks\|calm\|gates} ... --style <pack>`. |
| `hud/` | **HUD skin** (was `hudkit/`): plate, 9-slice frame and slots, minimap bezel, rules, corner caps, tab, empty-slot row (`skin.py`). `python3 -m artkit.hud <out> --style <pack>`. |
| `maps/` | **Narrative maps** (was `mapkit/`): the generator `mapkit.js` (JavaScript, no game knowledge, runs in Node and inlines into a page), `viewer.html`, `inline.py` (`python3 -m artkit.maps inline <index.html> --style <pack>`). Guide: `maps/README.md`. |
| `runtime/` | Drop-in for a browser game: `artkit.js` (stills, stages, turning parts, units), `units.js` (UnitKit), `glcanvas.js` (the WebGL renderer behind the Canvas 2D calls). |
| `demo/frontier/` | A second game's art (Frontier Outpost), built only from a style pack, six JSON recipes, four terrain pieces and four rigs. |
| `tests/engine_check.py` | The engine's own check, with nothing but the engine and the demo pack: Frontier stills, stages, turning parts, finishing, critic, a rig, a stock trooper, the composer. `expected_engine.txt` holds the expected lines. |
| `tests/team_check.py`, `tests/shadow_check.py` | The team and shadow options are additions: without them nothing changes, with them sprites stay byte-identical and only files are added; masks survive packing; the browser's recolour equals Python's; shadows fall down-right in every camera. |
| `tests/maps_identity.js` | Map plans from a generator and a templates file, hashed (games use it in their own map tests). |
| `tests/identity_kits.py` | Every output of the terrain, HUD and map modules (gates, rocks, calm rocks, procedural and painted ground, 18 HUD images, 76 map plans, the inlined block of `game/index.html`), through the old `terrainkit/`, `hudkit/`, `mapkit/` commands and through `artkit.terrain`, `artkit.hud`, `artkit.maps`; `expected_kits.txt` holds the hashes from before the move, and which of them equal the files in `game/`. |

## Terrain, HUD and maps from a style pack
Each module takes its look from the pack and knows no game:
- **terrain** (`styles/<pack>/terrain.json`): `gates.materials` (wood and concrete gate colours), `rocks` (per land:
  lit and shaded rock, soil, strata, moss, snow, optional dark ore host; ore stain, seam and glint), `calm` (grain,
  contrast, pinned atlas means), `ground.painted` (folder of painted sources, target colour and contrast per tile,
  grain and mottle) and `ground.procedural` (each tile as a small tree of operations: soil, grassy, pebbles, cracks,
  grit, blend, wind; see `terrain/ground.py`). The order of lands sets their seeds.
- **hud** (`styles/<pack>/hud.json`): plate colours (lo, hi, rust), the brass ramp (six stops, shade to highlight),
  outline, groove, edge, backing, slot tint and glow, empty-bay tint and rim, two random seeds.
- **maps** (`style.json` `"maps": {"templates": "maps/templates.js"}`): the game's templates as data for `maps/mapkit.js`.
A game's art can come out byte-identical to the kits it replaced (Brass and Bone's does). `frontier_outpost` has its own `terrain.json` and
`hud.json` as a proof (dust land, white-and-orange HUD); `demo/proposals/terrain_hud_two_packs.png` shows both.
Painted tiles are never regenerated by accident: `artkit.terrain ground` keeps an existing `ground_*.jpg` unless given
`--force`, and `fit` only reads the pack's painted sources. `python3 -m artkit.terrain fit <scratch>` reproduces all 15
of `game/art/ground_*.jpg` byte for byte.

## Design logic
The rule (learned on the Command Hall): **at play size only outline, value blocks and one colour carry.** A part
a few pixels big is wasted work. `design.py` turns that into something you can run.

- **The theme owns the taste.** `style.json` has a `design` section: `values` (which material is the base, the wall,
  the roof, the trim, the faction colour...), `massing` (margin, base motif, plans), `rhythm` (fins or ribs, bay
  width, which openings, how many lit), `roofs` and `signatures` by role, `door` by rank, `accent` (banner or band),
  `ground` by mood (siege: berm, wire, hedgehogs), and optional `targets`. Change the pack and the same brief comes
  out in another world: compare a game's pack with `styles/frontier_outpost`.
- **A brief has no shapes in it**: `{"key": "bank", "name": "Treasury", "footprint": [3, 3], "role": "store",
  "rank": "major", "mood": "siege", "mechanic": "...", "shows": ["nest", "crates"]}`.
- **compose** never builds one box: a podium with a set-back upper block, or a main block with a lower wing. The
  signature goes to the back corner because on screen height is z minus depth: the same tower at the front stands
  lower. It writes each decision to `asm.notes`.
- **critique** renders at play size and measures: how much of the outline one plain block explains, how far the
  signature stands above that block (after removing anything under 3 px), roof levels, light-to-dark range, share of
  the picture in large even areas, how much accent colour there is and whether it is in a few big pieces, parts too
  small to see, the theme's grammar (base, roof, signature, accent) and the assembly checker. It works on bare
  geometry too (older hand-built meshes), without the per-part checks.
- **design_set** designs the most important building first and steers each next one away from outlines already used.
- A composed `Assembly` is a starting point: add hand-made parts to it (`asm.add(..., tag=...)`), critique again.

`python3 -m artkit.design <style> <briefs.json> <out>` writes a card per brief (2x, play size, score, findings, reasons).

## Machines (vehicles, turrets, anything with mounts and joints)
Buildings have `Assembly.check()` (UNSUPPORTED, DANGLING, DOOR TO NOWHERE). Machines have `artkit.machine.Machine`:
every part says why it is there, what it is mounted on and how it moves, and `check()` holds the geometry to it.
```python
m = Machine('tank', ground=0.0)                      # ground=None for things that fly
m.add('hull', hull, why='crew and engine')           # the one root
m.add('arm_1', arm, why='holds the wheel axle', on='bracket_1')
m.add('wheel_1', wheel, why='carries the weight onto the track', on='arm_1', turns=(axle_point, (0, 1, 0)))
m.add('turret', turret, why='aims the gun', on='ring_guard', turns=(ring_centre, (0, 0, 1)))    # posable
m.belt('track', circles, y0, y1, thickness, 'rubber', why='...', on='sprocket', wraps=[...], teeth=(pitch, length, height))
assert m.check() == []
g = m.geometry(pose={'turret': 30})
```
- `on`: the part it is mounted on; it must really touch it (FLOATING otherwise). `contact`: other parts it bears on.
- Parts not mounted on each other must not pass through each other (CLASH; convex parts are the solids, a part with
  hollows is added with `convex=False`). A part that turns about a vertical axis is tried at eight headings.
- `turns`: (point, axis); the part must be centred on it (OFF AXIS). Hubs go on the outside of a wheel, not through
  its mount.
- `belt`: one continuous band on the true tangents round its circles (`shapes.belt_path`, `shapes.belt`): it cannot
  open gaps, and every wheel it wraps must carry it (TRACK OFF WHEEL; a roller below the run is reported).
- GROUND: something touches the ground and nothing goes below it. TOO SMALL: under 3 px at the export scale
  (`small_ok=True` with a reason for lines that carry, like a gun barrel, or hidden structure, like a bogie arm).
- **As a unit**: `machine.rig(origin, upper=['turret'], muzzle=, recoil=['gun', ...], headings=8)` is a `MachineRig`
  (an `artkit.rig.Rig`), so `Exporter.rig` exports it and the runtime draws it like any unit: the `upper` subtrees
  are the top layer (it aims on its own; socket = the turret's joint), the rest the bottom layer. Clips: `idle()`,
  `move()` (one cycle = one track pitch; the teeth run back along the band by the distance driven, so the runtime's
  distance-based frames keep the track from sliding), `fire()` (top layer; the `recoil` parts slide back). The canvas
  leaves room for every heading and a shadow. Its shadow layer leaves out top-layer parts that reach far from the axis
  (a gun): the top layer aims on its own in the game, so their shadow would point the wrong way (`shadow_geometry`).
  Use a `"unit_camera"` with `"plates": false` so the tracks keep their outline.
  `python3 -m artkit.demo.blockouts.drive <out>` exports the tank this way and draws it as the runtime does, driving
  in all eight directions (`demo/proposals/m4a3_drive.gif`, `m4a3_headings.png`).
- Example: `demo/blockouts/m4_medium_tank.py` (about 100 parts, `check()` empty). `artkit/tests/machine_check.py`
  puts each fault into a small machine and proves it is reported.

## Rotating buildings
Any still asset can be exported from all four sides: `Exporter.static(key, asset, facings=4)` (or 2). `Asset.facing(q)`
turns the geometry q quarter turns on its footprint; the light stays in the upper left, the footprint swaps for odd
turns, and stages, turning parts and **anchors** (named points such as `door`) turn with it. `assets.json` gets a
`facings` list, each with its own footprint, images and `anchors` (`{"door": {"at": [x, y, z] in tiles, "edge": "+y"}}`;
`+y` and `+x` face the camera). In the browser pass a facing index as the last argument of `ArtKit.drawStatic` and
`drawTurning`; `ArtKit.facingOf(lib, key, i)` gives that view's footprint and door for placement rules.
`design.to_asset(asm)` turns a composed building into such an asset, `design.all_round(asm, style)` scores it from the
four sides, and the composer dresses all four walls (`Brief.all_round`, on by default). `demo/proposals/facings.png`
shows two composed buildings and a demo recipe from every side.

## Hand-built structures
A game's own buildings can live in its style pack as code, written with `artkit.shapes`, `artkit.parts.building` and
`artkit.assembly` (Brass and Bone keeps its 36 in its pack's `buildings/`, with a `CATALOG` of game keys). An
`Assembly` becomes an `Asset` (`asm.asset(name, footprint, states=[...], anchors={'door': ...})`) with footprint, a
`door` anchor (position and which wall it faces) and build / damaged / ruined stages, so
`Exporter.static(key, asset, facings=4)` works on it. `Geometry.warp(fn)` reshapes geometry per corner (lumpy rocks,
stretched hulls) and re-derives face normals and thin flags per polygon; `Assembly(ordered=True)` keeps pieces in the
order added (which of two coplanar faces shows). `Assembly.mark_door` records a door drawn some other way.

## Using artkit in a game
A game keeps a **pinned copy** of this folder as `artkit/` and its own packs in `styles/<pack>/` beside it:
```
<game>/artkit/            this folder, copied at one commit of the engine repository; never edited in the game
<game>/artkit/VENDORED.json   which engine commit, and every file's hash (so a local edit is caught)
<game>/styles/<pack>/     the game's style pack: style.json, tiles, decals, terrain/hud/maps sections, buildings
```
Engine changes are made in the engine repository, tested there (`engine_check.py`), then brought into the game with
the game's update script, and the game's own tests are run. `Style.load()` with no name picks the game's one pack (or
`ARTKIT_STYLE`). The browser runtime (`runtime/`, `maps/mapkit.js`) is inlined or copied into the game the same way.

## Starting a new game
1. **Style pack.** Copy `styles/frontier_outpost` to `styles/<game>`. Write the setting in `about`, pick 8 to 15
   materials, give each a procedural stand-in (`"procedural": {"hull": [[214,214,206], "panel"]}`), set role colours,
   the ground colour, the palette, `game.tile_px`. Paint real tiles later (flat, seamless, evenly lit, no
   perspective) and drop them in `tiles/<name>.png`; they replace the stand-ins with nothing else changed.
2. **Before any geometry**: write briefs for the game's units, vehicles and props the way `DESIGN_METHOD.md` says
   (function, mechanism, scale, references), and agree blockouts with the user.
   Then **buildings**: add a `design` section to the style pack, write briefs, run `artkit.design`, then hand-finish.
   Props and simple structures as recipes (`demo/frontier/recipes/*.json`). Design each from its game mechanic, one
   signature silhouette, one role colour. Add `"states": ["build", "damaged", "ruined"]` and stages are made for you;
   add `"pivots"` for anything that turns.
3. **Terrain** with `heightfield`, `crater`, `rock`, `scatter`, `ribbon` (see `demo/frontier/build.py`, `terrain()`);
   ground tiles, rock atlases and gates with `artkit.terrain` from a `terrain.json`, the HUD skin with `artkit.hud`
   from a `hud.json`, maps with `maps/mapkit.js` and a `maps/templates.js` (copy `styles/frontier_outpost` and
   `styles/frontier_outpost` to start).
4. **Units** with `Rig`: legs, wheels, tracks, rotors, a turret. Humanoid soldiers use `artkit.figure.Biped` with
   `artkit.parts.soldier`; `Exporter.rig` takes either.
5. **Export** with `Exporter`, check with `python3 -m artkit.director <art> <style>`, look with
   `python3 -m artkit.preview <art>`.
6. **In the game**: load `assets.json` with `runtime/artkit.js`, draw through `glcanvas.js`. For several players add a
   `"team"` section and call `ArtKit.teams`; for shadows add `"shadow"` and draw `drawShadow` / `drawUnitShadow`
   first (see Team colours, Shadows).

## Cameras
Isometric is the default and stays the engine's own frame. A game seen from elsewhere names its view in its style
pack and builds its models in that view's axes; nothing else changes:
```json
"camera": {"view": "top_down", "ground": null}
```
- `"view"`: `"iso"` (default) or `"top_down"` (screen x = model x, screen y = model y growing down the screen, depth =
  model z toward the viewer). Any other orthographic view: `"matrix"`, a 3x3 that maps the model's axes into the
  isometric frame (`core.space.Camera`; it must keep handedness). A new named view is added to `Camera.VIEWS`.
- `"ground"`: the model height things stand on (default 0): faces just above it are ground plates and walls darken
  toward it. `null` for things that float, fly or sit in space: no plates, no wear, and shadows lifted away.
- `"plates"`: default true. `false`: things stand on the ground but no face is a ground plate (units: tracks, wheels and
  feet keep their outline; their shadows stay on the ground).
- The light stays where it is **on screen** (upper left) in every view, and so do lines, grain and ambient occlusion.
  `sprite.picture`, `sprite.frame` and `Exporter` (stills, turning strips, rigs, figures, their anchors and marks) all
  follow `style.camera`; `camera=` overrides it per call. `Canvas.around`, `raster`, `space.project`, `depth` and
  `screen_bounds` take `camera=` too.
- Still isometric-only: the design composer and critic, terrain, HUD skins, maps and the browser runtime. They are
  built around the 2:1 tile; a game in another view draws those itself or adds the view to them as a new option.
- **Units can have their own camera**: `"unit_camera"` (same format as `"camera"`) is used for animated unit strips
  (`Exporter.rig`), while stills keep `"camera"`. The usual use is the same view with no ground plates:
  ```json
  "unit_camera": {"view": "iso", "plates": false}
  ```
  `"plates": false` (any camera): things stand on the ground, but no face is a ground plate. Do not use `"ground":
  null` for ground units: that means "flies", and their shadows float away from them.
  Why: with a ground, faces lower than 8 units are treated as ground plates and get no outline against empty space
  (right for a building's yard), which erases the outline under a vehicle's tracks or wheels and under feet. Per call:
  `Exporter.rig(..., camera=)` and `Exporter.static(..., camera=)` (a vehicle exported as a still). Without
  `"unit_camera"` units use `"camera"`, exactly as before.
- `python3 artkit/tests/camera_check.py` proves the default is unchanged, the top-down view is right, and a unit
  camera keeps the outline under tracks while leaving buildings alone.

## Light (finishing rules)
A pack may tune how pictures are finished. Nothing here is on by default; a pack without `"light"` draws exactly as
before (`artkit/tests/light_check.py` proves it):
```json
"light": {"relief": {"strength": 0.4, "span": 40, "ref": 0.9},
          "ao": {"strength": 0.6, "depth": 15, "radii": [[1.5, 0.5], [4, 0.35], [9, 0.15]]},
          "ink": {"cover": 0.75}}
```
- `relief`: darken each pixel by how far it lies behind the picture's nearest point (depth = toward the viewer in the
  pack's camera), up to `strength` at `span` model units. Views that look straight at the tops of things (top-down)
  otherwise give every upward face the same light and read flat; relief gives them height. `ref` (default 1, the
  nearest point) measures from that quantile of the picture's depths instead, so a few tall thin parts (a mast) do not
  darken the rest. Emissive pixels are left alone.
- `ao`: this style's ambient occlusion (`core.light.AO_STRENGTH`, `AO_DEPTH`, `AO` radii in model units). Small
  radii and a shallow depth suit small parts seen close.
- `ink`: `cover`, how far lines go toward the ink colour (default 0.9); lower reads softer. And a **line weight
  hierarchy**, each key optional (any of them switches from `core.ink.lines` to `core.ink.lines_weighted`):
  ```json
  "ink": {"width": 0.75, "inner": 0.5, "step": 4, "crease": 35, "crease_width": 0.35}
  ```
  `width`: the outline as a share of one game pixel (default 1). `inner`: lines inside the figure (a nearer part in
  front of a farther one) as a share of the outline (default 1). `step`: the smallest depth step in model units that
  gets a line (default 12 for hard surfaces, 5 for smooth); lower draws small ledges. `crease`: an angle in degrees;
  hard-surface faces meeting at more than it get a line even with no depth step (a box's own edges), `crease_width`
  wide (default `inner`, or 0.5). Rounded (smooth-look) surfaces never get creases. Why: by default every line has
  the outline's weight and only depth steps over 12 units get one, so outlines read heavy and a box's own edges,
  lips and plates get none. Applies to `sprite.picture` and `sprite.frame` (stills, turning strips); rig and figure
  strips still keep the engine's lines.
- It is `style.lighting` (a `core.light.Rules`, or None). `sprite.picture(..., lighting=)` and `sprite.frame(...,
  lighting=)` override it per call, e.g. `style.lighting.with_(relief_span=90)` for tall terrain.
- Still default-only: rig and figure strips from `Exporter` (they keep the engine constants).

## Team colours
One export, any number of player colours, chosen when the game runs. Nothing changes for a pack without the section
(`artkit/tests/team_check.py` proves it):
```json
"team": {"materials": ["banner", "@faction", "hull@home"], "gain": 1.25}
```
- `materials`: which surfaces wear the player's colour. A plain name matches that material with any role (`banner`,
  `banner@mil`); `@role` matches every material tinted with that role; `name@role` matches exactly. Pick a light,
  fairly plain material: the recolour keeps its light and shade, so white or pale grey takes any colour cleanly.
- `gain`: the brightness of the recolour (the engine's role-tint rule, `core.materials.tint`; default 1.25).
- What the exporter adds (sprites themselves are byte-identical): `<picture>_team.png`, a grey mask the same size as
  its picture (white on team material, soft at its edges), named in the record: a still stage's `"team"`, a turning
  part's `"team"`, a unit clip's `"team": {layer: file}`. After packing a unit has `"team_pack"`: mask pages in exactly
  the layout of its `"pack"` pages, so the same rects cut both. Records gain `"team_gain"`. Pictures with no team
  material get no mask.
- In the browser: `ArtKit.teams(lib, [[220, 60, 50], [60, 120, 230], ...])` once after load makes one recoloured
  copy of every masked picture per colour (load time, never per frame); then pass the colour's index:
  `ArtKit.drawStatic(ctx, lib, key, state, x, y, k, facing, team)`, `drawTurning(..., facing, team)`,
  `drawUnit(ctx, lib, key, {..., team}, x, y, k)`. Without `teams()` or a team index the original pictures draw.
  Memory: one copy of each masked picture per player; unmasked pictures are shared.
- The recolour, in Python `artkit.team.recolour` and in the browser `ArtKit.recolourPixels`:
  `out = mix(rgb, clip(luminance(rgb) * colour * gain), mask)`.
- Per call: `Exporter.static(..., team=False)` / `Exporter.rig(..., team=False)` for none, or an `artkit.team.Team`.
  `sprite.picture(..., team=Team)` puts the mask in `meta['team_mask']`; `core.render.raster(..., team=)` records it.

## Shadows
The engine still bakes no shadows into sprites (the default convention). A pack may ask for them as their own
pictures, which the game draws first, under every sprite, so a shadow lies on the ground and never on a neighbour.
Nothing changes for a pack without the section (`artkit/tests/shadow_check.py` proves it):
```json
"shadow": {"length": 0.6, "dir": [2, 1], "opacity": 0.35, "blur": 1.5, "color": [16, 14, 20], "lift": 40}
```
- Every key is optional (`"shadow": {}` gives these defaults). `length`: ground distance per unit of height. `dir`:
  the way shadows fall **on screen** (down-right, away from the upper-left light); the ground direction is worked out
  through the pack's camera, so the same numbers suit isometric and top-down. `opacity`: the darkest it gets;
  overlapping parts never darken twice. `blur`: softness in output pixels. `color`: RGB. `lift`: for cameras with
  `"ground": null` (flying, floating), the height taken under the lowest point, so the shadow sits apart from the thing.
- Stills: each stage gets `<picture>_shadow.png` and `"shadow": {"src", "size", "near_corner", "origin"}` in its
  record: place it with the same point as the sprite. `ArtKit.drawShadow(ctx, lib, key, state, x, y, k, facing)`.
  Turning parts are not in the still's shadow (they are small and turn).
- Units: a layer `"S"` (frame, anchor, packed rects, like `L` and `U`): the whole body's shadow, in the clips that
  draw the legs. `ArtKit.drawUnitShadow(ctx, lib, key, {clip, frame, heading}, x, y, k)` with the legs' clip and
  frame. A unit whose shadow reaches past its canvas is cut at the canvas edge: widen the rig's canvas if it shows.
- Cost: flat polygons filled at 4x and blurred, no light or lines (a small part of a sprite's render); in the game
  one quad per thing, batched with everything else.
- Per call: `Exporter.static(..., shadow=False)` / `Exporter.rig(..., shadow=False)`, or an `artkit.shadow.Shadow`.

`demo/proposals/teams_and_shadows.png`: the Frontier turret and walker from one export, in four player colours, with
shadows (`"team": {"materials": ["orange", "hull"]}, "shadow": {"length": 0.6}`).

## Cards
For card games, autobattlers, build menus and tooltips: one framed picture per place, with its name in a box above
the art. Nothing changes for a game that does not use it (no other module imports `card.py`); `python3
artkit/tests/card_check.py` proves it works.
```python
from artkit.card import Scene, render, review
sc = Scene('Basic Farm', slab='soil')                    # a 400-unit square plot; slab: earth under it in iso
sc.add('plot', shapes.block(0, 400, 0, 400, -4, 0, 'grass'), 'the land', ground=True)
sc.add('barn walls', shapes.box(130, 90, 64, 'barn').move(50, 55, 0), 'the one shape that says farm')
sc.add('barn roof', shapes.gable(130, 90, 46, 'barn').move(50, 55, 70), 'all you see from above', cover=True)
sc.check()                                               # [] when every part has a reason and stays on the plot
img, meta = render(sc, style, view='iso')                # or 'top_down'; meta: window, name_box, parts_box, clipped
review(sc, style).save('farm_review.png')                # grey blockout beside the card (DESIGN_METHOD review)
```
`python3 -m artkit.card <scene.py ...> --style <pack> [--view iso|top_down] --out <dir>`: each file defines
`build()` returning a `Scene` (or a list); writes `<name>_<view>.png` and `<name>_<view>_review.png` and prints
`check()` issues.
- **Views.** `iso` (default): the plot as a thick tile, its earth sides showing, on a backdrop; walls, doors and
  heights read, so places are told apart at a glance. The tile is twice as wide as tall, so the card crops its side
  corners (`crop`) but never a standing part. `top_down`: the plot fills the window; roofs carry the colour (a wall
  is not seen), height comes from cast shadows and the pack's `light.relief`.
- **Layers**, bottom up: ground parts, cast shadows of everything else (the pack's `"shadow"`, else
  `artkit.shadow` defaults), everything else. Both views use the engine's cameras with the ground at z = 0.
- **Blockout**: `render(..., blockout=True)` draws ground parts dark grey, `cover` parts (roofs, canopies) light, the
  rest mid, from engine greys (packs need no grey materials).
- **The pack's `"card"` section** (every key optional): `size` (256), `border` (8), `gap` (4), `name_h` (24),
  `font` (a .ttf; default DejaVu Sans Bold, else Pillow's font), `font_size` (15; long names shrink to fit), `view`
  (`"iso"`), `crop` (0.78), `slab` (30 units; 0 for none), `shadow` (true), `iso_relief` (false: relief is for
  views that look straight down), colours `frame`, `trim`, `line`, `name_fill`, `name_ink`, `backdrop` (RGB).
- The frame and name box are flat 2D (Pillow); a game wanting its own frame takes `card.art(scene, style, win, view)`,
  the art window alone.

## 3D models and paintovers
Every asset is a full 3D model before it is a sprite. `artkit/mesh.py` lets it leave the engine as a real 3D file
and come back painted, so a hand-drawn layer sits on the code-built geometry and still follows every facing, stage
and turning part. It is an addition: nothing draws differently unless a game draws the painted model.
```
python3 -m artkit.mesh export  <asset> <out> [--key K] [--style P] [--facings 4] [--view-scale 1] [--density D]
python3 -m artkit.mesh project <out> <key> <painting.png> [--facing q] [--keep-light]
python3 -m artkit.mesh preview <out> <key> [--scale 0.4]
```
`<asset>` is a recipe `.json` or `module:function[:argument]` returning an Asset, Geometry or recipe (run from the
game's folder, e.g. `styles.<pack>.buildings:asset:<key>`). `export` writes:
- `<key>.obj`, `<key>.mtl`: the model, Y-up, one tile = 1 unit, textured with the atlas.
- `<key>_paint.png`: the **paint atlas**, the model's own materials unlit (colour before light); every source polygon
  has its own island, walls upright, tops as the screen sees them. `<key>_base.png` is an untouched copy.
  `<key>_layout.npz` maps texels to triangles. Density defaults to the finest tile on the model, so nothing is lost.
- `<key>_view<q>.png`: the finished render of each facing at `--view-scale` (1 = 2.5 times export size), to paint
  over; `<key>_views.json` records how to map each one back.

Three ways to paint, all ending in `<key>_paint.png`:
1. **Over a view** (the projection workflow): paint on `<key>_view<q>.png` in any image editor, as a layer with
   transparency or flattened, at the same size or larger at the same proportions; `project` puts it on the faces
   seen in that view (hidden faces untouched, faces nearly edge-on fade out). It divides out the face light and wear
   the renderer gave each face, so light you paint is not applied twice (`--keep-light` to skip). Project several
   facings in turn to cover all sides.
2. **In a 3D painter** (Blender texture paint, Substance, ...): import the OBJ, paint on the model, save the
   texture over `<key>_paint.png`. To match the game's view in Blender: orthographic camera at rotation
   (60, 0, -45) degrees, i.e. 30 degrees down, looking from +x +y; the engine's projection keeps heights at 0.8165
   of a true camera's, so scale the object's Z by 0.8165 while painting to see exactly the game's view (UVs are
   unaffected).
3. **Directly on the atlas** in an image editor (flat walls and roofs read as they are).

In a game's export: `lay = mesh.Layout.load(...)`, `atlas = mesh.load_atlas(path, lay)`,
`Exporter.static(key, mesh.paint_asset(asset, lay, atlas, style.materials(), name='paint:' + key), facings=4)`.
The renderer still lights the atlas from the upper left and adds wear, ambient occlusion and the even line. A layout
belongs to one model (triangles, polygons, materials); facings share it, a rebuilt model needs a new one (`bake`
refuses a mismatch). Glowing materials keep glowing, wire keeps casting no line. The design critic judges materials
by name, so critique the unpainted model. `python3 artkit/tests/mesh_check.py` (about 1.5 minutes) proves the round
trip (a model wearing its own bake draws within a few colour levels in every facing, stage and turning part), the
OBJ, and projection.

## Tests
`python3 artkit/tests/run_all.py` must print ALL PASS for any change meant to leave the art alone (about 4 minutes).
It runs every `tests/*_check.py`, so a new option's check joins by being added; `run_all.py camera light` runs only
those, `--list` shows them.

| Check | What it proves | About |
|---|---|---|
| `rules_check.py` | The four rules files say the same thing. | 1 s |
| `camera_check.py` | Other cameras are additions; the isometric default is unchanged. | seconds |
| `card_check.py` | Cards render in both views; `shapes.pyramid` faces outward. | 10 s |
| `clearance_check.py` | `clearance.check` finds clashes, the ground, allowed pairs, and nothing else. | 1 s |
| `light_check.py` | The `"light"` section and line hierarchy change nothing unless asked for. | seconds |
| `machine_check.py` | `Machine.check()` finds each fault; the demo tank and its rig pass. | 15 s |
| `mesh_check.py` | Models out as OBJ and paint back in, nothing else changed. | 1.5 min |
| `shadow_check.py`, `team_check.py` | Shadows and team colours only add files; sprites stay byte-identical. | 20 s, 30 s |
| `engine_check.py` | The whole engine on the demo pack against `expected_engine.txt`. | 2 min |

After a deliberate change, look at the pictures, then `python3 artkit/tests/engine_check.py --write` and say so in the
commit. `tests/maps_identity.js` is not an engine check: a game points it at its own map templates. A game that uses
artkit keeps its own identity tests against its shipped art (Brass and Bone: `tests/identity.py`,
`tests/identity_kits.py`, `tests/design_check.py` in its repository); run them before updating its pinned copy.

## Known limits
- The two looks keep their own legacy maths (light formula, pixel coverage, precision), so old art stays identical. A
  style may unify them later; that re-lights everything made in it.
- Faces, cloth and dense foliage are simple; fire, smoke, water and weather stay as in-game effects.
- Figures (`Biped`, `Tripod`) are drawn with the figure material registry and their own line pass, not the style's
  materials.
- The composer gives a building its theme and a readable outline, not its character: the mechanic-specific pieces
  (a gear train, a vault door, a washing line) are still added by hand on top of the composed assembly. Its plans
  are few (setback, wing right, wing forward). The critic's numbers are calibrated on one reference, the Command
  Hall; treat a score as a prompt to look, not a verdict.
