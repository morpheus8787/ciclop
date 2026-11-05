// =====================================================================
//  COLOSSEUM FORMICARIUM v5 (Řím) – Prusa CORE One (250 x 220 x 270 mm)
//  Eliptický prstenec s VÝSEČÍ 90° vpředu (jako ukrojený dort):
//   - uprostřed stupňovitá jáma (nejširší nahoře, dolů se zužuje) =
//     aréna, na dně sklo a pod ním velká komůrka královny,
//   - na obou řezech výseče hnízdo pod sklem se schodovitým profilem,
//   - za oblouky galerie kolem celé stavby (vidět mezi sloupy),
//   - celou stavbu obepíná průhledný pás (fólie), věnec s kopulí kryje
//     celý střed; vodní věž a krmítko s poklopem jsou venku.
//
//  Díly: body, core_left, core_right, crown, plinth_left/right,
//        bezel_left/right, cover_left/right, tower, tower_cap, dome_cap,
//        feeder, feeder_lid, feeder_hatch, plugs, plate (DXF), band (DXF)
// =====================================================================
include <lib/formicarium.scad>

PART = "assembly";

// ---------- budova (střed elipsy v počátku)
A = 112;  B = 93;  H = 118;  N_ARCH = 64;    // 64 širších oblouků = víc vidět dovnitř
ARCH_W = 7.2;  COL_D = 2.6;  CORNICE = 1.6;
TIERS = [[8, 36], [36, 64], [64, 92]];  ATTIC = [92, H];
GAP = 90;                                      // úhel výseče
TH_R = -90 + GAP / 2;                          // pravý řez
U = [cos(TH_R), sin(TH_R)];  N = [-sin(TH_R), cos(TH_R)];

// ---------- stupňovitá jáma (aréna) uprostřed: [měřítko elipsy, výška podlahy]
PIT = [[0.62, 88], [0.45, 70], [0.30, 52]];
QY = 15;  GLASS_R = 12;  QUEEN_R = 14;  QUEEN_Z = [30, PIT[2][1] - 3.2];
DOME_D = 180;  DOME_GROOVE = 2.6;  CROWN_T = 4;
// záhonek na hlínu a trávu nahoře (pod kopulí), výlezy z chodby v atice
BED_H = 12;  BED_WALL = 2;  BED_SECTOR = [-30, 210];     // jen nad tělem, ne nad výsečí/jádry
EXITS = [[0, 75], [-40, 62], [40, 62]];                 // výlezové věžičky v záhonku
R_FACE = 1 / sqrt(pow(cos(-90 + GAP / 2) / A, 2) + pow(sin(-90 + GAP / 2) / B, 2));   // délka řezu

// ---------- hnízdo na řezu (místní souřadnice řezu: x = vzdálenost od osy)
PLASTER_DROP = 6;
Z0 = 20;
CHAMBERS = [   // schodovité rozvržení podle profilu jámy
    [25, Z0, 26, CH_H * 1.3, 1], [57, Z0, 31, CH_H, 1],              // patro 0 (vlhké, sádra)
    [44, 41, 18, CH_H * 1.1, 0], [68, 41, 20, CH_H * 1.3, 0],        // patro 1
    [59, 58, 29, CH_H * 1.1, 0],                                     // patro 2
    [76, 79, 12, CH_H * 1.2, 0]];                                    // hlídka nahoře
TUNNELS = [
    [[50, Z0 + 3], [59, Z0 + 3]], [[45, Z0 + 7], [50, 44]], [[84, Z0 + 8], [80, 44]],
    [[60, 44], [70, 44]], [[56, 50], [64, 61]], [[84, 52], [84, 61]], [[84, 64], [82, 82]],
    [[30, Z0 + 9], [22, Z0 + 16]]];                                  // slepá odbočka u osy
WATER_Z = Z0 - 4;
FILL = [[120, WATER_Z], [30, WATER_Z]];
ZTF = 41;
VENTS = [[70, 60, H], [85, 88.5, H]];
// ---------- organické hnízdo („přírodní“ styl): jeden členitý prostor, ze stěn
//            vystupují zaoblené římsy/police s mírným sklonem, cesta se klikatí nahoru
//            [x1, z1, r1] -> [x2, z2, r2]: římsa od stěny (silnější) k hrotu (tenčí)
LEDGES = [   // řetězce bodů [x, z, r]: od stěny (silná) přes prohyb k hrotu
    [[97, 28.5, 4.6], [70, 26.5, 3.6], [44, 26.0, 2.8]],      // nad vlhkým dnem, průchod vlevo
    [[19, 35.5, 3.8], [33, 33.5, 2.4]],                       // polička vlevo
    [[97, 39.0, 3.4], [80, 40.5, 2.2]],                       // výstupek vpravo
    [[38, 52.0, 4.6], [58, 49.0, 3.6], [76, 48.5, 2.8]],      // průchod vpravo
    [[97, 68.5, 4.6], [80, 65.5, 3.6], [66, 66.0, 2.8]],      // průchod vlevo
    [[97, 57.5, 3.2], [86, 59.5, 2.2]],                       // výstupek vpravo
    [[54, 60.5, 3.0], [61, 61.5, 2.0]],                       // výstupek vlevo
    [[77, 84.0, 3.4], [83, 83.0, 1.8]],                       // komín nahoře – střídavé výstupky
    [[93, 93.0, 3.4], [87, 94.0, 1.8]],
    [[77, 101.0, 3.4], [82, 101.5, 1.8]]];
// zvlnění stěn: hrbolky a krápníky [x, z, r]
BUMPS = [[24, 22, 2.2], [24, 30, 1.8], [40, 16, 2.0], [62, 15.5, 2.4], [80, 16, 1.8],
         [88.5, 21, 2.0], [88.5, 46, 2.2], [52, 39.5, 2.0], [60, 39.5, 1.6], [45, 56.5, 1.8],
         [70, 52, 1.6], [88.5, 75, 2.0], [70, 73.5, 2.0], [61, 72, 1.6], [80, 107, 2.0]];
HUMID_Z = 24;                                // pod první římsou = vlhké dno se sádrou
module ledge2d(l) for (i = [0 : len(l) - 2]) hull() {
    translate([l[i][0], l[i][1]]) circle(l[i][2], $fn = 32);
    translate([l[i + 1][0], l[i + 1][1]]) circle(l[i + 1][2], $fn = 32);
}
module nest2d() offset(r = 0.8) offset(r = -0.8) difference() {      // finální vyhlazení (čistá geometrie)
    offset(r = 2.5) offset(r = -5) offset(r = 2.5) offset(delta = -5) plate2d();   // zaoblené rohy
    for (l = LEDGES) ledge2d(l);
    for (b = BUMPS) translate([b[0], b[1]]) circle(b[2], $fn = 24);
}
module humid2d() intersection() { nest2d(); translate([0, 0]) square([200, HUMID_Z]); }
function pit_s(k) = PIT[k][0] * R_FACE;
FACE_PTS = [[0, 0], [R_FACE, 0], [R_FACE, H], [pit_s(0), H], [pit_s(0), PIT[0][1]], [pit_s(1), PIT[0][1]],
            [pit_s(1), PIT[1][1]], [pit_s(2), PIT[1][1]], [pit_s(2), PIT[2][1]], [0, PIT[2][1]]];
SCREWS  = [[15.5, 20], [15.5, 46], [35, 6.5], [80, 6.5], [97, 28], [97, 72], [82, 114], [34, 60], [66, 100]];
MAGNETS = [[15.5, 33], [57, 6.5], [97, 50], [97, 95], [49.5, 78]];
PINS = [[50, 32], [80, 35], [75, 74]];

// ---------- galerie za oblouky
WALL = 2.4;
GH = 17;                                       // galerie skoro přes celou výšku oblouku
G1 = TIERS[0][0] + 5;  G2 = TIERS[1][0] + 5;  G3 = TIERS[2][0] + 5;
GZ1 = G1 + TUN_W / 2 + 0.5;  GZ2 = G2 + TUN_W / 2 + 0.5;  GZ3 = G3 + TUN_W / 2 + 0.5;
G4_Z = ATTIC[0] + 12.5;  G4_R = WALL + TUN_W / 2;     // chodba v atice za okénky
// x (vzdálenost od osy) na řezu, kde střed galerie protne rovinu v hloubce d
function g_s(d) = let(a = A - WALL - CH_D / 2, b = B - WALL - CH_D / 2,
                      p = [U[0] / a, U[1] / b], q = [N[0] * d / a, N[1] * d / b],
                      aa = p * p, bb = 2 * (p * q), cc = q * q - 1)
    (-bb + sqrt(bb * bb - 4 * aa * cc)) / (2 * aa);
LINKS = [[[80, 5, 46], [g_s(CORE_T + 3), CORE_T + 3, GZ1]],
         [[78, 5, 58.5], [g_s(CORE_T + 3), CORE_T + 3, GZ2]],
         [[85, 5, 88.5], [g_s(CORE_T + 3), CORE_T + 3, GZ3]]];
G_RAMPS  = [[10, 22], [60, 72], [108, 120], [158, 170]];          // G1 -> G2
G_RAMPS2 = [[35, 47], [85, 97], [133, 145], [183, 195]];          // G2 -> G3
G_RAMPS3 = [[70, 64], [110, 116], [20, 14], [160, 166]];          // G3 -> chodba v atice
G_NICHES = [ for (i = [0 : 2 : N_ARCH - 1]) let(t = (i + 0.5) * 360 / N_ARCH) t ];
function in_body(t) = let(tt = t > 180 ? t - 360 : t) !(tt < -28 && tt > -152);   // mimo výseč a jádra

// ---------- podstavec, obruba pro pás, věž, krmítko
PL = [172, 109];  PL_T = 8;  PL_RECESS = 1.5;
RIM = [A + 2, A + 9];  RIM_H = 12;  BAND_R = A + 5.5;  BAND_GROOVE = 1.6;
TOWER_POS = [-146, 0];  TOWER_POCKET = 6;  TOWER_SINK = TOWER_POCKET - PL_RECESS;
TOWER_OUT_ANG = [-12, 12];
TUBE40_OD = 40;  TUBE40_ID = 34;  TUBE40_L = 70;  TOWER_BASE_H = 12;
FEEDER_POS = [145, 0];  FEEDER = [40, 48, 32];

// =====================================================================
//  transformace řezu: místní (x, hloubka, z) -> svět
module frame_r() multmatrix([[U[0], N[0], 0, 0], [U[1], N[1], 0, 0], [0, 0, 1, 0]]) children();
module frame_r_inv() multmatrix([[U[0], U[1], 0, 0], [N[0], N[1], 0, 0], [0, 0, 1, 0]]) children();
function wr(p) = [U[0] * p[0] + N[0] * p[1], U[1] * p[0] + N[1] * p[1], p[2]];
module both() { children(); mirror([1, 0, 0]) children(); }

module e_prism(a, b, z0, h, fn = 180) translate([0, 0, z0]) scale([a, b, 1]) cylinder(r = 1, h = h, $fn = fn);
module wedge(h = 400) translate([0, 0, -50]) linear_extrude(h)
    polygon([[0, 0], [500 * cos(-90 - GAP / 2), 500 * sin(-90 - GAP / 2)], [0, -600], [500 * cos(TH_R), 500 * sin(TH_R)]]);
module slab_r(extra = 0) frame_r() translate([0, -extra, -50]) cube([400, CORE_T + 2 * extra, 400]);

module ell_place(t, z) translate([A * cos(t), B * sin(t), z]) rotate([0, 0, atan2(sin(t) / B, cos(t) / A)]) children();
function bay(i) = (i + 0.5) * 360 / N_ARCH;
module arcades(depth = WALL + 1) {
    for (i = [0 : N_ARCH - 1]) let(t = bay(i)) {
        for (tr = TIERS) ell_place(t, tr[0] + 3) {
            niche(ARCH_W, tr[1] - tr[0] - 8, depth);                              // průchozí oblouk
            translate([0.01, 0, -0.6]) niche(ARCH_W + 1.8, tr[1] - tr[0] - 6.8, 0.6);  // archivolta
        }
        ell_place(t, ATTIC[0] + 9) niche(3.6, 7, depth, arch = false);           // okénka atiky
    }
}
// polosloupy s hlavicí a patkou, vystupující římsy se zkosením 45° (tisk bez podpěr)
module pilasters() for (i = [0 : N_ARCH - 1]) let(t = i * 360 / N_ARCH) {
    for (tr = TIERS) ell_place(t, tr[0]) {
        cylinder(d = COL_D, h = tr[1] - tr[0], $fn = 10);
        translate([-0.6, -2, 0]) cube([1.6, 4, 1.4]);
        translate([-0.6, -2, tr[1] - tr[0] - 2.4]) cube([1.6, 4, 1.4]);
    }
    ell_place(t, ATTIC[0]) translate([-0.6, -1.2, 0]) cube([1.2, 2.4, ATTIC[1] - ATTIC[0] - 5]);   // pilastry atiky
}
module cornice_ring(z, out = CORNICE, h = 1.4) translate([0, 0, z]) {
    linear_extrude(out, scale = [(A + out) / A, (B + out) / B]) scale([A, B]) circle(1, $fn = 180);
    translate([0, 0, out - 0.01]) scale([A + out, B + out, 1]) cylinder(r = 1, h = h, $fn = 180);
}
module cornices() {
    for (z = [TIERS[0][1], TIERS[1][1], TIERS[2][1]]) cornice_ring(z - CORNICE - 1.4);
    cornice_ring(H - CORNICE - 1.6, h = 1.6);                                   // hlavní římsa
    scale([A + 1.2, B + 1.2, 1]) cylinder(r = 1, h = 4, $fn = 180);           // sokl
    translate([0, 0, 4]) linear_extrude(1.2, scale = [A / (A + 1.2), B / (B + 1.2)]) scale([A + 1.2, B + 1.2]) circle(1, $fn = 180);
}

module solid() difference() { union() { e_prism(A, B, 0, H); pilasters(); cornices(); } arcades(); }

// galerie se stropem 45°, otevřená do oblouků
module gallery_cut(z0, gh, d) {
    ao = A - WALL;  bo = B - WALL;  ai = ao - d;  bi = bo - d;
    difference() {
        union() {
            e_prism(ao + 0.6, bo + 0.6, z0, gh - d);
            difference() {
                e_prism(ao + 0.6, bo + 0.6, z0 + gh - d - 0.01, d);
                translate([0, 0, z0 + gh - d - 0.02]) linear_extrude(d + 0.04, scale = [(ao + 0.6) / ai, (bo + 0.6) / bi])
                    scale([ai, bi]) circle(1, $fn = 180);
            }
        }
        e_prism(ai, bi, z0 - 1, gh + 2);
    }
}
function gp(t, z) = [(A - WALL - CH_D / 2) * cos(t), (B - WALL - CH_D / 2) * sin(t), z];
function g4(t) = [(A - G4_R) * cos(t), (B - G4_R) * sin(t), G4_Z];
module ramp_set(rs, za, zb, pa = 0) for (r = rs) {
    capsule3(gp(r[0], za), gp((r[0] + r[1]) / 2, (za + zb) / 2), TUN_W);
    capsule3(gp((r[0] + r[1]) / 2, (za + zb) / 2), gp(r[1], zb), TUN_W);
}
module gallery_ramps() {
    ramp_set(G_RAMPS, GZ1, GZ2);
    ramp_set(G_RAMPS2, GZ2, GZ3);
    for (r = G_RAMPS3) capsule3(gp(r[0], GZ3), g4(r[1]), TUN_W);
}
// chodba v atice: smyčka kapslí za okénky (od pravého řezu dozadu k levému)
module attic_tunnel() for (a = [-36 : 6 : 210]) capsule3(g4(a), g4(a + 6), TUN_W);
// výklenky / komůrky ve vnitřní stěně galerií (tmavé otvory za oblouky)
module gallery_niches() for (k = [0 : 2]) for (j = [0 : len(G_NICHES) - 1]) let(t = G_NICHES[j] + (k % 2) * 360 / N_ARCH * 2)
    if (in_body(t))
        translate([(A - WALL - CH_D + 0.5) * cos(t), (B - WALL - CH_D + 0.5) * sin(t), [G1, G2, G3][k]])
            rotate([0, 0, atan2(sin(t) / B, cos(t) / A)]) niche(j % 3 == 0 ? 9 : 6, j % 3 == 0 ? 11 : 8, 7);

// spojení hnízd s galeriemi (místní) a s komůrkou královny (svět)
module links_local() for (l = LINKS) capsule3(l[0], l[1], TUN_W);
module queen_links() both() {
    capsule3([0, QY, QUEEN_Z[0] + 3], [10, QY - 4, QUEEN_Z[0] + 3], TUN_W);
    capsule3([10, QY - 4, QUEEN_Z[0] + 3], wr([52, 5, 42]), TUN_W);
}
// jáma: stupně dolů do středu + spirálové chodbičky ve stěnách stupňů
module pit() {
    for (k = [0 : len(PIT) - 1]) e_prism(PIT[k][0] * A, PIT[k][0] * B, PIT[k][1], H);
    for (k = [0 : len(PIT) - 1]) let(f = PIT[k][0], z0 = PIT[k][1] + 3,
                                     zt = (k == 0 ? H : PIT[k - 1][1]) - 4)
        for (a = [-20 : 15 : 190]) capsule3([(f * A + 1.5) * cos(a), (f * B + 1.5) * sin(a), z0 + (a + 20) / 210 * (zt - z0)],
            [(f * A + 1.5) * cos(a + 15), (f * B + 1.5) * sin(a + 15), z0 + (a + 35) / 210 * (zt - z0)], TUN_W);
    // výklenky ve stěnách stupňů jámy (vidět shora skrz kopuli)
    for (k = [0 : len(PIT) - 1]) let(f = PIT[k][0], zf = PIT[k][1])
        for (a = [0 : 30 : 180]) let(t = a + k * 15)
            translate([f * A * cos(t), f * B * sin(t), zf]) rotate([0, 0, atan2(sin(t) / (f * B), cos(t) / (f * A)) + 180])
                niche(7, 9, 5);
}
module queen_room() {
    translate([0, QY, QUEEN_Z[0]]) cylinder(r = QUEEN_R, h = QUEEN_Z[1] - QUEEN_Z[0], $fn = 96);
    translate([0, QY, QUEEN_Z[1] - 0.01]) cylinder(r = GLASS_R + 0.3, h = 10, $fn = 96);   // lůžko skla Ø 24
}

// ---------- hnízdo na pravém řezu (místní souřadnice)
module nest_local() {
    face_extrude(-1, CH_D * 0.45) nest2d();                    // stěny odstupňované do hloubky
    face_extrude(CH_D * 0.45 - 0.01, CH_D * 0.75) offset(r = -1) nest2d();
    face_extrude(CH_D * 0.75 - 0.01, CH_D) offset(r = -2) nest2d();
    face_extrude(CH_D - 0.01, CH_D + PLASTER_T) offset(delta = -1.5) humid2d();   // sádra, ryska 1,5 mm
    face_extrude(CH_D - 0.01, CH_D + PLASTER_T) translate([24, WATER_Z - 2]) square([62, 6]);   // spojení s vodním kanálem
    nest_cavities([], [], FILL, VENTS, []);
    links_local();
    vent_recesses(VENTS);
    screw_pilots(SCREWS);
}
module core_r() difference() {
    intersection() { solid(); slab_r(); }
    pit();
    frame_r() nest_local();
    queen_links();
    both() frame_r() pin_holes_y(PINS, CORE_T);
}

// ---------- tělo: prstenec + střed bez výseče a bez jader
module body() difference() {
    solid();
    wedge();
    pit();
    queen_room();
    both() slab_r();
    gallery_cut(G1, GH, CH_D);
    gallery_cut(G2, GH, CH_D);
    gallery_cut(G3, GH, CH_D);
    attic_tunnel();
    exit_tunnels();
    gallery_niches();
    gallery_ramps();
    both() frame_r() links_local();
    queen_links();
    both() frame_r() pin_holes_y(PINS, CORE_T);
}

// ---------- věnec: nese pás (drážka dole) a kopuli (drážka nahoře)
CROWN_VENTS = [[-30, -92], [30, -92], [-48, -85], [48, -85]];   // nad výsečí, mimo kopuli
function pit_r(a) = 1 / sqrt(pow(cos(a) / (PIT[0][0] * A), 2) + pow(sin(a) / (PIT[0][0] * B), 2));
module bed_sector(h) linear_extrude(h) polygon(concat([[0, 0]],
    [ for (a = [BED_SECTOR[0] : 5 : BED_SECTOR[1]]) 200 * [cos(a), sin(a)] ]));
DOME_IN = DOME_D / 2 - DOME_GROOVE / 2 - 1;              // vnější stěna záhonku uvnitř kopule
module bed_walls() translate([0, 0, H + CROWN_T]) intersection() {
    bed_sector(BED_H);
    union() {
        difference() { cylinder(r = DOME_IN, h = BED_H, $fn = 160); translate([0, 0, -1]) cylinder(r = DOME_IN - BED_WALL, h = BED_H + 2, $fn = 160); }
        difference() { scale([PIT[0][0] * A + 0.5 + BED_WALL, PIT[0][0] * B + 0.5 + BED_WALL, 1]) cylinder(r = 1, h = BED_H, $fn = 160);
                       translate([0, 0, -1]) scale([PIT[0][0] * A + 0.5, PIT[0][0] * B + 0.5, 1]) cylinder(r = 1, h = BED_H + 2, $fn = 160); }
        for (a = BED_SECTOR) rotate([0, 0, a]) translate([pit_r(a), a < 0 ? 0 : -BED_WALL, 0]) cube([DOME_IN - pit_r(a), BED_WALL, BED_H]);
    }
}
// výlezová věžička: trubka nad úroveň hlíny se dvěma oblouky nahoře
module exit_tower(p) translate([p[0], p[1], H + CROWN_T]) difference() {
    cylinder(d = 12, h = BED_H + 4, $fn = 32);
    for (r = [0, 90]) rotate([0, 0, r]) translate([0, 0, BED_H - 1]) rotate([90, 0, 0]) {
        translate([-2.5, 0, -10]) cube([5, 3.5, 20]); translate([0, 3.5, -10]) cylinder(d = 5, h = 20, $fn = 20); }
}
module exit_holes() for (p = EXITS) translate([p[0], p[1], H - 2]) cylinder(d = TUN_W + 1, h = BED_H + CROWN_T + 10, $fn = 24);
// výlezy: z chodby v atice šikmo nahoru do věžiček
module exit_tunnels() for (p = EXITS) let(t = atan2(p[1], p[0])) capsule3(g4(t), [p[0], p[1], H + 2], TUN_W);

module crown() difference() {
    union() { e_prism(A + 9, B + 9, H, CROWN_T); bed_walls(); for (p = EXITS) exit_tower(p); }
    e_prism(PIT[0][0] * A + 0.5, PIT[0][0] * B + 0.5, H - 1, 10);
    difference() { e_prism(BAND_R + BAND_GROOVE / 2, B + 5.5 + BAND_GROOVE / 2, H - 1, 4);
                   e_prism(BAND_R - BAND_GROOVE / 2, B + 5.5 - BAND_GROOVE / 2, H - 2, 6); }
    translate([0, 0, H + CROWN_T - 2.5]) difference() {        // drážka pro nalepení kopule
        cylinder(d = DOME_D + DOME_GROOVE, h = 5, $fn = 160); translate([0, 0, -1]) cylinder(d = DOME_D - DOME_GROOVE, h = 7, $fn = 160); }
    for (v = CROWN_VENTS) translate([v[0], v[1], H - 1]) { cylinder(d = 6, h = 10, $fn = 24);
        translate([0, 0, CROWN_T + 1 - MESH_RECESS]) cylinder(d = MESH_D + 0.4, h = 2, $fn = 32); }
    both() for (v = VENTS) let(p = wr([v[0], VENT_Y, 0])) translate([p[0], p[1], H - 1]) cylinder(d = 6, h = 10, $fn = 24);
    exit_holes();
}

// ---------- podstavec s obrubou (pás stojí v drážce obruby)
module plinth() difference() {
    union() {
        scale([PL[0], PL[1], 1]) cylinder(r = 1, h = PL_T, $fn = 180);
        translate([0, 0, PL_T]) difference() { e_prism(RIM[1], B + 9, 0, RIM_H); e_prism(RIM[0], B + 2, -1, RIM_H + 2); }
    }
    // zapuštění pro stavbu (bez výseče – tam je podlaha mezery)
    translate([0, 0, PL_T - PL_RECESS]) difference() { e_prism(A + 1.6, B + 1.6, 0, 10); wedge(); }
    // drážka pro pás
    translate([0, 0, PL_T + RIM_H - 4]) difference() {
        e_prism(BAND_R + BAND_GROOVE / 2, B + 5.5 + BAND_GROOVE / 2, 0, 10);
        e_prism(BAND_R - BAND_GROOVE / 2, B + 5.5 - BAND_GROOVE / 2, -1, 12); }
    // průchody obrubou: hadička krmítka (vpravo), 2 zavlažovací hadičky (vlevo)
    translate([A, 0, PL_T + 4]) rotate([0, 90, 0]) cylinder(d = TUBE_OD + 0.3, h = 20, $fn = 48);
    for (a = [176, 184]) rotate([0, 0, a]) translate([A, 0, PL_T + 3]) rotate([0, 90, 0]) cylinder(d = AIRLINE_OD + 0.6, h = 20, $fn = 24);
    translate([TOWER_POS[0], TOWER_POS[1], PL_T - TOWER_POCKET]) cylinder(d = 46.4, h = 10, $fn = 64);
    translate([FEEDER_POS[0] - FEEDER[0] / 2 - 2.2, FEEDER_POS[1] - FEEDER[1] / 2 - 2.2, PL_T - PL_RECESS])
        cube([FEEDER[0] + 4.4, FEEDER[1] + 4.4, 10]);
    for (y = [-60, 0, 60]) translate([0, y, PL_T / 2]) rotate([0, 90, 0])
        cylinder(d = PIN_D, h = 2 * PIN_L, center = true, $fn = 12);
}
// délka pásu (obvod elipsy) – pás fólie 0,5 mm
BAND_LEN = let(a = BAND_R, b = B + 5.5, n = 180, dt = 360 / n)
    [ for (i = [0 : n - 1]) let(t = (i + 0.5) * dt) sqrt(pow(a * sin(t), 2) + pow(b * cos(t), 2)) * dt * PI / 180 ] * [ for (i = [0 : n - 1]) 1 ];
BAND_H = (H + 3) - (RIM_H + PL_RECESS - 4);
module band2d() square([BAND_LEN + 12, BAND_H]);

// ---------- rámeček, víčko (pravý řez; levý je zrcadlo)
module face2d() polygon(FACE_PTS);
module plate2d() intersection() { offset(delta = -7.5) face2d(); translate([19, 10]) square(500); }   // sklo (DXF)
module outer2d() intersection() { offset(delta = -0.5) face2d(); translate([12, 3]) square(500); }
BEZEL_BRIDGES = [[[76, 34.5], [22, 3]], [[78, 54.5], [20, 3]]];   // drží ostrůvky rámečku
module windows2d() difference() {
    offset(r = 1.2) {
        for (c = CHAMBERS) translate([c[0], c[1]]) chamber2d(c[2], c[3]);
        for (t = TUNNELS) tunnel2d(t[0], t[1], TUN_W);
    }
    for (b = BEZEL_BRIDGES) translate(b[0]) square(b[1]);
}
module bezel_local() bezel(SCREWS, MAGNETS) { plate2d(); outer2d(); }   // jedno velké okno
module cover_local(label, mirrored = false) difference() {
    cover(MAGNETS) outer2d();
    face_extrude(-BEZEL_T - COVER_T - 1, -BEZEL_T - COVER_T + 0.6) translate([56, 30])
        mirror([mirrored ? 1 : 0, 0]) text(label, size = 8, halign = "center", valign = "center",
                                           font = "Liberation Serif:style=Bold");
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
        translate([4, 0, 4 - 2.5]) cylinder(d = 16, h = 3, $fn = 48);                    // jamka na cukr/med
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
        translate([4, 0, -1]) cylinder(d = 22, h = 10, $fn = 48);                       // otvor poklopu
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
        for (a = TOWER_OUT_ANG) rotate([0, 0, a]) translate([0, 0, 4.5]) rotate([0, 90, 0])
            cylinder(d = AIRLINE_OD + 0.4, h = 30, $fn = 24);      // 2 vývody: levé a pravé hnízdo
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

module dome_preview() translate([0, 0, H + CROWN_T - 2.5]) difference() {
    sphere(d = DOME_D, $fn = 64); sphere(d = DOME_D - 2, $fn = 64); translate([-100, -100, -200]) cube(200);
}
module band_preview() translate([0, 0, RIM_H + PL_RECESS - 4]) difference() {
    e_prism(BAND_R + 0.25, B + 5.75, 0, BAND_H); e_prism(BAND_R - 0.25, B + 5.25, -1, BAND_H + 2); }
module placed_tower()  translate([TOWER_POS[0], TOWER_POS[1], -TOWER_SINK]) children();
module placed_feeder() translate([FEEDER_POS[0], FEEDER_POS[1], 0]) children();

if (PART == "core_right")   print_core() frame_r_inv() core_r();
if (PART == "core_left")    mirror([1, 0, 0]) print_core() frame_r_inv() core_r();
if (PART == "body")         body();
if (PART == "crown")        translate([0, 0, -H]) crown();                              // záhonkem nahoru
if (PART == "plinth_left")  rotate([0, 0, 90]) intersection() { plinth(); translate([-500, -500, 0]) cube([500, 1000, 100]); }
if (PART == "plinth_right") rotate([0, 0, 90]) intersection() { plinth(); translate([0, -500, 0]) cube([500, 1000, 100]); }
if (PART == "bezel_right")  print_bezel() bezel_local();
if (PART == "bezel_left")   mirror([1, 0, 0]) print_bezel() bezel_local();
if (PART == "cover_right")  print_cover() cover_local("COLOSSEVM");
if (PART == "cover_left")   mirror([1, 0, 0]) print_cover() cover_local("ROMA", true);
if (PART == "tower")        tower();
if (PART == "tower_cap")    tower_cap();
if (PART == "dome_cap")     dome_cap();
if (PART == "feeder")       feeder();
if (PART == "feeder_lid")   feeder_lid();
if (PART == "feeder_hatch") feeder_hatch();
if (PART == "plugs")        plugs();
if (PART == "plate")        plate2d();
if (PART == "band")         band2d();
if (PART == "inner_view")   { body(); both() core_r(); }
if (PART == "assembly") {
    translate([0, 0, -PL_T + PL_RECESS]) color("DimGray") render() plinth();
    color("Wheat") render() body();
    color("BurlyWood") render() core_r();
    color("BurlyWood") mirror([1, 0, 0]) render() core_r();
    color("LightBlue", 0.45) translate([0, QY, QUEEN_Z[1]]) cylinder(r = GLASS_R, h = 3, $fn = 64);
    both() frame_r() { color("LightBlue", 0.35) face_extrude(-PLATE_T, 0) plate2d();
                       color("SaddleBrown") render() bezel_local(); }
    if (SHOW_COVER) color("Wheat") render() crown();
    if (SHOW_COVER) color("SaddleBrown") translate([0, 0, H + CROWN_T + 0.3]) render() intersection() {      // hlína (náhled)
        bed_sector(BED_H - 3); difference() { cylinder(r = DOME_IN - BED_WALL, h = 20, $fn = 96);
            scale([PIT[0][0] * A + 0.5 + BED_WALL, PIT[0][0] * B + 0.5 + BED_WALL, 1]) cylinder(r = 1, h = 20, $fn = 96);
            for (p = EXITS) translate([p[0], p[1], 0]) cylinder(d = 12, h = 20); } }
    if (SHOW_COVER) color("OliveDrab") for (a = [-20 : 14 : 200]) let(r = (pit_r(a) + DOME_IN) / 2)
        translate([r * cos(a), r * sin(a), H + CROWN_T + BED_H - 3]) cylinder(d1 = 7, d2 = 0.5, h = 9, $fn = 6);   // tráva
    if (SHOW_COVER) color("LightBlue", 0.25) dome_preview();
    if (SHOW_COVER) color("LightBlue", 0.15) band_preview();
    placed_tower() { color("Wheat") render() tower();
        color("LightBlue", 0.3) translate([0, 0, TOWER_BASE_H - 3]) cylinder(d = TUBE40_OD, h = TUBE40_L);
        translate([0, 0, TOWER_BASE_H - 3 + TUBE40_L]) color("Wheat") render() tower_cap(); }
    placed_feeder() rotate([0, 0, 0]) { color("Wheat") render() feeder();
        translate([0, 0, FEEDER[2] + 3]) mirror([0, 0, 1]) color("Tan") render() feeder_lid();
        translate([4, 0, FEEDER[2] + 5]) mirror([0, 0, 1]) color("SaddleBrown") render() feeder_hatch(); }
}
SHOW_COVER = true;
if (PART == "face_view")    { frame_r_inv() core_r(); frame_r_inv() frame_r() bezel_local(); }
if (PART == "nest_view")    frame_r_inv() core_r();
