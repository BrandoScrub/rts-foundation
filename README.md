# RTS Foundation

Age of Empires II's economy, unit counters and tech progression in a Warcraft III fantasy world with creep camps,
and no heroes. This build is **tier 1** (AoE2's Dark Age) only.

| Folder | What it is |
|---|---|
| `game/` | The playable build: `index.html`, `src/` (data, map, pathfinding, simulation, renderer, HUD), `lib/glcanvas.js` (artkit's WebGL renderer). |
| `artkit/` | The art engine, a **pinned copy** of BrandoScrub/Game-Engine-System-Design (version in `artkit/VENDORED.json`). Never edited here. |
| `styles/fantasy_realm/` | This game's art style pack (outside the engine): so far the ground recipes in `terrain.json`. |
| `tools/` | `update_artkit.py <engine checkout>` brings in a new engine version; `check_artkit.py` catches edits to the pinned copy; `build_ground.py` renders the ground tiles through artkit into `game/art/`. |
| `tests/` | `node tests/sim_check.js` (rules and economy) and `node tests/mechanics_check.js` (commands, determinism, replay, path budget, group paths, fog memory), both without a browser. |
| `docs/design.md` | Every decision so far, how AoE2 was followed, and the open questions. |

## Play
```
python3 -m http.server 8000 -d game
```
then open http://localhost:8000/. `?seed=N` makes a different map, `?gl=0` uses plain Canvas 2D, `?reveal=1` shows the whole map (testing).
Press **F1** in the game for every hotkey and the touch controls. Phones and narrow windows get the mobile interface (after Brass and Bone's); F1 can force Mobile or Desktop.

## Read first
`CLAUDE.md` (rules for every chat working here) and `docs/design.md`.
