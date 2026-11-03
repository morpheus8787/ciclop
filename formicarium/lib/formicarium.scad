// =====================================================================
//  Formicarium library – sdílené moduly pro mraveniště-památky
//  Konvence souřadnic (pro všechny modely):
//    x = šířka (vlevo/vpravo), z = výška, y = hloubka dozadu
//    y = 0  ... přední "řez" budovou = pozorovací plocha s komůrkami
//    y > 0  ... zadní polovina budovy (fasáda)
//  Hnízdní jádro (core) zabírá y = 0 .. CORE_T a tiskne se LEŽÍCÍ,
//  komůrkami nahoru => žádné podpěry, plochá čelní plocha pod sklo.
// =====================================================================

// ---------- Velikost mravenců (přepiš v modelu nebo -D 'SPECIES="large"')
//  small  : Tetramorium, Leptothorax, Temnothorax, nanitici (hloubka 6 mm)
//  medium : Lasius, Formica, Myrmica, Tapinoma               (hloubka 10 mm)
//  large  : Messor, Camponotus                               (hloubka 15 mm)
SPECIES = "medium";

// ---------- Hydratace / sklo / spojovací materiál
PLASTER_T   = 6;     // tloušťka sádrové (hydratační) vrstvy ve spodním patře
BACK_T      = 6;     // zadní stěna jádra
PLATE_T     = 3;     // plexisklo / sklo 3 mm
PLATE_CLEAR = 0.3;   // vůle kolem skla v rámečku
TUBE_OD     = 12;    // silikonová hadička k aréně (8x12 mm)
AIRLINE_OD  = 6;     // akvarijní vzduchovací hadička 4/6 mm = zavlažování
MESH_D      = 10;    // kolečko nerezové síťky 0,2 mm na větrání
MESH_RECESS = 0.8;
VENT_D      = 4;     // větrací kanálek
PIN_D       = 1.9;   // kolíky = kousky filamentu 1,75 mm
PIN_L       = 8;
SCREW_PILOT = 2.5;   // M3x12 zápustné samořezné do PETG
SCREW_CLEAR = 3.4;
SCREW_HEAD  = 6.4;
MAGNET_D    = 6.2;   // neodymový magnet 6x2 mm (zatemňovací víčko)
MAGNET_H    = 2.2;
COVER_T     = 3;
BEZEL_LIP   = 4;     // o kolik rámeček přesahuje přes sklo
GALLERY_WALL = 6;    // příčka mezi komůrkami
PLASTER_DROP = 0;    // o kolik sahá sádrová kapsa pod podlahu vlhkých komůrek
$fn = 40;

function species_preset(s) =
    s == "small" ? [6, 4, 7] :
    s == "large" ? [15, 9, 14] :
                   [10, 6, 10];          // [hloubka komůrky, šířka chodby, výška komůrky]

SP      = species_preset(SPECIES);
CH_D    = SP[0];
TUN_W   = SP[1];
CH_H    = SP[2];
CORE_T  = CH_D + PLASTER_T + BACK_T;
FLOOR_H_MIN = CH_H * 1.3 + 7;            // patro = nejvyšší komůrka + strop
WATER_Y = CH_D + PLASTER_T / 2 + 0.5;    // hloubka osy zavlažovacího kanálu
VENT_Y  = max(CH_D / 2, MESH_D / 2 + 1); // hloubka osy větracího kanálku
SOCKET_Y = TUBE_OD / 2 + 1.5;            // hloubka osy hrdla pro hadičku
BEZEL_T = PLATE_T + 2.2;

// ---------------------------------------------------------------------
//  2D (x,z) tvar -> 3D vrstva v hloubce y0..y1
module face_extrude(y0, y1) {
    translate([0, y1, 0]) rotate([90, 0, 0]) linear_extrude(y1 - y0) children();
}

// Komůrka: rovná podlaha, klenutý strop
module chamber2d(w, h) {
    r = min(w / 2, h * 0.5);
    hull() {
        square([w, max(h - r, 0.1)]);
        translate([w / 2, h - r]) scale([w / 2, r]) circle(1, $fn = 48);
    }
}

module tunnel2d(p1, p2, w) {
    hull() { translate(p1) circle(d = w); translate(p2) circle(d = w); }
}

module capsule(p1, p2, d, y) {
    hull() {
        translate([p1[0], y, p1[1]]) sphere(d = d, $fn = 20);
        translate([p2[0], y, p2[1]]) sphere(d = d, $fn = 20);
    }
}

module capsule3(p1, p2, d) {   // body [x, y, z]
    hull() { translate(p1) sphere(d = d, $fn = 20); translate(p2) sphere(d = d, $fn = 20); }
}

// ---------------------------------------------------------------------
//  Generátor pater: komůrka = [x, z, šířka, výška, vlhká(1/0)]
function floors_fit(z0, ztop, fh) = max(1, floor((ztop - z0 - CH_H * 1.3) / fh) + 1);

function _cw(x0, x1, n, wall) = (x1 - x0 - (n - 1) * wall) / n;

function row_chambers(x0, x1, z0, fh, cols, wall = GALLERY_WALL) =
    [ for (i = [0 : len(cols) - 1])
        let(n = cols[i], cw = _cw(x0, x1, n, wall))
        for (c = [0 : n - 1])
            [ x0 + c * (cw + wall), z0 + i * fh, cw,
              CH_H * (((c + i) % 2 == 0) ? 1.3 : 1.0),
              i == 0 ? 1 : 0 ] ];

// Chodby: vodorovné galerie mezi sousedními komůrkami + šikmé rampy
// mezi patry střídavě vpravo / vlevo (mravenci projdou celé hnízdo).
function row_tunnels(x0, x1, z0, fh, cols, wall = GALLERY_WALL) =
    concat(
        [ for (i = [0 : len(cols) - 1])
            let(n = cols[i], cw = _cw(x0, x1, n, wall), z = z0 + i * fh + TUN_W / 2)
            if (n > 1) for (c = [0 : n - 2])
                let(xe = x0 + c * (cw + wall) + cw)
                [[xe - 2, z], [xe + wall + 2, z]] ],
        len(cols) < 2 ? [] :
        [ for (i = [0 : len(cols) - 2])
            let(right = (i % 2 == 0),
                za = z0 + i * fh + CH_H * 0.5,
                zb = z0 + (i + 1) * fh + TUN_W / 2,
                xa = right ? x1 - TUN_W : x0 + TUN_W,
                xb = right ? xa - (zb - za) * 0.7 : xa + (zb - za) * 0.7)
            [[xa, za], [xb, zb]] ]);

function top_floor_vents(chambers, ztop_floor, z_exit) =
    [ for (c = chambers) if (abs(c[1] - ztop_floor) < 0.01)
        [c[0] + c[2] / 2, c[1] + c[3] / 2, z_exit] ];

// ---------------------------------------------------------------------
//  Negativní tvary hnízda
module chamber_cut(c) {
    face_extrude(-1, CH_D) translate([c[0], c[1]]) chamber2d(c[2], c[3]);
    // vlhká komůrka: kapsa na sádru, 1,5 mm schůdek = ryska "lij po sem"
    if (c[4] == 1)
        face_extrude(CH_D - 0.01, CH_D + PLASTER_T) translate([c[0], c[1]]) {
            offset(delta = -1.5) chamber2d(c[2], c[3]);
            if (PLASTER_DROP > 0)    // skrytá kapsa pod podlahou (spojení s vodním kanálem)
                translate([1.5, -PLASTER_DROP]) square([c[2] - 3, PLASTER_DROP + 2]);
        }
}

// port = [x začátku hrdla, x konce (za hranou jádra), z]
module port_cut(port) {
    x0 = min(port[0], port[1]);
    x1 = max(port[0], port[1]);
    translate([x0, SOCKET_Y, port[2]]) rotate([0, 90, 0])
        cylinder(d = TUBE_OD + 0.3, h = x1 - x0, $fn = 48);
}

module nest_cavities(chambers, tunnels, fill_path, vents, port) {
    for (c = chambers) chamber_cut(c);
    face_extrude(-1, CH_D) for (t = tunnels) tunnel2d(t[0], t[1], TUN_W);
    // zavlažovací kanál (hadička 4/6) + sádrový kanál spojující vlhké komůrky
    for (i = [0 : len(fill_path) - 2])
        capsule(fill_path[i], fill_path[i + 1], AIRLINE_OD + 0.6, WATER_Y);
    // větrání z horních (suchých) komůrek
    for (v = vents) capsule([v[0], v[1]], [v[0], v[2] + 12], VENT_D, VENT_Y);
    if (len(port) == 3) port_cut(port);
}

module vent_recesses(vents) {
    for (v = vents)
        translate([v[0], VENT_Y, v[2] - MESH_RECESS]) cylinder(d = MESH_D + 0.4, h = 30);
}

// kolíky v rovině y = konst. (spoj jádro <-> fasáda)
module pin_holes_y(pins, y) {
    for (p = pins) translate([p[0], y, p[1]]) rotate([90, 0, 0])
        cylinder(d = PIN_D, h = 2 * PIN_L, center = true, $fn = 12);
}
// kolíky ve vodorovné rovině z = konst. (spoj dílů nad sebou)
module pin_holes_z(pins, z) {
    for (p = pins) translate([p[0], p[1], z])
        cylinder(d = PIN_D, h = 2 * PIN_L, center = true, $fn = 12);
}

module screw_pilots(screws) {
    for (s = screws) translate([s[0], -1, s[1]]) rotate([-90, 0, 0])
        cylinder(d = SCREW_PILOT, h = 11, $fn = 16);
}

// ---------------------------------------------------------------------
//  Rámeček skla. children(0) = 2D tvar skla, children(1) = 2D vnější obrys,
//  volitelně children(2) = 2D okna (jinak jedno okno přes celé sklo)
module bezel(screws, magnets) {
    difference() {
        face_extrude(-BEZEL_T, 0) children(1);
        face_extrude(-BEZEL_T - 1, 1) intersection() {
            offset(delta = -BEZEL_LIP) children(0);
            if ($children > 2) children(2); else children(0);
        }
        face_extrude(-PLATE_T - 0.2, 1) offset(delta = PLATE_CLEAR) children(0);
        for (s = screws) {
            translate([s[0], -BEZEL_T - 1, s[1]]) rotate([-90, 0, 0])
                cylinder(d = SCREW_CLEAR, h = BEZEL_T + 2, $fn = 20);
            translate([s[0], -BEZEL_T - 0.01, s[1]]) rotate([-90, 0, 0])
                cylinder(d1 = SCREW_HEAD, d2 = SCREW_CLEAR, h = (SCREW_HEAD - SCREW_CLEAR) / 2, $fn = 20);
        }
        for (m = magnets) translate([m[0], -BEZEL_T - 0.01, m[1]]) rotate([-90, 0, 0])
            cylinder(d = MAGNET_D, h = MAGNET_H, $fn = 24);
    }
}

// Zatemňovací víčko na magnety (mravenci chtějí tmu). children(0) = obrys
module cover(magnets, label = "", label_pos = [0, 0], label_size = 6) {
    y0 = -BEZEL_T - COVER_T;
    difference() {
        face_extrude(y0, -BEZEL_T) children(0);
        for (m = magnets) translate([m[0], -BEZEL_T - MAGNET_H, m[1]]) rotate([-90, 0, 0])
            cylinder(d = MAGNET_D, h = MAGNET_H + 1, $fn = 24);
        if (label != "")
            face_extrude(y0 - 1, y0 + 0.6) translate(label_pos)
                text(label, size = label_size, halign = "center", valign = "center",
                     font = "Liberation Serif:style=Bold");
    }
}

// ---------------------------------------------------------------------
//  Zátky
module plugs() {   // tiskne se hlavou dolů (bez převisů)
    // zátka hrdla, když není připojená aréna
    cylinder(d = TUBE_OD + 6, h = 3, $fn = 48);
    translate([0, 0, 3]) cylinder(d = TUBE_OD + 0.1, h = 12, $fn = 48);
    // zátka zavlažovací hadičky (ID 4 mm)
    translate([TUBE_OD + 10, 0, 0]) {
        cylinder(d = 8, h = 3, $fn = 32);
        translate([0, 0, 3]) cylinder(d = 4.2, h = 7, $fn = 24);
    }
}

// ---------------------------------------------------------------------
//  Tisková orientace
module print_core() {            // čelo nahoru, komůrky otevřené nahoru
    translate([0, 0, CORE_T]) rotate([-90, 0, 0]) children();
}
module print_bezel() {           // pohledová strana na podložku
    translate([0, 0, BEZEL_T]) rotate([90, 0, 0]) children();
}
module print_cover() {           // nápis nahoru
    translate([0, 0, -BEZEL_T]) rotate([-90, 0, 0]) children();
}

// nika / okno: místní +x = vnější normála povrchu, z = od spodku niky
module niche(w, h, depth, arch = true) {
    translate([-depth, -w / 2, 0]) cube([depth + 3, w, arch ? h - w / 2 : h]);
    if (arch) translate([-depth, 0, h - w / 2]) rotate([0, 90, 0])
        cylinder(d = w, h = depth + 3, $fn = 20);
}
