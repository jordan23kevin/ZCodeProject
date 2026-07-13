# -*- coding: utf-8 -*-
"""
胚衣遮罩（Mask）生成模块
========================
为 03_MATERIAL 中的胚衣素材自动生成三层结构所需的遮罩：
    - body_mask     : 印花图案所在的 T 恤主体区域
    - occluder_mask : 遮挡物（手、头发、配饰等）区域
    - occluder_rgba : 从原图抠出的遮挡物像素，可直接作为最上层盖在贴图上

实现：
    1. BiRefNet（本地缓存）生成高精度人像 Alpha Matte（人 vs 背景）。
    2. 在人像内部使用 LAB 颜色聚类，将纯色 T 恤与皮肤/头发/配饰分开。
    3. 对纯色平面拍摄的 胚衣（flat-lay），occluder 为空或极小；对模特穿着图，
       手/头发等自然被识别为遮挡物。

注意：
    - 本模块不依赖外网下载，BiRefNet 权重已在 C:/Users/Administrator/.cache 中。
    - 若 T 恤与头发颜色过于接近（如黑 T + 黑长发），颜色聚类可能合并，此时需要
      SCHP 等语义解析模型做升级。模块架构已预留该扩展点。
"""
from __future__ import annotations

import os
import sys
import json
import time
import shutil
import datetime
import threading
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
from PIL import Image
import cv2
import scipy.ndimage as ndi
from skimage import color as skcolor

# 让 bridge 在 PYTHONPATH=E:/python_packages 下能找到 transformers/torch
sys.path.insert(0, os.environ.get("PYTHONPATH", r"E:/python_packages").split(os.pathsep)[0])

import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------
VERSION = "1.5.0"              # 2026-07-13：接入 FASHN 语义分割(可选,失败回退)——衣服主体用top更贴合,
                             # 遮挡物∪FASHN(戒指/手/头发/首饰)根治"印花盖戒指"。v1.4 版本归档+评分
MODEL_NAME = "ZhengPeng7/BiRefNet"
BIR_NET_INPUT_SIZE = (1024, 1024)
NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]

# 人像 matte 二值化阈值。之前 128（alpha>0.5）会把半透明的细发丝裁掉；
# 降到 64（alpha>0.25）可找回大量发丝，再用闭运算接回 + 按面积删噪点（见 generate_masks）。
ALPHA_THRESHOLD = 64
K_AB_CLUSTERS = 2              # 在 (a*,b*) 色度空间聚类数（用于找衣服色度中心）
BODY_CLOSE_ITERS = 2
BODY_OPEN_ITERS = 1
# v1.3：开运算关掉，避免把戒指/细手指/发丝等细遮挡物侵蚀掉
OCC_OPEN_ITERS = 0

# 人像轮廓（含发丝）恢复：降阈值后用闭运算把断裂的细发丝重新接回头部，
# 再按面积删除降阈值引入的孤立背景噪点。
PERSON_CLOSE_ITERS = 2
PERSON_MIN_COMP_RATIO = 0.0003   # 人像里小于「全图面积 × 该比例」的连通域视为噪点删除
# 白色手指甲 / 白色配饰 补回遮挡物：
NAIL_FLIP_MIN_AREA_ABS = 1500     # 小于此绝对面积的 body 小块才考虑翻转
NAIL_FLIP_MIN_RATIO = 0.02        # 也须小于「人像像素 × 该比例」才考虑翻转

# 遮挡物判定（核心改进：专治「平铺图褶皱被误判为遮挡物」）
# ---------------------------------------------------------------------------
# 衣物褶皱 / 扭曲只改变亮度 L，不改变色度（a*,b* = hue/chroma）；
# 而真实遮挡物（皮肤 / 头发 / 配饰）色度与衣服明显不同。
# 因此用「像素 (a*,b*) 到衣服色度中心的欧氏距离」判定，完全不依赖 L：
#     distance < CHROMA_TOL  -> 与衣服同色度 -> body（含褶皱暗谷、亮脊、表面投影）
#     distance >= CHROMA_TOL -> 色度明显不同   -> occluder（最上层）
CHROMA_TOL = 15.0             # LAB (a*,b*) 欧氏距离阈值（越大越宽松）

# v1.3.1：前景扩展，把紧贴人体的手持物（杯子/杯盖/手表/道具）包进遮挡。
# BiRefNet 只分割「人」，常把手持物当成「非人」排除在 person_mask 外，形成洞，
# 贴图时印花会透过杯子/杯盖。这里对 person_mask 做 闭运算填洞 + 膨胀外扩，
# 把紧贴着人/手的杯子包进前景。远处背景因距离远不会被包住；即便少量近景被包入，
# 也只在衣服之外，不影响衣服上的印花（遮挡层盖住衣服外区域无害）。
FG_CLOSE_ITERS = 8            # 前景闭运算：填人像内部小洞（含杯子与手之间的缝）
FG_DILATE_ITERS = 25          # 前景膨胀：外扩包住紧贴人体的杯子/手持物
# 安全网：遮挡物像素占比极小（< 阈值）时，多半是褶皱/压缩噪点，直接清空 occluder。
OCC_MIN_RATIO = 0.03          # 遮挡物像素 / 人像像素 的最小比例；平铺图里残留的道具/鞋/徽章通常 <3%，会被清空；真遮挡物（手/头发）通常 >10%，正常保留。
# 空间过滤：只保留位于衣服主体凸包内部的遮挡物。
# 平铺图里的鞋子、装饰徽章、背景道具等虽然在前景内，但位于衣服外部，应剔除；
# 真正遮挡物（手/头发/杯子）都压在衣服表面，位于凸包内。
OCC_HULL_DILATE_ITERS = 5    # 凸包外扩 5px，兼容发梢/边缘抗锯齿
OCC_FINAL_DILATE = 25        # 最后把 occluder 再扩 25px，覆盖 BiRefNet 漏掉的
                             # 戒指/杯盖/发丝等手边小物（v1.2.1）

SUFFIX_BODY_MASK = "body_mask.png"
SUFFIX_OCCLUDER_MASK = "occluder_mask.png"
SUFFIX_OCCLUDER = "occluder.png"
SUFFIX_PARSE = "parse.png"
SUFFIX_ALPHA = "alpha.png"

# 版本归档：每次生成把结果复制到 <素材目录>/<该目录名>/<stem>/vNNN/，并写 score.json。
# 标准路径(*_occluder.png 等)始终是最新版，生产贴图不受影响。
VERSION_DIRNAME = "_mask_versions"

# ---------------------------------------------------------------------------
# FASHN 语义分割增强（可选）：直接识别 衣服/手/头发/戒指/包 等部位，比
# BiRefNet+颜色聚类更准。加载失败(模型未下载/无网络)自动回退到原方法，绝不出错。
# ---------------------------------------------------------------------------
USE_FASHN = True
FASHN_MODEL = "fashn-ai/fashn-human-parser"
# FASHN 18 类标签：top=衣服主体；face/hair/bag/hat/scarf/glasses/arms/hands/torso/jewelry=遮挡物
FASHN_BODY_LABELS = {3}
FASHN_OCC_LABELS = {1, 2, 8, 9, 10, 11, 12, 13, 16, 17}

# ---------------------------------------------------------------------------
# 模型单例（bridge 进程内只加载一次）
# ---------------------------------------------------------------------------
_model: Optional[torch.nn.Module] = None
_model_lock = threading.Lock()
_inference_lock = threading.Lock()


def _load_model() -> torch.nn.Module:
    """加载/缓存 BiRefNet；首次调用约 2~5 秒，后续复用。"""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        # 权重已缓存在本机；若未缓存则允许在线下载（用户机器联网时）
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        m = AutoModelForImageSegmentation.from_pretrained(
            MODEL_NAME, trust_remote_code=True
        )
        m.float().eval()
        # 默认 CPU 即可；用户机器若有 GPU 可加速
        if torch.cuda.is_available():
            m = m.cuda()
        _model = m
        return _model


# ---------------------------------------------------------------------------
# 预处理 / 推理
# ---------------------------------------------------------------------------
def _preprocess(image: Image.Image) -> torch.Tensor:
    tf = transforms.Compose([
        transforms.Resize(BIR_NET_INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(NORMALIZE_MEAN, NORMALIZE_STD),
    ])
    return tf(image.convert("RGB")).unsqueeze(0)


def _infer_matte(image: Image.Image) -> np.ndarray:
    """对 image 运行 BiRefNet，返回 [0,1] 的 alpha 矩阵，尺寸与原图一致。"""
    model = _load_model()
    x = _preprocess(image)
    if next(model.parameters()).is_cuda:
        x = x.cuda()

    with _inference_lock, torch.no_grad():
        out = model(x)
    pred = out[0] if isinstance(out, (list, tuple)) else out
    alpha = torch.sigmoid(pred[0, 0]).cpu().numpy()  # [0,1]

    alpha_uint8 = (alpha * 255).astype(np.uint8)
    alpha_pil = Image.fromarray(alpha_uint8).resize(image.size, Image.BILINEAR)
    return np.array(alpha_pil) / 255.0


# ---------------------------------------------------------------------------
# 颜色聚类分割身体 / 遮挡物
# ---------------------------------------------------------------------------
def _shirt_color_hint(category: Optional[str]) -> Optional[str]:
    """从分类名推断 T 恤颜色：W白/B白 -> white, W黑/B黑 -> black。"""
    if not category:
        return None
    cat = category.strip()
    if "黑" in cat and "白" not in cat:
        return "black"
    if "白" in cat and "黑" not in cat:
        return "white"
    # 混合命名如 W黑 / B黑：第二个字符通常代表衣服颜色
    if "黑" in cat:
        return "black"
    if "白" in cat:
        return "white"
    return None


def _remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    """
    删除面积小于 min_area 的连通分量。

    用于人像 matte 降阈值后剔除由此引入的孤立背景噪点。
    与形态学开运算不同：它不会侵蚀细发丝等「与大主体相连的细长结构」，
    只删除真正孤立的小块，因此对头发恢复更友好。
    """
    if min_area <= 1:
        return mask
    labeled, num = ndi.label(mask)
    if num == 0:
        return mask
    sizes = ndi.sum(np.ones_like(labeled), labeled, range(1, num + 1))
    keep = np.zeros_like(labeled, dtype=bool)
    for i, s in enumerate(sizes, start=1):
        if s >= min_area:
            keep |= (labeled == i)
    return keep


def _color_cluster_split(
    image: Image.Image,
    person_mask: np.ndarray,
    shirt_color_hint: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """
    在人像内部把 T 恤主体（body）与真实遮挡物（occluder）分开。

    核心改进（专治「平铺图褶皱被误判为遮挡物」）：
        衣物褶皱 / 扭曲只改变亮度 L，不改变色度（a*,b* = hue/chroma）；
        而真实遮挡物（皮肤 / 头发 / 配饰）色度与衣服明显不同。
        因此用「像素 (a*,b*) 到衣服色度中心的欧氏距离」判定，完全不依赖 L：
            distance < CHROMA_TOL  -> 与衣服同色度 -> body（含褶皱暗谷、亮脊、表面投影）
            distance >= CHROMA_TOL -> 色度明显不同   -> occluder（最上层）
        从根本上避免把由明暗变化造成的褶皱误判为遮挡物。
    """
    arr = np.array(image.convert("RGB"))
    lab = skcolor.rgb2lab(arr).astype(np.float32)

    # v1.3.1：前景扩展，把紧贴人体的手持物（杯子/杯盖/手表/道具）包进遮挡，
    # 避免 BiRefNet 把它们当「非人」排除而形成洞（印花透过杯子）。
    person_mask = ndi.binary_closing(person_mask, iterations=FG_CLOSE_ITERS)
    person_mask = ndi.binary_dilation(person_mask, iterations=FG_DILATE_ITERS)

    ys, xs = np.where(person_mask)
    if len(xs) < 100:
        # 几乎没有人像，视为 flat-lay/空白
        return np.zeros_like(person_mask), np.zeros_like(person_mask), arr.copy(), {
            "is_person": False, "shirt_ab": None, "chroma_tol": CHROMA_TOL
        }

    person_lab = lab[ys, xs]                       # N x 3 : (L, a*, b*)
    ab = person_lab[:, 1:3].astype(np.float32)     # 只取色度 (a*, b*)

    # 1) 估计衣服色度中心 (a0, b0)
    if len(ab) > 50000:
        s = np.random.choice(len(ab), 50000, replace=False)
        ab_s = ab[s]
    else:
        ab_s = ab
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,  # max_iter
        0.1,  # epsilon
    )
    _, labels_ab, centers_ab = cv2.kmeans(
        ab_s, K_AB_CLUSTERS, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
    )
    if shirt_color_hint in ("white", "black"):
        # 白/黑 T 恤都是「消色」（a*,b* 接近 0）；选色度中心更接近 (0,0) 的簇，
        # 避免皮肤区域面积偶然较大时把衣服用色度中心算偏。
        shirt_idx = min(
            range(K_AB_CLUSTERS),
            key=lambda c: float(np.linalg.norm(centers_ab[c])),
        )
    else:
        # 彩色衣物：取面积最大的簇（衣服占主体）
        areas_ab = [(c, int((labels_ab == c).sum())) for c in range(K_AB_CLUSTERS)]
        shirt_idx = max(areas_ab, key=lambda x: x[1])[0]
    shirt_ab = centers_ab[shirt_idx].astype(np.float32)   # (a0, b0)

    # 2) 逐像素色度距离 -> 与衣服同色度则归 body
    da = person_lab[:, 1] - shirt_ab[0]
    db = person_lab[:, 2] - shirt_ab[1]
    chroma_d = np.sqrt(da * da + db * db)
    is_shirt = chroma_d < CHROMA_TOL

    # 2) 候选 body：人像内与衣服同色度的像素（褶皱只改亮度不改色度，故仍归衣服）
    body_candidate = np.zeros_like(person_mask)
    body_candidate[ys, xs] = is_shirt
    body_candidate = ndi.binary_closing(body_candidate, iterations=BODY_CLOSE_ITERS)
    body_candidate = ndi.binary_opening(body_candidate, iterations=BODY_OPEN_ITERS)

    # T 恤 = 候选 body 中「最大的连通块」。
    # 戒指/杯盖等同色小块即便落在衣服区，也只是小岛，不会成为主体，
    # 因此自然留在遮挡层（person 减去 shirt），不会被当成可贴图区域。
    labeled, ncomp = ndi.label(body_candidate)
    if ncomp == 0:
        body_mask = np.zeros_like(person_mask)
    else:
        sizes = ndi.sum(body_candidate, labeled, range(1, ncomp + 1))
        shirt_label = 1 + int(np.argmax(sizes))
        body_mask = (labeled == shirt_label)

    # 遮挡层 = 整个人像 扣掉 那块布。手/头发/脸/浅色头发（不在主布块里）都在此。
    occluder_mask = person_mask & (~body_mask)

    # ---- 配件/手部持物回收（v1.3 增强版）----
    # 戒指/杯盖/手表/浅色指甲：颜色与衣服接近时被归到 body 候选区，
    # 但因手/皮肤（occluder）隔开，它们是独立小块而非 T 恤主块。
    # 判定：body 候选里除主块外的连通域，只要「面积小 且 与 occluder 相邻」，
    # 整块翻回 occluder。不猜颜色，靠 相邻+小 两条，稳。
    # v1.3 关键修复：旧版只对「body_mask & occ_dil」的相邻像素打标，小块主体
    # 常被漏掉；现改对「body_candidate 除主块外的小块」整体判定 + 扩大膨胀半径。
    ACC_DILATE = 10
    ACC_MAX_ABS = 2500          # 小块绝对面积上限（戒指/杯盖级别）
    ACC_MAX_RATIO = 0.03        # 且 < 人像面积的 3%
    occ_dil = ndi.binary_dilation(occluder_mask, iterations=ACC_DILATE)
    extra_body = body_candidate & (~body_mask)   # 候选里除 T 恤主块外的小块
    person_n_acc = max(1, int(person_mask.sum()))
    if int(extra_body.sum()) > 0:
        e_labeled, ne = ndi.label(extra_body)
        for t in range(1, ne + 1):
            comp = e_labeled == t
            sz = int(comp.sum())
            if (sz < ACC_MAX_ABS and (sz / person_n_acc) < ACC_MAX_RATIO
                    and int((comp & occ_dil).sum()) > 0):
                occluder_mask = occluder_mask | comp
                body_mask = body_mask & (~comp)

    if OCC_OPEN_ITERS > 0:
        occluder_mask = ndi.binary_opening(occluder_mask, iterations=OCC_OPEN_ITERS)

    # 3) 安全网：遮挡物占比极小 -> 多半是褶皱/压缩噪点，直接清空 occluder
    person_n = int(person_mask.sum())
    occ_n = int(occluder_mask.sum())
    occ_ratio = (occ_n / person_n) if person_n > 0 else 0.0
    if person_n > 0 and occ_ratio < OCC_MIN_RATIO:
        occluder_mask = np.zeros_like(occluder_mask)
        occ_ratio = 0.0

    # 可视化：body 绿色，occluder 红色，叠加原图
    vis = arr.copy()
    vis[body_mask] = (vis[body_mask] * 0.6 + np.array([0, 255, 0], np.uint8) * 0.4).astype(np.uint8)
    vis[occluder_mask] = (vis[occluder_mask] * 0.6 + np.array([255, 0, 0], np.uint8) * 0.4).astype(np.uint8)

    info = {
        "is_person": True,
        "shirt_ab": [round(float(x), 2) for x in shirt_ab],
        "chroma_tol": CHROMA_TOL,
        "chroma_d_max": round(float(chroma_d.max()), 2),
        "chroma_d_occluder_mean": round(
            float(chroma_d[~is_shirt].mean()) if (~is_shirt).any() else 0.0, 2
        ),
        "person_px": person_n,
        "occluder_px": int(occluder_mask.sum()),
        "occluder_ratio": round(occ_ratio, 4),
    }
    return body_mask, occluder_mask, vis, info


# ---------------------------------------------------------------------------
# occluder_mask 后处理清洗（v6：衣服区减法 + 位置裁剪 组合）
# ---------------------------------------------------------------------------
# 解决：① 衣服阴影/褶皱被误识别为遮挡物（白W8 / 白B6 辫子下阴影）
#       ② 头/颈、短裤/腿部被误包含  ③ 散点噪点
# 直接用同流程算出的 body_mask（衣服主体）膨胀后做「衣服区减法」，
# 比从 parse 可视化图反推更可靠（无抗锯齿噪声）。
REFINE_MIN_SMALL_PX = 300        # v1.3：1500→300，保住戒指/杯盖/细手指等小遮挡物
REFINE_TOP_ZONE = 0.03           # v1.3.1：少裁头顶，保头发（头进遮挡无害，印花在衣服上）
REFINE_BOTTOM_ZONE = 0.04        # v1.3.1：少裁底部，保杯子/手持物（裤子进遮挡无害）
REFINE_SECONDARY_MIN_PX = 800    # v1.3：3000→800，二次清理放宽，保住手部持物
REFINE_SHIRT_RATIO = 0.75        # v1.3.1：更宽松，杯子/手持物靠近衣服也不误删
REFINE_SHIRT_DIL_ITER = 6        # v1.3.1：衣服区膨胀减小，少误伤紧挨衣服的杯子
REFINE_OPEN_KSIZE = 3            # ④ 形态学开运算核
REFINE_CLOSE_KSIZE = 7           # ④ 形态学闭运算核


def _detect_shirt_region_from_vis(
    vis: np.ndarray, dil_iter: int = REFINE_SHIRT_DIL_ITER
) -> np.ndarray:
    """
    从 parse 可视化图（绿=衣服 红=遮挡物）识别绿色衣服区域。

    衣服在可视化里表现为绿色 (G >> R, G >> B, G 较高)；阴影落在绿底上
    经 0.4 绿调后仍读为绿，因此能一并覆盖（专治白B6 辫子下阴影）。
    返回已膨胀 dil_iter 次的 bool(H,W) 衣服区。
    """
    r = vis[..., 0].astype(float)
    g = vis[..., 1].astype(float)
    b = vis[..., 2].astype(float)
    shirt = (g > r + 20) & (g > b + 20) & (g > 90)
    # 也包含深绿（短裤在 parse 里常是深绿）
    dark_green = (g > r + 10) & (g > b + 10) & (g > 40) & (g < 110) & (r < 90) & (b < 90)
    shirt = shirt | dark_green
    return ndi.binary_dilation(shirt, iterations=dil_iter)


def _refine_occluder_mask(
    occluder_mask: np.ndarray,
    h: int,
    w: int,
    *,
    shirt_region: np.ndarray | None = None,
    min_small_px: int = REFINE_MIN_SMALL_PX,
    top_zone: float = REFINE_TOP_ZONE,
    bottom_zone: float = REFINE_BOTTOM_ZONE,
    secondary_min_px: int = REFINE_SECONDARY_MIN_PX,
    shirt_ratio_thresh: float = REFINE_SHIRT_RATIO,
    open_ksize: int = REFINE_OPEN_KSIZE,
    close_ksize: int = REFINE_CLOSE_KSIZE,
) -> np.ndarray:
    """
    后处理清洗 occluder_mask：去掉衣服阴影/褶皱、头/裤等误识别。

    入参 occluder_mask 为 bool(H,W)；shirt_region 为已膨胀的衣服区（由
    _detect_shirt_region_from_vis 从 parse 图得到，可 None 降级为纯位置裁剪）。
    返回清洗后的 bool(H,W)。纯几何 + 颜色逻辑，不依赖模型，速度快（<0.5s）。
    """
    mask = occluder_mask.copy()

    # ① 删散点噪点，但保留顶部区域可能的发丝（发梢通常很细）。
    labeled, n = ndi.label(mask)
    sizes = ndi.sum(mask, labeled, range(1, n + 1))
    keep = set()
    for i, s in enumerate(sizes, start=1):
        if s >= min_small_px:
            keep.add(i)
            continue
        # 顶部小连通域更可能是发丝，放宽阈值
        comp = labeled == i
        ys, _ = np.where(comp)
        if ys.size > 0 and (ys.mean() / h) < 0.35:
            hair_min = max(50, min_small_px // 10)   # v1.3：发丝保留阈值放宽，防细发丝被删
            if s >= hair_min:
                keep.add(i)
    mask = np.isin(labeled, list(keep))

    # ② 衣服区减法：把主要落在衣服上的 occluder 组件删掉
    #    （阴影/褶皱长在衣服上；裤腿也常在衣服区/底部）
    if shirt_region is not None:
        labeled2, n2 = ndi.label(mask)
        refined = mask.copy()
        for lbl in range(1, n2 + 1):
            comp = labeled2 == lbl
            sz = int(comp.sum())
            if sz < 100:
                continue
            in_shirt = int((comp & shirt_region).sum())
            if in_shirt / sz > shirt_ratio_thresh:
                refined[comp] = False
        mask = refined

    # ③ 位置裁剪：顶部(头/颈) + 底部(腿/裤)
    top_cut = int(h * top_zone)
    bot_cut = int(h * (1 - bottom_zone))
    mask[:top_cut, :] = False
    mask[bot_cut:, :] = False

    # ④ 二次清理 + 形态学平滑
    labeled3, n3 = ndi.label(mask)
    sizes3 = ndi.sum(mask, labeled3, range(1, n3 + 1))
    keep3 = {i + 1 for i, s in enumerate(sizes3) if s >= secondary_min_px}
    mask = np.isin(labeled3, list(keep3))
    mask = ndi.binary_opening(
        mask, structure=np.ones((open_ksize, open_ksize), dtype=bool), iterations=1
    )
    mask = ndi.binary_closing(
        mask, structure=np.ones((close_ksize, close_ksize), dtype=bool), iterations=1
    )

    return mask


# ---------------------------------------------------------------------------
# 评分 + 版本归档（接入「数字孪生」蓝图的好点子；任何异常都不阻断遮罩生成）
# ---------------------------------------------------------------------------
def _compute_mask_score(body_mask, occluder_mask, person_mask, info, img_h, img_w):
    """根据遮罩客观指标打一个 0-100 的启发式分数 + 标记已知坏情况。

    分数用于「同一胚衣跨版本对比」（这次改好了还是改坏了），不是绝对质量标准。
    返回 (score, metrics, flags)。
    """
    score = 100.0
    flags = []
    person_n = int(person_mask.sum())
    body_n = int(body_mask.sum())
    occ_n = int(occluder_mask.sum())
    img_n = max(1, img_h * img_w)
    occ_ratio = (occ_n / person_n) if person_n > 0 else 0.0
    body_cov = body_n / img_n
    is_person = bool(info.get("is_person", False)) or person_n > 10000

    if body_n == 0:
        score -= 60
        flags.append("no_shirt_body")

    flat_lay = occ_ratio < 0.01          # 几乎无遮挡 = 平铺/纯白底（正常）
    if flat_lay:
        if occ_ratio > 0.05:             # 平铺却被识别出较多遮挡 = 误识别
            score -= 30
            flags.append("flatlay_over_occluded")
    else:
        if occ_ratio > 0.6:              # 模特图遮挡过多 = 把衣服也吃掉了
            score -= 25
            flags.append("occluder_too_much")
        elif occ_ratio < 0.01:           # 有模特却几乎没遮挡 = 漏了手/头发/杯子
            score -= 20
            flags.append("occluder_too_little")

    if body_cov < 0.02:
        score -= 20
        flags.append("shirt_too_small")
    elif body_cov > 0.85:
        score -= 15
        flags.append("shirt_too_large")

    score = max(0.0, min(100.0, score))
    metrics = {
        "is_person": is_person,
        "flat_lay": flat_lay,
        "person_px": person_n,
        "body_px": body_n,
        "occluder_px": occ_n,
        "occ_ratio": round(occ_ratio, 4),
        "body_coverage": round(body_cov, 4),
    }
    return round(score, 1), metrics, flags


def _archive_mask_version(out_dir, stem, saved_files, score, metrics, flags):
    """把本次生成的遮罩结果归档为一个版本 vNNN，并写 score.json + history.json。

    saved_files: dict[str, Path] 已落到标准路径的文件。返回版本号字符串或 None。
    """
    try:
        vroot = Path(out_dir) / VERSION_DIRNAME / stem
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

        for _name, p in saved_files.items():
            p = Path(p)
            if p.exists():
                shutil.copy2(p, vdir / p.name)

        score_obj = {
            "version": f"v{next_n:03d}",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "algorithm_version": VERSION,
            "score": score,
            "metrics": metrics,
            "flags": flags,
        }
        (vdir / "score.json").write_text(
            json.dumps(score_obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        hist_path = vroot / "history.json"
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
        except Exception:
            history = []
        history.append(score_obj)
        hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        (vroot / "latest.txt").write_text(f"v{next_n:03d}", encoding="utf-8")
        return f"v{next_n:03d}"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FASHN 语义分割（懒加载 + 失败回退）
# ---------------------------------------------------------------------------
_fashn = {"proc": None, "model": None, "tried": False}


def _get_fashn():
    """懒加载 FASHN。优先离线缓存(local_files_only)避免生产环境联网卡住；
    缓存没有再尝试在线下载。任何失败返回 None(回退到 BiRefNet+聚类)。"""
    if _fashn["tried"]:
        return (_fashn["proc"], _fashn["model"]) if _fashn["model"] is not None else None
    _fashn["tried"] = True
    try:
        from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
        try:
            proc = SegformerImageProcessor.from_pretrained(FASHN_MODEL, local_files_only=True)
            model = SegformerForSemanticSegmentation.from_pretrained(FASHN_MODEL, local_files_only=True).eval()
        except Exception:
            proc = SegformerImageProcessor.from_pretrained(FASHN_MODEL)
            model = SegformerForSemanticSegmentation.from_pretrained(FASHN_MODEL).eval()
        _fashn["proc"] = proc
        _fashn["model"] = model
        return proc, model
    except Exception:
        return None


def _fashn_segment(image):
    """返回 FASHN 18 类分割图(np.uint8, 同原图尺寸)；失败返回 None。"""
    got = _get_fashn()
    if got is None:
        return None
    proc, model = got
    try:
        inp = proc(images=image, return_tensors="pt")
        with torch.no_grad():
            out = model(**inp)
        up = torch.nn.functional.interpolate(
            out.logits, size=(image.size[1], image.size[0]),
            mode="bilinear", align_corners=False,
        )
        return up.argmax(dim=1)[0].numpy().astype(np.uint8)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------
def generate_masks(
    image_path: str | Path,
    category: Optional[str] = None,
) -> dict:
    """
    为单张胚衣素材生成遮罩文件。

    返回：
        {
            "ok": True/False,
            "image": 原图路径,
            "occluder": occluder RGBA 路径,
            "occluder_mask": 遮挡物灰度路径,
            "body_mask": T 恤主体灰度路径,
            "parse": 可视化路径,
            "alpha": 人像 Alpha 路径,
            "is_person": 是否识别到模特（True/False),
            "body_px": 身体像素数,
            "occluder_px": 遮挡物像素数,
            "elapsed": 耗时,
            "error": 错误信息（失败时）,
        }
    """
    t0 = time.time()
    image_path = Path(image_path)
    if not image_path.exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}

    stem = image_path.stem
    out_dir = image_path.parent

    try:
        image = Image.open(image_path).convert("RGB")
        if image.mode != "RGB":
            image = image.convert("RGB")

        # 1. 人像 matte
        alpha = _infer_matte(image)
        # 降阈值（128 -> 64）找回被高阈值裁掉的半透明发丝；
        # 闭运算把断裂的细发丝重新接回头部；
        # 最后按面积删除孤立噪点（比开运算更能保留细发丝）。
        person_mask = alpha >= (ALPHA_THRESHOLD / 255.0)
        person_mask = ndi.binary_closing(person_mask, iterations=PERSON_CLOSE_ITERS)
        h, w = person_mask.shape
        person_mask = _remove_small_components(
            person_mask, max(80, int(PERSON_MIN_COMP_RATIO * w * h))
        )

        # 2. 颜色聚类分割
        hint = _shirt_color_hint(category)
        body_mask, occluder_mask, parse_vis, info = _color_cluster_split(
            image, person_mask, shirt_color_hint=hint
        )

        # 3. 保存输出
        arr = np.array(image)

        # 后处理清洗：去掉衣服阴影/褶皱、头/裤等误识别（v6 自动修正）。
        # 包在 try 里：即使清洗逻辑异常，也绝不阻断正常遮罩生成。
        shirt_region = _detect_shirt_region_from_vis(parse_vis)  # 从 parse 图识别衣服区
        try:
            occ_before = int(occluder_mask.sum())
            occluder_mask = _refine_occluder_mask(
                occluder_mask, arr.shape[0], arr.shape[1], shirt_region=shirt_region
            )
            info["occluder_px_before_refine"] = occ_before
            info["occluder_px_after_refine"] = int(occluder_mask.sum())
        except Exception as _e:
            info["refine_error"] = f"{type(_e).__name__}: {_e}"

        # ---- FASHN 语义增强（可选；失败自动跳过，不影响原方法结果）----
        # 衣服主体用 FASHN 的 top(更贴合，治 15px 外扩)；遮挡物 = 现在的(杯子)
        # ∪ FASHN 的(戒指/手/头发/首饰)。FASHN 把戒指识别为 jewelry，从根上解决
        # "印花盖到戒指"问题。body 不进最终合成，改动零风险。
        if USE_FASHN:
            seg = _fashn_segment(image)
            if seg is not None:
                f_body = np.isin(seg, list(FASHN_BODY_LABELS))
                f_occ = np.isin(seg, list(FASHN_OCC_LABELS))
                if int(f_body.sum()) > 1000:
                    body_mask = f_body
                else:
                    body_mask = body_mask & (~f_occ)
                occluder_mask = (occluder_mask | f_occ) & (~body_mask)
                info["fashn"] = True
                info["fashn_occ_px"] = int(f_occ.sum())
            else:
                info["fashn"] = False

        # 用清洗后的 occluder 重画可视化（绿=衣服 红=遮挡物）
        parse_vis = arr.copy()
        parse_vis[body_mask] = (
            parse_vis[body_mask] * 0.6 + np.array([0, 255, 0], np.uint8) * 0.4
        ).astype(np.uint8)
        parse_vis[occluder_mask] = (
            parse_vis[occluder_mask] * 0.6 + np.array([255, 0, 0], np.uint8) * 0.4
        ).astype(np.uint8)

        # occluder RGBA：原图像素，遮挡物区域不透明（alpha=255）。
        # v1.2.1 用硬 alpha，并借助上面的 15px 膨胀，盖住 BiRefNet 漏掉的
        # 戒指/杯盖等手边小物；原图 RGB 仍保留，所以最终显示的是戒指/杯盖本身，
        # 而不是被印花覆盖。
        occ_rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
        occ_rgba[:, :, :3] = arr
        occ_rgba[:, :, 3] = (occluder_mask * 255).astype(np.uint8)

        occluder_path = out_dir / f"{stem}_occluder.png"
        occluder_mask_path = out_dir / f"{stem}_occluder_mask.png"
        body_mask_path = out_dir / f"{stem}_body_mask.png"
        parse_path = out_dir / f"{stem}_parse.png"
        alpha_path = out_dir / f"{stem}_alpha.png"

        Image.fromarray(occ_rgba).save(occluder_path, "PNG")
        Image.fromarray((occluder_mask * 255).astype(np.uint8)).save(occluder_mask_path, "PNG")
        Image.fromarray((body_mask * 255).astype(np.uint8)).save(body_mask_path, "PNG")
        Image.fromarray(parse_vis).save(parse_path, "PNG")
        Image.fromarray((alpha * 255).astype(np.uint8)).save(alpha_path, "PNG")

        # ---- 版本归档 + 评分（任何异常都不阻断遮罩生成）----
        score_val, metrics, flags = _compute_mask_score(
            body_mask, occluder_mask, person_mask, info, arr.shape[0], arr.shape[1]
        )
        ver = _archive_mask_version(
            out_dir, stem,
            {
                "occluder": occluder_path,
                "occluder_mask": occluder_mask_path,
                "body_mask": body_mask_path,
                "parse": parse_path,
                "alpha": alpha_path,
            },
            score_val, metrics, flags,
        )

        is_person = info.get("is_person", False) or int(person_mask.sum()) > 10000
        return {
            "ok": True,
            "image": str(image_path),
            "occluder": str(occluder_path),
            "occluder_mask": str(occluder_mask_path),
            "body_mask": str(body_mask_path),
            "parse": str(parse_path),
            "alpha": str(alpha_path),
            "is_person": bool(is_person),
            "body_px": int(body_mask.sum()),
            "occluder_px": int(occluder_mask.sum()),
            "score": score_val,
            "score_flags": flags,
            "version": ver,
            "elapsed": round(time.time() - t0, 2),
            "info": info,
        }

    except Exception as e:
        return {
            "ok": False,
            "image": str(image_path),
            "error": f"{type(e).__name__}: {e}",
            "elapsed": round(time.time() - t0, 2),
        }


# ---------------------------------------------------------------------------
# 小工具：列出某素材已有的遮罩文件
# ---------------------------------------------------------------------------
def mask_status(image_path: str | Path) -> dict:
    """返回一张图片的遮罩生成状态（不重新生成）。"""
    image_path = Path(image_path)
    stem = image_path.stem
    out_dir = image_path.parent
    files = {
        "occluder": out_dir / f"{stem}_occluder.png",
        "occluder_mask": out_dir / f"{stem}_occluder_mask.png",
        "body_mask": out_dir / f"{stem}_body_mask.png",
        "parse": out_dir / f"{stem}_parse.png",
        "alpha": out_dir / f"{stem}_alpha.png",
    }
    exists = {k: str(v) for k, v in files.items() if v.exists()}
    return {
        "has_mask": bool(exists.get("occluder")),
        "files": exists,
        "occluder_px": None,
    }
