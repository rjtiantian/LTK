# 单件展开图（2026-10-23）：L板1、L板2、yuan da hu ke 01

- 生成：`python3 tools/gen_order.py 单件/2026-10-23` → `展开图_2026-10-23.dxf`（零件定义 `tools/ps20261023.py`）
- 材料：L板1、L板2 为 Q235B（用户指定），yuan da hu ke 01 为 SUS304；件数未给，各按 1 件
- 自检：QA 0 问题，排版异常 0；展开面积 × 板厚与模型体积相差 0.4%~1.1%（BD 与 SolidWorks 折弯系数不同）

| 件 | 来源 | 下料 | 说明 |
|---|---|---|---|
| L板1 | `STEP/L板1.STEP` | Q235B 4mm 150 × 213.2 | L 形 90 + 130，`tools/step_unfold.py --bd 6.8` |
| L板2 | `STEP/L板2.STEP` | Q235B 4mm 170 × 183.2 | L 形 90 + 100，同上 |
| yuan da hu ke 01 | `STEP/yuan da hu ke 01.SLDPRT` → `STEP/yuan da hu ke 01.STEP` | SUS304 1.5mm 150.8 × 135.4 | 护壳：顶 60 × 40，四面下折 40，两侧再外翻 20 底边（4-Φ9）；`tools/step_unfold2.py --bd 2.3` |

## SLDPRT 转 STEP
- 在 1.5 上用 SolidWorks 2025 转：`C:\Temp\sw2step\sw2step.vbs`（`OpenDoc` + `SaveAs3`，AP214）
- SSH 会话里不能创建 SolidWorks COM 对象，需在桌面会话（console）里运行：临时建一次性计划任务（`schtasks /create /it`）跑完即删

## 展开工具
- `tools/step_unfold2.py`：新增，按折弯树展开任意方向的直线折弯（以最大平板为根，外形尺寸法逐块接上），
  对 L板1、fb12、扭力臂的结果与 `step_unfold.py` 完全一致
