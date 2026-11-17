/* glcanvas.js: the Canvas 2D drawing calls the game uses, carried out by WebGL2 in large batches.

   Why: a 2D canvas hands the GPU a separate job nearly every time the source image changes, and the
   world is drawn in depth order, so the image changes constantly. Here every draw goes into one vertex
   buffer, up to 15 textures are bound at once, and each vertex says which texture it reads. Thousands
   of draws in depth order become a handful of GPU calls, and the game's drawing code does not change.

   Use:  const ctx = GLCanvas.create(canvas);   // a WebGL object, or a plain 2D context as the fallback
         ... draw exactly as on a 2D context ...
         if (ctx.endFrame) ctx.endFrame();      // once a frame, after the last draw

   Fallback to plain 2D: no WebGL2, software-only WebGL, a shader that will not build, ?gl=0 in the
   address, or localStorage 'bb-renderer' = '2d'. ?gl=force accepts software WebGL (for tests).

   Supported: drawImage, paths (lines, arcs, ellipses, curves), fill, stroke with dashes and caps,
   fillRect, strokeRect, text, linear and radial gradients, transforms, save/restore, globalAlpha,
   source-over / lighter / multiply. Other composite modes draw as source-over and warn once. clip() is
   not supported on this context (nothing in the game clips the main view).
   Offscreen canvases stay real 2D canvases. Their edits are noticed automatically and re-uploaded.
   Images up to 256 px share atlas pages automatically; one that keeps changing moves to its own texture. */
const GLCanvas = (() => {
  'use strict';
  const MAXV = 65000, MAXI = 180000, STRIDE = 6, MAX_STOPS = 6, TEX_BUDGET = 800 * 1048576, TAU = Math.PI * 2;
  /* small images share a few GPU pages, so a crowd of different small sprites stays in one batch */
  const PAGE = 2048, PAGES_MAX = 6, SMALL = 256, GUTTER = 2;

  /* ---- colours ---- */
  const COLS = new Map();
  let scratch = null;
  const scr = () => scratch || (scratch = document.createElement('canvas').getContext('2d'));
  const num = s => s.endsWith('%') ? parseFloat(s) * 2.55 : parseFloat(s);
  function parseColor(s) {
    if (s.charCodeAt(0) === 35) {
      let h = s.slice(1);
      if (h.length < 6) h = [...h].map(c => c + c).join('');
      const v = parseInt(h.slice(0, 6), 16);
      return [v >> 16 & 255, v >> 8 & 255, v & 255, h.length > 6 ? parseInt(h.slice(6, 8), 16) / 255 : 1];
    }
    if (s.startsWith('rgb')) {
      const m = s.match(/-?[\d.]+(?:e[-+]?\d+)?%?/gi);  /* generated alphas can come out like 1.2e-16 */
      if (m && m.length >= 3) {
        const a = m.length > 3 ? (m[3].endsWith('%') ? parseFloat(m[3]) / 100 : parseFloat(m[3])) : 1;
        return [num(m[0]), num(m[1]), num(m[2]), a <= 0 ? 0 : a >= 1 ? 1 : a];
      }
    }
    const g = scr(); g.fillStyle = '#000'; g.fillStyle = s;
    const out = g.fillStyle;
    return out === s ? [0, 0, 0, 1] : parseColor(out);
  }
  function colorOf(s) {
    let c = COLS.get(s);
    if (!c) { c = parseColor(String(s)); if (COLS.size > 6000) COLS.clear(); COLS.set(s, c); }
    return c;
  }
  const clamp255 = v => v <= 0 ? 0 : v >= 255 ? 255 : v | 0;
  function premult(c, ga) {
    const a = c[3] * ga, r = clamp255(c[0] * a), g = clamp255(c[1] * a), b = clamp255(c[2] * a), A = clamp255(a * 255);
    return ((A << 24) | (b << 16) | (g << 8) | r) >>> 0;
  }

  /* ---- shaders ---- */
  const VS = `#version 300 es
layout(location=0) in vec2 aP; layout(location=1) in vec2 aU; layout(location=2) in vec4 aC; layout(location=3) in float aT;
uniform vec2 uRes; uniform float uZ; out vec2 vU; out vec4 vC; flat out int vT;
void main(){vU=aU;vC=aC;vT=int(floor(aT+.5));gl_Position=vec4(aP.x/uRes.x*2.-1.,1.-aP.y/uRes.y*2.,uZ*aU.x,1.);}`;
  const fsBatch = n => {
    let chain = '';
    for (let i = 0; i < n; i++) chain += `${i ? 'else ' : ''}if(vT==${i})c=texture(uS[${i}],vU);\n`;
    return `#version 300 es
precision mediump float; precision mediump int;
uniform sampler2D uS[${n}]; in vec2 vU; in vec4 vC; flat in int vT; out vec4 o;
void main(){vec4 c=vec4(1.);if(vT>=0){${chain}}o=c*vC;}`;
  };
  const FS_GRAD = `#version 300 es
precision highp float;
uniform int uK,uN; uniform vec4 uA; uniform vec2 uR; uniform vec4 uC[${MAX_STOPS}]; uniform float uO[${MAX_STOPS}];
in vec2 vU; in vec4 vC; out vec4 o;
void main(){float t;
 if(uK==0){vec2 d=uA.zw-uA.xy;float q=dot(d,d);t=q>0.?dot(vU-uA.xy,d)/q:0.;}
 else{t=(length(vU-uA.xy)-uR.x)/max(uR.y-uR.x,1e-6);}
 t=clamp(t,0.,1.);vec4 c=uC[0];
 if(t>=uO[uN-1])c=uC[uN-1];
 else for(int i=1;i<uN;i++){if(t<uO[i]){float s=(t-uO[i-1])/max(uO[i]-uO[i-1],1e-6);c=mix(uC[i-1],uC[i],s);break;}}
 c.rgb*=c.a;o=c*vC.a;}`;
  function shader(gl, type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader failed');
    return s;
  }
  function program(gl, fs) {
    const p = gl.createProgram();
    gl.attachShader(p, shader(gl, gl.VERTEX_SHADER, VS)); gl.attachShader(p, shader(gl, gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link failed');
    return p;
  }

  /* offscreen canvases mark themselves changed, so the GPU copy is refreshed the next time it is drawn */
  let patched = false;
  function watchCanvases() {
    if (patched) return; patched = true;
    const P = CanvasRenderingContext2D.prototype;
    for (const n of ['drawImage', 'fillRect', 'clearRect', 'putImageData', 'fill', 'stroke', 'fillText', 'strokeText']) {
      const o = P[n];
      P[n] = function () { const c = this.canvas; c._gv = (c._gv | 0) + 1; return o.apply(this, arguments); };
    }
  }

  class Grad {
    constructor(k, a, r) { this.k = k; this.a = a; this.r = r; this.s = []; }
    addColorStop(o, c) { this.s.push([+o, colorOf(c)]); }
  }

  class GLCtx {
    constructor(cv, gl) {
      this.canvas = cv; this.gl = gl; this.isGL = true;
      this.fillStyle = '#000'; this.strokeStyle = '#000'; this.globalAlpha = 1; this.lineWidth = 1;
      this.lineCap = 'butt'; this.lineJoin = 'miter'; this.miterLimit = 10; this.font = '10px sans-serif';
      this.textAlign = 'start'; this.textBaseline = 'alphabetic'; this.globalCompositeOperation = 'source-over';
      this.imageSmoothingEnabled = true; this.imageSmoothingQuality = 'low'; this.shadowBlur = 0; this.shadowColor = 'rgba(0,0,0,0)';
      this.lineDashOffset = 0; this._d = null; this.a = 1; this.b = 0; this.c = 0; this.d = 1; this.e = 0; this.f = 0;
      this._st = [];
      this.px = []; this.ss = []; this.cl = [];
      this.buf = new ArrayBuffer(MAXV * STRIDE * 4); this.F = new Float32Array(this.buf); this.U = new Uint32Array(this.buf);
      this.I = new Uint16Array(MAXI); this.n = 0; this.ni = 0;
      this.frame = 1; this.batch = 1; this.gen = 0; this.bytes = 0; this.ents = new Set(); this.text = new Map();
      this.stats = { calls: 0, verts: 0, uploads: 0, gpu: null, on: false };
      this.stat = { calls: 0, verts: 0, uploads: 0 };
      this.grad = null; this.warned = {}; this.q = []; this.warm = [];
      this._setup();
      cv.addEventListener('webglcontextlost', e => { e.preventDefault(); this.lost = true; });
      cv.addEventListener('webglcontextrestored', () => { this.lost = false; this._setup(); });
    }

    _setup() {
      const gl = this.gl;
      const units = Math.min(16, gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS));
      this.nslot = units - 1; this.upUnit = units - 1;  /* one unit is kept free for uploads */
      this.gen++; this.ents.clear(); this.bytes = 0; this.text.clear(); this.pages = [];
      this.slots = new Array(this.nslot).fill(null); this.bound = new Array(this.nslot).fill(null); this.ns = 0;
      this.pB = program(gl, fsBatch(this.nslot)); this.pG = program(gl, FS_GRAD);
      this.uG = {}; for (const u of ['uRes', 'uK', 'uN', 'uA', 'uR', 'uC', 'uO']) this.uG[u] = gl.getUniformLocation(this.pG, u);
      this.uRes = gl.getUniformLocation(this.pB, 'uRes'); this.uZ = gl.getUniformLocation(this.pB, 'uZ'); this.zrun = false; this.inU = false;
      gl.useProgram(this.pB);
      gl.uniform1iv(gl.getUniformLocation(this.pB, 'uS'), Array.from({ length: this.nslot }, (_, i) => i));
      this.prog = this.pB;
      this.vb = gl.createBuffer(); this.ib = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vb); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.ib);
      const s = STRIDE * 4;
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, s, 0);
      gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 2, gl.FLOAT, false, s, 8);
      gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 4, gl.UNSIGNED_BYTE, true, s, 16);
      gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 1, gl.FLOAT, false, s, 20);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); this.bl = 'source-over';
      gl.disable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
      this.vw = this.vh = 0;
      this.tq = gl.getExtension('EXT_disjoint_timer_query_webgl2'); this.tqOpen = null; this.tqQ = [];
    }

    /* ---- state ---- */
    save() {
      this._st.push({
        fs: this.fillStyle, ss: this.strokeStyle, ga: this.globalAlpha, lw: this.lineWidth, lc: this.lineCap, lj: this.lineJoin,
        fo: this.font, ta: this.textAlign, tb: this.textBaseline, co: this.globalCompositeOperation, sm: this.imageSmoothingEnabled,
        sb: this.shadowBlur, sc: this.shadowColor, ld: this.lineDashOffset, d_: this._d,
        a: this.a, b: this.b, c: this.c, d: this.d, e: this.e, f: this.f
      });
    }
    restore() {
      const s = this._st.pop(); if (!s) return;
      this.fillStyle = s.fs; this.strokeStyle = s.ss; this.globalAlpha = s.ga; this.lineWidth = s.lw; this.lineCap = s.lc; this.lineJoin = s.lj;
      this.font = s.fo; this.textAlign = s.ta; this.textBaseline = s.tb; this.globalCompositeOperation = s.co; this.imageSmoothingEnabled = s.sm;
      this.shadowBlur = s.sb; this.shadowColor = s.sc; this.lineDashOffset = s.ld; this._d = s.d_;
      this.a = s.a; this.b = s.b; this.c = s.c; this.d = s.d; this.e = s.e; this.f = s.f;
    }
    setTransform(a, b, c, d, e, f) { this.a = a; this.b = b; this.c = c; this.d = d; this.e = e; this.f = f; }
    resetTransform() { this.setTransform(1, 0, 0, 1, 0, 0); }
    transform(a, b, c, d, e, f) {
      const A = this.a, B = this.b, C = this.c, D = this.d;
      this.a = A * a + C * b; this.b = B * a + D * b; this.c = A * c + C * d; this.d = B * c + D * d;
      this.e += A * e + C * f; this.f += B * e + D * f;
    }
    translate(x, y) { this.e += this.a * x + this.c * y; this.f += this.b * x + this.d * y; }
    scale(x, y) { this.a *= x; this.b *= x; this.c *= y; this.d *= y; }
    rotate(r) { const s = Math.sin(r), c = Math.cos(r); this.transform(c, s, -s, c, 0, 0); }
    setLineDash(a) { this._d = a && a.length ? a.slice() : null; }
    getLineDash() { return this._d ? this._d.slice() : []; }
    measureText(s) { const g = scr(); g.font = this.font; return g.measureText(s); }
    _sc() { return Math.max(Math.hypot(this.a, this.b), Math.hypot(this.c, this.d)); }

    /* ---- batching ---- */
    _blend() {
      const m = this.globalCompositeOperation;
      if (m === this.bl) return;
      this.flush();
      const gl = this.gl;
      if (m === 'lighter') gl.blendFunc(gl.ONE, gl.ONE);
      else if (m === 'multiply') gl.blendFunc(gl.DST_COLOR, gl.ONE_MINUS_SRC_ALPHA);
      else {
        gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        if (m !== 'source-over' && !this.warned[m]) { this.warned[m] = 1; console.warn('glcanvas: composite mode not supported on the main view:', m); }
      }
      this.bl = m;
    }
    _room(v, i) { if (this.zrun && !this.inU) this._endZ(); if (this.n + v > MAXV || this.ni + i > MAXI) this.flush(); }
    _v(x, y, u, v, c, t) {
      const i = this.n * STRIDE, F = this.F;
      F[i] = x; F[i + 1] = y; F[i + 2] = u; F[i + 3] = v; this.U[i + 4] = c; F[i + 5] = t;
      return this.n++;
    }
    _tri(a, b, c) { const I = this.I, k = this.ni; I[k] = a; I[k + 1] = b; I[k + 2] = c; this.ni = k + 3; }

    flush() {
      if (!this.ni || this.lost) { this.n = this.ni = 0; this._nextBatch(); return; }
      const gl = this.gl, cv = this.canvas;
      if (cv.width !== this.vw || cv.height !== this.vh) { this.vw = cv.width; this.vh = cv.height; gl.viewport(0, 0, this.vw, this.vh); this.resDirty = (this.resDirty | 0) + 1; }
      const p = this.grad ? this.pG : this.pB;
      if (p !== this.prog) { gl.useProgram(p); this.prog = p; }
      if (p === this.pB) {
        gl.uniform2f(this.uRes, this.vw, this.vh); gl.uniform1f(this.uZ, this.zrun ? 1 : 0);
        for (let i = 0; i < this.ns; i++) {
          if (this.bound[i] !== this.slots[i]) { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, this.slots[i]); this.bound[i] = this.slots[i]; }
        }
      } else {
        const g = this.grad, u = this.uG, st = g._s;
        gl.uniform2f(u.uRes, this.vw, this.vh); gl.uniform1i(u.uK, g.k); gl.uniform1i(u.uN, st.n);
        gl.uniform4fv(u.uA, g.a); gl.uniform2fv(u.uR, g.r); gl.uniform4fv(u.uC, st.c); gl.uniform1fv(u.uO, st.o);
      }
      gl.bufferData(gl.ARRAY_BUFFER, this.F.subarray(0, this.n * STRIDE), gl.STREAM_DRAW);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, this.I.subarray(0, this.ni), gl.STREAM_DRAW);
      gl.drawElements(gl.TRIANGLES, this.ni, gl.UNSIGNED_SHORT, 0);
      this.stat.calls++; this.stat.verts += this.n;
      this.n = this.ni = 0; this._nextBatch();
    }
    _nextBatch() { this.batch++; this.ns = 0; }

    endFrame() {
      if (this.zrun) this._endZ();
      this.flush();
      const s = this.stats, t = this.stat;
      s.calls = t.calls; s.verts = t.verts; s.uploads = t.uploads; t.calls = t.verts = t.uploads = 0;
      s.tex = this.ents.size + this.pages.length; s.mb = this.bytes / 1048576;
      this._timer();
      this.frame++;
      /* sprite sheets are sent to the GPU a few at a time after loading, so no sheet stalls the frame it first appears in */
      for (let i = 0; i < 2 && this.warm.length; i++) {
        const im = this.warm.shift(), W = im.naturalWidth || im.width, H = im.naturalHeight || im.height;
        if (W && H) this._entry(im, W, H);
      }
      if (this.bytes > TEX_BUDGET) this._evict();
    }
    _timer() {
      const gl = this.gl, T = this.tq, s = this.stats;
      if (!T || !s.on) { if (this.tqOpen) { gl.endQuery(T.TIME_ELAPSED_EXT); this.tqOpen = null; } return; }
      if (this.tqOpen) { gl.endQuery(T.TIME_ELAPSED_EXT); this.tqQ.push(this.tqOpen); this.tqOpen = null; }
      while (this.tqQ.length && gl.getQueryParameter(this.tqQ[0], gl.QUERY_RESULT_AVAILABLE)) {
        const q = this.tqQ.shift();
        if (!gl.getParameter(T.GPU_DISJOINT_EXT)) s.gpu = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
        gl.deleteQuery(q);
      }
      if (this.tqQ.length < 8) { this.tqOpen = gl.createQuery(); gl.beginQuery(T.TIME_ELAPSED_EXT, this.tqOpen); }
    }
    _evict() {
      const list = [...this.ents].filter(e => e.used < this.frame - 300).sort((a, b) => a.used - b.used);
      for (const e of list) { if (this.bytes <= TEX_BUDGET * .85) break; this._free(e); }
    }
    _free(e) {
      if (e.pg) { const L = e.pg.list, i = L.indexOf(e); if (i >= 0) L.splice(i, 1); e.tex = null; e.pg = null; return; }
      if (e.tex) this.gl.deleteTexture(e.tex);
      for (let i = 0; i < this.nslot; i++) if (this.bound[i] === e.tex) this.bound[i] = null;
      e.tex = null; this.bytes -= e.w * e.h * 4; this.ents.delete(e);
    }

    /* the GPU copy of a source image, made or refreshed as needed */
    _entry(src, W, H) {
      const ver = src._gv | 0, near = !this.imageSmoothingEnabled;
      let e = src._glt;
      if (!e || !e.tex || e.gen !== this.gen) e = this._make(src, W, H, near);
      if (e.pg && (near || e.w !== W || e.h !== H || (e.ver >= 0 && e.ver !== ver && e.changes > 0))) {
        /* the atlas is linear-filtered and fixed-size, and re-copying a busy canvas with its gutter is wasteful */
        this._free(e);
        e = this._own(src, W, H);
      }
      if (e.pg) {
        if (e.ver !== ver) { if (e.ver >= 0) e.changes++; this._blit(e, src); e.ver = ver; }
      } else if (e.ver !== ver || e.w !== W || e.h !== H) { this._upload(e, src, W, H); e.ver = ver; }
      return e;
    }
    _make(src, W, H, near) {
      if (!near && W <= SMALL && H <= SMALL) { const e = this._place(src, W, H); if (e) return e; }
      return this._own(src, W, H);
    }
    _own(src, W, H) {
      const gl = this.gl;
      const e = { tex: gl.createTexture(), gen: this.gen, ver: -1, w: 0, h: 0, near: false, used: this.frame, slot: 0, sb: 0, pg: null };
      src._glt = e; this.ents.add(e);
      gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, e.tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return e;
    }
    _upload(e, src, W, H) {
      const gl = this.gl;
      gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, e.tex);
      if (e.w === W && e.h === H) gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, src);
      else {
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
        this.bytes += (W * H - e.w * e.h) * 4; e.w = W; e.h = H;
      }
      this.stat.uploads++;
    }

    /* ---- atlas pages for small images ---- */
    _newPage() {
      const gl = this.gl, tex = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, PAGE, PAGE, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      const pg = { tex, shelves: [], top: 0, list: [], used: this.frame, slot: 0, sb: 0 };
      this.pages.push(pg); this.bytes += PAGE * PAGE * 4;
      return pg;
    }
    /* rows of similar height, heights rounded up to 8 px */
    _fit(pg, bw, bh) {
      const rh = Math.ceil(bh / 8) * 8;
      for (const r of pg.shelves) if (r.h >= rh && r.h <= rh * 1.5 && r.x + bw <= PAGE) { const x = r.x; r.x += bw; return [x, r.y]; }
      if (pg.top + rh > PAGE) return null;
      const r = { y: pg.top, h: rh, x: bw };
      pg.shelves.push(r); pg.top += rh;
      return [0, r.y];
    }
    _place(src, W, H) {
      const bw = W + GUTTER * 2, bh = H + GUTTER * 2;
      let pg = null, at = null;
      for (let i = this.pages.length - 1; i >= 0 && !at; i--) { at = this._fit(this.pages[i], bw, bh); if (at) pg = this.pages[i]; }
      if (!at) {
        if (this.pages.length < PAGES_MAX) pg = this._newPage();
        else {
          /* all pages full: reuse the one drawn from longest ago, or give up if every page is on screen now */
          pg = this.pages.reduce((a, b) => b.used < a.used ? b : a);
          if (pg.used >= this.frame) return null;
          this._resetPage(pg);
        }
        at = this._fit(pg, bw, bh);
      }
      const e = { tex: pg.tex, gen: this.gen, ver: -1, w: W, h: H, near: false, used: this.frame, slot: 0, sb: 0, pg, x: at[0] + GUTTER, y: at[1] + GUTTER, changes: 0 };
      pg.list.push(e);
      src._glt = e;
      return e;
    }
    _resetPage(pg) {
      this.flush();
      const gl = this.gl;
      for (const e of pg.list) { e.tex = null; e.pg = null; }
      pg.list = []; pg.shelves = []; pg.top = 0;
      gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, pg.tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, PAGE, PAGE, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    }
    /* the image goes down five times, shifted a pixel each way, so edge pixels repeat outward as they would on a texture of their own */
    _blit(e, src) {
      const gl = this.gl;
      gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, e.tex);
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [0, 0]]) gl.texSubImage2D(gl.TEXTURE_2D, 0, e.x + dx, e.y + dy, gl.RGBA, gl.UNSIGNED_BYTE, src);
      this.stat.uploads++;
    }
    _slot(src, W, H) {
      const e = this._entry(src, W, H), near = !this.imageSmoothingEnabled;
      e.used = this.frame;
      const h = e.pg || e;
      if (e.pg) e.pg.used = this.frame;
      else if (e.near !== near) {
        if (e.sb === this.batch) this.flush();
        const gl = this.gl, f = near ? gl.NEAREST : gl.LINEAR;
        gl.activeTexture(gl.TEXTURE0 + this.upUnit); gl.bindTexture(gl.TEXTURE_2D, e.tex);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
        e.near = near;
      }
      this._e = e;
      if (h.sb === this.batch) return h.slot;
      if (this.ns >= this.nslot) this.flush();
      this.slots[this.ns] = h.tex; h.slot = this.ns++; h.sb = this.batch;
      return h.slot;
    }

    /* ---- images ---- */
    drawImage(src, a1, a2, a3, a4, a5, a6, a7, a8) {
      const W = src.naturalWidth || src.videoWidth || src.width, H = src.naturalHeight || src.videoHeight || src.height;
      if (!W || !H) return;
      const ga = this.globalAlpha; if (!(ga > 0)) return;
      let sx = 0, sy = 0, sw = W, sh = H, dx, dy, dw, dh;
      const n = arguments.length;
      if (n === 3) { dx = a1; dy = a2; dw = W; dh = H; }
      else if (n === 5) { dx = a1; dy = a2; dw = a3; dh = a4; }
      else { sx = a1; sy = a2; sw = a3; sh = a4; dx = a5; dy = a6; dw = a7; dh = a8; }
      const A = clamp255(ga * 255);
      this._blend();
      this._quad(src, W, H, sx, sy, sw, sh, dx, dy, dw, dh, ((A << 24) | (A << 16) | (A << 8) | A) >>> 0);
    }
    _quad(src, W, H, sx, sy, sw, sh, dx, dy, dw, dh, col) {
      this._room(4, 6);
      const t = this._slot(src, W, H), q = this._e;
      const a = this.a, b = this.b, c = this.c, d = this.d, e = this.e, f = this.f;
      if (q.pg) { sx += q.x; sy += q.y; W = H = PAGE; }
      const u0 = sx / W, v0 = sy / H, u1 = (sx + sw) / W, v1 = (sy + sh) / H, x1 = dx + dw, y1 = dy + dh;
      const i0 = this._v(a * dx + c * dy + e, b * dx + d * dy + f, u0, v0, col, t);
      this._v(a * x1 + c * dy + e, b * x1 + d * dy + f, u1, v0, col, t);
      this._v(a * x1 + c * y1 + e, b * x1 + d * y1 + f, u1, v1, col, t);
      this._v(a * dx + c * y1 + e, b * dx + d * y1 + f, u0, v1, col, t);
      this._tri(i0, i0 + 1, i0 + 2); this._tri(i0, i0 + 2, i0 + 3);
    }

    /* ---- gradients ---- */
    createLinearGradient(x0, y0, x1, y1) { return new Grad(0, [x0, y0, x1, y1], [0, 0]); }
    createRadialGradient(x0, y0, r0, x1, y1, r1) { return new Grad(1, [x1, y1, 0, 0], [r0, r1]); }
    _gradReady(g) {
      if (g._s) return;
      let s = g.s.slice().sort((p, q) => p[0] - q[0]);
      if (!s.length) s = [[0, [0, 0, 0, 0]]];
      if (s.length > MAX_STOPS) { const k = (s.length - 1) / (MAX_STOPS - 1), o = []; for (let i = 0; i < MAX_STOPS; i++) o.push(s[Math.round(i * k)]); s = o; }
      const c = new Float32Array(MAX_STOPS * 4), o = new Float32Array(MAX_STOPS);
      s.forEach((p, i) => { o[i] = p[0]; c[i * 4] = p[1][0] / 255; c[i * 4 + 1] = p[1][1] / 255; c[i * 4 + 2] = p[1][2] / 255; c[i * 4 + 3] = p[1][3]; });
      g._s = { n: s.length, c, o };
    }
    /* solid-area drawing through a gradient: vertices carry their position in gradient space */
    _gradDraw(g, pts, tris) {
      if (this.zrun) this._endZ();
      this._gradReady(g); this.flush(); this.grad = g;
      const a = this.a, b = this.b, c = this.c, d = this.d, e = this.e, f = this.f, det = a * d - b * c || 1;
      const A = clamp255(this.globalAlpha * 255), col = ((A << 24) | (A << 16) | (A << 8) | A) >>> 0;
      const n = pts.length / 2, i0 = this.n;
      for (let i = 0; i < n; i++) {
        const X = pts[i * 2], Y = pts[i * 2 + 1], x = X - e, y = Y - f;
        this._v(X, Y, (d * x - c * y) / det, (a * y - b * x) / det, col, 0);
      }
      for (let i = 0; i < tris.length; i += 3) this._tri(i0 + tris[i], i0 + tris[i + 1], i0 + tris[i + 2]);
      this.flush(); this.grad = null;
    }

    /* ---- rectangles ---- */
    fillRect(x, y, w, h) {
      const st = this.fillStyle, ga = this.globalAlpha; if (!(ga > 0)) return;
      const a = this.a, b = this.b, c = this.c, d = this.d, e = this.e, f = this.f, x1 = x + w, y1 = y + h;
      this._blend();
      if (typeof st !== 'string') {
        if (st instanceof Grad) this._gradDraw(st, [a * x + c * y + e, b * x + d * y + f, a * x1 + c * y + e, b * x1 + d * y + f, a * x1 + c * y1 + e, b * x1 + d * y1 + f, a * x + c * y1 + e, b * x + d * y1 + f], [0, 1, 2, 0, 2, 3]);
        return;
      }
      const col = premult(colorOf(st), ga);
      this._room(4, 6);
      const i0 = this._v(a * x + c * y + e, b * x + d * y + f, 0, 0, col, -1);
      this._v(a * x1 + c * y + e, b * x1 + d * y + f, 0, 0, col, -1);
      this._v(a * x1 + c * y1 + e, b * x1 + d * y1 + f, 0, 0, col, -1);
      this._v(a * x + c * y1 + e, b * x + d * y1 + f, 0, 0, col, -1);
      this._tri(i0, i0 + 1, i0 + 2); this._tri(i0, i0 + 2, i0 + 3);
    }
    clearRect(x, y, w, h) { const o = this.globalCompositeOperation, f = this.fillStyle, g = this.globalAlpha; this.globalCompositeOperation = 'source-over'; this.fillStyle = '#000'; this.globalAlpha = 1; this.fillRect(x, y, w, h); this.globalCompositeOperation = o; this.fillStyle = f; this.globalAlpha = g; }
    strokeRect(x, y, w, h) {
      const p = this.px, s = this.ss, c = this.cl;
      this.px = []; this.ss = []; this.cl = [];
      this.rect(x, y, w, h); this.stroke();
      this.px = p; this.ss = s; this.cl = c;
    }

    /* ---- paths: points are stored in device space, as the canvas rules require ---- */
    beginPath() { this.px.length = 0; this.ss.length = 0; this.cl.length = 0; }
    _pt(x, y) { this.px.push(this.a * x + this.c * y + this.e, this.b * x + this.d * y + this.f); }
    _dev(X, Y) { this.px.push(X, Y); }
    moveTo(x, y) { this.ss.push(this.px.length / 2); this.cl.push(false); this._pt(x, y); }
    lineTo(x, y) { if (!this.ss.length) return this.moveTo(x, y); this._reopen(); this._pt(x, y); }
    _reopen() {
      /* drawing on after closePath starts a new subpath at the closed subpath's first point */
      const k = this.cl.length - 1;
      if (this.cl[k]) { const i = this.ss[k] * 2, X = this.px[i], Y = this.px[i + 1]; this.ss.push(this.px.length / 2); this.cl.push(false); this.px.push(X, Y); }
    }
    closePath() { if (this.cl.length) this.cl[this.cl.length - 1] = true; }
    rect(x, y, w, h) { this.moveTo(x, y); this.lineTo(x + w, y); this.lineTo(x + w, y + h); this.lineTo(x, y + h); this.closePath(); }
    _last() { const n = this.px.length; return [this.px[n - 2], this.px[n - 1]]; }
    _unmap(X, Y) { const det = this.a * this.d - this.b * this.c || 1, x = X - this.e, y = Y - this.f; return [(this.d * x - this.c * y) / det, (this.a * y - this.b * x) / det]; }
    quadraticCurveTo(cx, cy, x, y) {
      if (!this.ss.length) this.moveTo(cx, cy); this._reopen();
      const p = this._unmap(...this._last()), L = (Math.hypot(cx - p[0], cy - p[1]) + Math.hypot(x - cx, y - cy)) * this._sc(), n = Math.max(2, Math.min(32, Math.ceil(Math.sqrt(L) * 1.2)));
      for (let i = 1; i <= n; i++) { const t = i / n, u = 1 - t; this._pt(u * u * p[0] + 2 * u * t * cx + t * t * x, u * u * p[1] + 2 * u * t * cy + t * t * y); }
    }
    bezierCurveTo(c1x, c1y, c2x, c2y, x, y) {
      if (!this.ss.length) this.moveTo(c1x, c1y); this._reopen();
      const p = this._unmap(...this._last()), L = (Math.hypot(c1x - p[0], c1y - p[1]) + Math.hypot(c2x - c1x, c2y - c1y) + Math.hypot(x - c2x, y - c2y)) * this._sc(), n = Math.max(3, Math.min(48, Math.ceil(Math.sqrt(L) * 1.3)));
      for (let i = 1; i <= n; i++) { const t = i / n, u = 1 - t, A = u * u * u, B = 3 * u * u * t, C = 3 * u * t * t, D = t * t * t; this._pt(A * p[0] + B * c1x + C * c2x + D * x, A * p[1] + B * c1y + C * c2y + D * y); }
    }
    arc(x, y, r, a0, a1, ccw) { this.ellipse(x, y, r, r, 0, a0, a1, ccw); }
    ellipse(x, y, rx, ry, rot, a0, a1, ccw) {
      let d = a1 - a0;
      if (!ccw && d >= TAU) d = TAU; else if (ccw && -d >= TAU) d = -TAU;
      else { d %= TAU; if (!ccw && d < 0) d += TAU; else if (ccw && d > 0) d -= TAU; }
      const rd = Math.max(rx, ry) * this._sc(), st = rd < .5 ? 1.2 : 2 * Math.acos(Math.max(0, 1 - .22 / rd)), n = Math.max(2, Math.min(120, Math.ceil(Math.abs(d) / st))), cr = Math.cos(rot || 0), sr = Math.sin(rot || 0);
      for (let i = 0; i <= n; i++) {
        const t = a0 + d * i / n, ex = rx * Math.cos(t), ey = ry * Math.sin(t), X = x + ex * cr - ey * sr, Y = y + ex * sr + ey * cr;
        if (i === 0) { if (this.ss.length) { this._reopen(); this._pt(X, Y); } else this.moveTo(X, Y); }
        else this._pt(X, Y);
      }
    }
    arcTo(x1, y1, x2, y2, r) {
      if (!this.ss.length) this.moveTo(x1, y1);
      const p = this._unmap(...this._last()), ax = p[0] - x1, ay = p[1] - y1, bx = x2 - x1, by = y2 - y1, la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
      const cross = ax * by - ay * bx;
      if (!la || !lb || Math.abs(cross) < 1e-6 || !r) return this.lineTo(x1, y1);
      const ang = Math.acos(Math.max(-1, Math.min(1, (ax * bx + ay * by) / (la * lb)))), t = r / Math.tan(ang / 2);
      const sx = x1 + ax / la * t, sy = y1 + ay / la * t, ex = x1 + bx / lb * t, ey = y1 + by / lb * t, ccw = cross > 0, nx = ccw ? ay / la : -ay / la, ny = ccw ? -ax / la : ax / la;
      const cx = sx + nx * r, cy = sy + ny * r;
      this.lineTo(sx, sy);
      this.arc(cx, cy, r, Math.atan2(sy - cy, sx - cx), Math.atan2(ey - cy, ex - cx), ccw);
    }

    /* ---- filling ---- */
    _subs() {
      const out = [], np = this.px.length / 2;
      for (let i = 0; i < this.ss.length; i++) { const a = this.ss[i], b = i + 1 < this.ss.length ? this.ss[i + 1] : np; if (b - a >= 3) out.push([a, b]); }
      return out;
    }
    fill() {
      const st = this.fillStyle, ga = this.globalAlpha; if (!(ga > 0)) return;
      const subs = this._subs(); if (!subs.length) return;
      this._blend();
      const P = this.px;
      if (typeof st !== 'string') {
        if (!(st instanceof Grad)) return;
        for (const [a, b] of subs) {
          const pts = P.slice(a * 2, b * 2), tr = triangulate(pts);
          if (tr) this._gradDraw(st, pts, tr);
        }
        return;
      }
      const c = colorOf(st), col = premult(c, ga);
      if (subs.length > 1 && c[3] * ga < .995 && this.bl !== 'lighter') return this._union(subs, col);
      for (const [a, b] of subs) {
        const pts = P.slice(a * 2, b * 2), tr = triangulate(pts);
        if (!tr) continue;
        const n = pts.length / 2;
        if (n >= MAXV) continue;
        this._room(n, tr.length);
        const i0 = this.n;
        for (let i = 0; i < n; i++) this._v(pts[i * 2], pts[i * 2 + 1], 0, 0, col, -1);
        for (let i = 0; i < tr.length; i += 3) this._tri(i0 + tr[i], i0 + tr[i + 1], i0 + tr[i + 2]);
      }
    }
    /* overlapping subpaths with see-through paint must cover each pixel once. Every path gets its own depth, so a second
       subpath of the same path fails the depth test, and any run of such paths (blood on the ground) is one GPU call */
    _union(subs, col) {
      const P = this.px, gl = this.gl, parts = [];
      let sign = 0;
      for (const [a, b] of subs) {
        const pts = P.slice(a * 2, b * 2), n = pts.length / 2;
        let area = 0;
        for (let i = 0; i < n; i++) { const j = (i + 1) % n; area += pts[i * 2] * pts[j * 2 + 1] - pts[j * 2] * pts[i * 2 + 1]; }
        const sg = area > 0 ? 1 : area < 0 ? -1 : 0;
        if (sg && sign && sg !== sign) return this._stencil(subs, col);  /* opposite windings may be holes */
        if (sg) sign = sg;
        const tr = triangulate(pts);
        if (tr) parts.push(pts, tr);
      }
      if (!this.zrun) { this.flush(); gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LESS); gl.clear(gl.DEPTH_BUFFER_BIT); this.zrun = true; this.z = .999; }
      if (this.z < -.9) { this.flush(); gl.clear(gl.DEPTH_BUFFER_BIT); this.z = .999; }
      this.z -= 1 / 20000;
      this.inU = true;
      for (let k = 0; k < parts.length; k += 2) {
        const pts = parts[k], tr = parts[k + 1], n = pts.length / 2;
        this._room(n, tr.length);
        const i0 = this.n;
        for (let i = 0; i < n; i++) this._v(pts[i * 2], pts[i * 2 + 1], this.z, 0, col, -1);
        for (let i = 0; i < tr.length; i += 3) this._tri(i0 + tr[i], i0 + tr[i + 1], i0 + tr[i + 2]);
      }
      this.inU = false;
    }
    _endZ() { this.flush(); this.gl.disable(this.gl.DEPTH_TEST); this.zrun = false; }
    _stencil(subs, col) {
      if (this.zrun) this._endZ();
      const gl = this.gl, P = this.px;
      if (!this._hasStencil) { this._hasStencil = gl.getContextAttributes().stencil ? 1 : -1; }
      if (this._hasStencil < 0) return;
      this.flush();
      gl.enable(gl.STENCIL_TEST); gl.colorMask(false, false, false, false);
      gl.stencilFunc(gl.ALWAYS, 0, 255);
      gl.stencilOpSeparate(gl.FRONT, gl.KEEP, gl.KEEP, gl.INCR_WRAP); gl.stencilOpSeparate(gl.BACK, gl.KEEP, gl.KEEP, gl.DECR_WRAP);
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const [a, b] of subs) {
        const n = b - a; this._room(n, (n - 2) * 3);
        const i0 = this.n;
        for (let i = a; i < b; i++) {
          const X = P[i * 2], Y = P[i * 2 + 1];
          if (X < x0) x0 = X; if (Y < y0) y0 = Y; if (X > x1) x1 = X; if (Y > y1) y1 = Y;
          this._v(X, Y, 0, 0, col, -1);
        }
        for (let i = 1; i < n - 1; i++) this._tri(i0, i0 + i, i0 + i + 1);
      }
      this.flush();
      gl.colorMask(true, true, true, true); gl.stencilFunc(gl.NOTEQUAL, 0, 255); gl.stencilOp(gl.ZERO, gl.ZERO, gl.ZERO);
      const i0 = this._v(x0, y0, 0, 0, col, -1); this._v(x1, y0, 0, 0, col, -1); this._v(x1, y1, 0, 0, col, -1); this._v(x0, y1, 0, 0, col, -1);
      this._tri(i0, i0 + 1, i0 + 2); this._tri(i0, i0 + 2, i0 + 3);
      this.flush();
      gl.disable(gl.STENCIL_TEST);
    }

    /* ---- stroking: outlines are built in user space, so a skewed transform skews the line as a canvas does ---- */
    stroke() {
      const st = this.strokeStyle, ga = this.globalAlpha; if (!(ga > 0)) return;
      let c;
      if (typeof st === 'string') c = colorOf(st);
      else if (st instanceof Grad && st.s.length) c = st.s[0][1];
      else return;
      this._blend();
      if (this.shadowBlur > 0) {
        const s = colorOf(this.shadowColor);
        if (s[3] > 0) { this._strokeAll(this.lineWidth + this.shadowBlur * 1.1, premult(s, ga * .22)); this._strokeAll(this.lineWidth + this.shadowBlur * .5, premult(s, ga * .3)); }
      }
      this._strokeAll(this.lineWidth, premult(c, ga));
    }
    _strokeAll(w, col) {
      const np = this.px.length / 2, P = this.px, hw = w / 2;
      const a = this.a, b = this.b, c = this.c, d = this.d, e = this.e, f = this.f, det = a * d - b * c;
      if (!det) return;
      for (let s = 0; s < this.ss.length; s++) {
        const i0 = this.ss[s], i1 = s + 1 < this.ss.length ? this.ss[s + 1] : np, pts = [];
        for (let i = i0; i < i1; i++) {
          const x = P[i * 2] - e, y = P[i * 2 + 1] - f, ux = (d * x - c * y) / det, uy = (a * y - b * x) / det, n = pts.length;
          if (n && Math.abs(pts[n - 2] - ux) < 1e-4 && Math.abs(pts[n - 1] - uy) < 1e-4) continue;
          pts.push(ux, uy);
        }
        let closed = this.cl[s];
        if (closed && pts.length >= 4 && Math.abs(pts[0] - pts[pts.length - 2]) < 1e-4 && Math.abs(pts[1] - pts[pts.length - 1]) < 1e-4) pts.length -= 2;
        if (pts.length < 4) continue;
        if (this._d) for (const q of dash(pts, closed, this._d, this.lineDashOffset)) this._extrude(q, false, hw, col);
        else this._extrude(pts, closed, hw, col);
      }
    }
    _extrude(p, closed, hw, col) {
      const n = p.length / 2; if (n < 2) return;
      const a = this.a, b = this.b, c = this.c, d = this.d, e = this.e, f = this.f;
      const count = closed ? n + 1 : n;
      this._room(count * 2 + 40, (count - 1) * 6 + 120);
      const put = (x, y) => this._v(a * x + c * y + e, b * x + d * y + f, 0, 0, col, -1);
      const first = this.n;
      let lastL = -1, lastR = -1;
      const cap = this.lineCap;
      for (let k = 0; k < count; k++) {
        const i = k % n, pi = closed ? (i + n - 1) % n : Math.max(0, i - 1), ni = closed ? (i + 1) % n : Math.min(n - 1, i + 1);
        let x = p[i * 2], y = p[i * 2 + 1];
        let dx0 = x - p[pi * 2], dy0 = y - p[pi * 2 + 1], dx1 = p[ni * 2] - x, dy1 = p[ni * 2 + 1] - y;
        let l0 = Math.hypot(dx0, dy0), l1 = Math.hypot(dx1, dy1);
        if (!l0) { dx0 = dx1; dy0 = dy1; l0 = l1; } if (!l1) { dx1 = dx0; dy1 = dy0; l1 = l0; }
        dx0 /= l0; dy0 /= l0; dx1 /= l1; dy1 /= l1;
        let nx = -(dy0 + dy1), ny = dx0 + dx1, m = Math.hypot(nx, ny);
        if (m < 1e-5) { nx = -dy1; ny = dx1; m = 1; }
        nx /= m; ny /= m;
        const dot = nx * -dy1 + ny * dx1, len = Math.min(dot > .1 ? 1 / dot : 2, this.lineJoin === 'miter' ? 4 : 1.6);
        if (cap === 'square' && !closed) { if (k === 0) { x -= dx1 * hw; y -= dy1 * hw; } if (k === count - 1) { x += dx0 * hw; y += dy0 * hw; } }
        const L = put(x + nx * hw * len, y + ny * hw * len), R = put(x - nx * hw * len, y - ny * hw * len);
        if (k) { this._tri(lastL, lastR, R); this._tri(lastL, R, L); }
        lastL = L; lastR = R;
      }
      if (cap === 'round' && !closed && hw * this._sc() > .6) {
        this._roundCap(p[0], p[1], p[0] - p[2], p[1] - p[3], hw, put, first, first + 1);
        const z = (n - 1) * 2;
        this._roundCap(p[z], p[z + 1], p[z] - p[z - 2], p[z + 1] - p[z - 1], hw, put, lastR, lastL);
      }
    }
    _roundCap(x, y, dx, dy, hw, put, ia, ib) {
      const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      const a0 = Math.atan2(dy, dx), seg = 6, c0 = put(x, y);
      let prev = ib;
      for (let i = 1; i < seg; i++) {
        const t = a0 + Math.PI / 2 - i / seg * Math.PI, q = put(x + Math.cos(t) * hw, y + Math.sin(t) * hw);
        this._tri(c0, prev, q); prev = q;
      }
      this._tri(c0, prev, ia);
    }

    /* ---- text: each string is drawn once to a small canvas and reused ---- */
    fillText(s, x, y) { this._text(s, x, y, 0, this.fillStyle); }
    strokeText(s, x, y) { this._text(s, x, y, this.lineWidth, this.strokeStyle); }
    _text(s, x, y, lw, style) {
      const ga = this.globalAlpha; if (!(ga > 0) || typeof style !== 'string') return;
      s = String(s);
      const k = Math.max(1, Math.ceil(this._sc() * 2) / 2), key = this.font + '|' + k + '|' + lw + '|' + s;
      let t = this.text.get(key);
      if (!t) {
        const g0 = scr(); g0.font = this.font; const m = g0.measureText(s);
        const asc = m.fontBoundingBoxAscent || 12, des = m.fontBoundingBoxDescent || 4, pad = Math.ceil(lw + 3);
        const c = document.createElement('canvas'); c.width = Math.max(1, Math.ceil((m.width + pad * 2) * k)); c.height = Math.max(1, Math.ceil((asc + des + pad * 2) * k));
        const g = c.getContext('2d'); g.scale(k, k); g.font = this.font; g.textBaseline = 'alphabetic'; g.lineJoin = 'round';
        g.fillStyle = '#fff'; g.strokeStyle = '#fff'; g.lineWidth = lw;
        if (lw) g.strokeText(s, pad, pad + asc); else g.fillText(s, pad, pad + asc);
        t = { c, k, w: m.width, pad, asc, des };
        if (this.text.size > 320) { const old = this.text.keys().next().value, o = this.text.get(old); if (o.c._glt) this._free(o.c._glt); this.text.delete(old); }
        this.text.set(key, t);
      }
      const al = this.textAlign, bl = this.textBaseline;
      const ax = al === 'center' ? -t.w / 2 : (al === 'right' || al === 'end') ? -t.w : 0;
      const ay = bl === 'top' || bl === 'hanging' ? t.asc : bl === 'middle' ? (t.asc - t.des) / 2 : bl === 'bottom' || bl === 'ideographic' ? -t.des : 0;
      this._blend();
      this._quad(t.c, t.c.width, t.c.height, 0, 0, t.c.width, t.c.height, x + ax - t.pad, y + ay - t.asc - t.pad, t.c.width / k, t.c.height / k, premult(colorOf(style), ga));
    }
  }

  /* triangle indices for one closed outline: a fan when convex, ear clipping otherwise */
  function triangulate(p) {
    let n = p.length / 2;
    if (n > 1 && Math.abs(p[0] - p[n * 2 - 2]) < 1e-6 && Math.abs(p[1] - p[n * 2 - 1]) < 1e-6) n--;
    if (n < 3) return null;
    let sign = 0, convex = true, area = 0;
    for (let i = 0; i < n; i++) {
      const a = i, b = (i + 1) % n, c = (i + 2) % n;
      const cr = (p[b * 2] - p[a * 2]) * (p[c * 2 + 1] - p[b * 2 + 1]) - (p[b * 2 + 1] - p[a * 2 + 1]) * (p[c * 2] - p[b * 2]);
      area += p[a * 2] * p[b * 2 + 1] - p[b * 2] * p[a * 2 + 1];
      if (Math.abs(cr) > 1e-7) { if (!sign) sign = cr > 0 ? 1 : -1; else if ((cr > 0 ? 1 : -1) !== sign) convex = false; }
    }
    const out = [];
    if (convex || n > 400) { for (let i = 1; i < n - 1; i++) out.push(0, i, i + 1); return out; }
    const V = []; for (let i = 0; i < n; i++) V.push(i);
    const s = area > 0 ? 1 : -1;
    const cross = (a, b, c) => (p[b * 2] - p[a * 2]) * (p[c * 2 + 1] - p[a * 2 + 1]) - (p[b * 2 + 1] - p[a * 2 + 1]) * (p[c * 2] - p[a * 2]);
    let guard = n * n + 8, i = 0;
    while (V.length > 3 && guard-- > 0) {
      const m = V.length, ia = V[(i + m - 1) % m], ib = V[i % m], ic = V[(i + 1) % m];
      let ear = cross(ia, ib, ic) * s > 1e-9;
      if (ear) for (const q of V) {
        if (q === ia || q === ib || q === ic) continue;
        if (cross(ia, ib, q) * s >= 0 && cross(ib, ic, q) * s >= 0 && cross(ic, ia, q) * s >= 0) { ear = false; break; }
      }
      if (ear) { out.push(ia, ib, ic); V.splice(i % m, 1); i = i % V.length; }
      else i = (i + 1) % m;
    }
    if (V.length === 3) out.push(V[0], V[1], V[2]);
    else for (let k = 1; k < V.length - 1; k++) out.push(V[0], V[k], V[k + 1]);
    return out;
  }

  /* split a polyline into its dashes */
  function dash(p, closed, pat, offset) {
    const seq = pat.length % 2 ? pat.concat(pat) : pat, total = seq.reduce((a, b) => a + b, 0), out = [];
    if (!(total > 0)) return [p];
    let idx = 0, rem, on = true, off = ((offset % total) + total) % total;
    while (off >= seq[idx]) { off -= seq[idx]; idx = (idx + 1) % seq.length; on = !on; if (seq[idx] === 0 && off === 0) break; }
    rem = seq[idx] - off;
    const n = p.length / 2, segs = closed ? n : n - 1;
    let cur = on ? [p[0], p[1]] : null;
    for (let s = 0; s < segs; s++) {
      const a = s, b = (s + 1) % n;
      let x = p[a * 2], y = p[a * 2 + 1];
      const X = p[b * 2], Y = p[b * 2 + 1];
      let L = Math.hypot(X - x, Y - y);
      const dx = L ? (X - x) / L : 0, dy = L ? (Y - y) / L : 0;
      while (L > rem) {
        x += dx * rem; y += dy * rem; L -= rem;
        if (on) { cur.push(x, y); out.push(cur); cur = null; } else cur = [x, y];
        on = !on; idx = (idx + 1) % seq.length; rem = seq[idx];
        if (out.length > 4000) return out;
      }
      rem -= L;
      if (on) cur.push(X, Y);
    }
    if (on && cur && cur.length >= 4) out.push(cur);
    return out;
  }

  function create(cv) {
    let mode = null, q = null;
    try { mode = localStorage.getItem('bb-renderer'); } catch (e) {}
    try { q = new URLSearchParams(location.search).get('gl'); } catch (e) {}
    const force = q === 'force';
    if (q === '0' || (mode === '2d' && !force && q !== '1')) return cv.getContext('2d');
    const opts = { alpha: false, antialias: true, depth: true, stencil: true, premultipliedAlpha: true, preserveDrawingBuffer: false, powerPreference: 'high-performance', failIfMajorPerformanceCaveat: !force };
    /* try the shaders on a throwaway canvas first: once the real canvas has a WebGL context it can never be 2D */
    try {
      const t = document.createElement('canvas').getContext('webgl2', opts);
      if (!t) return cv.getContext('2d');
      program(t, fsBatch(Math.min(16, t.getParameter(t.MAX_TEXTURE_IMAGE_UNITS)) - 1)); program(t, FS_GRAD);
      const lose = t.getExtension('WEBGL_lose_context'); if (lose) lose.loseContext();
    } catch (e) { console.warn('glcanvas: falling back to 2D', e); return cv.getContext('2d'); }
    const gl = cv.getContext('webgl2', opts);
    if (!gl) return cv.getContext('2d');
    watchCanvases();
    return new GLCtx(cv, gl);
  }
  return { create };
})();
