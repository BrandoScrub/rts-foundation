/* path.js: A* on the tile grid, 8 directions, no corner cutting, goal = any tile next to a rectangle.
   Paths are smoothed with line-of-sight checks so units walk straight across open ground. */
'use strict';
const Path = (() => {
  let W = 0, H = 0, g, f, from, stamp, closed, heap, hn, gen = 0;
  function init(w, h) {
    W = w; H = h; const n = w * h;
    g = new Float32Array(n); f = new Float32Array(n); from = new Int32Array(n); stamp = new Uint32Array(n); closed = new Uint32Array(n);
    heap = new Int32Array(n); hn = 0;
  }
  function push(i) { let k = hn++; heap[k] = i; while (k > 0) { const p = (k - 1) >> 1; if (f[heap[p]] <= f[i]) break; heap[k] = heap[p]; heap[p] = i; k = p; } }
  function pop() {
    const top = heap[0], last = heap[--hn]; let k = 0;
    if (hn > 0) { heap[0] = last;
      for (;;) { const l = 2 * k + 1, r = l + 1; let m = k;
        if (l < hn && f[heap[l]] < f[heap[m]]) m = l; if (r < hn && f[heap[r]] < f[heap[m]]) m = r;
        if (m === k) break; const t = heap[k]; heap[k] = heap[m]; heap[m] = t; k = m; } }
    return top;
  }
  const DX = [1, -1, 0, 0, 1, 1, -1, -1], DY = [0, 0, 1, -1, 1, -1, 1, -1], DC = [1, 1, 1, 1, 1.4142, 1.4142, 1.4142, 1.4142];

  /* walk(i) -> true if a unit may stand on tile i. Goal rectangle [x0, y0, x1, y1] inclusive; reach = tiles of slack
     around it (1 = stand next to it, 0 = stand on it). Returns a list of [x, y] tile centres, or null. */
  function find(sx, sy, goal, walk, reach = 0, limit = 30000) {
    gen++;
    const [x0, y0, x1, y1] = goal, gx0 = x0 - reach, gy0 = y0 - reach, gx1 = x1 + reach, gy1 = y1 + reach;
    const hcost = (x, y) => { const dx = x < gx0 ? gx0 - x : x > gx1 ? x - gx1 : 0, dy = y < gy0 ? gy0 - y : y > gy1 ? y - gy1 : 0;
      return Math.max(dx, dy) + 0.4142 * Math.min(dx, dy); };
    const s = sy * W + sx; hn = 0;
    stamp[s] = gen; g[s] = 0; f[s] = hcost(sx, sy); from[s] = -1; push(s);
    let best = s, bestH = f[s], n = 0, end = -1;
    while (hn > 0 && n++ < limit) {
      const i = pop(); if (closed[i] === gen) continue; closed[i] = gen;
      const x = i % W, y = (i / W) | 0, h = hcost(x, y);
      if (h === 0) { end = i; break; }
      if (h < bestH) { bestH = h; best = i; }
      for (let d = 0; d < 8; d++) {
        const nx = x + DX[d], ny = y + DY[d];
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const j = ny * W + nx; if (closed[j] === gen || !walk(j)) continue;
        if (d >= 4 && (!walk(y * W + nx) || !walk(ny * W + x))) continue;   // no squeezing past corners
        const ng = g[i] + DC[d];
        if (stamp[j] !== gen || ng < g[j]) { stamp[j] = gen; g[j] = ng; f[j] = ng + hcost(nx, ny); from[j] = i; push(j); }
      }
    }
    const last = end >= 0 ? end : best;
    const out = []; for (let i = last; i >= 0; i = from[i]) out.push([i % W, (i / W) | 0]);
    out.reverse();
    return { tiles: out, reached: end >= 0 };
  }
  function los(ax, ay, bx, by, walk) {   // can a unit walk straight between two tile centres?
    const dx = bx - ax, dy = by - ay, n = Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) * 2.5);
    for (let k = 1; k < n; k++) {
      const x = ax + 0.5 + dx * k / n, y = ay + 0.5 + dy * k / n;
      for (const ox of [-0.3, 0.3]) for (const oy of [-0.3, 0.3]) {
        const tx = Math.floor(x + ox), ty = Math.floor(y + oy);
        if (!walk(ty * W + tx)) return false;
      }
    }
    return true;
  }
  function smooth(tiles, walk) {
    if (tiles.length <= 2) return tiles;
    const out = [tiles[0]]; let a = 0;
    while (a < tiles.length - 1) {
      let b = tiles.length - 1;
      while (b > a + 1 && !los(tiles[a][0], tiles[a][1], tiles[b][0], tiles[b][1], walk)) b--;
      out.push(tiles[b]); a = b;
    }
    return out;
  }
  return { init, find, smooth, los };
})();
if (typeof module !== 'undefined') module.exports = Path;
