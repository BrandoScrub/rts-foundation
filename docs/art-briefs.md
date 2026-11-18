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

## Units: eight figures in the game (Nov 17, second pass)
User: "a more distinctive flair, closer to fantasy than medieval". Each race now has its own build and one
exaggerated signature, and the realm's crystal glows on weapons and shields. Briefs are the docstring of
`styles/fantasy_realm/units.py`; every attached part has its reason as its label. `python3 tools/build_units.py`
renders a sheet per unit and player (creeps: one neutral sheet): 8 headings x idle, 8 walk frames, 5 attack
frames. Line-up: `docs/blockouts/units_lineup_4.png` (rows: idle, attack, from behind).

| Figure | Signature | What still feels off |
|---|---|---|
| Peasant | tall bent pointed hat with a brim, pack, tool | one tool for every job; a carried load is a coloured dot |
| Militia | cowl in the player colour, crystal-bossed round shield, broad falchion | the leather body is dark against dark ground |
| Man-at-Arms | winged helm and plume, cape, big pauldrons, kite shield | busy at play size; the wings are thin |
| Dwarf Pikeman | horned helm, red beard, barrel body, tall pike with a crystal blade | the thrust is a lean, not a real lunge |
| Elf Archer | tallest and thinnest, pale hair, long ears, cloak, tall bow | the bow is hard to see from the front; no arrow or string |
| Halfling Slinger | smallest, curls, bare feet, pack with a pot | the sling is a few pixels |
| Goblin Raider | green, big ears, hunched, bone spear | reuses the human strike |
| Ogre Brute | twice a human, slab shoulders, belly, studded club | head is a plain ball; the knees show seams |

Not made yet: Wolf Rider, wolves, sheep, deer, boar (all need a four-legged rig); death animations; shadows.
