# -*- coding: utf-8 -*-
"""单件（2026-10-20）南方2750钣金（上海炬欣）：横撑1、侧板11、扭力臂、zhi jia 01-1，均 SUS304 拉丝。

几何取 STEP（SolidWorks 2017）：折弯件由 tools/step_unfold.py 展开（BD 外形尺寸法），平板件取模型面轮廓，
结果存于 单件/2026-10-20-南方2750/JSON/。件数、螺纹规格、方管规格取同名 DWG（文字为 CP932 编码，已译出）。
螺纹孔按下料规则开小径：M8 → Φ6.65（模型为 Φ6.8 底孔）、M6 → Φ4.92（模型为 Φ5）。
方管另按客户样例方式出 STEP（单件/2026-10-20-南方2750/管材STEP/，make_tubes.py），下料图里只写长度与截面。
"""
import json, os, math


def register(C):
    def flat(name, t, remap=None, mirror=False):
        J = json.load(open(os.path.join(os.path.dirname(C.dxf_dir), 'JSON', name + '.json'), encoding='utf-8'))
        p = C.Piece()
        for lp in J['loops']:
            if len(lp) == 2 and all(abs(abs(q[2]) - 1) < 1e-6 for q in lp):        # 两段半圆 = 圆孔
                d = math.dist(lp[0][:2], lp[1][:2])
                d = (remap or {}).get(round(d, 3), d)
                p.circle((lp[0][0] + lp[1][0]) / 2, (lp[0][1] + lp[1][1]) / 2, d)
            else:
                p.poly([tuple(q) for q in lp], True)
        for x, y, d in J['circles']:
            p.circle(x, y, (remap or {}).get(round(d, 3), d))
        for u, s0, s1, deg in J['bends']:
            p.bend(s0, u, s1, u, J['bd'], red_only=abs(deg - 90) > 0.5)
        return p.mirrored() if mirror else p

    # 横撑1 ×8：2040 方管（40×20，壁厚 2）长 398 + 两端 3mm 端板 70×20（R3，2-M6）。
    # 方管两个 40 宽面贯穿 3 条 9×49 腰孔（中心距 0 / ±120），需管材激光或另行加工，不在板料下料图
    @C.part('横撑1')
    def _(q):
        return [(C.lab(398, q), C.tube_rect(40, 20, 2)),
                (C.lab(3, 2 * q), flat('横撑1_端板', 3, {5.0: C.TAP['M6']}))]

    # 侧板11 ×4（左右各 2）：3mm C 形，腹板 122 + 下翻边 40（通长 2750）+ 上翻边 20（中段 2550），BD 5 → 2750 × 172。
    # 左右件为镜像：两件按原样、两件镜像下料，保证拉丝面朝外。Φ6.8 按 M8 开 Φ6.65（图纸 16-M8，模型有 17 个 Φ6.8）
    @C.part('侧板11')
    def _(q):
        rm = {6.8: C.TAP['M8']}
        return [(C.lab(3, q // 2), flat('侧板11', 3, rm)), (C.lab(3, q - q // 2), flat('侧板11', 3, rm, mirror=True))]

    # 扭力臂 ×2：5mm Z 形——上板 R55 圆盘（Φ45 中孔、12-Φ7 均布）+ 立板 + 下板（9×19 腰孔），BD 8.4
    @C.part('扭力臂')
    def _(q):
        return [(C.lab(5, q), flat('扭力臂', 5))]

    # zhi jia 01-1 ×4：焊接支架——4040 方管（壁厚 2）立柱 630 ×2、横撑 330 ×1；
    # 4mm 底板 40×40（Φ17，内焊 M16 螺母）×2；4mm 顶板 80×40（R3，2-Φ9）×2
    @C.part('zhi jia 01-1')
    def _(q):
        return [(C.lab(630, 2 * q), C.tube_rect(40, 40, 2)), (C.lab(330, q), C.tube_rect(40, 40, 2)),
                (C.lab(4, 2 * q), flat('zhijia_s3', 4)), (C.lab(4, 2 * q), flat('zhijia_s5', 4))]
