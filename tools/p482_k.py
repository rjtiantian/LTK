# -*- coding: utf-8 -*-
"""NO.482 11-19 异常单（AAF-0000432，称重忘放，需改设计）：4 件 L1485 直段件在原件上截成 L660，每样 1 件。

  1610515A-K82.5-L660  ← 1610501A-K82.5-L1485 机身板 A（169）：右段 825 切掉，距左端 645 新加 2 个腰孔
  1610516A-K82.5-L660  ← 1610502A-K82.5-L1485 机身板 A（150）：同上
  1610517A-K82.5-L660  ← 1610512A-K82.5-L1485 保护罩下（原图那件，不是「开槽」件）：右段 825 切掉，
                          上腿在 631~654 再切掉 23（腹板让位 7、根部 R4，上腿端角 R5）
  1610518A-K82.5-L660  ← 1610511A-K82.5-L1485 防护罩：右段 825 切掉

新图仍画着整条 1485 的视图，红框「方框内全部切除」是要切的段。做法：
- 机身板 / 防护罩：用 p482_f 的 body() / guard() 读新图（新加的腰孔一起读进来），再在 x = 视图宽 − 825 处截断。
  截断端照新图是直切（没有端角圆角）。截线若正好穿过孔（机身板翼边 Φ9 在 x=660），端面上留半圆缺口。
- 保护罩下：截断端（上腿让位、腹板让位、圆角）全部从新图主视图 / 俯视图矢量读，外形照 p482_f.lower() 的走法重画。
"""
import math
import p482_f as F
from p482_f import Path, K90, EPS, sheet, edge_pts, add_forward, split_tail, seq
from sheetlib import Piece

CUT825 = 825.0          # 右段切除长度（四张图都是标注 825）


def _cut_x(S, L):
    """红框 / 825 标注：截断位置 = 视图宽 − 825"""
    return L - CUT825


def _clip(p, Lc, notch_y=()):
    """把展开件在 x = Lc 处截断，只留左边。外形与截线只能交在直线段上；
    notch_y：截线正好穿过的孔 (y, d)，在端面上留半圆缺口。"""
    q = Piece()
    for k, d, a in p.ents:
        if k == 'LWPOLYLINE' and d[1] and a.get('layer') == F.CUT and max(v[0] for v in d[0]) > Lc + EPS \
                and min(v[0] for v in d[0]) < Lc - EPS and len(d[0]) > 4:
            vs, out = d[0], []
            n = len(vs)
            for i in range(n):
                x0, y0, b0 = vs[i]
                x1, y1, _ = vs[(i + 1) % n]
                if x0 <= Lc + 1e-9:
                    out.append([x0, y0, b0])
                if (x0 - Lc) * (x1 - Lc) < 0:
                    if abs(b0) > 1e-9:
                        raise ValueError('截线压在圆弧上 (%s,%s)-(%s,%s)' % (x0, y0, x1, y1))
                    yc = y0 + (y1 - y0) * (Lc - x0) / (x1 - x0)
                    out.append([Lc, yc, 0.0])
            # 端面（两个截点之间，沿 +y 走）插半圆缺口
            i = next(j for j in range(len(out)) if abs(out[j][0] - Lc) < 1e-9 and abs(out[(j + 1) % len(out)][0] - Lc) < 1e-9)
            ya, yb = out[i][1], out[(i + 1) % len(out)][1]
            if ya > yb:
                raise ValueError('端面方向不对')
            ins = []
            for y, dd in sorted(notch_y):
                if not (ya < y - dd / 2 and y + dd / 2 < yb):
                    raise ValueError('缺口不在端面上')
                ins += [[Lc, y - dd / 2, -1.0], [Lc, y + dd / 2, 0.0]]
            out[i + 1:i + 1] = ins
            q.ents.append((k, ([tuple(v) for v in out], True), a))
        elif k == 'LWPOLYLINE' and not d[1]:            # 折弯线：截到 Lc
            (xa, ya, _), (xb, yb, _) = d[0][0], d[0][1]
            if min(xa, xb) >= Lc - EPS:
                continue
            if max(xa, xb) > Lc:
                if abs(ya - yb) > 1e-9:
                    raise ValueError('斜折弯线过截线')
                xa, xb = min(xa, xb), Lc
            q.ents.append((k, ([(xa, ya, 0.0), (xb, yb, 0.0)], False), a))
        elif k == 'LWPOLYLINE':                         # 腰孔
            xs = [v[0] for v in d[0]]
            if max(xs) <= Lc - EPS:
                q.ents.append((k, d, a))
            elif min(xs) < Lc:
                raise ValueError('截线穿过腰孔 %s' % xs)
        elif k == 'CIRCLE':
            (cx, cy), r = d
            if cx + r <= Lc - EPS:
                q.ents.append((k, d, a))
            elif cx - r < Lc:
                if abs(cx - Lc) > 0.01 or not any(abs(cy - y) < 1e-6 for y, _ in notch_y):
                    raise ValueError('截线穿过孔 (%s,%s)' % (cx, cy))
        else:
            q.ents.append((k, d, a))
    return q


def body_cut(C, code, L):
    S = sheet(C, code)
    Lc = _cut_x(S, L)
    p = F.body(C, code, L)[0][1]
    hits = [(cy, 2 * r) for k, d, a in p.ents if k == 'CIRCLE' for (cx, cy), r in [d] if abs(cx - Lc) < 0.01]
    return [(C.lab(2.5, 1), _clip(p, Lc, hits))]


def guard_cut(C, code, L):
    S = sheet(C, code)
    Lc = _cut_x(S, L)
    p = F.guard(C, code, L)[0][1]
    return [(C.lab(1.5, 1), _clip(p, Lc))]


def lower_cut(C, code, L, a, b0, big, small):
    """保护罩下截短：整条按 lower() 先核一遍（图上原有特征没变），截断端从新图读"""
    F.lower(C, code, L, a, b0, big, small, None)       # 核对：左端、缺口序列、腹板让位都和原图一致
    t, w = 1.5, C.bd(1.5)
    S = sheet(C, code)
    Lc = _cut_x(S, L)
    main = [v for v in S.views if abs(v[3] - v[1] - 58) < 0.1 and abs(v[2] - v[0] - L) < 0.1]
    web = [v for v in S.views if abs(v[3] - v[1] - 56) < 0.1 and abs(v[2] - v[0] - L) < 0.1]
    if len(main) != 1 or len(web) != 1:
        raise ValueError('%s 视图' % code)
    main, web = main[0], web[0]
    x0, y0, y1 = main[0], main[1], main[3]
    # 上腿新端头：主视图上腿高度内、Lc 左边 50 以内的竖线（不在截线上的那条）
    ups = [l[0] - x0 for l in S.lines_in(main) if abs(l[0] - l[2]) < 1e-3 and min(l[1], l[3]) >= y0 + 42 - EPS and min(l[1], l[3]) < y0 + 46
           and Lc - 50 < l[0] - x0 < Lc - EPS]
    if len(set(round(u, 3) for u in ups)) != 1:
        raise ValueError('%s 上腿新端头 %s' % (code, ups))
    b = ups[0]
    # 上腿端角：圆心 (b − r, y1 − r)
    rcs = [q[2] for q in S.arcs_in(main) if abs(q[0] - x0 - (b - q[2])) < EPS and abs(q[1] - (y1 - q[2])) < EPS]
    if len(rcs) != 1:
        raise ValueError('%s 上腿端角 %s' % (code, rcs))
    rb = rcs[0]
    # 腹板让位：俯视图 Lc 处竖线下端到视图顶的距离，水平线回到 b + rr
    wtop = web[3]
    wl = S.lines_in(web)
    hz = [l for l in wl if abs(l[1] - l[3]) < 1e-3 and wtop - l[1] > 3 and abs(max(l[0], l[2]) - x0 - Lc) < 0.1 and min(l[0], l[2]) - x0 > b]
    if len(hz) != 1:
        raise ValueError('%s 腹板让位线 %s' % (code, hz))
    rel = wtop - hz[0][1]
    rr = min(hz[0][0], hz[0][2]) - x0 - b
    if abs(rel - 7) > EPS or abs(rr - 4) > EPS:
        raise ValueError('%s 腹板让位 %s / R%s' % (code, rel, rr))

    y_1 = 42 - w / 2
    y_2 = y_1 + 56 - w
    top = y_2 + 17.5 - w / 2
    ye = y_2 - (rel - w / 2)
    yc = ye + rr
    # 下腿端角半径（左端，同 lower()）
    rc = 5.0
    big_in = [c for c in big if c < Lc]
    small_in = [c for c in small if c < b]
    big_in, tail = split_tail(code, big_in, Lc, 25.5, 5.0)
    if tail is not None:
        raise ValueError('%s 截断端压缺口' % code)
    p = Piece()
    path = Path(rc, 0)
    add_forward(path, edge_pts(rc, Lc, big_in, 25.5, 5.0), lambda d: d)
    path.to(Lc, ye)                                      # 截断端直切
    path.to(b + rr, ye).arc(b, yc, -K90)
    path.to(b, top - rb).arc(b - rb, top, K90)           # 上腿新端角 R5（新图）
    for c in sorted(small_in, reverse=True):
        if c - 6.5 < a + 4:
            raise ValueError('%s 左端 Φ9 压端角' % code)
        if c + 6.5 > b - rb + 1e-6:
            raise ValueError('%s Φ9 %s 压新端角' % (code, c))
        path.to(c + 6.5, top).arc(c + 4.5, top - 2, K90).to(c + 4.5, top - 4)
        path.arc(c - 4.5, top - 4, -1.0).to(c - 4.5, top - 2).arc(c - 6.5, top, K90)
    path.to(a + 4, top).arc(a, top - 4, K90)
    path.to(a, yc).arc(a - rr, ye, -K90)
    path.to(rr, ye).arc(0, ye - rr, K90).to(0, rc).arc(rc, 0, K90)
    path.into(p)
    p.bend(0, y_1, Lc, y_1, w)
    p.bend(a, y_2, b, y_2, w)
    # 核对新图主视图上 Φ9 开口：c ± 4.5 在 b 左边的都画了
    vis = sorted({round(q[0] - x0, 2) for q in S.arcs_in(main) if abs(q[2] - 4.5) < 0.01})
    if [round(c, 2) for c in small_in] != [v for v in vis if v < b]:
        raise ValueError('%s Φ9 序列 %s vs %s' % (code, small_in, vis))
    return [(C.lab(t, 1), p)]


S825 = lambda n: seq(38.25, (82.5, n))


def register(C):
    C.PARTS['1610515A-K82.5-L660'] = F._make(body_cut, C, '1610515A-K82.5-L660', 1485)
    C.PARTS['1610516A-K82.5-L660'] = F._make(body_cut, C, '1610516A-K82.5-L660', 1485)
    C.PARTS['1610517A-K82.5-L660'] = F._make(lower_cut, C, '1610517A-K82.5-L660', 1479, 25, 1456, S825(17), S825(17))
    C.PARTS['1610518A-K82.5-L660'] = F._make(guard_cut, C, '1610518A-K82.5-L660', 1485)
