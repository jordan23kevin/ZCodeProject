# -*- coding: utf-8 -*-
"""白 T 恤样机贴图核心逻辑。"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
from psd_tools import PSDImage

from .config import DEFAULT_BLEND_MODE, SUPPORTED_BLEND_MODES


def load_template(psd_path: str | Path) -> Tuple[Image.Image, Image.Image, Tuple[int, int], Tuple[int, int]]:
    """
    加载 PSD 模板，返回背景层、前景层、前景层位置和画布尺寸。

    识别规则：
    - 占满整张画布的图层为背景（模特完整底图）
    - 小 bbox 的图层为手部前景遮罩
    """
    psd = PSDImage.open(str(psd_path))
    layers = list(psd)
    if len(layers) < 2:
        raise ValueError(f"模板至少需要 2 个图层，当前只有 {len(layers)} 个")

    canvas_bbox = (0, 0, psd.size[0], psd.size[1])
    bg_candidates = [layer for layer in layers if layer.bbox == canvas_bbox]
    fg_candidates = [layer for layer in layers if layer.bbox != canvas_bbox]

    if not bg_candidates or not fg_candidates:
        bg_layer = max(layers, key=lambda layer: (layer.size[0] * layer.size[1]))
        fg_layer = min(layers, key=lambda layer: (layer.size[0] * layer.size[1]))
    else:
        bg_layer = bg_candidates[0]
        fg_layer = fg_candidates[0]

    background = bg_layer.composite().convert("RGBA")
    foreground = fg_layer.composite().convert("RGBA")
    fg_position = fg_layer.bbox[:2]

    return background, foreground, fg_position, psd.size


def resize_design(design: Image.Image, target_height: int) -> Image.Image:
    """按目标高度等比缩放贴图，保持宽高比。"""
    w, h = design.size
    ratio = target_height / h
    new_size = (int(round(w * ratio)), target_height)
    return design.resize(new_size, Image.Resampling.LANCZOS)


def _apply_blend_mode(base: np.ndarray, blend: np.ndarray, mode: str) -> np.ndarray:
    """
    对 RGB 通道应用混合模式。

    base, blend: shape (H, W, 3), uint8
    """
    base_f = base.astype(np.float32) / 255.0
    blend_f = blend.astype(np.float32) / 255.0

    if mode == "multiply":
        result = base_f * blend_f
    elif mode == "screen":
        result = 1.0 - (1.0 - base_f) * (1.0 - blend_f)
    elif mode == "overlay":
        mask = base_f < 0.5
        result = np.empty_like(base_f)
        result[mask] = 2 * base_f[mask] * blend_f[mask]
        result[~mask] = 1.0 - 2 * (1.0 - base_f[~mask]) * (1.0 - blend_f[~mask])
    elif mode == "linear_burn":
        result = base_f + blend_f - 1.0
    else:
        raise ValueError(f"不支持的混合模式: {mode}")

    result = np.clip(result * 255, 0, 255).astype(np.uint8)
    return result


def paste_with_blend(
    canvas: Image.Image,
    design: Image.Image,
    position: Tuple[int, int],
    mode: str | None,
) -> None:
    """
    把贴图按指定混合模式贴到画布上。

    mode 为 None 或 "normal" 时使用普通 alpha 粘贴。
    """
    if mode is None or mode.lower() == "normal":
        canvas.paste(design, position, design)
        return

    mode = mode.lower()
    if mode not in SUPPORTED_BLEND_MODES:
        raise ValueError(f"不支持的混合模式: {mode}，可选: {SUPPORTED_BLEND_MODES}")

    cx, cy = position
    dw, dh = design.size
    cw, ch = canvas.size

    x1 = max(cx, 0)
    y1 = max(cy, 0)
    x2 = min(cx + dw, cw)
    y2 = min(cy + dh, ch)
    if x1 >= x2 or y1 >= y2:
        return

    base_region = canvas.crop((x1, y1, x2, y2)).convert("RGBA")
    design_region = design.crop((x1 - cx, y1 - cy, x2 - cx, y2 - cy))

    base_np = np.array(base_region)
    design_np = np.array(design_region)

    alpha = design_np[:, :, 3:4].astype(np.float32) / 255.0
    base_rgb = base_np[:, :, :3]
    design_rgb = design_np[:, :, :3]

    blended_rgb = _apply_blend_mode(base_rgb, design_rgb, mode)
    final_rgb = (blended_rgb * alpha + base_rgb * (1 - alpha)).astype(np.uint8)

    final_region = Image.fromarray(
        np.concatenate([final_rgb, base_np[:, :, 3:4]], axis=2), "RGBA"
    )
    canvas.paste(final_region, (x1, y1), final_region)


def calculate_design_position(
    design_size: Tuple[int, int],
    center_x: int,
    top_y: int,
) -> Tuple[int, int]:
    """根据中心 X 和顶部 Y 计算设计图左上角坐标。"""
    dw, _ = design_size
    left = int(round(center_x - dw / 2))
    return left, top_y


def apply_mockup(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    top_y: int,
    center_x: int,
    target_height: int,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
) -> dict:
    """
    将设计图贴到白 T 模板并导出 JPG。

    返回包含贴图参数的字典，便于测试和日志记录。
    """
    design = Image.open(str(design_path)).convert("RGBA")
    background, foreground, fg_position, canvas_size = load_template(template_path)

    design_resized = resize_design(design, target_height)
    dw, dh = design_resized.size

    left, top = calculate_design_position(design_resized.size, center_x, top_y)

    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    canvas.paste(background, (0, 0), background)
    paste_with_blend(canvas, design_resized, (left, top), blend_mode)
    canvas.paste(foreground, fg_position, foreground)

    canvas_rgb = canvas.convert("RGB")
    canvas_rgb.save(str(output_path), "JPEG", quality=quality, optimize=True)

    return {
        "output_size": canvas_rgb.size,
        "design_size": design_resized.size,
        "design_left": left,
        "design_top": top,
        "design_center": (center_x, top_y + dh // 2),
        "blend_mode": blend_mode or "normal",
    }
