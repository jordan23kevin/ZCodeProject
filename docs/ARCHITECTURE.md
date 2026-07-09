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

## PSD 模板结构

模板：`D:\Semems\1胚衣\白\3.psd`

- 画布尺寸：1340 × 1785 px
- 图层 1（背景）：完整模特 + 白 T 底图，占满整张画布
- 图层 2（前景遮罩）：手部区域裁切，bbox 为 (657, 1011, 1340, 1381)

代码通过 `bbox` 自动识别：占满 `(0, 0, width, height)` 的图层为背景，其余为前景遮罩。

## 贴图定位算法

1. 读取设计图，按 `target_height=677` 等比缩放，得到新宽度 `dw`。
2. 计算左上角：
   - `left = center_x - dw / 2`
   - `top = top_y`
3. 居中原理：以设计图顶部为垂直基准，以设计图水平中心为水平基准。

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
| `config.py` | 集中管理默认参数，避免硬编码 |
| `core.py` | 模板加载、缩放、混合、合成等无状态函数 |
| `cli.py` | 命令行参数解析和输出打印 |
| `__main__.py` | 支持 `python -m white_t_mockup` |
| `scripts/apply_mockup.py` | 兼容旧用法的单文件入口 |
