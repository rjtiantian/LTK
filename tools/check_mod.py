# -*- coding: utf-8 -*-
"""单模块自检（多批并行时互不影响）：只加载一个零件模块，逐件报外形、净面积、算重 vs 图纸重量、孔径统计、折弯数、QA。
用法: python3 tools/check_mod.py <订单> <模块名> [物料号,物料号] [输出.png]
"""
import os, sys, re, glob, math, importlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orderctx import Ctx
from layout import ROOT
from sheetlib import CUT, BEND
from qalib import dups, ends, arcs_dup

RHO = {'SUS': 7.93, 'Q23': 7.85, 'AL': 2.70}


def _arc_pts(cx, cy, r, a0, a1):
    a0, a1 = math.radians(a0), math.radians(a1)
    if a1 <= a0:
        a1 += 2 * math.pi
    n = max(4, int((a1 - a0) / 0.05))
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _bulge_pts(p0, p1, b):
    if abs(b) < 1e-9:
        return [p0, p1]
    ang = 4 * math.atan(b); dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy)
    if L < 1e-9:
        return [p0, p1]
    r = L / (2 * math.sin(ang / 2)); h = r * math.cos(ang / 2)
    cx, cy = (p0[0] + p1[0]) / 2 - h * dy / L, (p0[1] + p1[1]) / 2 + h * dx / L
    a0 = math.atan2(p0[1] - cy, p0[0] - cx); n = max(4, int(abs(ang) / 0.05))
    return [(cx + abs(r) * math.cos(a0 + ang * i / n), cy + abs(r) * math.sin(a0 + ang * i / n)) for i in range(n + 1)]


def _shoelace(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2


def net_area(p):
    """切割轮廓净面积 mm²：最大闭环 − 其余闭环。链不起来的开口段计入 open 返回"""
    loops, chains = [], []
    for k, d, a in p.ents:
        if a.get('layer') != CUT:
            continue
        if k == 'CIRCLE':
            (c, r) = d
            loops.append(math.pi * r * r)
        elif k == 'LINE':
            chains.append([tuple(d[0][:2]), tuple(d[1][:2])])
        elif k == 'ARC':
            (c, r, a0, a1) = d
            chains.append(_arc_pts(c[0], c[1], r, a0, a1))
        elif k == 'LWPOLYLINE':
            pts, closed = d
            out = []
            n = len(pts)
            for i in range(n if closed else n - 1):
                x0, y0, b = pts[i]; x1, y1, _ = pts[(i + 1) % n]
                out += _bulge_pts((x0, y0), (x1, y1), b)[:-1]
            if closed:
                loops.append(_shoelace(out))
            else:
                out.append(tuple(pts[-1][:2]))
                chains.append(out)
    tol = 0.2
    while chains:
        cur = chains.pop()
        grew = True
        while grew:
            grew = False
            for i, c in enumerate(chains):
                if math.dist(cur[-1], c[0]) < tol:
                    cur += c[1:]; chains.pop(i); grew = True; break
                if math.dist(cur[-1], c[-1]) < tol:
                    cur += c[::-1][1:]; chains.pop(i); grew = True; break
            if not grew and math.dist(cur[0], cur[-1]) >= tol:
                for i, c in enumerate(chains):
                    if math.dist(cur[0], c[-1]) < tol:
                        cur = c[:-1] + cur; chains.pop(i); grew = True; break
                    if math.dist(cur[0], c[0]) < tol:
                        cur = c[::-1][:-1] + cur; chains.pop(i); grew = True; break
        if math.dist(cur[0], cur[-1]) < tol:
            loops.append(_shoelace(cur))
    if not loops:
        return 0.0
    m = max(loops)
    return m - (sum(loops) - m)


def drawing_weights(dxf_dir, code):
    """同号图纸标题栏里写的重量：[(零件代号, kg)]（含组件子件）"""
    base = re.match(r'\d{7}', code)
    if not base:
        return []
    out = []
    from drawing_info import info
    for f in sorted(glob.glob(os.path.join(dxf_dir, base.group() + '*.dxf'))):
        try:
            a, _ = info(f)
        except Exception:
            continue
        w = next((v for k, v in a.items() if k.startswith('质量')), '')
        m = re.search(r'([\d.]+)\s*kg', w)
        if m and a.get('零件代号'):
            out.append((a['零件代号'], float(m.group(1))))
    return out


def report(C, codes):
    for code in codes:
        try:
            res = C.PARTS[code](1)
        except Exception as e:
            print('ERR ', code, repr(e)); continue
        if isinstance(res, tuple):
            print('TODO', code, res[2]); continue
        tot = 0.0
        for i, (l, p) in enumerate(res):
            b = p.normalized().bbox()
            A = net_area(p)
            m = re.match(r'([A-Za-z0-9]+)-([\d.]+)mm,(\d+)件', l)
            kg = 0.0
            if m:
                t, n = float(m.group(2)), int(m.group(3))
                rho = next((v for k, v in RHO.items() if m.group(1).upper().startswith(k)), 7.9)
                kg = A * t * rho * 1e-6
                tot += kg * n
            holes = collections.Counter(round(2 * d[1], 2) for k, d, a in p.ents if k == 'CIRCLE' and a.get('layer') == CUT)
            nb = sum(1 for k, d, a in p.ents if a.get('layer') == BEND and a.get('color') == 1)
            q = (len(dups(p)), len(ends(p)), len(arcs_dup(p)))
            print('%-24s %-22s %8.2f x %-8.2f A=%-10.0f kg=%-7.3f 红线%d 孔%s %s' % (
                code if i == 0 else '', l, b[2] - b[0], b[3] - b[1], A, kg, nb, dict(sorted(holes.items())),
                '' if q == (0, 0, 0) else 'QA! dup/open/arc=%s' % (q,)))
        print('    合计算重 %.3f kg | 图纸重量 %s' % (tot, drawing_weights(C.dxf_dir, code)))


if __name__ == '__main__':
    order, mod = sys.argv[1], sys.argv[2]
    C = Ctx(os.path.join(ROOT, order, 'DXF'))
    importlib.import_module(mod).register(C)
    codes = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] != 'all' else list(C.PARTS)
    report(C, codes)
    if len(sys.argv) > 4:
        from check import render
        render(C, codes, sys.argv[4])
