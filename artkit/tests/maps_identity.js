/* Prints one hash per generated map plan, so a move or refactor of the map generator can be checked byte for byte.
   node artkit/tests/maps_identity.js <mapkit.js> <templates.js>
   Every template that has a weight in a biome (and the Dead City everywhere), three seeds at 120 and one at 180.
   The plan's `ms` (generation time) is left out; everything else is hashed as JSON. */
const path = require('path'), crypto = require('crypto');
const MapKit = require(path.resolve(process.argv[2])), TPL = require(path.resolve(process.argv[3]));
const BIOMES = ['lowlands', 'highlands', 'wastes'];
const ctx = (biome, n) => ({biome, start: {x: n / 2 + .5, y: n / 2 + .5}, ore: {lowlands: 4, highlands: 6, wastes: 5}[biome],
  edges: {n: {open: true, neighbor: true, infected: true, name: 'Blighted Marsh'}, s: {open: true, neighbor: true, name: 'Oakwell'},
          e: {open: true, neighbor: true, name: 'Cinderford'}, w: {open: true, neighbor: false}},
  threatSide: 'n', budget: {hamlets: Math.round(6 * Math.pow(n / 120, 1.3)), caches: Math.round(40 * (n / 120) ** 2)}});
const H = o => crypto.createHash('sha256').update(JSON.stringify(o, (k, v) => ArrayBuffer.isView(v) ? Array.from(v) : v)).digest('hex').slice(0, 16);
const out = [];
for (const id of Object.keys(TPL.all).sort()) {
  const t = TPL.all[id];
  for (const b of BIOMES) {
    if (!t.w[b] && id !== 'deadcity') continue;
    for (const [i, size] of [[0, 120], [1, 120], [2, 120], [3, 180]]) {
      const seed = (i * 7919 + 1234 + id.length) | 0;
      const p = MapKit.generate({seed, w: size, h: size, template: t, context: ctx(b, size)}); delete p.ms;
      out.push(`map ${id} ${b} ${seed} ${size} ${H(p)}`);
    }
  }
}
out.push(`map exports ${H(Object.keys(MapKit).sort())} ${H(Object.keys(TPL).sort())}`);
console.log(out.join('\n'));
