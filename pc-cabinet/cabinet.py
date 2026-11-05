"""Sheet-metal industrial PC cabinet, 650 x 550 x 1650 mm (W x D x H).

Layout (bottom to top): PC compartment with door and adjustable shelf,
lockable keyboard drawer, worktop, open niche, ventilated monitor
compartment with window door and VESA bracket (monitor 540 x 330 x 200 mm).

World axes: X = width (left->right), Y = depth (front->back), Z = up.
Run:  python3 cabinet.py   -> STEP assembly, DXF flat patterns, BOM, checks.
"""
from __future__ import annotations

import csv
import itertools
from pathlib import Path

import cadquery as cq

from sheetmetal import Flange, Hole, SheetPart, Slot, place

# --- overall dimensions -------------------------------------------------
W, D, H = 650.0, 550.0, 1650.0
T_BODY, T_DOOR = 1.5, 1.0          # carcass / doors, drawer, shelf
WORKTOP_Z = 1000.0                  # top of lower carcass
UPPER_D = 320.0                     # depth of monitor compartment
UPPER_Y = D - UPPER_D               # front face of monitor compartment
MONITOR_FLOOR_Z = 1130.0            # floor of monitor compartment
DOOR_GAP = 3.0                      # side gap of overlay doors
LOCK_D = 20.0                       # cam lock hole
SIDE_FLANGE = 12.0                  # front flange of lower side panels

# --- orientation presets: (ex, ey); local flanges point along ex × ey ----
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
SIDE_L = (Y, Z)        # flanges +X
SIDE_R = (Z, Y)        # flanges -X
HORIZ_DOWN = (Y, X)    # flanges -Z
HORIZ_UP = (X, Y)      # flanges +Z
BACK = (X, Z)          # flanges -Y (towards the front)
FRONT = (Z, X)         # flanges +Y (doors, towards the carcass)

GREY, BLUE, ZINC = "RAL 7035", "RAL 5010", "pozink"


def vent_grid(cols, rows, w, h):
    return tuple(Slot(c, r, w, h) for c in cols for r in rows)


def frange(start, stop, step):
    n = int(round((stop - start) / step))
    return [start + i * step for i in range(n + 1)]


# --- lower carcass --------------------------------------------------------
LOW_SIDE_H = WORKTOP_Z - T_BODY
CLIP_Y = (40.0, 500.0)
CLIP_Z = frange(120.0, 792.0, 32.0)

side_l = SheetPart(
    "01 Bok spodni levy", a=D - T_BODY, b=LOW_SIDE_H, t=T_BODY,
    flanges=(Flange("x0", SIDE_FLANGE, trim1=31.0),),
    cutouts=tuple(Slot(y, z, 5, 12, False) for y in CLIP_Y for z in CLIP_Z))
side_r = SheetPart(
    "02 Bok spodni pravy", a=LOW_SIDE_H, b=D - T_BODY, t=T_BODY,
    flanges=(Flange("y0", SIDE_FLANGE, trim1=31.0),),
    cutouts=tuple(Slot(z, y, 12, 5, False) for y in CLIP_Y for z in CLIP_Z))

VENT_COLS = (145.0, 265.0, 385.0, 505.0)
back_low = SheetPart(
    "03 Zada spodni", a=W, b=LOW_SIDE_H, t=T_BODY,
    cutouts=vent_grid(VENT_COLS, frange(760, 940, 20), 100, 8)
    + vent_grid(VENT_COLS, frange(120, 200, 20), 100, 8)
    + (Slot(W / 2, 260, 160, 50),))

worktop = SheetPart(
    "04 Pracovni deska", a=D, b=W, t=T_BODY,
    flanges=(Flange("x0", 30.0, T_BODY, T_BODY),),
    cutouts=(Hole(500.0, W / 2, 60.0),))

bottom = SheetPart(
    "05 Dno se soklem", a=D - 2 * T_BODY, b=W - 2 * T_BODY, t=T_BODY,
    flanges=(Flange("x0", 50.0), Flange("x1", 50.0)))

DIVIDER_Z = 868.0
divider = SheetPart(
    "06 Mezidno nadprazi dveri", a=D - 2 * T_BODY, b=W - 2 * T_BODY, t=T_BODY,
    flanges=(Flange("x0", 40.0),),
    cutouts=(Hole(500.0 - T_BODY, W / 2 - T_BODY, 60.0),))

shelf = SheetPart(
    "07 Police stavitelna", a=500.0, b=W - 7.0, t=T_DOOR,
    flanges=(Flange("x0", 25.0), Flange("x1", 25.0)),
    material="DX51D+Z (pozink)", finish=ZINC)

# --- doors and drawer -------------------------------------------------------
DOOR_W = W - 2 * DOOR_GAP
DOOR_FLANGES = tuple(Flange(e, 20.0) for e in ("x0", "x1", "y0", "y1"))
LOW_DOOR_Z, LOW_DOOR_H = 54.0, 770.0
door_low = SheetPart(
    "08 Dvere spodni", a=LOW_DOOR_H, b=DOOR_W, t=T_DOOR, flanges=DOOR_FLANGES,
    cutouts=(Hole(LOW_DOOR_H / 2, DOOR_W - 34, LOCK_D),)
    + vent_grid((60.0, 100.0, 140.0), (DOOR_W / 2 - 120, DOOR_W / 2, DOOR_W / 2 + 120),
                8, 90),
    finish=BLUE)

DRAWER_Z, DRAWER_H = 872.0, 96.0
drawer_front = SheetPart(
    "09 Celo zasuvky", a=DRAWER_H, b=DOOR_W, t=T_DOOR, flanges=DOOR_FLANGES,
    cutouts=(Hole(DRAWER_H / 2, DOOR_W - 40, LOCK_D),
             Slot(DRAWER_H / 2, DOOR_W / 2, 20, 160)),
    finish=BLUE)

SLIDE_W = 13.0
drawer_body = SheetPart(
    "10 Vana zasuvky klavesnice", a=W - 2 * T_BODY - 2 * SLIDE_W, b=440.0,
    t=T_DOOR, flanges=tuple(Flange(e, 60.0) for e in ("x0", "x1", "y0", "y1")))

# --- upper (monitor) compartment -------------------------------------------
UP_SIDE_H = H - WORKTOP_Z - T_BODY
UP_VENT_ROWS = frange(520, 610, 15) + frange(150, 210, 15)
UP_VENT_COLS = (80.0, 160.0, 240.0)
up_side_l = SheetPart(
    "11 Bok horni levy", a=UPPER_D - T_BODY, b=UP_SIDE_H, t=T_BODY,
    flanges=(Flange("x0", 20.0, trim1=21.0),),
    cutouts=vent_grid(UP_VENT_COLS, UP_VENT_ROWS, 60, 6))
up_side_r = SheetPart(
    "12 Bok horni pravy", a=UP_SIDE_H, b=UPPER_D - T_BODY, t=T_BODY,
    flanges=(Flange("y0", 20.0, trim1=21.0),),
    cutouts=tuple(Slot(r, c, 6, 60) for c in UP_VENT_COLS for r in UP_VENT_ROWS))

up_back = SheetPart(
    "13 Zada horni", a=W, b=UP_SIDE_H, t=T_BODY,
    cutouts=vent_grid(VENT_COLS, frange(560, 620, 15), 100, 8))

up_top = SheetPart(
    "14 Strop horni", a=UPPER_D, b=W, t=T_BODY, flanges=(Flange("x0", 20.0, T_BODY, T_BODY),))

monitor_floor = SheetPart(
    "15 Dno monitoru", a=UPPER_D - 2 * T_BODY, b=W - 2 * T_BODY, t=T_BODY,
    flanges=(Flange("x0", 30.0),),
    cutouts=(Hole(500.0 - UPPER_Y - T_BODY, W / 2 - T_BODY, 50.0),))

UP_DOOR_Z = 1102.0
UP_DOOR_H = H - 3.0 - UP_DOOR_Z
WIN_CX, WIN_CY, WIN_H, WIN_W = 213.0, DOOR_W / 2, 350.0, 560.0
STUD_X = (WIN_CX - WIN_H / 2 - 15, WIN_CX, WIN_CX + WIN_H / 2 + 15)
STUD_Y = (WIN_CY - WIN_W / 2 - 15, WIN_CY, WIN_CY + WIN_W / 2 + 15)
STUDS = [(x, y) for x in STUD_X for y in STUD_Y if (x, y) != (WIN_CX, WIN_CY)]
door_up = SheetPart(
    "16 Dvere monitoru s oknem", a=UP_DOOR_H, b=DOOR_W, t=T_DOOR,
    flanges=DOOR_FLANGES,
    cutouts=(Slot(WIN_CX, WIN_CY, WIN_H, WIN_W, False),
             Hole(470.0, DOOR_W - 34, LOCK_D))
    + tuple(Hole(x, y, 4.2) for x, y in STUDS),
    finish=BLUE)

GLASS_H, GLASS_W = WIN_H + 60, WIN_W + 60
GLASS_OFF = (WIN_CX - GLASS_H / 2, WIN_CY - GLASS_W / 2)
glazing = SheetPart(
    "17 Zaskleni PC 4 mm", a=GLASS_H, b=GLASS_W, t=4.0,
    cutouts=tuple(Hole(x - GLASS_OFF[0], y - GLASS_OFF[1], 4.5) for x, y in STUDS),
    material="polykarbonat 4 mm", finish="cira", density=1.2e-6)

VESA_X, VESA_Z = W / 2 - 80, 1165.0
vesa = SheetPart(
    "18 Drzak VESA 75-100", a=300.0, b=160.0, t=2.0,
    flanges=(Flange("y0", D - T_BODY - 527.0), Flange("y1", D - T_BODY - 527.0)),
    cutouts=tuple(Hole(150 + dx, 80 + dy, 5.0)
                  for p in (50.0, 37.5) for dx in (-p, p) for dy in (-p, p)),
    finish=GREY)

# (part, origin, (ex, ey))
LAYOUT = [
    (side_l, (0, 0, 0), SIDE_L),
    (side_r, (W, 0, 0), SIDE_R),
    (back_low, (0, D, 0), BACK),
    (worktop, (0, 0, WORKTOP_Z), HORIZ_DOWN),
    (bottom, (T_BODY, T_BODY, 50.0), HORIZ_DOWN),
    (divider, (T_BODY, T_BODY, DIVIDER_Z), HORIZ_DOWN),
    (shelf, (3.5, 20.0, 450.0), HORIZ_DOWN),
    (door_low, (DOOR_GAP, -21.0, LOW_DOOR_Z), FRONT),
    (drawer_front, (DOOR_GAP, -21.0, DRAWER_Z), FRONT),
    (drawer_body, (T_BODY + SLIDE_W, -1.0, 874.0), HORIZ_UP),
    (up_side_l, (0, UPPER_Y, WORKTOP_Z), SIDE_L),
    (up_side_r, (W, UPPER_Y, WORKTOP_Z), SIDE_R),
    (up_back, (0, D, WORKTOP_Z), BACK),
    (up_top, (0, UPPER_Y, H), HORIZ_DOWN),
    (monitor_floor, (T_BODY, UPPER_Y + T_BODY, MONITOR_FLOOR_Z), HORIZ_DOWN),
    (door_up, (DOOR_GAP, UPPER_Y - 21.0, UP_DOOR_Z), FRONT),
    (glazing, (DOOR_GAP + GLASS_OFF[1], UPPER_Y - 20.0, UP_DOOR_Z + GLASS_OFF[0]), FRONT),
    (vesa, (VESA_X, 527.0, VESA_Z), FRONT),
]

WELDED = {side_l, side_r, back_low, worktop, bottom, divider, up_side_l,
          up_side_r, up_back, up_top, monitor_floor}


def world(origin, axes, lx, ly, lz=0.0):
    ex, ey = cq.Vector(*axes[0]), cq.Vector(*axes[1])
    return cq.Vector(*origin) + ex * lx + ey * ly + ex.cross(ey) * lz


def purchased_parts() -> list[tuple[str, cq.Shape]]:
    """Simplified bought-in parts: hinges, cam locks, drawer slides."""
    parts = []
    for z0, h, y0 in ((LOW_DOOR_Z, LOW_DOOR_H, 0.0), (UP_DOOR_Z, UP_DOOR_H, UPPER_Y)):
        for zc in (z0 + 60, z0 + h - 120):
            hinge = cq.Workplane("XY").circle(6).extrude(60).translate((DOOR_GAP - 2, y0 - 22, zc))
            parts.append(("Pant privarovaci", hinge.val()))
    lock_points = [
        (door_low, LAYOUT[7]), (drawer_front, LAYOUT[8]), (door_up, LAYOUT[15])]
    for part, (_, origin, axes) in lock_points:
        hole = next(c for c in part.cutouts if isinstance(c, Hole) and c.d == LOCK_D)
        p = world(origin, axes, hole.x, hole.y)
        lock = (cq.Workplane("XZ", origin=(p.x, p.y, p.z)).circle(LOCK_D / 2 + 2)
                .extrude(4).union(cq.Workplane("XZ", origin=(p.x, p.y, p.z))
                                  .circle(LOCK_D / 2 - 0.5).extrude(-18)))
        parts.append(("Zamek vackovy 20 mm", lock.val()))
    for x in (T_BODY, W - T_BODY - SLIDE_W + 0.3):
        slide = cq.Workplane("XY").box(SLIDE_W - 0.3, 400, 45, centered=False)
        parts.append(("Pojezd teleskopicky 400 mm", slide.translate((x, 2, 880)).val()))
    return parts


def placed_sheets() -> list[tuple[SheetPart, cq.Shape]]:
    return [(p, place(p.solid(), o, *axes)) for p, o, axes in LAYOUT]


def check_interference(sheets) -> list[str]:
    problems = []
    for (pa, sa), (pb, sb) in itertools.combinations(sheets, 2):
        ba, bb = sa.BoundingBox(), sb.BoundingBox()
        if (ba.xmax <= bb.xmin or bb.xmax <= ba.xmin or ba.ymax <= bb.ymin
                or bb.ymax <= ba.ymin or ba.zmax <= bb.zmin or bb.zmax <= ba.zmin):
            continue
        vol = sa.intersect(sb).Volume()
        if vol > 1.0:
            problems.append(f"{pa.name} x {pb.name}: {vol:.0f} mm3")
    return problems


def build(out: Path) -> None:
    out.mkdir(exist_ok=True)
    (out / "dxf").mkdir(exist_ok=True)
    sheets = placed_sheets()
    colors = {GREY: cq.Color(0.80, 0.81, 0.80), BLUE: cq.Color(0.10, 0.30, 0.60),
              ZINC: cq.Color(0.70, 0.72, 0.75), "cira": cq.Color(0.7, 0.85, 0.95, 0.35)}
    assy = cq.Assembly(name="pc_skrin")
    for part, shape in sheets:
        assy.add(shape, name=part.name.replace(" ", "_"), color=colors[part.finish])
    for i, (name, shape) in enumerate(purchased_parts()):
        assy.add(shape, name=f"N{i:02d}_{name.replace(' ', '_')}",
                 color=cq.Color(0.15, 0.15, 0.15))
    assy.export(str(out / "pc_skrin_sestava.step"))

    rows, total = [], 0.0
    for part, _ in sheets:
        fname = part.name.split(" ")[0] + "_" + part.name.split(" ", 1)[1].replace(" ", "_")
        part.export_dxf(str(out / "dxf" / f"{fname}.dxf"), qty=1)
        w, h = part.flat_size()
        mass = part.mass_kg()
        total += mass
        rows.append([part.name, 1, part.material, part.t, f"{w:.1f}", f"{h:.1f}",
                     len(part.flanges), part.finish, f"{mass:.2f}",
                     "svařenec korpusu" if part in WELDED else "samostatný díl"])
    with open(out / "kusovnik.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f, delimiter=";")
        wr.writerow(["dil", "ks", "material", "tloustka_mm", "rozvin_x_mm",
                     "rozvin_y_mm", "pocet_ohybu", "povrch", "hmotnost_kg", "pozn"])
        wr.writerows(rows)
        for name, _ in purchased_parts():
            wr.writerow([name, 1, "nakupovaný díl", "", "", "", "", "", "", ""])
    print(f"plechové díly: {len(rows)}, hmotnost plechů {total:.1f} kg")
    issues = check_interference(sheets)
    print("kolize:", "žádné" if not issues else "\n  " + "\n  ".join(issues))
    bb = cq.Compound.makeCompound([s for _, s in sheets]).BoundingBox()
    print(f"obrys sestavy: X {bb.xmin:.1f}..{bb.xmax:.1f}  Y {bb.ymin:.1f}..{bb.ymax:.1f}"
          f"  Z {bb.zmin:.1f}..{bb.zmax:.1f}")


if __name__ == "__main__":
    build(Path(__file__).parent / "vystup")
