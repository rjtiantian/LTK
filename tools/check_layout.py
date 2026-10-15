# -*- coding: utf-8 -*-
"""排版自检：读下料 DXF，按图元顺序分列（每列 = 黄色表头 + 其后写入的零件几何、绿/红文字），
检查相邻两列包围盒 X 向不重叠，且间距 = 750（容差 1）。用法: python3 tools/check_layout.py 文件.dxf"""
import sys, ezdxf
from ezdxf import bbox as ezbbox
sys.path.insert(0, __import__('os').path.dirname(__file__))
from layout import text_w

doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
ents = list(msp)
hdr = sorted([e for e in ents if e.dxftype() == 'TEXT' and e.dxf.color == 2], key=lambda e: e.dxf.insert.x)
def xr(e):
    if e.dxftype() == 'TEXT':
        x = e.dxf.insert.x; xs = [x, x + text_w(e.dxf.text, e.dxf.height)]
    else:
        xs = []
    b = ezbbox.extents([e])
    if b.has_data: xs += [b.extmin.x, b.extmax.x]
    return min(xs), max(xs)
# 列归属：排版时每列先写黄色表头，再写本列标签和几何，按图元顺序分列
spans = []
for e in ents:
    a, b = xr(e)
    if e.dxftype() == 'TEXT' and e.dxf.color == 2:
        spans.append([a, b])
    elif spans:
        spans[-1][0] = min(spans[-1][0], a); spans[-1][1] = max(spans[-1][1], b)
bad = 0
for i in range(len(hdr) - 1):
    gap = spans[i + 1][0] - spans[i][1]
    if gap < 0 or abs(gap - 750) > 1:
        bad += 1
        print('列间距异常: %s | %s  gap=%.1f' % (hdr[i].dxf.text[:40], hdr[i + 1].dxf.text[:40], gap))
print(sys.argv[1], '列数', len(hdr), '异常', bad)
