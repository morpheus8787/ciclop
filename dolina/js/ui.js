'use strict';
/* Dolina – dotykové rozhraní (panely, menu, hlášky). */

var UI = {
  speed: 1, panel: null, panelKind: null, panelRef: 0, tab: 0, confirmDemolish: 0,
  autoRoads: true, autoFlags: true, refreshT: 0, saveT: 0, modal: null
};
var SAVE_KEY = 'dolina-save-v1';
var PREF_KEY = 'dolina-prefs-v1';

function $(id) { return document.getElementById(id); }
function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

function initUI() {
  try {
    var p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
    if (p.autoRoads !== undefined) UI.autoRoads = p.autoRoads;
    if (p.autoFlags !== undefined) UI.autoFlags = p.autoFlags;
  } catch (e) { /* bez uložených předvoleb */ }
  document.body.addEventListener('click', onAction);
  updateTopBar();
}

function savePrefs() {
  try { localStorage.setItem(PREF_KEY, JSON.stringify({ autoRoads: UI.autoRoads, autoFlags: UI.autoFlags })); } catch (e) { /* ignorovat */ }
}

function toast(msg) {
  var box = $('toasts'), el = document.createElement('div');
  el.className = 'toast'; el.textContent = msg;
  box.appendChild(el);
  setTimeout(function () { el.classList.add('out'); }, 2600);
  setTimeout(function () { el.remove(); }, 3200);
  while (box.children.length > 4) box.firstChild.remove();
}

function costHtml(cost) {
  var s = '';
  for (var m in cost) s += '<span class="cost">' + WARES[m].icon + cost[m] + '</span>';
  return s;
}

/* ---------- horní lišta ---------- */
function updateTopBar() {
  if (!S) return;
  var t = totalStock(), st = t.stock, pp = t.people;
  $('res').innerHTML = ['plank', 'stone', 'log', 'tools'].map(function (k) {
    return '<span class="chip">' + WARES[k].icon + ' ' + (st[k] || 0) + '</span>';
  }).join('') + '<span class="chip">👤 ' + (pp.helper || 0) + '</span>';
  $('speedBtn').textContent = UI.speed === 0 ? '▶️' : '⏩ ' + UI.speed + '×';
  $('spotsBtn').classList.toggle('on', R.showSpots);
  $('goalBtn').textContent = '🎯 ' + Math.min(S.goal + 1, GOALS.length) + '/' + GOALS.length;
}

/* ---------- akce (delegace kliknutí) ---------- */
function onAction(ev) {
  var el = ev.target.closest('[data-a]');
  if (!el) return;
  var a = el.getAttribute('data-a'), v = el.getAttribute('data-v');
  var fn = ACTIONS[a];
  if (fn) { ev.preventDefault(); fn(v, el); }
}

var ACTIONS = {
  speed: function () { var seq = [1, 2, 4, 0]; UI.speed = seq[(seq.indexOf(UI.speed) + 1) % seq.length]; updateTopBar(); },
  spots: function () { R.showSpots = !R.showSpots; updateTopBar(); },
  stock: function () { openModal('stock'); },
  goals: function () { openModal('goals'); },
  menu: function () { openModal('menu'); },
  closeModal: function () { closeModal(); },
  closePanel: function () { closePanel(); },
  tab: function (v) { UI.tab = +v; renderPanel(); },
  build: function (v) { doBuild(v, R.sel); },
  flag: function () {
    var id = placeFlag(R.sel);
    if (!id) { toast('Sem nelze dát vlajku.'); return; }
    openFlagPanel(id);
  },
  road: function (v) { startRoad(+v); },
  connect: function (v) {
    var res = connectAuto(+v);
    toast(res.ok ? 'Připojeno k síti cest.' : res.msg);
    renderPanel();
  },
  removeFlag: function (v) { confirmThen('flag' + v, function () { removeFlag(+v); closePanel(); }); },
  removeRoad: function (v) { confirmThen('road' + v, function () { removeRoad(+v); closePanel(); }); },
  removeBuilding: function (v) { confirmThen('b' + v, function () { removeBuilding(+v); closePanel(); }); },
  pause: function (v) { var b = S.buildings[+v]; if (b) { b.paused = !b.paused; renderPanel(); } },
  endRoad: function () { endRoad(); },
  newGame: function () { confirmThen('new', function () { closeModal(); startNewGame(); }); },
  save: function () { saveGame(true); },
  load: function () { if (loadGame()) { closeModal(); toast('Hra načtena.'); } else toast('Žádná uložená hra.'); },
  help: function () { openModal('help'); },
  autoRoads: function () { UI.autoRoads = !UI.autoRoads; savePrefs(); openModal('menu'); },
  autoFlags: function () { UI.autoFlags = !UI.autoFlags; savePrefs(); openModal('menu'); },
  openB: function (v) { if (S.buildings[+v]) openBuildingPanel(+v); }
};

function confirmThen(key, fn) {
  if (UI.confirmDemolish === key) { UI.confirmDemolish = 0; fn(); return; }
  UI.confirmDemolish = key;
  toast('Klepni znovu pro potvrzení.');
  setTimeout(function () { if (UI.confirmDemolish === key) UI.confirmDemolish = 0; }, 3000);
}

/* ---------- stavba ---------- */
function doBuild(type, node) {
  var res = placeBuilding(type, node);
  if (!res.ok) { toast(res.msg); return; }
  var b = res.building;
  if (UI.autoRoads) {
    var c = connectAuto(b.flag);
    if (!c.ok && c.msg !== 'Už je připojeno.') toast('Postav cestu – ' + c.msg.toLowerCase());
  }
  openBuildingPanel(b.id);
}

function startRoad(fid) {
  if (!S.flags[fid]) return;
  R.roadFrom = fid;
  closePanel();
  $('banner').classList.add('show');
}

function endRoad() {
  R.roadFrom = 0;
  $('banner').classList.remove('show');
}

function roadTap(node) {
  var from = R.roadFrom;
  if (S.flagAt[node] === from) { endRoad(); return; }
  var existed = !!S.flagAt[node];
  var res = buildRoad(from, node, UI.autoFlags);
  if (!res.ok) { toast(res.msg); return; }
  if (existed || nearestWarehouse(res.endFlag) && S.flags[res.endFlag].roads.length > 1) { endRoad(); toast('Cesta postavena.'); }
  else R.roadFrom = res.endFlag; // pokračuj ve stavbě z nové vlajky
}

/* ---------- výběr uzlu ---------- */
function onTap(sx, sy) {
  if (UI.modal) return;
  var node = screenToNode(sx, sy);
  if (node < 0) { closePanel(); return; }
  if (R.roadFrom) { roadTap(node); return; }
  R.sel = node;
  // klepnutí na vlajku budovy zvolí budovu, pokud je vybraná
  if (S.bldAt[node]) { openBuildingPanel(S.bldAt[node]); return; }
  if (S.flagAt[node]) { openFlagPanel(S.flagAt[node]); return; }
  openNodePanel(node);
}

function openNodePanel(node) { UI.panelKind = 'node'; UI.panelRef = node; renderPanel(); }
function openFlagPanel(fid) { UI.panelKind = 'flag'; UI.panelRef = fid; R.sel = S.flags[fid].node; renderPanel(); }
function openBuildingPanel(bid) { UI.panelKind = 'building'; UI.panelRef = bid; R.sel = S.buildings[bid].node; renderPanel(); }

function closePanel() {
  UI.panelKind = null; R.sel = -1;
  $('panel').classList.remove('show');
}

function renderPanel() {
  var html = '';
  if (UI.panelKind === 'node') html = nodePanelHtml(UI.panelRef);
  else if (UI.panelKind === 'flag') html = S.flags[UI.panelRef] ? flagPanelHtml(S.flags[UI.panelRef]) : null;
  else if (UI.panelKind === 'building') html = S.buildings[UI.panelRef] ? buildingPanelHtml(S.buildings[UI.panelRef]) : null;
  if (html === null) { closePanel(); return; }
  if (!UI.panelKind) return;
  $('panelBody').innerHTML = html;
  $('panel').classList.add('show');
}

function nodePanelHtml(i) {
  if (!S.own[i]) return '<h3>Mimo území</h3><p class="muted">Rozšiř území stavbou vojenské budovy u hranice.</p>';
  var spot = buildSpot(i), h = '';
  var terrName = ['Voda', 'Písek', 'Louka', 'Hory', 'Sníh'][S.ter[i]];
  var info = terrName;
  if (S.obj[i] === O_TREE) info += ' · strom';
  if (S.obj[i] === O_STONE) info += ' · balvan';
  if (S.obj[i] === O_FIELD) info += ' · pole';
  if (S.res[i]) info += ' · ložisko: ' + RES_INFO[S.res[i]].name;
  h += '<h3>' + esc(info) + '</h3>';
  var actions = '';
  if (canFlag(i)) actions += '<button data-a="flag">🚩 Vlajka' + (S.roadAt[i] ? ' (rozdělit cestu)' : '') + '</button>';
  if (S.roadAt[i]) actions += '<button class="danger" data-a="removeRoad" data-v="' + S.roadAt[i] + '">🗑 Zbourat cestu</button>';
  if (actions) h += '<div class="row">' + actions + '</div>';
  if (spot) {
    var types = Object.keys(BUILDINGS).filter(function (t) { return BUILDINGS[t].buildable !== false && spotFits(t, spot); });
    var cats = CATEGORIES.map(function (c, ix) { return types.some(function (t) { return BUILDINGS[t].cat === ix; }) ? ix : -1; }).filter(function (x) { return x >= 0; });
    if (cats.indexOf(UI.tab) < 0) UI.tab = cats[0];
    h += '<div class="tabs">' + cats.map(function (ix) {
      return '<button data-a="tab" data-v="' + ix + '" class="' + (ix === UI.tab ? 'on' : '') + '">' + CATEGORIES[ix] + '</button>';
    }).join('') + '</div>';
    h += '<div class="grid">' + types.filter(function (t) { return BUILDINGS[t].cat === UI.tab; }).map(function (t) {
      var d = BUILDINGS[t];
      return '<button class="bbtn" data-a="build" data-v="' + t + '"><span class="ic">' + d.icon + '</span><b>' + d.name + '</b><small>' + costHtml(d.cost) + '</small></button>';
    }).join('') + '</div>';
    h += '<p class="muted">' + ['', 'Malé stavební místo', 'Velké stavební místo', 'Místo pro důl'][spot] + '</p>';
  } else if (!actions) {
    h += '<p class="muted">Zde nelze stavět. Zapni 🏗 pro zobrazení stavebních míst.</p>';
  }
  return h;
}

function flagPanelHtml(f) {
  var b = flagBuilding(f.id);
  var h = '<h3>🚩 Vlajka</h3>';
  var conn = !!nearestWarehouse(f.id) && (f.roads.length > 0 || (b && isWarehouse(b)));
  h += '<p>' + (conn ? 'Napojeno na sklad' : '<span class="warn">Není napojeno na sklad</span>') + ' · zboží: ' + f.wares.length + '/' + FLAG_CAP + '</p>';
  h += '<div class="row"><button class="primary" data-a="road" data-v="' + f.id + '">🛣️ Postavit cestu</button>';
  if (!conn) h += '<button data-a="connect" data-v="' + f.id + '">🔗 Připojit automaticky</button>';
  if (b) h += '<button data-a="openB" data-v="' + b.id + '">' + BUILDINGS[b.type].icon + ' ' + BUILDINGS[b.type].name + '</button>';
  if (!(b && b.type === 'hq')) h += '<button class="danger" data-a="removeFlag" data-v="' + f.id + '">🗑 Zbourat</button>';
  return h + '</div>';
}

function wareList(obj) {
  var keys = Object.keys(obj).filter(function (k) { return obj[k] > 0; });
  if (!keys.length) return '<span class="muted">nic</span>';
  return keys.map(function (k) { return '<span class="chip">' + WARES[k].icon + ' ' + obj[k] + '</span>'; }).join(' ');
}

function buildingPanelHtml(b) {
  var def = BUILDINGS[b.type];
  var h = '<h3>' + def.icon + ' ' + def.name + (b.state === 'site' ? ' <small>(stavba)</small>' : '') + '</h3>';
  if (def.desc) h += '<p class="muted">' + def.desc + '</p>';
  h += '<p><b>Stav:</b> ' + esc(b.status || '—') + '</p>';
  if (b.state === 'site') {
    var mats = Object.keys(b.site.need).map(function (m) {
      return '<span class="chip">' + WARES[m].icon + ' ' + (b.site.have[m] || 0) + '/' + b.site.need[m] + '</span>';
    }).join(' ');
    h += '<p><b>Materiál:</b> ' + mats + ' · postaveno ' + Math.round(100 * b.site.used / b.site.total) + ' %</p>';
  } else if (def.kind === 'store') {
    h += '<p><b>Zásoby:</b> ' + wareList(b.stock) + '</p>';
    h += '<p><b>Lidé:</b> ' + peopleList(b.people) + '</p>';
  } else if (def.kind === 'mil') {
    h += '<p><b>Vojáci:</b> ' + b.soldiers + '/' + def.soldiers + ' · dosah území ' + def.terr + '</p>';
  } else {
    if (b.slots.length) {
      h += '<p><b>Vstupy:</b> ' + b.slots.map(function (s) {
        return '<span class="chip">' + s.types.map(function (t) { return WARES[t].icon; }).join('') + ' ' + s.have + '/' + SLOT_CAP + '</span>';
      }).join(' ') + '</p>';
    }
    if (def.output) h += '<p><b>Výroba:</b> ' + WARES[def.output].icon + ' ' + WARES[def.output].name + ' · vyrobeno ' + b.made + '</p>';
    if (def.kind === 'mine') {
      var left = 0;
      nodesInRadius(b.node, 2).forEach(function (n) { if (S.res[n] === def.res) left += S.resAmt[n]; });
      h += '<p><b>Ložisko:</b> zbývá ' + left + '</p>';
    }
  }
  h += '<div class="row">';
  var conn = b.type === 'hq' || connected(b);
  if (!conn) h += '<button class="primary" data-a="connect" data-v="' + b.flag + '">🔗 Připojit cestou</button>';
  h += '<button data-a="road" data-v="' + b.flag + '">🛣️ Cesta z vlajky</button>';
  if (b.state === 'active' && (def.kind === 'prod' || def.kind === 'field' || def.kind === 'mine')) {
    h += '<button data-a="pause" data-v="' + b.id + '">' + (b.paused ? '▶️ Spustit' : '⏸ Pozastavit') + '</button>';
  }
  if (b.type !== 'hq') h += '<button class="danger" data-a="removeBuilding" data-v="' + b.id + '">🗑 Zbourat</button>';
  return h + '</div>';
}

function peopleList(pp) {
  var keys = Object.keys(pp).filter(function (k) { return pp[k] > 0; });
  if (!keys.length) return '<span class="muted">nikdo</span>';
  return keys.map(function (k) {
    var name = PEOPLE[k] || (BUILDINGS[k] ? BUILDINGS[k].name : k);
    return '<span class="chip">' + esc(name) + ' ' + pp[k] + '</span>';
  }).join(' ');
}

/* ---------- modální okna ---------- */
function openModal(kind) {
  UI.modal = kind;
  var h = '';
  if (kind === 'stock') {
    var t = totalStock();
    h = '<h2>📦 Zásoby</h2><div class="stock">' + Object.keys(WARES).map(function (k) {
      return '<div class="sitem"><span class="ic">' + WARES[k].icon + '</span><span>' + WARES[k].name + '</span><b>' + (t.stock[k] || 0) + '</b></div>';
    }).join('') + '</div><h3>Obyvatelé ve skladech</h3><p>' + peopleList(t.people) + '</p>';
  } else if (kind === 'goals') {
    h = '<h2>🎯 Cíle</h2><ol class="goals">' + GOALS.map(function (g, ix) {
      var prog = g.ware ? ' <small>(' + Math.min(S.stats[g.ware] || 0, g.n) + '/' + g.n + ')</small>' : '';
      return '<li class="' + (ix < S.goal ? 'done' : ix === S.goal ? 'cur' : '') + '">' + (ix < S.goal ? '✅ ' : '') + g.text + prog + '</li>';
    }).join('') + '</ol>' + (S.won ? '<p class="win">🏆 Všechny cíle splněny! Hraj dál, jak se ti líbí.</p>' : '');
  } else if (kind === 'menu') {
    h = '<h2>☰ Menu</h2><div class="col">' +
      '<button data-a="save">💾 Uložit hru</button>' +
      '<button data-a="load">📂 Načíst uloženou hru</button>' +
      '<button data-a="newGame">🗺️ Nová hra (nová mapa)</button>' +
      '<button data-a="autoRoads">' + (UI.autoRoads ? '✅' : '⬜') + ' Automaticky připojit nové budovy cestou</button>' +
      '<button data-a="autoFlags">' + (UI.autoFlags ? '✅' : '⬜') + ' Automaticky přidávat vlajky na cesty</button>' +
      '<button data-a="help">❓ Jak hrát</button></div>' +
      '<p class="muted">Hra se ukládá automaticky každou minutu a při zavření.</p>';
  } else if (kind === 'help') {
    h = HELP_HTML;
  }
  $('modalBody').innerHTML = h;
  $('modal').classList.add('show');
}

function closeModal() { UI.modal = null; $('modal').classList.remove('show'); }

var HELP_HTML = '<h2>❓ Jak hrát Dolinu</h2>' +
  '<h3>Ovládání</h3><ul>' +
  '<li><b>Posun mapy:</b> táhni jedním prstem. <b>Přiblížení:</b> roztáhni dvěma prsty.</li>' +
  '<li><b>Klepnutí na místo</b> otevře nabídku staveb. Tlačítko 🏗 ukáže, kde se dá stavět (žlutý domek = malá/velká budova, oranžový trojúhelník = důl).</li>' +
  '<li><b>Cesty:</b> klepni na vlajku → „Postavit cestu“ → klepni na cíl. Cesta se najde sama. Nové budovy se umí připojit i automaticky.</li></ul>' +
  '<h3>Jak funguje hospodářství</h3><ul>' +
  '<li>Každý úsek cesty mezi dvěma vlajkami má svého nosiče. Víc vlajek = víc nosičů = rychlejší doprava.</li>' +
  '<li>Stavby potřebují prkna 🟫 a kámen 🪨. Dřevorubec → kmeny → Pila → prkna. Kameník těží balvany.</li>' +
  '<li>Hajný sází stromy, aby dřevo nedošlo.</li>' +
  '<li>Jídlo: Rybář 🐟, Statek 🌾 → Mlýn → Pekárna 🍞 (+ Studna 💧), Vepřín → Řezník 🍖.</li>' +
  '<li>Doly (na horách) potřebují jídlo. Barevné tečky na horách ukazují ložiska: černá uhlí, rezavá železo, žlutá zlato, bílá žula.</li>' +
  '<li>Huť taví rudu + uhlí na železo. Nástrojárna vyrábí nářadí 🔨 – každý nový řemeslník ho potřebuje!</li>' +
  '<li>Zbrojíř kuje zbraně ⚔️ – z pomocníka a zbraně vznikne voják. Vojenské budovy u hranice rozšiřují území.</li>' +
  '<li>Mincovna razí mince 🪙 ze zlata a uhlí – to je poslední cíl.</li></ul>' +
  '<h3>Tip pro iPad</h3><p>V Safari dej <b>Sdílet → Přidat na plochu</b>. Hra se pak spouští přes celou obrazovku jako aplikace a funguje i offline.</p>';

/* ---------- uložení ---------- */
function saveGame(manual) {
  try {
    localStorage.setItem(SAVE_KEY, serialize());
    if (manual) toast('Hra uložena.');
  } catch (e) {
    if (manual) toast('Uložení se nezdařilo: ' + e.message);
  }
}

function loadGame() {
  var json = null;
  try { json = localStorage.getItem(SAVE_KEY); } catch (e) { return false; }
  if (!json) return false;
  try { deserialize(json); } catch (e) { toast('Uloženou hru nelze načíst.'); return false; }
  closePanel(); endRoad();
  var hq = S.buildings[S.hq];
  if (hq) centerOn(hq.node);
  updateTopBar();
  return true;
}

function startNewGame() {
  newGame();
  closePanel(); endRoad();
  centerOn(S.buildings[S.hq].node);
  updateTopBar();
  saveGame(false);
}

function uiTick(dt) {
  while (S.msgs.length) toast(S.msgs.shift());
  UI.refreshT += dt; UI.saveT += dt;
  if (UI.refreshT > 0.5) {
    UI.refreshT = 0;
    updateTopBar();
    if (UI.panelKind === 'building' || UI.panelKind === 'flag') renderPanel();
    if (UI.modal === 'stock' || UI.modal === 'goals') openModal(UI.modal);
  }
  if (UI.saveT > 60) { UI.saveT = 0; saveGame(false); }
}
