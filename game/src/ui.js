/* ui.js: mouse, keyboard and the HUD. The standard RTS conveniences, done the way AoE2 DE does them:
   box select, double-click / ctrl-click for all of a type on screen, control groups (Ctrl+N, Shift+N, N, NN),
   shift-queued orders, smart right-click, rally points (on a resource = new villagers gather it), production
   queues (shift-click = 5, click the queue to cancel and refund), idle villager / idle military keys, Town Bell,
   building placement with shift to keep placing, drag-placed palisades, edge/arrow/middle-drag scrolling,
   wheel zoom, minimap clicks, attack alerts with a jump-to key, pause and game speed. */
'use strict';
const UI = (() => {
  let W, R, cv;
  const sel = { set: new Set(), list() { return [...this.set].map(id => W.get(id)).filter(Boolean); } };
  const st = { hoverId: 0, box: null, ghost: null, placing: null, wallStart: null, mode: null, menu: null,
    groups: {}, lastGroup: { n: -1, t: 0 }, lastClick: { id: 0, t: 0 }, mouse: [0, 0], keys: new Set(), idleIdx: 0, milIdx: 0,
    paused: false, speed: 1, drag: null, mid: null, lastAlertSeen: 0 };
  const $ = id => document.getElementById(id);

  function init(world, canvas) {
    W = world; R = Render; cv = canvas;
    cv.addEventListener('contextmenu', e => e.preventDefault());
    cv.addEventListener('pointerdown', down); cv.addEventListener('pointermove', move); cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
    cv.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') st.inside = false; });
    window.addEventListener('mousemove', e => { if (e.target !== cv) st.inside = false; });
    cv.addEventListener('wheel', wheel, { passive: false });
    window.addEventListener('keydown', key); window.addEventListener('keyup', e => st.keys.delete(e.key));
    window.addEventListener('blur', () => st.keys.clear());
    const mini = $('mini'); mini.addEventListener('contextmenu', e => e.preventDefault());
    mini.addEventListener('pointerdown', miniDown); mini.addEventListener('pointermove', miniMove);
    mini.addEventListener('pointerup', miniUp); mini.addEventListener('pointercancel', miniUp);
    window.addEventListener('resize', Mobile.apply);
    $('btn-pause').onclick = togglePause; $('btn-speed').onclick = () => setSpeed(st.speed >= 2 ? 0.5 : st.speed + 0.5);
    $('btn-idle').onclick = () => idleVillager(); $('btn-help').onclick = () => $('help').classList.toggle('show');
    $('help').onclick = () => $('help').classList.remove('show');
    buildTop(); Mobile.init();
  }

  /* ---------------- picking ---------------- */
  function pickEntity(px, py, touch) {
    let best = null, bd = 1e9; const k = R.cam.zoom, P = W.players[0], slop = touch ? 8 : 0;
    for (const e of W.ents) {
      if (e.dead || e.garrisoned || e.kind === 'building' || (e.kind === 'artifact' && e.carrier)) continue;
      const ti = Math.floor(e.y) * W.W + Math.floor(e.x); if (e.owner !== 0 && !P.vis[ti]) continue;
      const [sx, sy] = R.toScreen(e.x, e.y, W.h(e.x, e.y)), tall = (e.type === 'ogre' ? 52 : e.kind === 'artifact' ? 30 : 30) * k, half = (e.type === 'ogre' || e.type === 'scout' ? 16 : 11) * k;
      if (px < sx - half - slop || px > sx + half + slop || py < sy - tall - slop || py > sy + 6 * k + slop) continue;
      const d = Math.abs(px - sx) + Math.abs(py - (sy - tall / 2)) * 0.5 - (e.owner === 0 ? 4 : 0); if (d < bd) { bd = d; best = e; }
    }
    if (best) return best;
    const [wx, wy] = R.toWorld(px, py);
    for (const [ox, oy] of [[1, 1], [0, 0], [2, 2]]) {   // a building's walls rise above the tiles behind it
      const tx = Math.floor(wx + ox), ty = Math.floor(wy + oy); if (tx < 0 || ty < 0 || tx >= W.W || ty >= W.H) continue;
      const id = W.occ[ty * W.W + tx]; if (id) { const b = W.get(id); if (b && (b.owner === 0 || P.explored[ty * W.W + tx])) return b; }
    }
    return null;
  }
  function pickNode(px, py) {
    const [wx, wy] = R.toWorld(px, py), P = W.players[0];
    for (const [ox, oy] of [[1, 1], [0.5, 0.5], [0, 0]]) {
      const tx = Math.floor(wx + ox), ty = Math.floor(wy + oy); if (tx < 0 || ty < 0 || tx >= W.W || ty >= W.H) continue;
      const i = ty * W.W + tx; if (W.map.node[i] && P.explored[i]) return i;
    }
    return -1;
  }
  const own = e => e && e.owner === 0;
  const ownUnits = () => sel.list().filter(e => e.owner === 0 && e.kind === 'unit');

  /* ---------------- pointer: mouse and touch ----------------
     Touch follows Brass and Bone: tap selects (with units selected, tap orders them), double-tap selects that type
     on screen, hold then drag draws a box, hold a unit adds/removes it, hold empty ground deselects, drag pans,
     pinch zooms. Building on touch: tap pins the ghost, tap it again (or the rail's Place) builds. */
  const P = { down: false, touches: new Map(), pinch: null };
  const cpos = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  function down(e) {
    const [px, py] = cpos(e); st.mouse = [px, py]; hideTip();
    try { cv.setPointerCapture(e.pointerId); } catch (_) { }
    const touch = e.pointerType !== 'mouse';
    if (touch) {
      P.touches.set(e.pointerId, [px, py]);
      if (P.touches.size === 2) { const [a, b] = [...P.touches.values()];
        P.pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, z: R.cam.zoom, mx: (a[0] + b[0]) / 2, my: (a[1] + b[1]) / 2, cx: R.cam.x, cy: R.cam.y };
        P.down = false; clearTimeout(P.lp); st.box = null; st.wallStart = null; return; }
    }
    Object.assign(P, { down: true, touch, sx: px, sy: py, moved: false, lpDone: false, camx: R.cam.x, camy: R.cam.y, shift: e.shiftKey, ctrl: e.ctrlKey || e.metaKey });
    if (e.button === 1) { P.mode = 'pan'; e.preventDefault(); return; }
    if (e.button === 2) { P.down = false; if (st.placing || st.mode) { cancelModes(); return; } return rightClick(px, py, e.shiftKey); }
    if (st.placing) {
      const D = DATA.BUILDINGS[st.placing];
      if (D.wall || D.gate) { P.mode = 'wall'; st.wallStart = tileAt(px, py, 1); updateGhost(); return; }
      P.mode = 'place'; return;
    }
    if (st.mode === 'amove') { P.mode = 'amove'; return; }
    P.mode = touch ? (Mobile.box ? 'box' : 'tap') : 'box';
    if (P.mode === 'box') st.box = [px, py, px, py];
    clearTimeout(P.lp);
    if (P.mode === 'tap') P.lp = setTimeout(() => {   // hold: becomes a selection box
      if (P.down && P.mode === 'tap' && !P.moved && !P.pinch) { P.mode = 'box'; P.lpDone = true; st.box = [P.sx, P.sy, P.sx, P.sy];
        try { navigator.vibrate && navigator.vibrate(12); } catch (_) { } const [x, y] = R.toWorld(P.sx, P.sy); mark(x, y, '#ffd76a'); }
    }, 340);
  }
  function move(e) {
    const [px, py] = cpos(e); st.mouse = [px, py];
    if (e.pointerType === 'mouse') st.inside = true;
    if (P.touches.has(e.pointerId)) {
      P.touches.set(e.pointerId, [px, py]);
      if (P.pinch && P.touches.size === 2) {
        const [a, b] = [...P.touches.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]), mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, pc = P.pinch;
        const nz = Math.max(0.5, Math.min(1.75, pc.z * d / pc.d));
        R.cam.zoom = nz; R.cam.x = pc.cx + (pc.mx - R.vw / 2) / pc.z - (mx - R.vw / 2) / nz; R.cam.y = pc.cy + (pc.my - R.vh / 2) / pc.z - (my - R.vh / 2) / nz; R.clampCam();
        return;
      }
    }
    if (P.down) {
      if (Math.hypot(px - P.sx, py - P.sy) > 7) P.moved = true;
      const pan = P.mode === 'pan' || (P.mode === 'tap' && P.moved) || ((P.mode === 'place' || P.mode === 'amove') && P.touch && P.moved);
      if (pan) { R.cam.x = P.camx - (px - P.sx) / R.cam.zoom; R.cam.y = P.camy - (py - P.sy) / R.cam.zoom; R.clampCam(); }
      if (P.mode === 'box' && st.box) { st.box[2] = px; st.box[3] = py; }
    }
    if (e.pointerType === 'mouse') { const h = pickEntity(px, py); st.hoverId = h ? h.id : 0; }
    if (!(P.touch && st.placing && P.mode !== 'wall')) updateGhost();
  }
  function up(e) {
    if (P.touches.has(e.pointerId)) { P.touches.delete(e.pointerId); if (P.pinch) { if (P.touches.size < 2) P.pinch = null; P.down = false; return; } }
    if (!P.down) return; P.down = false; clearTimeout(P.lp);
    if (e.type === 'pointercancel') { st.box = null; return; }
    const [px, py] = cpos(e), shift = e.shiftKey || P.shift;
    switch (P.mode) {
      case 'pan': return;
      case 'wall': if (st.placing) placeWall(shift || (P.touch && Mobile.repeat)); return;
      case 'place':
        if (!P.touch) return placeAt(px, py, shift);
        if (P.moved) return;
        return Mobile.pinTap(px, py);
      case 'amove': {
        if (P.touch && P.moved) return;
        const [x, y] = R.toWorld(px, py); W.groupMove(ownUnits(), x, y, shift, true); mark(x, y, '#ff6040'); if (!shift) st.mode = null; refresh(); return; }
      case 'tap': if (!P.moved) tapAt(px, py); return;
      case 'box': {
        const box = st.box; st.box = null; if (P.touch) Mobile.box = false;
        if (!box) return;
        if (P.lpDone && !P.moved) {   // hold without dragging: toggle a unit, or deselect
          const t = pickEntity(px, py, true);
          if (t && t.owner === 0) { sel.set.has(t.id) ? sel.set.delete(t.id) : sel.set.add(t.id); } else sel.set.clear();
          st.menu = null; refresh(); return;
        }
        const [a, b, c, d] = box;
        if (Math.abs(c - a) < 5 && Math.abs(d - b) < 5) return clickSelect(a, b, shift, P.ctrl);
        const x0 = Math.min(a, c), x1 = Math.max(a, c), y0 = Math.min(b, d), y1 = Math.max(b, d);
        const inBox = W.ents.filter(u => !u.dead && u.kind === 'unit' && u.owner === 0 && !u.garrisoned && u.type !== 'sheep' && (() => {
          const [sx, sy] = R.toScreen(u.x, u.y, W.h(u.x, u.y)); return sx >= x0 && sx <= x1 && sy - 12 >= y0 - 10 && sy - 12 <= y1 + 10; })());
        if (!shift) sel.set.clear();
        for (const u of inBox.slice(0, 60)) sel.set.add(u.id);   // AoE2 DE selection limit 60
        st.menu = null; refresh(); return;
      }
    }
  }
  /* a tap on touch: select, or order what is selected (AoE2's right-click, on one finger) */
  function tapAt(px, py) {
    const t = pickEntity(px, py, true), node = t ? -1 : pickNode(px, py), units = ownUnits();
    const blds = sel.list().filter(e => e.owner === 0 && e.kind === 'building');
    if (units.length) {
      const vil = units.some(u => u.type === 'villager');
      const orderTarget = t && (t.owner !== 0 || (t.kind === 'artifact') ||
        (t.kind === 'building' && vil && (!t.built || t.type === 'farm' || t.hp < t.maxHp)) ||
        (t.kind === 'building' && units.some(u => u.artifact) && t.type === 'town_hall'));
      const selectable = t && t.owner === 0 && !orderTarget || (t && t.owner !== 0 && t.kind === 'building' && !units.length);
      if (selectable) return clickSelect(px, py, false, false);
      if (t && !orderTarget && t.owner === 2 && !(t.D && (t.D.creep || t.D.food))) return clickSelect(px, py, false, false);
      if (!t && node < 0 && Mobile.tapOrder === 'amove') { const [x, y] = R.toWorld(px, py); W.groupMove(units, x, y, false, true); mark(x, y, '#ff6040'); return; }
      return rightClick(px, py, false);
    }
    if (!t && blds.some(b => b.D.trains)) return rightClick(px, py, false);   // rally point
    clickSelect(px, py, false, false);
  }
  function clickSelect(px, py, shift, ctrl) {
    const e = pickEntity(px, py), now = performance.now();
    if (!e) { if (!shift) sel.set.clear(); const n = pickNode(px, py); st.nodeSel = n; st.menu = null; return refresh(); }
    st.nodeSel = -1;
    const dbl = st.lastClick.id === e.id && now - st.lastClick.t < 350; st.lastClick = { id: e.id, t: now };
    if ((dbl || ctrl) && e.owner === 0) { if (!shift) sel.set.clear(); for (const u of onScreen(x => x.type === e.type && x.owner === 0)) sel.set.add(u.id); }
    else if (shift && e.owner === 0 && [...sel.set].every(id => { const s = W.get(id); return s && s.owner === 0; })) { sel.set.has(e.id) ? sel.set.delete(e.id) : sel.set.add(e.id); }
    else { sel.set.clear(); sel.set.add(e.id); }
    st.menu = null; refresh();
  }
  function onScreen(pred) {
    return W.ents.filter(e => !e.dead && !e.garrisoned && pred(e) && (() => { const [sx, sy] = R.toScreen(e.x, e.y, W.h(e.x, e.y)); return sx > 0 && sy > 0 && sx < R.vw && sy < R.vh; })());
  }
  function rightClick(px, py, shift) {
    const [x, y] = R.toWorld(px, py), t = pickEntity(px, py), node = t ? -1 : pickNode(px, py);
    const units = ownUnits(), blds = sel.list().filter(e => e.owner === 0 && e.kind === 'building');
    if (units.length) {
      const movers = units.filter(u => !W.smartOrder(u, t, node, x, y, shift));
      if (movers.length) W.groupMove(movers, x, y, shift);
      mark(x, y, t && W.isHostile(units[0], t) ? '#ff4030' : node >= 0 || t ? '#ffd040' : '#40ff60');
    } else if (blds.length) {
      for (const b of blds) if (b.D.trains) b.rally = { x, y, id: t ? t.id : 0, node: node >= 0 ? node : undefined };
      mark(x, y, '#ffffff');
    }
  }
  function mark(x, y, color) { W.fx.push({ kind: 'mark', x, y, t: 0, life: 0.5, color }); }
  function wheel(e) {
    e.preventDefault();
    const before = R.toWorld(e.offsetX, e.offsetY);
    R.cam.zoom = Math.max(0.5, Math.min(1.75, R.cam.zoom * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
    const after = R.toWorld(e.offsetX, e.offsetY);
    const [ax, ay] = iso(before[0], before[1]), [bx, by] = iso(after[0], after[1]); R.cam.x += ax - bx; R.cam.y += ay - by; R.clampCam();
  }
  const MM = { drag: false, lp: 0 };
  function miniPt(e) { const m = $('mini'), r = m.getBoundingClientRect(), sx = m.width / r.width; return R.miniToWorld((e.clientX - r.left) * sx, (e.clientY - r.top) * sx); }
  function miniSend(x, y, shift) {
    const us = ownUnits(); if (us.length) { W.groupMove(us, x, y, shift, Mobile.tapOrder === 'amove' && e2touch); mark(x, y, '#40ff60'); return true; }
    let any = false; for (const b of sel.list()) if (b.owner === 0 && b.D.trains) { b.rally = { x, y }; any = true; } return any;
  }
  let e2touch = false;
  function miniDown(e) {
    e.preventDefault(); const [x, y] = miniPt(e); if (x < 0 || y < 0 || x > W.W || y > W.H) return;
    e2touch = e.pointerType !== 'mouse';
    if (e.button === 2) { miniSend(x, y, e.shiftKey); return; }
    try { $('mini').setPointerCapture(e.pointerId); } catch (_) { }
    MM.drag = true; MM.sx = e.clientX; MM.sy = e.clientY; R.centerOn(x, y); clearTimeout(MM.lp);
    if (e2touch && sel.set.size) MM.lp = setTimeout(() => {   // hold the minimap: send the selection there (Brass and Bone)
      if (MM.drag && miniSend(x, y, false)) { MM.drag = false; msg('Sent.'); try { navigator.vibrate && navigator.vibrate(15); } catch (_) { } } }, 420);
  }
  function miniMove(e) { if (!MM.drag) return; if (Math.hypot(e.clientX - MM.sx, e.clientY - MM.sy) > 8) clearTimeout(MM.lp); const [x, y] = miniPt(e); R.centerOn(x, y); }
  function miniUp() { MM.drag = false; clearTimeout(MM.lp); }

  /* ---------------- placement ---------------- */
  function tileAt(px, py, s) { const [x, y] = R.toWorld(px, py); return [Math.round(x - s / 2), Math.round(y - s / 2)]; }
  function startPlacing(type) {
    const D = DATA.BUILDINGS[type];
    if (D.needs && !W.has(0, D.needs)) return msg(`Needs a ${DATA.BUILDINGS[D.needs].name} first.`);
    if (!W.canAfford(0, D.cost)) return msg(`Not enough resources for a ${D.name}.`);
    st.placing = type; st.menu = 'build'; Mobile.pin = null; if (Mobile.on) Mobile.startPin(); updateGhost(); refresh();
  }
  function wallLine(a, b) {   // straight or diagonal, the way AoE2 lays palisades
    const out = [], dx = b[0] - a[0], dy = b[1] - a[1], n = Math.max(Math.abs(dx), Math.abs(dy));
    for (let k = 0; k <= n; k++) out.push([a[0] + Math.round(dx * k / (n || 1)), a[1] + Math.round(dy * k / (n || 1))]);
    return out;
  }
  function updateGhost() {
    if (!st.placing) { st.ghost = null; return; }
    const D = DATA.BUILDINGS[st.placing], [px, py] = st.mouse;
    if ((D.wall || D.gate) && st.wallStart) {
      const tiles = wallLine(st.wallStart, tileAt(px, py, 1)); let wood = W.players[0].res.wood;
      st.ghost = tiles.map(([tx, ty]) => { wood -= D.cost.wood; return { type: st.placing, tx, ty, ok: wood >= 0 && W.canPlace(st.placing, 0, tx, ty) }; });
      return;
    }
    const [tx, ty] = Mobile.pin || tileAt(px, py, D.size);
    if (Mobile.on && !Mobile.pin && !(st.inside && !P.touch)) { st.ghost = null; return; }
    st.ghost = [{ type: st.placing, tx, ty, ok: W.canPlace(st.placing, 0, tx, ty) && W.canAfford(0, D.cost) }];
  }
  function builders() { return ownUnits().filter(u => u.type === 'villager'); }
  function placeAt(px, py, shift, tile) {
    const D = DATA.BUILDINGS[st.placing], [tx, ty] = tile || tileAt(px, py, D.size);
    const b = W.place(st.placing, 0, tx, ty);
    if (!b) return msg(W.canAfford(0, D.cost) ? 'Cannot build there.' : 'Not enough resources.');
    for (const u of builders()) W.order(u, { type: 'build', id: b.id }, shift);
    Mobile.pin = null;
    if (!shift) { st.placing = null; st.ghost = null; st.menu = null; } else updateGhost(); refresh();
    return b;
  }
  function placeWall(shift) {
    const D = DATA.BUILDINGS[st.placing], tiles = wallLine(st.wallStart, tileAt(...st.mouse, 1)); st.wallStart = null;
    const placed = []; for (const [tx, ty] of tiles) { const b = W.place(st.placing, 0, tx, ty); if (b) placed.push(b); }
    if (!placed.length) msg('Cannot build there.');
    const bs = builders();
    placed.forEach((b, k) => { for (const u of bs) W.order(u, { type: 'build', id: b.id }, shift || k > 0); });
    if (!shift) { st.placing = null; st.ghost = null; st.menu = null; }
    void D; refresh();
  }
  function cancelModes() { st.placing = null; st.ghost = null; st.wallStart = null; st.mode = null; Mobile.pin = null; refresh(); }


  /* ---------------- mobile interface (after Brass and Bone) ----------------
     Auto turns on below 900 px wide (or on a touch screen up to 1100 px); F1 lets the player force Mobile or Desktop.
     A rail of big buttons on the right, five group slots in the top bar, a pinned building ghost. */
  const ICON = {
    build: '<path d="M4 20h16M6 20V10l6-5 6 5v10M10 20v-5h4v5"/>', box: '<rect x="4.5" y="5.5" width="15" height="13" stroke-dasharray="3 2.6"/>',
    idle: '<circle cx="12" cy="7" r="3"/><path d="M6.5 20c0-4 2.5-7 5.5-7s5.5 3 5.5 7"/><path d="M18 4l2 0M19 3v2" />',
    army: '<path d="M5 19L17 7M14 5l5 0 0 5M5 15l4 4"/>', screen: '<path d="M4 8V4.5h3.5M20 8V4.5h-3.5M4 16v3.5h3.5M20 16v3.5h-3.5"/><circle cx="9" cy="12" r="1.7"/><circle cx="15" cy="12" r="1.7"/>',
    move: '<path d="M5 12h13M13 6.5l5.5 5.5-5.5 5.5"/>', amove: '<path d="M5 19L17 7M13 6h5v5"/><circle cx="8" cy="8" r="2.5"/>',
    clear: '<path d="M6 6l12 12M18 6L6 18"/>', map: '<path d="M4 6.5l5.5-2 5 2 5.5-2v13l-5.5 2-5-2-5.5 2zM9.5 4.5v13M14.5 6.5v13"/>',
    here: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', repeat: '<path d="M17 4l3 3-3 3M20 7H8a4 4 0 0 0-4 4M7 20l-3-3 3-3M4 17h12a4 4 0 0 0 4-4"/>',
  };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (_) { } } };
  const Mobile = {
    on: false, box: false, repeat: false, tapOrder: 'move', pin: null, layout: 'auto', lgT: 0, lg: false, lastSlot: { n: 0, t: 0 },
    want() {
      if (this.layout === 'mobile') return true; if (this.layout === 'desktop') return false;
      const coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches;
      return window.innerWidth <= 900 || (coarse && window.innerWidth <= 1100);
    },
    init() {
      this.layout = store.get('rf-layout') || 'auto';
      $('mrail').addEventListener('click', e => { const b = e.target.closest('[data-r]'); if (b) this.act(b.dataset.r); });
      const mg = $('mgroups');
      mg.addEventListener('contextmenu', e => e.preventDefault());
      mg.addEventListener('pointerdown', e => { const b = e.target.closest('[data-g]'); if (!b) return; this.lg = false; clearTimeout(this.lgT);
        this.lgT = setTimeout(() => { if (sel.set.size) { this.lg = true; st.groups[+b.dataset.g] = [...sel.set]; msg(`Group ${b.dataset.g} saved.`); this.groups(); try { navigator.vibrate && navigator.vibrate(15); } catch (_) { } } }, 480); });
      for (const t of ['pointerup', 'pointercancel', 'pointerleave']) mg.addEventListener(t, () => clearTimeout(this.lgT));
      mg.addEventListener('click', e => { const b = e.target.closest('[data-g]'); if (!b) return; if (this.lg) { this.lg = false; return; }
        const n = +b.dataset.g, g = (st.groups[n] || []).filter(id => W.get(id));
        if (g.length) { sel.set = new Set(g); st.menu = null; const now = performance.now();
          if (this.lastSlot.n === n && now - this.lastSlot.t < 450) { const u = W.get(g[0]); R.centerOn(u.x, u.y); } this.lastSlot = { n, t: now }; refresh(); }
        else if (sel.set.size) { st.groups[n] = [...sel.set]; msg(`Group ${n} saved.`); this.groups(); }
        else msg('Select something first, then tap a slot to save it.'); });
      $('layout').addEventListener('click', e => { e.stopPropagation(); const b = e.target.closest('[data-v]'); if (!b) return; this.layout = b.dataset.v; store.set('rf-layout', this.layout); this.apply(); });
      this.apply();
    },
    apply() {
      const on = Mobile.want(); Mobile.on = on; document.body.classList.toggle('mui', on);
      document.querySelectorAll('#layout [data-v]').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === Mobile.layout));
      requestAnimationFrame(() => { R.resize(); }); Mobile.rail(); Mobile.groups(); refresh();
    },
    groups() {
      if (!this.on) return; let h = '';
      for (let n = 1; n <= 5; n++) { const c = (st.groups[n] || []).filter(id => W.get(id)).length; h += `<button class="mg${c ? ' on' : ''}" data-g="${n}"><b>${n}</b>${c || ''}</button>`; }
      const el = $('mgroups'); if (el._h !== h) { el._h = h; el.innerHTML = h; }
    },
    rail() {
      if (!this.on) return;
      const rb = (a, label, cls) => `<button class="rb${cls ? ' ' + cls : ''}" data-r="${a}"><svg viewBox="0 0 24 24">${ICON[a]}</svg>${label}</button>`;
      const has = sel.set.size > 0, units = ownUnits().length > 0; let h = '';
      if (st.placing) {
        const g = st.ghost && st.ghost[0], D = DATA.BUILDINGS[st.placing];
        if (!(D.wall || D.gate)) h += rb('here', 'Place', this.pin ? (g && g.ok ? 'go2' : 'off') : 'off');
        h += rb('repeat', 'Repeat', this.repeat ? 'on' : '') + rb('clear', 'Cancel');
      } else {
        h += rb('build', 'Build', st.menu === 'build' ? 'on' : '') + rb('box', 'Box', this.box ? 'on' : '') + rb('idle', 'Idle') + rb('army', 'Army') + rb('screen', 'Screen');
        if (units) h += this.tapOrder === 'move' ? rb('move', 'Move') : rb('amove', 'Attack', 'on');
        if (has) h += rb('clear', 'Clear');
        h += rb('map', 'Map', document.body.classList.contains('m-mapoff') ? '' : 'on');
      }
      const el = $('mrail'); if (el._h !== h) { el._h = h; el.innerHTML = h; }
    },
    act(a) {
      if (a === 'build') {
        if (st.menu === 'build') { st.menu = null; return refresh(); }
        let v = ownUnits().filter(u => u.type === 'villager');
        if (!v.length) {   // no peasant selected: take an idle one, else the nearest to the middle of the screen
          const [cx, cy] = R.toWorld(R.vw / 2, R.vh / 2), all = W.ents.filter(u => !u.dead && u.owner === 0 && u.type === 'villager' && !u.garrisoned);
          const idle = all.filter(u => !u.order), pool = idle.length ? idle : all;
          pool.sort((a, b) => Math.hypot(a.x - cx, a.y - cy) - Math.hypot(b.x - cx, b.y - cy));
          if (!pool.length) return msg('No peasants.'); sel.set = new Set([pool[0].id]); msg('Building with the nearest peasant.');
        }
        st.menu = 'build'; return refresh();
      }
      if (a === 'box') { this.box = !this.box; if (this.box) msg('Drag on the map to select.'); return this.rail(); }
      if (a === 'idle') return idleVillager();
      if (a === 'army') { const us = W.ents.filter(u => !u.dead && u.owner === 0 && u.kind === 'unit' && DATA.UNITS[u.type] && u.type !== 'villager' && !u.garrisoned);
        if (!us.length) return msg('No military.'); sel.set = new Set(us.slice(0, 60).map(u => u.id)); st.menu = null; return refresh(); }
      if (a === 'screen') { const us = onScreen(u => u.owner === 0 && u.kind === 'unit' && u.type !== 'sheep'); if (!us.length) return msg('None of your units on screen.');
        sel.set = new Set(us.slice(0, 60).map(u => u.id)); st.menu = null; return refresh(); }
      if (a === 'move' || a === 'amove') { this.tapOrder = this.tapOrder === 'move' ? 'amove' : 'move'; msg(this.tapOrder === 'move' ? 'Tap the ground: move.' : 'Tap the ground: attack-move.'); return this.rail(); }
      if (a === 'clear') { if (st.placing || st.mode) return cancelModes(); sel.set.clear(); st.menu = null; return refresh(); }
      if (a === 'map') { document.body.classList.toggle('m-mapoff'); return this.rail(); }
      if (a === 'repeat') { this.repeat = !this.repeat; return this.rail(); }
      if (a === 'here') { if (this.pin) placeAt(0, 0, this.repeat, this.pin); return this.rail(); }
    },
    startPin() {   // a new building: pin the ghost in the middle of the screen
      const D = DATA.BUILDINGS[st.placing]; if (D.wall || D.gate) { this.pin = null; msg('Drag on the map to lay the line.'); return; }
      this.pin = tileAt(R.vw / 2, R.vh / 2, D.size); updateGhost(); this.rail();
    },
    pinTap(px, py) {
      const D = DATA.BUILDINGS[st.placing], t = tileAt(px, py, D.size), [wx, wy] = R.toWorld(px, py), p = this.pin;
      if (p && wx >= p[0] && wx < p[0] + D.size && wy >= p[1] && wy < p[1] + D.size) placeAt(0, 0, this.repeat, p);
      else { this.pin = t; updateGhost(); }
      this.rail();
    },
  };

  /* ---------------- keyboard ---------------- */
  function key(e) {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key; st.keys.add(k);
    if (/^[0-9]$/.test(k)) {
      const n = +k;
      if (e.ctrlKey) { st.groups[n] = [...sel.set]; msg(`Group ${n} set.`); e.preventDefault(); return; }
      if (e.shiftKey) { st.groups[n] = [...new Set([...(st.groups[n] || []), ...sel.set])]; return; }
      const g = (st.groups[n] || []).filter(id => W.get(id)); if (!g.length) return;
      sel.set = new Set(g); st.menu = null;
      const now = performance.now(); if (st.lastGroup.n === n && now - st.lastGroup.t < 400) { const u = W.get(g[0]); R.centerOn(u.x, u.y); }
      st.lastGroup = { n, t: now }; refresh(); return;
    }
    if (k === 'F3' || k === 'p' && e.ctrlKey) { e.preventDefault(); return togglePause(); }
    if (k === 'F1' || k === '?') { e.preventDefault(); return $('help').classList.toggle('show'); }
    if (k === '+' || k === '=') return setSpeed(Math.min(2, st.speed + 0.5));
    if (k === '-' || k === '_') return setSpeed(Math.max(0.5, st.speed - 0.5));
    if (k === 'Escape') { if (st.placing || st.mode) return cancelModes(); if (st.menu) { st.menu = null; return refresh(); } sel.set.clear(); return refresh(); }
    if (k === '.') return idleVillager();
    if (k === ',') return idleMilitary();
    if (k === ' ' ) { e.preventDefault(); const a = W.alerts[W.alerts.length - 1] || W.messages.filter(m => m.x !== undefined).pop(); if (a) R.centerOn(a.x, a.y); return; }
    if (k === 'Delete') { for (const x of sel.list()) if (x.owner === 0) { if (x.kind === 'building' && !x.built) W.pay(0, x.D.cost, -1); W.kill(x); } sel.set.clear(); return refresh(); }
    if ((k === 'h' || k === 'H') && !e.ctrlKey && !st.menu) {
      const halls = W.ents.filter(b => !b.dead && b.owner === 0 && b.type === 'town_hall'); if (!halls.length) return;
      const cur = sel.list()[0], i = cur && cur.type === 'town_hall' ? (halls.indexOf(cur) + 1) % halls.length : 0;
      sel.set = new Set([halls[i].id]); R.centerOn(halls[i].x, halls[i].y); return refresh();
    }
    // the command grid: Q W E R T / A S D F G / Z X C V B
    const b = [...document.querySelectorAll('#cmds button')].find(x => x.dataset.key === k.toUpperCase() && !x.disabled);
    if (b && !e.ctrlKey && !e.altKey) { e.preventDefault(); b.dispatchEvent(new MouseEvent('click', { shiftKey: e.shiftKey })); }
  }
  function idleVillager() {
    const idle = W.ents.filter(u => !u.dead && u.owner === 0 && u.type === 'villager' && !u.order && !u.garrisoned);
    if (!idle.length) return msg('No idle peasants.');
    const u = idle[st.idleIdx++ % idle.length]; sel.set = new Set([u.id]); R.centerOn(u.x, u.y); st.menu = null; refresh();
  }
  function idleMilitary() {
    const idle = W.ents.filter(u => !u.dead && u.owner === 0 && u.kind === 'unit' && DATA.UNITS[u.type] && u.type !== 'villager' && !u.order && !u.garrisoned);
    if (!idle.length) return msg('No idle military.');
    const u = idle[st.milIdx++ % idle.length]; sel.set = new Set([u.id]); R.centerOn(u.x, u.y); st.menu = null; refresh();
  }
  function togglePause() { st.paused = !st.paused; $('btn-pause').textContent = st.paused ? '▶' : '❚❚'; $('paused').style.display = st.paused ? 'flex' : 'none'; }
  function setSpeed(s) { st.speed = s; $('btn-speed').textContent = s.toFixed(1) + 'x'; }

  /* edge and arrow-key scrolling */
  function scroll(dt) {
    let dx = 0, dy = 0; const [mx, my] = st.mouse, edge = 6, sp = 900 * dt / R.cam.zoom;
    if (st.keys.has('ArrowLeft') || (st.inside && mx < edge)) dx -= sp;
    if (st.keys.has('ArrowRight') || (st.inside && mx > R.vw - edge)) dx += sp;
    if (st.keys.has('ArrowUp') || (st.inside && my < edge)) dy -= sp;
    if (st.keys.has('ArrowDown') || (st.inside && my > R.vh - edge)) dy += sp;
    if (dx || dy) { R.cam.x += dx; R.cam.y += dy; R.clampCam(); updateGhost(); }
  }

  /* ---------------- HUD ---------------- */
  function msg(text) { W.messages.push({ text, t: W.time }); }
  function costHtml(c) { return Object.entries(c).map(([k, v]) => `<span class="cost"><i style="background:${DATA.RES_INFO[k].color}"></i>${v}</span>`).join(' '); }
  function buildTop() {
    $('res').innerHTML = DATA.RES.map(r => `<div class="r" title="${DATA.RES_INFO[r].name}${DATA.RES_INFO[r].basic ? '' : ' (premium)'}"><i style="background:${DATA.RES_INFO[r].color}"></i><b id="r-${r}">0</b><small id="v-${r}"></small></div>`).join('') +
      `<div class="r" title="Population"><i class="pop"></i><b id="r-pop">0/0</b></div>`;
  }
  function button(key, label, tip, onclick, opts = {}) {
    const b = document.createElement('button'); b.dataset.key = key;
    b.innerHTML = `<span class="lbl">${label}</span>${opts.cost ? `<span class="cst">${Object.entries(opts.cost).map(([k, v]) => `<i style="background:${DATA.RES_INFO[k].color}"></i>${v}`).join(' ')}</span>` : ''}<span class="hk">${key}</span>`;
    b.disabled = !!opts.disabled; if (opts.cls) b.className = opts.cls;
    b.onclick = ev => { if (b._lp) { b._lp = false; return; } hideTip(); onclick(ev); };
    b.onmouseenter = () => tip && !Mobile.on && showTip(b, tip); b.onmouseleave = () => { if (!b._lp) hideTip(); };
    b.addEventListener('pointerdown', e => { if (e.pointerType === 'mouse' || !tip) return; clearTimeout(b._t); b._t = setTimeout(() => { b._lp = true; showTip(b, tip); setTimeout(hideTip, 2500); }, 450); });
    for (const t of ['pointerup', 'pointercancel']) b.addEventListener(t, () => clearTimeout(b._t));
    b.addEventListener('contextmenu', e => e.preventDefault());
    return b;
  }
  function showTip(b, html) { const t = $('tip'); t.innerHTML = html; t.style.display = 'block'; const r = b.getBoundingClientRect(); t.style.left = r.left + 'px'; t.style.bottom = (window.innerHeight - r.top + 6) + 'px'; }
  function hideTip() { $('tip').style.display = 'none'; }
  const GRID = ['Q', 'W', 'E', 'R', 'T', 'A', 'S', 'D', 'F', 'G', 'Z', 'X', 'C', 'V', 'B', 'N', 'U'];

  function refresh() {
    const cmds = $('cmds'); cmds.innerHTML = ''; hideTip();
    const list = sel.list(), mine = list.filter(own), units = mine.filter(e => e.kind === 'unit'), blds = mine.filter(e => e.kind === 'building');
    const add = b => cmds.appendChild(b);
    if (units.length) {
      const vils = units.filter(u => u.type === 'villager');
      if (vils.length && st.menu === 'build') {
        DATA.BUILD_MENU.forEach(t => { const D = DATA.BUILDINGS[t], need = D.needs && !W.has(0, D.needs);
          add(button(D.hotkey, D.name, `<b>${D.name}</b> ${costHtml(D.cost)}<br>${D.tip}${need ? `<br><em>Needs a ${DATA.BUILDINGS[D.needs].name}.</em>` : ''}`, () => startPlacing(t), { disabled: need, cls: st.placing === t ? 'on' : '', cost: D.cost })); });
        add(button('X', '◀ Back', 'Back (Esc)', () => { st.menu = null; cancelModes(); }));
      } else {
        if (vils.length) add(button('Q', 'Build', '<b>Build</b><br>Economic and military buildings', () => { st.menu = 'build'; refresh(); }));
        if (units.some(u => u.type !== 'villager' && u.type !== 'sheep')) add(button('A', 'Attack-move', '<b>Attack-move</b><br>Click a destination; units fight anything on the way.', () => { st.mode = 'amove'; msg('Attack-move: click a destination.'); }));
        add(button('S', 'Stop', '<b>Stop</b>', () => { for (const u of units) { u.queue = []; W.setOrder(u, null); } }));
        if (units.some(u => u.D.carries) && W.ents.some(a => !a.dead && a.kind === 'artifact' && !a.carrier && W.players[0].vis[Math.floor(a.y) * W.W + Math.floor(a.x)]))
          add(button('D', 'Get artifact', '<b>Pick up the nearest visible artifact</b>', () => { for (const u of units.filter(u => u.D.carries)) { const a = W.nearest(u, a => a.kind === 'artifact' && !a.carrier && W.players[0].vis[Math.floor(a.y) * W.W + Math.floor(a.x)]); if (a) W.order(u, { type: 'pickup', id: a.id }); } }));
        add(button('G', 'Garrison', '<b>Garrison</b> in the nearest Town Hall', () => { for (const u of units) { const th = W.nearest(u, b => b.kind === 'building' && b.owner === 0 && b.type === 'town_hall' && b.built); if (th && (u.type === 'villager' || u.D.cls && u.D.cls.includes('infantry'))) W.order(u, { type: 'garrison', id: th.id }); } }));
        add(button('V', 'Delete', '<b>Delete</b> (Del)', () => { for (const u of units) W.kill(u); sel.set.clear(); refresh(); }));
      }
    } else if (blds.length === 1 || (blds.length && blds.every(b => b.type === blds[0].type))) {
      const b = blds[0], D = b.D;
      if (b.built) {
        for (const t of D.trains || []) { const U = DATA.UNITS[t];
          add(button(U.hotkey, `Train ${U.name}`, `<b>${U.name}</b> ${costHtml(U.cost)} · ${U.time}s<br>${U.tip}<br><em>Shift-click: 5</em>`, ev => { let n = 0; for (const x of blds) n += W.queueTrain(x, t, ev.shiftKey ? 5 : 1); if (!n) msg(W.players[0].pop >= W.players[0].popCap ? 'Need more housing.' : 'Not enough resources.'); refresh(); }, { cost: U.cost })); }
        for (const t of D.researches || []) { const T = DATA.TECHS[t], done = W.players[0].techs.has(t), busy = W.ents.some(e => !e.dead && e.kind === 'building' && e.owner === 0 && e.queue.some(q => q.what === t));
          if (done) continue;
          add(button(T.hotkey, T.name, `<b>${T.name}</b> ${costHtml(T.cost)} · ${T.time}s<br>${T.tip}`, () => { if (!W.queueTech(b, t)) msg('Cannot research that now.'); refresh(); }, { disabled: T.locked || busy, cls: T.locked ? 'locked' : '', cost: T.cost })); }
        if (b.type === 'town_hall') {
          add(button('B', 'Town Bell', '<b>Ring the Town Bell</b><br>Every peasant runs to a Town Hall and hides; its arrows grow. (AoE2 Town Bell)', () => { W.townBell(0); msg('Town Bell rung!'); }));
          add(button('N', 'All Clear', '<b>All Clear</b><br>Everyone back to work.', () => W.allClear(0)));
        }
        if (b.garrison.length) add(button('U', 'Ungarrison', '<b>Ungarrison</b> all', () => { W.ungarrison(b); refresh(); }));
      }
      add(button('V', 'Delete', '<b>Delete</b> (Del)', () => { for (const x of blds) { if (!x.built) W.pay(0, x.D.cost, -1); W.kill(x); } sel.set.clear(); refresh(); }));
    }
    // order buttons in grid order
    const bs = [...cmds.children].sort((a, b) => GRID.indexOf(a.dataset.key) - GRID.indexOf(b.dataset.key));
    cmds.innerHTML = ''; for (const b of bs) cmds.appendChild(b);
    Mobile.rail(); Mobile.groups();
    info();
  }
  let infoKey = '';
  function info() {
    const list = sel.list(), el = $('info');
    if (!list.length) {
      if (st.nodeSel >= 0 && W.map.node[st.nodeSel]) {
        const k = MapGen.NODE_KEY[W.map.node[st.nodeSel]], c = W.wardedBy(st.nodeSel);
        el.innerHTML = `<h3>${DATA.NODES[k].name}</h3><p>${Math.ceil(W.map.amt[st.nodeSel])} ${k === 'tree' ? 'wood' : DATA.NODES[k].res} left</p>${c ? `<p class="warn">Warded by the ${DATA.CAMPS[c.type].name}. Clear it to mine here.</p>` : ''}`;
      } else el.innerHTML = '<p class="dim">Select something. <b>F1</b> lists the hotkeys.</p>';
      return;
    }
    if (list.length > 1) {
      el.innerHTML = `<h3>${list.length} selected</h3><div class="multi">` + list.map(e => `<span class="ic" data-id="${e.id}" title="${e.D.name}" style="--c:${W.players[e.owner].color}">${e.D.name.slice(0, 2)}<i style="width:${100 * e.hp / e.maxHp}%"></i></span>`).join('') + '</div>';
      el.querySelectorAll('.ic').forEach(s => s.onclick = ev => { if (ev.shiftKey) sel.set.delete(+s.dataset.id); else sel.set = new Set([+s.dataset.id]); refresh(); });
      return;
    }
    const e = list[0], D = e.D, P = W.players[e.owner];
    let h = `<h3>${D.name}${e.owner === 1 ? ' <small>(enemy)</small>' : e.owner === 2 && D.creep ? ' <small>(creep)</small>' : ''}</h3>`;
    if (e.kind !== 'artifact') h += `<div class="hp"><i style="width:${100 * e.hp / e.maxHp}%"></i><span>${Math.ceil(e.hp)} / ${e.maxHp}</span></div>`;
    if (e.kind === 'unit') {
      if (e.carcass) h += `<p>${Math.ceil(e.food)} food left</p>`;
      else {
        const arm = [(D.armor || [0, 0])[0] + W.armorBonus(e, false), (D.armor || [0, 0])[1] + W.armorBonus(e, true)];
        h += `<p class="stats">⚔ ${D.atk || 0} &nbsp; 🛡 ${arm[0]}/${arm[1]} &nbsp; 👁 ${D.los} &nbsp; ➜ ${D.speed}</p>`;
        if (e.type === 'villager') h += `<p>${e.carry.amt >= 0.5 ? `Carrying ${Math.floor(e.carry.amt)} ${e.carry.res}` : ''} ${e.order ? '· ' + taskName(e) : '· idle'}</p>`;
        if (e.artifact) h += '<p>Carrying an artifact: bring it to a Town Hall.</p>';
        if (D.food && !e.carcass) h += `<p>${D.food} food</p>`;
        if (e.camp !== undefined) { const c = W.campById(e.camp); h += `<p class="dim">Guards the ${DATA.CAMPS[c.type].name}.</p>`; }
      }
    } else if (e.kind === 'building') {
      if (!e.built) h += `<p>Under construction: ${Math.floor(e.progress * 100)}%</p>`;
      if (e.type === 'farm') h += `<p>${Math.ceil(e.food)} food left</p>`;
      if (D.garrison) h += `<p>Garrison ${e.garrison.length}/${D.garrison}${e.artifacts ? ` · Artifacts ${e.artifacts} (+${(e.artifacts * DATA.ARTIFACT_RATE).toFixed(1)} crystal/s)` : ''}</p>`;
      if (D.drop) h += `<p class="dim">Drop-off: ${D.drop.join(', ')}</p>`;
      if (e.queue.length) {
        h += '<div class="queue">' + e.queue.map((q, i) => `<span class="q" data-i="${i}" title="Click to cancel">${(q.kind === 'tech' ? DATA.TECHS : DATA.UNITS)[q.what].name.slice(0, 3)}${i === 0 ? `<i style="width:${100 * q.t / q.time}%"></i>` : ''}</span>`).join('') + '</div>';
        if (e.queue[0].housed) h += '<p class="warn">Need more housing (build a Cottage).</p>';
      }
    } else h += '<p>An artifact. Militia can carry it to your Town Hall for +0.5 crystal/s.</p>';
    const key = h; if (key !== infoKey) { el.innerHTML = h; infoKey = key;
      el.querySelectorAll('.q').forEach(s => s.onclick = () => { W.cancel(e, +s.dataset.i); refresh(); }); }
  }
  function taskName(u) {
    const o = u.order; if (!o) return 'idle';
    if (o.type === 'gather') { const r = u.lastGather && u.lastGather.res; return { food: 'gathering food', wood: 'chopping wood', stone: 'mining stone', iron: 'mining iron', crystal: 'mining crystal' }[r] || 'gathering'; }
    return { build: 'building', repair: 'repairing', dropoff: 'dropping off', move: 'moving', amove: 'attack-moving', attack: 'attacking', garrison: 'garrisoning', pickup: 'fetching artifact', deliver: 'delivering artifact' }[o.type] || o.type;
  }

  function frame(dt) {
    scroll(dt);
    // drop dead entities from the selection
    let changed = false; for (const id of sel.set) if (!W.get(id) || W.get(id).garrisoned) { sel.set.delete(id); changed = true; }
    if (changed) refresh();
    const P = W.players[0];
    for (const r of DATA.RES) $('r-' + r).textContent = Math.floor(P.res[r]);
    const on = { food: 0, wood: 0, stone: 0, iron: 0, crystal: 0 }; let idle = 0;
    for (const u of W.ents) if (!u.dead && u.owner === 0 && u.type === 'villager') { if (!u.order && !u.garrisoned) idle++; else if (u.order && (u.order.type === 'gather' || u.order.type === 'dropoff') && u.lastGather) on[u.lastGather.res]++; }
    for (const r of DATA.RES) $('v-' + r).textContent = on[r] ? on[r] : '';
    const pe = $('r-pop'); pe.textContent = `${P.pop}/${P.popCap}`; pe.className = P.pop >= P.popCap ? 'capped' : '';
    $('btn-idle').textContent = `Idle ${idle}`; $('btn-idle').className = idle ? 'hot' : '';
    const t = Math.floor(W.time); $('clock').textContent = `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
    // messages and alerts
    const m = $('msgs'), recent = [...W.messages.filter(x => W.time - x.t < 7), ...W.alerts.filter(a => W.time - a.t < 5).map(a => ({ text: a.text, t: a.t, alert: true }))].sort((a, b) => a.t - b.t).slice(-5);
    m.innerHTML = recent.map(x => `<div class="${x.alert ? 'alert' : ''}">${x.text}</div>`).join('');
    if (sel.set.size) info(); else if (st.nodeSel >= 0) info();
    if (Mobile.on) { Mobile.rail(); Mobile.groups(); }
    if (W.state !== 'playing' && !st.ended) { st.ended = true; $('end').style.display = 'flex'; $('end-text').textContent = W.state === 'victory' ? 'Victory' : 'Defeat'; }
  }
  return { init, frame, refresh, sel, st, msg, startPlacing, Mobile };
})();
