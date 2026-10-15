# -*- coding: utf-8 -*-
"""汇总 474/DXF 每张图纸的标题栏/技术要求/镜像表等文字信息"""
import ezdxf, glob, os, re, sys, json
def info(f):
    d = ezdxf.readfile(f)
    attrs, texts = {}, []
    for e in d.modelspace():
        t = e.dxftype()
        if t == 'INSERT':
            for a in e.attribs:
                if a.dxf.text.strip():
                    attrs[re.sub(r'_\d+$', '', a.dxf.tag)] = a.dxf.text.strip()
        elif t == 'TEXT':
            texts.append(e.dxf.text.strip())
        elif t == 'MTEXT':
            s = e.plain_text().replace('\n', ' / ').strip()
            if '1804' not in s and s:
                texts.append(s)
    return attrs, texts
if __name__ == '__main__':
    out = {}
    for f in sorted(glob.glob(sys.argv[1] + '/*.dxf')):
        a, t = info(f)
        out[os.path.basename(f)] = dict(attrs=a, texts=t)
    json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
