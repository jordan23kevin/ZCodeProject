"""
分析 03_UPLOAD vs 01_AI: 用图片相似度找出不匹配和缺失
"""

import numpy as np
from PIL import Image
import imagehash
import cv2
import os
import re
from datetime import datetime
from collections import defaultdict

BASE = r"D:\Semems WB\02_PROJECTS"
START, END = 166, 286
HASH_OK = 15  # pHash 阈值
ORB_OK = 0.15  # ORB 匹配率阈值 (BW类用)
ORB_OK_TEE = 0.08  # ORB 匹配率阈值 (T恤类，会更低)

STD_BGS = {"white":[255,255,255],"lgray":[224,224,224],"gray":[128,128,128],"dgray":[64,64,64],"black":[0,0,0]}


def estimate_bg(img_np, margin=15):
    h,w=img_np.shape[:2]
    e=np.vstack([img_np[:margin,:,:].reshape(-1,3),img_np[-margin:,:,:].reshape(-1,3),img_np[:,:margin,:].reshape(-1,3),img_np[:,-margin:,:].reshape(-1,3)])
    return np.median(e,axis=0)


def composite_rgba(cut_pil, bg, ts=(256,256)):
    if cut_pil.mode!="RGBA": cut_pil=cut_pil.convert("RGBA")
    if ts: cut_pil=cut_pil.resize(ts,Image.LANCZOS)
    c=np.array(cut_pil).astype(np.float32)
    a=c[:,:,3:4]/255.0
    b=np.array(bg,dtype=np.float32).reshape(1,1,3)
    return np.clip(a*c[:,:,:3]+(1-a)*b,0,255).astype(np.uint8)


def orb_match(img1, img2):
    """ORB 特征匹配，返回匹配率和优质匹配数"""
    if img1.size==0 or img2.size==0: return 0,0
    gray1=cv2.cvtColor(img1,cv2.COLOR_RGB2GRAY)
    gray2=cv2.cvtColor(img2,cv2.COLOR_RGB2GRAY)
    orb=cv2.ORB_create(nfeatures=1500)
    kp1,des1=orb.detectAndCompute(gray1,None)
    kp2,des2=orb.detectAndCompute(gray2,None)
    if des1 is None or des2 is None or len(kp1)<5 or len(kp2)<5: return 0,0
    FLANN_INDEX_LSH=6
    index_params=dict(algorithm=FLANN_INDEX_LSH,table_number=12,key_size=20,multi_probe_level=2)
    flann=cv2.FlannBasedMatcher(index_params,dict(checks=50))
    try:
        matches=flann.knnMatch(des1,des2,k=2)
    except:
        return 0,0
    good=[]
    for m in matches:
        if len(m)==2 and m[0].distance<0.75*m[1].distance:
            good.append(m[0])
    ratio=len(good)/max(len(kp1),len(kp2),1)
    return ratio, len(good)


# ─── 收集数据 ───
print(f"📦 分析 DX{START:04d}-DX{END:04d} 03_UPLOAD vs 01_AI...\n")

upload_status = {}  # (dx, 文件名) -> {"匹配原图": (dx, 文件名), "相似度": 值, "方法": str}

# 对于每个有 03_UPLOAD 的项目
for dx_id in range(START, END+1):
    up_dir=os.path.join(BASE,f"DX{dx_id:04d}","03_UPLOAD")
    ai_dir=os.path.join(BASE,f"DX{dx_id:04d}","01_AI")
    if not os.path.isdir(up_dir) or not os.path.isdir(ai_dir):
        continue

    # 收集本项目的原图
    ai_imgs=[]  # [(fname, pil, ph, bg, cb)]
    for f in os.listdir(ai_dir):
        if not re.match(rf'DX{dx_id:04d}_.+\.png',f): continue
        fp=os.path.join(ai_dir,f)
        try:
            img=Image.open(fp)
            if img.size!=(1024,1024): continue
            ph=imagehash.phash(img)
            bg=estimate_bg(np.array(img))
            cb=min(STD_BGS,key=lambda n:sum((bg[i]-STD_BGS[n][i])**2 for i in range(3)))
            ai_imgs.append((f,img,ph,bg,cb))
        except: pass

    if not ai_imgs: continue

    # 处理每个 upload 文件
    for f in os.listdir(up_dir):
        if not f.lower().endswith(('.jpg','.jpeg','.png')): continue
        fp=os.path.join(up_dir,f)

        # 从文件名推断对应原图类型
        # DX{N}_B_白T.jpg → B
        # DX{N}_白BW.jpg → BW
        base=f.replace('.jpg','').replace('.jpeg','').replace('.png','')
        parts=base.split('_')
        if len(parts)>=3 and parts[1] in ('B','W') and 'T' in parts[-1]:
            up_type=parts[1]  # B 或 W
        elif len(parts)>=2 and 'BW' in parts[-1]:
            up_type='BW'
        else:
            up_type=None

        # 尝试加载 upload 图
        try:
            up_img=Image.open(fp).convert('RGB')
        except:
            continue

        up_np=np.array(up_img)
        up_ph=imagehash.phash(up_img)
        up_small=cv2.resize(up_np,(256,256))

        # 与每个原图比较
        best_score=0
        best_ai=None
        best_method=None

        for ai_fname,ai_img,ai_ph,ai_bg,ai_cb in ai_imgs:
            ai_suffix=ai_fname.replace(f"DX{dx_id:04d}_","").replace(".png","")

            # 方法1: pHash (将原图缩放到 upload 尺寸比较)
            ai_resized=np.array(ai_img.resize((256,256),Image.LANCZOS))
            h=up_ph-imagehash.phash(Image.fromarray(ai_resized))

            ph_score=1.0-h/64
            if ph_score>best_score:
                best_score=ph_score
                best_ai=ai_fname
                best_method=f"pHash={ph_score:.3f}"

            # 方法2: ORB 特征匹配（用原图 vs upload）
            if h<=HASH_OK or True:  # 对每个都做ORB
                ai_np=np.array(ai_img.resize((256,256),Image.LANCZOS))
                orb_ratio,n_good=orb_match(ai_np,up_small)
                orb_score=orb_ratio

                if orb_score>best_score:
                    best_score=orb_score
                    best_ai=ai_fname
                    best_method=f"ORB={orb_ratio:.3f}({n_good})"

        # 判断是否匹配
        threshold=ORB_OK_TEE if ('T' in f) else ORB_OK
        is_match=(best_score>=threshold)

        upload_status[(dx_id,f)]={
            "best_ai":best_ai,
            "score":best_score,
            "method":best_method,
            "match":is_match,
        }

# ─── 输出结果 ───
print("="*70)
print("📋 03_UPLOAD vs 01_AI 匹配分析")
print("="*70)

# A. 不匹配的 upload 文件
mismatch_upload=[]
for (dx,f),info in sorted(upload_status.items()):
    if not info["match"]:
        mismatch_upload.append((dx,f,info))

if mismatch_upload:
    print(f"\n❌ 03_UPLOAD 中与 01_AI 不匹配的文件 ({len(mismatch_upload)} 个):")
    for dx,f,info in mismatch_upload:
        print(f"   DX{dx:04d}\\{f}")
        print(f"     最佳匹配原图: {info['best_ai']} ({info['method']})")

# B. 检查每个 01_AI 是否有对应的 upload
ai_missing_upload=[]
for dx_id in range(START,END+1):
    up_dir=os.path.join(BASE,f"DX{dx_id:04d}","03_UPLOAD")
    ai_dir=os.path.join(BASE,f"DX{dx_id:04d}","01_AI")
    if not os.path.isdir(ai_dir): continue

    # 01_AI 中的原图
    for f in os.listdir(ai_dir):
        if not re.match(rf'DX{dx_id:04d}_.+\.png',f): continue
        fp=os.path.join(ai_dir,f)
        try:
            img=Image.open(fp)
            if img.size!=(1024,1024): continue
        except: continue

        suffix=f.replace(f"DX{dx_id:04d}_","").replace(".png","")

        # 期望的 upload 文件名模式
        if suffix=="BW":
            expected_patterns=[
                f"DX{dx_id:04d}_白BW.jpg",
                f"DX{dx_id:04d}_黑BW.jpg",
            ]
        elif suffix in ("B","W"):
            expected_patterns=[
                f"DX{dx_id:04d}_{suffix}_白T.jpg",
                f"DX{dx_id:04d}_{suffix}_黑T.jpg",
            ]
        else:
            continue

        # 检查这些文件是否存在
        if not os.path.isdir(up_dir):
            ai_missing_upload.append((dx_id,f,"03_UPLOAD 文件夹不存在"))
            continue

        missing=[]
        for ep in expected_patterns:
            if not os.path.exists(os.path.join(up_dir,ep)):
                missing.append(ep)

        if missing:
            ai_missing_upload.append((dx_id,f,missing))

if ai_missing_upload:
    print(f"\n🏗  01_AI 原图缺少对应的 03_UPLOAD 文件:")
    for dx,f,missing in ai_missing_upload:
        if isinstance(missing,str):
            print(f"   DX{dx:04d}\\{f} → {missing}")
        else:
            for m in missing:
                print(f"   DX{dx:04d}\\{f} → 缺 {m}")

# C. 统计
total_upload=len(upload_status)
total_mismatch=len(mismatch_upload)
total_missing=len(ai_missing_upload)

print(f"\n{'='*70}")
print("📊 统计汇总")
print('='*70)
print(f"   检查的 upload 文件: {total_upload}")
print(f"   ❌ 不匹配: {total_mismatch}")
print(f"   🏗 缺 upload 的原图: {total_missing}")
print(f"   ✅ 匹配正常: {total_upload-total_mismatch}")
print(f"\n✅ 分析完成")
