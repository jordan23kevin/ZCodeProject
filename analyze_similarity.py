"""
图片相似度分析脚本 - 验证去背景图是否由原图生成
分析维度: SSIM, MSE/PSNR, 直方图相关性, ORB特征匹配, 感知哈希, Alpha通道
"""

import numpy as np
import cv2
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import mean_squared_error, peak_signal_noise_ratio
import imagehash
import sys
import os
from datetime import datetime

# ─── 配置 ──────────────────────────────────────────────────────────────
BASE_DIR = r"D:\Semems WB\02_PROJECTS\DX0192"

PAIRS = [
    {
        "name": "DX0192_B → DX0192_BW_cut",
        "original": os.path.join(BASE_DIR, r"01_AI\DX0192_B.png"),
        "cut": os.path.join(BASE_DIR, r"02_REM_BG\DX0192_BW_cut.png"),
    },
    {
        "name": "DX0192_W → DX0192_W_cut",
        "original": os.path.join(BASE_DIR, r"01_AI\DX0192_W.png"),
        "cut": os.path.join(BASE_DIR, r"02_REM_BG\DX0192_W_cut.png"),
    },
]

OUTPUT_DIR = os.path.join(BASE_DIR, "analysis_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── 工具函数 ─────────────────────────────────────────────────────────

def load_images(orig_path, cut_path):
    """加载原图和去背景图，返回统一尺寸的RGB数组"""
    # 原图 (RGB)
    orig_pil = Image.open(orig_path).convert("RGB")
    orig_np = np.array(orig_pil).astype(np.float32)

    # 去背景图 (RGBA)
    cut_pil = Image.open(cut_path)
    cut_mode = cut_pil.mode
    has_alpha = cut_mode == "RGBA"

    # 提取 RGB
    cut_rgb = cut_pil.convert("RGB")
    cut_np = np.array(cut_rgb).astype(np.float32)

    # 提取 Alpha 通道
    alpha_np = None
    if has_alpha:
        alpha_np = np.array(cut_pil.split()[-1]).astype(np.float32)

    # 记录原始尺寸
    orig_size = orig_pil.size
    cut_size = cut_pil.size

    # 将去背景图缩放到原图尺寸 (用于像素级对比)
    if cut_size != orig_size:
        cut_resized = cut_rgb.resize(orig_size, Image.LANCZOS)
        cut_np_resized = np.array(cut_resized).astype(np.float32)
        if has_alpha:
            alpha_resized = np.array(
                cut_pil.split()[-1].resize(orig_size, Image.LANCZOS)
            ).astype(np.float32)
        else:
            alpha_resized = None
        print(f"  ⚠ 分辨率不同: 原图={orig_size}, 去背景图={cut_size}")
        print(f"  → 已将去背景图缩放至 {orig_size} 进行像素级对比")
    else:
        cut_np_resized = cut_np
        alpha_resized = alpha_np

    return {
        "orig_np": orig_np,
        "orig_size": orig_size,
        "cut_np": cut_np,
        "cut_np_resized": cut_np_resized,
        "cut_size": cut_size,
        "alpha": alpha_resized,
        "has_alpha": has_alpha,
        "orig_pil": orig_pil,
        "cut_pil": cut_pil,
    }


def calc_ssim(img1, img2):
    """结构相似性 (0~1, 越接近1越相似)"""
    # 确保值在 0~255 范围
    ssim_value = ssim(
        img1, img2,
        data_range=255,
        channel_axis=-1,
        win_size=7,
    )
    return ssim_value


def calc_mse_psnr(img1, img2):
    """MSE 和 PSNR"""
    mse = mean_squared_error(img1, img2)
    psnr = peak_signal_noise_ratio(img1, img2, data_range=255)
    return mse, psnr


def calc_hist_correlation(img1, img2):
    """RGB 三通道直方图相关性"""
    img1_uint8 = np.clip(img1, 0, 255).astype(np.uint8)
    img2_uint8 = np.clip(img2, 0, 255).astype(np.uint8)

    correlations = {}
    channels = ["R", "G", "B"]
    for i, ch in enumerate(channels):
        hist1 = cv2.calcHist([img1_uint8], [i], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2_uint8], [i], None, [256], [0, 256])
        # 归一化
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        corr = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        correlations[ch] = float(corr)
    return correlations


def calc_orb_matching(img1, img2):
    """ORB 特征匹配"""
    img1_uint8 = np.clip(img1, 0, 255).astype(np.uint8)
    img2_uint8 = np.clip(img2, 0, 255).astype(np.uint8)

    # 转为灰度
    gray1 = cv2.cvtColor(img1_uint8, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2_uint8, cv2.COLOR_RGB2GRAY)

    orb = cv2.ORB_create(nfeatures=2000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    if des1 is None or des2 is None:
        return 0, 0, 0, [], []

    # 暴力匹配
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    # 按距离排序（越小越好）
    matches = sorted(matches, key=lambda x: x.distance)

    # 计算好匹配的比例 (距离 < 50 的视为好匹配)
    good_matches = [m for m in matches if m.distance < 50]
    match_ratio = len(matches) / max(len(kp1), len(kp2), 1)

    return len(kp1), len(kp2), len(matches), len(good_matches), match_ratio


def calc_phash(orig_pil, cut_pil):
    """感知哈希比较 - 缩放不变的图片指纹"""
    # 将两张图统一尺寸后计算哈希
    phash_orig = imagehash.phash(orig_pil)
    phash_cut = imagehash.phash(cut_pil.convert("RGB"))
    # 汉明距离: 越小越相似
    hamming_dist = phash_orig - phash_cut
    # 归一化相似度: 0~1, >0.8 表示高度相似
    # pHash 64位哈希, 最大距离64
    max_dist = 64
    similarity = 1.0 - (hamming_dist / max_dist)
    return hamming_dist, similarity, phash_orig, phash_cut


def analyze_alpha(alpha, orig_size):
    """分析 Alpha 通道, 检查主体保留情况"""
    if alpha is None:
        return "无Alpha通道（不是RGBA格式）"

    h, w = alpha.shape
    total = h * w

    # 透明区域 (alpha < 10)
    transparent = np.sum(alpha < 10)
    # 半透明区域
    semi = np.sum((alpha >= 10) & (alpha < 245))
    # 不透明区域 (alpha >= 245)
    opaque = np.sum(alpha >= 245)

    trans_pct = transparent / total * 100
    semi_pct = semi / total * 100
    opaque_pct = opaque / total * 100

    # 分析主体轮廓: 检查透明区域是否集中在边缘
    # 创建二值掩码: 主体区域
    mask = (alpha > 128).astype(np.uint8) * 255

    # 寻找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    summary = (
        f"  透明区域: {trans_pct:.1f}% (背景)\n"
        f"  半透明区域: {semi_pct:.1f}% (边缘过渡)\n"
        f"  不透明区域: {opaque_pct:.1f}% (主体)\n"
        f"  主体轮廓数: {len(contours)}"
    )

    # 检查主体完整性: 是否有大的空洞
    if len(contours) == 0:
        summary += "\n  ⚠ 未检测到主体轮廓！"
    elif len(contours) == 1:
        summary += "\n  ✅ 主体完整，单个连续轮廓"
    else:
        # 检查是否有明显的大轮廓
        areas = [cv2.contourArea(c) for c in contours]
        max_area = max(areas)
        if max_area / total < 0.5:
            summary += f"\n  ⚠ 主体可能分散，最大轮廓占比 {max_area/total*100:.1f}%"
        else:
            summary += f"\n  ✅ 主体基本完整 (最大轮廓占比 {max_area/total*100:.1f}%)"

    return summary


def compute_diff_map(img1, img2):
    """生成差异热力图"""
    diff = np.abs(img1.astype(np.float32) - img2.astype(np.float32))
    # 取最大通道差异
    diff_max = np.max(diff, axis=2)
    # 归一化到 0~255
    diff_norm = np.clip(diff_max, 0, 255).astype(np.uint8)
    # 应用颜色映射
    heatmap = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    return heatmap_rgb, diff_norm


def save_visual_comparison(orig_np, cut_np_resized, diff_heatmap, pair_name, suffix=""):
    """保存可视化对比图"""
    h, w = orig_np.shape[:2]

    # 创建对比拼图 (原图 | 去背景图 | 差异热力图)
    orig_uint8 = np.clip(orig_np, 0, 255).astype(np.uint8)
    cut_uint8 = np.clip(cut_np_resized, 0, 255).astype(np.uint8)

    # 并排显示
    panel = np.zeros((h, w * 4, 3), dtype=np.uint8)
    panel[:, :w] = orig_uint8
    panel[:, w : w * 2] = cut_uint8
    panel[:, w * 2 : w * 3] = diff_heatmap

    # 右侧：原图与去背景的半透明叠加
    overlay = cv2.addWeighted(orig_uint8, 0.5, cut_uint8, 0.5, 0)
    panel[:, w * 3 :] = overlay

    # 添加标签
    panel_with_labels = add_labels(panel, w, ["原图", "去背景图", "差异热力图", "叠加对比"])

    save_path = os.path.join(OUTPUT_DIR, f"{pair_name}_comparison{suffix}.png")
    Image.fromarray(panel_with_labels).save(save_path)
    print(f"  📊 可视化对比图已保存: {save_path}")
    return save_path


def add_labels(img, panel_w, labels):
    """给对比图添加文字标签"""
    result = img.copy()
    h, w = img.shape[:2]
    label_h = 30
    # 扩展画布放标签
    result = np.vstack([result, np.ones((label_h, w, 3), dtype=np.uint8) * 255])

    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, label in enumerate(labels):
        x = i * panel_w + panel_w // 2 - len(label) * 5
        cv2.putText(
            result, label, (x, h + 20),
            font, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
        )
    return result


def save_alpha_visualization(alpha, pair_name):
    """保存 Alpha 通道可视化"""
    if alpha is None:
        return

    alpha_uint8 = np.clip(alpha, 0, 255).astype(np.uint8)
    # 应用颜色映射使透明度更直观
    alpha_colored = cv2.applyColorMap(alpha_uint8, cv2.COLORMAP_VIRIDIS)
    alpha_colored_rgb = cv2.cvtColor(alpha_colored, cv2.COLOR_BGR2RGB)

    save_path = os.path.join(OUTPUT_DIR, f"{pair_name}_alpha.png")
    Image.fromarray(alpha_colored_rgb).save(save_path)
    print(f"  🎨 Alpha通道可视化已保存: {save_path}")


# ─── 主分析函数 ─────────────────────────────────────────────────────

def analyze_pair(pair, verbose=True):
    """分析一组图片对"""
    name = pair["name"]
    print("\n" + "=" * 70)
    print(f"📌 分析配对: {name}")
    print("=" * 70)

    # 1. 加载图片
    imgs = load_images(pair["original"], pair["cut"])

    # 2. SSIM
    ssim_val = calc_ssim(imgs["orig_np"], imgs["cut_np_resized"])
    print(f"\n📐 [SSIM 结构相似性]")
    print(f"  SSIM = {ssim_val:.6f}  (1.0 = 完全相同)")
    if ssim_val > 0.99:
        print(f"  ✅ 判断: 结构几乎一致 (>0.99)，同一源图")
    elif ssim_val > 0.95:
        print(f"  ✅ 判断: 高度相似 (>0.95)，极大概率同一源图")
    elif ssim_val > 0.85:
        print(f"  ⚠ 判断: 比较相似 (>0.85)，但可能有明显修改")
    else:
        print(f"  ❌ 判断: 差异较大 (<0.85)，可能不是同一源图")

    # 3. MSE / PSNR
    mse, psnr = calc_mse_psnr(imgs["orig_np"], imgs["cut_np_resized"])
    print(f"\n📏 [MSE / PSNR 像素级误差]")
    print(f"  MSE  = {mse:.4f}  (0 = 完全相同)")
    print(f"  PSNR = {psnr:.2f} dB (∞ = 完全相同)")
    if psnr > 40:
        print(f"  ✅ 判断: 差异极小 (>40dB)，几乎无损")
    elif psnr > 30:
        print(f"  ✅ 判断: 差异较小 (>30dB)，质量良好")
    elif psnr > 20:
        print(f"  ⚠ 判断: 有肉眼可见差异 (>20dB)")
    else:
        print(f"  ❌ 判断: 差异显著 (<20dB)")

    # 4. 直方图相关性
    hist_corr = calc_hist_correlation(imgs["orig_np"], imgs["cut_np_resized"])
    print(f"\n🌈 [直方图相关性]")
    avg_corr = 0
    for ch, val in hist_corr.items():
        status = "✅" if val > 0.9 else ("⚠" if val > 0.7 else "❌")
        print(f"  {status} {ch}通道: {val:.6f}")
        avg_corr += val
    avg_corr /= 3
    if avg_corr > 0.95:
        print(f"  ✅ 结论: 颜色分布高度一致 (>0.95)")
    elif avg_corr > 0.85:
        print(f"  ⚠ 结论: 颜色分布较一致 (>0.85)")
    else:
        print(f"  ❌ 结论: 颜色分布差异明显 (<0.85)")

    # 5. ORB 特征匹配
    kp1, kp2, n_matches, n_good, match_ratio = calc_orb_matching(
        imgs["orig_np"], imgs["cut_np_resized"]
    )
    print(f"\n🔍 [ORB 特征匹配]")
    print(f"  原图特征点: {kp1}")
    print(f"  去背景图特征点: {kp2}")
    print(f"  匹配点: {n_matches}")
    print(f"  优质匹配: {n_good}")
    print(f"  匹配率: {match_ratio*100:.1f}%")
    if kp1 > 0 and kp2 > 0:
        good_ratio = n_good / max(min(kp1, kp2), 1)
        if good_ratio > 0.5:
            print(f"  ✅ 判断: 特征高度匹配 (>50%)，同一源图")
        elif good_ratio > 0.3:
            print(f"  ✅ 判断: 特征较好匹配 (>30%)")
        elif good_ratio > 0.1:
            print(f"  ⚠ 判断: 部分特征匹配 (>10%)，可能有修改")
        else:
            print(f"  ❌ 判断: 特征匹配很少 (<10%)，可能不是同一图")

    # 6. 感知哈希
    hamming_dist, phash_sim, ph1, ph2 = calc_phash(
        imgs["orig_pil"], imgs["cut_pil"]
    )
    print(f"\n🔑 [感知哈希 - pHash]")
    print(f"  原图pH: {ph1}")
    print(f"  去背景pH: {ph2}")
    print(f"  汉明距离: {hamming_dist} (0=完全相同, <10=高度相似)")
    print(f"  哈希相似度: {phash_sim:.4f}")
    if hamming_dist == 0:
        print(f"  ✅ 判断: 哈希完全一致！")
    elif hamming_dist <= 5:
        print(f"  ✅ 判断: 哈希高度相似 (≤5)，极大概率一致")
    elif hamming_dist <= 10:
        print(f"  ✅ 判断: 哈希比较相似 (≤10)")
    elif hamming_dist <= 20:
        print(f"  ⚠ 判断: 哈希有一定相似 (≤20)")
    else:
        print(f"  ❌ 判断: 哈希差异大 (>20)，可能不是同一图")

    # 7. Alpha 通道分析
    print(f"\n🎭 [Alpha通道分析 - 去背景质量]")
    alpha_report = analyze_alpha(imgs["alpha"], imgs["orig_size"])
    print(alpha_report)

    # 8. 综合评分
    print(f"\n" + "-" * 50)
    print(f"📊 [综合评分]")
    
    # 各指标归一化评分 (0~100)
    score_ssim = ssim_val * 100
    score_psnr = min(psnr / 50 * 100, 100)
    score_hist = avg_corr * 100
    score_phash = phash_sim * 100
    score_orb = min(n_good / max(min(kp1, kp2), 1) * 100, 100) if kp1 > 0 and kp2 > 0 else 0
    
    total_score = (score_ssim * 0.25 + score_psnr * 0.15 + 
                   score_hist * 0.20 + score_phash * 0.20 + 
                   score_orb * 0.20)
    
    print(f"  SSIM评分:      {score_ssim:.1f}/100")
    print(f"  PSNR评分:      {score_psnr:.1f}/100")
    print(f"  直方图评分:    {score_hist:.1f}/100")
    print(f"  感知哈希评分:  {score_phash:.1f}/100")
    print(f"  特征匹配评分:  {score_orb:.1f}/100")
    print(f"  ─────────────────")
    print(f"  🏆 综合相似度: {total_score:.1f}/100")
    
    if total_score >= 95:
        final_verdict = "✅ 确定由原图去背景生成（高度一致）"
    elif total_score >= 85:
        final_verdict = "✅ 极大概率由原图去背景生成"
    elif total_score >= 70:
        final_verdict = "⚠ 可能由原图去背景生成，但有一定后期处理"
    elif total_score >= 50:
        final_verdict = "⚠ 部分相似，不确定是否由该原图生成"
    else:
        final_verdict = "❌ 不是由该原图生成（差异显著）"
    
    print(f"\n  📋 最终结论: {final_verdict}")

    # 9. 保存可视化
    diff_heatmap, diff_norm = compute_diff_map(
        imgs["orig_np"], imgs["cut_np_resized"]
    )
    save_visual_comparison(
        imgs["orig_np"], imgs["cut_np_resized"], diff_heatmap, name.replace(" → ", "_vs_")
    )

    # 保存 Alpha 可视化
    if imgs["alpha"] is not None:
        save_alpha_visualization(imgs["alpha"], name.replace(" → ", "_vs_"))

    # 差异统计
    diff_pixels = np.sum(diff_norm > 10)
    total_pixels = diff_norm.shape[0] * diff_norm.shape[1]
    diff_pct = diff_pixels / total_pixels * 100
    print(f"\n📈 [差异像素统计]")
    print(f"  差异显著像素: {diff_pixels}/{total_pixels} ({diff_pct:.2f}%)")
    if diff_pct < 1:
        print(f"  ✅ 几乎无差异")
    elif diff_pct < 5:
        print(f"  ⚠ 有少量差异")
    else:
        print(f"  ❌ 差异较大")

    return total_score, final_verdict


# ─── 主程序 ─────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("🧪 图片相似度全面分析")
    print(f"   分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   输出目录: {OUTPUT_DIR}")
    print("=" * 70)

    results = []
    for pair in PAIRS:
        # 检查文件是否存在
        for key in ["original", "cut"]:
            if not os.path.exists(pair[key]):
                print(f"\n❌ 文件不存在: {pair[key]}")
                continue
        score, verdict = analyze_pair(pair)
        results.append((pair["name"], score, verdict))
        print("\n")

    # 输出汇总
    print("\n" + "=" * 70)
    print("📋 分析汇总")
    print("=" * 70)
    for name, score, verdict in results:
        print(f"\n{name}:")
        print(f"  综合评分: {score:.1f}/100")
        print(f"  结论: {verdict}")

    print(f"\n{'=' * 70}")
    print(f"✅ 分析完成! 可视化结果保存在: {OUTPUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
