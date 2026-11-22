'use strict';
/* Dolina – postavičky: chodci, nosiči, pracovníci v terénu. */

function spawnWalker(path, role, prof) {
  var id = newId();
  var u = { id: id, kind: 'walker', role: role, prof: prof, path: path, pi: 0, p: 0, bid: 0, road: 0 };
  S.units[id] = u;
  return u;
}

/* člověk se vrátí do skladu (zjednodušeně: rovnou se připíše) */
function sendHome(u, prof) {
  var start = u.path ? u.path[Math.min(u.pi, u.path.length - 1)] : -1;
  var wh = warehouses()[0];
  var best = null, bd = Infinity;
  warehouses().forEach(function (w) {
    var d = start >= 0 ? hexDist(start, w.node) : 0;
    if (d < bd) { bd = d; best = w; }
  });
  wh = best || wh;
  if (wh) addPerson(wh, prof, 1);
  clearResv(u);
  delete S.units[u.id];
}

function clearResv(u) {
  for (var k in S.resv) if (S.resv[k] === u.id) delete S.resv[k];
}

function moveAlong(u, dt, speed) {
  u.p += dt * speed;
  while (u.p >= 1 && u.pi < u.path.length - 1) { u.p -= 1; u.pi++; }
  if (u.pi >= u.path.length - 1) { u.pi = u.path.length - 1; u.p = 0; return true; }
  return false;
}

function updateUnit(u, dt) {
  if (u.kind === 'walker') { if (moveAlong(u, dt, WALK_SPEED)) walkerArrived(u); }
  else if (u.kind === 'carrier') updateCarrier(u, dt);
  else if (u.kind === 'field') updateFieldWorker(u, dt);
}

function walkerArrived(u) {
  var b = S.buildings[u.bid];
  if (u.role === 'carrier') {
    var r = S.roads[u.road];
    if (!r || r.carrier !== u.id) { sendHome(u, 'helper'); return; }
    u.kind = 'carrier'; u.st = 'idle'; u.dir = 'mid'; u.ware = 0;
    u.rpos = r.path.indexOf(u.path[u.path.length - 1]);
    if (u.rpos < 0) u.rpos = 0;
    u.path = null;
    return;
  }
  if (u.role === 'builder') {
    if (b && b.state === 'site' && b.site.coming === u.id) { b.site.builder = 1; b.site.coming = 0; delete S.units[u.id]; }
    else sendHome(u, 'builder');
    return;
  }
  if (u.role === 'worker') {
    if (b && b.state === 'active' && b.workerComing === u.id) { b.worker = 1; b.workerComing = 0; delete S.units[u.id]; }
    else sendHome(u, u.prof);
    return;
  }
  if (u.role === 'soldier') {
    if (b && b.state === 'active') {
      b.solInc = Math.max(0, b.solInc - 1);
      b.soldiers++;
      delete S.units[u.id];
      if (b.soldiers === 1) { recomputeTerritory(); S.msgs.push(BUILDINGS[b.type].name + ' obsazena – území se rozšířilo!'); }
    } else sendHome(u, 'soldier');
    return;
  }
  if (u.role === 'home') {
    if (b && isWarehouse(b)) { addPerson(b, u.prof, 1); delete S.units[u.id]; }
    else sendHome(u, u.prof);
  }
}

/* ---------- nosič ---------- */
function roadEndFlag(r, end) { return end === 'a' ? r.a : r.b; }

function findCarrierJob(u, r) {
  var L = r.path.length - 1, best = null, bd = Infinity;
  ['a', 'b'].forEach(function (end) {
    var f = S.flags[roadEndFlag(r, end)];
    if (!f) return;
    for (var k = 0; k < f.wares.length; k++) {
      var w = S.wares[f.wares[k]];
      if (w && w.nextRoad === r.id && !w.resv) {
        var d = Math.abs(u.rpos - (end === 'a' ? 0 : L));
        if (d < bd) { bd = d; best = { w: w, end: end }; }
        break;
      }
    }
  });
  return best;
}

function updateCarrier(u, dt) {
  var r = S.roads[u.road];
  if (!r) { if (u.ware) destroyWare(S.wares[u.ware]); sendHome(u, 'helper'); return; }
  var L = r.path.length - 1;
  if (u.st === 'idle') {
    var job = findCarrierJob(u, r);
    if (job) { job.w.resv = u.id; u.ware = job.w.id; u.st = 'fetch'; u.dir = job.end; }
  }
  var tgt = u.dir === 'a' ? 0 : (u.dir === 'b' ? L : Math.floor(L / 2));
  var sp = (u.st === 'carry' ? CARRY_SPEED : WALK_SPEED) * dt;
  if (Math.abs(u.rpos - tgt) > 1e-6) {
    u.rpos = u.rpos < tgt ? Math.min(tgt, u.rpos + sp) : Math.max(tgt, u.rpos - sp);
    if (Math.abs(u.rpos - tgt) > 1e-6) return;
  }
  if (u.st === 'fetch') {
    var w = S.wares[u.ware], fid = roadEndFlag(r, u.dir);
    if (w && w.flag === fid && w.nextRoad === r.id) {
      var f = S.flags[fid], ix = f.wares.indexOf(w.id);
      if (ix >= 0) f.wares.splice(ix, 1);
      w.flag = 0; w.carrier = u.id; w.resv = 0;
      u.st = 'carry'; u.dir = u.dir === 'a' ? 'b' : 'a';
    } else {
      if (w && w.resv === u.id) w.resv = 0;
      u.ware = 0; u.st = 'idle'; u.dir = 'mid';
    }
  } else if (u.st === 'carry') {
    var cw = S.wares[u.ware];
    var tf = S.flags[roadEndFlag(r, u.dir)];
    if (!cw) { u.ware = 0; u.st = 'idle'; u.dir = 'mid'; return; }
    if (tf.wares.length >= FLAG_CAP) {
      // výměna: vezme zboží, které jde opačným směrem po téže cestě
      for (var k = 0; k < tf.wares.length; k++) {
        var w2 = S.wares[tf.wares[k]];
        if (w2 && w2.nextRoad === r.id && !w2.resv) {
          tf.wares.splice(k, 1);
          w2.flag = 0; w2.carrier = u.id;
          wareAtFlag(cw, tf.id);
          u.ware = w2.id; u.dir = u.dir === 'a' ? 'b' : 'a';
          return;
        }
      }
      return; // čeká
    }
    u.ware = 0; u.st = 'idle'; u.dir = 'mid';
    wareAtFlag(cw, tf.id);
  }
}

/* ---------- práce v terénu ---------- */
function freePath(s, g, maxDepth) {
  if (s === g) return [s];
  var prev = {}, q = [s], depth = {};
  prev[s] = -1; depth[s] = 0;
  for (var qi = 0; qi < q.length; qi++) {
    var cur = q[qi];
    if (depth[cur] >= maxDepth) continue;
    for (var d = 0; d < 6; d++) {
      var n = nb(cur, d);
      if (n < 0 || prev[n] !== undefined || !walkable(n)) continue;
      if (S.bldAt[n] && n !== g) continue;
      prev[n] = cur; depth[n] = depth[cur] + 1;
      if (n === g) {
        var path = [];
        for (var c = g; c !== -1; c = prev[c]) path.push(c);
        return path.reverse();
      }
      q.push(n);
    }
  }
  return null;
}

function plantable(i, b) {
  return S.ter[i] === T_GRASS && freeNode(i) && i !== nb(b.node, 1) && !S.resv[i];
}

function findFieldTarget(b, def) {
  var cand = nodesInRadius(b.node, def.radius).filter(function (i) { return i !== b.node; });
  var pick = null, job = def.job;
  function nearest(list) {
    list.sort(function (x, y) { return hexDist(b.node, x) - hexDist(b.node, y) + (rnd() - 0.5) * 0.5; });
    return list.length ? list[0] : null;
  }
  if (job === 'chop') pick = nearest(cand.filter(function (i) { return S.obj[i] === O_TREE && S.objv[i] >= 1 && !S.resv[i]; }));
  else if (job === 'stone') pick = nearest(cand.filter(function (i) { return S.obj[i] === O_STONE && S.objv[i] > 0 && !S.resv[i]; }));
  else if (job === 'plant') {
    var free = cand.filter(function (i) { return plantable(i, b) && hexDist(b.node, i) >= 2; });
    pick = free.length ? free[(rnd() * free.length) | 0] : null;
  } else if (job === 'farm') {
    pick = nearest(cand.filter(function (i) { return S.obj[i] === O_FIELD && S.objv[i] >= 1 && !S.resv[i]; }));
    if (pick === null) {
      var spots = cand.filter(function (i) { return plantable(i, b) && !S.occ[i]; });
      pick = spots.length ? spots[(rnd() * spots.length) | 0] : null;
    }
  } else if (job === 'fish') {
    var waters = cand.filter(function (i) { return S.ter[i] === T_WATER && S.fish[i] > 0 && !S.resv[i]; });
    waters.sort(function (x, y) { return hexDist(b.node, x) - hexDist(b.node, y); });
    for (var k = 0; k < waters.length; k++) {
      for (var d = 0; d < 6; d++) {
        var l = nb(waters[k], d);
        if (l >= 0 && walkable(l) && !S.bldAt[l]) {
          var p = freePath(b.node, l, 14);
          if (p) return { node: waters[k], path: p };
        }
      }
    }
    return null;
  }
  if (pick === null) return null;
  var path = freePath(b.node, pick, 14);
  return path ? { node: pick, path: path } : null;
}

function updateFieldBuilding(b, def, dt) {
  if (!b.worker) { b.status = b.workerComing ? 'Pracovník je na cestě' : 'Chybí pracovník (nářadí?)'; return; }
  if (b.fw) { if (!S.units[b.fw]) b.fw = 0; else return; }
  if (b.hold) {
    if (emit(b, b.hold)) { b.hold = null; b.made++; } else { b.status = 'Vlajka je plná'; return; }
  }
  if (b.paused) { b.status = 'Pozastaveno'; return; }
  if (b.rest > 0) { b.rest -= dt; return; }
  var t = findFieldTarget(b, def);
  if (!t) { b.status = 'Není co dělat v okolí'; b.rest = 3; return; }
  var id = newId();
  S.units[id] = { id: id, kind: 'field', bid: b.id, st: 'out', path: t.path, pi: 0, p: 0, target: t.node, timer: def.work, carry: null };
  S.resv[t.node] = id;
  b.fw = id;
  b.status = 'Pracuje';
}

function updateFieldWorker(u, dt) {
  var b = S.buildings[u.bid];
  if (!b) { clearResv(u); delete S.units[u.id]; return; }
  var def = BUILDINGS[b.type];
  if (u.st === 'out') {
    if (moveAlong(u, dt, WALK_SPEED)) u.st = 'work';
  } else if (u.st === 'work') {
    u.timer -= dt;
    if (u.timer > 0) return;
    u.carry = doFieldWork(def.job, u.target);
    clearResv(u);
    u.path = u.path.slice().reverse(); u.pi = 0; u.p = 0; u.st = 'back';
  } else if (u.st === 'back') {
    if (moveAlong(u, dt, WALK_SPEED)) {
      if (u.carry) b.hold = u.carry;
      b.fw = 0; b.rest = def.rest;
      delete S.units[u.id];
    }
  }
}

function doFieldWork(job, n) {
  if (job === 'chop') {
    if (S.obj[n] === O_TREE && S.objv[n] >= 1) { S.obj[n] = O_NONE; S.objv[n] = 0; return 'log'; }
  } else if (job === 'stone') {
    if (S.obj[n] === O_STONE && S.objv[n] > 0) { S.objv[n]--; if (S.objv[n] <= 0) S.obj[n] = O_NONE; return 'stone'; }
  } else if (job === 'plant') {
    if (freeNode(n) && S.ter[n] === T_GRASS) { S.obj[n] = O_TREE; S.objv[n] = 0.02; }
  } else if (job === 'farm') {
    if (S.obj[n] === O_FIELD && S.objv[n] >= 1) { S.obj[n] = O_NONE; S.objv[n] = 0; return 'grain'; }
    if (freeNode(n) && S.ter[n] === T_GRASS) { S.obj[n] = O_FIELD; S.objv[n] = 0.02; }
  } else if (job === 'fish') {
    if (S.fish[n] > 0) { S.fish[n]--; return 'fish'; }
  }
  return null;
}

/* pozice postavičky ve světě (px) */
function unitPos(u) {
  if (u.kind === 'carrier') {
    var r = S.roads[u.road]; if (!r) return null;
    var k = Math.floor(u.rpos), t = u.rpos - k;
    var a = nodePos(r.path[k]), b = nodePos(r.path[Math.min(k + 1, r.path.length - 1)]);
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, b[0] < a[0]];
  }
  if (!u.path) return null;
  var p0 = nodePos(u.path[u.pi]), p1 = nodePos(u.path[Math.min(u.pi + 1, u.path.length - 1)]);
  return [p0[0] + (p1[0] - p0[0]) * u.p, p0[1] + (p1[1] - p0[1]) * u.p, p1[0] < p0[0]];
}
