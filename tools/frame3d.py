# -*- coding: utf-8 -*-
"""按二维图建焊接框架三维模型（矩形管 / C 形钣金 / 平板），导出带零件名的装配 STEP。

需 OCP（cadquery-ocp）。所有零件直接在总装坐标系里建（轴向对齐的包围盒 + 斜切平面），
便于逐条对照二维图的视图坐标。
"""
import math
from OCP.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Pln, gp_Ax2
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeHalfSpace
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.GC import GC_MakeArcOfCircle
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDataStd import TDataStd_Name
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.BRepCheck import BRepCheck_Analyzer

AX = {'x': 0, 'y': 1, 'z': 2}


def _wire2d(segs, plane, w0):
    """segs: [('L', (u0,v0), (u1,v1)) | ('A', (u0,v0), (um,vm), (u1,v1))]，plane = (轴u, 轴v)，w0 = 法向坐标"""
    iu, iv = AX[plane[0]], AX[plane[1]]
    iw = 3 - iu - iv

    def P(u, v):
        c = [0.0, 0.0, 0.0]; c[iu] = u; c[iv] = v; c[iw] = w0
        return gp_Pnt(*c)
    mk = BRepBuilderAPI_MakeWire()
    for s in segs:
        if s[0] == 'L':
            mk.Add(BRepBuilderAPI_MakeEdge(P(*s[1]), P(*s[2])).Edge())
        else:
            mk.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(P(*s[1]), P(*s[2]), P(*s[3])).Value()).Edge())
    return mk.Wire()


def rrect(u0, v0, u1, v1, r):
    """圆角矩形（逆时针）分段"""
    if r <= 0:
        return [('L', (u0, v0), (u1, v0)), ('L', (u1, v0), (u1, v1)), ('L', (u1, v1), (u0, v1)), ('L', (u0, v1), (u0, v0))]
    k = r * (1 - math.sqrt(0.5))
    return [('L', (u0 + r, v0), (u1 - r, v0)), ('A', (u1 - r, v0), (u1 - k, v0 + k), (u1, v0 + r)),
            ('L', (u1, v0 + r), (u1, v1 - r)), ('A', (u1, v1 - r), (u1 - k, v1 - k), (u1 - r, v1)),
            ('L', (u1 - r, v1), (u0 + r, v1)), ('A', (u0 + r, v1), (u0 + k, v1 - k), (u0, v1 - r)),
            ('L', (u0, v1 - r), (u0, v0 + r)), ('A', (u0, v0 + r), (u0 + k, v0 + k), (u0 + r, v0))]


def prism(outer, holes, plane, w0, L):
    """二维截面（plane 内，法向坐标 w0）沿法向拉伸 L"""
    fm = BRepBuilderAPI_MakeFace(_wire2d(outer, plane, w0))
    for h in holes:
        w = _wire2d(h, plane, w0); w.Reverse(); fm.Add(w)
    iw = 3 - AX[plane[0]] - AX[plane[1]]
    v = [0.0, 0.0, 0.0]; v[iw] = L
    return BRepPrimAPI_MakePrism(fm.Face(), gp_Vec(*v)).Shape()


def tube(axis, lo, hi, t, ro, ri):
    """矩形管：轴向 axis，占据包围盒 lo ~ hi（三个坐标），壁厚 t，外角 ro、内角 ri"""
    ia = AX[axis]
    pl = [k for k in 'xyz' if k != axis]
    iu, iv = AX[pl[0]], AX[pl[1]]
    o = rrect(lo[iu], lo[iv], hi[iu], hi[iv], ro)
    i = rrect(lo[iu] + t, lo[iv] + t, hi[iu] - t, hi[iv] - t, ri)
    return prism(o, [i], (pl[0], pl[1]), lo[ia], hi[ia] - lo[ia])


def plate(axis, lo, hi, r, holes=()):
    """平板：法向 axis，包围盒 lo ~ hi，四角 R r，holes = [(u, v, d)]（另两轴坐标）"""
    ia = AX[axis]
    pl = [k for k in 'xyz' if k != axis]
    iu, iv = AX[pl[0]], AX[pl[1]]
    hs = []
    for u, v, d in holes:
        q = d / 2; k = q * math.sqrt(0.5)
        hs.append([('A', (u + q, v), (u, v + q), (u - q, v)), ('A', (u - q, v), (u, v - q), (u + q, v))])
    return prism(rrect(lo[iu], lo[iv], hi[iu], hi[iv], r), hs, (pl[0], pl[1]), lo[ia], hi[ia] - lo[ia])


def keep(shape, point, normal):
    """只保留 (p − point)·normal ≥ 0 的部分（斜切）"""
    n = gp_Dir(*normal)
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*point), n)).Face()
    ref = gp_Pnt(point[0] - normal[0] * 1000, point[1] - normal[1] * 1000, point[2] - normal[2] * 1000)
    hs = BRepPrimAPI_MakeHalfSpace(face, ref).Solid()
    return BRepAlgoAPI_Cut(shape, hs).Shape()


def cut(shape, *tools):
    for t in tools:
        shape = BRepAlgoAPI_Cut(shape, t).Shape()
    return shape


def box(lo, hi):
    return BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Shape()


def cyl(axis, c, d, a0, a1):
    """圆柱（孔用）：轴向 axis，过点 c（另两轴坐标取 c），轴向从 a0 到 a1"""
    p = list(c); p[AX[axis]] = a0
    dv = [0.0, 0.0, 0.0]; dv[AX[axis]] = 1
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*p), gp_Dir(*dv)), d / 2, a1 - a0).Shape()


def slot(axis, c0, c1, w, a0, a1):
    """腰孔体：沿 axis 贯穿（a0~a1），两端圆心 c0、c1（三维点，axis 分量忽略），宽 w"""
    s = BRepAlgoAPI_Fuse(cyl(axis, c0, w, a0, a1), cyl(axis, c1, w, a0, a1)).Shape()
    lo = [min(c0[i], c1[i]) for i in range(3)]; hi = [max(c0[i], c1[i]) for i in range(3)]
    ia = AX[axis]
    for i in range(3):
        if i == ia:
            lo[i], hi[i] = a0, a1
        elif abs(c0[i] - c1[i]) < 1e-9:
            lo[i] -= w / 2; hi[i] += w / 2
    return BRepAlgoAPI_Fuse(s, box(lo, hi)).Shape()


def volume(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()


def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, True); a, c = b.CornerMin(), b.CornerMax()
    return [round(v, 2) for v in (a.X(), a.Y(), a.Z(), c.X(), c.Y(), c.Z())]


def valid(s):
    return BRepCheck_Analyzer(s).IsValid()


def write_assembly(parts, path, name):
    """parts: [(零件名, shape)] → 一个 STEP，每个零件一个带名字的实体"""
    doc = TDocStd_Document(TCollection_ExtendedString('XmlOcaf'))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    top = st.NewShape()
    TDataStd_Name.Set_s(top, TCollection_ExtendedString(name))
    for nm, s in parts:
        lab = st.AddShape(s, False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(nm))
        from OCP.TopLoc import TopLoc_Location
        comp = st.AddComponent(top, lab, TopLoc_Location())
        TDataStd_Name.Set_s(comp, TCollection_ExtendedString(nm))
    st.UpdateAssemblies()
    Interface_Static.SetCVal_s('write.step.schema', 'AP214')
    w = STEPCAFControl_Writer()
    w.SetNameMode(True)
    assert w.Transfer(doc, STEPControl_AsIs)
    assert int(w.Write(path)) == 1, path
    fix_step_names(path)


def fix_step_names(path):
    """OCC 把中文名的 UTF-8 字节当 Latin-1 再编码了一次；改写为 STEP 标准的 \\X2\\…\\X0\\（UTF-16）"""
    import re
    raw = open(path, 'rb').read().decode('utf-8')

    def enc(s):
        try:
            s = s.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        out, buf = [], ''
        for ch in s:
            if ord(ch) < 128:
                if buf:
                    out.append('\\X2\\' + buf.encode('utf-16-be').hex().upper() + '\\X0\\'); buf = ''
                out.append(ch)
            else:
                buf += ch
        if buf:
            out.append('\\X2\\' + buf.encode('utf-16-be').hex().upper() + '\\X0\\')
        return ''.join(out)
    fixed = re.sub(r"'([^']*[^\x00-\x7f][^']*)'", lambda m: "'" + enc(m.group(1)) + "'", raw)
    open(path, 'wb').write(fixed.encode('ascii'))
