# -*- coding: utf-8 -*-
"""NO.482 批次 f：带 K / L 参数的直段件（28 行），SUS304。

三个族都按参数函数出，但外形、孔位、缺口全部从每张图的矢量读（不套公式），读不懂的图元直接报错：
- 机身板 2.5mm（L 形）：主视图 H(169 / 150) + 翼边 25，BD4，展开 H + 25 - 4。
  主视图是实形（x 不变）：y_展开 = 距主视图底外形 s + 21；翼边孔 y_展开 = 距翼边自由边 d。
  1610302A 这一类主视图看的是翼边那一面（翼边朝观察者），展开照主视图不翻面（同历史 1570201A 做法）。
- 防护罩 1.5mm（U 形）：前腿 20（带 Φ5.5 孔）+ 腹板 60 + 后腿 42（自由边带 Φ51 半圆缺口），BD2.3，
  展开从前腿自由边起（y=0），外表面朝上（同历史 1570501A）。
- 保护罩下 1.5mm（Z 形）：下腿 42（Φ51 半圆缺口）+ 腹板 56 + 上腿 17.5（Φ9 开口槽，两头短），BD2.3，
  展开与主视图同向。主视图多为断开画法：真实坐标 = 视图坐标 + 断开量；被省略段的缺口按标注节距补，
  看得见的缺口必须落在标注序列上，否则报错。
"""
import math, os, re
import ezdxf
from ezdxf import bbox as ezbbox
from sheetlib import Piece, CUT

HID = '隐藏 (ISO)'
BRK = '折线 (ISO)'
K90 = math.tan(math.radians(90) / 4)
EPS = 0.03

_CACHE = {}
VIEWMAP = {}          # 物料号 → 展开坐标回到图纸视图的映射（只给核对脚本用）


class Sheet:
    """一张图的线、弧、圆（可见层 / 隐藏层）和断开线"""

    def __init__(self, path):
        self.lines, self.arcs, self.circles, self.hid_arcs, self.hid_circles, self.brk = [], [], [], [], [], []
        boxes = []
        for e in ezdxf.readfile(path).modelspace():
            lay, t = e.dxf.layer, e.dxftype()
            if lay == BRK:
                b = ezbbox.extents([e])
                if b.has_data:
                    self.brk.append((b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y))
                continue
            if lay == HID:
                if t == 'ARC':
                    self.hid_arcs.append((e.dxf.center.x, e.dxf.center.y, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle))
                elif t == 'CIRCLE':
                    self.hid_circles.append((e.dxf.center.x, e.dxf.center.y, 2 * e.dxf.radius))
                continue
            if lay != CUT:
                continue
            if t == 'LINE':
                self.lines.append((e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y))
            elif t == 'ARC':
                self.arcs.append((e.dxf.center.x, e.dxf.center.y, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle))
            elif t == 'CIRCLE':
                self.circles.append((e.dxf.center.x, e.dxf.center.y, 2 * e.dxf.radius))
            else:
                continue
            b = ezbbox.extents([e])
            if b.has_data:
                boxes.append([b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y])
        self.views = _merge(boxes)

    def view(self, w, h, tol=0.1):
        """宽 w（None 不限）、高 h 的视图区域，取唯一一个"""
        hits = [v for v in self.views if (w is None or abs(v[2] - v[0] - w) < tol) and abs(v[3] - v[1] - h) < tol]
        if len(hits) != 1:
            raise ValueError('视图 %s x %s 不唯一：%s' % (w, h, hits))
        return hits[0]

    def _in(self, r, x0, y0, x1, y1, e=0.3):
        return x0 >= r[0] - e and x1 <= r[2] + e and y0 >= r[1] - e and y1 <= r[3] + e

    def lines_in(self, r):
        return [l for l in self.lines if self._in(r, min(l[0], l[2]), min(l[1], l[3]), max(l[0], l[2]), max(l[1], l[3]))]

    def arcs_in(self, r):
        return [a for a in self.arcs if self._in(r, a[0] - a[2], a[1] - a[2], a[0] + a[2], a[1] + a[2], e=a[2] * 2 + 0.3)
                and r[0] - 0.3 <= a[0] <= r[2] + 0.3 and r[1] - 0.3 <= a[1] <= r[3] + 0.3]

    def circles_in(self, r):
        return [c for c in self.circles if r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]]


def _merge(bs):
    merged = True
    while merged:
        merged, out = False, []
        for b in bs:
            for o in out:
                if b[0] <= o[2] + 1 and o[0] <= b[2] + 1 and b[1] <= o[3] + 1 and o[1] <= b[3] + 1:
                    o[:] = [min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])]
                    merged = True
                    break
            else:
                out.append(list(b))
        bs = out
    return bs


def sheet(C, code):
    for name in (code + '.idw.dxf', code + '.dxf'):
        path = C.DXF(name)
        if os.path.exists(path):
            if path not in _CACHE:
                _CACHE[path] = Sheet(path)
            return _CACHE[path]
    raise FileNotFoundError(code)


class Path:
    """带圆弧的闭合外形：to 走直线，arc 走圆弧（bulge）"""

    def __init__(self, x, y):
        self.v = [[x, y, 0.0]]

    def to(self, x, y):
        if abs(x - self.v[-1][0]) > 1e-6 or abs(y - self.v[-1][1]) > 1e-6:
            self.v.append([x, y, 0.0])
        return self

    def arc(self, x, y, b):
        self.v[-1][2] = b
        self.v.append([x, y, 0.0])
        return self

    def into(self, p):
        v = self.v
        if abs(v[-1][0] - v[0][0]) < 1e-6 and abs(v[-1][1] - v[0][1]) < 1e-6:
            v = v[:-1]
        p.poly([tuple(q) for q in v], True)
        return p


def _bulge(deg):
    return math.tan(math.radians(deg) / 4)


def split_tail(code, cs, L, R, rf):
    """缺口圆心排到端头以外、只剩一小截圆弧切掉端角的（1610321A / 1610322A 新图右端）：
    返回 (端头内的圆心, 端头外那个圆心或 None)。左端出现这种情况、或缺口压到端角圆角上的直接报错。"""
    tail = [c for c in cs if c > L]
    inner = [c for c in cs if c <= L]
    if len(tail) > 1 or (tail and not tail[0] - R < L):
        raise ValueError('%s 端头外缺口 %s' % (code, tail))
    if any(c < R + rf for c in inner):
        raise ValueError('%s 左端缺口压端角 %s' % (code, inner))
    lim = (tail[0] - R) if tail else L - rf    # 最后一个整缺口的倒圆不能越过端头 / 残缺口
    if inner and inner[-1] + math.sqrt((R + rf) ** 2 - rf ** 2) > lim + 1e-6:
        raise ValueError('%s 右端缺口压端角 %s' % (code, inner[-1]))
    return inner, (tail[0] if tail else None)


def tail_arc(c, L, R):
    """端头外缺口在端面上的高 h 和从自由边 (c-R, 0) 走到 (L, h) 的圆心角（度）"""
    h = math.sqrt(R * R - (c - L) ** 2)
    return h, math.degrees(math.asin(h / R))


def edge_pts(x0, x1, centers, R, rf, sharp=()):
    """自由边上一串半圆缺口：沿 +x 走，材料在 d 增大一侧。返回 [(x, d, 到下一点的 bulge)]；d = 距自由边。
    缺口圆心在自由边上（半径 R），两缺口之间倒圆 rf；节距放不下两个倒圆时（如 57.5）用一个 rf 圆弧同时相切两圆。
    sharp 里的缺口两边都不倒圆。"""
    pts = [[x0, 0.0, 0.0]]
    dx = math.sqrt((R + rf) ** 2 - rf ** 2)
    ang = math.degrees(math.asin(rf / (R + rf)))         # 接点相对圆心的仰角（9.435°）
    cs = sorted(centers)
    prev_tip = None                                      # 上一段留下的尖角圆（cx, cy）
    for i, c in enumerate(cs):
        if c in sharp:                                   # 不倒圆的缺口：直边直接接半圆（1610321A 新图最后一个整缺口）
            if prev_tip is not None:
                raise ValueError('不倒圆缺口 %s 紧挨着尖角圆' % c)
            pts.append([c - R, 0.0, -1.0])
            pts.append([c + R, 0.0, 0.0])
            continue
        if prev_tip is None:
            pts.append([c - dx, 0.0, _bulge(90 - ang)])  # 直边 → 倒圆
            p = (c - R * math.cos(math.radians(ang)), R * math.sin(math.radians(ang)))
            a_in = 180 - ang
        else:
            tx, ty = prev_tip
            k = R / (R + rf)
            p = (c + (tx - c) * k, ty * k)
            a_in = math.degrees(math.atan2(p[1], p[0] - c))
        nxt = cs[i + 1] if i + 1 < len(cs) else None
        if nxt is not None and nxt - c < 2 * dx:
            hg = (nxt - c) / 2
            ty = math.sqrt((R + rf) ** 2 - hg ** 2)
            tx = c + hg
            k = R / (R + rf)
            q = (c + (tx - c) * k, ty * k)
            a_out = math.degrees(math.atan2(q[1], q[0] - c))
            pts.append([p[0], p[1], -_bulge(a_in - a_out)])
            # 尖角圆弧绕 (tx, ty) 靠自由边一侧走过两个接点（1610322A：199.5°~340.5°，圆心角 141°）
            pts.append([q[0], q[1], _bulge(180 - 2 * math.degrees(math.atan2(ty, hg)))])
            prev_tip = (tx, ty)
        else:
            q = (c + R * math.cos(math.radians(ang)), R * math.sin(math.radians(ang)))
            pts.append([p[0], p[1], -_bulge(a_in - ang)])
            pts.append([q[0], q[1], _bulge(90 - ang)])
            pts.append([c + dx, 0.0, 0.0])
            prev_tip = None
    pts.append([x1, 0.0, 0.0])
    return pts


def add_forward(path, pts, y_of):
    """沿 +x 接到 Path（y_of(d) 给展开 y），bulge 符号取决于 d 方向：y 随 d 增大时不变，减小时取反"""
    sign = 1 if y_of(1) > y_of(0) else -1
    for i, (x, d, b) in enumerate(pts):
        path.to(x, y_of(d))
        path.v[-1][2] = sign * b
    path.v[-1][2] = 0.0
    return path


def add_reverse(path, pts, y_of):
    """沿 -x 接到 Path（顺序反过来）"""
    sign = 1 if y_of(1) > y_of(0) else -1
    n = len(pts)
    for i in range(n - 1, -1, -1):
        x, d, _ = pts[i]
        path.to(x, y_of(d))
        path.v[-1][2] = -sign * pts[i - 1][2] if i > 0 else 0.0
    return path


# ---------------------------------------------------------------- 机身板
def body(C, code, L):
    t, w = 2.5, C.bd(2.5)
    S = sheet(C, code)
    # 主视图：宽 L、高 > 100
    main = [v for v in S.views if abs(v[2] - v[0] - L) < 0.1 and v[3] - v[1] > 100]
    wing = S.view(L, 25)
    if len(main) != 1:
        raise ValueError('%s 主视图 %s' % (code, main))
    main = main[0]
    H = main[3] - main[1]
    x0m, y0m = main[0], main[1]
    W = 25.0
    yr = W - w / 2                     # 红线
    fy = lambda s: yr + (s - w / 2)    # 主视图上距底外形 s 的点
    top = fy(H)

    # ---- 主视图的弧：板角 R、腰形孔、缺口
    corners, notch_l, notch_r, slot_t, slot_b = [], [], [], [], []
    for cx, cy, r, a0, a1 in S.arcs_in(main):
        x, s = cx - x0m, cy - y0m
        if abs(r - 4.25) < 0.01:
            (slot_t if abs((a0 % 360) - 0) < 1 else slot_b).append((x, s))
        elif abs(r - 5) < 0.01:
            if abs(s - (H - 5)) < EPS and (abs(x - 5) < EPS or abs(x - (L - 5)) < EPS):
                corners.append((x, s))
            elif abs(a0 - 90) < 1:
                notch_l.append((x - 5, s + 5))
            elif abs(a0) < 1:
                notch_r.append((x + 5, s + 5))
            else:
                raise ValueError('%s 主视图未知 R5 (%s,%s) %s-%s' % (code, x, s, a0, a1))
        else:
            raise ValueError('%s 主视图未知圆弧 r=%s' % (code, r))
    if len(corners) != 2:
        raise ValueError('%s 板角 R5 %s' % (code, corners))
    if len(notch_l) != len(notch_r) or len(slot_t) != len(slot_b):
        raise ValueError('%s 缺口 / 腰孔不成对' % code)
    notches = []
    for (xa, sa), (xb, sb) in zip(sorted(notch_l), sorted(notch_r)):
        if abs(sa - sb) > EPS:
            raise ValueError('%s 缺口高不一致' % code)
        notches.append((xa, xb, sa))

    # ---- 翼边视图：自由边方向、圆角、孔
    wa = S.arcs_in(wing)
    if not wa or any(abs(a[2] - 5) > 0.01 for a in wa):
        raise ValueError('%s 翼边视图圆弧 %s' % (code, wa))
    ymid = (wing[1] + wing[3]) / 2
    free_top = all(a[1] > ymid for a in wa)
    if not free_top and not all(a[1] < ymid for a in wa):
        raise ValueError('%s 翼边圆角不在同一侧' % code)
    y_free = wing[3] if free_top else wing[1]
    if len(wa) != 2 + 2 * len(notches):
        raise ValueError('%s 翼边圆角 %d 个，缺口 %d' % (code, len(wa), len(notches)))
    wing_x = sorted(a[0] - wing[0] for a in wa)
    for xa, xb, _ in notches:              # 翼边圆角要贴着缺口两侧
        if not (min(abs(x - (xa - 5)) for x in wing_x) < EPS and min(abs(x - (xb + 5)) for x in wing_x) < EPS):
            raise ValueError('%s 翼边缺口和主视图不一致' % code)

    # ---- 外形
    Rc = 5.0
    VIEWMAP[code] = dict(kind='body', main=main, wing=wing, y_free=y_free, yr=yr, w=w)
    p = Piece()
    path = Path(Rc, 0)
    for xa, xb, sn in sorted(notches):
        yn = fy(sn)
        path.to(xa - Rc, 0).arc(xa, Rc, K90).to(xa, yn - Rc).arc(xa + Rc, yn, -K90)
        path.to(xb - Rc, yn).arc(xb, yn - Rc, -K90).to(xb, Rc).arc(xb + Rc, 0, K90)
    path.to(L - Rc, 0).arc(L, Rc, K90).to(L, top - Rc).arc(L - Rc, top, K90).to(Rc, top).arc(0, top - Rc, K90).to(0, Rc).arc(Rc, 0, K90)
    path.into(p)
    # ---- 折弯线（缺口处断开，端点落在轮廓上）
    x = 0.0
    for xa, xb, _ in sorted(notches):
        p.bend(x, yr, xa, yr, w)
        x = xb
    p.bend(x, yr, L, yr, w)
    # ---- 孔
    for cx, cy, d in S.circles_in(main):
        p.circle(cx - x0m, fy(cy - y0m), d)
    for cx, cy, d in S.circles_in(wing):
        p.circle(cx - wing[0], abs(y_free - cy), d)
    for (xt, st), (xb, sb) in zip(sorted(slot_t), sorted(slot_b)):   # 同 x 按高低配对（圆心距 10，宽 8.5）
        if abs(xt - xb) > EPS or not 0 < st - sb < 30:
            raise ValueError('%s 腰孔配对 (%s,%s) (%s,%s)' % (code, xt, st, xb, sb))
        p.slot(xt, fy(sb), xt, fy(st), 8.5)
    return [(C.lab(t, 1), p)]


# ---------------------------------------------------------------- 防护罩（U 形）
def guard(C, code, L):
    t, w = 1.5, C.bd(1.5)
    S = sheet(C, code)
    main = S.view(L, 42)
    web = S.view(L, 60)
    x0, ytop = main[0], main[3]
    if S.circles_in(web):
        raise ValueError('%s 腹板有孔' % code)
    # R25.5 缺口：可见两段，圆心在后腿自由边（视图底）
    # （圆心可能在视图外：右端被一截残缺口切掉端角，所以不用 arcs_in）
    cs = sorted({round(a[0] - x0, 3) for a in S.arcs if abs(a[2] - 25.5) < 0.01 and abs(a[1] - main[1]) < EPS
                 and main[0] - 25.5 < a[0] < main[2] + 25.5 and main[1] - 1 < a[1] < main[3]})
    # 倒圆 / 端角
    rf = {round(a[2], 3) for a in S.arcs_in(main) if a[2] < 10}
    if rf != {5.0}:
        raise ValueError('%s 圆角 %s' % (code, rf))
    # 前腿自由边：端角圆心比视图底高出的那一组
    yc = sorted({round(a[1] - main[1], 3) for a in S.arcs_in(main)
                 if abs(a[2] - 5) < 0.01 and abs(a[0] - x0 - 5) < EPS})
    if len(yc) != 2 or abs(yc[0] - 5) > EPS:
        raise ValueError('%s 端角 %s' % (code, yc))
    hF = 42 - (yc[1] - 5)              # 前腿高
    hB = 42.0
    r1 = hF - w / 2
    r2 = r1 + 60 - w
    top = r2 + hB - w / 2
    R, Rc = 25.5, 5.0
    VIEWMAP[code] = dict(kind='guard', main=main, web=web, hF=hF, top=top, r1=r1, r2=r2, w=w)
    p = Piece()
    # 每个整缺口两边有没有 R5 倒圆（圆心在自由边内 5、距缺口圆心 dx）
    dx = math.sqrt((R + Rc) ** 2 - Rc ** 2)
    fil = [a[0] - x0 for a in S.arcs_in(main) if abs(a[2] - Rc) < 0.01 and abs(a[1] - main[1] - Rc) < EPS]
    sharp = set()
    for c in cs:
        if c > L:
            continue
        n = sum(min((abs(f - (c + sg * dx)) for f in fil), default=9) < EPS for sg in (-1, 1))
        if n == 0:
            sharp.add(c)
        elif n == 1 and not (c - dx < Rc + 1e-6 or c + dx > L - Rc - 1e-6):
            raise ValueError('%s 缺口 %s 只有一边倒圆' % (code, c))
    cs, tail = split_tail(code, cs, L, R, Rc)
    path = Path(Rc, 0).to(L - Rc, 0).arc(L, Rc, K90)
    if tail is None:
        path.to(L, top - Rc).arc(L - Rc, top, K90)
        pts = edge_pts(Rc, L - Rc, cs, R, Rc, sharp)
    else:                              # 端角被残缺口切掉：端面直上到缺口，沿 R25.5 顺时针到自由边，不倒圆（按图）
        h, th = tail_arc(tail, L, R)
        path.to(L, top - h).arc(tail - R, top, -_bulge(th))
        pts = edge_pts(Rc, tail - R, cs, R, Rc, sharp)
    add_reverse(path, pts, lambda d: top - d)
    path.arc(0, top - Rc, K90).to(0, Rc).arc(Rc, 0, K90)
    path.into(p)
    p.bend(0, r1, L, r1, w).bend(0, r2, L, r2, w)
    for cx, cy, d in S.circles_in(main):
        p.circle(cx - x0, hF - (ytop - cy), d)
    return [(C.lab(t, 1), p)]


# ---------------------------------------------------------------- 保护罩下（Z 形）
def seq(start, *runs):
    """start, (节距, 个数), ... → 坐标表"""
    out = [start]
    for pitch, n in runs:
        for _ in range(n):
            out.append(out[-1] + pitch)
    return out


def lower(C, code, L, a, b, big, small, slot=None):
    t, w = 1.5, C.bd(1.5)
    S = sheet(C, code)
    # 主视图 / 俯视图可能被断开成几段：按 y 取同高的几段拼起来
    mains = sorted([v for v in S.views if abs(v[3] - v[1] - 58) < 0.1 and v[2] - v[0] > 50], key=lambda v: v[0])
    webs = sorted([v for v in S.views if abs(v[3] - v[1] - 56) < 0.1 and v[2] - v[0] > 50], key=lambda v: v[0])
    if not mains or not webs:
        raise ValueError('%s 视图 %s' % (code, S.views))
    # 只留和最宽那段同一行的（剖视 A 也可能是 56 x 58，如 1610346A）
    ym = max(mains, key=lambda v: v[2] - v[0])[1]
    mains = [v for v in mains if abs(v[1] - ym) < 0.1]
    yw = max(webs, key=lambda v: v[2] - v[0])[1]
    webs = [v for v in webs if abs(v[1] - yw) < 0.1]
    x0 = mains[0][0]
    y0, y1 = mains[0][1], mains[0][3]
    rg = (x0, y0, mains[-1][2], y1)
    # 断开位置：主视图范围内的折线成对（两条折线外包的中点）
    xs = sorted({round((q[0] + q[2]) / 2, 2) for q in S.brk if q[1] <= y1 and q[3] >= y0 and x0 < q[0] and q[2] < rg[2]})
    brks = [(xs[i] + xs[i + 1]) / 2 for i in range(0, len(xs) - 1, 2)]
    vw = rg[2] - rg[0]
    total = L - vw
    if len(brks) == 0:
        if abs(total) > 0.05:
            raise ValueError('%s 无断开但宽度 %s != %s' % (code, vw, L))
        shifts = []
    elif len(brks) == 1:
        shifts = [total]
    elif len(brks) == 2:
        # 两处断开：第一处的量由开槽定位尺寸定（槽左边线 = slot[0]）
        wy0 = webs[0][1]
        vl = [l for l in S.lines_in((x0, wy0, rg[2], webs[0][3])) if abs(l[0] - l[2]) < 1e-3 and abs(abs(l[1] - l[3]) - 27) < 0.1]
        sx = sorted(l[0] for l in vl)
        if len(sx) != 2 or slot is None:
            raise ValueError('%s 开槽边线 %s' % (code, sx))
        s1 = slot[0] - (sx[0] - x0)
        if abs(sx[1] - sx[0] - (slot[1] - slot[0])) > 0.05:
            raise ValueError('%s 开槽宽 %s' % (code, sx))
        shifts = [s1, total - s1]
    else:
        raise ValueError('%s 断开 %s 处' % (code, len(brks)))

    def tx(v, ref=None):
        """视图 x → 真实 x；ref 是判断落在哪一段用的点（断开处被截掉一半的缺口，圆心在另一段，要按弧中点判断）"""
        s = v - x0
        for k, br in enumerate(brks):
            if (v if ref is None else ref) > br:
                s += shifts[k]
        return s

    def atx(q):                             # 圆弧圆心按弧中点所在的段换算
        m = math.radians((q[3] + ((q[4] - q[3]) % 360) / 2))
        return tx(q[0], q[0] + q[2] * math.cos(m))

    arcs = S.arcs_in(rg)
    # 圆心在视图外的残缺口（端头外那个缺口切掉端角，1610322A 新图右端；断开处的半个缺口圆心也可能落在另一段）
    arcs += [q for q in S.arcs if abs(q[2] - 25.5) < 0.01 and abs(q[1] - y0) < EPS and q not in arcs
             and rg[0] - 25.5 < q[0] < rg[2] + 25.5]
    # ---- 看得见的缺口必须都在标注序列上
    for a_ in arcs:
        if abs(a_[2] - 25.5) < 0.01:
            if abs(a_[1] - y0) > EPS or min(abs(atx(a_) - c) for c in big) > 0.05:
                raise ValueError('%s Φ51 缺口 x=%.3f 不在标注序列' % (code, atx(a_)))
        elif abs(a_[2] - 4.5) < 0.01:
            if abs(a_[1] - (y1 - 4)) > EPS or min(abs(atx(a_) - c) for c in small) > 0.05:
                raise ValueError('%s Φ9 缺口 x=%.3f 不在标注序列' % (code, atx(a_)))
    # 上腿两端
    ups = sorted(l[0] for l in S.lines_in(rg) if abs(l[0] - l[2]) < 1e-3 and abs(l[1] - l[3]) > 1 and l[1] > y0 + 42.5 and l[3] > y0 + 42.5
                 and min(l[1], l[3]) < y0 + 46 and tx(l[0]) not in (0, L))
    if abs(min(tx(u) for u in ups) - a) > 0.05 or abs(max(tx(u) for u in ups) - b) > 0.05:
        raise ValueError('%s 上腿范围 %s' % (code, [round(tx(u), 2) for u in ups]))
    # 端角半径（下腿、上腿）
    rfc = {round(a_[2], 3) for a_ in arcs if abs(a_[1] - (y0 + a_[2])) < EPS and (abs(tx(a_[0]) - a_[2]) < EPS or abs(tx(a_[0]) - (L - a_[2])) < EPS)}
    if len(rfc) != 1:
        raise ValueError('%s 下腿端角 %s' % (code, rfc))
    rc = rfc.pop()
    rf = 5.0

    y_1 = 42 - w / 2
    y_2 = y_1 + 56 - w
    top = y_2 + 17.5 - w / 2
    web_s = lambda s: y_2 - (s - w / 2)     # 腹板上距上腿外表面 s
    rel, rr = 7.0, 4.0                      # 腹板两端让位 7、根部 R4（标注 7 / R4，下面按俯视图核对）
    wtop = webs[0][3]
    wr = (x0, webs[0][1], rg[2], wtop)
    wlines = S.lines_in(wr)
    if not any(abs(l[1] - l[3]) < 1e-3 and abs(wtop - l[1] - rel) < EPS and max(tx(l[0]), tx(l[2])) < a for l in wlines):
        raise ValueError('%s 腹板端部让位不是 7' % code)
    warcs = [q for q in S.arcs_in(wr)]
    if sorted({round(q[2], 3) for q in warcs}) != [4.0] or len(warcs) != 4:
        raise ValueError('%s 腹板圆角 %s' % (code, warcs))
    for ax_ in (a - rr, b + rr):
        if not any(abs(tx(q[0]) - ax_) < EPS and abs(wtop - q[1] - (rel - rr)) < EPS for q in warcs):
            raise ValueError('%s 腹板根部 R4 圆心不对 %s' % (code, ax_))
    sl_lines = [l for l in wlines if abs(l[0] - l[2]) < 1e-3 and abs(abs(l[1] - l[3]) - 27) < 0.1]
    if bool(sl_lines) != bool(slot):
        raise ValueError('%s 开槽和表不符 %s' % (code, sl_lines))
    # 槽底：slot 第 3 项 = 腹板视图上槽底距下腿外表面的高度 h（只切进折弯圆角一部分，1610512A 开槽件 0.405）；
    # 外 R3，从下腿切点起 φ = acos((3 − h) / 3)，展开按弧长比例落在折弯区（BA = 2×3 − BD）；没有第 3 项 = 切到下腿切点
    hcut = slot[2] if slot and len(slot) > 2 else None
    if slot and hcut is None and not any(abs(l[1] - l[3]) < 1e-3 and abs(l[1] - (y0 + 39)) < EPS and abs(abs(l[0] - l[2]) - (slot[1] - slot[0])) < 0.05
                        for l in S.lines_in(rg)):
        raise ValueError('%s 开槽下沿不在下腿距外表面 3 处' % code)
    if hcut is not None and not any(abs(l[1] - l[3]) < 1e-3 and abs(l[1] - (y0 + 42 - t)) < EPS and abs(abs(l[0] - l[2]) - (slot[1] - slot[0])) < 0.05
                                    for l in S.lines_in(rg)):
        raise ValueError('%s 开槽在主视图上应只切腹板厚度' % code)
    ye = web_s(rel)
    yc = ye + rr                            # 根部凹圆心

    VIEWMAP[code] = dict(kind='lower', x0=x0, y0=y0, y1=y1, wtop=wtop, brks=brks, shifts=shifts, y_1=y_1, y_2=y_2, top=top, w=w)
    p = Piece()
    path = Path(rc, 0)
    big_in, tail = split_tail(code, big, L, 25.5, rf)
    if tail is None:
        add_forward(path, edge_pts(rc, L - rc, big_in, 25.5, rf), lambda d: d)
        path.arc(L, rc, K90)
    else:                                   # 端角被残缺口切掉：沿 R25.5 顺时针到端面，不倒圆（按图）
        if not any(abs(atx(q) - tail) < 0.05 for q in arcs if abs(q[2] - 25.5) < 0.01):
            raise ValueError('%s 表里的端头外缺口 %s 图上没有' % (code, tail))
        h, th = tail_arc(tail, L, 25.5)
        add_forward(path, edge_pts(rc, tail - 25.5, big_in, 25.5, rf), lambda d: d)
        path.arc(L, h, -_bulge(th))
    path.to(L, ye - rr).arc(L - rr, ye, K90)
    path.to(b + rr, ye).arc(b, yc, -K90)
    # 上腿：右端角 R4
    path.to(b, top - 4).arc(b - 4, top, K90)
    for c in sorted(small, reverse=True):
        if c - 6.5 < a + 4:                 # 左端放不下：R4 直接和 Φ9 圆相切（1610322A）
            yr_ = top - 4
            path.to(c + 6.5, top).arc(c + 4.5, top - 2, K90).to(c + 4.5, yr_)
            cx1 = a + 4
            dx_ = c - cx1
            dy_ = math.sqrt(8.5 ** 2 - dx_ ** 2)
            cy1 = yr_ - dy_
            k = 4.5 / 8.5
            qx, qy = c + (cx1 - c) * k, yr_ + (cy1 - yr_) * k
            sw = 360 - math.degrees(math.atan2(qy - yr_, qx - c)) % 360
            path.arc(qx, qy, -_bulge(sw))
            sw2 = 180 - math.degrees(math.atan2(qy - cy1, qx - cx1))
            path.arc(a, cy1, _bulge(sw2))
            break
        path.to(c + 6.5, top).arc(c + 4.5, top - 2, K90).to(c + 4.5, top - 4)
        path.arc(c - 4.5, top - 4, -1.0).to(c - 4.5, top - 2).arc(c - 6.5, top, K90)
    else:
        path.to(a + 4, top).arc(a, top - 4, K90)
    path.to(a, yc).arc(a - rr, ye, -K90)
    path.to(rr, ye).arc(0, ye - rr, K90).to(0, rc).arc(rc, 0, K90)
    path.into(p)
    # 开槽：腹板上距下腿外表面 30，向下穿过折弯到下腿距外表面 3（主视图 42.639 那条线）
    if slot:
        sl = y_1 - (3 - w / 2)
        if hcut is not None:
            sl += (2 * 3 - w) * math.degrees(math.acos((3 - hcut) / 3)) / 90
        sh = y_1 + (30 - w / 2)
        p.rect(slot[0], sl, slot[1], sh)
        p.bend(0, y_1, slot[0], y_1, w).bend(slot[1], y_1, L, y_1, w)
    else:
        p.bend(0, y_1, L, y_1, w)
    p.bend(a, y_2, b, y_2, w)
    return [(C.lab(t, 1), p)]


# ---------------------------------------------------------------- 表
BODY = [('1610301A-K82.5-L2310', 2310), ('1610302A-K82.5-L2310', 2310), ('1610309A-K63.5-L2042', 2124.5),
        ('1610310A-K63.5-L2042', 2124.5), ('1610315A-K82.5-L2062.5', 2062.5), ('1610316A-K82.5-L2062.5', 2062.5),
        ('1610343A-K82.5-L2475', 2475), ('1610344A-K82.5-L2475', 2475), ('1610501A-K82.5-L1485', 1485),
        ('1610502A-K82.5-L1485', 1485), ('1610503A-K82.5-L1567.5', 1567.5), ('1610504A-K82.5-L1567.5', 1567.5),
        ('1610801A-K82.5-L907.5', 907.5), ('1610802A-K82.5-L907.5', 907.5)]
GUARD = [('1610311A-K82.5-L2310', 2310), ('1610317A-K82.5-L2062.5', 2062.5), ('1610321A-K63.5-L2042', 2124.5),
         ('1610345A-K82.5-L2475', 2475), ('1610511A-K82.5-L1485', 1485), ('1610513A-K82.5-L1567.5', 1567.5),
         ('1610813A-K82.5-L907.5', 907.5)]
# 号: L, 上腿 a, b, Φ51 序列, Φ9 序列, 开槽（尺寸全部抄标注，看得见的缺口在 lower() 里逐个核对）
_S825 = lambda n: seq(38.25, (82.5, n))
LOWER = [('1610312A-K82.5-L2310', 2304, 25, 2281, _S825(27), _S825(27), (1043, 1183)),
         ('1610318A-K82.5-L2062.5', 2056.5, 25, 2033.5, _S825(24), _S825(24), (587, 739)),
         ('1610322A-K63.5-L2042', 2118.5, 22, 2096.5, seq(41.25, (82.5, 4), (57.5, 1), (63.5, 27)), seq(28.75, (63.5, 32)), (1087.5, 1237.5)),
         ('1610346A-K82.5-L2475', 2469, 25, 2446, _S825(29), _S825(29), None),
         ('1610512A-K82.5-L1485', 1479, 25, 1456, _S825(17), _S825(17), None),
         ('1610512A-K82.5-L1485-开槽', 1479, 25, 1456, _S825(17), _S825(17), (257, 409, 0.405)),   # 11-12 更改单：2 件里 1 件改开槽
         ('1610514A-K82.5-L1567.5', 1561.5, 25, 1538.5, _S825(18), _S825(18), None),
         ('1610814A-K82.5-L907.5', 901.5, 25, 878.5, _S825(10), _S825(10), None)]


def _make(fn, *args):
    def f(q):
        lab, p = fn(*args)[0]
        return [(lab.replace(',1件', ',%d件' % q), p)]
    return f


def register(C):
    for code, L in BODY:
        C.PARTS[code] = _make(body, C, code, L)
    for code, L in GUARD:
        C.PARTS[code] = _make(guard, C, code, L)
    for code, L, a, b, big, small, slot in LOWER:
        C.PARTS[code] = _make(lower, C, code, L, a, b, big, small, slot)
