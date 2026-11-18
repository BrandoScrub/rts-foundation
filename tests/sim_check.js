/* node tests/sim_check.js : the simulation without a browser. Map symmetry, gathering, building, camps, artifacts,
   Town Bell, hunting. Prints PASS/FAIL lines and exits 1 on any failure. */
const World = require('../game/src/world.js');
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
const run = (w, s) => { for (let i = 0; i < 30 * s; i++) w.step(1 / 30); };
const w = new World(7), m = w.map, P = w.players[0];
let sym = true; for (let y = 0; y < 300; y++) for (let x = 0; x < 300; x++) if (m.node[y * 300 + x] !== m.node[(299 - y) * 300 + 299 - x]) sym = false;
for (let i = 0; i < 90000; i++) if (m.water[i] !== m.water[89999 - i]) sym = false;
ok(sym, 'resources and the river are point-symmetric between the two corners');
{ let deep = 0, ford = 0; for (const v of m.water) { if (v === 1) deep++; if (v === 2) ford++; }
  ok(deep > 1000 && ford > 100, `a river with fords runs between the players (deep ${deep}, ford ${ford})`);
  const Path = require('../game/src/path.js'); const r = Path.find(36, 38, [262, 262, 262, 262], i => w.walkable(i, 0), 0, 200000);
  ok(r.reached, 'a unit can walk from one base to the other across a ford'); }
ok(w.ents.filter(e => e.type === 'town_hall').length === 2, 'two Town Halls in opposite corners');
ok(P.pop === 4 && P.popCap === 5, 'start: 3 peasants + scout, population 4/5 (AoE2)');
const near = t => { let b = -1, bd = 1e9; for (let i = 0; i < m.node.length; i++) if (m.node[i] === t) { const d = Math.hypot(i % 300 - 34, (i / 300 | 0) - 34); if (d < bd) { bd = d; b = i; } } return b; };
const vs = w.ents.filter(e => e.owner === 0 && e.type === 'villager');
w.order(vs[0], { type: 'gather', node: near(2) }); w.order(vs[1], { type: 'gather', node: near(1) });
run(w, 90);
ok(P.gathered.food >= 10 && P.gathered.wood >= 10, `peasants gather and drop off (food ${P.gathered.food | 0}, wood ${P.gathered.wood | 0})`);
const spot = t => { for (let r = 4; r < 14; r++) for (let d = 0; d < 12; d++) { const x = 32 + Math.round(Math.cos(d) * r), y = 32 + Math.round(Math.sin(d) * r); if (w.canPlace(t, 0, x, y)) return [x, y]; } };
const h = w.place('cottage', 0, ...spot('cottage')); w.order(vs[2], { type: 'build', id: h.id }); run(w, 70);
ok(h.built && P.popCap === 10, 'a Cottage gets built and adds 5 population');
const camp = w.camps.find(c => c.type === 'goblin_post');
const ms = []; for (let k = 0; k < 8; k++) ms.push(w.addUnit('militia', 0, camp.x - 8 + (k % 4) * 0.6, camp.y - 8 + (k / 4 | 0) * 0.6)); w.recount(0);
const dep = camp.deposit[0], di = dep[1] * 300 + dep[0];
ok(!!w.wardedBy(di), 'the camp wards its iron');
w.groupMove(ms, camp.x, camp.y, false, true); run(w, 60);
ok(camp.cleared && !w.wardedBy(di), 'eight militia clear a Goblin Outpost and unward the iron');
const art = w.ents.find(e => e.kind === 'artifact' && !e.dead);
ok(!!art, 'the camp drops an artifact');
const m0 = ms.find(x => !x.dead); w.smartOrder(m0, art, -1, art.x, art.y, false); run(w, 240);
const tc = w.ents.find(e => e.type === 'town_hall' && e.owner === 0);
ok(tc.artifacts === 1 && P.res.crystal > 0, 'militia carries it home; it trickles crystal');
w.townBell(0); run(w, 25); ok(tc.garrison.length >= 2, `Town Bell garrisons peasants (${tc.garrison.length})`);
w.allClear(0); ok(tc.garrison.length === 0, 'All Clear empties the Town Hall');
const sheep = w.ents.filter(e => e.type === 'sheep').sort((a, b) => Math.hypot(a.x - 34, a.y - 34) - Math.hypot(b.x - 34, b.y - 34))[0];
w.order(vs[0], { type: 'gather', ent: sheep.id }); run(w, 30);
ok(sheep.carcass && sheep.food < 100, 'a peasant slaughters a sheep and gathers it');
process.exit(fail ? 1 : 0);
