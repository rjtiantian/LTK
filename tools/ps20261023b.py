# -*- coding: utf-8 -*-
"""单件（2026-10-23 第二批，NO.451 直发广州太古）：1574129B、1574181A 线槽支撑，SUS304 3mm 表面拉丝。

与 1574136A 同一画法（ps20261022 之前的 ps20261020）：U 形，宽 20，BD 5，两立边自由端角 R2，
顶面 2-M6（宽向居中），两立边各 1-M6 距底 11（两立边隐藏线均有）。几何取 DWG 矢量。
"""


def register(C):
    def u_support(legs, web, holes):
        t = 3; w = C.bd(t)
        L = legs + web + legs - 2 * w
        r1, r2 = legs - w / 2, L - legs + w / 2
        p = C.Piece().rect(0, 0, L, 20, 2)
        p.tap(11, 10, 'M6').tap(L - 11, 10, 'M6')
        for s in holes:                                       # 距左立边外表面 s
            p.tap(r1 + s - w / 2, 10, 'M6')
        p.bend(r1, 0, r1, 20, w).bend(r2, 0, r2, 20, w)
        return p

    # 立边 50 + 顶 98（外形）→ 展开 188 × 20；顶面 M6 距左外表面 24 / 74
    C.part('1574129B')(lambda q: [(C.lab(3, q), u_support(50, 98, (24, 74)))])
    # 立边 60 + 顶 147（外形）→ 展开 257 × 20；顶面 M6 距左外表面 28.5 / 118.5
    C.part('1574181A')(lambda q: [(C.lab(3, q), u_support(60, 147, (28.5, 118.5)))])
