# -*- coding: utf-8 -*-
"""NO.481 下料件（a 批，17 行）：3370137A-SUS304 / 3370138A-SUS304、3400xxx、3405142A、3405143A、
3420164A~3420167A、4010104C、7340114A。

老图先取历史人工件（histlib），和本单图纸逐项核对：一致就复用几何（折弯线按规则重画）；
历史折弯扣除或缺孔和规则 / 新图不符的，按新图重画，差异写在 481/notes_a.md。
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import histlib
from sheetlib import BEND


def _hist(code, pick=None, i=0):
    """历史人工展开件（左下角归零），折弯线去掉，由调用方按规则重画"""
    res = histlib.hist_pieces(code, pick)
    assert res, '历史中找不到 %s %s' % (code, pick)
    p = res[i][1].normalized()
    p.ents = [e for e in p.ents if e[2].get('layer') != BEND]
    # 人工图里 4 段圆弧画的圆孔换回真圆
    for i, (k, d, a) in enumerate(p.ents):
        if k == 'LWPOLYLINE' and d[1] and len(d[0]) == 4 and all(abs(abs(q[2]) - 0.41421) < 0.002 for q in d[0]):
            xs = [q[0] for q in d[0]]; ys = [q[1] for q in d[0]]
            c = (float(min(xs) + max(xs)) / 2, float(min(ys) + max(ys)) / 2)
            p.ents[i] = ('CIRCLE', (c, float(max(xs) - min(xs)) / 2), a)
    return p


def _isect(a, b, c, d):
    """直线 ab 与直线 cd 的交点"""
    x1, y1, x2, y2 = a + b
    x3, y3, x4, y4 = c + d
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _red(p, a, b):
    p.poly([a, b], False, BEND, linetype='CENTER', color=1, ltscale=0.5)


def _blue(p, a, b):
    p.poly([a, b], False, BEND, linetype='CENTER', color=5)


def _bend_clip(p, a, b, w, ea, eb):
    """90° 折弯：红线 a-b，蓝线距红线 w/2，两端都截到轮廓边 ea（a 端）、eb（b 端）上"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    _red(p, a, b)
    for s in (1, -1):
        a1 = (a[0] + s * nx, a[1] + s * ny)
        b1 = (b[0] + s * nx, b[1] + s * ny)
        _blue(p, _isect(a1, b1, *ea), _isect(a1, b1, *eb))


def _K(C, t):
    """由 90° BD 表反算 K（R = t）"""
    return (2 * (t + t) - C.bd(t)) / (math.pi / 2) / t - 1


def register(C):
    # =========================================================== 连接件（新图有 5 个孔，历史 NO.454 只有 2 个）
    @C.part('3370137A-SUS304')
    def _(q):
        # 2.5mm，长边 70 + 短边 27，高 75；展开 70 + 27 - 4 = 93；重量 4707mm² → 0.0933kg（图 0.095）
        t = 2.5; w = C.bd(t)
        xr = 27 - w / 2                                  # 25
        s = lambda d: xr + d - w / 2                     # 长边特征：距外面 d
        p = C.Piece().outline([
            (0, 30, 5), (30 * math.tan(math.radians(30)), 0, 5), (93, 0, 5), (93, 50, 5),
            (20.75, 50), (20.75, 52.5), (22, 52.5), (22, 75, 5), (0, 75, 5)])
        p.bend(xr, 0, xr, 50, w)
        p.circle(11.5, 62.5, 8.2)                        # 短边 Φ8.2：距上 12.5，距自由边 11.5
        p.circle(6, 36.06, 7).circle(16, 36.06, 7)       # 短边 2-Φ7：距上 38.94，距自由边 6 / 16
        p.circle(s(30), 8, 7).circle(s(30), 42, 7)       # 长边 2-Φ7：距外面 30，距下 8 / 42
        return [(C.lab(t, q), p)]

    C.mirror('3370138A-SUS304', '3370137A-SUS304')       # 3370137A 图“镜像制作”表

    # =========================================================== 护栏 5mm（历史 NO.452，外形孔一致）
    @C.part('3400117A')
    def _(q):
        # 腹板 110 整片（A 面），上折边 60，两端翼折边沿斜线（20.556°）；展开高 110 + 60 - 8.4 = 161.6
        t = 5; w = C.bd(t)
        p = _hist('3400117A')
        W = 1136.24
        vr = ((1036.3, 100.0), (1037.16, 111.6))         # 右侧 V 口：中段折边一侧
        vw = ((1036.3, 100.0), (1039.58, 111.16))        # 右侧 V 口：翼折边一侧
        ew = ((1113.05, 66.49), (1136.24, 128.31))       # 右翼折边端面
        m = lambda e: ((W - e[0][0], e[0][1]), (W - e[1][0], e[1][1]))
        _bend_clip(p, (W - 1036.73, 105.8), (1036.73, 105.8), w, m(vr), vr)
        _bend_clip(p, (1116.64, 76.07), (1037.94, 105.58), w, ew, vw)
        _bend_clip(p, (W - 1116.64, 76.07), (W - 1037.94, 105.58), w, m(ew), m(vw))
        return [(C.lab(t, q), p)]

    @C.part('3400217A')
    def _(q):
        # 护栏支杆：圆管 Φ20 壁厚 3，长 450（算重 0.572kg，图 0.582）；管材 STEP 在 481/管材STEP
        return [(C.lab(450, q), C.tube_round(20, 3))]

    @C.part('3400310A')
    def _(q):
        # 导向框主板 3mm（历史 NO.452，外形孔一致）：C 形 46.5 + 73 + 46.5，展开 155.95（规则 156）；
        # 腹板两端 20° 翼板 + 上下整片法兰。20° 折弯只画红线（历史 BD 0.56 = K 因子值）
        t = 3; w = C.bd(t)
        p = _hist('3400310A')
        W, H = 1106.87, 155.95
        v = ((67.95, 115.45), (85.49, 108.47))           # 左上 V 口上沿
        mx = lambda e: ((W - e[0][0], e[0][1]), (W - e[1][0], e[1][1]))
        my = lambda e: ((e[0][0], H - e[0][1]), (e[1][0], H - e[1][1]))
        _bend_clip(p, (76.72, 111.96), (W - 76.72, 111.96), w, v, mx(v))
        _bend_clip(p, (76.72, H - 111.96), (W - 76.72, H - 111.96), w, my(v), mx(my(v)))
        for x in (84.72, W - 84.72):
            _red(p, (x, 47.35), (x, 108.6))
        return [(C.lab(t, q), p)]

    @C.part('3400316A')
    def _(q):
        # 气缸顶板 5mm：15 + 90 + 15，两处 30° 折（外形交点量），按 K 因子展开 117.02（历史 115.65，见 notes）
        t = 5
        d = C.bd_angle(t, 30, _K(C, t), t)               # 1.492
        L = 120 - 2 * d
        p = C.Piece().rect(0, 0, L, 34, 5)
        for x in (15 - d / 2, L - 15 + d / 2):
            p.bend(x, 0, x, 34, 0, red_only=True)
        for x in (L / 2 - 35, L / 2 + 35):               # 4-Φ5.5（沉头只开通孔）
            p.circle(x, 8, 5.5).circle(x, 26, 5.5)
        return [(C.lab(t, q), p)]

    @C.part('3400317A')
    def _(q):
        # 气缸调节板 3mm 平板，120x20（历史 NO.452，与图一致）；2-Φ8.5 -3 深 = 通孔；算重 0.0444（图 0.045）
        return [(C.lab(3, q), _hist('3400317A'))]

    @C.part('3400322A')
    def _(q):
        # 光电安装板 3mm（历史 NO.452，与图一致）：50 + 54，展开 99，折弯 y=47.5
        t = 3; w = C.bd(t)
        p = _hist('3400322A')
        p.bend(0, 50 - w / 2, 60, 50 - w / 2, w)
        return [(C.lab(t, q), p)]

    @C.part('3400608A')
    def _(q):
        # 踏板 3mm 平板，180x30 R5，3-Φ5.5（历史 NO.452，与图一致）
        return [(C.lab(3, q), _hist('3400608A'))]

    @C.part('3405142A')
    def _(q):
        # 挡板 5mm（历史 NO.451，与图一致）：95 + 105，展开 191.6，折弯 y=90.8；4 角 R5（远端见轴测）；沉头只开 Φ5.5
        t = 5; w = C.bd(t)
        p = _hist('3405142A')
        p.bend(0, 95 - w / 2, 35, 95 - w / 2, w)
        return [(C.lab(t, q), p)]

    @C.part('3405143A')
    def _(q):
        # 垫板：图纸 3.5mm，SUS304 无 3.5 → 4mm（C.lab 自动，历史 NO.451 也是 4mm）；70x60 R5，4-Φ7
        return [(C.lab(3.5, q), _hist('3405143A'))]

    # =========================================================== 3420xxx 新件
    @C.part('3420164A')
    def _(q):
        # 夹板 5mm：平段 40（A 面外形交点量起）+ 斜段（水平 16、落差 3，实长 16.279），偏折 10.62°，R5/R10
        t = 5
        ang = math.degrees(math.atan2(3, 16))            # 10.62°
        d = C.bd_angle(t, ang, _K(C, t), t)              # 0.491
        ls = math.hypot(16, 3)
        L = 40 + ls - d                                  # 55.788
        p = C.Piece().rect(0, 0, L, 54, 5)
        p.bend(ls - d / 2, 0, ls - d / 2, 54, 0, red_only=True)
        p.circle(L - 30, 12, 8.5).circle(L - 30, 42, 8.5)
        return [(C.lab(t, q), p)]

    @C.part('3420165A')
    def _(q):
        # 输送固定支架 3mm，三面：立板 150x80（A 面，45° 缺口）+ 上折边 60 + 左折边 60
        # x：左折边自由端 0，红线 57.5，立板距左外面 s → x = 55 + s；y：立板距下 z → y = z，红线 77.5，上折边距立板外面 d → y = 75 + d
        t = 3; w = C.bd(t)                               # BD 5，展开 205 x 135
        rp, rg, rs = C.relief_params(t, w)               # 碰角 V 形释放槽 6, 1, 3.1；上折边全宽，左折边内缩
        xo, yo = 55, 80                                  # 外形交点
        tip = (xo + rp, yo - rp)                         # (61, 74)
        up = (xo, yo + rg)                               # (55, 81)
        lo = (xo - rg, yo - rs)                          # (54, 76.9)
        p = C.Piece().outline([
            (0, 0, 5), (95, 0, 5), (145, 50, 5), (205, 50, 5), (205, 135, 5), (55, 135),
            up, tip, lo, (0, yo - rs)])
        # 左折边：x=57.5，下端在下边，上端截到 V 口下沿
        _red(p, (57.5, 0), _isect((57.5, 0), (57.5, 1), tip, lo))
        for x in (55, 60):
            _blue(p, (x, 0), _isect((x, 0), (x, 1), tip, lo))
        # 上折边：y=77.5，左端截到 V 口上沿
        _red(p, _isect((0, 77.5), (1, 77.5), up, tip), (205, 77.5))
        for y in (75, 80):
            _blue(p, _isect((0, y), (1, y), up, tip), (205, y))
        for y in (93, 123):                              # 上折边 4 条腰孔：距立板外面 18 / 48，宽 9
            p.slot(70, y, 120, y, 9).slot(135, y, 185, y, 9)
        for y in (18, 58):                               # 左折边 2 条腰孔：距下 18 / 58，距自由端 25~45，宽 9
            p.slot(25, y, 45, y, 9)
        return [(C.lab(t, q), p)]

    C.mirror('3420166A', '3420165A')                     # 3420165A 图“对称制作”表

    @C.part('3420167A')
    def _(q):
        # 触摸屏安装件 10mm 扁条，宽 20：内侧 280 + 50，内角 120°（偏折 60°），R10/R20
        # 外形交点 = 内侧 + t·tan30°：285.774 + 55.774，BD 7.761，展开 333.786
        t = 10
        d = C.bd_angle(t, 60, _K(C, t), t)
        e = t * math.tan(math.radians(30))
        a, b = 50 + e, 280 + e
        L = a + b - d
        p = C.Piece().rect(0, 0, L, 20, 2)               # 四角 R2
        p.bend(a - d / 2, 0, a - d / 2, 20, 0, red_only=True)
        p.tap(L - 8, 10, 'M5').tap(L - 250, 10, 'M5')    # 2-M5：距端 8，间距 242
        p.circle(15, 10, 9)                              # 斜段 Φ9：图上没标注，矢量量得距尖端 15（见 notes）
        return [(C.lab(t, q), p)]

    # =========================================================== 其它老图
    @C.part('4010104C')
    def _(q):
        # 舌头垫板 Q235B 3mm，56x29 C2，4-Φ5.5（历史 NO.447，与图一致）；算重 0.0358（图 0.036）
        return [(C.lab(3, q, 'Q235B'), _hist('4010104C', 'NO.447'))]

    @C.part('7340114A')
    def _(q):
        # 把手 3mm。纵向：斜板 50 →60° 偏折→ 后板 55 →90°→ 顶板 50 →90°→ 前板 30；展开 185 - 2.262 - 10 = 172.738
        # 横向：侧板 50 + 后板 110 + 侧板 50，展开 200。历史 BD 5.12（199.76 x 172.42）与规则 5 不符，按规则重画，样式同历史：
        # 三块面板内缩 3.1 夹在两侧板之间（宽 103.8），碰角 V 形释放槽；图纸四角 R6 照图
        t = 3; w = C.bd(t)
        d = C.bd_angle(t, 60, _K(C, t), t)               # 2.262
        y1 = 50 - d / 2                                  # 60° 红线
        y2 = 50 - d + 55 - w / 2                         # 后板 / 顶板红线
        yo = y2 + w / 2                                  # 外形交点
        y3 = y2 + 50 - w                                 # 顶板 / 前板红线
        H = y3 + 30 - w / 2                              # 172.738
        rp, rg, rs = C.relief_params(t, w)
        xo = 45                                          # 左侧板外形交点（红线 47.5）
        xp = xo + rs                                     # 面板侧边 48.1
        vt, v1, v2 = (xo + rp, yo - rp), (xo - rg, yo), (xp, yo + rg)
        # 侧板外形取侧视矢量（图上 y' 距底，顶 80.206）：A = 自由边与 60° 端线交点，B = 尖角，下边线 30° 贴斜板外面
        dy = yo - 80.206                                 # y' → y
        Ay = 11.809 + dy
        Bx, By = 6.698, 0.206 + dy
        tx = 49.54                                       # 下 V 尖（同历史：距红线 2.04）
        ty = By + (tx - Bx) * math.tan(math.radians(30))
        lx, ly = xp, ty - 4.02                           # 面板侧边接 V 尖（同历史）
        W = 200
        p = C.Piece().outline([
            (xp, 0, 6), (W - xp, 0, 6), (W - lx, ly), (W - tx, ty), (W - Bx, By, 6), (W, Ay, 6), (W, yo, 6),
            (W - v1[0], yo), (W - vt[0], vt[1]), (W - v2[0], v2[1]), (W - xp, H, 6), (xp, H, 6),
            v2, vt, v1, (0, yo, 6), (0, Ay, 6), (Bx, By, 6), (tx, ty), (lx, ly)])
        low = lambda x: By + (x - Bx) * math.tan(math.radians(30))
        up = lambda x: _isect((x, 0), (x, 1), v1, vt)[1]
        for s in (1, -1):                                # 侧板折弯 x=47.5 / 152.5
            X = lambda x: x if s == 1 else W - x
            _red(p, (X(47.5), low(47.5)), (X(47.5), up(47.5)))
            _blue(p, (X(45), low(45)), (X(45), up(45)))
            _blue(p, (X(50), y1), (X(50), up(50)))
        _red(p, (50, y1), (W - 50, y1))                  # 60° 只画红线
        x2 = lambda y: _isect((0, y), (1, y), vt, v2)[0]
        for y, f in ((y2, _red), (y2 - w / 2, _blue), (y2 + w / 2, _blue)):
            f(p, (x2(y), y), (W - x2(y), y))
        p.bend(xp, y3, W - xp, y3, w)
        for x in (25, W - 25):                           # 侧板 2-Φ7：距自由边 25，距顶 20 / 45
            p.circle(x, yo - 20, 7).circle(x, yo - 45, 7)
        return [(C.lab(t, q), p)]
