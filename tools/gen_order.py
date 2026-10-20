# -*- coding: utf-8 -*-
"""生成 NO.463 / NO.475 / NO.477-478 下料图。

用法: python3 tools/gen_order.py 463        -> 463/NO.463.dxf
      python3 tools/gen_order.py 475        -> 475/NO.475.dxf
      python3 tools/gen_order.py 单件/5406205B -> 单件/5406205B/5406205B_展开图.dxf（单件出图）
      python3 tools/gen_order.py 477-478    -> 477-478/NO.477-NO.478.dxf
零件定义在 tools/p<订单>_*.py（每个模块提供 register(C)）。
"""
import os, sys, glob, importlib
sys.path.insert(0, os.path.dirname(__file__))
from orderctx import Ctx
from layout import build, ROOT

ORDERS = {'单件/2026-10-20': ('单件_2026-10-20.xlsx', '展开图_2026-10-20.dxf', 'ps20261020'),
          '单件/2026-10-17': ('单件_2026-10-17.xlsx', '展开图_2026-10-17.dxf', 'ps20261017'),
          '单件/5406205B': ('5406205B.xlsx', '5406205B_展开图.dxf', 'ps5406205B'),
          '463': ('NO.463.xlsx', 'NO.463.dxf', 'p463_'),
          '475': ('NO.475.xlsx', 'NO.475.dxf', 'p475_'),
          '477-478': ('NO.477-NO.478.xlsx', 'NO.477-NO.478.dxf', 'p477_')}


def load(order):
    xlsx, out, prefix = ORDERS[order]
    C = Ctx(os.path.join(ROOT, order, 'DXF'))
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), prefix + '*.py'))):
        m = importlib.import_module(os.path.basename(f)[:-3])
        m.register(C)
    return C, os.path.join(ROOT, order, xlsx), os.path.join(ROOT, order, out)


if __name__ == '__main__':
    order = sys.argv[1]
    C, xlsx, out = load(order)
    rep = build(xlsx, C.PARTS, out)
    for c, s in rep:
        print(c, s)
    print('saved', out)
