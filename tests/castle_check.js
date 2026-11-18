/* node tests/castle_check.js : AoE2's Castle Age rules. The advance and its gate, more Town Halls, unit-line upgrades,
   heavy cavalry and mounted archers, Mystics (heal, convert, faith, artifacts), siege engines, the Citadel, Academy
   research (Masonry, Fortified Wall, Guard Tower, Murder Holes, Ballistics) and the economy upgrades. */
const World = require('../game/src/world.js'), DATA = require('../game/src/data.js');
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
const run = (w, s) => { for (let i = 0; i < Math.round(30 * s); i++) w.step(1 / 30); };
const mineOf = (w, p, t) => w.ents.filter(e => !e.dead && e.owner === p && e.type === t);
const flat = (w, x, y, r = 8) => { for (let b = y - r; b <= y + r; b++) for (let a = x - r; a <= x + r; a++) w.map.hc[b * 301 + a] = 0; };
const age = (w, n, ps = [0, 1]) => { for (const p of ps) { w.players[p].age = n; w.players[p].rev++; } };
const give = (w, p, ...ts) => { for (const t of ts) w.applyTech(p, t); };
const rich = (w, p = 0) => { for (const k of DATA.RES) w.players[p].res[k] = 99999; };
const A = (w, u) => { const S = w.S(u); return { melee: S.melee, pierce: S.pierce, bonus: S.bonus }; };
const spot = (w, type) => { for (let r = 5; r < 16; r++) for (let d = 0; d < 16; d++) { const x = 34 + Math.round(Math.cos(d * 0.39) * r), y = 34 + Math.round(Math.sin(d * 0.39) * r); if (w.canPlace(type, 0, x, y)) return [x, y]; } return null; };
/* an empty, flat arena far from both bases and every camp; the player sees all of it (vision is not what is tested here) */
const arena = (n = 3) => { const w = new World(7); age(w, n); flat(w, 60, 60, 14); for (const e of w.ents) if (e.owner === 2 && Math.hypot(e.x - 60, e.y - 60) < 20) w.remove(e);
  const uv = w.updateVision.bind(w); w.updateVision = a => { uv(a); w.players[0].vis.fill(1); }; w.updateVision(); return w; };

/* 1. the advance: 800 food and 200 crystal, two Feudal Age buildings, 160 seconds (AoE2) */
{
  const w = new World(7), P = w.players[0], tc = mineOf(w, 0, 'town_hall')[0]; age(w, 2, [0]); rich(w);
  const T = DATA.TECHS.castle;
  ok(T.cost.food === 800 && T.cost.crystal === 200 && T.time === 160 && !T.locked, 'Castle Age: 800 food, 200 crystal (AoE2 gold), 160 s');
  ok(/two of/.test(w.techBlock(0, 'castle')), 'it needs two Feudal Age buildings: ' + w.techBlock(0, 'castle'));
  ok(w.place('castle', 0, ...spot(w, 'castle')) === null && w.place('town_hall', 0, ...spot(w, 'town_hall')) === null, 'no Citadel and no second Town Hall in the Feudal Age');
  let s = spot(w, 'blacksmith'); w.addBuilding('blacksmith', 0, s[0], s[1], true); s = spot(w, 'market'); w.addBuilding('market', 0, s[0], s[1], true);
  ok(w.techBlock(0, 'castle') === '', 'a Blacksmith and a Market open it');
  ok(w.techBlock(0, 'iron_casting') !== '' && w.techBlock(0, 'hand_cart') !== '', 'Castle Age research is closed before the advance');
  w.issue(0, { c: 'research', id: tc.id, tech: 'castle' }); run(w, 159); ok(P.age === 2, 'still Feudal after 159 s');
  run(w, 2); ok(P.age === 3 && P.res.food === 99999 - 800, 'Castle Age after 160 s');
  const th = w.place('town_hall', 0, ...spot(w, 'town_hall'));
  ok(!!th && P.res.wood === 99999 - 275 && P.res.stone === 99999 - 100, 'a second Town Hall can be founded: 275 wood, 100 stone (AoE2 Town Center)');
  ok(/Needs Forging/.test(w.techBlock(0, 'iron_casting')) && /Needs Man-at-Arms/.test(w.techBlock(0, 'long_swordsman')), 'each upgrade needs the step before it (Iron Casting after Forging, Long Swordsman after Man-at-Arms)');
  const c = w.place('castle', 0, ...spot(w, 'castle'));
  ok(!!c && P.res.stone === 99999 - 750, 'a Citadel costs 650 stone (AoE2 Castle)');
  const cap = P.popCap; c.built = true; c.progress = 1; w.recount(0); ok(P.popCap === cap + 20, 'a finished Citadel gives +20 population');
}
/* 2. unit lines upgrade in place; blacksmith research stacks; the new cavalry */
{
  const w = arena(); const mk = (t, p, x = 60, y = 60) => { const u = w.addUnit(t, p, x, y); u.stance = 'passive'; return u; };
  const mi = mk('militia', 0), sp = mk('spearman', 0), ar = mk('archer', 0), sk = mk('skirmisher', 0), sc = mk('scout', 0), kn = mk('knight', 1), ca = mk('cavarcher', 1), eAr = mk('archer', 1);
  give(w, 0, 'man_at_arms', 'long_swordsman', 'pikeman', 'crossbow', 'elite_skirmisher', 'light_cavalry');
  let S = w.S(mi); ok(mi.maxHp === 60 && S.melee === 9 && S.bonus.building === 3 && w.unitName(mi) === 'Long Swordsman', 'Long Swordsman: 60 HP, 9 attack, +3 against buildings');
  S = w.S(sp); ok(sp.maxHp === 55 && S.melee === 4 && w.unitName(sp) === 'Dwarf Halberdier' && w.damage(A(w, sp), kn, 60, 60) === 24, 'Dwarf Halberdier (AoE2 Pikeman): 55 HP; 4 - 2 armour + 22 bonus = 24 on a Bear Knight');
  S = w.S(ar); ok(ar.maxHp === 35 && S.pierce === 5 && S.range === 5 && S.acc === 0.85, 'Elf Longbow (AoE2 Crossbowman): 35 HP, 5 attack, range 5');
  S = w.S(sk); ok(sk.maxHp === 35 && S.pierce === 3 && S.armor[1] === 4 && S.range === 5 && w.damage(A(w, sk), eAr, 60, 60) === 7, 'Elite Halfling Slinger: 35 HP, 3 attack, 4 pierce armour, range 5; 3 + 4 = 7 on an archer');
  S = w.S(sc); ok(sc.maxHp === 60 && S.melee === 7 && S.bonus.monk === 10 && w.unitName(sc) === 'Wolf Raider', 'Wolf Raider (AoE2 Light Cavalry): 60 HP, 7 attack, +10 against Mystics');
  const fresh = w.addUnit('militia', 0, 61, 61); ok(fresh.maxHp === 60 && w.typeName(0, 'militia') === 'Long Swordsman', 'newly trained units come out upgraded');
  S = w.S(kn); ok(kn.maxHp === 100 && S.melee === 10 && S.armor[0] === 2 && S.armor[1] === 2 && S.speed === 1.35 && DATA.UNITS.knight.cost.food === 60 && DATA.UNITS.knight.cost.iron === 75, 'Bear Knight (AoE2 Knight): 100 HP, 10 attack, 2/2 armour, speed 1.35, 60 food and 75 iron');
  ok(w.damage(A(w, kn), eAr, 60, 60) === 10 && w.damage(A(w, eAr), kn, 60, 60) === 2, 'a Knight hits an archer for 10 and takes 4 - 2 = 2 from its arrow');
  S = w.S(ca); ok(ca.maxHp === 50 && S.pierce === 6 && S.range === 4 && S.speed === 1.4, 'Centaur Archer (AoE2 Cavalry Archer): 50 HP, 6 attack, range 4, speed 1.4');
  ok(w.damage(A(w, sp), ca, 60, 60) === 4 && w.damage(A(w, sk), ca, 60, 60) === 3 + 4 + 2, 'pikes get no cavalry bonus on a Centaur Archer; an Elite Slinger gets its archer bonus and +2 more');
  give(w, 0, 'forging', 'iron_casting', 'scale_mail', 'chain_mail', 'fletching', 'bodkin', 'padded_archer', 'leather_archer', 'squires', 'arson', 'gambesons', 'thumb_ring', 'husbandry');
  S = w.S(mi); ok(S.melee === 11 && S.armor[0] === 2 && S.armor[1] === 4 && S.bonus.building === 5 && Math.abs(S.speed - 0.99) < 1e-9, 'Forging + Iron Casting, Scale + Chain Mail, Gambesons, Arson, Squires: 11 attack, 2/4 armour, +5 against buildings, speed 0.99');
  S = w.S(ar); ok(S.pierce === 7 && S.range === 7 && S.armor[0] === 2 && S.armor[1] === 2 && S.acc === 1 && Math.abs(S.reload - 1.7) < 1e-9, 'Fletching + Bodkin, Padded + Leather, Thumb Ring: 7 attack, range 7, 2/2, never misses, fires 15% faster');
  ok(Math.abs(w.S(sc).speed - 1.55 * 1.1) < 1e-9, 'Husbandry: mounted units 10% faster');
  give(w, 1, 'bloodlines', 'scale_barding', 'chain_barding');
  ok(kn.maxHp === 120 && ca.maxHp === 70 && w.S(kn).armor[0] === 4 && w.S(ca).armor[0] === 0, 'Bloodlines covers both mounts; barding only the cavalry');
}
/* 3. Mystics: healing, conversion and faith, what they may not convert, Heresy */
{
  const w = arena(), C = DATA.UNITS.monk.convert;
  const m = w.addUnit('monk', 0, 60, 60), hurt = w.addUnit('militia', 0, 62, 60); hurt.hp = 10; w.recount(0);
  ok(DATA.UNITS.monk.cost.iron === 100 && m.maxHp === 30 && C.range === 9 && C.recharge === 62, 'Mystic (AoE2 Monk): 100 iron, 30 HP, converts from 9 tiles, faith back in 62 s');
  run(w, 4); ok(m.order && m.order.type === 'heal' && Math.abs(hurt.hp - (10 + 2.5 * 3.5)) < 1.5, `an idle Mystic heals the wounded beside it at 2.5 HP a second (${hurt.hp.toFixed(1)} HP after 4 s)`);
  run(w, 12); ok(hurt.hp === hurt.maxHp && !m.order, 'and stops when the patient is whole');
  const foe = w.addUnit('knight', 1, 66, 60); foe.stance = 'passive'; w.recount(1);
  const pop0 = w.players[0].pop, pop1 = w.players[1].pop, t0 = w.time;
  w.issue(0, { c: 'order', ids: [m.id], target: foe.id, x: foe.x, y: foe.y });
  let at = 0; for (let i = 0; i < 30 * 14 && !at; i++) { w.step(1 / 30); if (foe.owner === 0) at = w.time - t0; }
  ok(at >= C.min * C.tick - 0.1 && at <= C.max * C.tick + 0.2, `a Knight changes sides after ${at.toFixed(1)} s (AoE2: between the 4th and 10th monk second, 4.8 to 12 s)`);
  ok(w.players[0].pop === pop0 + 1 && w.players[1].pop === pop1 - 1 && m.faith < 0.05, 'population moves with it and the Mystic\'s faith is spent');
  const foe2 = w.addUnit('militia', 1, 66, 62); foe2.stance = 'passive';
  w.issue(0, { c: 'order', ids: [m.id], target: foe2.id, x: foe2.x, y: foe2.y }); run(w, 30);
  ok(foe2.owner === 1, 'no second conversion while faith is returning');
  run(w, 45); ok(foe2.owner === 0 && w.time - t0 > 62, 'after 62 s the faith is back and the next conversion goes through');
  const ram = w.addUnit('ram', 1, 64, 58), em = w.addUnit('monk', 1, 64, 64), wolf = w.addUnit('wolf', 2, 70, 70), etc = mineOf(w, 1, 'town_hall')[0], bar = w.addBuilding('barracks', 1, 66, 54, true);
  em.stance = 'passive'; wolf.camp = undefined; wolf.home = [70, 70];
  ok(w.convertBlock(0, ram) !== '' && w.convertBlock(0, em) !== '' && w.convertBlock(0, bar) !== '' && w.convertBlock(0, wolf) !== '', 'siege, Mystics, buildings and wild creatures cannot be converted at first');
  give(w, 0, 'redemption', 'atonement');
  ok(w.convertBlock(0, ram) === '' && w.convertBlock(0, em) === '' && w.convertBlock(0, bar) === '' && w.convertBlock(0, etc) !== '' && w.convertBlock(0, wolf) !== '', 'Redemption opens siege and buildings, Atonement opens Mystics; Town Halls and creeps never');
  w.convert(0, bar, m); ok(bar.owner === 0 && mineOf(w, 0, 'barracks').includes(bar), 'a converted Barracks is yours');
  give(w, 1, 'heresy'); w.convert(0, ram, m); ok(ram.dead && ram.owner === 1, 'Heresy: the converted die instead of changing sides');
}
/* 4. artifacts: a Mystic carries one to a Sanctum, which pays crystal like an AoE2 relic in a Monastery */
{
  const w = arena(), m = w.addUnit('monk', 0, 60, 60), a = w.addArtifact(62, 60), san = w.addBuilding('monastery', 0, 55, 62, true), c0 = w.players[0].res.crystal;
  w.issue(0, { c: 'pickup', ids: [m.id] }); run(w, 25);
  ok(san.artifacts === 1 && !m.artifact, 'picked up and stored in the nearest Sanctum');
  const c1 = w.players[0].res.crystal; run(w, 20); ok(Math.abs(w.players[0].res.crystal - c1 - 10) < 0.6, 'a stored artifact gives 0.5 crystal a second');
}
/* 5. siege engines */
{
  const w = arena(); const mk = (t, p, x, y) => { const u = w.addUnit(t, p, x, y); u.stance = 'passive'; return u; };
  const ram = mk('ram', 0, 60, 60), wall = w.addBuilding('stone_wall', 1, 64, 60, true), eAr = mk('archer', 1, 62, 64), eMi = mk('militia', 1, 62, 66);
  ok(w.damage(A(w, ram), wall, 60, 60) === 125 && w.damage(A(w, eAr), ram, 60, 60) === 1 && w.damage(A(w, eMi), ram, 60, 60) === 7, 'Battering Ram: 125 on a Stone Wall; an arrow does 1 to it, a sword 4 + 3 = 7 (armour -3/180)');
  ok(!w.canTarget(ram, eAr) && w.canTarget(ram, wall) && w.findEnemy(ram, 20) === wall, 'a Ram strikes buildings and siege only');
  w.issue(0, { c: 'order', ids: [ram.id], target: wall.id, x: wall.x, y: wall.y }); run(w, 14);
  ok(wall.hp <= 1800 - 125, `it walks up and batters the wall (${wall.hp} of 1800 HP after 14 s)`);
  // Catapult: the rock lands where it was aimed and hits everything there
  const cat = mk('mangonel', 0, 50, 70), pack = [mk('archer', 1, 57, 70), mk('archer', 1, 57.5, 70.4), mk('archer', 1, 56.6, 69.6)], far = mk('archer', 1, 57, 73), own = mk('militia', 0, 57.3, 69.5);
  flat(w, 54, 70);
  w.issue(0, { c: 'order', ids: [cat.id], target: pack[0].id, x: 57, y: 70 }); run(w, 4);
  ok(pack.every(u => u.dead) && far.hp === 30, 'a Catapult rock (40 damage) kills three archers standing together and leaves one 3 tiles off untouched');
  ok(own.hp < own.maxHp, 'your own soldier in the blast is hit too (AoE2 friendly fire)');
  const walker = mk('archer', 1, 57, 70); w.issue(0, { c: 'order', ids: [cat.id], target: walker.id, x: 57, y: 70 });   // once reloaded (6 s) it fires at the walker, who steps away while the rock is in the air
  let fired = false; for (let i = 0; i < 30 * 9; i++) { w.step(1 / 30); if (!fired && w.shots.length) { fired = true; walker.x += 2.5; } }
  ok(fired && walker.hp === 30, 'a rock misses a target that walks away from where it was aimed');
  const close = mk('archer', 1, 51.5, 70); cat.order = null; w.issue(0, { c: 'order', ids: [cat.id], target: close.id, x: close.x, y: close.y }); run(w, 8);
  ok(close.hp === 30, 'it cannot fire at something 1.5 tiles away (minimum range 3)');
  // Bolt Thrower: one bolt through a file of enemies
  const bolt = mk('scorpion', 0, 50, 54), file = [mk('militia', 1, 55, 54), mk('militia', 1, 55.9, 54), mk('militia', 1, 56.8, 54)], aside = mk('militia', 1, 55, 56);
  flat(w, 54, 54);
  w.issue(0, { c: 'order', ids: [bolt.id], target: file[1].id, x: 55.9, y: 54 }); run(w, 2.5);
  ok(file[0].hp === 40 - 11 && file[1].hp === 40 - 11 && aside.hp === 40, 'a Bolt Thrower bolt (12 pierce) runs through the enemies in its line and spares the one beside it');
}
/* 6. the Citadel, garrisons, and Academy research */
{
  const w = arena(), c = w.addBuilding('castle', 0, 58, 58, true), foe = w.addUnit('knight', 1, 67, 60); foe.stance = 'passive';
  const D = DATA.BUILDINGS.castle; ok(D.hp === 4800 && D.cost.stone === 650 && D.arrows.atk === 11 && D.arrows.range === 8 && D.arrows.base === 5 && D.garrison === 20 && D.time === 200, 'Citadel (AoE2 Castle): 4800 HP, 650 stone, 11 attack, range 8, five arrows, garrison 20, 200 s');
  run(w, 1.5); ok(foe.hp === 100 - 5 * 9, `five arrows at once, each 11 - 2 armour = 9 (Knight at ${foe.hp})`);
  w.remove(foe);
  const kn = w.addUnit('knight', 0, 56, 56), ram = w.addUnit('ram', 0, 56, 57), tw = w.addBuilding('watch_tower', 0, 54, 56, true), ar = w.addUnit('archer', 0, 55, 57);
  ok(w.canGarrison(kn, c) && !w.canGarrison(ram, c) && !w.canGarrison(kn, tw) && w.canGarrison(ar, tw), 'a Citadel shelters cavalry; nothing shelters siege; a tower takes only those on foot');
  const wall = w.addBuilding('stone_wall', 0, 50, 50, true), hall = mineOf(w, 0, 'town_hall')[0];
  give(w, 0, 'masonry'); ok(hall.maxHp === 2640 && hall.hp === 2640 && w.B(hall).armor[0] === 4 && w.B(hall).armor[1] === 6, 'Masonry: buildings +10% HP and +1/+1 armour (Town Hall 2640, 4/6)');
  give(w, 0, 'fortified_wall', 'guard_tower'); ok(wall.maxHp === 3300 && w.B(wall).armor[0] === 13 && tw.maxHp === 1650 && w.B(tw).atk === 1, 'Fortified Wall 3000 HP and 12/12, Guard Tower 1500 HP and +1 attack (each +10% and +1 from Masonry)');
  w.remove(c); kn.stance = ar.stance = 'passive'; const near = w.addUnit('militia', 1, 54.5, 57.6); near.stance = 'passive';
  const hpA = near.hp; run(w, 4); ok(w.distTo(near, tw) < 1 && near.hp === hpA, 'a tower cannot shoot straight down at a soldier hugging its wall');
  give(w, 0, 'murder_holes'); run(w, 4); ok(near.hp < hpA, 'with Murder Holes it can');
  // Ballistics
  const sh = w.addUnit('archer', 0, 60, 66), tg = w.addUnit('militia', 1, 64, 66); sh.stance = tg.stance = 'passive';
  w.shoot(sh, tg, { pierce: 6 }, 1, 0.7); tg.y += 1; run(w, 1); ok(tg.hp === 40, 'an arrow misses a target that stepped a tile aside while it flew');
  w.shoot(sh, tg, { pierce: 6 }, 1, 0.7); tg.x -= 1; run(w, 1); ok(tg.hp === 35, 'one that walked into the shot is still hit');
  give(w, 0, 'ballistics'); w.shoot(sh, tg, { pierce: 6 }, 1, 0.7); tg.y += 1; run(w, 1); ok(tg.hp === 30, 'with Ballistics the arrow leads its target and hits');
}
/* 7. economy research */
{
  const w = new World(7); age(w, 3, [0]); const v = mineOf(w, 0, 'villager')[0];
  give(w, 0, 'wheelbarrow', 'hand_cart', 'horse_collar', 'heavy_plow', 'town_watch', 'town_patrol');
  ok(w.carryCap(0) === 20 && Math.abs(w.S(v).speed - 0.8 * 1.21) < 1e-9, 'Hand Cart: peasants carry 20 and are another 10% faster');
  ok(w.farmFood(0) === 175 + 75 + 125, 'Heavy Plough: farms hold 375 food');
  ok(w.losOf(mineOf(w, 0, 'town_hall')[0]) === 16, 'Town Patrol: buildings see 4 further again');
  const T = DATA.TECHS; ok(T.bow_saw.req === 'double_bit_axe' && T.ore_shaft.req === 'ore_mining' && T.stone_shaft.req === 'stone_mining' && T.treadmill_crane.age === 3, 'Bow Saw, Ore Shaft Mining, Stone Shaft Mining and Treadmill Crane are in');
}
/* 8. the new rules keep the game deterministic */
{
  const play = () => { const w = arena(); const m = w.addUnit('monk', 0, 60, 60), cat = w.addUnit('mangonel', 0, 58, 62), es = [0, 1, 2, 3].map(k => w.addUnit(k % 2 ? 'knight' : 'archer', 1, 67 + k * 0.5, 60 + k));
    w.issue(0, { c: 'order', ids: [m.id], target: es[1].id, x: 67, y: 61 }); w.issue(0, { c: 'order', ids: [cat.id], target: es[0].id, x: 67, y: 60 }); run(w, 40); return w.hash(); };
  const h1 = play(), h2 = play(); ok(h1 === h2, `same seed and commands, same game, with conversion and siege in it (${h1})`);
}
process.exit(fail ? 1 : 0);
