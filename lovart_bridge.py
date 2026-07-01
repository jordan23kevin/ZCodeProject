#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lovart-WB Bridge Server v1.0
============================
Flask HTTP 桥接服务 — 连接 HTML 控制面板与本地 Lovart 管线 + 文件系统

架构: HTML ←HTTP/JSON→ Flask Bridge ←subprocess→ Lovart-official pipeline
                                    ←文件IO→   INBOX / DX 目录 / Registry

启动: python lovart_bridge.py  →  http://127.0.0.1:8765
"""

import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
import threading
import re
import io
import ctypes
from ctypes import wintypes
from pathlib import Path
from datetime import datetime

try:
    from flask import Flask, jsonify, request, send_file, abort
except ImportError:
    print("ERROR: Flask not installed. Run: pip install flask")
    sys.exit(1)

# ============================================================================
# 路径常量
# ============================================================================
BASE_DIR       = Path("D:/Semems WB")
INBOX_DIR      = BASE_DIR / "01_INBOX"
PROJECTS_DIR   = BASE_DIR / "02_PROJECTS"
REGISTRY_FILE  = BASE_DIR / ".image_registry.json"
LOVART_DIR     = Path("E:/Claude code/lovart-official")
LOVART_SCRIPT  = LOVART_DIR / "run_official_v53.py"

PYTHON_EXE     = r"C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe"
PYTHONPATH     = "E:/python_packages"

EXCLUDE_DIR    = "_bridge_exclude"   # 暂存未选中文件的子目录名
HOVER_CACHE    = INBOX_DIR / "_hover_cache"  # 悬停预览缩略图缓存

# ============================================================================
# Flask App
# ============================================================================
app = Flask(__name__, static_folder=None)

# ============================================================================
# 全局任务状态（持久化到磁盘，重启桥接后仍可见）
# ============================================================================
STATE_FILE = BASE_DIR / ".last_task_state.json"

task_state = {
    "status": "idle",            # idle | running | completed | error | cancelled
    "progress": "",
    "started_at": None,
    "completed_at": None,
    "log": [],
    "selected_files": [],
    "groups_processed": 0,
    "groups_total": 0,
    "task_id": None,
}


def _save_state():
    """将当前 task_state 持久化到磁盘"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(task_state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_state():
    """从磁盘恢复上次的 task_state"""
    global task_state
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # 只恢复 completed / error 状态（不恢复 running，因为进程已不在）
            if saved.get("status") in ("completed", "error", "idle"):
                task_state = saved
        except Exception:
            pass


_lock = threading.Lock()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def log(msg: str):
    """向任务日志追加一条带时间戳的消息"""
    ts = datetime.now().strftime("%H:%M:%S")
    task_state["log"].append(f"[{ts}] {msg}")


def get_python() -> str:
    """返回可用的 Python 可执行路径"""
    if os.path.exists(PYTHON_EXE):
        return PYTHON_EXE
    return "python"


# ---------------------------------------------------------------------------
# Registry 操作
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """加载 .image_registry.json，不存在则返回空骨架"""
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"version": 3, "images": {}, "groups": {}, "uid_index": {}, "name_index": {}}
    return {"version": 3, "images": {}, "groups": {}, "uid_index": {}, "name_index": {}}


def save_registry(reg: dict):
    """原子写入 registry（先写 .tmp 再 rename，防止写半截）"""
    tmp = REGISTRY_FILE.with_suffix(".json.tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    tmp.replace(REGISTRY_FILE)


def ensure_registry_v3(reg: dict) -> dict:
    """确保 registry 结构包含 v3 字段"""
    if reg.get("version", 1) < 3:
        reg.setdefault("groups", {})
        reg.setdefault("uid_index", {})
        reg.setdefault("name_index", {})
        reg["version"] = 3
    else:
        reg.setdefault("groups", {})
        reg.setdefault("uid_index", {})
        reg.setdefault("name_index", {})
    return reg


def compute_md5(filepath: str) -> str:
    """计算文件的 MD5 哈希"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_next_uid(reg: dict) -> str:
    """生成下一个 UID: DX{YYYYMMDD}_{NNNN}，每日从 0001 开始"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"DX{today}_"
    max_seq = 0
    for uid in reg.get("uid_index", {}):
        if uid.startswith(prefix):
            try:
                seq = int(uid.rsplit("_", 1)[-1])
                max_seq = max(max_seq, seq)
            except (ValueError, IndexError):
                pass
    return f"{prefix}{max_seq + 1:04d}"


def get_next_group_id(reg: dict) -> str:
    """生成下一个 group_id: G_{NNNNN}"""
    max_num = 0
    for gid in reg.get("groups", {}):
        if gid.startswith("G_"):
            try:
                num = int(gid.split("_", 1)[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"G_{max_num + 1:05d}"


# ---------------------------------------------------------------------------
# 文件名自动大写（b→B, w→W）
# ---------------------------------------------------------------------------

def auto_uppercase_inbox():
    """将 INBOX 中后缀为小写 b/w 的文件名改为大写，如 17b.png → 17B.png。
    Windows NTFS 保留大小写但查找不区分大小写，直接 rename 即可。
    """
    if not INBOX_DIR.exists():
        return 0
    count = 0
    # 匹配: 数字 + B/W/BW/WB + .png (不区分大小写)
    pattern = re.compile(r'^(\d+)([bw]+)(\.png)$', re.IGNORECASE)
    for fname in list(os.listdir(INBOX_DIR)):
        if fname.startswith('_'):
            continue
        m = pattern.match(fname)
        if not m:
            continue
        num = m.group(1)
        suffix = m.group(2)
        ext = m.group(3)
        upper = suffix.upper()
        if suffix == upper:
            continue  # 已是大写
        new_name = f"{num}{upper}{ext}"
        src = INBOX_DIR / fname
        dst = INBOX_DIR / new_name
        # Windows: 同一文件，直接 rename 改变显示大小写
        src.rename(dst)
        count += 1
        print(f"  [AutoUppercase] {fname} → {new_name}")
    return count


# ---------------------------------------------------------------------------
# 悬停预览缩略图（500px 缓存）
# ---------------------------------------------------------------------------

def get_hover_thumb(filename: str) -> Path:
    """生成或返回 500px 宽度的预览缓存图"""
    from PIL import Image
    safe = os.path.basename(filename)
    src = INBOX_DIR / safe
    if not src.exists():
        return None
    HOVER_CACHE.mkdir(parents=True, exist_ok=True)
    thumb_file = HOVER_CACHE / f"{safe}_500.jpg"
    # 缓存有效：源文件未修改
    if thumb_file.exists() and thumb_file.stat().st_mtime >= src.stat().st_mtime:
        return thumb_file
    try:
        img = Image.open(src).convert("RGBA")
        # 白底合成（透明背景看不清楚）
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        rgb = bg.convert("RGB")
        # 缩放到最长边 500px
        w, h = rgb.size
        if w > h:
            new_w = 500
            new_h = int(h * 500 / w)
        else:
            new_h = 500
            new_w = int(w * 500 / h)
        rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
        rgb.save(str(thumb_file), "JPEG", quality=90)
        return thumb_file
    except Exception as e:
        print(f"  [HoverThumbError] {filename}: {e}")
        return None


# ---------------------------------------------------------------------------
# 本地回收站：删除到 01_INBOX/回收站/，清空时才送入系统回收站
# ---------------------------------------------------------------------------

TRASH_DIR = INBOX_DIR / "回收站"

FO_DELETE = 3
FOF_ALLOWUNDO = 0x40
FOF_NOCONFIRMATION = 0x10

class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_int),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def move_to_trash(filename: str) -> bool:
    """将 INBOX 中的文件移到本地 回收站 目录"""
    safe = os.path.basename(filename)
    src = INBOX_DIR / safe
    if not src.exists():
        return False
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    dst = TRASH_DIR / safe
    # 防重名
    if dst.exists():
        stem, ext = os.path.splitext(safe)
        dst = TRASH_DIR / f"{stem}_{int(time.time())}{ext}"
    shutil.move(str(src), str(dst))
    # 清理 hover 缓存
    for f in (INBOX_DIR / "_hover_cache").glob(f"{safe}*"):
        try: f.unlink()
        except: pass
    return True


def empty_trash_to_system_recycle() -> int:
    """将本地回收站里的所有文件送入系统回收站。返回处理数量。"""
    if not TRASH_DIR.exists():
        return 0
    count = 0
    for f in list(TRASH_DIR.iterdir()):
        if not f.is_file():
            continue
        try:
            # 使用 Windows Shell API 送系统回收站
            fileop = SHFILEOPSTRUCTW()
            fileop.hwnd = 0
            fileop.wFunc = FO_DELETE
            fileop.pFrom = str(f) + "\0"
            fileop.pTo = None
            fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION
            if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop)) == 0:
                count += 1
            else:
                # 回退：直接删除
                f.unlink()
                count += 1
        except Exception:
            try: f.unlink()
            except: pass
            count += 1
    return count


# ---------------------------------------------------------------------------
# INBOX 重命名：B/W → BW（如 2B.png → 2BW.png）
# ---------------------------------------------------------------------------

def rename_to_bw(filename: str) -> tuple:
    """将 B 或 W 文件改名为 BW。
    返回 (ok, new_name, msg)
    """
    safe = os.path.basename(filename)
    m = re.match(r'^(\d+)([BW])(\.png)$', safe, re.IGNORECASE)
    if not m:
        return False, "", f"{safe} 不符合格式（需为 数字+B/W+.png）"
    num = m.group(1)
    suffix = m.group(2).upper()
    if suffix not in ("B", "W"):
        return False, "", f"{safe} 已是 BW 或 WB 格式"
    new_name = f"{num}BW.png"
    src = INBOX_DIR / safe
    dst = INBOX_DIR / new_name
    if dst.exists():
        return False, "", f"{new_name} 已存在"
    src.rename(dst)
    return True, new_name, f"{safe} → {new_name}"


# ---------------------------------------------------------------------------
# INBOX 分组逻辑
# ---------------------------------------------------------------------------

def group_inbox_files() -> list:
    """
    将 INBOX 中的 .png 按数字编号分组。
    例如: 1B.png + 1W.png → group "1"
          13BW.png        → group "13"
    返回: [{"group_number": int, "images": [...], "count": int, "types": [...]}, ...]
    """
    if not INBOX_DIR.exists():
        return []

    files = [f for f in os.listdir(INBOX_DIR)
             if f.endswith('.png') and not f.startswith('_')]

    groups = {}
    pattern = re.compile(r'^(\d+)(B|W|BW|WB)\.png$', re.IGNORECASE)
    for fname in files:
        m = pattern.match(fname)
        if not m:
            continue
        num = m.group(1)
        suffix = m.group(2).upper()
        fp = INBOX_DIR / fname
        groups.setdefault(num, []).append({
            "filename": fname,
            "suffix": suffix,
            "size": fp.stat().st_size if fp.exists() else 0,
        })

    sorted_groups = []
    for num in sorted(groups, key=lambda x: int(x)):
        images = groups[num]
        sorted_groups.append({
            "group_number": int(num),
            "images": images,
            "count": len(images),
            "types": [img["suffix"] for img in images],
        })
    return sorted_groups


# ============================================================================
# API 路由
# ============================================================================

@app.route('/')
def index():
    """提供 HTML 控制面板"""
    html_file = Path(__file__).parent / "lovart_control.html"
    if html_file.exists():
        return send_file(str(html_file))
    return "<h1>lovart_control.html not found</h1><p>请确保 lovart_control.html 与 bridge.py 在同一目录</p>", 404


@app.route('/api/inbox')
def api_inbox():
    """返回 INBOX 所有图片及分组信息"""
    if not INBOX_DIR.exists():
        return jsonify({"images": [], "groups": [], "total": 0})

    all_files = []
    for fname in os.listdir(INBOX_DIR):
        if not fname.endswith('.png') or fname.startswith('_'):
            continue
        fp = INBOX_DIR / fname
        try:
            st = fp.stat()
            all_files.append({
                "filename": fname,
                "size": st.st_size,
                "preview_url": f"/api/preview/{fname}",
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            })
        except OSError:
            continue

    groups = group_inbox_files()
    return jsonify({"images": all_files, "groups": groups, "total": len(all_files)})


@app.route('/api/preview/<path:filename>')
def api_preview(filename):
    """返回原图（由前端 CSS 控制显示大小）"""
    safe_name = os.path.basename(filename)
    filepath = INBOX_DIR / safe_name
    if not filepath.exists():
        abort(404)
    try:
        return send_file(str(filepath), mimetype='image/png', max_age=3600)
    except Exception:
        abort(404)


@app.route('/api/hover/<path:filename>')
def api_hover(filename):
    """返回 500px 悬停预览图（JPEG 白底）"""
    safe_name = os.path.basename(filename)
    thumb = get_hover_thumb(safe_name)
    if not thumb:
        abort(404)
    return send_file(str(thumb), mimetype='image/jpeg', max_age=3600)


@app.route('/api/inbox/group')
def api_inbox_group():
    """仅返回分组信息（前端页面可用来刷新分组）"""
    groups = group_inbox_files()
    return jsonify({"groups": groups, "total_groups": len(groups)})


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """启动 Lovart 生图任务"""
    global task_state

    with _lock:
        if task_state["status"] == "running":
            return jsonify({"error": "已有生图任务正在运行，请等待完成"}), 409

        data = request.get_json(silent=True) or {}
        selected = data.get("selected", [])

        if not selected:
            return jsonify({"error": "请至少选择一张图片"}), 400

        missing = [f for f in selected if not (INBOX_DIR / f).exists()]
        if missing:
            return jsonify({"error": f"以下文件不存在: {', '.join(missing)}"}), 400

        task_id = f"TASK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_state = {
            "status": "starting",
            "progress": "初始化中...",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "log": [],
            "selected_files": selected,
            "groups_processed": 0,
            "groups_total": 0,
            "task_id": task_id,
        }
        _save_state()

    # 后台线程执行
    t = threading.Thread(target=_run_generation, args=(selected, task_id), daemon=True)
    t.start()

    return jsonify({
        "status": "started",
        "task_id": task_id,
        "message": f"已启动生图任务，处理 {len(selected)} 张图片",
    })


@app.route('/api/status')
def api_status():
    """返回当前任务状态"""
    resp = jsonify(task_state)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route('/api/projects')
def api_projects():
    """列出最近 DX 项目及关联的 group 信息"""
    reg = load_registry()
    projects = []
    seen = set()
    dx_pattern = re.compile(r'^DX\d+_')

    if PROJECTS_DIR.exists():
        for d in sorted(os.listdir(PROJECTS_DIR), reverse=True):
            if not d.startswith('DX') or d in seen:
                continue
            seen.add(d)

            ai_dir = PROJECTS_DIR / d / "01_AI"
            rem_dir = PROJECTS_DIR / d / "02_REM_BG"
            up_dir  = PROJECTS_DIR / d / "03_UPLOAD"

            if not ai_dir.exists():
                continue

            # 所有文件
            all_ai = sorted([f for f in os.listdir(ai_dir) if f.endswith('.png')])
            # AI 生成的文件（DX{N}_*.png）
            ai_gen = sorted([f for f in all_ai if dx_pattern.match(f)])
            # 去背文件
            rem_files = sorted([f for f in os.listdir(rem_dir) if f.endswith(('.png','.jpg','.jpeg'))]) if rem_dir.exists() else []
            # 贴图文件（多为 jpg）
            up_files = sorted([f for f in os.listdir(up_dir) if f.endswith(('.png','.jpg','.jpeg'))]) if up_dir.exists() else []

            sm_path = PROJECTS_DIR / d / "source_map.json"
            source_map = {}
            if sm_path.exists():
                try:
                    with open(sm_path, 'r', encoding='utf-8') as f:
                        source_map = json.load(f)
                except Exception:
                    pass

            # 款号一致性检查：文件夹名 vs AI vs 去背 vs 贴图
            inconsistent = False
            incons_reason = []
            bad_files = []  # 记录不一致的文件名，用于前端高亮
            # 检查 AI 文件
            for f in ai_gen:
                if not f.startswith(f"{d}_"):
                    inconsistent = True
                    bad_files.append(f)
                    incons_reason.append(f"AI文件 {f}")
            # 检查去背文件
            for f in rem_files:
                stem = f.rsplit('.', 1)[0]
                base = stem.replace('_cut', '')
                if not base.startswith(f"{d}_"):
                    inconsistent = True
                    bad_files.append(f)
                    incons_reason.append(f"去背文件 {f}")
            # 检查贴图文件
            for f in up_files:
                if not f.startswith(f"{d}_"):
                    inconsistent = True
                    bad_files.append(f)
                    incons_reason.append(f"贴图文件 {f}")

            projects.append({
                "dx_id": d,
                "file_count": len(all_ai),
                "files": all_ai,
                "ai_gen": ai_gen,
                "rem_files": rem_files,
                "up_files": up_files,
                "has_rembg": len(rem_files) > 0,
                "has_upload": len(up_files) > 0,
                "inconsistent": inconsistent,
                "bad_files": bad_files,
                "incons_reason": "; ".join(incons_reason[:3]) + (f" 等{len(incons_reason)}处" if len(incons_reason) > 3 else ""),
                "source_map": source_map,
                "modified": datetime.fromtimestamp(ai_dir.stat().st_mtime).isoformat(),
            })

    # 关联 group 信息
    group_info = {}
    for gid, ginfo in reg.get("groups", {}).items():
        dx = ginfo.get("dx_folder", "")
        if dx:
            group_info[dx] = {
                "group_id": gid,
                "created": ginfo.get("created", ""),
                "status": ginfo.get("status", ""),
                "images": ginfo.get("images", []),
            }

    # 不一致的排最前面，其余按时间降序
    projects.sort(key=lambda p: (0 if p["inconsistent"] else 1, p["modified"]), reverse=False)
    # 修正倒序：不一致在前，一致的部分内部再按时间倒序
    incons = [p for p in projects if p["inconsistent"]]
    consist = sorted([p for p in projects if not p["inconsistent"]], key=lambda p: p["modified"], reverse=True)
    projects = incons + consist

    return jsonify({
        "projects": projects[:100],   # 最近 100 个
        "group_info": group_info,
        "total": len(projects),
    })


@app.route('/api/open/<path:folder>')
def api_open_folder(folder):
    """在文件管理器中打开指定文件夹"""
    # 支持: DX0001, DX0001/01_AI, DX0001/02_REM_BG, DX0001/03_UPLOAD, INBOX
    parts = folder.replace('\\', '/').split('/')
    first = parts[0]
    if first.startswith('DX'):
        target = PROJECTS_DIR / first
        if len(parts) > 1:
            sub = parts[1]
            if sub in ('01_AI', '02_REM_BG', '03_UPLOAD'):
                target = target / sub
    elif first == 'INBOX':
        target = INBOX_DIR
        if len(parts) > 1:
            target = target / parts[1]
    else:
        abort(404)
    if not target.exists():
        abort(404)
    try:
        subprocess.Popen(["explorer.exe", str(target)])
        return jsonify({"ok": True, "path": str(target)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/delete', methods=['POST'])
def api_delete():
    """将指定文件移到本地 回收站 目录"""
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "")
    safe = os.path.basename(filename)
    filepath = INBOX_DIR / safe
    if not filepath.exists():
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    ok = move_to_trash(safe)
    if ok:
        return jsonify({"ok": True, "msg": f"{safe} 已移到本地回收站"})
    else:
        return jsonify({"ok": False, "error": "删除失败"}), 500


@app.route('/api/empty-trash', methods=['POST'])
def api_empty_trash():
    """将本地回收站里的文件全部送入系统回收站"""
    count = empty_trash_to_system_recycle()
    return jsonify({"ok": True, "count": count, "msg": f"已清空 {count} 个文件到系统回收站"})


@app.route('/api/trash')
def api_trash():
    """列出本地回收站中的文件，按编号分组（同 INBOX 风格）"""
    files = []
    if TRASH_DIR.exists():
        for f in sorted(TRASH_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix.lower() == '.png':
                files.append({
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "preview_url": f"/api/preview-trash/{f.name}",
                })
    # 分组（同 INBOX 逻辑）
    groups = {}
    pattern = re.compile(r'^(\d+)(B|W|BW|WB)(\.png)$', re.IGNORECASE)
    others = []
    for img in files:
        m = pattern.match(img["filename"])
        if m:
            num = m.group(1)
            suffix = m.group(2).upper()
            groups.setdefault(num, []).append({
                "filename": img["filename"],
                "suffix": suffix,
                "size": img["size"],
                "preview_url": img["preview_url"],
            })
        else:
            others.append(img)
    sorted_groups = []
    for num in sorted(groups, key=lambda x: int(x)):
        imgs = groups[num]
        sorted_groups.append({
            "group_number": int(num),
            "images": imgs,
            "count": len(imgs),
            "types": list(set(img["suffix"] for img in imgs)),
        })
    return jsonify({
        "files": files,
        "groups": sorted_groups,
        "others": others,
        "count": len(files),
    })


@app.route('/api/preview-trash/<path:filename>')
def api_preview_trash(filename):
    """返回回收站中的文件预览"""
    safe = os.path.basename(filename)
    filepath = TRASH_DIR / safe
    if not filepath.exists():
        abort(404)
    try:
        return send_file(str(filepath), mimetype='image/png', max_age=3600)
    except Exception:
        abort(404)


@app.route('/api/restore', methods=['POST'])
def api_restore():
    """从本地回收站恢复文件到 INBOX"""
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "")
    safe = os.path.basename(filename)
    src = TRASH_DIR / safe
    if not src.exists():
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    dst = INBOX_DIR / safe
    if dst.exists():
        # 重名处理：加时间戳
        stem, ext = os.path.splitext(safe)
        dst = INBOX_DIR / f"{stem}_restored{ext}"
    shutil.move(str(src), str(dst))
    return jsonify({"ok": True, "msg": f"{safe} 已恢复到 INBOX"})


@app.route('/api/open/recycle')
def api_open_recycle():
    """打开本地回收站目录"""
    try:
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(TRASH_DIR)])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rename', methods=['POST'])
def api_rename():
    """将 B/W 图片改名为 BW（如 2B.png → 2BW.png）"""
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "")
    ok, new_name, msg = rename_to_bw(filename)
    if ok:
        return jsonify({"ok": True, "new_name": new_name, "msg": msg})
    else:
        return jsonify({"ok": False, "error": msg}), 400


@app.route('/api/registry/query')
def api_registry_query():
    """查询注册表中单张图片的信息（支持文件名 / UID / MD5）"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "请提供查询参数 ?q=filename_or_uid"}), 400

    reg = load_registry()
    results = []

    # 按 name_index 查找
    md5_by_name = reg.get("name_index", {}).get(q)
    if md5_by_name and md5_by_name in reg.get("images", {}):
        results.append(reg["images"][md5_by_name])

    # 按 uid_index 查找
    md5_by_uid = reg.get("uid_index", {}).get(q)
    if md5_by_uid and md5_by_uid in reg.get("images", {}) and reg["images"][md5_by_uid] not in results:
        results.append(reg["images"][md5_by_uid])

    # 按 MD5 直接查找
    if q in reg.get("images", {}):
        if reg["images"][q] not in results:
            results.append(reg["images"][q])

    return jsonify({"query": q, "results": results, "count": len(results)})


# ============================================================================
# 后台生图任务
# ============================================================================

def _run_generation(selected_files: list, task_id: str):
    """后台执行 Lovart 管线"""
    global task_state
    start_ts = datetime.now()

    reg = load_registry()
    reg = ensure_registry_v3(reg)

    try:
        log(f"▶ 任务 {task_id} 开始")
        log(f"选中文件: {', '.join(selected_files)}")

        # ── 1. 分配 UID / group_id ──────────────────────────────
        selected_set = set(selected_files)
        inbox_groups = group_inbox_files()

        uid_map = {}       # filename → uid
        group_map = {}     # group_number → group_id
        matched = [g for g in inbox_groups
                   if any(f["filename"] in selected_set for f in g["images"])]

        task_state["groups_total"] = len(matched)
        log(f"识别到 {len(matched)} 个图片组")

        for g in matched:
            gid = get_next_group_id(reg)
            group_map[g["group_number"]] = gid

            reg["groups"][gid] = {
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "images": [],
                "source_files": [],
                "dx_folder": "",
                "status": "pending",
            }

            for img in g["images"]:
                fname = img["filename"]
                if fname not in selected_set:
                    continue

                uid = get_next_uid(reg)
                uid_map[fname] = uid
                md5_val = compute_md5(str(INBOX_DIR / fname))

                entry = {
                    "md5": md5_val,
                    "src_id": "",
                    "design_number": g["group_number"],
                    "role": img["suffix"],
                    "original_name": fname,
                    "current_name": fname,
                    "current_path": f"01_INBOX/{fname}",
                    "paired_with": "",
                    "paired_name": "",
                    "cut_path": "",
                    "uid": uid,
                    "group_id": gid,
                    "inbox_original_name": fname,
                    "events": [{
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "event": "bridge_generate_start",
                        "detail": f"UID={uid}, group={gid}",
                    }],
                }

                reg["images"][md5_val] = entry
                reg["uid_index"][uid] = md5_val
                reg["name_index"][fname] = md5_val
                reg["groups"][gid]["images"].append(uid)
                reg["groups"][gid]["source_files"].append(fname)

        save_registry(reg)
        log(f"已分配 {len(uid_map)} 个 UID，{len(group_map)} 个 group_id")

        # ── 2. 暂存未选中的文件 ─────────────────────────────────
        task_state["progress"] = "暂存未选中的文件..."
        temp_dir = INBOX_DIR / EXCLUDE_DIR
        temp_dir.mkdir(exist_ok=True)

        moved = 0
        for fname in list(os.listdir(INBOX_DIR)):
            if not fname.endswith('.png') or fname.startswith('_'):
                continue
            if fname not in selected_set:
                shutil.move(str(INBOX_DIR / fname), str(temp_dir / fname))
                moved += 1
        log(f"暂存了 {moved} 个未选中文件")

        # ── 3. 运行 Lovart 管线 ─────────────────────────────────
        task_state["status"] = "running"
        task_state["progress"] = "正在运行 Lovart 生图管线..."
        log("启动 Lovart 管线...")
        _save_state()

        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH
        env["LOVART_INSECURE_SSL"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.Popen(
            [get_python(), "run_official_v53.py"],
            cwd=str(LOVART_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            env=env,
        )

        # 逐行读取输出，更新进度
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # 提取关键信息更新进度
            lower = line.lower()
            if any(kw in lower for kw in ("generating", "生成", "processing", "处理",
                                          "complete", "完成", "done", "成功",
                                          "error", "错误", "fail", "失败",
                                          "upload", "上传", "download", "下载",
                                          "group", "组", "register", "注册")):
                log(line[:300])
                task_state["progress"] = line[:200]

        proc.wait()

        # ── 4. 恢复暂存文件 ─────────────────────────────────────
        task_state["progress"] = "恢复暂存文件..."
        log("恢复未选中文件到 INBOX...")

        if temp_dir.exists():
            for fname in list(os.listdir(temp_dir)):
                shutil.move(str(temp_dir / fname), str(INBOX_DIR / fname))
            try:
                temp_dir.rmdir()
            except OSError:
                pass

        # ── 5. 更新 registry ────────────────────────────────────
        log("更新注册表...")
        reg = load_registry()
        reg = ensure_registry_v3(reg)

        # 扫描 Lovart 生成的 DX 文件夹，关联 group 信息
        if PROJECTS_DIR.exists():
            # 找生成时间之后创建/修改的 DX 文件夹
            cutoff = start_ts.timestamp()
            for d in sorted(os.listdir(PROJECTS_DIR)):
                if not d.startswith('DX'):
                    continue
                ai_dir = PROJECTS_DIR / d / "01_AI"
                if not ai_dir.exists():
                    continue

                # 检查是否是本次生成的
                dir_mtime = ai_dir.stat().st_mtime
                if dir_mtime < cutoff:
                    continue

                sm_path = PROJECTS_DIR / d / "source_map.json"
                if not sm_path.exists():
                    continue

                try:
                    with open(sm_path, 'r', encoding='utf-8') as f:
                        sm = json.load(f)
                except Exception:
                    continue

                # 通过 source_map 中的 src_id 关联回我们的 registry
                for src in sm.get("sources", []):
                    src_id = src.get("src_id", "")
                    role = src.get("role", "")
                    target_file = src.get("file", "")

                    # 尝试查找匹配的 group
                    for md5_key, img_info in reg.get("images", {}).items():
                        if img_info.get("role") == role and \
                           img_info.get("group_id") in group_map.values():
                            # 更新路径
                            img_info["current_name"] = target_file
                            img_info["current_path"] = f"02_PROJECTS/{d}/01_AI/{target_file}"
                            img_info["src_id"] = src_id
                            img_info["events"].append({
                                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "event": "bridge_generate_complete",
                                "detail": f"输出到 {d}/01_AI/{target_file}",
                            })
                            # 更新对应的 group
                            gid = img_info.get("group_id")
                            if gid in reg.get("groups", {}):
                                reg["groups"][gid]["dx_folder"] = d
                                reg["groups"][gid]["status"] = "generated"
                            break

        save_registry(reg)
        log("注册表更新完成")

        # ── 6. 完成 ─────────────────────────────────────────────
        task_state["status"] = "completed"
        task_state["completed_at"] = datetime.now().isoformat()
        task_state["progress"] = f"完成！处理 {len(matched)} 组 / {len(uid_map)} 张"
        if proc.returncode != 0:
            task_state["progress"] += f" (管线退出码: {proc.returncode})"
        log(f"✔ 任务 {task_id} 完成 ({len(uid_map)} 张, {len(matched)} 组)")
        _save_state()

    except Exception as e:
        task_state["status"] = "error"
        task_state["progress"] = f"错误: {str(e)}"
        log(f"✘ 错误: {str(e)}")
        _save_state()
        import traceback
        log(traceback.format_exc()[:300])

        # 尝试恢复文件
        try:
            td = INBOX_DIR / EXCLUDE_DIR
            if td.exists():
                for fname in list(os.listdir(td)):
                    shutil.move(str(td / fname), str(INBOX_DIR / fname))
                td.rmdir()
        except Exception:
            pass


# ============================================================================
# 入口
# ============================================================================

if __name__ == '__main__':
    # 恢复上次的任务状态（如果是已完成/错误状态）
    _load_state()

    # 自动大写 INBOX 文件名后缀
    renamed = auto_uppercase_inbox()
    if renamed:
        # 重新扫描分组（更新 registry 的 name_index）
        reg = load_registry()
        reg = ensure_registry_v3(reg)
        for fname in os.listdir(INBOX_DIR):
            if fname.endswith('.png') and not fname.startswith('_'):
                reg["name_index"][fname] = ""
        save_registry(reg)

    print("╔══════════════════════════════════════════╗")
    print("║   Lovart-WB Bridge Server v1.0          ║")
    if renamed:
        print(f"║   AutoUppercase: {renamed} files          ║")
    print("║                                         ║")
    print(f"║   INBOX:   {INBOX_DIR}")
    print(f"║   Output:  {PROJECTS_DIR}")
    print(f"║   Lovart:  {LOVART_SCRIPT}")
    print("║                                         ║")
    print("║   Open:  http://127.0.0.1:8765          ║")
    print("╚══════════════════════════════════════════╝")
    app.run(host='127.0.0.1', port=8765, debug=False)
