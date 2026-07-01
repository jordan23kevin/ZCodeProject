"""
全面终检：DX0166-0286
1. 缺去背图的原图
2. 放错文件夹的去背图
"""

import numpy as np
from PIL import Image
import imagehash, os, re
from collections import defaultdict

BASE=r'D:\Semems WB\02_PROJECTS'
START,END=166,286
HASH_OK=12

STD_BGS={'white':[255,255,255],'lgray':[224,224,224],'gray':[128,128,128],'dgray':[64,64,64],'black':[0,0,0]}

def estimate_bg(img_np,m=15):
    h,w=img_np.shape[:2]
    e=np.vstack([img_np[:m,:,:].reshape(-1,3),img_np[-m:,:,:].reshape(-1,3),img_np[:,:m,:].reshape(-1,3),img_np[:,-m:,:].reshape(-1,3)])
    return np.median(e,axis=0)

def composite_rgba(cut_pil,bg,ts=(256,256)):
    if cut_pil.mode!='RGBA': cut_pil=cut_pil.convert('RGBA')
    if ts: cut_pil=cut_pil.resize(ts,Image.LANCZOS)
    c=np.array(cut_pil).astype(np.float32)
    a=c[:,:,3:4]/255.0
    b=np.array(bg,dtype=np.float32).reshape(1,1,3)
    return np.clip(a*c[:,:,:3]+(1-a)*b,0,255).astype(np.uint8)

# ─── 1. 收集数据 ───
print("📦 收集数据...")

# 原图索引
orig_map=defaultdict(dict)  # dx -> {suffix: (pil, ph, bg, cb)}
for d in range(START,END+1):
    ai=os.path.join(BASE,f'DX{d:04d}','01_AI')
    if not os.path.isdir(ai): continue
    for f in os.listdir(ai):
        if not re.match(rf'DX{d:04d}_.+\.png',f): continue
        fp=os.path.join(ai,f)
        try:
            img=Image.open(fp)
            if img.size!=(1024,1024): continue
            ph=imagehash.phash(img)
            bg=estimate_bg(np.array(img))
            cb=min(STD_BGS,key=lambda n:sum((bg[i]-STD_BGS[n][i])**2 for i in range(3)))
            suf=f.replace(f'DX{d:04d}_','').replace('.png','')
            orig_map[d][suf]=(img,ph,bg,cb)
        except: pass

# Cut 索引
cut_hashes={}  # (dx, fname) -> {bg_name: phash}
cut_files=[]   # [(dx, fname, fp)]
for d in os.listdir(BASE):
    m=re.match(r'DX(\d{4})',d)
    if not m: continue
    dx=int(m.group(1))
    rem=os.path.join(BASE,d,'02_REM_BG')
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
            cut_hashes[(dx,f)]=hh
            cut_files.append((dx,f,fp,cut))
        except: pass

print(f"   原图: {sum(len(v) for v in orig_map.values())} 张")
print(f"   Cut:  {len(cut_files)} 个")

# ─── 2. 查缺去背图 ───
print(f"\n🔍 1. 缺去背图的原图...")
missing_cuts=[]
for dx in range(START,END+1):
    if dx not in orig_map: continue
    for suf,(img,ph,bg,cb) in orig_map[dx].items():
        # 先检查同文件夹同名匹配
        expected=f'DX{dx:04d}_{suf}_cut.png'
        rem_dir=os.path.join(BASE,f'DX{dx:04d}','02_REM_BG')
        found=False
        if os.path.isdir(rem_dir):
            efp=os.path.join(rem_dir,expected)
            if os.path.exists(efp):
                try:
                    cut=Image.open(efp)
                    comp=composite_rgba(cut,STD_BGS[cb],(256,256))
                    h=ph-imagehash.phash(Image.fromarray(comp))
                    if h<=HASH_OK:
                        found=True
                except: pass
        if not found:
            # 全库搜索
            best=(999,None,None)
            for (cdx,cfn),ch in cut_hashes.items():
                h=ph-ch[cb]
                if h<best[0]:
                    best=(h,cdx,cfn)
            h,cdx,cfn=best
            if h<=HASH_OK:
                found=True
        if not found:
            missing_cuts.append((dx,f'DX{dx:04d}_{suf}.png'))

print(f"   缺去背图: {len(missing_cuts)} 张")
for dx,fn in missing_cuts:
    print(f"     DX{dx:04d}\\01_AI\\{fn}")

# ─── 3. 查放错位置的 cut ───
print(f"\n🔍 2. 放错文件夹的 cut 文件...")
misplaced=[]
for dx in range(START,END+1):
    rem_dir=os.path.join(BASE,f'DX{dx:04d}','02_REM_BG')
    if not os.path.isdir(rem_dir): continue
    for f in os.listdir(rem_dir):
        if not ('_cut' in f and f.endswith('.png') and '_old' not in f): continue
        if dx not in orig_map: continue  # 无原图可对比
        
        suf=f.replace(f'DX{dx:04d}_','').replace('_cut.png','')
        if suf in orig_map[dx]:
            # 同名匹配，验证内容
            img,ph,bg,cb=orig_map[dx][suf]
            ch=cut_hashes.get((dx,f))
            if ch is None: continue
            h=ph-ch[cb]
            if h>HASH_OK:
                # 内容不对应
                misplaced.append((dx,f,f"内容不匹配(汉明={h})"))
        else:
            # 无同名原图
            # 查它到底匹配谁
            ch=cut_hashes.get((dx,f))
            if ch is None: continue
            best=(999,None,None)
            for d2 in orig_map:
                for suf2,(img2,ph2,bg2,cb2) in orig_map[d2].items():
                    h=ph2-ch[cb2]
                    if h<best[0]:
                        best=(h,d2,f'DX{d2:04d}_{suf2}.png')
            h,bdx,bfn=best
            if h<=HASH_OK:
                misplaced.append((dx,f,f"应属于 DX{bdx:04d}\\{bfn} (汉明={h})"))
            else:
                misplaced.append((dx,f,f"无匹配原图(最佳汉明={h})"))

print(f"   放错位置: {len(misplaced)} 个")
for dx,fn,reason in misplaced:
    print(f"     DX{dx:04d}\\02_REM_BG\\{fn}")
    print(f"       → {reason}")

# ─── 4. 汇总 ───
print(f"\n{'='*60}")
print("📊 最终汇总")
print('='*60)
print(f"   缺去背图的原图: {len(missing_cuts)}")
print(f"   放错位置的cut:  {len(misplaced)}")
if not missing_cuts and not misplaced:
    print(f"\n   ✅ 全部正确，无需处理！")
else:
    print(f"\n   需要修复: {len(missing_cuts)+len(misplaced)} 项")
print(f"\n✅ 分析完成")
