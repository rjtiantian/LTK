# -*- coding: utf-8 -*-
"""切割轮廓质量检查函数：重复线 dups、未闭合端点 ends、重复圆弧 arcs_dup"""
import math, collections
from sheetlib import CUT


def segs(p):
    out = []
    for k, d, a in p.ents:
        if a.get('layer') != CUT:
            continue
        if k == 'LINE':
            out.append((d[0], d[1]))
        elif k == 'LWPOLYLINE':
            pts, closed = d
            n = len(pts)
            for i in range(n if closed else n - 1):
                x0, y0, b = pts[i]; x1, y1, _ = pts[(i + 1) % n]
                if abs(b) < 1e-9:
                    out.append(((x0, y0), (x1, y1)))
    return out


def ends(p):
    pts = []
    for k, d, a in p.ents:
        if a.get('layer') != CUT:
            continue
        if k == 'LINE':
            pts += [d[0], d[1]]
        elif k == 'ARC':
            (cx, cy), r, a0, a1 = d
            pts += [(cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))),
                    (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))]
        elif k == 'LWPOLYLINE' and not d[1]:
            pts += [d[0][0][:2], d[0][-1][:2]]
    c = collections.Counter((round(x, 1), round(y, 1)) for x, y in pts)
    loose = []
    for (x, y), n in c.items():
        if n % 2 == 1:
            # 允许 0.15 内的邻点
            near = sum(m for (x2, y2), m in c.items() if (x2, y2) != (x, y) and abs(x2 - x) <= 0.15 and abs(y2 - y) <= 0.15)
            if (n + near) % 2 == 1:
                loose.append((x, y))
    return loose


def dups(p, dmax=1.5):
    S = [s for s in segs(p) if math.dist(*s) > 0.5]
    res = []
    for i in range(len(S)):
        (a, b) = S[i]
        ux, uy = b[0] - a[0], b[1] - a[1]; L = math.hypot(ux, uy); ux /= L; uy /= L
        for j in range(i + 1, len(S)):
            (c, d) = S[j]
            vx, vy = d[0] - c[0], d[1] - c[1]; M = math.hypot(vx, vy)
            if abs(ux * vy - uy * vx) / M > 0.01:
                continue
            off = abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux)
            if not (0.05 < off < dmax):
                continue
            t0 = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy
            t1 = (d[0] - a[0]) * ux + (d[1] - a[1]) * uy
            ov = min(L, max(t0, t1)) - max(0, min(t0, t1))
            if ov > 1.0:
                res.append((round(off, 2), round(ov, 1), tuple(round(v, 1) for v in a), tuple(round(v, 1) for v in b)))
    return res


def arcs_dup(p):
    A = []
    for k, d, a in p.ents:
        if a.get('layer') != CUT:
            continue
        if k == 'ARC':
            A.append(('A', d[0], d[1]))
        elif k == 'CIRCLE':
            A.append(('C', d[0], d[1]))
        elif k == 'LWPOLYLINE':
            pts, closed = d
            n = len(pts)
            for i in range(n if closed else n - 1):
                x0, y0, b = pts[i]; x1, y1, _ = pts[(i + 1) % n]
                if abs(b) > 1e-9:
                    th = 4 * math.atan(b); ch = math.hypot(x1 - x0, y1 - y0)
                    r = ch / (2 * abs(math.sin(th / 2)))
                    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                    h = math.sqrt(max(r * r - (ch / 2) ** 2, 0)) * (1 if (abs(th) < math.pi) == (b > 0) else -1)
                    nx, ny = -(y1 - y0) / ch, (x1 - x0) / ch
                    A.append(('P', (mx + nx * h, my + ny * h), r))
    res = []
    for i in range(len(A)):
        for j in range(i + 1, len(A)):
            (k1, c1, r1), (k2, c2, r2) = A[i], A[j]
            dc = math.dist(c1, c2)
            if 'C' in (k1 + k2) and k1 == k2 == 'C':
                continue
            if (dc < 0.05 and 0.05 < abs(r1 - r2) < 1.5 and min(r1, r2) > 1) or (0.05 < dc < 1.2 and abs(r1 - r2) < 0.05):
                res.append((k1, tuple(round(v, 1) for v in c1), round(r1, 2), k2, tuple(round(v, 1) for v in c2), round(r2, 2)))
    return res
