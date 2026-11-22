'use strict';
/* Testy herní simulace bez prohlížeče: node --test tests/ */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILES = ['data.js', 'map.js', 'world.js', 'econ.js', 'units.js', 'sim.js'];

function load() {
  const ctx = { console, Math, JSON, Object, Array };
  vm.createContext(ctx);
  const src = FILES.map((f) => fs.readFileSync(path.join(__dirname, '..', 'js', f), 'utf8')).join('\n');
  vm.runInContext(src + '\n;this.G = { get S(){return S;}, C, newGame, step, placeBuilding, buildRoad, placeFlag, buildSpot, canFlag, nb, serialize, deserialize, totalStock, ownedCount, removeFlag, removeBuilding, removeRoad, connectAuto: typeof connectAuto==="function"?connectAuto:null, BUILDINGS };', ctx);
  return ctx.G;
}

function run(G, seconds) { for (let t = 0; t < seconds * 10; t++) G.step(0.1); }

/* najde místo dané velikosti co nejblíže sídlu */
function spotNear(G, size, minD) {
  const S = G.S, hq = S.buildings[S.hq].node;
  let best = -1, bd = 1e9;
  for (let i = 0; i < S.N; i++) {
    const sp = G.buildSpot(i);
    const ok = size === 'mine' ? sp === 3 : size === 'large' ? sp === 2 : (sp === 1 || sp === 2);
    if (!ok) continue;
    const dx = (i % S.W) - (hq % S.W), dy = ((i / S.W) | 0) - ((hq / S.W) | 0);
    const d = dx * dx + dy * dy;
    if (d >= (minD || 4) && d < bd) { bd = d; best = i; }
  }
  return best;
}

function connect(G, b) {
  return G.connectAuto(b.flag).ok;
}

test('mapa je deterministická a sídlo stojí na trávě', () => {
  const G1 = load(); G1.newGame(42);
  const G2 = load(); G2.newGame(42);
  assert.strictEqual(G1.serialize(), G2.serialize());
  const S = G1.S;
  assert.ok(S.buildings[S.hq]);
  assert.ok(G1.ownedCount() > 100, 'území sídla');
});

test('vlajky nesmí stát vedle sebe', () => {
  const G = load(); G.newGame(7);
  const S = G.S, hqFlagNode = S.flags[S.buildings[S.hq].flag].node;
  for (let d = 0; d < 6; d++) {
    const n = G.nb(hqFlagNode, d);
    assert.strictEqual(G.canFlag(n), false);
  }
});

test('stavba cesty a rozdělení vlajkou', () => {
  const G = load(); G.newGame(3);
  const S = G.S;
  const spot = spotNear(G, 'small', 9);
  const res = G.placeBuilding('woodcutter', spot);
  assert.ok(res.ok, res.msg);
  assert.ok(connect(G, res.building), 'připojení cestou');
  assert.ok(Object.keys(S.roads).length >= 1);
});

test('dřevorubec a pila vyrábějí prkna', () => {
  const G = load(); G.newGame(11);
  const S = G.S;
  const wc = G.placeBuilding('woodcutter', spotNear(G, 'small', 16));
  assert.ok(wc.ok, wc.msg); assert.ok(connect(G, wc.building));
  const sm = G.placeBuilding('sawmill', spotNear(G, 'small', 9));
  assert.ok(sm.ok, sm.msg); assert.ok(connect(G, sm.building));
  run(G, 400);
  assert.strictEqual(S.buildings[wc.building.id].state, 'active', 'dřevorubec postaven: ' + S.buildings[wc.building.id].status);
  assert.strictEqual(S.buildings[sm.building.id].state, 'active', 'pila postavena');
  assert.ok((S.stats.log || 0) > 0, 'vyrobeny kmeny');
  assert.ok((S.stats.plank || 0) > 0, 'vyrobena prkna');
});

test('strážnice po obsazení rozšíří území', () => {
  const G = load(); G.newGame(5);
  const before = G.ownedCount();
  const res = G.placeBuilding('guardhouse', spotNear(G, 'small', 40));
  assert.ok(res.ok, res.msg); assert.ok(connect(G, res.building));
  run(G, 300);
  assert.ok(G.ownedCount() > before, 'území vzrostlo');
});

test('uložení a načtení zachová stav', () => {
  const G = load(); G.newGame(9);
  const wc = G.placeBuilding('woodcutter', spotNear(G, 'small', 9));
  connect(G, wc.building);
  run(G, 30);
  const json = G.serialize();
  G.deserialize(json);
  assert.strictEqual(G.serialize(), json);
  run(G, 30);
});

test('zbourání vlajky odstraní budovu i cesty', () => {
  const G = load(); G.newGame(13);
  const S = G.S;
  const res = G.placeBuilding('quarry', spotNear(G, 'small', 9));
  connect(G, res.building);
  run(G, 5);
  G.removeFlag(res.building.flag);
  assert.ok(!S.buildings[res.building.id]);
  run(G, 20);
});
