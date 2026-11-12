# -*- coding: utf-8 -*-
"""NO.481 导向框 B 版（11-12 更改单）：3420604B01/B02、3420605B01/B02 展开 JSON。

B 版和 A 版的差别：前后半「此面底部 30mm 向内收口 1.5mm」——模型里底部 30 是一块斜 2.86° 的平面，
和主面是尖棱相接（没有折弯圆柱），两侧 R10 折弯区用 B 样条过渡；另外 B02 压边端头的小缺口改成 R≈2 让位圆。
step_unfold2 只认圆柱折弯，会把这条 30 宽的斜带整条丢掉（展开短 30）。做法：
  1. 新 STP 按实体拆开，B01 / B02 照常 step_unfold2（BD 2.3）——压边端头等其它变化都取新模型；
  2. 丢掉的底边带：用 A 版 JSON 同一段轮廓补回（A、B 除这条带外轮廓逐点一致；斜带沿面长 30.04，比 A 长 0.04，忽略）；
  3. 在距底边 30 处加一条收口折弯线（2.86°，非 90° 只画红线），横跨主面到两侧 R10 折弯中线。
用法: python3 -I 481/make_b_json.py <scratch 目录>   （需 OCP；结果写 481/JSON/）"""
import sys, os, json, math, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), 'tools')
TUCK_DEG = math.degrees(math.atan2(1.5, 30))      # 2.86°


def split(step, outdir, want):
    """装配 STP 按实体名拆出 want 里的零件，返回 {名: 单件 step 路径}"""
    from OCP.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    r = STEPControl_Reader(); r.ReadFile(step); r.TransferRoots()
    tr = r.WS().TransferReader()
    e = TopExp_Explorer(r.OneShape(), TopAbs_SOLID); res = {}
    while e.More():
        s = e.Current(); e.Next()
        ent = tr.EntityFromShapeResult(s, 1)
        name = ent.Name().ToCString().split(':')[0] if ent is not None and ent.Name() is not None else '?'
        if name in want and name not in res:
            p = os.path.join(outdir, name + '.step')
            w = STEPControl_Writer(); w.Transfer(s, STEPControl_AsIs); w.Write(p)
            res[name] = p
    assert set(res) == set(want), (step, res.keys())
    return res


def key(q):
    return (round(q[0], 2), round(q[1], 2))


def patch_band(B, A, ymin):
    """B 环里 y > ymin 且 A 环里没有的连续点段，换成 A 环在同两端点之间的那段"""
    lb, la = B['loops'][0], A['loops'][0]
    ia = {key(q): i for i, q in enumerate(la)}
    n = len(lb)
    only = [key(q) not in ia for q in lb]
    start = next(i for i in range(n) if not only[i])       # 从一个公共点开始转一圈
    order = [(start + k) % n for k in range(n)]
    out, k, runs = [], 0, 0
    while k < n:
        i = order[k]
        if only[i]:
            j = k
            while j < n and only[order[j]]:
                j += 1
            run = [lb[order[m]] for m in range(k, j)]
            prev, nxt = lb[order[k - 1]], lb[order[j % n]]
            if min(q[1] for q in run) > ymin:
                a0, a1 = ia[key(prev)], ia[key(nxt)]
                L = len(la)
                fwd = (a1 - a0) % L
                before = ia.get(key(lb[order[k - 2]]))        # 锚点前一个公共点在 A 环里的位置定方向
                if before == (a0 - 1) % L:                    # A 环同向：照抄
                    b0 = la[a0][2]
                    seg = [list(la[(a0 + m) % L]) for m in range(1, fwd)]
                else:                                         # A 环反向：倒着走，bulge 取前一点的相反数
                    back = (a0 - a1) % L
                    b0 = -la[(a0 - 1) % L][2]
                    seg = [list(la[(a0 - m) % L][:2]) + [-la[(a0 - m - 1) % L][2]] for m in range(1, back)]
                out[-1] = list(out[-1][:2]) + [b0]
                out.extend(seg)
                runs += 1
            else:
                out.extend([list(q) for q in run])
            k = j
        else:
            out.append(list(lb[i])); k += 1
    B['loops'][0] = out
    return runs


def bottom_y(lp, ymin):
    """主面底边（收口那条边）在展开上的 y：y > ymin 的水平长边"""
    best = None
    for i, q in enumerate(lp):
        r = lp[(i + 1) % len(lp)]
        if q[1] > ymin and abs(q[1] - r[1]) < 1e-3 and abs(q[0] - r[0]) > 100:
            best = q[1] if best is None else max(best, q[1])
    return best


def add_tuck(J, ymin):
    yb = bottom_y(J['loops'][0], ymin)
    y = yb - 30
    xs = []
    for a, b, deg in J['bend_lines']:
        if abs(deg - 90.6) < 0.3 and min(a[1], b[1]) < y < max(a[1], b[1]):   # 主面两侧 R10 折弯中线
            t = (y - a[1]) / (b[1] - a[1]); xs.append(a[0] + t * (b[0] - a[0]))
    xs.sort()
    x0, x1 = xs[0], xs[-1]
    J['bend_lines'].append([[x0, y], [x1, y], round(TUCK_DEG, 2)])
    J['tuck'] = {'y_edge': yb, 'y_line': y, 'x': [x0, x1], 'deg': round(TUCK_DEG, 2)}
    return J['tuck']


def main():
    tmp = sys.argv[1]
    os.makedirs(tmp, exist_ok=True)
    jdir = os.path.join(HERE, 'JSON')
    jobs = [('3420604B00', '3420604B01', '3400604A01', 400), ('3420604B00', '3420604B02', '3400604A02', 250),
            ('3420605B00', '3420605B01', '3420605A01', 380), ('3420605B00', '3420605B02', '3420605A02', 220)]
    steps = {}
    for asm in sorted({j[0] for j in jobs}):
        steps.update(split(os.path.join(HERE, 'STEP', asm + '.stp'), tmp, [j[1] for j in jobs if j[0] == asm]))
    for asm, name, old, ymin in jobs:
        raw = os.path.join(tmp, name + '.json')
        subprocess.run([sys.executable, '-I', os.path.join(TOOLS, 'step_unfold2.py'), steps[name], raw, '--bd', '2.3'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        B = json.load(open(raw, encoding='utf-8'))
        A = json.load(open(os.path.join(jdir, old + '.json'), encoding='utf-8'))
        runs = patch_band(B, A, ymin)
        t = add_tuck(B, ymin)
        B['source'] = name + '.step（' + asm + '.stp 拆出）；底边 30 收口带按 A 版 ' + old + ' 补回'
        json.dump(B, open(os.path.join(jdir, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        xs = [q[0] for q in B['loops'][0]]; ys = [q[1] for q in B['loops'][0]]
        print(f"{name}: {max(xs)-min(xs):.2f} x {max(ys)-min(ys):.2f}  补回 {runs} 段  收口线 y={t['y_line']:.2f} x {t['x'][0]:.1f}~{t['x'][1]:.1f}")


if __name__ == '__main__':
    main()
