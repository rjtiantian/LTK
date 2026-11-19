# -*- coding: utf-8 -*-
"""焊接件轴测图：STEP → 消隐后的可见线（等轴测，Y 向上，同 SolidWorks「等轴测」），给下料图焊件列当装配参考。

iso_lines(step) -> {'w','h','prims':[[层, 'L'|'E', 数据], ...]}   原点在左下，单位 mm，1:1
  层 'v' → 可见 (ISO)，'n' → 可见窄的 (ISO)；L = [x0,y0,x1,y1]，E = [cx,cy,长轴x,长轴y,短长比,起,止]（同 DXF ELLIPSE）
结果按 STEP 内容的 md5 缓存在 STEP 同目录的 .iso/<名>.<md5前8>.json，重出下料图不再重算消隐。
命令行试看: python iso_view.py <step> [out.png]
"""
import os, sys, json, hashlib, math

VIEW = (1.0, 1.0, 1.0)          # 视线（从目标指向眼睛），SW 等轴测
UP = (0.0, 1.0, 0.0)


def _load(step):
    from OCP.STEPControl import STEPControl_Reader
    r = STEPControl_Reader()
    if r.ReadFile(step) != 1:
        raise RuntimeError('读不了 STEP: ' + step)
    r.TransferRoots()
    return r.OneShape()


def _edges(comp, lay, tol, out):
    """HLR 结果的边 → 图元：直线 LINE、圆 / 椭圆 ELLIPSE（同 SolidWorks 出的轴测图），其它曲线折成短 LINE"""
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Circle, GeomAbs_Ellipse
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    if comp is None or comp.IsNull():
        return
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More():
        try:
            c = BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
            u0, u1 = c.FirstParameter(), c.LastParameter()
            k = c.GetType()
            if k == GeomAbs_Line:
                p, q = c.Value(u0), c.Value(u1)
                out.append([lay, 'L', [p.X(), p.Y(), q.X(), q.Y()]])
            elif k in (GeomAbs_Circle, GeomAbs_Ellipse):
                g = c.Circle() if k == GeomAbs_Circle else c.Ellipse()
                ra, rb = (g.Radius(), g.Radius()) if k == GeomAbs_Circle else (g.MajorRadius(), g.MinorRadius())
                pos = g.Position(); o = pos.Location(); xd = pos.XDirection()
                if pos.Direction().Z() < 0:              # 轴朝 -Z：参数方向反过来
                    u0, u1 = -u1, -u0
                out.append([lay, 'E', [o.X(), o.Y(), xd.X() * ra, xd.Y() * ra, rb / ra, u0, u1]])
            else:
                d = GCPnts_QuasiUniformDeflection(c, tol)
                pts = [(d.Value(i).X(), d.Value(i).Y()) for i in range(1, d.NbPoints() + 1)] if d.IsDone() else []
                for a, b in zip(pts, pts[1:]):
                    out.append([lay, 'L', [a[0], a[1], b[0], b[1]]])
        except Exception:
            pass
        ex.Next()


def _bbox(prims):
    import math
    xs, ys = [], []
    for _, k, d in prims:
        if k == 'L':
            xs += [d[0], d[2]]; ys += [d[1], d[3]]
        else:
            cx, cy, mx, my, r, a0, a1 = d
            nx, ny = -my * r, mx * r
            n = max(8, int(abs(a1 - a0) / 0.05))
            for i in range(n + 1):
                t = a0 + (a1 - a0) * i / n
                xs.append(cx + mx * math.cos(t) + nx * math.sin(t)); ys.append(cy + my * math.cos(t) + ny * math.sin(t))
    return min(xs), min(ys), max(xs), max(ys)


def compute(step, tol=0.05):
    """返回 {'w','h','prims':[[层, 'L'|'E', 数据], ...]}，原点在左下。层 'v' = 可见 (ISO)（尖角边 + 轮廓线），'n' = 可见窄的 (ISO)（相切边）"""
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    shape = _load(step)
    v = gp_Dir(*VIEW)
    xd = gp_Dir(*UP).Crossed(v)                          # 屏幕 X = up × view
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), v, xd)))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    prims = []
    _edges(h.VCompound(), 'v', tol, prims)
    _edges(h.OutLineVCompound(), 'v', tol, prims)
    _edges(h.Rg1LineVCompound(), 'n', tol, prims)
    if not prims:
        raise RuntimeError('消隐没有结果: ' + step)
    x0, y0, x1, y1 = _bbox(prims)
    for p in prims:
        d = p[2]
        if p[1] == 'L':
            p[2] = [round(d[0] - x0, 3), round(d[1] - y0, 3), round(d[2] - x0, 3), round(d[3] - y0, 3)]
        else:
            p[2] = [round(d[0] - x0, 3), round(d[1] - y0, 3)] + [round(x, 6) for x in d[2:]]
    return dict(w=round(x1 - x0, 2), h=round(y1 - y0, 2), prims=prims)


def iso_lines(step):
    md5 = hashlib.md5(open(step, 'rb').read()).hexdigest()[:8]
    cdir = os.path.join(os.path.dirname(step), '.iso')
    cf = os.path.join(cdir, '%s.%s.v2.json' % (os.path.splitext(os.path.basename(step))[0], md5))
    if os.path.exists(cf):
        return json.load(open(cf))
    r = compute(step)
    os.makedirs(cdir, exist_ok=True)
    json.dump(r, open(cf, 'w'))
    return r


LAYERS = {'v': '可见 (ISO)', 'n': '可见窄的 (ISO)'}


def add_prims(layout, prims, dx=0.0, dy=0.0):
    """把图元画进 ezdxf 的 modelspace / 块（颜色随层）"""
    for lay, k, d in prims:
        a = dict(layer=LAYERS[lay])
        if k == 'L':
            layout.add_line((d[0] + dx, d[1] + dy), (d[2] + dx, d[3] + dy), dxfattribs=a)
        elif 1e-6 < d[4] <= 1 + 1e-9:
            layout.add_ellipse((d[0] + dx, d[1] + dy), (d[2], d[3]), min(d[4], 1.0), d[5], d[6], dxfattribs=a)


if __name__ == '__main__':
    import time
    t = time.time(); r = iso_lines(sys.argv[1])
    print('w %.1f h %.1f prims %d  %.1fs' % (r['w'], r['h'], len(r['prims']), time.time() - t))
    if len(sys.argv) > 2:
        import ezdxf
        d = ezdxf.new(); m = d.modelspace(); add_prims(m, r['prims'])
        d.saveas(sys.argv[2])
