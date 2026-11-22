'use strict';
/* Dolina – vlajky, cesty, budovy, území. */

function newId() { return S.nid++; }
function isOwned(i) { return i >= 0 && S.own[i] === 1; }

function freeNode(i) {
  return !S.flagAt[i] && !S.bldAt[i] && !S.occ[i] && !S.roadAt[i] && !S.obj[i];
}

/* Lze sem postavit vlajku? (uprostřed cesty = rozdělení cesty) */
function canFlag(i) {
  if (i < 0 || !isOwned(i) || !walkable(i)) return false;
  if (S.flagAt[i] || S.bldAt[i] || S.occ[i] || S.obj[i]) return false;
  for (var d = 0; d < 6; d++) { var n = nb(i, d); if (n >= 0 && S.flagAt[n]) return false; }
  return true;
}

/* 0 nic, 1 malá budova, 2 velká, 3 důl */
function buildSpot(i) {
  if (i < 0 || !isOwned(i) || !freeNode(i)) return 0;
  var t = S.ter[i];
  if (t !== T_GRASS && t !== T_MOUNT) return 0;
  var f = nb(i, 1);
  if (f < 0 || !isOwned(f)) return 0;
  if (!S.flagAt[f] && !canFlag(f)) return 0;
  var large = t === T_GRASS;
  for (var d = 0; d < 6; d++) {
    var n = nb(i, d);
    if (n < 0) return 0;
    if (S.bldAt[n] || S.occ[n]) return 0;
    if (d === 1) continue;
    if (S.ter[n] !== T_GRASS || !freeNode(n) || !isOwned(n)) large = false;
  }
  if (t === T_MOUNT) return 3;
  return large ? 2 : 1;
}

function spotFits(type, spot) {
  var size = BUILDINGS[type].size;
  if (size === 'mine') return spot === 3;
  if (size === 'large') return spot === 2;
  return spot === 1 || spot === 2;
}

/* ---------- vlajky ---------- */
function placeFlag(i) {
  if (!canFlag(i)) return 0;
  var rid = S.roadAt[i];
  var id = newId();
  S.flags[id] = { id: id, node: i, wares: [], roads: [] };
  S.flagAt[i] = id;
  if (rid) splitRoad(rid, i, id);
  graphChanged();
  return id;
}

function flagBuilding(fid) {
  var f = S.flags[fid]; if (!f) return null;
  var bn = nb(f.node, 4);
  if (bn < 0) return null;
  var b = S.buildings[S.bldAt[bn]];
  return b && b.flag === fid ? b : null;
}

function removeFlag(fid) {
  var f = S.flags[fid]; if (!f) return;
  var b = flagBuilding(fid);
  if (b && b.type === 'hq') return;
  if (b) removeBuilding(b.id);
  f.roads.slice().forEach(removeRoad);
  f.wares.slice().forEach(function (wid) { destroyWare(S.wares[wid]); });
  S.flagAt[f.node] = 0;
  delete S.flags[fid];
  graphChanged();
}

/* ---------- cesty ---------- */
function roadPassable(n, goal) {
  if (n === goal) return true;
  return isOwned(n) && walkable(n) && freeNode(n);
}

/* A* po uzlech; vrací pole uzlů od s do g nebo null */
function findRoadPath(s, g) {
  if (s === g || g < 0) return null;
  if (!S.flagAt[g] && !canFlag(g)) return null;
  var open = [s], came = {}, gs = {}, fs = {};
  gs[s] = 0; fs[s] = hexDist(s, g); came[s] = -1;
  var closed = {}, iter = 0;
  while (open.length && iter++ < 4000) {
    var bi = 0;
    for (var k = 1; k < open.length; k++) if (fs[open[k]] < fs[open[bi]]) bi = k;
    var cur = open[bi];
    open[bi] = open[open.length - 1]; open.pop();
    if (cur === g) {
      var path = [];
      while (cur !== -1) { path.push(cur); cur = came[cur]; }
      path.reverse();
      return path.length - 1 <= MAX_ROAD ? path : null;
    }
    closed[cur] = true;
    if (gs[cur] >= MAX_ROAD) continue;
    for (var d = 0; d < 6; d++) {
      var n = nb(cur, d);
      if (n < 0 || closed[n] || !roadPassable(n, g)) continue;
      // nesmí vést přes jinou vlajku (kromě cíle)
      var cost = gs[cur] + 1 + (S.ter[n] === T_MOUNT ? 0.4 : 0);
      if (gs[n] === undefined || cost < gs[n]) {
        if (gs[n] === undefined) open.push(n);
        gs[n] = cost; fs[n] = cost + hexDist(n, g); came[n] = cur;
      }
    }
  }
  return null;
}

function createRoad(fa, fb, path) {
  var id = newId();
  S.roads[id] = { id: id, a: fa, b: fb, path: path, carrier: 0 };
  for (var k = 1; k < path.length - 1; k++) S.roadAt[path[k]] = id;
  S.flags[fa].roads.push(id);
  S.flags[fb].roads.push(id);
  graphChanged();
  return id;
}

/* Postaví cestu z vlajky na uzel (případně vytvoří cílovou vlajku). Vrací {ok, msg, endFlag} */
function buildRoad(fromFlag, goalNode, autoFlags) {
  var f = S.flags[fromFlag];
  if (!f) return { ok: false, msg: 'Chybí výchozí vlajka.' };
  var path = findRoadPath(f.node, goalNode);
  if (!path) return { ok: false, msg: 'Cestu sem nelze postavit.' };
  var endFlag = S.flagAt[goalNode] || placeFlag(goalNode);
  if (!endFlag) return { ok: false, msg: 'Sem nelze dát vlajku.' };
  if (endFlag === fromFlag) return { ok: false, msg: 'Cesta musí vést jinam.' };
  var rid = createRoad(fromFlag, endFlag, path);
  if (autoFlags) {
    for (var k = 2; k < path.length - 2; k++) if (canFlag(path[k])) placeFlag(path[k]);
  }
  return { ok: true, road: rid, endFlag: endFlag };
}

/* Najde nejkratší cestu z vlajky k nejbližší vlajce/cestě napojené na sklad a postaví ji. */
function connectAuto(fromFlag) {
  var f = S.flags[fromFlag];
  if (!f) return { ok: false, msg: 'Chybí vlajka.' };
  if (f.roads.length && nearestWarehouse(fromFlag)) return { ok: false, msg: 'Už je připojeno.' };
  var start = f.node, prev = {}, depth = {}, q = [start];
  prev[start] = -1; depth[start] = 0;
  for (var qi = 0; qi < q.length; qi++) {
    var cur = q[qi];
    if (depth[cur] >= MAX_ROAD - 1) continue;
    for (var d = 0; d < 6; d++) {
      var n = nb(cur, d);
      if (n < 0 || prev[n] !== undefined) continue;
      var fl = S.flagAt[n];
      var goal = (fl && fl !== fromFlag && nearestWarehouse(fl)) ||
                 (S.roadAt[n] && canFlag(n) && nearestWarehouse(S.roads[S.roadAt[n]].a));
      if (goal && depth[cur] >= 1) {
        var res = buildRoad(fromFlag, n, true);
        if (res.ok) return res;
      }
      if (fl || !roadPassable(n, -2)) continue;
      prev[n] = cur; depth[n] = depth[cur] + 1;
      q.push(n);
    }
  }
  return { ok: false, msg: 'V dosahu není žádná připojená cesta.' };
}

function splitRoad(rid, node, fid) {
  var r = S.roads[rid];
  var k = r.path.indexOf(node);
  if (k <= 0 || k >= r.path.length - 1) return;
  var p1 = r.path.slice(0, k + 1), p2 = r.path.slice(k);
  var id2 = newId();
  var r2 = { id: id2, a: fid, b: r.b, path: p2, carrier: 0 };
  var fb = S.flags[r.b];
  fb.roads[fb.roads.indexOf(rid)] = id2;
  r.path = p1; r.b = fid;
  S.roads[id2] = r2;
  S.flags[fid].roads.push(rid, id2);
  S.roadAt[node] = 0;
  for (var j = 1; j < p2.length - 1; j++) S.roadAt[p2[j]] = id2;
  var u = r.carrier && S.units[r.carrier];
  if (u && u.kind === 'carrier' && u.road === rid && u.rpos > k) {
    u.road = id2; u.rpos -= k; r2.carrier = u.id; r.carrier = 0;
  }
}

function removeRoad(rid) {
  var r = S.roads[rid]; if (!r) return;
  for (var k = 1; k < r.path.length - 1; k++) S.roadAt[r.path[k]] = 0;
  [r.a, r.b].forEach(function (fid) {
    var f = S.flags[fid]; if (!f) return;
    var ix = f.roads.indexOf(rid); if (ix >= 0) f.roads.splice(ix, 1);
  });
  var u = r.carrier && S.units[r.carrier];
  if (u) {
    if (u.ware) destroyWare(S.wares[u.ware]);
    sendHome(u, 'helper');
  }
  delete S.roads[rid];
  graphChanged();
}

/* ---------- budovy ---------- */
function makeBuilding(type, node, fid, active) {
  var def = BUILDINGS[type];
  var id = newId();
  var total = 0, need = {};
  for (var m in def.cost) { need[m] = def.cost[m]; total += def.cost[m]; }
  var b = {
    id: id, type: type, node: node, flag: fid, state: active ? 'active' : 'site',
    site: { need: need, have: {}, inc: {}, used: 0, total: total, builder: 0, coming: 0, work: 0 },
    worker: 0, workerComing: 0,
    slots: (def.inputs || []).map(function (t) { return { types: t, have: 0, inc: 0 }; }),
    timer: 0, hold: null, rest: 0, fw: 0, soldiers: 0, solInc: 0,
    stock: {}, people: {}, status: '', made: 0
  };
  S.buildings[id] = b;
  S.bldAt[node] = id;
  if (def.size === 'large') {
    [0, 2, 3, 4, 5].forEach(function (d) { var n = nb(node, d); if (n >= 0) S.occ[n] = id; });
  }
  return b;
}

/* Hráčská stavba – vrací {ok, msg, building} */
function placeBuilding(type, node) {
  var def = BUILDINGS[type];
  if (!def || def.buildable === false) return { ok: false, msg: 'Neznámá budova.' };
  var spot = buildSpot(node);
  if (!spotFits(type, spot)) return { ok: false, msg: 'Sem se ' + def.name + ' nevejde.' };
  var fn = nb(node, 1);
  var fid = S.flagAt[fn] || placeFlag(fn);
  if (!fid) return { ok: false, msg: 'Chybí místo pro vlajku.' };
  var b = makeBuilding(type, node, fid, false);
  return { ok: true, building: b };
}

function removeBuilding(bid) {
  var b = S.buildings[bid]; if (!b || b.type === 'hq') return;
  var def = BUILDINGS[b.type];
  var wh = nearestWarehouseAny(b.flag, bid);
  if (wh) {
    if (b.worker) addPerson(wh, b.type, 1);
    if (b.site.builder) addPerson(wh, 'builder', 1);
    if (b.soldiers) addPerson(wh, 'soldier', b.soldiers);
  }
  if (b.fw && S.units[b.fw]) { clearResv(S.units[b.fw]); delete S.units[b.fw]; }
  S.bldAt[b.node] = 0;
  if (def.size === 'large') {
    [0, 2, 3, 4, 5].forEach(function (d) { var n = nb(b.node, d); if (n >= 0 && S.occ[n] === bid) S.occ[n] = 0; });
  }
  delete S.buildings[bid];
  if (def.kind === 'mil' && b.soldiers > 0) recomputeTerritory();
}

/* ---------- území ---------- */
function territorySources() {
  var out = [];
  for (var id in S.buildings) {
    var b = S.buildings[id], def = BUILDINGS[b.type];
    if (b.type === 'hq' || (def.kind === 'mil' && b.state === 'active' && b.soldiers > 0)) out.push([b.node, def.terr]);
  }
  return out;
}

function recomputeTerritory() {
  var own = new Uint8Array(S.N), expChanged = false;
  territorySources().forEach(function (src) {
    nodesInRadius(src[0], src[1]).forEach(function (i) { own[i] = 1; });
    nodesInRadius(src[0], src[1] + 3).forEach(function (i) { if (!S.exp[i]) { S.exp[i] = 1; expChanged = true; } });
  });
  var lost = false;
  for (var i = 0; i < S.N; i++) if (S.own[i] && !own[i]) { lost = true; break; }
  S.own = own;
  if (lost) {
    Object.keys(S.roads).forEach(function (rid) {
      var r = S.roads[rid];
      if (r && r.path.some(function (n) { return !own[n]; })) removeRoad(+rid);
    });
    Object.keys(S.flags).forEach(function (fid) {
      var f = S.flags[fid];
      if (f && !own[f.node]) removeFlag(+fid);
    });
    Object.keys(S.buildings).forEach(function (bid) {
      var b = S.buildings[bid];
      if (b && !own[b.node]) removeBuilding(+bid);
    });
  }
  C.terrDirty = true;
  return expChanged;
}

function ownedCount() {
  var c = 0;
  for (var i = 0; i < S.N; i++) c += S.own[i];
  return c;
}
