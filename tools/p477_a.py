# -*- coding: utf-8 -*-
"""NO.477-NO.478：机壳类零件（7420701A00 / 7420714A00 / 7420702A00 / 7420705A / 7420715A / 7420716A / 7420717A）
全部为 Q235B，标签/BD 均按 Q235B。DXF 主视图均为 1:1 实际尺寸（已用标注值核对）。"""
import math

MAT = 'Q235B'


def register(C):
    L = lambda t, n: C.lab(t, n, MAT)
    W = lambda t: C.bd(t, MAT)

    def drop_thread_arcs(p):
        """去掉与孔同心的螺纹大径/沉孔圆弧（只留小径/通孔圆）"""
        cs = [d[0] for k, d, a in p.ents if k == 'CIRCLE']
        p.ents = [e for e in p.ents if not (e[0] == 'ARC' and any(
            abs(e[1][0][0] - x) < 0.05 and abs(e[1][0][1] - y) < 0.05 for x, y in cs))]
        return p

    def plate(fname, region):
        return drop_thread_arcs(C.plate(fname, region))

    def note_piece(s):
        """组件中无法可靠展开的子件：只放红字说明（无切割线），标签照常给出材料厚度和件数"""
        return C.Piece().text(0, 0, s, h=30, color=1)

    # ================================================================ 7420701A00 / 7420714A00 子件
    def p_101A07():             # 轮支架 5mm 平板，1-Φ13
        return plate('7420701A00.idw_图纸_2.dxf', (130, 180, 395, 300))

    def p_201A02():             # 电控箱固定板 3mm：底 290 + 立边 60，宽 350，4-M6
        t = 3; w = W(t)
        p = C.Piece().rect(0, 0, 290 + 60 - w, 350)
        p.bend(290 - w / 2, 0, 290 - w / 2, 350, w)
        for x in (60, 240):
            for y in (45, 305):
                p.tap(x, y, 'M6')
        return p

    def p_201A03():             # 电气接头挡板 1.5mm：底板(425x250 五边形) + 前翻边 25 + 端板 125(六边形)
        t = 1.5; w = W(t)       # BD 2.5
        rp, rg, rs = C.relief_params(t, w)
        xw = 425 - w / 2 + (0 - w / 2)          # 端板高度 h -> x = 422.5 + h
        hx = lambda h: 425 - w + h
        yf = w - 25                              # 前翻边边缘 y = -22.5
        a = math.tan(math.radians(30))
        xs = (250 - 132.1) / a                   # 斜边到顶边交点 x=204.21
        top_l = 250 - 23                         # 端板顶边（y=227 ~ 136.84）
        top_r = 250 - (125 - 46) / a - 0         # 端板顶平段终点 y（距前面 136.84）
        top_r = (125 - 46) / a                   # = 136.83
        p = C.Piece()
        p.outline([(hx(85.16), 250, 10), (hx(125), top_l, 10), (hx(125), top_r, 10), (hx(46), 0, 10),
                   (425 + rg, 0), (425 - rp, rp), (425 - rs, -rg), (425 - rs, yf), (0, yf, 10),
                   (0, 132.1, 10), (xs, 250, 10)])
        p.bend(0, w / 2, 425, w / 2, w)                    # 前翻边 90°
        p.bend(425 - w / 2, 0, 425 - w / 2, 250, w)        # 端板 90°
        for x in (100, 160, 220, 280, 340):
            p.circle(x, 40, 18)
        return p

    def p_701A04():             # 升降气缸固定板 8mm：L 形 140(+4.5 凸台) + 38，长 678，4-M10
        t = 8; w = W(t)         # BD 13.6
        yb = w - 38             # 下折边边缘 -24.4
        p = C.Piece()
        p.outline([(0, yb), (678, yb), (678, 140, 5), (539, 140), (539, 144.5), (489, 144.5), (489, 140),
                   (189, 140), (189, 144.5), (139, 144.5), (139, 140), (0, 140, 5)])
        p.bend(0, w / 2, 678, w / 2, w)
        for x in (304, 374):
            for y in (34.5, 104.5):
                p.tap(x, y, 'M10')
        return p

    def p_701A05():             # 导轨固定板 8mm 平板（12-M6 已按小径、2 腰孔）
        return plate('7420701A00.idw_图纸_7.dxf', (250, 750, 1720, 990))

    def p_701A06():             # 左右机壳底板 5mm 平板（Φ30-5深 在 5mm 板上即通孔）
        return plate('7420701A00.idw_图纸_8.dxf', (330, 895, 2090, 1225))

    def p_701A09():             # 左右机壳补强板 8mm 平板
        return plate('7420701A00.idw_图纸_9.dxf', (170, 478, 855, 568))

    @C.part('7420701A00')
    def _(q):
        # 机壳（BOM）：1 轮支架×2，3 电控箱固定板×1，4 电气接头挡板×1，5 右机壳×1，
        # 6 升降气缸固定板×1，7 导轨固定板×2，8 左右机壳底板×1，9 左右机壳补强板×1
        return [(L(5, 2 * q), p_101A07()),
                (L(3, q), p_201A02()),
                (L(1.5, q), p_201A03()),
                (L(5, q), note_piece('7420701A01 右机壳：5mm 大型多折弯空间件(含120°/150°斜折、拼缝满焊)，待人工展开')),
                (L(8, q), p_701A04()),
                (L(8, 2 * q), p_701A05()),
                (L(5, q), p_701A06()),
                (L(8, q), p_701A09())]

    @C.part('7420714A00')
    def _(q):
        # 左机壳焊接位置图（BOM）：1 轮支架×2，3 电控箱固定板×1，4 升降气缸固定板×1，5 导轨固定板×2，
        # 6 左右机壳底板×1，7 左右机壳补强板×1，8 左机壳×1
        return [(L(5, 2 * q), p_101A07()),
                (L(3, q), p_201A02()),
                (L(8, q), p_701A04()),
                (L(8, 2 * q), p_701A05()),
                (L(5, q), p_701A06()),
                (L(8, q), p_701A09()),
                (L(5, q), note_piece('7420714A01 左机壳：5mm 大型多折弯空间件(含120°/150°斜折、拼缝满焊)，待人工展开'))]

    # ================================================================ 7420702A00 底层背板
    def p_702A01():
        # 背板 3mm：底 1440x1455，四周立边 100；上、左、右立边带 25 内翻边（角部 45° 斜接），
        # 下立边带 12 外翻边（Z 形，外形 15）；四角 V 形释放槽（左右立边全宽，上下立边内缩 s）
        t = 3; w = W(t)         # BD 5
        rp, rg, rs = C.relief_params(t, w)      # 6, 1, 3.1
        X, Y = 1440, 1455
        e = 100 + 25 - 2 * w    # 立边+内翻边 展开伸出 115
        eb = 105                # 下立边+外翻边（中性层：6+88+9 直段 + 2×7 弯曲）展开伸出 105
        r2 = w - 100 + w / 2    # 第二道折弯红线距外形线 -92.5
        c = 2.12                # 翻边 45° 斜接口偏离对角线量（图纸 3mm 间隙）
        mx = e - (100 - w) - c  # 立边端斜接起点（距端线）87.88
        p = C.Piece()
        p.outline([(-e, Y - e + 100 - w + c + (e - (100 - w)) - e + (100 - w)),  # placeholder, replaced below
                   ])
        p.ents = []
        ym = Y - (e - mx)       # 侧翻边斜接终点 y = 1427.88
        pts = [(-e, ym), (-e, 0), (-rg, 0), (rp, rp), (rs, -rg), (rs, -eb),
               (X - rs, -eb), (X - rs, -rg), (X - rp, rp), (X + rg, 0), (X + e, 0), (X + e, ym),
               (X + mx, Y), (X + rg, Y), (X - rp, Y - rp), (X - rs, Y + rg),
               (X - rs, Y + (100 - w) - w + w + rs - c + 0 * 0)]
        # 上翻边斜接：x = (y - (Y+90)) + c  (左)，在 x=rs 处 y = Y + 90 + rs - c
        yt = Y + (100 - w) - w / 2 - w / 2 + rs - c + w      # = Y+90+0.98
        yt = Y + 90 + rs - c
        pts = pts[:-1] + [(X - rs, yt), (X - (e - 90 + c), Y + e), (e - 90 + c, Y + e), (rs, yt),
                          (rs, Y + rg), (rp, Y - rp), (-rg, Y), (-mx, Y)]
        p.outline(pts)
        # 折弯线（90°：红+蓝，BD 5）
        p.bend(w / 2, 0, w / 2, Y, w).bend(X - w / 2, 0, X - w / 2, Y, w)
        p.bend(0, w / 2, X, w / 2, w).bend(0, Y - w / 2, X, Y - w / 2, w)
        yl = Y - (e - mx) + (e + r2)            # 侧翻边折弯线上端（落在斜接线上）
        p.bend(r2, 0, r2, yl, w).bend(X - r2, 0, X - r2, yl, w)
        p.bend(rs, r2, X - rs, r2, w)           # 下外翻边（反向折）
        xt = (Y - r2) - (Y + 90) + c            # 上翻边折弯线端点（斜接线上）
        p.bend(xt, Y - r2, X - xt, Y - r2, w)
        # 底面：4 个 R10 方口、3-Φ11、3 腰孔(11 宽)、8 个 5.5 小腰孔
        for x0, x1 in ((25, 105), (1325, 1420)):
            for y0 in (240, 1050):
                p.rect(x0, y0, x1, y0 + 150, 10)
        for y in (85, 720, 1355):
            p.circle(60, y, 11)
            p.slot(1330, y, 1390, y, 11)
        for x in (370, 1070):
            for y in (22.5, 482.5, 962.5, 1422.5):
                p.slot(x, y, x, y + 10, 5.5)
        # 下立边（h=30/70）：4-Φ11 + 4 腰孔；上立边：7-Φ11（h=80 两个，h=35 五个）
        for h in (30, 70):
            y = w - h
            p.circle(60, y, 11).circle(160, y, 11)
            p.slot(1230, y, 1290, y, 11).slot(1330, y, 1390, y, 11)
        p.circle(40, Y - w + 80, 11).circle(1400, Y - w + 80, 11)
        for x in (140, 390, 720, 1050, 1300):
            p.circle(x, Y - w + 35, 11)
        return p

    def p_702A02():
        # 补强钣金 3mm：几字(帽)形，4 处 135° 折弯（内 R3，中性层 K=0.48），长 1434，4-R5
        t = 3; rn = 3 + 0.48 * t
        arc = math.radians(45) * rn             # 3.487
        segs = [13.76, arc, 81.12, arc, 95.03, arc, 81.12, arc, 13.76]
        Wd = sum(segs)                          # 298.74
        p = C.Piece().rect(0, 0, 1434, Wd, 5)
        y = 0
        for i, s in enumerate(segs):
            if i % 2 == 1:
                p.bend(0, y + s / 2, 1434, y + s / 2, 0, red_only=True)
            y += s
        return p

    @C.part('7420702A00')
    def _(q):
        return [(L(3, q), p_702A01()), (L(3, 2 * q), p_702A02())]

    # ================================================================ 7420705A / 7420716A 机壳下/上挡板（3mm）
    def baffle(extra_slots=()):
        """主板 1405.46 →30°折→ 斜板 167.39 →150°回折→ 端唇 40；上下翻边 60（斜板段翻边上沿水平）；
        左端立板 80 + 上下三角折片（与翻边 45° 斜接拼缝满焊）。坐标：x 沿长度(端板外面=0)，y 沿宽 807.5。"""
        t = 3; w = W(t)                          # BD 5
        K, R = 0.48, 3
        d30 = C.bd_angle(t, 30, K, R)            # 0.891
        d150 = C.bd_angle(t, 150, K, R)          # 33.16
        Bw = 807.5
        A1 = 1405.46                             # 第一折外形交点
        x0 = A1 - d30                            # 斜板 s -> x = x0 + s
        r1 = A1 - d30 / 2                        # 30° 折弯红线
        A2 = x0 + 167.39
        r2 = A2 - d150 / 2                       # 150° 折弯红线
        xe = A2 - d150 + 40                      # 端唇边缘
        xb2 = x0 + 145.0                         # 斜板翻边止端（=150°弯起点）
        fh = w - 60                              # 翻边边缘 y=-55
        H = 80                                   # 端立板高
        c45 = 0.7                                # 斜接缝偏移

        def side(sg):
            """下侧(sg=1)外形点；上侧用 y -> Bw - y 镜像"""
            Y = (lambda y: y) if sg > 0 else (lambda y: Bw - y)
            ap1 = ((w + w + c45 - c45) / 2 + 0.0, 0)
            # 端立板三角折片斜接线 y = x + 0.7；翻边斜接 x + y = 5.7；交点即 V 槽尖点
            xa = (2 * w - c45 - c45) / 2 + 0.0
            xa = (5.7 - 0.7) / 2; ya = xa + 0.7
            # 30° 处 V 槽（两侧翻边斜接线交点）
            k = math.tan(math.radians(15))
            xp1 = x0 + 0.0                       # 占位
            return xa, ya
        xa, ya = side(1)
        k = math.tan(math.radians(15))
        # 主板翻边端 / 斜板翻边端（h=6 -> y=-1，h=60 -> y=-55），交于 30° 红线
        xA = r1 - k * (6.27); xB = r1 + k * 6.27
        P1h6 = (r1 - k * (6.27 - 0), -1)
        def fe1(y):     # 主板翻边斜接线
            return r1 - k * (ya1 - y)
        ya1 = 5.27
        def fe2(y):
            return r1 + k * (ya1 - y)
        # 斜板翻边上沿：h=60 至 s=56.07 处 R10 转为图中水平线，到 s=145.0 时 h=8.66
        s_c = 56.07
        lo = [(-H + w, fh, 10), (-(60 - w + c45) + 0.0, fh), (xa, ya), (60.7, fh), (fe1(fh), fh), (r1, ya1),
              (fe2(fh), fh), (x0 + s_c, fh, 10), (xb2, w - 8.66), (xb2, 6), (xe, 6, 10)]
        lo[1] = (fh - c45, fh)                   # 三角折片斜接线与 y=-55 交点 x=-55.7
        up = [(x, Bw - y) + tuple(r) for x, y, *r in reversed(lo)]
        p = C.Piece()
        p.outline(lo + up)
        # 折弯线
        p.bend(w / 2, ya, w / 2, Bw - ya, w)                                   # 端立板
        for yy in (w / 2, Bw - w / 2):
            p.bend(-H + w, yy, (yy if yy < Bw / 2 else Bw - yy) - c45 if False else (w / 2 - c45 if yy < Bw / 2 else w / 2 - c45), yy, w)
        p.ents = p.ents[:-6]                                                   # 重画三角折片/翻边折弯线
        xt = w / 2 - c45                                                        # 折片折弯线止于斜接线
        xf = 5.7 - w / 2                                                        # 翻边折弯线起于斜接线
        for yy in (w / 2, Bw - w / 2):
            p.bend(-H + w, yy, xt, yy, w)
            p.bend(xf, yy, fe1(w / 2), yy, w)
            p.bend(fe2(w / 2), yy, xb2, yy, w)
        p.bend(r1, ya1, r1, Bw - ya1, 0, red_only=True)                         # 30°
        p.bend(r2, 6, r2, Bw - 6, 0, red_only=True)                             # 150° 回折
        # 孔：翻边 5-Φ11、折片 Φ16，上下对称；端立板 2-Φ11；斜板 2 腰孔 7 宽
        for yy, sg in ((0, 1), (Bw, -1)):
            for x in (100, 600, 1100):
                p.circle(x, yy + sg * (w - 35), 11)
            p.circle(w - 65, yy + sg * (w - 30), 11)                           # 折片 u=30,h=65
            p.circle(w - 40, yy + sg * (w - 20), 16)                           # 折片 u=20,h=40
            p.circle(x0 + 105.72, yy + sg * (w - 14.015), 11)                   # 斜板翻边
        for y in (203.75, 603.75):
            p.circle(w - 40, y, 11)
        for s in (102, 127):
            p.slot(x0 + s, 396.25, x0 + s, 411.25, 7)
        for x0_, y0_, x1_, y1_, sw in extra_slots:
            p.slot(x0_, y0_, x1_, y1_, sw)
        return p

    @C.part('7420705A')
    def _(q):
        return [(L(3, q), baffle())]

    @C.part('7420716A')
    def _(q):
        # 同 7420705A，另在主板距端板外面 100 处有 3 个 18 宽竖腰孔（长 50+18）
        sl = [(100, y, 100, y + 50, 18) for y in (567.5, 647.5, 727.5)]
        return [(L(3, q), baffle(sl))]

    C.mirror('7420717A', '7420716A')

    # ================================================================ 7420715A 上层背板（3mm）
    @C.part('7420715A')
    def _(q):
        # 主板 1440x807.5；上下翻边 60；两端立板 95 + 上下三角折片（45° 斜接拼缝满焊）
        t = 3; w = W(t)
        X, Bw, H = 1440, 807.5, 95
        fh = w - 60; c45 = 0.71
        xa = (5.7 - c45) / 2; ya = xa + c45
        lo = [(-H + w, fh, 10), (fh - c45, fh), (xa, ya), (5.7 - fh, fh),
              (X - (5.7 - fh), fh), (X - xa, ya), (X - (fh - c45), fh), (X + H - w, fh, 10)]
        up = [(x, Bw - y) + tuple(r) for x, y, *r in reversed(lo)]
        p = C.Piece().outline(lo + up)
        p.bend(w / 2, ya, w / 2, Bw - ya, w).bend(X - w / 2, ya, X - w / 2, Bw - ya, w)
        for yy in (w / 2, Bw - w / 2):
            p.bend(-H + w, yy, w / 2 - c45, yy, w)
            p.bend(5.7 - w / 2, yy, X - (5.7 - w / 2), yy, w)
            p.bend(X - (w / 2 - c45), yy, X + H - w, yy, w)
        for yy, sg in ((0, 1), (Bw, -1)):
            for x in (140, 390, 720, 1050, 1300):
                p.circle(x, yy + sg * (w - 35), 11)
            for x in (w - 80, X - w + 80):                                     # 折片 u=40,h=80
                p.circle(x, yy + sg * (w - 40), 11)
        for y in (203.75, 603.75):
            p.circle(60, y, 11)
            p.slot(1330, y, 1390, y, 11)
        for x in (370, 1070):
            for y in (20, 398.75, 777.5):
                p.slot(x, y, x, y + 10, 5.5)
        return [(L(3, q), p)]
