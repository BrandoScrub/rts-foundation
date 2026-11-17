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
    cv.addEventListener('mousedown', down); window.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
    cv.addEventListener('wheel', wheel, { passive: false });
    window.addEventListener('keydown', key); window.addEventListener('keyup', e => st.keys.delete(e.key));
    window.addEventListener('blur', () => st.keys.clear());
    const mini = $('mini'); mini.addEventListener('contextmenu', e => e.preventDefault());
    mini.addEventListener('mousedown', miniDown); mini.addEventListener('mousemove', e => { if (e.buttons & 1) miniDown(e); });
    $('btn-pause').onclick = togglePause; $('btn-speed').onclick = () => setSpeed(st.speed >= 2 ? 0.5 : st.speed + 0.5);
    $('btn-idle').onclick = () => idleVillager(); $('btn-help').onclick = () => $('help').classList.toggle('show');
    $('help').onclick = () => $('help').classList.remove('show');
    buildTop();
  }

  /* ---------------- picking ---------------- */
  function pickEntity(px, py) {
    let best = null, bd = 1e9; const k = R.cam.zoom, P = W.players[0];
    for (const e of W.ents) {
      if (e.dead || e.garrisoned || e.kind === 'building' || (e.kind === 'artifact' && e.carrier)) continue;
      const ti = Math.floor(e.y) * W.W + Math.floor(e.x); if (e.owner !== 0 && !P.vis[ti]) continue;
      const [sx, sy] = R.toScreen(e.x, e.y, W.h(e.x, e.y)), tall = (e.type === 'ogre' ? 52 : e.kind === 'artifact' ? 30 : 30) * k, half = (e.type === 'ogre' || e.type === 'scout' ? 16 : 11) * k;
      if (px < sx - half || px > sx + half || py < sy - tall || py > sy + 6 * k) continue;
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

  /* ---------------- mouse ---------------- */
  function down(e) {
    const [px, py] = [e.offsetX, e.offsetY]; st.mouse = [px, py];
    if (e.button === 1) { st.mid = [px, py, R.cam.x, R.cam.y]; e.preventDefault(); return; }
    if (e.button === 2) { if (st.placing || st.mode) { cancelModes(); return; } return rightClick(px, py, e.shiftKey); }
    if (st.mode === 'amove') { const [x, y] = R.toWorld(px, py); W.groupMove(ownUnits(), x, y, e.shiftKey, true); mark(x, y, '#ff6040'); if (!e.shiftKey) st.mode = null; return; }
    if (st.placing) {
      const D = DATA.BUILDINGS[st.placing];
      if (D.wall || D.gate) { st.wallStart = tileAt(px, py, 1); return; }
      return placeAt(px, py, e.shiftKey);
    }
    st.box = [px, py, px, py];
  }
  function move(e) {
    const r = cv.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top; st.mouse = [px, py]; st.inside = e.target === cv;
    if (st.mid) { R.cam.x = st.mid[2] - (px - st.mid[0]) / R.cam.zoom; R.cam.y = st.mid[3] - (py - st.mid[1]) / R.cam.zoom; R.clampCam(); return; }
    if (st.box) { st.box[2] = px; st.box[3] = py; }
    const h = st.inside ? pickEntity(px, py) : null; st.hoverId = h ? h.id : 0;
    updateGhost();
  }
  function up(e) {
    if (e.button === 1) { st.mid = null; return; }
    if (e.button !== 0) return;
    if (st.wallStart && st.placing) { placeWall(e.shiftKey); return; }
    if (!st.box) return;
    const [a, b, c, d] = st.box; st.box = null;
    if (Math.abs(c - a) < 5 && Math.abs(d - b) < 5) return clickSelect(a, b, e.shiftKey, e.ctrlKey);
    const x0 = Math.min(a, c), x1 = Math.max(a, c), y0 = Math.min(b, d), y1 = Math.max(b, d);
    const inBox = W.ents.filter(u => !u.dead && u.kind === 'unit' && u.owner === 0 && !u.garrisoned && u.type !== 'sheep' && (() => {
      const [sx, sy] = R.toScreen(u.x, u.y, W.h(u.x, u.y)); return sx >= x0 && sx <= x1 && sy - 12 >= y0 - 10 && sy - 12 <= y1 + 10; })());
    if (!e.shiftKey) sel.set.clear();
    for (const u of inBox.slice(0, 60)) sel.set.add(u.id);   // AoE2 DE selection limit 60
    st.menu = null; refresh();
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
  function miniDown(e) {
    e.preventDefault(); const m = $('mini'), r = m.getBoundingClientRect(), sx = m.width / r.width;
    const [x, y] = R.miniToWorld((e.clientX - r.left) * sx, (e.clientY - r.top) * sx);
    if (x < 0 || y < 0 || x > W.W || y > W.H) return;
    if (e.button === 2) { const us = ownUnits(); if (us.length) { W.groupMove(us, x, y, e.shiftKey); mark(x, y, '#40ff60'); } else for (const b of sel.list()) if (b.owner === 0 && b.D.trains) b.rally = { x, y }; return; }
    R.centerOn(x, y);
  }

  /* ---------------- placement ---------------- */
  function tileAt(px, py, s) { const [x, y] = R.toWorld(px, py); return [Math.round(x - s / 2), Math.round(y - s / 2)]; }
  function startPlacing(type) {
    const D = DATA.BUILDINGS[type];
    if (D.needs && !W.has(0, D.needs)) return msg(`Needs a ${DATA.BUILDINGS[D.needs].name} first.`);
    if (!W.canAfford(0, D.cost)) return msg(`Not enough resources for a ${D.name}.`);
    st.placing = type; st.menu = 'build'; updateGhost(); refresh();
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
    const [tx, ty] = tileAt(px, py, D.size);
    st.ghost = [{ type: st.placing, tx, ty, ok: W.canPlace(st.placing, 0, tx, ty) && W.canAfford(0, D.cost) }];
  }
  function builders() { return ownUnits().filter(u => u.type === 'villager'); }
  function placeAt(px, py, shift) {
    const D = DATA.BUILDINGS[st.placing], [tx, ty] = tileAt(px, py, D.size);
    const b = W.place(st.placing, 0, tx, ty);
    if (!b) return msg(W.canAfford(0, D.cost) ? 'Cannot build there.' : 'Not enough resources.');
    for (const u of builders()) W.order(u, { type: 'build', id: b.id }, shift);
    if (!shift) { st.placing = null; st.ghost = null; st.menu = null; } refresh();
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
  function cancelModes() { st.placing = null; st.ghost = null; st.wallStart = null; st.mode = null; refresh(); }

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
    const b = document.createElement('button'); b.dataset.key = key; b.innerHTML = `<span class="lbl">${label}</span><span class="hk">${key}</span>`;
    b.disabled = !!opts.disabled; if (opts.cls) b.className = opts.cls;
    b.onclick = ev => onclick(ev); b.onmouseenter = () => tip && showTip(b, tip); b.onmouseleave = hideTip;
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
          add(button(D.hotkey, D.name, `<b>${D.name}</b> ${costHtml(D.cost)}<br>${D.tip}${need ? `<br><em>Needs a ${DATA.BUILDINGS[D.needs].name}.</em>` : ''}`, () => startPlacing(t), { disabled: need, cls: st.placing === t ? 'on' : '' })); });
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
          add(button(U.hotkey, `Train ${U.name}`, `<b>${U.name}</b> ${costHtml(U.cost)} · ${U.time}s<br>${U.tip}<br><em>Shift-click: 5</em>`, ev => { let n = 0; for (const x of blds) n += W.queueTrain(x, t, ev.shiftKey ? 5 : 1); if (!n) msg(W.players[0].pop >= W.players[0].popCap ? 'Need more housing.' : 'Not enough resources.'); refresh(); })); }
        for (const t of D.researches || []) { const T = DATA.TECHS[t], done = W.players[0].techs.has(t), busy = W.ents.some(e => !e.dead && e.kind === 'building' && e.owner === 0 && e.queue.some(q => q.what === t));
          if (done) continue;
          add(button(T.hotkey, T.name, `<b>${T.name}</b> ${costHtml(T.cost)} · ${T.time}s<br>${T.tip}`, () => { if (!W.queueTech(b, t)) msg('Cannot research that now.'); refresh(); }, { disabled: T.locked || busy, cls: T.locked ? 'locked' : '' })); }
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
    if (W.state !== 'playing' && !st.ended) { st.ended = true; $('end').style.display = 'flex'; $('end-text').textContent = W.state === 'victory' ? 'Victory' : 'Defeat'; }
  }
  return { init, frame, refresh, sel, st, msg, startPlacing };
})();
