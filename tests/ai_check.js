/* node tests/ai_check.js : the computer opponent (player 1), played without a browser. Its opening, the Feudal
   Age, counters, defence, creeping, attack waves, and that a game with it is still deterministic. Prints PASS/FAIL lines. */
const World = require('../game/src/world.js');
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
const run = (w, s) => { for (let i = 0; i < 30 * s && w.state === 'playing'; i++) w.step(1 / 30); };
const of = (w, f) => w.ents.filter(e => !e.dead && e.owner === 1 && f(e)), min = w => (w.time / 60).toFixed(1);

/* 1. off unless asked for; on, it only speaks in commands and the game stays deterministic */
{ const w = new World(7); run(w, 60);
  ok(!w.ai && !w.log.length && of(w, e => e.type === 'villager').every(u => !u.order), 'without { ai: true } the opponent stays idle');
  const a = new World(7, { ai: true }), b = new World(7, { ai: true }); run(a, 360); run(b, 360);
  ok(a.log.length > 20 && a.log.every(c => c.p === 1), `the opponent plays through world.issue() (${a.log.length} commands in 6 minutes)`);
  ok(a.hash() === b.hash(), `two games with the opponent are identical (${a.hash()})`); }

/* 2. the opening, the Feudal Age, an army, a wave, and a win against a player who does nothing */
{ const w = new World(7, { ai: true }), P = w.players[1]; run(w, 480);
  const v = of(w, e => e.type === 'villager');
  ok(v.length >= 20, `Dark Age: ${v.length} peasants after 8 minutes (AoE2: 21 and the scout before the Feudal Age)`);
  ok(w.has(1, 'lumber_camp') && w.has(1, 'mill') && of(w, e => e.type === 'cottage').length >= 3, 'it built Cottages, a Lumber Camp and a Mill');
  ok(v.filter(u => !u.order).length <= 1, 'no peasants stand idle');
  ok(P.gathered.food > 800 && P.gathered.wood > 450, `it gathers (food ${P.gathered.food | 0}, wood ${P.gathered.wood | 0})`);
  while (P.age < 2 && w.time < 900) run(w, 5);
  ok(P.age === 2 && P.techs.has('loom'), `Loom, then the Feudal Age at ${min(w)} minutes`);
  while (!w.ai.wave && w.time < 1200) run(w, 5);
  const army = of(w, e => e.kind === 'unit' && e.type !== 'villager' && e.type !== 'sheep');
  ok(w.ai.wave === 1 && army.length >= 8, `first attack wave leaves at ${min(w)} minutes with ${w.ai.squad.length} soldiers`);
  ok(['barracks', 'archery_range', 'stable'].every(t => of(w, e => e.type === t).length), 'Barracks, Archery Range and Stable stand');
  let near = 1e9; while (w.state === 'playing' && w.time < 2400) { run(w, 5); for (const id of w.ai.squad) { const u = w.get(id); if (u) near = Math.min(near, Math.hypot(u.x - 150, u.y - 150)); } }
  ok(near > 30, `the waves go round the Ogre Stronghold by a side ford (never within ${near | 0} tiles of it)`);
  const own = w.camps.filter(c => c.cleared && c.x + c.y > 299), kept = of(w, e => e.type === 'town_hall').reduce((a, b) => a + b.artifacts, 0);
  ok(own.length >= 2 && !w.camps.find(c => c.type === 'ogre_hold').cleared, `it creeps: ${own.length} camps on its bank cleared (${own.map(c => c.type).join(', ')}), the Ogre Stronghold left alone`);
  ok(kept >= 1 && w.players[1].gathered.crystal > 0, `a militia carried an artifact to its Town Hall (${kept} stored)`);
  ok(w.state === 'defeat', `a player who does nothing is destroyed (${min(w)} minutes)`); }

/* 3. counters: against an enemy of riders it trains pikemen above all */
{ const w = new World(7, { ai: true });
  for (let k = 0; k < 14; k++) w.addUnit('scout', 0, 40 + k % 5, 42 + (k / 5 | 0)); w.recount(0);
  run(w, 1200);
  const c = {}; for (const u of of(w, e => e.kind === 'unit')) c[u.type] = (c[u.type] || 0) + 1;
  ok((c.spearman || 0) > (c.militia || 0) && (c.spearman || 0) > (c.archer || 0), `enemy cavalry: Dwarf Pikemen lead its army (${JSON.stringify(c)})`); }

/* 4. defence: raiders at its Town Hall ring the Town Bell; afterwards everyone goes back to work */
{ const w = new World(7, { ai: true }); run(w, 150);
  const th = of(w, e => e.type === 'town_hall')[0];
  const raid = []; for (let k = 0; k < 4; k++) raid.push(w.addUnit('militia', 0, th.x - 7 + k * 0.6, th.y + 6)); w.recount(0);
  w.issue(0, { c: 'move', ids: raid.map(u => u.id), x: th.x, y: th.y + 3, attack: true });
  let hid = 0; for (let k = 0; k < 40; k++) { run(w, 1); hid = Math.max(hid, th.garrison.length); }
  ok(hid >= 4, `raiders by the Town Hall: the Town Bell rings and ${hid} peasants shoot from inside`);
  run(w, 150);
  ok(raid.every(u => u.dead) && !th.garrison.length && of(w, e => e.type === 'villager').filter(u => !u.order).length <= 1, 'the raid is beaten off, All Clear, and the peasants are back at work'); }
process.exit(fail ? 1 : 0);
