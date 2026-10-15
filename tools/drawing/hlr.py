# -*- coding: utf-8 -*-
"""STEP 模型投影（OpenCascade HLR 消隐）：返回指定视向的可见/不可见边二维折线"""
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS

# 视向：(观察方向 = 投影面法向指向观察者, 图上 X 轴方向)   模型 Y 向上（SolidWorks 默认）
VIEWS = {
    'front': ((0, 0, 1), (1, 0, 0)),     # 主视图：从 +Z 看
    'top':   ((0, 1, 0), (1, 0, 0)),     # 俯视图：从 +Y 看（第一角投影放在主视图下方）
    'left':  ((1, 0, 0), (0, 0, -1)),    # 左视图：从 +X 看（第一角投影放在主视图右方）
    'right': ((-1, 0, 0), (0, 0, 1)),
    'back':  ((0, 0, -1), (-1, 0, 0)),
    'bottom': ((0, -1, 0), (1, 0, 0)),
    'iso':   ((1, 1, 1), (1, 0, -1)),    # 正等轴测
}


def _edges(shape, defl=0.05):
    out = []
    if shape is None or shape.IsNull():
        return out
    ex = TopExp_Explorer(shape, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        c = BRepAdaptor_Curve(e)
        d = GCPnts_QuasiUniformDeflection(c, defl)
        if d.IsDone() and d.NbPoints() > 1:
            out.append([(d.Value(i).X(), d.Value(i).Y()) for i in range(1, d.NbPoints() + 1)])
        ex.Next()
    return out


def project(shape, view):
    n, xd = VIEWS[view] if isinstance(view, str) else view
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xd))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edges(h.VCompound()) + _edges(h.OutLineVCompound())
    hid = _edges(h.HCompound()) + _edges(h.OutLineHCompound())
    return vis, hid


def load(path):
    return cq.importers.importStep(path).val().wrapped
