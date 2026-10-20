# -*- coding: utf-8 -*-
"""南方2750 管材 STEP（交管材激光），按客户样例 支架1.STEP 的方式建模（见 tools/tube_step.py）。

用法（需 OCP）:  python3 单件/2026-10-20-南方2750/make_tubes.py   → 单件/2026-10-20-南方2750/管材STEP/*.step
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from tube_step import tube, box, slot_y, cut, fuse, volume, write, TAB_W, TAB_L, CLR

OUT = os.path.join(HERE, '管材STEP')
os.makedirs(OUT, exist_ok=True)
t = 2.0

# 横撑1：2040 方管 40（x）× 20（y）× 2，长 398；两 40 宽面（y 向）贯穿 3 条 9×49 腰孔，腰孔中心 z = L/2 + 0 / ±120
L = 398.0
s = tube(40, 20, t, L)
for zc in (-120, 0, 120):
    s = cut(s, slot_y(20, L / 2 + zc - 20, L / 2 + zc + 20, 9, -1, 21))
write(s, os.path.join(OUT, '横撑1-方管40x20x2-L398-8件.step'), '横撑1 方管40x20x2 L398')
print('横撑1 管 体积 %.0f' % volume(s))

# zhi jia 01-1：4040×2。立柱 L630（截面 x 0~40、z 方向为 40），横撑 L330 插在两立柱之间（立柱间净距 330）。
# 横撑在 x=0 一侧管壁两端各伸出定位舌 13 × 3.5（舌中心在横撑高度中线）；立柱在对应管角开 13.5 × 3.75 缺口。
# 立柱局部坐标：管长沿 z（= 原模型 y），截面 x 0~40、y 0~40（y = 原模型 z，横撑贴 y=40 面）；
# 横撑中心距立柱底 60（原模型 y 40~80）。
Lp, Lc = 630.0, 330.0
post = tube(40, 40, t, Lp)
zc = 60.0                                    # 横撑中心高度
w = TAB_W + 2 * CLR; d = TAB_L + CLR
post = cut(post, box(-1, 40 - d, zc - w / 2, 3.45, 41, zc + w / 2))   # 管角缺口：x 0~3.45、y 36.25~40
write(post, os.path.join(OUT, 'zhi jia 01-1-立柱-方管40x40x2-L630-8件.step'), 'zhi jia 01-1 立柱 方管40x40x2 L630')
print('立柱 体积 %.0f' % volume(post))

bar = tube(40, 40, t, Lc)
for z0, z1 in ((-TAB_L, 0), (Lc, Lc + TAB_L)):
    bar = fuse(bar, box(0, 20 - TAB_W / 2, z0, t, 20 + TAB_W / 2, z1))   # x=0 侧管壁伸出定位舌
write(bar, os.path.join(OUT, 'zhi jia 01-1-横撑-方管40x40x2-L330-4件.step'), 'zhi jia 01-1 横撑 方管40x40x2 L330')
print('横撑 体积 %.0f' % volume(bar))
