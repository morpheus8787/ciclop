// =====================================================================
//  COLOSSEUM FORMICARIUM v3 (Řím) – Prusa CORE One (250 x 220 x 270 mm)
//  Podle konceptu: celý eliptický amfiteátr, PŮLKRUHOVÝ výřez vpředu
//  (hnízdo za sklem), mravenčí galerie za oblouky (vidět mezi sloupy),
//  aréna nahoře pod kopulí, vodní věž vlevo, krmítko s poklopem vpravo.
//
//  Díly: core (jádro + přední oblouk), facade (vnitřní tělo s galeriemi),
//        shell (vnější arkáda), plinth_left/right, tower, tower_cap,
//        dome_cap, feeder, feeder_lid, feeder_hatch, bezel, cover, plugs,
//        plate (2D -> DXF), film (2D pás fólie -> DXF)
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";

// ---------- budova (střed elipsy YC za rovinou čela hnízda y = 0)
A = 112;  B = 93;  YC = 58;  H = 118;
TIERS = [[8, 36], [36, 64], [64, 92]];  ATTIC = [92, H];
SHELL_T = 2.25;  SHELL_GAP = 0.15;  N_ARCH = 80;
FILM_T = 0.75;                             // pás PET/PETG fólie 0,5 mm + vůle
FILM_Z = [12, 58];

// ---------- půlkruhový výřez (oblouk) – NOTCH_RZ = NOTCH_RX dá přesný půlkruh
NOTCH_RX = 84;  NOTCH_RZ = 114;
PLATE_R = [NOTCH_RX - 7, NOTCH_RZ - 7];    // sklo (půlelipsa) – laser DXF
PLATE_Z0 = 10;  BEZEL_Z0 = 2;

// ---------- aréna pod kopulí
DOME_D = 120;  DOME_CY = YC + 10;  DOME_GROOVE = 2.6;  DOME_SEAT = 4;
BASIN_R = 55;  ARENA_E = [34, 24];  ARENA_DEPTH = 18;  CAVEA_STEPS = 5;

// ---------- hnízdo
PLASTER_DROP = 6;
Z0 = 22;  FL = [Z0, 48, 76];               // podlahy pater
WATER_Z = Z0 - 4;
GH = CH_H + 2;                             // výška galerie za oblouky
G1 = TIERS[0][0] + 7;  G2 = TIERS[1][0] + 7;

FLOOR0 = row_chambers(-64, 64, Z0, 30, [4]);
LB = [-56, FL[1], 24, CH_H * 1.2, 0];       // plodová komůrka vlevo
RB = [ 32, FL[1], 24, CH_H * 1.2, 0];       // plodová komůrka vpravo
QUEEN = [0, FL[1] + CH_H * 0.8, 22, CH_H * 0.8];   // [cx, cz, poloosa x, poloosa z]
L2 = [-34, FL[2], 28, CH_H * 1.1, 0];
R2 = [  6, FL[2], 28, CH_H * 1.2, 0];
S1 = [-54, 64, 10, CH_H * 0.8, 0];         // slepý výklenek (sklad)
S2 = [ 44, 64, 10, CH_H * 0.8, 0];         // komůrka na odpad
CHAMBERS = concat(FLOOR0, [LB, RB, L2, R2, S1, S2]);

function poly(p) = [ for (i = [0 : len(p) - 2]) [p[i], p[i + 1]] ];
PZ = FL[2] + 3;
TUNNELS = concat(
    row_tunnels(-64, 64, Z0, 30, [4]),
    poly([[-58, 30], [-63, 40], [-50, FL[1] + 3]]),          // rampa L
    poly([[ 58, 30], [ 63, 40], [ 50, FL[1] + 3]]),          // rampa P
    poly([[-24, 32], [-30, 41], [-38, FL[1] + 3]]),          // druhá trasa L
    poly([[ 24, 32], [ 30, 41], [ 38, FL[1] + 3]]),          // druhá trasa P
    poly([[-34, FL[1] + 3], [-16, FL[1] + 5]]),              // jediný vchod ke královně
    poly([[-46, FL[1] + 9], [-40, 68], [-28, FL[2] + 3]]),   // klikatá rampa nahoru L
    poly([[ 46, FL[1] + 9], [ 40, 68], [ 28, FL[2] + 3]]),   // klikatá rampa nahoru P
    poly([[-41, 66], [-48, 67]]), poly([[41, 66], [48, 67]]), // odbočky do výklenků
    poly([[-8, FL[2] + 3], [8, FL[2] + 3]]),                 // spojka nahoře
    poly([[30, PZ], [44, PZ]]));                             // k hrdlu krmítka

FILL = [[-104, WATER_Z], [60, WATER_Z]];
VENTS = [[-28, FL[2] + 6, H], [28, FL[2] + 6, H]];
function dome_front(x) = DOME_CY - sqrt(DOME_D * DOME_D / 4 - x * x);
ENT_X = 14;
ENT_Y = dome_front(ENT_X) + DOME_GROOVE / 2 + 0.8 + TUN_W / 2;

// galerie: x na elipse středu galerie v hloubce y
function gx(y) = let(a = A - SHELL_T - SHELL_GAP - FILM_T - CH_D / 2, b = B - SHELL_T - SHELL_GAP - FILM_T - CH_D / 2)
    a * sqrt(max(0, 1 - pow((y - YC) / b, 2)));
GZ1 = G1 + TUN_W / 2 + 0.5;  GZ2 = G2 + TUN_W / 2 + 0.5;
LINKS = [   // [bod v hnízdě], [bod v galerii]
    [[60, 5, Z0 + 5], [gx(24), 24, GZ1]],
    [[52, 5, FL[1] + 4], [gx(24), 24, GZ2]] ];
PORT_LINK = [[44, 5, PZ], [60, SOCKET_Y, PZ]];
PORT = [58, A + 2, PZ];

SCREWS  = concat([[-50, 6], [0, 6], [50, 6]],
    [ for (a = [15, 60, 90, 120, 165]) [(NOTCH_RX - 3.5) * cos(a), (NOTCH_RZ - 3.5) * sin(a)] ]);
MAGNETS = concat([[-25, 6], [25, 6]],
    [ for (a = [37, 75, 105, 143]) [(NOTCH_RX - 3.5) * cos(a), (NOTCH_RZ - 3.5) * sin(a)] ]);
PINS = [[-60, 70], [60, 70], [0, 40], [0, 92]];

// ---------- podstavec, věž, krmítko
PL = [170, 107];  PL_T = 8;  PL_RECESS = 1.5;
TOWER_POS = [-138, YC - 10];  TOWER_POCKET = 6;  TOWER_SINK = TOWER_POCKET - PL_RECESS;
TUBE40_OD = 40;  TUBE40_ID = 34;  TUBE40_L = 70;  TOWER_BASE_H = 12;
FEEDER_POS = [140, YC - 10];  FEEDER = [48, 40, 32];

// =====================================================================
module semi2d(rx, rz, z0 = 0) intersection() {
    scale([rx, rz]) circle(1, $fn = 160); translate([-500, z0]) square(1000);
}
module notch2d() semi2d(NOTCH_RX, NOTCH_RZ, -1);
module plate2d() semi2d(PLATE_R[0], PLATE_R[1], PLATE_Z0);
module outer2d() semi2d(NOTCH_RX - 0.3, NOTCH_RZ - 0.3, BEZEL_Z0);
module queen2d() translate([QUEEN[0], QUEEN[1]]) scale([QUEEN[2], QUEEN[3]]) circle(1, $fn = 64);
// můstky rámečku přes chodby – drží „ostrůvky“ mezi chodbami
BEZEL_BRIDGES = [[[-74, 39.5], [20, 3]], [[54, 39.5], [20, 3]], [[-1.5, 72], [3, 18]]];
module windows2d() difference() {
    offset(r = 1.2) {
        for (c = CHAMBERS) translate([c[0], c[1]]) chamber2d(c[2], c[3]);
        queen2d();
        for (t = TUNNELS) tunnel2d(t[0], t[1], TUN_W);
    }
    for (b = BEZEL_BRIDGES) translate(b[0]) square(b[1]);
}

module ellipse_prism(a, b, z0, h, fn = 180) translate([0, YC, z0]) scale([a, b, 1]) cylinder(r = 1, h = h, $fn = fn);
module ell_place(t, z) {
    translate([A * cos(t), YC + B * sin(t), z]) rotate([0, 0, atan2(sin(t) / B, cos(t) / A)]) children();
}
function ell_y(t) = YC + B * sin(t);

module arcades(depth = 3.4) {
    for (i = [0 : N_ARCH - 1]) let(t = (i + 0.5) * 360 / N_ARCH) {
        for (tr = TIERS) ell_place(t, tr[0] + 3) niche(5.8, tr[1] - tr[0] - 8, depth);
        if (i % 2 == 0) ell_place(t, ATTIC[0] + 9) niche(3.6, 7, 1.8, arch = false);
    }
    for (zz = [TIERS[0][0], TIERS[0][1], TIERS[1][1], TIERS[2][1], H - 4])
        difference() { ellipse_prism(A + 1, B + 1, zz - 0.7, 1.4); ellipse_prism(A - 0.7, B - 0.7, zz - 1, 2); }
}
module pilasters() for (i = [0 : N_ARCH - 1]) let(t = i * 360 / N_ARCH)
    for (tr = TIERS) ell_place(t, tr[0] + 1) translate([-0.5, -0.9, 0]) cube([1.3, 1.8, tr[1] - tr[0] - 2]);

// galerie se stropem 45° (tisk bez podpěr): otevřená ven, hloubka d
module gallery_cut(z0, gh, d, r_off) {
    ao = A - r_off;  bo = B - r_off;  ai = ao - d;  bi = bo - d;
    difference() {
        union() {
            ellipse_prism(ao + 0.6, bo + 0.6, z0, gh - d);
            difference() {
                ellipse_prism(ao + 0.6, bo + 0.6, z0 + gh - d - 0.01, d);
                translate([0, YC, z0 + gh - d - 0.02]) linear_extrude(d + 0.04, scale = [(ao + 0.6) / ai, (bo + 0.6) / bi])
                    scale([ai, bi]) circle(1, $fn = 180);
            }
        }
        ellipse_prism(ai, bi, z0 - 1, gh + 2);
    }
}

module dome_groove() translate([0, DOME_CY, H - DOME_SEAT]) difference() {
    cylinder(d = DOME_D + DOME_GROOVE, h = 10, $fn = 160);
    translate([0, 0, -1]) cylinder(d = DOME_D - DOME_GROOVE, h = 12, $fn = 160);
}
module basin() {
    for (k = [0 : CAVEA_STEPS]) let(f = k / CAVEA_STEPS)
        translate([0, DOME_CY, H - ARENA_DEPTH + f * (ARENA_DEPTH - 2)])
            scale([ARENA_E[0] + f * (BASIN_R - ARENA_E[0]), ARENA_E[1] + f * (BASIN_R - ARENA_E[1]), 1])
                cylinder(r = 1, h = 40, $fn = 120);
    for (x = [-28 : 7 : 28]) translate([x - 0.6, DOME_CY - 20, H - ARENA_DEPTH - 1]) cube([1.2, 40, 2]);
}
function ray_s(c, s) = let(a = c * c / (A * A) + s * s / (B * B), b = 2 * (DOME_CY - YC) * s / (B * B),
                           k = (DOME_CY - YC) * (DOME_CY - YC) / (B * B) - 1)
    (-b + sqrt(b * b - 4 * a * k)) / (2 * a);
module arena_vents() for (ang = [55, 90, 125]) let(c = cos(ang), s = sin(ang), r = ray_s(c, s)) {
    translate([0, DOME_CY, H - 8]) rotate([0, 0, ang]) rotate([0, 90, 0]) cylinder(d = 5, h = r + 5, $fn = 24);
    translate([r * c, DOME_CY + r * s, H - 8]) rotate([0, 0, ang]) rotate([0, 90, 0])
        translate([0, 0, -0.8]) cylinder(d = MESH_D + 0.4, h = 5, $fn = 32);
}
module top_steps() for (k = [1 : 3]) ellipse_prism(A - 6 * k, B - 6 * k, H - 2 * k, 20);
module dome_collar() translate([0, DOME_CY, H - 6]) difference() {
    cylinder(d = DOME_D + 9, h = 6, $fn = 160); translate([0, 0, -1]) cylinder(d = DOME_D - 9, h = 8, $fn = 160);
}
// šikmé propojky mezi galeriemi (vidět skrz oblouky)
G_RAMPS = [[40, 50], [82, 72], [108, 98], [150, 140]];   // [úhel dole, úhel nahoře]
function gp(t, z) = let(a = A - SHELL_T - SHELL_GAP - FILM_T - 1, b = B - SHELL_T - SHELL_GAP - FILM_T - 1)
    [a * cos(t), YC + b * sin(t), z];
module gallery_ramps() for (r = G_RAMPS) {
    capsule3(gp(r[0], GZ1), gp((r[0] + r[1]) / 2, (GZ1 + GZ2) / 2), TUN_W);
    capsule3(gp((r[0] + r[1]) / 2, (GZ1 + GZ2) / 2), gp(r[1], GZ2), TUN_W);
}

module links() {
    for (l = LINKS) capsule3(l[0], l[1], TUN_W);
    // levá svislá spojka galerií (skrytá ve fasádě)
    capsule3([-gx(28), 28, GZ1], [-gx(28), 28, GZ2], TUN_W);
}

// ---------- jádro: hnízdo + přední část oblouku s půlkruhovým výřezem
module core() {
    difference() {
        intersection() {
            difference() { union() { ellipse_prism(A, B, 0, H); pilasters(); } arcades(); }
            translate([-500, -500, -1]) cube([1000, 500 + CORE_T, 1000]);
        }
        face_extrude(-200, 0) notch2d();
        dome_groove();
        nest_cavities(CHAMBERS, TUNNELS, FILL, VENTS, PORT);
        face_extrude(-1, CH_D) queen2d();
        capsule3([ENT_X, CH_D / 2, FL[2] + 6], [ENT_X, ENT_Y, H + 4], TUN_W);   // vstup do arény
        capsule3(PORT_LINK[0], PORT_LINK[1], TUN_W);
        links();
        vent_recesses(VENTS);
        screw_pilots(SCREWS);
        pin_holes_y(PINS, CORE_T);
    }
}

// ---------- vnitřní tělo fasády s galeriemi
module facade() {
    r_in = SHELL_T + SHELL_GAP;
    difference() {
        intersection() {
            union() {
                difference() {
                    ellipse_prism(A - r_in, B - r_in, 0, H);
                    top_steps();
                    difference() { ellipse_prism(A, B, FILM_Z[0], FILM_Z[1] - FILM_Z[0]);
                                   ellipse_prism(A - r_in - FILM_T, B - r_in - FILM_T, 0, H); }   // lůžko fólie
                }
                dome_collar();
            }
            translate([-500, CORE_T, -1]) cube(1000);
        }
        gallery_cut(G1, GH, CH_D, r_in + FILM_T);
        gallery_cut(G2, GH, CH_D, r_in + FILM_T);
        gallery_cut(TIERS[2][0] + 2, TIERS[2][1] - TIERS[2][0] - 4, 6, r_in);   // dekorativní ochoz
        gallery_ramps();
        links();
        dome_groove();
        basin();
        arena_vents();
        pin_holes_y(PINS, CORE_T);
    }
}

// ---------- vnější arkáda (navlékne se přes fólii)
module shell() {
    difference() {
        intersection() {
            difference() {
                union() { ellipse_prism(A, B, 0, H); pilasters(); }
                ellipse_prism(A - SHELL_T, B - SHELL_T, -1, H + 2);
                arcades(SHELL_T + 2);
            }
            translate([-500, CORE_T, -1]) cube(1000);
        }
        arena_vents();
    }
}

// délka pásu fólie (půlobvod elipsy za jádrem) – 2D obdélník pro DXF
FILM_LEN = let(a = A - SHELL_T - SHELL_GAP - FILM_T / 2, b = B - SHELL_T - SHELL_GAP - FILM_T / 2,
               t0 = asin((CORE_T - YC) / b), n = 90)
    sum_len(a, b, t0, 180 - t0, n);
function sum_len(a, b, t0, t1, n) = let(dt = (t1 - t0) / n)
    [ for (i = [0 : n - 1]) let(t = t0 + (i + 0.5) * dt) sqrt(pow(a * sin(t), 2) + pow(b * cos(t), 2)) * dt * PI / 180 ] * [ for (i = [0 : n - 1]) 1 ];
module film2d() square([FILM_LEN, FILM_Z[1] - FILM_Z[0] - 1]);

// ---------- podstavec (2 poloviny)
module plinth() {
    difference() {
        union() {
            translate([0, YC, 0]) scale([PL[0], PL[1], 1]) cylinder(r = 1, h = PL_T, $fn = 180);
            translate([0, YC, PL_T]) difference() {
                scale([A + 16, B + 12, 1]) cylinder(r = 1, h = 1.2, $fn = 180);
                translate([0, 0, -1]) scale([A + 11, B + 7, 1]) cylinder(r = 1, h = 4, $fn = 180);
            }
        }
        translate([0, 0, PL_T - PL_RECESS]) intersection() {
            translate([0, YC, 0]) scale([A + 0.4, B + 0.4, 1]) cylinder(r = 1, h = 10, $fn = 180);
            union() { translate([-500, -0.4, 0]) cube(1000);
                      for (sx = [-1, 1]) translate([sx > 0 ? NOTCH_RX - 0.4 : -500 - NOTCH_RX + 0.4, -500, 0]) cube(500); }
        }
        translate([TOWER_POS[0], TOWER_POS[1], PL_T - TOWER_POCKET]) cylinder(d = 46.4, h = 10, $fn = 64);
        hull() {
            translate([TOWER_POS[0], TOWER_POS[1], PL_T - PL_RECESS]) rotate([0, 90, 0]) cylinder(d = 7, h = 1, $fn = 24);
            translate([-A + 4, 13.5, PL_T - PL_RECESS]) rotate([0, 90, 0]) cylinder(d = 7, h = 1, $fn = 24);
        }
        translate([FEEDER_POS[0] - FEEDER[0] / 2 - 2.2, FEEDER_POS[1] - FEEDER[1] / 2 - 2.2, PL_T - PL_RECESS])
            cube([FEEDER[0] + 4.4, FEEDER[1] + 4.4, 10]);
        translate([0, -41, PL_T - 0.8]) linear_extrude(2) text("COLOSSEVM", size = 8, halign = "center",
            valign = "center", font = "Liberation Serif:style=Bold", spacing = 1.2);
        for (y = [YC - 60, YC, YC + 60]) translate([0, y, PL_T / 2]) rotate([0, 90, 0])
            cylinder(d = PIN_D, h = 2 * PIN_L, center = true, $fn = 12);
    }
}

// ---------- krmítko „ara“ (římský oltář) s poklopem
module feeder() {
    w = FEEDER[0];  d = FEEDER[1];  h = FEEDER[2];
    difference() {
        union() {
            hull() { translate([-w / 2 - 2, -d / 2 - 2, 0]) cube([w + 4, d + 4, 3]);
                     translate([-w / 2, -d / 2, 0]) cube([w, d, 5]); }
            translate([-w / 2, -d / 2, 0]) cube([w, d, h]);
            hull() { translate([-w / 2, -d / 2, h - 5]) cube([w, d, 0.01]);
                     translate([-w / 2 - 2, -d / 2 - 2, h - 3]) cube([w + 4, d + 4, 3]); }
        }
        translate([-w / 2 + 2.4, -d / 2 + 2.4, 4]) cube([w - 4.8, d - 4.8, h]);         // vnitřek
        translate([8, 0, 4 - 2.5]) cylinder(d = 16, h = 3, $fn = 48);                    // jamka na cukr/med
        translate([-w / 2 - 1, 0, 4 + TUBE_OD / 2 + 1]) rotate([0, 90, 0]) cylinder(d = TUBE_OD + 0.3, h = 5, $fn = 48);
        translate([0, -d / 2 + 0.8, 16]) rotate([90, 0, 0]) linear_extrude(1.6)
            text("CIBVS", size = 6, halign = "center", valign = "center", font = "Liberation Serif:style=Bold");
    }
}
module feeder_lid() {      // tiskne se vrchem dolů
    w = FEEDER[0];  d = FEEDER[1];
    difference() {
        union() {
            translate([-w / 2 - 2, -d / 2 - 2, 0]) cube([w + 4, d + 4, 3]);
            translate([-w / 2 + 2.7, -d / 2 + 2.7, 3]) cube([w - 5.4, d - 5.4, 3]);
        }
        translate([8, 0, -1]) cylinder(d = 22, h = 10, $fn = 48);                       // otvor poklopu
        translate([-12, 0, -1]) cylinder(d = 6, h = 10, $fn = 24);                      // větrání
        translate([-12, 0, -0.01]) cylinder(d = MESH_D + 0.4, h = MESH_RECESS, $fn = 32);
        translate([-w / 2 + 4.9, -d / 2 + 4.9, 4]) cube([w - 9.8, d - 9.8, 5]);
    }
}
module feeder_hatch() {    // poklop: zátka + příruba s úchytkou
    difference() {
        union() {
            cylinder(d = 30, h = 2, $fn = 48);
            translate([0, 0, 2]) cylinder(d = 21.7, h = 5, $fn = 48);
            hull() { translate([12, 0, 0]) cylinder(d = 8, h = 2, $fn = 24); translate([18, 0, 0]) cylinder(d = 8, h = 2, $fn = 24); }
        }
        translate([0, 0, 3]) cylinder(d = 18, h = 5, $fn = 48);
    }
}

// ---------- vodní věž: podstavec s nálevkou + 4 sloupky, plexi trubka 40/34
MAX_Z = WATER_Z + TOWER_SINK;   // hladina = osa vodního kanálu pod podlahou (spojené nádoby)
module tower() {
    difference() {
        union() {
            cylinder(d = 46, h = TOWER_BASE_H, $fn = 64);
            for (a = [45 : 90 : 360]) rotate([0, 0, a]) translate([TUBE40_OD / 2 + 2, 0, 0])
                cylinder(d = 4, h = TOWER_BASE_H - 3 + TUBE40_L, $fn = 16);
        }
        translate([0, 0, TOWER_BASE_H - 3]) cylinder(d = TUBE40_OD + 0.5, h = 100, $fn = 64);
        translate([0, 0, 5]) cylinder(d1 = 7, d2 = TUBE40_ID, h = TOWER_BASE_H - 8 + 0.01, $fn = 64);
        translate([0, 0, 4.5]) rotate([0, 90, 0]) cylinder(d = AIRLINE_OD + 0.4, h = 30, $fn = 24);
        // ryska MAX na sloupcích (= hladina pod podlahou hnízda)
        translate([0, 0, MAX_Z - 0.5]) difference() {
            cylinder(r = 30, h = 1); cylinder(r = TUBE40_OD / 2 + 2.6, h = 1);
        }
    }
}
module tower_cap() {
    difference() {
        union() {
            cylinder(d = 50, h = 4, $fn = 64);
            translate([0, 0, 4]) cylinder(d1 = 30, d2 = 18, h = 5, $fn = 48);
        }
        for (a = [45 : 90 : 360]) rotate([0, 0, a]) translate([TUBE40_OD / 2 + 2, 0, -1]) cylinder(d = 4.5, h = 4, $fn = 16);
        translate([0, 0, -1]) cylinder(d = 8, h = 20, $fn = 32);      // plnicí otvor
    }
}

// ---------- větrací čepička kopule (do otvoru Ø 30 vyvrtaného v kopuli)
module dome_cap() {
    // kroužek – přilepit zvenku kolem otvoru
    difference() { cylinder(d = 44, h = 1.6, $fn = 64); translate([0, 0, -1]) cylinder(d = 30, h = 4, $fn = 64); }
    difference() { cylinder(d = 34, h = 6, $fn = 64); translate([0, 0, -1]) cylinder(d = 30, h = 8, $fn = 64); }
    // zátka se síťkou (vyndáš = krmení)
    translate([55, 0, 0]) difference() {
        union() { cylinder(d = 40, h = 2.4, $fn = 64); translate([0, 0, 2.4]) cylinder(d = 29.6, h = 4, $fn = 64);
                  translate([0, 0, 2.4]) cylinder(d = 26.5, h = 4, $fn = 64); }
        translate([0, 0, -1]) cylinder(d = 20, h = 10, $fn = 48);
        translate([0, 0, 6.4 - 0.8]) cylinder(d = 26.4, h = 2, $fn = 48);   // lůžko síťky Ø 26
        translate([0, 0, 2.4]) difference() { cylinder(d = 27, h = 5, $fn = 48); cylinder(d = 26.4 + 1.2, h = 5, $fn = 48); }
    }
}

module the_bezel() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); windows2d(); }
module the_cover() cover(MAGNETS, "COLOSSEVM", [0, 55], 15) outer2d();
module dome_preview() translate([0, DOME_CY, H - DOME_SEAT]) difference() {
    sphere(d = DOME_D, $fn = 64); sphere(d = DOME_D - 2, $fn = 64); translate([-100, -100, -200]) cube(200);
}
module placed_tower()  translate([TOWER_POS[0], TOWER_POS[1], -TOWER_SINK]) children();
module placed_feeder() translate([FEEDER_POS[0], FEEDER_POS[1], 0]) children();

if (PART == "core")         print_core() core();
if (PART == "facade")       facade();
if (PART == "shell")        shell();
if (PART == "plinth_left")  rotate([0, 0, 90]) intersection() { plinth(); translate([-500, -500, 0]) cube([500, 1000, 100]); }
if (PART == "plinth_right") rotate([0, 0, 90]) intersection() { plinth(); translate([0, -500, 0]) cube([500, 1000, 100]); }
if (PART == "tower")        tower();
if (PART == "tower_cap")    tower_cap();
if (PART == "dome_cap")     dome_cap();
if (PART == "feeder")       feeder();
if (PART == "feeder_lid")   feeder_lid();
if (PART == "feeder_hatch") feeder_hatch();
if (PART == "bezel")        print_bezel() the_bezel();
if (PART == "cover")        print_cover() the_cover();
if (PART == "plugs")        plugs();
if (PART == "plate")        plate2d();
if (PART == "film")         film2d();
if (PART == "core_view")    core();
if (PART == "bezel_view")   { core(); the_bezel(); }
if (PART == "inner_view")   { core(); facade(); }
if (PART == "display")      { translate([0, 0, -PL_T + PL_RECESS]) plinth(); core(); facade(); shell(); }
if (PART == "assembly") {
    translate([0, 0, -PL_T + PL_RECESS]) color("DimGray") render() plinth();
    color("BurlyWood") render() core();
    color("Tan") render() facade();
    color("Wheat") render() shell();
    color("LightBlue", 0.35) face_extrude(-PLATE_T, 0) plate2d();
    color("SaddleBrown") render() the_bezel();
    color("LightBlue", 0.3) dome_preview();
    placed_tower() { color("Wheat") render() tower();
        color("LightBlue", 0.3) translate([0, 0, TOWER_BASE_H - 3]) cylinder(d = TUBE40_OD, h = TUBE40_L);
        translate([0, 0, TOWER_BASE_H - 3 + TUBE40_L]) color("Wheat") render() tower_cap(); }
    placed_feeder() { color("Wheat") render() feeder();
        translate([0, 0, FEEDER[2] + 3]) mirror([0, 0, 1]) color("Tan") render() feeder_lid();
        translate([8, 0, FEEDER[2] + 5]) mirror([0, 0, 1]) color("SaddleBrown") render() feeder_hatch(); }
}
