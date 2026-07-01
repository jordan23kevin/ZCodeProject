"""
全自动修复: 扫描 DX0166-0286 所有 01_AI 和 02_REM_BG
自动搬家、改名、复制，标记缺失
"""

import numpy as np
from PIL import Image
import imagehash
import os
import re
import shutil
from datetime import datetime
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
START, END = 166, 286
HASH_OK = 12

STD_BGS = {"white":[255,255,255],"lgray":[224,224,224],"gray":[128,128,128],"dgray":[64,64,64],"black":[0,0,0]}

def estimate_bg(img_np, margin=15):
    h,w=img_np.shape[:2]
    edges=np.vstack([img_np[:margin,:,:].reshape(-1,3),img_np[-margin:,:,:].reshape(-1,3),img_np[:,:margin,:].reshape(-1,3),img_np[:,-margin:,:].reshape(-1,3)])
    return np.median(edges,axis=0)

def closest_bg(bg):
    return min(STD_BGS,key=lambda n:sum((bg[i]-STD_BGS[n][i])**2 for i in range(3)))

def composite(cut_pil,bg,target=(256,256)):
    if cut_pil.mode!="RGBA": cut_pil=cut_pil.convert("RGBA")
    if target: cut_pil=cut_pil.resize(target,Image.LANCZOS)
    cut=np.array(cut_pil).astype(np.float32)
    a=cut[:,:,3:4]/255.0
    b=np.array(bg,dtype=np.float32).reshape(1,1,3)
    return np.clip(a*cut[:,:,:3]+(1-a)*b,0,255).astype(np.uint8)

# ─── 步骤1: 收集所有数据 ───
print("📦 收集数据...")

orig_by_id = defaultdict(list)  # dx_id -> [(fname, fp, phash, bg, cb_name)]
all_cuts = []  # [(cut_dx, cut_fname, cut_fp)]

for d in sorted(os.listdir(BASE)):
    m=re.match(r'DX(\d{4})',d)
    if not m: continue
    dx=int(m.group(1))

    # 原图
    ai=os.path.join(BASE,d,"01_AI")
    if os.path.isdir(ai):
        for f in os.listdir(ai):
            if not (f.lower().endswith(".png") and re.match(rf'DX{dx:04d}_.+\.png',f)): continue
            fp=os.path.join(ai,f)
            try:
                img=Image.open(fp)
                if img.size!=(1024,1024): continue
                ph=imagehash.phash(img)
                bg=estimate_bg(np.array(img))
                cb=closest_bg(bg)
                orig_by_id[dx].append((f,fp,ph,bg,cb,img))
            except: pass

    # cut
    rem=os.path.join(BASE,d,"02_REM_BG")
    if os.path.isdir(rem):
        for f in os.listdir(rem):
            if not ('_cut' in f and f.endswith('.png') and '_old' not in f): continue
            all_cuts.append((dx,f,os.path.join(rem,f)))

print(f"   原图: {sum(len(v) for v in orig_by_id.values())} 张")
print(f"   Cut:  {len(all_cuts)} 个 (全量)")

# ─── 步骤2: 预计算 cut 的 pHash ───
print("⚡ 预计算 cut pHash...")
cut_hashes = {}  # fp -> {bg_name: phash}
for _,_,fp in all_cuts:
    try:
        cut=Image.open(fp)
        small=cut.resize((256,256),Image.LANCZOS)
        hh={}
        for bn,bg in STD_BGS.items():
            comp=composite(small,bg,(256,256))
            hh[bn]=imagehash.phash(Image.fromarray(comp))
        cut_hashes[fp]=hh
    except: pass

# ─── 步骤3: 构建所有原图的查找索引 ───
all_origins = []  # [(dx, fname, fp, phash, cb_name)]
for dx, items in orig_by_id.items():
    for fname,fp,ph,bg,cb,img in items:
        all_origins.append((dx,fname,fp,ph,cb))

def best_orig_for_cut(cut_fp, cut_dx=None):
    """找 cut 的最佳原图匹配"""
    if cut_fp not in cut_hashes: return None
    ch=cut_hashes[cut_fp]
    best=(999,None)
    for dx,fname,fp,ph,cb in all_origins:
        if cut_dx is not None and dx==cut_dx:
            weight=0  # 同文件夹加分
        else:
            weight=0
        h=ph-ch[cb]
        if h+weight<best[0]:
            best=(h+weight,(dx,fname,fp,ph,cb,h))
    return best[1]

# ─── 步骤4: 逐一切割处理 ───
print(f"\n🔧 修复 DX{START:04d}-DX{END:04d}...\n{'='*60}")

moves=[]
renames=[]
copies=[]
orphans=[]
fixed_originals=set()  # 已找到匹配的原图 (dx, fname)

for cut_dx,cut_fname,cut_fp in all_cuts:
    if cut_dx<START or cut_dx>END: continue

    result=best_orig_for_cut(cut_fp)
    if result is None:
        orphans.append((cut_dx,cut_fname))
        continue

    odx,ofname,ofp,oph,ocb,oh=result
    fixed_originals.add((odx,ofname))

    # 期望的 cut 文件名
    osuffix=ofname.replace(f"DX{odx:04d}_","").replace(".png","")
    expect_name=f"DX{odx:04d}_{osuffix}_cut.png"

    same_folder=(cut_dx==odx)
    correct_name=(cut_fname==expect_name)

    if same_folder and correct_name:
        continue  # ✅ 完美

    if same_folder and not correct_name:
        # ⚠ 改名
        src=cut_fp
        dst=os.path.join(os.path.dirname(cut_fp),expect_name)
        if os.path.exists(dst):
            orphans.append((cut_dx,cut_fname))
            continue
        os.rename(src,dst)
        renames.append((cut_dx,cut_fname,expect_name))
        continue

    if not same_folder:
        # ❌ 搬走
        dst_dir=os.path.join(BASE,f"DX{odx:04d}","02_REM_BG")
        dst=os.path.join(dst_dir,expect_name)
        os.makedirs(dst_dir,exist_ok=True)
        if os.path.exists(dst):
            # 冲突：已经有一个同名文件了→复制一份
            src2=cut_fp
            copies.append((cut_dx,cut_fname,odx,expect_name))
            shutil.copy2(src2,dst)
        else:
            shutil.move(cut_fp,dst)
            moves.append((cut_dx,cut_fname,odx,expect_name))

# ─── 步骤5: 找出缺少 cut 的原图 ───
missing_origins=[]
for dx in range(START,END+1):
    if dx not in orig_by_id: continue
    for fname,fp,ph,bg,cb,img in orig_by_id[dx]:
        if (dx,fname) not in fixed_originals:
            # 再搜一次确保真没找到
            best=(999,None)
            for cfp,ch in cut_hashes.items():
                h=ph-ch[cb]
                if h<best[0]:
                    best=(h,cfp)
            if best[0]>HASH_OK:
                missing_origins.append((dx,fname,best[0]))

# ─── 输出报告 ───
print(f"\n{'='*60}")
print("📋 修复结果")
print('='*60)

if moves:
    print(f"\n✅ 搬家 ({len(moves)} 个):")
    for cd,cf,od,ef in sorted(moves):
        print(f"   DX{cd:04d}\\{cf} → DX{od:04d}\\{ef}")

if renames:
    print(f"\n✏️  改名 ({len(renames)} 个):")
    for dx,old,new in sorted(renames):
        print(f"   DX{dx:04d}\\{old} → {new}")

if copies:
    print(f"\n📋 复制 ({len(copies)} 个，因冲突无法搬家):")
    for cd,cf,od,ef in sorted(copies):
        print(f"   DX{cd:04d}\\{cf} → 复制到 DX{od:04d}\\{ef}")

if orphans:
    print(f"\n❓ 孤儿科特 (无匹配原图，{len(orphans)} 个):")
    for dx,fn in sorted(orphans):
        print(f"   DX{dx:04d}\\{fn}")

if missing_origins:
    print(f"\n🏗  缺去背景图的原图 ({len(missing_origins)} 张):")
    for dx,fn,bh in sorted(missing_origins):
        print(f"   DX{dx:04d}\\{fn}  (最佳汉明距离={bh})")

print(f"\n{'='*60}")
print("📊 统计")
print(f"{'='*60}")
print(f"   搬家:    {len(moves)}")
print(f"   改名:    {len(renames)}")
print(f"   复制:    {len(copies)}")
print(f"   孤儿科特: {len(orphans)}")
print(f"   缺原图去背: {len(missing_origins)}")
print(f"\n✅ 完成")
