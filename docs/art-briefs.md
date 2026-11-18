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

## Units: first three figures in the game (Nov 17)
Briefs are the docstring of `styles/fantasy_realm/units.py`; every attached part has its reason as its label.
`python3 tools/build_units.py` renders a sheet per unit and player (8 headings x idle, walk, strike) into
`game/art/u_<key>_<player>.png`. Picture: `docs/blockouts/in_game_3.png`.

| Figure | Reads as | What still feels off |
|---|---|---|
| Peasant | wide straw hat, tunic in the player colour, tool in hand | one tool (an axe) for every job; nothing carried on the back; no woman variant |
| Militia | iron cap, round shield, short sword | the shield hides at some headings; the strike is the peasant's chop |
| Man-at-Arms | mail, tall nasal helm, kite shield, coloured mantle | mail reads as plain grey at play size |

Not made yet: Dwarf Pikeman, Elf Archer, Halfling Slinger, Wolf Rider (needs a four-legged rig), sheep, deer, boar,
wolves, goblins, ogres; death animations; shadows.
