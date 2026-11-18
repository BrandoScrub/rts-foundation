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
    $('btn-help').onclick = () => $('help').classList.toggle('show');
    $('help').onclick = () => $('help').classList.remove('show');
    $('btn-menu').onclick = () => openMenu(true); $('btn-tree').onclick = () => openTree(true); $('tree').onclick = () => openTree(false);
    $('menu').onclick = e => { if (e.target.id === 'menu') openMenu(false); };
    $('menu').querySelectorAll('[data-a]').forEach(b => b.onclick = () => { const a = b.dataset.a; openMenu(false);
      if (a === 'tree') openTree(true); else if (a === 'help') $('help').classList.add('show'); else if (a === 'restart') location.reload();
      else if (a === 'resign') { st.ended = true; $('end').style.display = 'flex'; $('end-text').textContent = 'Defeat'; } });
    $('btn-mode').onclick = () => { st.miniMode = ((st.miniMode || 0) + 1) % 3; msg('Mini-map: ' + ['everything', 'economy', 'military'][st.miniMode] + '.'); R.drawMini(true); };
    $('btn-idlemil').onclick = () => idleMilitary();
    buildTop(); Mobile.init();
    fetch('art/icons.json').then(r => r.json()).then(j => { IC = j; st.ageShown = 0; buildTop(); refresh(); }).catch(() => { });
  }

  /* ---------------- picking ---------------- */
  /* Picking works in screen space against what is drawn: a unit by its body, a building by its silhouette (the
     footprint and the same footprint raised to the roof), a tree or mine by its sprite. A finger gets more slack. */
  const BH = { town_hall: 118, cottage: 40, mill: 62, lumber_camp: 34, mining_camp: 34, farm: 4, barracks: 52, palisade: 26, gate: 30, watchpost: 82,
    blacksmith: 50, market: 46, archery_range: 48, stable: 46, watch_tower: 78, stone_wall: 24, stone_gate: 34 };
  function inPoly(px, py, pts) { let c = false; for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j]; if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) c = !c; } return c; }
  function buildingHit(b, px, py, slop) {
    const k = R.cam.zoom, s = b.size, z = W.h(b.x, b.y), H = (BH[b.type] || 40) * k;
    const c = [[b.tx, b.ty], [b.tx + s, b.ty], [b.tx + s, b.ty + s], [b.tx, b.ty + s]].map(([x, y]) => R.toScreen(x, y, z));
    const [T, Rt, B, L] = c, up = p => [p[0], p[1] - H];
    const poly = [[B[0], B[1] + slop], [Rt[0] + slop, Rt[1]], up([Rt[0] + slop, Rt[1]]), up([T[0], T[1] - slop]), up([L[0] - slop, L[1]]), [L[0] - slop, L[1]]];
    return inPoly(px, py, poly);
  }
  function pickEntity(px, py, touch) {
    const k = R.cam.zoom, P = W.players[0], slop = touch ? 10 : 2;
    let best = null, bd = 1e9;
    for (const e of W.ents) {
      if (e.dead || e.garrisoned || e.kind === 'building' || (e.kind === 'artifact' && e.carrier)) continue;
      const ti = Math.floor(e.y) * W.W + Math.floor(e.x); if (e.owner !== 0 && !P.vis[ti]) continue;
      const [sx, sy] = R.toScreen(e.x, e.y, W.h(e.x, e.y)), tall = (e.type === 'scout' || e.type === 'archer' ? 32 : e.type === 'skirmisher' || e.type === 'spearman' ? 24 : e.kind === 'artifact' ? 30 : e.type === 'ogre' ? 60 : e.type === 'skirmisher' || e.type === 'goblin' ? 28 : DATA.UNITS[e.type] && e.type !== 'scout' ? 36 : 28) * k;
      const half = (e.type === 'ogre' || e.type === 'scout' ? 15 : 10) * k + slop;
      const cy = sy - tall / 2, dx = (px - sx) / half, dy = (py - cy) / (tall / 2 + slop);   // inside the body's ellipse
      const d = dx * dx + dy * dy; if (d > 1) continue;
      const score = d - (e.owner === 0 ? 0.15 : 0) - (e.x + e.y) * 0.002; if (score < bd) { bd = score; best = e; }
    }
    if (best) return best;
    let bb = null, bdep = -1e9;
    for (const e of W.ents) {
      if (e.dead || e.kind !== 'building') continue;
      if (e.owner !== 0 && !W.seesRect(P, e) && !P.seen.has(e.id)) continue;
      if (Math.abs(R.toScreen(e.x, e.y, 0)[0] - px) > (e.size * 40 + 40) * k) continue;
      if (buildingHit(e, px, py, touch ? 6 : 0) && e.x + e.y > bdep) { bdep = e.x + e.y; bb = e; }
    }
    return bb;
  }
  /* what is under the pointer: a unit, else whichever of a building and a tree/mine is drawn in front */
  function pickAt(px, py, touch) {
    const t = pickEntity(px, py, touch), node = pickNode(px, py, touch);
    if (t && t.kind === 'building' && node >= 0 && (node % W.W) + ((node / W.W) | 0) + 1 > t.x + t.y) return { t: null, node };
    return t ? { t, node: -1 } : { t: null, node };
  }
  function pickNode(px, py, touch) {
    const [wx, wy] = R.toWorld(px, py), P = W.players[0], k = R.cam.zoom, slop = touch ? 8 : 0;
    let best = -1, dep = -1e9;
    for (let ty = Math.floor(wy) - 1; ty <= Math.floor(wy) + 5; ty++) for (let tx = Math.floor(wx) - 1; tx <= Math.floor(wx) + 5; tx++) {
      if (tx < 0 || ty < 0 || tx >= W.W || ty >= W.H) continue;
      const i = ty * W.W + tx, n = W.map.node[i]; if (!n || !P.explored[i]) continue;
      const [sx, sy] = R.toScreen(tx + 0.5, ty + 0.5, W.h(tx + 0.5, ty + 0.5)), tall = (n === 1 ? 92 : n === 6 ? 8 : 26) * k, half = (n === 1 ? 15 : 14) * k + slop;
      if (px < sx - half || px > sx + half || py < sy - tall - slop || py > sy + 8 * k + slop) continue;
      if (tx + ty > dep) { dep = tx + ty; best = i; }   // the front-most sprite under the finger
    }
    return best;
  }
  const own = e => e && e.owner === 0;
  /* every action goes to the world as a command (world.issue); the HUD refreshes once the tick has run it */
  function cmd(c) { W.issue(0, c); st.refreshAt = W.tick + 1; }
  const ownIds = (all) => sel.list().filter(e => e.owner === 0 && (all || e.kind === 'unit')).map(e => e.id);
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
    if (st.mode === 'amove' || st.mode === 'patrol') { P.mode = 'amove'; return; }
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
        const [x, y] = R.toWorld(px, py); if (st.mode === 'patrol') cmd({ c: 'patrol', ids: ownIds(), x, y }); else cmd({ c: 'move', ids: ownIds(), x, y, shift, attack: true }); mark(x, y, '#ff6040'); if (!shift) st.mode = null; refresh(); return; }
      case 'tap': if (!P.moved) tapAt(px, py); return;
      case 'box': {
        const box = st.box; st.box = null; if (P.touch) Mobile.box = false;
        if (!box) return;
        if (P.lpDone && !P.moved) {   // hold without dragging: toggle a unit, or deselect
          const t = pickEntity(px, py, P.touch);
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
    const { t, node } = pickAt(px, py, true), units = ownUnits();
    const blds = sel.list().filter(e => e.owner === 0 && e.kind === 'building');
    if (units.length) {
      const vil = units.some(u => u.type === 'villager');
      const orderTarget = t && (t.owner !== 0 || (t.kind === 'artifact') ||
        (t.kind === 'building' && vil && (!t.built || t.type === 'farm' || t.hp < t.maxHp)) ||
        (t.kind === 'building' && units.some(u => u.artifact) && t.type === 'town_hall'));
      const selectable = t && t.owner === 0 && !orderTarget || (t && t.owner !== 0 && t.kind === 'building' && !units.length);
      if (selectable) return clickSelect(px, py, false, false);
      if (t && !orderTarget && t.owner === 2 && !(t.D && (t.D.creep || t.D.food))) return clickSelect(px, py, false, false);
      if (!t && node < 0 && Mobile.tapOrder === 'amove') { const [x, y] = R.toWorld(px, py); cmd({ c: 'move', ids: ownIds(), x, y, attack: true }); mark(x, y, '#ff6040'); return; }
      return rightClick(px, py, false);
    }
    if (!t && blds.some(b => b.D.trains)) return rightClick(px, py, false);   // rally point
    clickSelect(px, py, false, false);
  }
  function clickSelect(px, py, shift, ctrl) {
    const pk = pickAt(px, py, P.touch), e = pk.t, now = performance.now();
    if (!e) { if (!shift) sel.set.clear(); const n = pk.node; st.nodeSel = n; st.menu = null; return refresh(); }
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
    const [x, y] = R.toWorld(px, py), { t, node } = pickAt(px, py, P.touch);
    const units = ownUnits(), blds = sel.list().filter(e => e.owner === 0 && e.kind === 'building');
    if (units.length) {
      cmd({ c: 'order', ids: ownIds(), target: t ? t.id : 0, node, x, y, shift });
      mark(x, y, t && W.isHostile(units[0], t) ? '#ff4030' : node >= 0 || t ? '#ffd040' : '#40ff60');
    } else if (blds.length) {
      cmd({ c: 'rally', ids: blds.map(b => b.id), x, y, target: t ? t.id : 0, node });
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
    const us = ownUnits(); if (us.length) { cmd({ c: 'move', ids: ownIds(), x, y, shift, attack: Mobile.tapOrder === 'amove' && e2touch }); mark(x, y, '#40ff60'); return true; }
    const bs = sel.list().filter(b => b.owner === 0 && b.D.trains); if (bs.length) cmd({ c: 'rally', ids: bs.map(b => b.id), x, y }); return bs.length > 0;
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
    if ((D.age || 1) > W.players[0].age) return msg(`Needs the ${DATA.AGE_NAMES[D.age]}.`);
    if (D.needs && !W.has(0, D.needs)) return msg(`Needs a ${DATA.BUILDINGS[D.needs].name} first.`);
    if (!W.canAfford(0, D.cost)) return msg(`Not enough resources for a ${D.name}.`);
    st.placing = type; st.menu = DATA.BUILDINGS[type].menu || 'eco'; Mobile.pin = null; if (Mobile.on) Mobile.startPin(); updateGhost(); refresh();
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
    if (!W.canPlace(st.placing, 0, tx, ty)) return msg('Cannot build there.');
    if (!W.canAfford(0, D.cost)) return msg('Not enough resources.');
    cmd({ c: 'place', type: st.placing, tiles: [[tx, ty]], ids: builders().map(u => u.id), shift });
    Mobile.pin = null;
    if (!shift) { st.placing = null; st.ghost = null; st.menu = null; } else updateGhost(); refresh();
    return true;
  }
  function placeWall(shift) {
    const tiles = wallLine(st.wallStart, tileAt(...st.mouse, 1)); st.wallStart = null;
    cmd({ c: 'place', type: st.placing, tiles: tiles.filter(([tx, ty]) => W.canPlace(st.placing, 0, tx, ty)), ids: builders().map(u => u.id), shift });
    if (!shift) { st.placing = null; st.ghost = null; st.menu = null; }
    refresh();
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
        h += rb('build', 'Build', inMenu() ? 'on' : '') + rb('box', 'Box', this.box ? 'on' : '') + rb('idle', 'Idle') + rb('army', 'Army') + rb('screen', 'Screen');
        if (units) h += this.tapOrder === 'move' ? rb('move', 'Move') : rb('amove', 'Attack', 'on');
        if (has) h += rb('clear', 'Clear');
        h += rb('map', 'Map', document.body.classList.contains('m-mapoff') ? '' : 'on');
      }
      const el = $('mrail'); if (el._h !== h) { el._h = h; el.innerHTML = h; }
    },
    act(a) {
      if (a === 'build') {
        if (inMenu()) { st.menu = null; return refresh(); }
        let v = ownUnits().filter(u => u.type === 'villager');
        if (!v.length) {   // no peasant selected: take an idle one, else the nearest to the middle of the screen
          const [cx, cy] = R.toWorld(R.vw / 2, R.vh / 2), all = W.ents.filter(u => !u.dead && u.owner === 0 && u.type === 'villager' && !u.garrisoned);
          const idle = all.filter(u => !u.order), pool = idle.length ? idle : all;
          pool.sort((a, b) => Math.hypot(a.x - cx, a.y - cy) - Math.hypot(b.x - cx, b.y - cy));
          if (!pool.length) return msg('No peasants.'); sel.set = new Set([pool[0].id]); msg('Building with the nearest peasant.');
        }
        st.menu = 'eco'; return refresh();
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
    if (k === 'F2') { e.preventDefault(); return openTree(!$('tree').classList.contains('show')); }
    if (k === 'F10') { e.preventDefault(); return openMenu(!$('menu').classList.contains('show')); }
    if (k === '+' || k === '=') return setSpeed(Math.min(2, st.speed + 0.5));
    if (k === '-' || k === '_') return setSpeed(Math.max(0.5, st.speed - 0.5));
    if (k === 'Escape') { if ($('menu').classList.contains('show') || $('tree').classList.contains('show')) { openMenu(false); return openTree(false); } if (st.placing || st.mode) return cancelModes(); if (st.menu) { st.menu = null; return refresh(); } sel.set.clear(); return refresh(); }
    if (k === '.') return idleVillager();
    if (k === ',') return idleMilitary();
    if (k === ' ' ) { e.preventDefault(); const a = W.alerts[W.alerts.length - 1] || W.messages.filter(m => m.x !== undefined).pop(); if (a) R.centerOn(a.x, a.y); return; }
    if (k === 'Delete') { cmd({ c: 'delete', ids: ownIds(true) }); sel.set.clear(); return refresh(); }
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
  function togglePause() { st.paused = !st.paused; $('btn-pause').textContent = st.paused ? 'Resume' : 'Pause'; $('paused').style.display = st.paused ? 'flex' : 'none'; }
  function setSpeed(s) { st.speed = s; $('btn-speed').textContent = 'Speed: ' + s.toFixed(1) + 'x'; $('speedtxt').textContent = ({ 0.5: 'Slow', 1: 'Normal', 1.5: 'Fast', 2: 'Very fast' }[s] || '') + (s !== 1 ? ` (${s.toFixed(1)}x)` : ''); }

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
  /* ---- the HUD, laid out as AoE2's: pictures, not words. Icons come from one atlas cut from the game's own art
     (tools/build_icons.py -> art/icons.png, icons.json). ---- */
  let IC = null;
  function ico(key, size = 50) {
    const p = IC && IC.icons[key]; if (!p) return `<i class="ico" style="width:${size}px;height:${size}px;background:#241b12"></i>`;
    return `<i class="ico" style="width:${size}px;height:${size}px;background-size:${IC.cols * size}px ${IC.rows * size}px;background-position:-${p[0] * size}px -${p[1] * size}px"></i>`;
  }
  function costHtml(c) { const P = W.players[0]; return Object.entries(c).map(([k, v]) => `<span class="cost${P.res[k] < v ? ' short' : ''}">${ico('r_' + k, 16)}${v}</span>`).join(''); }
  const tipHtml = (name, cost, time, text, note) => `<b>${name}</b>${cost ? `<div class="costs">${costHtml(cost)}${time ? `<span class="cost dim">${time}s</span>` : ''}</div>` : '<br>'}${text || ''}${note ? `<br><em>${note}</em>` : ''}`;
  const ORDER = ['wood', 'food', 'iron', 'stone', 'crystal'];   // AoE2: wood, food, gold, stone; iron stands where gold does
  function buildTop() {
    $('res').innerHTML = ORDER.map(r => `<div class="r" title="${DATA.RES_INFO[r].name}${DATA.RES_INFO[r].basic ? '' : ' (premium)'}: stockpile, and the peasants gathering it">${ico('r_' + r, 30)}<b id="r-${r}">0</b><small id="v-${r}"></small></div>`).join('') +
      `<div class="r" title="Population / housing">${ico('r_pop', 30)}<b id="r-pop">0/0</b><small></small></div>` +
      `<button class="r" id="btn-idle" title="Idle peasants: click to select the next one (.)" hidden>${ico('r_idle', 30)}<b id="r-idle">0</b><small>idle</small></button>`;
    $('btn-idle').onclick = () => idleVillager();
    $('btn-tree').innerHTML = ico('m_techtree', 28); $('btn-help').innerHTML = ico('m_settings', 28); $('btn-menu').innerHTML = ico('m_menu', 28);
    $('btn-mode').innerHTML = ico('m_mode', 30); $('btn-idlemil').innerHTML = ico('c_stance_aggressive', 30);
  }
  function button(key, label, tip, onclick, opts = {}) {
    const b = document.createElement('button'); b.dataset.key = key; b.setAttribute('aria-label', label);
    b.innerHTML = `${ico(opts.icon, Mobile.on ? 48 : 52)}${opts.cost ? `<span class="cst">${Object.entries(opts.cost).map(([k, v]) => `${v}${k[0]}`).join(' ')}</span>` : ''}<span class="hk">${key}</span>`;
    b.disabled = !!opts.disabled; if (opts.cls) b.className = opts.cls;
    b._cost = opts.cost; if (opts.cost && !opts.disabled && !W.canAfford(0, opts.cost)) b.classList.add('poor');
    const full = tip ? tip.replace('</b>', `</b><span class="hkk">(${key})</span>`) : '';
    b.onclick = ev => { if (b._lp) { b._lp = false; return; } hideTip(); onclick(ev); };
    b.onmouseenter = () => tip && !Mobile.on && showTip(b, full); b.onmouseleave = () => { if (!b._lp) hideTip(); };
    b.addEventListener('pointerdown', e => { if (e.pointerType === 'mouse' || !tip) return; clearTimeout(b._t); b._t = setTimeout(() => { b._lp = true; showTip(b, full); setTimeout(hideTip, 2500); }, 450); });
    for (const t of ['pointerup', 'pointercancel']) b.addEventListener(t, () => clearTimeout(b._t));
    b.addEventListener('contextmenu', e => e.preventDefault());
    return b;
  }
  /* AoE2 shows the extended tooltip in one fixed place, just above the command panel */
  function showTip(b, html) { const t = $('tip'); t.innerHTML = html; t.style.display = 'block'; const c = $('cmds').getBoundingClientRect(), r = b.getBoundingClientRect();
    if (Mobile.on) { t.style.left = Math.max(6, Math.min(window.innerWidth - 306, r.left)) + 'px'; t.style.bottom = (window.innerHeight - r.top + 6) + 'px'; }
    else { t.style.left = (c.left + 8) + 'px'; t.style.bottom = (window.innerHeight - $('bottom').getBoundingClientRect().top + 8) + 'px'; } }
  function hideTip() { $('tip').style.display = 'none'; }
  const GRID = ['Q', 'W', 'E', 'R', 'T', 'A', 'S', 'D', 'F', 'G', 'Z', 'X', 'C', 'V', 'B'];   // 5 x 3, as AoE2's command panel
  function openMenu(on) { $('menu').classList.toggle('show', on); if (on !== st.paused && (on || st.menuPaused)) { st.menuPaused = on; togglePause(); } }
  /* The Technology Tree (AoE2: F2): one column per building, one row per age; what it trains and researches. */
  function openTree(on) {
    const el = $('tree'); el.classList.toggle('show', on); if (!on) return;
    const P = W.players[0], B = DATA.BUILDINGS, cols = Object.keys(B).filter(k => !['palisade', 'gate', 'stone_wall', 'stone_gate', 'farm', 'cottage'].includes(k)).concat(['palisade', 'stone_wall']);
    const cell = (cls, key, title) => `<span class="tk ${cls}" title="${title}">${ico(key, 38)}</span>`;
    let h = '<div></div>' + cols.map(k => `<div class="thead">${B[k].name}</div>`).join('');
    for (let age = 1; age <= 3; age++) {
      h += `<div class="tage">${DATA.AGE_NAMES[age]}</div>`;
      for (const k of cols) { const D = B[k]; let c = '';
        const sibs = k === 'palisade' ? ['palisade', 'gate'] : k === 'stone_wall' ? ['stone_wall', 'stone_gate'] : k === 'town_hall' ? ['town_hall', 'cottage'] : k === 'mill' ? ['mill', 'farm'] : [k];
        for (const b of sibs) if ((B[b].age || 1) === age) c += cell(W.has(0, b) ? 'have' : (B[b].age || 1) <= P.age && (!B[b].needs || W.has(0, B[b].needs)) ? 'can' : 'no', 'b_' + b, B[b].name);
        for (const u of D.trains || []) if ((DATA.UNITS[u].age || 1) === age) c += cell(!W.has(0, k) || (DATA.UNITS[u].age || 1) > P.age ? 'no' : 'can', 'u_' + u, DATA.UNITS[u].name);
        for (const t of D.researches || []) { const T = DATA.TECHS[t], ta = T.isAge ? T.isAge - 1 : (T.age || 1); if (ta === age) c += cell(P.techs.has(t) || (T.isAge && P.age >= T.isAge) ? 'have' : W.has(0, k) && !W.techBlock(0, t) ? 'can' : 'no', 't_' + t, T.name); }
        h += `<div class="tcol">${c}</div>`; }
    }
    const body = $('tree-body'); body.style.gridTemplateColumns = `26px repeat(${cols.length}, 92px)`; body.innerHTML = h;
  }
  const inMenu = () => st.menu === 'eco' || st.menu === 'mil';
  function refresh() {
    const cmds = $('cmds'); cmds.innerHTML = ''; hideTip();
    const list = sel.list(), mine = list.filter(own), units = mine.filter(e => e.kind === 'unit'), blds = mine.filter(e => e.kind === 'building');
    const P = W.players[0], slot = {}, add = b => { slot[b.dataset.key] = b; };
    if (units.length) {
      const vils = units.filter(u => u.type === 'villager'), army = units.filter(u => u.type !== 'villager' && u.type !== 'sheep');
      if (vils.length && inMenu()) {   // AoE2's two build pages: economic and military
        DATA.BUILD_MENU[st.menu].forEach((t, i) => { const D = DATA.BUILDINGS[t], young = (D.age || 1) > P.age, need = D.needs && !W.has(0, D.needs);
          add(button(GRID[i], D.name, tipHtml('Build ' + D.name, D.cost, 0, D.tip, young ? `Needs the ${DATA.AGE_NAMES[D.age]}.` : need ? `Needs a ${DATA.BUILDINGS[D.needs].name}.` : ''),
            () => startPlacing(t), { icon: 'b_' + t, disabled: young || need, cls: st.placing === t ? 'on' : '', cost: D.cost })); });
        add(button('V', st.menu === 'eco' ? 'Military buildings' : 'Economic buildings', tipHtml(st.menu === 'eco' ? 'Military buildings' : 'Economic buildings', null, 0, 'The other build page.'), () => { st.menu = st.menu === 'eco' ? 'mil' : 'eco'; cancelModes(); }, { icon: st.menu === 'eco' ? 'c_build_mil' : 'c_build_eco' }));
        add(button('B', 'Back', tipHtml('Back', null, 0, 'Return to the unit\'s commands (Esc).'), () => { st.menu = null; cancelModes(); }, { icon: 'c_back' }));
      } else {
        if (army.length) {   // AoE2 military panel: stances along the top, orders in the middle, formations along the bottom
          const stn = army[0].stance, fm = army[0].formation, ids = army.map(u => u.id);
          const ST = { aggressive: 'Chase whatever comes into sight.', defensive: 'Chase a short way, then return.', ground: 'Fight only what is in reach.', passive: 'Never fight.' };
          DATA.STANCES.forEach((v, i) => add(button(GRID[i], DATA.STANCE_NAMES[v], tipHtml(DATA.STANCE_NAMES[v] + ' stance', null, 0, ST[v] || ''), () => cmd({ c: 'stance', ids, stance: v }), { icon: 'c_stance_' + v, cls: stn === v ? 'on' : '' })));
          add(button('A', 'Attack-move', tipHtml('Attack-move', null, 0, 'Click a destination; units fight anything on the way.'), () => { st.mode = 'amove'; msg('Attack-move: click a destination.'); }, { icon: 'c_amove' }));
          add(button('F', 'Patrol', tipHtml('Patrol', null, 0, 'Click a point: units walk back and forth between here and there, attacking what they meet.'), () => { st.mode = 'patrol'; msg('Patrol: click the far end.'); }, { icon: 'c_patrol' }));
          const FM = { line: 'Wide ranks, melee in front, ranged behind.', staggered: 'Spread out against area damage.', box: 'A square, the weak inside.', flank: 'Two wings.' };
          DATA.FORMATIONS.forEach((v, i) => add(button(GRID[10 + i], DATA.FORMATION_NAMES[v], tipHtml(DATA.FORMATION_NAMES[v] + ' formation', null, 0, FM[v] || ''), () => cmd({ c: 'formation', ids, formation: v }), { icon: 'c_formation_' + v, cls: fm === v ? 'on' : '' })));
        } else if (vils.length) {
          add(button('Q', 'Build', tipHtml('Economic buildings', null, 0, 'Cottage, Mill, camps, Farm, Blacksmith, Market.'), () => { st.menu = 'eco'; refresh(); }, { icon: 'c_build_eco' }));
          add(button('W', 'Build military', tipHtml('Military buildings', null, 0, 'Barracks, Archery Range, Stable, walls, gates, towers.'), () => { st.menu = 'mil'; refresh(); }, { icon: 'c_build_mil' }));
        }
        add(button('S', 'Stop', tipHtml('Stop', null, 0, 'Drop the current order.'), () => cmd({ c: 'stop', ids: ownIds() }), { icon: 'c_stop' }));
        if (units.some(u => u.D.carries) && W.ents.some(a => !a.dead && a.kind === 'artifact' && !a.carrier && W.players[0].vis[Math.floor(a.y) * W.W + Math.floor(a.x)]))
          add(button('D', 'Get artifact', tipHtml('Fetch the artifact', null, 0, 'Pick up the nearest visible artifact and carry it home.'), () => cmd({ c: 'pickup', ids: ownIds() }), { icon: 'c_pickup' }));
        add(button('G', 'Garrison', tipHtml('Garrison', null, 0, 'Take cover in the nearest Town Hall or Watch Tower with room.'), () => cmd({ c: 'garrison', ids: ownIds() }), { icon: 'c_garrison' }));
        add(button('B', 'Delete', tipHtml('Delete', null, 0, 'Remove the selected units (Del).'), () => { cmd({ c: 'delete', ids: ownIds() }); sel.set.clear(); refresh(); }, { icon: 'c_delete' }));
      }
    } else if (blds.length === 1 || (blds.length && blds.every(b => b.type === blds[0].type))) {
      const b = blds[0], D = b.D;
      if (b.built) {
        (D.trains || []).forEach((t, i) => { const U = DATA.UNITS[t], young = (U.age || 1) > P.age, cost = W.unitCost(0, t), maa = t === 'militia' && W.tech(0, 'man_at_arms'), name = maa ? 'Man-at-Arms' : U.name;
          add(button(GRID[i], `Create ${name}`, tipHtml('Create ' + name, cost, U.time, U.tip, young ? `Needs the ${DATA.AGE_NAMES[U.age]}.` : 'Shift-click: 5'),
            ev => { cmd({ c: 'train', ids: blds.map(x => x.id), unit: t, n: ev.shiftKey ? 5 : 1 }); }, { icon: 'u_' + (maa ? 'militia_maa' : t), cost, disabled: young })); });
        (D.researches || []).filter(t => !P.techs.has(t) && !(DATA.TECHS[t].isAge && P.age >= DATA.TECHS[t].isAge)).forEach((t, i) => { const T = DATA.TECHS[t], why = W.techBlock(0, t);
          add(button(GRID[5 + i], T.name, tipHtml((T.isAge ? '' : 'Research ') + T.name, T.cost, T.time, T.tip, why || ''), () => cmd({ c: 'research', id: b.id, tech: t }), { icon: 't_' + t, disabled: !!why, cost: T.cost })); });
        if (D.market) ['food', 'wood', 'stone'].forEach((r, i) => { const pr = W.market[r], M = DATA.MARKET, buy = Math.round(pr * (1 + M.fee)), sellv = Math.round(pr * (1 - M.fee));
          add(button(GRID[i], `Buy ${r}`, tipHtml(`Buy 100 ${r}`, { iron: buy }, 0, 'The price rises with each purchase.'), () => cmd({ c: 'buy', res: r }), { icon: 'c_buy_' + r, cost: { iron: buy } }));
          add(button(GRID[5 + i], `Sell ${r}`, tipHtml(`Sell 100 ${r} for ${sellv} iron`, { [r]: 100 }, 0, 'The price falls with each sale.'), () => cmd({ c: 'sell', res: r }), { icon: 'c_sell_' + r, cost: { [r]: 100 } })); });
        if (b.type === 'town_hall') {
          add(button('Z', 'Town Bell', tipHtml('Ring the Town Bell', null, 0, 'Every peasant runs to a Town Hall and hides inside; a Town Hall shoots one arrow for each.'), () => cmd({ c: 'bell' }), { icon: 'c_bell' }));
          add(button('X', 'All Clear', tipHtml('All Clear', null, 0, 'Everyone back to work.'), () => cmd({ c: 'allclear' }), { icon: 'c_allclear' }));
        }
        if (b.garrison.length) add(button('C', 'Ungarrison', tipHtml('Ungarrison', null, 0, 'Everyone out.'), () => cmd({ c: 'ungarrison', ids: [b.id] }), { icon: 'c_ungarrison' }));
      }
      add(button('B', 'Delete', tipHtml('Delete', null, 0, 'Demolish the building (Del).'), () => { cmd({ c: 'delete', ids: blds.map(x => x.id) }); sel.set.clear(); refresh(); }, { icon: 'c_delete' }));
    }
    // always fifteen slots, in grid order: an empty slot is an empty frame, as in AoE2
    for (const k of GRID) { if (slot[k]) cmds.appendChild(slot[k]); else { const d = document.createElement('div'); d.className = 'slot'; cmds.appendChild(d); } }
    document.body.classList.toggle('m-empty', !sel.set.size && !inMenu() && !st.placing && !(st.nodeSel >= 0));
    Mobile.rail(); Mobile.groups();
    info();
  }
  let infoKey = '';
  const WHO = ['You', 'Enemy', 'Wild'];
  const artKey = e => e.kind === 'artifact' ? 'p_relic' : e.kind === 'building' ? 'b_' + e.type : 'u_' + (e.type === 'militia' && W.tech(e.owner, 'man_at_arms') ? 'militia_maa' : e.type);
  const stat = (icon, v, title) => `<span title="${title}">${ico(icon, 18)}${v}</span>`;
  function info() {
    const list = sel.list(), el = $('info'); let h;
    if (!list.length) {
      if (st.nodeSel >= 0 && W.map.node[st.nodeSel]) {
        const n = W.map.node[st.nodeSel], k = MapGen.NODE_KEY[n], c = W.wardedBy(st.nodeSel), pk = { 1: 'p_tree_0', 2: 'p_berry_0', 3: 'p_stone_0', 4: 'p_iron_0', 5: 'p_crystal_0' }[n] || 'r_food';
        h = `<div class="selp"><div class="port">${ico(pk, 84)}</div><div class="selb"><h3>${DATA.NODES[k].name}</h3><div class="own">Resource</div><p class="stats">${stat('r_' + (k === 'tree' ? 'wood' : DATA.NODES[k].res), Math.ceil(W.map.amt[st.nodeSel]), 'Left')}</p>${c ? `<p class="warn">Warded by the ${DATA.CAMPS[c.type].name}. Clear it to mine here.</p>` : ''}</div></div>`;
      } else h = '';
      if (h !== infoKey) { el.innerHTML = h; infoKey = h; } return;
    }
    if (list.length > 1) {   // AoE2: a grid of the selected units' pictures, each with its hit points
      h = '<div class="multi">' + list.map(e => `<span class="ic" data-id="${e.id}" title="${e.kind === 'unit' ? W.unitName(e) : e.D.name}" style="--c:${W.players[e.owner].color}">${ico(artKey(e), 34)}<u><s style="width:${Math.round(20 * e.hp / e.maxHp) * 5}%"></s></u></span>`).join('') + '</div>';
      if (h !== infoKey) { el.innerHTML = h; infoKey = h;
        el.querySelectorAll('.ic').forEach(s => s.onclick = ev => { if (ev.shiftKey) sel.set.delete(+s.dataset.id); else sel.set = new Set([+s.dataset.id]); refresh(); }); }
      return;
    }
    const e = list[0], D = e.D;
    h = `<div class="selp"><div class="port">${ico(artKey(e), 84)}${e.kind !== 'artifact' ? `<div class="hp"><i style="width:${100 * e.hp / e.maxHp}%"></i><span>${Math.ceil(e.hp)}/${e.maxHp}</span></div>` : ''}</div><div class="selb">`;
    h += `<h3>${e.kind === 'unit' ? W.unitName(e) : D.name}</h3><div class="own">${e.kind === 'artifact' ? 'Relic' : e.owner === 2 && D.creep ? 'Creep' : WHO[e.owner]}${e.kind === 'unit' && e.owner === 0 && e.type !== 'villager' && e.type !== 'sheep' ? ` · ${DATA.STANCE_NAMES[e.stance]} · ${DATA.FORMATION_NAMES[e.formation]}` : ''}</div>`;
    if (e.kind === 'unit') {
      if (e.carcass) h += `<p class="stats">${stat('r_food', Math.ceil(e.food), 'Food left')}</p>`;
      else {
        const S = W.S(e), bon = Object.entries(S.bonus).map(([k, v]) => `+${v} vs ${k}`).join(', ');
        h += `<p class="stats">${stat('s_attack', S.melee || S.pierce, 'Attack')}${stat('s_armor', S.armor[0], 'Melee armour')}${stat('s_pierce', S.armor[1], 'Pierce armour')}${S.range ? stat('s_range', S.range, 'Range') : ''}${stat('s_los', S.los, 'Line of sight')}${stat('s_speed', +S.speed.toFixed(2), 'Speed')}</p>`;
        if (bon) h += `<p class="dim">${bon}</p>`;
        if (e.type === 'villager') h += `<p class="stats">${e.carry.amt >= 0.5 ? stat('r_' + e.carry.res, Math.floor(e.carry.amt), 'Carrying') : ''}<span>${e.order ? taskName(e) : 'idle'}</span></p>`;
        if (e.artifact) h += '<p>Carrying an artifact: bring it to a Town Hall.</p>';
        if (D.food && !e.carcass) h += `<p class="stats">${stat('r_food', D.food, 'Food')}</p>`;
        if (e.camp !== undefined) { const c = W.campById(e.camp); h += `<p class="dim">Guards the ${DATA.CAMPS[c.type].name}.</p>`; }
      }
    } else if (e.kind === 'building') {
      let st2 = '';
      if (D.arrows) st2 += stat('s_attack', D.arrows.atk, 'Attack') + stat('s_range', D.arrows.range, 'Range');
      if (D.armor) st2 += stat('s_armor', D.armor[0], 'Melee armour') + stat('s_pierce', D.armor[1], 'Pierce armour');
      if (D.garrison) st2 += stat('s_garrison', `${e.garrison.length}/${D.garrison}`, 'Garrison');
      if (e.type === 'farm') st2 += stat('r_food', Math.ceil(e.food), 'Food left');
      if (e.artifacts) st2 += stat('p_relic', `${e.artifacts} (+${(e.artifacts * DATA.ARTIFACT_RATE).toFixed(1)}/s)`, 'Artifacts');
      if (st2) h += `<p class="stats">${st2}</p>`;
      if (!e.built) h += `<p>Under construction: ${Math.floor(e.progress * 100)}%</p>`;
      if (e.queue.length) {   // AoE2: the production queue as pictures, the first one with its progress
        const q0 = e.queue[0]; h += `<p class="dim">${q0.kind === 'tech' ? 'Researching' : 'Creating'} ${(q0.kind === 'tech' ? DATA.TECHS : DATA.UNITS)[q0.what].name} · ${Math.floor(100 * q0.t / q0.time)}%</p>`;
        h += '<div class="queue">' + e.queue.map((q, i) => `<span class="q" data-i="${i}" title="${(q.kind === 'tech' ? DATA.TECHS : DATA.UNITS)[q.what].name}: click to cancel">${ico((q.kind === 'tech' ? 't_' : 'u_') + q.what, i ? 36 : 42)}${i === 0 ? `<u><s style="width:${Math.round(100 * q.t / q.time)}%"></s></u>` : ''}</span>`).join('') + '</div>';
        if (e.queue[0].housed) h += '<p class="warn">Need more housing (build a Cottage).</p>';
      } else if (D.drop && e.owner === 0) h += `<p class="dim">Drop-off: ${D.drop.join(', ')}</p>`;
    } else h += '<p>Militia can carry it to your Town Hall for +0.5 crystal a second.</p>';
    h += '</div></div>';
    if (h !== infoKey) { el.innerHTML = h; infoKey = h;
      el.querySelectorAll('.q').forEach(s => s.onclick = () => cmd({ c: 'cancel', id: e.id, i: +s.dataset.i })); }
  }
  function taskName(u) {
    const o = u.order; if (!o) return 'idle';
    if (o.type === 'gather') { const r = u.lastGather && u.lastGather.res; return { food: 'gathering food', wood: 'chopping wood', stone: 'mining stone', iron: 'mining iron', crystal: 'mining crystal' }[r] || 'gathering'; }
    return { build: 'building', repair: 'repairing', dropoff: 'dropping off', move: 'moving', amove: 'attack-moving', attack: 'attacking', patrol: 'patrolling', garrison: 'garrisoning', pickup: 'fetching artifact', deliver: 'delivering artifact' }[o.type] || o.type;
  }

  function frame(dt) {
    scroll(dt);
    if (st.refreshAt && W.tick >= st.refreshAt) { st.refreshAt = 0; refresh(); }
    // drop dead entities from the selection
    let changed = false; for (const id of sel.set) if (!W.get(id) || W.get(id).garrisoned) { sel.set.delete(id); changed = true; }
    if (changed) refresh();
    const P = W.players[0];
    for (const r of DATA.RES) $('r-' + r).textContent = Math.floor(P.res[r]);
    const on = { food: 0, wood: 0, stone: 0, iron: 0, crystal: 0 }; let idle = 0;
    for (const u of W.ents) if (!u.dead && u.owner === 0 && u.type === 'villager') { if (!u.order && !u.garrisoned) idle++; else if (u.order && (u.order.type === 'gather' || u.order.type === 'dropoff') && u.lastGather) on[u.lastGather.res]++; }
    for (const r of DATA.RES) $('v-' + r).textContent = on[r] ? on[r] : '';
    if (st.ageShown !== P.age) { st.ageShown = P.age; $('age').textContent = DATA.AGE_NAMES[P.age]; $('age-ico').outerHTML = ico('age_' + P.age, 30).replace('<i ', '<i id="age-ico" '); }
    const pe = $('r-pop'); pe.textContent = `${P.pop}/${P.popCap}`; pe.className = P.pop >= P.popCap ? 'capped' : '';
    $('btn-idle').hidden = !idle; $('r-idle').textContent = idle;   // AoE2: the idle-villager button appears only when there are some
    const t = Math.floor(W.time); $('clock').textContent = `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
    // messages and alerts
    const m = $('msgs'), recent = [...W.messages.filter(x => W.time - x.t < 7), ...W.alerts.filter(a => W.time - a.t < 5).map(a => ({ text: a.text, t: a.t, alert: true }))].sort((a, b) => a.t - b.t).slice(-5);
    m.innerHTML = recent.map(x => `<div class="${x.alert ? 'alert' : ''}">${x.text}</div>`).join('');
    info();
    if (st.poorT !== Math.floor(W.time * 2)) { st.poorT = Math.floor(W.time * 2); for (const b of document.querySelectorAll('#cmds button')) if (b._cost) b.classList.toggle('poor', !b.disabled && !W.canAfford(0, b._cost)); }
    if (Mobile.on) { Mobile.rail(); Mobile.groups(); }
    if (W.state !== 'playing' && !st.ended) { st.ended = true; $('end').style.display = 'flex'; $('end-text').textContent = W.state === 'victory' ? 'Victory' : 'Defeat'; }
  }
  return { init, frame, refresh, sel, st, msg, startPlacing, Mobile, pickEntity, pickNode };
})();
