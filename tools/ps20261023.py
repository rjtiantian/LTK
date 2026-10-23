# -*- coding: utf-8 -*-
"""单件（2026-10-23）：L板1、L板2（STEP，Q235B 4mm）、yuan da hu ke 01（SLDPRT → 1.5 上 SolidWorks 转 STEP，SUS304 1.5mm）。

展开到 单件/2026-10-23/JSON/：L板 用 tools/step_unfold.py（BD 6.8），yuan da hu ke 01 为四面折弯护壳，
用 tools/step_unfold2.py（任意方向折弯树，BD 2.3）。
"""
import json, os, math


def register(C):
    def flat(name, t, mat):
        path = os.path.join(os.path.dirname(C.dxf_dir), 'JSON', name + '.json')
        if not os.path.exists(path):
            return None
        J = json.load(open(path, encoding='utf-8'))
        p = C.Piece()
        for lp in J['loops']:
            if len(lp) == 2 and all(abs(abs(q[2]) - 1) < 1e-6 for q in lp):
                p.circle((lp[0][0] + lp[1][0]) / 2, (lp[0][1] + lp[1][1]) / 2, math.dist(lp[0][:2], lp[1][:2]))
            else:
                p.poly([tuple(q) for q in lp], True)
        for x, y, d in J['circles']:
            p.circle(x, y, d)
        for u, s0, s1, deg in J.get('bends', []):              # step_unfold.py：平行折弯
            p.bend(s0, u, s1, u, J['bd'], red_only=abs(deg - 90) > 0.5)
        for a, b, deg in J.get('bend_lines', []):              # step_unfold2.py：任意方向折弯
            p.bend(a[0], a[1], b[0], b[1], J['bd'], red_only=abs(deg - 90) > 0.5)
        return p

    for code in ('L板1', 'L板2'):
        C.part(code)(lambda q, code=code: [(C.lab(4, q, 'Q235B'), flat(code, 4, 'Q235B'))])

    # yuan da hu ke 01：SUS304，SLDPRT 转 STEP 后展开（JSON 存在即出图，否则占位）
    def yuan(q):
        p = flat('yuan da hu ke 01', None, 'SUS304')
        if p is None:
            return ('TODO', [C.lab(0, q)], '待 SLDPRT 转 STEP 后展开')
        J = json.load(open(os.path.join(os.path.dirname(C.dxf_dir), 'JSON', 'yuan da hu ke 01.json'), encoding='utf-8'))
        return [(C.lab(J['t'], q), p)]
    C.part('yuan da hu ke 01')(yuan)
