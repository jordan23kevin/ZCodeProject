import sys, os, time, json, traceback

# 运行环境：本机 cv2/torch/transformers 来自 E:/python_packages
sys.path.insert(0, r'E:/python_packages')
sys.path.insert(0, r'C:/Users/Administrator/ZCodeProject')

from pathlib import Path
import peiyi_mask

ROOT = Path(r'D:/Semems WB/03_MATERIAL')
CATS = ['W白', 'W黑', 'B白', 'B黑']
LOG = Path(r'C:/Users/Administrator/ZCodeProject/_regen_all_log.json')

print(f"peiyi_mask VERSION = {getattr(peiyi_mask, 'VERSION', '?')}", flush=True)
print(f"开始重新生成，模型只加载一次。根目录: {ROOT}", flush=True)

results = []
t_all = time.time()
for cat in CATS:
    cat_dir = ROOT / cat
    jpgs = sorted(cat_dir.glob('*.jpg'))
    for jpg in jpgs:
        stem = jpg.stem
        t0 = time.time()
        try:
            res = peiyi_mask.generate_masks(jpg, category=cat)
            res['stem'] = f"{cat}/{stem}"
            res['elapsed'] = round(time.time() - t0, 1)
            results.append(res)
            print(f"[{cat}/{stem}] ok={res.get('ok')} version={res.get('version')} "
                  f"body={res.get('body_px')} occ={res.get('occluder_px')} ({res['elapsed']}s)", flush=True)
        except Exception as e:
            results.append({'stem': f"{cat}/{stem}", 'ok': False,
                            'error': str(e), 'trace': traceback.format_exc()})
            print(f"[{cat}/{stem}] ERROR: {e}", flush=True)

ok = [r for r in results if r.get('ok')]
fail = [r for r in results if not r.get('ok')]
print(f"\n=== SUMMARY: {len(ok)} 成功, {len(fail)} 失败, 共 {len(results)} 张, 耗时 {round(time.time()-t_all,1)}s ===", flush=True)
for r in fail:
    print("FAIL:", r.get('stem'), '->', r.get('error'), flush=True)

LOG.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"日志已写入: {LOG}", flush=True)
