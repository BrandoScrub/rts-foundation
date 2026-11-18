/* world.js: the simulation. No drawing and no DOM here, so it also runs in Node for tests.
   Players: 0 = you, 1 = the opponent (an idle placeholder in this build), 2 = nature (wildlife and creep camps). */
'use strict';
if (typeof module !== 'undefined') { global.DATA = require('./data.js'); global.MapGen = require('./map.js'); global.Path = require('./path.js'); }

class World {
  constructor(seed = 7) {
    const m = this.map = MapGen.generate(seed);
    this.W = m.W; this.H = m.H; this.time = 0; this.tick = 0; this.nextId = 1;
    this.rand = MapGen.rng(seed * 7919 + 13);   // every random choice in the simulation comes from here: same seed + same commands = same game
    this.pending = []; this.log = []; this.pathBudget = 0; this.shots = [];
    this.market = Object.assign({}, DATA.MARKET.start);   // AoE2: one set of market prices for the whole game
    this.ents = []; this.byId = new Map(); this.fx = []; this.alerts = []; this.messages = [];
    this.occ = new Int32Array(this.W * this.H);
    Path.init(this.W, this.H);
    this.players = [0, 1, 2].map(id => ({ id, color: DATA.PLAYER_COLORS[id], res: Object.assign({}, DATA.START_RES),
      techs: new Set(), age: 1, rev: 1, popCap: 0, pop: 0, gathered: { food: 0, wood: 0, stone: 0, iron: 0, crystal: 0 },
      vis: new Uint8Array(this.W * this.H), explored: new Uint8Array(this.W * this.H), seen: new Map(), defeated: false }));
    this.players[2].res = {};
    this.camps = m.camps.map(c => Object.assign(c, { members: [], cleared: false }));
    this.state = 'playing';
    this.setup();
    this.visTimer = 0; this.slowTimer = 0;
    this.updateVision(true);
  }

  /* ------------------------------------------------------------ setup */
  setup() {
    const m = this.map;
    m.starts.forEach(([cx, cy], p) => {
      const tc = this.addBuilding('town_hall', p, cx - 2, cy - 2, true);
      const sp = this.spawnPoint(tc);
      for (let k = 0; k < 3; k++) this.addUnit('villager', p, sp[0] + (k - 1) * 0.6, sp[1] + 0.6);
      this.addUnit('scout', p, sp[0] + 1.2, sp[1] + 1.5);
    });
    for (const s of m.spawns) this.addUnit(s.kind, 2, s.x, s.y);
    for (const c of this.camps) for (const g of c.guards) {
      const u = this.addUnit(g.kind, 2, g.x, g.y); u.camp = c.id; u.home = [g.x, g.y]; c.members.push(u.id);
    }
    this.recount(0); this.recount(1);
  }
  campById(id) { return this.camps.find(c => c.id === id); }

  /* ------------------------------------------------------------ entities */
  add(e) { e.id = this.nextId++; this.ents.push(e); this.byId.set(e.id, e); return e; }
  get(id) { const e = this.byId.get(id); return e && !e.dead ? e : null; }
  addUnit(type, owner, x, y) {
    const D = DATA.UNITS[type] || DATA.WILD[type];
    const u = this.add({ kind: 'unit', type, owner, x, y, D, hp: D.hp, maxHp: D.hp, r: D.r, order: null, queue: [],
      path: null, cool: 0, carry: { res: null, amt: 0 }, facing: this.rand() * 6.28, moving: false, walkT: 0, stuck: 0, repathT: 0,
      stance: 'aggressive', formation: 'line' });
    u.maxHp = u.hp = this.hpOf(u);
    return u;
  }
  addBuilding(type, owner, tx, ty, complete = false) {
    const D = DATA.BUILDINGS[type], s = D.size;
    const b = this.add({ kind: 'building', type, owner, D, tx, ty, size: s, x: tx + s / 2, y: ty + s / 2, r: s * 0.5,
      hp: complete ? D.hp : 1, maxHp: D.hp, progress: complete ? 1 : 0, built: complete, queue: [], rally: null,
      garrison: [], artifacts: 0, food: D.walk ? this.farmFood(owner) : 0, farmer: 0, cool: 0, builders: 0 });
    for (let y = ty; y < ty + s; y++) for (let x = tx; x < tx + s; x++) this.occ[y * this.W + x] = b.id;
    this.recount(owner);
    return b;
  }
  remove(e) {
    e.dead = true;
    if (e.kind === 'building') {
      for (let y = e.ty; y < e.ty + e.size; y++) for (let x = e.tx; x < e.tx + e.size; x++) if (this.occ[y * this.W + x] === e.id) this.occ[y * this.W + x] = 0;
      for (const id of e.garrison) { const u = this.byId.get(id); if (u) { u.garrisoned = 0; const p = this.spawnPoint(e); u.x = p[0]; u.y = p[1]; } }
      for (let k = 0; k < e.artifacts; k++) this.addArtifact(e.x + k * 0.5, e.y + e.r + 0.3);
      this.recount(e.owner);
    }
    if (e.kind === 'unit' && e.artifact) { const a = this.get(e.artifact); if (a) { a.carrier = 0; a.x = e.x; a.y = e.y; } }
  }
  addArtifact(x, y) { return this.add({ kind: 'artifact', type: 'artifact', owner: 2, x, y, r: 0.25, carrier: 0, hp: 1, maxHp: 1 }); }
  recount(p) {
    if (p > 1) return;
    let cap = 0, pop = 0;
    for (const e of this.ents) if (!e.dead && e.owner === p) {
      if (e.kind === 'building' && e.built && e.D.pop) cap += e.D.pop;
      if (e.kind === 'unit' && DATA.UNITS[e.type]) pop++;
    }
    this.players[p].popCap = Math.min(DATA.POP_MAX, cap); this.players[p].pop = pop;
  }

  /* ------------------------------------------------------------ stats: base numbers plus research and age */
  tech(p, k) { return p < 2 && this.players[p].techs.has(k); }
  farmFood(p) { return DATA.FARM.food + (this.tech(p, 'horse_collar') ? 75 : 0); }
  carryCap(p) { return DATA.CARRY * (this.tech(p, 'wheelbarrow') ? 1.25 : 1); }
  unitCost(p, type) { const c = Object.assign({}, DATA.UNITS[type].cost); if (type === 'militia' && this.tech(p, 'supplies')) c.food -= 15; return c; }
  unitName(u) { return u.type === 'militia' && this.tech(u.owner, 'man_at_arms') ? 'Man-at-Arms' : u.D.name; }
  hpOf(u) {
    const p = u.owner, c = u.D.cls || []; let hp = u.D.hp;
    if (u.type === 'villager' && this.tech(p, 'loom')) hp += 15;
    if (u.type === 'militia' && this.tech(p, 'man_at_arms')) hp = 45;
    if (c.includes('cavalry') && this.tech(p, 'bloodlines')) hp += 20;
    return hp;
  }
  /* S(u): a unit's effective stats, cached until its player's research changes */
  S(u) {
    const p = u.owner, rev = p < 2 ? this.players[p].rev : 0;
    if (u.sRev === rev && u.sCache) return u.sCache;
    const D = u.D, c = D.cls || [], T = k => this.tech(p, k);
    let melee = D.atk.melee || 0, pierce = D.atk.pierce || 0, am = D.armor[0], ap = D.armor[1], range = D.range || 0, speed = D.speed, los = D.los, bonus = D.bonus || {};
    const inf = c.includes('infantry'), cav = c.includes('cavalry'), arch = c.includes('archer');
    if (p < 2) {
      if (u.type === 'villager') { if (T('loom')) { am += 1; ap += 2; } if (T('wheelbarrow')) speed *= 1.1; }
      if (u.type === 'militia' && T('man_at_arms')) { melee = 6; bonus = { building: 2 }; }
      if (u.type === 'scout' && this.players[p].age >= 2) { melee += DATA.FEUDAL_SCOUT.atk; los += DATA.FEUDAL_SCOUT.los; speed = DATA.FEUDAL_SCOUT.speed; }
      if ((inf || cav) && T('forging')) melee += 1;
      if (inf && T('scale_mail')) { am++; ap++; }
      if (cav && T('scale_barding')) { am++; ap++; }
      if (arch && T('fletching')) { pierce++; range++; }
      if (arch && T('padded_archer')) { am++; ap++; }
    }
    u.sRev = rev;
    return u.sCache = { melee, pierce, bonus, armor: [am, ap], range, min: D.min || 0, acc: D.acc || 1, reload: D.reload || 2, speed, los };
  }
  /* AoE2's damage formula: each attack class against its armour, never below 0 each, at least 1 in total, times the hill factor */
  damage(A, t, sx, sy) {
    let am, ap, cls;
    if (t.kind === 'building') { am = t.D.armor[0]; ap = t.D.armor[1]; cls = ['building']; }
    else { const S = this.S(t); am = S.armor[0]; ap = S.armor[1]; cls = t.D.cls || []; }
    let d = (A.melee ? Math.max(0, A.melee - am) : 0) + (A.pierce ? Math.max(0, A.pierce - ap) : 0);
    if (A.bonus) for (const k in A.bonus) if (cls.includes(k)) d += A.bonus[k];
    const dh = this.h(sx, sy) - this.h(t.x, t.y);
    if (dh > 0.5) d *= 1 + DATA.ELEV_BONUS; else if (dh < -0.5) d *= 1 - DATA.ELEV_BONUS;
    return Math.max(1, d);
  }
  /* loose an arrow: it flies at AoE2's arrow speed and lands (or misses) when it arrives */
  shoot(src, t, A, acc, z0) {
    const d = Math.hypot(t.x - src.x, t.y - src.y), life = Math.max(0.12, d / DATA.ARROW_SPEED), hit = this.rand() < acc;
    const ox = hit ? 0 : (this.rand() - 0.5) * 1.6, oy = hit ? 0 : (this.rand() - 0.5) * 1.6;
    this.shots.push({ src: { id: src.id, owner: src.owner, x: src.x, y: src.y, kind: src.kind }, target: t.id, A, t: 0, life, hit });
    this.fx.push({ kind: 'arrow', x0: src.x, y0: src.y, z0, x1: t.x + ox, y1: t.y + oy, t: 0, life });
  }

  /* ------------------------------------------------------------ geometry */
  h(x, y) { return MapGen.tileH(this.map, x, y); }
  walkable(i, owner) {
    if (this.map.node[i] || this.map.water[i] === 1) return false;
    const b = this.occ[i]; if (!b) return true;
    const e = this.byId.get(b); if (!e) return true;
    return !!(e.D.walk || (e.D.gate && e.built && e.owner === owner));
  }
  walkFn(owner) { return i => this.walkable(i, owner); }
  rectOf(e) {
    if (e.kind === 'building') return [e.tx, e.ty, e.tx + e.size - 1, e.ty + e.size - 1];
    const x = Math.floor(e.x), y = Math.floor(e.y); return [x, y, x, y];
  }
  distTo(u, e) {   // edge distance from a unit's centre to an entity
    if (e.kind === 'building') {
      const dx = Math.max(e.tx - u.x, 0, u.x - (e.tx + e.size)), dy = Math.max(e.ty - u.y, 0, u.y - (e.ty + e.size));
      return Math.hypot(dx, dy);
    }
    return Math.max(0, Math.hypot(e.x - u.x, e.y - u.y) - (e.r || 0));
  }
  distToTile(u, t) { const x = t % this.W, y = (t / this.W) | 0;
    return Math.hypot(Math.max(x - u.x, 0, u.x - x - 1), Math.max(y - u.y, 0, u.y - y - 1)); }
  spawnPoint(b, toward) {   // a free tile just outside a building, on the side facing `toward` (or the front)
    const tx = toward ? toward[0] : b.x + b.size, ty = toward ? toward[1] : b.y + b.size;
    let best = null, bd = 1e9;
    for (let y = b.ty - 1; y <= b.ty + b.size; y++) for (let x = b.tx - 1; x <= b.tx + b.size; x++) {
      if (x >= b.tx && x < b.tx + b.size && y >= b.ty && y < b.ty + b.size) continue;
      if (x < 0 || y < 0 || x >= this.W || y >= this.H || !this.walkable(y * this.W + x, b.owner)) continue;
      const d = Math.hypot(x + 0.5 - tx, y + 0.5 - ty); if (d < bd) { bd = d; best = [x + 0.5, y + 0.5]; }
    }
    return best || [b.x, b.ty + b.size + 0.5];
  }
  isHostile(a, b) {
    if (!a || !b || a.owner === b.owner) return false;
    if (a.owner === 2 && !(a.D && (a.D.creep || a.D.fight))) return false;
    if (b.owner === 2 && b.kind === 'unit' && !(b.D.creep || b.D.fight)) return false;
    if (b.kind === 'artifact') return false;
    return true;
  }
  canAfford(p, cost) { const r = this.players[p].res; for (const k in cost) if ((r[k] || 0) < cost[k]) return false; return true; }
  pay(p, cost, sign = 1) { const r = this.players[p].res; for (const k in cost) r[k] = (r[k] || 0) - sign * cost[k]; }
  has(p, type) { return this.ents.some(e => !e.dead && e.owner === p && e.type === type && e.kind === 'building' && e.built); }

  /* ------------------------------------------------------------ placement */
  canPlace(type, p, tx, ty) {
    const D = DATA.BUILDINGS[type], s = D.size;
    if (tx < 1 || ty < 1 || tx + s > this.W - 1 || ty + s > this.H - 1) return false;
    let lo = 99, hi = -1;
    for (let y = ty; y < ty + s; y++) for (let x = tx; x < tx + s; x++) {
      const i = y * this.W + x;
      if (this.map.node[i] || this.occ[i] || this.map.water[i]) return false;
      if (p === 0 && !this.players[0].explored[i]) return false;
    }
    for (let y = ty; y <= ty + s; y++) for (let x = tx; x <= tx + s; x++) { const v = this.map.hc[y * (this.W + 1) + x]; lo = Math.min(lo, v); hi = Math.max(hi, v); }
    if (hi - lo > (s >= 3 ? 1 : 2)) return false;   // AoE2 allows gentle slopes; steep ground refuses big buildings
    for (const e of this.ents) if (!e.dead && e.kind === 'unit' && !e.garrisoned && e.owner !== p &&
      e.x > tx - 0.2 && e.x < tx + s + 0.2 && e.y > ty - 0.2 && e.y < ty + s + 0.2) return false;
    return true;
  }
  place(type, p, tx, ty) {   // a foundation; resources are paid now (AoE2 charges when the foundation is placed)
    const D = DATA.BUILDINGS[type];
    if (p < 2 && (D.age || 1) > this.players[p].age) return null;
    if (D.needs && !this.has(p, D.needs)) return null;
    if (!this.canPlace(type, p, tx, ty) || !this.canAfford(p, D.cost)) return null;
    this.pay(p, D.cost);
    const b = this.addBuilding(type, p, tx, ty, false);
    for (const e of this.ents) if (!e.dead && e.kind === 'unit' && e.owner === p && !e.garrisoned &&
      e.x > tx && e.x < tx + D.size && e.y > ty && e.y < ty + D.size) { const sp = this.spawnPoint(b, [e.x, e.y]); e.x = sp[0]; e.y = sp[1]; e.path = null; }
    return b;
  }

  /* ------------------------------------------------------------ orders */
  order(u, o, shift = false) {
    if (shift && (u.order || u.queue.length)) { u.queue.push(o); return true; }
    u.queue = []; this.setOrder(u, o); return true;
  }
  setOrder(u, o) {
    u.order = o; u.path = null; u.stuck = 0; u.repathT = 0;
  }
  nextOrder(u) { u.order = null; u.path = null; if (u.queue.length) this.setOrder(u, u.queue.shift()); }

  /* AoE2 formations. Slots are laid out facing the direction of travel: melee infantry in the front ranks, then
     cavalry, then ranged, then peasants ("the strongest up front"). Local x runs across the front, y back from it. */
  formationSlots(n, kind) {
    const out = [], sp = kind === 'staggered' ? 1.5 : 0.8;
    let cols = kind === 'box' ? Math.ceil(Math.sqrt(n)) : Math.max(1, Math.min(n, Math.ceil(Math.sqrt(n * 2.5))));
    if (kind === 'flank') cols = Math.max(2, cols + (cols % 2));
    for (let k = 0; k < n; k++) {
      const row = Math.floor(k / cols), inRow = Math.min(cols, n - row * cols), c = k % cols;
      let x = (c - (inRow - 1) / 2) * sp;
      if (kind === 'flank') x += (c < inRow / 2 ? -1 : 1) * 2.5;   // two wings with a gap between them
      out.push({ x, y: row * sp, row });
    }
    return out;
  }
  /* group move, the AoE2 way: one path for the group (found once, shared by every unit that stands near it), the
     whole group walks at the speed of its slowest member, and each unit ends in its own slot of the formation. */
  groupMove(units, x, y, shift, attackMove = false, patrol = false) {
    units = units.filter(u => !u.dead && u.kind === 'unit'); const n = units.length; if (!n) return;
    const mx = units.reduce((a, u) => a + u.x, 0) / n, my = units.reduce((a, u) => a + u.y, 0) / n;
    let shared = null;
    if (n >= 3 && !shift) {
      const lead = units.slice().sort((a, b) => Math.hypot(a.x - mx, a.y - my) - Math.hypot(b.x - mx, b.y - my))[0];
      const tx = Math.floor(x), ty = Math.floor(y), walk = this.walkFn(lead.owner);
      const r = Path.find(Math.floor(lead.x), Math.floor(lead.y), [tx, ty, tx, ty], walk, 0, 90000);
      this.pathBudget -= r.n || 0;
      shared = { from: [lead.x, lead.y], pts: Path.smooth(r.tiles, walk).slice(1).map(([a, b]) => [a + 0.5, b + 0.5]), reached: r.reached };
    }
    const dl = Math.hypot(x - mx, y - my) || 1, fx = (x - mx) / dl, fy = (y - my) / dl, rx = -fy, ry = fx;   // forward and right
    const gspeed = n > 1 ? Math.min(...units.map(u => this.S(u).speed)) : 0;
    const kind = units[0].formation || 'line', slots = this.formationSlots(n, kind);
    const ranked = units.slice().sort((a, b) => ((a.D.line === undefined ? 3 : a.D.line) - (b.D.line === undefined ? 3 : b.D.line)) || (a.id - b.id));
    for (let i = 0; i < n;) {   // fill rank by rank; inside a rank, left to right as the units already stand
      let j = i; while (j < n && slots[j].row === slots[i].row) j++;
      const rank = ranked.slice(i, j).sort((a, b) => ((a.x - mx) * rx + (a.y - my) * ry) - ((b.x - mx) * rx + (b.y - my) * ry));
      const rs = slots.slice(i, j).sort((a, b) => a.x - b.x);
      rank.forEach((u, k) => {
        const s = rs[k], px = n === 1 ? x : x + rx * s.x - fx * s.y, py = n === 1 ? y : y + ry * s.x - fy * s.y;
        const o = patrol ? { type: 'patrol', a: [u.x, u.y], b: [px, py], x: px, y: py, leg: 1 } : { type: attackMove ? 'amove' : 'move', x: px, y: py };
        if (gspeed) o.gspeed = gspeed;
        if (shared && Math.hypot(u.x - shared.from[0], u.y - shared.from[1]) < 8) o.shared = shared;
        this.order(u, o, shift);
      });
      i = j;
    }
  }

  /* the smart right-click: what does clicking on this target mean for this unit */
  smartOrder(u, target, tile, x, y, shift) {
    const vil = u.type === 'villager', p = u.owner;
    if (u.owner === 2) return true;
    if (target) {
      if (target.kind === 'artifact') { if (u.D.carries) return this.order(u, { type: 'pickup', id: target.id }, shift); return false; }
      if (target.kind === 'building' && target.owner === p) {
        if (!target.built && vil) return this.order(u, { type: 'build', id: target.id }, shift);
        if (vil && target.type === 'farm') return this.order(u, { type: 'gather', ent: target.id }, shift);
        if (u.artifact && target.type === 'town_hall') return this.order(u, { type: 'deliver', id: target.id }, shift);
        if (vil && target.hp < target.maxHp) return this.order(u, { type: 'repair', id: target.id }, shift);
        if (vil && u.carry.amt > 0 && target.D.drop && target.D.drop.includes(u.carry.res)) return this.order(u, { type: 'dropoff', id: target.id, then: null }, shift);
        if (target.D.garrison && target.built && (vil || u.D.cls.includes('infantry') || u.D.cls.includes('archer'))) return this.order(u, { type: 'garrison', id: target.id }, shift);
      }
      if (target.kind === 'unit' && vil && target.owner === 2 && target.D.food) return this.order(u, { type: 'gather', ent: target.id }, shift);
      if (target.kind === 'unit' && target.owner === p && target.type === 'sheep' && vil) return this.order(u, { type: 'gather', ent: target.id }, shift);
      if (this.isHostile(u, target) || (target.owner === 2 && target.kind === 'unit' && target.D.creep)) return this.order(u, { type: 'attack', id: target.id }, shift);
    }
    if (vil && tile >= 0 && this.map.node[tile]) return this.order(u, { type: 'gather', node: tile }, shift);
    return false;
  }

  /* ------------------------------------------------------------ movement */
  /* plan a path. Path searches share a budget of nodes per tick, so a big group order spreads over a few ticks
     instead of freezing a frame; a unit whose search is deferred waits (returns false) and asks again next tick. */
  goTo(u, rect, reach, finalPt, shared) {
    const sx = Math.max(0, Math.min(this.W - 1, Math.floor(u.x))), sy = Math.max(0, Math.min(this.H - 1, Math.floor(u.y)));
    const walk = this.walkFn(u.owner);
    if (shared && shared.pts.length) {   // join the group's path: straight to its first corner if the way is clear
      // join at the furthest corner of the group path in plain sight, or by a short search to its first corner
      let join = -1;
      for (let k = Math.min(shared.pts.length - 1, 3); k >= 0; k--) { const f = shared.pts[k]; if (Path.los(sx, sy, Math.floor(f[0]), Math.floor(f[1]), walk)) { join = k; break; } }
      let lead = [];
      if (join < 0) {   // go to where the group's path starts (a few tiles away), then follow it
        const fx = Math.floor(shared.from[0]), fy = Math.floor(shared.from[1]);
        if (Path.los(sx, sy, fx, fy, walk)) { lead = [shared.from.slice()]; join = 0; }
        else { const r = Path.find(sx, sy, [fx, fy, fx, fy], walk, 0, 2000); this.pathBudget -= r.n;
          if (r.reached) { lead = Path.smooth(r.tiles, walk).slice(1).map(([x, y]) => [x + 0.5, y + 0.5]); join = 0; } }
      }
      if (join >= 0) {
        u.path = lead.concat(shared.pts.slice(join).map(p => p.slice())); if (finalPt && shared.reached) u.path[u.path.length - 1] = finalPt;
        u.pathReached = shared.reached; u.repathT = 0.6; u.stuck = 0; u.pathFor = rect.join(','); return true;
      }
    }
    if (this.pathBudget <= 0) { u.path = null; return false; }
    const r = Path.find(sx, sy, rect, walk, reach, 90000);
    this.pathBudget -= r.n;
    const tiles = Path.smooth(r.tiles, walk);
    u.path = tiles.slice(1).map(([x, y]) => [x + 0.5, y + 0.5]);
    if (finalPt && r.reached) { if (u.path.length) u.path[u.path.length - 1] = finalPt; else u.path.push(finalPt); }
    u.pathReached = r.reached; u.repathT = 0.6; u.stuck = 0; u.pathFor = rect.join(',');
    return true;
  }
  /* approach an entity or tile until within `dist`; true when there */
  approach(u, e, dist, dt) {
    const d = typeof e === 'number' ? this.distToTile(u, e) : this.distTo(u, e);
    if (d <= dist) { u.path = null; u.moving = false; return true; }
    const rect = typeof e === 'number' ? [e % this.W, (e / this.W) | 0, e % this.W, (e / this.W) | 0] : this.rectOf(e);
    const key = rect.join(',');
    if (!u.path || (u.path.length === 0) || (u.pathFor !== key && u.repathT <= 0)) {
      if (u.repathT > 0 && u.path && u.path.length === 0) { u.moving = false; return false; }
      const bld = typeof e !== 'number' && e.kind === 'building';
      if (!this.goTo(u, rect, typeof e === 'number' ? 1 : bld ? (e.D.walk ? 0 : 1) : 0, typeof e === 'number' || bld ? null : [e.x, e.y])) { u.moving = false; return false; }
      if (!bld && typeof e !== 'number' && u.path.length) u.path[u.path.length - 1] = [e.x, e.y];
      if (!u.path.length && !bld && typeof e !== 'number') u.path.push([e.x, e.y]);
      if (!u.path.length) {   // already in the goal area but not close enough: step straight toward the nearest edge
        const [x0, y0, x1, y1] = rect, nx = Math.max(x0, Math.min(x1 + 1, u.x)), ny = Math.max(y0, Math.min(y1 + 1, u.y));
        const dx = u.x - nx, dy = u.y - ny, d = Math.hypot(dx, dy) || 1, back = Math.min(dist * 0.6, 0.45);
        u.path.push([nx + dx / d * back, ny + dy / d * back]);
      }
    }
    this.follow(u, dt);
    return false;
  }
  follow(u, dt) {
    u.moving = false;
    if (!u.path || !u.path.length) return true;
    const [tx, ty] = u.path[0], dx = tx - u.x, dy = ty - u.y, d = Math.hypot(dx, dy);
    const gs = u.order && u.order.gspeed, S = this.S(u);
    const sp = (gs ? Math.min(gs, S.speed) : S.speed) * (u.artifact ? 0.8 : 1) * dt;
    if (d <= sp) { u.x = tx; u.y = ty; u.path.shift(); u.moving = true; return !u.path.length; }
    if (u.path.length > 1 && d < 0.7) { u.path.shift(); return this.follow(u, dt); }   // a corner on the way: close is enough (a crowd can't all stand on it)
    let nx = u.x + dx / d * sp, ny = u.y + dy / d * sp;
    const ok = (x, y) => { const i = Math.floor(y) * this.W + Math.floor(x); return x > 0 && y > 0 && x < this.W && y < this.H && (this.walkable(i, u.owner) || i === Math.floor(u.y) * this.W + Math.floor(u.x)); };
    if (!ok(nx, ny)) { if (ok(nx, u.y)) ny = u.y; else if (ok(u.x, ny)) nx = u.x; else { nx = u.x; ny = u.y; } }
    if (Math.abs(nx - u.x) + Math.abs(ny - u.y) < sp * 0.2) { if (++u.stuck > 30) { u.path = null; u.stuck = 0; } }
    u.facing = Math.atan2(dy, dx); u.x = nx; u.y = ny; u.moving = true; u.walkT += dt;
    return false;
  }

  /* ------------------------------------------------------------ the tick */
  step(dt) {
    if (this.state !== 'playing') return;
    this.time += dt; this.tick++; this.pathBudget = 40000;
    if (this.pending.length) { const cmds = this.pending; this.pending = []; for (const c of cmds) this.run(c); }
    for (const e of this.ents) if (e.kind === 'unit') { e.px = e.x; e.py = e.y; }   // for smooth drawing between ticks
    for (const e of this.ents) {
      if (e.dead) continue;
      if (e.kind === 'unit' && !e.garrisoned && !e.carriedBy) this.unitTick(e, dt);
      else if (e.kind === 'building') this.buildingTick(e, dt);
    }
    this.separate();
    if (this.shots.length) {
      for (const sh of this.shots) { sh.t += dt; if (sh.t >= sh.life) { const t = sh.hit ? this.get(sh.target) : null; if (t && !t.garrisoned) this.hit(sh.src, t, sh.A); } }
      this.shots = this.shots.filter(sh => sh.t < sh.life);
    }
    for (const f of this.fx) f.t += dt;
    this.fx = this.fx.filter(f => f.t < f.life);
    this.slowTimer -= dt;
    if (this.slowTimer <= 0) { this.slowTimer = 0.5; this.slowTick(); }
    this.visTimer -= dt;
    if (this.visTimer <= 0) { this.visTimer = 0.2; this.updateVision(); }
    for (const p of [0, 1]) for (const k of DATA.RES) if (this.players[p].res[k] < 0) this.players[p].res[k] = 0;
  }

  slowTick() {
    if (this.ents.some(e => e.dead)) this.ents = this.ents.filter(e => !e.dead);
    // herdables change hands like AoE2: the nearest player's unit claims them
    for (const s of this.ents) if (!s.dead && s.kind === 'unit' && s.type === 'sheep' && !s.carcass) {
      let own = false, other = -1;
      for (const u of this.ents) if (!u.dead && u.kind === 'unit' && u.owner < 2 && !u.garrisoned && u.type !== 'sheep' && Math.hypot(u.x - s.x, u.y - s.y) < 2.5) {
        if (u.owner === s.owner) own = true; else other = u.owner;
      }
      if (other >= 0 && !own) { s.owner = other; s.order = null; s.path = null; }
    }
    // artifacts in town halls trickle crystal (AoE2 relics: 0.5 gold/s each)
    for (const b of this.ents) if (!b.dead && b.kind === 'building' && b.artifacts > 0 && b.owner < 2) {
      this.players[b.owner].res.crystal += b.artifacts * DATA.ARTIFACT_RATE * 0.5; this.players[b.owner].gathered.crystal += b.artifacts * DATA.ARTIFACT_RATE * 0.5;
    }
    // camps cleared?
    for (const c of this.camps) if (!c.cleared && c.members.every(id => !this.get(id))) {
      c.cleared = true;
      for (let k = 0; k < c.artifacts; k++) this.addArtifact(c.x + (k - (c.artifacts - 1) / 2) * 0.8, c.y);
      if (this.players[0].explored[Math.floor(c.y) * this.W + Math.floor(c.x)])
        this.message(`${DATA.CAMPS[c.type].name} cleared: its ${DATA.CAMPS[c.type].deposit[0]} is free to mine` + (c.artifacts ? `, ${c.artifacts > 1 ? c.artifacts + ' artifacts' : 'an artifact'} dropped.` : '.'), c.x, c.y);
    }
    // victory / defeat
    for (const p of [0, 1]) {
      const alive = this.ents.some(e => !e.dead && e.owner === p && (e.kind === 'building' || (e.kind === 'unit' && DATA.UNITS[e.type])));
      if (!alive && !this.players[p].defeated) { this.players[p].defeated = true; this.state = p === 0 ? 'defeat' : 'victory'; }
    }
  }
  message(text, x, y) { this.messages.push({ text, t: this.time, x, y }); }
  alert(e, text) {
    const last = this.alerts[this.alerts.length - 1];
    if (last && this.time - last.t < 12 && Math.hypot(last.x - e.x, last.y - e.y) < 15) return;
    this.alerts.push({ t: this.time, x: e.x, y: e.y, text });
  }

  /* soft push between units so crowds spread out */
  separate() {
    const cell = new Map(), key = (x, y) => (x << 16) | y;
    const us = this.ents.filter(e => !e.dead && e.kind === 'unit' && !e.garrisoned && !e.carcass);
    for (const u of us) { const k = key(u.x | 0, u.y | 0); let a = cell.get(k); if (!a) cell.set(k, a = []); a.push(u); }
    for (const u of us) {
      const cx = u.x | 0, cy = u.y | 0;
      for (let y = cy - 1; y <= cy + 1; y++) for (let x = cx - 1; x <= cx + 1; x++) {
        const a = cell.get(key(x, y)); if (!a) continue;
        for (const v of a) {
          if (v === u || v.id < u.id) continue;
          const dx = u.x - v.x, dy = u.y - v.y, d = Math.hypot(dx, dy), m = (u.r + v.r) * 0.85;
          if (d >= m || d < 1e-4) continue;
          const push = (m - d) * 0.25, px = dx / d * push, py = dy / d * push;
          this.nudge(u, px, py); this.nudge(v, -px, -py);
        }
      }
    }
  }
  nudge(u, dx, dy) {
    const x = u.x + dx, y = u.y + dy, i = Math.floor(y) * this.W + Math.floor(x);
    if (!(x > 0 && y > 0 && x < this.W && y < this.H && this.walkable(i, u.owner))) return;
    if (u.atWork) {   // working units may shuffle around their job (several peasants on one tree spread out) but stay in reach
      const w = u.workAt; if (!w) return;
      const d = w.tile !== undefined ? this.distToTile({ x, y }, w.tile) : this.distTo({ x, y }, w.ent);
      if (d > w.reach) return;
    }
    u.x = x; u.y = y;
  }

  /* ------------------------------------------------------------ units */
  unitTick(u, dt) {
    u.cool = Math.max(0, u.cool - dt); u.repathT -= dt; u.atWork = false;
    if (u.carcass) { u.decayT = (u.decayT || 0) + dt; if (u.food <= 0) this.remove(u); return; }
    if (u.owner === 2) return this.wildTick(u, dt);
    const o = u.order;
    if (!o) return this.idleTick(u, dt);
    switch (o.type) {
      case 'move': {
        if (!u.path || u.pathTarget !== o) { if (!this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y], o.shared)) { u.moving = false; break; } u.pathTarget = o; o.shared = null; }
        if (this.follow(u, dt) && !u.moving) this.nextOrder(u);
        else if (!u.path || !u.path.length) this.nextOrder(u);
        break;
      }
      case 'amove': case 'patrol': {   // walk, fighting whatever comes into sight; a patrol turns round at each end (AoE2 Patrol)
        if (!o.scan || this.time > o.scan) { o.scan = this.time + 0.4; const t = this.findEnemy(u, this.S(u).los); if (t) { u.queue.unshift(o); o.resume = true; this.setOrder(u, { type: 'attack', id: t.id, auto: true, roam: true }); break; } }
        if (!u.path || u.pathTarget !== o || o.resume) { o.resume = false; if (!this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y], o.shared)) { u.moving = false; break; } u.pathTarget = o; o.shared = null; }
        if (this.follow(u, dt) || !u.path || !u.path.length) {
          if (o.type === 'patrol' && !u.queue.length) { o.leg ^= 1; const q = o.leg ? o.b : o.a; o.x = q[0]; o.y = q[1]; o.gspeed = 0; u.path = null; u.pathTarget = null; }
          else this.nextOrder(u);
        }
        break;
      }
      case 'attack': return this.attackTick(u, o, dt);
      case 'gather': return this.gatherTick(u, o, dt);
      case 'dropoff': return this.dropoffTick(u, o, dt);
      case 'build': return this.buildTick(u, o, dt);
      case 'repair': return this.repairTick(u, o, dt);
      case 'garrison': {
        const b = this.get(o.id); if (!b || !b.built) return this.nextOrder(u);
        if (b.garrison.length >= b.D.garrison) return this.nextOrder(u);
        if (this.approach(u, b, 0.8, dt)) { u.garrisoned = b.id; b.garrison.push(u.id); u.order = null; u.path = null; }
        break;
      }
      case 'pickup': {
        const a = this.get(o.id); if (!a || a.carrier || u.artifact) return this.nextOrder(u);
        if (this.approach(u, a, 0.4, dt)) { a.carrier = u.id; u.artifact = a.id; this.nextOrder(u);
          if (!u.order) { const th = this.nearest(u, e => e.kind === 'building' && e.owner === u.owner && e.type === 'town_hall' && e.built); if (th) this.setOrder(u, { type: 'deliver', id: th.id }); } }
        break;
      }
      case 'deliver': {
        const b = this.get(o.id), a = this.get(u.artifact); if (!b || !a) return this.nextOrder(u);
        if (this.approach(u, b, 0.8, dt)) { b.artifacts++; this.remove(a); u.artifact = 0; this.nextOrder(u);
          if (u.owner === 0) this.message(`Artifact stored in the Town Hall: +${DATA.ARTIFACT_RATE} crystal/s`, b.x, b.y); }
        break;
      }
      default: this.nextOrder(u);
    }
    if (u.artifact) { const a = this.get(u.artifact); if (a) { a.x = u.x; a.y = u.y; } }
  }
  idleTick(u, dt) {
    u.moving = false;
    if (u.type === 'sheep' || u.type === 'villager' || u.stance === 'passive') return;
    if (!u.scanT || this.time > u.scanT) {   // AoE2 stances: aggressive and defensive units engage what comes into sight; stand ground only what is in reach
      u.scanT = this.time + 0.5;
      const S = this.S(u), t = this.findEnemy(u, u.stance === 'ground' ? (S.range || 0.6) : S.los, true);
      if (t) this.setOrder(u, { type: 'attack', id: t.id, auto: true, home: [u.x, u.y] });
    }
  }
  findEnemy(u, range, onlyThreats = false) {
    let best = null, bd = range;
    for (const e of this.ents) {
      if (e.dead || e.garrisoned || e.carcass || e.kind === 'artifact' || !this.isHostile(u, e)) continue;
      if (e.owner === 2 && onlyThreats && !(e.order && e.order.type === 'attack')) continue;
      if (u.owner === 0 && !this.players[0].vis[Math.floor(e.y) * this.W + Math.floor(e.x)]) continue;
      const d = this.distTo(u, e) + (e.kind === 'building' ? 2 : 0);   // AoE2 units prefer units over buildings
      if (d < bd) { bd = d; best = e; }
    }
    return best;
  }
  nearest(u, pred, max = 1e9) {
    let best = null, bd = max;
    for (const e of this.ents) if (!e.dead && pred(e)) { const d = this.distTo(u, e); if (d < bd) { bd = d; best = e; } }
    return best;
  }
  attackTick(u, o, dt) {
    const t = this.get(o.id), S = this.S(u);
    if (!t || t.garrisoned || (t.carcass)) {
      if ((o.auto || u.type !== 'villager') && u.owner !== 2 && u.stance !== 'passive') { const n = this.findEnemy(u, u.stance === 'ground' ? (S.range || 0.6) : S.los, true); if (n) { o.id = n.id; return; } }
      if (o.auto && o.home && u.owner < 2 && !u.queue.length && Math.hypot(u.x - o.home[0], u.y - o.home[1]) > 1) return this.setOrder(u, { type: 'move', x: o.home[0], y: o.home[1] });   // back to its post
      return this.nextOrder(u);
    }
    const reach = S.range > 0 ? S.range : u.r + 0.3, d = this.distTo(u, t);
    if (o.auto && u.owner < 2 && !o.roam) {   // stances limit how far a unit follows on its own
      if (u.stance === 'ground' && d > reach) return this.nextOrder(u);
      if (u.stance === 'defensive' && o.home && Math.hypot(u.x - o.home[0], u.y - o.home[1]) > 5 && !u.queue.length) return this.setOrder(u, { type: 'move', x: o.home[0], y: o.home[1] });
      if (u.stance === 'aggressive' && d > S.los + 4) return this.nextOrder(u);
    }
    if (this.approach(u, t, reach, dt)) {
      u.facing = Math.atan2(t.y - u.y, t.x - u.x);
      if (S.min && d < S.min - 0.3 && t.kind === 'unit') return;   // AoE2: slingers cannot fire at point-blank
      if (u.cool <= 0) {
        u.cool = S.reload; u.swingT = this.time;
        const A = { melee: S.melee, pierce: S.pierce, bonus: S.bonus };
        if (S.range > 0) this.shoot(u, t, A, S.acc, 0.7); else this.hit(u, t, A);
      }
    }
  }
  /* apply an attack. src may be a snapshot of the attacker (an arrow in flight outlives the archer) */
  hit(src, t, A) {
    const dmg = this.damage(A, t, src.x, src.y);
    t.hp -= dmg; t.hitT = this.time;
    if (t.owner === 0 && src.owner !== 0) this.alert(t, t.kind === 'building' ? 'A building is under attack!' : 'You are under attack!');
    // retaliation and calls for help
    if (t.kind === 'unit' && t.hp > 0) {
      const a = this.get(src.id);
      if (t.owner === 2) { if (a) this.provoke(t, a); }
      else if (a && a.kind === 'unit' && !t.order && t.type !== 'sheep' && (t.type === 'villager' || t.stance !== 'passive')) this.setOrder(t, { type: 'attack', id: a.id, auto: true, home: [t.x, t.y] });
    }
    if (t.hp <= 0) this.kill(t, src);
  }
  kill(t, src) {
    if (t.kind === 'unit' && t.D.food && !t.carcass) {   // hunted animals leave a carcass to gather from
      t.carcass = true; t.dieT = this.time; t.food = t.D.food; t.order = null; t.path = null; t.owner = 2; t.hp = 1; return;
    }
    if (t.kind === 'unit' && !t.carcass && !t.garrisoned) this.fx.push({ kind: 'corpse', key: t.type, maa: t.type === 'militia' && this.tech(t.owner, 'man_at_arms'), owner: t.owner, x: t.x, y: t.y, facing: t.facing, t: 0, life: 14 });   // a picture only: the fallen lie a while, then fade
    if (t.kind === 'building' && t.type !== 'farm' && (t.built || t.progress > 0.3)) this.fx.push({ kind: 'rubble', size: t.size, x: t.x, y: t.y, t: 0, life: 40 });   // AoE2: rubble that fades
    this.remove(t);
    if (t.kind === 'unit' && t.owner < 2) this.recount(t.owner);
  }
  provoke(t, src) {
    if (t.D.flee) { const a = Math.atan2(t.y - src.y, t.x - src.x); t.order = { type: 'move', x: t.x + Math.cos(a) * 5, y: t.y + Math.sin(a) * 5 }; t.path = null; return; }
    if (t.D.fight) { t.order = { type: 'attack', id: src.id }; return; }
    if (t.D.creep) { const c = this.campById(t.camp); for (const id of (c ? c.members : [t.id])) { const g = this.get(id); if (g && !g.returning) { g.order = { type: 'attack', id: src.id }; g.path = null; } } }
  }

  /* wildlife and creeps */
  wildTick(u, dt) {
    const o = u.order;
    if (u.D.creep) {
      const [hx, hy] = u.home, away = Math.hypot(u.x - hx, u.y - hy);
      if (u.returning) {
        if (!u.path || u.pathTarget !== 'home') { if (!this.goTo(u, [Math.floor(hx), Math.floor(hy), Math.floor(hx), Math.floor(hy)], 0, [hx, hy])) return; u.pathTarget = 'home'; }
        u.hp = Math.min(u.maxHp, u.hp + DATA.CREEP.regen * 3 * dt);
        if (this.follow(u, dt) || away < 0.3) { u.returning = false; u.path = null; u.order = null; }
        return;
      }
      if (o && o.type === 'attack') {
        if (away > DATA.CREEP.leash) { u.returning = true; u.order = null; u.path = null; return; }
        return this.attackTick(u, o, dt);
      }
      if (away > 1.5) { u.returning = true; return; }
      u.hp = Math.min(u.maxHp, u.hp + DATA.CREEP.regen * dt);
      if (!u.scanT || this.time > u.scanT) {
        u.scanT = this.time + 0.4;
        let best = null, bd = DATA.CREEP.aggro;
        for (const e of this.ents) if (!e.dead && e.owner < 2 && !e.garrisoned && e.kind === 'unit' && e.type !== 'sheep') {
          const d = Math.hypot(e.x - u.x, e.y - u.y); if (d < bd) { bd = d; best = e; } }
        if (best) this.provoke(u, best);
      }
      u.moving = false;
      return;
    }
    if (o && o.type === 'attack') { const t = this.get(o.id); if (!t || Math.hypot(t.x - u.x, t.y - u.y) > 10) { u.order = null; return; } return this.attackTick(u, o, dt); }
    if (o && o.type === 'move') {
      if (!u.path && !this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y])) return;
      if (this.follow(u, dt) || !u.path || !u.path.length) { u.order = null; u.path = null; }
      return;
    }
    u.moving = false;
  }

  /* ------------------------------------------------------------ economy */
  dropsite(u, res) {
    return this.nearest(u, e => e.kind === 'building' && e.owner === u.owner && e.built && e.D.drop && e.D.drop.includes(res));
  }
  wardedBy(i) { const w = this.map.ward[i]; if (w < 0) return null; const c = this.campById(w); return c && !c.cleared ? c : null; }
  gatherTick(u, o, dt) {
    if (u.type !== 'villager') return this.nextOrder(u);
    const node = o.node !== undefined ? o.node : -1;
    let src = null, res, rate;
    if (node >= 0) {
      const k = MapGen.NODE_KEY[this.map.node[node]];
      if (!k || this.wardedBy(node)) { if (k && u.owner === 0 && !o.warned) { o.warned = true; this.message('That vein is warded by a creep camp. Clear the camp first.'); } return this.findNext(u, o, node); }
      res = DATA.NODES[k].res; rate = DATA.NODES[k].rate; src = node; o.nodeType = this.map.node[node];
      if (k === 'tree' && this.tech(u.owner, 'double_bit_axe')) rate *= 1.2;
      if ((k === 'iron' || k === 'crystal') && this.tech(u.owner, 'ore_mining')) rate *= 1.15;
      if (k === 'stone' && this.tech(u.owner, 'stone_mining')) rate *= 1.15;
    } else {
      const e = this.get(o.ent);
      if (!e) return this.findNext(u, o, -1);
      if (e.kind === 'building') { if (e.type !== 'farm' || !e.built || (e.farmer && e.farmer !== u.id && this.get(e.farmer) && this.get(e.farmer).order && this.get(e.farmer).order.ent === e.id)) return this.nextOrder(u);
        res = 'food'; rate = DATA.FARM.rate; src = e; }
      else if (e.kind === 'unit' && !e.carcass) {   // hunt or slaughter first
        if (e.owner !== 2 && e.owner !== u.owner) return this.nextOrder(u);
        if (this.approach(u, e, u.r + 0.3, dt)) { if (u.cool <= 0) { u.cool = 1.5; this.hit(u, e, { melee: e.type === 'sheep' ? 99 : 3 }); } }
        return;
      } else { res = 'food'; rate = e.type === 'sheep' ? 0.33 : 0.41; src = e; }   // shepherd / hunter
    }
    if (u.carry.res !== res) u.carry = { res, amt: 0 };   // AoE2: switching resource drops what was carried
    u.lastGather = { node: node >= 0 ? node : undefined, ent: node < 0 ? o.ent : undefined, res };
    const cap = this.carryCap(u.owner);
    if (u.carry.amt >= cap) { const ds = this.dropsite(u, res); if (!ds) { u.moving = false; return; }
      u.queue.unshift(o); this.setOrder(u, { type: 'dropoff', id: ds.id }); return; }
    const isFarm = src && src.kind === 'building';
    const there = isFarm ? this.approach(u, src, 0.01, dt) : node >= 0 ? this.approach(u, node, 0.75, dt) : this.approach(u, src, u.r + 0.25, dt);
    if (!there) return;
    u.atWork = true; u.workAt = node >= 0 ? { tile: node, reach: 0.75 } : { ent: src, reach: isFarm ? 0.01 : u.r + 0.25 };
    u.job = isFarm ? 'farm' : res;   // for the picture only: which tool is in the hand
    if (isFarm) src.farmer = u.id;
    const tgt = node >= 0 ? [node % this.W + 0.5, ((node / this.W) | 0) + 0.5] : [src.x, src.y];
    if (!isFarm) u.facing = Math.atan2(tgt[1] - u.y, tgt[0] - u.x);
    const take = rate * dt;
    if (node >= 0) {
      const got = Math.min(take, this.map.amt[node]); this.map.amt[node] -= got; u.carry.amt += got;
      if (this.map.amt[node] <= 0.001) { this.map.node[node] = 0; this.map.amt[node] = 0; this.nodeGone && this.nodeGone(node); return this.findNext(u, o, node); }
    } else if (isFarm) {
      const got = Math.min(take, src.food); src.food -= got; u.carry.amt += got;
      if (src.food <= 0.001) {
        if (this.canAfford(u.owner, DATA.BUILDINGS.farm.cost)) { this.pay(u.owner, DATA.BUILDINGS.farm.cost); src.food = this.farmFood(u.owner); }  // auto-reseed
        else { src.farmer = 0; this.remove(src); this.nextOrder(u); if (u.owner === 0) this.message('A farm ran out (not enough wood to reseed).', src.x, src.y); }
      }
    } else {
      const got = Math.min(take, src.food); src.food -= got; u.carry.amt += got;
      if (src.food <= 0.001) { this.remove(src); return this.findNext(u, o, -1, src); }
    }
    u.carry.amt = Math.min(u.carry.amt, cap);
  }
  /* AoE2: when a resource runs out the villager moves to the nearest one of the same kind nearby */
  findNext(u, o, node, oldEnt) {
    const W = this.W;
    if (node >= 0 || o.node !== undefined) {
      const at = node >= 0 ? node : o.node, ax = at % W, ay = (at / W) | 0, want = o.nodeType || this.map.node[at] || o.lastType;
      o.lastType = want;
      let best = -1, bd = 1e9;
      if (want) for (let y = ay - 7; y <= ay + 7; y++) for (let x = ax - 7; x <= ax + 7; x++) {
        if (x < 0 || y < 0 || x >= W || y >= this.H) continue; const i = y * W + x;
        if (this.map.node[i] !== want || this.wardedBy(i)) continue;
        const d = Math.hypot(x + 0.5 - u.x, y + 0.5 - u.y); if (d < bd) { bd = d; best = i; }
      }
      if (best >= 0) { o.node = best; u.path = null; return; }
    } else {
      const ref = oldEnt || u;
      const n = this.nearest(u, e => e.kind === 'unit' && ((e.carcass) || (e.owner === u.owner && e.type === 'sheep')) && Math.hypot(e.x - ref.x, e.y - ref.y) < 8);
      if (n) { o.ent = n.id; u.path = null; return; }
    }
    if (u.carry.amt > 0) { const ds = this.dropsite(u, u.carry.res); if (ds) { this.setOrder(u, { type: 'dropoff', id: ds.id, final: true }); return; } }
    this.nextOrder(u);
  }
  dropoffTick(u, o, dt) {
    const b = this.get(o.id);
    if (!b || !u.carry.amt) return this.nextOrder(u);
    if (this.approach(u, b, 0.8, dt)) {
      const p = this.players[u.owner];
      p.res[u.carry.res] += u.carry.amt; p.gathered[u.carry.res] += u.carry.amt; u.carry.amt = 0;
      this.nextOrder(u);
      if (!u.order && !o.final && u.lastGather) this.setOrder(u, Object.assign({ type: 'gather' }, u.lastGather));
    }
  }
  buildTick(u, o, dt) {
    const b = this.get(o.id);
    if (!b || b.built) return this.afterBuild(u, b);
    if (!this.approach(u, b, 0.8, dt)) return;
    u.atWork = true; u.job = 'build'; u.workAt = { ent: b, reach: 0.8 }; u.facing = Math.atan2(b.y - u.y, b.x - u.x);
    b.builders++;
    const n = Math.max(1, b.lastBuilders || 1), rate = (n + 2) / (3 * b.D.time) / n;   // AoE2: n builders take 3T/(n+2)
    b.progress = Math.min(1, b.progress + rate * dt); b.hp = Math.min(b.maxHp, b.hp + b.maxHp * rate * dt);
    if (b.progress >= 1) { b.built = true; b.hp = Math.max(b.hp, 1); this.recount(b.owner); if (b.owner === 0) this.message(`${b.D.name} complete.`, b.x, b.y); }
  }
  afterBuild(u, b) {   // AoE2: builders of a drop site start gathering the nearest matching resource; farmers farm
    this.nextOrder(u); if (u.order || !b || b.dead) return;
    if (b.type === 'farm' && (!b.farmer || !this.get(b.farmer))) return this.setOrder(u, { type: 'gather', ent: b.id });
    const want = { lumber_camp: [MapGen.N.TREE], mining_camp: [MapGen.N.IRON, MapGen.N.STONE, MapGen.N.CRYSTAL], mill: [MapGen.N.BERRY, MapGen.N.FISH] }[b.type];
    if (!want) return;
    let best = -1, bd = 12;
    for (let y = b.ty - 8; y < b.ty + b.size + 8; y++) for (let x = b.tx - 8; x < b.tx + b.size + 8; x++) {
      if (x < 0 || y < 0 || x >= this.W || y >= this.H) continue; const i = y * this.W + x;
      if (!want.includes(this.map.node[i]) || this.wardedBy(i)) continue;
      const d = Math.hypot(x + 0.5 - u.x, y + 0.5 - u.y); if (d < bd) { bd = d; best = i; }
    }
    if (best >= 0) this.setOrder(u, { type: 'gather', node: best });
  }
  repairTick(u, o, dt) {
    const b = this.get(o.id);
    if (!b || b.hp >= b.maxHp) return this.nextOrder(u);
    if (!b.built) return this.setOrder(u, { type: 'build', id: b.id });
    if (!this.approach(u, b, 0.8, dt)) return;
    u.atWork = true; u.job = 'build'; u.workAt = { ent: b, reach: 0.8 };
    // AoE2: 750 HP a minute, costs half the building's price spread over its HP
    const hp = Math.min(b.maxHp - b.hp, 12.5 * dt), cost = {};
    for (const k in b.D.cost) cost[k] = b.D.cost[k] * 0.5 * hp / b.maxHp;
    if (!this.canAfford(u.owner, cost)) return this.nextOrder(u);
    this.pay(u.owner, cost); b.hp += hp;
  }

  /* ------------------------------------------------------------ buildings */
  buildingTick(b, dt) {
    b.lastBuilders = b.builders; b.builders = 0;
    if (!b.built) return;
    // production
    const q = b.queue[0];
    if (q) {
      if (q.kind === 'tech') { q.t += dt; if (q.t >= q.time) { b.queue.shift(); this.applyTech(b.owner, q.what); } }
      else {
        const p = this.players[b.owner];
        if (p.pop >= p.popCap) { q.housed = true; }
        else { q.housed = false; q.t += dt;
          if (q.t >= q.time) { b.queue.shift(); this.trainDone(b, q.what); } }
      }
    }
    // arrows. AoE2: a Town Center shoots only with units inside; a tower shoots one arrow and more with a garrison
    if (b.D.arrows) {
      b.cool -= dt;
      if (b.cool <= 0) {
        const A = b.D.arrows, fl = this.tech(b.owner, 'fletching');
        const n = (A.base || 0) + b.garrison.filter(id => { const g = this.get(id); return g && (g.type === 'villager' || g.D.range); }).length;
        const range = A.range + (fl && A.base ? 1 : 0); let t = null, bd = range;
        if (n > 0) for (const e of this.ents) {
          if (e.dead || e.kind !== 'unit' || e.garrisoned || e.carcass || !this.isHostile(b, e)) continue;
          const d = this.distTo(e, b); if (d < bd && d >= (A.min || 0)) { bd = d; t = e; }
        }
        if (t) { b.cool = A.reload; for (let k = 0; k < n; k++) this.shoot(b, t, { pierce: A.atk + (fl ? 1 : 0) }, 1, 2.5); }
        else b.cool = 0.3;
      }
    }
    // garrisoned units heal
    for (const id of b.garrison) { const g = this.get(id); if (g) g.hp = Math.min(g.maxHp, g.hp + dt * 0.5); }
  }
  queueTrain(b, what, n = 1) {
    const U = DATA.UNITS[what], P = this.players[b.owner]; let k = 0;
    if ((U.age || 1) > P.age) return 0;
    for (; k < n; k++) {
      const cost = this.unitCost(b.owner, what);
      if (b.queue.length >= 15 || !this.canAfford(b.owner, cost)) break;   // AoE2 DE queue holds 15
      this.pay(b.owner, cost); b.queue.push({ kind: 'unit', what, t: 0, time: U.time, cost });
    }
    return k;
  }
  /* why a technology cannot be researched now, or '' */
  techBlock(p, what) {
    const T = DATA.TECHS[what], P = this.players[p];
    if (T.locked) return 'Not in this build.';
    if (P.techs.has(what) || (T.isAge && P.age >= T.isAge)) return 'Already researched.';
    if ((T.age || 1) > P.age) return `Needs the ${DATA.AGE_NAMES[T.age]}.`;
    if (this.ents.some(e => !e.dead && e.kind === 'building' && e.owner === p && e.queue.some(q => q.what === what))) return 'Already being researched.';
    if (T.isAge === 2 && DATA.FEUDAL_NEEDS.filter(t => this.has(p, t)).length < 2) return 'Needs two of: Barracks, Mill, Lumber Camp, Mining Camp.';
    return '';
  }
  queueTech(b, what) {
    const T = DATA.TECHS[what];
    if (this.techBlock(b.owner, what) || !this.canAfford(b.owner, T.cost)) return false;
    this.pay(b.owner, T.cost); b.queue.push({ kind: 'tech', what, t: 0, time: T.time, cost: T.cost }); return true;
  }
  cancel(b, i) {
    const q = b.queue[i]; if (!q) return;
    b.queue.splice(i, 1); this.pay(b.owner, q.cost, -1);
  }
  /* AoE2 Market: buy or sell 100 of a commodity for iron; the price moves 3 with every trade */
  trade(p, res, buy) {
    const M = DATA.MARKET, P = this.players[p], price = this.market[res];
    if (price === undefined || !this.ents.some(e => !e.dead && e.owner === p && e.D.market && e.built)) return 'Needs a Market.';
    if (buy) { const cost = Math.round(price * (1 + M.fee)); if (P.res[M.coin] < cost) return 'Not enough iron.';
      P.res[M.coin] -= cost; P.res[res] += M.lot; this.market[res] = Math.min(M.max, price + M.step); }
    else { if (P.res[res] < M.lot) return `Not enough ${res}.`;
      P.res[res] -= M.lot; P.res[M.coin] += Math.round(price * (1 - M.fee)); this.market[res] = Math.max(M.min, price - M.step); }
    return '';
  }
  trainDone(b, what) {
    const sp = this.spawnPoint(b, b.rally ? [b.rally.x, b.rally.y] : null);
    const u = this.addUnit(what, b.owner, sp[0], sp[1]); this.recount(b.owner);
    const r = b.rally;
    if (r) {
      const t = r.id ? this.get(r.id) : null;
      if (what === 'villager' && r.node !== undefined && this.map.node[r.node]) this.setOrder(u, { type: 'gather', node: r.node });
      else if (what === 'villager' && t && (t.type === 'farm' || t.kind === 'unit')) this.setOrder(u, { type: 'gather', ent: t.id });
      else if (what === 'villager' && t && t.kind === 'building' && !t.built) this.setOrder(u, { type: 'build', id: t.id });
      else this.setOrder(u, { type: 'move', x: r.x, y: r.y });
    }
    return u;
  }
  applyTech(p, what) {
    const P = this.players[p], T = DATA.TECHS[what]; P.techs.add(what); P.rev++;
    if (T.isAge) P.age = T.isAge;
    for (const e of this.ents) if (!e.dead && e.owner === p) {
      if (e.kind === 'unit') { const hp = this.hpOf(e); if (hp !== e.maxHp) { e.hp += hp - e.maxHp; e.maxHp = hp; } }   // Loom, Bloodlines, Man-at-Arms
      if (what === 'horse_collar' && e.type === 'farm') e.food += 75;
    }
    if (p === 0) this.message(T.isAge ? `You have advanced to the ${DATA.AGE_NAMES[T.isAge]}.` : `${T.name} researched.`);
  }
  losOf(e) { let l = e.kind === 'unit' ? this.S(e).los : (e.D.los || 4); if (e.kind === 'building' && e.built && e.owner < 2 && this.players[e.owner].techs.has('town_watch')) l += 4; return l; }
  ungarrison(b) {
    for (const id of b.garrison) { const u = this.byId.get(id); if (!u || u.dead) continue; u.garrisoned = 0;
      const sp = this.spawnPoint(b, b.rally ? [b.rally.x, b.rally.y] : null); u.x = sp[0] + (this.rand() - 0.5) * 0.5; u.y = sp[1] + (this.rand() - 0.5) * 0.5;
      if (u.belled) { u.belled = false; if (u.belledOrder) this.setOrder(u, u.belledOrder); u.belledOrder = null; } }
    b.garrison = [];
  }
  /* AoE2 Town Bell: every villager runs to the nearest Town Hall and hides; All Clear sends them back to work */
  townBell(p) {
    const halls = this.ents.filter(e => !e.dead && e.owner === p && e.type === 'town_hall' && e.built);
    if (!halls.length) return;
    for (const u of this.ents) if (!u.dead && u.owner === p && u.type === 'villager' && !u.garrisoned) {
      const th = halls.slice().sort((a, b) => this.distTo(u, a) - this.distTo(u, b)).find(h => h.garrison.length + (h.incoming || 0) < h.D.garrison);
      if (!th) continue; th.incoming = (th.incoming || 0) + 1;
      u.belledOrder = u.order && u.order.type !== 'garrison' ? Object.assign({}, u.order) : (u.lastGather ? Object.assign({ type: 'gather' }, u.lastGather) : null);
      u.belled = true; u.queue = []; this.setOrder(u, { type: 'garrison', id: th.id });
    }
    for (const h of halls) h.incoming = 0;
  }
  allClear(p) { for (const b of this.ents) if (!b.dead && b.owner === p && b.kind === 'building' && b.garrison.length) this.ungarrison(b); }

  /* ------------------------------------------------------------ vision (AoE2: black = unexplored, fog = explored) */
  updateVision(all) {
    const W = this.W, H = this.H;
    for (const p of [0]) {
      const P = this.players[p], vis = P.vis; vis.fill(0);
      for (const e of this.ents) {
        if (e.dead || e.owner !== p || e.garrisoned) continue;
        const r = this.losOf(e) + (e.kind === 'building' ? e.size / 2 : 0), cx = e.x, cy = e.y, r2 = r * r;
        for (let y = Math.max(0, Math.floor(cy - r)); y <= Math.min(H - 1, Math.ceil(cy + r)); y++)
          for (let x = Math.max(0, Math.floor(cx - r)); x <= Math.min(W - 1, Math.ceil(cx + r)); x++) {
            const dx = x + 0.5 - cx, dy = y + 0.5 - cy; if (dx * dx + dy * dy <= r2) { vis[y * W + x] = 1; P.explored[y * W + x] = 1; }
          }
      }
      // fog memory: other players' buildings are shown as they were last seen, and stay until the spot is seen again
      for (const e of this.ents) if (!e.dead && e.kind === 'building' && e.owner !== p && this.seesRect(P, e))
        P.seen.set(e.id, { id: e.id, type: e.type, owner: e.owner, tx: e.tx, ty: e.ty, size: e.size, built: e.built, progress: e.progress, food: e.food, x: e.x, y: e.y, D: e.D, kind: 'building' });
      for (const [id, m] of P.seen) { const e = this.byId.get(id); if ((!e || e.dead) && this.seesRect(P, m)) P.seen.delete(id); }
    }
  }
  seesRect(P, b) { for (let y = b.ty; y < b.ty + b.size; y++) for (let x = b.tx; x < b.tx + b.size; x++) if (P.vis[y * this.W + x]) return true; return false; }

  /* ------------------------------------------------------------ commands
     Every player action enters here as plain data and runs at the start of the next tick, the way an RTS keeps
     games in lockstep: the UI, a future AI and a replay all speak this one language. this.log records them. */
  issue(p, cmd) { const c = Object.assign({ p }, cmd); this.pending.push(c); this.log.push(Object.assign({ tick: this.tick + 1 }, c)); }
  mine(p, ids) { return (ids || []).map(id => this.get(id)).filter(e => e && e.owner === p); }
  run(c) {
    const p = c.p, say = t => { if (p === 0) this.message(t); };
    switch (c.c) {
      case 'order': {   // the smart order (AoE2's right-click)
        const units = this.mine(p, c.ids).filter(u => u.kind === 'unit' && !u.garrisoned), t = c.target ? this.get(c.target) : null;
        const movers = units.filter(u => !this.smartOrder(u, t, c.node === undefined ? -1 : c.node, c.x, c.y, c.shift));
        if (movers.length) this.groupMove(movers, c.x, c.y, c.shift, !!c.attack);
        break; }
      case 'move': this.groupMove(this.mine(p, c.ids).filter(u => u.kind === 'unit' && !u.garrisoned), c.x, c.y, c.shift, !!c.attack); break;
      case 'patrol': this.groupMove(this.mine(p, c.ids).filter(u => u.kind === 'unit' && !u.garrisoned && u.type !== 'villager'), c.x, c.y, false, true, true); break;
      case 'stance': if (DATA.STANCES.includes(c.stance)) for (const u of this.mine(p, c.ids)) if (u.kind === 'unit') { u.stance = c.stance; if (c.stance === 'passive' && u.order && u.order.type === 'attack' && u.order.auto) this.setOrder(u, null); } break;
      case 'formation': if (DATA.FORMATIONS.includes(c.formation)) for (const u of this.mine(p, c.ids)) if (u.kind === 'unit') u.formation = c.formation; break;
      case 'buy': case 'sell': { const why = this.trade(p, c.res, c.c === 'buy'); if (why) say(why); break; }
      case 'stop': for (const u of this.mine(p, c.ids)) if (u.kind === 'unit') { u.queue = []; this.setOrder(u, null); } break;
      case 'train': { let n = 0; for (const b of this.mine(p, c.ids)) if (b.built && (b.D.trains || []).includes(c.unit)) n += this.queueTrain(b, c.unit, c.n || 1);
        if (!n) say(this.players[p].pop >= this.players[p].popCap ? 'Need more housing.' : 'Not enough resources.'); break; }
      case 'research': { const b = this.mine(p, [c.id])[0]; if (!b || !b.built || !(b.D.researches || []).includes(c.tech)) break;
        if (!this.queueTech(b, c.tech)) say(this.techBlock(p, c.tech) || 'Not enough resources.'); break; }
      case 'cancel': { const b = this.mine(p, [c.id])[0]; if (b) this.cancel(b, c.i); break; }
      case 'place': {   // one building, or a line of palisade tiles; the named peasants go and build
        const D = DATA.BUILDINGS[c.type], builders = this.mine(p, c.ids).filter(u => u.type === 'villager'), placed = [];
        if ((D.age || 1) > this.players[p].age) { say(`Needs the ${DATA.AGE_NAMES[D.age]}.`); break; }
        if (D.needs && !this.has(p, D.needs)) { say(`Needs a ${DATA.BUILDINGS[D.needs].name} first.`); break; }
        for (const [tx, ty] of c.tiles) { const b = this.place(c.type, p, tx, ty); if (b) placed.push(b); else if (!this.canAfford(p, D.cost)) break; }
        if (!placed.length) { say(this.canAfford(p, D.cost) ? 'Cannot build there.' : 'Not enough resources.'); break; }
        placed.forEach((b, k) => { for (const u of builders) this.order(u, { type: 'build', id: b.id }, c.shift || k > 0); });
        break; }
      case 'rally': for (const b of this.mine(p, c.ids)) if (b.kind === 'building' && b.D.trains) b.rally = { x: c.x, y: c.y, id: c.target || 0, node: c.node >= 0 ? c.node : undefined }; break;
      case 'bell': this.townBell(p); say('Town Bell rung!'); break;
      case 'allclear': this.allClear(p); break;
      case 'ungarrison': for (const b of this.mine(p, c.ids)) if (b.kind === 'building') this.ungarrison(b); break;
      case 'garrison': for (const u of this.mine(p, c.ids)) { if (u.kind !== 'unit' || !(u.type === 'villager' || (u.D.cls && (u.D.cls.includes('infantry') || u.D.cls.includes('archer'))))) continue;
        const th = this.nearest(u, b => b.kind === 'building' && b.owner === p && b.D.garrison && b.built && b.garrison.length < b.D.garrison); if (th) this.order(u, { type: 'garrison', id: th.id }); } break;
      case 'pickup': for (const u of this.mine(p, c.ids)) { if (!u.D.carries) continue;
        const a = this.nearest(u, a => a.kind === 'artifact' && !a.carrier && (p !== 0 || this.players[0].vis[Math.floor(a.y) * this.W + Math.floor(a.x)])); if (a) this.order(u, { type: 'pickup', id: a.id }); } break;
      case 'delete': for (const e of this.mine(p, c.ids)) { if (e.kind === 'building' && !e.built && e.progress === 0) this.pay(p, e.D.cost, -1); this.kill(e); } break;
    }
  }
  /* a fingerprint of the game state, for determinism checks and, later, desync detection */
  hash() {
    let h = 2166136261; const mix = v => { h ^= Math.round(v * 1000) | 0; h = Math.imul(h, 16777619); };
    for (const e of this.ents) if (!e.dead) { mix(e.id); mix(e.x); mix(e.y); mix(e.hp); }
    for (const p of this.players) for (const k of DATA.RES) mix(p.res[k] || 0);
    return (h >>> 0).toString(16);
  }
}
if (typeof module !== 'undefined') module.exports = World;
