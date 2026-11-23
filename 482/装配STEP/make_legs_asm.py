# -*- coding: utf-8 -*-
"""NO.482 支撑腿焊接件 → 整件装配 STEP（立柱 + 横撑 + 支撑安装件 + 支撑腿件，按总图位置装好）。
11-23 用户：要装配体，不要单独的零部件（替代 管材STEP/ 下按根出的方管 STEP）。

用法（需 OCP）: python 482/装配STEP/make_legs_asm.py
坐标（照总图主视图，取自 DWG 矢量）：x 沿横撑，左立柱外面 x=0；y 沿 60 宽（A-A 视图左→右 0~60）；z 向上，地面 z=0。
- 1430022A 支撑腿件 10mm：60(y)×40(x)，R5，M16 开小径 Φ13.84，垫在立柱下 z 0~10。
- 立柱 A40×60：x 0~40（右柱 x Lb+40 ~ Lb+80），z 10 起；顶端 45° 斜切，靠横撑一侧长 L、外侧 L−40。
  壁厚：左 2mm、右 3mm（主视图隐藏线）；1611203A00 两根都是 2mm。
- 横撑 40×40×2：45° 菱形放，平头顶在两立柱内面之间，截面中心 y=30、z=40（1610108A00 z=340）。
- 支撑安装件 5mm：斜段贴在立柱斜切面上，竖段 x 38~43（超出立柱内面 3，两件竖段内面距 = 横撑长 − 6），
  竖段内交点到顶 140（1611203A00 为 100），斜段外端 x=−4；折弯按尖角建（不影响下料，下料按展开图）。
- 孔：立柱 Φ9 沿 y 贯穿，距底面（地面）38 / 65、x=20（1611203A00 无）；1610108A00 立柱 2-Φ6.647（M8 小径）
  沿 x 贯穿，z=400、y=20 / 40。
管材圆角按材料规则（SUS304 外 R = 1.2t、内 R = 外 − t），图纸上的 R 不用。
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from frame3d import tube, keep, cut, cyl, box, prism, plate, volume, bbox, valid, write_assembly
from OCP.gp import gp_Trsf, gp_Ax1, gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

RHO = 7.93e-6
S2 = math.sqrt(0.5)


def xform(s, tr):
    return BRepBuilderAPI_Transform(s, tr, True).Shape()


def mirror_x(s, xm):
    tr = gp_Trsf(); tr.SetMirror(gp_Ax2(gp_Pnt(xm, 0, 0), gp_Dir(1, 0, 0)))
    return xform(s, tr)


def foot(x0):
    return plate('z', (x0, 0, 0), (x0 + 40, 60, 10), 5, [(x0 + 20, 30, 13.84)])


def post(t, L, holes9=True, m8=False):
    """左立柱（外面 x=0）"""
    s = tube('z', (0, 0, 10), (40, 60, 10 + L), t)
    s = keep(s, (40, 0, 10 + L), (S2, 0, -S2))            # 保留 z ≤ 10+L−40+x
    if holes9:
        for z in (38, 65):
            s = cut(s, cyl('y', (20, 0, z), 9, -1, 61))
    if m8:
        for y in (20, 40):
            s = cut(s, cyl('x', (0, y, 400), 6.647, -1, 41))
    return s


def rail(Lb, zc):
    """横撑：x 40 ~ 40+Lb，菱形（绕 x 转 45°），截面中心 (y30, z zc)"""
    s = tube('x', (40, 10, zc - 20), (40 + Lb, 50, zc + 20), 2)
    tr = gp_Trsf(); tr.SetRotation(gp_Ax1(gp_Pnt(0, 30, zc), gp_Dir(1, 0, 0)), math.radians(45))
    return xform(s, tr)


def bracket_body(L, V):
    """左支撑安装件的折弯外形（尖角），沿 y 0~60。L = 立柱长，V = 竖段内交点到顶"""
    H = 10 + L
    zl = lambda x: H - 40 + x                              # 立柱斜切面
    d = 5 * S2
    a = -4 + d                                             # 斜段外端（下表面）x
    zu38 = zl(38) + 5 / S2                                 # 竖段内面与斜段上表面交点
    ztop = zu38 + V
    pts = [(a, zl(a)), (43, zl(43)), (43, ztop), (38, ztop), (38, zu38), (-4, zl(a) + d)]
    segs = [('L', pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    return prism(segs, [], ('x', 'z'), 0, 60), ztop        # plane (x,z) 法向 y，从 y=0 拉 60


def poly_x(pts, x0=30, x1=50):
    """yz 平面多边形沿 x 拉伸（切除用）"""
    segs = [('L', pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    return prism(segs, [], ('y', 'z'), x0, x1 - x0)


def arc_slot(zc, R=90, w=10.5, da=5):
    """R90 圆弧腰孔（圆心 y30 / z zc，±5°，宽 w），中间叠 Φ11"""
    hw = w / 2
    P = lambda r, ang: (30 + r * math.cos(math.radians(ang)), zc + r * math.sin(math.radians(ang)))
    ro, ri = R + hw, R - hw
    a0, a1 = 90 - da, 90 + da
    e0, e1 = P(R, a0), P(R, a1)
    ext = lambda c, ang: (c[0] + hw * math.cos(math.radians(ang)), c[1] + hw * math.sin(math.radians(ang)))
    segs = [('A', P(ro, a0), P(ro, 90), P(ro, a1)),
            ('A', P(ro, a1), ext(e1, a1 + 90), P(ri, a1)),
            ('A', P(ri, a1), P(ri, 90), P(ri, a0)),
            ('A', P(ri, a0), ext(e0, a0 - 90), P(ro, a0))]
    s = prism(segs, [], ('y', 'z'), 30, 20)
    return cut_union(s, cyl('x', (0, 30, zc + R), 11, 30, 50))


def cut_union(a, b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    return BRepAlgoAPI_Fuse(a, b).Shape()


def bracket_157(L, yn=81, yw=91, holes=(103,)):
    """1570904A01 / 1460104A01：竖段上部 40 宽居中（到顶 yn），45° 过渡到 60 宽（到顶 yw）；
    Φ11 距顶 holes，R90 弧形腰孔以距顶 103 的孔为圆心"""
    s, zt = bracket_body(L, 140)
    s = cut(s, poly_x([(-1, zt - yw - 1), (10, zt - yn), (10, zt + 1), (-1, zt + 1)]),
            poly_x([(61, zt - yw - 1), (50, zt - yn), (50, zt + 1), (61, zt + 1)]))
    for r in (box((30, 10, zt - 5), (50, 15, zt + 1)), box((30, 45, zt - 5), (50, 50, zt + 1))):
        s = cut(s, r)                                      # 顶角 R5
    s = cut_union(s, cyl('x', (0, 15, zt - 5), 10, 38, 43))
    s = cut_union(s, cyl('x', (0, 45, zt - 5), 10, 38, 43))
    for h in holes:
        s = cut(s, cyl('x', (0, 30, zt - h), 11, 30, 50))
    return cut(s, arc_slot(zt - 103)), zt


def bracket_1432114(L):
    """1432114A03：竖段到顶 100；上部只留 y 0~30（到顶 38），45° 过渡到 60 宽（到顶 69）；
    y=13 两条竖腰孔（距顶 13~23、68~78，宽 11），y=47 Φ11 距顶 73"""
    s, zt = bracket_body(L, 100)
    s = cut(s, poly_x([(30, zt + 1), (30, zt - 38), (61, zt - 69), (61, zt + 1)]))
    for z0, z1 in ((13, 23), (68, 78)):
        s = cut(s, cyl('x', (0, 13, zt - z0), 11, 30, 50), cyl('x', (0, 13, zt - z1), 11, 30, 50),
                box((30, 7.5, zt - z1), (50, 18.5, zt - z0)))
    return cut(s, cyl('x', (0, 47, zt - 73), 11, 30, 50)), zt


def leg(posts, Lb, zc=40, holes9=True, m8=False, kind='157', tab=None):
    """posts = [(左壁厚, 左长), (右壁厚, 右长)]（单腿只给一个）；返回 [(名, shape)]"""
    parts = []
    xm = (80 + Lb) / 2
    tab = tab or {}
    for i, (t, L) in enumerate(posts):
        p = post(t, L, holes9, m8)
        if kind == '157':
            b, _ = bracket_157(L, **{k: v for k, v in tab.items() if k != 'name'})
            bname = tab.get('name', '1570904A01-支撑安装件-5')
        else:
            b, _ = bracket_1432114(L)
            bname = '1432114A0%d-支撑安装件-5' % (3 + i)
        f = foot(0)
        if i == 1:
            p, b, f = mirror_x(p, xm), mirror_x(b, xm), mirror_x(f, xm)
        parts += [('方管A40x60x%d-L%d-45' % (t, L), p), (bname, b), ('1430022A-支撑腿件-10', f)]
    if Lb:
        parts.append(('方管40x40x2-L%d' % Lb, rail(Lb, zc)))
    return parts


A01 = dict(name='1460104A01-支撑安装件-5', yn=100, yw=110, holes=(48, 103))
JOBS = [
    # (物料号, 套数, 零件, 明细栏总重 kg)
    ('1610108A00', 6, leg([(2, 951), (3, 951)], 526, zc=340, holes9=False, m8=True), 4.11 + 1.26 + 2.79 + 0.81 + 0.36),
    ('1610323A00', 8, leg([(2, 323), (3, 323)], 346), 1.34 + 0.91 + 0.81 + 0.81 + 0.36),
    ('1610330A00', 2, leg([(2, 323), (3, 323)], 411), 1.34 + 0.91 + 0.96 + 0.81 + 0.36),
    ('1610335A00', 2, leg([(2, 323)], 0), 1.486),
    ('1610629A00', 2, leg([(2, 323), (3, 323)], 611), 1.34 + 0.91 + 0.81 + 0.36 + 1.43),
    ('1610707A00', 4, leg([(2, 302), (3, 318)], 441, tab=A01), 1.31 + 0.84 + 1.03 + 0.36 + 0.77),
    ('1611203A00', 2, leg([(2, 288), (2, 288)], 536, holes9=False, kind='1432114'), 3.831),
]


def main(only=None, out=HERE, counts=None):
    for code, n, parts, bom in JOBS:
        if only and code not in only:
            continue
        n = (counts or {}).get(code, n)
        name = '%s-支撑腿-装配-%d套' % (code, n)
        kg = 0
        for nm, s in parts:
            assert valid(s), (code, nm)
            kg += volume(s) * RHO
        write_assembly(parts, os.path.join(out, name + '.step'), name)
        print('%-34s %d 件  算重 %.2f kg  明细栏 %.2f  差 %+.1f%%' % (name, len(parts), kg, bom, (kg / bom - 1) * 100))


if __name__ == '__main__':
    main()
    # 钣金2 单：1610629A00 2 套（同图）
    d = os.path.join(HERE, '钣金2'); os.makedirs(d, exist_ok=True)
    main(['1610629A00'], d)
