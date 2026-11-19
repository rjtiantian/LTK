# -*- coding: utf-8 -*-
"""单件 2026-11-19：AX-26-191 扬声器支架（客户 DWG 一张，四种钣金件，SUS304，表面不处理）。

图里四个件的文字说明都写“灯杆抱箍”（复制粘贴），名称按形状另起；几何全部取 DWG 矢量（块 圆盘固定件4/5/6 + 模型空间）。
  -1 灯杆抱箍 5mm 2件：半圆盘（上下两片）+ 分缝处两条耳板一体折弯（侧视图 U 形带 R5.5 外圆角），
     耳板内侧再折 20 的挡边（高 132，两端各让 5）。外形：宽 232.97，盘深 110.5（自耳板外面），高 152。
  -2 U形卡 5mm 2件：腿 50 + 底 152 + 腿 50，宽 44；两腿 Φ11 距自由端 20、端角 R10；底面三个 6.2 宽腰孔。
  -3 / -4 箱体 1.2mm：外形 280×200×150；前面 Φ122.5（距左 100、上下居中）；右侧面居中开 Φ78.4（-3，4件）/ Φ106（-4，2件）
     接倒相管（图里品红色的管，外购 / 另做，不在本图）。做法（我定的）：箱身 = 后板 + 四面墙十字展开（墙高 148.8），
     前面板 280×200 平板盖上焊接。
"""
import math
from sheetlib import BEND

B90 = math.tan(math.radians(90) / 4)          # 0.41421


def _blue(p, x0, y0, x1, y1):
    p.poly([(x0, y0), (x1, y1)], False, BEND, linetype='CENTER', color=5)


def register(C):
    C.mat = 'SUS304'

    # ------------------------------------------------------------------ -1 灯杆抱箍
    @C.part('AX-26-191-1')
    def _(q):
        t = 5; w = C.bd(t)                    # BD 8.4
        Wd = 232.97                           # 盘宽（耳板外面所在的分缝边）
        D = 110.5                             # 盘深：自耳板外面到圆弧顶
        Hh = 152                              # 外形高
        r1 = D - w / 2                        # 上盘—耳板折弯红线 106.3
        r2 = r1 + Hh - w                      # 下盘—耳板折弯红线 249.9
        ut = lambda d: r1 + w / 2 - d         # 上盘：距耳板外面 d
        ub = lambda d: r2 - w / 2 + d         # 下盘
        ue = lambda s: r1 + s - w / 2         # 耳板：距上盘外面 s
        e0, e1 = 14, 65                       # 左耳板 x（右耳板对称）
        lipx = 72                             # 挡边外面 x
        xl = lipx - w / 2                     # 挡边折弯红线 67.8
        lipe = xl + (20 - w / 2)              # 挡边外伸 20（自耳板外面）→ 展开到 83.6
        m = lambda x: Wd - x
        fe_t, fe_b = ut(5), ub(5)             # 盘分缝边（耳板内面）105.5 / 250.7
        sd_t, sd_b = ut(20.84), ub(20.84)     # 盘两侧直边到外圆弧弦 89.66 / 266.54
        l0, l1 = ue(10), ue(142)              # 挡边高 132（距盘外面 10 ~ 142）
        bo, bp = 0.77, 0.713                  # 外圆弧 R120.5、抱杆圆弧 R46 的凸度（取自 DWG）
        p = C.Piece()
        p.poly([(0, sd_t, bo), (Wd, sd_t, 0), (Wd, fe_t, 0), (m(e0), fe_t, 0), (m(e0), fe_b, 0), (Wd, fe_b, 0),
                (Wd, sd_b, bo), (0, sd_b, 0), (0, fe_b, 0), (e0, fe_b, 0), (e0, fe_t, 0), (0, fe_t, 0)])
        r = 2                                  # 挡边自由角 R2
        p.poly([(e1, fe_t, 0), (73, fe_t, bp), (m(73), fe_t, 0), (m(e1), fe_t, 0), (m(e1), l0, 0),
                (m(lipe) + r, l0, -B90), (m(lipe), l0 + r, 0), (m(lipe), l1 - r, -B90), (m(lipe) + r, l1, 0),
                (m(e1), l1, 0), (m(e1), fe_b, 0), (m(73), fe_b, bp), (73, fe_b, 0), (e1, fe_b, 0), (e1, l1, 0),
                (lipe - r, l1, -B90), (lipe, l1 - r, 0), (lipe, l0 + r, -B90), (lipe - r, l0, 0), (e1, l0, 0)])
        for u in (r1, r2):
            p.bend(e0, u, e1, u, w).bend(m(e1), u, m(e0), u, w)
        p.bend(xl, l0, xl, l1, w).bend(m(xl), l0, m(xl), l1, w)
        # 盘上 5-Φ11（PCD 约 Φ196，距耳板外面 d）
        for x, d in [(116.49, 88.0), (67.49, 74.87), (31.62, 39.0), (165.48, 74.87), (201.35, 39.0)]:
            p.circle(x, ut(d), 11).circle(x, ub(d), 11)
        # 耳板 2-Φ13（距盘外面 26 / 126，距耳板外侧 29）
        for x in (43, m(43)):
            for s in (26, 126):
                p.circle(x, ue(s), 13)
        return [(C.lab(t, q), p)]

    # ------------------------------------------------------------------ -2 U形卡
    @C.part('AX-26-191-2')
    def _(q):
        t = 5; w = C.bd(t)
        L = 50 + 152 + 50 - 2 * w             # 235.2
        r1 = 50 - w / 2; r2 = L - r1          # 45.8 / 189.4
        ue = lambda s: r1 + s - w / 2         # 底面：距下腿外面 s
        p = C.Piece().outline([(0, 0, 10), (L, 0, 10), (L, 44, 10), (0, 44, 10)])
        p.circle(20, 22, 11).circle(L - 20, 22, 11)
        p.slot(ue(19), 22, ue(23), 22, 6.2)                    # 沿长度的腰孔（距下腿外面 19~23）
        p.slot(ue(123), 8, ue(123), 11, 6.2).slot(ue(123), 33, ue(123), 36, 6.2)   # 横向两腰孔
        p.bend(r1, 0, r1, 44, w).bend(r2, 0, r2, 44, w)
        return [(C.lab(t, q), p.rotated(90))]

    # ------------------------------------------------------------------ -3 / -4 箱体
    def box(q, dside):
        t = 1.2; w = C.bd(t)                  # BD 2
        rp, rg, rs = C.relief_params(t, w)    # 2.4, 0.4, 1.3：上下墙全宽，左右墙内缩
        A, Bh, Hw = 280, 200, 150 - t         # 后板外形 280×200，墙高 148.8（前面板压在墙口上）
        xa = Hw - w; xb = xa + A; W = xb + xa
        ya = Hw - w; yb = ya + Bh; H = yb + ya
        xr0, xr1 = xa + w / 2, xb - w / 2
        yr0, yr1 = ya + w / 2, yb - w / 2
        pts = [(xa, 0), (xb, 0), (xb, ya - rg), (xb - rp, ya + rp), (xb + 1, ya + rs), (W, ya + rs), (W, yb - rs),
               (xb + 1, yb - rs), (xb - rp, yb - rp), (xb, yb + rg), (xb, H), (xa, H), (xa, yb + rg),
               (xa + rp, yb - rp), (xa - 1, yb - rs), (0, yb - rs), (0, ya + rs), (xa - 1, ya + rs),
               (xa + rp, ya + rp), (xa, ya - rg)]
        p = C.Piece().poly(pts)
        ev = lambda y: xa + (y - (ya - rg)) * rp / (rp + rg)
        eh = lambda x: ya + rs + (x - (xa - 1)) * (rp - rs) / (rp + 1)
        for y in (yr0, yr1):
            p.bend(ev(yr0), y, W - ev(yr0), y, 0, red_only=True)
        for y0 in (yr0 - w / 2, yr0 + w / 2):
            x0 = ev(y0)
            _blue(p, x0, y0, W - x0, y0)
            _blue(p, x0, H - y0, W - x0, H - y0)
        for x in (xr0, xr1):
            xx = x if x < W / 2 else W - x
            p.bend(x, eh(xx), x, H - eh(xx), 0, red_only=True)
        for x0 in (xr0 - w / 2, xr0 + w / 2):
            y0 = eh(x0)
            _blue(p, x0, y0, x0, H - y0)
            _blue(p, W - x0, y0, W - x0, H - y0)
        p.circle(xr1 + 75 - w / 2, H / 2, dside)          # 右侧墙：距后板外面 75、上下居中
        front = C.Piece().rect(0, 0, A, Bh).circle(100, 100, 122.5)
        return [(C.lab(t, q), p), (C.lab(t, q), front)]

    C.part('AX-26-191-3')(lambda q: box(q, 78.4))
    C.part('AX-26-191-4')(lambda q: box(q, 106))
