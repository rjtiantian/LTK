# -*- coding: utf-8 -*-
"""单件（2026-10-20 第二批）：fb12、fb123（STEP 模型）、Z板2（上海炬欣 DWG），均 SUS304 3mm。

fb12 / fb123：帽形件——顶板 100 宽（两长边 90° V 形缺口）+ 两侧下折立板 93 + 外翻底脚（各一条 9 宽腰孔），
模型内 R0.74；展开轮廓由 tools/step_hat_flat.py 从 STEP 提取到 单件/2026-10-20-fb/<名>.json（按 BD 5 外形尺寸法）。
"""
import json, os
from ps20261020 import _outline


def register(C):
    def hat(name, q):
        J = json.load(open(os.path.join(os.path.dirname(C.dxf_dir), name + '.json'), encoding='utf-8'))
        p = C.Piece().poly([(u, z, 0) for u, z in J['outline']], True)
        for u0, z0, u1, z1, w in J['slots']:
            p.slot(u0, z0, u1, z1, w)
        for u, z, d in J['circles']:
            p.circle(u, z, d)
        z0, z1 = J['width']
        for u in J['bends']:
            p.bend(u, z0, u, z1, J['bd'])
        return [(C.lab(J['t'], q), p)]

    C.part('fb12')(lambda q: hat('fb12', q))
    C.part('fb123')(lambda q: hat('fb123', q))

    # Z板2 3mm（图纸 1:2，块内几何为标注值一半）：上折边 35 + 腹板 110 + 下折边 35（Z 形，外形 70 × 110），宽 40。
    # 外形尺寸法：上折边外形 35 + 3 = 38，腹板 110，下折边 35，BD 5 → 展开 173 × 40；
    # 两折边端部各一条开口 U 槽（R4.1，槽底圆心距端 15），端部两角 R3。
    @C.part('Z板2')
    def _(q):
        t = 3; w = C.bd(t)
        r1 = 38 - w / 2; r2 = r1 + 110 - w; L = r2 + 35 - w / 2
        p = C.Piece()
        _outline(p, [(0, 0, 3), (L, 0, 3), (L, 20 - 4.1), (L - 15, 20 - 4.1, 4.1), (L - 15, 20 + 4.1, 4.1),
                   (L, 20 + 4.1), (L, 40, 3), (0, 40, 3), (0, 20 + 4.1), (15, 20 + 4.1, 4.1), (15, 20 - 4.1, 4.1),
                   (0, 20 - 4.1)])
        p.bend(r1, 0, r1, 40, w).bend(r2, 0, r2, 40, w)
        return [(C.lab(t, q), p)]
