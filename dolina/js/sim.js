'use strict';
/* Dolina – nová hra, simulační krok, ukládání. */

var TYPED_FIELDS = {
  ter: Uint8Array, h: Float32Array, obj: Uint8Array, objv: Float32Array, res: Uint8Array, resAmt: Uint8Array,
  fish: Uint8Array, own: Uint8Array, exp: Uint8Array, flagAt: Int32Array, bldAt: Int32Array, occ: Int32Array, roadAt: Int32Array
};

function newGame(seed) {
  if (seed === undefined) seed = (Math.random() * 1e9) | 0;
  var hq = generateMap(seed);
  C.routes = {}; C.gver = 0; C.terrDirty = true;
  var fn = nb(hq, 1);
  var fid = newId();
  S.flags[fid] = { id: fid, node: fn, wares: [], roads: [] };
  S.flagAt[fn] = fid;
  var b = makeBuilding('hq', hq, fid, true);
  for (var k in START_STOCK) b.stock[k] = START_STOCK[k];
  for (k in START_PEOPLE) b.people[k] = START_PEOPLE[k];
  recomputeTerritory();
  S.hq = b.id;
  S.msgs.push('Vítej v Dolině! Postav dřevorubce, pilu a kameníka.');
  return S;
}

function step(dt) {
  S.time += dt;
  var T = S.timers;
  for (var uid in S.units) { var u = S.units[uid]; if (u) updateUnit(u, dt); }
  for (var bid in S.buildings) { var b = S.buildings[bid]; if (b) updateBuilding(b, dt); }
  T.dispatch += dt; T.grow += dt; T.helper += dt; T.goals += dt; T.route += dt;
  if (T.dispatch >= 0.5) { T.dispatch = 0; dispatch(); }
  if (T.route >= 2) { T.route = 0; rerouteStuck(); }
  if (T.grow >= 1) { growNature(T.grow); T.grow = 0; }
  if (T.helper >= 12) { T.helper = 0; produceHelpers(); }
  if (T.goals >= 1) { T.goals = 0; checkGoals(); }
}

function serialize() {
  var out = {};
  for (var k in S) {
    out[k] = TYPED_FIELDS[k] ? Array.prototype.slice.call(S[k]) : S[k];
  }
  return JSON.stringify(out);
}

function deserialize(json) {
  var o = JSON.parse(json);
  if (!o || o.v !== 1 || !o.W) throw new Error('Neplatná uložená hra');
  for (var k in TYPED_FIELDS) if (o[k]) o[k] = new TYPED_FIELDS[k](o[k]);
  S = o;
  C.nbr = buildNeighbors(S.W, S.H);
  C.routes = {}; C.gver++; C.terrDirty = true;
  return S;
}
