# -*- coding: utf-8 -*-
"""AI 去背/贴图 OS 的额外 W 胚衣贴图 helper。

在原有 PS 贴图流程后调用：随机选一个 W 后缀胚衣 preset（当前如 W3.psd），
用 white_t_mockup 额外生成一张 W 胚衣白 T 图。
"""

from __future__ import annotations

import json
import random
from pathlib import Path


W_MOCKUP_ROOT = Path(r"E:\Kimi Code")
W_MOCKUP_PY = W_MOCKUP_ROOT / "psd_env" / "Scripts" / "python.exe"
W_MOCKUP_PRESETS = W_MOCKUP_ROOT / "white_t_mockup" / "presets.json"


def _load_w_template_names() -> list[str]:
    """从 white_t_mockup/presets.json 读取 W 后缀胚衣模板名。"""
    if not W_MOCKUP_PRESETS.exists():
        return []
    try:
        data = json.loads(W_MOCKUP_PRESETS.read_text(encoding="utf-8"))
    except Exception:
        return []

    names = []
    for name in data.get("templates", {}).keys():
        upper = name.upper()
        # W 胚衣：W3.psd / W4.png 这类；排除 BW。
        if upper.startswith("W") and not upper.startswith("BW") and upper.endswith((".PSD", ".PNG", ".JPG", ".JPEG")):
            names.append(name)
    return sorted(names)


def generate_w_template_mockup(dx: str, base_dir: Path, runner) -> tuple[bool, str]:
    """为指定 DX 额外生成一张 W 胚衣贴图。

    runner 由 check_rem.py 传入，签名与 _run_ps_script_with_timeout 相同：
    runner(cmd, cwd=..., label=...) -> (ok, msg)
    """
    rem_dir = base_dir / dx / "02_REM_BG"
    up_dir = base_dir / dx / "03_UPLOAD"
    cut_path = rem_dir / f"{dx}_W_cut.png"

    if not cut_path.exists():
        return True, f"无 {cut_path.name}，跳过 W 胚衣"

    templates = _load_w_template_names()
    if not templates:
        return True, "没有 W 胚衣 preset，跳过 W 胚衣"

    template_name = random.choice(templates)
    template_stem = Path(template_name).stem
    out_path = up_dir / f"{dx}_W_{template_stem}_白T.jpg"
    up_dir.mkdir(parents=True, exist_ok=True)

    if not W_MOCKUP_PY.exists():
        return False, f"W 胚衣 Python 不存在: {W_MOCKUP_PY}"

    cmd = [
        str(W_MOCKUP_PY),
        "-m",
        "white_t_mockup",
        str(cut_path),
        str(out_path),
        "--preset",
        template_name,
    ]
    ok, msg = runner(cmd, cwd=str(W_MOCKUP_ROOT), label=f"W胚衣贴图({template_name})")
    if not ok:
        return False, f"W胚衣贴图失败: {dx} ({msg})"
    return True, f"W胚衣贴图完成: {out_path.name}"
