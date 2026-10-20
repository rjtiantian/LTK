# -*- coding: utf-8 -*-
"""矩形管 STEP 生成（交管材激光）：照客户样例 支架1.STEP 的做法——
空心矩形管，外角 R = 1.5t、内角 R = 0.5t（40×40×2 → R3 / R1），每种管单独一个实体/文件；
孔、腰孔贯穿；横撑与立柱插接定位：横撑一侧管壁伸出 3.5 作定位舌（宽 13，两边各 0.25 间隙），
立柱对应管角开 13.5 × 3.75 缺口（同样例 支架1：舌 13.02 × 3.5，缺口 13.52 × 3.75 / 3.45）。

需 OCP（cadquery-ocp）。坐标：管长沿 +z（0 ~ L），截面 x ∈ [0, a]、y ∈ [0, b]。
"""
import math
from OCP.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir, gp_Circ
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.GC import GC_MakeArcOfCircle
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp


def _rrect_wire(x0, y0, x1, y1, r, z=0.0):
    """圆角矩形线框（逆时针）"""
    P = lambda x, y: gp_Pnt(x, y, z)
    mk = BRepBuilderAPI_MakeWire()
    pts = [((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)), ((x1 - r, y1), (x0 + r, y1)), ((x0, y1 - r), (x0, y0 + r))]
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    for (a, b), (cx, cy, a0) in zip(pts, corners):
        mk.Add(BRepBuilderAPI_MakeEdge(P(*a), P(*b)).Edge())
        if r > 0:
            am = math.radians(a0 + 45); a1 = math.radians(a0 + 90); a0r = math.radians(a0)
            arc = GC_MakeArcOfCircle(P(cx + r * math.cos(a0r), cy + r * math.sin(a0r)),
                                     P(cx + r * math.cos(am), cy + r * math.sin(am)),
                                     P(cx + r * math.cos(a1), cy + r * math.sin(a1))).Value()
            mk.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
    return mk.Wire()


def tube(a, b, t, L, ro=None, ri=None):
    """矩形管实体：截面 a × b、壁厚 t、长 L（沿 z）"""
    ro = 1.5 * t if ro is None else ro
    ri = 0.5 * t if ri is None else ri
    fm = BRepBuilderAPI_MakeFace(_rrect_wire(0, 0, a, b, ro))
    inner = _rrect_wire(t, t, a - t, b - t, ri)
    inner.Reverse()
    fm.Add(inner)
    return BRepPrimAPI_MakePrism(fm.Face(), gp_Vec(0, 0, L)).Shape()


def box(x0, y0, z0, x1, y1, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def slot_y(xc, zc0, zc1, w, y0, y1):
    """沿 y 贯穿的腰孔（两端圆心 z = zc0 / zc1，宽 w）"""
    r = w / 2
    s = box(xc - r, y0, zc0, xc + r, y1, zc1)
    for zc in (zc0, zc1):
        c = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(xc, y0, zc), gp_Dir(0, 1, 0)), r, y1 - y0).Shape()
        s = BRepAlgoAPI_Fuse(s, c).Shape()
    return s


def cut(s, *tools):
    for k in tools:
        s = BRepAlgoAPI_Cut(s, k).Shape()
    return s


def fuse(s, *tools):
    for k in tools:
        s = BRepAlgoAPI_Fuse(s, k).Shape()
    return s


def volume(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()


def write(shape, path, name):
    Interface_Static.SetCVal_s('write.step.schema', 'AP214')
    Interface_Static.SetCVal_s('write.step.product.name', name)
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    assert w.Write(path) == 1, path


TAB_W, TAB_L, CLR = 13.0, 3.5, 0.25          # 定位舌宽、伸出长、单边间隙（同样例）
