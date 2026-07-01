"""
生成完整的修复计划：搬家 + 改名
基于 find_cut_by_similarity.py 的分析结果
"""

import numpy as np
from PIL import Image
import imagehash
import os
import re
from datetime import datetime
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
START_ID, END_ID = 166, 286
HASH_MATCH = 15  # 汉明距离 ≤ 15 视为可靠匹配

# ─── 工具函数（同前） ─────────────────────────────────────────────────

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

# ─── 收集数据 ────────────────────────────────────────────────────────

def collect_all():
    """收集所有原图和 cut 文件的数据"""
    originals = []  # [(dx_id, fname, fullpath, pil, phash)]
    cut_files = []  # [(dx_id, fname, fullpath, pil)]

    for dx_id in range(1, 287):  # 全量扫描
        ai_dir = os.path.join(BASE, f"DX{dx_id:04d}", "01_AI")
        rem_dir = os.path.join(BASE, f"DX{dx_id:04d}", "02_REM_BG")

        # 原图
        if os.path.isdir(ai_dir):
            for f in sorted(os.listdir(ai_dir)):
                if not (f.lower().endswith(".png") and re.match(rf'DX{dx_id:04d}_[A-Za-z]+\.png', f)):
                    continue
                fp = os.path.join(ai_dir, f)
                try:
                    img = Image.open(fp)
                    if img.size == (1024, 1024) and img.mode == "RGB":
                        ph = imagehash.phash(img)
                        originals.append((dx_id, f, fp, img, ph))
                except:
                    pass

        # cut 文件
        if os.path.isdir(rem_dir):
            for f in sorted(os.listdir(rem_dir)):
                if not (f.lower().endswith(".png") and "_cut" in f):
                    continue
                fp = os.path.join(rem_dir, f)
                try:
                    cut_files.append((dx_id, f, fp, Image.open(fp)))
                except:
                    pass

    return originals, cut_files


def precompute_cut_hashes(cut_files):
    """预计算 cut 文件合成到白/黑/灰背景后的 pHash"""
    cut_hashes = []
    for idx, (dx_id, fname, fp, cut_pil) in enumerate(cut_files):
        small = cut_pil.resize((256, 256), Image.LANCZOS)
        hashes = {}
        for bg_name, bg in [("white", [255,255,255]), ("gray", [128,128,128])]:
            comp = composite_rgba_on_bg(small, bg, (256, 256))
            hashes[bg_name] = imagehash.phash(Image.fromarray(comp))
        cut_hashes.append((dx_id, fname, fp, hashes, cut_pil))
    return cut_hashes


def find_best_match(orig_ph, cut_hashes):
    """找最佳匹配"""
    best = (999, None)
    for dx_id, fname, fp, hashes, cut_pil in cut_hashes:
        for bg_name, cut_ph in hashes.items():
            h = orig_ph - cut_ph
            if h < best[0]:
                best = (h, (dx_id, fname, fp, bg_name, cut_pil))
    return best


def get_suffix(filename):
    """从文件名提取后缀: DX0166_BW.png → BW, DX0166_BW_cut.png → BW"""
    base = filename.replace(".png", "")
    if "_cut" in base:
        base = base.replace("_cut", "")
    parts = base.split("_", 1)
    return parts[-1] if len(parts) > 1 else ""


def suggest_target_name(orig_fname, orig_dx):
    """基于原图文件名建议正确的 cut 文件名"""
    suffix = get_suffix(orig_fname)
    return f"DX{orig_dx:04d}_{suffix}_cut.png"


# ─── 主程序 ─────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("📋 生成修复计划：搬家 + 改名")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. 收集数据
    print("\n📦 收集数据...")
    originals, cut_files = collect_all()
    print(f"   原图: {len(originals)} 张")
    print(f"   Cut文件: {len(cut_files)} 个")

    # 2. 预计算 cut hashes
    print("⚡ 预计算 hashes...")
    cut_hashes = precompute_cut_hashes(cut_files)

    # 3. 逐一匹配（只处理 DX0166-DX0286 的原图）
    fix_items = []  # [(type, orig_dx, orig_fname, cur_dx, cur_fname, action_desc)]

    for orig_dx, orig_fname, orig_fp, orig_img, orig_ph in originals:
        if orig_dx < START_ID or orig_dx > END_ID:
            continue

        best = find_best_match(orig_ph, cut_hashes)
        hamming = best[0]

        if hamming > HASH_MATCH:
            # 没找到可靠匹配
            fix_items.append(("missing", orig_dx, orig_fname, None, None,
                            f"❓ 未找到任何 cut 文件匹配"))
            continue

        m_dx, m_fname, m_fp, bg_name, m_cut_pil = best[1]
        same_folder = (orig_dx == m_dx)
        orig_suffix = get_suffix(orig_fname)
        cut_suffix = get_suffix(m_fname)

        # 期望的 cut 文件名
        expected_name = suggest_target_name(orig_fname, orig_dx)
        expected_folder = os.path.join(BASE, f"DX{orig_dx:04d}", "02_REM_BG")

        if same_folder and m_fname == expected_name:
            # ✅ 完全正确，不记录
            continue

        if same_folder and m_fname != expected_name:
            # ⚠ 同文件夹但名字不对
            fix_items.append(("rename", orig_dx, orig_fname, orig_dx, m_fname,
                            f"改名: {m_fname} → {expected_name}"))
            continue

        if not same_folder:
            # ❌ 放错了文件夹
            action = f"搬家: DX{m_dx:04d}\\02_REM_BG\\{m_fname}"
            action += f" → DX{orig_dx:04d}\\02_REM_BG\\{expected_name}"
            fix_items.append(("move", orig_dx, orig_fname, m_dx, m_fname, action))
            continue

    # 4. 按类别输出报告
    print("\n" + "=" * 70)
    print("📋 修复计划")
    print("=" * 70)

    moves = [x for x in fix_items if x[0] == "move"]
    renames = [x for x in fix_items if x[0] == "rename"]
    missing = [x for x in fix_items if x[0] == "missing"]

    # ── A. 需要搬家的 ──
    if moves:
        print(f"\n{'─' * 70}")
        print(f"🔄 A. 需要搬家的文件 ({len(moves)} 个)")
        print(f"{'─' * 70}")
        print(f"  这些文件的去背景图被放在了错误的项目文件夹中：")
        print()

        # 按原项目分组
        by_orig = defaultdict(list)
        for item in moves:
            by_orig[item[1]].append(item)

        for dx_id in sorted(by_orig.keys()):
            items = by_orig[dx_id]
            print(f"\n  📁 DX{dx_id:04d}:")
            for item in items:
                print(f"     {item[5]}")

    # ── B. 需要改名的 ──
    if renames:
        print(f"\n{'─' * 70}")
        print(f"✏️  B. 同文件夹但需要改名的 ({len(renames)} 个)")
        print(f"{'─' * 70}")
        print()

        by_orig = defaultdict(list)
        for item in renames:
            by_orig[item[1]].append(item)

        for dx_id in sorted(by_orig.keys()):
            items = by_orig[dx_id]
            print(f"  📁 DX{dx_id:04d}:")
            for item in items:
                print(f"     {item[5]}")

    # ── C. 缺失的 ──
    if missing:
        print(f"\n{'─' * 70}")
        print(f"❓ C. 原图存在、但所有 02_REM_BG 都找不到匹配的 ({len(missing)} 个)")
        print(f"{'─' * 70}")
        print(f"  这些原图可能还没有被去背景处理：")
        for item in missing:
            print(f"  📁 DX{item[1]:04d}/{item[2]} — 需要重新去背景")

    # ── D. 已知异常的补录 ──
    # 对于之前发现的"没有01_AI但有02_REM_BG"的项目
    print(f"\n{'─' * 70}")
    print(f"📌 D. 其他已知问题")
    print(f"{'─' * 70}")

    orphan_folders = []
    for dx_id in range(START_ID, END_ID + 1):
        rem_dir = os.path.join(BASE, f"DX{dx_id:04d}", "02_REM_BG")
        ai_dir = os.path.join(BASE, f"DX{dx_id:04d}", "01_AI")
        if os.path.isdir(rem_dir) and not os.path.isdir(ai_dir):
            orphan_folders.append(dx_id)

    if orphan_folders:
        print(f"\n  以下项目有 02_REM_BG 但缺少 01_AI 文件夹：")
        for dx_id in orphan_folders:
            rem_dir = os.path.join(BASE, f"DX{dx_id:04d}", "02_REM_BG")
            files = [f for f in os.listdir(rem_dir) if "_cut" in f]
            print(f"  📁 DX{dx_id:04d}: {', '.join(files)}")
        print(f"\n  建议: 检查这些文件是否误放，或者补充 01_AI 原图")

    # ── 总统计 ──
    print(f"\n{'=' * 70}")
    print("📊 修复统计")
    print(f"{'=' * 70}")
    print(f"  需要搬家:    {len(moves)} 个")
    print(f"  需要改名:    {len(renames)} 个")
    print(f"  缺少cut图:   {len(missing)} 个（需要重新去背景）")
    print(f"  孤文件夹:    {len(orphan_folders)} 个")
    print(f"\n  总计修正项:  {len(moves) + len(renames) + len(missing)}")

    # 生成 bat 脚本
    if moves or renames:
        print(f"\n{'=' * 70}")
        print("💾 生成修复脚本: fix_cuts.bat")
        print(f"{'=' * 70}")

        bat_path = os.path.join(BASE, "fix_cuts.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("chcp 65001 >nul\n")
            f.write(f"echo 修复计划 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("echo ========================================\n\n")

            # 搬家
            f.write("echo === 搬家操作 ===\n")
            for item in moves:
                src_dx, dst_dx = item[3], item[1]
                src_fname = item[4]
                dst_fname = suggest_target_name(item[2], dst_dx)
                src = f"\"{BASE}\\DX{src_dx:04d}\\02_REM_BG\\{src_fname}\""
                dst_dir = f"\"{BASE}\\DX{dst_dx:04d}\\02_REM_BG\""
                dst = f"{dst_dir}\\{dst_fname}"

                # 创建目标目录
                f.write(f"if not exist {dst_dir} mkdir {dst_dir}\n")
                f.write(f"move {src} {dst}\n")
                f.write(f"echo   已搬家: DX{src_dx:04d}\\{src_fname} → DX{dst_dx:04d}\\{dst_fname}\n\n")

            # 改名
            f.write("\necho === 改名操作 ===\n")
            for item in renames:
                dx_id = item[1]
                old_name = item[4]
                new_name = suggest_target_name(item[2], dx_id)
                path = f"\"{BASE}\\DX{dx_id:04d}\\02_REM_BG\\{old_name}\""
                new_path = f"\"{BASE}\\DX{dx_id:04d}\\02_REM_BG\\{new_name}\""
                f.write(f"rename {path} {new_name}\n")
                f.write(f"echo   已改名: DX{dx_id:04d}\\{old_name} → {new_name}\n\n")

            f.write("\necho ========================================\n")
            f.write("echo 修复完成！\n")
            f.write("pause\n")

        print(f"  已生成: {bat_path}")

    print(f"\n✅ 修复计划生成完毕")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
