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
       'M10': 8.376, 'M12': 10.106, 'M16': 13.835}


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

    def line(self, x0, y0, x1, y1, layer=CUT, **attr):
        self.ents.append(('LINE', ((x0, y0), (x1, y1)), dict(layer=layer, **attr)))
        return self

    def arc(self, cx, cy, r, a0, a1, layer=CUT):
        self.ents.append(('ARC', ((cx, cy), r, a0, a1), dict(layer=layer)))
        return self

    def bend(self, x0, y0, x1, y1, w):
        """折弯线：中心线(红) + 两侧各 w/2 的边界线(蓝)，w 为 BD（同 NO.441 人工图）"""
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        self.poly([(x0, y0), (x1, y1)], False, BEND, linetype='CENTER', color=1, ltscale=0.5)
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny)], False, BEND, linetype='CENTER', color=5)
        self.poly([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny)], False, BEND, linetype='CENTER', color=5)
        return self

    def text(self, x, y, s, h=5, layer='0', color=1):
        self.ents.append(('TEXT', ((x, y), s, h), dict(layer=layer, color=color, style='Z-English')))
        return self

    # ---- 变换 ----
    def _map(self, f, mirror=False):
        p = Piece(self.name)
        for kind, data, attr in self.ents:
            if kind == 'LWPOLYLINE':
                pts, closed = data
                npts = [f(x, y) + ((-b if mirror else b),) for x, y, b in pts]
                p.ents.append((kind, (npts, closed), attr))
            elif kind == 'CIRCLE':
                (cx, cy), r = data
                p.ents.append((kind, (f(cx, cy), r), attr))
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
                p.ents.append((kind, (c2, r, n0, n1), attr))
            elif kind == 'TEXT':
                (x, y), s, h = data
                p.ents.append((kind, (f(x, y), s, h), attr))
        return p

    def moved(self, dx, dy):
        return self._map(lambda x, y: (x + dx, y + dy))

    def rotated(self, deg):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        return self._map(lambda x, y: (x * c - y * s, x * s + y * c))

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


def extract(path, region, layers=(CUT,), drop=None):
    """从图纸 DXF 的某个视图区域提取可见轮廓线/孔，返回以区域左下角为原点的 Piece。
    drop(kind, info) 返回 True 的图元会被丢弃。"""
    doc = ezdxf.readfile(path)
    x0, y0, x1, y1 = region
    p = Piece()
    eps = 0.05
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
