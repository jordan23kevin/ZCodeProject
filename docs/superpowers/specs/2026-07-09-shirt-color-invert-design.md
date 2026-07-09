# 反黑/反白预处理改进设计文档

## 背景与目标

当前 AI 去背贴图页面的“反黑”“反白”按钮使用简单的黑白剪影逻辑：

- 反黑：把非透明像素全部变成白色，用于黑色 T 恤。
- 反白：把非透明像素全部变成黑色，用于白色 T 恤。

这种处理方式丢失了所有颜色信息，用户反馈“太粗糙”。

**目标**：把反黑/反白的默认算法改成“亮度反相（HSV Value Invert）”，在保留色相和饱和度的前提下反转明暗，使印花在对应颜色 T 恤上可见，同时保留颜色。

## 决策结论

经用户确认，采用 **亮度反相（HSV Value Invert）** 作为新的默认预处理算法。

反黑和反白均使用同一算法，区别仅在于标注用途：

- 反黑（黑色 T 恤）：暗色变亮，整体在黑底上可见。
- 反白（白色 T 恤）：亮色变暗，适合原本偏浅的设计。

旧的黑白剪影逻辑保留为 `silhouette` 模式，便于回滚和对比。

## 算法说明

### 亮度反相（value_invert）

1. 将 RGBA 图像的 RGB 部分转换到 HSV 色彩空间。
2. 对 V（亮度/明度）通道做取反：`V' = 255 - V`。
3. 转回 RGB。
4. 保留原始 alpha 通道不变。

效果：色相、饱和度保留，明暗反转。例如深蓝变亮蓝，浅黄变暗黄。

### 剪影（silhouette，旧逻辑保留）

- 反黑：将所有非透明像素的 RGB 设为 `(255, 255, 255)`，alpha 不变。
- 反白：将所有非透明像素的 RGB 设为 `(0, 0, 0)`，alpha 不变。

### 无预处理（none）

原图直接用于贴图。

## 架构改动

### 新增函数：`core.prepare_design_for_shirt`

```python
def prepare_design_for_shirt(
    design: Image.Image,
    shirt_color: Literal["black", "white"],
    method: Literal["value_invert", "silhouette", "none"] = "value_invert",
) -> Image.Image:
    """
    在贴图前对设计图做预处理，使其更适合目标 T 恤颜色。

    Args:
        design: 透明底 RGBA 设计图。
        shirt_color: 目标 T 恤颜色，"black" 或 "white"。
        method: 预处理方法，默认 "value_invert"。

    Returns:
        预处理后的 RGBA 图像。
    """
```

位置：`white_t_mockup/core.py`。

### 修改函数：`apply_mockup` 与 `apply_mockup_transform`

两个高层函数新增参数：

```python
shirt_color: Literal["black", "white"] | None = None,
prepare_method: Literal["value_invert", "silhouette", "none"] = "value_invert",
```

执行顺序：

1. 打开设计图。
2. 如果 `shirt_color` 不为 `None`，调用 `prepare_design_for_shirt()`。
3. 继续原有流程：缩放/旋转、定位、混合、保存。

### CLI 参数

`white_t_mockup/cli.py` 新增：

```text
--shirt-color {black,white}
    指定目标 T 恤颜色，启用预处理。

--prepare-method {value_invert,silhouette,none}
    预处理方法，默认 value_invert。

--for-black-shirt
    快捷开关，等价于 --shirt-color black --prepare-method value_invert。

--for-white-shirt
    快捷开关，等价于 --shirt-color white --prepare-method value_invert。
```

### 数据流更新

```text
输入 PNG 设计图
    │
    ▼
[可选] prepare_design_for_shirt() ──▶ 亮度反相 / 剪影 / 无处理
    │
    ▼
resize_design() / apply_transform() ──▶ 缩放、旋转
    │
    ▼
paste_with_blend() ──▶ 定位并混合到背景
    │
    ▼
手部前景遮罩（PSD 模板）
    │
    ▼
输出 JPG
```

## 测试策略

在 `tests/test_transform.py` 或新增 `tests/test_prepare.py` 中覆盖：

1. **value_invert 保留色相/饱和度**
   - 构造已知 RGB 色块，预处理后 H、S 不变，V 取反。
2. **value_invert 保留 alpha**
   - 半透明像素预处理后 alpha 值不变。
3. **silhouette 反黑**
   - 非透明像素全部变为白色，透明像素不变。
4. **silhouette 反白**
   - 非透明像素全部变为黑色，透明像素不变。
5. **none**
   - 输出与输入完全一致。
6. **集成测试**
   - 使用 `--for-black-shirt` 和 `--for-white-shirt` 跑 CLI，确认输出与预处理后的样图一致。

## 文档更新

1. `docs/ARCHITECTURE.md`
   - 在数据流图中增加 `prepare_design_for_shirt()` 节点。
   - 在“核心函数”表格中新增 `prepare_design_for_shirt()`。

2. `README.md`
   - 新增反黑/反白使用示例。
   - 说明 `value_invert` 与 `silhouette` 的区别。

3. `CHANGELOG.md`
   - 记录新增预处理功能。

## 兼容性

- 默认行为不变：不指定 `--shirt-color` 时，完全不调用预处理，现有输出保持一致。
- 旧版 `silhouette` 逻辑保留，可通过 `--prepare-method silhouette` 启用。
- `apply_mockup()` 和 `apply_mockup_transform()` 的新参数均有默认值，不破坏现有调用。

## 风险与回滚

| 风险 | 缓解措施 |
|------|----------|
| 亮度反相对某些极亮/极暗设计效果不佳 | 保留 `silhouette` 和 `none` 可选；用户可切换。 |
| HSV 转换与 PIL 版本相关 | 使用 `colorsys` 或 Pillow 稳定 API，测试覆盖。 |
| CLI 参数命名与用户页面不一致 | 快捷开关 `--for-black-shirt` / `--for-white-shirt` 直接对应页面按钮语义。 |

## 验收标准

- [ ] `core.py` 中 `prepare_design_for_shirt()` 实现并通过单元测试。
- [ ] `apply_mockup()` 与 `apply_mockup_transform()` 支持 `shirt_color` 和 `prepare_method`。
- [ ] CLI 支持 `--shirt-color`、`--prepare-method`、`--for-black-shirt`、`--for-white-shirt`。
- [ ] 生成与样图 `_sample_value_inv.png` 一致的输出。
- [ ] `ARCHITECTURE.md`、`README.md`、`CHANGELOG.md` 已更新。
- [ ] 所有测试通过。
