"""
用 pHash 汉明距离检查：02_REM_BG 的 cut 文件和对应的 01_AI 原图是否匹配
全覆盖 DX0166-DX0286 当前状态
"""

import numpy as np
from PIL import Image
import imagehash
import os
import re
from datetime import datetime

BASE = r"D:\Semems WB\02_PROJECTS"
START, END = 166, 286
THRESHOLD = 12  # 汉明距离 > 12 视为不匹配

STD_BGS = {"white":[255,255,255],"lgray":[224,224,224],"gray":[128,128,128],"dgray":[64,64,64],"black":[0,0,0]}

def estimate_bg(img_np, margin=15):
    h,w=img_np.shape[:2]
    e=np.vstack([img_np[:margin,:,:].reshape(-1,3),img_np[-margin:,:,:].reshape(-1,3),img_np[:,:margin,:].reshape(-1,3),img_np[:,-margin:,:].reshape(-1,3)])
    return np.median(e,axis=0)

def composite_rgba(cut_pil,bg,ts=(256,256)):
    if cut_pil.mode!="RGBA": cut_pil=cut_pil.convert("RGBA")
    if ts: cut_pil=cut_pil.resize(ts,Image.LANCZOS)
    c=np.array(cut_pil).astype(np.float32)
    a=c[:,:,3:4]/255.0
    b=np.array(bg,dtype=np.float32).reshape(1,1,3)
    return np.clip(a*c[:,:,:3]+(1-a)*b,0,255).astype(np.uint8)

# ─── 扫描 ───
print(f"🔍 检查 DX{START:04d}-DX{END:04d} 02_REM_BG vs 01_AI...\n")

mismatch_list = []   # cut不匹配本文件夹原图
missing_cut = []     # 原图没有对应的cut
total_ok = 0
total_check = 0

for dx_id in range(START, END+1):
    rem_dir = os.path.join(BASE, f"DX{dx_id:04d}", "02_REM_BG")
    ai_dir = os.path.join(BASE, f"DX{dx_id:04d}", "01_AI")

    if not os.path.isdir(ai_dir):
        continue

    # 收集本项目的原图 (1024x1024)
    ai_map = {}  # suffix -> (pil, phash, bg_color)
    for f in os.listdir(ai_dir):
        if not re.match(rf'DX{dx_id:04d}_.+\.png', f): continue
        fp = os.path.join(ai_dir, f)
        try:
            img = Image.open(fp)
            if img.size != (1024, 1024): continue
            ph = imagehash.phash(img)
            bg = estimate_bg(np.array(img))
            suffix = f.replace(f"DX{dx_id:04d}_", "").replace(".png", "")
            ai_map[suffix] = (img, ph, bg)
        except:
            pass

    if not ai_map:
        continue

    # 处理本项目的 cut 文件
    if os.path.isdir(rem_dir):
        for f in os.listdir(rem_dir):
            if not ('_cut' in f and f.endswith('.png') and '_old' not in f):
                continue

            # 从 cut 文件名推断对应的原图后缀
            # DX{N}_BW_cut.png → BW
            # DX{N}_B_cut.png → B
            # DX{N}_W_cut.png → W
            cut_suffix = f.replace(f"DX{dx_id:04d}_", "").replace("_cut.png", "")
            
            # 查找对应原图
            orig = None
            orig_fname = None
            for suf, (img, ph, bg) in ai_map.items():
                if suf == cut_suffix:
                    orig = (img, ph, bg)
                    orig_fname = f"DX{dx_id:04d}_{suf}.png"
                    break

            if orig is None:
                # 没找到同名的原图，跳过（如 WB_cut 对应 WB 原图）
                continue

            # 加载 cut 图
            fp = os.path.join(rem_dir, f)
            try:
                cut_pil = Image.open(fp)
            except:
                continue

            # 合成到原图背景色上，比较 pHash
            comp = composite_rgba(cut_pil, orig[2], (256, 256))
            cut_ph = imagehash.phash(Image.fromarray(comp))
            hamming = orig[1] - cut_ph

            total_check += 1

            if hamming > THRESHOLD:
                mismatch_list.append((dx_id, f, orig_fname, hamming))
            else:
                total_ok += 1

    # 检查哪些原图没有对应的 cut 文件
    if os.path.isdir(rem_dir):
        cut_suffixes = set()
        for f in os.listdir(rem_dir):
            if '_cut' in f and f.endswith('.png') and '_old' not in f:
                s = f.replace(f"DX{dx_id:04d}_", "").replace("_cut.png", "")
                cut_suffixes.add(s)

        for suf, (img, ph, bg) in ai_map.items():
            if suf not in cut_suffixes:
                missing_cut.append((dx_id, f"DX{dx_id:04d}_{suf}.png"))
    else:
        # 没有 REM_BG 文件夹
        for suf, (img, ph, bg) in ai_map.items():
            missing_cut.append((dx_id, f"DX{dx_id:04d}_{suf}.png"))

# ─── 输出 ───
print("="*60)
print("📋 分析结果")
print("="*60)

print(f"\n✅ 正常匹配: {total_ok}/{total_check}")
print()

if mismatch_list:
    print(f"❌ 不匹配的 cut 文件 ({len(mismatch_list)} 个):")
    print(f"   {'项目':>8} {'cut文件':>30} {'对应原图':>25} {'汉明距离':>8}")
    print("   " + "-"*75)
    for dx, cf, of, h in sorted(mismatch_list):
        print(f"   DX{dx:04d}  {cf:>30}  {of:>25}  {h:>4}")
    print()

if missing_cut:
    print(f"🏗  缺 cut 文件的原图 ({len(missing_cut)} 张):")
    for dx, fname in sorted(missing_cut):
        print(f"   DX{dx:04d}\\01_AI\\{fname}")
    print()

print("="*60)
print(f"检查范围: DX{START:04d}-DX{END:04d}")
print(f"总检查: {total_check} 对")
print(f"不匹配: {len(mismatch_list)}")
print(f"缺cut:  {len(missing_cut)}")
print(f"✅ 完成")
