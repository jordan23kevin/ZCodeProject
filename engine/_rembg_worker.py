#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单张去背工作进程
由 check_rem.py /rembg 端点启动，负责在后台运行美图去背并清理锁。
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# 把 engine 目录加入路径，方便导入 check_rem
sys.path.insert(0, str(Path(__file__).parent))

from check_rem import rembg_one_file, TEMP_REMBG


def _setup_logging():
    log_dir = Path(os.environ.get("SEMEMS_ROOT", "D:/Semems WB")) / "_debug"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"_rembg_worker_{datetime.now():%Y%m%d_%H%M%S}.log"
    f = open(log_path, "a", encoding="utf-8")
    sys.stdout = f
    sys.stderr = f
    return log_path, f


def main():
    log_path, log_f = _setup_logging()
    print(f"[_rembg_worker] 日志: {log_path}", flush=True)

    if len(sys.argv) < 3:
        print("用法: _rembg_worker.py <DX> <ai_file>", flush=True)
        log_f.close()
        return 1

    dx = sys.argv[1]
    ai_file = sys.argv[2]
    token = sys.argv[3] if len(sys.argv) > 3 else None
    lock = TEMP_REMBG / ".rembg_lock"

    try:
        print(f"[_rembg_worker] 开始 {dx}/{ai_file}", flush=True)
        ok, msg = rembg_one_file(dx, ai_file)
        print(f"[_rembg_worker] {'✅' if ok else '❌'} {msg}", flush=True)
    except Exception as e:
        print(f"[_rembg_worker] ❌ 异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
        try:
            from check_rem import _restore_config
            _restore_config()
        except Exception:
            pass
    finally:
        try:
            if lock.exists():
                # 仅当锁还是本任务的（token 匹配，或未传 token）才清理，
                # 避免被强制重跑时误删新任务刚写入的锁
                content = lock.read_text(encoding="utf-8")
                if token is None or token in content:
                    lock.unlink()
                    print("[_rembg_worker] 锁已清理", flush=True)
                else:
                    print("[_rembg_worker] 锁已被新任务接管，跳过清理", flush=True)
        except Exception as e:
            print(f"[_rembg_worker] 清理锁失败: {e}", flush=True)
        try:
            log_f.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
