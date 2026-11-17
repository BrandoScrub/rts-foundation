# artkit.maps (was mapkit)

Narrative map generation for isometric RTS games. It simulates a map's history in order, so everything on the map has a cause: land, settlement, roads, districts, history, approaches, population, validation.

`mapkit.js` is game-agnostic: no canvas, no DOM, no game globals. It runs under Node and inlines into a browser game. A game's templates are data in its style pack (`styles/<style>/maps/templates.js`, named in `style.json` as `"maps": {"templates": ...}`); Brass and Bone's are in `styles/brass_and_bone/maps/`. The adapter lives in the game (`game/index.html`, search `mapkit adapter`). The old `mapkit/` folder keeps thin wrappers so its commands still work.

## Use it

```js
const plan = MapKit.generate({ seed, w: 120, h: 120, template, context });
```

`context` holds what the game knows:

```js
{ biome:'lowlands', start:{x,y}, ore:4, threatSide:'n',
  edges:{n:{open:true,neighbor:true,infected:true,name:'Blighted Marsh'}, s:{open:true}, e:{open:true}, w:{open:true}},
  mod:null, budget:{hamlets:6, caches:40}, clearing:10.5 }
```
`clearing` (optional, default 10.5) is the mean radius of the open ground round the start, in tiles. The rings kept free of craters, ore and blobs, and the radius the generator guarantees open, move out by the same amount.
`content` (optional, default `w / 120`) scales how many infected packs and road wanderers the plan places; a game whose map grew for room rather than for more to fight passes the old size's factor.

The same seed, size, template and context give the same plan. Each pass has its own RNG stream, so changing one pass does not reshuffle the others.

## MapPlan

- `grids`: `land` (0 open, 1 forest, 2 rock, 3 water, 4 wall, 5 ore), `ford`, `district`, `roadClass` (0 to 3), `scarTag` (indexes `plan.tags`), `flow`, `reserved`, `tvar`
- `sites[]`, `roads[]` (each joins two named things), `approaches[]`, `placements[]`, `chronicle[]`, `metrics`
- Each placement has a `siteId` or `beatId`: what caused it.

## Write a template

A template is data: `land`, `sites`, `districts`, `districtOf`, `eras`, `names`, `roadNames`, `population`. See `styles/brass_and_bone/maps/templates.js`; The Dead City is the reference. A beat is:

```js
{ id:'blown', where:'bridge', stamp:[{op:'cutBridge'}], text:'Sappers dropped {site} into the water.' }
```

Add `phase:'approaches'` when a beat needs the approaches (last stand, checkpoint). New `where` rules and stamp ops go in `MapKit.register.where` and `MapKit.register.op`.

## Write an adapter (minimal)

```js
const plan = MapKit.generate({ seed, w, h, template, context });
for (let i = 0; i < w * h; i++) myTiles[i] = TILE_FROM_LAND[plan.grids.land[i]];
for (const p of plan.placements) {
  if (p.type === 'blocker' || p.type === 'threat') spawnEnemy(p);
  if (p.type === 'loot') spawnLoot(p);
}
```

Blockers are enemy-held and sit in gaps the scenery leaves. The core reserves their footprint (`grids.reserved`). The adapter decides what they are.

## Enemies on roads

`flow` and `approaches` are core outputs. How enemies use them is the adapter's business. The pattern used here:

1. Pick an approach for the edge an attack enters from, by `weight`.
2. A share of the attackers (here 70%) follow `approach.path` tile by tile, with a lateral offset for a column. The rest move as they always did.
3. Leave the path as soon as the next tile is blocked or the target is close, and fall back to the game's normal pathing. Roads are a preference, never a rail.
4. Name the warning after `approach.short` and `fromEdge`.

## Tools

- `viewer.html`: seed, size, template in; the plan drawn flat with toggles. `viewer.html?style=<pack>` picks the templates.
- `node mapkit/test/run.js [seeds] [size]`: Brass and Bone's pass table and metric ranges.
- `python3 -m artkit.maps inline <index.html> --style <pack>`: inlines the generator and the style's templates between the `MAPKIT-INLINE` markers. Run it after editing either (`python3 mapkit/tools/inline.py` does this for `game/index.html`).
- `artkit/tests/maps_identity.js`: one hash per plan, for checking a refactor byte for byte (part of `tests/identity_kits.py`).
