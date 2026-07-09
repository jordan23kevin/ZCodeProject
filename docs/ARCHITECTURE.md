# 架构说明

## 整体数据流

```
输入 PNG 设计图
    │
    ▼
resize_design() ──▶ 等比缩放到 target_height
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

### PSD 模板（如 `D:\Semems\1胚衣\白\3.psd`）

- 画布尺寸：1340 × 1785 px
- 图层 1（背景）：完整模特 + 白 T 底图，占满整张画布
- 图层 2（前景遮罩）：手部区域裁切，bbox 为 (657, 1011, 1340, 1381)

代码通过 `bbox` 自动识别：占满 `(0, 0, width, height)` 的图层为背景，其余为前景遮罩。

### PNG 模板（如 `D:\Semems\1胚衣\白\W4.png`）

- 单图层图片，无手部遮罩
- 整张图片作为背景，直接在其上合成贴图

`load_any_template()` 会根据文件后缀自动选择加载方式。

## 模板预设

每张胚衣模板的参数独立记录在 `white_t_mockup/presets.json`，由 `config.load_presets()` / `config.get_preset()` 读取。CLI 支持 `--preset <模板文件名>` 显式选择预设；如果未指定 `--preset`，会尝试从 `--template` 的文件名自动匹配预设。

| 模板 | 方法 | 参数 |
|------|------|------|
| `3.psd` | legacy | `target_height=677`, `top_y=449`, `center_x=735`, `blend_mode=multiply` |
| `W4.png` | transform | `scale=0.40`, `rotation_degrees=1.0`, `effective_top_y=490`, `effective_center_x=780`, `blend_mode=multiply` |
| `1B.png` | transform | `scale=0.40`, `rotation_degrees=0`, `effective_top_y=925`, `effective_center_x=840`, `blend_mode=multiply` |

新增胚衣时，只新增一条 preset，不要把已有模板的参数硬编码进代码或测试。

## 贴图定位算法

### 旧版方法（兼容 DX0533）

1. 读取设计图，按 `target_height=677` 等比缩放，得到新宽度 `dw`。
2. 计算左上角：
   - `left = center_x - dw / 2`
   - `top = top_y`
3. 居中原理：以设计图顶部为垂直基准，以设计图水平中心为水平基准。

### 新版方法（transform）

1. 读取设计图，按 `scale` 等比缩放（如 0.40 = 40%）。
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
| `core.py` | 模板加载（PSD/PNG）、缩放、旋转、有效像素定位、混合、合成等无状态函数 |
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
