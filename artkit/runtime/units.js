/* unitkit runtime: draws unitkit sprite strips in any 2D canvas game. No dependencies, no game globals.

   Strips: one image per clip and layer; row = heading (world angle, 360/n steps from +x), column = frame.
   A layered unit has legs (L) and torso (U) strips; a plain unit has one (F).
   World: x and y on the ground, screen = (x - y, (x + y)/2). Positions passed in are in world pixels.

   Use:
     const sprites = {};
     UnitKit.load('art/', manifestsByKey, sprites);          // sprites[key] appears when all its images are in
     const mem = UnitKit.mem(entity);                        // per-entity memory, kept outside your save data
     const p = UnitKit.troopPose(sprites[key], mem, {x, y, aim, t, since, inside, id}, k);
     UnitKit.drawFig(ctx, sprites[key], p, screenX, screenY, k);
   k is the draw scale: screen pixels per strip pixel. Feet stay planted only if the same k scales the ground,
   i.e. the unit is drawn at the size its world movement implies (see PIPELINE.md, "Scale").            */
const UnitKit = (() => {
  const TAU = Math.PI * 2, MEM = new WeakMap();
  const mem = e => { let m = MEM.get(e); if (!m) MEM.set(e, m = {}); return m; };

  /* load one unit's strips: sprites[key] appears when all its images are in. Large or rarely seen units can be
     loaded the first time they are wanted, so they cost no memory until then. */
  function loadOne(base, key, m, into, onReady) {
      const o = { m, img: {}, n: 0 }; let tot = 0;
      if (m.pack) { /* packed by artdirector/pack_units.py: a few tight pages instead of one strip per clip */
        const tp = m.team_pack || [], all = m.pack.length + tp.length;   // team masks: same layout, same rects (artkit/team.py)
        if (tp.length) o.tmask = {};
        const done = () => { if (++o.n === all) { into[key] = o; if (onReady) onReady(key, o); } };
        const page = (src, put) => {
          const im = new Image();
          im.onload = () => { if (typeof createImageBitmap === 'function') createImageBitmap(im).then(bm => { put(bm); done(); }, done); else done(); };
          im.src = base + src; put(im);
        };
        m.pack.forEach((src, i) => page(src, b => { o.img['p' + i] = b; }));
        tp.forEach((src, i) => page(src, b => { o.tmask['p' + i] = b; }));
        return;
      }
      for (const cn in m.clips) if (m.clips[cn].team) { o.tmask = o.tmask || {}; tot += Object.keys(m.clips[cn].team).length; }
      for (const cn in m.clips) for (const L in m.clips[cn].files) {
        tot++; const im = new Image();
        /* decode each strip once, up front, into a bitmap: a plain Image is decoded lazily on first draw and can be thrown away and decoded again, which shows as hitches */
        const done = () => { if (++o.n === tot) { into[key] = o; if (onReady) onReady(key, o); } };
        im.onload = () => { if (typeof createImageBitmap === 'function') createImageBitmap(im).then(bm => { o.img[cn + L] = bm; done(); }, done); else done(); };
        im.src = base + m.clips[cn].files[L]; o.img[cn + L] = im;
        const tf = m.clips[cn].team && m.clips[cn].team[L];
        if (tf) { const mi = new Image(); mi.onload = () => { o.tmask[cn + L] = mi; done(); }; mi.onerror = done; mi.src = base + tf; }
      }
  }

  function load(base, manifests, into, onReady) {
    for (const key in manifests) loadOne(base, key, manifests[key], into, onReady);
    return into;
  }

  /* where a named point (steam vent, foot...) is this frame, in strip pixels from the unit's ground anchor.
     layer 'L' reads it off the legs; otherwise it is read off the torso clip and carried by the waist socket */
  function mark(o, p, name, layer) {
    const m = o.m.clips, u = m[p.uc], l = m[p.lc];
    if (layer !== 'L' && u.marks && u.marks[name]) {
      const a = l.socket[p.lh][p.lf], b = u.socket[p.uh][p.uf], q = u.marks[name][p.uh][p.uf];
      return [q[0] + a[0] - b[0], q[1] + a[1] - b[1]];
    }
    return l.marks && l.marks[name] ? l.marks[name][p.lh][p.lf] : null;
  }

  const head = (a, o) => { const n = o.m.heading_world_deg.length; return ((Math.round(a / (TAU / n)) % n) + n) % n; };

  function drawLayer(c, o, L, clip, fr, h, x, y, k) {
    const ly = o.m.layers[L], fw = ly.frame[0], fh = ly.frame[1], cl = o.m.clips[clip];
    if (cl.rects) {
      const a = cl.rects[L], i = (h * cl.frames + fr) * 7;
      if (a[i + 3]) c.drawImage(o.img['p' + a[i]], a[i + 1], a[i + 2], a[i + 3], a[i + 4], x + (a[i + 5] - ly.anchor[0]) * k, y + (a[i + 6] - ly.anchor[1]) * k, a[i + 3] * k, a[i + 4] * k);
      return;
    }
    c.drawImage(o.img[clip + L], fr * fw, h * fh, fw, fh, x - ly.anchor[0] * k, y - ly.anchor[1] * k, fw * k, fh * k);
  }

  /* p = {lc, lf, lh, uc, uf, uh}: legs clip/frame/heading and torso clip/frame/heading. The torso is stood on the
     legs' waist socket, so the two may come from different clips and face different ways. */
  function drawFig(c, o, p, x, y, k) {
    const m = o.m;
    if (!m.layers.L) { drawLayer(c, o, 'F', p.lc, p.lf, p.lh, x, y, k); return; }
    drawLayer(c, o, 'L', p.lc, p.lf, p.lh, x, y, k);
    const a = m.clips[p.lc].socket[p.lh][p.lf], b = m.clips[p.uc].socket[p.uh][p.uf];
    drawLayer(c, o, 'U', p.uc, p.uf, p.uh, x + (a[0] - b[0]) * k, y + (a[1] - b[1]) * k, k);
  }

  /* ground covered by one cycle of a gait, in world pixels */
  const stridePx = (o, clip, k) => Math.abs(o.m.clips[clip].stride_units) * o.m.scale * k;

  /* walk or run: whichever's natural pace is nearer the speed v (world px/s), with a bias to the current one */
  function gaitPick(o, me, v, k) {
    const m = o.m.clips; if (!me.gc) me.gc = m.run ? 'run' : 'walk';
    if (m.walk && m.run && v > 0) {
      const cost = c => Math.abs(Math.log(v / stridePx(o, c, k) * m[c].cycle_s)) - (c === me.gc ? .25 : 0);
      me.gc = cost('run') < cost('walk') ? 'run' : 'walk';
    }
    return me.gc;
  }

  /* how far and which way the entity really moved since it was last drawn; returns the distance */
  function motion(me, x, y, t, aim) {
    if (me.t === undefined || t < me.t || t - me.t > .5) { me.t = t; me.x = x; me.y = y; me.rx = x; me.ry = y; me.v = 0; me.md = aim; if (me.gp === undefined) me.gp = 0; }
    const dt = t - me.t; let dd = Math.hypot(x - me.x, y - me.y);
    if (dd > 24) { dd = 0; me.rx = x; me.ry = y; }                      // a jump (teleport, garrison) is not a step
    me.x = x; me.y = y; me.t = t;
    if (dt > 1e-4) me.v = me.v * .7 + dd / dt * .3;
    const rx = x - me.rx, ry = y - me.ry;
    if (rx * rx + ry * ry > 6.25) { me.md = Math.atan2(ry, rx); me.rx = x; me.ry = y; }
    return dd;
  }

  /* A soldier with clips idle, walk, run, back, aim, fire.
     st: x, y world px; aim = facing/aim angle; t = game time; since = seconds since its last shot (big if never);
         inside = garrisoned (stands and aims); id = any number, staggers the idle.
     Legs follow real movement; the torso follows the action. Within `combat` seconds of a shot a moving soldier keeps
     his torso on the target: forward gait if he moves toward it, the back gait facing away from travel otherwise. */
  function troopPose(o, me, st, k) {
    const m = o.m.clips, F = m.fire, ah = head(st.aim, o), since = st.since, t = st.t;
    const fwin = F.loop ? F.frames / F.fps + .08 : (F.frames - 1) / F.fps, firing = since >= 0 && since < fwin;
    const fireF = F.loop ? Math.floor(since * F.fps) % F.frames : Math.min(F.frames - 1, 1 + Math.floor(since * F.fps));
    const hold = m.aim.frames - 1, combatFor = Math.max(.8, fwin + .3);
    const dd = st.inside ? 0 : motion(me, st.x, st.y, t, st.aim), moving = !st.inside && me.v > 3;
    const p = { lc: 'idle', lf: 0, lh: ah, uc: 'idle', uf: 0, uh: ah };
    if (moving) {
      const combat = since >= 0 && since < combatFor;
      let rel = me.md - st.aim; rel = Math.atan2(Math.sin(rel), Math.cos(rel));
      if (combat && m.back && Math.abs(rel) > 1.75) { p.lc = 'back'; p.lh = head(me.md + Math.PI, o); }
      else { p.lc = gaitPick(o, me, me.v, k); p.lh = head(me.md, o); }
      me.gp = (((me.gp + dd / stridePx(o, p.lc, k)) % 1) + 1) % 1;
      p.lf = Math.floor(me.gp * m[p.lc].frames) % m[p.lc].frames;
      if (firing) { p.uc = 'fire'; p.uf = fireF; }
      else if (combat) { p.uc = 'aim'; p.uf = hold; }
      else { p.uc = p.lc; p.uf = p.lf; p.uh = p.lh; }
    }
    else if (firing) { p.lc = p.uc = 'fire'; p.lf = p.uf = fireF; }
    else if ((since >= 0 && since < 2.5) || st.inside) { p.lc = p.uc = 'aim'; p.lf = p.uf = hold; }
    else if (since >= 0 && since < 2.9) { p.lc = p.uc = 'aim'; p.lf = p.uf = Math.max(0, hold - Math.floor((since - 2.5) / .4 * m.aim.frames)); }
    else p.lf = p.uf = Math.floor((t * m.idle.fps + (st.id || 0) * 3) % m.idle.frames);
    if (!(m[p.lc].rects || m[p.lc].files).L) { p.lc = 'idle'; p.lf = 0; }                    // a torso-only clip: the legs just stand
    if (o.m.free_torso) { if (moving) me.lh = p.lh; else if (me.lh !== undefined) p.lh = me.lh; }   // stands where it stopped
    return p;
  }

  /* A single-layer creature with clips walk [, run], hit.
     st: dist = total distance it has walked (world px), a = facing, t, moving, hit (flinching), attack (striking),
         stateless = true to pick the walk frame from dist alone (for sprite caches). */
  function walkerPose(o, me, st, k) {
    const m = o.m.clips, p = { lc: 'walk', lf: 0, lh: head(st.a, o) };
    if (m.attack && st.since >= 0 && st.since < m.attack.frames / m.attack.fps) { p.lc = 'attack'; p.lf = Math.floor(st.since * m.attack.fps); }
    else if (st.hit) { p.lc = 'hit'; p.lf = 1; }
    else if (st.moving) {
      if (st.stateless) p.lf = Math.floor(((st.dist / stridePx(o, 'walk', k)) % 1 + 1) % 1 * m.walk.frames) % m.walk.frames;
      else {
        if (me.t === undefined || st.t < me.t || st.t - me.t > .4 || st.dist < me.d) { me.d = st.dist; me.t = st.t; me.v = -1; if (me.gp === undefined) me.gp = 0; }
        const dd = st.dist - me.d, dt = st.t - me.t; me.d = st.dist; me.t = st.t;
        if (dt > 1e-4) { const v = dd / dt; me.v = me.v < 0 ? v : me.v * .85 + v * .15; }
        p.lc = gaitPick(o, me, me.v, k);
        me.gp = (((me.gp + dd / stridePx(o, p.lc, k)) % 1) + 1) % 1;
        p.lf = Math.floor(me.gp * m[p.lc].frames) % m[p.lc].frames;
      }
    }
    else if (st.attack && m.hit) { p.lc = 'hit'; p.lf = 2; }
    else if (m.idle) { p.lc = 'idle'; p.lf = Math.floor((st.t * m.idle.fps + (st.id || 0) * 3) % m.idle.frames); }
    return p;
  }

  return { load, loadOne, mark, mem, head, drawLayer, drawFig, stridePx, gaitPick, motion, troopPose, walkerPose };
})();
