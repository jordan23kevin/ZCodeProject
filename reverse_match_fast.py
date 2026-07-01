"""
反向匹配 v2 (优化版): 对每个 02_REM_BG cut 文件，在所有 01_AI 中找对应的原图
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
HASH_THRESHOLD = 15

# 标准背景色板 - RGB
STD_BGS = {
    "white":    [255, 255, 255],
    "lgray":    [224, 224, 224],
    "gray":     [128, 128, 128],
    "dgray":    [64, 64, 64],
    "black":    [0, 0, 0],
}

def estimate_bg_color(img_np, margin=15):
    h, w = img_np.shape[:2]
    edges = np.vstack([
        img_np[:margin, :, :].reshape(-1, 3),
        img_np[-margin:, :, :].reshape(-1, 3),
        img_np[:, :margin, :].reshape(-1, 3),
        img_np[:, -margin:, :].reshape(-1, 3),
    ])
    return np.median(edges, axis=0)

def closest_std_bg(bg_color):
    """找最接近的标准背景色"""
    best = None
    best_dist = 999
    for name, std_bg in STD_BGS.items():
        dist = sum((bg_color[i] - std_bg[i])**2 for i in range(3))
        if dist < best_dist:
            best_dist = dist
            best = name
    return best

def composite_rgba_on_bg(cut_pil, bg, target_size):
    if cut_pil.mode != "RGBA":
        cut_pil = cut_pil.convert("RGBA")
    if target_size:
        cut_pil = cut_pil.resize(target_size, Image.LANCZOS)
    cut_np = np.array(cut_pil).astype(np.float32)
    alpha = cut_np[:, :, 3:4] / 255.0
    rgb = cut_np[:, :, :3]
    bg_a = np.array(bg, dtype=np.float32).reshape(1, 1, 3)
    return np.clip(alpha * rgb + (1 - alpha) * bg_a, 0, 255).astype(np.uint8)

# ─── 预计算 ────────────────────────────────────────────────────────

print("📦 预计算 01_AI 原图...")
originals = []  # [(dx_id, fname, phash, bg_color, closest_bg_name)]
for d in sorted(os.listdir(BASE)):
    m = re.match(r'DX(\d{4})', d)
    if not m: continue
    dx_id = int(m.group(1))
    ai_dir = os.path.join(BASE, d, "01_AI")
    if not os.path.isdir(ai_dir): continue
    for f in sorted(os.listdir(ai_dir)):
        if not (f.lower().endswith(".png") and re.match(rf'DX{dx_id:04d}_.+\.png', f)):
            continue
        fp = os.path.join(ai_dir, f)
        try:
            img = Image.open(fp)
            if img.size != (1024, 1024): continue
            ph = imagehash.phash(img)
            bg = estimate_bg_color(np.array(img))
            cb = closest_std_bg(bg)
            originals.append((dx_id, f, fp, ph, bg, cb, img))
        except:
            pass

print(f"   找到 {len(originals)} 张原图")

# 预计算每个标准背景色下 cut 的 pHash
print("⚡ 预计算 cut 文件 pHash (标准背景色)...")
cut_cache = {}  # (cut_fp) -> {bg_name: phash}
all_cuts = []

for d in sorted(os.listdir(BASE)):
    m = re.match(r'DX(\d{4})', d)
    if not m: continue
    dx_id = int(m.group(1))
    rem_dir = os.path.join(BASE, d, "02_REM_BG")
    if not os.path.isdir(rem_dir): continue
    for f in sorted(os.listdir(rem_dir)):
        if not (f.lower().endswith(".png") and "_cut" in f): continue
        if "_old" in f: continue  # 跳过备份文件
        fp = os.path.join(rem_dir, f)
        try:
            cut_pil = Image.open(fp)
            small = cut_pil.resize((256, 256), Image.LANCZOS)
            hashes = {}
            for bg_name, bg in STD_BGS.items():
                comp = composite_rgba_on_bg(small, bg, (256, 256))
                hashes[bg_name] = imagehash.phash(Image.fromarray(comp))
            cut_cache[fp] = hashes
            all_cuts.append((dx_id, f, fp))
        except:
            pass

print(f"   找到 {len(all_cuts)} 个 cut 文件")

# ─── 匹配 ──────────────────────────────────────────────────────────

print(f"\n🔍 开始匹配...\n{'='*70}")
print("📋 匹配结果")
print('='*70)

issues = []
correct = 0

for cut_dx, cut_fname, cut_fp in all_cuts:
    cut_hashes = cut_cache[cut_fp]
    best_h = 999
    best_orig = None
    best_bg = None

    # 用原图最接近的标准背景色的 cut hash 来比较
    for orig_dx, orig_fname, orig_fp, orig_ph, orig_bg, cb_name, orig_img in originals:
        cut_ph = cut_hashes[cb_name]
        h = orig_ph - cut_ph
        if h < best_h:
            best_h = h
            best_orig = (orig_dx, orig_fname, orig_fp, orig_ph, orig_bg, cb_name)
            best_bg = cb_name

    if best_orig is None:
        continue

    bo = best_orig
    same_folder = (cut_dx == bo[0])
    h = best_h

    # 判断命名是否匹配
    cut_suffix = cut_fname.replace(f"DX{cut_dx:04d}_", "").replace("_cut.png", "")
    orig_suffix = bo[1].replace(f"DX{bo[0]:04d}_", "").replace(".png", "")
    naming_ok = same_folder and (cut_suffix == orig_suffix)

    if same_folder and naming_ok and h <= HASH_THRESHOLD:
        correct += 1
        continue

    # 有问题的才显示
    if not same_folder and h <= HASH_THRESHOLD:
        print(f"  ❌ {cut_fname} (DX{cut_dx:04d})")
        print(f"      → 原图在: DX{bo[0]:04d}/{bo[1]} (hamming={h})")
        issues.append(("move", cut_dx, cut_fname, bo[0], bo[1], h))
    elif same_folder and not naming_ok and h <= HASH_THRESHOLD:
        print(f"  ⚠ {cut_fname} ↔ {bo[1]} (hamming={h}) — 后缀不匹配")
        issues.append(("rename", cut_dx, cut_fname, bo[0], bo[1], h))
    elif h > HASH_THRESHOLD:
        print(f"  ❓ {cut_fname} (DX{cut_dx:04d}): 无匹配原图 (最佳=DX{bo[0]:04d}/{bo[1]}, hamming={h})")
        issues.append(("orphan", cut_dx, cut_fname, bo[0], bo[1], h))

# ─── 汇总 ───
print(f"\n{'='*70}")
print("📊 汇总")
print('='*70)
print(f"   总 cut 文件: {len(all_cuts)}")
print(f"   ✅ 正确:     {correct}")
print(f"   ❌ 放错位置: {len([x for x in issues if x[0]=='move'])}")
print(f"   ⚠ 后缀不匹配: {len([x for x in issues if x[0]=='rename'])}")
print(f"   ❓ 无匹配:   {len([x for x in issues if x[0]=='orphan'])}")

moves = [x for x in issues if x[0] == "move"]
if moves:
    print(f"\n{'─'*70}")
    print("❌ 仍放错位置的 cut 文件（需要搬家）:")
    print(f"{'─'*70}")
    for item in moves:
        _, cut_dx, cut_fname, orig_dx, orig_fname, h = item
        expect_name = orig_fname.replace(".png", "_cut.png")
        print(f"   {cut_fname} (DX{cut_dx:04d})")
        print(f"     → 搬到: DX{orig_dx:04d}\\02_REM_BG\\{expect_name}")

orphans = [x for x in issues if x[0] == "orphan"]
if orphans:
    print(f"\n{'─'*70}")
    print("❓ 在所有 01_AI 中都找不到原图的 cut 文件:")
    print(f"{'─'*70}")
    for item in orphans:
        _, cut_dx, cut_fname, _, _, _ = item
        print(f"   DX{cut_dx:04d}/{cut_fname}")

print(f"\n✅ 分析完成")
