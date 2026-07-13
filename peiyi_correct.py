# -*- coding: utf-8 -*-
"""
胚衣遮罩手动校正模块
=====================
用户点一下图片上漏掉/多算的区域，算法自动用「颜色生长」圈出整块，
合并到现有遮罩中。

用法：
    1. 在图片上点一下漏掉的透明杯子 → add_occ（加进遮挡物）
    2. 在图片上点一下被误裁的衣服边缘 → add_body（加进衣身）
    3. 在图片上点一下多算的遮挡物 → remove_occ（从遮挡物移除）

算法：从点击位置做 LAB 色度距离的连通域生长，
      再用边缘检测（Canny）做边界约束，防止长到衣服上。
"""
from __future__ import annotations

import os
import json
import shutil
import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import cv2
import scipy.ndimage as ndi
from skimage import color as skcolor

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
COLOR_TOLERANCE = 20        # LAB 色度距离阈值（越大长得越远；原18调至20更容错）
SOBEL_WEIGHT = 0.2          # 边缘惩罚权重（0=无视边缘，1=边缘完全阻挡；原0.3调至0.2）
MIN_REGION_PX = 100         # 最小有效区域像素（原200调至100，细戒指也能识别）
MAX_REGION_PX = 1200000     # 最大区域像素（原500000调至1200000，点击大面积区域不轻易报错）

# 形态学清理
CLEAN_CLOSE_ITERS = 2
CLEAN_OPEN_ITERS = 1


def _grow_region(
    image: np.ndarray,
    seed_y: int,
    seed_x: int,
    tolerance: float = COLOR_TOLERANCE,
    sobel_weight: float = SOBEL_WEIGHT,
) -> np.ndarray:
    """从种子点生长出相似颜色的连通区域。

    原理：
        1. 把原图转 LAB，用色度距离找与种子点颜色接近的所有像素。
        2. 取包含种子点的最大连通域（排除了远处同色但不相连的噪点）。
        3. 使用 Sobel 边缘检测做边界约束：若种子在强边缘一侧，
           生长不会跨过边缘（避免长到衣服上）。

    参数：
        image: RGB uint8 (H,W,3)
        seed_y, seed_x: 点击坐标
        tolerance: 色度距离阈值
        sobel_weight: 边缘约束强度

    返回：
        bool (H,W) — 生长出来的区域
    """
    h, w = image.shape[:2]

    # 1) 颜色相似度
    lab = skcolor.rgb2lab(image).astype(np.float32)
    seed_color = lab[seed_y, seed_x]
    dist = np.sqrt(np.sum((lab - seed_color) ** 2, axis=2))
    similar = dist < tolerance

    # 2) 找包含种子点的连通域
    labeled, n = ndi.label(similar)
    if n == 0:
        return np.zeros((h, w), dtype=bool)
    region = labeled == labeled[seed_y, seed_x]

    # 3) 边缘约束——用 Sobel 梯度在种子附近建阻隔
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    # 归一化到 0-1
    grad_max = grad.max()
    if grad_max > 0:
        grad = grad / grad_max
    # 强边缘处 = 阻隔
    edge_penalty = grad * sobel_weight
    # 重新做生长：从种子点 BFS，每一步累加 edge_penalty，超限停止
    # 简化版：对 region 内边缘强度超阈值的像素标记为阻隔墙
    EDGE_THRESH = 0.4  # 边缘强度阈值（Canny 风格）
    strong_edge = grad > EDGE_THRESH

    # 在 region 内去掉跨过强边缘的部分
    # 用形态学：对 strong_edge 膨胀 2px 形成"墙"
    wall = ndi.binary_dilation(strong_edge, iterations=2)
    # region 被墙切碎 -> 保留含种子的那块
    region_clean = region & (~wall)
    labeled2, n2 = ndi.label(region_clean)
    if n2 > 0 and labeled2[seed_y, seed_x] > 0:
        region = labeled2 == labeled2[seed_y, seed_x]
    # 如果墙把区域切没了，退回到无墙的 region
    if region.sum() < MIN_REGION_PX:
        region = labeled == labeled[seed_y, seed_x]

    return region


def _merge_region(
    mask: np.ndarray,
    region: np.ndarray,
    mode: str,
) -> np.ndarray:
    """把生长出来的 region 合并到现有遮罩中。

    mode:
        "add_occ"   — region 加入遮挡物（mask |= region）
        "remove_occ" — region 从遮挡物移除（mask &= ~region）
        "add_body"   — region 从遮挡物移除（等价于加入衣身）
    """
    if mode == "add_occ":
        result = mask | region
    elif mode == "remove_occ":
        result = mask & (~region)
    elif mode == "add_body":
        result = mask & (~region)
    else:
        raise ValueError(f"未知模式: {mode}")

    # 形态学清理
    if CLEAN_CLOSE_ITERS > 0:
        result = ndi.binary_closing(result, iterations=CLEAN_CLOSE_ITERS)
    if CLEAN_OPEN_ITERS > 0:
        result = ndi.binary_opening(result, iterations=CLEAN_OPEN_ITERS)
    return result


def correct_mask(
    image_path: str | Path,
    click_x: int,
    click_y: int,
    mode: str = "add_occ",
    color_tolerance: float = COLOR_TOLERANCE,
) -> dict:
    """对指定胚衣做单次点击校正。

    流程：
        1. 从原图加载当前遮罩文件
        2. 从点击位置做颜色生长
        3. 合并到遮罩中
        4. 保存并归档新版本

    参数：
        image_path: 原图路径（如 D:/.../白W3.jpg）
        click_x, click_y: 点击坐标（原图坐标）
        mode: "add_occ" | "remove_occ" | "add_body"

    返回：
        {
            "ok": True/False,
            "region_px": 区域像素数,
            "new_version": 新版本号,
            "error": ...
        }
    """
    image_path = Path(image_path)
    if not image_path.exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}

    stem = image_path.stem
    out_dir = image_path.parent

    # 加载原图
    image = np.array(Image.open(image_path).convert("RGB"))
    h, w = image.shape[:2]

    # 边界检查
    if click_x < 0 or click_x >= w or click_y < 0 or click_y >= h:
        return {"ok": False, "error": f"点击坐标({click_x},{click_y})超出图片范围({w}x{h})"}

    # 加载当前遮罩
    occ_mask_path = out_dir / f"{stem}_occluder_mask.png"
    if not occ_mask_path.exists():
        return {"ok": False, "error": f"遮罩文件不存在: {occ_mask_path}；请先生成自动遮罩"}

    occ_mask = np.array(Image.open(occ_mask_path)) > 128

    # 颜色生长
    region = _grow_region(image, click_y, click_x, tolerance=color_tolerance)
    region_px = int(region.sum())

    if region_px < MIN_REGION_PX:
        return {"ok": False, "error": f"圈出的区域太小({region_px}px)，请点在一块的明显区域（如杯子边缘、戒指）"}
    if region_px > MAX_REGION_PX:
        # 太大可能是误生长，缩小 tolerance 重试
        return {"ok": False, "error": f"圈出的区域太大({region_px}px)，请点在小一点的区域试试"}

    # 合并
    new_occ = _merge_region(occ_mask, region, mode)

    # 重建 occluder RGBA
    arr = np.array(Image.open(image_path).convert("RGB"))
    occ_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    occ_rgba[:, :, :3] = arr
    occ_rgba[:, :, 3] = (new_occ * 255).astype(np.uint8)

    # 保存到标准路径
    Image.fromarray(occ_rgba).save(occ_mask_path.with_name(f"{stem}_occluder.png"), "PNG")
    Image.fromarray((new_occ * 255).astype(np.uint8)).save(occ_mask_path, "PNG")

    # ---- 归档到 _mask_versions ----
    version = _archive_correction(out_dir, stem, mode, region_px)

    return {
        "ok": True,
        "region_px": region_px,
        "new_version": version,
        "mode": mode,
    }


def _archive_correction(out_dir: Path, stem: str, mode: str, region_px: int) -> Optional[str]:
    """把手动校正存档为一个版本 vNNN（自动版本的下一个号）。

    将标准路径的 5 个文件复制到 _mask_versions/<stem>/vNNN/，
    并写 score.json 标记 manual_correction。
    """
    try:
        vroot = out_dir / "_mask_versions" / stem
        vroot.mkdir(parents=True, exist_ok=True)

        def _vnum(p):
            try:
                return int(p.name[1:])
            except Exception:
                return 0

        existing = [p for p in vroot.glob("v*") if p.is_dir()]
        next_n = (max([_vnum(p) for p in existing]) + 1) if existing else 1
        vdir = vroot / f"v{next_n:03d}"
        vdir.mkdir(parents=True, exist_ok=True)

        for suffix in ["_occluder.png", "_occluder_mask.png", "_body_mask.png",
                        "_parse.png", "_alpha.png"]:
            src = out_dir / f"{stem}{suffix}"
            if src.exists():
                shutil.copy2(src, vdir / src.name)

        score_obj = {
            "version": f"v{next_n:03d}",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "algorithm_version": "manual",
            "manual_correction": {
                "mode": mode,
                "region_px": region_px,
            },
            "score": None,
            "metrics": {},
            "flags": ["manual_correction"],
        }
        (vdir / "score.json").write_text(
            json.dumps(score_obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 更新 history.json
        hist_path = vroot / "history.json"
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
        except Exception:
            history = []
        history.append(score_obj)
        hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        (vroot / "latest.txt").write_text(f"v{next_n:03d}", encoding="utf-8")

        return f"v{next_n:03d}"
    except Exception as e:
        return None
