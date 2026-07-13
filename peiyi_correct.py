# -*- coding: utf-8 -*-
"""
胚衣遮罩手动校正模块
=====================
用户点一下图片上漏掉/多算的区域，算法自动用「颜色生长」圈出整块，
先预览效果，确认后才存档为版本。

两种操作模式：
    1. preview (预览) — 圈出区域 + 合并到临时遮罩，返回预览结果，不归档
    2. confirm (确认) — 把临时遮罩存档为一个新版本
    3. cancel (取消) — 清除临时遮罩，回到上一个已存版本

算法：从点击位置做 LAB 色度距离的连通域生长，
      再用 Sobel 边缘检测做边界约束。
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
COLOR_TOLERANCE = 20        # LAB 色度距离阈值
SOBEL_WEIGHT = 0.2          # 边缘约束强度
MIN_REGION_PX = 50          # 最小有效区域像素（再小就忽略）
MAX_REGION_PX = 1200000     # 最大区域像素

CLEAN_CLOSE_ITERS = 2
CLEAN_OPEN_ITERS = 1
WORKING_DIR = "_working"    # 临时遮罩目录名


# ---------------------------------------------------------------------------
# 核心算法
# ---------------------------------------------------------------------------
def _grow_region(image, seed_y, seed_x, tolerance=COLOR_TOLERANCE, sobel_weight=SOBEL_WEIGHT):
    """从种子点生长出相似颜色的连通区域。"""
    h, w = image.shape[:2]
    lab = skcolor.rgb2lab(image).astype(np.float32)
    seed_color = lab[seed_y, seed_x]
    dist = np.sqrt(np.sum((lab - seed_color) ** 2, axis=2))
    similar = dist < tolerance

    labeled, n = ndi.label(similar)
    if n == 0:
        return np.zeros((h, w), dtype=bool)
    region = labeled == labeled[seed_y, seed_x]

    # Sobel 边缘约束
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    grad_max = grad.max()
    if grad_max > 0:
        grad = grad / grad_max
    EDGE_THRESH = 0.4
    strong_edge = grad > EDGE_THRESH
    wall = ndi.binary_dilation(strong_edge, iterations=2)
    region_clean = region & (~wall)
    labeled2, n2 = ndi.label(region_clean)
    if n2 > 0 and labeled2[seed_y, seed_x] > 0:
        region = labeled2 == labeled2[seed_y, seed_x]
    if region.sum() < MIN_REGION_PX:
        region = labeled == labeled[seed_y, seed_x]
    return region


def _merge_region(mask, region, mode):
    """把 region 合并到遮罩中（不修改原 mask）"""
    if mode == "add_occ":
        result = mask | region
    elif mode == "remove_occ":
        result = mask & (~region)
    elif mode == "add_body":
        result = mask & (~region)
    else:
        raise ValueError(f"未知模式: {mode}")
    if CLEAN_CLOSE_ITERS > 0:
        result = ndi.binary_closing(result, iterations=CLEAN_CLOSE_ITERS)
    if CLEAN_OPEN_ITERS > 0:
        result = ndi.binary_opening(result, iterations=CLEAN_OPEN_ITERS)
    return result


# ---------------------------------------------------------------------------
# 工作区管理：读/写临时遮罩
# ---------------------------------------------------------------------------
def _working_dir(image_path: Path) -> Path:
    """临时遮罩目录 _mask_versions/<stem>/_working/"""
    stem = image_path.stem
    return image_path.parent / "_mask_versions" / stem / WORKING_DIR


def _save_working(work_dir: Path, stem: str, body_mask, occluder_mask, image_arr):
    """把遮罩保存到临时工作区"""
    work_dir.mkdir(parents=True, exist_ok=True)
    h, w = image_arr.shape[:2]
    # occluder RGBA
    occ_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    occ_rgba[:, :, :3] = image_arr
    occ_rgba[:, :, 3] = (occluder_mask * 255).astype(np.uint8)
    # parse 可视化
    parse_vis = image_arr.copy()
    parse_vis[body_mask] = (parse_vis[body_mask] * 0.6 + np.array([0, 255, 0], np.uint8) * 0.4).astype(np.uint8)
    parse_vis[occluder_mask] = (parse_vis[occluder_mask] * 0.6 + np.array([255, 0, 0], np.uint8) * 0.4).astype(np.uint8)

    Image.fromarray(occ_rgba).save(work_dir / f"{stem}_occluder.png", "PNG")
    Image.fromarray((occluder_mask * 255).astype(np.uint8)).save(work_dir / f"{stem}_occluder_mask.png", "PNG")
    Image.fromarray((body_mask * 255).astype(np.uint8)).save(work_dir / f"{stem}_body_mask.png", "PNG")
    Image.fromarray(parse_vis).save(work_dir / f"{stem}_parse.png", "PNG")


def _load_current_masks(out_dir: Path, stem: str):
    """加载当前使用的遮罩（先看 _working 再看标准路径）"""
    work_dir = out_dir / "_mask_versions" / stem / WORKING_DIR
    occ_mask_path = out_dir / f"{stem}_occluder_mask.png"

    # 优先读 _working（有未确认的修改）
    if (work_dir / f"{stem}_occluder_mask.png").exists():
        body_mask = np.array(Image.open(work_dir / f"{stem}_body_mask.png")) > 128
        occ_mask = np.array(Image.open(work_dir / f"{stem}_occluder_mask.png")) > 128
        return body_mask, occ_mask, True
    # 回退到标准路径
    if occ_mask_path.exists():
        body_path = out_dir / f"{stem}_body_mask.png"
        body_mask = np.array(Image.open(body_path)) > 128 if body_path.exists() else np.zeros((1, 1), dtype=bool)
        occ_mask = np.array(Image.open(occ_mask_path)) > 128
        return body_mask, occ_mask, False
    return None, None, False


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def preview_correction(
    image_path: str | Path,
    click_x: int,
    click_y: int,
    mode: str = "add_occ",
) -> dict:
    """预览校正效果 — 不保存，返回 region 信息和预览图路径。

    流程：
        1. 读当前遮罩（_working 或标准路径）
        2. 从点击点做颜色生长
        3. 合并到遮罩中存到 _working
        4. 返回 region_px + 预览图 URL 路径
    """
    image_path = Path(image_path)
    if not image_path.exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}
    if mode not in ("add_occ", "remove_occ", "add_body"):
        return {"ok": False, "error": f"未知模式: {mode}"}

    stem = image_path.stem
    out_dir = image_path.parent
    image = np.array(Image.open(image_path).convert("RGB"))
    h, w = image.shape[:2]

    if click_x < 0 or click_x >= w or click_y < 0 or click_y >= h:
        return {"ok": False, "error": f"点击坐标({click_x},{click_y})超出图片范围({w}x{h})"}

    # 加载当前遮罩
    body_mask, occ_mask, is_working = _load_current_masks(out_dir, stem)
    if occ_mask is None:
        return {"ok": False, "error": "请先生成自动遮罩"}

    # 颜色生长
    region = _grow_region(image, click_y, click_x)
    region_px = int(region.sum())

    if region_px < MIN_REGION_PX:
        return {"ok": False, "error": f"圈出的区域太小({region_px}px)，请点在一块的明显区域（如杯子边缘、戒指）"}
    if region_px > MAX_REGION_PX:
        return {"ok": False, "error": f"圈出的区域太大({region_px}px)，请点在小一点的区域试试"}

    new_occ = _merge_region(occ_mask, region, mode)
    new_body = body_mask.copy()
    if mode in ("remove_occ", "add_body"):
        new_body = new_body | region  # 从遮挡移除也加回衣身

    # 存到 _working 临时区
    work_dir = _working_dir(image_path)
    _save_working(work_dir, stem, new_body, new_occ, image)

    return {
        "ok": True,
        "region_px": region_px,
        "mode": mode,
        "has_unsaved": True,  # _working 里有未确认的修改
    }


def confirm_correction(image_path: str | Path) -> dict:
    """确认临时遮罩 → 归档为新版本 + 复制到标准路径。"""
    image_path = Path(image_path)
    stem = image_path.stem
    out_dir = image_path.parent
    work_dir = _working_dir(image_path)

    # 验证 _working 存在
    required = [f"{stem}_occluder.png", f"{stem}_occluder_mask.png",
                f"{stem}_body_mask.png", f"{stem}_parse.png"]
    for fn in required:
        if not (work_dir / fn).exists():
            return {"ok": False, "error": f"临时遮罩不完整，缺少 {fn}"}

    # 复制到标准路径
    for fn in required:
        shutil.copy2(work_dir / fn, out_dir / fn)

    # 归档版本
    version = _archive_from_working(out_dir, stem, work_dir, required)

    # 清除 _working
    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "ok": True,
        "new_version": version,
    }


def cancel_correction(image_path: str | Path) -> dict:
    """放弃临时修改 → 删除 _working 目录。"""
    work_dir = _working_dir(Path(image_path))
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    return {"ok": True}


def check_working_status(image_path: str | Path) -> dict:
    """检查是否临时工作区有未确认的修改。"""
    work_dir = _working_dir(Path(image_path))
    has = work_dir.exists() and any(work_dir.iterdir())
    return {"ok": True, "has_unsaved": has}


# ---------------------------------------------------------------------------
# 归档
# ---------------------------------------------------------------------------
def _archive_from_working(out_dir: Path, stem: str, work_dir: Path, files: list[str]) -> Optional[str]:
    """把 _working 的内容归档为新版本。"""
    try:
        vroot = out_dir / "_mask_versions" / stem
        vroot.mkdir(parents=True, exist_ok=True)
        existing = [p for p in vroot.glob("v*") if p.is_dir() and p.name != WORKING_DIR]
        def _vnum(p):
            try: return int(p.name[1:])
            except: return 0
        next_n = (max([_vnum(p) for p in existing]) + 1) if existing else 1
        vdir = vroot / f"v{next_n:03d}"
        vdir.mkdir(parents=True, exist_ok=True)

        for fn in files:
            src = work_dir / fn
            if src.exists():
                shutil.copy2(src, vdir / fn)

        score_obj = {
            "version": f"v{next_n:03d}",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "algorithm_version": "manual",
            "manual_correction": True,
            "score": None, "metrics": {}, "flags": ["manual_correction"],
        }
        (vdir / "score.json").write_text(
            json.dumps(score_obj, ensure_ascii=False, indent=2), encoding="utf-8")
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


# ---------------------------------------------------------------------------
# 删除版本
# ---------------------------------------------------------------------------
def delete_version(
    out_dir: str | Path,
    stem: str,
    version: str,
) -> dict:
    """删除一个版本（vNNN 目录），更新 history.json 和 latest.txt。

    安全：不会删除当前正在使用的版本（latest.txt 指向的）。
    """
    out_dir = Path(out_dir)
    vroot = out_dir / "_mask_versions" / stem
    vdir = vroot / version

    if not vdir.exists() or not vdir.is_dir():
        return {"ok": False, "error": f"版本 {version} 不存在"}

    # 检查是否当前版本
    latest_txt = vroot / "latest.txt"
    current = latest_txt.read_text(encoding="utf-8").strip() if latest_txt.exists() else ""
    if current == version:
        return {"ok": False, "error": f"版本 {version} 是当前使用的版本，不能删除。请先切换到其他版本"}

    # 从 history.json 移除
    hist_path = vroot / "history.json"
    try:
        if hist_path.exists():
            history = json.loads(hist_path.read_text(encoding="utf-8"))
            history = [h for h in history if h.get("version") != version]
            hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # 删除目录
    shutil.rmtree(vdir, ignore_errors=True)

    return {"ok": True}


# ---------------------------------------------------------------------------
# 导入手动 PS 遮罩：读取用户手动制作的 PNG，与 AI 遮罩合并
# ---------------------------------------------------------------------------
# 原则：不做任何分析，用户画的任何非透明像素都直接加到 AI 遮挡物上
#       （用户只需要把 AI 没识别到的遮挡物画上去就行了）
MANUAL_SUFFIX = "_manual.png"   # 用户手动遮罩文件名后缀


def import_manual_mask(image_path: str | Path) -> dict:
    """导入用户手动制作的遮罩，与 AI 最新遮罩合并。

    流程：
        1. 读取 `{stem}_manual.png`
        2. 取出用户画的像素（任何非透明像素 = 用户要加的修正）
        3. 加到 AI 的遮挡物上：final_occ = AI_occ | 用户画的区域
        4. 保存 + 归档新版本

    参数：
        image_path: 原图路径（如 D:/.../白W2.jpg）

    返回：
        { ok, new_version, added_px }
    """
    image_path = Path(image_path)
    if not image_path.exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}

    stem = image_path.stem
    out_dir = image_path.parent

    # 1. 找手动遮罩文件
    manual_path = out_dir / f"{stem}{MANUAL_SUFFIX}"
    if not manual_path.exists():
        manual_path2 = out_dir / "_mask_versions" / stem / f"{stem}{MANUAL_SUFFIX}"
        if manual_path2.exists():
            manual_path = manual_path2
        else:
            manual_path3 = out_dir / "_mask_versions" / stem / f"{stem}.png"
            if manual_path3.exists():
                manual_path = manual_path3
            else:
                return {"ok": False, "error": f"未找到手动遮罩文件，请保存为 {stem}_manual.png 到素材目录"}

    # 2. 读取用户画的像素（任何非透明 = 用户要加的修正）
    manual_img = Image.open(manual_path).convert("RGBA")
    manual_arr = np.array(manual_img)
    # 用户画的区域：alpha>0 或 RGB 平均值 > 100（非黑色）
    r, g, b, a = manual_arr[:,:,0].astype(float), manual_arr[:,:,1].astype(float), manual_arr[:,:,2].astype(float), manual_arr[:,:,3].astype(float)
    user_paint = (a > 30) | ((r + g + b) / 3 > 100)

    # 3. 加载 AI 遮罩
    image = np.array(Image.open(image_path).convert("RGB"))
    img_h, img_w = image.shape[:2]
    if user_paint.shape[0] != img_h or user_paint.shape[1] != img_w:
        return {"ok": False, "error": f"手动遮罩尺寸({user_paint.shape[1]}x{user_paint.shape[0]})与原图({img_w}x{img_h})不一致"}

    ai_occ_path = out_dir / f"{stem}_occluder_mask.png"
    ai_body_path = out_dir / f"{stem}_body_mask.png"
    ai_occ = np.array(Image.open(ai_occ_path)) > 128 if ai_occ_path.exists() else np.zeros((img_h, img_w), dtype=bool)
    ai_body = np.array(Image.open(ai_body_path)) > 128 if ai_body_path.exists() else np.zeros((img_h, img_w), dtype=bool)
    person_mask = ai_body | ai_occ

    # 4. 合并：把你画的区域加到遮挡物上（只取人像范围内的）
    added = user_paint & person_mask
    final_occ = ai_occ | added
    final_body = person_mask & (~final_occ)

    # 5. 保存
    h, w = img_h, img_w
    occ_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    occ_rgba[:, :, :3] = image
    occ_rgba[:, :, 3] = (final_occ * 255).astype(np.uint8)
    parse_vis = image.copy()
    parse_vis[final_body] = (parse_vis[final_body] * 0.6 + np.array([0, 255, 0], np.uint8) * 0.4).astype(np.uint8)
    parse_vis[final_occ] = (parse_vis[final_occ] * 0.6 + np.array([255, 0, 0], np.uint8) * 0.4).astype(np.uint8)

    Image.fromarray(occ_rgba).save(out_dir / f"{stem}_occluder.png", "PNG")
    Image.fromarray((final_occ * 255).astype(np.uint8)).save(out_dir / f"{stem}_occluder_mask.png", "PNG")
    Image.fromarray((final_body * 255).astype(np.uint8)).save(out_dir / f"{stem}_body_mask.png", "PNG")
    Image.fromarray(parse_vis).save(out_dir / f"{stem}_parse.png", "PNG")

    # 6. 归档
    added_px = int(added.sum())
    version = _archive_manual_version(out_dir, stem, manual_path.name, added_px)
    return {
        "ok": True,
        "new_version": version,
        "added_px": added_px,
        "manual_file": manual_path.name,
    }


def _archive_manual_version(out_dir: Path, stem: str, manual_fn: str, added_px: int) -> Optional[str]:
    """手动导入的新版本归档。"""
    try:
        vroot = out_dir / "_mask_versions" / stem
        vroot.mkdir(parents=True, exist_ok=True)
        existing = [p for p in vroot.glob("v*") if p.is_dir() and p.name != WORKING_DIR]
        def _vnum(p):
            try: return int(p.name[1:])
            except: return 0
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
            "algorithm_version": "manual_import",
            "manual_correction": True,
            "manual_source": manual_fn,
            "manual_added_px": added_px,
            "score": None, "metrics": {}, "flags": ["manual_import"],
        }
        (vdir / "score.json").write_text(
            json.dumps(score_obj, ensure_ascii=False, indent=2), encoding="utf-8")
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
