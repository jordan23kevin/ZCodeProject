# -*- coding: utf-8 -*-
"""白 T 恤样机贴图核心逻辑。

v1.6.2 (2026-07-12) 褶皱贴合增强：
  - apply_displacement 新增 mask_feather（默认 5px），对 mask 边缘高斯羽化，
    使位移在印花边界平滑衰减到 0，配合更大 disp_strength 也不产生边界折叠/撕裂。

v1.6.1 (2026-07-12) 褶皱低频化：
  - apply_displacement 新增 smooth（默认 80）+ dead_zone（默认 15，软斜坡）。
  - smooth 只保留大褶皱形变，抑制小褶皱/布纹水波纹；dead_zone 让小起伏区域
    几乎不扭曲，软斜坡消除旧硬死区导致的重映射折叠撕裂。

v1.6.0 (2026-07-12) 黑衫显色重构：
  - 新增 prepare_method="white_underbase"（黑衫默认）：自适应浓度白墨打底
    add_white_underbase + 轻度暗部提亮 enhance_dark_print_for_black_shirt，
    组合为 black_shirt_print_optimize。模拟真实 DTG 黑衫『先喷白墨再喷彩色』，
    使极暗区域在黑布上可见，同时保留全部原色、不漂白。
  - 保留旧 prepare_method：dark_boost（仅提亮暗部）、value_invert / silhouette
    （旧反相/剪影，已不推荐）。白衫 white_underbase/dark_boost 均为 no-op。
  - 根因记录：旧『反黑』把非透明像素涂纯白(silhouette)或 HSV 明度反相
    (value_invert)，导致颜色全丢/亮色变黑；且 PS 贴图(place_design.jsx)从不铺
    白底，纯黑设计印黑布物理不可见。white_underbase 在贴图前把白墨打底烘进
    设计图本身，无需改 PS 脚本即可显色。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Tuple

import numpy as np
from PIL import Image

# psd_tools 为可选依赖：仅在处理 PSD 模板时需要。
# 离线/未安装环境下，PNG 模板仍可正常贴图（含 _tpl 扭曲管线）。
try:
    from psd_tools import PSDImage
except ImportError:  # pragma: no cover - 离线环境无 psd_tools
    PSDImage = None

from .config import DEFAULT_BLEND_MODE, SUPPORTED_BLEND_MODES

# ---- PS 缩放复现（final 像素模型）----
# 每款在 CSV 直接填贴图最终像素「缩放后宽px/缩放后高px」（PS 里贴图层缩放后的 final_w/final_h），
# 代码把贴图直接 resize 到 (final_w, final_h)；原图固定 2048×2048，final 即目标像素，100% 复现 PS。


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
        if PSDImage is None:
            raise ImportError(
                "处理 PSD 模板需要 psd_tools，但当前环境未安装。"
                "请改用 PNG 模板，或安装：pip install psd-tools"
            )
        return load_template(template_path)
    return load_png_template(template_path)


def _paste_occluder_top(canvas: Image.Image, occluder_path) -> Image.Image:
    """把生成的遮挡物 RGBA（最上层）盖到画布最上方，与画布同尺寸对齐。

    遮挡物来自胚衣遮罩（peiyi_mask.generate_masks 产出的 *_occluder.png），
    其像素坐标系与原始胚衣图一致；当画布尺寸不一致时自动缩放对齐。
    """
    occ = Image.open(str(occluder_path)).convert("RGBA")
    if occ.size != canvas.size:
        occ = occ.resize(canvas.size, Image.Resampling.LANCZOS)
    canvas.paste(occ, (0, 0), occ)
    return canvas


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
    final_w: int,
    final_h: int,
    rotation_degrees: float,
) -> Image.Image:
    """
    复现 Photoshop 贴图最终大小：直接把贴图 resize 到 (final_w, final_h) 再旋转。

    final_w/final_h: 贴图最终像素（PS 里贴图层缩放后的宽×高，原图固定 2048×2048）。
    rotation_degrees: 顺时针旋转角度（正值为顺时针，负值为逆时针，同 PS）。
    """
    resized = design.resize((int(final_w), int(final_h)), Image.Resampling.LANCZOS)
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


def apply_realism(design, *, saturation=0.97, brightness=1.0, blur_radius=0.4):
    """印花真实感：微降饱和、边缘柔化（模拟丝印 + 纤维扩散）。

    关键：边缘柔化采用【预乘 alpha 感知模糊】——先按 alpha 预乘再模糊再还原，
    避免透明底（RGB≈中灰）在模糊时渗入不透明的白字/浅色印花，从而不会把印花
    整体染灰、变暗。brightness 默认 1.0（不再统一压暗印花，保持色彩鲜亮）。
    """
    from PIL import ImageEnhance, ImageFilter
    d = design
    if saturation != 1.0:
        d = ImageEnhance.Color(d).enhance(saturation)
    if brightness != 1.0:
        d = ImageEnhance.Brightness(d).enhance(brightness)
    if blur_radius and blur_radius > 0:
        arr = np.array(d.convert("RGBA")).astype(np.float32)
        a = arr[:, :, 3:4] / 255.0
        pm = arr.copy()
        pm[:, :, :3] *= a  # 预乘：透明区 RGB 归零，不再污染
        blurred = Image.fromarray(
            np.clip(pm, 0, 255).astype(np.uint8), "RGBA"
        ).filter(ImageFilter.GaussianBlur(blur_radius))
        parr = np.array(blurred).astype(np.float32)
        pa = parr[:, :, 3:4] / 255.0
        pa[pa == 0] = 1.0
        parr[:, :, :3] = np.clip(parr[:, :, :3] / pa, 0, 255)  # 还原（非预乘）
        d = Image.fromarray(parr.astype(np.uint8), "RGBA")
    return d


def overlay_texture(canvas, background, design, paste_x, paste_y, *, mode="multiply", opacity=0.25):
    """把 background 的明暗纹理限印花区域、以 mode 混合、opacity 透明叠到 canvas（布纹/褶皱透出）。"""
    dw, dh = design.size
    cw, ch = canvas.size
    x0, y0 = paste_x, paste_y
    bx0, by0 = max(x0, 0), max(y0, 0)
    bx1, by1 = min(x0 + dw, cw), min(y0 + dh, ch)
    if bx0 >= bx1 or by0 >= by1:
        return
    bg_gray = background.crop((bx0, by0, bx1, by1)).convert("L").convert("RGBA")
    mask = design.crop((bx0 - x0, by0 - y0, bx1 - x0, by1 - y0)).split()[3]
    bg_arr = np.array(bg_gray)
    a = (np.array(mask).astype(np.float32) * opacity).astype(np.uint8)
    bg_arr[:, :, 3] = a
    tex = Image.fromarray(bg_arr, "RGBA")
    paste_with_blend(canvas, tex, (bx0, by0), mode)


def _remap_channels(arr: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    """向量化双线性重采样。arr:(H,W,C) float；map_x/map_y:(H,W) 源采样坐标。"""
    h, w = map_x.shape
    x0 = np.floor(map_x).astype(np.int32)
    y0 = np.floor(map_y).astype(np.int32)
    x1, y1 = x0 + 1, y0 + 1
    x0c = np.clip(x0, 0, w - 1)
    x1c = np.clip(x1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y1, 0, h - 1)
    wx = (map_x - x0)[..., None]
    wy = (map_y - y0)[..., None]
    Ia = arr[y0c, x0c]
    Ib = arr[y0c, x1c]
    Ic = arr[y1c, x0c]
    Id = arr[y1c, x1c]
    return Ia * (1 - wx) * (1 - wy) + Ib * wx * (1 - wy) + Ic * (1 - wx) * wy + Id * wx * wy


def apply_displacement(
    design: Image.Image,
    disp: Image.Image,
    mask: Image.Image,
    paste_x: int,
    paste_y: int,
    strength: float = 8.0,
    smooth: float = 80.0,
    dead_zone: float = 15.0,
    mask_feather: float = 5.0,
) -> Image.Image:
    """
    按置换图 disp（画布尺寸 L 模式）对 design 做形变，限 mask 区域。

    disp 灰度 128=不偏移，>128 向 +，<128 向 -；strength 为最大像素偏移。
    mask=0 处不偏移。各向同性（x/y 同灰度偏移）。paste_x/paste_y 为 design 在画布的左上角。

    smooth: 对 disp 做大尺度高斯平滑（sigma 像素）后再取偏移——只保留大褶皱形变，
            抹掉小褶皱/布纹等高频分量，消除印花"水波纹"抖动。0=不平滑（旧行为）。
    dead_zone: 灰度死区。|g-128| < dead_zone 的区域 off 平滑趋零（软斜坡），
            小起伏区域几乎不扭曲；边界为平滑过渡，避免硬台阶导致重映射折叠/撕裂。
    mask_feather: 对 mask 边缘做高斯羽化（sigma 像素），使位移在 mask 边界处
            平滑衰减到 0，避免 mask 硬边造成重映射折叠/设计边缘撕裂。0=不羽化。
    """
    dw, dh = design.size
    arr = np.array(design).astype(np.float32)
    disp_arr = np.array(disp.convert("L")).astype(np.float32)
    mask_arr = np.array(mask.convert("L")).astype(np.float32) / 255.0
    H, W = disp_arr.shape

    # 对 mask 边缘羽化：位移在边界平滑衰减，消除 mask 硬边带来的折叠/撕裂
    if mask_feather and mask_feather > 0:
        import cv2
        mask_arr = cv2.GaussianBlur(mask_arr, (0, 0), float(mask_feather))

    # 低频化：只让大褶皱参与位移（sigma 越大，保留的褶皱尺度越大）
    if smooth and smooth > 0:
        import cv2
        disp_arr = cv2.GaussianBlur(disp_arr, (0, 0), float(smooth))

    yy, xx = np.mgrid[0:dh, 0:dw].astype(np.float32)
    cx = np.clip(paste_x + xx, 0, W - 1).astype(np.int32)
    cy = np.clip(paste_y + yy, 0, H - 1).astype(np.int32)
    g = disp_arr[cy, cx]
    m = mask_arr[cy, cx]
    # 软死区：|g-128| 在 dead_zone 内时 off 随距离平滑趋零（不再硬置 0）。
    # 旧版硬死区在 |g-128|=dead_zone 处从 0 突跳到 (dead_zone/128)*strength（strength=30 时
    # 约 3.5px/像素），使重映射 d(off)/dx>1 发生折叠(fold-over)，文字在 128±dead_zone
    # 轮廓线上被对折/重影，表现为「上下撕裂」。软斜坡彻底消除该台阶，褶皱位移量不变。
    if dead_zone and dead_zone > 0:
        d = np.abs(g - 128.0)
        ramp = np.clip(d / float(dead_zone), 0.0, 1.0)
        g = 128.0 + (g - 128.0) * ramp
    off = (g - 128.0) / 128.0 * strength * m
    map_x = xx - off
    map_y = yy - off

    out = _remap_channels(arr, map_x, map_y)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def apply_occlusion_alpha(
    design: Image.Image,
    occ: Image.Image,
    paste_x: int,
    paste_y: int,
    strength: float = 1.0,
) -> Image.Image:
    """按遮挡图 occ（画布尺寸 L，255=完全可见，0=折入隐藏）降低 design 的 alpha。

    真实布料的大褶皱折入内部，其表面图案被前方布料挡住而看不见。occ 图标出这些
    折入区域，本函数据此把 design 对应位置的 alpha 拉低，使贴图在褶皱处自然淡出/
    消失，仅在褶皱之外正常显示。strength=1.0 完全按 occ 隐藏，0 则不隐藏。
    """
    dw, dh = design.size
    arr = np.array(design).astype(np.float32)
    occ_arr = np.array(occ.convert("L")).astype(np.float32) / 255.0
    H, W = occ_arr.shape

    yy, xx = np.mgrid[0:dh, 0:dw]
    cx = np.clip(paste_x + xx, 0, W - 1).astype(np.int32)
    cy = np.clip(paste_y + yy, 0, H - 1).astype(np.int32)
    vis = occ_arr[cy, cx]
    if strength < 1.0:
        vis = 1.0 - (1.0 - vis) * float(strength)
    arr[:, :, 3] = arr[:, :, 3] * vis
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def transfer_shadow_highlight(
    canvas: Image.Image,
    design: Image.Image,
    paste_x: int,
    paste_y: int,
    mask: Image.Image,
    shadow: Image.Image | None,
    highlight: Image.Image | None,
    *,
    shadow_opacity: float = 0.35,
    highlight_opacity: float = 0.25,
) -> None:
    """
    把衣服暗部(shadow, Multiply)与亮边(highlight, Overlay)转移到 canvas 的印花区域。

    强度 = 印花alpha × (mask/255) × opacity。shadow/highlight 为画布尺寸 L 模式，None 则跳过。
    直接改 canvas（in-place）。
    """
    if shadow is None and highlight is None:
        return
    dw, dh = design.size
    cw, ch = canvas.size
    bx0, by0 = max(paste_x, 0), max(paste_y, 0)
    bx1, by1 = min(paste_x + dw, cw), min(paste_y + dh, ch)
    if bx0 >= bx1 or by0 >= by1:
        return

    region = canvas.crop((bx0, by0, bx1, by1)).convert("RGBA")
    reg_np = np.array(region).astype(np.float32)
    base_rgb = reg_np[:, :, :3]

    dmask = design.crop((bx0 - paste_x, by0 - paste_y, bx1 - paste_x, by1 - paste_y)).split()[3]
    alpha = np.array(dmask).astype(np.float32) / 255.0
    mask_crop = mask.crop((bx0, by0, bx1, by1)).convert("L")
    m = np.array(mask_crop).astype(np.float32) / 255.0
    strength_base = alpha * m

    if shadow is not None and shadow_opacity > 0:
        s = np.array(shadow.crop((bx0, by0, bx1, by1)).convert("L")).astype(np.float32) / 255.0
        # 归一化为【相对褶皱阴影】：以印花区内平坦布料(高百分位)为基准=不压暗，
        # 只保留“褶皱比平坦暗”的相对结构。避免黑衣绝对暗度(中位~0.13)整体压灰印花。
        sel = strength_base > 0.05
        ref = np.percentile(s[sel], 85) if sel.any() else 1.0
        if ref < 1e-3:
            ref = 1.0
        s = np.clip(s / ref, 0.0, 1.0)
        # 相对阴影再设下限，最深褶皱最多压到 SHADOW_FLOOR，防止细缝把印花打穿成黑
        SHADOW_FLOOR = 0.55
        s = SHADOW_FLOOR + (1.0 - SHADOW_FLOOR) * s
        s3 = s[..., None]
        st = (strength_base * shadow_opacity)[..., None]
        mul = base_rgb * s3  # multiply
        base_rgb = base_rgb * (1 - st) + mul * st

    if highlight is not None and highlight_opacity > 0:
        h = np.array(highlight.crop((bx0, by0, bx1, by1)).convert("L")).astype(np.float32) / 255.0
        h3 = h[..., None]
        b = base_rgb / 255.0
        ov = np.where(b < 0.5, 2 * b * h3, 1 - 2 * (1 - b) * (1 - h3)) * 255.0
        st = (strength_base * highlight_opacity)[..., None]
        base_rgb = base_rgb * (1 - st) + ov * st

    reg_np[:, :, :3] = np.clip(base_rgb, 0, 255)
    out = Image.fromarray(reg_np.astype(np.uint8), "RGBA")
    canvas.paste(out, (bx0, by0), out)


def _load_tpl_optional(tpl_dir: Path, name: str, canvas_size: Tuple[int, int]):
    """加载模板衍生图（L 模式，对齐 canvas 尺寸），不存在返回 None。"""
    p = tpl_dir / name
    if not p.exists():
        return None
    im = Image.open(str(p)).convert("L")
    if im.size != canvas_size:
        im = im.resize(canvas_size, Image.Resampling.LANCZOS)
    return im


def apply_mockup_transform(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    final_w: int,
    final_h: int,
    rotation_degrees: float,
    effective_top_y: int,
    effective_center_x: int,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
    shirt_color: Literal["black", "white"] | None = None,
    prepare_method: Literal["value_invert", "silhouette", "none", "dark_boost", "white_underbase"] = "white_underbase",
    realism: bool = True,
    saturation: float = 0.97,
    brightness: float = 1.0,
    blur_radius: float = 0.4,
    texture_mode: str = "multiply",
    texture_opacity: float = 0.25,
    tpl_dir: str | Path | None = None,
    disp_strength: float = 8.0,
    disp_smooth: float = 80.0,
    disp_dead_zone: float = 15.0,
    disp_mask_feather: float = 5.0,
    shadow_opacity: float = 0.22,
    highlight_opacity: float = 0.22,
    occluder: str | Path | None = None,
    occlusion_strength: float = 1.0,
) -> dict:
    """
    新版贴图方法：resize 到最终像素 → 旋转 → 按有效像素定位 → 混合。

    支持 PSD/PNG 模板；tpl_dir 含 mask.png 时启用模板管线：
    displacement(disp，限 mask) → occlusion(褶皱折入隐藏) → shadow(Multiply) +
    highlight(Overlay) 转移，限印花∩衣服区。
    disp_smooth/disp_dead_zone：位移低频化（只保留大褶皱）+ 小起伏死区，防水波纹。
    """
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
    background, foreground, fg_position, canvas_size = load_any_template(template_path)

    transformed = apply_transform_ps(design, final_w, final_h, rotation_degrees)
    paste_x, paste_y, effective_bbox = calculate_effective_position(
        transformed, effective_top_y, effective_center_x
    )

    mask_im = disp_im = shadow_im = highlight_im = occ_im = None
    if tpl_dir:
        td = Path(tpl_dir)
        mask_im = _load_tpl_optional(td, "mask.png", canvas_size)
        if mask_im is not None:
            disp_im = _load_tpl_optional(td, "disp.png", canvas_size)
            shadow_im = _load_tpl_optional(td, "shadow.png", canvas_size)
            highlight_im = _load_tpl_optional(td, "highlight.png", canvas_size)
            occ_im = _load_tpl_optional(td, "occlusion.png", canvas_size)
    use_tpl = mask_im is not None
    used_occlusion = False

    if use_tpl and disp_im is not None:
        transformed = apply_displacement(
            transformed, disp_im, mask_im, paste_x, paste_y, disp_strength,
            smooth=disp_smooth, dead_zone=disp_dead_zone,
            mask_feather=disp_mask_feather,
        )

    if use_tpl and occ_im is not None and occlusion_strength > 0:
        transformed = apply_occlusion_alpha(
            transformed, occ_im, paste_x, paste_y, occlusion_strength
        )
        used_occlusion = True

    if realism:
        transformed = apply_realism(
            transformed, saturation=saturation, brightness=brightness, blur_radius=blur_radius
        )

    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    canvas.paste(background, (0, 0), background)
    paste_with_blend(canvas, transformed, (paste_x, paste_y), blend_mode)

    if use_tpl:
        transfer_shadow_highlight(
            canvas, transformed, paste_x, paste_y, mask_im, shadow_im, highlight_im,
            shadow_opacity=shadow_opacity, highlight_opacity=highlight_opacity,
        )
    elif realism:
        overlay_texture(
            canvas, background, transformed, paste_x, paste_y,
            mode=texture_mode, opacity=texture_opacity,
        )

    if foreground is not None and fg_position is not None:
        canvas.paste(foreground, fg_position, foreground)

    # 最上层：生成的遮挡物（手/头发/配饰），自然盖在印花图案之上
    if occluder is not None:
        canvas = _paste_occluder_top(canvas, occluder)

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
        "final_w": final_w,
        "final_h": final_h,
        "rotation_degrees": rotation_degrees,
        "blend_mode": blend_mode or "normal",
        "template_pipeline": use_tpl,
        "occluder_applied": occluder is not None,
        "occlusion_applied": used_occlusion,
    }


def apply_mockup(
    design_path: str | Path,
    output_path: str | Path,
    template_path: str | Path,
    top_y: int,
    center_x: int,
    final_w: int,
    final_h: int,
    blend_mode: str | None = DEFAULT_BLEND_MODE,
    quality: int = 95,
    shirt_color: Literal["black", "white"] | None = None,
    prepare_method: Literal["value_invert", "silhouette", "none", "dark_boost", "white_underbase"] = "white_underbase",
    tpl_dir: str | Path | None = None,
    disp_strength: float = 8.0,
    disp_smooth: float = 80.0,
    disp_dead_zone: float = 15.0,
    disp_mask_feather: float = 5.0,
    shadow_opacity: float = 0.22,
    highlight_opacity: float = 0.22,
    occluder: str | Path | None = None,
    occlusion_strength: float = 1.0,
) -> dict:
    """
    旧版贴图方法：resize 到最终像素 → 按顶部/中心定位 → 混合 → 盖手部遮罩（仅 PSD）。

    tpl_dir 含 mask.png 时启用模板管线：displacement(disp) + occlusion(褶皱折入隐藏)
    + shadow/highlight 转移。返回包含贴图参数的字典，便于测试和日志记录。
    """
    design = Image.open(str(design_path)).convert("RGBA")
    if shirt_color is not None:
        design = prepare_design_for_shirt(design, shirt_color, prepare_method)
    background, foreground, fg_position, canvas_size = load_template(template_path)

    design_resized = design.resize((int(final_w), int(final_h)), Image.Resampling.LANCZOS)
    dw, dh = design_resized.size
    left, top = calculate_design_position(design_resized.size, center_x, top_y)

    mask_im = disp_im = shadow_im = highlight_im = occ_im = None
    if tpl_dir:
        td = Path(tpl_dir)
        mask_im = _load_tpl_optional(td, "mask.png", canvas_size)
        if mask_im is not None:
            disp_im = _load_tpl_optional(td, "disp.png", canvas_size)
            shadow_im = _load_tpl_optional(td, "shadow.png", canvas_size)
            highlight_im = _load_tpl_optional(td, "highlight.png", canvas_size)
            occ_im = _load_tpl_optional(td, "occlusion.png", canvas_size)
    use_tpl = mask_im is not None
    used_occlusion = False

    if use_tpl and disp_im is not None:
        design_resized = apply_displacement(
            design_resized, disp_im, mask_im, left, top, disp_strength,
            smooth=disp_smooth, dead_zone=disp_dead_zone,
            mask_feather=disp_mask_feather,
        )

    if use_tpl and occ_im is not None and occlusion_strength > 0:
        design_resized = apply_occlusion_alpha(
            design_resized, occ_im, left, top, occlusion_strength
        )
        used_occlusion = True

    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    canvas.paste(background, (0, 0), background)
    paste_with_blend(canvas, design_resized, (left, top), blend_mode)

    if use_tpl:
        transfer_shadow_highlight(
            canvas, design_resized, left, top, mask_im, shadow_im, highlight_im,
            shadow_opacity=shadow_opacity, highlight_opacity=highlight_opacity,
        )

    canvas.paste(foreground, fg_position, foreground)

    # 最上层：生成的遮挡物（手/头发/配饰），自然盖在印花图案之上
    if occluder is not None:
        canvas = _paste_occluder_top(canvas, occluder)

    canvas_rgb = canvas.convert("RGB")
    canvas_rgb.save(str(output_path), "JPEG", quality=quality, optimize=True)

    return {
        "output_size": canvas_rgb.size,
        "design_size": design_resized.size,
        "design_left": left,
        "design_top": top,
        "design_center": (center_x, top_y + dh // 2),
        "blend_mode": blend_mode or "normal",
        "template_pipeline": use_tpl,
        "occluder_applied": occluder is not None,
        "occlusion_applied": used_occlusion,
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


def enhance_dark_print_for_black_shirt(
    design: Image.Image,
    dark_boost: float = 0.55,
    protect_threshold: int = 140,
    min_brightness: int = 20,
    sat_compensation: float = 0.3,
    smooth_radius: int = 9,
) -> Image.Image:
    """
    黑衫智能显色：仅提亮暗部、完整保留原色，模拟数码印花白墨打底效果。

    内部自动完成 PIL RGBA <-> OpenCV BGRA 双向转换，调用方直接传 PIL Image，
    从根源避免红蓝互换的静默错误。对全透明 / 空图直接返回原图，不崩、不产废图。

    :param design: 透明底 RGBA 设计图（PIL Image）
    :param dark_boost: 暗部提亮强度 0~1，越大暗部越亮，黑衫推荐 0.45~0.65
    :param protect_threshold: 亮部保护阈值 0~255，高于此亮度的像素完全不改动
    :param min_brightness: 极暗保底亮度 0~255，纯黑图案强制提到此亮度，避免融进黑布
    :param sat_compensation: 饱和度补偿 0~1，避免提亮后色彩发灰
    :param smooth_radius: 权重过渡平滑半径（自动取整为奇数），越大过渡越柔和
    :return: 增强后的 RGBA 图像（PIL Image）
    """
    if design is None:
        return design
    if design.mode != "RGBA":
        design = design.convert("RGBA")
    arr = np.array(design)
    if arr.size == 0:
        return design

    # 仅本函数需要 OpenCV：懒加载，避免影响其它预处理与模块导入
    import cv2

    # PIL RGBA -> OpenCV BGRA
    bgra = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    bgr = bgra[..., :3].copy()
    alpha = bgra[..., 3].astype(np.float32) / 255.0

    valid_mask = alpha > 0.01
    if not np.any(valid_mask):
        return design  # 全透明，无需处理

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0]
    A = lab[..., 1]
    B = lab[..., 2]

    L_norm = L / 255.0
    thresh_norm = protect_threshold / 255.0

    # 暗部权重遮罩：越暗权重越高，亮部为 0；再乘 alpha，透明区权重强制为 0
    weight = np.clip((thresh_norm - L_norm) / thresh_norm, 0.0, 1.0)
    weight = weight * alpha

    # 鲁棒性：smooth_radius 强制奇数，杜绝 GaussianBlur 参数报错
    sr = int(round(smooth_radius)) | 1
    if sr < 1:
        sr = 1
    weight = cv2.GaussianBlur(weight, (sr, sr), 0)
    weight = np.clip(weight, 0.0, 1.0)

    # 暗部伽马提亮（幅度仅由 dark_boost 控制，与权重解耦；下限防 nan）
    target_gamma = max(0.15, 1.0 - dark_boost * 0.7)
    L_boosted = 255.0 * np.power(L_norm, target_gamma)

    # 极暗保底：纯黑/极暗像素强制提到 min_brightness，避免融进黑布
    min_mask = (L < min_brightness) & valid_mask
    L_boosted[min_mask] = np.maximum(L_boosted[min_mask], min_brightness)
    L_boosted = np.clip(L_boosted, 0.0, 255.0)

    # 加权融合：暗部用提亮值，亮部完全保留原始值
    L_final = L * (1 - weight) + L_boosted * weight

    # 饱和度补偿：仅在被提亮区域增强，亮部原色 100% 保留
    sat_gain = 1.0 + sat_compensation * weight
    A_final = (A - 128.0) * sat_gain + 128.0
    B_final = (B - 128.0) * sat_gain + 128.0
    A_final = np.clip(A_final, 0.0, 255.0)
    B_final = np.clip(B_final, 0.0, 255.0)

    lab_final = np.stack([L_final, A_final, B_final], axis=-1).astype(np.uint8)
    bgr_final = cv2.cvtColor(lab_final, cv2.COLOR_LAB2BGR)

    # OpenCV BGRA -> PIL RGBA
    bgra_final = np.dstack([bgr_final, (alpha * 255).astype(np.uint8)])
    rgba_final = cv2.cvtColor(bgra_final, cv2.COLOR_BGRA2RGBA)
    return Image.fromarray(rgba_final, "RGBA")


def add_white_underbase(
    design: Image.Image,
    max_white_opacity: float = 0.9,
    min_white_opacity: float = 0.05,
    transition_threshold: int = 130,
    edge_feather: int = 5,
    boost_sat: float = 0.35,
) -> Image.Image:
    """自适应浓度白墨打底（黑衫显色）：越暗白墨越厚，亮/饱和色保留原色。

    模拟真实 DTG 黑衫印花『先喷白墨、再喷彩色』工序，使极暗区域在黑布上可见，
    同时避免全铺白底导致的颜色漂白。内部完成 PIL↔数组转换，调用方直接传 PIL Image。
    """
    if getattr(design, "mode", None) != "RGBA":
        design = design.convert("RGBA")
    import cv2  # 懒加载，与其它预处理保持一致
    arr = np.array(design)
    rgb = arr[..., :3].astype(np.float32)
    alpha = arr[..., 3].astype(np.float32) / 255.0
    valid = alpha > 0.01
    if not valid.any():
        return design
    rgb_u = rgb.astype(np.uint8)
    gray = cv2.cvtColor(rgb_u, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_u, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[..., 1] / 255.0
    th = transition_threshold / 255.0
    white_mask = np.clip((th - gray) / th, 0.0, 1.0)            # 越暗越 1
    white_alpha = min_white_opacity + white_mask * (max_white_opacity - min_white_opacity)
    white_alpha = white_alpha * alpha
    if edge_feather > 0:
        k = int(edge_feather) * 2 + 1
        white_alpha = cv2.GaussianBlur(white_alpha, (k, k), 0)
    white_alpha = np.clip(white_alpha, 0.0, 1.0)
    white = np.ones_like(rgb) * 255.0
    # 保留色相：暗但饱和的颜色多保留原色，避免漂成纯白
    keep = np.clip(gray + boost_sat * sat, 0.0, 1.0)
    color_on_white = white * (1 - keep)[..., None] + rgb * keep[..., None]
    final = rgb * (1 - white_alpha)[..., None] + color_on_white * white_alpha[..., None]
    final = np.clip(final, 0, 255).astype(np.uint8)
    out = np.dstack([final, (alpha * 255).astype(np.uint8)])
    return Image.fromarray(out, "RGBA")


def black_shirt_print_optimize(design: Image.Image) -> Image.Image:
    """黑衫终极显色流水线：自适应白墨打底 + 轻度暗部提亮 + 饱和补偿。"""
    step1 = add_white_underbase(design)
    step2 = enhance_dark_print_for_black_shirt(
        step1, dark_boost=0.25, protect_threshold=160, min_brightness=20, sat_compensation=0.2
    )
    return step2


def prepare_design_for_shirt(
    design: Image.Image,
    shirt_color: Literal["black", "white"],
    method: Literal["value_invert", "silhouette", "none", "dark_boost", "white_underbase"] = "white_underbase",
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

    if method == "dark_boost":
        if shirt_color == "white":
            # 白衫对称方案暂未实现，保持原色不处理
            return design.copy()
        return enhance_dark_print_for_black_shirt(design)

    if method == "white_underbase":
        if shirt_color == "white":
            # 白衫无需白墨打底，保持原色
            return design.copy()
        # 黑衫默认：自适应白墨打底 + 轻度暗部提亮，极暗区域也能显色
        return black_shirt_print_optimize(design)

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
