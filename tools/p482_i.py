# -*- coding: utf-8 -*-
"""NO.482 客户 11-12 更改（张泉泉 11-11 18:34 / 18:46 微信，「有个护板错了」「电机护罩那个支架」）。

电机安装板四件换 B 版 STEP（482/STEP/），板 + 两块加强筋：
  1610305B00（板 1610305B01 + 筋 1610305B02 / 1610305A04）
  1610341B00（板 1610341A01 + 筋 1610305B02 ×2）
  1610342B00（板 1610604B01 + 筋 1610305A04 ×2）
  1610604B00（板 1610604A01 + 筋 1610305B02 ×2）
加强筋从 Z 形折弯件（展开 195、2-Φ9）改成 143×117 平板（带三角减重孔），四件的筋完全一样（B02 / A04 同形，左右对放）。
板：腹板 175 → 149，下翼 120 改成通长、两端各 2-Φ9，上翼两端各加 1-Φ9；305 下翼中间开梯形缺口。
展开：tools/step_split.py（BD 5）→ 482/JSON/<号>-板.json / -筋.json。

1610512A-K82.5-L1485-开槽：在 p482_f.LOWER 表里（开槽 257~409，深 30）。
"""
import json, os, math


def register(C):
    def flat(name):
        path = os.path.join(os.path.dirname(C.dxf_dir), 'JSON', name + '.json')
        J = json.load(open(path, encoding='utf-8'))
        p = C.Piece()
        for lp in J['loops']:
            if len(lp) == 2 and all(abs(abs(q[2]) - 1) < 1e-6 for q in lp):
                p.circle((lp[0][0] + lp[1][0]) / 2, (lp[0][1] + lp[1][1]) / 2, math.dist(lp[0][:2], lp[1][:2]))
            else:
                p.poly([tuple(q) for q in lp], True)
        for x, y, d in J['circles']:
            p.circle(x, y, d)
        for u, s0, s1, deg in J.get('bends', []):
            p.bend(s0, u, s1, u, J['bd'], red_only=abs(deg - 90) > 0.5)
        return p, J['t']

    for code in ('1610305B00', '1610341B00', '1610342B00', '1610604B00'):
        def make(q, code=code):
            plate, t = flat(code + '-板')
            rib, t2 = flat(code + '-筋')
            return [(C.lab(t, q), plate), (C.lab(t2, 2 * q), rib)]   # 筋平板，两块同形左右翻面用
        C.part(code)(make)
        C.iso(code, os.path.join(os.path.dirname(C.dxf_dir), 'STEP', code + '.stp'))   # 焊接件（板 + 筋）：轴测图取整件 STEP
