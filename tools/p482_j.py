# -*- coding: utf-8 -*-
"""NO.482 钣金2（客户 11-12 增补单）：K95.2 L2951.2 直段件 4 件，SUS304。

和 K82.5 系同截面，直接套 p482_f 的三个族（外形、孔、缺口全部从图纸矢量读，族函数里逐个核对）：
- 1610601A / 1610602A 机身板 2.5mm（主视图高 169 / 150 + 翼边 25，BD4）
- 1610611A 防护罩 1.5mm（前腿 20 + 腹板 60 + 后腿 42，Φ51 缺口 31 个，起点 47.6、节距 95.2）
- 1610612A 保护罩下 1.5mm（L 2945.2，上腿 25 ~ 2922.2；Φ51 / Φ9 缺口 44.6 + 30×95.2；开槽 1182.5 ~ 1334.5，高 30）
"""
import p482_f as F

BODY = [('1610601A-K95.2-L2951.2', 2951.2), ('1610602A-K95.2-L2951.2', 2951.2)]
GUARD = [('1610611A-K95.2-L2951.2', 2951.2)]
_S952 = F.seq(44.6, (95.2, 30))
LOWER = [('1610612A-K95.2-L2951.2', 2945.2, 25, 2922.2, _S952, _S952, (1182.5, 1334.5))]


def register(C):
    for code, L in BODY:
        C.PARTS[code] = F._make(F.body, C, code, L)
    for code, L in GUARD:
        C.PARTS[code] = F._make(F.guard, C, code, L)
    for code, L, a, b, big, small, slot in LOWER:
        C.PARTS[code] = F._make(F.lower, C, code, L, a, b, big, small, slot)
