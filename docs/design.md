# RTS Foundation: design record (tier 1)

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

## Creep camps (Warcraft III style)
Guards stand at home, attack anything that comes within 5 tiles, call the whole camp in when one is hit, chase up to
11 tiles from home, then walk back healing. Per side: 2 Wolf Dens (crystal x4), 2 Goblin Outposts (iron x7, 1
artifact), 1 Ogre Lair (crystal x6, 1 artifact); in the middle one Ogre Stronghold (crystal x10, 2 artifacts).
Each player's home also has free iron (7 + 4 + 4), stone (5 + 5), berries, 6 sheep, 2 boar, 4 deer and woodlines,
like AoE2 Arabia.

## Open questions (ask before building past tier 1)
1. Tier 2 content: which units make up the counter triangle (spear / archer / cavalry equivalents) and how much
   crystal tier 2 costs.
2. Where artifacts should live once tier 2 has a temple-like building (AoE2 Monastery) and who carries them then.
3. Water: AoE2 maps have lakes and docks; this map has none yet.
4. Whether the opponent gets an AI and how strong.
5. Final art direction for buildings and units (artkit briefs and blockouts).
