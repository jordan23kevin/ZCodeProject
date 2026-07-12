# CHANGELOG — white_t_mockup（模特图贴图引擎）

## v1.8.0 — 2026-07-12（布料同步明度）
- `core.py` 新增 `apply_fabric_synced_shading` + `_compute_fabric_synced_shading_field`：
  - 仅缩放印花 HSV 的 **V（明度）**，H/S 零偏差 → 印花固有色与源文件完全一致。
  - 明度严格跟随同位置布料（深褶处 shading→0 自然隐没），杜绝"布料暗了印花仍高亮"。
  - 判据用**局部对比**（非全局亮度），只压"深褶皱窄缝"，平整/均匀区（含黑衫整片暗布）零压暗。
  - 手部/前景遮挡区 shading 强制置 1（不调制）。
- `core.py::apply_mockup_transform / apply_mockup`：开启布料同步明度时**关闭**旧的 `transfer_shadow_highlight`（其 multiply/overlay 会偏色）。
- `cli.py`：新增 `--no-fabric-shading` / `--shading-blur`（默认开启，shading-blur=4）。
- `__init__.py`：`__version__ = "1.8.0"`。
- 生产调用方 `04_OS/engine/w_mockup_extra.py` 已加 `--shading-blur 4`。

## v1.7.0 — 2026-07-12（2D 梯度褶皱贴合 + 防重影 + 手部防扭曲）
- `apply_displacement` 新增 `disp_mode="gradient"`：把 disp 当高度场沿褶皱切线做 2D 梯度位移，印花真正"裹"在褶皱上。
- 新增 `_limit_gradient_2d`（|∇off|≤0.45）消除尖锐褶皱脊处的镜像重影/折叠。
- 手部/前景遮挡物区位移压平到 128（`occluder`），消除"引力场"假位移。
- 遮罩(mask)不参与位移，只由设计图自身 alpha 裁剪。
- 用户 4×5 测试图对比选定：`--disp-strength 90 --disp-smooth 40 --disp-dead-zone 15 --preserve-color`。

## v1.6.2 — 2026-07-12（mask 边缘羽化 + 更大位移强度）
- mask 边缘 `mask_feather=5` 羽化，支撑大强度下边界不折叠。
- 支持更高 disp 强度档位（测试用）。

## v1.6.1 — 2026-07-12（位移死区软斜坡，消除文字撕裂）
- `apply_displacement` 旧版硬死区在轮廓线位移突跳 → 重映射折叠 → 文字"上下撕裂/重影"。
- 改为软斜坡 `ramp=clip(d/dead_zone,0,1)`，off 在 128 附近平滑趋零，折叠像素=0。

## v1.6.0 — 2026-07（黑衫白墨打底）
- `white_underbase`（自适应浓度白墨打底）成为黑衫默认 `prepare_method`，解决近黑像素贴在黑衫上物理不可见。
