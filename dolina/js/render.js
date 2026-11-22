'use strict';
/* Dolina – vykreslování na canvas (procedurální grafika). */

var R = {
  canvas: null, ctx: null, dpr: 1, w: 0, h: 0,
  cam: { x: 0, y: 0, z: 1.6 }, terr: null,
  showSpots: false, sel: -1, roadFrom: 0, t: 0, connCache: {}, connVer: -1
};
var PLAYER = '#2f6fd6';

function hash(i) { var x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }

function initRender(canvas) {
  R.canvas = canvas;
  R.ctx = canvas.getContext('2d');
  resizeRender();
}

function resizeRender() {
  R.dpr = Math.min(window.devicePixelRatio || 1, 2);
  R.w = window.innerWidth; R.h = window.innerHeight;
  R.canvas.width = Math.round(R.w * R.dpr); R.canvas.height = Math.round(R.h * R.dpr);
  R.canvas.style.width = R.w + 'px'; R.canvas.style.height = R.h + 'px';
  clampCam();
}

function centerOn(node) {
  var p = nodePos(node);
  R.cam.x = p[0] - R.w / 2 / R.cam.z;
  R.cam.y = p[1] - R.h / 2 / R.cam.z;
  clampCam();
}

function clampCam() {
  if (!S) return;
  var mw = (S.W + 2) * TW, mh = (S.H + 2) * TH, z = R.cam.z;
  R.cam.x = Math.max(-R.w / z / 2, Math.min(mw - R.w / z / 2, R.cam.x));
  R.cam.y = Math.max(-R.h / z / 2, Math.min(mh - R.h / z / 2, R.cam.y));
}

function screenToWorld(sx, sy) { return [sx / R.cam.z + R.cam.x, sy / R.cam.z + R.cam.y]; }

function screenToNode(sx, sy) {
  var w = screenToWorld(sx, sy), best = -1, bd = Infinity;
  var ry = Math.round((w[1] - TH) / TH);
  for (var y = ry - 1; y <= ry + 2; y++) {
    if (y < 0 || y >= S.H) continue;
    var rx = Math.round((w[0] - TW) / TW);
    for (var x = rx - 1; x <= rx + 1; x++) {
      if (x < 0 || x >= S.W) continue;
      var i = y * S.W + x, p = nodePos(i);
      var d = (p[0] - w[0]) * (p[0] - w[0]) + (p[1] - w[1]) * (p[1] - w[1]);
      if (d < bd) { bd = d; best = i; }
    }
  }
  return bd < TW * TW ? best : -1;
}

/* ---------- terén ---------- */
function vertexColor(i) {
  if (!S.exp[i]) return [14, 18, 24];
  var t = S.ter[i], v = hash(i), h = S.h[i], c;
  if (t === T_WATER) c = nearWalkable(i) ? [62, 124, 176] : [40, 88, 146];
  else if (t === T_SAND) c = [212, 194, 138];
  else if (t === T_GRASS) {
    var k = Math.max(0, Math.min(1, (h - 0.39) / 0.24));
    c = [100 + v * 22 - k * 20, 152 + v * 18 - k * 18, 60 + v * 10 - k * 8];
  } else if (t === T_MOUNT) { var m = (h - 0.63) / 0.15; c = [122 + m * 30 + v * 10, 108 + m * 28 + v * 8, 90 + m * 24]; }
  else c = [232, 236, 242];
  var nw = nb(i, 4), se = nb(i, 1);
  var hn = nw >= 0 ? S.h[nw] : h, hs = se >= 0 ? S.h[se] : h;
  var mult = (t === T_MOUNT || t === T_SNOW) ? 7 : 3;
  var L = Math.max(0.72, Math.min(1.3, 1 + (hn - hs) * mult));
  if (t === T_WATER) L = 1;
  return [c[0] * L, c[1] * L, c[2] * L];
}

function buildTerrain() {
  if (!R.terr) R.terr = document.createElement('canvas');
  var c = R.terr;
  c.width = (S.W + 2) * TW; c.height = (S.H + 2) * TH;
  var g = c.getContext('2d');
  g.fillStyle = '#0e1218'; g.fillRect(0, 0, c.width, c.height);
  var cols = new Array(S.N), pos = new Array(S.N);
  for (var i = 0; i < S.N; i++) { cols[i] = vertexColor(i); pos[i] = nodePos(i); }
  g.lineWidth = 0.8; g.lineJoin = 'round';
  function tri(a, b, d) {
    if (b < 0 || d < 0) return;
    var ca = cols[a], cb = cols[b], cd = cols[d];
    var col = 'rgb(' + ((ca[0] + cb[0] + cd[0]) / 3 | 0) + ',' + ((ca[1] + cb[1] + cd[1]) / 3 | 0) + ',' + ((ca[2] + cb[2] + cd[2]) / 3 | 0) + ')';
    g.fillStyle = col; g.strokeStyle = col;
    g.beginPath(); g.moveTo(pos[a][0], pos[a][1]); g.lineTo(pos[b][0], pos[b][1]); g.lineTo(pos[d][0], pos[d][1]); g.closePath();
    g.fill(); g.stroke();
  }
  for (i = 0; i < S.N; i++) { tri(i, nb(i, 0), nb(i, 1)); tri(i, nb(i, 1), nb(i, 2)); }
  // značky surovin v horách (jen prozkoumané a vlastní území)
  for (i = 0; i < S.N; i++) {
    if (S.res[i] && S.own[i]) {
      g.fillStyle = RES_INFO[S.res[i]].color; g.globalAlpha = 0.75;
      g.beginPath(); g.arc(pos[i][0], pos[i][1] - 1, 2.2, 0, 7); g.fill();
      g.globalAlpha = 1;
    }
  }
  C.terrDirty = false;
}

/* ---------- objekty ---------- */
function drawTree(g, x, y, gr, i) {
  var s = 0.3 + 0.7 * gr;
  g.fillStyle = 'rgba(0,0,0,0.18)';
  g.beginPath(); g.ellipse(x + 2 * s, y, 7 * s, 2.6 * s, 0, 0, 7); g.fill();
  g.fillStyle = '#5a3b1e'; g.fillRect(x - 1.2 * s, y - 6 * s, 2.4 * s, 6 * s);
  if (hash(i) < 0.45) {
    var cs = ['#2c5a2a', '#356a30', '#43803a'];
    for (var k = 0; k < 3; k++) {
      var yy = y - 4 * s - k * 5 * s, ww = (8 - k * 2) * s;
      g.fillStyle = cs[k];
      g.beginPath(); g.moveTo(x - ww, yy); g.lineTo(x, yy - 9 * s); g.lineTo(x + ww, yy); g.closePath(); g.fill();
    }
  } else {
    g.fillStyle = '#346b2c'; g.beginPath(); g.arc(x - 3 * s, y - 10 * s, 5 * s, 0, 7); g.fill();
    g.fillStyle = '#3f7d34'; g.beginPath(); g.arc(x + 2.5 * s, y - 11 * s, 5.5 * s, 0, 7); g.fill();
    g.fillStyle = '#5a9c45'; g.beginPath(); g.arc(x + 0.5 * s, y - 15 * s, 4.5 * s, 0, 7); g.fill();
  }
}

function drawStone(g, x, y, a, i) {
  var n = Math.max(1, Math.ceil(a / 2.5));
  var off = [[0, 0], [-5, 1], [4, 2], [-1, -3]];
  for (var k = 0; k < n; k++) {
    var ox = off[k][0], oy = off[k][1], r = 4.5 - k * 0.6 + hash(i + k) * 1.5;
    g.fillStyle = 'rgba(0,0,0,0.2)'; g.beginPath(); g.ellipse(x + ox + 1.5, y + oy + 1, r * 1.2, r * 0.5, 0, 0, 7); g.fill();
    g.fillStyle = '#8f9196'; g.beginPath(); g.ellipse(x + ox, y + oy - r * 0.5, r * 1.1, r * 0.8, 0, 0, 7); g.fill();
    g.fillStyle = '#b8babf'; g.beginPath(); g.ellipse(x + ox - r * 0.3, y + oy - r * 0.8, r * 0.5, r * 0.35, 0, 0, 7); g.fill();
  }
}

function drawField(g, x, y, gr) {
  var r = (110 + (222 - 110) * gr) | 0, gg = (160 + (190 - 160) * gr) | 0, b = (60 + (70 - 60) * gr) | 0;
  g.fillStyle = 'rgb(' + r + ',' + gg + ',' + b + ')';
  g.beginPath(); g.moveTo(x - 12, y); g.lineTo(x, y - 7); g.lineTo(x + 12, y); g.lineTo(x, y + 7); g.closePath(); g.fill();
  g.strokeStyle = 'rgba(80,60,20,0.35)'; g.lineWidth = 0.8;
  for (var k = -2; k <= 2; k++) { g.beginPath(); g.moveTo(x - 6 + k * 3, y - 3.5 + k * 1.75 + 3.5); g.lineTo(x + 6 + k * 3 - 6, y + 3.5 + k * 1.75 - 7 + 3.5); g.stroke(); }
}

function drawFlag(g, x, y, f) {
  var wave = Math.sin(R.t * 4 + f.id) * 1.5;
  g.strokeStyle = '#3a2a1a'; g.lineWidth = 1.2;
  g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 15); g.stroke();
  g.fillStyle = PLAYER;
  g.beginPath(); g.moveTo(x, y - 15); g.quadraticCurveTo(x + 4, y - 16 + wave, x + 8, y - 14 + wave * 0.5);
  g.lineTo(x + 8, y - 9 + wave * 0.5); g.quadraticCurveTo(x + 4, y - 10 + wave, x, y - 9); g.closePath(); g.fill();
  for (var k = 0; k < f.wares.length && k < FLAG_CAP; k++) {
    var w = S.wares[f.wares[k]]; if (!w) continue;
    var ox = -4 - (k % 4) * 4, oy = -2 - ((k / 4) | 0) * 4;
    g.fillStyle = WARES[w.type].color; g.fillRect(x + ox - 1.6, y + oy - 1.6, 3.4, 3.4);
    g.strokeStyle = 'rgba(0,0,0,0.5)'; g.lineWidth = 0.5; g.strokeRect(x + ox - 1.6, y + oy - 1.6, 3.4, 3.4);
  }
}

function house(g, x, y, w, hgt, roof, wall) {
  g.fillStyle = 'rgba(0,0,0,0.22)'; g.beginPath(); g.ellipse(x + 3, y + 1, w * 0.75, w * 0.25, 0, 0, 7); g.fill();
  g.fillStyle = wall || '#eadcbd'; g.strokeStyle = '#6b5638'; g.lineWidth = 0.8;
  g.fillRect(x - w / 2, y - hgt, w, hgt); g.strokeRect(x - w / 2, y - hgt, w, hgt);
  g.fillStyle = roof;
  g.beginPath(); g.moveTo(x - w / 2 - 2.5, y - hgt); g.lineTo(x, y - hgt - w * 0.55); g.lineTo(x + w / 2 + 2.5, y - hgt); g.closePath(); g.fill();
  g.strokeStyle = 'rgba(0,0,0,0.35)'; g.stroke();
  g.fillStyle = '#4b3420'; g.fillRect(x - 2, y - 6, 4, 6);
  g.fillStyle = '#9cc6e8'; g.fillRect(x - w / 2 + 2.5, y - hgt + 3, 3.5, 3); g.fillRect(x + w / 2 - 6, y - hgt + 3, 3.5, 3);
}

function tower(g, x, y, w, hgt, roof) {
  g.fillStyle = 'rgba(0,0,0,0.22)'; g.beginPath(); g.ellipse(x + 3, y + 1, w * 0.8, w * 0.3, 0, 0, 7); g.fill();
  g.fillStyle = '#c9c3b5'; g.strokeStyle = '#5d584e'; g.lineWidth = 0.8;
  g.fillRect(x - w / 2, y - hgt, w, hgt); g.strokeRect(x - w / 2, y - hgt, w, hgt);
  for (var k = 0; k < 3; k++) g.fillRect(x - w / 2 + k * (w / 2.5), y - hgt - 3, w / 5, 3);
  g.fillStyle = '#3a3a3a'; g.fillRect(x - 2, y - 7, 4, 7);
  g.strokeStyle = '#3a2a1a'; g.beginPath(); g.moveTo(x, y - hgt - 3); g.lineTo(x, y - hgt - 13); g.stroke();
  g.fillStyle = roof; g.fillRect(x, y - hgt - 13, 7, 4.5);
}

function drawBuilding(g, b) {
  var p = nodePos(b.node), x = p[0], y = p[1], def = BUILDINGS[b.type];
  var large = def.size === 'large';
  if (b.state === 'site') { drawSite(g, x, y, b, large); return; }
  if (b.type === 'hq') {
    tower(g, x - 15, y - 2, 9, 26, PLAYER); tower(g, x + 15, y - 2, 9, 26, PLAYER);
    house(g, x, y + 2, 26, 18, def.roof, '#efe3c6');
  } else if (def.kind === 'mil') {
    if (large) { tower(g, x - 12, y, 10, 24, PLAYER); tower(g, x + 12, y, 10, 24, PLAYER); tower(g, x, y + 3, 14, 18, PLAYER); }
    else tower(g, x, y, b.type === 'watchtower' ? 11 : 13, b.type === 'watchtower' ? 26 : 17, PLAYER);
  } else if (def.kind === 'mine') {
    g.fillStyle = 'rgba(0,0,0,0.25)'; g.beginPath(); g.ellipse(x, y, 11, 4, 0, 0, 7); g.fill();
    g.fillStyle = '#2a2018'; g.beginPath(); g.arc(x, y - 2, 8, Math.PI, 0); g.lineTo(x + 8, y); g.lineTo(x - 8, y); g.fill();
    g.strokeStyle = '#8b5a2b'; g.lineWidth = 2.2;
    g.beginPath(); g.moveTo(x - 8, y); g.lineTo(x - 8, y - 9); g.lineTo(x + 8, y - 9); g.lineTo(x + 8, y); g.stroke();
  } else {
    house(g, x, y, large ? 26 : 17, large ? 15 : 12, def.roof);
    if (b.timer > 0 && def.kind === 'prod') {
      for (var k = 0; k < 3; k++) {
        var ph = (R.t * 0.8 + k / 3) % 1;
        g.fillStyle = 'rgba(220,220,220,' + (0.5 * (1 - ph)) + ')';
        g.beginPath(); g.arc(x + 5 + ph * 4, y - 22 - ph * 14, 2 + ph * 3, 0, 7); g.fill();
      }
    }
  }
  var iy = def.kind === 'mine' ? y - 17 : y - (large ? 34 : 26);
  if (def.kind === 'mil') iy = y - 36;
  g.fillStyle = 'rgba(255,255,255,0.85)';
  g.beginPath(); g.arc(x, iy, 6.5, 0, 7); g.fill();
  g.font = '8px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(def.icon, x, iy + 0.5);
  if (needsAttention(b)) {
    g.fillStyle = '#e53935'; g.beginPath(); g.arc(x + 7, iy - 5, 3.3, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.font = 'bold 5px sans-serif'; g.fillText('!', x + 7, iy - 4.6);
  }
}

function drawSite(g, x, y, b, large) {
  var w = large ? 24 : 16, prog = b.site.total ? b.site.used / b.site.total : 0;
  g.fillStyle = '#b89a6a';
  g.beginPath(); g.moveTo(x - w / 2 - 3, y); g.lineTo(x, y - w * 0.3); g.lineTo(x + w / 2 + 3, y); g.lineTo(x, y + w * 0.3); g.closePath(); g.fill();
  if (prog > 0) {
    var hh = 14 * prog;
    g.fillStyle = 'rgba(234,220,189,0.9)'; g.fillRect(x - w / 2, y - hh, w, hh);
    g.strokeStyle = '#7a5a30'; g.lineWidth = 1.4;
    g.beginPath(); g.moveTo(x - w / 2, y); g.lineTo(x - w / 2, y - 16); g.moveTo(x + w / 2, y); g.lineTo(x + w / 2, y - 16);
    g.moveTo(x - w / 2, y - 16); g.lineTo(x + w / 2, y - 16); g.stroke();
  } else {
    g.strokeStyle = '#7a5a30'; g.lineWidth = 1.2;
    g.beginPath(); g.moveTo(x - 4, y); g.lineTo(x - 4, y - 8); g.moveTo(x + 4, y); g.lineTo(x + 4, y - 8); g.stroke();
  }
  var pl = (b.site.have.plank || 0), st = (b.site.have.stone || 0);
  for (var k = 0; k < Math.min(pl, 4); k++) { g.fillStyle = WARES.plank.color; g.fillRect(x - w / 2 - 8, y - 2 - k * 1.8, 7, 1.6); }
  for (k = 0; k < Math.min(st, 4); k++) { g.fillStyle = '#a7a7a7'; g.beginPath(); g.arc(x + w / 2 + 4 + (k % 2) * 3, y - 1 - ((k / 2) | 0) * 2.5, 1.7, 0, 7); g.fill(); }
  g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x - 10, y + 5, 20, 3);
  g.fillStyle = '#7ddc5a'; g.fillRect(x - 10, y + 5, 20 * prog, 3);
  if (needsAttention(b)) {
    g.fillStyle = '#e53935'; g.beginPath(); g.arc(x, y - 22, 4, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.font = 'bold 6px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('!', x, y - 21.6);
  }
}

function needsAttention(b) {
  if (R.connVer !== C.gver) { R.connCache = {}; R.connVer = C.gver; }
  if (R.connCache[b.id] === undefined) R.connCache[b.id] = b.type === 'hq' || connected(b);
  return !R.connCache[b.id];
}

var ROLE_COLORS = { carrier: '#d1a35c', builder: '#e07b39', worker: '#4a8fd6', soldier: '#2a4a9a', home: '#8b8b8b', field: '#58a058' };

function drawUnit(g, u, pos) {
  var x = pos[0], y = pos[1], moving = true;
  var role = u.kind === 'carrier' ? 'carrier' : u.kind === 'field' ? 'field' : u.role;
  if (u.kind === 'carrier' && u.st === 'idle') moving = false;
  if (u.kind === 'field' && u.st === 'work') moving = false;
  var ph = moving ? Math.sin(R.t * 12 + u.id) : 0;
  g.fillStyle = 'rgba(0,0,0,0.2)'; g.beginPath(); g.ellipse(x, y, 3.2, 1.2, 0, 0, 7); g.fill();
  g.strokeStyle = '#3b2c20'; g.lineWidth = 1.2;
  g.beginPath(); g.moveTo(x - 0.8, y - 4); g.lineTo(x - 0.8 + ph * 1.5, y); g.moveTo(x + 0.8, y - 4); g.lineTo(x + 0.8 - ph * 1.5, y); g.stroke();
  g.fillStyle = ROLE_COLORS[role] || '#999';
  g.fillRect(x - 2.2, y - 9, 4.4, 5.5);
  g.fillStyle = '#f1c9a0'; g.beginPath(); g.arc(x, y - 10.8, 1.9, 0, 7); g.fill();
  if (role === 'soldier') { g.strokeStyle = '#ddd'; g.lineWidth = 0.8; g.beginPath(); g.moveTo(x + 3, y - 1); g.lineTo(x + 3, y - 14); g.stroke(); }
  var carry = u.kind === 'carrier' && u.st === 'carry' && S.wares[u.ware] ? S.wares[u.ware].type : (u.kind === 'field' && u.st === 'back' ? u.carry : null);
  if (carry) {
    g.fillStyle = WARES[carry].color; g.fillRect(x - 2.2, y - 16.5, 4.4, 4);
    g.strokeStyle = 'rgba(0,0,0,0.5)'; g.lineWidth = 0.5; g.strokeRect(x - 2.2, y - 16.5, 4.4, 4);
  }
  if (u.kind === 'field' && u.st === 'work') {
    var a = Math.sin(R.t * 10) * 0.9;
    g.strokeStyle = '#6b4a2b'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x + 2, y - 7); g.lineTo(x + 2 + Math.cos(a - 1) * 6, y - 7 + Math.sin(a - 1) * 6); g.stroke();
  }
}

function drawSpot(g, x, y, sp) {
  g.lineWidth = 0.8; g.strokeStyle = 'rgba(40,30,0,0.8)'; g.fillStyle = '#ffd54a';
  if (sp === 2 || sp === 1) {
    var s = sp === 2 ? 1.35 : 0.9;
    g.beginPath(); g.moveTo(x - 4 * s, y - 1); g.lineTo(x - 4 * s, y - 5 * s); g.lineTo(x, y - 9 * s); g.lineTo(x + 4 * s, y - 5 * s); g.lineTo(x + 4 * s, y - 1); g.closePath();
    g.fill(); g.stroke();
  } else if (sp === 3) {
    g.fillStyle = '#ffb74a';
    g.beginPath(); g.moveTo(x - 5, y - 1); g.lineTo(x, y - 8); g.lineTo(x + 5, y - 1); g.closePath(); g.fill(); g.stroke();
  } else if (sp === 4) {
    g.strokeStyle = '#ffd54a'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 6); g.lineTo(x + 3, y - 5); g.lineTo(x, y - 4); g.stroke();
  }
}

/* ---------- hlavní kreslení ---------- */
function draw(dtReal) {
  R.t += dtReal;
  var g = R.ctx, z = R.cam.z, dpr = R.dpr;
  if (C.terrDirty || !R.terr) buildTerrain();
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.fillStyle = '#0e1218'; g.fillRect(0, 0, R.w, R.h);
  g.setTransform(dpr * z, 0, 0, dpr * z, -R.cam.x * dpr * z, -R.cam.y * dpr * z);
  g.imageSmoothingEnabled = true;
  g.drawImage(R.terr, 0, 0);

  var x0 = R.cam.x - 40, y0 = R.cam.y - 40, x1 = R.cam.x + R.w / z + 40, y1 = R.cam.y + R.h / z + 60;
  var ry0 = Math.max(0, Math.floor(y0 / TH) - 1), ry1 = Math.min(S.H - 1, Math.ceil(y1 / TH) + 1);
  var rx0 = Math.max(0, Math.floor(x0 / TW) - 1), rx1 = Math.min(S.W - 1, Math.ceil(x1 / TW));

  // vodní třpyt
  g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 0.8;
  for (var y = ry0; y <= ry1; y++) for (var x = rx0; x <= rx1; x++) {
    var i = y * S.W + x;
    if (S.ter[i] !== T_WATER || !S.exp[i]) continue;
    var ph = (R.t * 0.5 + hash(i)) % 1;
    if (ph > 0.35) continue;
    var p = nodePos(i);
    g.globalAlpha = Math.sin(ph / 0.35 * Math.PI);
    g.beginPath(); g.moveTo(p[0] - 3, p[1]); g.quadraticCurveTo(p[0], p[1] - 1.5, p[0] + 3, p[1]); g.stroke();
  }
  g.globalAlpha = 1;

  // hranice území
  g.fillStyle = PLAYER;
  for (y = ry0; y <= ry1; y++) for (x = rx0; x <= rx1; x++) {
    i = y * S.W + x;
    if (!S.own[i]) continue;
    var edge = false;
    for (var d = 0; d < 6; d++) { var n = nb(i, d); if (n < 0 || !S.own[n]) { edge = true; break; } }
    if (!edge) continue;
    p = nodePos(i);
    g.beginPath(); g.arc(p[0], p[1] - 2, 1.8, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.beginPath(); g.arc(p[0] - 0.5, p[1] - 2.6, 0.6, 0, 7); g.fill(); g.fillStyle = PLAYER;
  }

  // cesty
  g.lineCap = 'round'; g.lineJoin = 'round';
  for (var rid in S.roads) {
    var r = S.roads[rid];
    g.beginPath();
    for (var k = 0; k < r.path.length; k++) { p = nodePos(r.path[k]); if (k) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]); }
    g.strokeStyle = '#7b5a36'; g.lineWidth = 5; g.stroke();
    g.strokeStyle = '#c8a876'; g.lineWidth = 2.8; g.stroke();
  }

  if (R.showSpots) {
    for (y = ry0; y <= ry1; y++) for (x = rx0; x <= rx1; x++) {
      i = y * S.W + x;
      if (!S.own[i]) continue;
      var sp = buildSpot(i);
      if (!sp && canFlag(i)) sp = 4;
      if (sp) { p = nodePos(i); drawSpot(g, p[0], p[1], sp); }
    }
  }

  // objekty + postavy seřazené podle y
  var list = [];
  for (y = ry0; y <= ry1; y++) for (x = rx0; x <= rx1; x++) {
    i = y * S.W + x;
    if (!S.exp[i]) continue;
    p = nodePos(i);
    if (S.obj[i]) list.push([p[1], 0, i, p]);
    if (S.flagAt[i]) list.push([p[1] + 0.1, 1, S.flagAt[i], p]);
    if (S.bldAt[i]) list.push([p[1] + 0.2, 2, S.bldAt[i], p]);
  }
  for (var uid in S.units) {
    var u = S.units[uid];
    if (u.kind === 'walker' && u.pi === 0 && u.p === 0 && u.path && S.bldAt[u.path[0]]) continue;
    var up = unitPos(u);
    if (!up || up[0] < x0 || up[0] > x1 || up[1] < y0 || up[1] > y1) continue;
    list.push([up[1] + 0.3, 3, u, up]);
  }
  list.sort(function (a, b) { return a[0] - b[0]; });
  for (k = 0; k < list.length; k++) {
    var it = list[k];
    if (it[1] === 0) {
      i = it[2];
      if (S.obj[i] === O_TREE) drawTree(g, it[3][0], it[3][1], S.objv[i], i);
      else if (S.obj[i] === O_STONE) drawStone(g, it[3][0], it[3][1], S.objv[i], i);
      else if (S.obj[i] === O_FIELD) drawField(g, it[3][0], it[3][1], S.objv[i]);
    } else if (it[1] === 1) drawFlag(g, it[3][0], it[3][1], S.flags[it[2]]);
    else if (it[1] === 2) drawBuilding(g, S.buildings[it[2]]);
    else drawUnit(g, it[2], it[3]);
  }

  // výběr
  if (R.sel >= 0) {
    p = nodePos(R.sel);
    g.strokeStyle = '#fff'; g.lineWidth = 1.5;
    g.beginPath(); g.ellipse(p[0], p[1], 9, 4.5, 0, 0, 7); g.stroke();
  }
  if (R.roadFrom && S.flags[R.roadFrom]) {
    p = nodePos(S.flags[R.roadFrom].node);
    var pulse = 7 + Math.sin(R.t * 6) * 2;
    g.strokeStyle = '#ffd54a'; g.lineWidth = 2;
    g.beginPath(); g.ellipse(p[0], p[1], pulse * 1.4, pulse * 0.7, 0, 0, 7); g.stroke();
  }
}
