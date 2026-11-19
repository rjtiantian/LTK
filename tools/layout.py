# -*- coding: utf-8 -*-
"""通用下料图排版（同 NO.441 / NO.474）：每个清单行一列，黄色表头 + 绿色“材料-厚度,件数”标签 + 展开图。

build(xlsx, PARTS, out_path, ISO=None)
  PARTS: code -> f(qty) -> [(label, Piece)] 或 ('TODO', [labels], note)
  ISO:   焊接件 code -> 整件 STEP；消隐轴测图建块插在该列最顶上（上面零件再往上 STACK_GAP），比例 1。
         块名「客户 订单·yymmdd_HHMMSS·5位号」、块内 可见 (ISO) / 可见窄的 (ISO)，同用户给的蓝探科样例
  cust:  块名里的客户名
  dwg_iso: 没登记 STEP 的件，客户 DWG（DXF/<物料号>.dxf 等）上有轴测视图就原样 1:1 取 可见 / 可见窄的 层建块，
         同样插在列最顶上（2026-11-19 用户定：DWG 上有轴测图的都加）
"""
import os, datetime
import ezdxf, openpyxl
import oldparts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HDR_Y = 26431.0        # 表头文字基线（与 NO.441 一致）
LAB_Y = 26524.4        # 第一个“材料-厚度”标签
PIECE_DY = 86.3        # 标签到零件底边
STACK_GAP = 150.0      # 零件顶到上一个标签
X0 = -1148.0
COL_GAP = 750.0        # 上一列（零件几何 + 绿色标签 + 黄色表头）包围盒右端到下一列包围盒左端的间距
TXT_H = 30.0


def text_w(s, h=TXT_H):
    return sum(h * (1.0 if ord(ch) > 0x2E80 else 0.62) for ch in s)


def _xrange(ents):
    """列内图元的 X 向包围盒：ezdxf 包围盒与文字字宽估算（含中文全角）取并集，保证不小估"""
    from ezdxf import bbox as ezbbox
    xs = []
    if ents:
        b = ezbbox.extents(ents)
        if b.has_data:
            xs += [b.extmin.x, b.extmax.x]
    for e in ents:
        if e.dxftype() == 'TEXT':
            x = e.dxf.insert.x
            xs += [x, x + text_w(e.dxf.text, e.dxf.height)]
    return min(xs), max(xs)


def _text(msp, s, x, y, color):
    msp.add_text(s, height=TXT_H, dxfattribs=dict(layer='0', color=color, style='Z-English', insert=(x, y)))


def _draw_iso(doc, msp, name, step, cx, ybot):
    """轴测图建块（照 2026-11-09 用户给的蓝探科样例：块名「客户 订单·yymmdd_HHMMSS·5位号」，块内 1:1，
    LINE / ELLIPSE 在「可见 (ISO)」「可见窄的 (ISO)」层，块插在 0 层、比例 1，左右居中在零件中线，底边在 ybot）"""
    from iso_view import iso_lines, add_prims, LAYERS
    for ly in LAYERS.values():
        if ly not in doc.layers:
            doc.layers.add(ly, color=7)
    r = iso_lines(step)
    blk = doc.blocks.new(name)
    add_prims(blk, r['prims'])
    return [msp.add_blockref(name, (cx - r['w'] / 2, ybot), dxfattribs=dict(layer='0', ltscale=0.5))]


def _dwg_src(code, dxf_dir):
    """客户图纸转出的 DXF（多张时取第 1 张：总图 / 焊接件的轴测图在第 1 张）"""
    for n in (code + '.idw.dxf', code + '.dxf', code + '_图纸_1.dxf', code + '.idw_图纸_1.dxf', code + ' .idw.dxf'):
        f = os.path.join(dxf_dir, n)
        if os.path.exists(f):
            return f
    return None


def _draw_dwg_iso(doc, msp, name, dxf, cx, ybot, flip=False):
    """客户 DWG 上的轴测视图原样（1:1，只取 可见 / 可见窄的 层）建块，插法同 _draw_iso；图上没有轴测图返回 None"""
    from dwg_iso import iso_prims, KEEP
    r = iso_prims(dxf)
    if r is None:
        return None
    ents, w, h = r
    for ly in KEEP:
        if ly not in doc.layers:
            doc.layers.add(ly, color=7)
    blk = doc.blocks.new(name)
    for e in ents:
        e.dxf.color = 256                         # 随层
        blk.add_entity(e)
    if flip:                                      # 镜像件：块 X 比例 -1，插入点放右边
        return [msp.add_blockref(name, (cx + w / 2, ybot), dxfattribs=dict(layer='0', ltscale=0.5, xscale=-1))]
    return [msp.add_blockref(name, (cx - w / 2, ybot), dxfattribs=dict(layer='0', ltscale=0.5))]


def build(xlsx, PARTS, out_path, ISO=None, cust='', dwg_iso=True, mirror=None):
    mirror = mirror or {}
    ISO = ISO or {}
    import random
    stamp = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
    used = set()
    tpl = ezdxf.readfile(os.path.join(ROOT, '441', 'NO.441.dxf'))
    msp = tpl.modelspace()
    for e in list(msp):
        msp.delete_entity(e)
    for b in list(tpl.blocks):
        if b.name.startswith(('蓝探科', 'Drawing6')):
            tpl.blocks.delete_block(b.name, safe=False)

    ws = openpyxl.load_workbook(xlsx).active
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[3]]
    cursor = X0
    report = []
    dxf_dir = os.path.join(os.path.dirname(xlsx), 'DXF')
    old = []
    for r in rows:
        date, no, order, code, name, qty = r[0], r[1], r[2], str(r[3]).strip(), r[4], int(r[5])
        dstr = date.strftime('%Y-%m-%d') if isinstance(date, datetime.datetime) else ('' if date is None else str(date))
        surf = (r[7] or '').strip() if r[7] else ''
        tag, red = oldparts.mark(code, dxf_dir)    # 老图：历史做过同号件 / 版本比历史旧 / 清单与图纸版本不一致
        if len(r) > 8 and r[8] and str(r[8]).strip():     # 客户清单备注（如“沟通后再加工”）红字写在表头下方
            ns = str(r[8]).strip()                         # 「；▲」分隔的几条各占一行
            red = red + [(t if t.startswith('▲') else '▲客户备注：' + t) for t in ns.replace('；▲', '\n▲').split('\n')]
        hdr = '·'.join(str(v) for v in [dstr, no, order, code, name, '%d件' % qty, surf, tag] if v)   # 单件出图无序号/订单号
        if tag or red:
            old.append((code, tag, red))
        before = set(e.dxf.handle for e in msp)
        x = 0.0                                   # 先在 x=0 处画出本列，再按包围盒整体平移
        hw = text_w(hdr)
        _text(msp, hdr, x, HDR_Y, 2)
        for i, t in enumerate(red):               # 红字提醒写在表头下方
            _text(msp, t, x, HDR_Y - 50 * (i + 1), 1)
        cx = x + hw / 2
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
                report.append((code, '占位-' + note))
            else:
                y = LAB_Y
                for l, p in res:
                    p = p.normalized()
                    b = p.bbox()
                    w, h = b[2] - b[0], b[3] - b[1]
                    _text(msp, l, cx - text_w(l) / 2, y, 3)
                    p.draw(msp, cx - w / 2, y + PIECE_DY)
                    y = y + PIECE_DY + h + STACK_GAP
                report.append((code, '已完成'))
        col = [e for e in msp if e.dxf.handle not in before]
        src = ISO.get(code) or (dwg_iso and f is not None and _dwg_src(code, dxf_dir))
        flip = False
        if not src and dwg_iso and f is not None and code in mirror:      # 镜像件自己没图：取源件轴测图，块 X 比例 -1（同历史图）
            src = _dwg_src(mirror[code], dxf_dir)
            flip = bool(src)
        if src:                                   # 轴测图块放本列最顶上：焊接件用整件 STEP，其余取客户 DWG 上的轴测视图
            from ezdxf import bbox as ezbbox
            ytop = ezbbox.extents(col).extmax.y
            n = random.randint(10000, 99999)
            while n in used:
                n = random.randint(10000, 99999)
            used.add(n)
            bname = ('%s %s·%s·%d' % (cust, order or code, stamp, n)).strip()
            if str(src).lower().endswith('.dxf'):
                ins = _draw_dwg_iso(tpl, msp, bname, src, cx, ytop + STACK_GAP, flip)
                if ins:
                    col += ins
                    report.append((code, '轴测图(DWG)'))
            else:
                col += _draw_iso(tpl, msp, bname, src, cx, ytop + STACK_GAP)
                report.append((code, '轴测图'))
        x0, x1 = _xrange(col)                     # 轴测图块 1:1 可能比零件宽，算列宽要带上
        dx = cursor - x0
        for e in col:
            e.translate(dx, 0, 0)
        cursor = x1 + dx + COL_GAP
    tpl.saveas(out_path)
    for code, tag, red in old:
        print('老图标注', code, tag, ' '.join(red))
    return report
