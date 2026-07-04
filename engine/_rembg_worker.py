#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单张去背工作进程
由 check_rem.py /rembg 端点启动，负责在后台运行美图去背并清理锁。
"""
import sys
import os
from pathlib import Path

# 把 engine 目录加入路径，方便导入 check_rem
sys.path.insert(0, str(Path(__file__).parent))

from check_rem import rembg_one_file, TEMP_REMBG


def main():
    if len(sys.argv) < 3:
        print("用法: _rembg_worker.py <DX> <ai_file>", flush=True)
        return 1

    dx = sys.argv[1]
    ai_file = sys.argv[2]
    lock = TEMP_REMBG / ".rembg_lock"

    try:
        print(f"[_rembg_worker] 开始 {dx}/{ai_file}", flush=True)
        ok, msg = rembg_one_file(dx, ai_file)
        print(f"[_rembg_worker] 结果: ok={ok}, msg={msg}", flush=True)
    except Exception as e:
        print(f"[_rembg_worker] 异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        try:
            if lock.exists():
                lock.unlink()
                print("[_rembg_worker] 锁已清理", flush=True)
        except Exception as e:
            print(f"[_rembg_worker] 清理锁失败: {e}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
