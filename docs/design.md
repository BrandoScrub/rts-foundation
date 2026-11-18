# RTS Foundation: design record (Dark Age to Castle Age)

An Age of Empires II economy and tech game in a Warcraft III fantasy world, without heroes. When a rule is in
doubt, we copy what AoE2 (Definitive Edition) does. Every number lives in `game/src/data.js`, with the AoE2 value it
comes from in a comment.

## Decided (Nov 17 2026)
| Question | Decision |
|---|---|
| Engine | Browser (HTML5 + JavaScript, no build step). Art through artkit (pinned in `artkit/`), WebGL batching through artkit's `glcanvas.js` (falls back to Canvas 2D; `?gl=0` forces it). |
| View | 2D isometric, AoE2 style, artkit conventions: 2:1, 64 px tile, light from the upper left. |
| Map | 300 x 300 tiles (AoE2 Giant is 240). Players start in opposite corners (north and south on screen). Smooth hills built into the ground (corner heights 0 to 6, at most one level per tile, so no cliffs yet). Point-symmetric so both starts are equal. |
| Opponent (first build) | Idle placeholder: a full enemy start (Town Hall, 3 Peasants, Scout) that does nothing. Destroying everything it has wins. |
| Factions | One shared faction for both players. |
| Resources | Basic: food, wood, stone (the foundation of the early game). Premium: **iron** (military, takes AoE2 gold's role for soldiers and armour) and **crystal** (magic, age-ups and mystic techs from tier 2). |
| Creep camps | Clearing a camp **unwards the deposit it guards** (crystal or iron you cannot mine before) and **drops artifacts** that work like AoE2 relics. No XP (no heroes). |
| Mobile (Nov 17) | Touch controls copied from Brass and Bone: auto below 900 px wide (or a touch screen up to 1100), forced Mobile/Desktop in F1. Tap selects or orders, double-tap selects the type on screen, hold-drag boxes, hold toggles a unit, drag pans, pinch zooms; right-hand rail (Build, Box, Idle, Army, Screen, Move/Attack, Clear, Map); group slots 1-5; pinned building ghost with Place and Repeat; hold the minimap to send troops; hold a command button for its tooltip. |
| Tier 2 counters (Nov 17) | A fantasy races mix, built into the one shared faction (trained from normal buildings), in the classic set: dwarf pikemen (spear), elf archers (archer), halfling slingers (skirmisher), wolf riders (light cavalry), human men-at-arms (infantry upgrade). Same counters as AoE2. Not built yet. |
| Tier 2 cost (Nov 17) | 500 food, no crystal, plus two tier 1 buildings: exactly AoE2's Feudal Age. Crystal first matters from tier 3. |
| Opponent (Nov 17) | Stays idle for now. |
| Opponent AI (Nov 17, begun) | "Begin work on enemy AI" (user). The opponent is now a computer player; `?ai=0` brings back the idle one. See Opponent AI below. |
| River (Nov 17, built) | A river runs corner to corner between the players. Deep water blocks; five shallow fords cross it: the wide centre ford, held by the Ogre Stronghold and its crystal, and two pairs further out. Banks slope down into a valley. |
| Fishing (Nov 17, built) | Shore fish only: schools along the river banks (AoE2 DE shore fish: 200 food, fisherman 0.43/s), gathered by peasants from the bank and dropped at a Mill or Town Hall. No Dock or boats. |
| Art timing (Nov 17) | Not yet for buildings and units; the **ground is made through the art engine now** (user, Nov 17): style pack `styles/fantasy_realm/` (terrain.json recipes) -> `python3 tools/build_ground.py` -> `game/art/ground_realm_*.jpg`, blended on the height field in the game. |
| Structure first (Nov 17) | Mechanics and structure before content. See Foundations below. |
| As close to AoE2 as possible, through the Feudal Age (Nov 17) | Research in `docs/aoe2-research.md`. Ages 1 and 2 are built; the Castle Age shows locked. |
| Ore generation (Nov 17) | Iron and crystal each generate exactly like AoE2 gold: a 7-tile and two 4-tile mines by every Town Hall, scattered 3-tile piles, 800 a tile, gold mining rate, 100 of each to start. |
| Camp ore (Nov 17) | Kept as bonus veins on top of the AoE2 layout; camps still drop artifacts. |
| Gold prices (Nov 17) | Units pay **iron** where AoE2 charges gold; technologies pay **crystal**. The Market trades in iron. |
| Art (Nov 17) | Start artkit briefs and grey blockouts now, after the Feudal mechanics. Then "focus on art": all 16 buildings are designed as blockouts (brief and a reason per part), rendered through artkit in player colours and drawn in the game (`tools/build_buildings.py`). Units are still code-drawn. See `docs/art-briefs.md`. |
| Castle Age (Nov 17) | "Begin work on mechanics up until castle age. Refer to Age of Empires 2, but continue to make it fantasy as we have been." Built as AoE2's Castle Age with fantasy names; see Castle Age below. Names and the open points there are Claude's proposals until the user confirms them. |
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

## Art direction (user, Nov 17)
- **Darker, more fantasy, realistic.** Weathered stone, dark timber, player colours muted to a tint, steep spires,
  darker ground. Set in `styles/fantasy_realm/style.json` (`procedural`, `look`) and `terrain.json`.
- **Units before building detail.**
- **Figures stay oversized for visibility** (about twice what the doors imply).
- **Fantasy, not medieval** (user, second note): each race gets its own build and an exaggerated signature, and
  the realm's crystal glows on weapons and shields.
- **Push farther** (user, third note): bigger weapons, more glow, stranger outlines; the wild glows magenta
  where the realm glows cyan. The Wolf Rider is a halfling on a tame dire wolf.
- Built as artkit figures (`styles/fantasy_realm/units.py`, `tools/build_units.py`), 8 headings; idle, walk, attack
  and death; in both player colours: Peasant, Militia, Man-at-Arms, Dwarf Pikeman, Elf Archer, Halfling Slinger,
  Wolf Rider; neutral: Goblin Raider, Ogre Brute, Dire Wolf, Boar, Deer, Sheep. The fallen lie 14 s and fade
  (AoE2 leaves decaying bodies); hunted animals stay as the carcass. Soft shadows under units and buildings.
- **Weak spots, then building detail** (user, fourth note): Wolf Rider couches a lance; peasants hold the tool of
  their job and carry visible loads; walls and gates join their neighbours in straight runs and corners; buildings
  rise from a site, burn when damaged and leave rubble (all as AoE2). Details in `docs/art-briefs.md`.
- **One style** (user, fifth note): everything on the map goes through the art engine with one set of materials
  and one light: trees, ore, stone, berries, relics, farms and camp landmarks join the ground, buildings and
  figures. Shadows are cast shadows drawn under everything. Walls are detailed and run on diagonals. No AI yet.
- **Building detail** (user, sixth note): half-timbering, lit windows, slate and thatch roofs, coursed stone,
  crystal finials and lanterns on all main buildings; then the small fixes (stronger shadows, diagonal gates, farm
  stages, stumps, dug building sites, grazing animals, larger camp landmarks).

## Interface (user, Nov 17: "the UI and menus in the exact same format as Age of Empires 2")
Laid out as AoE2 Definitive Edition's HUD (source: the official Learn to Play pages, ageofempires.com/learn-to-play):
- **Top left, the resource bar:** wood, food, iron (where AoE2 has gold), stone, crystal; under each the number of
  peasants gathering it; then population; then the idle-peasant button, shown only when someone is idle.
- **Top centre:** the current age with its emblem. **Top right, the menu bar:** Technology Tree (F2), Controls and
  settings (F1), Menu (F10: Return to Game, Pause, Speed, Technology Tree, Controls, Restart, Resign). AoE2's
  Objectives, Chat and Diplomacy buttons are left out: there is nothing behind them yet.
- **Under the bar, top left:** game time and speed.
- **Bottom left, the command panel:** always 5 x 3 picture buttons on Q W E R T / A S D F G / Z X C V B; empty slots
  are empty frames. Military: the four stances along the top (the active one lit), Attack-move, Stop, Patrol,
  Garrison in the middle, the four formations along the bottom, Delete bottom right. Peasants: Build, Build
  military; inside a build page the other page and Back sit bottom right. Buildings: units on the top row,
  technologies on the second, Town Bell / All Clear / Ungarrison on the third. A button you cannot afford is tinted
  red; one you cannot use yet is grey.
- **The extended tooltip** appears in one fixed place above the command panel: name, hotkey, cost, time, text.
- **Bottom centre, the selection panel:** portrait with the hit-point bar under it; name; owner; attack, melee
  armour, pierce armour, range, sight, speed as icons; the production queue as pictures with progress; several
  units as a grid of portraits with their own bars.
- **Bottom right, the mini-map** with its buttons beside it: mini-map mode (everything / economy / military) and
  idle military.
- Every icon is cut from the game's own art (`tools/build_icons.py` -> `game/art/icons.png`).
- Not done: a main menu and game-setup screens before the match; save and load; score panel; Objectives, Chat,
  Diplomacy.
- **Readability on all fronts** (user): units must read by silhouette and role at a glance; menus and tooltips must
  be easy to read. The checks, their sources and the current results are in `docs/readability.md`;
  `python3 tools/readability_check.py` measures them. This overrides "muted player colours" for figures: the
  owner's colour on a unit is now bright (buildings stay muted).

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

## Castle Age and AoE2 systems (built Nov 17, on the user's go-ahead: "mechanics up until castle age")
Names are fantasy, rules and numbers are AoE2's (in `game/src/data.js`); gold is iron for units, crystal for research.
- **Advance:** 800 food, 200 crystal, 160 s, any two of Archery Range, Stable, Blacksmith, Market (AoE2).
- **Buildings:** more **Town Halls** (275 wood, 100 stone); **Sanctum** (Monastery); **Academy** (University);
  **Siege Workshop** (needs a Blacksmith); **Citadel** (Castle: 650 stone, 4800 HP, five arrows of 11, range 8,
  garrison 20 of anything but siege, +20 population).
- **Unit lines upgrade in place** (data: a technology with `up`): Man-at-Arms -> **Long Swordsman**; Dwarf Pikeman ->
  **Dwarf Halberdier** (AoE2 Pikeman, +22 vs mounted); Elf Archer -> **Elf Longbow** (Crossbowman); Halfling Slinger ->
  **Elite Halfling Slinger**; Wolf Rider -> **Wolf Raider** (Light Cavalry, +10 vs Mystics).
- **New units:** **Bear Knight** (Knight: a dwarf lancer on a war bear); **Centaur Archer** (Cavalry Archer; not
  "cavalry" for pike bonuses, as in AoE2); **Mystic** (Monk); **Battering Ram**, **Catapult** (Mangonel), **Bolt
  Thrower** (Scorpion).
- **Mystics:** heal 2.5 HP a second from 4 tiles (idle ones heal on their own); convert from 9 tiles: from the 4th
  1.2 s "monk second" each has a 27% chance and the 10th is certain; faith is spent and returns in 62 s. Siege and
  buildings need Redemption, Mystics need Atonement; Town Halls, Sanctums, Citadels, walls, gates, farms and wild
  creatures never convert. Heresy: your converted units die instead.
- **Artifacts:** Mystics carry them (Militia still can, so camps pay before the Castle Age) to a Town Hall or a
  **Sanctum**; 0.5 crystal a second each, as before.
- **Siege:** a Ram strikes only buildings and siege (+125), armour -3/180; a Catapult's rock lands where it was
  aimed and hits everything there, your own units included, minimum range 3; a Bolt Thrower's bolt runs through
  every enemy in its line.
- **Ballistics is now a real rule:** an arrow is aimed where its target stood; it misses a unit that stepped aside
  or ran on while it flew (walking into the shot still gets hit). Researching Ballistics removes that. This also
  changes Feudal fights slightly, as in AoE2.
- **Research:** Hand Cart, Town Patrol; Heavy Plough; Bow Saw; Ore Shaft and Stone Shaft Mining; Iron Casting, Chain
  Mail, Chain Barding, Bodkin Arrow, Leather Archer Armour; Squires, Arson, Gambesons; Thumb Ring; Husbandry;
  Sanctity, Fervour, Redemption, Atonement, Herbal Medicine, Heresy; Masonry, Fortified Wall, Guard Tower, Murder
  Holes, Treadmill Crane, Ballistics. A later step shows only once the step before it is researched (AoE2).
- **Garrisons:** towers and Town Halls take those on foot; a Citadel also takes cavalry; nothing takes siege.
- **Pictures are stand-ins.** The four buildings and three siege engines are drawn in code; Bear Knight, Centaur
  Archer and Mystic borrow the Wolf Rider and Peasant figures with a coloured diamond over them; upgraded lines
  keep their Feudal figure. Each needs a brief and a grey blockout through artkit (see `docs/art-briefs.md`).
- **Left out of age 3, on purpose:** the Citadel's unique unit and unique technology (needs a decision), Petards,
  Camel Riders, Coinage/Caravan and Trade Carts (no trade without an active second player), Heated Shot (no ships),
  Faith/Devotion/Theocracy, Siege Towers.

## Opponent AI (begun Nov 17)
Player 1 is a computer player (`new World(seed, { ai: true })`; the browser turns it on, `?ai=0` turns it off; tests
and replays leave it off unless they ask). It lives in `game/src/world.js` (`aiInit`, `aiThink`), thinks once a second,
uses no randomness, and acts only through `world.issue()` at the player's prices, so a game with it is still
deterministic (to replay one: same seed, the opponent on, and the human's commands).
- **Dark Age, the standard AoE2 opening:** six peasants on sheep (the scout fetches the further sheep and the flock
  walks to the Town Hall), then wood, berries and a Mill, Farms round the Town Hall, a Lumber Camp on the wood line,
  Cottages ahead of the population, a Barracks, then Loom and the Feudal Age at 21 peasants and the scout (22
  population). It reaches the Feudal Age at about 12 minutes.
- **Feudal Age:** Archery Range, Stable, Blacksmith, Mining Camps on iron and crystal, peasants to 45, all the Feudal
  research as it can pay for it, a second Barracks, Range and Stable when wood piles up.
- **Army by counters:** it counts what the enemy fields and trains against it, as AoE2's counters say: pikemen
  against riders, slingers (and riders) against archers, archers and men-at-arms against infantry.
- **Attack waves:** the first leaves with 8 soldiers (about minute 18), each later one needs 4 more (to 28), at least
  two minutes apart. Waves cross the river by the two nearest fords in turn, never the centre one (the Ogre
  Stronghold), go for the Town Hall, then for whatever the enemy has left. A wave beaten down to a quarter goes home.
- **Defence:** soldiers at home answer any attack on the base; when raiders by the Town Hall outnumber them it rings
  the Town Bell, and All Clear when they are gone.
- **Not yet like a person (my choices, open to change):** it knows the whole map (no fog for it); it does not hunt
  boar or deer, fish, wall, build towers, use the Market, clear camps on purpose or collect artifacts; one
  difficulty. It beats a player who does nothing in about half an hour.
- **Fixed on the way:** a unit on a move or attack-move that got stuck used to drop the order (and jump to its next
  queued one); it now looks for a new way, up to six times.

## Creep camps (Warcraft III style)
Guards stand at home, attack anything that comes within 5 tiles, call the whole camp in when one is hit, chase up to
11 tiles from home, then walk back healing. Per side: 2 Wolf Dens (crystal x4), 2 Goblin Outposts (iron x7, 1
artifact), 1 Ogre Lair (crystal x6, 1 artifact); in the middle one Ogre Stronghold (crystal x10, 2 artifacts).
Each player's home also has free iron (7 + 4 + 4), stone (5 + 5), berries, 6 sheep, 2 boar, 4 deer and woodlines,
like AoE2 Arabia.

## Open questions
1. Castle Age names: Bear Knight, Centaur Archer, Mystic, Sanctum, Academy, Citadel, Dwarf Halberdier, Elf Longbow,
   Wolf Raider are proposals. Keep or change?
2. The Citadel's unique unit and unique technology (AoE2 Castles train one per civilisation; there is one faction).
3. Artifacts: AoE2 lets only Monks carry relics and only Monasteries hold them. Here Militia and Town Halls still
   work too, so camps pay off before age 3. Keep both, or Mystics and Sanctums only?
4. Should crystal be buyable at the Market, or stay mine-only?
5. Opponent AI, next steps: should it play by the fog (scout first)? Should it clear camps and take artifacts? Hunt
   boar and deer, towers and walls, the Market? Difficulty levels (AoE2 has Easiest to Extreme)?
6. Art: briefs and grey blockouts for the Castle Age buildings and units.
7. Imperial Age (age 4): not started; ask first.
