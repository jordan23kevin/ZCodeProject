# 架构说明

## 整体数据流

```
输入 PNG 设计图
    │
    ▼
[可选] prepare_design_for_shirt() ──▶ 亮度反相 / 剪影 / 无处理
    │
    ▼
    resize_design() / apply_transform() ──▶ 缩放、旋转
    │
    ▼
paste_with_blend() ──▶ 按 (center_x, top_y) 定位，使用 Multiply 等混合模式贴到背景上
    │
    ▼
手部前景遮罩 ──▶ 按原 PSD bbox 位置盖上，遮挡贴图穿帮部分
    │
    ▼
输出 JPG
```

## 模板类型

### PSD 模板（如 `D:\Semems\1胚衣\白\W3.psd`）

- 画布尺寸：1340 × 1785 px
- 图层 1（背景）：完整模特 + 白 T 底图，占满整张画布
- 图层 2（前景遮罩）：手部区域裁切，bbox 为 (657, 1011, 1340, 1381)

代码通过 `bbox` 自动识别：占满 `(0, 0, width, height)` 的图层为背景，其余为前景遮罩。

### PNG 模板（如 `D:\Semems\1胚衣\白\W4.png`）

- 单图层图片，无手部遮罩
- 整张图片作为背景，直接在其上合成贴图

`load_any_template()` 会根据文件后缀自动选择加载方式。

## 模板预设

每张胚衣的参数统一记录在 [`docs/胚衣参数表_模板.csv`](./胚衣参数表_模板.csv)，由 `scripts/sync_presets_from_csv.py` 同步到 `white_t_mockup/presets.json`（`config.load_presets()` / `config.get_preset()` 读取）。CLI 支持 `--preset <模板文件名>` 显式选择预设；未指定时从 `--template` 文件名自动匹配。新增或修改胚衣只改 CSV，不要把参数硬编码进代码或测试。

## 贴图定位算法

### 旧版方法（兼容 DX0533）

1. 读取设计图，resize 到 CSV 指定的最终像素 `(final_w, final_h)`，得到新尺寸。
2. 计算左上角：
   - `left = center_x - dw / 2`
   - `top = top_y`
3. 居中原理：以设计图顶部为垂直基准，以设计图水平中心为水平基准。

### 新版方法（transform）

1. 读取设计图，resize 到 CSV 指定的最终像素 `(final_w, final_h)`。
2. 顺时针旋转 `rotation_degrees` 度（PIL 中正角度为逆时针，因此传入负值）。
3. 计算有效（非透明）像素边界框 `(left, top, right, bottom)`。
4. 按有效像素定位：
   - `paste_y = effective_top_y - top`
   - `paste_x = effective_center_x - (left + right) / 2`
5. 用指定混合模式贴到背景上；若模板是 PSD，再盖上手部遮罩。

## 混合模式实现

默认使用 **Multiply（正片叠底）**，计算公式：

```
result = base * blend / 255
```

实现细节：

1. 截取画布上与设计图重叠的区域作为 `base`。
2. 截取对应位置的设计图区域作为 `blend`。
3. 对 RGB 通道应用混合公式。
4. 用设计图的 alpha 通道做普通 alpha 混合：
   `final = blended * alpha + base * (1 - alpha)`。
5. 把结果写回画布。

这样既能保留设计图的透明边缘，又能让有色区域与衣褶自然融合。

## 模块职责

| 模块 | 职责 |
|------|------|
| `config.py` | 集中管理默认参数与模板预设（`presets.json`），避免硬编码 |
| `core.py` | 模板加载（PSD/PNG）、缩放、旋转、有效像素定位、混合、**预处理**、合成等无状态函数 |
| `cli.py` | 命令行参数解析，支持 `--preset` / `--list-presets`，自动判断新版/旧版方法，输出打印 |
| `__main__.py` | 支持 `python -m white_t_mockup` |
| `scripts/apply_mockup.py` | 兼容旧用法的单文件入口 |

## 核心函数

| 函数 | 作用 |
|------|------|
| `load_template()` | 加载 PSD 模板，返回背景/前景/位置/尺寸 |
| `load_png_template()` | 加载 PNG 模板 |
| `load_any_template()` | 根据后缀自动选择加载方式 |
| `resize_design()` | 按目标高度等比缩放（旧版） |
| `apply_transform()` | 缩放 + 顺时针旋转（新版） |
| `find_effective_bbox()` | 找出有效（非透明）像素边界框 |
| `calculate_effective_position()` | 按有效像素最高点/中心点计算粘贴位置 |
| `paste_with_blend()` | 按混合模式贴图 |
| `apply_mockup()` | 旧版高层封装 |
| `apply_mockup_transform()` | 新版高层封装 |
| `prepare_design_for_shirt()` | 根据目标 T 恤颜色预处理设计图：亮度反相、剪影或不做处理 |

## 两条贴图渲染链（v1.5.0）

贴图成品有两条入口，改动参数时需同步：

### ① 手动贴图（lovart_bridge `/api/mockup`）

```
前端点击"贴图"
  → lovart_bridge.py api_mockup() (POST /api/mockup)
  → _run_white_t_mockup()
  → subprocess: python -m white_t_mockup
    参数: --template <胚衣> --final-w/h --rotate --effective-top-y/center-x
           --disp-strength 12 --shadow-opacity 0.22 --highlight-opacity 0.22
           --for-black-shirt / --for-white-shirt
           [--preserve-color] [--occluder]
```

### ② 自动贴图（check_rem → w_mockup_extra）

```
check_rem.py 点击"贴图"
  → _ps_sticker() → _run_sticker_task() → _run_one_sticker()
  → 判定: 单面款(W-only/B-only) → w_mockup_extra.generate_single_side_mockup()
  → subprocess: python -m white_t_mockup
    参数: --preset <胚衣> [--preserve-color(黑衫)]
```

### 共享渲染核心（core.py）

```
prepare_design_for_shirt()  → 反色/显色/原样 (dark_boost/value_invert/none)
apply_transform()           → 缩放+旋转+定位
apply_displacement()        → 褶皱位移扭曲 (disp.png)
apply_occlusion_alpha()     → 褶皱折入隐藏 (occlusion.png)
apply_realism()             → 降饱和/降亮度/边缘模糊 (保色模式跳过)
paste_with_blend()          → 混合贴图 (normal/multiply/screen)
transfer_shadow_highlight() → 阴影Multiply/高光Overlay (限印花∩衣服)
overlay_texture()           → 布纹透出 (保色模式跳过)
_paste_occluder_top()       → 顶层遮挡物
```

## 保色模式（--preserve-color）

仅做几何变形（遮罩裁剪 + displacement 位移扭曲），完全不碰颜色：

| 参数 | 默认 | 保色模式 |
|------|------|---------|
| prepare_method | dark_boost | none |
| saturation | 0.97 | 1.0 |
| brightness | 1.0 | 1.0 |
| shadow_opacity | 0.22 | 0.0 |
| highlight_opacity | 0.22 | 0.0 |
| realism | True | False |
| blend_mode | (按衫色) | normal |

### 排查方法论

1. **确定渲染链**：单面款→check_rem→w_mockup_extra；多面款→check_rem→PS脚本；手动→bridge /api/mockup
2. **测量亮度**：必须用设计图自身 alpha 锁定印花核心像素，不能用整图阈值（会混入衬衫白背景产生假象）
3. **模板差异**：不同胚衣模板（如黑W1模特图 vs 黑W11平铺）背景亮度差异极大，会干扰整体亮度判断
4. **暗像素消失**：设计图近黑(L<30)像素在黑衫上物理不可见，需 dark_boost 或白底(underbase)
