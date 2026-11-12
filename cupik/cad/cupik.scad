// ============================================================
//  Cupík – malý chodící robot pro školy
//  Parametrický model pro OpenSCAD (https://openscad.org)
//  Licence: CERN-OHL-S-2.0
//
//  Vyber díl v proměnné `dil` (nebo v Customizeru) a dej F6 + Export STL.
//  Všechny rozměry jsou v milimetrech.
// ============================================================

/* [Díl] */
dil = "sestava"; // [sestava, telo, vicko, noha, chodidlo, tykadlo]

/* [Tolerance tisku] */
tol = 0.3;       // vůle pro zasunutí dílů
$fn = 48;

/* [Servo SG90 – změř si svoje kusy!] */
sv_l = 22.8;            // délka těla serva
sv_w = 12.2;            // šířka těla serva
sv_h = 22.7;            // výška těla serva (bez hřídele)
sv_tab_span = 32.3;     // celková délka přes úchyty
sv_tab_t = 2.5;         // tloušťka úchytů
sv_tab_from_top = 4.3;  // vzdálenost úchytů od horní plochy (strana hřídele)
sv_hole_span = 27.8;    // rozteč děr v úchytech
sv_shaft_off = 5.9;     // hřídel od bližšího konce serva
screw_pilot = 1.8;      // díra pro samořezný šroubek serva

/* [Páka serva (jednoramenná)] */
horn_face = 7.5;        // od horní plochy serva k vnější ploše páky
horn_hub_d = 7.2;       // průměr středu páky
horn_tip_d = 4.2;       // průměr konce ramene
horn_len = 14;          // střed páky -> střed konce ramene
horn_t = 1.6;           // hloubka kapsy pro páku

/* [Tělo] */
wall = 3;
floor_t = 3;
lid_t = 3;
in_x = 70;              // vnitřní šířka
in_y = 60;              // vnitřní hloubka
in_z = 60;              // vnitřní výška
corner_r = 6;
hip_x = 23;             // vzdálenost kyčle od středu (vlevo/vpravo)

/* [Baterie 4×AA – plochý držák] */
bat = [63, 58, 15.5];   // šířka, hloubka, výška držáku
bat_z = 20.5;           // výška police pro baterie

/* [Elektronika] */
pcb = [68, 44, 1.6];    // deska plošných spojů
pcb_z = 38;             // výška spodní strany desky
eye_d = 16.6;           // otvory pro HC-SR04
eye_sp = 26;            // rozteč „očí“
eye_z = 47;             // výška středu očí
usb_y = 40;  usb_z = 51;  usb_size = [13, 8];   // otvor pro USB-C (pravý bok)
sw_y = 40;   sw_z = 43;   sw_size = [12, 6];    // otvor pro vypínač (levý bok)

/* [Nohy] */
leg_d = 16;             // hloubka pouzdra kotníkového serva
leg_wall = 2.4;
leg_cap_t = 4;          // horní deska nohy (páka kyčle)
leg_hip_y = 8;          // poloha osy kyčle v noze
foot_w = 28;
foot_t = 3;
foot_front = 10;        // jak daleko chodidlo přesahuje dopředu
foot_back = 38;         // jak daleko chodidlo přesahuje dozadu (těžiště je vzadu)

// ---------- odvozené rozměry ----------
leg_x = sv_w + 2*tol + 2*leg_wall;         // šířka nohy
leg_h = sv_l + 2*tol + 2*5.3;              // výška pouzdra
ankle_z = leg_h/2 - sv_l/2 + sv_shaft_off; // výška osy kotníku v noze
sv_center_off = sv_l/2 - sv_shaft_off;     // střed serva vůči hřídeli
plate_back = -(sv_tab_from_top + horn_face - horn_t); // zadní plocha desky chodidla
plate_t = 4;
sole_top = ankle_z - 15;
gap_y0 = in_y/2 - sv_w/2 - 3;               // volné místo pro vložení kyčelních serv
gap_y1 = in_y/2 + sv_w/2 + 3;

// ============================================================
//  Pomocné tvary
// ============================================================
// zaoblený kvádr: x na střed, y od 0, z od 0
module rbox(size, r) {
    hull() for (sx = [-1, 1], yy = [r, size[1] - r])
        translate([sx * (size[0]/2 - r), yy, 0]) cylinder(r = r, h = size[2]);
}

// kapsa pro jednoramennou páku (rameno míří ve směru +y)
module horn_pocket(depth) {
    hull() {
        cylinder(d = horn_hub_d + 2*tol, h = depth);
        translate([0, horn_len, 0]) cylinder(d = horn_tip_d + 2*tol, h = depth);
    }
}

// podpěrná lišta se zkosením 45° (tiskne se bez podpěr)
module ledge(len_y, width, height) {
    // lišta na stěně: x od 0 (stěna) do -width, y 0..len_y, horní hrana v z = 0
    translate([0, 0, -height]) hull() {
        translate([-width, 0, height - 0.01]) cube([width, len_y, 0.01]);
        translate([-0.01, 0, 0]) cube([0.01, len_y, height]);
    }
}

// ============================================================
//  TĚLO
// ============================================================
module telo() {
    difference() {
        union() {
            difference() {
                translate([0, -wall, -floor_t])
                    rbox([in_x + 2*wall, in_y + 2*wall, floor_t + in_z], corner_r);
                translate([0, 0, 0])
                    rbox([in_x, in_y, in_z + 1], corner_r - wall);
            }
            // police pro baterie (obě boční stěny)
            // (vynechané místo uprostřed, aby šla serva vložit shora)
            for (m = [0, 1]) mirror([m, 0, 0]) {
                translate([in_x/2, 0, bat_z]) ledge(gap_y0, 6, 8);
                translate([in_x/2, gap_y1, bat_z]) ledge(in_y - gap_y1, 6, 8);
                // lišty pro desku plošných spojů
                translate([in_x/2, 15, pcb_z]) ledge(gap_y0 - 15, 3, 5);
                translate([in_x/2, gap_y1, pcb_z]) ledge(in_y - gap_y1, 3, 5);
            }
            // lišta pod senzor HC-SR04 (přední stěna)
            translate([-20, 0, eye_z - 10.5]) rotate([0, 0, -90]) ledge(40, 3, 4);
        }
        // otvory pro kyčelní serva + díry pro šroubky
        for (s = [-1, 1]) {
            cx = s * (hip_x - sv_center_off);
            translate([cx, in_y/2, 0])
                cube([sv_l + 2*tol, sv_w + 2*tol, 3*floor_t + 1], center = true);
            for (h = [-1, 1])
                translate([cx + h * sv_hole_span/2, in_y/2, -floor_t - 1])
                    cylinder(d = screw_pilot, h = floor_t + 2);
        }
        // oči (HC-SR04)
        for (s = [-1, 1])
            translate([s * eye_sp/2, 1, eye_z]) rotate([90, 0, 0])
                cylinder(d = eye_d, h = wall + 2);
        // šuplík na baterie (zadní stěna)
        translate([-(bat[0] + 1)/2, in_y - 1, bat_z])
            cube([bat[0] + 1, wall + 2, bat[2] + 1]);
        // USB-C (pravý bok) a vypínač (levý bok)
        translate([in_x/2 - 1, usb_y - usb_size[0]/2, usb_z - usb_size[1]/2])
            cube([wall + 2, usb_size[0], usb_size[1]]);
        translate([-in_x/2 - wall - 1, sw_y - sw_size[0]/2, sw_z - sw_size[1]/2])
            cube([wall + 2, sw_size[0], sw_size[1]]);
        // průchod kabelů pod polici k servům je volný po stranách
    }
}

// ============================================================
//  VÍČKO (s otvory pro tykadla nebo vlastní ozdoby)
// ============================================================
lip_h = 3;
module vicko() {
    difference() {
        union() {
            translate([0, -wall, 0])
                rbox([in_x + 2*wall, in_y + 2*wall, lid_t], corner_r);
            // límec, který drží víčko v těle
            translate([0, tol, lid_t]) difference() {
                rbox([in_x - 2*tol, in_y - 2*tol, lip_h], corner_r - wall);
                translate([0, 1.6, -1])
                    rbox([in_x - 2*tol - 3.2, in_y - 2*tol - 3.2, lip_h + 2], corner_r - wall - 1.6);
            }
        }
        // díry pro tykadla
        for (s = [-1, 1]) translate([s * 20, in_y/2, -1]) cylinder(d = 5 + tol, h = lid_t + 2);
    }
}

// tykadlo – zasune se do víčka (děti si můžou navrhnout vlastní ozdoby)
module tykadlo() {
    cylinder(d = 5 - tol, h = lid_t + 1);
    translate([0, 0, lid_t + 1]) cylinder(d1 = 7, d2 = 3, h = 18);
    translate([0, 0, lid_t + 22]) sphere(d = 9);
}

// ============================================================
//  NOHA (2 kusy, obě stejné) – tiskni vzhůru nohama
//  Lokální osy: x = 0 osa kotníku, y = 0 přední plocha pouzdra,
//  z = 0 spodek nohy. Kotníkové servo se zasouvá zepředu.
// ============================================================
module noha() {
    cav = [sv_w + 2*tol, sv_l + 2*tol];
    difference() {
        union() {
            translate([-leg_x/2, 0, 0]) cube([leg_x, leg_d, leg_h]);
            // horní deska s kapsou pro páku kyčelního serva
            translate([-leg_x/2, -6, leg_h]) cube([leg_x, 32, leg_cap_t]);
        }
        // dutina pro kotníkové servo (průchozí zepředu dozadu)
        translate([-cav[0]/2, -1, leg_h/2 - cav[1]/2]) cube([cav[0], leg_d + 2, cav[1]]);
        // díry pro šroubky úchytů serva
        for (h = [-1, 1])
            translate([0, -1, leg_h/2 + h * sv_hole_span/2]) rotate([-90, 0, 0])
                cylinder(d = screw_pilot, h = 7);
        // kapsa pro páku kyčle (shora)
        translate([0, leg_hip_y, leg_h + leg_cap_t - horn_t]) horn_pocket(horn_t + 1);
        // průchod pro šroubovák (šroubek páky kyčle)
        translate([0, leg_hip_y, -1]) cylinder(d = 3.2, h = leg_h + leg_cap_t + 2);
        // místo pro střed páky (náboj)
        translate([0, leg_hip_y, leg_h - 1]) cylinder(d = 3.2, h = 10);
    }
}

// ============================================================
//  CHODIDLO (2 kusy, obě stejné)
//  Stejné lokální osy jako noha. Páka kotníku je v zadní ploše desky.
// ============================================================
module chodidlo() {
    plate_top = ankle_z + horn_len + horn_tip_d/2 + 2.5;
    difference() {
        union() {
            // svislá deska
            translate([-9, plate_back - plate_t, sole_top - 0.01])
                cube([18, plate_t, plate_top - sole_top]);
            // podrážka se zaoblenými rohy
            translate([0, plate_back - plate_t - foot_front, sole_top - foot_t])
                rbox([foot_w, foot_front + plate_t + foot_back, foot_t], 5);
            // výztuhy před deskou
            for (s = [-1, 1]) translate([s * 6 - 1.5, plate_back - plate_t, sole_top])
                hull() {
                    translate([0, -0.01, 0]) cube([3, 0.01, 12]);
                    translate([0, -8, 0]) cube([3, 8, 0.01]);
                }
        }
        // kapsa pro páku (rameno míří nahoru)
        translate([0, plate_back + 0.01, ankle_z]) rotate([90, 0, 0])
            horn_pocket(horn_t + 0.01);
        // díra pro šroubek páky + zahloubení
        translate([0, plate_back + 1, ankle_z]) rotate([90, 0, 0]) cylinder(d = 2.5, h = plate_t + 2);
        translate([0, plate_back - plate_t + 1.2, ankle_z]) rotate([90, 0, 0]) cylinder(d = 5.5, h = 2);
    }
}

// ============================================================
//  SESTAVA (jen pro náhled)
// ============================================================
module servo_model() { // horní plocha (hřídel) směrem -z, hřídel v počátku
    color("steelblue") {
        translate([sv_center_off - sv_l/2, -sv_w/2, 0]) cube([sv_l, sv_w, sv_h]);
        translate([sv_center_off - sv_tab_span/2, -sv_w/2, sv_tab_from_top])
            cube([sv_tab_span, sv_w, sv_tab_t]);
        translate([0, 0, -4]) cylinder(d = 5, h = 4);
    }
}

leg_top_world = -floor_t - (sv_tab_from_top - floor_t) - horn_face + horn_t;

module sestava() {
    color("gold") telo();
    color("orange") translate([0, 0, in_z + lid_t]) mirror([0, 0, 1]) vicko();
    color("orange") for (s = [-1, 1]) translate([s * 20, in_y/2, in_z + lid_t]) tykadlo();
    // kyčelní serva (hřídel dolů, k vnější straně)
    for (s = [-1, 1]) translate([s * hip_x, in_y/2, -(sv_tab_from_top - floor_t) - floor_t])
        mirror([s < 0 ? 1 : 0, 0, 0]) mirror([1, 0, 0]) servo_model();
    for (s = [-1, 1])
        translate([s * hip_x, in_y/2 - leg_hip_y, leg_top_world - leg_h - leg_cap_t]) {
            color("deepskyblue") noha();
            color("tomato") chodidlo();
        }
}

// ============================================================
if (dil == "sestava")  sestava();
if (dil == "telo")     telo();
if (dil == "vicko")    vicko();
if (dil == "noha")     rotate([180, 0, 0]) noha();      // tisk vzhůru nohama
if (dil == "chodidlo") translate([0, 0, -sole_top + foot_t]) chodidlo();
if (dil == "tykadlo")  tykadlo();
