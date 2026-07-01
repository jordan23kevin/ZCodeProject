"""
反向匹配: 对每个 02_REM_BG 的 cut 文件，在所有 01_AI 中找对应的原图
全覆盖 DX0001-DX0286
"""

import numpy as np
from PIL import Image
import imagehash
import os
import re
from datetime import datetime
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
HASH_THRESHOLD = 12


def estimate_bg_color(img_np, margin=15):
    h, w = img_np.shape[:2]
    edges = np.vstack([
        img_np[:margin, :, :].reshape(-1, 3),
        img_np[-margin:, :, :].reshape(-1, 3),
        img_np[:, :margin, :].reshape(-1, 3),
        img_np[:, -margin:, :].reshape(-1, 3),
    ])
    return np.median(edges, axis=0)


def composite_rgba_on_bg(cut_pil, bg_color, target_size):
    if cut_pil.mode != "RGBA":
        cut_pil = cut_pil.convert("RGBA")
    if target_size:
        cut_pil = cut_pil.resize(target_size, Image.LANCZOS)
    cut_np = np.array(cut_pil).astype(np.float32)
    alpha = cut_np[:, :, 3:4] / 255.0
    rgb = cut_np[:, :, :3]
    bg = np.array(bg_color, dtype=np.float32).reshape(1, 1, 3)
    return np.clip(alpha * rgb + (1 - alpha) * bg, 0, 255).astype(np.uint8)


# ─── 步骤1: 预计算所有 01_AI 原图的 pHash ────────────────────────

def precompute_originals():
    """预计算所有 01_AI 原图的 pHash"""
    originals = []  # [(dx_id, fname, fullpath, phash)]

    for d in sorted(os.listdir(BASE)):
        m = re.match(r'DX(\d{4})', d)
        if not m:
            continue
        dx_id = int(m.group(1))
        ai_dir = os.path.join(BASE, d, "01_AI")
        if not os.path.isdir(ai_dir):
            continue

        for f in sorted(os.listdir(ai_dir)):
            if not (f.lower().endswith(".png") and re.match(rf'DX{dx_id:04d}_.+\.png', f)):
                continue
            fp = os.path.join(ai_dir, f)
            try:
                img = Image.open(fp)
                if img.size != (1024, 1024):
                    continue
                ph = imagehash.phash(img)
                bg_color = estimate_bg_color(np.array(img))
                originals.append((dx_id, f, fp, ph, bg_color, img))
            except:
                pass

    return originals


# ─── 步骤2: 对每个 cut 文件找匹配 ────────────────────────────────

def analyze_cut(cut_dx, cut_fname, cut_fp, originals):
    """对单个 cut 文件，在所有原图中找最佳匹配"""
    try:
        cut_pil = Image.open(cut_fp)
    except:
        return None

    results = []
    # 对每个原图，用它的背景色合成 cut 后再比较
    for orig_dx, orig_fname, orig_fp, orig_ph, bg_color, orig_img in originals:
        comp = composite_rgba_on_bg(cut_pil, bg_color, (1024, 1024))
        comp_pil = Image.fromarray(comp)
        cut_ph = imagehash.phash(comp_pil)
        hamming = orig_ph - cut_ph
        results.append((hamming, orig_dx, orig_fname))

    # 按汉明距离排序
    results.sort(key=lambda x: x[0])

    best = results[0]
    second = results[1] if len(results) > 1 else None

    # 判断状态
    same_folder = (best[1] == cut_dx)
    best_orig_suffix = best[2].replace(f"DX{best[1]:04d}_", "").replace(".png", "")
    cut_suffix = cut_fname.replace(f"DX{cut_dx:04d}_", "").replace("_cut.png", "")

    naming_match = False
    if same_folder:
        if best_orig_suffix == cut_suffix:
            naming_match = True
        elif best_orig_suffix == "BW" and cut_suffix == "W":
            # BW→W_cut 是不对的，但图片是匹配的
            pass
        elif best_orig_suffix == "B" and cut_suffix == "BW":
            pass

    return {
        "cut_dx": cut_dx,
        "cut_fname": cut_fname,
        "best_dx": best[1],
        "best_fname": best[2],
        "hamming": best[0],
        "same_folder": same_folder,
        "naming_match": naming_match,
        "best_suffix": best_orig_suffix,
        "cut_suffix": cut_suffix,
    }


# ─── 主程序 ───────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("🔄 反向匹配: 02_REM_BG cut → 01_AI 原图")
    print(f"   时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    # 预计算原图
    print("\n📦 预计算所有 01_AI 原图的 pHash...")
    originals = precompute_originals()
    print(f"   找到 {len(originals)} 张 1024x1024 原图")

    # 收集所有 cut 文件
    all_cuts = []
    for d in sorted(os.listdir(BASE)):
        m = re.match(r'DX(\d{4})', d)
        if not m:
            continue
        dx_id = int(m.group(1))
        rem_dir = os.path.join(BASE, d, "02_REM_BG")
        if not os.path.isdir(rem_dir):
            continue
        for f in sorted(os.listdir(rem_dir)):
            if f.lower().endswith(".png") and "_cut" in f:
                all_cuts.append((dx_id, f, os.path.join(rem_dir, f)))

    print(f"   找到 {len(all_cuts)} 个 cut 文件")
    print(f"\n{'=' * 70}")
    print("📋 匹配结果")
    print(f"{'=' * 70}")

    # 如果过多，只显示有问题的
    issues = []
    correct = 0

    for cut_dx, cut_fname, cut_fp in all_cuts:
        result = analyze_cut(cut_dx, cut_fname, cut_fp, originals)
        if result is None:
            print(f"  ⚠ {cut_fname}: 无法读取")
            continue

        h = result["hamming"]
        same = result["same_folder"]
        naming = result["naming_match"]

        if same and naming and h <= HASH_THRESHOLD:
            correct += 1
            continue  # 正确匹配，不显示

        if same and not naming and h <= HASH_THRESHOLD:
            # 同文件夹但后缀不对
            print(f"  ⚠ {cut_fname} ↔ {result['best_fname']} (汉明距离={h}) — 后缀不匹配")
            issues.append(("rename", result))
        elif not same and h <= HASH_THRESHOLD:
            # 最佳匹配在其他文件夹
            print(f"  ❌ {cut_fname} → 实际原图: DX{result['best_dx']:04d}/{result['best_fname']} (汉明距离={h})")
            issues.append(("move", result))
        elif h > HASH_THRESHOLD:
            # 没有好的匹配
            print(f"  ❓ {cut_fname}: 无匹配原图 (最佳={result['best_fname']}, hamming={h})")
            issues.append(("orphan", result))

    # 汇总
    print(f"\n{'=' * 70}")
    print("📊 汇总")
    print(f"{'=' * 70}")
    print(f"   总 cut 文件: {len(all_cuts)}")
    print(f"   ✅ 正确匹配: {correct}")
    print(f"   ⚠ 后缀不匹配: {len([x for x in issues if x[0]=='rename'])}")
    print(f"   ❌ 放错位置: {len([x for x in issues if x[0]=='move'])}")
    print(f"   ❓ 无匹配: {len([x for x in issues if x[0]=='orphan'])}")

    # 列出放错位置的详细清单
    moves = [x for x in issues if x[0] == "move"]
    if moves:
        print(f"\n{'─' * 70}")
        print("❌ 仍然放错位置的 cut 文件:")
        print(f"{'─' * 70}")
        for typ, r in moves:
            print(f"   {r['cut_fname']} (DX{r['cut_dx']:04d})")
            print(f"     → 原图在: DX{r['best_dx']:04d}/{r['best_fname']} (hamming={r['hamming']})")
            print()

    # 列出无匹配的
    orphans = [x for x in issues if x[0] == "orphan"]
    if orphans:
        print(f"\n{'─' * 70}")
        print("❓ 无匹配原图的 cut 文件:")
        print(f"{'─' * 70}")
        for typ, r in orphans:
            print(f"   {r['cut_fname']} (DX{r['cut_dx']:04d}) — 在所有 01_AI 中均无匹配")


if __name__ == "__main__":
    main()
