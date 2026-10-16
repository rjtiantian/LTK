# -*- coding: utf-8 -*-
"""老图标注：清单物料号在历史人工下料图（历史图纸/LTK历史图纸.zip）里做过的，在黄色表头末尾追加说明（同历史表头“·更新”的写法）。

物料号 = 7 位数字 + 版本字母 + 可选 2 位子件号（如 1450220A00），最后一位字母是版本号。
  同号同版本做过        -> 表头追加“老图NO.xxx”（最近一次订单）
  历史已有更高版本      -> 表头追加“老图A版(NO.427已做B版)”，并加红字 ▲ 提醒：本单按旧版图纸下料，需与客户确认
  历史只有更低版本      -> 表头追加“更新(NO.xxx为A版)”：图纸已改版，不能直接用旧程序
另外检查订单 DXF 目录：清单版本与图纸文件版本不一致的（如清单 7420118A、图纸只有 7420118B），加红字说明。
"""
import os, re, collections

PAT = re.compile(r'(\d{7})([A-Z])(\d{2})?')
_IDX = None


def _order_key(no):
    m = re.search(r'\d+', no)
    return int(m.group()) if m else -1


def _index():
    """(7位号, 子件号) -> [(版本, 订单号)]，只取表头里的物料号字段（备注里的别名号不算）"""
    global _IDX
    if _IDX is None:
        import histlib
        histlib.headers('')
        _IDX = collections.defaultdict(list)
        for p in histlib._DATA['parts']:
            f = [s.strip() for s in p['h'].split('·')]
            no = next((s for s in f if re.match(r'^(NO|AO)\.?\s*\d', s)), '')
            code = next((s for s in f if PAT.fullmatch(s)), None)
            if not code:
                continue
            m = PAT.fullmatch(code)
            _IDX[(m.group(1), m.group(3) or '')].append((m.group(2), no.split()[0] if no else '?'))
    return _IDX


def _latest(lst):
    return max(lst, key=lambda v: _order_key(v[1]))[1]


def mark(code, dxf_dir=None):
    """返回 (表头追加文字, [红字提醒])"""
    m = PAT.fullmatch(code)
    if not m:
        return '', []
    base, ver, sub = m.group(1), m.group(2), m.group(3) or ''
    suffix, red = '', []
    hist = _index().get((base, sub), [])
    same = [h for h in hist if h[0] == ver]
    newer = [h for h in hist if h[0] > ver]
    older = [h for h in hist if h[0] < ver]
    if newer:
        nv = max(h[0] for h in newer)
        no = _latest([h for h in newer if h[0] == nv])
        suffix = '老图%s版(%s已做%s版)' % (ver, no, nv)
        red.append('▲%s版为旧版：%s已做%s%s%s，本单按%s版图纸下料，请与客户确认' % (ver, no, base, nv, sub, ver))
    elif same:
        suffix = '老图' + _latest(same)
    elif older:
        ov = max(h[0] for h in older)
        suffix = '更新(%s为%s版)' % (_latest([h for h in older if h[0] == ov]), ov)
    if dxf_dir and os.path.isdir(dxf_dir):
        vs = set()
        for f in os.listdir(dxf_dir):
            mm = PAT.match(f)
            if mm and mm.group(1) == base and (mm.group(3) or '') == sub:
                vs.add(mm.group(2))
        if vs and ver not in vs:
            red.append('▲清单为%s版，图纸只有%s版，按%s版下料' % (ver, '/'.join(sorted(vs)), max(vs)))
    return suffix, red
