# -*- coding: utf-8 -*-
"""STEP 钣金展开（任意方向直线折弯，按折弯树展开），输出与 step_unfold.py 相同格式的 JSON。

用法（需 OCP）:  python3 tools/step_unfold2.py <model.step> <out.json> --bd 2.3 [--root auto]
做法：
  - 折弯 = 同轴的一对圆柱面（内 R、外 R+t，SolidWorks 拆开的同轴同半径圆柱面并成一组）；平板 = 与折弯相邻、法向垂直于轴线的平面
  - 以面积最大的平板为根，沿折弯树逐块展开；每块板取同一侧表面（跨折弯时随圆柱换到相连的面）
  - 外形尺寸法：子板上一点 p，以外模线点 M、轴向 D、子板内离开折弯的方向 e_c 计：
      F_c(p) = F_p(M) + ((p−M)·D)·F_p(D) + ((p−M)·e_c − BD)·F_p(e_p)
    红线 = F_p(M) − BD/2·F_p(e_p)；折弯区内的边按绕轴转角在两条切线的展开位置之间插值
"""
import sys, json, math, argparse
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Circle
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

V = lambda p: (p.X(), p.Y(), p.Z())
dot = lambda a, b: sum(x * y for x, y in zip(a, b))
sub = lambda a, b: tuple(x - y for x, y in zip(a, b))
add = lambda a, b: tuple(x + y for x, y in zip(a, b))
mul = lambda a, k: tuple(x * k for x in a)
cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(dot(a, a)); return mul(a, 1 / L)


def solve3(A, b):
    """3×3 线性方程（克拉默法则）"""
    det = lambda m: (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                     + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    d = det(A); out = []
    for i in range(3):
        m = [list(r) for r in A]
        for k in range(3):
            m[k][i] = b[k]
        out.append(det(m) / d)
    return tuple(out)


class Map:
    """平板展开映射：F(p) = C + (a·(p−O), b·(p−O))，a、b 为三维向量（不一定落在板面内）"""
    def __init__(self, O, a, b, C):
        self.O, self.a, self.b, self.C = O, a, b, C

    def __call__(self, p):
        d = sub(p, self.O); return (self.C[0] + dot(self.a, d), self.C[1] + dot(self.b, d))

    def vec(self, v):
        return (dot(self.a, v), dot(self.b, v))


def face_point(f):
    a = BRepAdaptor_Surface(f)
    return V(a.Value((a.FirstUParameter() + a.LastUParameter()) / 2, (a.FirstVParameter() + a.LastVParameter()) / 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step'); ap.add_argument('out')
    ap.add_argument('--bd', type=float, required=True)
    A = ap.parse_args()
    r = STEPControl_Reader(); r.ReadFile(A.step); r.TransferRoots(); shape = r.OneShape()

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
    info = {}
    for i, f in enumerate(faces):
        a = BRepAdaptor_Surface(f)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane(); info[i] = ('P', norm(V(pl.Axis().Direction())), V(pl.Location()))
        elif a.GetType() == GeomAbs_Cylinder:
            c = a.Cylinder(); info[i] = ('C', norm(V(c.Axis().Direction())), V(c.Axis().Location()), c.Radius())
        else:
            info[i] = ('?',)
    coax = lambda i, j: (abs(abs(dot(info[i][1], info[j][1])) - 1) < 1e-6 and
                         math.sqrt(max(dot(cross(sub(info[j][2], info[i][2]), info[i][1]),
                                           cross(sub(info[j][2], info[i][2]), info[i][1])), 0)) < 1e-4)
    # 同轴同半径圆柱面合并
    rep = {}
    cl = [i for i in info if info[i][0] == 'C']
    for i in cl:
        for j in cl:
            if j >= i:
                break
            if rep.get(j, j) == j and abs(info[i][3] - info[j][3]) < 1e-6 and coax(i, j):
                rep[i] = j; break
    seam = set()
    for k, fs in enumerate(eface):
        rr = sorted({rep.get(f, f) for f in fs})
        if len(rr) == 1 and len(fs) > 1:
            seam.add(k)
        eface[k] = rr
    fedges = {i: [] for i in range(len(faces))}
    for k, fs in enumerate(eface):
        if k not in seam:
            for f in fs:
                fedges[f].append(k)
    for i in list(info):
        if i in rep:
            del info[i]

    def nbr_planes(cf):
        D = info[cf][1]
        return sorted({g for k in fedges[cf] for g in eface[k] if g != cf and info[g][0] == 'P' and abs(dot(info[g][1], D)) < 1e-6})
    # 折弯：同轴、半径差 > 0.3、两侧各有两块相邻平面
    cyls = [i for i in info if info[i][0] == 'C']
    bends, used = [], set()
    for i in cyls:
        for j in cyls:
            if i >= j or i in used or j in used or not coax(i, j) or abs(info[i][3] - info[j][3]) < 0.3:
                continue
            ni, nj = nbr_planes(i), nbr_planes(j)
            if len(ni) == 2 and len(nj) == 2:
                inner, outer = (i, j) if info[i][3] < info[j][3] else (j, i)
                bends.append(dict(inner=inner, outer=outer, t=abs(info[i][3] - info[j][3]),
                                  in_f=nbr_planes(inner), out_f=nbr_planes(outer)))
                used |= {i, j}
    if not bends:
        raise SystemExit('没有找到折弯')
    t = bends[0]['t']
    # 平板：内外两面（法向平行、相距 t）合为一块
    flat_of, flats = {}, []
    for b in bends:
        b['flats'] = []
        for fi in b['in_f']:
            fo = [g for g in b['out_f'] if abs(abs(dot(info[fi][1], info[g][1])) - 1) < 1e-6
                  and abs(abs(dot(info[fi][1], sub(info[g][2], info[fi][2]))) - t) < 1e-3]
            assert fo, '找不到与内侧面相对的外侧面'
            ks = {flat_of[x] for x in (fi, fo[0]) if x in flat_of}
            if not ks:
                flats.append(set()); k = len(flats) - 1
            else:
                k = min(ks)
                for k2 in ks - {k}:
                    flats[k] |= flats[k2]
                    for g in flats[k2]:
                        flat_of[g] = k
                    flats[k2] = set()
            flats[k] |= {fi, fo[0]}; flat_of[fi] = flat_of[fo[0]] = k
            b['flats'].append(k)
    for b in bends:
        b['flats'] = [flat_of[f] for f in b['in_f']]

    def area(f):
        g = GProp_GProps(); BRepGProp.SurfaceProperties_s(faces[f], g); return g.Mass()
    root = max({k for b in bends for k in b['flats']}, key=lambda k: max(area(f) for f in flats[k]))
    # 根板：取任一面，基 a、b 在板面内
    rf = max(flats[root], key=area)
    n = info[rf][1]
    a0 = norm(cross(n, (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0)))
    maps = {root: Map(info[rf][2], a0, cross(n, a0), (0.0, 0.0))}
    side = {root: rf}
    order, red, bend_map = [root], [], {}
    queue = [root]
    done_b = set()
    while queue:
        cur = queue.pop(0)
        for bi, b in enumerate(bends):
            if bi in done_b or cur not in b['flats']:
                continue
            done_b.add(bi)
            ch = next(k for k in b['flats'] if k != cur)
            fc = side[cur]
            cyl = b['inner'] if fc in b['in_f'] else b['outer']
            sf = b['in_f'] if cyl == b['inner'] else b['out_f']
            side[ch] = next(f for f in sf if flat_of[f] == ch)
            D = info[cyl][1]; L = info[cyl][2]
            po = next(f for f in b['out_f'] if flat_of[f] == cur)
            co = next(f for f in b['out_f'] if flat_of[f] == ch)
            np_, nc = info[po][1], info[co][1]
            M = solve3([np_, nc, D], [dot(np_, info[po][2]), dot(nc, info[co][2]), dot(D, L)])
            def inplane(v, nn):
                v = sub(v, mul(D, dot(v, D))); v = sub(v, mul(nn, dot(v, nn))); return norm(v)
            ep = inplane(sub(M, face_point(faces[side[cur]])), np_)
            ec = inplane(sub(face_point(faces[side[ch]]), M), nc)
            Fp = maps[cur]
            FM = Fp(M); Fd = Fp.vec(D); E = Fp.vec(ep)
            # F_c(p) = FM − BD·E + ((p−M)·D)·Fd + ((p−M)·ec)·E
            ax3 = add(mul(D, Fd[0]), mul(ec, E[0])); bx3 = add(mul(D, Fd[1]), mul(ec, E[1]))
            maps[ch] = Map(M, ax3, bx3, (FM[0] - A.bd * E[0], FM[1] - A.bd * E[1]))
            # 折弯区：两条切线（与两侧所选面相交的圆柱边）
            tang = {}
            for kk in fedges[cyl]:
                oth = [g for g in eface[kk] if g != cyl]
                if oth and oth[0] in (side[cur], side[ch]):
                    c = BRepAdaptor_Curve(edges[kk])
                    tang[oth[0]] = V(c.Value((c.FirstParameter() + c.LastParameter()) / 2))
            u1 = norm(cross(D, (1, 0, 0) if abs(D[0]) < 0.9 else (0, 1, 0))); u2 = cross(D, u1)
            ang = lambda p, L=L, u1=u1, u2=u2: math.atan2(dot(sub(p, L), u2), dot(sub(p, L), u1))
            tp, tc = tang[side[cur]], tang[side[ch]]
            a_p, a_c = ang(tp), ang(tc)
            sw = (a_c - a_p + math.pi) % (2 * math.pi) - math.pi
            bend_map[cyl] = (cur, ch, tp, tc, D, a_p, sw, ang)
            ss = []
            for kk in fedges[cyl]:
                c = BRepAdaptor_Curve(edges[kk])
                ss += [dot(sub(V(c.Value(c.FirstParameter())), M), D), dot(sub(V(c.Value(c.LastParameter())), M), D)]
            R0 = (FM[0] - A.bd / 2 * E[0], FM[1] - A.bd / 2 * E[1])
            red.append(((R0[0] + min(ss) * Fd[0], R0[1] + min(ss) * Fd[1]), (R0[0] + max(ss) * Fd[0], R0[1] + max(ss) * Fd[1]),
                        abs(math.degrees(sw))))
            queue.append(ch); order.append(ch)

    def M3(p, f):
        if f in bend_map:
            cur, ch, tp, tc, D, a_p, sw, ang = bend_map[f]
            fr = ((ang(p) - a_p + math.pi) % (2 * math.pi) - math.pi) / sw
            P0 = add(tp, mul(D, dot(sub(p, tp), D))); P1 = add(tc, mul(D, dot(sub(p, tc), D)))
            q0, q1 = maps[cur](P0), maps[ch](P1)
            return (q0[0] + fr * (q1[0] - q0[0]), q0[1] + fr * (q1[1] - q0[1]))
        return maps[flat_of[f]](p)

    sel = set(side.values()) | set(bend_map)
    segs, circles = [], []
    for f in sel:
        for kk in fedges[f]:
            if any(g in sel and g != f for g in eface[kk]):
                continue
            c = BRepAdaptor_Curve(edges[kk]); t0, t1 = c.FirstParameter(), c.LastParameter()
            if c.GetType() == GeomAbs_Line:
                segs.append((M3(V(c.Value(t0)), f), M3(V(c.Value(t1)), f), 0.0))
            elif c.GetType() == GeomAbs_Circle and f not in bend_map:
                if abs(t1 - t0 - 2 * math.pi) < 1e-6:
                    q = M3(V(c.Circle().Location()), f); circles.append((q[0], q[1], 2 * c.Circle().Radius())); continue
                p0, pm, p1 = (M3(V(c.Value(x)), f) for x in (t0, (t0 + t1) / 2, t1))
                crs = (pm[0] - p0[0]) * (p1[1] - p0[1]) - (pm[1] - p0[1]) * (p1[0] - p0[0])
                segs.append((p0, p1, math.tan((t1 - t0) / 4) * (1 if crs > 0 else -1)))
            else:
                pts = [M3(V(c.Value(t0 + (t1 - t0) * q / 24)), f) for q in range(25)]
                segs += [(a, b, 0.0) for a, b in zip(pts, pts[1:])]
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

    def simp(lp):
        out = []; n_ = len(lp)
        for q in range(n_):
            a, b2, c = lp[q - 1], lp[q], lp[(q + 1) % n_]
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
    lines = [[[a[0] - x0, a[1] - y0], [b2[0] - x0, b2[1] - y0], round(deg, 2)] for a, b2, deg in red]
    W = max(p[0] for p in allp) - x0; H = max(p[1] for p in allp) - y0
    json.dump(dict(source=A.step.split('/')[-1], t=round(t, 3), bd=A.bd, size=[round(W, 3), round(H, 3)],
                   loops=loops, circles=circles, bend_lines=lines), open(A.out, 'w'), ensure_ascii=False, indent=1)
    print('t=%.2f 展开 %.2f × %.2f，环 %d，整圆 %d，折弯 %d 条 %s' %
          (t, W, H, len(loops), len(circles), len(lines), [l[2] for l in lines]))


if __name__ == '__main__':
    main()
