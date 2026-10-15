# -*- coding: utf-8 -*-
"""NO.474 第二批图纸（NO.474 图纸.zip）的展开件定义"""
import math
from sheetlib import (Piece, extract, extract_unbroken, stretch_tab, drop_concentric_outer, bd, TAP,
                      relief_params, clip_out_box, bd_angle)


def setup(PARTS, DXF, lab, plate, circles, todo):
    def part(code):
        def deco(f):
            PARTS[code] = f
            return f
        return deco

    def mirror_of(src):
        def f(q):
            res = PARTS[src](q)
            if isinstance(res, tuple):
                return res
            return [(l, p.mirrored()) for l, p in res]
        return f

    # ------------------------------------------------ 护栏挡板：2mm，端部 15°(或10°) 小折边
    def dedupe_tab(p, xb, side, dmin=0.15, dmax=1.2, tol=0.03):
        """折边朝向视图时，图纸会同时画出折边的正、反两面轮廓（相距 t·tanα），
        展开只保留最外侧一圈：删掉向外平移 d 后能与另一图元重合的内侧图元"""
        sgn = 1 if side == 'right' else -1
        def pts(e):
            k, d, a = e
            if k == 'LWPOLYLINE':
                return [(x, y) for x, y, *_ in d[0]]
            if k == 'LINE':
                return list(d)
            if k == 'ARC':
                return [d[0]]
            return None
        def beyond(e):
            ps = pts(e)
            return ps and all((x - xb) * sgn > dmin for x, y in ps)
        cand = [e for e in p.ents if beyond(e)]
        drop = set()
        for i, e in enumerate(cand):
            pe = pts(e)
            for f in cand:
                if f is e or f[0] != e[0] or len(pts(f)) != len(pe):
                    continue
                pf = pts(f)
                d = (pf[0][0] - pe[0][0]) * sgn
                if dmin < d < dmax and all(abs((fx - ex) * sgn - d) < tol and abs(fy - ey) < tol
                                           for (ex, ey), (fx, fy) in zip(pe, pf)):
                    drop.add(id(e)); break
        p.ents = [e for e in p.ents if id(e) not in drop]

    def guard(fname, region, L, side='left', ang=15, t=2):
        def f(q):
            p = extract_unbroken(DXF(fname), region)
            drop_concentric_outer(p)
            b = p.bbox()
            if side == 'left':
                xb = b[2] - L
            else:
                xb = b[0] + L
            p = stretch_tab(p, xb, ang, side)
            dedupe_tab(p, xb, side)
            # 小角度折边根部保留图纸原有的 1x1 释放口（按要求不改为 V 形槽）
            b = p.bbox()
            # 小角度折弯只画红色中心线（同 NO.441 4020142B）；折边范围取折弯线处的轮廓高度
            ys = []
            for k, data, a in p.ents:
                pts = data[0] if k == 'LWPOLYLINE' else (data if k == 'LINE' else [])
                for pt in pts:
                    x, y = pt[0], pt[1]
                    if (side == 'left' and x < xb - 0.5) or (side == 'right' and x > xb + 0.5):
                        ys.append(y)
            y0, y1 = (min(ys), max(ys)) if ys else (b[1], b[3])
            p.poly([(xb, y0), (xb, y1)], False, '折弯线', linetype='CENTER', color=1, ltscale=0.5)
            return [(lab(t, q), p)]
        return f

    G = [('0184601A', (109.2, 170.5, 328.5, 270.5), 200, 'left', 15),
         ('0184701A', (105.0, 253.2, 534.3, 353.2), 410, 'left', 15),
         ('0185101A', (74.2, 178.8, 403.5, 278.8), 310, 'right', 15),
         ('0185109A', (172.9, 541.0, 992.4, 641.1), 2000, 'left', 15),
         ('0185111A', (137.8, 239.0, 458.3, 339.0), 647, 'left', 15),
         ('0185113A', (110.0, 374.6, 821.4, 474.6), 692, 'left', 15),
         ('0185115A', (104.8, 235.7, 499.5, 335.7), 380, 'right', 10),
         ('0185203A', (122.7, 170.7, 342.0, 270.7), 200, 'left', 15),
         ('0185301A', (159.1, 408.2, 773.5, 508.2), 1000, 'left', 15),
         ('0185303A', (239.9, 738.1, 1549.3, 838.1), 2000, 'left', 15),
         ('0185401A', (128.1, 404.1, 747.4, 504.1), 600, 'left', 15),
         ('0185403A', (253.1, 675.9, 1252.5, 775.9), 2000, 'left', 15),
         ('0185501A', (168.5, 401.0, 707.1, 501.0), 1167, 'left', 15),
         ('0185601A', (196.7, 386.3, 706.7, 486.3), 867, 'left', 15)]
    for code, reg, L, side, ang in G:
        PARTS[code] = guard(code + '.idw.dxf', reg, L, side, ang)
    MIR = {'0184602A': '0184601A', '0184702A': '0184701A', '0185102A': '0185101A', '0185110A': '0185109A',
           '0185112A': '0185111A', '0185114A': '0185113A', '0185116A': '0185115A', '0185204A': '0185203A',
           '0185302A': '0185301A', '0185304A': '0185303A', '0185402A': '0185401A', '0185404A': '0185403A',
           '0185502A': '0185501A', '0185602A': '0185601A'}
    for m, s in MIR.items():
        PARTS[m] = mirror_of(s)
    return part, mirror_of


def setup2(PARTS, DXF, lab, plate, circles, todo, part, mirror_of):
    from sheetlib import fold_edge, Piece, extract_unbroken, drop_concentric_outer, bd

    def lab_tube(spec, L, n):
        # 型材按 NO.441 写法：材料-长度,件数（如 Q235B-1200mm,1件）
        return lab(L, n)

    def tube(a, t, r=0):
        # 方管截面示意（外框+内框），同 NO.441 3170801A00 画法
        return Piece().rect(0, 0, a, a, 2 * t if r == 0 else r).rect(t, t, a - t, a - t, t if r == 0 else max(r - t, 0))

    @part('0121403A')
    def _(q):
        t = 2; w = bd(t)            # 挡板：立板120x70 + 底板50，R6
        p = Piece().rect(0, 0, 120, 117, 6)
        p.bend(0, 68.5, 120, 68.5, w)
        for x in (10, 60, 110):
            p.circle(x, 67 + 30, 6.6)
        for x in (35, 85):
            for d in (22, 38):
                p.circle(x, 67 + d, 6.6)
        return [(lab(t, q), p)]

    @part('0121506A')
    def _(q):
        t = 4; w = bd(t)            # 皮带光电支架：底板62x30 + 立板(宽50,高30)
        p = Piece()
        p.outline([(85.2, 0, 6), (65.2, 0, 6), (65.2, 20), (0, 20, 6), (0, 50, 6), (70.2, 50, 6), (85.2, 35, 6)])
        p.bend(58.6, 20, 58.6, 50, w)
        p.circle(7.5, 35, 6.6).circle(47.5, 35, 6.6)
        p.circle(80.2, 7.5, 4.5).circle(70.2, 7.5, 4.5)
        return [(lab(t, q), p)]

    def end_flanged(fname, region, t, L):
        def f(q):
            w = bd(t)
            p = extract_unbroken(DXF(fname), region)
            drop_concentric_outer(p)
            b = p.bbox()
            fold_edge(p, b[0], L, w, 'left', tol=0.2)
            fold_edge(p, b[2], L, w, 'right', tol=0.2)
            return [(lab(t, q), p)]
        return f
    PARTS['0180185A'] = end_flanged('0180185A.idw.dxf', (104.0, 235.6, 418.8, 330.8), 1.5, 10)
    PARTS['0180186A'] = end_flanged('0180186A.idw.dxf', (126.2, 234.4, 441.1, 329.6), 1.5, 10)

    @part('0180190A')
    def _(q):
        t = 2; w = bd(t)            # 护栏01：C 形 960 长，腹板80，上下翼边20，翼边端部 C10
        p = Piece()
        p.outline([(0, 10, 6), (10, 0, 6), (950, 0, 6), (960, 10, 6), (960, 104, 6), (950, 114, 6),
                   (10, 114, 6), (0, 104, 6)])
        p.bend(0, 18.5, 960, 18.5, w).bend(0, 95.5, 960, 95.5, w)
        p.circle(350, 57, 6.6).circle(760, 57, 6.6)
        return [(lab(t, q), p)]

    @part('0180550A')
    def _(q):
        t = 5; w = bd(t)            # 固定板：立板420，右段顶部翻边50，左端翻边50
        p = Piece()
        p.outline([(0, 0), (320.002, 0, 10), (420, 50, 10), (420, 100), (420, 141.6, 10), (300, 141.6, 10),
                   (300, 100), (300, 54, 10), (0, 54), (-41.6, 54, 10), (-41.6, 0, 10)])
        p.bend(300, 95.8, 420, 95.8, w).bend(4.2, 0, 4.2, 54, w)
        for x in (310, 350, 390):
            p.slot(x, 121.6, x + 20, 121.6, 9)
        p.slot(-21.6, 12, -21.6, 42, 9)
        return [(lab(t, q), p)]
    PARTS['0180551A'] = mirror_of('0180550A')

    @part('0180625A')
    def _(q):
        t = 4                       # 连接板：4 处 135° 折弯，中性层 K=0.46 计算展开长 331.55
        L = 331.546; ba = math.radians(45) * (4 + 0.46 * 4)
        w45 = 2 * 8 * math.tan(math.radians(22.5)) - ba
        p = Piece().outline([(0, 0, 2), (L, 0, 2), (L, 40, 2), (0, 40, 2)])
        for x in (38.98, 121.79, 209.75, 292.57):
            p.bend(x, 0, x, 40, w45)
        for x0 in (8.5, L - 22):
            p.slot(x0, 7.5, x0 + 13.5, 7.5, 6.5).slot(x0, 32.5, x0 + 13.5, 32.5, 6.5)
        p.circle(L / 2, 20, 9)
        return [(lab(t, q), p)]

    def c_channel(t, Lx, web, fl1, fl2, slots=(), holes=(), w=None):
        """C 形槽：长 Lx，腹板外形 web，两翼边外形 fl1/fl2；腹板上的孔用腹板坐标(y 从下翼边外表面起)"""
        w = w or bd(t)
        y1 = fl1 - w
        y2 = fl1 + web - 2 * w
        H = fl1 + web + fl2 - 2 * w
        p = Piece().rect(0, 0, Lx, H)
        p.bend(0, y1 + w / 2, Lx, y1 + w / 2, w).bend(0, y2 + w / 2, Lx, y2 + w / 2, w)
        for (x0, ya, x1, yb, sw) in slots:
            p.slot(x0, y1 + ya, x1, y1 + yb, sw)
        for (x, y, d) in holes:
            p.circle(x, y1 + y, d)
        return p, y1, y2, H

    @part('0181301A00')
    def _(q):
        # 底座：方管焊接框 + 0181301A01 横撑(4mm C 形) ×2 + 0120201A02(腿焊接02) ×2
        p, *_ = c_channel(4, 740, 100, 50, 50,
                          slots=[(x, 32.6, x, 67.6, 22) for x in (65, 325, 415, 675)])
        a02 = plate('0181301A00.idw_图纸_3.dxf', (40.1, 37.8, 90.1, 87.8))
        return [(lab(4, 2 * q), p), (lab(15, 2 * q), a02),
                (lab_tube('50x50x4', 910, 2 * q), tube(50, 4)),
                (lab_tube('50x50x1', 840, 2 * q), tube(50, 1)),
                (lab_tube('50x50x1', 115, 2 * q), tube(50, 1))]

    @part('0183143A')
    def _(q):
        t = 2; w = bd(t)            # 气源支撑：Z 形 20+15+20，宽20
        p = Piece().rect(0, 0, 49, 20, 5)
        p.bend(18.5, 0, 18.5, 20, w).bend(30.5, 0, 30.5, 20, w)
        p.circle(8, 10, 6.5).circle(41, 10, 6.5)
        return [(lab(t, q), p)]

    @part('0183147A')
    def _(q):
        t = 2; w = bd(t)            # 支撑件：几字形 22+22+130+22+22，宽20
        p = Piece().rect(0, 0, 206, 20, 5)
        for x in (20.5, 39.5, 166.5, 185.5):
            p.bend(x, 0, x, 20, w)
        p.circle(10, 10, 6.5).circle(196, 10, 6.5)
        for x in (72, 98, 108, 134):
            p.circle(x, 10, 5.5)
        return [(lab(t, q), p)]

    @part('0185123A')
    def _(q):
        t = 3                       # 支撑连接件：32.7°×2 + 90°×2，中性层 K=0.48 展开 246.34
        rn = 3 + 0.48 * 3
        L = 246.338
        def bdw(a):
            a = math.radians(a)
            return 2 * 6 * math.tan(a / 2) - a * rn
        p = Piece().rect(0, 0, L, 78, 5)
        for x, a in ((49.505, 32.7), (91.004, 32.7), (163.877, 90), (198.851, 90)):
            p.bend(x, 0, x, 78, bdw(a))
        p.circle(24, 59, 9).circle(L - 15, 59, 9).circle(L - 15, 19, 9)
        # R40 弧形腰孔（宽9，45°）
        cx, cy = 24, 59
        p.arc(cx, cy, 35.5, 247.5, 292.5).arc(cx, cy, 44.5, 247.5, 292.5)
        for a in (247.5, 292.5):
            ex, ey = cx + 40 * math.cos(math.radians(a)), cy + 40 * math.sin(math.radians(a))
            if a < 270:
                p.arc(ex, ey, 4.5, a - 180 + 0, a)        # 外端半圆
            else:
                p.arc(ex, ey, 4.5, a, a + 180)
        return [(lab(t, q), p)]
    PARTS['0185124A'] = mirror_of('0185123A')

    @part('0185708A')
    def _(q):
        t = 2.5; w = bd(t)          # 支架：C 形 600 长，腹板75，翼边37.5；上翼边端部 50x22.5 斜角+3孔
        p = Piece()
        p.outline([(0, 0), (600, 0), (600, 119.5, 5), (550, 142, 5), (0, 142, 5)])
        p.bend(0, 35.5, 600, 35.5, w).bend(0, 106.5, 600, 106.5, w)
        for k in range(8):
            x = 10 + 30 * k
            p.circle(x, 33.5 + 20, 9).circle(x, 33.5 + 55, 9)
        p.circle(585, 33.5 + 17.5, 11).circle(585, 33.5 + 57.5, 11)
        for x in (410, 470, 530):
            p.circle(x, 104.5 + 22, 9)
        return [(lab(t, q), p)]

    @part('0185711A00')
    def _(q):
        # 横撑：0185711A01 连接件(2.5mm C 形 288，腹板55，翼边30) + 3130510A02 连接板(6mm) ×2
        p, *_ = c_channel(2.5, 288, 55, 30, 30)
        a02 = plate('0185711A00.idw_图纸_3.dxf', (87.6, 103.7, 142.6, 133.7))
        return [(lab(2.5, q), p), (lab(6, 2 * q), a02)]

    @part('0120821A')
    def _(q):
        t = 1; w = bd(t)            # 挡片：U 形 10+25+10，长28
        p = Piece().rect(0, 0, 41.6, 28, 1)
        p.bend(9.15, 0, 9.15, 28, w).bend(32.45, 0, 32.45, 28, w)
        return [(lab(t, q), p)]

    @part('0120822A')
    def _(q):
        # 挡片：65号弹簧钢 1mm，65 + 5(折 30°)，展开 69.71（K=0.5,R=1 计算）
        L = 69.71
        p = Piece().outline([(0, 0, 1), (18, 0, 1), (18, L, 2), (0, L, 2)])
        p.poly([(0, 4.86), (18, 4.86)], False, '折弯线', linetype='CENTER', color=1, ltscale=0.5)
        p.circle(9, L - 5.5, 4.5).circle(9, L - 15.5, 4.5).circle(9, L - 60.5, 3.2)
        return [(lab(1, q, '65钢'), p)]

    @part('0120526A')
    def _(q):
        t = 2; w = bd(t)            # 撑箱片：底板 + 沿 80° 斜边翻起的侧板(外形57，R10/R30)
        P1, P2 = (0, 0), (21.16, 120)
        p = Piece()
        p.outline([P1, (200, 0, 5), (200, 25.0, 5), (166.16, 120, 10), P2, (-32.02, 129.374, 10), (-53.18, 9.374, 30)])
        p.bend(1.477, -0.26, 22.64, 119.74, w)
        for x in (15, 100, 185):
            p.circle(x, 5, 4.2)
        return [(lab(t, q), p)]

    @part('0183146A')
    def _(q):
        t = 3; w = bd(t)            # 阀岛护板：C 形 1200，腹板70，上翼边25，下翼边25(带3个凸耳至50)
        v = [(0, 0, 10)]
        for xc in (150, 600, 1050):
            v += [(xc - 20, 0, 10), (xc - 20, -25, 10), (xc + 20, -25, 10), (xc + 20, 0, 10)]
        v += [(1200, 0, 10), (1200, 110), (0, 110)]
        p = Piece().outline(v)
        p.bend(0, 22.5, 1200, 22.5, w).bend(0, 87.5, 1200, 87.5, w)
        for xc in (150, 600, 1050):
            p.circle(xc, -15, 11)
        web = extract_unbroken(DXF('0183146A.idw.dxf'), (96.5, 365.1, 686.0, 435.3))
        drop_concentric_outer(web)
        for k, data, a in web.ents:
            if k == 'CIRCLE':
                (cx, cy), r = data
                p.circle(cx - 0.087, 20 + cy - 0.12, 2 * r)
        return [(lab(t, q), p)]

    # ------------------------------------------------ 平板件
    def P(code, fname, region, t, keep=None, n=1):
        def f(q):
            return [(lab(t, q * n), plate(fname, region, keep_outline_d=keep))]
        PARTS[code] = f
    P('0120127A', '0120127A.idw.dxf', (62.0, 63.5, 109.0, 113.5), 10)
    P('0120160A', '0120160A.idw.dxf', (40.0, 103.9, 220.0, 123.9), 5)
    P('0181302A', '0181302A.idw.dxf', (56.4, 89.0, 216.4, 168.9), 10)
    P('0183113A', '0183113A.idw.dxf', (48.4, 115.0, 214.4, 131.0), 3)
    P('0183114A', '0183114A.idw.dxf', (24.9, 51.9, 110.9, 67.9), 3)
    P('0183118A', '0183118A.idw.dxf', (36.4, 38.6, 96.4, 83.6), 3)
    P('0183139A', '0183139A.idw.dxf', (78.2, 83.4, 164.2, 169.4), 3, keep=86)
    P('0183142A', '0183142A.idw.dxf', (15.3, 17.4, 29.3, 31.4), 4, keep=14)

    @part('0120203A')
    def _(q):
        return [(lab(5, q), Piece().circle(27.5, 27.5, 55).circle(27.5, 27.5, 22))]   # 螺杆压板 Φ55/Φ22

    @part('0183151A')
    def _(q):
        return [(lab(2, q), Piece().circle(9, 9, 18).circle(9, 9, 5.5))]               # 垫片 Φ18，沉头孔 Φ5.5

    def U(code, fname, region, t):
        def f(q):
            p = extract_unbroken(DXF(fname), region)
            drop_concentric_outer(p)
            return [(lab(t, q), p)]
        PARTS[code] = f
    U('0180189A', '0180189A.idw.dxf', (97.0, 227.9, 443.4, 258.1), 10)

    @part('0120612A')
    def _(q):
        # 连接板：3mm 扁条 1742.5x15（两端斜削为机加，下料按矩形），5-Φ5.5 沉头孔
        p = Piece().rect(0, 0, 1742.5, 15)
        for x in (45, 465, 885, 1305, 1722.5):
            p.circle(x, 7.5, 5.5)
        return [(lab(3, q), p)]

    @part('0180613A')
    def _(q):
        # 连接板：3mm 扁条 914.4x15（两端斜削为机加，下料按矩形），4-Φ5.5 沉头孔
        p = Piece().rect(0, 0, 914.4, 15)
        for x in (20, 440.4, 594.4, 894.4):
            p.circle(x, 7.5, 5.5)
        return [(lab(3, q), p)]
    U('0180181A', '0180181A.idw.dxf', (115.3, 480.7, 1090.5, 690.9), 5)

    # ------------------------------------------------ 组件
    @part('0120201A00')
    def _(q):
        # 输送腿01：A01 腿焊接01(20mm) + A02 腿焊接02(15mm) + A03 腿焊接03(2mm) + 方管50x50x4-225
        a01 = plate('0120201A00.idw_图纸_2.dxf', (104.0, 152.4, 284.1, 202.4))
        a02 = plate('0120201A00.idw_图纸_3.dxf', (92.9, 93.5, 142.9, 143.5))
        a03 = plate('0120201A00.idw_图纸_4.dxf', (106.9, 96.0, 156.9, 138.5))
        return [(lab(20, q), a01), (lab(15, q), a02), (lab(2, q), a03), (lab(225, q), tube(50, 4))]

    @part('0120731A00')
    def _(q):
        # 箱输送腿：A01 方管40x40-365(端部45°斜切) + A02 腿连接板1(10mm) + A03 腿连接板2(3mm,40x42.43) + A04 腿连接板3(15mm)
        a02 = plate('0120731A00.idw_图纸_2.dxf', (168.0, 119.5, 258.0, 209.5))
        a03 = Piece().outline([(0, 0, 7.5), (40, 0, 7.5), (40, 42.43), (0, 42.43)])
        a04 = plate('0120731A00.idw_图纸_4.dxf', (64.5, 55.1, 104.5, 95.1))
        return [(lab(365, q), Piece().rect(0, 0, 40, 40)), (lab(10, q), a02), (lab(3, q), a03), (lab(15, q), a04)]

    @part('0120817B00')
    def _(q):
        # 挡片：B01 挡片1(6mm 66x25, 3-Φ6.4) + B02 挡片2(3mm 33x20)
        b1 = Piece().rect(0, 0, 66, 25)
        for x in (24.5, 41, 57.5):
            b1.circle(x, 12.5, 6.4)
        return [(lab(6, q), b1), (lab(3, q), Piece().rect(0, 0, 33, 20))]

    @part('0120841A00')
    def _(q):
        # 挡片：A01 挡片1(6mm 25x17, Φ6.4) + A02 挡片2(3mm)
        a1 = Piece().rect(0, 0, 25, 17).circle(12.5, 8.5, 6.4)
        a2 = plate('0120841A00.idw_图纸_2.dxf', (78.7, 67.1, 98.7, 95.1))
        return [(lab(6, q), a1), (lab(3, q), a2)]

    @part('0180909A00')
    def _(q):
        # 主真空管：Φ51x2 管 2480 ×1、真空连接管 Φ51x2-90 ×4、真空连接1(3mm 板) ×4；封盖、真空接头为机加/冲压件不下料
        pipe = Piece().circle(25.5, 25.5, 51).circle(25.5, 25.5, 47)
        a01 = plate('0180909A00.idw_图纸_2.dxf', (105.0, 86.5, 170.0, 151.5))
        return [(lab(2480, q), pipe), (lab(90, 4 * q), pipe), (lab(3, 4 * q), a01)]

    # ------------------------------------------------ 复杂件：占位
    for c, t, note in [('0180621A', 2, '0180621A 待人工展开（C 形长件，端部 5° 折弯）'),
                       ('0185105A', 2, '0185105A 待人工展开（垂直 10° 弯折护栏挡板）'),
                       ('0185106A', 2, '0185106A 为0185105A镜像件，待人工展开'),
                       ('0185107A', 2, '0185107A 待人工展开（垂直 10° 弯折护栏挡板）'),
                       ('0185108A', 2, '0185108A 为0185107A镜像件，待人工展开'),
                       ('0185201A', 2, '0185201A 待人工展开（垂直 10° 弯折护栏挡板）'),
                       ('0185202A', 2, '0185202A 为0185201A镜像件，待人工展开'),
                       ('0185305A', 2, '0185305A 待人工展开（Φ1105 卷圆护栏挡板）'),
                       ('0185306A', 2, '0185306A 待人工展开（Φ895 卷圆护栏挡板）'),
                       ('0185720A', 2.5, '0185720A 待人工展开（长槽型侧板）'),
                       ('0185721A', 2.5, '0185721A 为0185720A镜像件，待人工展开'),
                       ('0185722A', 2.5, '0185722A 待人工展开（槽型侧板）'),
                       ('0185723A', 2.5, '0185723A 为0185722A镜像件，待人工展开')]:
        PARTS[c] = todo(t, note)
