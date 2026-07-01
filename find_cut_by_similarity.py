"""
拿着 01_AI 的原图，到所有 02_REM_BG 里按图片相似度找到真正的去背景图
"""

import numpy as np
from PIL import Image
import imagehash
import os
import re
from datetime import datetime
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
START_ID, END_ID = 166, 286  # 我们关注的范围
HASH_THRESHOLD = 15  # 汉明距离 < 15 视为潜在匹配

# ─── 预计算：所有 cut 文件的 pHash ─────────────────────────────────

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
    comp = np.clip(alpha * rgb + (1 - alpha) * bg, 0, 255).astype(np.uint8)
    return comp


def phash_of_cut(cut_pil, bg_color, target_size):
    """计算 cut 图合成到背景色后的 pHash"""
    comp = composite_rgba_on_bg(cut_pil, bg_color, target_size)
    comp_pil = Image.fromarray(comp)
    return imagehash.phash(comp_pil)


# ─── 步骤1: 收集所有 01_AI 原图 ────────────────────────────────────

def collect_originals():
    """收集 DX0166-DX0286 中所有 01_AI 原图"""
    originals = []  # [(dx_id, filename, fullpath, pil_image, phash)]

    for dx_id in range(START_ID, END_ID + 1):
        ai_dir = os.path.join(BASE, f"DX{dx_id:04d}", "01_AI")
        if not os.path.isdir(ai_dir):
            continue

        for f in sorted(os.listdir(ai_dir)):
            if not (f.lower().endswith(".png") and f.startswith(f"DX{dx_id:04d}_")):
                continue
            fp = os.path.join(ai_dir, f)
            try:
                img = Image.open(fp)
                if img.size != (1024, 1024):
                    continue  # 只取 1024x1024 的 AI 输出
                ph = imagehash.phash(img)
                originals.append((dx_id, f, fp, img, ph))
            except:
                pass

    return originals


# ─── 步骤2: 预计算所有 cut 文件的 pHash ────────────────────────────

def precompute_cut_hashes():
    """预计算所有 02_REM_BG 中的 cut 文件在不同背景色下的 pHash"""
    cut_entries = []  # [(dx_id, filename, fullpath)]

    base = BASE
    for d in sorted(os.listdir(base)):
        dx_match = re.match(r'DX(\d{4})', d)
        if not dx_match:
            continue
        rem_dir = os.path.join(base, d, "02_REM_BG")
        if not os.path.isdir(rem_dir):
            continue

        for f in sorted(os.listdir(rem_dir)):
            if f.lower().endswith(".png") and "_cut" in f:
                fp = os.path.join(rem_dir, f)
                cut_entries.append((int(dx_match.group(1)), f, fp))

    print(f"  找到 {len(cut_entries)} 个 cut 文件")

    # 对每个 cut 文件，用多种背景色计算 pHash
    # 缓存结果避免重复计算
    cut_hashes = []  # [(dx_id, filename, fullpath, ph_white, ph_black, ph_gray)]

    bg_presets = {
        "white": [255, 255, 255],
        "black": [0, 0, 0],
        "gray": [128, 128, 128],
    }

    for idx, (dx_id, fname, fp) in enumerate(cut_entries):
        if (idx + 1) % 100 == 0:
            print(f"    预计算进度: {idx+1}/{len(cut_entries)}")

        try:
            cut_pil = Image.open(fp)
            # 缩小到 256x256 加速（pHash 内部会缩到 32x32）
            small = cut_pil.resize((256, 256), Image.LANCZOS)

            hashes = {}
            for name, bg in bg_presets.items():
                comp = composite_rgba_on_bg(small, bg, (256, 256))
                comp_pil = Image.fromarray(comp)
                hashes[name] = imagehash.phash(comp_pil)

            cut_hashes.append((dx_id, fname, fp, hashes))
        except Exception as e:
            print(f"     ⚠ 无法处理 {fname}: {e}")

    return cut_hashes


# ─── 步骤3: 对每张原图，找最佳匹配 cut ────────────────────────────

def find_best_match(orig_ph, cut_hashes):
    """对一张原图的 pHash，在所有 cut 中找最佳匹配"""
    best_hamming = 999
    best_match = None

    for dx_id, fname, fp, hashes in cut_hashes:
        for bg_name, cut_ph in hashes.items():
            hamming = orig_ph - cut_ph
            if hamming < best_hamming:
                best_hamming = hamming
                best_match = (dx_id, fname, fp, bg_name, hamming)

    return best_match


# ─── 主程序 ─────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("🔎 按图索骥：用 01_AI 原图搜索所有 02_REM_BG")
    print(f"   搜索范围: DX{START_ID:04d}-DX{END_ID:04d} 共 264 个 02_REM_BG 文件夹")
    print(f"   开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    # 步骤1: 收集原图
    print("\n📦 步骤1/3: 收集 01_AI 原图...")
    originals = collect_originals()
    print(f"  找到 {len(originals)} 张 1024x1024 原图")

    # 步骤2: 预计算 cut 的 pHash
    print("\n⚡ 步骤2/3: 预计算所有 cut 文件的 pHash...")
    cut_hashes = precompute_cut_hashes()
    print(f"  完成: {len(cut_hashes)} 个 cut 文件已预计算")

    # 步骤3: 逐一匹配
    print(f"\n🔍 步骤3/3: 逐张匹配...")
    print(f"\n{'='*70}")
    print(f"📋 匹配结果")
    print(f"{'='*70}")

    results = defaultdict(list)  # dx_id -> [(orig_fname, match_info)]

    for dx_id, fname, fp, img, ph in originals:
        match = find_best_match(ph, cut_hashes)

        if match:
            m_dx, m_fname, m_fp, bg_name, hamming = match

            # 提取后缀类型
            orig_suffix = fname.replace(f"DX{dx_id:04d}_", "").replace(".png", "")
            cut_suffix = m_fname.replace(f"DX{m_dx:04d}_", "").replace("_cut.png", "")

            # 是否在同一文件夹
            same_folder = (dx_id == m_dx)

            # 预期配对判断
            expected_pair = False
            if same_folder:
                if orig_suffix == "W" and cut_suffix == "W":
                    expected_pair = True
                elif orig_suffix == "BW" and cut_suffix == "BW":
                    expected_pair = True
                elif orig_suffix == "B" and cut_suffix == "BW":
                    expected_pair = True

            status = "✅" if expected_pair else ("❌" if not same_folder else "⚠")
            note = ""
            if not same_folder:
                note = f"  ← 在 DX{m_dx:04d} 找到！"
            elif not expected_pair:
                note = f"  命名不匹配"

            results[dx_id].append({
                "orig_fname": fname,
                "match_fname": m_fname,
                "match_folder": m_dx,
                "hamming": hamming,
                "same_folder": same_folder,
                "expected_pair": expected_pair,
                "status": status,
                "note": note,
            })

    # ─── 输出报告 ───
    # 按 dx_id 分组输出
    for dx_id in sorted(results.keys()):
        entries = results[dx_id]
        folder_name = f"DX{dx_id:04d}"

        for e in entries:
            flag = e["status"]
            match_folder_str = f"DX{e['match_folder']:04d}"
            h = e["hamming"]
            note = e["note"]

            if flag == "❌":
                print(f"  {flag} {folder_name}/{e['orig_fname']} → {match_folder_str}/{e['match_fname']} (汉明距离={h}){note}")
            elif flag == "⚠":
                print(f"  {flag} {folder_name}/{e['orig_fname']} → DX{e['match_folder']:04d}/{e['match_fname']} (汉明距离={h}){note}")
            elif flag == "✅":
                pass  # 正常匹配不显示

    # ─── 汇总 ───
    total_originals = len(originals)
    matched_in_own = sum(1 for e_list in results.values() for e in e_list if e["same_folder"])
    matched_elsewhere = sum(1 for e_list in results.values() for e in e_list if not e["same_folder"])
    naming_mismatch = sum(1 for e_list in results.values() for e in e_list if e["same_folder"] and not e["expected_pair"])

    print(f"\n{'=' * 70}")
    print("📊 统计汇总")
    print(f"{'=' * 70}")
    print(f"   参与匹配的原图总数: {total_originals}")
    print(f"   在同文件夹找到匹配: {matched_in_own}")
    print(f"   ❌ 在别处找到匹配: {matched_elsewhere}")
    print(f"   ⚠ 同文件夹但命名不对应: {naming_mismatch}")

    # 列出所有"在别处找到"的
    if matched_elsewhere > 0:
        print(f"\n{'─' * 70}")
        print("❌ 原图在别处找到了它的去背景图（放错文件夹）:")
        print(f"{'─' * 70}")
        for dx_id in sorted(results.keys()):
            for e in results[dx_id]:
                if not e["same_folder"]:
                    print(f"   {e['orig_fname']} (DX{dx_id:04d})")
                    print(f"     → 实际在: DX{e['match_folder']:04d}/{e['match_fname']}")
                    print(f"     汉明距离: {e['hamming']}")
                    print()

    # 列出"根本找不到匹配"的
    found_set = set()
    for dx_id, entries in results.items():
        for e in entries:
            found_set.add((dx_id, e["orig_fname"]))

    not_found = [(dx_id, fname, fp) for dx_id, fname, fp, _, _ in originals
                 if (dx_id, fname) not in found_set]

    if not_found:
        print(f"\n{'─' * 70}")
        print(f"❓ 在所有 02_REM_BG 中都找不到匹配的 ({len(not_found)}张):")
        print(f"{'─' * 70}")
        for dx_id, fname, fp in not_found:
            print(f"   DX{dx_id:04d}/{fname}")

    print(f"\n✅ 分析完成")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
