# white-t-mockup

## 用途

自动把透明底 PNG 贴图合成到白 T 恤样机模板，输出标准电商展示图。

## 使用场景

- 给新款白 T 恤生成带贴图的展示图
- 批量替换胸口/背面设计图，保持位置、大小、光影一致
- 需要 100% 复现已有效果时

## 输入

- **design**：透明底 PNG 设计图（如 `DX0001_W_cut.png`）
- **output**：输出 JPG 路径
- 模板路径（PSD 或 PNG）
- 贴图参数：缩放比例、旋转角度、有效像素最高点 Y、有效像素中心 X、混合模式

## 输出

- 白 T 恤样机 JPG

## 调用方式

### 命令行（使用模板预设，推荐）

```bash
# 列出所有已配置模板
python -m white_t_mockup --list-presets

# 使用预设自动加载该模板的参数
python -m white_t_mockup design.png output.jpg --preset 1B.png
```

### 命令行（手动指定参数）

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白\W4.png" \
  --scale 0.40 \
  --rotate 1 \
  --effective-top-y 490 \
  --effective-center-x 780 \
  --blend-mode multiply
```

### 命令行（旧版方法，兼容 DX0533）

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白\W3.psd" \
  --top-y 449 --center-x 735 --target-height 677
```

### Python API

```python
from white_t_mockup import apply_mockup_transform

apply_mockup_transform(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白\W4.png",
    scale=0.40,
    rotation_degrees=1.0,
    effective_top_y=490,
    effective_center_x=780,
    blend_mode="multiply",
    quality=95,
)
```

## 工作流程

1. 用户提供：胚衣模板路径、缩放比例、最高像素点 Y、中心点 X、旋转角度、混合模式。
2. 脚本：缩放贴图 → 顺时针旋转 → 计算有效像素边界 → 按最高点和中心点定位 → 用指定混合模式合成 → 输出 JPG。
3. 输出图应与用户预期位置、大小、角度、风格一致。

## 参数说明

| 参数 | 含义 |
|------|------|
| `--preset` | 使用已配置的模板预设（自动加载参数） |
| `--list-presets` | 列出所有已配置模板 |
| `--scale` | 贴图缩放比例（如 0.40 = 40%） |
| `--rotate` | 顺时针旋转角度（如 1） |
| `--effective-top-y` | 有效像素最高点 Y 坐标 |
| `--effective-center-x` | 有效像素水平中心 X 坐标 |
| `--blend-mode` | 混合模式，默认 `multiply` |
| `--quality` | JPG 质量，默认 95 |

## 已配置模板预设

| 模板 | 方法 | 缩放 | 旋转 | 最高点 y | 中心 x | 混合 |
|------|------|------|------|----------|--------|------|
| `W3.psd` | legacy | 677px | 0 | 449 | 735 | multiply |
| `1B.png` | transform | 40% | 0 | 725 | 649 | multiply |
| `3B.png` | transform | 32% | 逆时针 3° | 700 | 777 | multiply |
| `4B.png` | transform | 28% | 顺时针 2° | 1011 | 576 | multiply |

新增胚衣时，先让用户用 Excel 填写 `docs/胚衣参数表_模板.csv` 并保存/导出为 CSV UTF-8；再读取该 CSV，转换成 `docs/胚衣参数表.md`，并同步到 `white_t_mockup/presets.json`。

## 注意事项

1. 输入 PNG 必须是透明底。
2. PSD 模板需含背景层 + 手部遮罩层；PNG 模板是单图层图片。
3. PSD 模板合成顺序：背景 → 贴图 → 手部遮罩。
4. "有效像素"指贴图中非透明的部分，定位以有效像素的最高点和中心为准。

## 文件位置

- 核心包：`white_t_mockup/`
- 命令行入口：`python -m white_t_mockup` 或 `scripts/apply_mockup.py`
- 文档：`docs/`
- 示例：`examples/`
