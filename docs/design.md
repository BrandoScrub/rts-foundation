# RTS Foundation: design record (Dark Age and Feudal Age)

An Age of Empires II economy and tech game in a Warcraft III fantasy world, without heroes. When a rule is in
doubt, we copy what AoE2 (Definitive Edition) does. Every number lives in `game/src/data.js`, with the AoE2 value it
comes from in a comment.

## Decided (Nov 17 2026)
| Question | Decision |
|---|---|
| Engine | Browser (HTML5 + JavaScript, no build step). Art through artkit (pinned in `artkit/`), WebGL batching through artkit's `glcanvas.js` (falls back to Canvas 2D; `?gl=0` forces it). |
| View | 2D isometric, AoE2 style, artkit conventions: 2:1, 64 px tile, light from the upper left. |
| Map | 300 x 300 tiles (AoE2 Giant is 240). Players start in opposite corners (north and south on screen). Smooth hills built into the ground (corner heights 0 to 6, at most one level per tile, so no cliffs yet). Point-symmetric so both starts are equal. |
| Opponent | Idle placeholder: a full enemy start (Town Hall, 3 Peasants, Scout) that does nothing. Destroying everything it has wins. |
| Factions | One shared faction for both players. |
| Resources | Basic: food, wood, stone (the foundation of the early game). Premium: **iron** (military, takes AoE2 gold's role for soldiers and armour) and **crystal** (magic, age-ups and mystic techs from tier 2). |
| Creep camps | Clearing a camp **unwards the deposit it guards** (crystal or iron you cannot mine before) and **drops artifacts** that work like AoE2 relics. No XP (no heroes). |
| Mobile (Nov 17) | Touch controls copied from Brass and Bone: auto below 900 px wide (or a touch screen up to 1100), forced Mobile/Desktop in F1. Tap selects or orders, double-tap selects the type on screen, hold-drag boxes, hold toggles a unit, drag pans, pinch zooms; right-hand rail (Build, Box, Idle, Army, Screen, Move/Attack, Clear, Map); group slots 1-5; pinned building ghost with Place and Repeat; hold the minimap to send troops; hold a command button for its tooltip. |
| Tier 2 counters (Nov 17) | A fantasy races mix, built into the one shared faction (trained from normal buildings), in the classic set: dwarf pikemen (spear), elf archers (archer), halfling slingers (skirmisher), wolf riders (light cavalry), human men-at-arms (infantry upgrade). Same counters as AoE2. Not built yet. |
| Tier 2 cost (Nov 17) | 500 food, no crystal, plus two tier 1 buildings: exactly AoE2's Feudal Age. Crystal first matters from tier 3. |
| Opponent (Nov 17) | Stays idle for now. |
| River (Nov 17, built) | A river runs corner to corner between the players. Deep water blocks; five shallow fords cross it: the wide centre ford, held by the Ogre Stronghold and its crystal, and two pairs further out. Banks slope down into a valley. |
| Fishing (Nov 17, built) | Shore fish only: schools along the river banks (AoE2 DE shore fish: 200 food, fisherman 0.43/s), gathered by peasants from the bank and dropped at a Mill or Town Hall. No Dock or boats. |
| Art timing (Nov 17) | Not yet for buildings and units; the **ground is made through the art engine now** (user, Nov 17): style pack `styles/fantasy_realm/` (terrain.json recipes) -> `python3 tools/build_ground.py` -> `game/art/ground_realm_*.jpg`, blended on the height field in the game. |
| Structure first (Nov 17) | Mechanics and structure before content. See Foundations below. |
| As close to AoE2 as possible, through the Feudal Age (Nov 17) | Research in `docs/aoe2-research.md`. Ages 1 and 2 are built; the Castle Age shows locked. |
| Ore generation (Nov 17) | Iron and crystal each generate exactly like AoE2 gold: a 7-tile and two 4-tile mines by every Town Hall, scattered 3-tile piles, 800 a tile, gold mining rate, 100 of each to start. |
| Camp ore (Nov 17) | Kept as bonus veins on top of the AoE2 layout; camps still drop artifacts. |
| Gold prices (Nov 17) | Units pay **iron** where AoE2 charges gold; technologies pay **crystal**. The Market trades in iron. |
| Art (Nov 17) | Start artkit briefs and grey blockouts now, after the Feudal mechanics. Then "focus on art": all 16 buildings are designed as blockouts (brief and a reason per part), rendered through artkit in player colours and drawn in the game (`tools/build_buildings.py`). Units are still code-drawn. See `docs/art-briefs.md`. |
| Art | Gameplay first with placeholder sprites drawn in code; real art follows artkit's DESIGN_METHOD (briefs, then grey blockouts for approval). |

## How AoE2 was followed (tier 1 = Dark Age)
- Start: 200 food, 200 wood, 200 stone, 100 iron (AoE2 gold), 0 crystal; Town Hall, 3 Peasants, 1 Scout; population 4/5.
- Peasant (Villager): 25 HP, 3 attack, 0.8 speed, carries 10, 50 food, 25 s. Gather rates: forager 0.31, hunter 0.41,
  shepherd 0.33, farmer 0.32, lumberjack 0.39, stone 0.36, iron 0.38 (AoE2 gold). Crystal 0.30 (ours: premium).
- Switching resource type drops what was carried. When a node runs out the peasant moves to the nearest one of the
  same kind. Builders of a Lumber or Mining Camp or Mill start gathering beside it; a Farm's builder farms it.
- Several builders: total time 3T/(n+2). Repair: 750 HP a minute for half the building's cost.
- Herdables belong to whoever's unit is near; deer flee; the boar fights back. Kills leave carcasses.
- Buildings: Town Hall (Town Center, not buildable until tier 3), Cottage (House, +5 pop), Mill, Lumber Camp, Mining
  Camp, Farm (175 food, reseeds itself for 60 wood like DE's auto-reseed), Barracks, Palisade (2 wood a tile, drag to
  lay), Palisade Gate (simplified to one tile), Watchpost (Outpost). Population limit 200.
- Units: Militia (60 food, 20 iron: AoE2's 20 gold), Scout Rider (start only; trained from tier 2 like AoE2's stable).
- Techs: Loom (50 iron), Town Watch (75 food). Tier 2 is shown and locked (AoE2: 500 food and two buildings).
- Town Hall arrows: one, plus one per garrisoned peasant; Town Bell and All Clear.
- Elevation: +25% damage from higher ground, -25% from lower. Damage is at least 1.
- Fog: black where never seen, dim where explored but not in sight.
- Artifacts: carried by Militia (AoE2: Monks, which come later), stored in a Town Hall, 0.5 crystal a second each
  (AoE2 relic: 0.5 gold a second).

## Foundations (Nov 17)
- **Commands.** Every player action is data (`world.issue(player, {c: ...})`), run at the start of the next tick and
  logged. The HUD, a future AI and replays all use it; nothing in the UI changes the world directly.
- **Determinism.** One seeded random source for the simulation, fixed 30 Hz ticks: the same seed and commands give
  the same game (`world.hash()`), and the command log replays a game exactly. Groundwork for lockstep multiplayer.
- **Pathing.** A* on the tile grid with a node budget per tick (a big order spreads over a few ticks instead of
  freezing a frame); a group shares one path; corners on the way count as reached when close, so crowds flow.
- **Work spots.** Peasants on the same tree, mine or building spread around it while staying in reach.
- **Fog memory.** Other players' buildings show as last seen until the spot is seen again (AoE2).
- **Drawing.** Units are drawn between ticks (interpolated), so movement is smooth at any frame rate.
- **Picking.** In screen space against what is drawn: a unit's body, a building's silhouette, a tree's sprite; the
  front-most wins; a finger gets more slack. The canvas re-measures itself every frame, so taps and drawing agree.

## Feudal Age and AoE2 systems (built Nov 17)
- **Damage:** AoE2's formula with attack and armour classes; buildings have melee/pierce armour.
- **Counters:** Dwarf Pikeman (Spearman, +15 vs cavalry), Elf Archer (Archer), Halfling Slinger (Skirmisher, +3 vs
  archers, minimum range), Wolf Rider (Scout Cavalry, stronger in Feudal), Man-at-Arms (Militia upgrade). AoE2 stats.
- **Arrows** fly at 7 tiles a second and can miss (Archer 80%, Slinger 90%).
- **Stances:** Aggressive, Defensive, Stand Ground, No Attack. **Formations:** Line, Staggered, Box, Flank; a group
  walks at its slowest member's speed. **Patrol.**
- **Buildings:** Archery Range and Stable (need a Barracks), Blacksmith, Market (needs a Mill), Watch Tower, Stone
  Wall, Stone Gate. Two build pages, economic and military, as in AoE2.
- **Research:** Loom; Wheelbarrow, Town Watch; Horse Collar; Double-Bit Axe; Ore Mining (AoE2 Gold Mining, both
  ores), Stone Mining; Man-at-Arms, Supplies; Bloodlines; Forging, Scale Mail, Scale Barding, Fletching, Padded
  Archer Armour.
- **Market:** buy or sell 100 food, wood or stone for iron; 30% fee; each trade moves the price by 3.
- **Town Hall** shoots only when units are inside (one arrow each); a **Watch Tower** shoots one arrow, more with a
  garrison.
- Changed to match AoE2: Militia 50 food 20 iron; Palisade 3 wood, 150 HP; Palisade Gate 30 wood; Town Watch moved
  to the Feudal Age; 6 berry bushes.

## Creep camps (Warcraft III style)
Guards stand at home, attack anything that comes within 5 tiles, call the whole camp in when one is hit, chase up to
11 tiles from home, then walk back healing. Per side: 2 Wolf Dens (crystal x4), 2 Goblin Outposts (iron x7, 1
artifact), 1 Ogre Lair (crystal x6, 1 artifact); in the middle one Ogre Stronghold (crystal x10, 2 artifacts).
Each player's home also has free iron (7 + 4 + 4), stone (5 + 5), berries, 6 sheep, 2 boar, 4 deer and woodlines,
like AoE2 Arabia.

## Open questions
1. Castle Age content (age 3): not started. Who carries artifacts once there is a temple (AoE2 Monastery and Monks)?
2. Should crystal be buyable at the Market, or stay mine-only?
3. An AI for the opponent (it is still idle).
4. Art: approve or change the grey blockouts before any detail is added.
