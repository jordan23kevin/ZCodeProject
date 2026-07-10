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
- 贴图参数：最终像素（宽/高）、旋转角度、有效像素最高点 Y、有效像素中心 X、混合模式

## 输出

- 白 T 恤样机 JPG

## 调用方式

### 命令行（使用模板预设，推荐）

```bash
# 列出所有已配置模板
python -m white_t_mockup --list-presets

# 使用预设自动加载该模板的参数
python -m white_t_mockup design.png output.jpg --preset 白正2.jpg
```

### 命令行（手动指定参数）

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白正2.jpg" \
  --final-w 546 \
  --final-h 546 \
  --rotate -2 \
  --effective-top-y 644 \
  --effective-center-x 670 \
  --blend-mode multiply
```

### 命令行（旧版方法，兼容 DX0533）

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白\白W3.psd" \
  --top-y 449 --center-x 735 --final-w 546 --final-h 546
```

### Python API

```python
from white_t_mockup import apply_mockup_transform

apply_mockup_transform(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白正2.jpg",
    final_w=546,
    final_h=546,
    rotation_degrees=-2.0,
    effective_top_y=644,
    effective_center_x=670,
    blend_mode="multiply",
    quality=95,
)
```

## 工作流程

1. 用户提供：胚衣模板路径、最终像素（宽/高）、最高像素点 Y、中心点 X、旋转角度、混合模式。
2. 脚本：resize 到最终像素 → 旋转（正=顺时针/负=逆时针） → 计算有效像素边界 → 按最高点和中心点定位 → 用指定混合模式合成 → 输出 JPG。
3. 输出图应与用户预期位置、大小、角度、风格一致。

## 参数说明

| 参数 | 含义 |
|------|------|
| `--preset` | 使用已配置的模板预设（自动加载参数） |
| `--list-presets` | 列出所有已配置模板 |
| `--final-w` / `--final-h` | 贴图最终宽/高像素（PS 缩放后尺寸） |
| `--rotate` | 旋转角度（正=顺时针/负=逆时针，同 PS） |
| `--effective-top-y` | 有效像素最高点 Y 坐标 |
| `--effective-center-x` | 有效像素水平中心 X 坐标 |
| `--blend-mode` | 混合模式，默认 `multiply` |
| `--quality` | JPG 质量，默认 95 |

## 已配置模板预设

所有胚衣参数统一记录在 `docs/胚衣参数表_模板.csv`（缩放后宽/高 px、旋转角度、最高像素点 y、中心 x、方法），贴图前由 `scripts/sync_presets_from_csv.py` 同步到 `white_t_mockup/presets.json`。新增或修改胚衣只让用户编辑该 CSV，不再维护镜像文档。

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
