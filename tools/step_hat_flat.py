# -*- coding: utf-8 -*-
"""帽形钣金件（顶板 + 两侧下折立板 + 外翻底脚，直线折弯）由 STEP 生成展开轮廓 JSON。

用法（需 OCP / cadquery-ocp）:  python3 tools/step_hat_flat.py <model.step> <out.json> [--t 3 --bd 5]
模型约定（SolidWorks 导出）：顶板外表面 y=0，立板沿 ±x，底脚外表面 y=-H，宽向为 z。
展开按外形尺寸法（同下料规则）：顶板 u = x；立板外形高 H；底脚上一点到立板外模线 (xo−t) 的距离 s →
u = ±(xo − BD/2 + H − BD + s − BD/2)。立板无特征时整宽直连。
输出：outline [(u, z)]（闭合）、slots [(u0, z0, u1, z1, w)]、circles [(u, z, d)]、bends [u]、width
"""
import sys, json, math, argparse
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Line, GeomAbs_Circle
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp


def load(f):
    r = STEPControl_Reader(); r.ReadFile(f); r.TransferRoots(); return r.OneShape()


def planar_faces(s):
    ex = TopExp_Explorer(s, TopAbs_FACE)
    while ex.More():
        fc = TopoDS.Face(ex.Current()); a = BRepAdaptor_Surface(fc)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane(); n = pl.Axis().Direction(); p = pl.Location()
            g = GProp_GProps(); BRepGProp.SurfaceProperties_s(fc, g)
            yield fc, (n.X(), n.Y(), n.Z()), (p.X(), p.Y(), p.Z()), g.Mass()
        ex.Next()


def wires(fc):
    outer = BRepTools.OuterWire_s(fc)
    wx = TopExp_Explorer(fc, TopAbs_WIRE)
    while wx.More():
        w = TopoDS.Wire(wx.Current())
        es = []
        ex = TopExp_Explorer(w, TopAbs_EDGE)
        while ex.More():
            c = BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
            p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
            e = dict(a=(p0.X(), p0.Z()), b=(p1.X(), p1.Z()), kind='L')
            if c.GetType() == GeomAbs_Circle:
                ci = c.Circle(); e.update(kind='C', c=(ci.Location().X(), ci.Location().Z()), r=ci.Radius())
            elif c.GetType() != GeomAbs_Line:
                e['kind'] = '?'
            es.append(e)
            ex.Next()
        yield w.IsSame(outer), es
        wx.Next()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step'); ap.add_argument('out')
    ap.add_argument('--t', type=float, default=3); ap.add_argument('--bd', type=float, default=5)
    A = ap.parse_args()
    s = load(A.step)
    faces = list(planar_faces(s))
    top = [f for f in faces if abs(f[1][1]) > 0.999 and abs(f[2][1]) < 1e-6][0][0]
    legs = [f for f in faces if abs(f[1][0]) > 0.999 and f[3] > 1000]
    xo = max(abs(f[2][0]) for f in legs)                    # 立板外表面 |x|
    feetH = sorted({round(-f[2][1], 4) for f in faces if abs(f[1][1]) > 0.999 and f[2][1] < -1})
    H = feetH[-1]                                           # 底脚外表面 y=-H
    feet = [f[0] for f in faces if abs(f[1][1]) > 0.999 and abs(f[2][1] + H) < 1e-6]
    t, bd = A.t, A.bd
    W = None
    r1 = xo - bd / 2; r2 = r1 + H - bd
    dfoot = r2 - bd / 2 - (xo - t)                          # 底脚：u = |x| + dfoot
    segs, slots, circles = [], [], []
    xt_top = None
    for outer, es in wires(top):
        assert outer, '顶板有内孔，需补充处理'
        xt_top = max(max(abs(e['a'][0]), abs(e['b'][0])) for e in es)
        for e in es:
            assert e['kind'] == 'L'
            if abs(abs(e['a'][0]) - xt_top) < 1e-3 and abs(abs(e['b'][0]) - xt_top) < 1e-3:
                continue                                    # 折弯切线
            segs.append((e['a'], e['b']))
        zs = [z for e in es for z in (e['a'][1], e['b'][1])]
        W = (min(zs), max(zs))
    fu = lambda x: math.copysign(abs(x) + dfoot, x)
    for fc in feet:
        for outer, es in wires(fc):
            if outer:
                xt = min(min(abs(e['a'][0]), abs(e['b'][0])) for e in es)
                for e in es:
                    a, b = e['a'], e['b']
                    if abs(abs(a[0]) - xt) < 1e-3 and abs(abs(b[0]) - xt) < 1e-3:
                        continue                            # 折弯切线
                    if abs(a[1] - b[1]) < 1e-6 and abs(abs(a[1]) - W[1]) < 1e-6 and min(abs(a[0]), abs(b[0])) - xt < 1e-3:
                        continue                            # 切线到模线的小段，由宽边直连代替
                    P = [list(a), list(b)]
                    for i in (0, 1):                        # 斜切线止于切线处（未到宽边）：沿直线延伸到宽边
                        if abs(abs(P[i][0]) - xt) < 1e-3 and abs(abs(P[i][1]) - W[1]) > 1e-6:
                            j = 1 - i
                            zt = math.copysign(W[1], P[i][1])
                            k = (zt - P[j][1]) / (P[i][1] - P[j][1])
                            P[i] = [P[j][0] + k * (P[i][0] - P[j][0]), zt]
                    segs.append(((fu(P[0][0]), P[0][1]), (fu(P[1][0]), P[1][1])))
            else:
                lines = [e for e in es if e['kind'] == 'L']
                arcs = [e for e in es if e['kind'] == 'C']
                r = arcs[0]['r']
                cs = sorted({(round(e['c'][0], 4), round(e['c'][1], 4)) for e in arcs})
                if len(cs) == 2:
                    (x0, z0), (x1, z1) = cs
                    slots.append((fu(x0), z0, fu(x1), z1, 2 * r))
                else:
                    circles.append((fu(cs[0][0]), cs[0][1], 2 * r))
    # 宽边直连：两侧 z = W 上，从顶板切线端到底脚最内点
    for sgn in (1, -1):
        for zt in W:
            pts = [p for sg in segs for p in sg if abs(p[1] - zt) < 1e-6 and p[0] * sgn > 0]
            near = min(pts, key=lambda p: abs(p[0]))
            far = [p for p in pts if abs(p[0]) > xt_top + 1]
            if not far:
                raise SystemExit('宽边 z=%g 侧 %d 找不到底脚端点' % (zt, sgn))
            segs.append(((sgn * xt_top, zt), min(far, key=lambda p: abs(p[0]))))
    # 串成闭合轮廓
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append(b); adj.setdefault(key(b), []).append(a)
    odd = [k for k, v in adj.items() if len(v) != 2]
    if odd:
        raise SystemExit('轮廓未闭合: %s' % odd[:6])
    start = segs[0][0]; poly = [start]; prev = None; cur = start
    while True:
        nxt = [q for q in adj[key(cur)] if prev is None or key(q) != key(prev)]
        q = nxt[0]
        if key(q) == key(start):
            break
        poly.append(q); prev, cur = cur, q
    # 去掉共线点
    out = []
    n = len(poly)
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-6:
            out.append([round(b[0], 4), round(b[1], 4)])
    json.dump(dict(source=A.step.split('/')[-1], t=t, bd=bd, xo=xo, H=H, width=W,
                   bends=[-r2, -r1, r1, r2], outline=out, slots=slots, circles=circles),
              open(A.out, 'w'), ensure_ascii=False, indent=1)
    us = [p[0] for p in out]
    print('展开 %.2f × %.2f，轮廓 %d 点，腰孔 %d，圆孔 %d，红线 %s' %
          (max(us) - min(us), W[1] - W[0], len(out), len(slots), len(circles), [round(v, 2) for v in (-r2, -r1, r1, r2)]))


if __name__ == '__main__':
    main()
