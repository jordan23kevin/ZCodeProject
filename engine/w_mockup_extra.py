# -*- coding: utf-8 -*-
"""单面贴图新流程 v2.4（模特图+平铺图贴图）：02_REM_BG 里只有 W 或只有 B 时，用 white_t_mockup 胚衣出图。

变更 v2.4（素材库按品类根解析）：
  - 素材库根 MATERIAL_DIR 由写死 T恤（D:\\Semems WB\\03_MATERIAL）改为读 SEMEMS_ROOT
    环境变量（check_rem 启动时注入：T恤 D:\\Semems WB、卫衣 D:\\Semems Hoodie；缺省 T恤）。
    卫衣单面款贴图从此使用卫衣素材库（D:\\Semems Hoodie\\03_MATERIAL\\W黑 等），
    不再错贴 T恤 胚衣。
  - 卫衣素材库无平铺胚衣（无 白W11/黑W11/白B12/黑B7），只会出模特图命名
    （HXxxxx_黑W.jpg 等），属预期行为。

变更 v2.3（gradient 褶皱贴合，用户选定 s=90）：
  - 位移模式由 isotropic（鼓包/平移）改为 gradient：把 disp 当高度场，沿褶皱切线
    做 2D 梯度位移，印花真实「裹」在褶皱上。强度、smooth 经用户 4×5 测试图对比选定
    s=90 / smooth=40。
  - 手部/前景遮挡物清零：disp.png 含手/前景明暗，会在这些区域造出假位移（"引力场"）；
    core.py 在 smooth 前把 occluder 覆盖区位移压平到 128，仅遮挡不扭曲。
  - 位移场经 _limit_gradient_2d 限幅（|∇off|≤0.45）消除尖锐褶皱脊处的镜像重影/折叠。
  - 遮罩(mask)不参与位移，只由设计图自身 alpha 裁剪贴图区域。
  - 白/黑模特图统一 --preserve-color，贴图颜色与源文件一致、无色差。

变更 v2.2（褶皱贴合 + 无色差）：
  - 模特图（白/黑）统一走 --preserve-color，消除 multiply/阴影/高光导致的色差，
    贴图颜色与源文件一致。
  - disp-strength 由 30 提到 90，配合 core.py 的 mask 边缘羽化 + 软死区，
    大褶皱区域明显随褶皱形变，小褶皱保持平整，无撕裂。

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
import os
import random
from pathlib import Path

import wb_naming as naming  # 命名规则唯一出处（同目录）

# white_t_mockup 工程根目录与专用解释器（psd_tools/PIL 都装在这个 venv 里）
W_MOCKUP_ROOT = Path(r"E:\Kimi Code")
W_MOCKUP_PY = W_MOCKUP_ROOT / "psd_env" / "Scripts" / "python.exe"

# 品类根（check_rem 启动时注入 SEMEMS_ROOT；缺省 T恤）。
# 素材库根目录（胚衣 jpg + meta.json 参数）按品类解析，卫衣自动用 D:\Semems Hoodie\03_MATERIAL。
SEMEMS_ROOT = Path(os.environ.get("SEMEMS_ROOT", r"D:\Semems WB"))
MATERIAL_DIR = SEMEMS_ROOT / "03_MATERIAL"
# 扭曲素材根目录（mask/disp/shadow/highlight/occlusion）
TPL_ROOT = Path(r"D:\Semems\1胚衣\_tpl")

# 素材库分类目录映射：(role, color) → 目录
_CATEGORY_MAP = {
    ("W", "白"): MATERIAL_DIR / "W白",
    ("W", "黑"): MATERIAL_DIR / "W黑",
    ("B", "白"): MATERIAL_DIR / "B白",
    ("B", "黑"): MATERIAL_DIR / "B黑",
}

def _read_meta(embryo_path: Path, use_bw: bool = False) -> dict | None:
    """读取素材库胚衣的 .meta.json 参数。返回 None 表示缺失或损坏。

    use_bw=True 时读取 "bw" 块（双面款正面专用五参），适用于 DXxxxxBW 款的 W 面。
    若 use_bw=True 但 meta.json 中无 "bw" 块，抛 ValueError（不兜底，避免用错尺寸）。
    """
    meta_path = embryo_path.parent / (embryo_path.stem + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        if use_bw:
            bw = data.get("bw")
            if not bw:
                raise ValueError(
                    f"{meta_path.name} 缺少 \"bw\" 块：双面款正面(W)需要 bw 五参，"
                    f"请在胚衣制作·素材库里补充该款的 bw 参数"
                )
            src = bw
        else:
            src = data
        w = src.get("width", 0)
        h = src.get("height", 0)
        if not w or not h or w <= 0 or h <= 0:
            return None
        return {
            "final_w": int(w),
            "final_h": int(h),
            "rotation": float(src.get("rotation", 0)),
            "effective_top_y": int(src.get("highest_y", 0)),
            "effective_center_x": int(src.get("center_x", 670)),
        }
    except ValueError:
        raise
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


def _list_material_embryos(role: str, color: str, use_bw: bool = False) -> list[dict]:
    """列出素材库中指定 role+color 的可用胚衣。

    返回 [{path, stem, meta, tpl_dir, occluder}, ...]，仅包含有有效 meta.json 的胚衣。
    use_bw=True 时读取 meta.json 的 "bw" 块（双面款正面专用）。
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
        # use_bw=True 时，无 "bw" 块的胚衣跳过（不适用于双面款正面）
        try:
            meta = _read_meta(fp, use_bw=use_bw)
        except ValueError:
            continue
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


def plan_single_side_jobs(
    dx: str,
    base_dir: Path,
    role: str,
    cut_path: str | Path | None = None,
    only_color: str | None = None,
) -> tuple[list[dict], list[str]]:
    """为单面款规划模特图贴图任务（只规划不执行，供批量模式统一调度）。

    - dx: 款号，如 ``DX0001``
    - base_dir: 项目根目录（其下有 ``<dx>/02_REM_BG``、``<dx>/03_UPLOAD``）
    - role: ``"W"`` 或 ``"B"``
    - cut_path: 指定用哪张去背图（默认 ``<base_dir>/<dx>/02_REM_BG/<dx>_<role>_cut.png``）
    - only_color: ``"白"`` 只贴白T 胚衣、``"黑"`` 只贴黑T 胚衣、``None`` 两色都贴

    每色出 2 张：固定平铺胚衣（W=白W11/黑W11，B=白B12/黑B7）+ 随机 1 张模特胚衣。
    返回 (jobs, notes)：jobs 为 [{dx, tag, out, argv}]，argv 即 white_t_mockup CLI
    单张模式的全部参数（与旧逐张调用完全一致，保证输出不变）；notes 为跳过原因。
    """
    try:
        if role not in ("W", "B"):
            return [], [f"不支持的单面角色: {role}"]
        if only_color not in (None, "白", "黑"):
            return [], [f"不支持的 only_color: {only_color}"]
        rem_dir = Path(base_dir) / dx / "02_REM_BG"
        up_dir = Path(base_dir) / dx / "03_UPLOAD"
        cut = Path(cut_path) if cut_path is not None else rem_dir / f"{dx}_{role}_cut.png"
        if not cut.exists():
            return [], [f"缺少 {cut.name}"]

        if not W_MOCKUP_PY.exists():
            return [], [f"模特图贴图解释器不存在: {W_MOCKUP_PY}"]

        # 双面款(DXxxxxBW)的正面(W)使用 meta.json 的 "bw" 块五参（尺寸更小、位置偏移），
        # 因为双面款正面印花只占衣服前半部分；背面(B)和单面款用顶层五参。
        use_bw = dx.endswith("BW") and role == "W"

        # 按颜色列出素材库胚衣
        colors_to_do = []
        if only_color is None or only_color == "白":
            colors_to_do.append("白")
        if only_color is None or only_color == "黑":
            colors_to_do.append("黑")

        selected: list[tuple[dict, str]] = []  # (embryo_info, color)
        notes: list[str] = []
        for color in colors_to_do:
            pool = _list_material_embryos(role, color, use_bw=use_bw)
            if not pool:
                notes.append(f"{color}T 跳过：素材库无可用 {role}{color} 胚衣（或 meta.json 缺失/损坏）")
                continue
            # 每色出 2 张：固定平铺胚衣 1 张 + 随机模特胚衣 1 张
            mandatory = naming.FLAT_MANDATORY.get((role, color))
            fixed = [e for e in pool if e["stem"] == mandatory]
            models = [e for e in pool if not naming.is_flat_stem(e["stem"])]
            if fixed:
                selected.append((fixed[0], color))
            else:
                notes.append(f"{color}T 平铺胚衣 {mandatory} 不可用（meta 缺失/损坏），仅出模特图")
            if models:
                selected.append((random.choice(models), color))
            if not fixed and not models:
                notes.append(f"{color}T 跳过：无可用胚衣")

        if not selected:
            return [], [f"无可用 {role} 模特图胚衣（素材库白/黑候选均为空或 meta.json 缺失）"]

        up_dir.mkdir(parents=True, exist_ok=True)

        jobs: list[dict] = []
        for embryo, color in selected:
            stem = embryo["stem"]
            meta = embryo["meta"]
            # 平铺胚衣 → 平铺命名；其余胚衣 → 模特命名（规则见 wb_naming）
            if naming.is_flat_stem(stem):
                out = up_dir / naming.flat_name(dx, role, color)
            else:
                out = up_dir / naming.model_name(dx, role, color)

            # ---- 基础参数：五参定位（所有款通用）----
            argv = [
                str(cut), str(out),
                "--template", str(embryo["path"]),
                "--final-w", str(meta["final_w"]),
                "--final-h", str(meta["final_h"]),
                "--rotate", str(meta["rotation"]),
                "--effective-top-y", str(meta["effective_top_y"]),
                "--effective-center-x", str(meta["effective_center_x"]),
            ]
            is_flat = naming.is_flat_stem(stem)
            if (not is_flat) and color == "黑":
                # ★ 黑T 直贴模式（用户 2026-07-15 最终敲定）：
                # 不分析褶皱、不改动任何颜色/明暗，仅按五参定位原色 Normal 贴 + 手部遮挡。
                # 对应 white_t_mockup 的 --black-t-plain（关闭 tpl_dir/disp/occlusion/
                # fabric_shading/shadow/highlight 全部布料分析，只保留手部 occluder）。
                argv += ["--black-t-plain"]
                if embryo["occluder"]:
                    argv += ["--occluder", embryo["occluder"]]
            else:
                # 白/黑平铺/白黑模特（非黑T直贴）：保色平贴 + 几何位移 + 布料光影关闭
                argv += [
                    # 位移：v2.4 改为平贴（disp-strength=0）。用户实测发现位移 90 会把
                    # T恤褶皱折痕"印"到图案上（白模特出现亮斑、黑平铺出现暗斑）；
                    # 改为 0 后图案平整干净，深褶隐藏改由 occlusion 几何实现（不靠位移）。
                    "--disp-mode", "gradient",
                    "--disp-strength", "0",
                    "--disp-smooth", "40",
                    "--disp-dead-zone", "15",
                    "--shading-blur", "4",
                    # 关闭布料光影（fabric_shading）：用户实测开启时会把 T恤褶皱的明暗
                    # 直接画到贴图上（白模特亮斑、黑平铺暗斑）。关掉后图案干净、颜色与
                    # 源文件一致；深褶隐藏由 occlusion 几何实现，不依赖阴影。
                    "--no-fabric-shading",
                ]
                if embryo["tpl_dir"]:
                    argv += ["--tpl-dir", embryo["tpl_dir"]]
                # 白/黑模特图统一保色：不做 multiply/阴影/高光/降饱和，贴图颜色与源文件一致，
                # 褶皱立体感完全由 displacement + occlusion 几何实现。
                argv += ["--preserve-color"]
                # 告诉贴图引擎目标布料色，使保色模式下能按白/黑做去预乘去光晕，
                # 消除黑底/白底 PNG 边缘偏色导致的泛白/泛黑问题。
                shirt_color_arg = "white" if color == "白" else "black"
                argv += ["--shirt-color", shirt_color_arg]
                if embryo["occluder"]:
                    argv += ["--occluder", embryo["occluder"]]
                # 白模特/平铺一律 0.0 遮挡，避免遮挡把褶皱折痕"印"到图案上形成暗斑/亮斑。
                argv += ["--occlusion-strength", "0.0"]

            # tag 带 dx 前缀，保证整批跨款唯一（同款同色同胚衣会撞名）
            tag = f"{dx}|{role}/{color}T/{stem}"
            jobs.append({"dx": dx, "tag": tag, "out": str(out), "argv": argv})

        return jobs, notes
    except Exception as e:
        return [], [f"{role} 模特图贴图计划异常: {e}"]


def run_mockup_jobs(jobs: list[dict], max_workers: int = 3) -> list[tuple[dict, bool, str]]:
    """把贴图任务切成 max_workers 份，起等量个 ``white_t_mockup --batch`` 常驻进程并行执行。

    每个 worker 单进程顺序跑完自己那份（解释器启动/import/胚衣素材缓存只付一次，
    替代旧版"每张图一个进程"）；返回 [(job, ok, err), ...]，顺序与 jobs 对齐。
    """
    import os
    import shutil
    import subprocess
    import tempfile

    if not jobs:
        return []
    # 每 worker 启动约 1s（import 等），小批量并行不划算：约每 4 张才加 1 个 worker
    workers = max(1, min(max_workers, max(1, len(jobs) // 4), max(1, (os.cpu_count() or 4) // 2)))
    chunks = [jobs[i::workers] for i in range(workers)]
    tmpdir = Path(tempfile.mkdtemp(prefix="wmock_batch_"))
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE：最小化不抢焦点
    procs = []
    try:
        for i, chunk in enumerate(chunks):
            jf = tmpdir / f"jobs_{i}.json"
            jf.write_text(json.dumps({"jobs": chunk}, ensure_ascii=False), encoding="utf-8")
            p = subprocess.Popen(
                [str(W_MOCKUP_PY), "-m", "white_t_mockup", "--batch", str(jf)],
                cwd=str(W_MOCKUP_ROOT),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                startupinfo=startupinfo)
            procs.append((i, jf, p))
        by_tag: dict[str, tuple[bool, str]] = {}
        for i, jf, p in procs:
            out, _ = p.communicate()
            rf = Path(str(jf) + ".result.json")
            if rf.exists():
                for r in json.loads(rf.read_text(encoding="utf-8")):
                    by_tag[r["tag"]] = (bool(r.get("ok")), r.get("error", ""))
            else:  # worker 整体失败（没产出结果文件）：该份全部记失败
                tail = (out or "")[-400:]
                for job in chunks[i]:
                    by_tag[job["tag"]] = (False, tail)
            if p.returncode != 0:
                print(f"[批量贴图] worker{i} 退出码 {p.returncode}", flush=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return [(job, *by_tag.get(job["tag"], (False, "无结果"))) for job in jobs]


def generate_single_side_mockup(
    dx: str,
    base_dir: Path,
    role: str,
    runner,
    cut_path: str | Path | None = None,
    only_color: str | None = None,
) -> tuple[bool, str]:
    """用素材库胚衣为单面款出模特图贴图（签名/返回与旧版一致，内部改为批量执行：
    该款全部图由一个 white_t_mockup --batch 进程一次跑完，不再逐张起进程）。
    runner 参数保留仅为兼容旧调用，批量执行统一走 run_mockup_jobs。"""
    jobs, notes = plan_single_side_jobs(dx, base_dir, role, cut_path=cut_path, only_color=only_color)
    if not jobs:
        return False, "; ".join(notes) or f"无可用 {role} 模特图胚衣"
    texts = []
    ok = False
    for job, jok, err in run_mockup_jobs(jobs, max_workers=1):
        stag = job["tag"].split("|", 1)[-1]
        if jok:
            ok = True
            texts.append(f"{stag} 完成: {Path(job['out']).name}")
        else:
            texts.append(f"{stag} 失败: {err}")
    return ok, "; ".join(notes + texts)
