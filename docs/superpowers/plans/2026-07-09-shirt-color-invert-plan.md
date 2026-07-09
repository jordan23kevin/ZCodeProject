# 反黑/反白亮度反相 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `white_t_mockup` 中新增贴图前预处理步骤，把反黑/反白的默认算法从黑白剪影改为亮度反相（HSV Value Invert），保留颜色信息。

**Architecture:** 在 `core.py` 新增无状态函数 `prepare_design_for_shirt()`，负责 HSV 亮度反相与旧剪影逻辑；`apply_mockup()` / `apply_mockup_transform()` 在打开设计图后调用该函数；CLI 增加 `--shirt-color`、`--prepare-method` 与快捷开关 `--for-black-shirt` / `--for-white-shirt`。

**Tech Stack:** Python 3.11+, Pillow, NumPy, pytest, argparse.

## Global Constraints

- 不指定 `--shirt-color` 时，输出必须与改动前完全一致（默认行为不变）。
- 必须保留旧黑白剪影逻辑，可通过 `--prepare-method silhouette` 回滚。
- 预处理仅作用于非透明像素，alpha 通道原样保留。
- 所有新函数/参数必须有类型注解。
- 单元测试不依赖外部模板文件存在与否（使用 `pytest.skip` 或构造 synthetic 图像）。
- 每次任务完成后提交一次 git commit。

---

## File Structure

| File | Responsibility |
|------|----------------|
| `white_t_mockup/core.py` | 新增 `prepare_design_for_shirt()` 与 HSV 辅助函数；修改 `apply_mockup()` / `apply_mockup_transform()` 接入预处理。 |
| `white_t_mockup/cli.py` | 解析 `--shirt-color`、`--prepare-method`、`--for-black-shirt`、`--for-white-shirt` 并传给 core。 |
| `white_t_mockup/__init__.py` | 导出 `prepare_design_for_shirt`。 |
| `tests/test_prepare.py` | `prepare_design_for_shirt` 的单元测试。 |
| `tests/test_presets.py` | 新增 CLI 参数传递的回归测试。 |
| `docs/ARCHITECTURE.md` | 更新数据流图与核心函数表。 |
| `README.md` | 新增反黑/反白 CLI 示例。 |
| `CHANGELOG.md` | 记录新功能。 |

---

### Task 1: Implement `prepare_design_for_shirt` in `core.py`

**Files:**
- Modify: `white_t_mockup/core.py`
- Test: `tests/test_prepare.py`（在 Task 2 中编写，但本任务会先写失败测试再实现）

**Interfaces:**
- Produces: `prepare_design_for_shirt(design, shirt_color, method)` → `Image.Image`
- Produces: `_rgb_to_hsv(rgb)` → `np.ndarray`
- Produces: `_hsv_to_rgb(hsv)` → `np.ndarray`

- [ ] **Step 1: Add imports and helper functions**

在 `white_t_mockup/core.py` 顶部，现有 `import` 下方添加：

```python
from typing import Literal
```

在文件末尾追加 HSV 辅助函数与预处理函数：

```python
def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """
    将 RGB 数组（值域 [0, 1]）批量转换到 HSV（H 值域 [0, 1]）。
    """
    maxc = rgb.max(axis=-1)
    minc = rgb.min(axis=-1)
    delta = maxc - minc

    h = np.zeros_like(maxc)
    s = np.zeros_like(maxc)
    v = maxc

    nonzero = delta != 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    h = np.where(nonzero & (maxc == r), ((g - b) / delta) % 6, h)
    h = np.where(nonzero & (maxc == g), ((b - r) / delta) + 2, h)
    h = np.where(nonzero & (maxc == b), ((r - g) / delta) + 4, h)
    h = h / 6.0

    s = np.where(nonzero, delta / maxc, s)

    return np.stack([h, s, v], axis=-1)


def _hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    """
    将 HSV 数组（H 值域 [0, 1]）批量转回 RGB（值域 [0, 1]）。
    """
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    h = np.clip(h, 0.0, 1.0)
    s = np.clip(s, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    h6 = (h * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i

    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    r_candidates = np.stack([v, q, p, p, t, v], axis=-1)
    g_candidates = np.stack([t, v, v, q, p, p], axis=-1)
    b_candidates = np.stack([p, p, t, v, v, q], axis=-1)

    idx = i[..., None]
    r = np.take_along_axis(r_candidates, idx, axis=-1).squeeze(-1)
    g = np.take_along_axis(g_candidates, idx, axis=-1).squeeze(-1)
    b = np.take_along_axis(b_candidates, idx, axis=-1).squeeze(-1)

    return np.stack([r, g, b], axis=-1)


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
    if method == "none":
        return design.copy()

    arr = np.array(design).astype(np.float32)
    alpha = arr[:, :, 3]
    mask = alpha > 0

    if method == "silhouette":
        if shirt_color == "black":
            arr[mask, :3] = 255.0
        else:
            arr[mask, :3] = 0.0
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    # method == "value_invert"
    rgb = arr[:, :, :3].copy()
    rgb_norm = rgb / 255.0
    hsv = _rgb_to_hsv(rgb_norm)
    hsv[:, :, 2] = 1.0 - hsv[:, :, 2]
    rgb_inv = _hsv_to_rgb(hsv) * 255.0

    result = arr.copy()
    result[mask, :3] = rgb_inv[mask]
    return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGBA")
```

- [ ] **Step 2: Verify import succeeds**

Run:
```bash
python -c "from white_t_mockup.core import prepare_design_for_shirt; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add white_t_mockup/core.py
git commit -m "feat(core): add prepare_design_for_shirt with value_invert and silhouette"
```

---

### Task 2: Unit tests for `prepare_design_for_shirt`

**Files:**
- Create: `tests/test_prepare.py`

**Interfaces:**
- Consumes: `prepare_design_for_shirt(design, shirt_color, method)` from `core.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_prepare.py`：

```python
# -*- coding: utf-8 -*-
"""prepare_design_for_shirt 预处理单元测试。"""

import numpy as np
import pytest
from PIL import Image

from white_t_mockup.core import prepare_design_for_shirt


def _rgb_to_float(arr):
    return arr.astype(np.float32) / 255.0


def test_value_invert_preserves_hue_and_saturation():
    # 用一个纯色块：纯红
    design = Image.new("RGBA", (10, 10), (200, 50, 50, 255))
    result = prepare_design_for_shirt(design, "black", "value_invert")

    result_arr = np.array(result)
    # 色相应保持红色（R 最大）
    assert result_arr[:, :, 0].mean() > result_arr[:, :, 1].mean()
    assert result_arr[:, :, 0].mean() > result_arr[:, :, 2].mean()
    # 亮度应反转：原 R=200，反向后应接近 55
    assert result_arr[5, 5, 0] == pytest.approx(55, abs=3)


def test_value_invert_inverts_value():
    design = Image.new("RGBA", (10, 10), (100, 100, 100, 255))
    result = prepare_design_for_shirt(design, "black", "value_invert")
    result_arr = np.array(result)
    # 灰度 100 -> 亮度反相后约 155
    assert result_arr[5, 5, 0] == pytest.approx(155, abs=3)


def test_value_invert_preserves_alpha():
    design = Image.new("RGBA", (10, 10), (100, 100, 100, 128))
    result = prepare_design_for_shirt(design, "black", "value_invert")
    result_arr = np.array(result)
    assert result_arr[5, 5, 3] == 128


def test_value_invert_leaves_transparent_pixels_unchanged():
    design = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    design.load()[5, 5] = (255, 0, 0, 255)
    result = prepare_design_for_shirt(design, "black", "value_invert")
    result_arr = np.array(result)
    # 透明像素保持透明
    assert result_arr[0, 0, 3] == 0
    # 不透明像素被处理
    assert result_arr[5, 5, 3] == 255
    assert result_arr[5, 5, 0] == pytest.approx(0, abs=3)


def test_silhouette_black_shirt_makes_white():
    design = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
    result = prepare_design_for_shirt(design, "black", "silhouette")
    result_arr = np.array(result)
    assert np.all(result_arr[:, :, :3] == 255)
    assert np.all(result_arr[:, :, 3] == 255)


def test_silhouette_white_shirt_makes_black():
    design = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
    result = prepare_design_for_shirt(design, "white", "silhouette")
    result_arr = np.array(result)
    assert np.all(result_arr[:, :, :3] == 0)
    assert np.all(result_arr[:, :, 3] == 255)


def test_none_returns_copy():
    design = Image.new("RGBA", (10, 10), (123, 45, 67, 255))
    result = prepare_design_for_shirt(design, "black", "none")
    result_arr = np.array(result)
    assert np.all(result_arr[:, :, :3] == [123, 45, 67])
    assert np.all(result_arr[:, :, 3] == 255)
```

- [ ] **Step 2: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/test_prepare.py -v
```

Expected: 7 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_prepare.py
git commit -m "test(prepare): add tests for value_invert, silhouette and none"
```

---

### Task 3: Integrate preprocessing into `apply_mockup` and `apply_mockup_transform`

**Files:**
- Modify: `white_t_mockup/core.py`
- Test: `tests/test_core.py`, `tests/test_transform.py`

**Interfaces:**
- Consumes: `prepare_design_for_shirt(design, shirt_color, method)`
- Produces: `apply_mockup(..., shirt_color=None, prepare_method="value_invert")`
- Produces: `apply_mockup_transform(..., shirt_color=None, prepare_method="value_invert")`

- [ ] **Step 1: Modify `apply_mockup_transform`**

在 `white_t_mockup/core.py` 中找到 `apply_mockup_transform` 函数签名，改为：

```python
def apply_mockup_transform(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    scale: float,
    rotation_degrees: float,
    effective_top_y: int,
    effective_center_x: int,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
    shirt_color: Literal["black", "white"] | None = None,
    prepare_method: Literal["value_invert", "silhouette", "none"] = "value_invert",
) -> dict:
```

在函数体中，把：

```python
    design = Image.open(str(design_path)).convert("RGBA")
```

改为：

```python
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
```

- [ ] **Step 2: Modify `apply_mockup`**

在 `white_t_mockup/core.py` 中找到 `apply_mockup` 函数签名，改为：

```python
def apply_mockup(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    top_y: int,
    center_x: int,
    target_height: int,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
    shirt_color: Literal["black", "white"] | None = None,
    prepare_method: Literal["value_invert", "silhouette", "none"] = "value_invert",
) -> dict:
```

同样地，在打开设计图后添加预处理调用：

```python
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
```

- [ ] **Step 3: Update `white_t_mockup/__init__.py` 导出**

在 `white_t_mockup/__init__.py` 中：

```python
from .core import (
    apply_mockup,
    apply_mockup_transform,
    apply_transform,
    find_effective_bbox,
    load_any_template,
    load_png_template,
    load_template,
    paste_with_blend,
    prepare_design_for_shirt,
    resize_design,
)

__all__ = [
    "apply_mockup",
    "apply_mockup_transform",
    "apply_transform",
    "find_effective_bbox",
    "load_any_template",
    "load_png_template",
    "load_template",
    "paste_with_blend",
    "prepare_design_for_shirt",
    "resize_design",
]
```

- [ ] **Step 4: Add integration test in `tests/test_transform.py`**

在 `tests/test_transform.py` 末尾追加：

```python
def test_apply_mockup_transform_with_shirt_color_preparation(tmp_path):
    design = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
    design_path = tmp_path / "design.png"
    output_path = tmp_path / "out.jpg"
    design.save(design_path)

    # 用 PNG 模板，避免依赖外部 PSD
    template = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    template_path = tmp_path / "template.png"
    template.save(template_path)

    result = apply_mockup_transform(
        design_path=design_path,
        output_path=output_path,
        template_path=template_path,
        scale=1.0,
        rotation_degrees=0.0,
        effective_top_y=50,
        effective_center_x=100,
        blend_mode="normal",
        shirt_color="black",
        prepare_method="value_invert",
    )

    assert output_path.exists()
    assert result["output_size"] == (200, 200)

    # 黑设计经过 value_invert 后应变为亮色，混合到白底上应可见
    output = Image.open(output_path).convert("RGB")
    arr = np.array(output)
    # 中心区域应接近白色（亮度反相后的黑色）
    assert arr[50, 100, 0] > 200
```

- [ ] **Step 5: Run core and transform tests**

Run:
```bash
python -m pytest tests/test_core.py tests/test_transform.py tests/test_prepare.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add white_t_mockup/core.py white_t_mockup/__init__.py tests/test_transform.py
git commit -m "feat(core): integrate shirt-color preparation into mockup pipelines"
```

---

### Task 4: CLI arguments for shirt color and preparation method

**Files:**
- Modify: `white_t_mockup/cli.py`
- Test: `tests/test_presets.py`

**Interfaces:**
- Consumes: `apply_mockup(..., shirt_color, prepare_method)`
- Consumes: `apply_mockup_transform(..., shirt_color, prepare_method)`

- [ ] **Step 1: Add CLI arguments**

在 `white_t_mockup/cli.py` 的 `_build_parser` 函数中，在 `--quality` 参数之前（或之后）添加：

```python
    parser.add_argument(
        "--shirt-color",
        choices=["black", "white"],
        default=None,
        help="目标 T 恤颜色，启用预处理（反黑/反白）",
    )
    parser.add_argument(
        "--prepare-method",
        choices=["value_invert", "silhouette", "none"],
        default="value_invert",
        help="预处理方法（默认: value_invert）",
    )
    parser.add_argument(
        "--for-black-shirt",
        action="store_true",
        help="快捷开关：等价于 --shirt-color black --prepare-method value_invert",
    )
    parser.add_argument(
        "--for-white-shirt",
        action="store_true",
        help="快捷开关：等价于 --shirt-color white --prepare-method value_invert",
    )
```

- [ ] **Step 2: Resolve shortcut flags and pass to core**

在 `cli.main()` 中，解析 `args` 后、调用 `apply_mockup_*` 之前添加：

```python
    shirt_color = args.shirt_color
    prepare_method = args.prepare_method

    if args.for_black_shirt:
        shirt_color = "black"
        prepare_method = "value_invert"
    elif args.for_white_shirt:
        shirt_color = "white"
        prepare_method = "value_invert"
```

然后修改两处 `apply_mockup_transform` / `apply_mockup` 调用，增加参数：

```python
        result = apply_mockup_transform(
            ...,
            blend_mode=blend_mode,
            quality=quality,
            shirt_color=shirt_color,
            prepare_method=prepare_method,
        )
```

以及：

```python
        result = apply_mockup(
            ...,
            blend_mode=blend_mode,
            quality=quality,
            shirt_color=shirt_color,
            prepare_method=prepare_method,
        )
```

- [ ] **Step 3: Add CLI regression tests**

在 `tests/test_presets.py` 末尾追加：

```python
def test_cli_for_black_shirt_passes_params(monkeypatch, tmp_path):
    calls = []

    def fake_apply_mockup_transform(**kwargs):
        calls.append(kwargs)
        return _fake_transform_result(kwargs)

    monkeypatch.setattr(cli, "apply_mockup_transform", fake_apply_mockup_transform)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "white_t_mockup",
            "design.png",
            str(tmp_path / "out.jpg"),
            "--preset",
            "1B.png",
            "--for-black-shirt",
        ],
    )

    cli.main()

    assert len(calls) == 1
    assert calls[0]["shirt_color"] == "black"
    assert calls[0]["prepare_method"] == "value_invert"


def test_cli_shirt_color_and_prepare_method(monkeypatch, tmp_path):
    calls = []

    def fake_apply_mockup_transform(**kwargs):
        calls.append(kwargs)
        return _fake_transform_result(kwargs)

    monkeypatch.setattr(cli, "apply_mockup_transform", fake_apply_mockup_transform)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "white_t_mockup",
            "design.png",
            str(tmp_path / "out.jpg"),
            "--preset",
            "1B.png",
            "--shirt-color",
            "white",
            "--prepare-method",
            "silhouette",
        ],
    )

    cli.main()

    assert len(calls) == 1
    assert calls[0]["shirt_color"] == "white"
    assert calls[0]["prepare_method"] == "silhouette"
```

- [ ] **Step 4: Run preset tests**

Run:
```bash
python -m pytest tests/test_presets.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add white_t_mockup/cli.py tests/test_presets.py
git commit -m "feat(cli): add --shirt-color, --prepare-method and shortcut flags"
```

---

### Task 5: Update documentation

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update `docs/ARCHITECTURE.md`**

在“整体数据流”代码块中，在 `输入 PNG 设计图` 之后增加预处理节点：

```text
输入 PNG 设计图
    │
    ▼
[可选] prepare_design_for_shirt() ──▶ 亮度反相 / 剪影 / 无处理
    │
    ▼
resize_design() / apply_transform() ──▶ 缩放、旋转
```

在“核心函数”表格末尾新增一行：

```markdown
| `prepare_design_for_shirt()` | 根据目标 T 恤颜色预处理设计图：亮度反相、剪影或不做处理 |
```

在“模块职责”表格的 `core.py` 行末尾补充：

```markdown
| `core.py` | 模板加载（PSD/PNG）、缩放、旋转、有效像素定位、混合、**预处理**、合成等无状态函数 |
```

- [ ] **Step 2: Update `README.md`**

在 CLI 示例部分新增：

```markdown
### 反黑/反白预处理

新版默认使用亮度反相（HSV Value Invert），保留颜色，只反转明暗：

```bash
# 适合黑色 T 恤
python -m white_t_mockup design.png out.jpg --preset W4.png --for-black-shirt

# 适合白色 T 恤
python -m white_t_mockup design.png out.jpg --preset W4.png --for-white-shirt

# 显式选择预处理方法
python -m white_t_mockup design.png out.jpg --preset W4.png --shirt-color black --prepare-method value_invert

# 回滚到旧剪影模式
python -m white_t_mockup design.png out.jpg --preset W4.png --shirt-color black --prepare-method silhouette
```
```

- [ ] **Step 3: Update `CHANGELOG.md`**

在顶部新增：

```markdown
## [Unreleased]

### Added
- `prepare_design_for_shirt()`：支持 `value_invert`（亮度反相，保留色相/饱和度）、`silhouette`（黑白剪影）、`none`（无处理）。
- `apply_mockup()` 与 `apply_mockup_transform()` 新增 `shirt_color` 和 `prepare_method` 参数。
- CLI 新增 `--shirt-color`、`--prepare-method`、`--for-black-shirt`、`--for-white-shirt`。
```

- [ ] **Step 4: Commit**

```bash
git add docs/ARCHITECTURE.md README.md CHANGELOG.md
git commit -m "docs: update architecture, readme and changelog for shirt-color preparation"
```

---

### Task 6: Full verification and sample generation

**Files:**
- Uses: existing test suite and sample inputs

- [ ] **Step 1: Run full test suite**

Run:
```bash
python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 2: Generate a visual sample with the new method**

Run:
```bash
python -m white_t_mockup \
    "D:\Semems WB\02_PROJECTS\DX0030\02_REM_BG\DX0030_W_cut.png" \
    "psd_layers/_sample_value_invert_mockup.jpg" \
    --preset W4.png \
    --for-black-shirt
```

Expected: 文件生成成功，无报错。

- [ ] **Step 3: Commit**

```bash
git add psd_layers/_sample_value_invert_mockup.jpg
git commit -m "chore: add value-invert mockup sample"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Implementing Task |
|--------------|-------------------|
| 新增 `prepare_design_for_shirt()` | Task 1 |
| `value_invert` 算法 | Task 1 |
| `silhouette` 旧逻辑保留 | Task 1 |
| `none` 无处理 | Task 1 |
| 接入 `apply_mockup()` / `apply_mockup_transform()` | Task 3 |
| CLI 参数 | Task 4 |
| 测试策略 | Task 2, Task 3, Task 4 |
| 文档更新 | Task 5 |
| 兼容性（默认行为不变） | Task 3, Task 4 默认值设计 |
| 验收标准 | Task 6 |

### Placeholder Scan

- 无 `TBD` / `TODO` / "implement later"。
- 所有代码步骤均含完整代码块。
- 所有命令均含预期输出。
- 无 "similar to Task N" 引用。

### Type Consistency

- `prepare_design_for_shirt` 签名在 Task 1、Task 2、Task 3、Task 4 中一致。
- `shirt_color: Literal["black", "white"] | None` 与 `prepare_method: Literal["value_invert", "silhouette", "none"]` 在 core 与 CLI 中一致。
- `_fake_transform_result` 在 `tests/test_presets.py` 中未变，新增测试仍使用同一 helper。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-09-shirt-color-invert-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
