# -*- coding: utf-8 -*-
"""参考 441/NO.441.dxf（人工下料图）的排版规则，生成 474/NO.474.dxf 下料图。

用法:  python3 tools/gen_474.py
排版：每个订单行一列，最下方黄色表头“日期·序号·订单·物料号·名称·数量·表面”，
其上为绿色“材料-厚度,件数”标签，标签上方为展开图（切割轮廓在“可见 (ISO)”层，
折弯线在“折弯线”层：红色中心线 + 两侧蓝线，间距 = 折弯扣除 BD）。
"""
import os, sys, math, datetime
import ezdxf, openpyxl
from ezdxf import bbox as ezbbox

sys.path.insert(0, os.path.dirname(__file__))
from sheetlib import Piece, extract, drop_concentric_outer, bd, TAP, CUT, BEND, relief_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D474 = os.path.join(ROOT, '474')
DXF = lambda n: os.path.join(D474, 'DXF', n)

MAT = 'SUS304'
# 表头“表面”取自 NO.474.xlsx 的“表面”列（由 tools/surface_474.py 按图纸材料+技术要求补填）


def lab(t, n, mat=MAT):
    t = ('%g' % t)
    return '%s-%smm,%d件' % (mat, t, n)


# ---------------------------------------------------------------- 平板件(直接取主视图)
def plate(fname, region, drop=None, keep_outline_d=None):
    p = extract(DXF(fname), region, drop=drop)
    drop_concentric_outer(p, keep_outline_d)
    return p


PARTS = {}      # code -> function(qty) -> list[(label, Piece)] 或 ('TODO', [labels], note)


def part(code):
    def deco(f):
        PARTS[code] = f
        return f
    return deco


@part('0185729A')
def _(q):
    return [(lab(6, q), plate('0185729A.idw.dxf', (88.56, 107.51, 178.56, 137.51)))]


@part('0185731A')
def _(q):
    return [(lab(6, q), plate('0185731A.idw.dxf', (16.83, 54.09, 111.83, 74.09)))]


@part('0185733A')
def _(q):
    return [(lab(6, q), plate('0185733A.idw.dxf', (20.09, 71.33, 150.09, 91.33)))]


@part('0185734A')
def _(q):
    return [(lab(2, q), plate('0185734A.idw.dxf', (139.34, 207.73, 424.17, 412.39)))]


@part('0185737A')
def _(q):
    return [(lab(6, q), plate('0185737A.idw.dxf', (35.45, 39.07, 75.45, 79.07)))]


@part('0185905A')
def _(q):
    return [(lab(5, q), plate('0185905A.idw.dxf', (184.28, 393.76, 538.28, 543.76)))]


@part('0186020A')
def _(q):
    return [(lab(4, q), plate('0186020A.idw.dxf', (74.19, 201.66, 269.12, 325.24)))]


@part('0186021A')   # 0186020A 的镜像件（见 0186020A 图纸镜像表）
def _(q):
    return [(lab(4, q), plate('0186020A.idw.dxf', (74.19, 201.66, 269.12, 325.24)).mirrored())]


@part('1431212A')
def _(q):
    return [(lab(3, q), plate('1431212A.idw.dxf', (22.11, 26.83, 52.11, 56.83), keep_outline_d=30))]


@part('1431213A')
def _(q):
    return [(lab(3, q), plate('1431213A.idw.dxf', (14.81, 16.76, 30.81, 32.76), keep_outline_d=16))]


@part('1431220A')
def _(q):
    return [(lab(4, q), plate('1431220A.idw.dxf', (74.19, 201.66, 269.12, 325.24)))]


@part('1431221A')   # 1431220A 的镜像件
def _(q):
    return [(lab(4, q), plate('1431220A.idw.dxf', (74.19, 201.66, 269.12, 325.24)).mirrored())]


@part('1431225A')
def _(q):
    return [(lab(3, q), plate('1431225A.idw.dxf', (82.04, 85.31, 173.04, 155.52)))]


@part('1431226A')
def _(q):
    # 沉头孔与外形相交，手工建模：34x8 R2，2-Φ4.5(沉头) + 1-Φ4
    p = Piece().rect(0, 0, 34, 8, 2).circle(5.5, 4, 4.5).circle(16.5, 4, 4.5).circle(30, 4, 4)
    return [(lab(3.5, q), p)]


# ---------------------------------------------------------------- 折弯件（按外形尺寸 - BD 手工展开）
# 展开规则（与 NO.441 人工图核对）：相邻两边外形尺寸 A、B，展开长 = A + B - BD；
# 折弯区宽 BD，两侧蓝线分别距 A 边自由边 A、距 B 边自由边 B（各边按外形交点定位），
# 红色中心线位于折弯区中间。

@part('0185727A00')
def _(q):
    t = 3; w = bd(t)
    # 0185727A01 电机支撑板：U 形，腹板 320x180，上下翻边 25，左端耳片 50 宽伸出 25
    p = Piece()
    p.outline([(0, 0, 5), (12, 0), (12, 5), (42, 5), (42, 0), (278, 0), (278, 5), (308, 5), (308, 0),
               (320, 0, 5), (320, 220, 5), (308, 220), (308, 215), (278, 215), (278, 220), (42, 220),
               (42, 215), (12, 215), (12, 220), (0, 220, 5), (0, 138), (7.5, 138), (7.5, 135),
               (-20, 135, 5), (-20, 85, 5), (7.5, 85), (7.5, 82), (0, 82)])
    p.bend(0, 22.5, 320, 22.5, w).bend(0, 197.5, 320, 197.5, w).bend(2.5, 85, 2.5, 135, w)
    for x in (18, 128):
        p.slot(x, 42.5, x, 67.5, 9).slot(x, 152.5, x, 177.5, 9)
    for x in (5.5, 30.5, 115.5, 140.5):
        p.tap(x, 10, 'M6').tap(x, 210, 'M6')
    p.tap(-14, 110, 'M6')
    a02 = plate('0185727A00.idw_图纸_3.dxf', (47.38, 105.14, 227.38, 135.14))
    return [(lab(3, q), p), (lab(5, q * 2), a02)]


@part('0185728A')
def _(q):
    t = 3; w = bd(t)
    # 顶板 100x79 + 左右侧板(高60，梯形) + 侧板后端内折安装脚(30，R10，腰孔)
    fl = [(0, 0), (20, 0, 10), (60, 65, 10), (60, 110, 10), (20, 110, 10), (20, 79), (0, 79)]
    left = [(5 - h, y, *r) for h, y, *r in fl]
    right = [(95 + h, y, *r) for h, y, *r in fl]
    p = Piece()
    p.outline(right + left[::-1])
    p.bend(2.5, 0, 2.5, 79, w).bend(97.5, 0, 97.5, 79, w)
    p.bend(5 - 20, 82.5, 5 - 60, 82.5, w).bend(95 + 20, 82.5, 95 + 60, 82.5, w)
    for x in (33, 67):
        for y0 in (8.5, 32.5, 56.5):
            p.slot(x, y0, x, y0 + 15, 6.5)
    for x in (5 - 40, 95 + 40):
        p.slot(x - 7.5, 100, x + 7.5, 100, 9)
    return [(lab(t, q), p)]


def circles(fname, region):
    """取视图区域内的圆(已去掉同心大圆)，返回 [(x, y, d)]，坐标相对区域左下角"""
    p = plate(fname, region)
    return [(e[1][0][0], e[1][0][1], 2 * e[1][1]) for e in p.ents if e[0] == 'CIRCLE']


@part('0185732A')
def _(q):
    t = 1.5; w = bd(t)          # 气缸护罩：顶板130x80，两侧板高47，左右前耳片，右侧板底部内折27
    p = Piece()
    p.outline([(-0.7, 0), (130.7, 0), (130.7, -21.2, 5), (171.7, -21.2, 5), (171.7, 0),
               (199.4, 0, 5), (199.4, 80, 5), (-44.7, 80, 5), (-44.7, -21.2, 5), (-0.7, -21.2, 5)])
    p.bend(1.15, 0, 1.15, 80, w).bend(128.85, 0, 128.85, 80, w).bend(173.55, 0, 173.55, 80, w)
    p.bend(-0.7, 1.15, -44.7, 1.15, w).bend(130.7, 1.15, 171.7, 1.15, w)
    for h in (12.5, 32.5):
        p.circle(2.3 - h, -11.2, 6.5).circle(127.7 + h, -11.2, 6.5)
    return [(lab(t, q), p)]


@part('0185736A')
def _(q):
    t = 3; w = bd(t)            # 护罩固定件：立板40x30 + 顶翻边16
    p = Piece()
    p.outline([(0, 0, 5), (40, 0, 5), (40, 41, 5), (0, 41, 5)])
    p.bend(0, 27.5, 40, 27.5, w)
    p.slot(5, 10, 35, 10, 5.5)
    p.tap(15, 34.2, 'M6').tap(25, 34.2, 'M6')
    # 图示折弯处中间 20 宽有台阶，两侧各一条 0.5 宽工艺缝（需人工复核）
    p.rect(10, 24, 10.5, 31).rect(29.5, 24, 30, 31)
    return [(lab(t, q), p)]


@part('0185739A')
def _(q):
    t = 3; w = bd(t)            # 安装板：立板120x80 + 平板100
    p = Piece()
    p.outline([(0, 0, 5), (120, 0, 5), (120, 175, 5), (0, 175, 5)])
    p.bend(0, 77.5, 120, 77.5, w)
    for x, y, d in circles('0185739A.idw.dxf', (153.545, 293.052, 273.545, 373.052)):
        p.circle(x, y, d)
    for x, y, d in circles('0185739A.idw.dxf', (153.545, 118.065, 273.545, 218.065)):
        p.circle(x, 75 + y, d)
    return [(lab(t, q), p)]


@part('0185740A')
def _(q):
    t = 5; w = bd(t)            # 输送连接件：底板60(梯形) + 立板30
    p = Piece()
    p.outline([(0, 35.0, 10), (30, 0, 10), (90, 0, 10), (120, 35.0, 10), (120, 81.6, 10), (0, 81.6, 10)])
    p.bend(0, 55.8, 120, 55.8, w)
    p.circle(40, 20, 11).circle(80, 20, 11)
    for x in (15, 60, 105):
        p.tap(x, 73.6, 'M8')
    return [(lab(t, q), p)]


@part('0185742A')
def _(q):
    t = 1; w = bd(t)            # 盖板：立板153x40 + 顶翻边25，3-M5 铆螺母孔 Φ8
    p = Piece()
    p.outline([(0, 0, 5), (153, 0, 5), (153, 63.3, 5), (0, 63.3, 5)])
    p.bend(0, 39.15, 153, 39.15, w)
    for x in (16.5, 76.5, 136.5):
        p.circle(x, 5, 8)
    return [(lab(t, q), p)]


@part('0185753A')
def _(q):
    t = 1; w = bd(t)            # 食品盖板：立板153x80 + 翻边20
    p = Piece()
    p.outline([(0, 0, 5), (153, 0, 5), (153, 98.3, 5), (0, 98.3, 5)])
    p.bend(0, 79.15, 153, 79.15, w)
    for x in (16, 66, 116):
        p.circle(x, 93.3, 6.5)
    return [(lab(t, q), p)]


@part('0185754A')
def _(q):
    t = 1.5; w = bd(t)          # 护罩：顶板125x85，两侧板高42，右侧板底部内折27，后边下折挡板15
    # 后角释放槽按“释放槽样式.dxf”：侧板为全宽翻边，后挡板每侧内缩 s，V 形槽
    rp, rg, rs = relief_params(t, w)
    p = Piece()
    p.outline([(-39.7, 0), (189.4, 0), (189.4, 85), (125 + rg, 85), (125 - rp, 85 - rp), (125 - rs, 85 + rg),
               (125 - rs, 97.7, 2), (rs, 97.7, 2), (rs, 85 + rg), (rp, 85 - rp), (-rg, 85), (-39.7, 85, 5)])
    p.bend(1.15, 0, 1.15, 85, w).bend(123.85, 0, 123.85, 85, w).bend(163.55, 0, 163.55, 85, w)
    p.bend(0, 83.85, 125, 83.85, w)
    p.circle(8, 91.7, 6.5).circle(90, 91.7, 6.5)
    return [(lab(t, q), p)]


@part('0185755A')
def _(q):
    t = 5; w = bd(t)            # 连接件：长边490 + 立边80，宽60
    p = Piece()
    p.outline([(0, 0, 5), (561.6, 0, 5), (561.6, 60, 5), (0, 60, 5)])
    p.bend(485.8, 0, 485.8, 60, w)
    p.slot(14.5, 15, 114.5, 15, 9).slot(14.5, 45, 114.5, 45, 9)
    for x in (506.6, 541.6):
        p.circle(x, 15, 9).circle(x, 45, 9)
    return [(lab(t, q), p)]


@part('0186023A')
def _(q):
    t = 2; w = bd(t)            # 过渡板：U 形，腹板117x16，两侧边高22宽25
    p = Piece()
    p.outline([(-19, 0, 2), (136, 0, 2), (136, 25, 2), (124, 25, 2), (124, 16, 2), (-7, 16, 2),
               (-7, 25, 2), (-19, 25, 2)])
    p.bend(1.5, 0, 1.5, 16, w).bend(115.5, 0, 115.5, 16, w)
    for y in (6, 19):
        p.slot(-11, y, -15, y, 4).slot(128, y, 132, y, 4)
    return [(lab(t, q), p)]


@part('1431333A')
def _(q):
    t = 3; w = bd(t)            # 护罩支架：U 形，腹板39，两侧边高20，宽25
    p = Piece()
    p.outline([(-15, 0, 5), (54, 0, 5), (54, 25, 5), (-15, 25, 5)])
    p.bend(2.5, 0, 2.5, 25, w).bend(36.5, 0, 36.5, 25, w)
    for y in (5, 20):
        p.tap(-9, y, 'M5').tap(48, y, 'M5')
    return [(lab(t, q), p)]


@part('1190107A00')
def _(q):
    t = 2.5; w = bd(t)          # 1190107A01 调节支架：C 形 420 长，腹板68，翼边35，端部 20x20 斜角
    p = Piece()
    p.outline([(0, 0), (400, 0, 5), (420, 20, 5), (420, 110, 5), (400, 130, 5), (0, 130)])
    p.bend(0, 33, 420, 33, w).bend(0, 97, 420, 97, w)
    for x in (195, 255, 315, 375):
        p.slot(x, 47.5, x + 30, 47.5, 9).slot(x, 82.5, x + 30, 82.5, 9)
    a02 = plate('1190107A00.idw_图纸_3.dxf', (87.06, 105.56, 155.06, 140.56))
    return [(lab(t, q), p), (lab(10, q), a02)]


# ---------------------------------------------------------------- 复杂件：占位，人工补全
def todo(t, note):
    return lambda q: ('TODO', [lab(t, q)], note)


PARTS['0185730A'] = todo(5, '0185730A 待人工展开（J形+梳齿铰接，复杂）')
PARTS['0185735A'] = todo(1.5, '0185735A 待人工展开（锥形护罩，多槽）')
PARTS['0185738A'] = todo(3, '0185738A 待人工展开（卷边铰接件）')
PARTS['0185750A'] = todo(2.5, '0185750A 待人工展开（长槽型件，展开宽约20+144.5+60+20-3x4=232.5）')
PARTS['0185751A'] = todo(2.5, '0185751A 为0185750A镜像件，待人工展开')
PARTS['0186033A'] = todo(1.5, '0186033A 待人工展开（围板+顶板）')
PARTS['1530201A'] = todo(4, '1530201A 待人工展开（135°多折弯支座）')


import parts_474b
_part, _mirror_of = parts_474b.setup(PARTS, DXF, lab, plate, circles, todo)
parts_474b.setup2(PARTS, DXF, lab, plate, circles, todo, _part, _mirror_of)


# ---------------------------------------------------------------- 输出
HDR_Y = 26431.0        # 表头文字基线（与 NO.441 一致）
LAB_Y = 26524.4        # 第一个“材料-厚度”标签
PIECE_DY = 86.3        # 标签到零件底边
STACK_GAP = 150.0      # 零件顶到上一个标签
X0 = -1148.0
COL_GAP = 520.0
TXT_H = 30.0


def text_w(s, h=TXT_H):
    w = 0
    for ch in s:
        w += h * (1.0 if ord(ch) > 0x2E80 else 0.62)
    return w


def build(out_path):
    tpl = ezdxf.readfile(os.path.join(ROOT, '441', 'NO.441.dxf'))
    msp = tpl.modelspace()
    for e in list(msp):
        msp.delete_entity(e)
    for b in list(tpl.blocks):
        if b.name.startswith(('蓝探科', 'Drawing6')):
            tpl.blocks.delete_block(b.name, safe=False)

    ws = openpyxl.load_workbook(os.path.join(D474, 'NO.474.xlsx')).active
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[3]]
    x = X0
    report = []
    for r in rows:
        date, no, order, code, name, qty = r[0], r[1], r[2], r[3], r[4], int(r[5])
        dstr = date.strftime('%Y-%m-%d') if isinstance(date, datetime.datetime) else str(date)
        f = PARTS.get(code)
        surf = (r[7] or '').strip() if r[7] else ''
        hdr = '·'.join([dstr, str(no), order, code, name, '%d件' % qty] + ([surf] if surf else []))
        hw = text_w(hdr)
        msp.add_text(hdr, height=TXT_H, dxfattribs=dict(layer='0', color=2, style='Z-English', insert=(x, HDR_Y)))
        cx = x + hw / 2
        colw = hw
        if f is None:
            note = '无图纸，待人工补充'
            msp.add_text(note, height=TXT_H, dxfattribs=dict(layer='0', color=1, style='Z-English',
                                                             insert=(cx - text_w(note) / 2, LAB_Y)))
            report.append((code, '无图纸-占位'))
        else:
            res = f(qty)
            if isinstance(res, tuple) and res[0] == 'TODO':
                _, labels, note = res
                y = LAB_Y
                for l in labels:
                    msp.add_text(l, height=TXT_H, dxfattribs=dict(layer='0', color=3, style='Z-English',
                                                                  insert=(cx - text_w(l) / 2, y)))
                    y += 60
                msp.add_text(note, height=TXT_H, dxfattribs=dict(layer='0', color=1, style='Z-English',
                                                                 insert=(cx - text_w(note) / 2, y + 30)))
                colw = max(colw, text_w(note))
                report.append((code, '占位-' + note))
            else:
                y = LAB_Y
                for l, p in res:
                    p = p.normalized()
                    b = p.bbox()
                    w, h = b[2] - b[0], b[3] - b[1]
                    msp.add_text(l, height=TXT_H, dxfattribs=dict(layer='0', color=3, style='Z-English',
                                                                  insert=(cx - text_w(l) / 2, y)))
                    p.draw(msp, cx - w / 2, y + PIECE_DY)
                    colw = max(colw, w, text_w(l))
                    y = y + PIECE_DY + h + STACK_GAP
                report.append((code, '已完成'))
        x += max(colw, hw) + COL_GAP
    tpl.saveas(out_path)
    return report


if __name__ == '__main__':
    out = os.path.join(D474, 'NO.474.dxf')
    rep = build(out)
    for c, s in rep:
        print(c, s)
    print('saved', out)
