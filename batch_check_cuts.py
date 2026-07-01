"""
批量检查 DX0166-DX0286: 02_REM_BG里的去背景图是否由01_AI的原图生成
使用 pHash 快速比对，复合到背景色后进行公平比较
"""

import numpy as np
from PIL import Image
import imagehash
import os
import sys
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
START, END = 166, 286

THRESHOLD_HAMMING = 12  # 汉明距离 > 12 视为不匹配
THRESHOLD_SSIM = 0.60   # SSIM < 0.60 视为不匹配（用于二次确认）

# 使用系统Python的cv2/skimage (仅在需要二次确认时)
USE_DETAILED_CHECK = True
try:
    import cv2
    from skimage.metrics import structural_similarity as ssim
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("⚠ cv2/skimage 不可用，将仅使用 pHash 判断")


def estimate_bg_color(img_np, margin=15):
    """从图像边缘采样估计背景色"""
    h, w = img_np.shape[:2]
    edges = np.vstack([
        img_np[:margin, :, :].reshape(-1, 3),
        img_np[-margin:, :, :].reshape(-1, 3),
        img_np[:, :margin, :].reshape(-1, 3),
        img_np[:, -margin:, :].reshape(-1, 3),
    ])
    return np.median(edges, axis=0)


def composite_rgba_on_bg(cut_pil, bg_color, target_size):
    """将 RGBA 合成到指定背景色上"""
    if cut_pil.mode != "RGBA":
        cut_pil = cut_pil.convert("RGBA")
    if target_size:
        cut_pil = cut_pil.resize(target_size, Image.LANCZOS)
    cut_np = np.array(cut_pil).astype(np.float32)
    alpha = cut_np[:, :, 3:4] / 255.0
    rgb = cut_np[:, :, :3]
    bg = np.array(bg_color, dtype=np.float32).reshape(1, 1, 3)
    comp = np.clip(alpha * rgb + (1 - alpha) * bg, 0, 255).astype(np.uint8)
    return comp


def compute_phash_similarity(orig_pil, cut_pil, bg_color):
    """
    将cut图合成到原图背景色上，然后计算pHash相似度
    返回 (hamming_distance, similarity_0to1)
    """
    target_size = orig_pil.size
    comp = composite_rgba_on_bg(cut_pil, bg_color, target_size)
    comp_pil = Image.fromarray(comp)

    ph_orig = imagehash.phash(orig_pil)
    ph_comp = imagehash.phash(comp_pil)
    hamming = ph_orig - ph_comp
    similarity = 1.0 - hamming / 64
    return hamming, similarity, ph_orig, ph_comp


def compute_ssim(orig_np, cut_pil, bg_color):
    """SSIM 二次确认"""
    target_size = (orig_np.shape[1], orig_np.shape[0])
    comp = composite_rgba_on_bg(cut_pil, bg_color, target_size)
    comp_np = comp.astype(np.float32)
    return ssim(orig_np, comp_np, data_range=255, channel_axis=-1)


def find_matching_original(cut_name, orig_files):
    """
    根据cut文件名找到对应的原图
    返回 (original_filename, is_expected_match)
    """
    # 提取cut的基础名称: DX0166_BW_cut.png → BW
    # DX0166_W_cut.png → W
    # DX0166_B_cut.png → B
    base = cut_name.replace("_cut.png", "")  # DX0166_BW
    suffix = base.split("_", 1)[-1]  # BW or W or B

    # 预期匹配规则
    candidates = []

    if suffix == "BW":
        # BW_cut 可能对应 BW 原图，也可能对应 B 原图
        bw_orig = base + ".png"  # DX0166_BW.png
        b_orig = base.replace("_BW", "_B") + ".png"  # DX0166_B.png
        if bw_orig in orig_files:
            candidates.append((bw_orig, True))
        if b_orig in orig_files:
            candidates.append((b_orig, False))
    elif suffix == "W":
        # W_cut 对应 W 原图
        w_orig = base + ".png"  # DX0166_W.png
        if w_orig in orig_files:
            candidates.append((w_orig, True))
    elif suffix == "B":
        # B_cut 对应 B 原图
        b_orig = base + ".png"  # DX0166_B.png
        if b_orig in orig_files:
            candidates.append((b_orig, True))

    return candidates if candidates else None


def check_project(dx_id):
    """检查单个项目"""
    folder = os.path.join(BASE, f"DX{dx_id:04d}")
    ai_dir = os.path.join(folder, "01_AI")
    rem_dir = os.path.join(folder, "02_REM_BG")

    issues = []

    if not os.path.isdir(ai_dir):
        return ["❌ 01_AI 文件夹不存在"]
    if not os.path.isdir(rem_dir):
        return ["❌ 02_REM_BG 文件夹不存在"]

    # 收集原图 (DX{id}_*.png, 1024x1024 的)
    orig_files = {}
    for f in os.listdir(ai_dir):
        if f.lower().endswith(".png") and f.startswith(f"DX{dx_id:04d}_"):
            fp = os.path.join(ai_dir, f)
            try:
                img = Image.open(fp)
                orig_files[f] = img
            except Exception as e:
                issues.append(f"  ⚠ 无法读取原图 {f}: {e}")

    # 收集去背景图
    cut_files = {}
    for f in os.listdir(rem_dir):
        if f.lower().endswith(".png") and "_cut" in f:
            fp = os.path.join(rem_dir, f)
            try:
                img = Image.open(fp)
                cut_files[f] = img
            except Exception as e:
                issues.append(f"  ⚠ 无法读取去背景图 {f}: {e}")

    if not orig_files:
        issues.append("❌ 01_AI 中没有找到 DX{id}_*.png 原图")
        return issues
    if not cut_files:
        issues.append("❌ 02_REM_BG 中没有找到 _cut.png 去背景图")
        return issues

    # 对每个 cut 文件，找到对应的原图并比较
    for cut_name, cut_img in sorted(cut_files.items()):
        candidates = find_matching_original(cut_name, orig_files)

        if not candidates:
            # 检查是否编号错位（前一个项目的cut跑到了这里）
            issues.append(f"  ⚠ {cut_name} 在 01_AI 中无对应原图")
            continue

        # 尝试所有候选，取最佳匹配
        best_hamming = 999
        best_match_name = None
        best_similarity = 0

        for orig_name, is_expected in candidates:
            orig_img = orig_files[orig_name]
            bg_color = estimate_bg_color(np.array(orig_img))
            hamming, similarity, _, _ = compute_phash_similarity(
                orig_img, cut_img, bg_color
            )

            if hamming < best_hamming:
                best_hamming = hamming
                best_match_name = orig_name
                best_similarity = similarity

        # 判断
        status = "✅" if best_hamming <= THRESHOLD_HAMMING else "❌"
        if best_hamming > THRESHOLD_HAMMING:
            # 二次确认: SSIM
            ssim_val = None
            if HAS_CV2:
                orig_np = np.array(orig_files[best_match_name]).astype(np.float32)
                bg_color = estimate_bg_color(np.array(orig_files[best_match_name]))
                ssim_val = compute_ssim(orig_np, cut_img, bg_color)

                if ssim_val >= THRESHOLD_SSIM:
                    status = "✅"  # SSIM 通过，判定为匹配
                    best_similarity = max(best_similarity, ssim_val)

            issues.append(
                f"  {status} {cut_name} ↔ {best_match_name} "
                f"(汉明距离={best_hamming}, "
                f"{'SSIM=' + f'{ssim_val:.4f}' if ssim_val is not None else 'pHash相似=' + f'{best_similarity:.3f}'})"
            )

    return issues


def main():
    print("=" * 70)
    print(f"🔍 批量检查 DX{START:04d}-DX{END:04d}")
    print(f"   汉明距离阈值: {THRESHOLD_HAMMING}")
    if HAS_CV2:
        print(f"   SSIM二次确认阈值: {THRESHOLD_SSIM}")
    print(f"   使用系统Python: {sys.executable}")
    print("=" * 70)

    results = {}  # dx_id -> list of issue strings
    dx_nonexistent = []

    for dx_id in range(START, END + 1):
        folder = os.path.join(BASE, f"DX{dx_id:04d}")
        if not os.path.isdir(folder):
            dx_nonexistent.append(dx_id)
            continue

        print(f"\n📁 DX{dx_id:04d}...", end="", flush=True)
        issues = check_project(dx_id)
        if issues:
            results[dx_id] = issues
            for iss in issues:
                if iss.startswith("  "):
                    print(f"\n  {iss}", end="")
            print()
        else:
            print(" ✅ 全部匹配", end="")

    # ─── 汇总报告 ───
    print("\n\n" + "=" * 70)
    print("📋 最终汇总报告")
    print("=" * 70)

    # 不存在的项目
    if dx_nonexistent:
        print(f"\n📭 不存在的项目 ({len(dx_nonexistent)}个):")
        # 按连续分组显示
        groups = []
        start = dx_nonexistent[0]
        end = dx_nonexistent[0]
        for i in range(1, len(dx_nonexistent)):
            if dx_nonexistent[i] == end + 1:
                end = dx_nonexistent[i]
            else:
                groups.append((start, end))
                start = end = dx_nonexistent[i]
        groups.append((start, end))
        for s, e in groups:
            if s == e:
                print(f"  DX{s:04d}")
            else:
                print(f"  DX{s:04d}-DX{e:04d}")

    # 有问题的项目
    mismatches = {k: v for k, v in results.items()
                  if any("❌" in iss for iss in v)}
    warnings = {k: v for k, v in results.items()
                if not any("❌" in iss for iss in v) and v}

    if mismatches:
        print(f"\n❌ 不匹配的项目 ({len(mismatches)}个):")
        for dx_id in sorted(mismatches.keys()):
            print(f"\n  📁 DX{dx_id:04d}:")
            for iss in mismatches[dx_id]:
                print(f"    {iss}")

    if warnings:
        print(f"\n⚠ 有注意项但无错误 ({len(warnings)}个):")
        for dx_id in sorted(warnings.keys()):
            print(f"  📁 DX{dx_id:04d}: {len(warnings[dx_id])}项")
            for iss in warnings[dx_id]:
                print(f"    {iss}")

    total_checked = (END - START + 1) - len(dx_nonexistent)
    total_issues = len(mismatches)
    total_warnings = len(warnings)
    total_ok = total_checked - total_issues - total_warnings

    print(f"\n{'=' * 70}")
    print(f"📊 统计:")
    print(f"   总项目数: {END - START + 1}")
    print(f"   实际存在: {total_checked}")
    print(f"   ✅ 全部匹配: {total_ok}")
    print(f"   ⚠ 有注意项: {total_warnings}")
    print(f"   ❌ 有不匹配: {total_issues}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
