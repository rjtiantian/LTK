# -*- coding: utf-8 -*-
"""NO.482 第 e 批支撑腿方管 STEP（1610108A00 / 1610323A00 / 1610330A00 / 1610335A00）。
用法（需 OCP）: python 482/管材STEP/make_tubes_e.py
坐标：管长沿 z（底端 z=0），x 沿 40 边，y 沿 60 边；45° 斜切在顶端，x=40 一侧最长（=L），x=0 一侧 L−40。
圆角按材料规则（SUS304 外 R = 1.2t、内 R = 外 R − t），图纸 / 明细栏上的 R 不用。
孔取总图矢量：323/330/335 为 2-Φ9（距管底 28、55，x=20，贯穿两块 40 宽壁，图注 4-Φ9/2-Φ9 通孔）；
108 总图上 2 个 M8 小径 Φ6.647（距管底 390，y=20、40，贯穿两块 60 宽壁，图上无标注，见 notes_e 需复核）。
横撑 40x40x2 斜 45° 摆放、平头顶在立柱 60 宽壁内侧，没有贴外侧的管壁，定位舌 / 缺口不适用，未加。
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from frame3d import tube, keep, cut, cyl, volume, bbox, valid, write_assembly

RHO = 7.93e-6


def mitre_tube(t, L, holes_y=(), holes_x=()):
    s = tube('z', (0, 0, 0), (40, 60, L), t)
    s = keep(s, (40, 0, L), (1, 0, -1))
    for x, z, d in holes_y:           # 沿 y 贯穿（穿 40 宽壁）
        s = cut(s, cyl('y', (x, 0, z), d, -1, 61))
    for y, z, d in holes_x:           # 沿 x 贯穿（穿 60 宽壁）
        s = cut(s, cyl('x', (0, y, z), d, -1, 41))
    return s


def bar(L):
    return tube('z', (0, 0, 0), (40, 40, L), 2)


P9 = [(20, 28, 9), (20, 55, 9)]
M8 = [(20, 390, 6.647), (40, 390, 6.647)]
JOBS = [
    ('1610108A00', '方管40x60x3-L%d-45', 951, 6, mitre_tube(3, 951, holes_x=M8), 4.11),
    ('1610108A00', '方管40x60x2-L%d-45', 951, 6, mitre_tube(2, 951, holes_x=M8), 2.79),
    ('1610108A00', '方管40x40x2-L%d', 526, 6, bar(526), 1.26),
    ('1610323A00', '方管40x60x3-L%d-45', 323, 9, mitre_tube(3, 323, holes_y=P9), 1.34),
    ('1610323A00', '方管40x60x2-L%d-45', 323, 9, mitre_tube(2, 323, holes_y=P9), 0.91),
    ('1610323A00', '方管40x40x2-L%d', 376, 9, bar(376), 0.88),
    ('1610330A00', '方管40x60x3-L%d-45', 323, 2, mitre_tube(3, 323, holes_y=P9), 1.34),
    ('1610330A00', '方管40x60x2-L%d-45', 323, 2, mitre_tube(2, 323, holes_y=P9), 0.91),
    ('1610330A00', '方管40x40x2-L%d', 511, 2, bar(511), 1.20),
    ('1610335A00', '方管40x60x2-L%d-45', 323, 2, mitre_tube(2, 323, holes_y=P9), 0.91),
]
for code, spec, L, n, s, bom in JOBS:
    name = '%s-支撑腿-%s-%d件' % (code, spec % L, n)
    assert valid(s), name
    write_assembly([(name, s)], os.path.join(HERE, name + '.step'), name)
    print('%-44s bbox %s  算重 %.3f kg（×1.017=%.3f）明细栏 %.2f' % (name, bbox(s), volume(s) * RHO, volume(s) * RHO * 1.0172, bom))
