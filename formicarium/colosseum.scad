// =====================================================================
//  COLOSSEUM FORMICARIUM v2 (Řím) – Prusa CORE One (250 x 220 x 270 mm)
//  Podle konceptu: celý eliptický amfiteátr s výsekem vpředu (hnízdo za
//  sklem), aréna nahoře pod průhlednou kopulí = outworld, vodní věž
//  vlevo propojená trubkou se sádrou, eliptický podstavec s chodníkem.
//
//  Díly: core, facade, plinth_left, plinth_right, tower, tower_cap,
//        dome_cap, bezel, cover, plugs, plate (2D -> DXF)
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";

// ---------- budova (střed elipsy je YC za čelní plochou řezu y = 0)
A = 112;  B = 93;  YC = 58;  H = 118;
TIERS = [[8, 36], [36, 64], [64, 92]];  ATTIC = [92, H];
OUTER_WALL = 2.4;  CORRIDOR = 6;  N_ARCH = 80;           // 80 oblouků jako originál

// ---------- aréna pod kopulí (dělitelná průhledná koule Ø 120 mm)
DOME_D = 120;  DOME_CY = YC + 10;  DOME_GROOVE = 2.6;  DOME_SEAT = 4;
BASIN_R = 55;  ARENA_E = [34, 24];  ARENA_DEPTH = 18;  CAVEA_STEPS = 5;

// ---------- hnízdo (patra sladěná s patry arkád)
PLASTER_DROP = 6;
FIELD_X = [-73, 73];
Z0 = 36;  ZTOP = 107;
FLOOR_H = max(28, FLOOR_H_MIN);
NF = floors_fit(Z0, ZTOP, FLOOR_H);
COLS = [ for (i = [0 : NF - 1]) [4, 4, 3, 3][i] ];
CHAMBERS = row_chambers(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS);
ZTF = Z0 + (NF - 1) * FLOOR_H;
PZ = Z0 + FLOOR_H + TUN_W / 2;
TUNNELS = concat(row_tunnels(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS),
                 [[[FIELD_X[1] - 6, PZ], [FIELD_X[1] + 4, PZ]]]);
PORT = [FIELD_X[1] + 2, A, PZ];                           // boční hrdlo (volitelná 2. aréna)
WATER_Z = Z0 - 4;                                         // vodní kanál pod podlahou
FILL = [[-104, WATER_Z], [FIELD_X[1] - 4, WATER_Z]];
VENTS = [ for (c = CHAMBERS) if (abs(c[1] - ZTF) < 0.01 && abs(c[0] + c[2] / 2) > 20)
            [c[0] + c[2] / 2, c[1] + c[3] / 2, H] ];
ENT_Y = DOME_CY - DOME_D / 2 + DOME_GROOVE / 2 + 0.8 + TUN_W / 2;   // vstup do arény pod kopulí

PLATE = [[-79, 30], [79, 111]];                           // sklo 158 x 81 x 3 mm
SCREWS  = [[-60, 26.5], [0, 26.5], [60, 26.5], [-25, 114.5], [25, 114.5], [-82.5, 70], [82.5, 70]];
MAGNETS = [[-30, 26.5], [30, 26.5], [-65, 114.5], [65, 114.5]];
PINS = [[-60, 50], [60, 50], [0, 78], [-85, 100], [85, 100]];

// ---------- podstavec a vodní věž
PL = [170, 107];  PL_T = 8;  PL_RECESS = 1.5;
TOWER_POS = [-138, YC - 10];
TUBE40_OD = 40;  TUBE40_ID = 34;  TUBE40_L = 70;          // plexi trubka 40/34 x 70 mm
TOWER_BASE_H = 12;

// =====================================================================
module plate2d() translate(PLATE[0]) square(PLATE[1] - PLATE[0]);
module outer2d() offset(r = 7) plate2d();
module windows2d() offset(r = 1.2) {
    for (c = CHAMBERS) translate([c[0], c[1]]) chamber2d(c[2], c[3]);
    for (t = TUNNELS) tunnel2d(t[0], t[1], TUN_W);
}

module ellipse_prism(a, b, z0, h, fn = 180) translate([0, YC, z0]) scale([a, b, 1]) cylinder(r = 1, h = h, $fn = fn);
module front_cut() translate([-500, 0, -500]) cube(1000);        // y >= 0

module ell_place(t, z) {
    translate([A * cos(t), YC + B * sin(t), z]) rotate([0, 0, atan2(sin(t) / B, cos(t) / A)]) children();
}
function ell_y(t) = YC + B * sin(t);

module arcades() {
    for (i = [0 : N_ARCH - 1]) let(t = (i + 0.5) * 360 / N_ARCH) if (ell_y(t) > 4) {
        for (tr = TIERS) ell_place(t, tr[0] + 3) niche(5.8, tr[1] - tr[0] - 8, OUTER_WALL + 1);
        if (i % 2 == 0) ell_place(t, ATTIC[0] + 9) niche(3.6, 7, 1.8, arch = false);
    }
    for (zz = [TIERS[0][0], TIERS[0][1], TIERS[1][1], TIERS[2][1], H - 4])
        difference() { ellipse_prism(A + 1, B + 1, zz - 0.7, 1.4); ellipse_prism(A - 0.7, B - 0.7, zz - 1, 2); }
}

module corridors() {   // ochoz za průchozími oblouky (jen ve fasádě)
    for (tr = TIERS) difference() {
        ellipse_prism(A - OUTER_WALL, B - OUTER_WALL, tr[0] + 2, tr[1] - tr[0] - 4.5);
        ellipse_prism(A - OUTER_WALL - CORRIDOR, B - OUTER_WALL - CORRIDOR, tr[0], 40);
    }
}

module dome_groove() translate([0, DOME_CY, H - DOME_SEAT]) difference() {
    cylinder(d = DOME_D + DOME_GROOVE, h = 10, $fn = 160);
    translate([0, 0, -1]) cylinder(d = DOME_D - DOME_GROOVE, h = 12, $fn = 160);
}

module basin() {      // cavea stupně dolů do arény (jen ve fasádě)
    for (k = [0 : CAVEA_STEPS]) let(f = k / CAVEA_STEPS)
        translate([0, DOME_CY, H - ARENA_DEPTH + f * (ARENA_DEPTH - 2)])
            scale([ARENA_E[0] + f * (BASIN_R - ARENA_E[0]), ARENA_E[1] + f * (BASIN_R - ARENA_E[1]), 1])
                cylinder(r = 1, h = 40, $fn = 120);
    for (x = [-28 : 7 : 28]) translate([x - 0.6, DOME_CY - 20, H - ARENA_DEPTH - 1]) cube([1.2, 40, 2]);
}

// větrání arény: radiální otvory atikou se síťkou zvenku
function ray_s(c, s) = let(a = c * c / (A * A) + s * s / (B * B), b = 2 * (DOME_CY - YC) * s / (B * B),
                           k = (DOME_CY - YC) * (DOME_CY - YC) / (B * B) - 1)
    (-b + sqrt(b * b - 4 * a * k)) / (2 * a);
ARENA_VENT_ANG = [55, 90, 125];
module arena_vents() for (ang = ARENA_VENT_ANG) let(c = cos(ang), s = sin(ang), r = ray_s(c, s)) {
    translate([0, DOME_CY, H - 8]) rotate([0, 0, ang]) rotate([0, 90, 0]) cylinder(d = 5, h = r + 5, $fn = 24);
    translate([r * c, DOME_CY + r * s, H - 8]) rotate([0, 0, ang]) rotate([0, 90, 0])
        translate([0, 0, -0.8]) cylinder(d = MESH_D + 0.4, h = 5, $fn = 32);
}

// polosloupy mezi oblouky
module pilasters() for (i = [0 : N_ARCH - 1]) let(t = i * 360 / N_ARCH) if (ell_y(t) > 4)
    for (tr = TIERS) ell_place(t, tr[0] + 1) translate([-0.5, -0.9, 0]) cube([1.3, 1.8, tr[1] - tr[0] - 2]);

module body() intersection() {
    difference() { union() { ellipse_prism(A, B, 0, H); pilasters(); } arcades(); }
    front_cut();
}

// stupně hlediště kolem kopule (jen fasáda) + límec pro kopuli
module top_steps() for (k = [1 : 3]) ellipse_prism(A - 6 * k, B - 6 * k, H - 2 * k, 20);
module dome_collar() translate([0, DOME_CY, H - 6]) difference() {
    cylinder(d = DOME_D + 9, h = 6, $fn = 160); translate([0, 0, -1]) cylinder(d = DOME_D - 9, h = 8, $fn = 160);
}

module core() {
    difference() {
        intersection() { body(); translate([-500, 0, -1]) cube([1000, CORE_T, 1000]); }
        dome_groove();
        nest_cavities(CHAMBERS, TUNNELS, FILL, VENTS, PORT);
        capsule3([0, CH_D / 2, ZTF + CH_H * 0.5], [0, ENT_Y, H + 4], TUN_W);   // vstup do arény
        vent_recesses(VENTS);
        screw_pilots(SCREWS);
        pin_holes_y(PINS, CORE_T);
        face_extrude(-1, 0.6) translate([0, 13]) text("COLOSSEVM", size = 9, halign = "center",
            valign = "center", font = "Liberation Serif:style=Bold", spacing = 1.15);
    }
}

module facade() {
    difference() {
        intersection() {
            union() { difference() { body(); top_steps(); } dome_collar(); }
            translate([-500, CORE_T, -1]) cube(1000);
            ellipse_prism(A + 2, B + 2, -1, H + 2);
        }
        dome_groove();
        corridors();
        basin();
        arena_vents();
        pin_holes_y(PINS, CORE_T);
    }
}

// ---------- podstavec (2 poloviny, slepit kolíky)
module plinth() {
    difference() {
        union() {
            translate([0, YC, 0]) scale([PL[0], PL[1], 1]) cylinder(r = 1, h = PL_T, $fn = 180);
            // obvodový chodník
            translate([0, YC, PL_T]) difference() {
                scale([A + 16, B + 12, 1]) cylinder(r = 1, h = 1.2, $fn = 180);
                translate([0, 0, -1]) scale([A + 11, B + 7, 1]) cylinder(r = 1, h = 4, $fn = 180);
            }
        }
        // zapuštění pro budovu
        translate([0, 0, PL_T - PL_RECESS]) intersection() {
            translate([0, YC, 0]) scale([A + 0.4, B + 0.4, 1]) cylinder(r = 1, h = 10, $fn = 180);
            translate([-500, -0.4, 0]) cube(1000);
        }
        // místo pro věž + drážka pro hadičku
        translate([TOWER_POS[0], TOWER_POS[1], PL_T - PL_RECESS]) cylinder(d = 46.4, h = 10, $fn = 64);
        hull() {
            translate([TOWER_POS[0], TOWER_POS[1], PL_T]) rotate([0, 90, 0]) cylinder(d = 7, h = 1, $fn = 24);
            translate([-A + 4, 13.5, PL_T]) rotate([0, 90, 0]) cylinder(d = 7, h = 1, $fn = 24);
        }
        // kolíky mezi polovinami
        for (y = [YC - 60, YC, YC + 60]) translate([0, y, PL_T / 2]) rotate([0, 90, 0])
            cylinder(d = PIN_D, h = 2 * PIN_L, center = true, $fn = 12);
    }
}

// ---------- vodní věž: podstavec s nálevkou + 4 sloupky, plexi trubka 40/34
MAX_Z = WATER_Z;   // hladina = osa vodního kanálu pod podlahou (komunikující nádoby)
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
module the_cover() cover(MAGNETS, "COLOSSEVM", [0, 70], 15) outer2d();

module dome_preview() translate([0, DOME_CY, H - DOME_SEAT]) difference() {
    sphere(d = DOME_D, $fn = 64); sphere(d = DOME_D - 2, $fn = 64); translate([-100, -100, -200]) cube(200);
}

if (PART == "core")        print_core() core();
if (PART == "facade")      facade();
if (PART == "plinth_left") rotate([0, 0, 90]) intersection() { plinth(); translate([-500, -500, 0]) cube([500, 1000, 100]); }
if (PART == "plinth_right") rotate([0, 0, 90]) intersection() { plinth(); translate([0, -500, 0]) cube([500, 1000, 100]); }
if (PART == "tower")       tower();
if (PART == "tower_cap")   tower_cap();
if (PART == "dome_cap")    dome_cap();
if (PART == "bezel")       print_bezel() the_bezel();
if (PART == "cover")       print_cover() the_cover();
if (PART == "plugs")       plugs();
if (PART == "plate")       plate2d();
if (PART == "core_view")   core();
if (PART == "bezel_view")  { core(); the_bezel(); }
if (PART == "display")     { translate([0, 0, -PL_T + PL_RECESS]) plinth(); core(); facade(); translate([TOWER_POS[0], TOWER_POS[1], 0]) tower(); }
if (PART == "assembly") {
    translate([0, 0, -PL_T + PL_RECESS]) color("DimGray") render() plinth();
    color("BurlyWood") render() core();
    color("Wheat") render() facade();
    color("LightBlue", 0.35) face_extrude(-PLATE_T, 0) plate2d();
    color("SaddleBrown") render() the_bezel();
    color("LightBlue", 0.3) dome_preview();
    translate([TOWER_POS[0], TOWER_POS[1], 0]) { color("Wheat") render() tower();
        color("LightBlue", 0.3) translate([0, 0, TOWER_BASE_H - 3]) cylinder(d = TUBE40_OD, h = TUBE40_L);
        translate([0, 0, TOWER_BASE_H - 3 + TUBE40_L]) color("Wheat") render() tower_cap(); }
}
