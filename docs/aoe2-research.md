# How Age of Empires II works, and what this game copies (researched Nov 17 2026)

Sources are linked beside each finding. "Here" says what RTS Foundation does with it.

## Design philosophy
- Ages gate everything: each advance needs a resource payment and two buildings of the current age, and unlocks new
  buildings, units and research ([ageofempires.com, Advancing](https://www.ageofempires.com/learn-to-play/advancing-aoe2/)).
  Feudal costs 500 food; Castle 800 food and 200 gold. **Here:** the same, with ages 1 and 2 built and 3 locked.
- Counters come from bonus damage, not from multipliers: spearmen carry an attack bonus against cavalry, and so on
  ([Wikipedia, Age of Empires II](https://www.wikipedia.com/wiki/Age_of_Empires_2)). **Here:** the same classes.
- The cheap "trash" counters cost no gold: Spearman, Skirmisher and Scout Cavalry cost only food or food and wood
  ([ageofempires.com, Military Units](https://ageofempires.com/learn-to-play/military-and-economy-aoe2)). **Here:**
  Dwarf Pikeman, Halfling Slinger and Wolf Rider cost no ore.

## Damage
`damage = max(1, (max(0, melee - melee armour) + max(0, pierce - pierce armour) + sum of bonuses against the target's
armour classes) x elevation)`; the elevation factor is 1.25 from higher ground
([openage, reverse-engineered damage](https://simonsan.github.io/openage-webdocs/sphinx/doc/reverse_engineering/game_mechanics/damage.html);
[armour class guide](https://divy1211.github.io/AoE2DE_UGC_Guide/general/damage_calculation/)).
**Here:** `World.damage()` is that formula; x0.75 from lower ground.

## Movement and pathfinding
- AoK shipped with three pathfinders, an obstruction manager and a formation system: a high-level pathfinder plans
  the route across the map ignoring walking units, and lower-level ones thread through crowds
  ([AoK postmortem](https://www.gamedeveloper.com/design/postmortem-ensemble-studio-s-age-of-empires-ii-age-of-kings);
  [developer's forum account](https://aok.heavengames.com/cgi-bin/forums/display.cgi?action=st&f=0%2C0%2C0%2C0&fn=3&st=250&tn=40110)).
  **Here:** one A* over the tile grid for the route (units ignored), soft pushing between units for crowds, a
  node budget per tick. No second, fine-grained pathfinder yet.
- A group order is one path search, as for a single unit ([0 A.D. notes on Age of Mythology's
  system](https://wildfiregames.com/forum/topic/13042-aom-like-pathfindingmovement/)). **Here:** the same.
- Units given a move order together are bound into a formation, and automatic formations put the strongest units in
  front ([Steam discussion](https://steamcommunity.com/app/813780/discussions/0/4039230033364269988/); AoK postmortem).
  **Here:** Line, Staggered, Box and Flank; infantry front, cavalry, ranged, peasants last; the group walks at its
  slowest member's speed. Units share the route and end in their slots; they do not yet hold ranks while walking.
- DE makes your own idle units step aside for moving ones
  ([Steam, developer reply](https://steamcommunity.com/app/813780/discussions/0/2803982773091323561/)). **Here:**
  units push each other softly instead.
- The simulation is lockstep and integer-based, which is why commands are data
  ([Hacker News thread on AoE DE pathing](https://news.ycombinator.com/item?id=16490523)). **Here:** commands,
  fixed ticks, one seeded random source, replayable logs (floating point, so same-machine determinism only).

## Map generation (Arabia, the standard open map)
- Each player's start: 8 herdables, 2 boar, 4 deer, 6 forage bushes, three forests, 7 tiles of gold and 5 of stone
  close by ([ageofempires.com, Starting Resources](https://www.ageofempires.com/learn-to-play/defending-your-empires-aoe2/)),
  plus two 4-tile gold mines and a 4-tile stone mine further out, 800 gold and 350 stone a tile
  ([Fandom, Arabia](https://ageofempires.fandom.com/wiki/Arabia)); neutral 3-tile gold and 2-tile stone piles are
  scattered over the map ([aoe2.guide](https://aoe2.guide/arabia/)).
- **Here:** exactly that around each Town Hall, with iron **and** crystal each getting the full gold set (7 + 4 + 4),
  both at 800 a tile and the gold mining rate, and scattered 3-tile piles of both. Creep camps guard extra veins.

## Feudal Age content
- Buildings: Archery Range, Stable, Blacksmith, Market, Watch Tower, Stone Wall, Gate (ageofempires.com, Advancing).
- Blacksmith research and costs: Forging 150 food; Scale Mail 100 food; Scale Barding 150 food; Fletching 100 food
  50 gold; Padded Archer Armor 100 food; Bloodlines 150 food 100 gold
  ([aoe2insights tech tree](https://www.aoe2insights.com/civilization/wu/tech-tree/)). Supplies: 150 food 100 gold,
  Militia line -15 food ([DE balance changelog](https://www.forgottenempires.net/age-of-empires-ii-definitive-edition/balance-changelog)).
- Units: Spearman 35 food 25 wood, 45 HP, attack 3, reload 3, speed 1; Militia line 50 food 20 gold; Man-at-Arms 45 HP,
  attack 6 ([Fandom comparison table](https://ageofempires.fandom.com/wiki/Flemish_Militia)); Skirmisher 30 HP,
  attack 2, 3 pierce armour, range 4 (aoe2insights).
- Other numbers (Archer, Scout Cavalry, building HP and times, Market fee of 30% and price step of 3, Town Center
  firing only when garrisoned) are from memory of the game and were not re-checked against a source today.

## Art
- All of AoE's 2D sprites began as 3D models, textured, animated and rendered out to sprite frames
  ([AoE postmortem](https://www.gamedeveloper.com/game-platforms/the-game-developer-archives-postmortem-ensemble-s-age-of-empires-)).
- The original units turn in 8 directions; the Definitive Edition renders 16 or 32
  ([Forgotten Empires](https://www.forgottenempires.net/age-of-empires-definitive-edition-is-it-a-3d-or-a-2d-game/);
  [modding forum](https://forums.ageofempires.com/t/is-there-a-guidebook-for-creating-slp-for-aoe2-de/61111)).
- The team's current pipeline is concept sketch, then 3D model and animation, then render
  ([The Art of The Last Chieftains](https://www.ageofempires.com/news/from-concept-to-final-polish-the-art-of-the-last-chieftains/)).
- **Here:** artkit is the same idea (3D model to 2:1 isometric sprite). Placeholders are still drawn in code; the
  blockouts in `styles/fantasy_realm/` start the real set.

## Not copied (and why)
- Docks, ships and fish traps: the user chose shore fish only.
- Trade Carts and tribute: need a second active player.
- Stone and palisade gates are one tile, not four.
- A missed arrow does nothing; in AoE2 it can land on another unit.
- Guard and Follow orders, and garrison-to-heal rates, are not in yet.
