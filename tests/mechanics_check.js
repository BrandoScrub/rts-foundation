/* node tests/mechanics_check.js : the foundations under the content. Commands, determinism and replays, the path
   budget, shared group paths, crossing the river, peasants spreading around one job, fog memory. */
const World = require('../game/src/world.js'), Path = require('../game/src/path.js');
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
const run = (w, s) => { for (let i = 0; i < 30 * s; i++) w.step(1 / 30); };
const mineOf = (w, p, t) => w.ents.filter(e => !e.dead && e.owner === p && e.type === t);
const near = (w, t) => { let b = -1, bd = 1e9; for (let i = 0; i < w.map.node.length; i++) if (w.map.node[i] === t) { const d = Math.hypot(i % 300 - 34, (i / 300 | 0) - 34); if (d < bd) { bd = d; b = i; } } return b; };

/* 1. commands are data, run next tick, logged; the same seed and commands give the same game; a log replays it */
function script(w) {
  const vs = mineOf(w, 0, 'villager'), tc = mineOf(w, 0, 'town_hall')[0], sc = mineOf(w, 0, 'scout')[0];
  w.issue(0, { c: 'order', ids: [vs[0].id, vs[1].id], node: near(w, 2), x: 0, y: 0 });
  w.issue(0, { c: 'train', ids: [tc.id], unit: 'villager', n: 3 });
  w.issue(0, { c: 'move', ids: [sc.id], x: 90, y: 60 });
  let spot = null; for (let r = 4; r < 12 && !spot; r++) for (let d = 0; d < 8 && !spot; d++) { const x = 32 + Math.round(Math.cos(d) * r), y = 32 + Math.round(Math.sin(d) * r); if (w.canPlace('cottage', 0, x, y)) spot = [x, y]; }
  w.issue(0, { c: 'place', type: 'cottage', tiles: [spot], ids: [vs[2].id] });
}
const a = new World(7), b = new World(7);
script(a); script(b);
ok(a.pending.length === 4 && mineOf(a, 0, 'cottage').length === 0, 'commands wait for the next tick');
a.step(1 / 30); b.step(1 / 30);
ok(mineOf(a, 0, 'cottage').length === 1 && mineOf(a, 0, 'town_hall')[0].queue.length === 3, 'they run at the start of that tick');
for (let i = 0; i < 30 * 120; i++) { a.step(1 / 30); b.step(1 / 30); }
ok(a.hash() === b.hash(), `same seed + same commands = same game after 2 minutes (${a.hash()})`);
const c = new World(7), log = a.log.slice();
for (let t = 1; t <= a.tick; t++) { for (const e of log) if (e.tick === t) { const { tick, p, ...cmd } = e; c.issue(p, cmd); } c.step(1 / 30); }
ok(c.hash() === a.hash(), `the command log replays the game exactly (${a.log.length} commands)`);

/* 2. a big order does not freeze a frame: path searches share a per-tick budget; groups share one path */
{
  const w = new World(7), us = [];
  for (let k = 0; k < 40; k++) us.push(w.addUnit('militia', 0, 40 + (k % 8) * 0.6, 40 + (k / 8 | 0) * 0.6));
  w.recount(0);
  let nodes = 0; const f = Path.find; Path.find = function () { const r = f.apply(this, arguments); nodes += r.n; return r; };
  const solo = f(40, 40, [250, 255, 250, 255], i => w.walkable(i, 0), 0, 90000).n;
  w.issue(0, { c: 'move', ids: us.map(u => u.id), x: 250, y: 255 });
  let worst = 0; for (let i = 0; i < 30 * 5; i++) { const t = process.hrtime.bigint(); w.step(1 / 30); worst = Math.max(worst, Number(process.hrtime.bigint() - t) / 1e6); }
  Path.find = f;
  ok(nodes < solo * 3, `40 units crossing the map share one group path (${nodes} path nodes searched; one unit alone needs ${solo})`);
  ok(worst < 80, `no tick of that order takes long (worst ${worst.toFixed(1)} ms)`);
  run(w, 420);
  const there = us.filter(u => Math.hypot(u.x - 250, u.y - 255) < 6).length;
  ok(there >= 36, `the group crosses the river by a ford and arrives (${there}/40 within 6 tiles)`);
}
/* 3. several peasants on one tree spread around it instead of standing in one spot */
{
  const w = new World(7), t = near(w, 1), tx = t % 300 + 0.5, ty = (t / 300 | 0) + 0.5, vs = [];
  for (let k = 0; k < 4; k++) vs.push(w.addUnit('villager', 0, tx + 2 + k * 0.1, ty + 2));
  w.issue(0, { c: 'order', ids: vs.map(v => v.id), node: t, x: tx, y: ty }); run(w, 15);
  let md = 1e9; for (let i = 0; i < 4; i++) for (let j = i + 1; j < 4; j++) md = Math.min(md, Math.hypot(vs[i].x - vs[j].x, vs[i].y - vs[j].y));
  ok(vs.every(v => v.atWork) && md > 0.2, `four peasants all chop one tree, spread out (closest pair ${md.toFixed(2)} tiles)`);
}
/* 4. fog remembers enemy buildings as last seen */
{
  const w = new World(7), P = w.players[0], etc = mineOf(w, 1, 'town_hall')[0], s = w.addUnit('scout', 0, etc.x - 3.5, etc.y - 3.5);
  run(w, 1); ok(P.seen.has(etc.id), 'a scout near the enemy Town Hall records it');
  w.issue(0, { c: 'move', ids: [s.id], x: 200, y: 200 }); run(w, 70);
  ok(!w.seesRect(P, etc) && P.seen.has(etc.id), 'out of sight, it is still shown where it was seen');
  w.remove(etc); run(w, 1);
  ok(P.seen.has(etc.id), 'destroyed out of sight: the memory stays until the spot is seen again');
  s.x = etc.x - 3; s.y = etc.y - 3; s.order = null; run(w, 1);
  ok(!P.seen.has(etc.id), 'seen again: the memory is cleared');
}
process.exit(fail ? 1 : 0);
