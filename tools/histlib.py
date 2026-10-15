# -*- coding: utf-8 -*-
"""历史人工下料图（历史图纸/LTK历史图纸.zip）复用：按物料号取出人工画好的展开件。

首次使用会解压并缓存为 历史图纸/hist_cache.pkl（只含几何与文字，约数十 MB，不入库）。
hist_pieces(code, pick=None) -> [(label, Piece)]，标签为人工写的绿色文字，件数需调用方按本单重写。
"""
import os, re, math, pickle, zipfile, bisect, collections
import ezdxf
from sheetlib import Piece, CUT, BEND

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDIR = os.path.join(ROOT, '历史图纸')
CACHE = os.path.join(HDIR, 'hist_cache.pkl')


def _bb(t, p):
    if p is None:
        return None
    if t == 'LINE':
        return (min(p[0][0], p[1][0]), min(p[0][1], p[1][1]), max(p[0][0], p[1][0]), max(p[0][1], p[1][1]))
    if t in ('CIRCLE', 'ARC'):
        c, r = p[0], p[1]
        return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
    if t == 'LWPOLYLINE':
        xs = [q[0] for q in p[0]]; ys = [q[1] for q in p[0]]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None
    if t == 'TEXT':
        x, y = p[0]
        return (x, y, x + len(p[1]) * p[2] * 0.8, y + p[2])
    if t == 'ELLIPSE':
        c = p[0]; r = math.hypot(*p[1])
        return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
    if t == 'SPLINE':
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None
    return None


def _load():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    z = zipfile.ZipFile(os.path.join(HDIR, 'LTK历史图纸.zip'))
    name = [n for n in z.namelist() if n.lower().endswith('.dxf')][0]
    tmp = os.path.join(HDIR, '_hist.dxf')
    open(tmp, 'wb').write(z.read(name))
    doc = ezdxf.readfile(tmp)
    lay = {l.dxf.name: (l.dxf.get('color'), l.dxf.get('linetype')) for l in doc.layers}
    ents = []
    for e in doc.modelspace():
        t = e.dxftype()
        d = dict(t=t, l=e.dxf.layer, c=e.dxf.get('color', 256), lt=e.dxf.get('linetype', 'BYLAYER'))
        try:
            if t == 'LINE':
                d['p'] = (tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2])
            elif t == 'CIRCLE':
                d['p'] = (tuple(e.dxf.center)[:2], e.dxf.radius)
            elif t == 'ARC':
                d['p'] = (tuple(e.dxf.center)[:2], e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)
            elif t == 'LWPOLYLINE':
                d['p'] = ([tuple(x) for x in e.get_points('xyb')], e.closed)
            elif t == 'TEXT':
                d['p'] = (tuple(e.dxf.insert)[:2], e.dxf.text, e.dxf.height)
            elif t in ('ELLIPSE', 'SPLINE'):
                d['t'] = 'SPLINE'
                d['p'] = [(v.x, v.y) for v in e.flattening(0.01)]
            else:
                continue
        except Exception:
            continue
        d['bb'] = _bb(d['t'], d['p'])
        ents.append(d)
    os.remove(tmp)
    data = dict(ents=ents, layers=lay, parts=_group(ents))
    pickle.dump(data, open(CACHE, 'wb'))
    return data


def _group(E):
    """按黄色表头分列：表头所在行按表头中点分界，表头上方的图元归该列"""
    H = [i for i, e in enumerate(E) if e['t'] == 'TEXT' and e['c'] == 2 and '·' in e['p'][1] and abs(e['p'][2] - 30) < 1]
    rows = collections.defaultdict(list)
    for i in H:
        rows[round(E[i]['p'][0][1] / 50)].append(i)
    byy = collections.defaultdict(list)
    for ids in rows.values():
        ids.sort(key=lambda i: E[i]['p'][0][0])
        cs = [E[i]['p'][0][0] + len(E[i]['p'][1]) * 30 * 0.7 / 2 for i in ids]
        for j, i in enumerate(ids):
            x0 = (cs[j - 1] + cs[j]) / 2 if j > 0 else cs[j] - 3000
            x1 = (cs[j] + cs[j + 1]) / 2 if j < len(ids) - 1 else cs[j] + 3000
            byy[E[i]['p'][0][1]].append((x0, x1, i))
    ys = sorted(byy)
    parts = collections.defaultdict(list)
    hs = set(H)
    for idx, e in enumerate(E):
        if not e['bb'] or idx in hs:
            continue
        cx = (e['bb'][0] + e['bb'][2]) / 2
        y = e['bb'][1]
        k = bisect.bisect_right(ys, y) - 1
        while k >= 0 and y - ys[k] < 8000:
            hit = [c[2] for c in byy[ys[k]] if c[0] <= cx < c[1]]
            if hit:
                parts[hit[0]].append(idx)
                break
            k -= 1
    return [dict(h=E[h]['p'][1], ids=ids) for h, ids in parts.items()]


_DATA = None


def headers(code):
    global _DATA
    _DATA = _DATA or _load()
    return [p['h'] for p in _DATA['parts'] if '·' + code + '·' in p['h']]


def hist_pieces(code, pick=None):
    """取历史中该物料号的人工展开件；pick 为表头中需包含的字符串（如 'NO.373'）以选定某次下料"""
    global _DATA
    _DATA = _DATA or _load()
    E, LY = _DATA['ents'], _DATA['layers']
    cand = [p for p in _DATA['parts'] if '·' + code + '·' in p['h'] and (pick is None or pick in p['h'])]
    if not cand:
        return []
    p = cand[0]
    es = [E[i] for i in p['ids']]
    labs = sorted([e for e in es if e['t'] == 'TEXT' and e['c'] == 3 and re.search(r'\d+件', e['p'][1])],
                  key=lambda e: e['p'][0][1])
    geo = [e for e in es if e['t'] != 'TEXT' and e['bb']]
    out = []
    for k, l in enumerate(labs):
        y0 = l['p'][0][1]
        y1 = labs[k + 1]['p'][0][1] if k + 1 < len(labs) else 1e18
        sub = [e for e in geo if e['bb'][1] > y0 and e['bb'][3] < y1]
        out.append((l['p'][1], _to_piece(sub, LY)))
    return out


def _color(e, LY):
    return e['c'] if e['c'] != 256 else LY.get(e['l'], (7,))[0]


def _to_piece(sub, LY):
    pc = Piece()
    for e in sub:
        t, p = e['t'], e['p']
        lt = e['lt'] if e['lt'] != 'BYLAYER' else LY.get(e['l'], (7, 'Continuous'))[1]
        col = _color(e, LY)
        bend = lt == 'CENTER' or e['l'] == '折弯线'
        if bend:
            pts = [p[0], p[1]] if t == 'LINE' else ([q[:2] for q in p[0]] if t == 'LWPOLYLINE' else None)
            if not pts:
                continue
            if col == 1:
                pc.poly(pts, False, BEND, linetype='CENTER', color=1, ltscale=0.5)
            else:
                pc.poly(pts, False, BEND, linetype='CENTER', color=5)
            continue
        if t == 'LINE':
            pc.line(*p[0], *p[1])
        elif t == 'CIRCLE':
            pc.circle(p[0][0], p[0][1], 2 * p[1])
        elif t == 'ARC':
            pc.arc(p[0][0], p[0][1], p[1], p[2], p[3])
        elif t == 'LWPOLYLINE':
            pc.poly([tuple(q[:2]) + ((q[2] if len(q) > 2 else 0),) for q in p[0]], p[1])
        elif t == 'SPLINE':
            pc.poly(p, False)
    return pc
