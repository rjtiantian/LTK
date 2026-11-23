# -*- coding: utf-8 -*-
"""NO.481 B 批方管 STEP（交管材激光）：3420101A00 框架、3420161A00 / 3420162A00 安全门。

用法（需 OCP）:  python 481/装配STEP/make_tubes_b.py  → 481/装配STEP/<物料号>-<名称>-装配-1套.step
11-23 用户：焊接件要整件装配体，不要单根零件 → 默认只出装配（框架连同 5 个 3400101A02 支撑腿件）；
单根方管 STEP 要时把 PER_TUBE 改 True。
几何取 DWG 矢量（各视图 1:1）：x 沿主视宽、y 沿主视高、z 由前（0）向后。
做法照 flat-pattern 技能第 5 节：空心管，SUS304 外 R = 1.2t、内 R = 外 − t（图纸 / 明细栏的 R1 不用）；45° 斜接照图；
孔只开在图纸标的那面壁（“Φ5.5 -8 深”“M8↧22.2”都小于管外形，不贯穿）；
横撑与立柱插接定位（图纸没有，按样例加）：横撑贴立柱外侧的管壁两端伸出舌 13 × 3.5，立柱对应管角开 13.5 × 3.75 缺口。

螺纹孔：图纸没写热熔工艺，FLOW = False 按小径开（M3 2.459 / M5 4.134 / M6 4.917 / M8 6.647 / M10 8.376）；
要走热熔底孔把 FLOW 改 True 重出（M6 Φ1 / M8 Φ1.5 / M10 Φ2，M3 / M5 用户没给数，仍按小径）。
"""
import os, sys, math, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from frame3d import tube, keep, cut, box, cyl, volume, bbox, valid, write_assembly, AX
from tube_step import TAB_W, TAB_L, CLR
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Common

FLOW = False
TAP = {'M3': 2.459, 'M5': 4.134, 'M6': 4.917, 'M8': 6.647, 'M10': 8.376}
PILOT = {'M6': 1.0, 'M8': 1.5, 'M10': 2.0}
RHO = 7.93e-6
S2 = math.sqrt(0.5)
OUT = HERE
CHK = os.path.join(HERE, '..', '装配STEP')
PER_TUBE = False
NW = TAB_W + 2 * CLR                 # 立柱缺口宽 13.5
ND = TAB_L + CLR                     # 立柱缺口深（沿横撑方向）3.75


def dia(k):
    if isinstance(k, str):
        return PILOT.get(k, TAP[k]) if FLOW else TAP[k]
    return k


class T:
    def __init__(self, name, axis, lo, hi, t, spec, miter=()):
        self.name, self.axis, self.lo, self.hi, self.t, self.spec = name, axis, lo, hi, t, spec
        self.miter = list(miter)      # [(点, 法向)]：保留 (p-点)·法向 ≥ 0
        self.holes, self.tabs, self.notches = [], [], []

    def L(self):
        i = AX[self.axis]
        return self.hi[i] - self.lo[i]

    def hole(self, face, side, d, pts):
        """face = 孔轴向 'x'/'y'/'z'，side = 'lo'/'hi' 该轴上哪面壁，pts = 另两轴坐标（按 xyz 顺序）"""
        i = AX[face]
        others = [k for k in range(3) if k != i]
        w = (self.lo if side == 'lo' else self.hi)[i]
        for u, v in pts:
            c = [0, 0, 0]; c[i] = w; c[others[0]] = u; c[others[1]] = v
            for k, q in zip(others, (u, v)):
                assert self.lo[k] - 1e-6 <= q <= self.hi[k] + 1e-6, (self.name, face, side, u, v)
            self.holes.append((face, side, tuple(c), d))
        return self


def build(tube_list, joints):
    """joints: (横撑名, 'lo'/'hi' 端, 立柱名, 贴外侧的轴, 该轴坐标)"""
    D = {t.name: t for t in tube_list}
    for rail, end, post, fa, fc in joints:
        R, P = D[rail], D[post]
        ia = AX[R.axis]
        c = (R.lo if end == 'lo' else R.hi)[ia]
        ifa = AX[fa]
        ipa = 3 - ia - ifa                     # 立柱长度方向（也是舌的宽度方向）
        assert AX[P.axis] == ipa, (rail, post, P.axis)
        assert abs((P.hi if end == 'lo' else P.lo)[ia] - c) < 1e-6, (rail, end, post)
        mid = (R.lo[ipa] + R.hi[ipa]) / 2
        # 舌：横撑贴外侧的管壁伸出 TAB_L
        lo, hi = [0, 0, 0], [0, 0, 0]
        lo[ipa], hi[ipa] = mid - TAB_W / 2, mid + TAB_W / 2
        out_lo = abs(fc - R.lo[ifa]) < 1e-6
        lo[ifa], hi[ifa] = (fc, fc + R.t) if out_lo else (fc - R.t, fc)
        s = -1 if end == 'lo' else 1
        lo[ia], hi[ia] = (c, c + s * TAB_L) if s > 0 else (c + s * TAB_L, c)
        R.tabs.append((tuple(lo), tuple(hi)))
        # 缺口：立柱管角
        lo, hi = [0, 0, 0], [0, 0, 0]
        lo[ipa], hi[ipa] = mid - NW / 2, mid + NW / 2
        NA = P.t + 1.45
        lo[ifa], hi[ifa] = (fc - 1, fc + NA) if out_lo else (fc - NA, fc + 1)
        lo[ia], hi[ia] = (c - 1, c + s * ND) if s > 0 else (c + s * ND, c + 1)
        P.notches.append((tuple(lo), tuple(hi)))
        # 缺口不能碰孔
        for face, side, h, d in P.holes:
            if all(lo[k] - dia(d) <= h[k] <= hi[k] + dia(d) for k in range(3)):
                raise AssertionError('缺口碰孔 %s %s %s' % (post, h, d))
    out = {}
    for t in tube_list:
        s = tube(t.axis, t.lo, t.hi, t.t)
        for p, n in t.miter:
            q = math.sqrt(sum(v * v for v in n))
            s = keep(s, p, tuple(v / q for v in n))
        for lo, hi in t.tabs:
            s = BRepAlgoAPI_Fuse(s, box(lo, hi)).Shape()
        for lo, hi in t.notches:
            s = cut(s, box(lo, hi))
        for face, side, c, d in t.holes:
            i = AX[face]
            w = c[i]
            a0, a1 = (w - 1, w + t.t + 1) if side == 'lo' else (w - t.t - 1, w + 1)
            s = cut(s, cyl(face, c, dia(d), a0, a1))
        assert valid(s), t.name
        out[t.name] = s
    return out


def canon(t):
    """同形判定：把斜接 / 孔 / 舌 / 缺口换到管自身坐标，取 8 种（方管 16 种里的真旋转）姿态里最小的描述。"""
    ia = AX[t.axis]
    iu, iv = [k for k in range(3) if k != ia]
    c = [(t.lo[k] + t.hi[k]) / 2 for k in range(3)]
    ft = []
    for p, n in t.miter:
        q = math.sqrt(sum(v * v for v in n))
        # 平面用：轴线交点 + 单位法向
        ns = [v / q for v in n]
        d = sum((p[k] - c[k]) * ns[k] for k in range(3))
        ft.append(('M', ns[ia] and d / ns[ia], 0, 0, ns[ia], ns[iu], ns[iv]))
    for face, side, h, dd in t.holes:
        ft.append(('H', h[ia] - c[ia], h[iu] - c[iu], h[iv] - c[iv], dia(dd), 0, 0))
    for lo, hi in t.tabs:
        m = [(lo[k] + hi[k]) / 2 - c[k] for k in range(3)]
        ft.append(('T', m[ia], m[iu], m[iv], 0, 0, 0))
    for lo, hi in t.notches:
        m = [(lo[k] + hi[k]) / 2 - c[k] for k in range(3)]
        ft.append(('N', m[ia], m[iu], m[iv], 0, 0, 0))

    def rot(f, flip, k):
        tag, s, u, v, a, b, e = f
        if tag == 'M':
            ns, nu, nv = a, b, e
            if flip:
                s, ns, nv = -s, -ns, -nv
            for _ in range(k):
                nu, nv = -nv, nu
            # 平面法向取一致符号
            return (tag, round(s, 2), 0, 0, round(ns, 3), round(nu, 3), round(nv, 3))
        if flip:
            s, v = -s, -v
        for _ in range(k):
            u, v = -v, u
        return (tag, round(s, 2), round(u, 2), round(v, 2), a if tag == 'H' else 0, 0, 0)
    sq = abs((t.hi[iu] - t.lo[iu]) - (t.hi[iv] - t.lo[iv])) < 1e-6
    best = None
    for flip in (0, 1):
        for k in ((0, 1, 2, 3) if sq else (0, 2)):
            d = tuple(sorted(rot(f, flip, k) for f in ft))
            if best is None or d < best:
                best = d
    return (t.spec, round(t.L(), 2), best)


# ======================================================================= 3420101A00 框架
def frame_101():
    t = 2.5
    sp = '方管50x50x2.5'
    def Y(n, x, z, y0, y1, tag='', miter=()):
        return T(n, 'y', (x, y0, z), (x + 50, y1, z + 50), t, '%s-L%d%s' % (sp, y1 - y0, tag), miter)
    def X(n, y, z, x0, x1, tag='', miter=()):
        return T(n, 'x', (x0, y, z), (x1, y + 50, z + 50), t, '%s-L%d%s' % (sp, x1 - x0, tag), miter)
    def Z(n, x, y, z0, z1, tag='', miter=()):
        return T(n, 'z', (x, y, z0), (x + 50, y + 50, z1), t, '%s-L%d%s' % (sp, z1 - z0, tag), miter)
    G = Y('G', 0, 0, 50, 1300, '-45', [((0, 1300, 0), (-1, -1, 0))])
    V2 = Y('V2', 1750, 0, 50, 1250)
    V3 = Y('V3', 340, 0, 50, 750)
    V4 = Y('V4', 1000, 0, 50, 750)
    V5 = Y('V5', 0, 800, 50, 750)
    V6 = Y('V6', 1750, 800, 50, 750)
    V7 = Y('V7', 1000, 900, 50, 750)
    V8 = Y('V8', 340, 0, 800, 1250)
    V9 = Y('V9', 700, 950, 800, 1250)
    V10 = Y('V10', 1750, 950, 800, 1250)
    CG = Y('CG', 0, 950, 750, 1300, '-45-45', [((0, 1300, 0), (-1, -1, 0)), ((0, 750, 0), (-1, 1, 0))])
    Hft = X('Hf_top', 1250, 0, 0, 1800, '-45', [((0, 1300, 0), (1, 1, 0))])
    Hrt = X('Hr_top', 1250, 950, 0, 1800, '-45', [((0, 1300, 0), (1, 1, 0))])
    Hrm = X('Hr_mid', 750, 950, 0, 1800, '-45', [((0, 750, 0), (1, -1, 0))])
    Hfm = X('Hf_mid', 750, 0, 50, 1750)
    Hfb = X('Hf_bot', 0, 0, 0, 1800, '-45', [((0, 0, 0), (1, 0, -1))])
    Hrb = X('Hr_bot', 0, 950, 0, 1800, '-45', [((0, 0, 1000), (1, 0, 1))])
    AE = Z('AE', 0, 0, 0, 1000, '-45-45', [((0, 0, 0), (-1, 0, 1)), ((0, 0, 1000), (-1, 0, -1))])
    Zb1 = Z('Zb1', 1000, 0, 50, 950)
    Zb2 = Z('Zb2', 1750, 0, 50, 950)
    Zm0 = Z('Zm0', 0, 750, 50, 950)
    Zm1 = Z('Zm1', 1000, 750, 50, 950)
    Zm2 = Z('Zm2', 1750, 750, 50, 950)

    F55 = 5.5
    # ---- x-y 平面的孔（z 向，主视 / A 向）
    Hft.hole('z', 'lo', 'M8', [(x, 1260) for x in (410, 840, 1270)])
    Hrt.hole('z', 'hi', 'M8', [(x, 1260) for x in (770, 1020, 1270)] + [(390, 1268.5), (550, 1268.5)])
    Hrm.hole('z', 'hi', 'M8', [(x, 790) for x in (770, 1020, 1270)])
    Hrm.hole('z', 'lo', 'M8', [(94, 772.5), (194, 772.5)])              # 主视 / A 向都是虚线圆，俯视虚线落在 z=950~952.5 壁上
    Hfb.hole('z', 'lo', 'M8', [(x, 40) for x in (410, 705, 1000)])
    Hrb.hole('z', 'hi', 'M6', [(x, 40) for x in (100, 130, 885, 915, 1670, 1700)])
    for H, side in ((Hfb, 'hi'), (Hrb, 'lo')):                          # Y=10 这排两面都有（俯视两处壁厚虚线）
        H.hole('z', side, F55, [(x, 10) for x in (150, 525, 900, 1150, 1650)])
    V3.hole('z', 'lo', 'M8', [(380, y) for y in (70, 400, 730)])
    V8.hole('z', 'lo', 'M8', [(380, y) for y in (820, 1230)])
    V9.hole('z', 'hi', 'M8', [(740, y) for y in (820, 1025, 1230)])
    V10.hole('z', 'lo', 'M6', [(1762.5, 1233.3), (1787.5, 1233.3)])
    # ---- x-z 平面的孔（y 向，C-C / D-D / E-E / B-B / 俯视）
    Hft.hole('y', 'hi', 'M6', [(x, 40) for x in (100, 130, 885, 915, 1670, 1700)])
    Hft.hole('y', 'lo', 'M8', [(x, 25) for x in (640, 680, 1200, 1240, 1497, 1537)])
    Hft.hole('y', 'lo', F55, [(195, 10)])
    Hrt.hole('y', 'lo', 'M8', [(x, 975) for x in (640, 680, 1200, 1240, 1497, 1537)] + [(94, 972.5), (194, 972.5)])
    Hrt.hole('y', 'lo', F55, [(230, 990), (600, 990)])
    Hfm.hole('y', 'hi', 'M8', [(1497, 25), (1537, 25)])
    Hfm.hole('y', 'hi', F55, [(195, 10)])
    Hfm.hole('y', 'lo', F55, [(x, 10) for x in (195, 1150, 1650)])
    Hrm.hole('y', 'hi', 'M8', [(1497, 975), (1537, 975)])
    Hrm.hole('y', 'hi', F55, [(150, 990), (600, 990)])
    Hfb.hole('y', 'hi', F55, [(x, 10) for x in (195, 1150, 1650)])
    Zm2.hole('y', 'lo', 'M6', [(1762.5, 933.3), (1787.5, 933.3)])
    # ---- y-z 平面的孔（x 向，F-F / G-G / H-H / J-J / K-K / L-L）
    G.hole('x', 'hi', F55, [(y, 10) for y in (150, 650, 900, 1150)])
    CG.hole('x', 'hi', F55, [(y, 990) for y in (900, 1150)])
    AE.hole('x', 'hi', F55, [(10, z) for z in (150, 850)])
    V3.hole('x', 'lo', F55, [(y, 10) for y in (150, 650)])
    V8.hole('x', 'lo', F55, [(y, 10) for y in (900, 1150)])
    V9.hole('x', 'lo', F55, [(y, 990) for y in (900, 1150)])
    V4.hole('x', 'lo', 'M8', [(y, 25) for y in (127.5, 172.5, 627.5, 672.5)])
    V4.hole('x', 'hi', F55, [(y, 10) for y in (150, 650)])
    V7.hole('x', 'lo', 'M8', [(y, 925) for y in (127.5, 172.5, 627.5, 672.5)])
    V2.hole('x', 'lo', F55, [(y, 10) for y in (150, 650)])
    Zb1.hole('x', 'lo', F55, [(10, z) for z in (150, 850)])
    Zb1.hole('x', 'hi', F55, [(10, z) for z in (150, 850)])
    Zb2.hole('x', 'lo', F55, [(10, z) for z in (150, 850)])
    Zm1.hole('x', 'hi', 'M10', [(775, z) for z in (220, 780)])

    L = [G, V2, V3, V4, V5, V6, V7, V8, V9, V10, CG, Hft, Hrt, Hrm, Hfm, Hfb, Hrb, AE, Zb1, Zb2, Zm0, Zm1, Zm2]
    J = [('G', 'lo', 'Hf_bot', 'z', 0), ('V2', 'lo', 'Hf_bot', 'z', 0), ('V2', 'hi', 'Hf_top', 'z', 0),
         ('V3', 'lo', 'Hf_bot', 'z', 0), ('V3', 'hi', 'Hf_mid', 'z', 0), ('V4', 'lo', 'Hf_bot', 'z', 0), ('V4', 'hi', 'Hf_mid', 'z', 0),
         ('V5', 'lo', 'AE', 'x', 0), ('V5', 'hi', 'Zm0', 'x', 0), ('V6', 'lo', 'Zb2', 'x', 1800), ('V6', 'hi', 'Zm2', 'x', 1800),
         ('V7', 'lo', 'Zb1', 'x', 1050), ('V7', 'hi', 'Zm1', 'x', 1050), ('V8', 'lo', 'Hf_mid', 'z', 0), ('V8', 'hi', 'Hf_top', 'z', 0),
         ('V9', 'lo', 'Hr_mid', 'z', 1000), ('V9', 'hi', 'Hr_top', 'z', 1000), ('V10', 'lo', 'Hr_mid', 'z', 1000), ('V10', 'hi', 'Hr_top', 'z', 1000),
         ('Hf_mid', 'lo', 'G', 'z', 0), ('Hf_mid', 'hi', 'V2', 'z', 0),
         ('Zb1', 'lo', 'Hf_bot', 'y', 0), ('Zb1', 'hi', 'Hr_bot', 'y', 0), ('Zb2', 'lo', 'Hf_bot', 'y', 0), ('Zb2', 'hi', 'Hr_bot', 'y', 0),
         ('Zm0', 'lo', 'G', 'x', 0), ('Zm0', 'hi', 'CG', 'x', 0), ('Zm1', 'lo', 'Hf_mid', 'y', 800), ('Zm1', 'hi', 'Hr_mid', 'y', 800),
         ('Zm2', 'lo', 'V2', 'x', 1800), ('Zm2', 'hi', 'Hr_mid', 'y', 800)]
    return L, J


# ======================================================================= 3420161A00 / 162A00 安全门
def door(H, xc, top_m6, bot_m6, rear_top, m6_inner, inner_on_top, xs55, ys_side, ys_cl, ys_cr):
    """1800 × H 框：25×50×2 四根 45° 斜接，中立 50×50×2；rear_top = 背面螺纹孔那根是不是上框"""
    t = 2
    s25 = '方管25x50x2'
    s50 = '方管50x50x2'
    Bot = T('Bot', 'x', (0, 0, 0), (1800, 25, 50), t, '%s-L1800-45-45' % s25, [((0, 0, 0), (1, -1, 0)), ((1800, 0, 0), (-1, -1, 0))])
    Top = T('Top', 'x', (0, H - 25, 0), (1800, H, 50), t, '%s-L1800-45-45' % s25, [((0, H, 0), (1, 1, 0)), ((1800, H, 0), (-1, 1, 0))])
    Lf = T('Left', 'y', (0, 0, 0), (25, H, 50), t, '%s-L%d-45-45' % (s25, H), [((0, 0, 0), (-1, 1, 0)), ((0, H, 0), (-1, -1, 0))])
    Rt = T('Right', 'y', (1775, 0, 0), (1800, H, 50), t, '%s-L%d-45-45' % (s25, H), [((1800, 0, 0), (1, 1, 0)), ((1800, H, 0), (1, -1, 0))])
    Ce = T('Center', 'y', (xc, 25, 0), (xc + 50, H - 25, 50), t, '%s-L%d' % (s50, H - 50))
    # 正面 6-M6
    (Top if top_m6 else Bot).hole('z', 'lo', 'M6', [(x, H - 10 if top_m6 else 10) for x in (100, 130, 885, 915, 1670, 1700)])
    # 背面：M5 ×2、M8 ×1、M3 ×2（M3 跨在斜接两边：1757.5 在长管、1792.5 在竖管）
    A = Top if rear_top else Bot
    ym5, ym8, ym3 = (H - 13, H - 12.5, H - 12.6) if rear_top else (13, 12.5, 12.7)
    A.hole('z', 'hi', 'M5', [(124, ym5), (164, ym5)]).hole('z', 'hi', 'M8', [(900, ym8)]).hole('z', 'hi', 'M3', [(1757.5, ym3)])
    Rt.hole('z', 'hi', 'M3', [(1792.5, ym3)])
    # 内侧面 Φ5.5（距正面 10）
    Top.hole('y', 'lo', 5.5, [(x, 10) for x in xs55])
    Bot.hole('y', 'hi', 5.5, [(x, 10) for x in xs55])
    (Top if inner_on_top else Bot).hole('y', 'lo' if inner_on_top else 'hi', 'M6', [(x, 25) for x in m6_inner])
    Lf.hole('x', 'hi', 5.5, [(y, 10) for y in ys_side])
    Rt.hole('x', 'lo', 5.5, [(y, 10) for y in ys_side])
    Ce.hole('x', 'lo', 5.5, [(y, 10) for y in ys_cl])
    Ce.hole('x', 'hi', 5.5, [(y, 10) for y in ys_cr])
    return [Bot, Top, Lf, Rt, Ce], [('Center', 'lo', 'Bot', 'z', 0), ('Center', 'hi', 'Top', 'z', 0)]


def feet_101():
    """3400101A02 支撑腿件 10mm 50×50 R2、M16 开小径 Φ13.84：垫在 x=1800 端 5 根横管下（主视 / 俯视矢量 x 1800~1810，
    y 0 / 750 / 1250、z 0 / 950；y750 只在 z950 那根 Hr_mid 下）"""
    from frame3d import plate
    pos = [(0, 0), (0, 950), (1250, 0), (1250, 950), (750, 950)]
    return [('3400101A02 支撑腿件-10', plate('x', (1800, y, z), (1810, y + 50, z + 50), 2, [(y + 25, z + 25, 13.84)])) for y, z in pos]


def run(code, name, L, J, bom, rep, extra=()):
    S = build(L, J)
    asm = [(t.name + ' ' + t.spec, S[t.name]) for t in L] + list(extra)
    fn = '%s-%s-装配-1套' % (code, name)
    write_assembly(asm, os.path.join(CHK, fn + '.step'), fn)
    print(fn, '零件', len(asm), '算重 %.2f kg' % (sum(volume(s) for _, s in asm) * RHO))
    # 干涉：两两共同体积
    bad = []
    for a, b in itertools.combinations(L, 2):
        ba, bb = bbox(S[a.name]), bbox(S[b.name])
        if any(ba[k] > bb[k + 3] + 0.01 or bb[k] > ba[k + 3] + 0.01 for k in range(3)):
            continue
        v = volume(BRepAlgoAPI_Common(S[a.name], S[b.name]).Shape())
        if v > 0.5:
            bad.append((a.name, b.name, round(v, 2)))
    groups = {}
    for t in L:
        groups.setdefault(canon(t), []).append(t)
    specs = {}
    for k, ts in groups.items():
        specs.setdefault(ts[0].spec, []).append(ts)
    tot = 0
    for spec, tss in sorted(specs.items()):
        n_all = sum(len(x) for x in tss)
        assert bom[spec] == n_all, (spec, n_all, bom)
        for i, ts in enumerate(sorted(tss, key=lambda x: x[0].name)):
            tag = '' if len(tss) == 1 else '-%s' % 'abcdefgh'[i]
            s = S[ts[0].name]
            fn = '%s-%s-%s%s-%d件.step' % (code, name, spec, tag, len(ts))
            if PER_TUBE:
                write_assembly([(spec + tag, s)], os.path.join(OUT, fn), '%s %s %s' % (code, name, spec))
            nh = len(ts[0].holes)
            rep.append((fn, '+'.join(t.name for t in ts), nh, round(volume(s) * RHO, 3)))
            tot += volume(s) * RHO * len(ts)
    print(code, '共', len(L), '根，', len(groups), '种，算重 %.2f kg，干涉' % tot, bad)
    return tot


if __name__ == '__main__':
    os.makedirs(CHK, exist_ok=True)
    rep = []
    sp = '方管50x50x2.5'
    L, J = frame_101()
    run('3420101A00', '框架', L, J, {sp + '-L1250-45': 1, sp + '-L550-45-45': 1, sp + '-L1800-45': 5, sp + '-L1000-45-45': 1, sp + '-L900': 5,
                                     sp + '-L700': 5, sp + '-L450': 3, sp + '-L1700': 1, sp + '-L1200': 1}, rep, feet_101())
    L, J = door(685, 1000, True, False, False, (1075, 1100), False, (165, 512.5, 860, 1190, 1635), (125, 560), (125, 560), (175, 560))
    run('3420161A00', '安全门', L, J, {'方管25x50x2-L1800-45-45': 2, '方管25x50x2-L685-45-45': 2, '方管50x50x2-L635': 1}, rep)
    L, J = door(885, 875, False, True, True, (950, 975), True, (165, 450, 735, 1065, 1350, 1635), (125, 760), (125, 760), (125, 720))
    run('3420162A00', '安全门', L, J, {'方管25x50x2-L1800-45-45': 2, '方管25x50x2-L885-45-45': 2, '方管50x50x2-L835': 1}, rep)
    for r in rep:
        print('%-62s %-22s 孔%-3d 单重 %.3f' % r)
