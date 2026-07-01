"""
图片相似度分析 v2 - 正确处理背景透明问题
关键改进：
- 用 Alpha 通道作为掩码，只对主体区域进行像素对比
- 将去背景图合成到原图的背景色上再进行对比
- 更准确地评估"是否由同一原图去背景生成"
"""

import numpy as np
import cv2
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import mean_squared_error, peak_signal_noise_ratio
import imagehash
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


def estimate_bg_color(img_np, margin=20):
    """从图像边缘采样估计背景色"""
    h, w = img_np.shape[:2]
    # 取四边边缘像素
    top = img_np[:margin, :, :]
    bottom = img_np[-margin:, :, :]
    left = img_np[:, :margin, :]
    right = img_np[:, -margin:, :]
    edges = np.vstack([top.reshape(-1, 3), bottom.reshape(-1, 3),
                       left.reshape(-1, 3), right.reshape(-1, 3)])
    # 取中位数作为背景色（更鲁棒）
    bg_color = np.median(edges, axis=0)
    return bg_color


def composite_on_bg(cut_pil, bg_color, target_size=None):
    """
    将 RGBA 图像合成到指定背景色上
    公式: result = alpha * fg + (1-alpha) * bg
    """
    if cut_pil.mode != "RGBA":
        cut_pil = cut_pil.convert("RGBA")

    if target_size:
        cut_pil = cut_pil.resize(target_size, Image.LANCZOS)

    cut_np = np.array(cut_pil).astype(np.float32)
    alpha = cut_np[:, :, 3:4] / 255.0  # [H, W, 1]
    rgb = cut_np[:, :, :3]
    bg = np.array(bg_color, dtype=np.float32).reshape(1, 1, 3)

    # 合成: result = alpha * fg + (1-alpha) * bg
    composited = alpha * rgb + (1 - alpha) * bg
    composited = np.clip(composited, 0, 255).astype(np.uint8)
    return composited, alpha.squeeze()


def compare_masked(orig_np, cut_np, alpha_mask, threshold=0.5):
    """
    仅在主体区域（alpha > threshold）进行对比
    """
    mask = alpha_mask > threshold
    if mask.sum() == 0:
        return None, None, None  # 没有主体

    orig_masked = orig_np[mask]
    cut_masked = cut_np[mask]

    mse = mean_squared_error(orig_masked, cut_masked)
    psnr = peak_signal_noise_ratio(orig_masked, cut_masked, data_range=255)

    # 仅对主体区域计算 SSIM (需要 reshape 回 2D)
    # 用全图 SSIM 但只关注主体区域
    ssim_full = ssim(orig_np, cut_np, data_range=255, channel_axis=-1)

    # 计算主体区域的差异统计
    diff = np.abs(orig_np.astype(np.float32) - cut_np.astype(np.float32))
    diff_per_pixel = np.mean(diff, axis=2)  # 平均通道差异

    # 主体区域的平均差异
    subject_mean_diff = diff_per_pixel[mask].mean()

    return ssim_full, mse, psnr, subject_mean_diff, mask


def calc_hist_correlation_masked(img1, img2, mask):
    """在掩码区域内计算直方图相关性"""
    mask_bool = mask > 0.5
    if mask_bool.sum() < 100:
        return None

    img1_uint8 = np.clip(img1, 0, 255).astype(np.uint8)
    img2_uint8 = np.clip(img2, 0, 255).astype(np.uint8)

    correlations = {}
    channels = ["R", "G", "B"]
    for i, ch in enumerate(channels):
        # 提取掩码区域的像素
        pixels1 = img1_uint8[:, :, i][mask_bool]
        pixels2 = img2_uint8[:, :, i][mask_bool]

        hist1 = np.histogram(pixels1, bins=256, range=(0, 256))[0].astype(np.float32)
        hist2 = np.histogram(pixels2, bins=256, range=(0, 256))[0].astype(np.float32)

        # 归一化
        hist1 = hist1 / (hist1.sum() + 1e-10)
        hist2 = hist2 / (hist2.sum() + 1e-10)

        # 相关性
        corr = np.corrcoef(hist1, hist2)[0, 1]
        if np.isnan(corr):
            corr = 0.0
        correlations[ch] = float(corr)
    return correlations


def calc_orb_matching(img1, img2, mask=None):
    """ORB 特征匹配"""
    img1_uint8 = np.clip(img1, 0, 255).astype(np.uint8)
    img2_uint8 = np.clip(img2, 0, 255).astype(np.uint8)

    gray1 = cv2.cvtColor(img1_uint8, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2_uint8, cv2.COLOR_RGB2GRAY)

    orb = cv2.ORB_create(nfeatures=2000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:
        return 0, 0, 0, 0, 0.0

    # FLANN 匹配（更快更准）
    FLANN_INDEX_LSH = 6
    index_params = dict(algorithm=FLANN_INDEX_LSH,
                        table_number=12, key_size=20, multi_probe_level=2)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)

    # Lowe's ratio test
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

    match_ratio = len(good_matches) / max(len(kp1), len(kp2), 1)
    return len(kp1), len(kp2), len(good_matches), match_ratio


def load_and_prepare(orig_path, cut_path):
    """加载并准备对比数据"""
    # 原图
    orig_pil = Image.open(orig_path).convert("RGB")
    orig_np = np.array(orig_pil)

    # 估计原图背景色
    bg_color = estimate_bg_color(orig_np)
    print(f"  估计原图背景色: RGB({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")

    # 去背景图
    cut_pil = Image.open(cut_path)
    cut_size = cut_pil.size
    orig_size = orig_pil.size

    print(f"  原图尺寸: {orig_size}, 去背景图尺寸: {cut_size}")

    # 方案A: 将去背景图合成到原图背景色上（公平像素对比）
    composited = composite_on_bg(cut_pil, bg_color, target_size=orig_size)
    comp_np, alpha = composited

    # 方案B: 将去背景图合成到白色背景上（模拟透明转白色）
    white_bg = [255, 255, 255]
    comp_white, _ = composite_on_bg(cut_pil, white_bg, target_size=orig_size)

    # 方案C: 将去背景图合成到黑色背景上（模拟透明转黑色）
    black_bg = [0, 0, 0]
    comp_black, _ = composite_on_bg(cut_pil, black_bg, target_size=orig_size)

    return {
        "orig_np": orig_np,
        "orig_pil": orig_pil,
        "orig_size": orig_size,
        "comp_np": comp_np,        # 合成到原图背景色
        "comp_white": comp_white,  # 合成到白色
        "comp_black": comp_black,  # 合成到黑色
        "alpha": alpha,
        "bg_color": bg_color,
        "cut_size": cut_size,
    }


def visualize_results(orig_np, comp_np, comp_white, alpha, diff_masked,
                       pair_name):
    """生成全面的可视化对比图"""
    h, w = orig_np.shape[:2]

    # 差异热力图（主体区域）
    diff = np.abs(orig_np.astype(np.float32) - comp_np.astype(np.float32))
    diff_max = np.max(diff, axis=2).astype(np.uint8)
    heatmap = cv2.applyColorMap(diff_max, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    # Alpha 通道热力图
    alpha_uint8 = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    alpha_colored = cv2.applyColorMap(alpha_uint8, cv2.COLORMAP_VIRIDIS)
    alpha_colored_rgb = cv2.cvtColor(alpha_colored, cv2.COLOR_BGR2RGB)

    # 主体掩码叠加到原图
    mask_3ch = np.stack([alpha, alpha, alpha], axis=2)
    overlay_orig = (orig_np * 0.6 + comp_np * 0.4 * mask_3ch).astype(np.uint8)

    # 创建 2x3 网格
    panel_w, panel_h = w, h
    rows, cols = 2, 3
    canvas = np.zeros((panel_h * rows + 60, panel_w * cols, 3), dtype=np.uint8)

    def place(img, row, col, label=""):
        y0 = row * panel_h + (30 if row > 0 else 0)
        x0 = col * panel_w
        canvas[y0:y0 + h, x0:x0 + w] = img[:h, :w]
        if label:
            cv2.putText(canvas, label, (x0 + 10, y0 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    place(orig_np, 0, 0, "原图 (Original)")
    place(comp_white, 0, 1, "去背景图+白背景")
    place(comp_np, 0, 2, "去背景图+原背景色")
    place(alpha_colored_rgb, 1, 0, "Alpha通道 (主体区域)")
    place(heatmap_rgb, 1, 1, "差异热力图")
    place(overlay_orig, 1, 2, "主体重叠对比")

    save_path = os.path.join(OUTPUT_DIR, f"{pair_name}_full_analysis.png")
    Image.fromarray(canvas).save(save_path)
    print(f"  📊 完整分析图已保存: {save_path}")
    return save_path


def analyze_pair(pair):
    """分析一组图片对"""
    name = pair["name"]
    print("\n" + "=" * 70)
    print(f"📌 分析配对: {name}")
    print("=" * 70)

    # 1. 加载准备
    data = load_and_prepare(pair["original"], pair["cut"])

    # ─── 对比一: 去背景图合成到原图背景色 ───
    print(f"\n{'─' * 50}")
    print("📊 对比 A: 去背景图合成到原图背景色（最公平对比）")
    print(f"{'─' * 50}")

    ssim_val, mse, psnr, subj_diff, mask = compare_masked(
        data["orig_np"].astype(np.float32),
        data["comp_np"].astype(np.float32),
        data["alpha"]
    )

    if ssim_val is not None:
        print(f"  SSIM (全图): {ssim_val:.6f}")
        print(f"  MSE (全图):  {mse:.4f}")
        print(f"  PSNR (全图): {psnr:.2f} dB")
        print(f"  主体区域平均像素差异: {subj_diff:.2f} / 255")

        subject_pixels = mask.sum()
        total_pixels = mask.size
        subject_pct = subject_pixels / total_pixels * 100
        print(f"  主体区域占比: {subject_pct:.1f}%")

        # 主体区域差异比例
        diff_per_pixel = np.mean(
            np.abs(data["orig_np"].astype(np.float32) - data["comp_np"].astype(np.float32)),
            axis=2
        )
        subject_diff_pixels = (diff_per_pixel[mask] > 10).sum()
        subject_diff_pct = subject_diff_pixels / subject_pixels * 100 if subject_pixels > 0 else 0
        print(f"  主体区域中差异>10的像素: {subject_diff_pct:.1f}%")

        if ssim_val > 0.98 and subject_diff_pct < 1:
            print(f"  ✅ 主体区域几乎完全一致！")
        elif ssim_val > 0.90 and subject_diff_pct < 5:
            print(f"  ✅ 主体高度一致")
        elif ssim_val > 0.80:
            print(f"  ⚠ 主体基本一致，可能有轻微后期处理")
        else:
            print(f"  ⚠ 主体有一定差异 (SSIM={ssim_val:.4f})")

    # ─── 对比二: 主体区域直方图 ───
    print(f"\n{'─' * 50}")
    print("🌈 对比 B: 主体区域直方图相关性（掩码区域）")
    print(f"{'─' * 50}")

    hist_corr = calc_hist_correlation_masked(
        data["orig_np"].astype(np.float32),
        data["comp_np"].astype(np.float32),
        data["alpha"]
    )

    if hist_corr is not None:
        avg_corr = 0
        for ch, val in hist_corr.items():
            status = "✅" if val > 0.95 else ("⚠" if val > 0.8 else "❌")
            print(f"  {status} {ch}通道: {val:.6f}")
            avg_corr += val
        avg_corr /= 3
        print(f"  平均相关性: {avg_corr:.6f}")
    else:
        avg_corr = 0
        print(f"  ⚠ 主体区域太小，无法计算有效直方图")

    # ─── 对比三: ORB 特征匹配 ───
    print(f"\n{'─' * 50}")
    print("🔍 对比 C: ORB 特征匹配（缩放不变）")
    print(f"{'─' * 50}")

    kp1, kp2, n_good, match_ratio = calc_orb_matching(
        data["orig_np"].astype(np.float32),
        data["comp_np"].astype(np.float32)
    )

    print(f"  原图特征点: {kp1}")
    print(f"  去背景图特征点: {kp2}")
    print(f"  优质匹配 (Lowe's test): {n_good}")
    print(f"  匹配率: {match_ratio*100:.1f}%")

    if match_ratio > 0.5:
        print(f"  ✅ 特征高度匹配 (>50%)")
    elif match_ratio > 0.3:
        print(f"  ✅ 特征较好匹配 (>30%)")
    elif match_ratio > 0.1:
        print(f"  ⚠ 部分特征匹配 (>10%)")
    else:
        print(f"  ❌ 特征匹配很少 (<10%)")

    # ─── 对比四: 感知哈希 ───
    print(f"\n{'─' * 50}")
    print("🔑 对比 D: 感知哈希 (pHash)")
    print(f"{'─' * 50}")

    # 对合成到原背景色的版本计算哈希
    comp_pil = Image.fromarray(data["comp_np"])
    ph_orig = imagehash.phash(data["orig_pil"])
    ph_comp = imagehash.phash(comp_pil)
    hamming = ph_orig - ph_comp
    ph_sim = 1.0 - hamming / 64

    print(f"  原图pHash:      {ph_orig}")
    print(f"  去背景pHash:    {ph_comp}")
    print(f"  汉明距离:       {hamming}")
    print(f"  哈希相似度:     {ph_sim:.4f}")

    if hamming <= 3:
        print(f"  ✅ 哈希高度一致")
    elif hamming <= 8:
        print(f"  ✅ 哈希比较相似")
    elif hamming <= 15:
        print(f"  ⚠ 哈希有一定相似")
    else:
        print(f"  ❌ 哈希差异较大")

    # ─── 对比五: Alpha 通道分析 ───
    print(f"\n{'─' * 50}")
    print("🎭 对比 E: Alpha 通道分析（去背景质量）")
    print(f"{'─' * 50}")

    alpha = data["alpha"]
    h_a, w_a = alpha.shape
    total_a = h_a * w_a
    transparent = np.sum(alpha < 0.05) / total_a * 100
    semi = np.sum((alpha >= 0.05) & (alpha < 0.95)) / total_a * 100
    opaque = np.sum(alpha >= 0.95) / total_a * 100

    print(f"  透明区域 (背景):    {transparent:.1f}%")
    print(f"  半透明区域 (边缘):  {semi:.1f}%")
    print(f"  不透明区域 (主体):  {opaque:.1f}%")

    # 主体轮廓完整性
    mask_uint8 = (alpha > 0.5).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 1:
        print(f"  ✅ 主体完整，单个连续轮廓")
    elif len(contours) <= 3:
        print(f"  ⚠ 主体基本完整，{len(contours)}个轮廓")
    else:
        print(f"  ⚠ 主体分散，{len(contours)}个轮廓")

    # ─── 综合评分 ───
    print(f"\n{'─' * 50}")
    print("📊 [综合评分]")
    print(f"{'─' * 50}")

    # 各指标归一化评分 (0~100)
    score_ssim = ssim_val * 100 if ssim_val is not None else 0
    score_psnr = min(psnr / 50 * 100, 100) if psnr is not None else 0
    score_hist = max(avg_corr * 100, 0) if avg_corr else 0
    score_phash = ph_sim * 100
    score_orb = min(match_ratio * 100, 100)

    # 权重: SSIM 最重要（主体结构）
    total_score = (score_ssim * 0.30 + score_psnr * 0.10 +
                   score_hist * 0.15 + score_phash * 0.20 +
                   score_orb * 0.25)

    print(f"  SSIM评分:      {score_ssim:.1f}/100  (权重30%)")
    print(f"  PSNR评分:      {score_psnr:.1f}/100  (权重10%)")
    print(f"  直方图评分:    {score_hist:.1f}/100  (权重15%)")
    print(f"  感知哈希评分:  {score_phash:.1f}/100  (权重20%)")
    print(f"  特征匹配评分:  {score_orb:.1f}/100  (权重25%)")
    print(f"  ─────────────────────")
    print(f"  🏆 综合相似度: {total_score:.1f}/100")

    if total_score >= 95:
        verdict = "✅ 确定由原图去背景生成（主体完全一致）"
    elif total_score >= 85:
        verdict = "✅ 极大概率由原图去背景生成"
    elif total_score >= 70:
        verdict = "✅ 很可能由原图去背景生成（可能有轻微后期处理）"
    elif total_score >= 55:
        verdict = "⚠ 可能是同一源图，但有较明显的后期修改"
    elif total_score >= 40:
        verdict = "⚠ 不确定：部分相似但差异明显"
    else:
        verdict = "❌ 不是由该原图生成（差异显著）"

    print(f"\n  📋 最终结论: {verdict}")

    # ─── 生成可视化 ───
    visualize_results(
        data["orig_np"],
        data["comp_np"],
        data["comp_white"],
        data["alpha"],
        None,
        name.replace(" → ", "_")
    )

    return total_score, verdict


def main():
    print("=" * 70)
    print("🧪 图片相似度全面分析 v2（正确处理透明背景）")
    print(f"   分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   输出目录: {OUTPUT_DIR}")
    print("=" * 70)

    results = []
    for pair in PAIRS:
        if not all(os.path.exists(pair[k]) for k in ["original", "cut"]):
            print(f"\n❌ 文件不存在: {pair['original']} 或 {pair['cut']}")
            continue
        score, verdict = analyze_pair(pair)
        results.append((pair["name"], score, verdict))

    # 汇总
    print("\n\n" + "=" * 70)
    print("📋 最终分析汇总")
    print("=" * 70)
    for name, score, verdict in results:
        print(f"\n{name}:")
        print(f"  综合评分: {score:.1f}/100")
        print(f"  结论: {verdict}")

    print(f"\n{'=' * 70}")
    print(f"✅ 分析完成! 完整可视化图保存在: {OUTPUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
