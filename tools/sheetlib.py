# -*- coding: utf-8 -*-
"""下料图生成用的小工具库：零件几何(Piece)、圆角轮廓、折弯线、从图纸视图提取几何。"""
import math
import ezdxf
from ezdxf import bbox as ezbbox

CUT = '可见 (ISO)'
BEND = '折弯线'

# 折弯扣除 BD（厚度 -> BD），来自 “SUS304 折弯计算.png” / “Q235B 折弯计算.png”
BD_SUS304 = {0.5: 0.8, 0.8: 1.4, 1: 1.7, 1.2: 2, 1.5: 2.3, 2: 3, 2.5: 4, 3: 5,
             4: 6.8, 5: 8.4, 6: 10.5, 8: 14, 10: 17, 12: 22}
BD_Q235B = {0.5: 0.8, 0.8: 1.4, 1: 1.7, 1.2: 2, 1.5: 2.5, 2: 3.5, 2.5: 4.25, 3: 5,
            4: 6.8, 5: 8.4, 6: 10.2, 8: 13.6, 10: 17, 12: 20.6}

# 螺纹孔按小径开孔（与 NO.441 人工下料一致：M4->3.24, M5->4.13, M6->4.92, M8->6.65）
TAP = {'M3': 2.459, 'M4': 3.242, 'M5': 4.134, 'M6': 4.917, 'M8': 6.647,
       'M10': 8.376, 'M12': 10.106, 'M16': 13.835, 'M20': 17.294}


def bd(thk, mat='SUS304'):
    return (BD_SUS304 if mat.upper().startswith('SUS') else BD_Q235B)[thk]


def fillet_path(verts, closed=True):
    """verts: [(x, y, r)] 多边形顶点及该顶点圆角半径 -> [(x, y, bulge)] 供 LWPOLYLINE 使用"""
    n = len(verts)
    out = []
    for i, (x, y, r) in enumerate(verts):
        if r <= 0 or (not closed and (i == 0 or i == n - 1)):
            out.append([x, y, 0.0])
            continue
        px, py = verts[i - 1][:2]
        nx, ny = verts[(i + 1) % n][:2]
        u1 = (px - x, py - y); l1 = math.hypot(*u1); u1 = (u1[0] / l1, u1[1] / l1)
        u2 = (nx - x, ny - y); l2 = math.hypot(*u2); u2 = (u2[0] / l2, u2[1] / l2)
        cosang = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        ang = math.acos(cosang)
        d = r / math.tan(ang / 2)
        sweep = math.pi - ang
        cross = (x - px) * (ny - y) - (y - py) * (nx - x)
        b = math.tan(sweep / 4) * (1 if cross > 0 else -1)
        out.append([x + u1[0] * d, y + u1[1] * d, b])
        out.append([x + u2[0] * d, y + u2[1] * d, 0.0])
    return out


class Piece:
    """一个零件展开件，坐标为零件局部坐标(mm)。"""

    def __init__(self, name=''):
        self.name = name
        self.ents = []   # (kind, data, attribs)

    # ---- 基本图元 ----
    def poly(self, pts, closed=True, layer=CUT, **attr):
        pts = [tuple(p) + (0.0,) * (3 - len(p)) for p in pts]
        self.ents.append(('LWPOLYLINE', (pts, closed), dict(layer=layer, **attr)))
        return self

    def outline(self, verts, closed=True, layer=CUT):
        """verts: [(x,y)] 或 [(x,y,r)]，r 为该角的圆角半径"""
        verts = [tuple(v) + (0.0,) * (3 - len(v)) for v in verts]
        return self.poly(fillet_path(verts, closed), closed, layer)

    def rect(self, x0, y0, x1, y1, r=0.0, layer=CUT):
        return self.outline([(x0, y0, r), (x1, y0, r), (x1, y1, r), (x0, y1, r)], True, layer)

    def circle(self, cx, cy, d, layer=CUT):
        self.ents.append(('CIRCLE', ((cx, cy), d / 2.0), dict(layer=layer)))
        return self

    def tap(self, cx, cy, m):
        return self.circle(cx, cy, TAP[m])

    def slot(self, x0, y0, x1, y1, w, layer=CUT):
        """腰形孔：两端圆心 (x0,y0)-(x1,y1)，宽 w"""
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-9:
            return self.circle(x0, y0, w, layer)
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        pts = [(x0 - nx, y0 - ny, 0), (x1 - nx, y1 - ny, 1), (x1 + nx, y1 + ny, 0), (x0 + nx, y0 + ny, 1)]
        return self.poly(pts, True, layer)

    def arc_slot(self, cx, cy, r, a0, a1, w, layer=CUT):
        """弧形腰孔：中心 (cx,cy)、中心线半径 r、从 a0 逆时针到 a1（度）、宽 w"""
        ro, ri = r + w / 2, r - w / 2
        b = math.tan(math.radians(a1 - a0) / 4)
        pt = lambda rr, a: (cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)))
        pts = [pt(ro, a0) + (b,), pt(ro, a1) + (1,), pt(ri, a1) + (-b,), pt(ri, a0) + (1,)]
        return self.poly(pts, True, layer)

    def line(self, x0, y0, x1, y1, layer=CUT, **attr):
        self.ents.append(('LINE', ((x0, y0), (x1, y1)), dict(layer=layer, **attr)))
        return self

    def arc(self, cx, cy, r, a0, a1, layer=CUT):
        self.ents.append(('ARC', ((cx, cy), r, a0, a1), dict(layer=layer)))
        return self

    def bend(self, x0, y0, x1, y1, w, red_only=False):
        """折弯线：中心线(红) + 两侧各 w/2 的边界线(蓝)，w 为 BD（同 NO.441 人工图）。
        非 90° 折弯按历史人工习惯只画红色中心线（red_only=True）。"""
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        self.poly([(x0, y0), (x1, y1)], False, BEND, linetype='CENTER', color=1, ltscale=0.5)
        if red_only:
            return self
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny)], False, BEND, linetype='CENTER', color=5)
        self.poly([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny)], False, BEND, linetype='CENTER', color=5)
        return self

    def text(self, x, y, s, h=5, layer='0', color=1):
        self.ents.append(('TEXT', ((x, y), s, h), dict(layer=layer, color=color, style='Z-English')))
        return self

    # ---- 变换 ----
    def _map(self, f, mirror=False, k=1.0):
        p = Piece(self.name)
        for kind, data, attr in self.ents:
            if kind == 'LWPOLYLINE':
                pts, closed = data
                npts = [f(x, y) + ((-b if mirror else b),) for x, y, b in pts]
                p.ents.append((kind, (npts, closed), attr))
            elif kind == 'CIRCLE':
                (cx, cy), r = data
                p.ents.append((kind, (f(cx, cy), r * k), attr))
            elif kind == 'LINE':
                a, b = data
                p.ents.append((kind, (f(*a), f(*b)), attr))
            elif kind == 'ARC':
                (cx, cy), r, a0, a1 = data
                c2 = f(cx, cy)
                # 通过端点求新角度
                def ang(a):
                    x, y = cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
                    nx, ny = f(x, y)
                    return math.degrees(math.atan2(ny - c2[1], nx - c2[0]))
                n0, n1 = ang(a0), ang(a1)
                if mirror:
                    n0, n1 = n1, n0
                p.ents.append((kind, (c2, r * k, n0, n1), attr))
            elif kind == 'TEXT':
                (x, y), s, h = data
                p.ents.append((kind, (f(x, y), s, h), attr))
        return p

    def moved(self, dx, dy):
        return self._map(lambda x, y: (x + dx, y + dy))

    def rotated(self, deg):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        return self._map(lambda x, y: (x * c - y * s, x * s + y * c))

    def scaled(self, k):
        """按比例缩放（图纸视图非 1:1 时还原实际尺寸）"""
        return self._map(lambda x, y: (x * k, y * k), k=k)

    def mirrored(self):
        """左右镜像 (x -> -x)"""
        return self._map(lambda x, y: (-x, y), mirror=True)

    def normalized(self):
        b = self.bbox()
        return self.moved(-b[0], -b[1])

    def bbox(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        self.draw(msp, 0, 0)
        b = ezbbox.extents(msp)
        return (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)

    def draw(self, msp, ox, oy):
        for kind, data, attr in self.ents:
            if kind == 'LWPOLYLINE':
                pts, closed = data
                msp.add_lwpolyline([(x + ox, y + oy, 0, 0, b) for x, y, b in pts], format='xyseb',
                                   close=closed, dxfattribs=attr)
            elif kind == 'CIRCLE':
                (cx, cy), r = data
                msp.add_circle((cx + ox, cy + oy), r, dxfattribs=attr)
            elif kind == 'LINE':
                (x0, y0), (x1, y1) = data
                msp.add_line((x0 + ox, y0 + oy), (x1 + ox, y1 + oy), dxfattribs=attr)
            elif kind == 'ARC':
                (cx, cy), r, a0, a1 = data
                msp.add_arc((cx + ox, cy + oy), r, a0, a1, dxfattribs=attr)
            elif kind == 'TEXT':
                (x, y), s, h = data
                msp.add_text(s, height=h, dxfattribs=dict(attr, insert=(x + ox, y + oy)))


def fit_holes(p, *ds):
    """带正公差的配合孔(如 Φ24 +0.021/0、Φ46 H7)：按历史人工习惯切割孔径 +0.1（NO.360 1431220A Φ24 -> Φ24.1）"""
    for i, (kind, data, attr) in enumerate(p.ents):
        if kind == 'CIRCLE':
            c, r = data
            for d in ds:
                if abs(2 * r - d) < 0.01:
                    p.ents[i] = (kind, (c, (d + 0.1) / 2), attr)
    return p


def extract(path, region, layers=(CUT,), drop=None):
    """从图纸 DXF 的某个视图区域提取可见轮廓线/孔，返回以区域左下角为原点的 Piece。
    drop(kind, info) 返回 True 的图元会被丢弃。"""
    doc = ezdxf.readfile(path)
    x0, y0, x1, y1 = region
    p = Piece()
    eps = 0.3
    for e in doc.modelspace():
        if e.dxf.layer not in layers:
            continue
        t = e.dxftype()
        if t not in ('LINE', 'ARC', 'CIRCLE', 'LWPOLYLINE', 'ELLIPSE', 'SPLINE'):
            continue
        b = ezbbox.extents([e])
        if not b.has_data:
            continue
        if not (b.extmin.x >= x0 - eps and b.extmax.x <= x1 + eps and b.extmin.y >= y0 - eps and b.extmax.y <= y1 + eps):
            continue
        if t == 'LINE':
            info = dict(a=(e.dxf.start.x - x0, e.dxf.start.y - y0), b=(e.dxf.end.x - x0, e.dxf.end.y - y0))
            if drop and drop('LINE', info):
                continue
            p.line(*info['a'], *info['b'])
        elif t == 'CIRCLE':
            info = dict(c=(e.dxf.center.x - x0, e.dxf.center.y - y0), d=2 * e.dxf.radius)
            if drop and drop('CIRCLE', info):
                continue
            p.circle(info['c'][0], info['c'][1], info['d'])
        elif t == 'ARC':
            info = dict(c=(e.dxf.center.x - x0, e.dxf.center.y - y0), r=e.dxf.radius, a0=e.dxf.start_angle, a1=e.dxf.end_angle)
            if drop and drop('ARC', info):
                continue
            p.arc(info['c'][0], info['c'][1], info['r'], info['a0'], info['a1'])
        else:
            # ELLIPSE/SPLINE 等转为多段线近似
            pts = [(v.x - x0, v.y - y0) for v in e.flattening(0.01)] if hasattr(e, 'flattening') else []
            if drop and drop(t, dict(pts=pts)):
                continue
            if pts:
                p.poly(pts, False)
    return p


def drop_concentric_outer(p, keep_outline_d=None, tol=0.05):
    """同心圆只保留最小的(通孔)；keep_outline_d 指定要保留的外形圆直径(如垫片外圆)"""
    circles = [(i, e) for i, e in enumerate(p.ents) if e[0] == 'CIRCLE']
    remove = set()
    for i, (k, ((cx, cy), r), a) in circles:
        for j, (k2, ((cx2, cy2), r2), a2) in circles:
            if i != j and abs(cx - cx2) < tol and abs(cy - cy2) < tol and r > r2 + 1e-6:
                if keep_outline_d and abs(2 * r - keep_outline_d) < 0.01:
                    continue
                remove.add(i)
    p.ents = [e for i, e in enumerate(p.ents) if i not in remove]
    return p


# ---------------------------------------------------------------- 断开视图还原
def _break_deltas(doc, region, axis=0):
    """找出区域内的断开线(图层“折线 (ISO)”)，用尺寸标注的覆盖文字求每处断开的真实缺口量。
    返回 [(a, b, delta)]：断开左边界 a、右边界 b（图纸坐标）、需补的长度 delta。"""
    x0, y0, x1, y1 = region
    lo, hi = (x0, x1) if axis == 0 else (y0, y1)
    zz = []
    for e in doc.modelspace():
        if e.dxf.layer != '折线 (ISO)':
            continue
        b = ezbbox.extents([e])
        if not b.has_data:
            continue
        if b.extmax.x < x0 - 1 or b.extmin.x > x1 + 1 or b.extmax.y < y0 - 1 or b.extmin.y > y1 + 1:
            continue
        c = (b.center.x if axis == 0 else b.center.y)
        if lo < c < hi:
            zz.append(c)
    zz.sort()
    # 成对：两条折线距离 < 20 视为一处断开
    brk = []
    i = 0
    while i < len(zz):
        if i + 1 < len(zz) and zz[i + 1] - zz[i] < 20:
            brk.append([zz[i], zz[i + 1], None]); i += 2
        else:
            i += 1
    # 用尺寸求 delta
    dims = []
    for e in doc.modelspace().query('DIMENSION'):
        t = (e.dxf.get('text') or '').strip()
        try:
            T = float(t)
        except ValueError:
            continue
        p2, p3 = e.dxf.get('defpoint2'), e.dxf.get('defpoint3')
        if p2 is None or p3 is None:
            continue
        a, b = (p2.x, p3.x) if axis == 0 else (p2.y, p3.y)
        a, b = min(a, b), max(a, b)
        # 尺寸方向需与 axis 一致
        ang = e.dxf.get('angle', 0) or 0
        if (axis == 0 and abs(math.sin(math.radians(ang))) > 0.01) or (axis == 1 and abs(math.cos(math.radians(ang))) > 0.01):
            continue
        dims.append((a, b, T - (b - a)))
    for _ in range(5):
        for a, b, dl in dims:
            inside = [k for k in brk if a < k[0] and k[1] < b]
            unknown = [k for k in inside if k[2] is None]
            if len(unknown) == 1:
                unknown[0][2] = dl - sum(k[2] for k in inside if k[2] is not None)
    return [tuple(k) for k in brk]


def extract_unbroken(path, region, drop=None, axis=0, layers=(CUT,)):
    """提取带断开(打断)画法的视图，按尺寸还原成真实长度，并补齐断开处的轮廓线"""
    doc = ezdxf.readfile(path)
    brk = _break_deltas(doc, region, axis)
    if any(d is None for _, _, d in brk):
        raise ValueError('断开处长度无法由尺寸确定: %s %s' % (path, brk))
    x0, y0 = region[0], region[1]

    def shift(v):
        s = 0.0
        for a, b, d in brk:
            if v > (a + b) / 2:
                s += d
        return s

    p = extract(path, region, layers=layers, drop=drop)
    q = Piece()
    for kind, data, attr in p.ents:
        def f(x, y):
            v = (x + x0) if axis == 0 else (y + y0)
            s = shift(v)
            return (x + s, y) if axis == 0 else (x, y + s)
        tmp = Piece(); tmp.ents = [(kind, data, attr)]
        q.ents += tmp._map(f).ents
    # 补线：断开左右两侧同一高度的端点相连
    for a, b, d in brk:
        sa = shift(a - 1e-6) ; sb = shift(b + 1e-6)
        al, bl = (a - x0, b - x0) if axis == 0 else (a - y0, b - y0)
        left, right = [], []
        for kind, data, attr in q.ents:
            if kind != 'LINE':
                continue
            for pt in data:
                u, w = (pt[0], pt[1]) if axis == 0 else (pt[1], pt[0])
                if abs(u - (al + sa)) < 1.0:
                    left.append((u, w))
                elif abs(u - (bl + sb)) < 1.0:
                    right.append((u, w))
        for u, w in left:
            for u2, w2 in right:
                if abs(w - w2) < 0.05:
                    if axis == 0:
                        q.line(u, w, u2, w2)
                    else:
                        q.line(w, u, w2, u2)
                    break
    return q


def stretch_tab(p, xb, angle_deg, side='left'):
    """小角度折弯边在视图中被投影缩短：把 xb 左(右)侧部分按 1/cos(angle) 拉伸还原"""
    k = 1.0 / math.cos(math.radians(angle_deg))
    if side == 'left':
        f = lambda x, y: ((xb - (xb - x) * k) if x < xb else x, y)
    else:
        f = lambda x, y: ((xb + (x - xb) * k) if x > xb else x, y)
    return p._map(f)


def fold_edge(p, x_edge, L, w, side='left', tol=0.05):
    """把视图中位于 x=x_edge 的竖直外轮廓线替换为向外展开的翻边(外形长 L，BD=w)。
    返回 (y_lo, y_hi)。side='left' 表示翻边向 -x 展开。"""
    ys = []
    keep = []
    for e in p.ents:
        k, data, a = e
        if k == 'LINE':
            (x0, y0), (x1, y1) = data
            if abs(x0 - x_edge) < tol and abs(x1 - x_edge) < tol:
                ys += [y0, y1]
                continue
        keep.append(e)
    p.ents = keep
    if not ys:
        raise ValueError('未找到边线 x=%s' % x_edge)
    y_lo, y_hi = min(ys), max(ys)
    s = -1 if side == 'left' else 1
    xf = x_edge + s * (L - w)
    p.poly([(x_edge, y_lo), (xf, y_lo), (xf, y_hi), (x_edge, y_hi)], False)
    xc = x_edge - s * w / 2
    p.bend(xc, y_lo, xc, y_hi, w)
    return y_lo, y_hi


def relief_params(t, w):
    """角部释放槽参数（按“释放槽样式.dxf”）：
    p = 2t（V 形槽尖点伸入底板的距离，沿两方向各 p）
    g = 2t - BD（槽口在两翻边侧边上距底板外形线的距离）
    s = t + 0.1（相邻两翻边中，内缩翻边每侧内缩量；另一翻边保持全宽）"""
    p = 2 * t
    return p, p - w, t + 0.1


def clip_out_box(p, x0, y0, x1, y1, layer=CUT, eps=1e-6):
    """删除/裁剪切割层直线中落在矩形框内的部分（用于在已有轮廓上开释放槽）"""
    out = []
    for e in p.ents:
        k, d, a = e
        if k != 'LINE' or a.get('layer') != layer:
            out.append(e); continue
        (ax, ay), (bx, by) = d
        # Liang-Barsky 求线段在框内的参数区间
        t0, t1 = 0.0, 1.0
        dx, dy = bx - ax, by - ay
        ok = True
        for pp, qq in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            if abs(pp) < 1e-12:
                if qq < -eps:
                    ok = False
                continue
            r = qq / pp
            if pp < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
        if not ok or t0 >= t1 - 1e-9:
            out.append(e); continue
        if t0 > 1e-9:
            out.append(('LINE', ((ax, ay), (ax + dx * t0, ay + dy * t0)), a))
        if t1 < 1 - 1e-9:
            out.append(('LINE', ((ax + dx * t1, ay + dy * t1), (bx, by)), a))
    p.ents = out
    return p


def bd_angle(t, ang, K, R=None):
    """任意角度折弯的折弯扣除（外形尺寸法），R 默认取 t"""
    R = t if R is None else R
    a = math.radians(ang)
    return 2 * (R + t) * math.tan(a / 2) - a * (R + K * t)
