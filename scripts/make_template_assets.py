# -*- coding: utf-8 -*-
"""从合成模特图自动生成模板管线素材（mask/disp/shadow/highlight）。

用法：
    python scripts/make_template_assets.py --src "D:/Semems/1胚衣/黑/黑W5.png"
    # 输出到 D:/Semems/1胚衣/_tpl/黑W5/

分割优先 GrabCut + 暗度先验（OpenCV），不修改 core.py / cli.py，只生成素材。
分割质量不足不会停止：输出当前 mask，并在 metadata.json 标记需人工修正位置。
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


def segment_shirt(img_rgb: Image.Image):
    """GrabCut 矩形 + 暗度先验分割黑色 T 恤，返回 (mask_L, gray)。"""
    import cv2

    arr = np.array(img_rgb.convert("RGB"))
    h, w = arr.shape[:2]
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # 矩形包住 T 恤主体（相对坐标），框外为确定背景
    rect = (int(0.07 * w), int(0.13 * h), int(0.86 * w), int(0.72 * h))
    gc = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    fg = np.where((gc == 2) | (gc == 0), 0, 1).astype(np.uint8)

    # 暗度先验：前景必须偏暗（去除手臂/皮肤/亮背景）
    dark = (gray < 95).astype(np.uint8)
    fg = (fg & dark).astype(np.uint8)

    # 排除头顶头发区（与黑T同色，硬性排除顶部）
    top = np.zeros((h, w), np.uint8)
    top[: int(0.20 * h), :] = 1
    fg = (fg & (1 - top)).astype(np.uint8)

    # 形态学闭+开，取位于躯干中心的最大连通域
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    fg2 = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k, iterations=2)
    fg2 = cv2.morphologyEx(
        fg2, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    )
    num, labels, stats, _ = cv2.connectedComponentsWithStats(fg2, connectivity=8)
    out = fg2
    if num > 1:
        best, besta = 0, 0
        for i in range(1, num):
            a = stats[i, cv2.CC_STAT_AREA]
            cx = stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] / 2
            if a > besta and abs(cx - w / 2) < 0.3 * w:
                besta, best = a, i
        if best:
            out = (labels == best).astype(np.uint8)

    out = cv2.GaussianBlur(out, (5, 5), 0)
    return (out * 255).astype(np.uint8), gray


def make_disp(img_rgb: Image.Image, mask: Image.Image) -> Image.Image:
    """mask 区内灰度做局部对比增强保留褶皱，区外填 128（PS Displacement 中性）。"""
    import cv2

    g = np.array(img_rgb.convert("L"))
    m = (np.array(mask) > 127).astype(np.float32)
    ge = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    ge = cv2.GaussianBlur(ge, (3, 3), 0)
    disp = (ge.astype(np.float32) * m + 128.0 * (1 - m)).astype(np.uint8)
    return Image.fromarray(disp, "L")


def make_shadow(img_rgb: Image.Image, mask: Image.Image) -> Image.Image:
    """mask 区内原图灰度（暗处低→Multiply 拉暗，亮处高→无影响），区外 255。"""
    g = np.array(img_rgb.convert("L")).astype(np.float32)
    m = (np.array(mask) > 127).astype(np.float32)
    s = g * m + 255.0 * (1 - m)
    return Image.fromarray(s.astype(np.uint8), "L")


def make_highlight(img_rgb: Image.Image, mask: Image.Image) -> Image.Image:
    """mask 区内亮部增强（Overlay 提亮），区外 128（中性）。"""
    g = np.array(img_rgb.convert("L")).astype(np.float32)
    m = (np.array(mask) > 127).astype(np.float32)
    hi = np.clip((g - 128.0) * 1.5 + 128.0, 0, 255)
    out = hi * m + 128.0 * (1 - m)
    return Image.fromarray(out.astype(np.uint8), "L")


def save_preview(src, mask, disp, shadow, highlight, outdir: Path) -> None:
    prev = outdir / "_preview"
    prev.mkdir(parents=True, exist_ok=True)
    base = np.array(src.convert("RGBA")).astype(np.float32)
    m = np.array(mask) > 127
    tint = np.array([255, 0, 0, 255], dtype=np.float32)
    base[m] = (0.6 * base[m] + 0.4 * tint).astype(np.uint8)
    Image.fromarray(base.astype(np.uint8), "RGBA").convert("RGB").save(prev / "mask_overlay.jpg", quality=90)
    mask.save(prev / "mask.png")
    disp.save(prev / "disp.png")
    shadow.save(prev / "shadow.png")
    highlight.save(prev / "highlight.png")


def main() -> None:
    ap = argparse.ArgumentParser(description="从合成图自动生成模板素材")
    ap.add_argument("--src", required=True, help="源模特图（PNG/JPG）")
    ap.add_argument("--out-dir", default=None, help="输出目录（默认 胚衣根/_tpl/<stem>）")
    args = ap.parse_args()

    src_path = Path(args.src)
    src = Image.open(str(src_path)).convert("RGB")
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = src_path.parent.parent / "_tpl" / src_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    log = []
    log.append(f"source={src_path} size={src.size}")

    shutil.copy(str(src_path), str(out_dir / "source.png"))

    mask_arr, gray = segment_shirt(src)
    mask = Image.fromarray(mask_arr, "L")
    cov = float((mask_arr > 127).mean())
    log.append(f"segment=grabcut+darkness  mask_coverage={cov:.3f}")

    disp = make_disp(src, mask)
    shadow = make_shadow(src, mask)
    highlight = make_highlight(src, mask)

    for name, im in [("mask", mask), ("disp", disp), ("shadow", shadow), ("highlight", highlight)]:
        assert im.size == src.size, f"{name} 尺寸 {im.size} != {src.size}"

    mask.save(out_dir / "mask.png")
    disp.save(out_dir / "disp.png")
    shadow.save(out_dir / "shadow.png")
    highlight.save(out_dir / "highlight.png")

    needs_fix = [
        "领口与头发交界（同色易混）",
        "袖口与手臂交界",
        "下摆与短裤/腿交界（短裤若暗可能误入）",
        "如 mask 含非衣服暗区，用 PS 蒙版擦除",
    ]
    meta = {
        "source": str(src_path),
        "size": list(src.size),
        "method": "grabcut+darkness_prior (OpenCV)",
        "mask_coverage": cov,
        "needs_manual_fix": needs_fix,
        "note": "自动分割质量低于人工 PS；黑T与黑发/短裤/阴影易混，请按 _preview 检查并人工修正 mask 后再批量",
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    save_preview(src, mask, disp, shadow, highlight, out_dir)

    log.append(f"out_dir={out_dir}")
    log.append("files: source.png mask.png disp.png shadow.png highlight.png metadata.json _preview/")
    (out_dir / "build_log.txt").write_text("\n".join(log), encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main()
