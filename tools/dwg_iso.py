# -*- coding: utf-8 -*-
"""从客户 DWG（Inventor 出图，转 DXF）里找轴测图视图，取出来做下料图顶上的轴测图块。

  python3 tools/dwg_iso.py a.dxf [b.dxf ...]        # 列每张图的视图，标出哪个是轴测图

找法：「可见 (ISO)」层按包围盒并成视图；视图里直线方向大多在 ±30°（等轴测）或其它斜向、
又几乎没有水平线的算轴测图（正投影视图直线全是 0° / 90°）；带 ELLIPSE 的加分。
Inventor 的视图在模型空间是 1:1，轴测图照原样 1:1 取，不缩放。
取的层：可见 (ISO)、可见窄的 (ISO)（同 2026-11-09 用户给的 NO.441 样例块）；隐藏线、中心线、尺寸不取。
"""
import math, sys, os
from collections import Counter
import ezdxf
from ezdxf import bbox
from ezdxf.sections import objects as _o

_orig = _o.ObjectsSection.setup_object_management_tables


def _safe(self, rootdict):
    try:
        _orig(self, rootdict)
    except ValueError:
        pass


_o.ObjectsSection.setup_object_management_tables = _safe

VIS = '可见 (ISO)'
KEEP = ('可见 (ISO)', '可见窄的 (ISO)')
TYPES = ('LINE', 'ARC', 'CIRCLE', 'LWPOLYLINE', 'POLYLINE', 'ELLIPSE', 'SPLINE')


def _boxes(msp, layer=VIS, gap=1.0):
    items = []
    for e in msp:
        if e.dxf.layer != layer or e.dxftype() not in TYPES:
            continue
        try:
            b = bbox.extents([e])
        except Exception:
            continue
        if b.has_data:
            items.append([b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y])
    merged = True
    while merged:
        merged, out = False, []
        for b in items:
            for o in out:
                if b[0] <= o[2] + gap and o[0] <= b[2] + gap and b[1] <= o[3] + gap and o[1] <= b[3] + gap:
                    o[:] = [min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])]
                    merged = True
                    break
            else:
                out.append(list(b))
        items = out
    return items


def _inside(e, box, tol=0.5):
    try:
        b = bbox.extents([e])
    except Exception:
        return False
    return (b.has_data and b.extmin.x >= box[0] - tol and b.extmin.y >= box[1] - tol
            and b.extmax.x <= box[2] + tol and b.extmax.y <= box[3] + tol)


def classify(msp, box):
    """返回 (是否轴测, 统计)"""
    ang = Counter()
    n_line = n_ell = 0
    for e in msp:
        if e.dxf.layer != VIS or not _inside(e, box):
            continue
        t = e.dxftype()
        if t == 'ELLIPSE':
            n_ell += 1
        if t == 'LINE':
            s, p = e.dxf.start, e.dxf.end
            L = math.hypot(p.x - s.x, p.y - s.y)
            if L < 1:
                continue
            n_line += 1
            a = math.degrees(math.atan2(p.y - s.y, p.x - s.x)) % 180
            if a < 1 or a > 179:
                ang['h'] += 1
            elif abs(a - 90) < 1:
                ang['v'] += 1
            else:
                ang['slant'] += 1
    st = dict(lines=n_line, ellipses=n_ell, **ang)
    if n_line + n_ell < 6:
        return False, st
    slant = ang['slant'] / max(n_line, 1)
    hfrac = ang['h'] / max(n_line, 1)
    iso = (slant >= 0.4 and hfrac <= 0.15) or (n_ell >= 2 and slant >= 0.25 and hfrac <= 0.25)
    return iso, st


def find_iso(dxf):
    """返回 [(box, 统计)]，最像轴测图的在前"""
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    res = []
    for b in _boxes(msp):
        ok, st = classify(msp, b)
        if ok:
            res.append((b, st))
    # 真轴测图椭圆、斜线多；剖视 / 断面偶尔也有几条斜线，按 椭圆 + 斜线 数挑，再按面积
    res.sort(key=lambda r: (-(r[1]['ellipses'] + r[1].get('slant', 0)), -(r[0][2] - r[0][0]) * (r[0][3] - r[0][1])))
    return res


def iso_prims(dxf, box=None):
    """取轴测图视图内 可见 / 可见窄的 层图元（复制品，已平移到包围盒左下角 = 原点），返回 (ents, w, h)。
    box 不给就取最大的那个轴测视图；没有轴测图返回 None。"""
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    if box is None:
        r = find_iso(dxf)
        if not r:
            return None
        box = r[0][0]
    # 别的视图（俯视图端头等）伸进轴测图包围盒的部分不要：整条落在别的视图框里的图元剔掉
    others = [b for b in _boxes(msp) if b != box and not (b[0] >= box[0] - 0.5 and b[1] >= box[1] - 0.5
                                                          and b[2] <= box[2] + 0.5 and b[3] <= box[3] + 0.5)]
    ents = []
    for e in msp:
        if e.dxf.layer in KEEP and e.dxftype() in TYPES and _inside(e, box) and not any(_inside(e, o, 0.01) for o in others):
            c = e.copy()
            c.translate(-box[0], -box[1], 0)
            ents.append(c)
    return ents, box[2] - box[0], box[3] - box[1]


if __name__ == '__main__':
    for f in sys.argv[1:]:
        doc = ezdxf.readfile(f)
        msp = doc.modelspace()
        out = []
        for b in sorted(_boxes(msp), key=lambda b: -(b[2] - b[0]) * (b[3] - b[1])):
            if (b[2] - b[0]) * (b[3] - b[1]) < 100:
                continue
            ok, st = classify(msp, b)
            out.append('%s[%.0f,%.0f %.0fx%.0f %s]' % ('ISO' if ok else '', b[0], b[1], b[2] - b[0], b[3] - b[1],
                                                     ','.join('%s%d' % (k[0], v) for k, v in st.items())))
        print(os.path.basename(f), ' '.join(out[:8]))
