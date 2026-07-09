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
