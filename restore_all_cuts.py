"""
全量恢复去背图：对每个 01_AI 原图，在所有 02_REM_BG + 备份中搜索匹配
找到后按 DX文件夹款号命名复制到对应的 02_REM_BG
"""

import numpy as np
from PIL import Image
import imagehash, os, re, shutil
from datetime import datetime

BASE = r"D:\Semems WB\02_PROJECTS"
BACKUP = os.path.join(BASE, "备份")
HASH_OK = 12

STD_BGS = {"white":[255,255,255],"lgray":[224,224,224],"gray":[128,128,128],"dgray":[64,64,64],"black":[0,0,0]}

def estimate_bg(img_np,m=15):
    h,w=img_np.shape[:2]
    e=np.vstack([img_np[:m,:,:].reshape(-1,3),img_np[-m:,:,:].reshape(-1,3),img_np[:,:m,:].reshape(-1,3),img_np[:,-m:,:].reshape(-1,3)])
    return np.median(e,axis=0)

def composite_rgba(cut_pil,bg,ts=(256,256)):
    if cut_pil.mode!="RGBA": cut_pil=cut_pil.convert("RGBA")
    if ts: cut_pil=cut_pil.resize(ts,Image.LANCZOS)
    c=np.array(cut_pil).astype(np.float32)
    a=c[:,:,3:4]/255.0
    b=np.array(bg,dtype=np.float32).reshape(1,1,3)
    return np.clip(a*c[:,:,:3]+(1-a)*b,0,255).astype(np.uint8)

# ─── 1. 收集所有原图 ───
print("📦 收集所有 01_AI 原图...")
origins = []  # [(dx, fname, ph, bg, cb)]
for d in os.listdir(BASE):
    m=re.match(r'DX(\d{4})',d)
    if not m: continue
    dx=int(m.group(1))
    ai=os.path.join(BASE,d,"01_AI")
    if not os.path.isdir(ai): continue
    for f in os.listdir(ai):
        if not re.match(rf'DX{dx:04d}_.+\.png',f): continue
        fp=os.path.join(ai,f)
        try:
            img=Image.open(fp)
            if img.size!=(1024,1024): continue
            ph=imagehash.phash(img)
            bg=estimate_bg(np.array(img))
            cb=min(STD_BGS,key=lambda n:sum((bg[i]-STD_BGS[n][i])**2 for i in range(3)))
            origins.append((dx,f,ph,bg,cb))
        except: pass
print(f"   共 {len(origins)} 张原图")

# ─── 2. 预计算所有 cut 的 pHash（现有文件夹 + 备份） ───
print("⚡ 预计算所有 cut 的 pHash...")
cut_db = []  # [(source_label, fname, fp, {bg: phash})]

# 现有 02_REM_BG
for d in os.listdir(BASE):
    m=re.match(r'DX(\d{4})',d)
    if not m: continue
    rem=os.path.join(BASE,d,"02_REM_BG")
    if not os.path.isdir(rem): continue
    for f in os.listdir(rem):
        if not ('_cut' in f and f.endswith('.png') and '_old' not in f): continue
        fp=os.path.join(rem,f)
        try:
            cut=Image.open(fp)
            small=cut.resize((256,256),Image.LANCZOS)
            hh={}
            for bn,bg in STD_BGS.items():
                comp=composite_rgba(small,bg,(256,256))
                hh[bn]=imagehash.phash(Image.fromarray(comp))
            cut_db.append((f"REM_BG",f,fp,hh))
        except: pass

# 备份文件夹
for root,_,files in os.walk(BACKUP):
    for f in files:
        if '_cut' in f and f.endswith('.png'):
            fp=os.path.join(root,f)
            try:
                cut=Image.open(fp)
                small=cut.resize((256,256),Image.LANCZOS)
                hh={}
                for bn,bg in STD_BGS.items():
                    comp=composite_rgba(small,bg,(256,256))
                    hh[bn]=imagehash.phash(Image.fromarray(comp))
                cut_db.append((f"备份",f,fp,hh))
            except: pass

print(f"   共 {len(cut_db)} 个 cut 文件（含备份）")

# ─── 3. 逐张原图搜索匹配 ───
print(f"\n🔍 搜索并恢复...\n")

restored = 0
already_have = 0
not_found = []

for dx,fname,ph,bg,cb in sorted(origins):
    suffix=fname.replace(f'DX{dx:04d}_','').replace('.png','')
    expected=f'DX{dx:04d}_{suffix}_cut.png'
    dst_dir=os.path.join(BASE,f'DX{dx:04d}','02_REM_BG')
    dst=os.path.join(dst_dir,expected)
    
    # 检查是否已有且匹配
    if os.path.exists(dst):
        try:
            cut=Image.open(dst)
            comp=composite_rgba(cut,STD_BGS[cb],(256,256))
            h=ph-imagehash.phash(Image.fromarray(comp))
            if h<=HASH_OK:
                already_have+=1
                continue
        except: pass
    
    # 全库搜索
    best=(999,None,None,None)
    for src_label,fp_label,fp,ch in cut_db:
        h=ph-ch[cb]
        if h<best[0]:
            best=(h,src_label,fp_label,fp)
    
    h,src_label,fp_label,fp=best
    if h<=HASH_OK:
        # 找到匹配，复制回去
        os.makedirs(dst_dir,exist_ok=True)
        shutil.copy2(fp,dst)
        restored+=1
        print(f"   ✅ DX{dx:04d}\\{expected} ← {src_label}\\{fp_label} (汉明={h})")
    else:
        not_found.append((dx,fname,h,fp_label))
        print(f"   ❌ DX{dx:04d}\\{fname} → 无匹配 (最佳汉明={h})")

# ─── 4. 汇总 ───
print(f"\n{'='*60}")
print("📊 恢复汇总")
print('='*60)
print(f"   已有匹配: {already_have}")
print(f"   新恢复:   {restored}")
print(f"   仍未找到: {len(not_found)}")
if not_found:
    print(f"\n仍未找到去背图的原图:")
    for dx,fname,h,bf in not_found:
        print(f"   DX{dx:04d}\\{fname} (最佳汉明={h})")
print(f"\n✅ 完成")
