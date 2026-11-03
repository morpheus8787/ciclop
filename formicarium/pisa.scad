// =====================================================================
//  LEANING TOWER FORMICARIUM  (Šikmá věž, Pisa) – Prusa CORE One
//  Svislý řez věží: 7 pater hnízda nad sebou = 7 pater věže.
//  Věž se kloní o 4° (jako originál); podlahy komůrek jsou skloněné
//  stejně – mravencům to nevadí.
//  Díly: core, tower_lower, tower_upper, belfry (zvonice + víčko jádra),
//        bezel, cover, plugs, plate (2D obdélník 66 x 160 mm)
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";  // assembly | display | core | tower_lower | tower_upper | belfry | bezel | cover | plugs | plate

R = 40;  LEAN = 4;
STOREYS = [0, 44, 68, 92, 116, 140, 164, 188];
BELFRY = [27, 20, 188, 226];         // r vnější, r vnitřní, z0, z1
Z_SPLIT = 116;                        // dělení fasády (svět. souřadnice)
ZS = 184;                             // horní hrana jádra (svět.)

// ---------- hnízdo (lokální souřadnice věže)
FIELD_X = [-27, 27];
Z0 = 18;  ZTOP = 163;
FLOOR_H = max(22, FLOOR_H_MIN);
NF = floors_fit(Z0, ZTOP, FLOOR_H);
COLS = [ for (i = [0 : NF - 1]) (CH_D > 12 ? 1 : (i % 2 == 0 ? 1 : 2)) ];
CHAMBERS = row_chambers(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS);
PZ = Z0 + FLOOR_H + TUN_W / 2;
TUNNELS = concat(row_tunnels(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS),
                 [[[FIELD_X[1] - 6, PZ], [FIELD_X[1] + 4, PZ]]]);
PORT = [FIELD_X[1] + 2, R + 3, PZ];
FILL = [[-12, 215], [-12, 176], [-30, 168], [-30, Z0 + 4], [FIELD_X[1] - 6, Z0 + 4]];
ZTF = Z0 + (NF - 1) * FLOOR_H;
VENTS = [[0, ZTF + CH_H * 0.5, 215], [12, ZTF + CH_H * 0.5, 215]];

PLATE = [[-33, 12], [33, 172]];             // sklo 66 x 160 x 3 mm
OUTER = [[-37, 4], [37, 182]];
SCREWS  = [[-18, 8], [18, 8], [-18, 177], [18, 177]];
MAGNETS = [[0, 8], [0, 177]];
PINS = [[0, 60], [0, 120], [0, 170]];

module plate2d() translate(PLATE[0]) square(PLATE[1] - PLATE[0]);
module outer2d() translate(OUTER[0]) offset(r = 3) offset(delta = -3) square(OUTER[1] - OUTER[0]);

module lean() rotate([0, LEAN, 0]) children();
function axis_x(z) = z * tan(LEAN);
// místo, kde svislá lokální přímka x = xl protne světovou výšku zw
function world_x(xl, zw) = let(zl = (zw + xl * sin(LEAN)) / cos(LEAN)) xl * cos(LEAN) + zl * sin(LEAN);

module storey_niches() {
    for (a = [-10 : 20 : 190]) rotate([0, 0, a]) translate([R, 0, 6]) niche(9, 30, 2.5);
    for (s = [1 : 6]) for (a = [-6 : 12 : 186])
        rotate([0, 0, a]) translate([R, 0, STOREYS[s] + 1.5]) niche(5.5, 18, 2.5);
}

module cornice(z, r) translate([0, 0, z - 3]) {
    cylinder(r1 = r, r2 = r + 1.6, h = 1.6, $fn = 120);
    translate([0, 0, 1.6]) cylinder(r = r + 1.6, h = 1.4, $fn = 120);
}

module belfry() {
    difference() {
        union() {
            translate([0, 0, BELFRY[2]]) cylinder(r = BELFRY[0], h = BELFRY[3] - BELFRY[2], $fn = 96);
            cornice(BELFRY[3], BELFRY[0]);
        }
        translate([0, 0, BELFRY[2] + 2]) cylinder(r = BELFRY[1], h = 60, $fn = 96);
        for (a = [15 : 30 : 165]) rotate([0, 0, a])
            translate([BELFRY[0], 0, BELFRY[2] + 9]) niche(7, 19, 9);
    }
}

module tower(with_belfry) {
    difference() {
        union() {
            translate([0, 0, -8]) cylinder(r = R, h = STOREYS[7] + 8, $fn = 120);
            for (s = [1 : 7]) cornice(STOREYS[s], R);
            if (with_belfry) belfry();
        }
        storey_niches();
    }
}

module back_half() translate([-500, 0, -500]) cube(1000);
module above(z) translate([-500, -500, z]) cube(1000);
module below(z) translate([-500, -500, -1000 + z]) cube(1000);

module through_holes() {   // zavlažování + větrání pokračují skrz víčko zvonice
    for (i = [0 : len(FILL) - 2]) capsule(FILL[i], FILL[i + 1], AIRLINE_OD + 0.6, WATER_Y);
    for (v = VENTS) capsule([v[0], v[1]], [v[0], v[2]], VENT_D, VENT_Y);
}

module core() {
    difference() {
        intersection() {
            lean() difference() {
                intersection() { tower(false); translate([-500, 0, -500]) cube([1000, CORE_T, 1000]); }
                nest_cavities(CHAMBERS, TUNNELS, FILL, VENTS, PORT);
                screw_pilots(SCREWS);
                pin_holes_y(PINS, CORE_T);
            }
            above(0); below(ZS);
        }
        for (v = VENTS) translate([world_x(v[0], ZS), VENT_Y, ZS - MESH_RECESS])
            cylinder(d = MESH_D + 0.4, h = 5);
    }
}

TOWER_PINS = function(z) [[axis_x(z), 31], [axis_x(z) - 20, 28], [axis_x(z) + 20, 28]];

module tower_part(z0, z1) {
    difference() {
        intersection() {
            lean() difference() { tower(false); pin_holes_y(PINS, CORE_T); }
            translate([-500, CORE_T, -500]) cube(1000);
            above(z0); below(z1);
        }
        if (z0 > 0) pin_holes_z(TOWER_PINS(z0), z0);
        pin_holes_z(TOWER_PINS(z1), z1);
    }
}

module top_part() {
    difference() {
        intersection() {
            lean() difference() { tower(true); through_holes(); }
            back_half(); above(ZS);
        }
        pin_holes_z(TOWER_PINS(ZS), ZS);
    }
}

module the_bezel() lean() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); }
module the_cover() lean() cover(MAGNETS, "PISA", [0, 92], 12) outer2d();

// bezel / cover se tisknou v lokálních (nenakloněných) souřadnicích
if (PART == "core")        print_core() core();
if (PART == "tower_lower") tower_part(0, Z_SPLIT);
if (PART == "tower_upper") translate([0, 0, -Z_SPLIT]) tower_part(Z_SPLIT, ZS);
if (PART == "belfry")      translate([0, 0, -ZS]) top_part();
if (PART == "bezel")       print_bezel() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); }
if (PART == "cover")       print_cover() cover(MAGNETS, "PISA", [0, 92], 12) outer2d();
if (PART == "plugs")       plugs();
if (PART == "plate")       plate2d();
if (PART == "core_view")   core();
if (PART == "display")     { core(); tower_part(0, Z_SPLIT); tower_part(Z_SPLIT, ZS); top_part(); }
if (PART == "assembly") {
    color("BurlyWood") core();
    color("Ivory") { tower_part(0, Z_SPLIT); tower_part(Z_SPLIT, ZS); top_part(); }
    color("LightBlue", 0.35) lean() face_extrude(-PLATE_T, 0) plate2d();
    color("DimGray") the_bezel();
}
