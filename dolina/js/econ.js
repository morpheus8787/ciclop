'use strict';
/* Dolina – ekonomika: trasy zboží, sklady, poptávka, výroba. */

function graphChanged() {
  C.gver++;
  C.routes = {};
  for (var wid in S.wares) {
    var w = S.wares[wid];
    if (w.flag) { w.resv = 0; routeWare(w); }
  }
}

/* vzdálenosti všech vlajek k cílové vlajce (Dijkstra po síti cest) */
function distMap(target) {
  var cached = C.routes[target];
  if (cached && cached.v === C.gver) return cached.d;
  var dist = {}, open = [target], done = {};
  dist[target] = 0;
  while (open.length) {
    var bi = 0;
    for (var k = 1; k < open.length; k++) if (dist[open[k]] < dist[open[bi]]) bi = k;
    var f = open[bi];
    open[bi] = open[open.length - 1]; open.pop();
    if (done[f]) continue;
    done[f] = true;
    var fl = S.flags[f];
    if (!fl) continue;
    for (var j = 0; j < fl.roads.length; j++) {
      var r = S.roads[fl.roads[j]];
      if (!r) continue;
      var o = r.a === f ? r.b : r.a;
      var nd = dist[f] + r.path.length - 1 + 0.5;
      if (dist[o] === undefined || nd < dist[o]) { dist[o] = nd; open.push(o); }
    }
  }
  C.routes[target] = { v: C.gver, d: dist };
  return dist;
}

function flagDist(from, to) {
  if (from === to) return 0;
  var d = distMap(to)[from];
  return d === undefined ? Infinity : d;
}

/* další cesta z vlajky směrem k cíli; 0 = už jsme tam, -1 = nedosažitelné */
function nextRoadFor(from, to) {
  if (from === to) return 0;
  var d = distMap(to), f = S.flags[from];
  if (!f) return -1;
  var best = -1, bc = Infinity;
  for (var j = 0; j < f.roads.length; j++) {
    var r = S.roads[f.roads[j]];
    if (!r) continue;
    var o = r.a === from ? r.b : r.a;
    if (d[o] === undefined) continue;
    var c = r.path.length - 1 + 0.5 + d[o];
    if (c < bc) { bc = c; best = r.id; }
  }
  return best;
}

/* posloupnost uzlů z vlajky na vlajku po cestách (pro chodce) */
function routeNodes(from, to) {
  var nodes = [S.flags[from].node], cur = from, guard = 0;
  while (cur !== to && guard++ < 400) {
    var rid = nextRoadFor(cur, to);
    if (rid <= 0) return null;
    var r = S.roads[rid];
    var p = r.a === cur ? r.path : r.path.slice().reverse();
    for (var k = 1; k < p.length; k++) nodes.push(p[k]);
    cur = r.a === cur ? r.b : r.a;
  }
  return cur === to ? nodes : null;
}

/* ---------- sklady ---------- */
function isWarehouse(b) { return b && BUILDINGS[b.type].kind === 'store' && b.state === 'active'; }

function warehouses() {
  var out = [];
  for (var id in S.buildings) if (isWarehouse(S.buildings[id])) out.push(S.buildings[id]);
  return out;
}

function nearestWarehouse(flag, test) {
  var best = null, bd = Infinity;
  warehouses().forEach(function (w) {
    if (test && !test(w)) return;
    var d = flagDist(w.flag, flag);
    if (d < bd) { bd = d; best = w; }
  });
  return best;
}

/* i bez spojení cestou (pro návrat lidí při bourání) */
function nearestWarehouseAny(flag, excludeId) {
  var w = nearestWarehouse(flag, function (x) { return x.id !== excludeId; });
  if (w) return w;
  var all = warehouses().filter(function (x) { return x.id !== excludeId; });
  return all[0] || null;
}

function addPerson(wh, prof, n) { wh.people[prof] = (wh.people[prof] || 0) + n; }
function addStock(wh, ware, n) { wh.stock[ware] = (wh.stock[ware] || 0) + n; }

function totalStock() {
  var st = {}, pp = {};
  warehouses().forEach(function (w) {
    for (var k in w.stock) st[k] = (st[k] || 0) + w.stock[k];
    for (k in w.people) pp[k] = (pp[k] || 0) + w.people[k];
  });
  return { stock: st, people: pp };
}

/* ---------- zboží ---------- */
function deficit(b, type) {
  if (b.state === 'site') {
    var need = b.site.need[type] || 0;
    return need - (b.site.have[type] || 0) - (b.site.inc[type] || 0);
  }
  if (b.state !== 'active') return 0;
  for (var k = 0; k < b.slots.length; k++) {
    var s = b.slots[k];
    if (s.types.indexOf(type) >= 0) return SLOT_CAP - s.have - s.inc;
  }
  return 0;
}

function addIncoming(b, type, n) {
  if (b.state === 'site') { b.site.inc[type] = (b.site.inc[type] || 0) + n; return; }
  for (var k = 0; k < b.slots.length; k++) if (b.slots[k].types.indexOf(type) >= 0) { b.slots[k].inc += n; return; }
}

function findConsumer(type, fromFlag, excludeId) {
  var best = null, bd = Infinity;
  for (var id in S.buildings) {
    var b = S.buildings[id];
    if (b.id === excludeId || deficit(b, type) <= 0) continue;
    var d = flagDist(fromFlag, b.flag);
    if (b.state === 'site') d -= 3; // stavby mají mírnou přednost
    if (d < bd) { bd = d; best = b; }
  }
  return best;
}

function setDest(w, b) {
  w.dest = b ? b.id : 0;
  if (b && !isWarehouse(b)) addIncoming(b, w.type, 1);
}

function retarget(w, fromFlag) {
  var b = findConsumer(w.type, fromFlag, 0) || nearestWarehouse(fromFlag);
  setDest(w, b);
}

function createWare(type, flagId, dest) {
  var id = newId();
  var w = { id: id, type: type, flag: 0, carrier: 0, dest: 0, nextRoad: 0, resv: 0 };
  S.wares[id] = w;
  if (dest) setDest(w, dest); else retarget(w, flagId);
  wareAtFlag(w, flagId);
  return w;
}

function destroyWare(w) {
  if (!w) return;
  var b = w.dest && S.buildings[w.dest];
  if (b && !isWarehouse(b)) addIncoming(b, w.type, -1);
  if (w.flag && S.flags[w.flag]) {
    var fw = S.flags[w.flag].wares, ix = fw.indexOf(w.id);
    if (ix >= 0) fw.splice(ix, 1);
  }
  delete S.wares[w.id];
}

function wareAtFlag(w, fid) {
  var f = S.flags[fid];
  if (!f) { destroyWare(w); return; }
  w.flag = fid; w.carrier = 0; w.resv = 0;
  if (f.wares.indexOf(w.id) < 0) f.wares.push(w.id);
  routeWare(w);
}

/* určí další cestu; při příchodu na cílovou vlajku zboží doručí */
function routeWare(w) {
  var b = w.dest && S.buildings[w.dest];
  if (!b || (!isWarehouse(b) && deficitTarget(b, w) === false)) {
    if (b && !isWarehouse(b)) addIncoming(b, w.type, -1);
    retarget(w, w.flag);
    b = w.dest && S.buildings[w.dest];
  }
  if (!b) { w.nextRoad = -1; return; }
  if (b.flag === w.flag) { deliver(w, b); return; }
  w.nextRoad = nextRoadFor(w.flag, b.flag);
}

/* cíl stále zboží přijímá? */
function deficitTarget(b, w) {
  if (b.state === 'site') return (b.site.need[w.type] || 0) > 0;
  for (var k = 0; k < b.slots.length; k++) if (b.slots[k].types.indexOf(w.type) >= 0) return true;
  return false;
}

function deliver(w, b) {
  var f = S.flags[w.flag];
  if (f) { var ix = f.wares.indexOf(w.id); if (ix >= 0) f.wares.splice(ix, 1); }
  if (isWarehouse(b)) addStock(b, w.type, 1);
  else if (b.state === 'site') {
    b.site.have[w.type] = (b.site.have[w.type] || 0) + 1;
    b.site.inc[w.type] = Math.max(0, (b.site.inc[w.type] || 0) - 1);
  } else {
    for (var k = 0; k < b.slots.length; k++) {
      var s = b.slots[k];
      if (s.types.indexOf(w.type) >= 0) { s.have++; s.inc = Math.max(0, s.inc - 1); break; }
    }
  }
  delete S.wares[w.id];
}

/* vyrobené zboží položí na vlajku budovy */
function emit(b, type) {
  var f = S.flags[b.flag];
  if (!f || f.wares.length >= FLAG_CAP) return false;
  S.stats[type] = (S.stats[type] || 0) + 1;
  var dest = findConsumer(type, b.flag, b.id) || nearestWarehouse(b.flag);
  createWare(type, b.flag, dest);
  return true;
}

/* ---------- poptávka (dispečer) ---------- */
function connected(b) {
  return !!nearestWarehouse(b.flag);
}

function sendFromWarehouse(b, types) {
  for (var t = 0; t < types.length; t++) {
    var type = types[t];
    var wh = nearestWarehouse(b.flag, function (w) {
      return (w.stock[type] || 0) > 0 && S.flags[w.flag] && S.flags[w.flag].wares.length < FLAG_CAP;
    });
    if (!wh || flagDist(wh.flag, b.flag) === Infinity) continue;
    wh.stock[type]--;
    createWare(type, wh.flag, b);
    return true;
  }
  return false;
}

/* vyšle člověka dané profese ze skladu; specialisté vznikají z pomocníka + nářadí */
function requestPerson(destFlag, prof) {
  // co pomocník potřebuje, aby se stal danou profesí ('' = nic, null = nelze)
  var helperNeeds = prof === 'soldier' ? 'weapon' : prof === 'helper' ? null : prof === 'builder' ? '' : 'tools';
  var wh = nearestWarehouse(destFlag, function (w) { return (w.people[prof] || 0) > 0; });
  if (!wh && helperNeeds !== null) {
    wh = nearestWarehouse(destFlag, function (w) {
      return (w.people.helper || 0) > 0 && (!helperNeeds || (w.stock[helperNeeds] || 0) > 0);
    });
    if (wh) { wh.people.helper--; if (helperNeeds) wh.stock[helperNeeds]--; addPerson(wh, prof, 1); }
  }
  if (!wh) return null;
  var path = routeNodes(wh.flag, destFlag);
  if (!path) return null;
  wh.people[prof]--;
  path.unshift(wh.node);
  return path;
}

function dispatch() {
  // nosiči na cesty
  for (var rid in S.roads) {
    var r = S.roads[rid];
    if (r.carrier) continue;
    var path = requestPerson(r.a, 'helper');
    if (!path) continue;
    var u = spawnWalker(path, 'carrier', 'helper');
    u.road = r.id;
    r.carrier = u.id;
  }
  var ids = Object.keys(S.buildings).map(Number).sort(function (a, b) { return a - b; });
  for (var k = 0; k < ids.length; k++) {
    var b = S.buildings[ids[k]];
    if (!b) continue;
    var def = BUILDINGS[b.type];
    if (b.state === 'site') {
      if (!b.site.builder && !b.site.coming) {
        var p = requestPerson(b.flag, 'builder');
        if (p) { p.push(b.node); var bu = spawnWalker(p, 'builder', 'builder'); bu.bid = b.id; b.site.coming = bu.id; }
      }
      for (var m in b.site.need) if (deficit(b, m) > 0) sendFromWarehouse(b, [m]);
      continue;
    }
    if (def.kind === 'prod' || def.kind === 'field' || def.kind === 'mine') {
      if (!b.worker && !b.workerComing) {
        var wp = requestPerson(b.flag, b.type);
        if (wp) { wp.push(b.node); var wu = spawnWalker(wp, 'worker', b.type); wu.bid = b.id; b.workerComing = wu.id; }
      }
      for (var s = 0; s < b.slots.length; s++) {
        var sl = b.slots[s];
        if (SLOT_CAP - sl.have - sl.inc > 0) sendFromWarehouse(b, sl.types);
      }
    } else if (def.kind === 'mil') {
      if (b.soldiers + b.solInc < def.soldiers) {
        var sp = requestPerson(b.flag, 'soldier');
        if (sp) { sp.push(b.node); var su = spawnWalker(sp, 'soldier', 'soldier'); su.bid = b.id; b.solInc++; }
      }
    }
  }
}

/* zboží, které nemělo kudy jít, zkusí znovu */
function rerouteStuck() {
  for (var wid in S.wares) {
    var w = S.wares[wid];
    if (w.flag && w.nextRoad <= 0) routeWare(w);
  }
}

/* ---------- budovy: stavba a výroba ---------- */
function updateBuilding(b, dt) {
  var def = BUILDINGS[b.type];
  if (b.state === 'site') { updateSite(b, dt); return; }
  if (def.kind === 'prod' || def.kind === 'mine') updateProduction(b, def, dt);
  else if (def.kind === 'field') updateFieldBuilding(b, def, dt);
  else if (def.kind === 'mil') b.status = b.soldiers ? 'Obsazeno (' + b.soldiers + '/' + def.soldiers + ')' : 'Čeká na vojáky';
  else b.status = 'Sklad';
}

function updateSite(b, dt) {
  var st = b.site;
  if (!st.builder) { b.status = st.coming ? 'Stavitel je na cestě' : (connected(b) ? 'Čeká na stavitele' : 'Není připojeno cestou!'); return; }
  if (st.work > 0) {
    st.work -= dt;
    if (st.work <= 0) { st.used++; if (st.used >= st.total) finishSite(b); }
    b.status = 'Staví se';
    return;
  }
  var delivered = 0;
  for (var m in st.have) delivered += st.have[m];
  if (delivered > st.used) { st.work = 1.6; b.status = 'Staví se'; }
  else b.status = 'Čeká na materiál';
}

function finishSite(b) {
  b.state = 'active';
  b.site.builder = 0;
  b.status = '';
  var path = null, wh = nearestWarehouse(b.flag);
  if (wh) path = routeNodes(b.flag, wh.flag);
  if (path) { path.unshift(b.node); path.push(wh.node); var u = spawnWalker(path, 'home', 'builder'); u.bid = wh.id; }
  else if (wh || warehouses()[0]) addPerson(wh || warehouses()[0], 'builder', 1);
  S.msgs.push(BUILDINGS[b.type].name + ' je postaven(a).');
}

function updateProduction(b, def, dt) {
  if (!b.worker) { b.status = b.workerComing ? 'Pracovník je na cestě' : 'Chybí pracovník (nářadí?)'; return; }
  if (b.paused) { b.status = 'Pozastaveno'; return; }
  if (b.hold) {
    if (emit(b, b.hold)) { b.hold = null; b.made++; } else { b.status = 'Vlajka je plná'; return; }
  }
  if (b.timer > 0) {
    b.timer -= dt; b.status = 'Pracuje';
    if (b.timer <= 0) b.hold = def.output;
    return;
  }
  for (var k = 0; k < b.slots.length; k++) {
    if (b.slots[k].have < 1) { b.status = 'Chybí ' + b.slots[k].types.map(function (t) { return WARES[t].name.toLowerCase(); }).join(' / '); return; }
  }
  if (def.kind === 'mine') {
    var rn = findResource(b.node, def.res);
    if (rn < 0) { b.status = 'Ložisko vyčerpáno'; return; }
    S.resAmt[rn]--;
    if (!S.resAmt[rn]) S.res[rn] = 0;
  }
  for (k = 0; k < b.slots.length; k++) b.slots[k].have--;
  b.timer = def.time;
  b.status = 'Pracuje';
}

function findResource(node, res) {
  var near = nodesInRadius(node, 2);
  for (var k = 0; k < near.length; k++) if (S.res[near[k]] === res && S.resAmt[near[k]] > 0) return near[k];
  return -1;
}

/* ---------- příroda ---------- */
function growNature(dt) {
  for (var i = 0; i < S.N; i++) {
    var o = S.obj[i];
    if (o === O_TREE && S.objv[i] < 1) S.objv[i] = Math.min(1, S.objv[i] + dt / 70);
    else if (o === O_FIELD && S.objv[i] < 1) S.objv[i] = Math.min(1, S.objv[i] + dt / 40);
    else if (S.ter[i] === T_WATER && S.fish[i] < 3 && nearWalkable(i) && rnd() < dt * 0.002) S.fish[i]++;
  }
}

function produceHelpers() {
  var hq = null;
  for (var id in S.buildings) if (S.buildings[id].type === 'hq') hq = S.buildings[id];
  if (!hq) return;
  var t = totalStock().people.helper || 0;
  if (t < 60) addPerson(hq, 'helper', 1);
}

function checkGoals() {
  while (S.goal < GOALS.length) {
    var g = GOALS[S.goal], done;
    if (g.territory) done = territorySources().length > 1;
    else done = (S.stats[g.ware] || 0) >= g.n;
    if (!done) break;
    S.msgs.push('🎯 Splněno: ' + g.text);
    S.goal++;
    if (S.goal >= GOALS.length && !S.won) { S.won = true; S.msgs.push('🏆 Vítězství! Dolina vzkvétá.'); }
  }
}
