/* map.js: the 300x300 map. Corner heights (smooth slopes like AoE2's elevation), ground types, static resources,
   wildlife, creep camps. Two players in opposite corners; everything is point-symmetric so both starts are equal. */
'use strict';
const MapGen = (() => {
  const T = { GRASS: 0, GRASS2: 1, DIRT: 2, FOREST: 3, ROCK: 4, SAND: 5, WATER: 6, FORD: 7 };
  const N = { NONE: 0, TREE: 1, BERRY: 2, STONE: 3, IRON: 4, CRYSTAL: 5, FISH: 6 };
  const NODE_KEY = [null, 'tree', 'berry', 'stone', 'iron', 'crystal', 'fish'];
  const MAXH = 6;

  function rng(seed) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function valueNoise(W, H, cell, R) {
    const gw = Math.ceil(W / cell) + 2, gh = Math.ceil(H / cell) + 2, g = new Float32Array(gw * gh);
    for (let i = 0; i < g.length; i++) g[i] = R();
    const s = t => t * t * (3 - 2 * t);
    return (x, y) => {
      const fx = x / cell, fy = y / cell, ix = Math.floor(fx), iy = Math.floor(fy), tx = s(fx - ix), ty = s(fy - iy);
      const a = g[iy * gw + ix], b = g[iy * gw + ix + 1], c = g[(iy + 1) * gw + ix], d = g[(iy + 1) * gw + ix + 1];
      return a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty;
    };
  }

  function generate(seed = 1, W = 300, H = 300) {
    const R = rng(seed);
    const m = { W, H, seed, terr: new Uint8Array(W * H), node: new Uint8Array(W * H), amt: new Float32Array(W * H),
      ward: new Int16Array(W * H).fill(-1), water: new Uint8Array(W * H), hc: new Uint8Array((W + 1) * (H + 1)), spawns: [], camps: [], starts: [] };
    const idx = (x, y) => y * W + x, inb = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
    const mir = (x, y) => [W - 1 - x, H - 1 - y];

    /* ---- heights: fBm, symmetric, flattened at the starts and camps, slopes at most one level per tile ---- */
    const n1 = valueNoise(W + 1, H + 1, 48, R), n2 = valueNoise(W + 1, H + 1, 20, R), n3 = valueNoise(W + 1, H + 1, 9, R);
    const raw = new Float32Array((W + 1) * (H + 1));
    for (let y = 0; y <= H; y++) for (let x = 0; x <= W; x++) raw[y * (W + 1) + x] = n1(x, y) * 0.6 + n2(x, y) * 0.3 + n3(x, y) * 0.1;
    const hf = new Float32Array(raw.length);
    for (let y = 0; y <= H; y++) for (let x = 0; x <= W; x++) {
      const a = raw[y * (W + 1) + x], b = raw[(H - y) * (W + 1) + (W - x)];
      hf[y * (W + 1) + x] = Math.max(0, ((a + b) / 2 - 0.35) / 0.4) * MAXH;   // lowlands stay flat, hills rise
    }
    const starts = [[34, 34], mir(34, 34).map(v => v + 1)];   // TC centre (corner coordinates); mirror of 34 is 266
    m.starts = starts;
    const flatten = (cx, cy, r, soft) => {
      const target = hf[Math.round(cy) * (W + 1) + Math.round(cx)];
      for (let y = Math.max(0, cy - r - soft); y <= Math.min(H, cy + r + soft); y++)
        for (let x = Math.max(0, cx - r - soft); x <= Math.min(W, cx + r + soft); x++) {
          const d = Math.hypot(x - cx, y - cy); if (d > r + soft) continue;
          const k = d <= r ? 1 : 1 - (d - r) / soft, i = y * (W + 1) + x;
          hf[i] = hf[i] * (1 - k) + target * k;
        }
    };
    for (const [x, y] of starts) flatten(x, y, 12, 8);
    flatten(150, 150, 9, 6);
    /* ---- the river: corner to corner between the players, along x + y = W - 1, wandering by an odd function of
       (x - y) so the map stays point-symmetric. Deep water blocks; fords (the centre, guarded by the Ogre
       Stronghold, and two pairs further out) are shallow and walkable. ---- */
    const sg = R() < 0.5 ? 1 : -1, A1 = 7 + R() * 4, A2 = 3 + R() * 2;
    const wander = t => sg * A1 * Math.sin(t / 37) + A2 * Math.sin(t / 13);   // odd in t: keeps the mirror
    const FORDS = [0, 95, -95, 190, -190], HALF = 3.2;
    m.river = { wander, half: HALF, fords: FORDS };
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const t = x - y, off = (x + y) - (W - 1) - wander(t);
      if (Math.abs(off) > HALF) continue;
      const ford = FORDS.some(f => Math.abs(t - f) < (f === 0 ? 16 : 7));
      m.water[y * W + x] = ford ? 2 : 1;
    }
    for (let y = 0; y <= H; y++) for (let x = 0; x <= W; x++) {   // the valley floor
      const t = x - y, off = Math.abs((x + y) - W - wander(t));
      if (off < HALF + 2) hf[y * (W + 1) + x] = Math.min(hf[y * (W + 1) + x], 0);
    }
    for (let i = 0; i < hf.length; i++) m.hc[i] = Math.max(0, Math.min(MAXH, Math.round(hf[i])));
    for (let pass = 0; pass < 8; pass++) {          // no cliffs: neighbours differ by at most one level
      let changed = false;
      for (let y = 0; y <= H; y++) for (let x = 0; x <= W; x++) {
        const i = y * (W + 1) + x; let lo = 255;
        if (x > 0) lo = Math.min(lo, m.hc[i - 1]); if (x < W) lo = Math.min(lo, m.hc[i + 1]);
        if (y > 0) lo = Math.min(lo, m.hc[i - W - 1]); if (y < H) lo = Math.min(lo, m.hc[i + W + 1]);
        if (m.hc[i] > lo + 1) { m.hc[i] = lo + 1; changed = true; }
      }
      if (!changed) break;
    }
    for (let y = 0; y <= H / 2; y++) for (let x = 0; x <= W; x++) {   // re-symmetrise after relaxing
      const a = y * (W + 1) + x, b = (H - y) * (W + 1) + (W - x), v = Math.min(m.hc[a], m.hc[b]); m.hc[a] = m.hc[b] = v;
    }

    /* ---- ground types ---- */
    const gn = valueNoise(W, H, 14, R), sn = valueNoise(W, H, 30, R);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const [mx, my] = mir(x, y), v = (gn(x, y) + gn(mx, my)) / 2, s = (sn(x, y) + sn(mx, my)) / 2, h = tileH(m, x, y);
      m.terr[idx(x, y)] = h >= 4.5 ? T.ROCK : s > 0.78 ? T.SAND : v > 0.55 ? T.GRASS2 : T.GRASS;
    }
    for (let i = 0; i < W * H; i++) if (m.water[i]) m.terr[i] = m.water[i] === 1 ? T.WATER : T.FORD;
    for (const [cx, cy] of starts) for (let y = cy - 9; y < cy + 9; y++) for (let x = cx - 9; x < cx + 9; x++)
      if (inb(x, y) && Math.hypot(x + 0.5 - cx, y + 0.5 - cy) < 7 + R() * 2.5) m.terr[idx(x, y)] = T.DIRT;

    /* ---- placement helpers (P1 side; every placement is mirrored) ---- */
    const reserved = new Uint8Array(W * H);   // keep clear: town halls, camp floors
    const free = (x, y) => inb(x, y) && !m.node[idx(x, y)] && !reserved[idx(x, y)] && !m.water[idx(x, y)];
    const freeBoth = (x, y) => { const [a, b] = mir(x, y); return free(x, y) && free(a, b) && !(a === x && b === y); };
    function put(x, y, type, amount, ward = -1) {
      for (const [px, py] of [[x, y], mir(x, y)]) {
        const i = idx(px, py); m.node[i] = type; m.amt[i] = amount; if (ward >= 0) m.ward[i] = ward;
        if (type === N.TREE && m.terr[i] !== T.DIRT) m.terr[i] = T.FOREST;
      }
    }
    function blob(x, y, n, ok) {     // grow a cluster of n tiles from (x, y)
      const out = [[x, y]], seen = new Set([y * W + x]);
      for (let k = 0; out.length < n && k < n * 30; k++) {
        const [bx, by] = out[Math.floor(R() * out.length)], d = [[1, 0], [-1, 0], [0, 1], [0, -1]][Math.floor(R() * 4)];
        const nx = bx + d[0], ny = by + d[1];
        if (!seen.has(ny * W + nx) && ok(nx, ny)) { seen.add(ny * W + nx); out.push([nx, ny]); }
      }
      return out;
    }
    const polar = (cx, cy, d0, d1, a0 = 0, a1 = Math.PI * 2) => {
      const a = a0 + R() * (a1 - a0), d = d0 + R() * (d1 - d0); return [Math.round(cx + Math.cos(a) * d), Math.round(cy + Math.sin(a) * d)];
    };
    const p1side = (x, y, margin = 20) => x + y < W - 1 - margin;
    function cluster(cx, cy, d0, d1, n, type, amount, ward = -1, tries = 200, a0, a1) {
      for (let t = 0; t < tries; t++) {
        const [x, y] = polar(cx, cy, d0, d1, a0, a1);
        if (!freeBoth(x, y) || !p1side(x, y)) continue;
        const tiles = blob(x, y, n, (a, b) => freeBoth(a, b) && p1side(a, b) && clearOf(a, b, 1));
        if (tiles.length < n) continue;
        for (const [a, b] of tiles) put(a, b, type, amount, ward);
        return tiles;
      }
      return null;
    }
    const clearOf = (x, y, r) => { for (let b = y - r; b <= y + r; b++) for (let a = x - r; a <= x + r; a++) {
      if (!inb(a, b)) return false; const i = idx(a, b); if (m.node[i] && m.node[i] !== N.TREE) return false; } return true; };
    const spawn = (kind, x, y, extra) => { m.spawns.push(Object.assign({ kind, x: x + 0.5, y: y + 0.5 }, extra));
      const [a, b] = mir(x, y); m.spawns.push(Object.assign({ kind, x: a + 0.5, y: b + 0.5 }, extra)); };

    const [sx, sy] = starts[0];
    for (let y = sy - 4; y < sy + 4; y++) for (let x = sx - 4; x < sx + 4; x++) { reserved[idx(x, y)] = 1; const [a, b] = mir(x, y); reserved[idx(a, b)] = 1; }

    /* ---- camps first (they need open floors) ---- */
    let campId = 0;
    function camp(type, cx, cy) {
      const C = DATA.CAMPS[type], id = campId++, sym = cx === 150 && cy === 150;
      const rec = (x, y) => { const c = { id, type, x: x + 0.5, y: y + 0.5, deposit: [] }; m.camps.push(c); return c; };
      const a = rec(cx, cy), b = sym ? null : rec(...mir(cx, cy));
      if (b) b.id = campId++;
      for (let y = cy - 3; y <= cy + 3; y++) for (let x = cx - 3; x <= cx + 3; x++) if (inb(x, y)) { reserved[idx(x, y)] = 1; const [p, q] = mir(x, y); reserved[idx(p, q)] = 1; }
      const res = C.deposit[0] === 'crystal' ? N.CRYSTAL : N.IRON, amount = DATA.NODES[C.deposit[0]].amount;
      if (sym) {   // centre: a ring of veins around the middle, symmetric by construction
        const ring = [[-5, -1], [-5, 0], [-5, 1], [-4, -2], [-4, 2]];
        for (const [dx, dy] of ring) { put(cx + dx, cy + dy, res, amount, a.id); a.deposit.push([cx + dx, cy + dy], mir(cx + dx, cy + dy)); }
      } else {
        const tiles = cluster(cx, cy, 4, 5, C.deposit[1], res, amount, a.id, 300);
        if (tiles) for (const [x, y] of tiles) { a.deposit.push([x, y]); const [p, q] = mir(x, y); b.deposit.push([p, q]); m.ward[idx(p, q)] = b.id; }
      }
      for (const c of b ? [a, b] : [a]) {
        c.guards = []; c.artifacts = C.artifacts;
        let k = 0;
        for (const kind in C.guards) for (let j = 0; j < C.guards[kind]; j++, k++) {
          const ang = k / 6 * Math.PI * 2 + 0.4, r = kind === 'ogre' ? 0.6 : 1.8;
          c.guards.push({ kind, x: c.x + Math.cos(ang) * r, y: c.y + Math.sin(ang) * r });
        }
      }
    }
    camp('ogre_hold', 150, 150);
    const campSpot = (d0, d1) => { for (let t = 0; t < 400; t++) {
      const [x, y] = polar(sx, sy, d0, d1, -0.2, Math.PI / 2 + 0.2);
      if (!inb(x - 6, y - 6) || !inb(x + 6, y + 6) || !p1side(x, y, 40)) continue;
      let ok = true; for (const c of m.camps) if (Math.hypot(c.x - x, c.y - y) < 26) ok = false;
      for (let b = y - 4; b <= y + 4 && ok; b++) for (let a = x - 4; a <= x + 4; a++) if (m.water[idx(a, b)]) { ok = false; break; }
      if (ok) return [x, y]; } return null; };
    for (const [type, d0, d1] of [['wolf_den', 38, 55], ['wolf_den', 38, 60], ['goblin_post', 60, 90], ['goblin_post', 60, 95], ['ogre_lair', 95, 135]]) {
      const p = campSpot(d0, d1); if (p) camp(type, p[0], p[1]);
    }

    /* ---- each player's home: AoE2 Arabia-like layout around the Town Hall ---- */
    const home = (d0, d1) => [sx, sy, d0, d1];
    for (let k = 0; k < 6; k++) { const [x, y] = polar(...home(5, 8)); if (freeBoth(x, y) && clearOf(x, y, 1)) put(x, y, N.TREE, 100); }  // stragglers
    cluster(...home(9, 11), 7, N.BERRY, DATA.NODES.berry.amount);
    cluster(...home(10, 12), 7, N.IRON, DATA.NODES.iron.amount);
    cluster(...home(17, 23), 4, N.IRON, DATA.NODES.iron.amount);
    cluster(...home(18, 24), 4, N.IRON, DATA.NODES.iron.amount);
    cluster(...home(12, 18), 5, N.STONE, DATA.NODES.stone.amount);
    cluster(...home(16, 21), 5, N.STONE, DATA.NODES.stone.amount);
    for (let k = 0; k < 3; k++) cluster(...home(18, 26), 90 + Math.floor(R() * 60), N.TREE, 100, -1, 300);  // home woodlines
    // open-map extras, unguarded
    for (const [n, type, d0, d1] of [[5, N.IRON, 60, 110], [5, N.IRON, 70, 130], [5, N.STONE, 60, 120], [7, N.BERRY, 40, 80]])
      cluster(sx, sy, d0, d1, n, type, DATA.NODES[NODE_KEY[type]].amount, -1, 300, -0.2, Math.PI / 2 + 0.2);

    // wildlife (AoE2: 4 sheep near the TC + 4 further, 2 boar, a herd of deer)
    const animal = (kind, d0, d1, n = 1, spread = 0) => { for (let t = 0; t < 200; t++) {
      const [x, y] = polar(sx, sy, d0, d1); if (!freeBoth(x, y) || !p1side(x, y)) continue;
      for (let j = 0; j < n; j++) spawn(kind, x + (j % 2) * spread, y + Math.floor(j / 2) * spread);
      return; } };
    for (let k = 0; k < 4; k++) animal('sheep', 5, 8);
    animal('sheep', 14, 20, 2, 1); animal('sheep', 16, 22, 2, 1);
    animal('boar', 15, 19); animal('boar', 16, 20);
    animal('deer', 20, 27, 4, 1);

    // shore fish in the river, gathered from the bank by peasants (no Dock: the user's call)
    for (let k = 0, made = 0; k < 4000 && made < 7; k++) {
      const x = Math.floor(R() * W), y = Math.floor(R() * H), i = idx(x, y), [a, b] = mir(x, y);
      if (m.water[i] !== 1 || m.node[i] || !(x + y < W - 1) || (a === x && b === y)) continue;
      const land = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => inb(x + dx, y + dy) && !m.water[idx(x + dx, y + dy)]);
      if (!land || Math.abs(x - y) > 200) continue;
      put(x, y, N.FISH, DATA.NODES.fish.amount); made++;
      for (const [dx, dy] of [[1, -1], [-1, 1]]) { const nx = x + dx, ny = y + dy; if (inb(nx, ny) && m.water[idx(nx, ny)] === 1 && !m.node[idx(nx, ny)] && nx + ny < W - 1) put(nx, ny, N.FISH, DATA.NODES.fish.amount); }
    }
    // forests across the map, mirrored
    for (let k = 0; k < 70; k++) {
      const x = Math.floor(R() * W), y = Math.floor(R() * H);
      if (!p1side(x, y, 4)) continue;
      let near = false; for (const [a, b] of starts) if (Math.hypot(x - a, y - b) < 16) near = true;
      for (const c of m.camps) if (Math.hypot(x - c.x, y - c.y) < 9) near = true;
      if (near) continue;
      const tiles = blob(x, y, 40 + Math.floor(R() * 200), (a, b) => freeBoth(a, b) && p1side(a, b, 2) &&
        starts.every(([p, q]) => Math.hypot(a - p, b - q) > 14) && m.camps.every(c => Math.hypot(a - c.x, b - c.y) > 7));
      for (const [a, b] of tiles) put(a, b, N.TREE, 100);
    }
    // the map's edge is dense forest, as on AoE2 land maps
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if ((x < 2 || y < 2 || x >= W - 2 || y >= H - 2) && free(x, y)) {
      m.node[idx(x, y)] = N.TREE; m.amt[idx(x, y)] = 100; m.terr[idx(x, y)] = T.FOREST; }
    return m;
  }

  function tileH(m, x, y) {     // height (in levels) at a continuous point, bilinear over corners
    const W = m.W, cx = Math.max(0, Math.min(m.W - 0.001, x)), cy = Math.max(0, Math.min(m.H - 0.001, y));
    const ix = Math.floor(cx), iy = Math.floor(cy), fx = cx - ix, fy = cy - iy, r = W + 1;
    const a = m.hc[iy * r + ix], b = m.hc[iy * r + ix + 1], c = m.hc[(iy + 1) * r + ix], d = m.hc[(iy + 1) * r + ix + 1];
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy;
  }
  return { generate, tileH, T, N, NODE_KEY, MAXH };
})();
if (typeof module !== 'undefined') module.exports = MapGen;
