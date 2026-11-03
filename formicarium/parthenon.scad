// =====================================================================
//  PARTHENON FORMICARIUM  (Atény)  – Prusa CORE One (250 x 220 x 270 mm)
//  Řez napříč chrámem: vpředu štít (tympanon) s komůrkami, vzadu
//  peristyl se 46 sloupy -> zadní pohled = klasické průčelí s 8 sloupy.
//  Díly: core, temple (krepidoma+sloupy+kladí), roof (střecha+štít),
//        bezel, cover, plugs, plate (2D pětiúhelník -> DXF laser)
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";  // assembly | display | core | temple | roof | bezel | cover | plugs | plate

STEP_HW = [118, 113, 108];   // polovina šířky stupňů krepidomatu
HW = 108;  HWC = 111;         // tělo / římsa
COL_TOP = 76;  APEX = 122;
L = CORE_T + 150;             // celková hloubka modelu
ENT_BACK  = L - 11.5;
CORN_BACK = ENT_BACK + 3;

// ---------- hnízdo
FIELD_X = [-86, 86];
Z0 = 25;  ZTOP = 80;
FLOOR_H = max(20, FLOOR_H_MIN);
NF = floors_fit(Z0, ZTOP, FLOOR_H);
COLS = [ for (i = [0 : NF - 1]) [4, 3, 3, 3][i] ];
CHAMBERS = row_chambers(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS);
ZTF = Z0 + (NF - 1) * FLOOR_H;                 // spodek nejvyššího patra
PORT_FLOOR = min(1, NF - 1);
PZ = Z0 + PORT_FLOOR * FLOOR_H + TUN_W / 2;
TUNNELS = concat(row_tunnels(FIELD_X[0], FIELD_X[1], Z0, FLOOR_H, COLS),
                 [[[FIELD_X[1] - 6, PZ], [FIELD_X[1] + 4, PZ]],
                  [[6, ZTF + CH_H * 0.5], [-4, 96]]]);          // rampa do tympanonu
PORT = [FIELD_X[1] + 3, HW + 2, PZ];
FILL = [[-89, 106], [-89, Z0 + 4], [FIELD_X[1] - 4, Z0 + 4]];
function roof_z(x) = 92 + (APEX - 92) * (1 - abs(x) / HWC);
VENTS = [[-14, 97, roof_z(14)], [14, 97, roof_z(14)]];

PLATE_PTS = [[-92, 20], [92, 20], [92, 84], [0, 109], [-92, 84]];
function slope_off(x, d) = let(n = [25 / 92, 1] / norm([25 / 92, 1]))
    [x + sign(x) * n[0] * d, 84 + (92 - abs(x)) * 25 / 92 + n[1] * d];
SCREWS  = [[-60, 16], [0, 16], [60, 16], [-96, 50], [96, 50], slope_off(-46, 4), slope_off(46, 4)];
MAGNETS = [[-30, 16], [30, 16], slope_off(-76, 4), slope_off(76, 4)];
PINS = [[-60, 45], [60, 45], [0, 60], [0, 102]];
ROOF_PINS = [[-60, CORE_T + 70], [60, CORE_T + 70], [0, CORE_T + 120]];

module plate2d() polygon(PLATE_PTS);
module outer2d() offset(r = 8) plate2d();

module profile2d() polygon([
    [-118, 0], [118, 0], [118, 5], [113, 5], [113, 10], [108, 10], [108, 81], [111, 86],
    [111, 92], [0, APEX], [-111, 92], [-111, 86], [-108, 81], [-108, 10], [-113, 10],
    [-113, 5], [-118, 5]]);

module tympanon2d() intersection() {
    offset(delta = -6) plate2d();
    translate([-200, 92]) square([400, 100]);
}

module core() {
    difference() {
        face_extrude(0, CORE_T) profile2d();
        nest_cavities(CHAMBERS, TUNNELS, FILL, VENTS, PORT);
        face_extrude(-1, CH_D) tympanon2d();
        vent_recesses(VENTS);
        screw_pilots(SCREWS);
        pin_holes_y(PINS, CORE_T);
    }
}

module column(x, y) translate([x, y, 15]) {
    cylinder(d1 = 11, d2 = 9, h = 56, $fn = 20);                     // dřík (20 kanelur)
    translate([0, 0, 56]) cylinder(d1 = 9, d2 = 12.5, h = 3, $fn = 32);  // echinus
    translate([-6.5, -6.5, 59]) cube([13, 13, 2]);                    // abakus
}

module temple() {
    Y0 = CORE_T;
    difference() {
        union() {
            for (s = [0 : 2]) translate([-STEP_HW[s], Y0, 5 * s]) cube([2 * STEP_HW[s], L - 5 * s - Y0, 5]);
            // cella se 45° náběhem pod kladí (tisk bez podpěr)
            hull() {
                translate([-80, Y0, 15]) cube([160, L - 30 - Y0, 49]);
                translate([-92, Y0, COL_TOP - 0.01]) cube([184, L - 26 - Y0, 0.01]);
            }
            for (sx = [-1, 1]) for (i = [0 : 7]) column(sx * 101, Y0 + 8 + i * (L - 26 - Y0) / 7);
            for (j = [1 : 6]) column(-101 + j * 202 / 7, L - 18);
            // kladí: architráv + vlys, náběh 45°, římsa
            translate([-HW, Y0, COL_TOP]) cube([2 * HW, ENT_BACK - Y0, 5]);
            hull() {
                translate([-HW, Y0, 81]) cube([2 * HW, ENT_BACK - Y0, 0.01]);
                translate([-HWC, Y0, 86]) cube([2 * HWC, CORN_BACK - Y0, 0.01]);
            }
            translate([-HWC, Y0, 86]) cube([2 * HWC, CORN_BACK - Y0, 6]);
        }
        // triglyfy na vlysu (zadní průčelí + boky)
        for (x = [-104 : 8 : 104]) translate([x - 0.8, ENT_BACK - 0.8, 77.5]) cube([1.6, 2, 3]);
        for (sx = [-1, 1]) for (y = [Y0 + 6 : 8 : ENT_BACK - 4])
            translate([sx * HW - 1.2, y - 0.8, 77.5]) cube([2.4, 1.6, 3]);
        // vchod do celly na zadní straně (slepé dveře)
        translate([-10, L - 31, 15]) cube([20, 3, 32]);
        pin_holes_y(PINS, CORE_T);
        pin_holes_z(ROOF_PINS, 92);
    }
}

module roof_prism() translate([0, CORN_BACK, 0]) rotate([90, 0, 0])
    linear_extrude(CORN_BACK - CORE_T) polygon([[-HWC, 92], [HWC, 92], [0, APEX]]);

module roof() {
    difference() {
        roof_prism();
        // tympanon zadního štítu
        translate([0, CORN_BACK + 0.01, 0]) rotate([90, 0, 0]) linear_extrude(1.5)
            polygon([[-98, 94.5], [98, 94.5], [0, APEX - 4.5]]);
        // řady tašek (drážky po spádu střechy)
        for (y = [CORE_T + 5 : 5 : CORN_BACK - 3]) intersection() {
            translate([-200, y - 0.4, 0]) cube([400, 0.8, 200]);
            difference() { roof_prism(); translate([0, 0, -1.2]) roof_prism(); }
        }
        pin_holes_y(PINS, CORE_T);
        pin_holes_z(ROOF_PINS, 92);
    }
}

module the_bezel() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); }
module the_cover() cover(MAGNETS, "ΠΑΡΘΕΝΩΝ", [0, 55], 15) outer2d();

if (PART == "core")      print_core() core();
if (PART == "temple")    temple();
if (PART == "roof")      translate([0, 0, -92]) roof();
if (PART == "bezel")     print_bezel() the_bezel();
if (PART == "cover")     print_cover() the_cover();
if (PART == "plugs")     plugs();
if (PART == "plate")     plate2d();
if (PART == "core_view") core();
if (PART == "display")   { core(); temple(); roof(); }
if (PART == "assembly") {
    color("BurlyWood") core();
    color("Ivory") temple();
    color("Wheat") roof();
    color("LightBlue", 0.35) face_extrude(-PLATE_T, 0) plate2d();
    color("DimGray") the_bezel();
}
