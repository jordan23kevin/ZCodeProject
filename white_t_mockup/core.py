# -*- coding: utf-8 -*-
"""白 T 恤样机贴图核心逻辑。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Tuple

import numpy as np
from PIL import Image
from psd_tools import PSDImage

from .config import DEFAULT_BLEND_MODE, SUPPORTED_BLEND_MODES

# ---- PS 水平缩放复现校准（统一算法）----
# CSV/presets 里的 scale 含义 = Photoshop 自由变换「水平(W)」百分比（如 30 = 30%）。
# 标定来源（用户定义的统一算法）：2048x2048 cut 置入 PS，水平填 30% 实际显示 544x602。
# 故所有款统一：显示 = cut整图 x (scale * PS_SCALE_KX, scale * PS_SCALE_KY)（非等比）。
#   PS_SCALE_KX = 544 / (2048*0.30) = 0.8854166667  （水平）
#   PS_SCALE_KY = 602 / (2048*0.30) = 0.9798177083  （垂直；PS 里 W/H 未锁比例）
# 用户在 CSV「缩放百分比」列填每款的水平 W%，代码按此统一比例出图。
PS_SCALE_KX = 0.8854166666666666
PS_SCALE_KY = 0.9798177083333333


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


def load_png_template(png_path: str | Path) -> Tuple[Image.Image, None, None, Tuple[int, int]]:
    """
    加载 PNG 模板，返回背景层、前景层（None）、前景位置（None）和画布尺寸。

    PNG 模板是单图层图片，没有手部遮罩。
    """
    background = Image.open(str(png_path)).convert("RGBA")
    return background, None, None, background.size


def load_any_template(
    template_path: str | Path,
) -> Tuple[Image.Image, Image.Image | None, Tuple[int, int] | None, Tuple[int, int]]:
    """自动识别 PSD 或 PNG 模板并加载。"""
    path = Path(template_path)
    if path.suffix.lower() == ".psd":
        return load_template(template_path)
    return load_png_template(template_path)


def apply_transform(
    design: Image.Image,
    scale: float,
    rotation_degrees: float,
) -> Image.Image:
    """
    对设计图做缩放和旋转。

    scale: 缩放比例，例如 0.40 表示 40%
    rotation_degrees: 顺时针旋转角度（正值为顺时针）
    """
    w, h = design.size
    new_size = (int(round(w * scale)), int(round(h * scale)))
    resized = design.resize(new_size, Image.Resampling.LANCZOS)
    # PIL 正角度为逆时针，顺时针需取负
    rotated = resized.rotate(-rotation_degrees, expand=True, resample=Image.Resampling.BICUBIC)
    return rotated


def apply_transform_ps(
    design: Image.Image,
    scale: float,
    rotation_degrees: float,
    kx: float | None = None,
    ky: float | None = None,
) -> Image.Image:
    """
    复现 Photoshop 自由变换「水平(W)百分比」的贴图缩放（非等比）。

    scale: PS 水平百分比（0.20 = 20%）。内部按 kx/ky 把 cut 整图非等比缩放，
           使贴图有效大小与 PS 里填同一百分比的效果一致。
    kx/ky: 每款的水平/垂直校准系数；None 时回退到全局默认 PS_SCALE_KX/PS_SCALE_KY。
           标定方法：kx = PS显示宽 / (cut整图宽 * scale)，ky 同理。
    rotation_degrees: 顺时针旋转角度（正值为顺时针）。
    """
    kx = PS_SCALE_KX if kx is None else kx
    ky = PS_SCALE_KY if ky is None else ky
    w, h = design.size
    new_size = (
        int(round(w * scale * kx)),
        int(round(h * scale * ky)),
    )
    resized = design.resize(new_size, Image.Resampling.LANCZOS)
    # PIL 正角度为逆时针，顺时针需取负
    return resized.rotate(-rotation_degrees, expand=True, resample=Image.Resampling.BICUBIC)


def find_effective_bbox(image: Image.Image, alpha_threshold: int = 10) -> Tuple[int, int, int, int]:
    """
    找出图像中有效（非透明）像素的边界框。

    返回 (left, top, right, bottom)。
    """
    arr = np.array(image)
    if arr.shape[2] < 4:
        # 无 alpha 通道，整个图像都是有效像素
        return (0, 0, image.width - 1, image.height - 1)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > alpha_threshold)
    if len(xs) == 0:
        return (0, 0, image.width - 1, image.height - 1)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def calculate_effective_position(
    transformed: Image.Image,
    effective_top_y: int,
    effective_center_x: int,
    alpha_threshold: int = 10,
) -> Tuple[int, int, Tuple[int, int, int, int]]:
    """
    根据有效像素的最高点和中心点计算粘贴左上角坐标。

    返回 (paste_x, paste_y, effective_bbox)。
    """
    left, top, right, bottom = find_effective_bbox(transformed, alpha_threshold)

    paste_y = effective_top_y - top
    bbox_center_x = (left + right) / 2
    paste_x = int(round(effective_center_x - bbox_center_x))

    return paste_x, paste_y, (left, top, right, bottom)


def apply_mockup_transform(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    scale: float,
    rotation_degrees: float,
    effective_top_y: int,
    effective_center_x: int,
    kx: float | None = None,
    ky: float | None = None,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
    shirt_color: Literal["black", "white"] | None = None,
    prepare_method: Literal["value_invert", "silhouette", "none"] = "value_invert",
) -> dict:
    """
    新版贴图方法：缩放 → 旋转 → 按有效像素定位 → 混合。

    支持 PSD 和 PNG 两种模板。
    """
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
    background, foreground, fg_position, canvas_size = load_any_template(template_path)

    transformed = apply_transform_ps(design, scale, rotation_degrees, kx, ky)
    paste_x, paste_y, effective_bbox = calculate_effective_position(
        transformed, effective_top_y, effective_center_x
    )

    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    canvas.paste(background, (0, 0), background)
    paste_with_blend(canvas, transformed, (paste_x, paste_y), blend_mode)
    if foreground is not None and fg_position is not None:
        canvas.paste(foreground, fg_position, foreground)

    canvas_rgb = canvas.convert("RGB")
    canvas_rgb.save(str(output_path), "JPEG", quality=quality, optimize=True)

    return {
        "output_size": canvas_rgb.size,
        "design_size": transformed.size,
        "design_left": paste_x,
        "design_top": paste_y,
        "effective_bbox": effective_bbox,
        "effective_top": effective_top_y,
        "effective_center_x": effective_center_x,
        "scale": scale,
        "rotation_degrees": rotation_degrees,
        "blend_mode": blend_mode or "normal",
    }


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
    """
    将设计图贴到白 T 模板并导出 JPG。

    返回包含贴图参数的字典，便于测试和日志记录。
    """
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
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

    with np.errstate(divide="ignore", invalid="ignore"):
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

    if method == "value_invert":
        rgb = arr[:, :, :3].copy()
        rgb_norm = rgb / 255.0
        hsv = _rgb_to_hsv(rgb_norm)
        hsv[:, :, 2] = 1.0 - hsv[:, :, 2]
        rgb_inv = _hsv_to_rgb(hsv) * 255.0

        result = arr.copy()
        result[mask, :3] = rgb_inv[mask]
        return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGBA")

    raise ValueError(f"不支持的预处理方法: {method}")
