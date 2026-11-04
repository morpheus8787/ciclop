// Zkušební pulzní motor s magnety 20 x 10 x 2 mm
// Rozměry odpovídají výchozím parametrům v motor_model.py.
// Vyberte díl:  dil = "rotor" | "stojan" | "civka" | "sestava"
dil = "sestava";

$fn = 96;

// --- magnet ---
mag_t = 10.0;      // tečně
mag_h = 20.0;      // podél osy
mag_d = 2.0;       // tloušťka (směr magnetizace)
vule  = 0.25;      // vůle kapsy
// --- rotor ---
n_mag   = 8;
r_mag   = 30.0;    // osa -> střed magnetu
stena   = 0.8;     // vnější stěna před magnetem (drží proti odstředivé síle!)
rotor_h = 22.0;
hridel  = 8.2;     // závitová tyč M8 / hřídel 8 mm
// --- cívka (vinutí 0,3 mm CuL, cca 580 z) ---
civ_ri = 4.0;  civ_ro = 11.0;  civ_l = 12.0;
celo_predni = 0.6; celo_zadni = 1.2;
mezera = 2.5;      // čelo magnetu -> čelo vinutí (= Civka.mezera v modelu)
// --- stojan (ložiska 608ZZ) ---
loz_d = 22.2;  loz_w = 7.0;  osa_v = 45.0;

apotema  = r_mag + mag_d / 2 + vule + stena;      // vnější plocha rotoru
x_vinuti = r_mag + mag_d / 2 + mezera;            // čelo vinutí od osy
x_civka  = x_vinuti - celo_predni;                // začátek kostry cívky
delka_kostry = celo_predni + civ_l + celo_zadni;
echo(str("Vůle rotor - cívka: ", x_civka - apotema, " mm"));

module rotor() {
    difference() {
        rotate([0, 0, 180 / n_mag])
            cylinder(r = apotema / cos(180 / n_mag), h = rotor_h, $fn = n_mag);
        translate([0, 0, -1]) cylinder(d = hridel, h = rotor_h + 2);
        // kapsy na magnety, vkládají se shora
        for (i = [0 : n_mag - 1]) rotate([0, 0, i * 360 / n_mag])
            translate([r_mag - mag_d / 2 - vule, -(mag_t + 2 * vule) / 2,
                       (rotor_h - mag_h) / 2])
                cube([mag_d + 2 * vule, mag_t + 2 * vule, rotor_h]);
        // odlehčení
        for (i = [0 : n_mag - 1]) rotate([0, 0, (i + 0.5) * 360 / n_mag])
            translate([18, 0, -1]) cylinder(d = 9, h = rotor_h + 2);
    }
}

module civka_kostra() {
    difference() {
        union() {
            cylinder(r = civ_ri, h = delka_kostry);
            cylinder(r = civ_ro + 0.5, h = celo_predni);
            translate([0, 0, delka_kostry - celo_zadni])
                cylinder(r = civ_ro + 1, h = celo_zadni);
        }
        translate([0, 0, -1]) cylinder(d = 3.2, h = delka_kostry + 2);   // šroub M3
        translate([civ_ri - 0.5, -0.6, delka_kostry - celo_zadni - 1])
            cube([civ_ro, 1.2, celo_zadni + 2]);                       // vývod drátu
    }
}

module stojan() {
    sirka = rotor_h + 2 * loz_w + 12;
    translate([-45, -sirka / 2, 0]) cube([105, sirka, 4]);
    // dva stojánky s ložisky 608ZZ
    for (s = [-1, 1]) translate([0, s * (rotor_h / 2 + 3 + loz_w / 2), 0])
        difference() {
            translate([-16, -loz_w / 2, 0]) cube([32, loz_w, osa_v + 16]);
            translate([0, 0, osa_v]) rotate([90, 0, 0])
                cylinder(d = loz_d, h = loz_w + 2, center = true);
        }
    // sloupek cívky (cívka přišroubována M3 z boku)
    translate([x_civka + delka_kostry, -8, 0]) difference() {
        cube([5, 16, osa_v + 8]);
        translate([-1, 8, osa_v]) rotate([0, 90, 0]) cylinder(d = 3.2, h = 7);
    }
    // sloupek Hallovy sondy naproti cívce (180° = 4 rozteče);
    // svislá drážka umožní posunem sondy nahoru/dolů ladit úhel sepnutí
    translate([-apotema - 6, -6, 0]) difference() {
        cube([4, 12, osa_v + 12]);
        translate([-1, 4.5, osa_v - 9]) cube([6, 3, 18]);
    }
}

module sestava() {
    stojan();
    translate([0, rotor_h / 2, osa_v]) rotate([90, 0, 0]) rotor();
    translate([x_civka, 0, osa_v]) rotate([0, 90, 0]) color("orange") civka_kostra();
}

if (dil == "rotor") rotor();
else if (dil == "stojan") stojan();
else if (dil == "civka") civka_kostra();
else sestava();
