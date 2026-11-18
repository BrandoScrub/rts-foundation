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

Not made yet: walls that join their neighbours, tool per job, carried loads, building damage and rubble.
