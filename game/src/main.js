/* main.js: boot and the loop. The simulation steps at a fixed 30 Hz (times the game speed); drawing follows rAF. */
'use strict';
(() => {
  const seed = +(new URLSearchParams(location.search).get('seed') || 7);
  const world = new World(seed);
  const canvas = document.getElementById('view');
  Render.init(world, canvas); Render.initMini(document.getElementById('mini'));
  UI.init(world, canvas);
  const tc = world.ents.find(e => e.owner === 0 && e.type === 'town_hall');
  if (UI.Mobile.on) Render.cam.zoom = 0.75;   // more of the map on a phone
  Render.centerOn(tc.x + 2, tc.y + 2);
  UI.sel.set.add(tc.id); UI.refresh();
  UI.msg('Your Town Hall stands in the north corner. Train Peasants (Q), find sheep with your Scout, and grow.');
  window.addEventListener('resize', () => Render.resize());
  if (/[?&]reveal=1/.test(location.search)) world.players[0].explored.fill(1);   // testing aid: show the whole map
  window.game = { world, Render, UI };

  const STEP = 1 / 30; let acc = 0, last = performance.now();
  function loop(now) {
    const dt = Math.min(0.25, (now - last) / 1000); last = now;
    if (!UI.st.paused) { acc += dt * UI.st.speed; let n = 0; while (acc >= STEP && n++ < 8) { world.step(STEP); acc -= STEP; } if (n >= 8) acc = 0; }
    UI.frame(dt);
    Render.draw(UI.sel, UI.st);
    Render.drawMini(); Render.blitMini(world.alerts, world.time);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();
