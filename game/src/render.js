/* render.js: 2:1 isometric view (artkit's convention: 64 px tile, light from the upper left). Terrain is baked
   into 16x16-tile chunks with real corner heights; everything standing on the map is a placeholder sprite drawn
   in code and cached. When artkit sprites exist for a key, they replace the placeholder (see Art.sprite). */
'use strict';
const TW = 64, TH = 32, EL = 12, CH = 16;
const iso = (x, y, z = 0) => [(x - y) * TW / 2, (x + y) * TH / 2 - z * EL];

const Render = (() => {
  let W, ctx, canvas, cam = { x: 0, y: 0, zoom: 1 }, vw = 0, vh = 0, dpr = 1;
  const chunks = new Map(); const CHUNK_MAX = 56;
  const TERR_COL = [[92, 132, 58], [80, 120, 50], [138, 110, 72], [62, 92, 44], [128, 124, 110], [190, 172, 120], [46, 92, 140], [96, 140, 150]];

  function init(world, cv) {
    W = world; canvas = cv;
    ctx = (typeof GLCanvas !== 'undefined' && !/[?&]gl=0/.test(location.search)) ? GLCanvas.create(canvas) : canvas.getContext('2d');
    resize(); loadGround();
  }
  function resize() {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    vw = canvas.clientWidth; vh = canvas.clientHeight;
    canvas.width = Math.round(vw * dpr); canvas.height = Math.round(vh * dpr);
  }
  const hash = (x, y) => { let h = (x * 374761393 + y * 668265263) >>> 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };

  /* ---------------- camera ---------------- */
  function toScreen(x, y, z) { const [sx, sy] = iso(x, y, z); return [(sx - cam.x) * cam.zoom + vw / 2, (sy - cam.y) * cam.zoom + vh / 2]; }
  function toWorld(px, py) {
    const sx = (px - vw / 2) / cam.zoom + cam.x, sy0 = (py - vh / 2) / cam.zoom + cam.y;
    let x = 0, y = 0, z = 0;
    for (let k = 0; k < 5; k++) { const sy = sy0 + z * EL; x = (sx / (TW / 2) + sy / (TH / 2)) / 2; y = (sy / (TH / 2) - sx / (TW / 2)) / 2; z = W.h(x, y); }
    return [x, y];
  }
  function centerOn(x, y) { const [sx, sy] = iso(x, y, W.h(x, y)); cam.x = sx; cam.y = sy; clampCam(); }
  function clampCam() {
    const [l] = iso(0, W.H), [r] = iso(W.W, 0), [, b] = iso(W.W, W.H);
    cam.x = Math.max(l, Math.min(r, cam.x)); cam.y = Math.max(0, Math.min(b, cam.y));
  }
  function viewTiles() {   // world bounding box of the screen, with a margin
    const c = [toWorld(0, 0), toWorld(vw, 0), toWorld(0, vh + 120), toWorld(vw, vh + 120)];
    const xs = c.map(p => p[0]), ys = c.map(p => p[1]);
    return [Math.max(0, Math.floor(Math.min(...xs)) - 2), Math.max(0, Math.floor(Math.min(...ys)) - 2),
            Math.min(W.W - 1, Math.ceil(Math.max(...xs)) + 2), Math.min(W.H - 1, Math.ceil(Math.max(...ys)) + 2)];
  }

  /* ---------------- terrain chunks ---------------- */
  /* Ground: artkit's procedural tiles (styles/fantasy_realm/terrain.json -> tools/build_ground.py -> art/ground_*.jpg),
     1024 px = 16 tiles, laid out top-down. Each chunk is first painted top-down, every ground type through a soft
     bilinear mask so neighbours blend (masks sum to one, added with 'lighter'), then each tile is carried onto its
     real corner heights as two affine-mapped triangles, then shaded by its slope (light from the upper left). */
  const MATS = ['grass', 'meadow', 'dirt', 'forest', 'rock', 'sand', 'water', 'ford'], TP = 64, TEX = 1024;
  const tex = []; let texReady = false;
  function vnoise(x, y) {   // smooth value noise on the world grid, seamless across chunks
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const a = hash(ix, iy), b = hash(ix + 1, iy), c = hash(ix, iy + 1), d = hash(ix + 1, iy + 1);
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  }
  function loadGround(done) {
    let left = MATS.length;
    MATS.forEach((m, i) => { const im = new Image(); im.onload = im.onerror = () => { tex[i] = im.naturalWidth ? im : null; if (--left === 0) { texReady = true; chunks.clear(); done && done(); } }; im.src = `art/ground_realm_${m}.jpg`; });
  }
  let top = null, layer = null, maskCv = null;
  function paintTop(x0, y0) {   // the chunk and a one-tile margin, top-down, 64 px a tile
    const n = CH + 2, S = n * TP, m = W.map;
    if (!top) { top = document.createElement('canvas'); top.width = top.height = S; layer = document.createElement('canvas'); layer.width = layer.height = S;
      maskCv = document.createElement('canvas'); maskCv.width = maskCv.height = n; }
    const g = top.getContext('2d'), lg = layer.getContext('2d'), mg = maskCv.getContext('2d');
    g.globalCompositeOperation = 'source-over'; g.fillStyle = '#000'; g.fillRect(0, 0, S, S);
    const present = new Set(), types = new Uint8Array(n * n);
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
      const x = Math.max(0, Math.min(W.W - 1, x0 - 1 + i)), y = Math.max(0, Math.min(W.H - 1, y0 - 1 + j)), t = m.terr[y * W.W + x];
      types[j * n + i] = t; present.add(t);
    }
    const ox = -(((x0 - 1) * TP) % TEX + TEX) % TEX, oy = -(((y0 - 1) * TP) % TEX + TEX) % TEX;   // keep the texture continuous across chunks
    // blend weights at 16 px a tile: bilinear between tile centres, roughened by noise and sharpened (w^4, renormalised),
    // so borders wander instead of following the tile grid; they still sum to one, so layers add up exactly
    const MR = 16, M = n * MR, list = [...present], wts = list.map(() => new Float32Array(M * M));
    for (let py = 0; py < M; py++) for (let px = 0; px < M; px++) {
      const fx = (px + 0.5) / MR - 0.5, fy = (py + 0.5) / MR - 0.5, ix = Math.max(0, Math.min(n - 2, Math.floor(fx))), iy = Math.max(0, Math.min(n - 2, Math.floor(fy)));
      const tx = Math.min(1, Math.max(0, fx - ix)), ty = Math.min(1, Math.max(0, fy - iy)), wx = x0 - 1 + px / MR, wy = y0 - 1 + py / MR;
      let sum = 0;
      for (let k = 0; k < list.length; k++) {
        const t = list[k];
        let w = (types[iy * n + ix] === t ? (1 - tx) * (1 - ty) : 0) + (types[iy * n + ix + 1] === t ? tx * (1 - ty) : 0) +
                (types[(iy + 1) * n + ix] === t ? (1 - tx) * ty : 0) + (types[(iy + 1) * n + ix + 1] === t ? tx * ty : 0);
        if (w > 0) { w *= 0.35 + vnoise(wx * 1.1 + t * 17.3, wy * 1.1 - t * 9.1) * 1.3; w = w * w; w = w * w; }
        wts[k][py * M + px] = w; sum += w;
      }
      if (sum > 0) for (let k = 0; k < list.length; k++) wts[k][py * M + px] /= sum;
    }
    if (maskCv.width !== M) { maskCv.width = maskCv.height = M; }
    list.forEach((t, k) => {
      const img = mg.createImageData(M, M), w = wts[k];
      for (let q = 0; q < M * M; q++) img.data[q * 4 + 3] = Math.round(w[q] * 255);
      mg.putImageData(img, 0, 0);
      lg.globalCompositeOperation = 'source-over'; lg.clearRect(0, 0, S, S);
      if (tex[t]) { for (let yy = oy; yy < S; yy += TEX) for (let xx = ox; xx < S; xx += TEX) lg.drawImage(tex[t], xx, yy); }
      else { const c = TERR_COL[t]; lg.fillStyle = `rgb(${c})`; lg.fillRect(0, 0, S, S); }
      lg.globalCompositeOperation = 'destination-in'; lg.imageSmoothingEnabled = true; lg.imageSmoothingQuality = 'low';
      lg.drawImage(maskCv, 0, 0, S, S);
      g.globalCompositeOperation = list.length > 1 ? 'lighter' : 'source-over'; g.drawImage(layer, 0, 0);
    });
    g.globalCompositeOperation = 'source-over';
    return top;
  }
  let buildBudget = 0;   // full chunk builds allowed this frame; the rest get a quick flat-colour stand-in, upgraded later
  function chunk(cx, cy) {
    const key = cx * 1000 + cy; let c = chunks.get(key);
    if (c && (!c.rough || buildBudget <= 0 || !texReady)) { c.used = performance.now(); return c; }
    const full = texReady && buildBudget > 0; if (full) buildBudget--;
    if (!c && chunks.size >= CHUNK_MAX) { let old = null; for (const [k, v] of chunks) if (!old || v.used < old[1].used) old = [k, v]; chunks.delete(old[0]); }
    const x0 = cx * CH, y0 = cy * CH, ox = (x0 - (y0 + CH)) * TW / 2, oy = (x0 + y0) * TH / 2 - MapGen.MAXH * EL;
    const cv = c ? c.cv : document.createElement('canvas'); cv.width = CH * TW + 2; cv.height = CH * TH + MapGen.MAXH * EL + 4;
    const g = cv.getContext('2d'), m = W.map, R = W.W + 1, x1 = Math.min(W.W, x0 + CH), y1 = Math.min(W.H, y0 + CH);
    const P4 = (x, y) => { const a = m.hc[y * R + x], b = m.hc[y * R + x + 1], c2 = m.hc[(y + 1) * R + x + 1], d = m.hc[(y + 1) * R + x];
      return [a, b, c2, d, [iso(x, y, a), iso(x + 1, y, b), iso(x + 1, y + 1, c2), iso(x, y + 1, d)].map(([sx, sy]) => [sx - ox + 1, sy - oy])]; };
    const quad = (P, grow) => { g.moveTo(P[0][0], P[0][1] - grow); g.lineTo(P[1][0] + grow * 1.6, P[1][1]); g.lineTo(P[2][0], P[2][1] + grow); g.lineTo(P[3][0] - grow * 1.6, P[3][1]); g.closePath(); };
    if (full) {
      const src = paintTop(x0, y0), levels = new Map(), sloped = [];
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        const q = P4(x, y); if (q[0] === q[1] && q[1] === q[2] && q[2] === q[3]) { let l = levels.get(q[0]); if (!l) levels.set(q[0], l = []); l.push(q[4]); } else sloped.push([x, y, q]);
      }
      // flat tiles: one affine draw per height level, clipped to that level's tiles
      for (const [h, list] of levels) {
        g.save(); g.beginPath(); for (const P of list) quad(P, 0.6); g.clip();
        // top-down (u, v) -> screen: tile (x, y) at u = (x - x0 + 1) * TP
        const a = TW / 2 / TP, b = TH / 2 / TP, k0 = iso(x0 - 1, y0 - 1, h);
        g.setTransform(a, b, -a, b, k0[0] - ox + 1, k0[1] - oy);
        g.drawImage(src, 0, 0); g.restore();
      }
      for (const [x, y, q] of sloped) { const P = q[4], u = (x - x0 + 1) * TP, v = (y - y0 + 1) * TP; tri(g, src, u, v, P[0], P[1], P[2], 0); tri(g, src, u, v, P[0], P[2], P[3], 1); }
    } else {
      g.clearRect(0, 0, cv.width, cv.height);
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const q = P4(x, y), c = TERR_COL[m.terr[y * W.W + x]]; g.fillStyle = `rgb(${c})`; g.beginPath(); quad(q[4], 0.7); g.fill(); }
    }
    // slope shading (light from the upper left)
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const [a, b, c2, d, P] = P4(x, y), gx = (b + c2 - a - d) / 2, gy = (d + c2 - a - b) / 2;
      const light = gx * 0.2 + gy * 0.07 + ((a + b + c2 + d) / 4) * 0.02;
      if (Math.abs(light) > 0.01) { g.fillStyle = light > 0 ? `rgba(255,246,220,${Math.min(0.3, light * 0.8)})` : `rgba(10,16,30,${Math.min(0.45, -light)})`; g.beginPath(); quad(P, 0.4); g.fill(); }
    }
    if (!c) { c = { cv, ox: ox - 1, oy }; chunks.set(key, c); }
    c.rough = !full; c.used = performance.now(); return c;
  }
  /* one textured triangle: the top-down square (u, v, TP) mapped onto screen points; k = 0 upper-right half, 1 lower-left */
  function tri(g, src, u, v, p0, p1, p2, k) {
    const s = TP, cx = (p0[0] + p1[0] + p2[0]) / 3, cy = (p0[1] + p1[1] + p2[1]) / 3, grow = p => { const dx = p[0] - cx, dy = p[1] - cy, l = Math.hypot(dx, dy) || 1; return [p[0] + dx / l * 0.8, p[1] + dy / l * 0.8]; };
    let a, b, c, d;
    if (k === 0) { a = (p1[0] - p0[0]) / s; b = (p1[1] - p0[1]) / s; c = (p2[0] - p1[0]) / s; d = (p2[1] - p1[1]) / s; }
    else { c = (p2[0] - p0[0]) / s; d = (p2[1] - p0[1]) / s; a = (p1[0] - p2[0]) / s; b = (p1[1] - p2[1]) / s; }
    const e = p0[0] - a * u - c * v, f = p0[1] - b * u - d * v, q0 = grow(p0), q1 = grow(p1), q2 = grow(p2);
    g.save(); g.beginPath(); g.moveTo(q0[0], q0[1]); g.lineTo(q1[0], q1[1]); g.lineTo(q2[0], q2[1]); g.closePath(); g.clip();
    g.setTransform(a, b, c, d, e, f); g.drawImage(src, u - 1, v - 1, s + 2, s + 2, u - 1, v - 1, s + 2, s + 2); g.restore();
  }

  /* ---------------- sprites (placeholders, cached at 2x) ---------------- */
  const cache = new Map();
  function sprite(key, w, h, ax, ay, draw) {
    let s = cache.get(key); if (s) return s;
    const cv = document.createElement('canvas'), S = 2; cv.width = w * S; cv.height = h * S;
    const g = cv.getContext('2d'); g.scale(S, S); g.translate(ax, ay); g.lineJoin = 'round'; g.lineCap = 'round';
    draw(g); s = { cv, w, h, ax, ay }; cache.set(key, s); return s;
  }
  function blit(s, x, y, flip = false, alpha = 1) {
    const k = cam.zoom; ctx.globalAlpha = alpha;
    if (flip) { ctx.save(); ctx.translate(x, y); ctx.scale(-1, 1); ctx.drawImage(s.cv, -s.ax * k, -s.ay * k, s.w * k, s.h * k); ctx.restore(); }
    else ctx.drawImage(s.cv, x - s.ax * k, y - s.ay * k, s.w * k, s.h * k);
    ctx.globalAlpha = 1;
  }
  const shade = (hex, f) => { const v = parseInt(hex.slice(1), 16); const c = [v >> 16, v >> 8 & 255, v & 255].map(x => Math.max(0, Math.min(255, x * f | 0))); return `rgb(${c})`; };
  function poly(g, pts, fill, line = 'rgba(30,20,10,0.85)') { g.beginPath(); g.moveTo(...pts[0]); for (const p of pts.slice(1)) g.lineTo(...p); g.closePath(); g.fillStyle = fill; g.fill(); if (line) { g.strokeStyle = line; g.lineWidth = 1; g.stroke(); } }
  function ell(g, x, y, rx, ry, fill, line) { g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fillStyle = fill; g.fill(); if (line) { g.strokeStyle = line; g.lineWidth = 1; g.stroke(); } }

  /* an isometric block on a footprint s tiles wide (origin = footprint centre on the ground) */
  function block(g, s, hgt, wall, roof, roofH = 0, inset = 0.12) {
    const hw = (s - inset * 2) * TW / 4, hh = (s - inset * 2) * TH / 4;
    const top = [0, -hh * 2], right = [hw * 2, 0], bottom = [0, hh * 2], left = [-hw * 2, 0];
    const up = p => [p[0], p[1] - hgt];
    poly(g, [left, bottom, up(bottom), up(left)], shade(wall, 0.78));
    poly(g, [bottom, right, up(right), up(bottom)], shade(wall, 1.0));
    if (roofH > 0) {   // gable along the x axis (ridge from upper-left to lower-right)
      const rl = [(left[0] + top[0]) / 2, (left[1] + top[1]) / 2 - hgt - roofH], rr = [(bottom[0] + right[0]) / 2, (bottom[1] + right[1]) / 2 - hgt - roofH];
      poly(g, [up(left), up(bottom), rr, rl], shade(roof, 0.85));
      poly(g, [up(bottom), up(right), rr], shade(roof, 1.08));
      poly(g, [up(left), up(top), rl], shade(roof, 0.7));
      poly(g, [up(top), up(right), rr, rl], shade(roof, 1.15));
    } else poly(g, [up(top), up(right), up(bottom), up(left)], shade(roof, 1.1));
  }
  function buildingSprite(b, team) {
    const s = b.size, t = b.type, stage = b.built ? 'done' : (b.progress < 0.5 ? 'f0' : 'f1');
    const key = `b:${t}:${team}:${stage}:${t === 'farm' ? Math.min(4, Math.ceil((b.food / DATA.FARM.food) * 4)) : 0}`;
    const w = s * TW + 20, h = s * TH + 150;
    return sprite(key, w, h, w / 2, h - s * TH / 2 - 6, g => {
      const hw = s * TW / 2, hh = s * TH / 2;
      if (!b.built) {   // foundation and scaffold
        poly(g, [[0, -hh], [hw, 0], [0, hh], [-hw, 0]], 'rgba(150,120,80,0.75)', 'rgba(60,40,20,0.9)');
        if (stage === 'f1') block(g, s, 18 * Math.min(s, 3) / 2, '#b0a080', '#9c7b52', 0, 0.15);
        g.strokeStyle = '#6b4a28'; g.lineWidth = 1.5;
        for (const [px, py] of [[-hw * 0.7, 0], [hw * 0.7, 0], [0, hh * 0.7]]) { g.beginPath(); g.moveTo(px, py); g.lineTo(px, py - 14 * Math.min(s, 3)); g.stroke(); }
        return;
      }
      const C = team;
      switch (t) {
        case 'town_hall': {
          block(g, 4, 30, '#9a958a', '#5d5a55', 0, 0.06);
          g.translate(0, -30); block(g, 3, 22, '#b58e5e', '#7a2f22', 30, 0.1); g.translate(0, 30);
          g.translate(0, -26); block(g, 1, 52, '#a39d90', '#6a2a1f', 18, 0.05); g.translate(0, 26);
          g.fillStyle = C; g.fillRect(-2, -118, 12, 8); g.strokeStyle = '#3a2a1a'; g.beginPath(); g.moveTo(-2, -100); g.lineTo(-2, -120); g.stroke();
          g.fillStyle = '#2b2018'; g.fillRect(8, -18, 10, 14);
          break; }
        case 'cottage': block(g, 2, 16, '#c9b087', '#b08a3c', 20); g.fillStyle = C; g.fillRect(10, -12, 6, 5); g.fillStyle = '#3a2a1a'; g.fillRect(-14, -12, 6, 10); break;
        case 'mill': {
          block(g, 2, 26, '#c8b898', '#8b5a2b', 14);
          g.save(); g.translate(-6, -38); g.strokeStyle = '#5a3b1d'; g.lineWidth = 2;
          for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + 0.4, c = Math.cos(a), sn = Math.sin(a);
            g.beginPath(); g.moveTo(0, 0); g.lineTo(c * 24, sn * 24); g.stroke();
            poly(g, [[c * 8 - sn * 1, sn * 8 + c * 1], [c * 24 - sn * 1, sn * 24 + c * 1], [c * 24 - sn * 7, sn * 24 + c * 7], [c * 8 - sn * 6, sn * 8 + c * 6]], '#e8dcc0', '#6b5233'); }
          ell(g, 0, 0, 2.5, 2.5, '#3a2a1a'); g.restore(); g.fillStyle = C; g.fillRect(14, -30, 5, 4); break; }
        case 'lumber_camp': {
          block(g, 2, 14, '#8d6b45', '#6b4f2e', 12, 0.2);
          for (let k = 0; k < 3; k++) ell(g, 16 - k * 3, 2 - k * 5, 9, 3.5, '#9a6a3a', '#4a2f15');
          g.fillStyle = C; g.fillRect(-2, -36, 6, 4); break; }
        case 'mining_camp': {
          block(g, 2, 14, '#8a8478', '#5e4b36', 12, 0.2);
          ell(g, 14, 2, 8, 4, '#9a9a94', '#333'); ell(g, 19, -1, 5, 3, '#6d7b8c', '#333'); ell(g, 10, 6, 4, 2.5, '#62e0ff', '#2a6a80');
          g.fillStyle = C; g.fillRect(-2, -36, 6, 4); break; }
        case 'farm': {
          const f = b.food / DATA.FARM.food;
          poly(g, [[0, -hh + 3], [hw - 6, 0], [0, hh - 3], [-hw + 6, 0]], '#7a5a34', '#4a3218');
          g.strokeStyle = f > 0.25 ? 'rgba(120,170,60,0.95)' : 'rgba(170,150,70,0.9)'; g.lineWidth = 2;
          for (let k = -3; k <= 3; k++) { const o = k * 7; g.beginPath(); g.moveTo(-hw / 2 + 8 + o, -hh / 2 + 4 + o / 2); g.lineTo(hw / 2 - 8 + o, hh / 2 - 4 + o / 2); g.stroke(); }
          break; }
        case 'barracks': {
          block(g, 3, 22, '#8f8574', '#4f3e2c', 18);
          g.fillStyle = C; g.fillRect(4, -64, 12, 9); g.strokeStyle = '#2a1d10'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(4, -48); g.lineTo(4, -66); g.stroke();
          g.strokeStyle = '#ccc'; g.beginPath(); g.moveTo(16, -4); g.lineTo(32, -26); g.moveTo(32, -4); g.lineTo(16, -26); g.stroke();
          break; }
        case 'palisade': {
          for (let k = -2; k <= 2; k++) { const x = k * 6, y = -k * 3 * 0 + Math.abs(k); poly(g, [[x - 2.5, y], [x + 2.5, y], [x + 2.5, y - 22], [x, y - 26], [x - 2.5, y - 22]], k % 2 ? '#8a6238' : '#9b7044'); }
          break; }
        case 'gate': {
          poly(g, [[-14, 2], [-9, 2], [-9, -30], [-14, -30]], '#7b5530'); poly(g, [[9, 2], [14, 2], [14, -30], [9, -30]], '#7b5530');
          poly(g, [[-9, 0], [9, 0], [9, -20], [-9, -20]], '#5a3b1d'); g.fillStyle = C; g.fillRect(-3, -28, 6, 5); break; }
        case 'watchpost': {
          g.strokeStyle = '#5a3b1d'; g.lineWidth = 2.5;
          for (const [x0, x1] of [[-12, -7], [12, 7], [-4, -3], [4, 3]]) { g.beginPath(); g.moveTo(x0, 4); g.lineTo(x1, -46); g.stroke(); }
          g.translate(0, -46); block(g, 1, 8, '#8a6238', '#6b2a1f', 10, 0.0); g.translate(0, 46);
          g.fillStyle = C; g.fillRect(-1, -78, 8, 5); break; }
        case 'blacksmith': {
          block(g, 3, 20, '#7d7468', '#3d3a38', 16);
          poly(g, [[-26, -44], [-16, -44], [-16, -66], [-26, -66]], '#5a5550'); ell(g, -21, -70, 6, 4, 'rgba(90,90,90,0.6)');
          poly(g, [[14, -2], [30, -2], [27, -10], [17, -10]], '#3a3a3e'); ell(g, 22, -12, 5, 2.5, '#ff8a30');
          g.fillStyle = C; g.fillRect(4, -58, 8, 6); break; }
        case 'market': {
          block(g, 4, 6, '#a08a66', '#8a7450', 0, 0.06);
          for (const [x, y, c] of [[-34, -8, '#c94f3a'], [6, -26, '#d8b24a'], [34, -6, '#4f8ac9'], [0, 12, '#6fae5a']]) { g.save(); g.translate(x, y); block(g, 1.4, 12, '#b89868', c, 12, 0.05); g.restore(); }
          g.fillStyle = C; g.fillRect(-2, -60, 10, 7); g.strokeStyle = '#2a1d10'; g.beginPath(); g.moveTo(-2, -40); g.lineTo(-2, -62); g.stroke(); break; }
        case 'archery_range': {
          block(g, 3, 16, '#9b8660', '#5d6b3a', 14);
          ell(g, 26, -12, 8, 8, '#f2ead8', '#3a2a1a'); ell(g, 26, -12, 5, 5, '#c94f3a'); ell(g, 26, -12, 2, 2, '#f2ead8');
          g.strokeStyle = '#5a3b1d'; g.lineWidth = 2; g.beginPath(); g.moveTo(26, -4); g.lineTo(22, 6); g.moveTo(26, -4); g.lineTo(30, 6); g.stroke();
          g.fillStyle = C; g.fillRect(-4, -52, 9, 6); break; }
        case 'stable': {
          block(g, 3, 16, '#a07a50', '#7a5a34', 16);
          g.fillStyle = '#2b2018'; g.fillRect(6, -18, 12, 16); g.fillRect(24, -12, 10, 12);
          g.strokeStyle = '#6b4a28'; g.lineWidth = 2; g.beginPath(); g.moveTo(-44, 10); g.lineTo(-14, 26); g.moveTo(-44, 4); g.lineTo(-14, 20); g.stroke();
          g.fillStyle = C; g.fillRect(-4, -54, 9, 6); break; }
        case 'watch_tower': {
          block(g, 1, 56, '#a9a498', '#8a857a', 0, 0.12);
          g.translate(0, -56); block(g, 1, 8, '#b8b3a6', '#6a2a1f', 12, 0.0); g.translate(0, 56);
          g.fillStyle = '#2b2018'; g.fillRect(3, -44, 3, 8); g.fillStyle = C; g.fillRect(-1, -92, 9, 6); break; }
        case 'stone_wall': block(g, 1, 20, '#a9a498', '#bdb8aa', 0, 0.02); break;
        case 'stone_gate': {
          block(g, 1, 28, '#a9a498', '#bdb8aa', 0, 0.02);
          poly(g, [[2, -2], [14, -8], [14, -22], [8, -27], [2, -22]], '#4a3320'); g.fillStyle = C; g.fillRect(-3, -40, 7, 5); break; }
      }
    });
  }
  const NODE_SPR = {};
  function nodeSprite(type, v) {
    const key = `n:${type}:${v}`;
    return sprite(key, 70, 110, 35, 90, g => {
      if (type !== 6) ell(g, 0, 2, 16, 7, 'rgba(0,0,0,0.22)');
      if (type === 1) {   // tree: broadleaf or conifer
        if (v < 2) { g.fillStyle = '#5b3c20'; g.fillRect(-2.5, -18, 5, 20);
          ell(g, 0, -30, 17, 15, v ? '#2f5f2a' : '#3a6e2e', '#1d3a17'); ell(g, -6, -40, 12, 10, v ? '#386f30' : '#478236', '#1d3a17'); ell(g, 5, -45, 9, 8, v ? '#468039' : '#559440', '#1d3a17'); }
        else { g.fillStyle = '#4a3018'; g.fillRect(-2, -10, 4, 12);
          for (let k = 0; k < 3; k++) poly(g, [[-15 + k * 3, -6 - k * 14], [15 - k * 3, -6 - k * 14], [0, -32 - k * 14]], v === 2 ? '#2a5a3a' : '#24503a', '#14301f'); }
      } else if (type === 2) {
        ell(g, 0, -6, 13, 9, '#3c7a32', '#1f4019');
        for (let k = 0; k < 7; k++) ell(g, Math.cos(k * 2.3) * 8, -6 + Math.sin(k * 1.7) * 5, 2, 2, '#c0283a');
      } else {
        if (type === 6) {   // shore fish: a few shapes under the surface
          for (let k = 0; k < 3; k++) { const x = (k - 1) * 9, y = -2 + (k % 2) * 4; ell(g, x, y, 5, 2.2, 'rgba(190,215,230,0.85)', 'rgba(30,60,90,0.6)'); poly(g, [[x + 5, y], [x + 9, y - 2.5], [x + 9, y + 2.5]], 'rgba(190,215,230,0.85)', null); }
          return;
        }
        const col = { 3: ['#a8a69e', '#7a786f'], 4: ['#5d5f63', '#8a5a3a'], 5: ['#3a8fb0', '#7af0ff'] }[type];
        if (type === 5) {
          for (let k = 0; k < 4; k++) { const x = (k - 1.5) * 7, hgt = 16 + (k * 7 + v * 5) % 14;
            poly(g, [[x - 4, 0], [x + 4, 0], [x + 2, -hgt], [x - 1, -hgt - 5]], k % 2 ? col[0] : col[1], '#155066'); }
        } else {
          for (let k = 0; k < 3; k++) { const x = (k - 1) * 9 + v, y = -(k % 2) * 4;
            poly(g, [[x - 9, y], [x - 6, y - 10], [x + 2, y - 14], [x + 9, y - 6], [x + 8, y + 1]], col[0], '#333');
            if (type === 4) { g.strokeStyle = col[1]; g.lineWidth = 2; g.beginPath(); g.moveTo(x - 4, y - 6); g.lineTo(x + 4, y - 9); g.stroke(); } }
        }
      }
    });
  }
  function unitSprite(u, team, frame) {
    const t = u.type, carry = u.carry && u.carry.amt > 0 ? u.carry.res : '', maa = t === 'militia' && W.tech(u.owner, 'man_at_arms'), key = `u:${t}:${team}:${frame}:${carry}:${u.carcass ? 1 : 0}:${u.artifact ? 1 : 0}:${maa ? 1 : 0}`;
    return sprite(key, 60, 70, 30, 56, g => {
      const bob = frame === 1 ? -1.5 : 0, leg = frame === 1 ? 3 : frame === 2 ? -3 : 0;
      ell(g, 0, 0, t === 'ogre' ? 13 : t === 'scout' ? 12 : 7, t === 'ogre' ? 5 : 3.5, 'rgba(0,0,0,0.25)');
      if (u.carcass) { ell(g, 0, -3, t === 'boar' ? 11 : 8, 4, t === 'sheep' ? '#e6e2d6' : t === 'boar' ? '#4a3426' : '#a57a4c', '#3a2a1a'); ell(g, 4, -4, 3, 1.5, '#8a2020'); return; }
      const human = (tunic, skin = '#e0b48a', scale = 1) => {
        g.strokeStyle = '#3a2a1a'; g.lineWidth = 2.5 * scale;
        g.beginPath(); g.moveTo(-2 * scale, -9 * scale + bob); g.lineTo(-2 * scale - leg * 0.5, 0); g.moveTo(2 * scale, -9 * scale + bob); g.lineTo(2 * scale + leg * 0.5, 0); g.stroke();
        poly(g, [[-5 * scale, -8 * scale + bob], [5 * scale, -8 * scale + bob], [4 * scale, -19 * scale + bob], [-4 * scale, -19 * scale + bob]], tunic, '#2a1d10');
        ell(g, 0, -23 * scale + bob, 3.6 * scale, 3.8 * scale, skin, '#2a1d10');
      };
      switch (t) {
        case 'villager':
          human(team);
          g.fillStyle = '#6b4a2a'; g.fillRect(-4, -27 + bob, 8, 2);
          if (carry) { const c = DATA.RES_INFO[carry].color; ell(g, -6, -15 + bob, 4, 4, c, '#2a1d10'); }
          else { g.strokeStyle = '#5a3b1d'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(5, -12 + bob); g.lineTo(9, -24 + bob); g.stroke(); }
          break;
        case 'militia':
          human(team);
          ell(g, 0, -25 + bob, 4, 2.8, '#9aa0a8', '#333');
          g.strokeStyle = '#d8dce0'; g.lineWidth = 1.8; g.beginPath(); g.moveTo(6, -12 + bob); g.lineTo(11, -26 + bob); g.stroke();
          ell(g, -6, -14 + bob, maa ? 4.5 : 3.5, maa ? 6 : 5, maa ? '#9aa0a8' : '#7a5a34', '#2a1d10');
          if (maa) poly(g, [[-4, -9 + bob], [4, -9 + bob], [4, -18 + bob], [-4, -18 + bob]], 'rgba(170,176,184,0.75)', '#2a1d10');
          if (u.artifact) { ell(g, 0, -34 + bob, 4, 4, '#ffd76a', '#8a6a10'); }
          break;
        case 'scout':   // wolf rider
          ell(g, 0, -10 + bob, 12, 5.5, '#6e7178', '#26282c');
          g.strokeStyle = '#3a3c42'; g.lineWidth = 2.2; g.beginPath(); for (const x of [-8, -4, 5, 9]) { g.moveTo(x, -6); g.lineTo(x + (x % 2 ? leg : -leg) * 0.4, 0); } g.stroke();
          ell(g, 12, -14 + bob, 4.5, 3.5, '#6e7178', '#26282c'); poly(g, [[11, -17 + bob], [12, -22 + bob], [14, -17 + bob]], '#55585e'); poly(g, [[-12, -11 + bob], [-18, -15 + bob], [-12, -8 + bob]], '#6e7178', '#26282c');
          poly(g, [[-3, -14 + bob], [3, -14 + bob], [2, -24 + bob], [-2, -24 + bob]], team, '#2a1d10'); ell(g, 0, -27 + bob, 3, 3, '#7fae4a', '#2a1d10');
          g.strokeStyle = '#8a6a3a'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(5, -12 + bob); g.lineTo(9, -32 + bob); g.stroke();
          break;
        case 'spearman':   // dwarf pikeman: short, broad, long pike
          human(team, '#e0b48a', 0.82); ell(g, 0, -20 + bob, 3.6, 2.4, '#8a8f98', '#333'); poly(g, [[-3, -15 + bob], [3, -15 + bob], [0, -9 + bob]], '#b8703a', '#3a2010');
          g.strokeStyle = '#6b4a28'; g.lineWidth = 1.6; g.beginPath(); g.moveTo(5, 0); g.lineTo(9, -38 + bob); g.stroke(); poly(g, [[7.5, -38 + bob], [10.5, -38 + bob], [9.3, -45 + bob]], '#d8dce0', '#333');
          break;
        case 'archer':   // elf archer: slim, hooded, bow
          human(team, '#ecd0b0', 1.02); poly(g, [[-4, -24 + bob], [4, -24 + bob], [0, -31 + bob]], '#2f5f3a', '#14301f');
          g.strokeStyle = '#6b4a28'; g.lineWidth = 1.6; g.beginPath(); g.arc(7, -15 + bob, 9, -1.2, 1.2); g.stroke(); g.strokeStyle = '#ddd'; g.lineWidth = 0.7; g.beginPath(); g.moveTo(10.3, -23.4 + bob); g.lineTo(10.3, -6.6 + bob); g.stroke();
          break;
        case 'skirmisher':   // halfling slinger: small, sling and a wicker shield
          human(team, '#e8c09a', 0.72); ell(g, -5, -10 + bob, 3.5, 4.5, '#b89858', '#3a2a1a');
          g.strokeStyle = '#4a3320'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(4, -12 + bob); g.quadraticCurveTo(12, -24 + bob, 8, -28 + bob); g.stroke(); ell(g, 8, -28 + bob, 1.8, 1.8, '#888');
          break;
        case 'sheep': ell(g, 0, -7, 8, 5.5, '#efece2', '#7a776d'); ell(g, 8, -8, 3, 2.5, '#3a3530'); break;
        case 'deer':
          g.strokeStyle = '#5a3b1d'; g.lineWidth = 1.6; g.beginPath(); for (const x of [-6, -3, 4, 7]) { g.moveTo(x, -6); g.lineTo(x, 0); } g.stroke();
          ell(g, 0, -9 + bob, 9, 4.5, '#b07a45', '#4a2f15'); ell(g, 10, -14 + bob, 3, 2.5, '#b07a45', '#4a2f15');
          g.beginPath(); g.moveTo(10, -16); g.lineTo(8, -23); g.moveTo(11, -16); g.lineTo(14, -22); g.stroke(); break;
        case 'boar': ell(g, 0, -7 + bob, 11, 6, '#4a3426', '#1d130b'); ell(g, 10, -8 + bob, 4, 3.5, '#4a3426', '#1d130b'); g.fillStyle = '#eee'; g.fillRect(12, -7 + bob, 3, 1.2); break;
        case 'wolf': ell(g, 0, -8 + bob, 10, 4.5, '#6e7178', '#26282c'); ell(g, 10, -11 + bob, 4, 3, '#6e7178', '#26282c'); poly(g, [[9, -14 + bob], [10, -18 + bob], [12, -14 + bob]], '#55585e'); g.fillStyle = '#ff5030'; g.fillRect(12, -12 + bob, 1.5, 1.2); break;
        case 'goblin': human('#4e6b2a', '#7fae4a', 0.85); g.strokeStyle = '#8a6a3a'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(6, -4 + bob); g.lineTo(9, -30 + bob); g.stroke(); poly(g, [[8, -30 + bob], [10, -30 + bob], [9, -35 + bob]], '#bbb'); break;
        case 'ogre': human('#6b4a30', '#a9b07a', 1.7); g.strokeStyle = '#4a3018'; g.lineWidth = 4; g.beginPath(); g.moveTo(10, -18 + bob); g.lineTo(18, -40 + bob); g.stroke(); break;
      }
    });
  }
  function artifactSprite() {
    return sprite('artifact', 40, 50, 20, 40, g => {
      ell(g, 0, 0, 8, 3.5, 'rgba(0,0,0,0.25)');
      poly(g, [[-6, 0], [6, 0], [4, -16], [-4, -16]], '#8a8478', '#333');
      ell(g, 0, -22, 6, 6, '#ffd76a', '#8a6a10'); ell(g, 0, -22, 2.5, 2.5, '#fff8d0');
    });
  }

  /* ---------------- frame ---------------- */
  function draw(sel, ui, alpha = 1) {
    // the canvas can change size without a window resize (the HUD reflowing on a phone): keep the backing store and
    // the input maths in step, or taps land off from what is drawn
    if (canvas.clientWidth !== vw || canvas.clientHeight !== vh || Math.min(2, window.devicePixelRatio || 1) !== dpr) resize();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, vw, vh);
    const [x0, y0, x1, y1] = viewTiles(), P = W.players[0], Wd = W.W;
    // terrain chunks
    const T0 = performance.now(); buildBudget = 1;
    const cx0 = Math.floor(x0 / CH), cy0 = Math.floor(y0 / CH), cx1 = Math.floor(x1 / CH), cy1 = Math.floor(y1 / CH);
    for (let s = cx0 + cy0; s <= cx1 + cy1; s++) for (let cx = cx0; cx <= cx1; cx++) {
      const cy = s - cx; if (cy < cy0 || cy > cy1) continue;
      const x0c = cx * CH, y0c = cy * CH, cox = (x0c - (y0c + CH)) * TW / 2 - 1, coy = (x0c + y0c) * TH / 2 - MapGen.MAXH * EL;
      const px = (cox - cam.x) * cam.zoom + vw / 2, py = (coy - cam.y) * cam.zoom + vh / 2;
      if (px > vw || py > vh || px + (CH * TW + 2) * cam.zoom < 0 || py + (CH * TH + MapGen.MAXH * EL + 4) * cam.zoom < 0) continue;
      const c = chunk(cx, cy);
      ctx.drawImage(c.cv, px, py, c.cv.width * cam.zoom, c.cv.height * cam.zoom);
    }
    const T1 = performance.now();
    const k = cam.zoom, list = [];
    // static resources
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const i = y * Wd + x, n = W.map.node[i]; if (!n || !P.explored[i]) continue;
      list.push({ d: x + y + 1, f: () => {
        const [sx, sy] = toScreen(x + 0.5, y + 0.5, W.h(x + 0.5, y + 0.5));
        if (sx < -60 || sx > vw + 60 || sy < -40 || sy > vh + 120) return;
        const v = Math.floor(hash(x, y) * 4);
        blit(nodeSprite(n, n === 1 ? v : v % 3), sx, sy);
        if (n === 5 || n === 4) { const c = W.wardedBy(i); if (c) { ctx.strokeStyle = 'rgba(190,90,255,0.75)'; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.ellipse(sx, sy - 4 * k, 18 * k, 9 * k, 0, 0, Math.PI * 2); ctx.stroke(); } }
      } });
    }
    for (const e of W.ents) {
      if (e.dead || e.garrisoned || (e.kind === 'artifact' && e.carrier)) continue;
      const ti = Math.floor(e.y) * Wd + Math.floor(e.x);
      if (e.x < x0 - 3 || e.x > x1 + 3 || e.y < y0 - 3 || e.y > y1 + 3) continue;
      if (e.owner !== 0) { if (e.kind === 'building' ? !W.seesRect(P, e) : !P.vis[ti]) continue; }
      list.push({ d: e.x + e.y + (e.kind === 'building' && e.D.walk ? -e.size : 0), e });
    }
    // fog memory: other players' buildings as last seen
    for (const g of P.seen.values()) if (!W.seesRect(P, g) && g.x > x0 - 3 && g.x < x1 + 3 && g.y > y0 - 3 && g.y < y1 + 3)
      list.push({ d: g.x + g.y + (g.D.walk ? -g.size : 0), e: g, ghost: true });
    list.sort((a, b) => a.d - b.d);
    const selSet = sel.set;
    for (const it of list) {
      if (it.f) { it.f(); continue; }
      const e = it.e, team = W.players[e.owner].color;
      const ex = e.kind === 'unit' && e.px !== undefined ? e.px + (e.x - e.px) * alpha : e.x, ey = e.kind === 'unit' && e.py !== undefined ? e.py + (e.y - e.py) * alpha : e.y;   // between ticks
      const z = W.h(ex, ey), [sx, sy] = toScreen(ex, ey, z);
      if (it.ghost) { blit(buildingSprite(e, team), sx, sy); continue; }
      if (selSet.has(e.id) || ui.hoverId === e.id) {
        const r = e.kind === 'building' ? e.size * 0.75 : e.r * 1.6;
        ctx.strokeStyle = e.owner === 0 ? 'rgba(255,255,255,0.9)' : e.owner === 1 ? 'rgba(255,80,60,0.9)' : 'rgba(255,220,80,0.9)';
        ctx.lineWidth = 1.5; ctx.beginPath(); ctx.ellipse(sx, sy, r * TW / 2 * k, r * TH / 2 * k, 0, 0, Math.PI * 2); ctx.stroke();
      }
      if (e.kind === 'building') {
        const fz = W.h(e.x, e.y);
        blit(buildingSprite(e, team), sx, sy + (fz - z) * EL * k);
      } else if (e.kind === 'artifact') {
        const s = artifactSprite(); blit(s, sx, sy + Math.sin(W.time * 3 + e.id) * 2 * k);
        ctx.fillStyle = 'rgba(255,220,120,0.18)'; ctx.beginPath(); ctx.arc(sx, sy - 22 * k, 14 * k, 0, 7); ctx.fill();
      } else {
        const frame = e.moving ? (Math.floor(e.walkT * 6) % 2) + 1 : (e.swingT && W.time - e.swingT < 0.3 ? 1 : 0);
        const flip = Math.cos(e.facing) - Math.sin(e.facing) < 0;   // screen-left headings mirror the sprite
        blit(unitSprite(e, team, frame), sx, sy, flip);
      }
      // health bar
      if (e.kind !== 'artifact' && !e.carcass && (selSet.has(e.id) || ui.hoverId === e.id || (e.hp < e.maxHp && e.kind === 'unit' && e.hitT && W.time - e.hitT < 4))) {
        const top = e.kind === 'building' ? sy - (e.size * 16 + 40) * k : sy - (e.type === 'ogre' ? 60 : 38) * k, bw = (e.kind === 'building' ? 40 : 22) * k;
        ctx.fillStyle = 'rgba(0,0,0,0.7)'; ctx.fillRect(sx - bw / 2 - 1, top - 1, bw + 2, 5);
        ctx.fillStyle = e.owner === 0 ? '#5fd35f' : e.owner === 1 ? '#e04a3a' : '#e8c440'; ctx.fillRect(sx - bw / 2, top, bw * Math.max(0, e.hp / e.maxHp), 3);
        if (e.kind === 'building' && !e.built) { ctx.fillStyle = '#6fb0ff'; ctx.fillRect(sx - bw / 2, top + 4, bw * e.progress, 2); }
      }
    }
    const T2 = performance.now();
    // effects
    for (const f of W.fx) {
      if (f.t < 0) continue;
      if (f.kind === 'arrow') {
        const p = Math.min(1, f.t / f.life), x = f.x0 + (f.x1 - f.x0) * p, y = f.y0 + (f.y1 - f.y0) * p, z = W.h(x, y) + f.z0 * (1 - p) + Math.sin(p * Math.PI) * 1.5;
        const [sx, sy] = toScreen(x, y, z), [ex, ey] = toScreen(f.x1, f.y1, W.h(f.x1, f.y1));
        const a = Math.atan2(ey - sy, ex - sx); ctx.strokeStyle = '#2a1a0a'; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx - Math.cos(a) * 7 * k, sy - Math.sin(a) * 7 * k); ctx.stroke();
      } else if (f.kind === 'mark') {
        const [sx, sy] = toScreen(f.x, f.y, W.h(f.x, f.y)), r = (1 - f.t / f.life) * 12 * k;
        ctx.strokeStyle = f.color; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(sx, sy, r, r / 2, 0, 0, 7); ctx.stroke();
      }
    }
    // fog of war: black where never seen, dim where explored but not in sight
    const black = [], dim = [];
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const i = y * Wd + x; if (P.vis[i]) continue;
      (P.explored[i] ? dim : black).push(x, y);
    }
    const R = Wd + 1, hc = W.map.hc;
    const fill = (arr, style) => {
      if (!arr.length) return; ctx.fillStyle = style; ctx.beginPath();
      for (let j = 0; j < arr.length; j += 2) {
        const x = arr[j], y = arr[j + 1];
        const a = toScreen(x, y, hc[y * R + x]), b = toScreen(x + 1, y, hc[y * R + x + 1]), c = toScreen(x + 1, y + 1, hc[(y + 1) * R + x + 1]), d = toScreen(x, y + 1, hc[(y + 1) * R + x]);
        ctx.moveTo(a[0], a[1] - 1); ctx.lineTo(b[0] + 1, b[1]); ctx.lineTo(c[0], c[1] + 1); ctx.lineTo(d[0] - 1, d[1]); ctx.closePath();
      }
      ctx.fill();
    };
    const T3 = performance.now();
    fill(dim, 'rgba(0,0,0,0.42)'); fill(black, '#000');
    prof.ground = T1 - T0; prof.objects = T2 - T1; prof.fogscan = T3 - T2; prof.fog = performance.now() - T3; prof.n = list.length; prof.chunks = chunks.size; prof.rough = [...chunks.values()].filter(c => c.rough).length; prof.vis = (cx1 - cx0 + 1) * (cy1 - cy0 + 1);
    // overlays: rally point, placement ghost, drag box
    for (const id of selSet) { const b = W.get(id); if (b && b.kind === 'building' && b.rally && b.owner === 0) {
      const [sx, sy] = toScreen(b.rally.x, b.rally.y, W.h(b.rally.x, b.rally.y));
      ctx.strokeStyle = '#eee'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx, sy - 22 * k); ctx.stroke();
      ctx.fillStyle = W.players[0].color; ctx.fillRect(sx, sy - 22 * k, 10 * k, 7 * k); } }
    if (ui.ghost) for (const gh of ui.ghost) {
      const D = DATA.BUILDINGS[gh.type], s = D.size, ok = gh.ok;
      const pts = [[gh.tx, gh.ty], [gh.tx + s, gh.ty], [gh.tx + s, gh.ty + s], [gh.tx, gh.ty + s]].map(([x, y]) => toScreen(x, y, W.h(x, y)));
      ctx.fillStyle = ok ? 'rgba(80,255,120,0.28)' : 'rgba(255,60,60,0.35)'; ctx.beginPath(); ctx.moveTo(...pts[0]); for (const p of pts.slice(1)) ctx.lineTo(...p); ctx.closePath(); ctx.fill();
      const [sx, sy] = toScreen(gh.tx + s / 2, gh.ty + s / 2, W.h(gh.tx + s / 2, gh.ty + s / 2));
      blit(buildingSprite({ type: gh.type, size: s, built: true, food: DATA.FARM.food }, W.players[0].color), sx, sy, false, 0.55);
    }
    if (ui.box) { const [a, b, c, d] = ui.box; ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1; ctx.strokeRect(Math.min(a, c), Math.min(b, d), Math.abs(c - a), Math.abs(d - b));
      ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.fillRect(Math.min(a, c), Math.min(b, d), Math.abs(c - a), Math.abs(d - b)); }
    if (ctx.endFrame) ctx.endFrame();
  }

  /* ---------------- minimap (AoE2-style diamond) ---------------- */
  let mini, mctx, mbase, mimg, mT = 0;
  function initMini(cv) {
    mini = cv; mctx = cv.getContext('2d');
    const off = document.createElement('canvas'); off.width = W.W; off.height = W.H; mbase = off;
    mimg = off.getContext('2d').createImageData(W.W, W.H);
  }
  function drawMini(force) {
    if (!mini) return;
    mT -= 1; if (mT > 0 && !force) return; mT = 15;
    const d = mimg.data, P = W.players[0], m = W.map, Wd = W.W;
    for (let i = 0; i < Wd * W.H; i++) {
      let c;
      if (!P.explored[i]) c = [0, 0, 0];
      else { const n = m.node[i];
        c = n === 1 ? [40, 80, 34] : n === 2 ? [190, 60, 70] : n === 3 ? [170, 170, 160] : n === 4 ? [120, 150, 180] : n === 5 ? [98, 224, 255] : n === 6 ? [200, 225, 240] : TERR_COL[m.terr[i]];
        if (!P.vis[i]) c = c.map(v => v * 0.55); }
      d[i * 4] = c[0]; d[i * 4 + 1] = c[1]; d[i * 4 + 2] = c[2]; d[i * 4 + 3] = 255;
    }
    const dot = (x, y, s, col) => { for (let yy = y; yy < y + s; yy++) for (let xx = x; xx < x + s; xx++) { if (xx < 0 || yy < 0 || xx >= Wd || yy >= W.H) continue; const i = yy * Wd + xx; d[i * 4] = col[0]; d[i * 4 + 1] = col[1]; d[i * 4 + 2] = col[2]; } };
    const pc = [[80, 140, 255], [255, 70, 50], [235, 210, 90]];
    for (const g of P.seen.values()) dot(g.tx, g.ty, g.size, pc[g.owner].map(v => v * 0.7));
    for (const e of W.ents) {
      if (e.dead || e.garrisoned) continue; const i = Math.floor(e.y) * Wd + Math.floor(e.x);
      if (e.owner !== 0 && (e.kind === 'building' ? !W.seesRect(P, e) : !P.vis[i])) continue;
      if (e.kind === 'building') dot(e.tx, e.ty, e.size, pc[e.owner]);
      else if (e.kind === 'artifact') dot(Math.floor(e.x) - 1, Math.floor(e.y) - 1, 3, [255, 255, 255]);
      else if (!e.carcass) dot(Math.floor(e.x), Math.floor(e.y), 2, e.owner === 2 && e.D.creep ? [230, 60, 230] : pc[e.owner]);
    }
    mbase.getContext('2d').putImageData(mimg, 0, 0);
  }
  function blitMini(alerts, time) {
    if (!mini) return;
    const w = mini.width, h = mini.height, g = mctx;
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h);
    g.setTransform(w / (2 * W.W), h / (2 * W.H), -w / (2 * W.W), h / (2 * W.H), w / 2, 0);
    g.imageSmoothingEnabled = false; g.drawImage(mbase, 0, 0);
    const mp = (x, y) => [(x - y) / W.W * w / 2 + w / 2, (x + y) / W.H * h / 2];
    g.setTransform(1, 0, 0, 1, 0, 0);
    const c = [toWorld(0, 0), toWorld(vw, 0), toWorld(vw, vh), toWorld(0, vh)].map(([x, y]) => mp(x, y));
    g.strokeStyle = '#fff'; g.lineWidth = 1; g.beginPath(); g.moveTo(...c[0]); for (const p of c.slice(1)) g.lineTo(...p); g.closePath(); g.stroke();
    for (const a of alerts) if (time - a.t < 4) { const [x, y] = mp(a.x, a.y), r = 4 + ((time - a.t) * 10) % 12; g.strokeStyle = '#ff3030'; g.lineWidth = 2; g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke(); }
  }
  function miniToWorld(px, py) { const w = mini.width, h = mini.height, a = (px - w / 2) / (w / 2) * W.W, b = py / (h / 2) * W.H; return [(a + b) / 2, (b - a) / 2]; }

  const prof = {};
  return { prof, init, resize, draw, toScreen, toWorld, centerOn, clampCam, cam, initMini, drawMini, blitMini, miniToWorld, get vw() { return vw; }, get vh() { return vh; } };
})();
