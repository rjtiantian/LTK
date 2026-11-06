# -*- coding: utf-8 -*-
"""NO.482 第 e 批（28 行）：机身板、横撑固定板、尾部封板、支撑腿、接水槽、电机安装板、链轮护罩等。
外形尺寸法：展开长 = 各段外形和 − 折弯数 × BD；孔位取 DWG 矢量。说明与核对见 482/notes_e.md。"""
import math
from sheetlib import fillet_path, BEND


def register(C):
    def outline(p, verts):
        """同 Piece.outline，但去掉圆角切点和相邻顶点重合产生的零长线段"""
        verts = [tuple(v) + (0.0,) * (3 - len(v)) for v in verts]
        pts = fillet_path(verts, True)
        out = []
        for i, pt in enumerate(pts):
            nx = pts[(i + 1) % len(pts)]
            if abs(pt[0] - nx[0]) < 1e-6 and abs(pt[1] - nx[1]) < 1e-6:
                if abs(pt[2]) > 1e-9:          # 圆弧起点不能丢，丢的是下一个点的直线段起点
                    nx[2] = pt[2]
                continue
            out.append(list(pt))
        return p.poly([tuple(q) for q in out], True)

    def bline(p, a, b, color):
        attr = dict(linetype='CENTER', color=color)
        if color == 1:
            attr['ltscale'] = 0.5
        return p.poly([a, b], False, BEND, **attr)

    def red(p, x0, y0, x1, y1):
        return p.bend(x0, y0, x1, y1, 0, red_only=True)

    # ================================================================== 机身板 2.5mm（Z 向两翼 + 中部梯形）
    def web_common(p, holes10, holes9, slots, big):
        for x, y in holes10:
            p.circle(x, y, 10.5)
        for x, y in holes9:
            p.circle(x, y, 9)
        for s in slots:
            p.slot(*s)
        for x, y, d in big:
            p.circle(x, y, d)

    @C.part('1610101A')
    def _(q):
        # 下翼 20（外面 y=140）、上翼 17.5（外面 y=300）；左端耳板到 311；中部梯形 160/250 下探到 y=0
        t = 2.5; w = C.bd(t)
        yb, yt = 140 + w / 2, 300 - w / 2             # 红线 142 / 298
        fb, ft = yb - (20 - w / 2), yt + (17.5 - w / 2)   # 翼边边缘 124 / 313.5
        p = C.Piece()
        p.outline([(320, 0, 5), (480, 0, 5), (525, 140), (525, 146.25), (527.5, 146.25), (527.5, fb, 5),
                   (2000, fb, 5), (2000, ft, 5), (50, ft, 5), (50, 295), (49, 295), (49, 311, 5), (0, 311, 5),
                   (0, fb, 5), (272.5, fb, 5), (272.5, 146.25), (275, 146.25), (275, 140)])
        p.bend(0, yb, 272.5, yb, w).bend(527.5, yb, 2000, yb, w).bend(50, yt, 2000, yt, w)
        web_common(p,
                   [(200, 265), (200, 175), (400, 195), (400, 159.7), (376.1, 127.7), (423.9, 127.7), (470, 15), (330, 15)],
                   [(x, y) for x in (600, 1000, 1400, 1800, 1975) for y in (175, 265)],     # 图注 8-Φ9，视图 10 个
                   [(70, 210, 70, 240, 8.5), (15, 222, 15, 232, 10.5), (15, 162, 15, 172, 10.5),
                    (270, 175, 320, 175, 10.5), (430, 175, 480, 175, 10.5)],
                   [(400, 75, 60), (400, 6, 4.2), (32, 284, 8.5)])
        for x in (20, 220, 252.5, 547.5, 580, 931.75, 1283.5, 1635.25, 1987):    # 9-M5 只在下翼，距腹板外面 14
            p.tap(x, yb - (14 - w / 2), 'M5')
        return [(C.lab(t, q), p)]
    C.mirror('1610102A', '1610101A')                  # 制作方式表：镜像制作 1610102A

    @C.part('1610103A')
    def _(q):
        # 下翼 20 通长、上翼 17.5 到 x=1950；右端耳板到 171
        t = 2.5; w = C.bd(t)
        yb, yt = w / 2, 160 - w / 2                   # 红线 2 / 158
        fb, ft = yb - (20 - w / 2), yt + (17.5 - w / 2)   # -16 / 173.5
        p = C.Piece()
        p.outline([(0, fb, 5), (2000, fb, 5), (2000, 171, 5), (1951, 171, 5), (1951, 155), (1950, 155),
                   (1950, ft, 5), (0, ft, 5)])
        p.bend(0, yb, 2000, yb, w).bend(0, yt, 1950, yt, w)
        for x in (25, 200, 600, 1000, 1400, 1800):
            p.circle(x, 35, 9).circle(x, 125, 9)
        p.circle(1940, 90, 8.5).circle(1968, 144, 8.5)
        p.slot(1985, 22, 1985, 32, 10.5).slot(1985, 82, 1985, 92, 10.5)
        for x in (13, 364.75, 716.5, 1068.25, 1420, 1771.75, 1987):               # 7-M5 只在下翼
            p.tap(x, yb - (14 - w / 2), 'M5')
        return [(C.lab(t, q), p)]
    C.mirror('1610104A', '1610103A')

    @C.part('1610201A')
    def _(q):
        t = 2.5; w = C.bd(t)
        yb, yt = 140 + w / 2, 300 - w / 2
        fb, ft = yb - (20 - w / 2), yt + (17.5 - w / 2)
        p = C.Piece()
        p.outline([(420, 0, 5), (580, 0, 5), (625, 140), (625, 146.25), (627.5, 146.25), (627.5, fb, 5),
                   (1000, fb, 5), (1000, 311, 5), (951, 311, 5), (951, 295), (950, 295), (950, ft, 5),
                   (50, ft, 5), (50, 295), (49, 295), (49, 311, 5), (0, 311, 5),
                   (0, fb, 5), (372.5, fb, 5), (372.5, 146.25), (375, 146.25), (375, 140)])
        p.bend(0, yb, 372.5, yb, w).bend(627.5, yb, 1000, yb, w).bend(50, yt, 950, yt, w)
        web_common(p,
                   [(100, 265), (100, 175), (200, 265), (200, 175), (800, 265), (800, 175), (900, 265), (900, 175),
                    (72, 224), (928, 224), (580, 175), (500, 195), (500, 159.7), (476.1, 127.7), (523.9, 127.7),
                    (570, 15), (430, 15)],                    # 图注 18-Φ10.5，视图 17 个
                   [(32, 284), (968, 284)],
                   [(15, 162, 15, 172, 10.5), (15, 222, 15, 232, 10.5), (985, 162, 985, 172, 10.5),
                    (985, 222, 985, 232, 10.5), (370, 175, 420, 175, 10.5)],
                   [(500, 75, 60), (500, 6, 4.2)])
        for x in (20, 320, 352.5, 647.5, 680, 980):                               # 6-M5 只在下翼
            p.tap(x, yb - (14 - w / 2), 'M5')
        return [(C.lab(t, q), p)]
    C.mirror('1610202A', '1610201A')

    # ================================================================== 1610105A00 横撑固定板
    @C.part('1610105A00')
    def _(q):
        # 单张焊接图拆 2 种：折弯横撑 2.5mm（30 + 30 + 18，45° 斜边，长 505）×1 + 两端板 5mm ×2
        # 同 NO.373 1450211A00：展开 72.31，90° 红线 y=28（BD4），135° 红线 y=55.16（历史人工值）
        t = 2.5; w = C.bd(t)
        p = C.Piece().rect(0, 0, 505, 72.31)
        p.bend(0, 28, 505, 28, w)
        red(p, 0, 55.16, 505, 55.16)
        for i in range(11):                           # 11-Φ8.5 “-2.5 深” = 通孔，距端 40（总长 515 算 45）
            p.circle(40 + 42.5 * i, 15, 8.5)
        end = C.plate('1610105A00.idw.dxf', (804.411, 319.873, 834.411, 364.873))   # 30x45，3 角 R5，1-M10
        return [(C.lab(t, q), p), (C.lab(5, 2 * q), end)]

    # ================================================================== 尾部封板
    def nut_plate_157():
        # 1570902A02 螺母板 5mm：85x20，C5，R3，2-M8（与 NO.451 1570902A00 的 5mm 件一致）
        return C.plate('1610306A00.idw_图纸_3.dxf', (22.504, 55.802, 107.504, 75.802))

    @C.part('1610106A00')
    def _(q):
        # A01 2mm：下翼 25 + 腹板 140 + 上斜边 12（140°，偏折 40°），长 515，展开 173.15
        t = 2; w = C.bd(t)
        d40 = C.bd_angle(t, 40, 0.48, t)              # 0.85
        y1 = 25 - w / 2
        y2 = y1 + 140 - w / 2 - d40 / 2
        H = y2 - d40 / 2 + 12
        p = C.Piece().rect(0, 0, 515, H, 5)           # 斜边角 R5 图示；下翼角未画，按“未注圆角 R5”
        p.bend(0, y1, 515, y1, w)
        red(p, 0, y2, 515, y2)
        Y = lambda s: y1 + (s - w / 2)                # 腹板上距下翼外面 s
        p.slot(182.5, Y(25), 182.5, Y(75), 11)
        p.slot(307.5, Y(50), 357.5, Y(50), 11)
        a02 = C.plate('1610106A00.idw_图纸_3.dxf', (97.569, 118.497, 192.569, 141.497))   # 1430581A02 螺纹板 5mm
        return [(C.lab(t, q), p), (C.lab(5, 2 * q), a02)]

    def seal_plate(L, tab_left, sv, sh, m10x=None):
        """封板 3mm：下翼 25 通长 + 腹板到上翼外面 145 + 上翼 19 + 端部耳板到 164（3.5 宽缺口把耳板和上翼分开）
        L 长；tab_left 耳板在左；sv 竖腰孔 x（y 25~75）；sh 横腰孔左圆心 x（长 50，y=50）；m10x 2-M10 的 x（y 35 / 125）"""
        t = 3; w = C.bd(t)
        y1, y2 = w / 2, 145 - w / 2                   # 2.5 / 142.5
        fb, ft = y1 - (25 - w / 2), y2 + (19 - w / 2)  # -20 / 159
        p = C.Piece()
        if tab_left:
            verts = [(0, fb, 5), (L, fb, 5), (L, ft, 5), (56.5, ft, 5), (56.5, 125), (53, 125), (53, 164, 5), (0, 164, 5)]
            p.bend(56.5, y2, L, y2, w)
        else:
            verts = [(0, fb, 5), (L, fb, 5), (L, 164, 5), (L - 53, 164, 5), (L - 53, 125), (L - 56.5, 125),
                     (L - 56.5, ft, 5), (0, ft, 5)]
            p.bend(0, y2, L - 56.5, y2, w)
        p.outline(verts)
        p.bend(0, y1, L, y1, w)
        p.slot(sv, 25, sv, 75, 11)
        p.slot(sh, 50, sh + 50, 50, 11)
        if m10x is not None:
            p.tap(m10x, 35, 'M10').tap(m10x, 125, 'M10')
        return p

    @C.part('1610306A00')
    def _(q):
        return [(C.lab(3, q), seal_plate(500, False, 175, 300)), (C.lab(5, 2 * q), nut_plate_157())]

    @C.part('1610307A00')
    def _(q):
        return [(C.lab(3, q), seal_plate(500, True, 325, 150, 100)), (C.lab(5, 2 * q), nut_plate_157())]

    @C.part('1610340A00')
    def _(q):
        return [(C.lab(3, q), seal_plate(600, True, 375, 200, 100)), (C.lab(5, 2 * q), nut_plate_157())]

    # ================================================================== 支撑腿
    def foot_143():
        # 1430022A 支撑腿件 10mm：60x40，4 角 R5，M16（小件图只在 1610330A00 第 3 页）
        return C.plate('1610330A00.idw_图纸_3.dxf', (81.518, 113.954, 141.518, 153.954))

    def leg_157(hole_d, slot_w):
        """1570904A01 支撑安装件 5mm：60→40 窄头 + 45° 斜边；Φd + 中径 R90 圆弧腰孔（±5°，中部带同径圆）"""
        t = 5
        d45 = C.bd_angle(t, 45, 0.48, t)              # 2.47
        V = 142.071; S = 61.467                       # 竖段、斜段外形（到外面交点）
        T = V + S - d45                               # 展开 201.07
        yr = S - d45 / 2                              # 红线 60.23
        A, B = T - 91, T - 81
        p = C.Piece()
        p.outline([(0, 0, 5), (60, 0, 5), (60, A, 5), (50, B, 5), (50, T, 5), (10, T, 5), (10, B, 5), (0, A, 5)])
        red(p, 0, yr, 60, yr)
        cx, cy = 30, T - 103
        p.circle(cx, cy, hole_d)
        R, hw, rc = 90.0, slot_w / 2, hole_d / 2
        ro, ri = R + hw, R - hw
        off = lambda r: math.degrees(math.acos((r * r + R * R - rc * rc) / (2 * r * R)))   # 半径 r 与同径圆的交点偏角
        ao, ai = off(ro), off(ri)
        p.arc(cx, cy, ro, 85, 90 - ao).arc(cx, cy, ro, 90 + ao, 95)
        p.arc(cx, cy, ri, 85, 90 - ai).arc(cx, cy, ri, 90 + ai, 95)
        pol = lambda a, r=R: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        e0, e1 = pol(85), pol(95)
        p.arc(e0[0], e0[1], hw, 265, 85).arc(e1[0], e1[1], hw, 95, 275)
        # 中部同径圆：上弧到外缘交点、下弧到内缘交点
        cc = (cx, cy + R)
        pt = lambda r, a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        ang = lambda q: math.degrees(math.atan2(q[1] - cc[1], q[0] - cc[0]))
        p.arc(cc[0], cc[1], rc, ang(pt(ro, 90 - ao)), ang(pt(ro, 90 + ao)))
        p.arc(cc[0], cc[1], rc, ang(pt(ri, 90 + ai)) % 360, ang(pt(ri, 90 - ai)) % 360)
        return p

    def leg_set(q, tubes, hole_d=11, slot_w=10.5, n=2):
        """tubes: [(a, b, 壁厚, 长, 每台根数)]；n = 1570904A01 / 1430022A 每台件数"""
        out = [(C.lab(L, m * q), C.tube_rect(a, b, t)) for a, b, t, L, m in tubes]
        out.append((C.lab(5, n * q), leg_157(hole_d, slot_w)))
        out.append((C.lab(10, n * q), foot_143()))
        return out

    @C.part('1610108A00')
    def _(q):
        # 方管 A40x60x3-L951-45 / A40x60x2-L951-45 / 40x40x2-L526；本单 1570904A01 图（第 2 页）为 Φ11 + 10.5 腰孔
        return leg_set(q, [(40, 60, 3, 951, 1), (40, 60, 2, 951, 1), (40, 40, 2, 526, 1)])

    @C.part('1610323A00')
    def _(q):
        # 单张总图：1570904A01 无小件图，总图视图为 Φ11 + 10.5 腰孔
        return leg_set(q, [(40, 60, 3, 323, 1), (40, 60, 2, 323, 1), (40, 40, 2, 376, 1)])

    @C.part('1610330A00')
    def _(q):
        # 本单第 2 页 1570904A01 小件图是 Φ9 + 8.5 腰孔（同页总图画的是 Φ11），照小件图，见 notes 需复核
        return leg_set(q, [(40, 60, 3, 323, 1), (40, 60, 2, 323, 1), (40, 40, 2, 511, 1)], hole_d=9, slot_w=8.5)

    @C.part('1610335A00')
    def _(q):
        # 单腿：方管 A40x60x2-L323-45 ×1 + 1570904A01 ×1（总图 Φ11）+ 1430022A ×1
        return leg_set(q, [(40, 60, 2, 323, 1)], n=1)

    # ================================================================== 接水槽 1.2mm（四边翻边，长边 25 / 短边 16.2，都带 8 卷边）
    T_TRAY = 1.2; W_TRAY = C.bd(T_TRAY)                # BD 2
    K_HEM = math.pi * (0.3 + 0.485 * T_TRAY) / 2       # 卷边（内 R0.3）半弧长 1.385

    def tray(L, Wd, hole=None, lip=None):
        """L x Wd 外形；4 角 V 形释放槽（长边翻边全宽、短边内缩 s）。
        翻边 H 卷 8：基红线 → 卷边红线 = H − 1.115，卷边红线 → 边缘 = 7.885（1434023A 等历史件 25 边为 23.83）。
        lip = (外形长, BD)：右端不做翻边，改小角度舌边（只画红线）"""
        t, w = T_TRAY, W_TRAY
        rp, rg, rs = C.relief_params(t, w)             # 2.4, 0.4, 1.3
        h1 = lambda H: (2.4 - w / 2) + (H - 2.4 - 1.5) + K_HEM   # 基红线到卷边红线
        h2 = K_HEM + 8 - 1.5                                      # 卷边红线到边缘
        yl = w / 2 - h1(25) - h2                       # 长边翻边边缘（-30.77）
        xe = w / 2 - h1(16.2) - h2                     # 短边翻边边缘（-21.97）
        left = [(0, Wd + rg), (rp, Wd - rp), (-rg, Wd - rs), (xe, Wd - rs), (xe, rs), (-rg, rs), (rp, rp), (0, -rg)]
        if lip:
            d = lip[1]; xr = L - d / 2; xl = L - d + lip[0]
            right = [(L, -rg), (L - rp, rp), (xl, rp, 5), (xl, Wd - rp, 5), (L - rp, Wd - rp), (L, Wd + rg)]
        else:
            right = [(L, -rg), (L - rp, rp), (L + rg, rs), (L - xe, rs), (L - xe, Wd - rs), (L + rg, Wd - rs),
                     (L - rp, Wd - rp), (L, Wd + rg)]
        p = C.Piece()
        p.outline([(0, yl), (L, yl)] + right + [(L, Wd - yl), (0, Wd - yl)] + left)
        # 长边基线：端点落在 V 边上（红 y=1、蓝 y=0 / 2）
        vx = lambda y: rp * (y + rg) / (rp + rg)
        for yy, c in ((w / 2, 1), (0, 5), (w, 5)):
            a = vx(yy)
            bline(p, (a, yy), (L - a, yy), c)
            bline(p, (a, Wd - yy), (L - a, Wd - yy), c)
        # 短边基线：红 x=1、蓝 x=0 / 2
        vy = lambda x: rs + (rp - rs) * (x + rg) / (rp + rg)
        for xx, c in ((w / 2, 1), (0, 5), (w, 5)):
            a = vy(xx)
            bline(p, (xx, a), (xx, Wd - a), c)
            if not lip:
                bline(p, (L - xx, a), (L - xx, Wd - a), c)
        if lip:
            red(p, xr, rp, xr, Wd - rp)
        # 卷边（180°）只画红线
        y2 = w / 2 - h1(25)
        red(p, 0, y2, L, y2); red(p, 0, Wd - y2, L, Wd - y2)
        x2 = w / 2 - h1(16.2)
        red(p, x2, rs, x2, Wd - rs)
        if not lip:
            red(p, L - x2, rs, L - x2, Wd - rs)
        if hole:
            p.circle(*hole)
        return p

    @C.part('1610110A')
    def _(q):
        return [(C.lab(T_TRAY, q), tray(2000, 515, hole=(1950, 257.5, 30)))]

    @C.part('1610111A')
    def _(q):
        # 左端短边翻边 16.2 + 卷边；右端 165° 舌边 10（偏折 15°），R5
        return [(C.lab(T_TRAY, q), tray(3000, 515, lip=(10, C.bd_angle(T_TRAY, 15, 0.48, T_TRAY))))]

    # ================================================================== 1610141A 线槽安装板 3mm（U 形）
    @C.part('1610141A')
    def _(q):
        # 腹板外形 66 + 两侧板 63，长 100；侧板再向左伸 40（高 57）；展开 182
        t = 3; w = C.bd(t)
        y1, y2 = 63 - w / 2, 63 - w / 2 + 66 - w        # 60.5 / 121.5
        H = y2 + 63 - w / 2                             # 182
        p = C.Piece()
        p.outline([(0, 0, 5), (40, 0, 5), (140, 48, 5), (140, H - 48, 5), (40, H, 5), (0, H, 5), (0, H - 57, 5),
                   (40, H - 57), (40, 57), (0, 57, 5)])
        p.bend(40, y1, 140, y1, w).bend(40, y2, 140, y2, w)
        for y0, y1s in ((10, 20), (37, 47)):            # 2 腰孔 9 宽，两侧板都有
            p.slot(20, y0, 20, y1s, 9)
            p.slot(20, H - y1s, 20, H - y0, 9)
        p.circle(60, H / 2, 9).circle(100, H / 2, 9)
        return [(C.lab(t, q), p)]

    # ================================================================== 电机安装板
    def motor_plate(L, win, six, slots, phi7, s7):
        """板 3mm：下翼 120（宽到两端各缩 30）+ 腹板 175 + 上翼 40（通长）；下部两端 R6 / R3 避让"""
        t = 3; w = C.bd(t)
        y1, y2 = w / 2, 175 - w / 2                     # 2.5 / 172.5
        fb, ft = y1 - (120 - w / 2), y2 + (40 - w / 2)  # -115 / 210
        p = C.Piece()
        p.outline([(30, fb), (L - 30, fb), (L - 30, 26, 3), (L, 26, 6), (L, ft), (0, ft), (0, 26, 6), (30, 26, 3)])
        p.bend(30, y1, L - 30, y1, w).bend(0, y2, L, y2, w)
        p.rect(win[0], 20, win[1], 155, 5)              # 方窗 135 高，R5
        p.circle(six, 65, 6.5).circle(six, 135, 6.5)
        for x in slots:
            p.slot(x, 50, x, 70, 6.5).slot(x, 135, x, 155, 6.5)
        for x in phi7:                                  # “-3 深”=通孔
            p.circle(x, y2 + (s7 - w / 2), 7)
        return p

    def rib(x0, x1):
        """加强筋 3mm：146 + 33 + 26（Z 形），宽 117，展开 195；2-Φ9 距 26 边外面 18"""
        t = 3; w = C.bd(t)
        y1 = 146 - w / 2; y2 = y1 + 33 - w; H = y2 + 26 - w / 2     # 143.5 / 171.5 / 195
        p = C.Piece()
        p.outline([(0, 0, 3), (37, 0), (117, 122, 5), (117, H), (0, H, 3)])
        p.bend(0, y1, 117, y1, w).bend(0, y2, 117, y2, w)
        p.circle(x0, y2 - (18 - w / 2), 9).circle(x1, y2 - (18 - w / 2), 9)
        return p

    @C.part('1610305A00')
    def _(q):
        a01 = motor_plate(370, (52, 162), 320, (287.5, 192.5), (100, 160, 210, 270), 23)
        a02 = rib(17.25, 99.75)
        return [(C.lab(3, q), a01), (C.lab(3, q), a02), (C.lab(3, q), a02.mirrored())]   # A03 = A02 镜像

    @C.part('1610341A00')
    def _(q):
        # 明细栏用 1610305A02 / A03（图在 1610305A00）
        a01 = motor_plate(505, (167, 297), 455, (422.5, 327.5), (98.5, 158.5, 346.5, 406.5), 25)
        a02 = rib(17.25, 99.75)
        return [(C.lab(3, q), a01), (C.lab(3, q), a02), (C.lab(3, q), a02.mirrored())]

    @C.part('1610342A00')
    def _(q):
        # 明细栏“板”是 1610604A01（图在 1610604A00 第 2 页，本单没有单独小件图）；筋 1610342A01 / A02（镜像）
        a01 = motor_plate(605, (267, 397), 555, (524, 429), (98.5, 158.5, 446.5, 506.5), 23)
        a02 = rib(26.75, 90.25)
        return [(C.lab(3, q), a01), (C.lab(3, q), a02), (C.lab(3, q), a02.mirrored())]

    # ================================================================== 链轮护罩一组
    @C.part('1610332A')
    def _(q):
        # 1.5mm 盒形：后板 + 左边 17 + 右边 46 + 下边 46 带前唇 15 + 上边 46 带前唇 15（x≥40.5）+ 耳部顶边 46
        # 耳部右壁（x=38.5~40，46 深）展开后和上边翼板重叠，不能一体下料：单出一块 44.5x19.5，见 notes
        t = 1.5; w = C.bd(t); h = w / 2                  # BD 2.3
        sh = 3 - h                                       # 距外面 3（切点）的展开偏移 1.85
        ybr, ytr = h, 132.25 - h                         # 下 / 上基线 1.15 / 131.1
        ybl = ybr - (46 - w); ytl = ytr + (46 - w)        # 前唇线 -42.55 / 174.8
        ybe = ybl - (15 - h); yte = ytl + (15 - h)        # 唇边 -56.4 / 188.65
        xl = h - (17 - h)                                # 左边缘 -14.7
        xr = 217 - h; xre = xr + (46 - h)                # 右基线 215.85、边缘 260.7
        yk = 152.25 - h; yke = yk + (46 - h)             # 耳顶基线 151.1、边缘 195.95
        cap = 3 * math.tan(math.radians(48.19 / 2))      # 右上 / 右下 R3 肩（48.19° 弧）虚拟顶点到切点
        s52 = 5.237 - h                                  # 肩圆心距基线（距外面 5.237）
        p = C.Piece()
        outline(p, [
            (0, ybe, 3), (215, ybe, 3),
            (215, ybr - s52 + cap, 3), (214, ybr - sh),            # 下边右肩
            (214, 3), (xr + sh, 3), (xr + sh, 0, 3), (xre, 0, 3),  # 右边（宽 132.25，根部 3~129.25）
            (xre, 132.25, 3), (xr + sh, 132.25, 3), (xr + sh, 129.25), (214, 129.25),
            (214, ytr + sh), (215, ytr + s52 - cap, 3),            # 上边右肩
            (215, yte, 3), (40.5, yte, 3), (40.5, 129.25), (40, 129.25),
            (40, 149.25), (37, 149.25), (37, yk + sh), (40, yk + sh, 3), (40, yke, 3),   # 耳部顶边（宽 40，根部 3~37）
            (0, yke, 3), (0, yk + sh, 3), (3, yk + sh), (3, 149.25),
            (xl, 149.25, 3), (xl, 3, 3), (3, 3), (3, ybr - sh), (0, ybr - sh, 3)])       # 左边 + 下边左肩
        p.bend(h, 3, h, 149.25, w)
        p.bend(3, ybr, 214, ybr, w).bend(0, ybl, 215, ybl, w)
        p.bend(xr, 3, xr, 129.25, w)
        p.bend(40.5, ytr, 214, ytr, w).bend(40.5, ytl, 215, ytl, w)
        p.bend(3, yk, 37, yk, w)
        p.slot(154, 59.25, 174, 59.25, 25)               # 后板腰孔 25 宽
        for x in (127, 197):
            p.tap(x, ybl - (9 - h), 'M5')                # 前唇 4-M5（翻边抽芽工艺，孔径待确认，见 notes）
            p.tap(x, ytl + (9 - h), 'M5')
            p.circle(x, ytr + (25 - h), 6.5)             # 上边 2-Φ6.5（距后面 25）
        wall = C.Piece()
        wall.outline([(0, 0), (44.5, 0, 3), (44.5, 19.5), (0, 19.5)])    # 耳部右壁，前下角 R3
        return [(C.lab(t, q), p), (C.lab(t, q), wall)]

    @C.part('1610333A')
    def _(q):
        return [(C.lab(1.5, q), C.plate('1610333A.idw.dxf', (121.535, 178.69, 338.535, 330.94)))]

    def l_plate(t, W, Lv, Lh, vh, hh):
        """L 形：立边 Lv + 平边 Lh，宽 W，四角 R5；vh / hh = 立边 / 平边孔 [(x, 距该边自由端, 类型)]"""
        w = C.bd(t)
        yr = Lv - w / 2; H = Lv + Lh - w
        p = C.Piece().rect(0, 0, W, H, 5)
        p.bend(0, yr, W, yr, w)
        for x, s, k in vh:
            p.tap(x, s, k) if k.startswith('M') else p.circle(x, s, float(k))
        for x, s, k in hh:
            p.tap(x, H - s, k) if k.startswith('M') else p.circle(x, H - s, float(k))
        return p

    @C.part('1610334A')
    def _(q):
        # 立边 30（2-Φ7）+ 平边 37（2-M8），宽 120，展开 58.6
        return [(C.lab(5, q), l_plate(5, 120, 30, 37, [(12.5, 10, '7'), (107.5, 10, '7')], [(30, 17, 'M8'), (90, 17, 'M8')]))]

    @C.part('1610336A')
    def _(q):
        # 1mm：主板外形 54.5 x 150（斜边）+ 翼 25（只在下部 70 高）
        t = 1; w = C.bd(t)
        xr = 54.5 - w / 2; xe = xr + 25 - w / 2          # 53.65 / 77.8
        p = C.Piece()
        p.outline([(34.5, 0, 5), (xe, 0, 5), (xe, 70, 5), (52.5, 70), (52.5, 150, 5), (0, 150, 5), (0, 120, 5)])
        p.bend(xr, 0, xr, 70, w)
        p.circle(42, 9.5, 9).circle(42, 59.5, 9)
        p.circle(xr + (15 - w / 2), 10, 9).circle(xr + (15 - w / 2), 60, 9)
        return [(C.lab(t, q), p)]

    @C.part('1610337A')
    def _(q):
        return [(C.lab(5, q), l_plate(5, 70, 76, 41.75, [(10, 10, 'M8'), (60, 10, 'M8')], [(10, 10, 'M8'), (60, 10, 'M8')]))]

    @C.part('1610338A')
    def _(q):
        return [(C.lab(5, q), l_plate(5, 55, 50, 51.25, [(10, 10, 'M8'), (45, 10, 'M8')], [(9, 10, 'M8'), (45, 10, 'M8')]))]

    @C.part('1610339A')
    def _(q):
        # 5mm 错位板（Z，偏折 36.87°，高差 20），宽 40，四角 R5；中性层展开 254.52（投影 250）
        t = 5; W = 40
        a = math.degrees(math.atan(0.75))                # 36.87°
        arc = math.radians(a) * (5 + 0.48 * t)           # 单弯弧长 4.762
        xa = 88.333; sl = 20.0                           # 左直段到切点、斜段直线
        r1 = xa + arc / 2; xb = xa + arc + sl; r2 = xb + arc / 2
        L = xb + arc + (250 - 113.333)                   # 254.52
        dx = L - 250                                     # 右段孔位偏移（投影 → 展开）4.52
        p = C.Piece().rect(0, 0, L, W, 5)
        red(p, r1, 0, r1, W)
        red(p, r2, 0, r2, 15.5); red(p, r2, 24.5, r2, W)  # 第二道折弯线被开口腰孔断开
        p.circle(10, 20, 9)
        p.slot(205 + dx, 20, 235 + dx, 20, 9)
        # 长腰孔：左端平头（止于第二道折弯起点 = 斜段末端），右端 R4.5，圆心投影 x=145
        xc = 145 + dx
        p.poly([(xb, 15.5, 0), (xc, 15.5, 1), (xc, 24.5, 0), (xb, 24.5, 0)], True)
        return [(C.lab(t, q), p)]
