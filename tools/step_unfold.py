# -*- coding: utf-8 -*-
"""STEP 钣金件展开（所有折弯轴线平行、90° 等任意角直线折弯），输出展开轮廓 JSON。

用法（需 OCP / cadquery-ocp）:  python3 tools/step_unfold.py <model.step> <out.json> --bd 8.4 [--solid N]
做法：
  - 折弯 = 同轴的一对圆柱面（内 R、外 R+t）；平板 = 与折弯圆柱面相邻的平面
  - 从一端平板起，沿折弯走一侧表面（同一侧的面、同一侧的圆柱），按外形尺寸法定位：
    相邻两板外表面延长线交点为外模线点 M，跨过折弯 u 减 BD；红线在 M 处 − BD/2
  - 平板上的边（含孔）按刚体映射到 (s, u)：s 沿折弯轴线，u 沿展开方向；折弯区内的边按转角比例映射
  - 所有边串成闭合环；整圆单独输出
输出：loops [[[x, y, bulge], ...]]（x = s，y = u）、circles [[x, y, d]]、bends [[u, s0, s1, 角度]]
"""
import sys, json, math, argparse
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer, TopExp
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Circle


def V(p):
    return (p.X(), p.Y(), p.Z())


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x * k for x in a)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(dot(a, a)); return mul(a, 1 / L)


def load(f, idx=None):
    r = STEPControl_Reader(); r.ReadFile(f); r.TransferRoots(); s = r.OneShape()
    if idx is None:
        return s
    ex = TopExp_Explorer(s, TopAbs_SOLID); i = 0
    while ex.More():
        if i == idx:
            return ex.Current()
        i += 1; ex.Next()
    raise SystemExit('没有第 %d 个实体' % idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step'); ap.add_argument('out')
    ap.add_argument('--bd', type=float, default=0)
    ap.add_argument('--solid', type=int, default=None)
    ap.add_argument('--plate', default=None,
                    help='平板件：取该平面上的面轮廓，nx,ny,nz,d（面上点 p 满足 n·p = d）；写 auto 取最大平面')
    A = ap.parse_args()
    shape = load(A.step, A.solid)

    faces = []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        faces.append(TopoDS.Face(ex.Current())); ex.Next()
    edges, eface, buckets = [], [], {}
    for i, f in enumerate(faces):
        ex = TopExp_Explorer(f, TopAbs_EDGE)
        while ex.More():
            ed = TopoDS.Edge(ex.Current()); h = hash(ed)
            for k in buckets.get(h, []):
                if edges[k].IsSame(ed):
                    if i not in eface[k]:
                        eface[k].append(i)
                    break
            else:
                buckets.setdefault(h, []).append(len(edges)); edges.append(ed); eface.append([i])
            ex.Next()
    fedges = {i: [] for i in range(len(faces))}
    for k, fs in enumerate(eface):
        for f in fs:
            fedges[f].append(k)

    info = {}
    for i, f in enumerate(faces):
        a = BRepAdaptor_Surface(f)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane(); info[i] = ('P', V(pl.Axis().Direction()), V(pl.Location()))
        elif a.GetType() == GeomAbs_Cylinder:
            c = a.Cylinder(); info[i] = ('C', V(c.Axis().Direction()), V(c.Axis().Location()), c.Radius())
        else:
            info[i] = ('?',)
    # SolidWorks 常把一个折弯圆柱面拆成几块：同轴同半径的圆柱面并成一组（以第一块为代表），组内分界缝不算边界
    rep = {}
    cl = [i for i in info if info[i][0] == 'C']
    for i in cl:
        for j in cl:
            if j >= i:
                break
            if rep.get(j, j) != j:
                continue
            di = info[i][1]; w = sub(info[j][2], info[i][2])
            if abs(abs(dot(di, info[j][1])) - 1) < 1e-6 and abs(info[i][3] - info[j][3]) < 1e-6 and \
               math.sqrt(max(dot(cross(w, di), cross(w, di)), 0)) < 1e-4:
                rep[i] = j
                break
    seam = set()
    for k, fs in enumerate(eface):
        r = sorted({rep.get(f, f) for f in fs})
        if len(r) == 1 and len(fs) > 1:
            seam.add(k)
        eface[k] = r
    fedges = {i: [] for i in range(len(faces))}
    for k, fs in enumerate(eface):
        if k in seam:
            continue
        for f in fs:
            fedges[f].append(k)
    for i in list(info):
        if i in rep:
            del info[i]

    # 折弯圆柱：同轴成对，半径差 = t
    cyls = [i for i in info if info[i][0] == 'C']
    bends = []
    used = set()
    for i in cyls:
        for j in cyls:
            if i >= j or i in used or j in used:
                continue
            di, dj = info[i][1], info[j][1]
            if abs(abs(dot(di, dj)) - 1) > 1e-6:
                continue
            w = sub(info[j][2], info[i][2])
            if math.sqrt(max(dot(cross(w, di), cross(w, di)), 0)) > 1e-4:
                continue
            ri, rj = info[i][3], info[j][3]
            nb_i = [g for k in fedges[i] for g in eface[k] if g != i and info[g][0] == 'P'
                    and abs(dot(norm(info[g][1]), norm(di))) < 1e-6]
            nb_j = [g for k in fedges[j] for g in eface[k] if g != j and info[g][0] == 'P'
                    and abs(dot(norm(info[g][1]), norm(di))) < 1e-6]
            if len(set(nb_i)) >= 2 and len(set(nb_j)) >= 2 and abs(ri - rj) > 0.3:
                inner, outer = (i, j) if ri < rj else (j, i)
                bends.append(dict(inner=inner, outer=outer, t=abs(ri - rj)))
                used |= {i, j}
    if A.plate:
        return plate(A, faces, info, fedges, eface, edges)
    if not bends:
        raise SystemExit('没有找到折弯')
    D = norm(info[bends[0]['inner']][1])
    for b in bends:
        assert abs(abs(dot(norm(info[b['inner']][1]), D)) - 1) < 1e-6, '折弯轴线不平行'
    t = bends[0]['t']
    # 截面二维基
    ax = norm(cross(D, (1, 0, 0) if abs(D[0]) < 0.9 else (0, 1, 0)))
    ay = cross(D, ax)
    P2 = lambda p: (dot(p, ax), dot(p, ay))

    def nbr_planes(cf):
        return sorted({g for k in fedges[cf] for g in eface[k] if g != cf and info[g][0] == 'P'
                       and abs(dot(norm(info[g][1]), D)) < 1e-6})

    for b in bends:
        b['in_f'] = nbr_planes(b['inner']); b['out_f'] = nbr_planes(b['outer'])
        assert len(b['in_f']) == 2 and len(b['out_f']) == 2, '折弯相邻平面不是两块：%s' % b

    def plane_key(f):
        n, p = info[f][1], info[f][2]
        n = norm(n)
        if n < (0, 0, 0):
            n = mul(n, -1)
        return (tuple(round(x, 5) for x in n), round(dot(n, p), 3))

    # 平板 = 同一块板的两面（法向相同、相距 t）；以折弯连接关系建链
    flat_of = {}
    flats = []

    def flat_id(f):
        if f in flat_of:
            return flat_of[f]
        flats.append({f}); flat_of[f] = len(flats) - 1
        return flat_of[f]
    for b in bends:
        pairs = []
        for fi in b['in_f']:
            ni = norm(info[fi][1])
            fo = [g for g in b['out_f'] if abs(abs(dot(ni, norm(info[g][1]))) - 1) < 1e-6
                  and abs(abs(dot(ni, sub(info[g][2], info[fi][2]))) - t) < 1e-3]
            assert fo, '找不到与内侧面相对的外侧面'
            k = flat_id(fi)
            if fo[0] in flat_of and flat_of[fo[0]] != k:
                # 合并
                k2 = flat_of[fo[0]]
                flats[k] |= flats[k2]
                for g in flats[k2]:
                    flat_of[g] = k
                flats[k2] = set()
            flats[k].add(fo[0]); flat_of[fo[0]] = k
            pairs.append(k)
        b['flats'] = pairs
    # 链：从只连一个折弯的平板起
    deg = {}
    for b in bends:
        for k in b['flats']:
            deg[k] = deg.get(k, 0) + 1
    start = min(k for k in deg if deg[k] == 1)
    # 选同一侧：起始板取与第一个折弯内侧圆柱相邻的面
    order = [start]; side_face = {}; bend_seq = []
    b0 = next(b for b in bends if start in b['flats'])
    side_face[start] = next(f for f in b0['in_f'] if flat_of[f] == start)
    cur, prevb = start, None
    while True:
        nb = [b for b in bends if cur in b['flats'] and b is not prevb]
        if not nb:
            break
        b = nb[0]
        f_cur = side_face[cur]
        cyl = b['inner'] if f_cur in b['in_f'] else b['outer']
        side_f = b['in_f'] if cyl == b['inner'] else b['out_f']
        nxt = next(k for k in b['flats'] if k != cur)
        side_face[nxt] = next(f for f in side_f if flat_of[f] == nxt)
        bend_seq.append((b, cur, nxt, cyl))
        order.append(nxt); cur, prevb = nxt, b

    # 平板方向与外模线点
    def line2d(f):
        n = norm(info[f][1]); p = info[f][2]
        n2 = norm(P2(n)); return n2, dot(n2, P2(p))

    def inter(l1, l2):
        (n1, d1), (n2, d2) = l1, l2
        det = n1[0] * n2[1] - n1[1] * n2[0]
        return ((d1 * n2[1] - d2 * n1[1]) / det, (n1[0] * d2 - n2[0] * d1) / det)
    Ms = []
    for b, i, j, cyl in bend_seq:
        fo_i = next(f for f in b['out_f'] if flat_of[f] == i)
        fo_j = next(f for f in b['out_f'] if flat_of[f] == j)
        Ms.append(inter(line2d(fo_i), line2d(fo_j)))
    e = {}; Aoff = {}
    for idx, k in enumerate(order):
        n2, _ = line2d(side_face[k])
        d = (-n2[1], n2[0])
        if idx < len(Ms):
            ref = sub(Ms[idx], Ms[idx - 1]) if idx > 0 else None
        if idx == 0:
            # 指向第一个折弯：取板上任一点到 M0 的方向
            c = P2(face_point(faces[side_face[k]]))
            ref = sub(Ms[0], c)
        elif idx == len(order) - 1:
            c = P2(face_point(faces[side_face[k]]))
            ref = sub(c, Ms[-1])
        if dot(d, ref) < 0:
            d = (-d[0], -d[1])
        e[k] = d
    Aoff[order[0]] = 0.0
    redu = []
    for (b, i, j, cyl), M in zip(bend_seq, Ms):
        Aoff[j] = Aoff[i] + dot(M, e[i]) - A.bd - dot(M, e[j])
        redu.append(Aoff[i] + dot(M, e[i]) - A.bd / 2)

    def U(p3, k):
        return Aoff[k] + dot(P2(p3), e[k])

    # 折弯区映射：按绕轴转角在两切线 u 之间插值
    bend_map = {}
    for (b, i, j, cyl), ru in zip(bend_seq, redu):
        c3 = info[cyl][2]
        tang = {}
        for kk in fedges[cyl]:
            others = [g for g in eface[kk] if g != cyl]
            if others and others[0] in (side_face[i], side_face[j]):
                cc = BRepAdaptor_Curve(edges[kk])
                tang[others[0]] = V(cc.Value((cc.FirstParameter() + cc.LastParameter()) / 2))
        pi, pj = tang[side_face[i]], tang[side_face[j]]
        cc2 = P2(c3)
        ang = lambda p, c=cc2: math.atan2(P2(p)[1] - c[1], P2(p)[0] - c[0])
        a0, a1 = ang(pi), ang(pj)
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        bend_map[cyl] = (a0, sweep, U(pi, i), U(pj, j), ang)
        b['deg'] = abs(math.degrees(sweep))

    def M3(p, face):
        s = dot(p, D)
        if face in bend_map:
            a0, sw, u0, u1, ang = bend_map[face]
            f = ((ang(p) - a0 + math.pi) % (2 * math.pi) - math.pi) / sw
            return (s, u0 + f * (u1 - u0))
        return (s, U(p, flat_of[face]))

    sel = set(side_face.values()) | {cyl for _, _, _, cyl in bend_seq}
    segs, circles = [], []
    for f in sel:
        for kk in fedges[f]:
            if any(g in sel and g != f for g in eface[kk]):
                continue                                # 板与折弯区的切线
            cc = BRepAdaptor_Curve(edges[kk])
            t0, t1 = cc.FirstParameter(), cc.LastParameter()
            if cc.GetType() == GeomAbs_Line:
                segs.append((M3(V(cc.Value(t0)), f), M3(V(cc.Value(t1)), f), 0.0))
            elif cc.GetType() == GeomAbs_Circle and f not in bend_map:
                if abs(t1 - t0 - 2 * math.pi) < 1e-6:
                    c = M3(V(cc.Circle().Location()), f)
                    circles.append((c[0], c[1], 2 * cc.Circle().Radius()))
                    continue
                p0, pm, p1 = (M3(V(cc.Value(x)), f) for x in (t0, (t0 + t1) / 2, t1))
                chord = math.dist(p0, p1)
                crs = (pm[0] - p0[0]) * (p1[1] - p0[1]) - (pm[1] - p0[1]) * (p1[0] - p0[0])
                sweep = t1 - t0
                bul = math.tan(sweep / 4) * (1 if crs > 0 else -1)
                segs.append((p0, p1, bul))
            else:
                n = 24
                pts = [M3(V(cc.Value(t0 + (t1 - t0) * q / n)), f) for q in range(n + 1)]
                for a, b2 in zip(pts, pts[1:]):
                    segs.append((a, b2, 0.0))
    return finish(A, segs, circles, bend_seq_out(bend_seq, redu, fedges, edges, D), t)


def bend_seq_out(bend_seq, redu, fedges, edges, D):
    bl = []
    for (b, i, j, cyl), ru in zip(bend_seq, redu):
        ss = []
        for kk in fedges[cyl]:
            c = BRepAdaptor_Curve(edges[kk])
            ss += [dot(V(c.Value(c.FirstParameter())), D), dot(V(c.Value(c.LastParameter())), D)]
        bl.append([ru, min(ss), max(ss), round(b['deg'], 2)])
    return bl


def finish(A, segs, circles, bends, t):
    # 串环
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    pool = [s for s in segs if math.dist(s[0], s[1]) > 1e-6]
    loops = []
    while pool:
        a, b2, bu = pool.pop()
        loop = [[a[0], a[1], bu]]; cur = b2; start = key(a)
        while key(cur) != start:
            for q, (x, y, bb) in enumerate(pool):
                if key(x) == key(cur):
                    loop.append([cur[0], cur[1], bb]); cur = y; pool.pop(q); break
                if key(y) == key(cur):
                    loop.append([cur[0], cur[1], -bb]); cur = x; pool.pop(q); break
            else:
                raise SystemExit('轮廓不闭合，断点 %s' % (key(cur),))
        loops.append(loop)
    # 去共线点
    def simp(lp):
        out = []
        n = len(lp)
        for q in range(n):
            a, b2, c = lp[q - 1], lp[q], lp[(q + 1) % n]
            if abs(a[2]) < 1e-9 and abs(b2[2]) < 1e-9 and \
               abs((b2[0] - a[0]) * (c[1] - b2[1]) - (b2[1] - a[1]) * (c[0] - b2[0])) < 1e-6:
                continue
            out.append([round(v, 4) for v in b2])
        return out
    loops = [simp(l) for l in loops]
    allp = [p for l in loops for p in l] + [[c[0], c[1]] for c in circles]
    x0 = min(p[0] for p in allp); y0 = min(p[1] for p in allp)
    loops = [[[p[0] - x0, p[1] - y0, p[2]] for p in l] for l in loops]
    circles = [[c[0] - x0, c[1] - y0, c[2]] for c in circles]
    bl = [[u - y0, s0 - x0, s1 - x0, deg] for u, s0, s1, deg in bends]
    W = max(p[0] for p in allp) - x0; H = max(p[1] for p in allp) - y0
    json.dump(dict(source=A.step.split('/')[-1], t=round(t, 3), bd=A.bd, size=[round(W, 3), round(H, 3)],
                   loops=loops, circles=circles, bends=bl), open(A.out, 'w'), ensure_ascii=False, indent=1)
    print('t=%.2f 展开 %.2f × %.2f，环 %d（最大 %d 点），整圆 %d，折弯 %s' %
          (t, W, H, len(loops), max(len(l) for l in loops), len(circles),
           [(round(b[0], 2), b[3]) for b in bl]))


def plate(A, faces, info, fedges, eface, edges):
    """平板件：所选平面上的面（可多块）的全部边投影到该平面二维坐标"""
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    planes = [i for i in info if info[i][0] == 'P']
    if A.plate == 'auto':
        def area(i):
            g = GProp_GProps(); BRepGProp.SurfaceProperties_s(faces[i], g); return g.Mass()
        f0 = max(planes, key=area)
        n = norm(info[f0][1]); d = dot(n, info[f0][2])
    else:
        v = [float(x) for x in A.plate.split(',')]
        n = norm(tuple(v[:3])); d = v[3]
    sel = [i for i in planes if abs(abs(dot(norm(info[i][1]), n)) - 1) < 1e-6 and abs(dot(n, info[i][2]) - d) < 1e-4]
    if not sel:
        raise SystemExit('该平面上没有面')
    ax = norm(cross(n, (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0))); ay = cross(n, ax)
    M = lambda p: (dot(p, ax), dot(p, ay))
    segs, circles = [], []
    for f in sel:
        for kk in fedges[f]:
            if all(g in sel for g in eface[kk]):
                continue
            cc = BRepAdaptor_Curve(edges[kk]); t0, t1 = cc.FirstParameter(), cc.LastParameter()
            if cc.GetType() == GeomAbs_Line:
                segs.append((M(V(cc.Value(t0))), M(V(cc.Value(t1))), 0.0))
            elif cc.GetType() == GeomAbs_Circle:
                if abs(t1 - t0 - 2 * math.pi) < 1e-6:
                    c = M(V(cc.Circle().Location())); circles.append((c[0], c[1], 2 * cc.Circle().Radius())); continue
                p0, pm, p1 = (M(V(cc.Value(x))) for x in (t0, (t0 + t1) / 2, t1))
                crs = (pm[0] - p0[0]) * (p1[1] - p0[1]) - (pm[1] - p0[1]) * (p1[0] - p0[0])
                segs.append((p0, p1, math.tan((t1 - t0) / 4) * (1 if crs > 0 else -1)))
            else:
                pts = [M(V(cc.Value(t0 + (t1 - t0) * q / 24))) for q in range(25)]
                segs += [(a, b, 0.0) for a, b in zip(pts, pts[1:])]
    return finish(A, segs, circles, [], 0.0)


def face_point(f):
    a = BRepAdaptor_Surface(f)
    u = (a.FirstUParameter() + a.LastUParameter()) / 2; v = (a.FirstVParameter() + a.LastVParameter()) / 2
    return V(a.Value(u, v))


if __name__ == '__main__':
    main()
