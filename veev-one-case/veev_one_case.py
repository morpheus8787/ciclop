"""Parametric sleeve case for the IQOS VEEV ONE (battery body).

Measured/assumed device size (body without pod): 85.4 x 19 x 10 mm.
Measure your own device with calipers and adjust the constants below.
Run: python3 veev_one_case.py  -> writes veev_one_case.stl and .step
"""
import cadquery as cq

# --- Device dimensions (mm) ---
DEVICE_W = 19.0       # width
DEVICE_D = 10.0       # depth / thickness
DEVICE_EDGE_R = 3.0   # corner radius of the device cross-section

# --- Case parameters (mm) ---
CLEARANCE = 0.25      # gap per side; raise to 0.35 for a looser fit
WALL = 1.6            # side wall thickness
FLOOR = 1.2           # bottom thickness
SLEEVE_LEN = 72.0     # inner depth; leaves the pod and pod latch free
USB_W, USB_H = 11.0, 5.5          # USB-C opening in the floor
THUMB_W, THUMB_LEN = 9.0, 30.0    # push-out slot on the front face
THUMB_FROM_BOTTOM = 8.0

inner_w = DEVICE_W + 2 * CLEARANCE
inner_d = DEVICE_D + 2 * CLEARANCE
outer_w = inner_w + 2 * WALL
outer_d = inner_d + 2 * WALL
outer_len = SLEEVE_LEN + FLOOR
inner_r = DEVICE_EDGE_R + CLEARANCE
outer_r = inner_r + WALL


def build_case() -> cq.Workplane:
    outer = (cq.Workplane("XY").rect(outer_w, outer_d).extrude(outer_len)
             .edges("|Z").fillet(outer_r))
    cavity = (cq.Workplane("XY").workplane(offset=FLOOR)
              .rect(inner_w, inner_d).extrude(SLEEVE_LEN + 1)
              .edges("|Z").fillet(inner_r))
    case = outer.cut(cavity)

    usb = (cq.Workplane("XY").workplane(offset=-1)
           .slot2D(USB_W, USB_H).extrude(FLOOR + 2))
    case = case.cut(usb)

    # XZ workplane normal points to -Y: start just outside the front face
    # and cut only through the front wall
    thumb = (cq.Workplane("XZ", origin=(0, outer_d / 2 + 1, 0))
             .center(0, FLOOR + THUMB_FROM_BOTTOM + THUMB_LEN / 2)
             .slot2D(THUMB_LEN, THUMB_W, angle=90)
             .extrude(WALL + 2))
    case = case.cut(thumb)

    # soften the top rim and the outer bottom edge
    case = case.faces(">Z").edges().fillet(0.6)
    case = case.faces("<Z").edges("not %CIRCLE").fillet(0.8)
    return case


if __name__ == "__main__":
    model = build_case()
    cq.exporters.export(model, "veev_one_case.stl", tolerance=0.02,
                        angularTolerance=0.1)
    cq.exporters.export(model, "veev_one_case.step")
    bb = model.val().BoundingBox()
    print(f"outer size: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
