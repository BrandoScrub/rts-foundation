/* node tests/feudal_check.js : AoE2's Feudal Age rules. Ore generated like gold, the damage formula and counters,
   arrows, stances, formations, age advance and gating, research effects, the Market. */
const World = require('../game/src/world.js'), DATA = require('../game/src/data.js'), MapGen = require('../game/src/map.js');
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
const run = (w, s) => { for (let i = 0; i < 30 * s; i++) w.step(1 / 30); };
const mineOf = (w, p, t) => w.ents.filter(e => !e.dead && e.owner === p && e.type === t);
const flat = (w, x, y) => { for (let b = y - 3; b <= y + 4; b++) for (let a = x - 3; a <= x + 4; a++) w.map.hc[b * 301 + a] = 0; };

/* ore like AoE2 gold: a 7-tile and two 4-tile mines of EACH ore near every Town Hall */
{
  const w = new World(7), m = w.map;
  const piles = (type) => { const seen = new Set(), out = [];
    for (let i = 0; i < m.node.length; i++) { if (m.node[i] !== type || seen.has(i) || m.ward[i] >= 0) continue; const x = i % 300, y = i / 300 | 0; if (Math.hypot(x - 34, y - 34) > 30) continue;
      let n = 0; const st = [i]; seen.add(i); while (st.length) { const j = st.pop(); n++; for (const d of [1, -1, 300, -300]) { const k = j + d; if (m.node[k] === type && !seen.has(k)) { seen.add(k); st.push(k); } } } out.push(n); }
    return out.sort((a, b) => b - a).join('+'); };
  ok(piles(MapGen.N.IRON) === '7+4+4' && piles(MapGen.N.CRYSTAL) === '7+4+4', `home ore follows AoE2 gold: iron ${piles(MapGen.N.IRON)}, crystal ${piles(MapGen.N.CRYSTAL)}`);
  ok(piles(MapGen.N.STONE) === '5+4' && piles(MapGen.N.BERRY) === '6', `home stone ${piles(MapGen.N.STONE)} and ${piles(MapGen.N.BERRY)} berry bushes (AoE2 Arabia)`);
  ok(DATA.NODES.crystal.amount === 800 && DATA.NODES.crystal.rate === DATA.NODES.iron.rate && w.players[0].res.crystal === 100, 'crystal holds 800 a tile, mines at the gold rate, and you start with 100 of each ore');
}
/* the damage formula and the counter triangle */
{
  const w = new World(7); w.players[0].age = w.players[1].age = 2; w.players[0].rev++; w.players[1].rev++; flat(w, 60, 60);
  const mk = (t, p, x = 60, y = 60) => w.addUnit(t, p, x, y);
  const A = u => { const S = w.S(u); return { melee: S.melee, pierce: S.pierce, bonus: S.bonus }; };
  const sp = mk('spearman', 0), sc = mk('scout', 1), ar = mk('archer', 0), sk = mk('skirmisher', 1), mi = mk('militia', 1), th = mineOf(w, 1, 'town_hall')[0];
  ok(w.damage(A(sp), sc, 60, 60) === 18, 'Pikeman hits cavalry for 3 + 15 bonus = 18');
  ok(w.damage(A(sp), mi, 60, 60) === 3, 'Pikeman hits infantry for 3');
  ok(w.damage(A(ar), sp, 60, 60) === 7 && w.damage(A(ar), sk, 60, 60) === 1, 'Archer: 4 + 3 bonus = 7 on a Pikeman, the minimum 1 on a Slinger (3 pierce armour)');
  ok(w.damage(A(sk), ar, 60, 60) === 5, 'Slinger hits an Archer for 2 + 3 bonus = 5');
  ok(w.damage(A(ar), th, 60, 60) === 1 && w.damage(A(mi), th, 60, 60) === 1, 'arrows and swords barely scratch a Town Hall (armour 3/5)');
  ok(w.S(sc).melee === 5 && w.S(sc).speed === 1.55 && w.S(sc).los === 6, 'a Scout gains +2 attack, +2 sight and speed 1.55 in the Feudal Age');
  for (let y = 0; y <= 3; y++) for (let x = 0; x <= 3; x++) w.map.hc[(80 + y) * 301 + 80 + x] = 3;
  const hi = mk('militia', 0, 81.5, 81.5), lo = mk('militia', 1, 60, 60);
  ok(w.damage(A(hi), lo, hi.x, hi.y) === 5 && w.damage(A(lo), hi, lo.x, lo.y) === 3, 'higher ground x1.25 (4 -> 5), lower ground x0.75 (4 -> 3)');
}
/* arrows fly, then land; 10 pikemen beat 10 scouts; 10 archers beat 10 pikemen */
{
  const fight = (a, b, n = 10) => { const w = new World(7); w.players[0].age = w.players[1].age = 2; flat(w, 100, 60); flat(w, 104, 60);
    for (let k = 0; k < n; k++) { w.addUnit(a, 0, 97 + (k % 5) * 0.5, 59 + (k / 5 | 0) * 0.5); w.addUnit(b, 1, 105 + (k % 5) * 0.5, 59 + (k / 5 | 0) * 0.5); }
    for (const u of mineOf(w, 1, b)) w.setOrder(u, { type: 'amove', x: 97, y: 59 });
    for (const u of mineOf(w, 0, a)) w.setOrder(u, { type: 'amove', x: 105, y: 59 });
    run(w, 90); return [mineOf(w, 0, a).length, mineOf(w, 1, b).length]; };
  const w = new World(7); w.players[0].age = 2; flat(w, 100, 60);
  const ar = w.addUnit('archer', 0, 100, 60), dummy = w.addUnit('militia', 1, 103.5, 60); dummy.stance = 'passive';
  w.setOrder(ar, { type: 'attack', id: dummy.id }); let first = 0; for (let i = 0; i < 90 && !first; i++) { w.step(1 / 30); if (w.shots.length && dummy.hp === 40) first = 1; }
  ok(first === 1, 'an arrow is in the air before it does damage (speed 7 tiles/s)');
  const r1 = fight('spearman', 'scout'), r2 = fight('archer', 'spearman'), r3 = fight('skirmisher', 'archer');
  ok(r1[0] > 0 && r1[1] === 0, `10 Pikemen beat 10 Wolf Riders (${r1[0]} left)`);
  ok(r2[0] > 0 && r2[1] === 0, `10 Archers beat 10 Pikemen (${r2[0]} left)`);
  ok(r3[0] > 0 && r3[1] === 0, `10 Slingers beat 10 Archers (${r3[0]} left)`);
}
/* formations: slowest speed, melee in front, ranged behind */
{
  const w = new World(7); w.players[0].age = 2; w.players[0].rev++; const us = [];
  for (let k = 0; k < 4; k++) { us.push(w.addUnit('archer', 0, 60 + k * 0.5, 60), w.addUnit('militia', 0, 60 + k * 0.5, 61), w.addUnit('scout', 0, 60 + k * 0.5, 62)); }
  w.issue(0, { c: 'move', ids: us.map(u => u.id), x: 60, y: 80 }); w.step(1 / 30);
  ok(us.every(u => u.order.gspeed === 0.9), 'a mixed group marches at its slowest member\'s speed (Militia 0.9)');
  const front = t => us.filter(u => u.type === t).reduce((a, u) => a + u.order.y, 0) / 4;
  ok(front('militia') > front('scout') && front('scout') > front('archer'), 'line formation: infantry in front, cavalry next, archers at the back');
  w.issue(0, { c: 'formation', ids: us.map(u => u.id), formation: 'box' }); w.issue(0, { c: 'stance', ids: us.map(u => u.id), stance: 'ground' }); w.step(1 / 30);
  ok(us.every(u => u.formation === 'box' && u.stance === 'ground'), 'formation and stance are set by command');
}
/* stances */
{
  const test = (stance) => { const w = new World(7); flat(w, 100, 60); flat(w, 104, 60); const m = w.addUnit('militia', 0, 100, 60), e = w.addUnit('militia', 1, 103, 60); e.stance = 'passive'; m.stance = stance; run(w, 6); return [Math.hypot(m.x - 100, m.y - 60), e.hp]; };
  const ag = test('aggressive'), gr = test('ground'), pa = test('passive');
  ok(ag[1] < 40 && ag[0] > 1, 'Aggressive: walks over and attacks an enemy in sight');
  ok(gr[0] < 0.1 && gr[1] === 40 && pa[1] === 40, 'Stand Ground does not leave its spot; No Attack does nothing');
}
/* patrol */
{
  const w = new World(7); flat(w, 100, 60); const m = w.addUnit('militia', 0, 100, 60);
  w.issue(0, { c: 'patrol', ids: [m.id], x: 104, y: 60 }); run(w, 6); const far = m.x; run(w, 6);
  ok(far > 103 && m.x < 101.5 && m.order && m.order.type === 'patrol', 'Patrol walks to the far end and back again');
}
/* age advance, gating, research */
{
  const w = new World(7), P = w.players[0], tc = mineOf(w, 0, 'town_hall')[0], v = mineOf(w, 0, 'villager')[0];
  Object.assign(P.res, { food: 5000, wood: 5000, stone: 5000, iron: 5000, crystal: 5000 });
  const spot = t => { for (let r = 5; r < 16; r++) for (let d = 0; d < 16; d++) { const x = 32 + Math.round(Math.cos(d) * r), y = 32 + Math.round(Math.sin(d) * r); if (w.canPlace(t, 0, x, y)) return [x, y]; } };
  const build = t => { const b = w.place(t, 0, ...spot(t)); if (b) { b.built = true; b.progress = 1; b.hp = b.maxHp; w.recount(0); } return b; };
  ok(!w.place('blacksmith', 0, ...spot('blacksmith')) && w.queueTrain(tc, 'villager') === 1, 'Dark Age: no Blacksmith yet');
  ok(w.techBlock(0, 'feudal').startsWith('Needs two'), 'the Feudal Age needs two Dark Age buildings');
  const bar = build('barracks'); build('mill');
  ok(w.queueTrain(bar, 'spearman') === 0, 'Dark Age Barracks cannot train Pikemen');
  tc.queue = []; const f0 = P.res.food; ok(w.queueTech(tc, 'feudal') && P.res.food === f0 - 500, 'with a Barracks and a Mill the advance starts and costs 500 food');
  run(w, 129); ok(P.age === 1, 'still Dark Age at 129 s'); run(w, 2); ok(P.age === 2, 'Feudal Age reached after 130 s');
  const sm = build('blacksmith'), ra = build('archery_range'), stb = build('stable'), mk = build('market'), tw = build('watch_tower'), lc = build('lumber_camp');
  ok(sm && ra && stb && mk && tw, 'Feudal buildings can now be placed: Blacksmith, Archery Range, Stable, Market, Watch Tower');
  ok(w.queueTrain(bar, 'spearman') === 1 && w.queueTrain(ra, 'archer') === 1 && w.queueTrain(stb, 'scout') === 1, 'and their units trained');
  const mi = w.addUnit('militia', 0, 50, 50), ar = w.addUnit('archer', 0, 50, 51), sc = w.addUnit('scout', 0, 50, 52);
  for (const t of ['man_at_arms', 'supplies', 'forging', 'scale_mail', 'fletching', 'bloodlines', 'wheelbarrow', 'double_bit_axe', 'horse_collar', 'loom']) w.applyTech(0, t);
  let S = w.S(mi);
  ok(mi.maxHp === 45 && S.melee === 7 && S.armor[0] === 1 && S.armor[1] === 2 && w.unitName(mi) === 'Man-at-Arms', 'Man-at-Arms + Forging + Scale Mail: 45 HP, 7 attack, 1/2 armour');
  ok(w.unitCost(0, 'militia').food === 35, 'Supplies: Militia line costs 15 less food');
  S = w.S(ar); ok(S.pierce === 5 && S.range === 5, 'Fletching: Archer 5 attack, range 5');
  ok(sc.maxHp === 65 && sc.hp === 65, 'Bloodlines: Wolf Rider 65 HP');
  ok(w.carryCap(0) === 12.5 && Math.abs(w.S(v).speed - 0.88) < 1e-9 && v.maxHp === 40, 'Wheelbarrow: carry 12.5, speed 0.88; Loom: 40 HP');
  ok(w.farmFood(0) === 250, 'Horse Collar: farms hold 250 food');
  const before = P.res.iron; ok(w.trade(0, 'food', true) === '' && P.res.iron === before - 130 && w.market.food === 103, 'Market: buying 100 food costs 130 iron and lifts the price to 103');
  ok(w.trade(0, 'stone', false) === '' && w.market.stone === 127, 'selling 100 stone pays 91 iron and drops its price to 127');
  /* towers and town halls */
  const foe = w.addUnit('militia', 1, tw.x + 4, tw.y); foe.stance = 'passive'; run(w, 5);
  ok(foe.hp < 40, 'a Watch Tower shoots an enemy in range');
  const foe2 = w.addUnit('militia', 1, tc.x + 5, tc.y); foe2.stance = 'passive'; run(w, 5);
  ok(foe2.hp === 40, 'an empty Town Hall does not shoot (AoE2)');
  w.issue(0, { c: 'bell' }); run(w, 12); ok(foe2.dead || foe2.hp < 40, 'with peasants inside it does');
}
process.exit(fail ? 1 : 0);
