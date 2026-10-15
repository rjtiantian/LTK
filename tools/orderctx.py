# -*- coding: utf-8 -*-
"""每个订单的零件定义上下文（NO.475 / NO.477-478 起使用）。

零件模块写法:
    def register(C):
        @C.part('0100107A')
        def _(q):
            t = 3; w = C.bd(t)
            p = C.Piece().rect(0, 0, 115, 55, 2)
            p.bend(0, 30, 115, 30, w)
            return [(C.lab(t, q), p)]
        C.mirror('0100108A', '0100107A')
        C.todo_part('xxxx', 2, '待人工展开（原因）')

返回值: [(标签, Piece), ...]；标签用 C.lab(厚度, 件数[, 材料])，件数 = 订单数 × 每台用量。
"""
import os, math
from sheetlib import (Piece, extract, extract_unbroken, stretch_tab, drop_concentric_outer, bd as _bd, TAP,
                      CUT, BEND, relief_params, clip_out_box, bd_angle, fit_holes, fold_edge)

THK_SUB = {15: 16}                       # 15mm 一律用 16mm（用户确认）
SUS_SUB = {3.5: 4}                       # SUS304 无 3.5 板料，按 4mm（历史习惯）


class Ctx:
    Piece = Piece
    extract = staticmethod(extract)
    extract_unbroken = staticmethod(extract_unbroken)
    stretch_tab = staticmethod(stretch_tab)
    drop_concentric_outer = staticmethod(drop_concentric_outer)
    relief_params = staticmethod(relief_params)
    clip_out_box = staticmethod(clip_out_box)
    bd_angle = staticmethod(bd_angle)
    fit_holes = staticmethod(fit_holes)
    fold_edge = staticmethod(fold_edge)
    TAP = TAP
    CUT = CUT
    BEND = BEND
    math = math

    def __init__(self, dxf_dir, mat='SUS304'):
        self.dxf_dir = dxf_dir
        self.mat = mat
        self.PARTS = {}

    # ---- 路径 / 材料 ----
    def DXF(self, name):
        return os.path.join(self.dxf_dir, name)

    def bd(self, t, mat=None):
        return _bd(t, mat or self.mat)

    def lab(self, t, n, mat=None):
        mat = mat or self.mat
        t = THK_SUB.get(t, t)
        if mat.upper().startswith('SUS'):
            t = SUS_SUB.get(t, t)
        return '%s-%smm,%d件' % (mat, '%g' % t, n)

    # ---- 注册 ----
    def part(self, code):
        def deco(f):
            self.PARTS[code] = f
            return f
        return deco

    def mirror(self, code, src):
        """镜像件：按源件左右镜像"""
        def f(q):
            res = self.PARTS[src](q)
            if isinstance(res, tuple):
                return res
            return [(l, p.mirrored()) for l, p in res]
        self.PARTS[code] = f

    def todo_part(self, code, t, note, mat=None):
        self.PARTS[code] = lambda q: ('TODO', [self.lab(t, q, mat)], note)

    # ---- 常用件 ----
    def plate(self, fname, region, drop=None, keep_outline_d=None):
        """平板件：直接取视图区域内的可见轮廓（区域左下角为原点），去掉沉头/螺纹大径同心圆"""
        p = extract(self.DXF(fname), region, drop=drop)
        drop_concentric_outer(p, keep_outline_d)
        return p

    def tube_rect(self, a, b, t, r=None):
        """矩形/方管截面示意（同 NO.441 画法），标签写长度：C.lab(长度, 件数)"""
        r = 2 * t if r is None else r
        return Piece().rect(0, 0, a, b, r).rect(t, t, a - t, b - t, max(r - t, 0))

    def tube_round(self, d, t):
        return Piece().circle(d / 2, d / 2, d).circle(d / 2, d / 2, d - 2 * t)
