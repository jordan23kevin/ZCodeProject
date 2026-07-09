# -*- coding: utf-8 -*-
"""white_t_mockup 新版 transform 方法单元测试。"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from white_t_mockup import __version__
from white_t_mockup.core import (
    apply_mockup_transform,
    apply_transform,
    calculate_effective_position,
    find_effective_bbox,
    load_any_template,
    load_png_template,
)


def test_version_bumped():
    assert __version__ == "1.2.1"


def test_apply_transform_scales_correctly():
    design = Image.new("RGBA", (1000, 500), (255, 0, 0, 255))
    transformed = apply_transform(design, scale=0.40, rotation_degrees=0)
    assert transformed.size == (400, 200)


def test_apply_transform_rotates_clockwise():
    # 创建一个顶部有标记的图，旋转后标记应在右侧
    design = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    pixels = design.load()
    for y in range(10):
        for x in range(45, 55):
            pixels[x, y] = (255, 0, 0, 255)

    transformed = apply_transform(design, scale=1.0, rotation_degrees=90)
    arr = np.array(transformed)
    # 顺时针 90° 后，原来顶部中心的红点应跑到右侧
    ys, xs = np.where(arr[:, :, 3] > 10)
    assert xs.mean() > transformed.width / 2


def test_find_effective_bbox_with_transparent():
    design = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    pixels = design.load()
    for y in range(30, 70):
        for x in range(20, 80):
            pixels[x, y] = (255, 0, 0, 255)

    bbox = find_effective_bbox(design)
    assert bbox == (20, 30, 79, 69)


def test_find_effective_bbox_no_alpha():
    design = Image.new("RGB", (100, 100), (255, 0, 0))
    bbox = find_effective_bbox(design)
    assert bbox == (0, 0, 99, 99)


def test_calculate_effective_position():
    # 有效像素在 (20, 30) 到 (79, 69)
    design = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    pixels = design.load()
    for y in range(30, 70):
        for x in range(20, 80):
            pixels[x, y] = (255, 0, 0, 255)

    paste_x, paste_y, bbox = calculate_effective_position(
        design, effective_top_y=490, effective_center_x=780
    )
    assert paste_y == 490 - 30  # top 对齐到 490
    assert paste_x == 780 - int(round((20 + 79) / 2))


def test_load_png_template():
    template_path = Path(r"D:\Semems\1胚衣\白\1B.png")
    if not template_path.exists():
        pytest.skip("PNG 模板不存在，跳过此测试")

    with Image.open(template_path) as template_image:
        expected_canvas_size = template_image.size

    background, foreground, fg_position, canvas_size = load_png_template(template_path)
    assert canvas_size == expected_canvas_size
    assert foreground is None
    assert fg_position is None


def test_load_any_template_png():
    template_path = Path(r"D:\Semems\1胚衣\白\1B.png")
    if not template_path.exists():
        pytest.skip("PNG 模板不存在，跳过此测试")

    with Image.open(template_path) as template_image:
        expected_canvas_size = template_image.size

    background, foreground, fg_position, canvas_size = load_any_template(template_path)
    assert canvas_size == expected_canvas_size
    assert foreground is None


def test_apply_mockup_transform_with_png_template():
    template_path = Path(r"D:\Semems\1胚衣\白\1B.png")
    design_path = Path("examples/dx0533/input/DX0533_BW_cut.png")
    output_path = Path("tests/_test_transform_output.jpg")

    if not template_path.exists() or not design_path.exists():
        pytest.skip("模板或示例输入不存在，跳过此测试")

    with Image.open(template_path) as template_image:
        expected_output_size = template_image.size

    result = apply_mockup_transform(
        design_path=design_path,
        output_path=output_path,
        template_path=template_path,
        scale=0.40,
        rotation_degrees=0.0,
        effective_top_y=725,
        effective_center_x=649,
        blend_mode="multiply",
        quality=95,
    )

    assert result["output_size"] == expected_output_size
    assert result["scale"] == 0.40
    assert result["rotation_degrees"] == 0.0
    assert result["effective_top"] == 725
    assert result["effective_center_x"] == 649
    assert output_path.exists()

    output_path.unlink(missing_ok=True)


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


def test_apply_mockup_transform_with_white_shirt_preparation(tmp_path):
    design = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
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
        shirt_color="white",
        prepare_method="value_invert",
    )

    assert output_path.exists()
    assert result["output_size"] == (200, 200)

    # 白设计经过 value_invert 后应变为暗色，混合到白底上中心区域应可见深色
    output = Image.open(output_path).convert("RGB")
    arr = np.array(output)
    # 中心区域应接近黑色（亮度反相后的白色）
    assert arr[50, 100, 0] < 50
