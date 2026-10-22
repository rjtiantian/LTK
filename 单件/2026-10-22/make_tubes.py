# -*- coding: utf-8 -*-
"""5363401A00 一步梯、5409920A00 两步梯 方管 STEP（交管材激光）+ 7390202A 空心管。

用法（需 OCP）:  python3 单件/2026-10-22/make_tubes.py  → 单件/2026-10-22/管材STEP/*.step、管材STEP/装配核对/*.step
几何取 DWG 矢量（总装图主视 / 俯视 / 侧视，1:1）：x 沿主视宽、y 向上（y=0 为脚板底面）、z 沿侧视宽。
做法同客户样例 支架1：空心方管，圆角按材料规则（Q235B 外 R = 1.5t、内 R = 外 R − t → 40×40×1.5 R2.25 / R0.75）；
横撑与立柱插接定位：横撑贴立柱外侧的那面管壁两端各伸出定位舌 13 × 3.5，立柱对应管角开 13.5 × 3.75 缺口
（横向深 t + 1.45，避开内圆角；同样例单边间隙 0.25）。其余对接（立柱顶框架、框架压立柱）为平头。
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from frame3d import tube, keep, cut, box, volume, bbox, valid, write_assembly, prism
from tube_step import TAB_W, TAB_L, CLR
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

S2 = math.sqrt(0.5)
OUT = os.path.join(HERE, '管材STEP')
CHK = os.path.join(OUT, '装配核对')
os.makedirs(CHK, exist_ok=True)
T = 1.5
NW = TAB_W + 2 * CLR                 # 立柱缺口宽 13.5
ND = TAB_L + CLR                     # 立柱缺口深（沿横撑方向）3.75
NA = T + 1.45                        # 立柱缺口横向深（从外侧面起）


def fuse(s, *tools):
    for k in tools:
        s = BRepAlgoAPI_Fuse(s, k).Shape()
    return s


def tq(axis, lo, hi):
    return tube(axis, lo, hi, T, mat='Q235B')


def rail_x(x0, x1, y0, z0, flush, tabs=(True, True)):
    """沿 x 的横撑（截面 y0~y0+40、z0~z0+40），flush = 贴立柱外侧的管壁所在 z 面（z0 或 z0+40）"""
    s = tq('x', (x0, y0, z0), (x1, y0 + 40, z0 + 40))
    zc = (z0, z0 + T) if flush == z0 else (z0 + 40 - T, z0 + 40)
    yc = y0 + 20
    if tabs[0]:
        s = fuse(s, box((x0 - TAB_L, yc - TAB_W / 2, zc[0]), (x0, yc + TAB_W / 2, zc[1])))
    if tabs[1]:
        s = fuse(s, box((x1, yc - TAB_W / 2, zc[0]), (x1 + TAB_L, yc + TAB_W / 2, zc[1])))
    return s


def rail_z(z0, z1, y0, x0, flush, tabs=(True, True)):
    s = tq('z', (x0, y0, z0), (x0 + 40, y0 + 40, z1))
    xc = (x0, x0 + T) if flush == x0 else (x0 + 40 - T, x0 + 40)
    yc = y0 + 20
    if tabs[0]:
        s = fuse(s, box((xc[0], yc - TAB_W / 2, z0 - TAB_L), (xc[1], yc + TAB_W / 2, z0)))
    if tabs[1]:
        s = fuse(s, box((xc[0], yc - TAB_W / 2, z1), (xc[1], yc + TAB_W / 2, z1 + TAB_L)))
    return s


def notch(post, face_axis, face, out_axis, out, yc):
    """立柱管角缺口：face_axis/face = 横撑顶住的立柱面（坐标），out_axis/out = 立柱外侧面（坐标）"""
    lo, hi = [0, yc - NW / 2, 0], [0, yc + NW / 2, 0]
    ia = {'x': 0, 'z': 2}
    i, j = ia[face_axis], ia[out_axis]
    # 沿横撑方向：从接触面向立柱内 ND；横向：从外侧面向内 NA（各多切 1 以免共面）
    b = bbox(post)
    sgn_f = 1 if abs(face - b[i]) < abs(face - b[i + 3]) else -1           # 接触面是立柱的 min 面 → 向 + 切
    lo[i], hi[i] = (face - 1, face + ND) if sgn_f > 0 else (face - ND, face + 1)
    sgn_o = 1 if abs(out - b[j]) < abs(out - b[j + 3]) else -1
    lo[j], hi[j] = (out - 1, out + NA) if sgn_o > 0 else (out - NA, out + 1)
    return cut(post, box(tuple(lo), tuple(hi)))


def frame_miter(xs, zs, y0, X0, X1, Z0, Z1):
    """上框架：x 向管（z0~z0+40，两端斜接）+ z 向管（x0~x0+40，两端斜接），外框 X0~X1 × Z0~Z1"""
    P = []
    for z0 in zs:
        s = tq('x', (X0, y0, z0), (X1, y0 + 40, z0 + 40))
        if z0 == Z0:
            s = keep(s, (X0, 0, Z0), (S2, 0, -S2)); s = keep(s, (X1, 0, Z0), (-S2, 0, -S2))
        else:
            s = keep(s, (X0, 0, Z1), (S2, 0, S2)); s = keep(s, (X1, 0, Z1), (-S2, 0, S2))
        P.append(s)
    for x0 in xs:
        s = tq('z', (x0, y0, Z0), (x0 + 40, y0 + 40, Z1))
        if x0 == X0:
            s = keep(s, (X0, 0, Z0), (-S2, 0, S2)); s = keep(s, (X0, 0, Z1), (-S2, 0, -S2))
        else:
            s = keep(s, (X1, 0, Z0), (S2, 0, S2)); s = keep(s, (X1, 0, Z1), (S2, 0, -S2))
        P.append(s)
    return P


def step1():
    """5363401A00 一步梯：腿 x 0~40 / 360~400、z 0~40 / 160~200，y 8~308；顶框 y 308~348；中撑 y 158~198"""
    P = []
    ux = frame_miter((0, 360), (0, 160), 308, 0, 400, 0, 200)
    names = ['方管40x40x1.5-L400-45-45 (7)', '方管40x40x1.5-L400-45-45 (7)', '方管40x40x1.5-L200-45-45 (6)', '方管40x40x1.5-L200-45-45 (6)']
    P += list(zip(names, ux))
    yc = 178
    for x0 in (0, 360):
        for z0 in (0, 160):
            leg = tq('y', (x0, 8, z0), (x0 + 40, 308, z0 + 40))
            # 前后中撑（沿 x）顶在腿的内 x 面，贴腿外 z 面；侧中撑（沿 z）顶在腿的内 z 面，贴腿外 x 面
            fx = x0 + 40 if x0 == 0 else x0
            oz = z0 if z0 == 0 else z0 + 40
            fz = z0 + 40 if z0 == 0 else z0
            ox = x0 if x0 == 0 else x0 + 40
            leg = notch(leg, 'x', fx, 'z', oz, yc)
            leg = notch(leg, 'z', fz, 'x', ox, yc)
            P.append(('方管40x40x1.5-L300 腿 (4)', leg))
    for z0 in (0, 160):
        P.append(('方管40x40x1.5-L320 前后中撑 (5)', rail_x(40, 360, 158, z0, z0 if z0 == 0 else z0 + 40)))
    for x0 in (0, 360):
        P.append(('方管40x40x1.5-L120 侧中撑 (3)', rail_z(40, 160, 158, x0, x0 if x0 == 0 else x0 + 40)))
    return P


def step2():
    """5409920A00 两步梯：后腿 x 0~40 y 8~540；前腿 x 560~600 y 8~250；中腿 x 260~300 y 290~540；
    上框 x 0~300 × z 0~400（y 540~580）；下框 L560 x 40~600 + 前 z 管 x 560~600（y 250~290）+ 后 z 撑 L320 x 0~40"""
    P = []
    up = frame_miter((0, 260), (0, 360), 540, 0, 300, 0, 400)
    P += list(zip(['方管40x40x1.5-L300-45-45 (9)'] * 2 + ['方管40x40x1.5-L400-45-45 (10)'] * 2, up))
    yc = 270
    for z0 in (0, 360):
        oz = z0 if z0 == 0 else z0 + 40
        fz = z0 + 40 if z0 == 0 else z0
        leg = tq('y', (0, 8, z0), (40, 540, z0 + 40))
        leg = notch(leg, 'x', 40, 'z', oz, yc)            # 下框 L560 顶在后腿 x=40 面
        leg = notch(leg, 'z', fz, 'x', 0, yc)             # 后 z 撑 L320 顶在后腿内 z 面
        P.append(('方管40x40x1.5-L532 后腿 (7)', leg))
        P.append(('方管40x40x1.5-L242 前腿 (4)', tq('y', (560, 8, z0), (600, 250, z0 + 40))))
        P.append(('方管40x40x1.5-L250 中腿 (5)', tq('y', (260, 290, z0), (300, 540, z0 + 40))))
        s = rail_x(40, 600, 250, z0, oz, tabs=(True, False))
        s = keep(s, (600, 0, 0 if z0 == 0 else 400), (-S2, 0, -S2) if z0 == 0 else (-S2, 0, S2))
        P.append(('方管40x40x1.5-L560-45 下框 (8)', s))
    f = tq('z', (560, 250, 0), (600, 290, 400))
    f = keep(f, (600, 0, 0), (S2, 0, S2)); f = keep(f, (600, 0, 400), (S2, 0, -S2))
    P.append(('方管40x40x1.5-L400-45-45 下框前 (10)', f))
    P.append(('方管40x40x1.5-L320 下框后撑 (6)', rail_z(40, 360, 250, 0, 0)))
    return P


def round_tube(d, t, L):
    """圆管：外径 d、壁厚 t、长 L（沿 z）"""
    q = d / 2; k = q * S2; r = q - t; kr = r * S2
    o = [('A', (q, 0), (0, q), (-q, 0)), ('A', (-q, 0), (0, -q), (q, 0))]
    i = [('A', (r, 0), (0, r), (-r, 0)), ('A', (-r, 0), (0, -r), (r, 0))]
    return prism(o, [i], ('x', 'y'), 0, L)


if __name__ == '__main__':
    report = []
    for code, name, fn, qty in (('5363401A00', '一步梯', step1, 1), ('5409920A00', '两步梯', step2, 1)):
        parts = fn()
        write_assembly(parts, os.path.join(CHK, '%s_%s_方管装配.step' % (code, name)), '%s %s 方管' % (code, name))
        groups = {}
        for nm, s in parts:
            assert valid(s), nm
            groups.setdefault(nm.split(' ')[0], []).append((nm, s))
        for spec, items in groups.items():
            v = [round(volume(s), 1) for _, s in items]
            assert max(v) - min(v) < 1, (spec, v)                 # 同规格件必须完全相同（同一 STEP）
            fname = '%s-%s-%s-%d件.step' % (code, name, spec, len(items) * qty)
            write_assembly([(spec, items[0][1])], os.path.join(OUT, fname), '%s %s %s' % (code, name, spec))
            report.append((fname, v[0], bbox(items[0][1])))
    # 7390202A 空心管 20×2-L1200（无图纸，按物料描述）
    s = round_tube(20, 2, 1200)
    write_assembly([('7390202A 空心管 Φ20x2-L1200', s)], os.path.join(OUT, '7390202A-空心管-Φ20x2-L1200-2件.step'), '7390202A 空心管')
    report.append(('7390202A-空心管-Φ20x2-L1200-2件.step', round(volume(s), 1), bbox(s)))
    for r in report:
        print('%-60s 体积 %9.1f  %s' % r)
