# -*- coding: utf-8 -*-
"""把 docs/胚衣参数表_模板.csv 同步到 white_t_mockup/presets.json（CSV 是唯一参数来源）。

CSV 是胚衣参数的 single source of truth；本脚本全量重建 presets.json 的 templates。
贴图参数（缩放/旋转/y/x/路径/混合）以 presets.json 为准，所以新增胚衣或改参数后跑一次本脚本即可。
`w_mockup_extra.generate_single_side_mockup` 贴图前也会自动调用本同步（仅当 CSV 比 presets.json 新时）。

列名匹配做"去括号规范化"：如「缩放百分比（transform）」与「缩放百分比」视为同一列，
这样改列名括号注释或微调也不影响同步。

「胚衣文件名」是 presets 的唯一 key；黑白两套胚衣若同名（如 B1.png）必须改成唯一名
（如 白B1.png/黑B1.png），否则本脚本会报错拒绝同步，防止后写覆盖前写导致贴图错位。

用法：
  python scripts/sync_presets_from_csv.py            # 有变更才写
  python scripts/sync_presets_from_csv.py --dry-run  # 只显示差异，不写
  python scripts/sync_presets_from_csv.py --force    # 无视 mtime，强制写
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # E:/Kimi Code
CSV_PATH = ROOT / "docs" / "胚衣参数表_模板.csv"
PRESETS_PATH = ROOT / "white_t_mockup" / "presets.json"

ENTRY_KEYS = (
    "path", "method", "blend_mode", "notes",
    "final_w", "final_h", "rotation_degrees", "effective_top_y", "effective_center_x",
)

def _norm_key(k):
    """列名规范化：去 BOM、去首尾空白、去掉中英文括号及其内容。"""
    if not k:
        return ""
    k = k.lstrip("﻿").strip()
    return re.sub(r"[（(].*?[）)]", "", k).strip()


def _decode_csv_bytes(raw):
    """依次尝试 utf-8-sig / utf-8 / gbk 解码 CSV 字节，返回文本（去 BOM）。

    兼容 Excel 另存为 ANSI(gbk) 或工具写成无 BOM UTF-8 的情况，避免中文乱码/解码失败。
    """
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc).lstrip("﻿")
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, "无法用 utf-8/gbk 解码 CSV")


def ensure_bom(path):
    """若 CSV 无 BOM 且为合法 UTF-8，补 BOM（幂等）。Excel 据此按 UTF-8 显示中文。

    返回 True 表示本次补了 BOM。gbk 文件不补（避免破坏），交由 _decode_csv_bytes 读取。
    """
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        return False
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    path.write_bytes(b"\xef\xbb\xbf" + raw)
    return True


def _read_csv_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV 不存在: {path}")
    text = _decode_csv_bytes(path.read_bytes())
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    except Exception:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
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


def _parse_rotation(deg_text):
    """角度列直接带符号：负=逆时针，正=顺时针（与 PS/white_t_mockup.apply_transform 一致）。"""
    return _num(deg_text) or 0.0


def _row_to_entry(row):
    name = _col(row, "胚衣文件名")
    if not name:
        return None, None
    top_y = _num(_col(row, "最高像素点y"))
    cx = _num(_col(row, "中心点x"))
    fw = _num(_col(row, "缩放后宽px"))
    fh = _num(_col(row, "缩放后高px"))
    entry = {
        "path": _col(row, "胚衣完整路径"),
        "method": _col(row, "方法") or "transform",
        "blend_mode": (_col(row, "混合模式") or "multiply").lower(),
        "notes": _col(row, "备注"),
        "final_w": int(fw) if fw is not None else None,
        "final_h": int(fh) if fh is not None else None,
        "rotation_degrees": _parse_rotation(_col(row, "旋转角度")),
        "effective_top_y": int(top_y) if top_y is not None else None,
        "effective_center_x": int(cx) if cx is not None else None,
    }
    return name, entry


def build_templates(csv_path=CSV_PATH):
    templates = {}
    seen_path = {}
    for row in _read_csv_rows(csv_path):
        name, entry = _row_to_entry(row)
        if not name:
            continue
        if name in templates:
            raise ValueError(
                f"胚衣文件名重复: {name!r} "
                f"(path1={seen_path[name]!r}, path2={entry['path']!r})。"
                "请在 CSV 改成唯一名（如加 白/黑 前缀：白B1.png / 黑B1.png）。"
            )
        seen_path[name] = entry["path"]
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
    ensure_bom(csv_path)  # 每次贴图前自动补 BOM（幂等），彻底避免 Excel 乱码
    csv_mtime = csv_path.stat().st_mtime
    presets_mtime = presets_path.stat().st_mtime if presets_path.exists() else 0
    if presets_mtime >= csv_mtime:
        return False, "presets.json 已是最新，跳过同步"
    p_changed, new, old = sync_presets_from_csv(csv_path, presets_path, write=True, force=True)
    return True, f"已从 CSV 同步 presets.json（{len(new)} 模板，变更={p_changed}）"


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
    try:
        p_changed, new, old = sync_presets_from_csv(write=not dry, force=force)
    except ValueError as e:
        print(f"同步中止：{e}")
        sys.exit(2)
    _report(new, old)
    tag = "DRY-RUN " if dry else ""
    print(f"{tag}presets {'有变更' if p_changed else '无变更'}（{len(new)} 个模板）")
    if dry and p_changed:
        print("（dry-run 未写入；去掉 --dry-run 执行实际同步）")


if __name__ == "__main__":
    main()
