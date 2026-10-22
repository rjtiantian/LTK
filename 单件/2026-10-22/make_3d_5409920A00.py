# -*- coding: utf-8 -*-
"""5409920A00 两步梯 三维模型（STEP 装配），几何取总装图 DWG 矢量（主视 / 俯视 / 侧视，1:1）。

用法（需 OCP）:  python3 单件/2026-10-22/make_3d_5409920A00.py → 单件/2026-10-22/5409920A00_两步梯.step
坐标：x 沿主视宽 0~600（x=0 为高台一侧）、y 向上（y=0 为脚板底面）、z 沿侧视宽 0~400。
方管与 管材STEP 完全相同（make_tubes.step2：Q235B 圆角 1.5t、插接定位舌 / 缺口）；
板件：5363402A02 上踏板 3mm（x 0~300，y 580~583，R10）、5363402A01 下踏板 3mm（x 300~600，y 290~293，R10，
x=300 边 z 40~360 下折 25，内 R3 外 R6，两侧 3 × 7.5 释放口）、5363401A01 连接板 8mm ×4（80×40，内端 R5，10 宽腰孔）。
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from frame3d import prism, rrect, cut, box, slot, volume, bbox, valid, write_assembly
from make_tubes import step2
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Common

S2 = math.sqrt(0.5)


def plate_xz(outline, y0, t, holes=()):
    """水平板：outline 为 xz 面内分段（u = x, v = z），底面 y0，厚 t"""
    return prism(outline, list(holes), ('x', 'z'), y0, t)


def poly_r(pts):
    """[(u, v, r)] 圆角多边形 → 分段（圆角用三点弧）"""
    n = len(pts); segs = []; corners = []
    for i, (u, v, r) in enumerate(pts):
        pu, pv = pts[i - 1][:2]; nu, nv = pts[(i + 1) % n][:2]
        if r <= 0:
            corners.append(((u, v), (u, v), None)); continue
        a = (pu - u, pv - v); la = math.hypot(*a); a = (a[0] / la, a[1] / la)
        b = (nu - u, nv - v); lb = math.hypot(*b); b = (b[0] / lb, b[1] / lb)
        ang = math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1])))
        d = r / math.tan(ang / 2)
        p0 = (u + a[0] * d, v + a[1] * d); p1 = (u + b[0] * d, v + b[1] * d)
        bis = (a[0] + b[0], a[1] + b[1]); lbis = math.hypot(*bis); bis = (bis[0] / lbis, bis[1] / lbis)
        c = (u + bis[0] * r / math.sin(ang / 2), v + bis[1] * r / math.sin(ang / 2))
        m = (c[0] - bis[0] * r, c[1] - bis[1] * r)
        corners.append((p0, p1, m))
    for i in range(n):
        p0, p1, m = corners[i]
        if m is not None:
            segs.append(('A', p0, m, p1))
        q0 = corners[(i + 1) % n][0]
        if math.dist(p1, q0) > 1e-9:
            segs.append(('L', p1, q0))
    return segs


def build():
    P = list(step2())
    # 5363402A02 上踏板
    P.append(('5363402A02 花纹板 上踏板 (3)', plate_xz(poly_r([(0, 0, 10), (300, 0, 10), (300, 400, 10), (0, 400, 10)]), 580, 3)))
    # 5363402A01 下踏板：板（x=300 边在 z 40~360 让出折弯区）+ 折边 L 截面（xy 面，沿 z 40~360）
    top = plate_xz(poly_r([(300, 0, 10), (600, 0, 10), (600, 400, 10), (300, 400, 10),
                           (300, 363, 0), (307.5, 363, 0), (307.5, 360, 0), (306, 360, 0),
                           (306, 40, 0), (307.5, 40, 0), (307.5, 37, 0), (300, 37, 0)]), 290, 3)
    k3, k6 = 3 * S2, 6 * S2
    sec = [('L', (300, 268), (303, 268)), ('L', (303, 268), (303, 287)),
           ('A', (303, 287), (306 - k3, 287 + k3), (306, 290)), ('L', (306, 290), (307.5, 290)),
           ('L', (307.5, 290), (307.5, 293)), ('L', (307.5, 293), (306, 293)),
           ('A', (306, 293), (306 - k6, 287 + k6), (300, 287)), ('L', (300, 287), (300, 268))]
    flange = prism(sec, [], ('x', 'y'), 40, 320)          # 截面在 xy 面，沿 z 从 40 拉到 360
    P.append(('5363402A01 花纹板 下踏板 (2)', BRepAlgoAPI_Fuse(top, flange).Shape()))
    # 5363401A01 连接板 8mm ×4：后腿下 x 0~80（R5 在 x=80 端），前腿下 x 520~600（R5 在 x=520 端）
    for x0, x1, inner in ((0, 80, 80), (520, 600, 520)):
        for z0 in (0, 360):
            if inner == x1:
                pts = [(x0, z0, 0), (x1, z0, 5), (x1, z0 + 40, 5), (x0, z0 + 40, 0)]
                sc = (x1 - 27, x1 - 13)
            else:
                pts = [(x0, z0, 5), (x1, z0, 0), (x1, z0 + 40, 0), (x0, z0 + 40, 5)]
                sc = (x0 + 13, x0 + 27)
            p = plate_xz(poly_r(pts), 0, 8)
            p = cut(p, slot('y', (sc[0], 0, z0 + 20), (sc[1], 0, z0 + 20), 10, -1, 9))
            P.append(('5363401A01 连接板 x%d z%d (1)' % (x0, z0), p))
    return P


if __name__ == '__main__':
    P = build()
    for nm, s in P:
        assert valid(s), nm
    bad = 0
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            a, b = bbox(P[i][1]), bbox(P[j][1])
            if all(a[k] < b[k + 3] - 1e-6 and b[k] < a[k + 3] - 1e-6 for k in range(3)):
                v = volume(BRepAlgoAPI_Common(P[i][1], P[j][1]).Shape())
                if v > 0.01:
                    bad += 1; print('干涉 %.2f mm3：%s × %s' % (v, P[i][0], P[j][0]))
    out = os.path.join(HERE, '5409920A00_两步梯.step')
    write_assembly(P, out, '5409920A00 两步梯')
    tot = sum(volume(s) for _, s in P)
    print('5409920A00 两步梯：%d 件，干涉 %d，总质量 %.2f kg（7.85） → %s' % (len(P), bad, tot * 7.85e-6, out))
    for nm, s in P[-7:]:
        print('  %-28s 体积 %8.0f  %s' % (nm, volume(s), bbox(s)))
