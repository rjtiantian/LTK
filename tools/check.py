# -*- coding: utf-8 -*-
"""自检：python3 tools/check.py <订单> [物料号,物料号 输出.png]
1) 所有零件：重复线 / 未闭合端点 / 重复圆弧
2) 给出物料号时，渲染这些零件的展开图到 PNG 便于目检（标题含外形尺寸、孔径统计）"""
import os, sys, math, collections
sys.path.insert(0, os.path.dirname(__file__))
from gen_order import load
from qalib import dups, ends, arcs_dup


def qa(C, codes=None):
    bad = 0
    for code in sorted(codes or C.PARTS):
        res = C.PARTS[code](1)
        if isinstance(res, tuple):
            continue
        for i, (l, p) in enumerate(res):
            d, e, a = dups(p), ends(p), arcs_dup(p)
            if d or e or a:
                bad += 1
                print('QA', code, i, l, 'dup', len(d), d[:2], 'open', len(e), e[:4], 'arc', len(a), a[:2])
    print('QA 有问题的件数:', bad)


def render(C, codes, out):
    import ezdxf
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    items = []
    for c in codes:
        res = C.PARTS[c](1)
        if isinstance(res, tuple):
            print(c, 'TODO', res[2]); continue
        items += [(c + ' ' + l, p) for l, p in res]
    n = len(items); cols = min(n, 2); rows = math.ceil(n / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(9 * cols, 6 * rows), squeeze=False)
    for ax in axs.ravel():
        ax.axis('off')
    for ax, (t, p) in zip(axs.ravel(), items):
        p = p.normalized()
        doc = ezdxf.new(); doc.layers.add('折弯线'); doc.layers.add('可见 (ISO)')
        p.draw(doc.modelspace(), 0, 0)
        for e in doc.modelspace():
            if e.dxf.color in (256, 7):
                e.dxf.color = 250
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace())
        b = p.bbox()
        holes = collections.Counter(round(2 * d[1], 2) for k, d, a in p.ents if k == 'CIRCLE')
        ax.set_title('%s  %.2f x %.2f\n孔 %s' % (t, b[2] - b[0], b[3] - b[1], dict(holes)), fontsize=9,
                     family='WenQuanYi Zen Hei')
        ax.axis('on'); ax.grid(True, lw=0.3, color='gray')
    fig.tight_layout(); fig.savefig(out, dpi=80)
    print('render ->', out)


if __name__ == '__main__':
    C, _, _ = load(sys.argv[1])
    if len(sys.argv) > 3:
        codes = sys.argv[2].split(',')
        qa(C, codes)
        render(C, codes, sys.argv[3])
    else:
        qa(C)
