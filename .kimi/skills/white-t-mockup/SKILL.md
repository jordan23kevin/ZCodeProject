# white-t-mockup

## 用途

自动把透明底 PNG 贴图合成到白 T 恤样机模板，输出 1340×1785 px 的 JPG 成品图。

## 使用场景

- 给新款白 T 恤生成带贴图的电商展示图
- 批量替换胸口/背面的设计图，保持位置、大小、光影一致
- 需要 100% 复现 DX0533 同款效果时

## 输入

- **design**：透明底 PNG 设计图（如 `DX0533_BW_cut.png`）
- **output**：输出 JPG 路径
- 可选：模板路径、top-y、center-x、target-height、blend-mode、quality

## 输出

- 白 T 恤样机 JPG，尺寸 1340×1785

## 调用方式

### 命令行

```bash
# 使用默认白 T 参数（Multiply 混合模式）
python -m white_t_mockup design.png output.jpg

# 使用普通混合模式
python -m white_t_mockup design.png output.jpg --blend-mode normal
```

### Python API

```python
from white_t_mockup import apply_mockup

apply_mockup(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白\3.psd",
    top_y=449,
    center_x=735,
    target_height=677,
    blend_mode="multiply",
    quality=95,
)
```

## 标准参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| template | `D:\Semems\1胚衣\白\3.psd` | 白 T 胚衣模板 |
| top-y | 449 | 贴图最高点 Y 坐标 |
| center-x | 735 | 贴图水平中心 X 坐标 |
| target-height | 677 | 贴图缩放后高度 |
| blend-mode | multiply | 正片叠底，使贴图融入衣褶 |
| quality | 95 | JPG 质量 |

## 注意事项

1. 输入 PNG 必须是透明底，否则会被黑色/白色背景覆盖。
2. 模板 `3.psd` 必须包含两个图层：
   - 占满画布的背景层（模特底图）
   - 手部前景遮罩层（小 bbox）
3. 合成顺序固定为：背景 → 贴图 → 手部遮罩。
4. 所有白 T 款统一使用上述标准参数，不要随意改动。

## 文件位置

- 核心包：`white_t_mockup/`
- 命令行入口：`python -m white_t_mockup` 或 `scripts/apply_mockup.py`
- 文档：`docs/`
- 示例：`examples/dx0533/`
