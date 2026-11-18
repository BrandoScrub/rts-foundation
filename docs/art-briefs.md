# Art briefs and blockouts (artkit/DESIGN_METHOD.md)

Nothing here is detailed art. A blockout is flat grey masses with a reason for every part, shown for approval first.

## Buildings: blockout 2 (Nov 17), in the game
All 16 buildings of the Dark and Feudal Ages (the Farm stays a ground field) are in
`styles/fantasy_realm/blockouts/buildings.py`: a brief, references and a one-line reason for every part; the
checker reports nothing for any of them. `python3 tools/build_buildings.py` renders them through artkit with the
pack's stand-in materials and each player's colour (roofs and one accent) into `game/art/`, and the game draws
them. This is still blockout level: masses and material colours, no windows, beams, wear or props beyond the ones
that identify the building. Picture: `docs/blockouts/in_game_2.png`.

Changed since blockout 1: Town Hall door moved to the gable end (it was hidden by the porch) with a coloured
frame, a stone course and loophole on the keep; Barracks has a cookhouse stack at the back; Watch Tower has a
straight shaft on a stepped foot and a taller roof clear of the deck.

What still feels off, to fix in the detail pass or on the user's word:
- People are drawn about twice as large as the buildings' doors imply (AoE2 does the same; ours is stronger).
- The Mill's sails face away from some angles and its store hides the door.
- Market and Blacksmith yards are plain paving; Archery Range is mostly empty ground.
- Walls are single tiles that repeat; they do not yet pick a shape from their neighbours.
- No construction, damage or ruin stages from the engine yet (foundations are still the code-drawn scaffold).
- No shadows.

## Units: thirteen figures in the game (Nov 17, third pass)
User: "Push farther, polish those 8, then continue". Weapons are about a third larger, crystal glows on every
realm figure (hat band, helm brow, sword fuller, pike blade, bow string, sling shard), the wild glows a sour
magenta instead (creep eyes, the goblin's spear, shards beaten into the ogre's club), and the shapes are stranger.
Briefs are the docstrings in `styles/fantasy_realm/units.py`. `python3 tools/build_units.py` renders a sheet per
unit and player (wild things: one neutral sheet): 8 headings x idle, 8 walk, 5 attack, 8 death frames; each unit
has its own cell, origin and draw scale in `game/art/units.json`. Line-up: `docs/blockouts/units_lineup_5.png`
(rows: idle, attack, dead).

| Figure | Signature | What still feels off |
|---|---|---|
| Peasant | very tall bent hat with a crystal on the band, pack, big axe | one tool for every job; a carried load is a coloured dot |
| Militia | long-tailed cowl with an iron face-plate, player-colour body, glowing cleaver, crystal-bossed shield | - |
| Man-at-Arms | thick swept helm wings, tall plume, spiked pauldrons, greatsword with a glowing fuller | dense at play size |
| Dwarf Pikeman | wide horns, rune-stone brow, long red beard, pike with a crystal blade and cross-guard | the thrust is a lean, not a lunge |
| Elf Archer | antlered hood with a circlet, tall bow with a string of light | no arrow on the string |
| Halfling Slinger | cooking pot worn as a helmet, bare feet, slings crystal shards | small: reads mostly by the pot |
| Wolf Rider | halfling scout on a saddled dire wolf, crystal lance and pennon | rider sits stiff; no lance thrust (the wolf bites) |
| Goblin Raider | long ears, big jaw, glowing eyes, sour-shard spear | reuses the human strike |
| Ogre Brute | big jawed head with tusks and a horn, glowing eyes, club with shards | knees show seams |
| Dire Wolf | high shoulders, spiked dark mane, glowing eyes | legs are straight tubes |
| Boar, Deer, Sheep | bristle ridge and tusks; antlers and pale rump; wool ball with curled horns | grazing animals have no head-down idle |

Four-legged figures use `artkit.rig.Rig` (`quadruped()` and `quad_clips()` in units.py): four IK legs, a neck and a
tail joint, a trot, a bite and a fall onto the side. Deaths: a killed unit leaves a picture (`fx` kind `corpse`)
that plays the death frames, lies 14 s and fades; hunted animals play theirs and stay as the carcass. Shadows are
soft ellipses drawn by the game, down and right of the figure or building (artkit bakes none).

## Fourth pass (Nov 17): weak spots, then building detail
User: "Weak spots first. Then building details".
- **Wolf Rider:** rider and lance are their own joints; he leans into the trot and couches the lance to strike.
- **Elf Archer:** an arrow of light on the string. **Peasant:** four sheets, one per tool (axe: wood and meat; pick:
  ore and stone; hammer: building and repair; hoe: farms), chosen by the job (`u.job`); the carried load is drawn on
  the back (logs, sack, stone, ore, shard). **Shadows** are stronger.
- Unit sheets are saved with 255 colours (a fifth of the size, no visible change).
- **Walls join:** Palisade, Stone Wall and both gates have three pictures: a straight run along x (`_x`), along y
  (`_y`), and the corner piece (plain key: corner, crossing or alone; a king post or a turret). The game picks by
  the neighbours on the four sides (`wallKey` in render.js); any building counts as a neighbour. Gates turn with
  the wall. Not done: diagonal runs (AoE2 has them), wall ends.
- **Construction:** one site picture per footprint size (`site_1..4`: stripped earth, corner poles, ledgers, piled
  timber and stone), then the building rises inside it from 15% (the finished picture revealed from the ground up).
- **Damage:** flames and smoke below 75%, 50% and 25% hit points (AoE2), drawn by the game. **Rubble:** `rubble_1..4`,
  left for 40 s, fading (AoE2).

## Fifth pass (Nov 17): one style for everything
User: "Detail walls, fix shadows, make artwork all have the same style (ground, units, buildings, terrain), work on
trees, ores and any other missing passes."
- **Nothing on the map is drawn in code any more** except shore fish (shapes under the water), fire and smoke, and
  the peasant's carried load. Trees, stone, iron, crystal, berries, the relic and the camps' dressing are engine
  props: `styles/fantasy_realm/props.py` -> `python3 tools/build_props.py` -> `game/art/p_<key>.png`, `props.json`.
  Same materials (`style.json` "procedural"), light, outline and scale (0.4 px a unit, drawn at half) as buildings.
- **Trees:** three oaks (forked leaning trunk, wide dark crown; one with glowing lantern fungus) and three black
  pines; the game picks one of six per tile. **Stone** pale with squared blocks; **iron** blue-black with rust and
  metal; **crystal** a fan of glowing cyan spikes; **berries** a dark bush dotted red; **relic** a carved stone
  under a golden light.
- **Camps** have a landmark behind the guards (dressing, walked over): Wolf Den (rock mound, black mouth, bones),
  Goblin Outpost (hide tents, stakes, skull totem, fire), Ogre Lair and Stronghold (rib-and-hide hut, totems,
  glowing cauldron). All carry the wild's magenta shard.
- **Farm** is an engine building now: furrows, crop rows, a low fence, a scarecrow in the owner's colour.
- **Shadows are cast shadows** (artkit's `shadow` option, pack section "shadow": length 0.72, down-right, 50%):
  every building, prop and unit frame has its own shadow picture (`*_s.png`), and the game draws all shadows
  first, under every sprite. The soft ellipses are gone.
- **Walls:** uneven hand-cut logs with two lashed rails and a banded king post; stone curtain with a plank
  wall-walk, string course, buttress and arrow loops; corner turrets with loops, a watch fire and a pennant in the
  owner's colour. **Diagonal runs** have their own pieces (`_d1`, `_d2`) for Palisade and Stone Wall.

## Sixth pass (Nov 17): building detail, then the small fixes
User: "Building pass first, then immediately do smaller fixes above".
- **Detail helpers** on `Block` (buildings.py), all on the two faces the camera sees: `framing` (half-timbering: dark
  beams, daub panels, corner braces), `windows` (frame, lit amber pane, mullion, sill, shutters), `quoins` (pale
  dressed corner stones), `doorway` (jambs, lintel, open leaf, threshold), `gable_end` (daub triangle, king post,
  collar, barge boards), `finial` (a crystal on the peak). Every part still carries its reason; `findings()` empty.
- **Materials** (tools/build_buildings.py): roofs are slates in staggered courses, each a shade of its own; stone is
  coursed masonry with staggered joints; thatch is combed in laps; yards are trodden earth, not planks. New pack
  materials: `beam`, `plaster`, `window` (glows), `soil`, `crop`.
- **Per building:** Town Hall (half-timbered hall, lit windows, closed gable, quoined undercroft, keep windows,
  crystal finial and door lanterns), Barracks (framing, windows, shields on the gable, spears in the rack), Watch
  Tower (quoins, lit window, doorway, signal fire, finial), Cottage (framing, windows, loft window, woodpile,
  lantern), Mill (stone bands, lit window, millstone), Lumber Camp (chopping block and axe, chips, lantern), Mining
  Camp (quoins, window, pick, lantern), Blacksmith (quoins, windows, chimney cap with fire glow, ingots, water in
  the trough), Market (quoins, windows, wares on the stalls, a well), Archery Range (arrow barrel, shooting line),
  Stable (framing, loft, water, saddle).
- **Small fixes:** shadows 60% (were 50%); both gates have diagonal pieces; the Farm shows what is left (full, half
  the rows cut, all stubble); felled trees leave stumps; the building site is dug earth with foundation trenches
  and a spoil heap; sheep and deer lower their heads to graze; camp landmarks are 1.5x so a tent is bigger than
  its goblin (checked in the game).

## Seventh pass (Nov 17): smoke, Watchpost, walls, HUD icons
- Chimney smoke on the Town Hall, Barracks, Cottage and Blacksmith (positions come from the model: `b.smoke`).
- Watchpost: thatch canopy, platform rails, ladder rungs, crystal lantern, warning horn, shield in the owner's colour.
- Stone curtain: a lit torch basket on each buttress, moss at the foot. Palisade corner: a rag in the owner's colour.
- `tools/build_icons.py`: 124 HUD icons in one atlas, cut from the unit sheets, building and prop pictures;
  technologies are the thing they improve with a gold chevron; commands and resources are drawn signs.

Still off: a diagonal wall on a slope steps at each tile (each piece stands at its own tile's height); a wall
running straight toward the camera shows mostly its top; windows and framing are only on the two seen faces (the
camera never turns); no smoke from chimneys; Watchpost and walls got no extra pass this round.
