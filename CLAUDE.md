# Rules for every chat working on RTS Foundation

## The brief
AoE2's workers, counters, unit variety, base building and tech progression; Warcraft III's fantasy and creep camps;
no heroes. When in doubt, research how Age of Empires II (Definitive Edition) handles it and copy it; note the AoE2
value beside the number in `game/src/data.js`.

## Scope
- The Dark Age and the Feudal Age (ages 1 and 2) are built, as close to AoE2 as possible; what was researched and
  what differs is in `docs/aoe2-research.md`. Do not code the Castle Age or later until the user says so; ask for
  direction first (open questions are listed in `docs/design.md`).
- Gold: units pay iron where AoE2 charges gold, technologies pay crystal. Both ores generate like AoE2 gold.
- The opponent (player 1) is a computer player (`aiInit`, `aiThink` in `world.js`; Opponent AI in `docs/design.md`).
  It acts only through `world.issue()`, pays what the player pays and uses no randomness. Keep it that way.
- Record every design decision the user makes in `docs/design.md`.

## Where things go
- Numbers: `game/src/data.js`. Map generation: `game/src/map.js`. Rules and AI: `game/src/world.js` (no DOM, runs
  in Node). Drawing: `game/src/render.js`. Input and HUD: `game/src/ui.js`.
- `artkit/` is a pinned copy of BrandoScrub/Game-Engine-System-Design and is never edited here. Engine changes go to
  that repository (its CLAUDE.md), then `python3 tools/update_artkit.py <engine checkout>` here. `python3
  tools/check_artkit.py` must print OK before every commit. `game/lib/glcanvas.js` must equal
  `artkit/runtime/glcanvas.js`.
- Every player action goes through `world.issue()` as a command (see Foundations in `docs/design.md`); the UI never
  changes the world directly, and the simulation uses only `world.rand`, never `Math.random`, so games stay
  deterministic and replayable.
- Ground tiles: recipes in `styles/fantasy_realm/terrain.json`, rendered by `python3 tools/build_ground.py`.
- Buildings: geometry in `styles/fantasy_realm/blockouts/buildings.py` (every part needs a reason; `findings()` must be
  empty), rendered by `python3 tools/build_buildings.py` into `game/art/b_<key>_<player>.png`. State of the art and
  what is still off: `docs/art-briefs.md`.
- Figures: `styles/fantasy_realm/units.py` (artkit `Biped`; animals and the Wolf Rider on `artkit.rig.Rig`), rendered by `python3 tools/build_units.py` into
  `game/art/u_<key>_<player>.png`. Art direction (user): darker, more fantasy, realistic; figures oversized.
- Props (trees, ore, stone, berries, relic, camp landmarks): `styles/fantasy_realm/props.py`, rendered by `python3
  tools/build_props.py` into `game/art/p_<key>.png`. Cast shadows (`*_s.png`) come from the pack's "shadow" section and
  are written by all three build tools; the game draws them first. Nothing on the map is drawn in code except shore
  fish, fire and carried loads: new map art goes through the engine so everything keeps one style.
- HUD: AoE2's layout (see Interface in `docs/design.md`). Buttons are pictures from `game/art/icons.png`; after changing
  unit, building or prop art run `python3 tools/build_icons.py`. A new command needs an icon key and a grid slot.
- This game's art content (its style pack) lives in `styles/fantasy_realm/`, outside the engine. Any new building, unit
  or prop follows `artkit/DESIGN_METHOD.md`: a brief, references, then a grey blockout shown to the user before detail.

## Before you commit
`node tests/sim_check.js`, `node tests/mechanics_check.js`, `node tests/feudal_check.js` and `node tests/ai_check.js` print only PASS lines; `python3 tools/check_artkit.py` prints OK; load the game in a
browser and check the console is clean.
