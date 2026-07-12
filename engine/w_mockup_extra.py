# -*- coding: utf-8 -*-
"""单面贴图新流程 v2.1（模特图+平铺图贴图）：02_REM_BG 里只有 W 或只有 B 时，用 white_t_mockup 胚衣出图。

变更 v2.1（命名规则 + 平铺/模特分类）：
  - 胚衣按是否平铺分类：平铺胚衣 = 白W11/黑W11(正面)/白B12/黑B7(背面)，其余为模特图。
  - 输出命名（用户规则 2026-07-12）：
      平铺图 ``{dx}_{role}{color}T.jpg``（例 DX0650_W白T.jpg / DX0650_B黑T.jpg）；
      模特图 ``{dx}_{color}{role}.jpg`` （例 DX0650_白W.jpg  / DX0650_黑B.jpg）。
  - 每色固定出 2 张：固定平铺胚衣 1 张 + 随机模特胚衣 1 张（W/B 统一）。
  - B 款从"随机 1 张"改为与 W 款一致的"固定平铺 + 随机模特"。

变更 v2.0（架构重构）：
  - 胚衣来源从 presets.json/CSV 改为素材库（D:\\Semems WB\\03_MATERIAL\\）。
  - 参数从素材库同名 .meta.json 读取（width/height/rotation/highest_y/center_x）。
  - 扭曲素材自动探测 D:\\Semems\\1胚衣\\_tpl\\<款名>\\（mask/disp/shadow/highlight/occlusion）。
  - 黑衫贴图用 --preserve-color（原样保色，几何变形 only）。
  - 不再依赖 presets.json 和 胚衣参数表_模板.csv。

变更 v1.1：
  - 黑衫从 `--blend-mode screen` 改为 `--preserve-color`。

胚衣选择规则：
- 每色出 2 张：固定平铺胚衣（W=白W11/黑W11，B=白B12/黑B7）+ 随机 1 张模特胚衣。
- 某颜色无候选则跳过该颜色（记入返回 msg），不报错。

去背图颜色路由（check_rem 调用时传入）：
- cut_path：指定用哪张去背图（默认 ``{dx}_{role}_cut.png``）。
- only_color：``"白"`` 只贴白T 胚衣、``"黑"`` 只贴黑T 胚衣、``None`` 两色都贴。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# white_t_mockup 工程根目录与专用解释器（psd_tools/PIL 都装在这个 venv 里）
W_MOCKUP_ROOT = Path(r"E:\Kimi Code")
W_MOCKUP_PY = W_MOCKUP_ROOT / "psd_env" / "Scripts" / "python.exe"

# 素材库根目录（胚衣 jpg + meta.json 参数）
MATERIAL_DIR = Path(r"D:\Semems WB\03_MATERIAL")
# 扭曲素材根目录（mask/disp/shadow/highlight/occlusion）
TPL_ROOT = Path(r"D:\Semems\1胚衣\_tpl")

# 素材库分类目录映射：(role, color) → 目录
_CATEGORY_MAP = {
    ("W", "白"): MATERIAL_DIR / "W白",
    ("W", "黑"): MATERIAL_DIR / "W黑",
    ("B", "白"): MATERIAL_DIR / "B白",
    ("B", "黑"): MATERIAL_DIR / "B黑",
}

# 平铺图胚衣（T 恤平铺在场景里，非人穿）：其余胚衣一律视为模特图。
# 用户指定（2026-07-12）：白W11 / 黑W11（正面平铺）、白B12 / 黑B7（背面平铺）。
_FLAT_STEMS = {"白W11", "黑W11", "白B12", "黑B7"}

# 各 (role, color) 固定使用的平铺胚衣（素材库 stem 名）
_FLAT_MANDATORY = {
    ("W", "白"): "白W11",
    ("W", "黑"): "黑W11",
    ("B", "白"): "白B12",
    ("B", "黑"): "黑B7",
}


def _is_flat(stem: str) -> bool:
    """该胚衣是否平铺图（决定输出命名：平铺 vs 模特）。"""
    return stem in _FLAT_STEMS


def _output_name(dx: str, role: str, color: str, stem: str) -> str:
    """按平铺/模特规则生成输出文件名。

    - 平铺图：``{dx}_{role}{color}T.jpg``  例：DX0650_W白T.jpg / DX0650_B黑T.jpg
    - 模特图：``{dx}_{color}{role}.jpg``   例：DX0650_白W.jpg / DX0650_黑B.jpg
    """
    if _is_flat(stem):
        return f"{dx}_{role}{color}T.jpg"
    return f"{dx}_{color}{role}.jpg"


def _read_meta(embryo_path: Path) -> dict | None:
    """读取素材库胚衣的 .meta.json 参数。返回 None 表示缺失或损坏。"""
    meta_path = embryo_path.parent / (embryo_path.stem + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        w = data.get("width", 0)
        h = data.get("height", 0)
        if not w or not h or w <= 0 or h <= 0:
            return None
        return {
            "final_w": int(w),
            "final_h": int(h),
            "rotation": float(data.get("rotation", 0)),
            "effective_top_y": int(data.get("highest_y", 0)),
            "effective_center_x": int(data.get("center_x", 670)),
        }
    except Exception:
        return None


def _find_tpl_dir(embryo_path: Path) -> str | None:
    """自动探测扭曲素材目录：D:\\Semems\\1胚衣\\_tpl\\<款名>\\。"""
    cand = TPL_ROOT / embryo_path.stem
    if (cand / "mask.png").exists():
        return str(cand)
    return None


def _find_occluder(embryo_path: Path) -> str | None:
    """自动探测顶层遮挡物：<款名>_occluder.png。"""
    occ = embryo_path.parent / (embryo_path.stem + "_occluder.png")
    if occ.exists():
        return str(occ)
    return None


def _list_material_embryos(role: str, color: str) -> list[dict]:
    """列出素材库中指定 role+color 的可用胚衣。

    返回 [{path, stem, meta, tpl_dir, occluder}, ...]，仅包含有有效 meta.json 的胚衣。
    """
    cat_dir = _CATEGORY_MAP.get((role, color))
    if not cat_dir or not cat_dir.is_dir():
        return []
    results = []
    for fp in sorted(cat_dir.iterdir()):
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        # 跳过遮罩侧车文件
        if any(fp.name.endswith(s) for s in ("_occluder.png", "_occluder_mask.png",
                                              "_body_mask.png", "_parse.png", "_alpha.png")):
            continue
        meta = _read_meta(fp)
        if meta is None:
            continue
        results.append({
            "path": fp,
            "stem": fp.stem,
            "meta": meta,
            "tpl_dir": _find_tpl_dir(fp),
            "occluder": _find_occluder(fp),
        })
    return results


def generate_single_side_mockup(
    dx: str,
    base_dir: Path,
    role: str,
    runner,
    cut_path: str | Path | None = None,
    only_color: str | None = None,
) -> tuple[bool, str]:
    """用素材库胚衣为单面款出模特图贴图。

    - dx: 款号，如 ``DX0001``
    - base_dir: 项目根目录（其下有 ``<dx>/02_REM_BG``、``<dx>/03_UPLOAD``）
    - role: ``"W"`` 或 ``"B"``
    - runner: 等价于 check_rem.run_minimized 的可调用对象
    - cut_path: 指定用哪张去背图（默认 ``<base_dir>/<dx>/02_REM_BG/<dx>_<role>_cut.png``）
    - only_color: ``"白"`` 只贴白T 胚衣、``"黑"`` 只贴黑T 胚衣、``None`` 两色都贴

    每色出 2 张：固定平铺胚衣（W=白W11/黑W11，B=白B12/黑B7）+ 随机 1 张模特胚衣。
    平铺图命名为 ``{dx}_{role}{color}T.jpg``，模特图为 ``{dx}_{color}{role}.jpg``。
    某颜色无候选则跳过该颜色（记入返回 msg），不报错。
    失败返回 ``(False, 错误信息)``；任一颜色成功则 ok=True，逐张结果都写入 msg。
    """
    try:
        if role not in ("W", "B"):
            return False, f"不支持的单面角色: {role}"
        if only_color not in (None, "白", "黑"):
            return False, f"不支持的 only_color: {only_color}"
        rem_dir = Path(base_dir) / dx / "02_REM_BG"
        up_dir = Path(base_dir) / dx / "03_UPLOAD"
        cut = Path(cut_path) if cut_path is not None else rem_dir / f"{dx}_{role}_cut.png"
        if not cut.exists():
            return False, f"缺少 {cut.name}"

        if not W_MOCKUP_PY.exists():
            return False, f"模特图贴图解释器不存在: {W_MOCKUP_PY}"

        # 按颜色列出素材库胚衣
        colors_to_do = []
        if only_color is None or only_color == "白":
            colors_to_do.append("白")
        if only_color is None or only_color == "黑":
            colors_to_do.append("黑")

        selected: list[tuple[dict, str]] = []  # (embryo_info, color)
        notes: list[str] = []
        for color in colors_to_do:
            pool = _list_material_embryos(role, color)
            if not pool:
                notes.append(f"{color}T 跳过：素材库无可用 {role}{color} 胚衣（或 meta.json 缺失/损坏）")
                continue
            # 每色出 2 张：固定平铺胚衣 1 张 + 随机模特胚衣 1 张
            mandatory = _FLAT_MANDATORY.get((role, color))
            fixed = [e for e in pool if e["stem"] == mandatory]
            models = [e for e in pool if not _is_flat(e["stem"])]
            if fixed:
                selected.append((fixed[0], color))
            else:
                notes.append(f"{color}T 平铺胚衣 {mandatory} 不可用（meta 缺失/损坏），仅出模特图")
            if models:
                selected.append((random.choice(models), color))
            if not fixed and not models:
                notes.append(f"{color}T 跳过：无可用胚衣")

        if not selected:
            return False, f"无可用 {role} 模特图胚衣（素材库白/黑候选均为空或 meta.json 缺失）"

        up_dir.mkdir(parents=True, exist_ok=True)

        results: list[tuple[str, bool, str]] = []
        for embryo, color in selected:
            stem = embryo["stem"]
            meta = embryo["meta"]
            out = up_dir / _output_name(dx, role, color, stem)

            cmd = [
                str(W_MOCKUP_PY), "-m", "white_t_mockup",
                str(cut), str(out),
                "--template", str(embryo["path"]),
                "--final-w", str(meta["final_w"]),
                "--final-h", str(meta["final_h"]),
                "--rotate", str(meta["rotation"]),
                "--effective-top-y", str(meta["effective_top_y"]),
                "--effective-center-x", str(meta["effective_center_x"]),
                # 位移强度：v2.1 由 18 调回 30（大褶皱恢复旧版扭曲水平；
                # 小褶皱水波纹由 core.py 的 --disp-smooth 80 + --disp-dead-zone 15 抑制，
                # 平滑只去高频小褶，强度再高也不会出现水波纹）
                "--disp-strength", "30",
                "--disp-smooth", "80",
                "--disp-dead-zone", "15",
            ]
            if embryo["tpl_dir"]:
                cmd += ["--tpl-dir", embryo["tpl_dir"]]
            if color == "黑":
                cmd += ["--preserve-color"]
            if embryo["occluder"]:
                cmd += ["--occluder", embryo["occluder"]]

            proc = runner(cmd, cwd=str(W_MOCKUP_ROOT), capture_output=True, text=True)
            tag = f"{role}/{color}T/{stem}"
            if getattr(proc, "returncode", 1) != 0:
                tail = (getattr(proc, "stderr", "") or getattr(proc, "stdout", "") or "")[-400:]
                results.append((stem, False, f"{tag} 失败: {tail}"))
            else:
                results.append((stem, True, f"{tag} 完成: {out.name}"))

        ok = any(ok for _, ok, _ in results)
        msg = "; ".join(notes + [text for _, _, text in results])
        return ok, msg
    except Exception as e:
        return False, f"{role} 模特图贴图异常: {e}"
