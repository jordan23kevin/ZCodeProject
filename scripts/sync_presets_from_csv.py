# -*- coding: utf-8 -*-
"""把 docs/胚衣参数表_模板.csv 同步到 white_t_mockup/presets.json。

CSV 是胚衣参数的 single source of truth；本脚本全量重建 presets.json 的 templates。
贴图参数（缩放/旋转/y/x/路径/混合）以 presets.json 为准，所以新增胚衣或改参数后跑一次本脚本即可。
`w_mockup_extra.generate_single_side_mockup` 贴图前也会自动调用本同步（仅当 CSV 比 presets.json 新时）。

列名匹配做"去括号规范化"：如「缩放百分比（transform）」与「缩放百分比」视为同一列，
这样改列名括号注释或微调也不影响同步。

用法：
  python scripts/sync_presets_from_csv.py            # 有变更才写
  python scripts/sync_presets_from_csv.py --dry-run  # 只显示差异，不写
  python scripts/sync_presets_from_csv.py --force    # 无视 mtime，强制写
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # E:/Kimi Code
CSV_PATH = ROOT / "docs" / "胚衣参数表_模板.csv"
PRESETS_PATH = ROOT / "white_t_mockup" / "presets.json"

ENTRY_KEYS = (
    "path", "method", "blend_mode", "notes",
    "scale", "rotation_degrees", "effective_top_y", "effective_center_x",
)


def _norm_key(k):
    """列名规范化：去 BOM、去首尾空白、去掉中英文括号及其内容。"""
    if not k:
        return ""
    k = k.lstrip("﻿").strip()
    return re.sub(r"[（(].*?[）)]", "", k).strip()


def _read_csv_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV 不存在: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            yield {_norm_key(k): (v or "") for k, v in row.items() if k is not None}


def _col(row, name):
    return (row.get(name) or "").strip()


def _num(text):
    t = (text or "").strip().replace("%", "").replace("％", "")
    if not t:
        return None
    try:
        return float(t)
    except Exception:
        return None


def _parse_scale(text):
    """缩放百分比：32 → 0.32；兼容填 0.32（<=1 直接用）。"""
    s = _num(text)
    if s is None:
        return None
    return s / 100.0 if s > 1 else s


def _parse_rotation(dir_text, deg_text):
    """顺时针→正，逆时针→负，无/空→0（与 white_t_mockup.apply_transform 一致）。"""
    deg = _num(deg_text) or 0.0
    d = (dir_text or "").strip()
    if d == "顺时针":
        return abs(deg)
    if d == "逆时针":
        return -abs(deg)
    return 0.0


def _row_to_entry(row):
    name = _col(row, "胚衣文件名")
    if not name:
        return None, None
    top_y = _num(_col(row, "最高像素点y"))
    cx = _num(_col(row, "中心点x"))
    entry = {
        "path": _col(row, "胚衣完整路径"),
        "method": _col(row, "方法") or "transform",
        "blend_mode": (_col(row, "混合模式") or "multiply").lower(),
        "notes": _col(row, "备注"),
        "scale": _parse_scale(_col(row, "缩放百分比")),
        "rotation_degrees": _parse_rotation(_col(row, "旋转方向"), _col(row, "旋转角度")),
        "effective_top_y": int(top_y) if top_y is not None else None,
        "effective_center_x": int(cx) if cx is not None else None,
    }
    return name, entry


def build_templates(csv_path=CSV_PATH):
    templates = {}
    for row in _read_csv_rows(csv_path):
        name, entry = _row_to_entry(row)
        if name:
            templates[name] = entry
    return templates


def _load_old_templates(presets_path):
    if not presets_path.exists():
        return {}
    try:
        return json.loads(presets_path.read_text(encoding="utf-8")).get("templates", {})
    except Exception:
        return {}


def sync_presets_from_csv(csv_path=CSV_PATH, presets_path=PRESETS_PATH, write=True, force=False):
    """同步 CSV → presets.json。

    返回 (changed, new_templates, old_templates)。
    write=True 且 (changed 或 force) 时原子写入 presets.json。
    """
    new_templates = build_templates(csv_path)
    old_templates = _load_old_templates(presets_path)
    changed = new_templates != old_templates
    if (changed or force) and write:
        presets_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = presets_path.with_suffix(presets_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"templates": new_templates}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(presets_path)
    return changed, new_templates, old_templates


def sync_if_stale(csv_path=CSV_PATH, presets_path=PRESETS_PATH):
    """仅当 CSV 比 presets.json 新时同步（供贴图前调用）。返回 (synced, msg)。"""
    if not csv_path.exists():
        return False, f"CSV 不存在: {csv_path}"
    if presets_path.exists() and presets_path.stat().st_mtime >= csv_path.stat().st_mtime:
        return False, "presets.json 已是最新，跳过同步"
    changed, new, old = sync_presets_from_csv(csv_path, presets_path, write=True, force=True)
    if changed:
        return True, f"已从 CSV 同步 presets.json（{len(new)} 个模板）"
    return True, f"CSV 较新但内容一致，已刷新 presets.json（{len(new)} 个模板）"


def _report(new, old):
    all_keys = sorted(set(new) | set(old))
    for k in all_keys:
        if k not in old:
            print(f"  + 新增 {k}: {new[k]}")
        elif k not in new:
            print(f"  - 删除 {k}: {old[k]}")
        elif new[k] != old[k]:
            print(f"  ~ 变更 {k}:")
            for kk in sorted(set(new[k]) | set(old[k])):
                if new[k].get(kk) != old[k].get(kk):
                    print(f"      {kk}: {old[k].get(kk)!r} -> {new[k].get(kk)!r}")


def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    changed, new, old = sync_presets_from_csv(write=not dry, force=force)
    _report(new, old)
    tag = "DRY-RUN " if dry else ""
    print(f"{tag}{'有变更' if changed else '无变更'}，共 {len(new)} 个模板")
    if dry and changed:
        print("（dry-run 未写入；去掉 --dry-run 执行实际同步）")


if __name__ == "__main__":
    main()
