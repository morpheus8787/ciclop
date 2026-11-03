"""Offscreen preview renders of the PC cabinet (needs VTK with EGL/OSMesa)."""
from pathlib import Path

import vtk

from cabinet import BLUE, GREY, ZINC, placed_sheets, purchased_parts

COLORS = {GREY: (0.80, 0.81, 0.80), BLUE: (0.10, 0.30, 0.62),
          ZINC: (0.70, 0.72, 0.75), "cira": (0.65, 0.85, 1.0)}
DOOR_PARTS = ("08 ", "09 ", "16 ", "17 ")


def actor(shape, rgb, opacity=1.0):
    verts, tris = shape.tessellate(0.3, 0.3)
    pts, polys = vtk.vtkPoints(), vtk.vtkCellArray()
    for v in verts:
        pts.InsertNextPoint(v.x, v.y, v.z)
    for a, b, c in tris:
        polys.InsertNextCell(3, (a, b, c))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(polys)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(30)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    act = vtk.vtkActor()
    act.SetMapper(mapper)
    prop = act.GetProperty()
    prop.SetColor(*rgb)
    prop.SetOpacity(opacity)
    prop.SetSpecular(0.15)
    return act


def render(path, actors, cam_pos, size=(900, 1300)):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for a in actors:
        ren.AddActor(a)
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(325, 275, 820)
    cam.SetPosition(*cam_pos)
    cam.SetViewUp(0, 0, 1)
    ren.ResetCamera()
    cam.Zoom(0.95)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.AddRenderer(ren)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(grab.GetOutputPort())
    writer.Write()


def main(out: Path):
    sheets = placed_sheets()
    bought = [actor(s, (0.12, 0.12, 0.12)) for _, s in purchased_parts()]
    closed = [actor(s, COLORS[p.finish], 0.35 if p.finish == "cira" else 1.0)
              for p, s in sheets] + bought
    opened = [actor(s, COLORS[p.finish]) for p, s in sheets
              if not p.name.startswith(DOOR_PARTS)]
    render(out / "nahled_zavreno.png", closed, (-1500, -2300, 1900))
    render(out / "nahled_bez_dveri.png", opened, (-1500, -2300, 1900))
    render(out / "nahled_zezadu.png", closed, (2100, 2900, 1700))
    render_flats(out)


def render_flats(out: Path, names=("01_Bok_spodni_levy", "16_Dvere_monitoru_s_oknem")):
    import ezdxf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    fig, axes = plt.subplots(1, len(names), figsize=(14, 9), dpi=130)
    for ax, name in zip(axes, names):
        doc = ezdxf.readfile(out / "dxf" / f"{name}.dxf")
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace())
        ax.set_title(name.replace("_", " "))
        ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out / "nahled_rozvin.png", facecolor="white")


if __name__ == "__main__":
    main(Path(__file__).parent / "vystup")
