# -*- coding: utf-8 -*-
"""STEP 装配体 → 蓝探科风格 A4 横向装配图（DXF + PDF + PNG）

用法: python3 tools/drawing/make_drawing.py <model.step> <输出前缀>

风格取自蓝探科 Inventor 出图（tools/drawing/蓝探科_A4横向样板.dxf 为从其图纸提取的原图框/标题栏块）：
- 图框“图框 最新国标”、标题栏“标题栏 最新国标”（含未注公差表、UNIT: mm、第一角投影符号），属性填零件代号/名称/材料/比例/质量/设计人
- 图层同其 ISO 模板：可见 (ISO) 黑、隐藏 (ISO) 蓝虚线、中心线 (ISO) 红点划线、尺寸/符号 (ISO) 绿色，仿宋字体
- 第一角投影：主视图、俯视图（下）、左视图（右），另加向视图与轴测图；明细栏在标题栏上方，表头在下（序号/代号/库存编号/数量/材料/备注）
- 技术要求绿色文字写在标题栏上方
"""
import os, sys, math
import ezdxf
from ezdxf.enums import TextEntityAlignment
import cadquery as cq
sys.path.insert(0, os.path.dirname(__file__))
from hlr import project

TPL = os.path.join(os.path.dirname(__file__), '蓝探科_A4横向样板.dxf')

INFO = dict(code='BJ-ZFG-CHT-028', name='组装 SiCl4烘箱', designer='ZWK', scale='1 : 10',
            note='SiCl4&GeCl4蒸发柜壳  YW-260233-1  2026-ZXKJ-018-01')
PARTS = [  # 序号, 代号, 库存编号(名称), 数量, 材料（与 STEP 装配顺序一致）
    (1, 'BJ-ZFG-CHT-028-01', '箱体', 1, 'SUS304'),
    (2, 'BJ-ZFG-CHT-028-02', '内顶板', 1, 'SUS304'),
    (3, 'BJ-ZFG-CHT-028-03', '内底板', 1, 'SUS304'),
]
TECH = ['技术要求：',
        '1. 飞边去毛刺；',
        '2. 未注倒角C0.5；',
        '3. 304镜面板T=2，保护镜面不得划伤；',
        '4. 装配后去除保护膜；',
        '5. 项目：SiCl4&GeCl4蒸发柜壳',
        '   YW-260233-1  2026-ZXKJ-018-01。']

K = 0.1                                   # 1:10
GREEN = 3
FONT = '最新国标'                          # 样板中的仿宋字体样式

V_FRONT = ((0, 0, 1), (1, 0, 0))          # 主视图（+Z 为箱体开口）
V_TOP = ((0, 1, 0), (1, 0, 0))            # 俯视图（第一角：主视图下方）
V_LEFT = ((-1, 0, 0), (0, 0, 1))          # 左视图（第一角：主视图右方）
V_BOTTOM = ((0, -1, 0), (1, 0, 0))        # A 向视图（自下向上）
V_ISO = ((1, 1, 1), (1, 0, -1))           # 轴测图


def text(msp, s, x, y, h=2.8, align='BL', color=GREEN, layer='符号 (ISO)'):
    al = {'BL': TextEntityAlignment.BOTTOM_LEFT, 'MC': TextEntityAlignment.MIDDLE_CENTER,
          'BC': TextEntityAlignment.BOTTOM_CENTER, 'ML': TextEntityAlignment.MIDDLE_LEFT}[align]
    t = msp.add_text(s, height=h, dxfattribs=dict(style=FONT, layer=layer, color=color))
    t.set_placement((x, y), align=al)
    return t


def line(msp, a, b, layer, color=None):
    att = dict(layer=layer)
    if color is not None:
        att['color'] = color
    msp.add_line(a, b, dxfattribs=att)


def place_view(msp, shape, view, cx, cy, hidden=False):
    """薄板装配图不画虚线（板厚两侧的不可见边会糊满视图）"""
    vis, hid = project(shape, view)
    pts = [p for pl in vis for p in pl]
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    T = lambda x, y: (cx + (x - mx) * K, cy + (y - my) * K)
    for pl in vis:
        msp.add_lwpolyline([T(*p) for p in pl], dxfattribs=dict(layer='可见 (ISO)', lineweight=35))
    if hidden:
        for pl in hid:
            msp.add_lwpolyline([T(*p) for p in pl], dxfattribs=dict(layer='隐藏 (ISO)', ltscale=0.3))
    n, vx = view
    vy = (n[1] * vx[2] - n[2] * vx[1], n[2] * vx[0] - n[0] * vx[2], n[0] * vx[1] - n[1] * vx[0])
    nx = math.sqrt(sum(c * c for c in vx)); vxn = [c / nx for c in vx]
    ny = math.sqrt(sum(c * c for c in vy)); vyn = [c / ny for c in vy]

    def T2(*q):
        if len(q) == 3:
            q = (sum(a * b for a, b in zip(q, vxn)), sum(a * b for a, b in zip(q, vyn)))
        return T(*q)
    return T2, (*T(x0, y0), *T(x1, y1))


def center_cross(msp, c, r):
    x, y = c
    e = r + 1.5
    line(msp, (x - e, y), (x + e, y), '中心线 (ISO)')
    line(msp, (x, y - e), (x, y + e), '中心线 (ISO)')


def dim(msp, p1, p2, base, angle):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle='LT',
                           dxfattribs=dict(layer='尺寸 (ISO)'))
    d.render()


def leader_note(msp, tip, end, s):
    msp.add_circle(tip, 0.4, dxfattribs=dict(layer='符号 (ISO)', color=GREEN))
    line(msp, tip, end, '符号 (ISO)', GREEN)
    w = len(s) * 2.0
    line(msp, end, (end[0] + w, end[1]), '符号 (ISO)', GREEN)
    text(msp, s, end[0] + 0.5, end[1] + 0.6)


def balloon(msp, tip, c, n):
    msp.add_circle(tip, 0.5, dxfattribs=dict(layer='符号 (ISO)', color=GREEN))
    dx, dy = tip[0] - c[0], tip[1] - c[1]; L = math.hypot(dx, dy)
    line(msp, tip, (c[0] + dx / L * 3.5, c[1] + dy / L * 3.5), '符号 (ISO)', GREEN)
    msp.add_circle(c, 3.5, dxfattribs=dict(layer='符号 (ISO)', color=GREEN))
    text(msp, str(n), c[0], c[1], 3.5, 'MC')


def bom(msp, masses):
    """明细栏（同蓝探科样式）：行高 4.5，列宽 8, 25.4, 25.4, 8, 18, 18；表头在最下，序号自下而上"""
    cols = [8, 25.4, 25.4, 8, 18, 18]
    x1 = 290.0; x0 = x1 - sum(cols)
    y0 = 47.0; h = 4.5
    xs = [x0]
    for c in cols:
        xs.append(xs[-1] + c)
    n = len(PARTS)
    for i in range(n + 2):
        line(msp, (x0, y0 + i * h), (x1, y0 + i * h), '符号 (ISO)', GREEN)
    for xx in xs:
        line(msp, (xx, y0), (xx, y0 + h * (n + 1)), '符号 (ISO)', GREEN)
    for s, a, b in zip(['序号', '代号', '库存编号', '数量', '材料', '备注'], xs, xs[1:]):
        text(msp, s, (a + b) / 2, y0 + h / 2, 2.0, 'MC')
    for i, (no, code, name, q, mat) in enumerate(PARTS):
        yy = y0 + h * (i + 1) + h / 2
        for s, a, b in zip([str(no), code, name, str(q), mat, '镜面板 T=2'], xs, xs[1:]):
            t = text(msp, s, (a + b) / 2, yy, 2.0, 'MC')
            if s == code:
                t.dxf.width = 0.85                         # 代号较长，压缩字宽避免顶格
    return y0 + h * (n + 1)


def build(step, out):
    asm = cq.importers.importStep(step)
    shape = asm.val().wrapped
    masses = [s.Volume() * 7.93e-6 for s in asm.solids().vals()]
    doc = ezdxf.readfile(TPL)
    msp = doc.modelspace()
    ds = doc.dimstyles.new('LT')                           # 同其“默认 (GB)”：字高 2.8、箭头 2.5、绿色
    for k, v in dict(dimtxt=2.8, dimasz=2.5, dimexe=1.5, dimexo=0.8, dimgap=0.8, dimtxsty=FONT, dimlfac=1 / K,
                     dimdec=0, dimtad=1, dimtih=0, dimtoh=0, dimclrd=GREEN, dimclre=GREEN, dimclrt=GREEN).items():
        ds.dxf.set(k, v)

    # 标题栏 / 图框属性
    for ins in msp.query('INSERT'):
        for a in ins.attribs:
            tag = a.dxf.tag.split('_')[0]
            a.dxf.text = {'零件代号': INFO['code'], '库存编号': INFO['name'], '质量\\P3;': '%.1f kg' % sum(masses),
                          '视图比例': INFO['scale'], '设计人': INFO['designer'], '材料': ''}.get(tag, a.dxf.text)
            if tag == '零件代号' and ins.dxf.name == '标题栏 最新国标':
                a.dxf.width = 0.75                         # 代号比样板长，压缩字宽放进格内
    bom(msp, masses)

    # 视图（1:10，长对正、高平齐、宽相等）
    Tf, bf = place_view(msp, shape, V_FRONT, 62, 136)
    Tt, bt = place_view(msp, shape, V_TOP, 62, bf[1] - 17 - 20)
    Tl, bl = place_view(msp, shape, V_LEFT, bf[2] + 14 + 20, 136)
    Tb, bb = place_view(msp, shape, V_BOTTOM, 168, 146)
    Ti, bi = place_view(msp, shape, V_ISO, 247, 128, hidden=False)

    for (x0, y0, x1, y1) in (bf, bt, bb):                  # 对称中心线
        cx = (x0 + x1) / 2
        line(msp, (cx, y0 - 2.5), (cx, y1 + 2.5), '中心线 (ISO)')
    for (x0, y0, x1, y1) in (bf, bl):
        cy = (y0 + y1) / 2
        line(msp, (x0 - 2.5, cy), (x1 + 2.5, cy), '中心线 (ISO)')

    top_ports = [(-98, 30), (107, 30)]                       # 内顶板 2-Φ40
    bot40 = [(-158, 90), (-158, 150), (-158, 210), (107, 30)]  # 内底板 4-Φ40
    bot42 = [(-63, 40), (7, 40)]                             # 内底板 2-Φ42
    for x, z in top_ports:
        center_cross(msp, Tt(x, -z), 2.0)
    for x, z in bot40 + bot42:
        center_cross(msp, Tb(x, z), 2.0)

    # 尺寸
    dim(msp, Tf(-190, 360), Tf(190, 360), (0, bf[3] + 10), 0)
    dim(msp, Tf(-160, 330), Tf(160, 330), (0, bf[3] + 4.5), 0)
    dim(msp, Tf(-190, -360), Tf(-190, 360), (bf[0] - 10, 0), 90)
    dim(msp, Tf(-160, -330), Tf(-160, 330), (bf[0] - 4.5, 0), 90)
    dim(msp, (bl[0], bl[3]), (bl[2], bl[3]), (0, bl[3] + 4.5), 0)
    # 俯视图：内顶板工艺口定位（左边、后面）
    dim(msp, Tt(-190, 2), Tt(-98, -30), (0, bt[3] + 5), 0)            # 尺寸放在视图上方，尺寸界线不穿过视图
    dim(msp, Tt(-98, -30), Tt(107, -30), (0, bt[3] + 5), 0)
    dim(msp, Tt(190, 2), Tt(107, -30), (bt[2] + 5, 0), 90)
    leader_note(msp, Tt(107 + 14, -30 - 14), (bt[2] + 3, bt[3] - 22), '2-Φ40')
    # A 向视图：内底板工艺口
    leader_note(msp, Tb(-158 + 14, 90 - 14), (bb[0] + 4, bb[1] - 6), '4-Φ40')
    leader_note(msp, Tb(7 + 15, 40 - 15), (bb[0] + 24, bb[1] - 12), '2-Φ42')
    # 向视图标注
    text(msp, 'A', (bb[0] + bb[2]) / 2, bb[3] + 2.5, 3.5, 'BC')
    ax_ = bf[2] - 6
    tip = (ax_, bf[1] - 1.5)
    line(msp, (ax_, tip[1] - 9), tip, '符号 (ISO)', GREEN)
    msp.add_solid([(ax_ - 1, tip[1] - 3.5), (ax_ + 1, tip[1] - 3.5), tip, tip], dxfattribs=dict(layer='符号 (ISO)', color=GREEN))
    text(msp, 'A', ax_ + 1.5, tip[1] - 9, 3.5)

    # 序号
    balloon(msp, Ti(190, 120, 250), (bi[2] + 6, (bi[1] + bi[3]) / 2), 1)
    balloon(msp, Ti(0, 345, 150), (bi[2] + 6, bi[3] - 6), 2)
    balloon(msp, Ti(60, -345, 330), (bi[2] + 6, bi[1] + 10), 3)

    # 技术要求
    for i, s in enumerate(TECH):
        text(msp, s, 112, 92 - i * 4.6, 3.5 if i == 0 else 2.8)
    doc.saveas(out + '.dxf')


def render(dxf, out):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, LineweightPolicy
    doc = ezdxf.readfile(dxf)
    import re
    for st in doc.styles:
        st.dxf.font = 'wqy-zenhei.ttc'                    # 仅渲染用（PDF 预览）：统一中文字体
    for blk in doc.blocks:                                # 去掉 MTEXT 内联字体代码，避免中文缺字
        for e in blk:
            if e.dxftype() == 'MTEXT':
                e.text = re.sub(r'\\f[^;]*;', '', e.text)
    fig = plt.figure(figsize=(297 / 25.4, 210 / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, lineweight_policy=LineweightPolicy.ABSOLUTE)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
    ax.set_xlim(0, 297); ax.set_ylim(0, 210); ax.axis('off')
    fig.savefig(out + '.pdf'); fig.savefig(out + '.png', dpi=220)


if __name__ == '__main__':
    step, out = sys.argv[1], sys.argv[2]
    build(step, out)
    render(out + '.dxf', out)
    print('saved', out + '.dxf / .pdf / .png')
