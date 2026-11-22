'use strict';
/* Dolina – mapa: mřížka uzlů (šestiúhelníkové sousedství), generátor krajiny. */

var S = null;            // herní stav (serializovatelný)
var C = { nbr: null, routes: {}, gver: 0, terrDirty: true, conn: {}, connVer: -1 };  // cache

// směry: 0 V, 1 JV, 2 JZ, 3 Z, 4 SZ, 5 SV
var DIR_EVEN = [[1, 0], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1]];
var DIR_ODD = [[1, 0], [1, 1], [0, 1], [-1, 0], [0, -1], [1, -1]];

function rnd() {
  var t = (S.rs = (S.rs + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

function buildNeighbors(W, H) {
  var nbr = new Int32Array(W * H * 6);
  for (var y = 0; y < H; y++) {
    var dirs = (y & 1) ? DIR_ODD : DIR_EVEN;
    for (var x = 0; x < W; x++) {
      var i = y * W + x;
      for (var d = 0; d < 6; d++) {
        var nx = x + dirs[d][0], ny = y + dirs[d][1];
        nbr[i * 6 + d] = (nx >= 0 && ny >= 0 && nx < W && ny < H) ? ny * W + nx : -1;
      }
    }
  }
  return nbr;
}

function nb(i, d) { return C.nbr[i * 6 + d]; }

function hexDist(a, b) {
  var W = S.W;
  var ax = a % W, ay = (a / W) | 0, bx = b % W, by = (b / W) | 0;
  var aq = ax - ((ay - (ay & 1)) >> 1), bq = bx - ((by - (by & 1)) >> 1);
  var dq = aq - bq, dr = ay - by;
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2;
}

/* všechny uzly v hex. vzdálenosti <= r */
function nodesInRadius(c, r) {
  var W = S.W, H = S.H, cx = c % W, cy = (c / W) | 0, out = [];
  for (var y = Math.max(0, cy - r); y <= Math.min(H - 1, cy + r); y++) {
    for (var x = Math.max(0, cx - r - 1); x <= Math.min(W - 1, cx + r + 1); x++) {
      var i = y * W + x;
      if (hexDist(c, i) <= r) out.push(i);
    }
  }
  return out;
}

function elev(i) {
  var t = S.ter[i];
  return (t === T_MOUNT || t === T_SNOW) ? Math.max(0, S.h[i] - 0.6) * 70 : 0;
}

function nodePos(i) {
  var W = S.W, x = i % W, y = (i / W) | 0;
  return [x * TW + ((y & 1) ? TW / 2 : 0) + TW, y * TH + TH - elev(i)];
}

function walkable(i) { var t = S.ter[i]; return t !== T_WATER && t !== T_SNOW; }

/* ---------- šum ---------- */
function valueNoise(W, H, cell) {
  var gw = Math.ceil(W / cell) + 3, gh = Math.ceil(H / cell) + 3;
  var g = new Float32Array(gw * gh);
  for (var k = 0; k < g.length; k++) g[k] = rnd();
  return function (x, y) {
    var fx = x / cell, fy = y / cell, ix = Math.floor(fx), iy = Math.floor(fy);
    var tx = fx - ix, ty = fy - iy;
    tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
    var a = g[iy * gw + ix], b = g[iy * gw + ix + 1], c = g[(iy + 1) * gw + ix], d = g[(iy + 1) * gw + ix + 1];
    return a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty;
  };
}

function fbm(W, H) {
  var oct = [[16, 0.5], [8, 0.27], [4, 0.15], [2, 0.08]].map(function (o) { return [valueNoise(W, H, o[0]), o[1]]; });
  return function (x, y) {
    var s = 0;
    for (var k = 0; k < oct.length; k++) s += oct[k][0](x, y) * oct[k][1];
    return s;
  };
}

/* ---------- generátor ---------- */
function emptyState(W, H, seed) {
  var N = W * H;
  return {
    v: 1, W: W, H: H, N: N, seed: seed, rs: seed | 0,
    ter: new Uint8Array(N), h: new Float32Array(N),
    obj: new Uint8Array(N), objv: new Float32Array(N),
    res: new Uint8Array(N), resAmt: new Uint8Array(N), fish: new Uint8Array(N),
    own: new Uint8Array(N), exp: new Uint8Array(N),
    flagAt: new Int32Array(N), bldAt: new Int32Array(N), occ: new Int32Array(N), roadAt: new Int32Array(N),
    resv: {}, flags: {}, roads: {}, buildings: {}, units: {}, wares: {},
    nid: 1, time: 0, timers: { dispatch: 0, grow: 0, helper: 0, goals: 0, route: 0 },
    stats: {}, goal: 0, won: false, msgs: []
  };
}

function terrainFromHeight(h) {
  if (h < 0.36) return T_WATER;
  if (h < 0.39) return T_SAND;
  if (h < 0.63) return T_GRASS;
  if (h < 0.78) return T_MOUNT;
  return T_SNOW;
}

function generateMap(seed) {
  S = emptyState(MAP_W, MAP_H, seed);
  C.nbr = buildNeighbors(S.W, S.H);
  var W = S.W, H = S.H, N = S.N;
  var hN = fbm(W, H), mN = fbm(W, H), rN = [null, valueNoise(W, H, 6), valueNoise(W, H, 6), valueNoise(W, H, 5), valueNoise(W, H, 6)];
  var cx = W / 2, cy = H / 2;
  for (var i = 0; i < N; i++) {
    var x = i % W, y = (i / W) | 0;
    var px = x + ((y & 1) ? 0.5 : 0), py = y * 0.87;
    var dx = (px - cx) / cx, dy = (y - cy) / cy;
    var d = Math.sqrt(dx * dx + dy * dy);
    var h = hN(px, py) * 1.25 - 0.1;
    h = h - Math.max(0, d - 0.75) * 0.9;          // okraje -> voda
    var dc = Math.sqrt((px - cx) * (px - cx) + (py - cy * 0.87) * (py - cy * 0.87));
    if (dc < 7) { var k = 1 - dc / 7; h = h * (1 - k) + 0.5 * k; } // střed obyvatelný
    S.h[i] = Math.max(0, Math.min(1, h));
    S.ter[i] = terrainFromHeight(S.h[i]);
  }
  var hq = (cy | 0) * W + (cx | 0);
  ensureFeature(hq, T_MOUNT, 16, 18, 0.72);
  ensureFeature(hq, T_WATER, 15, 10, 0.3);

  // objekty a suroviny
  for (i = 0; i < N; i++) {
    x = i % W; y = (i / W) | 0;
    var t = S.ter[i];
    if (t === T_GRASS) {
      var m = mN(x + 100, y * 0.87 + 50);
      if ((m > 0.52 && rnd() < 0.55) || rnd() < 0.03) { S.obj[i] = O_TREE; S.objv[i] = 1; }
      else if (nearTerrain(i, T_MOUNT) && rnd() < 0.18) { S.obj[i] = O_STONE; S.objv[i] = 5 + ((rnd() * 4) | 0); }
      else if (rnd() < 0.008) { S.obj[i] = O_STONE; S.objv[i] = 5 + ((rnd() * 4) | 0); }
    } else if (t === T_MOUNT) {
      var best = 0, bv = 0.55;
      for (var r = 1; r <= 4; r++) {
        var v = rN[r](x, y) + (r === R_GOLD ? -0.08 : 0);
        if (v > bv) { bv = v; best = r; }
      }
      if (best) { S.res[i] = best; S.resAmt[i] = 6 + ((rnd() * 10) | 0); }
    } else if (t === T_WATER) {
      if (nearWalkable(i)) S.fish[i] = 4 + ((rnd() * 5) | 0);
    }
  }
  ensureResources(hq);
  prepareStart(hq);
  return hq;
}

function nearTerrain(i, t) {
  for (var d = 0; d < 6; d++) { var n = nb(i, d); if (n >= 0 && S.ter[n] === t) return true; }
  return false;
}
function nearWalkable(i) {
  for (var d = 0; d < 6; d++) { var n = nb(i, d); if (n >= 0 && walkable(n)) return true; }
  return false;
}

/* zajistí, že v dosahu startu je hora / voda */
function ensureFeature(hq, terr, maxDist, minCount, hval) {
  var cnt = 0, near = nodesInRadius(hq, maxDist);
  for (var k = 0; k < near.length; k++) if (S.ter[near[k]] === terr) cnt++;
  if (cnt >= minCount) return;
  var ang = rnd() * Math.PI * 2, W = S.W;
  var cxp = (hq % W) + Math.cos(ang) * 11, cyp = ((hq / W) | 0) + Math.sin(ang) * 11;
  var c = Math.round(cyp) * W + Math.round(cxp);
  if (c < 0 || c >= S.N) c = hq + 11;
  var blob = nodesInRadius(c, 3);
  for (k = 0; k < blob.length; k++) {
    var i = blob[k], dd = hexDist(c, i);
    if (terr === T_MOUNT) { S.h[i] = Math.max(S.h[i], hval - dd * 0.025); }
    else { S.h[i] = Math.min(S.h[i], hval + dd * 0.02); }
    S.ter[i] = terrainFromHeight(S.h[i]);
    if (terr === T_MOUNT && S.ter[i] === T_SNOW && dd > 0) { S.ter[i] = T_MOUNT; }
  }
}

function ensureResources(hq) {
  var near = nodesInRadius(hq, 17), mounts = [], have = {};
  for (var k = 0; k < near.length; k++) {
    var i = near[k];
    if (S.ter[i] === T_MOUNT) { mounts.push(i); if (S.res[i]) have[S.res[i]] = true; }
  }
  mounts.sort(function (a, b) { return hexDist(hq, a) - hexDist(hq, b); });
  var need = [R_COAL, R_IRON, R_GOLD, R_GRANITE].filter(function (r) { return !have[r]; });
  for (var n = 0; n < need.length && mounts.length; n++) {
    var c = mounts[(n * 5) % mounts.length];
    var area = nodesInRadius(c, 1);
    for (k = 0; k < area.length; k++) if (S.ter[area[k]] === T_MOUNT) { S.res[area[k]] = need[n]; S.resAmt[area[k]] = 10; }
  }
}

function prepareStart(hq) {
  var core = nodesInRadius(hq, 3);
  for (var k = 0; k < core.length; k++) {
    var i = core[k];
    S.ter[i] = T_GRASS; S.h[i] = 0.5; S.obj[i] = O_NONE; S.res[i] = 0;
  }
  // pár stromů a kamenů v dosahu startu
  var ring = nodesInRadius(hq, 8).filter(function (i) { return hexDist(hq, i) >= 4 && S.ter[i] === T_GRASS && !S.obj[i]; });
  var trees = 0, stones = 0;
  for (k = 0; k < ring.length * 3 && (trees < 14 || stones < 4); k++) {
    var j = ring[(rnd() * ring.length) | 0];
    if (S.obj[j]) continue;
    if (stones < 4 && rnd() < 0.3) { S.obj[j] = O_STONE; S.objv[j] = 7; stones++; }
    else if (trees < 14) { S.obj[j] = O_TREE; S.objv[j] = 1; trees++; }
  }
}
