# -*- coding: utf-8 -*-
"""通用下料图排版（同 NO.441 / NO.474）：每个清单行一列，黄色表头 + 绿色“材料-厚度,件数”标签 + 展开图。

build(xlsx, PARTS, out_path)
  PARTS: code -> f(qty) -> [(label, Piece)] 或 ('TODO', [labels], note)
"""
import os, datetime
import ezdxf, openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HDR_Y = 26431.0        # 表头文字基线（与 NO.441 一致）
LAB_Y = 26524.4        # 第一个“材料-厚度”标签
PIECE_DY = 86.3        # 标签到零件底边
STACK_GAP = 150.0      # 零件顶到上一个标签
X0 = -1148.0
COL_GAP = 520.0
TXT_H = 30.0


def text_w(s, h=TXT_H):
    return sum(h * (1.0 if ord(ch) > 0x2E80 else 0.62) for ch in s)


def _text(msp, s, x, y, color):
    msp.add_text(s, height=TXT_H, dxfattribs=dict(layer='0', color=color, style='Z-English', insert=(x, y)))


def build(xlsx, PARTS, out_path):
    tpl = ezdxf.readfile(os.path.join(ROOT, '441', 'NO.441.dxf'))
    msp = tpl.modelspace()
    for e in list(msp):
        msp.delete_entity(e)
    for b in list(tpl.blocks):
        if b.name.startswith(('蓝探科', 'Drawing6')):
            tpl.blocks.delete_block(b.name, safe=False)

    ws = openpyxl.load_workbook(xlsx).active
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[3]]
    x = X0
    report = []
    for r in rows:
        date, no, order, code, name, qty = r[0], r[1], r[2], str(r[3]).strip(), r[4], int(r[5])
        dstr = date.strftime('%Y-%m-%d') if isinstance(date, datetime.datetime) else str(date)
        surf = (r[7] or '').strip() if r[7] else ''
        hdr = '·'.join([dstr, str(no), order, code, name, '%d件' % qty] + ([surf] if surf else []))
        hw = text_w(hdr)
        _text(msp, hdr, x, HDR_Y, 2)
        cx = x + hw / 2
        colw = hw
        f = PARTS.get(code)
        if f is None:
            note = '无图纸，待人工补充'
            _text(msp, note, cx - text_w(note) / 2, LAB_Y, 1)
            report.append((code, '无图纸-占位'))
        else:
            res = f(qty)
            if isinstance(res, tuple) and res[0] == 'TODO':
                _, labels, note = res
                y = LAB_Y
                for l in labels:
                    _text(msp, l, cx - text_w(l) / 2, y, 3)
                    y += 60
                _text(msp, note, cx - text_w(note) / 2, y + 30, 1)
                colw = max(colw, text_w(note))
                report.append((code, '占位-' + note))
            else:
                y = LAB_Y
                for l, p in res:
                    p = p.normalized()
                    b = p.bbox()
                    w, h = b[2] - b[0], b[3] - b[1]
                    _text(msp, l, cx - text_w(l) / 2, y, 3)
                    p.draw(msp, cx - w / 2, y + PIECE_DY)
                    colw = max(colw, w, text_w(l))
                    y = y + PIECE_DY + h + STACK_GAP
                report.append((code, '已完成'))
        x += max(colw, hw) + COL_GAP
    tpl.saveas(out_path)
    return report
