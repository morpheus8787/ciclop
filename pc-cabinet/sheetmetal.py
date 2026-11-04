"""Minimal sheet-metal helper: flat plate with 90° flanges.

A part is defined in its local frame by its outer (mould-line) size a x b,
thickness t, flanges on any of the four edges (all bent towards +Z) and
cutouts in the base plate. The same definition produces:
  * a 3D solid (sharp-cornered approximation of the bent part)
  * a flat pattern (DXF) using bend allowance with a K-factor.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq
from cadquery.occ_impl.exporters.dxf import DxfDocument

K_FACTOR = 0.44  # fallback only, for thicknesses missing in BEND_DEDUCTION
STEEL_DENSITY = 7.85e-6  # kg / mm^3

# Bend deduction per 90° bend from the press-brake shop (mm), by thickness.
# Flat length = sum of outer dimensions - number_of_bends * deduction.
BEND_DEDUCTION = {1.0: 2.0, 1.5: 2.5}


@dataclass(frozen=True)
class Flange:
    edge: str            # "x0", "x1", "y0" or "y1"
    height: float        # outer height, including sheet thickness
    trim0: float = 0.0   # shorten flange at the low end of the edge
    trim1: float = 0.0   # shorten flange at the high end of the edge


@dataclass(frozen=True)
class Hole:
    x: float
    y: float
    d: float


@dataclass(frozen=True)
class Slot:
    """Centered slot; w along local x, h along local y."""
    x: float
    y: float
    w: float
    h: float
    rounded: bool = True


@dataclass(frozen=True)
class SheetPart:
    name: str
    a: float
    b: float
    t: float
    flanges: tuple = ()
    cutouts: tuple = ()
    material: str = "DC01"
    finish: str = "RAL 7035"
    density: float = STEEL_DENSITY
    radius: float | None = None

    # --- bend geometry -------------------------------------------------
    @property
    def r(self) -> float:
        return self.t if self.radius is None else self.radius

    @property
    def bend_deduction(self) -> float:
        if self.t in BEND_DEDUCTION:
            return BEND_DEDUCTION[self.t]
        return 2 * self.setback - math.pi / 2 * (self.r + K_FACTOR * self.t)

    @property
    def bend_allowance(self) -> float:
        # consistent with the deduction: BD = 2 * (R + t) - BA
        return 2 * self.setback - self.bend_deduction

    @property
    def setback(self) -> float:
        return self.r + self.t

    def flange(self, edge: str) -> Flange | None:
        return next((f for f in self.flanges if f.edge == edge), None)

    def span(self, f: Flange) -> tuple[float, float]:
        """Extent of a flange along its edge (mould coordinates)."""
        if f.edge in ("x0", "x1"):
            length, low, high = self.b, "y0", "y1"
        else:
            length, low, high = self.a, "x0", "x1"
        s0 = max(f.trim0, self.setback if self.flange(low) else 0.0)
        s1 = length - max(f.trim1, self.setback if self.flange(high) else 0.0)
        return s0, s1

    # --- 3D ----------------------------------------------------------------
    def solid(self) -> cq.Workplane:
        t = self.t
        body = cq.Workplane("XY").box(self.a, self.b, t, centered=False)
        for c in self.cutouts:
            body = body.cut(_cutter(c, t))
        for f in self.flanges:
            s0, s1 = self.span(f)
            x, y, dx, dy = {
                "x0": (0, s0, t, s1 - s0),
                "x1": (self.a - t, s0, t, s1 - s0),
                "y0": (s0, 0, s1 - s0, t),
                "y1": (s0, self.b - t, s1 - s0, t),
            }[f.edge]
            plate = cq.Workplane("XY").box(dx, dy, f.height, centered=False)
            body = body.union(plate.translate((x, y, 0)))
        return body

    # --- flat pattern ------------------------------------------------------
    def _ext(self, edge: str) -> float:
        f = self.flange(edge)
        return f.height - self.setback + self.bend_allowance if f else 0.0

    def _sb(self, edge: str) -> float:
        return self.setback if self.flange(edge) else 0.0

    def mx(self, x: float) -> float:
        return self._ext("x0") + x - self._sb("x0")

    def my(self, y: float) -> float:
        return self._ext("y0") + y - self._sb("y0")

    def flat(self) -> cq.Workplane:
        """Flat blank as a thin solid in XY (z = 0..t)."""
        t = self.t
        x0, x1 = self.mx(self._sb("x0")), self.mx(self.a - self._sb("x1"))
        y0, y1 = self.my(self._sb("y0")), self.my(self.b - self._sb("y1"))
        rects = [(x0, y0, x1, y1)]
        for f in self.flanges:
            s0, s1 = self.span(f)
            ext = self._ext(f.edge)
            rects.append({
                "x0": (0, self.my(s0), x0, self.my(s1)),
                "x1": (x1, self.my(s0), x1 + ext, self.my(s1)),
                "y0": (self.mx(s0), 0, self.mx(s1), y0),
                "y1": (self.mx(s0), y1, self.mx(s1), y1 + ext),
            }[f.edge])
        blank = None
        for (ax, ay, bx, by) in rects:
            box = cq.Workplane("XY").box(bx - ax, by - ay, t, centered=False)
            box = box.translate((ax, ay, 0))
            blank = box if blank is None else blank.union(box)
        for c in self.cutouts:
            moved = (Hole(self.mx(c.x), self.my(c.y), c.d) if isinstance(c, Hole)
                     else Slot(self.mx(c.x), self.my(c.y), c.w, c.h, c.rounded))
            blank = blank.cut(_cutter(moved, t))
        return blank

    def bend_lines(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        half = self.bend_allowance / 2
        lines = []
        for f in self.flanges:
            s0, s1 = self.span(f)
            if f.edge == "x0":
                x = self.mx(self.setback) - half
                lines.append(((x, self.my(s0)), (x, self.my(s1))))
            elif f.edge == "x1":
                x = self.mx(self.a - self.setback) + half
                lines.append(((x, self.my(s0)), (x, self.my(s1))))
            elif f.edge == "y0":
                y = self.my(self.setback) - half
                lines.append(((self.mx(s0), y), (self.mx(s1), y)))
            else:
                y = self.my(self.b - self.setback) + half
                lines.append(((self.mx(s0), y), (self.mx(s1), y)))
        return lines

    def flat_size(self) -> tuple[float, float]:
        bb = self.flat().val().BoundingBox()
        return bb.xlen, bb.ylen

    def mass_kg(self) -> float:
        return self.flat().val().Volume() * self.density

    def export_dxf(self, path: str, qty: int) -> None:
        face = self.flat().faces("<Z").val()
        doc = DxfDocument()
        doc.add_layer("CUT", color=7)
        doc.add_layer("BEND", color=1, linetype="DASHED")
        doc.add_layer("TEXT", color=3)
        doc.add_shape(face, "CUT")
        msp = doc.document.modelspace()
        note = f"OHYB NAHORU 90° R{self.r:g}"
        for (p0, p1) in self.bend_lines():
            msp.add_line(p0, p1, dxfattribs={"layer": "BEND"})
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            msp.add_text(note, height=4, dxfattribs={"layer": "TEXT"}).set_placement(mid)
        w, h = self.flat_size()
        label = (f"{self.name} | {self.material} t={self.t:g} | {qty} ks | "
                 f"rozvin {w:.1f} x {h:.1f} | odecet ohybu {self.bend_deduction:.2f} mm")
        msp.add_text(label, height=6, dxfattribs={"layer": "TEXT"}).set_placement((0, -15))
        doc.document.saveas(path)


def _cutter(c, t: float) -> cq.Workplane:
    wp = cq.Workplane("XY").workplane(offset=-1).center(c.x, c.y)
    if isinstance(c, Hole):
        sk = wp.circle(c.d / 2)
    elif not c.rounded:
        sk = wp.rect(c.w, c.h)
    elif c.w >= c.h:
        sk = wp.slot2D(c.w, c.h)
    else:
        sk = wp.slot2D(c.h, c.w, angle=90)
    return sk.extrude(t + 2)


def place(shape: cq.Workplane, origin, ex, ey) -> cq.Shape:
    """Map local (x, y, z) to world origin + x*ex + y*ey + z*(ex × ey)."""
    ex, ey = cq.Vector(*ex), cq.Vector(*ey)
    plane = cq.Plane(origin=origin, xDir=ex, normal=ex.cross(ey))
    return shape.val().moved(cq.Location(plane))
