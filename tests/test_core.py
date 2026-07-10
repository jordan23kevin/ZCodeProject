# -*- coding: utf-8 -*-
"""white_t_mockup 核心函数单元测试。"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from white_t_mockup import __version__
from white_t_mockup.config import DEFAULT_CENTER_X, DEFAULT_TARGET_HEIGHT, DEFAULT_TOP_Y
from white_t_mockup.core import (
    apply_mockup,
    calculate_design_position,
    load_template,
    paste_with_blend,
    resize_design,
)


def test_version():
    assert __version__ == "1.2.2"


def test_resize_design_maintains_aspect_ratio():
    design = Image.new("RGBA", (1000, 500), (255, 0, 0, 255))
    resized = resize_design(design, 250)
    assert resized.size == (500, 250)


def test_calculate_design_position():
    left, top = calculate_design_position((600, 700), center_x=735, top_y=449)
    assert left == 435
    assert top == 449


def test_blend_mode_multiply():
    canvas = Image.new("RGBA", (100, 100), (200, 200, 200, 255))
    design = Image.new("RGBA", (100, 100), (128, 128, 128, 128))

    paste_with_blend(canvas, design, (0, 0), "multiply")

    result = np.array(canvas)
    # Multiply: 200 * 128 / 255 ≈ 100; alpha blend with 0.5 -> ~150
    expected = int(100 * 0.5 + 200 * 0.5)
    assert result[50, 50, 0] == pytest.approx(expected, abs=2)


def test_paste_normal_with_full_alpha():
    canvas = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
    design = Image.new("RGBA", (50, 50), (0, 0, 255, 255))

    paste_with_blend(canvas, design, (25, 25), None)

    result = np.array(canvas)
    assert result[40, 40, 2] == 255  # 蓝色区域
    assert result[10, 10, 2] == 255  # 原背景白色


def test_load_template_returns_correct_layers():
    template_path = Path(r"D:\Semems\1胚衣\白\W3.psd")
    if not template_path.exists():
        pytest.skip("模板文件不存在，跳过此测试")

    background, foreground, fg_position, canvas_size = load_template(template_path)

    assert canvas_size == (1340, 1785)
    assert background.size == canvas_size
    assert foreground.size == (683, 370)
    assert fg_position == (657, 1011)


def test_apply_mockup_output_size():
    template_path = Path(r"D:\Semems\1胚衣\白\W3.psd")
    design_path = Path("examples/dx0533/input/DX0533_BW_cut.png")
    output_path = Path("tests/_test_output.jpg")

    if not template_path.exists() or not design_path.exists():
        pytest.skip("模板或示例输入不存在，跳过此测试")

    result = apply_mockup(
        design_path=design_path,
        output_path=output_path,
        template_path=template_path,
        top_y=DEFAULT_TOP_Y,
        center_x=DEFAULT_CENTER_X,
        target_height=DEFAULT_TARGET_HEIGHT,
        blend_mode="multiply",
        quality=95,
    )

    assert result["output_size"] == (1340, 1785)
    assert result["design_size"][1] == DEFAULT_TARGET_HEIGHT
    assert result["design_center"] == (DEFAULT_CENTER_X, DEFAULT_TOP_Y + DEFAULT_TARGET_HEIGHT // 2)
    assert output_path.exists()

    # 清理
    output_path.unlink(missing_ok=True)
