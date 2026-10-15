# -*- coding: utf-8 -*-
"""按图纸材料 + 技术要求补清单“表面”列（格式同 NO.441 历史：SUS304-拉丝 / Q235B-RAL9007）
用法: python3 tools/fill_surface.py 475/NO.475.xlsx 475/DXF"""
import sys, re, openpyxl
from surface_474 import dxf_for
from drawing_info import info

OVERRIDE = {'7420709A': 'Q235B-RAL9007', '7420710A': 'Q235B-RAL9007',   # 采用较新的 7420709A.dxf（烤漆版）
            '7420118A': 'Q235B-RAL9007'}                                # 图纸为 7420118B


def surface(code, dxfdir):
    if code in OVERRIDE:
        return OVERRIDE[code]
    fs, _ = dxf_for(code, dxfdir)
    if not fs:
        return None
    mat, txt = '', ''
    for f in fs:
        a, t = info(f)
        mat = mat or a.get('材料', '')
        txt += ' '.join(t)
    mat = mat or ('Q235B' if 'RAL' in txt else 'SUS304')
    m = re.search(r'RAL\s*(\d{4})', txt) or re.search(r'烤漆\s*(\d{4})', txt)
    if mat.startswith('Q235'):
        return 'Q235B-RAL' + m.group(1) if m else 'Q235B'
    for k in ('拉丝', '喷砂', '镀镍'):
        if k in txt:
            return mat + '-' + k
    return mat


if __name__ == '__main__':
    x, d = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(x)
    ws = wb.active
    for row in ws.iter_rows(min_row=2):
        if row[3].value:
            s = surface(str(row[3].value).strip(), d)
            row[7].value = s
            print(row[3].value, s)
    wb.save(x)
