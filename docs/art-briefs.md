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

## Units: briefs only, no geometry yet
Held until the building language is agreed, because the figures must match it. artkit's figure engine (`Biped`)
ships with modern soldier parts, so fantasy bodies, clothes and tools are new parts for this pack.

**Peasant.** Is: a farmhand of the realm. Does: gathers, builds, repairs, hides in the Town Hall. Gameplay: the
most numerous unit; the player must tell what each one is doing, so the carried tool or load is the largest
feature (axe, pick, hoe, sack, basket). Moves: walks; work swings from the shoulder. Made of: tunic in the player
colour, hood or straw hat, bare forearms. References: AoE2 Villager (task shown by what is carried), medieval
labourers in the Luttrell Psalter (hood, short tunic, hose). Reads at play size: a small figure, a block of
player colour, one tool.

**Militia / Man-at-Arms.** Is: a levy with a sword and a round shield, later mail and a kite shield. Does:
front-line infantry; carries artifacts. Gameplay: must read as "armed" against the Peasant at 30 px: shield on
the left as the biggest shape, weapon raised to the right. The upgrade swaps the shield shape and adds a helmet
and mail (a lighter value block), so the player sees the research. References: AoE2 Militia and Man-at-Arms
(silhouette changes with the upgrade), Bayeux Tapestry fyrd and Norman foot. Reads at play size: shield disc,
helmet dot, player-colour tunic.
