#!/bin/sh
# DWG -> DXF 批量转换（LibreDWG 0.13.3 的 dwg2dxf），转换后修复长文本断行以便 ezdxf 读取
set -e
cd "$(dirname "$0")/.."
for d in ${DIRS:-441 474}; do
  mkdir -p "$d/DXF"
  for f in "$d"/DWG/*.dwg; do
    b=$(basename "$f" .dwg)
    dwg2dxf -y -o "$d/DXF/$b.dxf" "$f" >/dev/null 2>&1 || echo "WARN: $f"
  done
  python3 tools/fix_libredwg_dxf.py "$d"/DXF/*.dxf
done
