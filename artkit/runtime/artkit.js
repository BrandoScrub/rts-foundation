/* artkit.js: draws everything artkit exports, from one assets.json. No dependencies.
   Needs units.js (UnitKit) beside it for animated units; use glcanvas.js for a WebGL main view.

   const lib = {};
   ArtKit.load('art/', assetsJson, lib, () => start());
   // a building, prop or terrain piece; (x, y) is where its footprint's near corner sits on screen
   ArtKit.drawStatic(ctx, lib, 'hab', 'normal', x, y, k);          // stages: 'build33', 'build66', 'damaged', 'ruined'
   ArtKit.drawTurning(ctx, lib, 'hab', 'dish', worldDeg, x, y, k); // a turning part, over drawStatic
   // rotated buildings: pass a facing index as the last argument of both; ArtKit.facingOf(lib, key, i) has its footprint and door
   // a unit: lib[key] is a UnitKit sprite set, so UnitKit.drawFig / troopPose / walkerPose all work on it
   ArtKit.drawUnit(ctx, lib, 'rover', {clip: 'move', frame: f, heading: deg, upperClip: 'fire', upperFrame: g, upperHeading: deg2}, x, y, k);
   k = screen pixels per sprite pixel. Sprites are exported at 0.4 pixels per unit: a game whose tile is T px wide
   draws them at true size with k = T / 64.

   Optional, when the style pack exported them (artkit/team.py, artkit/shadow.py); without them nothing changes:
   // player colours: once after load (and again if colours change), one recoloured copy per player
   ArtKit.teams(lib, [[220, 60, 50], [60, 120, 230]]);
   ArtKit.drawStatic(ctx, lib, 'hab', 'normal', x, y, k, facing, team);   // team = index into that list
   ArtKit.drawTurning(ctx, lib, 'hab', 'dish', deg, x, y, k, facing, team);
   ArtKit.drawUnit(ctx, lib, 'rover', {..., team: 1}, x, y, k);
   // shadows: draw every shadow first, then every sprite, so shadows lie on the ground and never on a neighbour
   ArtKit.drawShadow(ctx, lib, 'hab', 'normal', x, y, k, facing);
   ArtKit.drawUnitShadow(ctx, lib, 'rover', {clip: 'move', frame: f, heading: deg}, x, y, k); */
const ArtKit = (() => {
  'use strict';
  function img(base, src, done) {
    const im = new Image();
    im.onload = () => { if (typeof createImageBitmap === 'function') createImageBitmap(im).then(b => done(b), () => done(im)); else done(im); };
    im.onerror = () => done(null);
    im.src = base + src;
  }
  function load(base, assets, into, onAll) {
    let left = 0; const tick = () => { if (--left === 0 && onAll) onAll(into); };
    for (const key in assets) {
      const a = assets[key];
      if (a.kind === 'static') {
        const o = { m: a, img: {}, mask: {} }; into[key] = o;
        const one = (pre, M) => {                 // a facing's stages and turning parts, with their masks and shadows
          for (const st in M.states) { const S = M.states[st];
            left++; img(base, S.src, b => { o.img[pre + 's:' + st] = b; tick(); });
            if (S.team) { left++; img(base, S.team, b => { o.mask[pre + 's:' + st] = b; tick(); }); }
            if (S.shadow) { left++; img(base, S.shadow.src, b => { o.img[pre + 'h:' + st] = b; tick(); }); } }
          for (const pv in M.turning || {}) { const T = M.turning[pv];
            left++; img(base, T.src, b => { o.img[pre + 't:' + pv] = b; tick(); });
            if (T.team) { left++; img(base, T.team, b => { o.mask[pre + 't:' + pv] = b; tick(); }); } } };
        one('', a);
        (a.facings || []).forEach((f, i) => { if (i) one(i + ':', f); });   // facing 0 is the asset itself
      } else if (typeof UnitKit !== 'undefined') {
        left++; UnitKit.loadOne(base, key, a, into, () => tick());
      }
    }
    if (left === 0 && onAll) onAll(into);
  }
  /* facing: index into the asset's facings (0 = as authored). facingOf(lib, key, i) gives that view's footprint,
     anchors (door tile and the edge it is on) and turn, for placement rules. */
  function facingOf(lib, key, i) { const o = lib[key]; if (!o) return null; const f = o.m.facings; return f ? f[((i | 0) % f.length + f.length) % f.length] : o.m; }
  /* ---- player colours (artkit/team.py): the engine's role-tint rule on finished pixels, weighted by the mask.
     recolourPixels works on raw RGBA bytes (a Uint8ClampedArray) and a mask's bytes (its red channel is read). */
  function recolourPixels(px, mk, col, gain) {
    const g = gain == null ? 1.25 : gain, r = col[0] / 255, gg = col[1] / 255, b = col[2] / 255;
    for (let i = 0; i < px.length; i += 4) {
      const w = mk[i] / 255; if (!w) continue;
      const R = px[i] / 255, G = px[i + 1] / 255, B = px[i + 2] / 255, l = R * .3 + G * .59 + B * .11;
      const tr = Math.min(1, l * r * g), tg = Math.min(1, l * gg * g), tb = Math.min(1, l * b * g);
      px[i] = Math.round(Math.min(1, Math.max(0, R + (tr - R) * w)) * 255);
      px[i + 1] = Math.round(Math.min(1, Math.max(0, G + (tg - G) * w)) * 255);
      px[i + 2] = Math.round(Math.min(1, Math.max(0, B + (tb - B) * w)) * 255);
    }
    return px;
  }
  function canvasOf(w, h) {
    if (typeof OffscreenCanvas === 'function') return new OffscreenCanvas(w, h);
    const c = document.createElement('canvas'); c.width = w; c.height = h; return c;
  }
  function pixelsOf(im) {
    const w = im.width, h = im.height, c = canvasOf(w, h), x = c.getContext('2d', { willReadFrequently: true });
    x.drawImage(im, 0, 0); return x.getImageData(0, 0, w, h);
  }
  function recoloured(im, mask, col, gain) {
    const d = pixelsOf(im); recolourPixels(d.data, pixelsOf(mask).data, col, gain);
    const c = canvasOf(im.width, im.height); c.getContext('2d').putImageData(d, 0, 0); return c;
  }
  /* teams(lib, colours[, gain]): one recoloured copy of every masked picture per colour, made now (load time), so
     drawing in a team colour costs nothing per frame. Pictures without a mask are shared, not copied. */
  function teams(lib, colours, gain) {
    for (const key in lib) {
      const o = lib[key]; if (!o || !o.m) continue;
      const gn = gain == null ? o.m.team_gain : gain;
      if (o.mask && Object.keys(o.mask).length) {
        o.tv = colours.map(col => { const t = {}; for (const n in o.mask) if (o.img[n] && o.mask[n]) t[n] = recoloured(o.img[n], o.mask[n], col, gn); return t; });
      } else if (o.tmask && Object.keys(o.tmask).length) {       // a unit: a view object per team sharing its manifest
        o.tv = colours.map(col => { const img = Object.assign({}, o.img);
          for (const n in o.tmask) if (o.img[n] && o.tmask[n]) img[n] = recoloured(o.img[n], o.tmask[n], col, gn);
          return { m: o.m, img, n: o.n }; });
      }
    }
    return lib;
  }
  const teamImg = (o, name, team) => (team != null && o.tv && o.tv[team] && o.tv[team][name]) || o.img[name];
  function drawShadow(c, lib, key, state, x, y, k, facing) {
    const o = lib[key]; if (!o) return;
    const fi = o.m.facings ? ((facing | 0) % o.m.facings.length + o.m.facings.length) % o.m.facings.length : 0;
    const M = fi ? o.m.facings[fi] : o.m, pre = fi ? fi + ':' : '';
    const st = M.states[state] ? state : 'normal', S = M.states[st].shadow, im = o.img[pre + 'h:' + st];
    if (!S || !im) return;
    const a = S.near_corner || S.origin;
    c.drawImage(im, x - a[0] * k, y - a[1] * k, S.size[0] * k, S.size[1] * k);
  }
  function drawStatic(c, lib, key, state, x, y, k, facing, team) {
    const o = lib[key]; if (!o) return;
    const fi = o.m.facings ? ((facing | 0) % o.m.facings.length + o.m.facings.length) % o.m.facings.length : 0;
    const M = fi ? o.m.facings[fi] : o.m, pre = fi ? fi + ':' : '';
    const st = M.states[state] ? state : 'normal', m = M.states[st], im = teamImg(o, pre + 's:' + st, team);
    if (!im) return;
    const a = m.near_corner || m.origin;
    c.drawImage(im, x - a[0] * k, y - a[1] * k, m.size[0] * k, m.size[1] * k);
  }
  function drawTurning(c, lib, key, pivot, deg, x, y, k, facing, team) {
    const o = lib[key]; if (!o) return;
    const fi = o.m.facings ? ((facing | 0) % o.m.facings.length + o.m.facings.length) % o.m.facings.length : 0;
    const t = (fi ? o.m.facings[fi] : o.m).turning[pivot], im = teamImg(o, (fi ? fi + ':' : '') + 't:' + pivot, team); if (!im) return;
    const n = t.headings, i = ((Math.round(deg / 360 * n) % n) + n) % n, fw = t.frame[0], fh = t.frame[1];
    c.drawImage(im, i * fw, 0, fw, fh, x - t.near_corner[0] * k, y - t.near_corner[1] * k, fw * k, fh * k);
  }
  function hIndex(m, deg) { const n = m.headings; return ((Math.round(deg / 360 * n) % n) + n) % n; }
  function drawUnit(c, lib, key, s, x, y, k) {
    const o0 = lib[key]; if (!o0) return;
    const o = (s.team != null && o0.tv && o0.tv[s.team]) || o0;
    const m = o.m, h = hIndex(m, s.heading || 0);
    const p = { lc: s.clip, lf: s.frame | 0, lh: h, uc: s.upperClip || s.clip, uf: (s.upperFrame == null ? s.frame : s.upperFrame) | 0,
                uh: s.upperHeading == null ? h : hIndex(m, s.upperHeading) };
    const lc = m.clips[p.lc], uc = m.clips[p.uc];
    if (m.layers.L && !(lc.rects || lc.files).L) p.lc = Object.keys(m.clips).find(n => (m.clips[n].rects || m.clips[n].files).L);
    if (m.layers.U && !(uc.rects || uc.files).U) p.uc = p.lc;
    p.lf %= m.clips[p.lc].frames; p.uf %= m.clips[p.uc].frames;
    UnitKit.drawFig(c, o, p, x, y, k);
  }
  /* the unit's shadow layer "S" (artkit/shadow.py), following the legs' clip, frame and heading; nothing if none */
  function drawUnitShadow(c, lib, key, s, x, y, k) {
    const o = lib[key]; if (!o || !o.m.layers || !o.m.layers.S) return;
    const m = o.m; let cl = s.clip; const cc = m.clips[cl];
    if (!cc || !(cc.rects || cc.files).S) cl = Object.keys(m.clips).find(n => (m.clips[n].rects || m.clips[n].files).S);
    if (!cl) return;
    UnitKit.drawLayer(c, o, 'S', cl, (s.frame | 0) % m.clips[cl].frames, hIndex(m, s.heading || 0), x, y, k);
  }
  /* which frame of a clip: by distance moved for clips with a stride (feet and wheels never slide), else by time */
  function frameOf(m, clip, t, dist, k) {
    const c = m.clips[clip];
    if (c.stride_units && dist != null) {
      const px = c.stride_units * m.scale * k;
      return Math.floor(((dist / px) % 1 + 1) % 1 * c.frames);
    }
    const f = Math.floor(t * c.fps);
    return c.loop ? f % c.frames : Math.min(f, c.frames - 1);
  }
  return { load, drawStatic, drawTurning, drawUnit, frameOf, facingOf, teams, recolourPixels, drawShadow, drawUnitShadow };
})();
if (typeof module !== 'undefined') module.exports = ArtKit;
