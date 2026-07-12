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
import time
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
OCC_OPEN_ITERS = 1

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
# 安全网：遮挡物像素占比极小（< 阈值）时，多半是褶皱/压缩噪点，直接清空 occluder。
OCC_MIN_RATIO = 0.03          # 遮挡物像素 / 人像像素 的最小比例；平铺图里残留的道具/鞋/徽章通常 <3%，会被清空；真遮挡物（手/头发）通常 >10%，正常保留。
# 空间过滤：只保留位于衣服主体凸包内部的遮挡物。
# 平铺图里的鞋子、装饰徽章、背景道具等虽然在前景内，但位于衣服外部，应剔除；
# 真正遮挡物（手/头发/杯子）都压在衣服表面，位于凸包内。
OCC_HULL_DILATE_ITERS = 5    # 凸包外扩 5px，兼容发梢/边缘抗锯齿

SUFFIX_BODY_MASK = "body_mask.png"
SUFFIX_OCCLUDER_MASK = "occluder_mask.png"
SUFFIX_OCCLUDER = "occluder.png"
SUFFIX_PARSE = "parse.png"
SUFFIX_ALPHA = "alpha.png"

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

    body_mask = np.zeros_like(person_mask)
    body_mask[ys, xs] = is_shirt
    # 形态学：填掉褶皱内部因局部色度抖动产生的空洞
    body_mask = ndi.binary_closing(body_mask, iterations=BODY_CLOSE_ITERS)
    body_mask = ndi.binary_opening(body_mask, iterations=BODY_OPEN_ITERS)

    occluder_mask = person_mask & (~body_mask)

    # 同时计算两个凸包：
    #   - 人像凸包：保留头/手臂/头发等真实遮挡物；
    #   - 衣服主体凸包：用来区分「衣服内部」与「衣服外部」。
    def _hull_mask(mask: np.ndarray, dilate: int) -> np.ndarray:
        m_u8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            m_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return np.ones_like(mask, dtype=np.uint8)
        all_pts = np.vstack(contours)
        hull = cv2.convexHull(all_pts)
        hm = np.zeros_like(mask, dtype=np.uint8)
        cv2.fillPoly(hm, [hull], 1)
        if dilate > 0:
            hm = ndi.binary_dilation(hm, iterations=dilate)
        return hm

    person_hull_mask = _hull_mask(person_mask, OCC_HULL_DILATE_ITERS)
    body_hull_mask = _hull_mask(body_mask, OCC_HULL_DILATE_ITERS)

    # 空间过滤：只保留位于「整个人像轮廓凸包」内部的遮挡物。
    # 之前用「衣服主体凸包」，会把头顶上方的头发（在衣服轮廓之外）误裁掉；
    # 改用「整个人像（含头/手臂）凸包」后，头发与手都落在凸包内被保留，
    # 而平铺图里位于衣服外的鞋子/徽章等道具仍在人像轮廓之外被剔除。
    occluder_mask = occluder_mask & person_hull_mask

    # 把「与衣服同色度、但其实是遮挡物一部分」的 body 区域补回 occluder：
    #   典型1：白色手指甲（白 T 上白色指甲的色度与衣服一致被归为 body）——
    #         小块，且紧邻皮肤/头发（occluder）。
    #   典型2：白色/浅色头发落在衣服外（如白金发、银发）——
    #         与衣服色度相同，但位于衣服主体凸包之外，且与皮肤/头发相连。
    # 判定：body 连通域若与 occluder 相邻，且满足「小」或「主要位于衣服外」任一条件，
    # 则翻为 occluder。真正的衣服主体（面积大且位于衣服凸包内）不受影响。
    body_labeled, ncomp = ndi.label(body_mask)
    if ncomp > 1:
        person_n = int(person_mask.sum())
        flip_min = max(NAIL_FLIP_MIN_AREA_ABS, int(NAIL_FLIP_MIN_RATIO * person_n))
        for c in range(1, ncomp + 1):
            comp = body_labeled == c
            area = int(comp.sum())
            grown = ndi.binary_dilation(comp, iterations=1) & person_mask
            if not (grown & occluder_mask).any():
                continue  # 与 occluder 不相邻，不可能是其一部分
            if area < flip_min:
                # 小块：指甲、白色配饰等 -> occluder
                flip = True
            else:
                # 大块：只有当它主要位于衣服凸包外（如头发、脸）才翻转；
                # 衣服主体（位于凸包内）保持 body。
                overlap = (comp & body_hull_mask).sum()
                flip = (overlap < area * 0.5)
            if flip:
                occluder_mask = occluder_mask | comp
                body_mask = body_mask & (~comp)

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
REFINE_MIN_SMALL_PX = 1500       # ① 删散点：小于此面积的连通域删除
REFINE_TOP_ZONE = 0.12           # ③ 顶部裁剪比例（头/颈）
REFINE_BOTTOM_ZONE = 0.12        # ③ 底部裁剪比例（腿/裤）
REFINE_SECONDARY_MIN_PX = 3000   # ④ 二次清理阈值
REFINE_SHIRT_RATIO = 0.45        # ② 组件落在衣服区占比 > 此值 → 删除
REFINE_SHIRT_DIL_ITER = 10       # ② 衣服区膨胀次数（覆盖阴影溢出边界）
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

    # ① 删散点噪点
    labeled, n = ndi.label(mask)
    sizes = ndi.sum(mask, labeled, range(1, n + 1))
    keep = {i + 1 for i, s in enumerate(sizes) if s >= min_small_px}
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

        # 用清洗后的 occluder 重画可视化（绿=衣服 红=遮挡物）
        parse_vis = arr.copy()
        parse_vis[body_mask] = (
            parse_vis[body_mask] * 0.6 + np.array([0, 255, 0], np.uint8) * 0.4
        ).astype(np.uint8)
        parse_vis[occluder_mask] = (
            parse_vis[occluder_mask] * 0.6 + np.array([255, 0, 0], np.uint8) * 0.4
        ).astype(np.uint8)

        # occluder RGBA：原图像素，仅遮挡物区域不透明。
        # 用原始 matte 的软 alpha 乘到遮挡物区域，使发丝/边缘自然半透明，避免硬边光晕。
        occ_rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
        occ_rgba[:, :, :3] = arr
        soft = (alpha * 255).astype(np.uint8)
        occ_rgba[:, :, 3] = (occluder_mask * soft).astype(np.uint8)

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
