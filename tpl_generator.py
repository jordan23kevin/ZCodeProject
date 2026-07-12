#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 white_t_mockup 模板生成 _tpl 扭曲/光影素材。

输入：PNG/JPG/PSD 模板源图
输出：_tpl/<款名>/
    - source.png    原图（参考用）
    - mask.png      印花/扭曲作用区域（L 模式）
    - disp.png      位移贴图（128=无偏移）
    - shadow.png    阴影（Multiply）
    - highlight.png 高光（Overlay）
    - occlusion.png 褶皱可见性/遮挡（255=可见，0=折入隐藏）
    - metadata.json 生成信息
    - _preview/mask_overlay.jpg  红色 mask 叠加预览

分割逻辑：根据中心区域亮度判断黑白 → 颜色/亮度先验 + GrabCut + 形态学清理。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

DEFAULT_TPL_ROOT = Path(r"D:\Semems\1胚衣\_tpl")
DEFAULT_PRESETS = Path(r"E:\Kimi Code\white_t_mockup\presets.json")
CSV_PATH = Path(r"E:\Kimi Code\docs\胚衣参数表_模板.csv")


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------
def _read_image(path: Path) -> np.ndarray | None:
    """兼容中文路径的图像读取：先 cv2，失败转 PIL。"""
    img = cv2.imread(str(path))
    if img is not None:
        return img
    try:
        pil = Image.open(str(path)).convert("RGB")
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def _save_image(path: Path, img: np.ndarray) -> None:
    """兼容中文路径的保存。灰度图直接存，BGR 转 RGB 存。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if img.ndim == 2:
        Image.fromarray(img).save(str(path))
    else:
        Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(str(path))


def load_source_image(path: Path) -> Tuple[np.ndarray, Path]:
    """加载源图。PSD 会优先使用同目录同名 PNG/JPG。"""
    if path.suffix.lower() == ".psd":
        for ext in (".png", ".jpg", ".jpeg"):
            raster = path.with_suffix(ext)
            if raster.exists():
                img = _read_image(raster)
                if img is not None:
                    return img, raster
        raise NotImplementedError(
            f"PSD 未找到同名 PNG/JPG: {path}\n"
            "请在该目录放一个同名的 PNG/JPG 作为源图。"
        )
    img = _read_image(path)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img, path


# ---------------------------------------------------------------------------
# 颜色判断
# ---------------------------------------------------------------------------
def detect_shirt_color(gray: np.ndarray) -> str:
    """根据中心 crop 的平均亮度判断黑/白/未知。"""
    h, w = gray.shape
    y0, y1 = max(0, h // 2 - h // 6), min(h, h // 2 + h // 6)
    x0, x1 = max(0, w // 2 - w // 6), min(w, w // 2 + w // 6)
    crop = gray[y0:y1, x0:x1]
    mean_l = float(crop.mean())
    if mean_l < 100:
        return "black"
    if mean_l > 180:
        return "white"
    return "unknown"


# ---------------------------------------------------------------------------
# 分割
# ---------------------------------------------------------------------------
def _keep_centered_component(mask: np.ndarray, cyx: Tuple[int, int] | None = None) -> np.ndarray:
    """保留包含/最接近图像中心的连通域（T 恤通常位于画面中心）。"""
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels <= 1:
        return mask
    h, w = mask.shape
    if cyx is None:
        cy, cx = h // 2, w // 2
    else:
        cy, cx = cyx
    best_label = 1
    best_score = float("inf")
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area < 100:
            continue
        y, x = centroids[label]
        dist = (y - cy) ** 2 + (x - cx) ** 2
        if dist < best_score:
            best_score = dist
            best_label = label
    return (labels == best_label).astype(np.uint8)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """填充 mask 内部空洞（纯 OpenCV/numpy 实现，无需 scipy）。

    原理：对反色 mask 从边界 floodFill，未被填充到的内部区域即为空洞。
    """
    if mask.sum() == 0:
        return mask
    h, w = mask.shape
    inv = cv2.bitwise_not(mask)
    flood = np.zeros((h + 2, w + 2), np.uint8)
    flood[1:-1, 1:-1] = inv
    cv2.floodFill(flood, None, (0, 0), 255)
    holes = cv2.bitwise_not(flood[1:-1, 1:-1])
    return cv2.bitwise_or(mask, holes)


def segment_shirt(img_bgr: np.ndarray) -> Tuple[np.ndarray, str]:
    """分割 T 恤主体，返回 L 模式 mask (0/255) 和颜色提示。"""
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("empty image")

    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    l = lab[:, :, 0]

    color_hint = detect_shirt_color(l)
    h, w = l.shape

    # ---- 1. 颜色先验：得到大致的 T 恤区域 ----
    # 白/未知：用中心颜色距离，比单一亮度更能区分白 T 和暖色背景
    # 黑：用亮度，但只作为辅助参考（避免短裤等暗物混入）
    if color_hint == "black":
        thr = np.percentile(l, 40)
        color_mask = (l < thr).astype(np.uint8)
    else:
        y0, y1 = int(h * 0.20), int(h * 0.80)
        x0, x1 = int(w * 0.20), int(w * 0.80)
        center_color = lab[y0:y1, x0:x1].mean(axis=(0, 1))
        dist = np.linalg.norm(lab - center_color, axis=2)
        thr = np.percentile(dist, 50)
        color_mask = (dist < thr).astype(np.uint8)

    # 颜色先验轻度清理
    kernel_3 = np.ones((3, 3), np.uint8)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel_3, iterations=1)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel_3, iterations=2)

    # ---- 2. 中心矩形：T 恤一定在画面中心，放较宽但避开下方腿部/桌面 ----
    rect_mask = np.zeros_like(color_mask)
    y0, y1 = int(h * 0.15), int(h * 0.75)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    rect_mask[y0:y1, x0:x1] = 1

    # ---- 3. GrabCut 精修 ----
    gc_mask = np.full_like(color_mask, cv2.GC_PR_BGD, dtype=np.uint8)
    # 白/未知：颜色先验作为可能前景；黑 T 只信任中心矩形（避免把短裤也扩进来）
    if color_hint in ("white", "unknown"):
        gc_mask[color_mask == 1] = cv2.GC_PR_FGD
    gc_mask[rect_mask == 1] = cv2.GC_FGD

    margin = max(2, min(h, w) // 60)
    gc_mask[:margin, :] = cv2.GC_BGD
    gc_mask[-margin:, :] = cv2.GC_BGD
    gc_mask[:, :margin] = cv2.GC_BGD
    gc_mask[:, -margin:] = cv2.GC_BGD

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb, gc_mask, None, bgd, fgd, iterCount=5, mode=cv2.GC_INIT_WITH_MASK)

    mask = np.where(
        (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 1, 0
    ).astype(np.uint8)

    # ---- 4. 后处理：保留中心组件、填洞、缩放到 0/255、平滑 ----
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    mask = _fill_holes(mask)
    mask = _keep_centered_component(mask)

    mask = (mask * 255).astype(np.uint8)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    return mask, color_hint


# ---------------------------------------------------------------------------
# 贴图生成
# ---------------------------------------------------------------------------
def compute_shading_maps(
    img_bgr: np.ndarray, mask: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """从原图推导 disp / shadow / highlight。"""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray = cv2.bilateralFilter(gray.astype(np.uint8), 9, 75, 75).astype(np.float32)

    m = (mask > 128).astype(np.float32)
    inside = gray[m > 0]
    if inside.size == 0:
        inside = np.array([128.0])

    median = float(np.median(inside))
    std = max(float(np.std(inside)), 20.0)

    # disp: 以 128 为中心，按亮度偏移
    disp = (gray - median) / std * 32.0 + 128.0
    disp = np.clip(disp, 0, 255).astype(np.uint8)
    disp = (disp * m + 128 * (1 - m)).astype(np.uint8)

    # shadow: 原图亮度，暗处会让 Multiply 更暗
    shadow = np.clip(gray, 0, 255).astype(np.uint8)
    shadow = (shadow * m + 255 * (1 - m)).astype(np.uint8)

    # highlight: 中心化，亮处提亮、暗处压暗（Overlay 对比增强）
    highlight = (gray - median) * 1.5 + 128.0
    highlight = np.clip(highlight, 0, 255).astype(np.uint8)
    highlight = (highlight * m + 128 * (1 - m)).astype(np.uint8)

    return disp, shadow, highlight


def compute_occlusion_map(
    img_bgr: np.ndarray,
    mask: np.ndarray,
    hide_strength: float = 0.85,
) -> np.ndarray:
    """生成褶皱可见性/遮挡图 occlusion.png（L 模式，255=完全可见，0=折入隐藏）。

    原理：真实布料的大褶皱是「折进衣服内部」的深凹沟，其表面图案会被前方布料
    挡住而看不见。这类褶皱在照片里表现为「比周围明显更暗的窄暗线（暗谷）」。
    本函数用「局部亮度基准 − 实际亮度」估计每个像素的凹陷深度：
        groove = 局部亮度均值 − 该像素亮度   （>0 表示比周围暗，即处于凹谷）
    仅对最深的一小部分暗谷（褶皱折入处）降低可见性，越深越透明；平缓的明暗
    变化（普通光影）保持完全可见，交给 disp/shadow/highlight 处理。

    与 disp 的区别：disp 只「挪动」图案（亮度位移），从不隐藏；本图专门负责
    「褶皱折入处图案消失」，两者互补。
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray = cv2.bilateralFilter(gray.astype(np.uint8), 9, 50, 50).astype(np.float32)

    m = (mask > 128).astype(np.float32)
    if m.sum() == 0:
        return np.full(gray.shape, 255, dtype=np.uint8)

    h, w = gray.shape
    # 大尺度高斯得到「局部亮度基准」，用 mask 加权避免背景亮度渗入
    k = max(31, (min(h, w) // 12) | 1)  # 奇数核
    g_sum = cv2.GaussianBlur(gray * m, (k, k), 0)
    w_sum = cv2.GaussianBlur(m, (k, k), 0) + 1e-6
    local = g_sum / w_sum

    groove = local - gray  # >0：比局部基准暗 = 处于凹谷/褶皱折入
    groove[m <= 0] = 0.0

    inside = groove[m > 0]
    t_lo = float(np.percentile(inside, 80))   # 仅最深 ~20% 的暗谷开始淡出
    t_hi = float(np.percentile(inside, 98))   # 最深 ~2% 淡到最透明
    t_hi = max(t_hi, t_lo + 1.0)

    gn = np.clip((groove - t_lo) / (t_hi - t_lo), 0.0, 1.0)
    occ = 1.0 - gn * float(hide_strength)     # 谷越深，可见度越低
    occ = occ * m + 1.0 * (1.0 - m)           # mask 外恒为完全可见（该处本无图案）
    occ = cv2.GaussianBlur(occ, (0, 0), sigmaX=2.0)  # 柔化边缘，淡出自然
    return np.clip(occ * 255.0, 0, 255).astype(np.uint8)


def strengthen_occlusion(
    disp: np.ndarray,
    occ: np.ndarray,
    threshold: float = 0.30,
    disp_scale: float = 1.6,
    occ_scale: float = 2.0,
    smooth: float = 80.0,
) -> np.ndarray:
    """深褶隐藏加强（2026-07-12 方案2·全隐藏，黑W10 实测拍板）。

    基础 occlusion 偏保守（印花区内深隐藏常 <2%），大褶皱折入处贴图仍可见、
    不真实。本函数在生成阶段自动加强：
        褶皱深度 = max(|平滑80后的disp − 128| / 128 × disp_scale,
                       (255 − occ) / 255 × occ_scale)
        深度 > threshold 处贴图完全隐藏，边缘高斯羽化 8（不生硬）；
        浅褶/布纹（高频）被 sigma80 平滑滤除，不参与隐藏也不扭曲。
    同款离线脚本：~/.workbuddy/skills/white-t-mockup-tpl-gen/scripts/
    strengthen_occlusion.py（用于给存量 _tpl 补加强，参数须与此处一致）。
    """
    disp_f = disp.astype(np.float32)
    occ_f = occ.astype(np.float32)
    disp_s = cv2.GaussianBlur(disp_f, (0, 0), smooth)
    depth_disp = np.abs(disp_s - 128.0) / 128.0 * disp_scale
    depth_occ = np.clip((255.0 - occ_f) / 255.0 * occ_scale, 0, 1)
    depth = np.clip(np.maximum(depth_disp, depth_occ), 0, 1)
    depth = cv2.GaussianBlur(depth, (0, 0), 6)
    hard = (depth < threshold).astype(np.float32)
    vis = cv2.GaussianBlur(hard, (0, 0), 8)
    return np.clip(vis * 255.0, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 预览
# ---------------------------------------------------------------------------
def build_preview(img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    red = np.full_like(img_bgr, (0, 0, 255))
    alpha = (mask > 128).astype(np.float32) * 0.4
    alpha_3ch = np.stack([alpha] * 3, axis=-1)
    preview = (
        img_bgr.astype(np.float32) * (1 - alpha_3ch)
        + red.astype(np.float32) * alpha_3ch
    ).astype(np.uint8)
    return preview


# ---------------------------------------------------------------------------
# 主生成函数
# ---------------------------------------------------------------------------
def generate_for_source(
    source_path: Path, out_dir: Path
) -> Tuple[Path, float, str]:
    img, raster_path = load_source_image(source_path)
    mask, color_hint = segment_shirt(img)
    disp, shadow, highlight = compute_shading_maps(img, mask)
    occlusion = strengthen_occlusion(disp, compute_occlusion_map(img, mask))

    out_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = out_dir / "_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    _save_image(out_dir / "source.png", img)
    _save_image(out_dir / "mask.png", mask)
    _save_image(out_dir / "disp.png", disp)
    _save_image(out_dir / "shadow.png", shadow)
    _save_image(out_dir / "highlight.png", highlight)
    _save_image(out_dir / "occlusion.png", occlusion)

    preview = build_preview(img, mask)
    _save_image(preview_dir / "mask_overlay.jpg", preview)

    coverage = float(mask[mask > 128].size) / float(mask.size)
    m_bool = mask > 128
    occ_hidden = float(((occlusion < 200) & m_bool).sum()) / float(max(m_bool.sum(), 1))
    meta = {
        "source": str(raster_path.resolve()),
        "size": [int(img.shape[1]), int(img.shape[0])],
        "method": "color_prior+grabcut+morphology (OpenCV, offline)",
        "color_hint": color_hint,
        "mask_coverage": round(coverage, 3),
        "occlusion_fold_ratio": round(occ_hidden, 3),
        "needs_manual_fix": coverage < 0.1 or coverage > 0.8,
        "note": "自动分割，请按 _preview/mask_overlay.jpg 检查；如有背景渗入或 T 恤缺失，用 PS 修正 mask.png 后重新运行脚本。",
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_dir, coverage, color_hint


# ---------------------------------------------------------------------------
# 按 preset 名生成
# ---------------------------------------------------------------------------
def preset_stem(name: str, presets_path: Path = DEFAULT_PRESETS) -> str:
    """返回 preset 对应的 _tpl 名（模板文件名去后缀）。"""
    presets = json.loads(Path(presets_path).read_text(encoding="utf-8"))
    if name not in presets.get("templates", {}):
        raise KeyError(f"preset 不存在: {name}")
    return Path(presets["templates"][name]["path"]).stem


def generate_for_preset(
    name: str,
    presets_path: Path = DEFAULT_PRESETS,
    tpl_root: Path = DEFAULT_TPL_ROOT,
) -> Tuple[Path, float, str]:
    """按 preset 名生成单个模板的 _tpl 素材（覆盖式，便于重算）。

    返回 (输出目录, coverage, color_hint)。
    """
    presets = json.loads(Path(presets_path).read_text(encoding="utf-8"))
    if name not in presets.get("templates", {}):
        raise KeyError(
            f"preset 不存在: {name}；可用: {sorted(presets.get('templates', {}).keys())}"
        )
    path = Path(presets["templates"][name]["path"])
    out = Path(tpl_root) / path.stem
    return generate_for_source(path, out)


# ---------------------------------------------------------------------------
# 为素材库图片生成 _tpl（接「胚衣制作·素材库」的「生成遮罩」按钮）
# ---------------------------------------------------------------------------
def _find_template_for_stem(stem: str) -> Path | None:
    """在胚衣参数表 CSV 中按「胚衣文件名」的 stem 匹配，返回其「胚衣完整路径」。

    优先用 CSV 里的模板原图作为 _tpl 源——它与 white_t_mockup 贴图时用的背景是
    同一张，褶皱扭曲最精准对齐。找不到或文件不存在则返回 None。
    """
    if not CSV_PATH.exists():
        return None
    try:
        text = CSV_PATH.read_text(encoding="utf-8-sig")
        delim = ";" if ";" in text[:2000] else ","
        rows = [r for r in csv.reader(text.splitlines(), delimiter=delim) if r]
        if len(rows) < 2:
            return None
        norm = lambda h: re.sub(r"[（(].*?[）)]", "", (h or "").strip()).strip()
        hdr = [norm(h) for h in rows[0]]
        try:
            i_name = hdr.index("胚衣文件名")
            i_path = hdr.index("胚衣完整路径")
        except ValueError:
            return None
        for r in rows[1:]:
            if len(r) <= max(i_name, i_path):
                continue
            if Path(r[i_name].strip()).stem == stem:
                p = Path(r[i_path].strip())
                if p.exists():
                    return p
    except Exception:
        return None
    return None


def generate_tpl_for_material(
    image_path: str | Path,
    tpl_root: Path = DEFAULT_TPL_ROOT,
) -> Tuple[Path, float, str, Path]:
    """为素材库图片生成 _tpl/<款名>/ 扭曲素材。

    优先用胚衣参数表里的模板原图（与贴图背景一致），找不到则退回素材库图片本身。
    返回 (输出目录, coverage, color_hint, 实际使用的源图路径)。
    """
    image_path = Path(image_path)
    stem = image_path.stem
    src = _find_template_for_stem(stem) or image_path
    out = Path(tpl_root) / stem
    out_dir, cov, hint = generate_for_source(src, out)
    return out_dir, cov, hint, src


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _batch_from_presets(tpl_root: Path) -> None:
    presets = json.loads(DEFAULT_PRESETS.read_text(encoding="utf-8"))
    templates = sorted(presets["templates"].keys())

    for name in templates:
        info = presets["templates"][name]
        path = Path(info["path"])
        out = tpl_root / path.stem
        if out.exists() and (out / "mask.png").exists():
            # 已存在则跳过（含手工精修的 黑W5 样板，不覆盖）
            print(f"SKIP (exists): {name}")
            continue
        try:
            out, cov, hint = generate_for_source(path, out)
            print(f"OK {name}: {hint} coverage={cov:.3f} -> {out}")
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="生成 white_t_mockup 的 _tpl 扭曲素材（离线/CPU 可跑）"
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="源图路径（PNG/JPG/PSD），不传则处理 presets.json 里所有模板",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_TPL_ROOT,
        help=f"输出目录，默认 {DEFAULT_TPL_ROOT}",
    )
    args = parser.parse_args()

    if args.source:
        src = Path(args.source)
        out = args.out_dir / src.stem
        out, cov, hint = generate_for_source(src, out)
        print(f"已生成: {out}\n  color_hint={hint} coverage={cov:.3f}")
    else:
        _batch_from_presets(args.out_dir)


if __name__ == "__main__":
    main()
