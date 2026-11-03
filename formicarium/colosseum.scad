// =====================================================================
//  COLOSSEUM FORMICARIUM  (Řím)  – Prusa CORE One (250 x 220 x 270 mm)
//  Díly:  core (hnízdo), facade (zadní polovina amfiteátru), bezel
//  (rámeček skla), cover (zatemnění), plugs, plate (2D -> DXF pro řezání)
//  openscad -D 'PART="core"' -o core.stl colosseum.scad
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";  // assembly | core | facade | bezel | cover | plugs | plate

A = 115;  B = 95;  H = 125;        // poloosy elipsy a výška (stylizováno)
ARENA = [55, 36];  ARENA_Z = 58;  CAVEA_STEPS = 6;
TIERS = [[6, 36], [36, 66], [66, 96]];  ATTIC = [96, 121];

// ---------- hnízdo
FIELD_X = [-98, 98];
Z0 = 14;  ZTOP = 107;
FLOOR_H = max(20, FLOOR_H_MIN);
NF = floors_fit(Z0, ZTOP, FLOOR_H);
COLS = [ for (i = [0 : NF - 1]) [5, 4, 5, 4, 3, 3][i] ];
CHAMBERS = row_chambers(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS);
PORT_FLOOR = min(2, NF - 1);
PZ = Z0 + PORT_FLOOR * FLOOR_H + TUN_W / 2;
TUNNELS = concat(row_tunnels(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS),
                 [[[FIELD_X[1] - 6, PZ], [FIELD_X[1] + 4, PZ]]]);
PORT = [FIELD_X[1] + 3, A + 2, PZ];
FILL = [[-101, H + 5], [-101, Z0 + 4], [FIELD_X[1] - 4, Z0 + 4]];
VENTS = top_floor_vents(CHAMBERS, Z0 + (NF - 1) * FLOOR_H, H);

PLATE = [[-104, 8], [104, 113]];            // sklo 208 x 105 x 3 mm
SCREWS  = [[-80, 4], [0, 4], [80, 4], [-80, 117], [0, 117], [80, 117], [-108, 60], [108, 60]];
MAGNETS = [[-40, 4], [40, 4], [-40, 117], [40, 117]];
PINS = [[0, 45], [-70, 75], [70, 75], [-95, 100], [95, 100]];

module plate2d() translate(PLATE[0]) square(PLATE[1] - PLATE[0]);
module outer2d() offset(r = 8) plate2d();

module ellipse_prism(a, b, z0, h, fn = 160) translate([0, 0, z0]) scale([a, b, 1]) cylinder(r = 1, h = h, $fn = fn);
module back_half() translate([-500, 0, -500]) cube(1000);

module ell_place(t, z) {
    p = [A * cos(t), B * sin(t)];
    translate([p[0], p[1], z]) rotate([0, 0, atan2(sin(t) / B, cos(t) / A)]) children();
}

module arcades() {
    n = 40;
    for (i = [0 : n - 1]) let(t = (i + 0.5) * 180 / n) {
        for (tr = TIERS) ell_place(t, tr[0] + 3) niche(5.2, tr[1] - tr[0] - 8, 2.5);
        if (i % 2 == 0) ell_place(t, ATTIC[0] + 8) niche(3.6, 7, 1.8, arch = false);
    }
    for (zz = [TIERS[0][1], TIERS[1][1], TIERS[2][1], H - 4])
        difference() { ellipse_prism(A + 1, B + 1, zz - 0.8, 1.6); ellipse_prism(A - 0.8, B - 0.8, zz - 1, 2); }
}

module body(with_cavea) {
    difference() {
        intersection() { ellipse_prism(A, B, 0, H); back_half(); }
        if (with_cavea) for (k = [0 : CAVEA_STEPS]) let(f = k / CAVEA_STEPS)
            ellipse_prism(ARENA[0] + f * (A - 11 - ARENA[0]), ARENA[1] + f * (B - 11 - ARENA[1]),
                          ARENA_Z + f * (H - 3 - ARENA_Z), H, 120);
        if (with_cavea) // hypogeum – rýhy v podlaze arény
            for (x = [-40 : 10 : 40]) translate([x - 0.6, CORE_T, ARENA_Z - 1]) cube([1.2, 40, 2]);
        arcades();
    }
}

module core() {
    difference() {
        intersection() { body(false); translate([-500, 0, -1]) cube([1000, CORE_T, 1000]); }
        nest_cavities(CHAMBERS, TUNNELS, FILL, VENTS, PORT);
        vent_recesses(VENTS);
        screw_pilots(SCREWS);
        pin_holes_y(PINS, CORE_T);
    }
}

module facade() {
    difference() {
        intersection() { body(true); translate([-500, CORE_T, -1]) cube(1000); }
        pin_holes_y(PINS, CORE_T);
    }
}

module the_bezel() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); }
module the_cover() cover(MAGNETS, "COLOSSEVM", [0, 60], 16) outer2d();

if (PART == "core")   print_core() core();
if (PART == "facade") facade();
if (PART == "bezel")  print_bezel() the_bezel();
if (PART == "cover")  print_cover() the_cover();
if (PART == "plugs")  plugs();
if (PART == "plate")  plate2d();
if (PART == "core_view") core();
if (PART == "display") { core(); facade(); }
if (PART == "assembly") {
    color("BurlyWood") core();
    color("Wheat") facade();
    color("LightBlue", 0.35) face_extrude(-PLATE_T, 0) plate2d();
    color("DimGray") the_bezel();
}
