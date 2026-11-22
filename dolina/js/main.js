'use strict';
/* Dolina – spuštění, herní smyčka, dotykové ovládání mapy. */

(function () {
  var canvas = document.getElementById('game');
  var pointers = {}, drag = null, pinch = null;

  function count() { return Object.keys(pointers).length; }

  function onDown(e) {
    canvas.setPointerCapture(e.pointerId);
    pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
    var n = count();
    if (n === 1) drag = { x: e.clientX, y: e.clientY, cx: R.cam.x, cy: R.cam.y, moved: false };
    else if (n === 2) {
      var ps = Object.keys(pointers).map(function (k) { return pointers[k]; });
      var mx = (ps[0].x + ps[1].x) / 2, my = (ps[0].y + ps[1].y) / 2;
      pinch = { d: Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y), z: R.cam.z, w: screenToWorld(mx, my) };
      if (drag) drag.moved = true;
    }
  }

  function onMove(e) {
    if (!pointers[e.pointerId]) return;
    pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
    var n = count();
    if (n === 1 && drag) {
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 10) drag.moved = true;
      if (drag.moved) { R.cam.x = drag.cx - dx / R.cam.z; R.cam.y = drag.cy - dy / R.cam.z; clampCam(); }
    } else if (n === 2 && pinch) {
      var ps = Object.keys(pointers).map(function (k) { return pointers[k]; });
      var mx = (ps[0].x + ps[1].x) / 2, my = (ps[0].y + ps[1].y) / 2;
      var d = Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y);
      R.cam.z = Math.max(0.6, Math.min(4, pinch.z * d / pinch.d));
      R.cam.x = pinch.w[0] - mx / R.cam.z; R.cam.y = pinch.w[1] - my / R.cam.z;
      clampCam();
    }
  }

  function onUp(e) {
    if (!pointers[e.pointerId]) return;
    var n = count();
    if (n === 1 && drag && !drag.moved) onTap(e.clientX, e.clientY);
    delete pointers[e.pointerId];
    if (count() === 1) {
      var k = Object.keys(pointers)[0];
      drag = { x: pointers[k].x, y: pointers[k].y, cx: R.cam.x, cy: R.cam.y, moved: true };
      pinch = null;
    } else if (count() === 0) { drag = null; pinch = null; }
  }

  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', function (e) { delete pointers[e.pointerId]; drag = null; pinch = null; });
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    var w = screenToWorld(e.clientX, e.clientY);
    R.cam.z = Math.max(0.6, Math.min(4, R.cam.z * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
    R.cam.x = w[0] - e.clientX / R.cam.z; R.cam.y = w[1] - e.clientY / R.cam.z;
    clampCam();
  }, { passive: false });
  // zabránit systémovému zoomu Safari
  ['gesturestart', 'gesturechange', 'gestureend'].forEach(function (t) {
    document.addEventListener(t, function (e) { e.preventDefault(); });
  });
  window.addEventListener('resize', resizeRender);
  document.addEventListener('visibilitychange', function () { if (document.hidden) saveGame(false); });
  window.addEventListener('pagehide', function () { saveGame(false); });
  window.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { endRoad(); closePanel(); closeModal(); }
    if (e.key === ' ') { UI.speed = UI.speed ? 0 : 1; updateTopBar(); }
  });

  initRender(canvas);
  if (!loadGame()) startNewGame();
  initUI();

  var acc = 0, last = performance.now();
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    acc += dt * UI.speed;
    var steps = 0;
    while (acc >= 0.1 && steps < 40) { step(0.1); acc -= 0.1; steps++; }
    if (steps >= 40) acc = 0;
    draw(dt);
    uiTick(dt);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    navigator.serviceWorker.register('sw.js').catch(function () { /* offline režim nedostupný */ });
  }
})();
