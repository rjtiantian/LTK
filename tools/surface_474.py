# -*- coding: utf-8 -*-
"""按图纸标题栏材料 + 技术要求，推出 NO.474 清单“表面”列（格式同 NO.441：材料-表面处理）"""
import os, re, glob
import ezdxf
from drawing_info import info


def dxf_for(code, dxfdir):
    fs = sorted(glob.glob(os.path.join(dxfdir, code + '*.dxf')))
    if fs:
        return fs, None
    # 镜像件：在其它图纸的镜像表里找
    for f in sorted(glob.glob(os.path.join(dxfdir, '*.dxf'))):
        if code.encode() in open(f, 'rb').read():
            src = os.path.basename(f).split('.')[0].split('_')[0]
            return sorted(glob.glob(os.path.join(dxfdir, src + '*.dxf'))), src
    return [], None


def surface(code, dxfdir):
    fs, src = dxf_for(code, dxfdir)
    if not fs:
        return None, None
    attrs, texts = info(fs[0])
    mat = attrs.get('材料', '')
    if not mat or '钢，软' in mat:
        # 组件首页无材料：取子件材料
        for f in fs[1:]:
            a, _ = info(f)
            if a.get('材料'):
                mat = a['材料']; break
    txt = ' '.join(texts)
    if '65号弹簧钢' in txt or mat == '65':
        mat = '65钢'
    mat = mat or 'SUS304'
    s = ''
    if '拉丝' in txt:
        s = '拉丝'
    elif '镀镍' in txt:
        s = '镀镍'
    elif '喷砂' in txt:
        s = '喷砂'
    return (mat + '-' + s) if s else mat, src
