/* world.js: the simulation. No drawing and no DOM here, so it also runs in Node for tests.
   Players: 0 = you, 1 = the opponent (an idle placeholder in this build), 2 = nature (wildlife and creep camps). */
'use strict';
if (typeof module !== 'undefined') { global.DATA = require('./data.js'); global.MapGen = require('./map.js'); global.Path = require('./path.js'); }

class World {
  constructor(seed = 7) {
    const m = this.map = MapGen.generate(seed);
    this.W = m.W; this.H = m.H; this.time = 0; this.nextId = 1;
    this.ents = []; this.byId = new Map(); this.fx = []; this.alerts = []; this.messages = [];
    this.occ = new Int32Array(this.W * this.H);
    Path.init(this.W, this.H);
    this.players = [0, 1, 2].map(id => ({ id, color: DATA.PLAYER_COLORS[id], res: Object.assign({}, DATA.START_RES),
      techs: new Set(), popCap: 0, pop: 0, gathered: { food: 0, wood: 0, stone: 0, iron: 0, crystal: 0 },
      vis: new Uint8Array(this.W * this.H), explored: new Uint8Array(this.W * this.H), defeated: false }));
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
      path: null, cool: 0, carry: { res: null, amt: 0 }, facing: Math.random() * 6.28, moving: false, walkT: 0, stuck: 0, repathT: 0 });
    if (owner < 2 && this.players[owner].techs.has('loom') && type === 'villager') { u.maxHp += 15; u.hp += 15; }
    return u;
  }
  addBuilding(type, owner, tx, ty, complete = false) {
    const D = DATA.BUILDINGS[type], s = D.size;
    const b = this.add({ kind: 'building', type, owner, D, tx, ty, size: s, x: tx + s / 2, y: ty + s / 2, r: s * 0.5,
      hp: complete ? D.hp : 1, maxHp: D.hp, progress: complete ? 1 : 0, built: complete, queue: [], rally: null,
      garrison: [], artifacts: 0, food: D.walk ? DATA.FARM.food : 0, farmer: 0, cool: 0, builders: 0 });
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
    if (o && o.type !== 'gather' && o.type !== 'dropoff' && u.type === 'villager' && u.gatherMemo && o.type !== 'build') { /* keep memo */ }
  }
  nextOrder(u) { u.order = null; u.path = null; if (u.queue.length) this.setOrder(u, u.queue.shift()); }

  /* group move: spread units into a block around the point so they don't fight over one tile */
  groupMove(units, x, y, shift, attackMove = false) {
    const n = units.length, cols = Math.ceil(Math.sqrt(n)), sp = 0.75;
    const sorted = units.slice().sort((a, b) => Math.hypot(a.x - x, a.y - y) - Math.hypot(b.x - x, b.y - y));
    sorted.forEach((u, k) => {
      const ox = n === 1 ? 0 : ((k % cols) - (cols - 1) / 2) * sp, oy = n === 1 ? 0 : (Math.floor(k / cols) - (Math.ceil(n / cols) - 1) / 2) * sp;
      this.order(u, { type: attackMove ? 'amove' : 'move', x: x + ox, y: y + oy }, shift);
    });
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
        if (target.D.garrison && (vil || u.D.cls.includes('infantry'))) return this.order(u, { type: 'garrison', id: target.id }, shift);
      }
      if (target.kind === 'unit' && vil && target.owner === 2 && target.D.food) return this.order(u, { type: 'gather', ent: target.id }, shift);
      if (target.kind === 'unit' && target.owner === p && target.type === 'sheep' && vil) return this.order(u, { type: 'gather', ent: target.id }, shift);
      if (this.isHostile(u, target) || (target.owner === 2 && target.kind === 'unit' && target.D.creep)) return this.order(u, { type: 'attack', id: target.id }, shift);
    }
    if (vil && tile >= 0 && this.map.node[tile]) return this.order(u, { type: 'gather', node: tile }, shift);
    return false;
  }

  /* ------------------------------------------------------------ movement */
  goTo(u, rect, reach, finalPt) {
    const sx = Math.max(0, Math.min(this.W - 1, Math.floor(u.x))), sy = Math.max(0, Math.min(this.H - 1, Math.floor(u.y)));
    const walk = this.walkFn(u.owner), r = Path.find(sx, sy, rect, walk, reach);
    const tiles = Path.smooth(r.tiles, walk);
    u.path = tiles.slice(1).map(([x, y]) => [x + 0.5, y + 0.5]);
    if (finalPt && r.reached) { if (u.path.length) u.path[u.path.length - 1] = finalPt; else u.path.push(finalPt); }
    u.pathReached = r.reached; u.repathT = 0.6; u.stuck = 0; u.pathFor = rect.join(',');
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
      this.goTo(u, rect, typeof e === 'number' ? 1 : bld ? (e.D.walk ? 0 : 1) : 0, typeof e === 'number' || bld ? null : [e.x, e.y]);
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
    const sp = u.D.speed * (u.artifact ? 0.8 : 1) * dt;
    if (d <= sp) { u.x = tx; u.y = ty; u.path.shift(); u.moving = true; return !u.path.length; }
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
    this.time += dt;
    for (const e of this.ents) {
      if (e.dead) continue;
      if (e.kind === 'unit' && !e.garrisoned && !e.carriedBy) this.unitTick(e, dt);
      else if (e.kind === 'building') this.buildingTick(e, dt);
    }
    this.separate();
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
      if (u.order && (u.order.type === 'gather' && u.atWork)) continue;
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
    if (u.atWork) return;
    const x = u.x + dx, y = u.y + dy, i = Math.floor(y) * this.W + Math.floor(x);
    if (x > 0 && y > 0 && x < this.W && y < this.H && this.walkable(i, u.owner)) { u.x = x; u.y = y; }
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
        if (!u.path || u.pathTarget !== o) { this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y]); u.pathTarget = o; }
        if (this.follow(u, dt) && !u.moving) this.nextOrder(u);
        else if (!u.path || !u.path.length) this.nextOrder(u);
        break;
      }
      case 'amove': {
        if (!o.scan || this.time > o.scan) { o.scan = this.time + 0.4; const t = this.findEnemy(u, u.D.los); if (t) { u.queue.unshift(o); this.setOrder(u, { type: 'attack', id: t.id, auto: true }); break; } }
        if (!u.path || u.pathTarget !== o) { this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y]); u.pathTarget = o; }
        if (this.follow(u, dt) || !u.path || !u.path.length) this.nextOrder(u);
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
    if (u.type === 'sheep') return;
    if (u.type !== 'villager' && (!u.scanT || this.time > u.scanT)) {   // aggressive stance: engage what comes into sight
      u.scanT = this.time + 0.5;
      const t = this.findEnemy(u, u.D.los, true);
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
    const t = this.get(o.id);
    if (!t || t.garrisoned || (t.carcass)) {
      if (o.auto || u.type !== 'villager') { const n = this.findEnemy(u, u.D.los, true); if (n && u.owner !== 2) { o.id = n.id; return; } }
      return this.nextOrder(u);
    }
    if (o.auto && o.home && u.owner < 2 && Math.hypot(u.x - o.home[0], u.y - o.home[1]) > 8 && !u.queue.length) { this.setOrder(u, { type: 'move', x: o.home[0], y: o.home[1] }); return; }
    if (this.approach(u, t, u.r + 0.3 + (u.D.range || 0), dt)) {
      u.facing = Math.atan2(t.y - u.y, t.x - u.x);
      if (u.cool <= 0) { u.cool = u.D.reload || 2; this.hit(u, t, this.attackOf(u)); u.swingT = this.time; }
    }
  }
  attackOf(u) { return u.D.atk; }
  hit(src, t, atk, pierce = false) {
    const armor = t.kind === 'unit' ? (t.D.armor || [0, 0])[pierce ? 1 : 0] + this.armorBonus(t, pierce) : (pierce ? 8 : 0);
    let dmg = Math.max(1, atk - armor);                                 // AoE2: at least 1 damage
    const dh = this.h(src.x, src.y) - this.h(t.x, t.y);
    if (dh > 0.5) dmg *= 1 + DATA.ELEV_BONUS; else if (dh < -0.5) dmg *= 1 - DATA.ELEV_BONUS;   // AoE2 elevation
    t.hp -= dmg; t.hitT = this.time;
    if (t.owner === 0 && src.owner !== 0) this.alert(t, t.kind === 'building' ? 'A building is under attack!' : 'You are under attack!');
    // retaliation and calls for help
    if (t.kind === 'unit' && t.hp > 0) {
      if (t.owner === 2) this.provoke(t, src);
      else if (!t.order && t.type !== 'villager' && t.type !== 'sheep') this.setOrder(t, { type: 'attack', id: src.id, auto: true, home: [t.x, t.y] });
      else if (!t.order && t.type === 'villager' && src.kind === 'unit') this.setOrder(t, { type: 'attack', id: src.id, auto: true, home: [t.x, t.y] });
    }
    if (t.hp <= 0) this.kill(t, src);
  }
  armorBonus(t, pierce) { return t.type === 'villager' && t.owner < 2 && this.players[t.owner].techs.has('loom') ? (pierce ? 2 : 1) : 0; }
  kill(t, src) {
    if (t.kind === 'unit' && t.D.food && !t.carcass) {   // hunted animals leave a carcass to gather from
      t.carcass = true; t.food = t.D.food; t.order = null; t.path = null; t.owner = 2; t.hp = 1; return;
    }
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
        if (!u.path || u.pathTarget !== 'home') { this.goTo(u, [Math.floor(hx), Math.floor(hy), Math.floor(hx), Math.floor(hy)], 0, [hx, hy]); u.pathTarget = 'home'; }
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
      if (!u.path) this.goTo(u, [Math.floor(o.x), Math.floor(o.y), Math.floor(o.x), Math.floor(o.y)], 0, [o.x, o.y]);
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
    } else {
      const e = this.get(o.ent);
      if (!e) return this.findNext(u, o, -1);
      if (e.kind === 'building') { if (e.type !== 'farm' || !e.built || (e.farmer && e.farmer !== u.id && this.get(e.farmer) && this.get(e.farmer).order && this.get(e.farmer).order.ent === e.id)) return this.nextOrder(u);
        res = 'food'; rate = DATA.FARM.rate; src = e; }
      else if (e.kind === 'unit' && !e.carcass) {   // hunt or slaughter first
        if (e.owner !== 2 && e.owner !== u.owner) return this.nextOrder(u);
        if (this.approach(u, e, u.r + 0.3, dt)) { if (u.cool <= 0) { u.cool = 1.5; this.hit(u, e, e.type === 'sheep' ? 99 : 3); } }
        return;
      } else { res = 'food'; rate = e.type === 'sheep' ? 0.33 : 0.41; src = e; }   // shepherd / hunter
    }
    if (u.carry.res !== res) u.carry = { res, amt: 0 };   // AoE2: switching resource drops what was carried
    u.lastGather = { node: node >= 0 ? node : undefined, ent: node < 0 ? o.ent : undefined, res };
    if (u.carry.amt >= DATA.CARRY) { const ds = this.dropsite(u, res); if (!ds) { u.moving = false; return; }
      u.queue.unshift(o); this.setOrder(u, { type: 'dropoff', id: ds.id }); return; }
    const isFarm = src && src.kind === 'building';
    const there = isFarm ? this.approach(u, src, 0.01, dt) : node >= 0 ? this.approach(u, node, 0.75, dt) : this.approach(u, src, u.r + 0.25, dt);
    if (!there) return;
    u.atWork = true;
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
        if (this.canAfford(u.owner, DATA.BUILDINGS.farm.cost)) { this.pay(u.owner, DATA.BUILDINGS.farm.cost); src.food = DATA.FARM.food; }  // auto-reseed
        else { src.farmer = 0; this.remove(src); this.nextOrder(u); if (u.owner === 0) this.message('A farm ran out (not enough wood to reseed).', src.x, src.y); }
      }
    } else {
      const got = Math.min(take, src.food); src.food -= got; u.carry.amt += got;
      if (src.food <= 0.001) { this.remove(src); return this.findNext(u, o, -1, src); }
    }
    u.carry.amt = Math.min(u.carry.amt, DATA.CARRY);
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
    u.atWork = true; u.facing = Math.atan2(b.y - u.y, b.x - u.x);
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
    u.atWork = true;
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
    // arrows (AoE2 Town Center: one arrow, plus one per garrisoned villager)
    if (b.D.arrows) {
      b.cool -= dt;
      if (b.cool <= 0) {
        const A = b.D.arrows; let t = null, bd = A.range;
        for (const e of this.ents) {
          if (e.dead || e.kind !== 'unit' || e.garrisoned || e.carcass || !this.isHostile(b, e)) continue;
          const d = this.distTo(e, b); if (d < bd) { bd = d; t = e; }
        }
        if (t) {
          b.cool = A.reload; const n = 1 + b.garrison.filter(id => { const g = this.get(id); return g && g.type === 'villager'; }).length;
          for (let k = 0; k < n; k++) { this.fx.push({ kind: 'arrow', x0: b.x, y0: b.y, z0: 2.5, x1: t.x + (Math.random() - 0.5) * 0.4, y1: t.y + (Math.random() - 0.5) * 0.4, t: -k * 0.08, life: 0.5 }); }
          for (let k = 0; k < n; k++) { if (t.hp > 0) this.hit(b, t, A.atk, true); }
        } else b.cool = 0.3;
      }
    }
    // garrisoned units heal
    for (const id of b.garrison) { const g = this.get(id); if (g) g.hp = Math.min(g.maxHp, g.hp + dt * 0.5); }
  }
  queueTrain(b, what, n = 1) {
    const U = DATA.UNITS[what]; let k = 0;
    for (; k < n; k++) {
      if (b.queue.length >= 15 || !this.canAfford(b.owner, U.cost)) break;   // AoE2 DE queue holds 15
      this.pay(b.owner, U.cost); b.queue.push({ kind: 'unit', what, t: 0, time: U.time });
    }
    return k;
  }
  queueTech(b, what) {
    const T = DATA.TECHS[what], p = this.players[b.owner];
    if (T.locked || p.techs.has(what) || this.ents.some(e => !e.dead && e.kind === 'building' && e.owner === b.owner && e.queue.some(q => q.what === what))) return false;
    if (!this.canAfford(b.owner, T.cost)) return false;
    this.pay(b.owner, T.cost); b.queue.push({ kind: 'tech', what, t: 0, time: T.time }); return true;
  }
  cancel(b, i) {
    const q = b.queue[i]; if (!q) return;
    b.queue.splice(i, 1); this.pay(b.owner, (q.kind === 'tech' ? DATA.TECHS : DATA.UNITS)[q.what].cost, -1);
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
    const P = this.players[p]; P.techs.add(what);
    if (what === 'loom') for (const e of this.ents) if (!e.dead && e.owner === p && e.type === 'villager') { e.maxHp += 15; e.hp += 15; }
    if (p === 0) this.message(`${DATA.TECHS[what].name} researched.`);
  }
  losOf(e) { let l = e.D.los || 4; if (e.kind === 'building' && e.built && e.owner < 2 && this.players[e.owner].techs.has('town_watch')) l += 4; return l; }
  ungarrison(b) {
    for (const id of b.garrison) { const u = this.byId.get(id); if (!u || u.dead) continue; u.garrisoned = 0;
      const sp = this.spawnPoint(b, b.rally ? [b.rally.x, b.rally.y] : null); u.x = sp[0] + (Math.random() - 0.5) * 0.5; u.y = sp[1] + (Math.random() - 0.5) * 0.5;
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
    }
  }
}
if (typeof module !== 'undefined') module.exports = World;
