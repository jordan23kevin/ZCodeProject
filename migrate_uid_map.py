"""
UID/group_id 全链路溯源迁移脚本 v1.0
======================================
扫描 D:\Semems WB\02_PROJECTS 下所有 DX 文件夹，为没有 sidecar/uid_map 的
旧项目生成 uid_map.json 与 .meta.json sidecar。

用法:
  python migrate_uid_map.py              # 迁移所有 DX 项目
  python migrate_uid_map.py DX0255       # 只迁移指定款
  python migrate_uid_map.py --dry-run    # 只打印会做什么，不写入
"""

import sys
import argparse
from pathlib import Path

_ZCODE = Path(__file__).parent
if str(_ZCODE) not in sys.path:
    sys.path.insert(0, str(_ZCODE))

try:
    import wb_meta
except Exception as e:
    print(f"❌ 无法导入 wb_meta: {e}")
    sys.exit(1)


def migrate_dx(dx_name: str, dry_run: bool = False):
    dx_dir = Path("D:/Semems WB/02_PROJECTS") / dx_name
    if not dx_dir.is_dir():
        print(f"❌ 不存在: {dx_dir}")
        return False
    if dry_run:
        print(f"[dry-run] 将迁移 {dx_name}")
        return True
    try:
        wb_meta.migrate_dx(dx_dir)
        print(f"✅ 迁移完成: {dx_name}")
        return True
    except Exception as e:
        print(f"❌ 迁移失败 {dx_name}: {e}")
        return False


def migrate_all(dry_run: bool = False):
    projects_dir = Path("D:/Semems WB/02_PROJECTS")
    if not projects_dir.exists():
        print(f"❌ 项目目录不存在: {projects_dir}")
        return
    count = 0
    for d in sorted(projects_dir.iterdir()):
        if d.is_dir() and d.name.startswith("DX") and d.name[2:].isdigit():
            if migrate_dx(d.name, dry_run=dry_run):
                count += 1
    print(f"\n共处理 {count} 款")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="迁移 DX 项目到 UID/group_id 元数据系统")
    parser.add_argument("dx", nargs="?", help="指定 DX 款号，如 DX0255")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写入")
    args = parser.parse_args()

    if args.dx:
        migrate_dx(args.dx, dry_run=args.dry_run)
    else:
        migrate_all(dry_run=args.dry_run)
