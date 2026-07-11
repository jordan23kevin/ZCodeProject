"""01_CHECK_REM v2.2.6 — AI图 vs 去背图 vs 贴图成品 对比预览（本地服务）

仿 01_CHECK (check_sync.py) 的网页预览，但对比的是每个 DX 款的
01_AI 生成图、02_REM_BG 去背图、03_UPLOAD 贴图成品，方便人工判断
去背质量、贴图完整度与黑T专用图优先级。

功能 v2.2.6：
  - 修复 DX0339_W 等单张去背无输出：美图保存路径未切换时，结果会落到 `_temp_rembg/save`。
    check_rem.py 现在会从 `TEMP_REMBG/{DX}/02_REM_BG`、`WB_ROOT/_temp_rembg/save`、
    `WB_ROOT/_temp_rembg/archive` 三个位置收集 `_cut.png` / `_副本.png`，并把 `_副本.png` 改名为 `_cut.png`。
  - `rembg_one_file` / `batch_rembg` 暂存时额外复制 `source_map.json` 与原始配对文件（1B.png / 1W.png 等），
    让美图 `precheck_pairs` 能正确识别 B/W 角色和配对完整性。
  - 修复 `/batch-rembg` 的 BW 过滤 bug：原实现按全局 dx_files 判断是否含 BW，导致前一个有 BW 的款会污染后续所有款，
    现在改为每个 DX 独立判断，只跳过该 DX 自己的 B/W。

功能 v2.2.5：
  - PS 贴图流程队列化：单张/批量贴图统一进入后台队列，串行执行，避免并发冲突
  - 新增 `_sticker_worker_loop` + `/sticker-status`，前端入队后轮询进度
  - 每步 PS 脚本（黑T贴图 / 通用贴图 / BW合成）增加 5 分钟超时，卡住自动终止并继续下一款
  - 前端 `batchSticker()` 改为全部入队后统一轮询，不再因单个请求挂起而中断

功能 v2.2.4：
  - 修复单张「重新去背」失效：补全缺失的 `_rembg_worker.py`，`/rembg` 端点现在能正常后台驱动美图
  - `rembg_one_file` 暂存时把同 DX 所有生成图都放入 `_temp_rembg/{DX}/01_AI`，避免美图 `precheck_pairs` 因缺少 B/W 配对而跳过
  - 只 untrack 目标图 MD5，同 DX 其他已处理图不会被重复去背

功能 v2.2.3：
  - 反相与贴图解耦：反相只生成黑版专用去背图，不再自动调用贴图流水线
  - 贴图由用户单独点击「贴图」或「批量贴图」触发

功能 v2.2.2：
  - 反相任务统一队列：单张「反相」与「批量反相」加入同一个后台队列，串行执行
  - 新增 `_invert_worker_loop` 工作线程，避免多个反相同时驱动 Photoshop 导致冲突
  - `/invert-rem` 与 `/batch-invert-rem` 改为立即返回「已加入队列」
  - `/batch-invert-result` 同时兼容单张与批量反相的进度轮询

功能 v2.2.1：
  - 启动后 1 秒后台自动预扫描，把结果 warming 到缓存，用户首次打开首页无需等待

功能 v2.2.0：
  - 新增 scan_projects 30 秒缓存，避免每次刷新首页都全量扫描，大幅提升页面加载速度
  - 刷新全部（/refresh）时清空缓存，确保立即看到最新结果

功能 v2.1.9：
  - 修复悬停放大图位置乱跳：等原图加载后用实际尺寸定位，不再按固定 900x90vh 预判

功能 v2.1.8：
  - 日期分类统一按 DX 文件夹建立日期（st_ctime），不再按 AI/去背图最后更新时间

功能 v2.1.7：
  - 日期选择下拉框样式与 WB 上款 页统一：加大 padding、圆角、字号
  - toolbar 按钮/输入框样式同步调整，视觉更协调

功能 v2.1.6：
  - 根路径 / 直接重定向到最新日期页面，移除原来的日期分类 landing 页
  - 页面顶部已存在日期选择下拉框，可直接切换日期
  - Y2 控制台点击「去背预览」后直接进入最新日期的 AI 去背 贴图 OS 页面

功能 v2.1.5：
  - 修复反相后 BW 合成图不生成的问题：_run_sticker_pipeline 现在会先清理旧的自动生成贴图/BW文件，再重新贴图+合成BW
  - 修复 _ps_batch 端点的 DX 正则表达式错误（\\d 应为 \d）
  - 反相单张图后自动全部重新贴图，包括 BW 合成图

功能 v2.1.3：
  - 新增「批量反相」按钮：勾选多款后一键反相所有 B/W/BW 去背图，生成黑版专用图
  - 批量反相后自动跑完整贴图流水线（黑T专用 → 通用贴图 → BW 合成）
  - /batch-invert-rem + /batch-invert-result 端点，支持后台执行与进度轮询

功能 v2.1：
  - UI 整体放大：卡片、缩略图、文字、按钮全部放大，提升可点击性
  - 去背缩略图完整显示（不再叠加分辨率文字），分辨率过低时按钮区显示 🔍 放大
  - 放大镜按钮固定在最后一位，不再与反相/删除/刷新按钮混排
  - 新增「反相」按钮：一键生成 黑B/黑W/黑BW 专用去背图，并自动重跑该款贴图+BW合成
  - 03_UPLOAD 成品按 BW / B / W 分组展示，一行两张缩略图，与 AI/去背图等宽
  - 黑版变体（_黑B / _黑W / _黑BW）单独展示，不占用 AI/REM 配对位
  - 悬停放大图自动避让视口底部/右边缘，避免显示不全
  - 贴图流水线：黑T优先使用黑版专用文件 → 通用文件做白T → 自动合成BW
  - PS / 命令行窗口最小化运行，不抢焦点，不影响用户操作其他窗口

功能 v2.0：
  - JavaScript 独立为 check_rem.js，彻底规避 f-string 转义地狱
  - 批量去背：勾选多款一次美图处理
  - 血缘 Hook：去背成功后自动通知 Bridge 注册血缘
  - 全选、款号一致性检查、自动修复、回收站、一键跳转等

端口 8766（避开 01_CHECK 的 8765）。
"""
__version__ = "2.2.6"
VERSION = __version__
import os, re, json, time, hashlib, ctypes, subprocess, sys, shutil, requests, io, threading, queue
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from PIL import Image, ImageOps
from ctypes import wintypes

# 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 控制台打印 emoji/生僻字时崩溃
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

# ── 文件日志：check_rem.py 启动后把 stdout/stderr 重定向到 _debug，便于排查去背失败 ──
_LOG_FILE = None
_ORIG_STDOUT = None
_ORIG_STDERR = None

def _setup_file_logging():
    """把当前进程的 stdout/stderr 同时写入 _debug/check_rem_YYYYMMDD_HHMMSS.log。
    保留原始 stdout/stderr 引用，供子进程/外部工具需要时恢复。"""
    global _LOG_FILE, _ORIG_STDOUT, _ORIG_STDERR
    log_dir = WB_ROOT / "_debug"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"check_rem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    try:
        f = open(log_path, "a", encoding="utf-8", buffering=1)
        _LOG_FILE = f
        _ORIG_STDOUT = sys.stdout
        _ORIG_STDERR = sys.stderr
        sys.stdout = f
        sys.stderr = f
        print(f"[check_rem] 日志重定向到: {log_path}", flush=True)
        return log_path
    except Exception as e:
        print(f"[check_rem] 文件日志启用失败: {e}", flush=True)
        return None

# ── UID 元数据系统 ──────────────────────────────────
try:
    sys.path.insert(0, r"D:\Semems WB\04_OS\engine")
    import wb_meta
except Exception:
    wb_meta = None

# ── 路径 ────────────────────────────────────────────
WB_ROOT   = Path(r"D:\Semems WB")
BASE      = WB_ROOT / "02_PROJECTS"
CHECK     = BASE / "01_CHECK_REM"
THUMB_DIR = CHECK / "_thumbs"
PORT      = 8766

# 美图去背脚本 / 配置 / 跟踪文件
MEITU_SCRIPT = Path(r"E:\Claude code\WB去背\去背变清晰\wb_meitu_batch.py")
MEITU_CONFIG = Path(r"E:\Claude code\WB去背\去背变清晰\config.json")
MEITU_TRACK  = WB_ROOT / ".meitu_track.json"
TEMP_REMBG   = WB_ROOT / "_temp_rembg"          # 暂存根
CONFIG_BACKUP = MEITU_CONFIG.with_suffix(".json.bak_checkrem")  # 备份

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

CHECK.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

# scan_projects 结果缓存（避免每次请求都全量扫描）
_SCAN_PROJECTS_CACHE = {"projects": None, "timestamp": 0, "lock": threading.Lock()}
_SCAN_PROJECTS_TTL = 30  # 秒

# ── 反相任务队列（单张 + 批量统一串行执行，避免并发冲突）────────────────
_INVERT_QUEUE = queue.Queue()
_INVERT_WORKER_THREAD = None
_INVERT_STATUS_LOCK = threading.Lock()
_INVERT_STATUS = {
    "running": False,
    "current": None,
    "pending": 0,
    "completed_total": 0,
    "last_result": None,
    "last_error": None,
}


def _ensure_invert_worker():
    """启动反相后台工作线程（幂等）。"""
    global _INVERT_WORKER_THREAD
    if _INVERT_WORKER_THREAD is None or not _INVERT_WORKER_THREAD.is_alive():
        _INVERT_WORKER_THREAD = threading.Thread(target=_invert_worker_loop, daemon=True)
        _INVERT_WORKER_THREAD.start()


def _invert_worker_loop():
    """反相队列消费者：按顺序执行单张/批量反相任务。"""
    while True:
        task = _INVERT_QUEUE.get()
        if task is None:
            break
        with _INVERT_STATUS_LOCK:
            _INVERT_STATUS["running"] = True
            _INVERT_STATUS["current"] = task.get("dx") or (task.get("dx_list", [None])[0] if task.get("dx_list") else None)
            _INVERT_STATUS["pending"] = _INVERT_QUEUE.qsize()
        try:
            if task["type"] == "single":
                Handler._run_single_invert_sync(task["dx"], task["file"])
                result = {
                    "ok": True,
                    "msg": f"{task['dx']} 反相完成（未自动贴图）",
                    "results": [{"ok": True, "dx": task["dx"], "msg": "单张反相完成"}]
                }
            else:
                results = batch_invert_rem(task["dx_list"])
                ok_count = sum(1 for r in results if r["ok"])
                fail_count = len(results) - ok_count
                result = {
                    "ok": fail_count == 0,
                    "msg": f"批量反相完成 {ok_count}/{len(results)}" + (f"，{fail_count} 个失败" if fail_count else "") + "（未自动贴图）",
                    "results": results
                }
            with _INVERT_STATUS_LOCK:
                _INVERT_STATUS["last_result"] = result
                _INVERT_STATUS["completed_total"] += 1
        except Exception as e:
            with _INVERT_STATUS_LOCK:
                _INVERT_STATUS["last_error"] = str(e)
        finally:
            with _INVERT_STATUS_LOCK:
                _INVERT_STATUS["running"] = False
                _INVERT_STATUS["current"] = None
                _INVERT_STATUS["pending"] = _INVERT_QUEUE.qsize()


# ── PS 贴图任务队列（单张 + 批量统一串行执行，避免 PS 并发冲突 + 超时兜底）────────
_STICKER_QUEUE = queue.Queue()
_STICKER_WORKER_THREAD = None
_STICKER_STATUS_LOCK = threading.Lock()
_STICKER_STATUS = {
    "running": False,
    "current": None,
    "pending": 0,
    "completed_total": 0,
    "last_result": None,
    "last_error": None,
}
STICKER_STEP_TIMEOUT = 300  # 每步 PS 脚本最多 5 分钟


def _ensure_sticker_worker():
    """启动 PS 贴图后台工作线程（幂等）。"""
    global _STICKER_WORKER_THREAD
    if _STICKER_WORKER_THREAD is None or not _STICKER_WORKER_THREAD.is_alive():
        _STICKER_WORKER_THREAD = threading.Thread(target=_sticker_worker_loop, daemon=True)
        _STICKER_WORKER_THREAD.start()


def _run_ps_script_with_timeout(cmd, cwd=None, timeout=STICKER_STEP_TIMEOUT, label="PS脚本"):
    """运行 PS 脚本，超时则 kill 子进程并返回失败。"""
    import subprocess as _sub
    try:
        print(f"  [贴图队列] 启动 {label}: {' '.join(cmd)}", flush=True)
        proc = run_minimized(cmd, cwd=cwd, wait=False)
        try:
            proc.wait(timeout=timeout)
        except _sub.TimeoutExpired:
            print(f"  [贴图队列] {label} 超时 {timeout}s，强制终止", flush=True)
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
            return False, f"{label} 超时（{timeout}s）"
        if proc.returncode != 0:
            return False, f"{label} 返回码非零: {proc.returncode}"
        return True, f"{label} 完成"
    except Exception as e:
        return False, f"{label} 启动/执行异常: {e}"


def _run_ps_script_sync(cmd, cwd=None, label="PS脚本"):
    """同步运行 PS 脚本（无超时，保留旧行为供直接调用）。"""
    try:
        proc = run_minimized(cmd, cwd=cwd)
        if proc.returncode != 0:
            return False, f"{label} 返回码非零: {proc.returncode}"
        return True, f"{label} 完成"
    except Exception as e:
        return False, f"{label} 启动/执行异常: {e}"


def _sticker_worker_loop():
    """贴图队列消费者：按顺序执行每款完整贴图流水线。"""
    while True:
        task = _STICKER_QUEUE.get()
        if task is None:
            break
        dx = task.get("dx")
        with _STICKER_STATUS_LOCK:
            _STICKER_STATUS["running"] = True
            _STICKER_STATUS["current"] = dx
            _STICKER_STATUS["pending"] = _STICKER_QUEUE.qsize()
        try:
            ok, msg = Handler._run_sticker_pipeline(dx, use_timeout=True)
            result = {
                "ok": ok,
                "msg": msg,
                "results": [{"ok": ok, "dx": dx, "msg": msg}]
            }
            with _STICKER_STATUS_LOCK:
                _STICKER_STATUS["last_result"] = result
                _STICKER_STATUS["completed_total"] += 1
            print(f"[贴图队列] {dx} 完成: ok={ok}, msg={msg}", flush=True)
        except Exception as e:
            with _STICKER_STATUS_LOCK:
                _STICKER_STATUS["last_error"] = str(e)
            print(f"[贴图队列] {dx} 异常: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            with _STICKER_STATUS_LOCK:
                _STICKER_STATUS["running"] = False
                _STICKER_STATUS["current"] = None
                _STICKER_STATUS["pending"] = _STICKER_QUEUE.qsize()


# ── 回收站删除（与 check_sync.py 一致，可撤销）─────
FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION = 3, 0x40, 0x10
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.INT), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID), ("lpszProgressTitle", wintypes.LPCWSTR)]

def send_to_recycle_bin(path):
    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd, fileop.wFunc = 0, FO_DELETE
    fileop.pFrom, fileop.pTo = str(path) + "\0", None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop)) == 0


# ── 扫描：列出所有 DX 款的 AI/REM_BG 配对 ─────────
def is_generated_ai(fname, dx):
    """是否为该DX的生成图：DXxxxx_? 格式，下划线数==1（排除源图/原图/_副本/_cut）"""
    if not fname.lower().endswith(IMG_EXT):
        return False
    stem, _ = os.path.splitext(fname)
    if "_副本" in fname or "_cut" in fname or "已归档" in fname or "原图" in fname:
        return False
    if not fname.startswith(dx + "_"):
        return False
    return stem.count("_") == 1

def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _uid_map_exists(dx_dir):
    """uid_map.json 存在且非空（位于 05_META）"""
    if wb_meta is None:
        return False
    p = wb_meta.uid_map_path(dx_dir)
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        data = wb_meta.read_uid_map(dx_dir)
        return bool(data.get("images"))
    except Exception:
        return False


def _need_migrate_dx(dx_dir):
    """旧项目迁移条件：无 uid_map 或任意 AI/rembg 文件缺少 sidecar（sidecar 在 05_META）"""
    if wb_meta is None:
        return False
    if not _uid_map_exists(dx_dir):
        return True
    for sub in ("01_AI", "02_REM_BG"):
        d = dx_dir / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if f.name.endswith(".meta.json"):
                continue
            if f.suffix.lower() not in IMG_EXT:
                continue
            if not wb_meta.read_meta(f):
                return True
    return False


def _meta_for(file_path):
    """读取单文件 sidecar，失败或禁用时返回空 dict"""
    if wb_meta is None:
        return {}
    try:
        m = wb_meta.read_meta(file_path)
        return m or {}
    except Exception:
        return {}


def _role_from_name(fname, dx):
    """从文件名推断 role（元数据不可用时回退）"""
    stem, _ = os.path.splitext(fname)
    if stem.startswith(dx + "_"):
        suffix = stem[len(dx)+1:]
        if suffix.endswith("_cut"):
            suffix = suffix[:-4]
        return suffix
    return "?"


def _new_uid(path):
    """为新输出文件生成稳定 UID（基于文件 MD5）"""
    if wb_meta is None:
        return None
    try:
        return f"UID_UPLOAD_{wb_meta.compute_md5(path)[:16]}"
    except Exception:
        return None


def scan_projects(force=False):
    """返回 [{dx, pairs:[{stem, ai_file, rem_file, group_id, ai_uid, rem_uid,
                          ai_stage, rem_stage, role}],
              black_variants:[{stem, rem_file, group_id, rem_uid, rem_stage}]}]"""
    global _SCAN_PROJECTS_CACHE
    with _SCAN_PROJECTS_CACHE["lock"]:
        if not force and _SCAN_PROJECTS_CACHE["projects"] is not None:
            if time.time() - _SCAN_PROJECTS_CACHE["timestamp"] < _SCAN_PROJECTS_TTL:
                return _SCAN_PROJECTS_CACHE["projects"]

    projects = []
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not re.match(r"^DX\d+$", d.name):
            continue
        dx = d.name
        ai_dir = d / "01_AI"
        rem_dir = d / "02_REM_BG"

        # 迁移旧项目：uid_map 不存在/为空或任意 AI/rembg 文件缺少 sidecar
        if _need_migrate_dx(d):
            try:
                wb_meta.migrate_dx(d)
            except Exception as e:
                print(f"  [wb_meta] 迁移 {dx} 失败: {e}", flush=True)

        # MD5 主键对账：图片改名/移动后，用 MD5 修正 uid_map 里的 file 路径
        if wb_meta is not None:
            try:
                wb_meta.reconcile_dx(d)
            except Exception as e:
                print(f"  [wb_meta] 对账 {dx} 失败: {e}", flush=True)

        # 收集所有出现过的 stem（AI生成图 stem 与 REM_BG stem 去掉 _cut 后）
        ai_files = []
        if ai_dir.is_dir():
            for f in sorted(ai_dir.iterdir()):
                if f.is_file() and is_generated_ai(f.name, dx):
                    ai_files.append(f.name)

        rem_files = []
        if rem_dir.is_dir():
            for f in sorted(rem_dir.iterdir()):
                if f.is_file() and f.name.lower().endswith(".png") and f.name.endswith("_cut.png"):
                    rem_files.append(f.name)

        if not ai_files and not rem_files:
            continue  # 该款既无AI图也无去背图，跳过

        # 元数据查找表（wb_meta 可用时）
        ai_meta_by_file = {}
        rem_meta_by_file = {}
        if wb_meta is not None:
            for af in ai_files:
                ai_meta_by_file[af] = _meta_for(ai_dir / af)
            for rf in rem_files:
                rem_meta_by_file[rf] = _meta_for(rem_dir / rf)

        # 以 AI 图为主键配对；剩余的 _cut.png（无对应AI图）也单列
        rem_by_stem = {}
        for rf in rem_files:
            stem = rf[:-len("_cut.png")]  # 去掉 _cut.png 后缀（含扩展名）
            rem_by_stem.setdefault(stem, []).append(rf)

        pairs = []
        covered_rem = set()
        for af in ai_files:
            stem = os.path.splitext(af)[0]
            ai_meta = ai_meta_by_file.get(af, {})
            ai_uid = ai_meta.get("uid")
            group_id = ai_meta.get("group_id") or ""
            role = ai_meta.get("role") or _role_from_name(af, dx)

            # 优先按 UID 元数据匹配（parent_uid == ai_uid 或 rem uid == ai_uid），再按 stem 回退
            matched = []
            if ai_uid:
                for rf in rem_files:
                    if rf in covered_rem:
                        continue
                    m = rem_meta_by_file.get(rf, {})
                    if m.get("parent_uid") == ai_uid or m.get("uid") == ai_uid:
                        matched.append(rf)
            if not matched:
                matched = rem_by_stem.get(stem, [])

            for rf in matched:
                covered_rem.add(rf)
            rem_meta = rem_meta_by_file.get(matched[0], {}) if matched else {}
            pairs.append({
                "stem": stem,
                "ai_file": af,
                "rem_file": matched[0] if matched else None,
                "group_id": group_id or rem_meta.get("group_id", ""),
                "ai_uid": ai_uid,
                "rem_uid": rem_meta.get("uid") if matched else None,
                "ai_stage": ai_meta.get("stage", "ai"),
                "rem_stage": rem_meta.get("stage", "rembg") if matched else None,
                "role": role,
            })

        # 黑版变体：_黑B/_黑W/_黑BW 等，group_id 强制归属到对应 pair 以支持前端分组
        black_variants = []
        for rf in sorted(rem_files):
            if rf in covered_rem or "_黑" not in rf:
                continue
            stem = rf[:-len("_cut.png")]
            m = rem_meta_by_file.get(rf, {})
            group_id = ""
            parent_uid = m.get("parent_uid")
            # 优先按 parent_uid 或 rem_uid 找到对应 pair
            if parent_uid:
                for pr in pairs:
                    if pr.get("ai_uid") == parent_uid or pr.get("rem_uid") == parent_uid:
                        group_id = pr.get("group_id", "")
                        break
            # 再按文件名前缀（DXxxxx_黑B → DXxxxx_B）回退
            if not group_id:
                plain_stem = stem.replace("黑", "", 1)
                for pr in pairs:
                    if pr["stem"] == plain_stem:
                        group_id = pr.get("group_id", "")
                        break
            # 都匹配不到才使用自身元数据
            if not group_id:
                group_id = m.get("group_id", "")
            black_variants.append({
                "stem": stem,
                "rem_file": rf,
                "group_id": group_id,
                "rem_uid": m.get("uid"),
                "rem_stage": m.get("stage", "rembg"),
            })
            covered_rem.add(rf)

        # 没有对应AI图且不是黑版变体的 _cut.png（真·缺AI）
        for rf in rem_files:
            if rf in covered_rem:
                continue
            stem = rf[:-len("_cut.png")]
            m = rem_meta_by_file.get(rf, {})
            pairs.append({
                "stem": stem,
                "ai_file": None,
                "rem_file": rf,
                "group_id": m.get("group_id", ""),
                "ai_uid": None,
                "rem_uid": m.get("uid"),
                "ai_stage": None,
                "rem_stage": m.get("stage", "rembg"),
                "role": m.get("role") or _role_from_name(rf, dx),
            })

        # 该款的日期统一按 DX 文件夹建立日期（YYMMDD）分类，不按文件 mtime
        try:
            dx_date = time.strftime("%y%m%d", time.localtime(d.stat().st_ctime))
        except Exception:
            dx_date = ""

        projects.append({"dx": dx, "date": dx_date, "pairs": pairs, "black_variants": black_variants})

    with _SCAN_PROJECTS_CACHE["lock"]:
        _SCAN_PROJECTS_CACHE["projects"] = projects
        _SCAN_PROJECTS_CACHE["timestamp"] = time.time()
    return projects


def _invalidate_scan_cache():
    """文件变更后清空 scan_projects 缓存，下次请求重新扫描。"""
    global _SCAN_PROJECTS_CACHE
    with _SCAN_PROJECTS_CACHE["lock"]:
        _SCAN_PROJECTS_CACHE["projects"] = None
        _SCAN_PROJECTS_CACHE["timestamp"] = 0


def list_dates(projects):
    """返回所有出现过的日期（降序），用于首页下拉框。"""
    dates = sorted({p["date"] for p in projects if p["date"]}, reverse=True)
    return dates


# ── 缩略图 ─────────────────────────────────────────
def get_thumb(dx, kind, file):
    """kind: 'ai' → 01_AI/file ; 'rem' → 02_REM_BG/file ; 'up' → 03_UPLOAD/file
    返回缩略图路径（不存在则生成）。"""
    sub = "01_AI" if kind == "ai" else "02_REM_BG" if kind == "rem" else "03_UPLOAD"
    src = BASE / dx / sub / file
    if not src.exists():
        return None
    # 缩略图命名：DX0244__ai__DX0244_BW.png.jpg（用双下划线分隔避免与文件名冲突）
    thumb_name = f"{dx}__{kind}__{file}.jpg"
    thumb = THUMB_DIR / thumb_name
    if not thumb.exists() or thumb.stat().st_mtime < src.stat().st_mtime:
        try:
            img = Image.open(src)
            img = img.convert("RGBA")
            # 白底合成（去背图透明背景看不清）
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            bg.alpha_composite(img)
            img = bg.convert("RGB")
            img.thumbnail((300, 300))
            img.save(str(thumb), "JPEG", quality=85)
        except Exception as e:
            print(f"  [缩略图失败] {dx}/{file}: {e}", flush=True)
            return None
    return thumb


# ── 去背结果收集：兼容美图保存路径未切换的兜底 ─────────────
def _collect_rembg_results(dx, stems, rem_dir):
    """从多个可能位置收集去背产物，返回 {stem: dest_path}。

    美图保存对话框若路径未生效，_副本.png 可能落到 DST_SAVE / archive；
    本函数会扫描：
      1. TEMP_REMBG/{dx}/02_REM_BG
      2. WB_ROOT/_temp_rembg/save
      3. WB_ROOT/_temp_rembg/archive
    并把 *_副本.png 改名为 *_cut.png 后移动到真实 rem_dir。
    """
    stems = set(stems)
    found = {}
    search_roots = [
        TEMP_REMBG / dx / "02_REM_BG",
        WB_ROOT / "_temp_rembg" / "save",
        WB_ROOT / "_temp_rembg" / "archive",
    ]
    patterns = ["*_cut.png", "*_副本.png"]
    for root in search_roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            for f in root.glob(pat):
                if f.stat().st_size < 100_000:
                    continue
                stem = f.stem.replace("_副本", "").replace("_cut", "")
                if stem not in stems:
                    continue
                if stem in found:
                    continue  # 已收集，跳过重复
                cut_name = f"{stem}_cut.png"
                dest = rem_dir / cut_name
                rem_dir.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    send_to_recycle_bin(str(dest))
                try:
                    shutil.move(str(f), str(dest))
                    print(f"  [重去背] 收集新结果 → {dest} (来源: {root}/{f.name})", flush=True)
                    found[stem] = dest
                except Exception as e:
                    print(f"  [重去背] 移动结果失败 {f} → {dest}: {e}", flush=True)
    return found


# ── 重新去背：单张 AI 图安全重跑美图秀秀 ─────────────
def rembg_one_file(dx, ai_file):
    """驱动 wb_meitu_batch.py 重跑「指定 DX 的某一张 AI 图」的去背。

    ai_file 形如 DX0244_BW.png；输出会写回该 DX 的 02_REM_BG/{stem}_cut.png。
    安全策略：
      - 先把该 stem 对应的旧 _cut.png 备份（纯复制，不送回收站）
      - 跑美图；若美图没产出新结果，从备份还原旧 _cut.png
      - 跑成功（有新结果）才清掉备份
    """
    ai_dir = BASE / dx / "01_AI"
    rem_dir = BASE / dx / "02_REM_BG"
    ai_path = ai_dir / ai_file
    if not ai_path.exists():
        return False, f"{dx}/{ai_file} 不存在"

    # 校验：必须是该DX的生成图（DXxxxx_? 格式）
    if not is_generated_ai(ai_file, dx):
        return False, f"{ai_file} 不是 {dx} 的生成图（格式不符）"

    stem = os.path.splitext(ai_file)[0]
    cut_name = f"{stem}_cut.png"

    # 0. 读取 AI 图元数据（UID / group_id / role）
    ai_meta = _meta_for(ai_path)
    ai_uid = ai_meta.get("uid")
    group_id = ai_meta.get("group_id") or ""
    role = ai_meta.get("role") or _role_from_name(ai_file, dx)

    # 1. 幂等守卫：若 config.json 上次被改未恢复，先恢复
    _maybe_restore_config()

    # 2. 备份该 stem 对应的旧 _cut.png（纯复制）
    backup_dir = TEMP_REMBG / "_backup" / dx
    backup_dir.mkdir(parents=True, exist_ok=True)
    old_cut_path = rem_dir / cut_name
    had_old = old_cut_path.exists()
    if had_old:
        shutil.copy2(str(old_cut_path), str(backup_dir / cut_name))
        print(f"  [重去背] {dx}/{ai_file}: 备份旧 {cut_name} → {backup_dir}", flush=True)

    # 3. 清理旧 _cut.png（送回收站，给美图腾位）
    if had_old:
        send_to_recycle_bin(str(old_cut_path))

    # 4. 暂存目标图及其配对图到 _temp_rembg/{DX}/01_AI/
    #    美图脚本的 precheck_pairs 会检查 B/W 配对完整性；如果只暂存单张 W，
    #    当 source_map / orig_files 中缺少 B 时会导致整批跳过。因此把同 DX 的
    #    所有生成图都暂存进来，让配对预检看到完整画面（已在 track 的图不会被重跑）。
    staging_root = TEMP_REMBG / dx / "01_AI"
    if staging_root.exists():
        shutil.rmtree(str(staging_root), ignore_errors=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    staged_md5 = []
    for f in sorted(ai_dir.iterdir()):
        if is_generated_ai(f.name, dx):
            shutil.copy2(str(f), str(staging_root / f.name))
            staged_md5.append(file_md5(str(f)))
    # 4b. 复制 source_map.json 与原始配对文件到暂存目录，
    #     让美图 precheck_pairs 能正确识别 B/W 角色与配对完整性。
    src_smap = BASE / dx / "source_map.json"
    if src_smap.exists():
        shutil.copy2(str(src_smap), str(TEMP_REMBG / dx / "source_map.json"))
    for f in sorted(ai_dir.iterdir()):
        if not is_generated_ai(f.name, dx) and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            # 原始配对文件（如 1B.png / 1W.png）
            shutil.copy2(str(f), str(staging_root / f.name))

    if not staged_md5:
        _restore_config()
        _restore_one_backup(cut_name, backup_dir, rem_dir)
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)
        return False, f"{dx} 没有可暂存的生成图"

    # 5. 备份并改写 config.json：SRC 指向 _temp_rembg（脚本扫描 DX*/01_AI）
    shutil.copy2(str(MEITU_CONFIG), str(CONFIG_BACKUP))
    cfg = json.loads(MEITU_CONFIG.read_text(encoding="utf-8"))
    cfg.setdefault("paths", {})
    cfg["paths"]["SRC"] = str(TEMP_REMBG)               # 扫描 _temp_rembg/{DX}/01_AI
    cfg["paths"]["DST_OAI"] = str(BASE)                  # 写回 BASE/DX/02_REM_BG
    cfg["paths"]["DST_SAVE"] = str(WB_ROOT / "_temp_rembg" / "save")
    cfg["paths"]["DST_ARCHIVE"] = str(WB_ROOT / "_temp_rembg" / "archive")
    (WB_ROOT / "_temp_rembg" / "save").mkdir(parents=True, exist_ok=True)
    (WB_ROOT / "_temp_rembg" / "archive").mkdir(parents=True, exist_ok=True)
    MEITU_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # 6. 从 track 移除目标图 md5（仅让美图重跑此图，不影响血缘 registry 中的 AI 图 MD5）
    removed = _untrack_md5([file_md5(str(ai_path))], dx=dx)

    # 7. 真实驱动美图（新控制台窗口，接管屏幕）
    if not MEITU_SCRIPT.exists():
        _restore_config()
        _restore_one_backup(cut_name, backup_dir, rem_dir)
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)
        return False, f"美图脚本不存在: {MEITU_SCRIPT}"

    print(f"  [重去背] {dx}/{ai_file}: 暂存 {len(staged_md5)} 张（目标 + 同DX生成图）, 启动美图...", flush=True)
    print(f"  ⚠ 美图将接管屏幕，请勿动键鼠，等待脚本结束。", flush=True)
    try:
        proc = run_minimized(
            [sys.executable, str(MEITU_SCRIPT)],
            cwd=str(MEITU_SCRIPT.parent),
            capture_output=True, timeout=600,
        )
        ok = proc.returncode == 0
        # 把美图脚本的完整输出写入日志，便于排查「未产出结果」原因
        if proc.stdout:
            print("  [重去背] 美图 stdout:\n" + proc.stdout.decode('utf-8', errors='replace'), flush=True)
        if proc.stderr:
            print("  [重去背] 美图 stderr:\n" + proc.stderr.decode('utf-8', errors='replace'), flush=True)
        print(f"  [重去背] 美图 returncode={proc.returncode}", flush=True)
    except Exception as e:
        ok = False
        print(f"  [重去背] {dx}/{ai_file} 美图运行异常: {e}", flush=True)

    # 8. 收尾：恢复 config（无论成功失败）
    _restore_config()

    # 8b. 收集美图产物。美图保存对话框若路径未生效，_副本.png 可能落到 DST_SAVE / archive；
    #     因此从多个位置扫描并归位到真实 02_REM_BG。
    found = _collect_rembg_results(dx, [stem], rem_dir)
    dest = found.get(stem)
    if dest and dest.exists():
        # 注册去背输出元数据
        if wb_meta is not None and ai_uid:
            try:
                wb_meta.register_rembg(dest, uid=ai_uid, group_id=group_id,
                                       role=role, parent_uid=ai_uid, ai_file=ai_file)
            except Exception as e:
                print(f"  [重去背] 元数据注册失败: {e}", flush=True)
        # 同步执行 ESRGAN 放大到 2024×2048（美图脚本是异步Popen，可能来不及跑完）
        upscaler = MEITU_SCRIPT.parent / "upscale_worker.py"
        if upscaler.exists():
            try:
                subprocess.run([sys.executable, str(upscaler), str(dest)],
                               capture_output=True, timeout=120)
                sz = os.path.getsize(dest) // 1024
                print(f"  [重去背] ESRGAN 放大完成 → {sz}KB", flush=True)
            except Exception as e:
                print(f"  [重去背] ESRGAN 放大跳过: {e}", flush=True)

    # 9. 检查美图是否产出该 stem 的新结果（在真实目录里判断）
    new_exists = rem_dir.is_dir() and (rem_dir / cut_name).exists() \
                 and (rem_dir / cut_name).stat().st_size > 100_000
    if new_exists:
        # 有新结果，清掉备份与暂存
        shutil.rmtree(str(backup_dir), ignore_errors=True)
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)
        # 👇 Hook：通知 Bridge 记录血缘
        try:
            requests.post("http://127.0.0.1:8765/api/lineage/register",
                json={"child_path": str(rem_dir / cut_name), "parent_path": str(ai_path),
                      "stage": "rembg", "uid": ai_uid, "group_id": group_id, "role": role},
                timeout=1)
        except Exception:
            pass
        return True, f"{dx}/{ai_file} 去背完成 → {cut_name}"
    else:
        # 美图没产出 → 从备份还原旧图
        _restore_one_backup(cut_name, backup_dir, rem_dir)
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)
        msg = (f"{dx}/{ai_file} 美图未产出新结果，已还原旧去背图"
               if had_old else f"{dx}/{ai_file} 美图未产出新结果")
        return False, msg


# ── 批量去背：一次美图处理全部 ────────────────────────
def batch_rembg(dx_files):
    """批量去背：将多个 DX 的 AI 图一次性交给美图处理。
    dx_files: [(dx, ai_file), ...]
    返回: [(dx, ai_file, ok, msg), ...]
    """
    _maybe_restore_config()
    results = []
    staged = []  # [(dx, ai_file, stem, cut_name, ai_path, rem_dir, backup_dir, had_old, ai_uid, group_id, role)]

    # 1. 暂存所有 AI 图 + 备份旧 cut
    for dx, ai_file in dx_files:
        ai_dir = BASE / dx / "01_AI"
        rem_dir = BASE / dx / "02_REM_BG"
        ai_path = ai_dir / ai_file
        if not ai_path.exists():
            results.append((dx, ai_file, False, f"{dx}/{ai_file} 不存在"))
            continue
        stem = os.path.splitext(ai_file)[0]
        cut_name = f"{stem}_cut.png"

        # 读取 AI 图元数据
        ai_meta = _meta_for(ai_path)
        ai_uid = ai_meta.get("uid")
        group_id = ai_meta.get("group_id") or ""
        role = ai_meta.get("role") or _role_from_name(ai_file, dx)

        # 备份旧 cut
        backup_dir = TEMP_REMBG / "_batch_backup" / dx
        backup_dir.mkdir(parents=True, exist_ok=True)
        old_cut = rem_dir / cut_name
        had_old = old_cut.exists()
        if had_old:
            shutil.copy2(str(old_cut), str(backup_dir / cut_name))
            send_to_recycle_bin(str(old_cut))

        # 暂存 AI 图
        staging_root = TEMP_REMBG / dx / "01_AI"
        staging_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(ai_path), str(staging_root / ai_file))

        # 暂存 source_map.json 与原始配对文件，帮助美图 precheck_pairs 识别角色
        dx_ai_dir = BASE / dx / "01_AI"
        src_smap = BASE / dx / "source_map.json"
        if src_smap.exists():
            shutil.copy2(str(src_smap), str(TEMP_REMBG / dx / "source_map.json"))
        for f in sorted(dx_ai_dir.iterdir()):
            if not is_generated_ai(f.name, dx) and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                shutil.copy2(str(f), str(staging_root / f.name))

        staged.append((dx, ai_file, stem, cut_name, ai_path, rem_dir, backup_dir, had_old, ai_uid, group_id, role))

    if not staged:
        return results

    # 2. 改写 config.json
    shutil.copy2(str(MEITU_CONFIG), str(CONFIG_BACKUP))
    cfg = json.loads(MEITU_CONFIG.read_text(encoding="utf-8"))
    cfg.setdefault("paths", {})
    cfg["paths"]["SRC"] = str(TEMP_REMBG)
    cfg["paths"]["DST_OAI"] = str(BASE)
    cfg["paths"]["DST_SAVE"] = str(WB_ROOT / "_temp_rembg" / "save")
    cfg["paths"]["DST_ARCHIVE"] = str(WB_ROOT / "_temp_rembg" / "archive")
    (WB_ROOT / "_temp_rembg" / "save").mkdir(parents=True, exist_ok=True)
    (WB_ROOT / "_temp_rembg" / "archive").mkdir(parents=True, exist_ok=True)
    MEITU_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. 从 track 移除所有 MD5
    for dx, ai_file, *_ in staged:
        ai_path = BASE / dx / "01_AI" / ai_file
        _untrack_md5([file_md5(str(ai_path))], dx=dx)

    # 4. 运行美图（一次）
    print(f"  [批量去背] 共 {len(staged)} 张, 启动美图...", flush=True)
    print(f"  ⚠ 美图将接管屏幕，请勿动键鼠，等待脚本结束。", flush=True)
    try:
        proc = run_minimized(
            [sys.executable, str(MEITU_SCRIPT)],
            cwd=str(MEITU_SCRIPT.parent),
            capture_output=True, timeout=600,
        )
        ok = proc.returncode == 0
        # 把美图脚本的完整输出写入日志，便于排查「未产出结果」原因
        if proc.stdout:
            print("  [批量去背] 美图 stdout:\n" + proc.stdout.decode('utf-8', errors='replace'), flush=True)
        if proc.stderr:
            print("  [批量去背] 美图 stderr:\n" + proc.stderr.decode('utf-8', errors='replace'), flush=True)
        print(f"  [批量去背] 美图 returncode={proc.returncode}", flush=True)
    except subprocess.TimeoutExpired:
        ok = False
        print("  [批量去背] 美图超时", flush=True)
    except Exception as e:
        ok = False
        print(f"  [批量去背] 美图异常: {e}", flush=True)
    finally:
        _restore_config()

    # 5. 从多个可能位置收集结果到真实 DX 文件夹
    dx_stems = {}
    for dx, ai_file, stem, cut_name, ai_path, rem_dir, backup_dir, had_old, ai_uid, group_id, role in staged:
        dx_stems.setdefault(dx, {"rem_dir": rem_dir, "items": []})
        dx_stems[dx]["items"].append((ai_file, stem, cut_name, ai_path, ai_uid, group_id, role))
    for dx, info in dx_stems.items():
        stems = [item[1] for item in info["items"]]
        found = _collect_rembg_results(dx, stems, info["rem_dir"])
        for ai_file, stem, cut_name, ai_path, ai_uid, group_id, role in info["items"]:
            dest = found.get(stem)
            if dest and dest.exists():
                # 注册去背输出元数据
                if wb_meta is not None and ai_uid:
                    try:
                        wb_meta.register_rembg(dest, uid=ai_uid, group_id=group_id,
                                               role=role, parent_uid=ai_uid, ai_file=ai_file)
                    except Exception as e:
                        print(f"  [批量去背] 元数据注册失败 {dest}: {e}", flush=True)
                # ESRGAN 放大
                upscaler = MEITU_SCRIPT.parent / "upscale_worker.py"
                if upscaler.exists():
                    try:
                        subprocess.run([sys.executable, str(upscaler), str(dest)],
                                       capture_output=True, timeout=120)
                        sz = os.path.getsize(dest) // 1024
                        print(f"  [批量去背] ESRGAN 放大完成 → {sz}KB", flush=True)
                    except Exception as e:
                        print(f"  [批量去背] ESRGAN 放大跳过: {e}", flush=True)

    # 6. 检查结果
    for dx, ai_file, stem, cut_name, ai_path, rem_dir, backup_dir, had_old, ai_uid, group_id, role in staged:
        result_path = rem_dir / cut_name
        if result_path.exists() and result_path.stat().st_size > 100_000:
            # 成功
            try:
                requests.post("http://127.0.0.1:8765/api/lineage/register",
                    json={"child_path": str(result_path), "parent_path": str(ai_path),
                          "stage": "rembg", "uid": ai_uid, "group_id": group_id, "role": role},
                    timeout=1)
            except Exception:
                pass
            results.append((dx, ai_file, True, f"{dx}/{ai_file} 去背完成 → {cut_name}"))
        else:
            # 失败，还原
            _restore_one_backup(cut_name, backup_dir, rem_dir)
            results.append((dx, ai_file, False,
                f"{dx}/{ai_file} 美图未产出结果" + ("（已还原旧图）" if had_old else "")))

    # 7. 清理暂存
    shutil.rmtree(str(TEMP_REMBG / "_batch_backup"), ignore_errors=True)
    for dx, *_ in staged:
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)

    return results


# ── 批量反相：对多个 DX 的非黑版 _cut.png 反相生成黑版专用图 ────────────────────────
def batch_invert_rem(dx_list):
    """批量反相：对选中 DX 的所有非黑版 _cut.png 反相生成黑版专用图。
    不再自动跑贴图流水线；贴图由用户单独点击「贴图」或「批量贴图」触发。
    dx_list: [dx, ...]
    返回: [{dx, files:[{src,dest}], ok, msg}, ...]
    """
    results = []
    for dx in dx_list:
        rem_dir = BASE / dx / "02_REM_BG"
        if not rem_dir.is_dir():
            results.append({"dx": dx, "files": [], "ok": False,
                            "msg": f"{dx}: 02_REM_BG 不存在"})
            continue

        files = []
        errors = []
        for f in sorted(rem_dir.iterdir()):
            name = f.name
            if not name.lower().endswith("_cut.png"):
                continue
            if "_黑" in name:
                continue
            # 解析后缀：DXxxxx_B / DXxxxx_W / DXxxxx_BW
            stem = name[:-len("_cut.png")]
            suffix = stem[len(dx)+1:] if stem.startswith(dx + "_") else ""
            if not suffix:
                continue
            dest_name = f"{dx}_黑{suffix}_cut.png"
            dest = rem_dir / dest_name
            try:
                img = Image.open(f).convert("RGBA")
                r, g, b, a = img.split()
                rgb = Image.merge("RGB", (r, g, b))
                inv_rgb = ImageOps.invert(rgb)
                inv = Image.merge("RGBA", (*inv_rgb.split(), a))
                inv.save(dest)
                files.append({"src": name, "dest": dest_name})
                # 注册黑版变体元数据
                if wb_meta is not None:
                    try:
                        src_meta = _meta_for(f)
                        parent_uid = src_meta.get("uid")
                        gid = src_meta.get("group_id") or ""
                        black_role = f"黑{suffix}"
                        if parent_uid:
                            wb_meta.register_rembg(dest, uid=_new_uid(dest), group_id=gid,
                                                   role=black_role, parent_uid=parent_uid,
                                                   ai_file=name)
                        else:
                            wb_meta.ensure_meta(dest, group_id=gid, stage="rembg", role=black_role)
                    except Exception as e:
                        print(f"  [批量反相] 元数据注册失败 {dest}: {e}", flush=True)
                # 清缩略图缓存
                for tf in THUMB_DIR.glob(f"{dx}__rem__{dest_name}.*"):
                    try: tf.unlink()
                    except: pass
            except Exception as e:
                errors.append(f"{name}: {e}")

        if not files and errors:
            results.append({"dx": dx, "files": files, "ok": False,
                            "msg": f"{dx}: 反相失败 - " + "; ".join(errors)})
            continue
        if not files:
            results.append({"dx": dx, "files": files, "ok": True,
                            "msg": f"{dx}: 无需要反相的图"})
            continue

        # 仅生成黑版反相图，不自动跑贴图流水线
        results.append({"dx": dx, "files": files, "ok": not errors,
                        "msg": f"{dx}: 反相 {len(files)} 张完成" + ("; 错误: " + "; ".join(errors) if errors else "")})
    return results


def _restore_one_backup(cut_name, backup_dir, rem_dir):
    """从备份还原单个 _cut.png（美图没产出时调用）。"""
    backup_file = backup_dir / cut_name
    if not backup_file.exists():
        return
    rem_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(backup_file), str(rem_dir / cut_name))
    print(f"  [重去背]: 已从备份还原 {cut_name}", flush=True)


def _maybe_restore_config():
    """若 config.json 备份存在（上次中断未恢复），先恢复。"""
    if CONFIG_BACKUP.exists():
        _restore_config()

def _restore_config():
    if CONFIG_BACKUP.exists():
        shutil.copy2(str(CONFIG_BACKUP), str(MEITU_CONFIG))
        try:
            CONFIG_BACKUP.unlink()
        except Exception:
            pass

def _untrack_md5(md5_list, dx=None):
    """从 .meitu_track.json 移除该图 md5（防 get_new_images 跳过），
    并把 dx 从 processed_subdirs 移除（防 get_image_subdirs 整款跳过）。
    美图跑完后会重新写入这些标记。"""
    if not MEITU_TRACK.exists():
        return 0
    try:
        track = json.loads(MEITU_TRACK.read_text(encoding="utf-8"))
    except Exception:
        return 0
    changed = False
    # 1. 移除 md5
    arr = track.get("processed_source_md5", [])
    md5set = set(md5_list)
    new_arr = [m for m in arr if m not in md5set]
    removed = len(arr) - len(new_arr)
    if removed:
        track["processed_source_md5"] = new_arr
        changed = True
    # 2. 移除 processed_subdirs 中的 dx（get_image_subdirs 跳过已处理款的根因）
    if dx:
        subs = track.get("processed_subdirs", [])
        if dx in subs:
            subs.remove(dx)
            track["processed_subdirs"] = subs
            removed += 1
            changed = True
    if changed:
        MEITU_TRACK.write_text(json.dumps(track, ensure_ascii=False), encoding="utf-8")
    return removed


def run_minimized(cmd, cwd=None, wait=True, **extra):
    """Windows 下以最小化、不抢前台焦点的方式运行外部程序。
    wait=True 阻塞等待并返回 CompletedProcess；wait=False 立即返回 Popen 对象。
    extra 可传 capture_output、timeout 等 subprocess 参数。"""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE：最小化，不激活前台
    kwargs = {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NEW_CONSOLE,
    }
    if cwd:
        kwargs["cwd"] = cwd
    kwargs.update(extra)
    if wait:
        return subprocess.run(cmd, **kwargs)
    return subprocess.Popen(cmd, **kwargs)


def _is_rembg_lock_stale(lock):
    """去背锁是否过期：>15分钟 或 锁文件格式损坏(旧版纯文本)。
    防止美图脚本卡死/崩溃后锁永久残留导致"已有去背任务在运行"死锁。"""
    try:
        info = json.loads(lock.read_text(encoding="utf-8"))
        age = time.time() - info.get("ts", 0)
        return age > 900  # 15 分钟
    except Exception:
        return True  # 旧格式(纯文本)或损坏 → 视为过期


def _has_missing(proj):
    """判断一个 project 是否真正缺图（只检查 AI/REM 文件缺失，不检查 B/W 配对）。"""
    for pr in proj["pairs"]:
        if pr["ai_file"] is None or pr["rem_file"] is None:
            return True
    return False


# ── HTTP 服务 ───────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        dx = qs.get("dx", [""])[0]
        kind = qs.get("kind", [""])[0]
        which = qs.get("which", [""])[0]
        file = qs.get("file", [""])[0]
        stem = qs.get("stem", [""])[0]

        if path == "/" or path == "":
            # 根路径直接重定向到最新日期页面，不再显示日期分类 landing
            projects = scan_projects()
            dates = list_dates(projects)
            if dates:
                latest = dates[0]
                self.send_response(302)
                self.send_header("Location", f"/{latest}/")
                self.end_headers()
            else:
                self._send_html("<h2 style='background:#1a1a1a;color:#fff;padding:40px;'>还没有数据</h2>".encode("utf-8"))
        elif path == "/thumb":
            self._serve_thumb(dx, kind, file)
        elif path == "/original":
            self._serve_original(dx, kind, file)
        elif path == "/open":
            self._open_folder(dx, which)
        elif path == "/del":
            self._del_file(dx, which, file)
        elif path == "/rembg":
            self._rembg(dx, file)
        elif path == "/batch-rembg":
            self._batch_rembg()
        elif path == "/api/check-rembg-lock":
            self._check_rembg_lock()
        elif path == "/rembg_stop":
            self._rembg_stop()
        elif path == "/batch-result":
            self._batch_result()
        elif path == "/api/projects":
            self._api_projects()
        elif path == "/check_rem.js":
            self._serve_js()
        elif path == "/refresh-thumb":
            self._refresh_thumb(dx, stem)
        elif path == "/rename":
            target = qs.get("target", [""])[0]
            self._rename_stem(dx, stem, target)
        elif path == "/repair-names":
            self._repair_names()
        elif path == "/refresh":
            self._refresh()
        elif path == "/ps-sticker":
            self._ps_sticker(dx)
        elif path == "/ps-batch":
            self._ps_batch(dx)
        elif path == "/sticker-status":
            self._sticker_status()
        elif path == "/upscale-rem":
            self._upscale_rem(dx, file)
        elif path == "/invert-rem":
            self._invert_rem(dx, file)
        elif path == "/batch-invert-rem":
            self._batch_invert_rem()
        elif path == "/batch-invert-result":
            self._batch_invert_result()
        elif re.match(r"^/(\d{6})/?$", path):
            # /260630/ → 按日期过滤的首页
            m = re.match(r"^/(\d{6})/?$", path)
            self._serve_index(m.group(1))
        else:
            self._send(404, b"NOT FOUND")

    # 按日期过滤的首页（date 为空则显示全部）
    def _serve_index(self, date=""):
        projects = scan_projects()
        dates = list_dates(projects)
        if date:
            shown = [p for p in projects if p["date"] == date]
        else:
            shown = projects
        html = self._render_html(shown, dates, date)
        self._send_html(html.encode("utf-8"))

    def _render_html(self, projects, dates=None, current_date=""):
        if dates is None:
            dates = list_dates(scan_projects())
        # 日期下拉框选项
        date_opts = ['<option value="">全部</option>']
        for dt in dates:
            sel = " selected" if dt == current_date else ""
            date_opts.append(
                f'<option value="{dt}"{sel}>20{dt[:2]}-{dt[2:4]}-{dt[4:6]}</option>'
            )
        date_opts_html = "\n".join(date_opts)
        # 卡片HTML（缺图的款排前面，其余按DX号）
        # "缺图"包括：缺AI图、缺去背
        projects = sorted(projects, key=lambda p: (
            0 if _has_missing(p) else 1, p["dx"]
        ))
        cards = []
        for p in projects:
            dx = p["dx"]
            rows = []
            # 对同类款的分组：BW、B、W 分开
            bw_pairs = [pr for pr in p["pairs"] if pr["stem"].endswith("_BW")]
            b_pairs  = [pr for pr in p["pairs"] if pr["stem"].endswith("_B")]
            w_pairs  = [pr for pr in p["pairs"] if pr["stem"].endswith("_W")]
            other_pairs = [pr for pr in p["pairs"]
                           if pr not in bw_pairs and pr not in b_pairs and pr not in w_pairs]

            # — 辅助：渲染单个 AI+REM 格 —
            def _render_cells(dx, pr, kind_tag=""):
                """kind_tag 如 'ai','rem' 仅在 extra 时用；按 pr 内的 ai_file/rem_file 渲染"""
                stem = pr["stem"]
                ai_file = pr["ai_file"]
                rem_file = pr["rem_file"]
                # 获取文件mtime做缓存破弃
                def _ts(sub, fn):
                    p = BASE / dx / sub / (fn or "")
                    return int(p.stat().st_mtime) if fn and p.exists() else 0
                ai_ts = _ts("01_AI", ai_file)
                rem_ts = _ts("02_REM_BG", rem_file)
                if ai_file:
                    ai_c = f'''<div class="cell-wrap"><div class="cell" id="{dx}-{stem}-ai">
                        <img src="/thumb?dx={dx}&kind=ai&file={quote(ai_file)}&t={ai_ts}" onclick="openFolder('{dx}','ai')">
                        <span class="tag">AI</span></div>
                        <div class="btn-bar">
                        <button class="del" onclick="delImg('{dx}','ai','{ai_file}','{dx}-{stem}-ai')" title="删除AI图">×</button>
                        <button class="rmbg" onclick="rembg('{dx}','{ai_file}')" title="重新去背">🔄</button>
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                else:
                    ai_c = '<div class="cell missing"><span>⚠ 缺AI图</span></div>'
                if rem_file:
                    # 检查分辨率：任意一边低于 2000 才显示放大镜，并在按钮旁显示当前尺寸
                    rem_path = BASE / dx / "02_REM_BG" / rem_file
                    _w = _h = 0
                    try:
                        with Image.open(rem_path) as _img:
                            _w, _h = _img.size
                    except:
                        pass
                    show_up = (_w < 2000 or _h < 2000)
                    dim_text = f"{_w}x{_h}" if (_w and _h) else ""
                    up_btn = f'<button class="upscale" onclick="upscaleRem(\'{dx}\',\'{rem_file}\',\'{dx}-{stem}-rem\')" title="放大到2046x2046">🔍</button>' if show_up else ''
                    dim_hint = f'<span class="dim-hint" title="当前分辨率">{dim_text}</span>' if show_up else ''
                    inv_btn = f'<button class="invert" onclick="invertRem(\'{dx}\',\'{rem_file}\',\'{stem}\',\'{dx}-{stem}-rem\')" title="生成黑版反相贴图">反相</button>' if '_黑' not in rem_file else ''
                    rem_c = f'''<div class="cell-wrap"><div class="cell" id="{dx}-{stem}-rem">
                        <img id="img-{dx}-{stem}-rem" src="/thumb?dx={dx}&kind=rem&file={quote(rem_file)}&t={rem_ts}" onclick="openFolder('{dx}','rem')">
                        <span class="tag">REM</span></div>
                        <div class="btn-bar">
                        <button class="del" onclick="delImg('{dx}','rem','{rem_file}','{dx}-{stem}-rem')" title="删除去背图">×</button>
                        <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="刷新预览图">🔄</button>
                        {inv_btn}
                        {up_btn}{dim_hint}
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                else:
                    rem_c = f'''<div class="cell-wrap"><div class="cell missing" id="{dx}-{stem}-rem">
                        <span id="img-{dx}-{stem}-rem">⚠ 缺去背</span>
                        <span class="tag">REM</span></div>
                        <div class="btn-bar">
                        <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="重新扫描去背图">🔄</button>
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                return f'<div class="pair-imgs">{ai_c}{rem_c}</div>'

            # — BW 行（独立，紫色badge）—
            for pr in bw_pairs:
                stem = pr["stem"]
                gid = pr.get("group_id", "")
                rows.append(
                    f'<div class="pair" data-group-id="{gid}" data-ai-uid="{pr.get("ai_uid") or ""}" '
                    f'data-rem-uid="{pr.get("rem_uid") or ""}" data-stem="{stem}"><div class="stem">'
                    f'<span class="badge badge-bw">BW</span> {stem}</div>'
                    f'{_render_cells(dx, pr)}</div>')

            # — B+W 配对行（左右并排）—
            # 建索引 prefix → pair
            b_by_prefix = {}
            for pr in b_pairs:
                prefix = pr["stem"][:-2]  # 去掉末尾 _B
                b_by_prefix[prefix] = pr
            w_by_prefix = {}
            for pr in w_pairs:
                prefix = pr["stem"][:-2]  # 去掉末尾 _W
                w_by_prefix[prefix] = pr
            grouped_prefixes = set(b_by_prefix) | set(w_by_prefix)
            for prefix in sorted(grouped_prefixes):
                b_pr = b_by_prefix.get(prefix)
                w_pr = w_by_prefix.get(prefix)

                def _half(dx, pr, badge_class, badge_text):
                    if not pr:
                        return ""
                    gid = pr.get("group_id", "")
                    stem = pr["stem"]
                    if stem.endswith("_B"):
                        opts = [("W", "→ W"), ("BW", "→ BW")]
                    elif stem.endswith("_W"):
                        opts = [("B", "→ B"), ("BW", "→ BW")]
                    elif stem.endswith("_BW"):
                        opts = [("B", "→ B"), ("W", "→ W")]
                    else:
                        opts = []
                    opt_html = "".join(f'<option value="{k}">{v}</option>' for k, v in opts)
                    rename_sel = f'''<select class="ren-sel" onchange="event.stopPropagation(); if(this.value){{renameStem('{dx}','{stem}',this.value);}} this.selectedIndex=0;" title="改名为...">
                        <option value="" selected>改名...</option>{opt_html}</select>''' if opts else ""
                    return f'''<div class="bw-half" data-group-id="{gid}" data-ai-uid="{pr.get("ai_uid") or ""}" data-rem-uid="{pr.get("rem_uid") or ""}" data-stem="{stem}">
                        <div class="stem"><span class="badge {badge_class}">{badge_text}</span>{rename_sel}</div>
                        {_render_cells(dx, pr)}
                    </div>'''

                left  = _half(dx, b_pr, "badge-b", "B")
                right = _half(dx, w_pr, "badge-w", "W")
                left_gid = b_pr.get("group_id", "") if b_pr else ""
                right_gid = w_pr.get("group_id", "") if w_pr else ""
                rows.append(f'<div class="bw-group" data-group-left="{left_gid}" data-group-right="{right_gid}">{left}{right}</div>')

            # — 其他（_BB 等）普通行 —
            for pr in other_pairs:
                gid = pr.get("group_id", "")
                rows.append(
                    f'<div class="pair" data-group-id="{gid}" data-ai-uid="{pr.get("ai_uid") or ""}" '
                    f'data-rem-uid="{pr.get("rem_uid") or ""}" data-stem="{pr["stem"]}">'
                    f'<div class="stem">{pr["stem"]}</div>'
                    f'{_render_cells(dx, pr)}</div>')

            # — 黑版变体行（无独立AI，按 group_id 分组后前端会移到对应 pair 旁）—
            def _render_black_cell(dx, bv):
                stem = bv["stem"]
                rem_file = bv["rem_file"]
                gid = bv.get("group_id", "")
                rem_uid = bv.get("rem_uid") or ""
                rem_path = BASE / dx / "02_REM_BG" / rem_file
                rem_ts = int(rem_path.stat().st_mtime) if rem_path.exists() else 0
                tag = stem[len(dx)+1:] if stem.startswith(dx + "_") else "REM"
                return f'''<div class="cell-wrap black-variant" data-group-id="{gid}" data-rem-uid="{rem_uid}" data-stem="{stem}"><div class="cell" id="{dx}-{stem}-rem">
                    <img id="img-{dx}-{stem}-rem" src="/thumb?dx={dx}&kind=rem&file={quote(rem_file)}&t={rem_ts}" onclick="openFolder('{dx}','rem')">
                    <span class="tag">{tag}</span></div>
                    <div class="btn-bar">
                    <button class="del" onclick="delImg('{dx}','rem','{rem_file}','{dx}-{stem}-rem')" title="删除去背图">×</button>
                    <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="刷新预览图">🔄</button>
                    <span class="btn-stem">{stem}</span>
                    </div></div>'''

            black_variants = p.get("black_variants", [])
            for bv in sorted(black_variants, key=lambda x: x["stem"]):
                rows.append(
                    f'<div class="pair black-variant-row" data-kind="black-variant" data-group-id="{bv.get("group_id", "")}">'
                    f'<div class="stem"><span class="badge badge-other">黑版</span></div>'
                    f'<div class="pair-imgs">{_render_black_cell(dx, bv)}</div></div>')

            rows_html = "\n".join(rows)
            up_dir = BASE / dx / "03_UPLOAD"
            has_up = up_dir.is_dir() and any(f for f in up_dir.iterdir() if f.suffix.lower() in ('.png','.jpg','.jpeg'))
            up_detail = self._upload_detail(dx, has_up)
            cards.append(f'''<div class="card" data-dx="{dx}">
                <div class="card-head">
                    <input type="checkbox" class="dx-check" data-dx="{dx}" onchange="updateBatchBtn()" style="width:16px;height:16px;accent-color:#4CAF50;cursor:pointer;">
                    <span class="dxname" onclick="copyDx('{dx}')" title="点击复制款号">{dx}</span>
                    <span class="pipeline"><span class="pipe pipe-ok" title="AI生图完成">🎨AI</span><span class="pipe {'pipe-ok' if any(pr['rem_file'] for pr in p['pairs']) or p.get('black_variants') else 'pipe-pend'}" title="去背完成">✂️</span><span class="pipe {'pipe-ok' if has_up else 'pipe-pend'}" title="贴图（黑T优先用黑版文件）+BW合成完成">📎</span></span>
                    <span class="card-act">
                        <button class="btn-ps" onclick="psSticker('{dx}')" title="PS贴图（白T用通用文件，黑T优先用黑版文件，再合成BW）">📎 贴图</button>
                        <button class="btn-bw" onclick="psBatch('{dx}')" {'disabled' if not has_up else ''} title="仅用已贴好的B/W合成BW">🔄 BW</button>
                        <button class="btn-open" onclick="openFolder('{dx}','up')" title="打开 03_UPLOAD">📂</button>
                    </span>
                    <span class="pcount">{len(p['pairs']) + len(p.get('black_variants', []))}款</span>
                </div>
                <div class="pairs">{rows_html}</div>
                {up_detail}
            </div>''')
        cards_html = "\n".join(cards) or '<p class="empty">暂无数据</p>'

        return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>AI 去背 贴图 OS v{__version__}</title>
<style>
body {{ margin:0; padding:22px; background:#1a1a1a; color:#eee;
       font-family:'Microsoft YaHei',sans-serif; }}
h1 {{ text-align:center; font-size:28px; margin:0 0 14px; }}
h1 .v {{ font-size:14px; color:#666; font-weight:normal; }}
.toolbar {{ text-align:center; margin-bottom:16px; position:sticky; top:0; background:#1a1a1a; padding:10px 0; z-index:10; }}
.toolbar input {{ padding:11px 16px; font-size:16px; width:260px; border-radius:5px; border:1px solid #555; background:#2a2a2a; color:#eee; }}
.toolbar select {{ padding:11px 16px; font-size:16px; border-radius:5px; border:1px solid #555; background:#2a2a2a; color:#eee; }}
.toolbar button {{ padding:11px 20px; font-size:16px; cursor:pointer; background:#2196F3; color:#fff; border:none; border-radius:5px; margin-left:8px; font-weight:600; }}
.toolbar button:hover {{ background:#1976D2; }}
.toolbar .cnt {{ color:#888; margin-left:12px; font-size:14px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(520px,1fr)); gap:18px; max-width:1920px; margin:0 auto; }}
.card {{ background:#1e1e1e; border-radius:10px; border:1px solid #333; overflow:hidden; }}
.card-head {{ display:flex; align-items:center; gap:10px; padding:12px 16px; background:#252525; border-bottom:1px solid #333; }}
.dxname {{ font-weight:700; font-size:18px; cursor:pointer; color:#4CAF50; letter-spacing:.3px; }}
.pcount {{ color:#666; font-size:13px; flex-shrink:0; }}
.pairs {{ padding:10px 12px 6px; display:flex; flex-direction:column; gap:8px; }}
.pair {{ border-top:1px solid #2a2a2a; padding:8px 0 4px; }}
.pair:first-child {{ border-top:none; padding-top:0; }}
.stem {{ color:#888; font-size:13px; margin-bottom:5px; padding:0 2px; }}
.pair-imgs {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.cell-wrap {{ display:flex; flex-direction:column; }}
.cell {{ height:220px; max-height:220px; background:#fff; border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center; position:relative; }}
.cell.missing {{ background:#2a1a1a; color:#e57373; font-size:14px; }}
.cell img {{ width:100%; height:100%; object-fit:contain; cursor:pointer; transition:transform .15s; }}
.cell:hover img {{ transform:scale(1.06); }}
.cell .tag {{ position:absolute; top:4px; left:4px; background:rgba(0,0,0,.7); color:#fff; font-size:11px; padding:2px 6px; border-radius:3px; line-height:1.6; }}
.btn-bar {{ display:flex; align-items:center; gap:4px; padding:5px 2px 3px; min-height:30px; flex-wrap:wrap; }}
.btn-bar button {{ border:none; border-radius:4px; cursor:pointer; font-size:13px; padding:3px 8px; line-height:24px; flex-shrink:0; }}
.btn-bar .del {{ background:#e53935; color:#fff; }}
.btn-bar .del:hover {{ background:#b71c1c; }}
.btn-bar .rmbg {{ background:#ff9800; color:#fff; }}
.btn-bar .rmbg:hover {{ background:#e65100; }}
.btn-bar .refr {{ background:#2196F3; color:#fff; }}
.btn-bar .refr:hover {{ background:#1565C0; }}
.btn-bar .invert {{ background:#673ab7; color:#fff; }}
.btn-bar .invert:hover {{ background:#512da8; }}
.btn-bar .upscale {{ background:#4caf50; color:#fff; font-size:14px; padding:3px 9px; }}
.btn-bar .upscale:hover {{ background:#2e7d32; }}
.btn-bar .dim-hint {{ color:#888; font-size:11px; margin-left:3px; white-space:nowrap; }}
.btn-stem {{ color:#666; font-size:11px; margin-left:auto; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:110px; flex-shrink:1; }}
.badge {{ display:inline-block; font-size:12px; font-weight:bold; padding:2px 7px; border-radius:3px; margin-right:4px; }}
.badge-bw {{ background:#9c27b0; color:#fff; }}
.badge-b {{ background:#555; color:#fff; }}
.badge-w {{ background:#e0e0e0; color:#333; }}
.bw-group {{ display:flex; gap:10px; }}
.bw-half {{ flex:1; min-width:0; }}
.ps-btn {{ display:inline-flex; align-items:center; gap:2px; font-size:12px; padding:2px 10px; border-radius:4px; cursor:pointer; background:#7b1fa2; color:#fff; border:none; line-height:24px; white-space:nowrap; margin-left:auto; }}
.ps-btn:hover {{ background:#9c27b0; }}
.ps-btn.ps-done {{ background:#2e7d32; }}
.ps-btn.ps-done:hover {{ background:#388e3c; }}
.ren-btn {{ display:inline; font-size:12px; padding:1px 5px; margin-left:3px; border-radius:2px;
           background:#4caf50; color:#fff; border:none; cursor:pointer; vertical-align:middle; }}
.ren-btn:hover {{ background:#388e3c; }}
.ren-sel {{ display:inline; font-size:12px; padding:1px 3px; margin-left:3px; border-radius:2px;
            background:#4caf50; color:#fff; border:none; cursor:pointer; vertical-align:middle; }}
.ren-sel option {{ background:#fff; color:#333; }}
.cell.deleted {{ opacity:.3; }}
.empty {{ text-align:center; color:#888; margin-top:40px; font-size:16px; }}
.toast {{ position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:#333; color:#fff;
	          padding:14px 26px; border-radius:8px; font-size:16px; display:none; z-index:999; max-width:80%; }}
/* 悬停预览（出现在cell旁边，不挡cell） */
.preview {{ position:fixed; z-index:9999; pointer-events:none; display:none;
            max-width:900px; max-height:90vh; border:2px solid #555;
            border-radius:6px; box-shadow:0 4px 25px rgba(0,0,0,.85);
            background:#00b300; }}
.preview img {{ display:block; max-width:900px; max-height:90vh; object-fit:contain; }}
/* pipeline status */
.pipeline {{ display:none; align-items:center; gap:5px; font-size:12px; margin-left:6px; }}
.pipe {{ display:inline-flex; align-items:center; gap:2px; padding:2px 6px; border-radius:3px; font-weight:600; }}
.pipe-ok {{ background:#0d4420; color:#7ee787; }}
.pipe-miss {{ background:#4d1a1a; color:#f87171; }}
.pipe-pend {{ background:#442d0a; color:#f7c843; }}
/* per-card PS/BW buttons */
.card-act {{ display:flex; gap:4px; margin-left:auto; }}
.card-act button {{ font-size:13px; padding:3px 10px; border-radius:4px; border:none; cursor:pointer; font-weight:600; line-height:24px; transition:.1s; white-space:nowrap; }}
.card-act button:active {{ transform:scale(.95); }}
.card-act button:disabled {{ opacity:.4; cursor:not-allowed; }}
.btn-ps {{ background:#7b1fa2; color:#fff; }}
.btn-ps:hover:not(:disabled) {{ background:#9c27b0; }}
.btn-bw {{ background:#e65100; color:#fff; }}
.btn-bw:hover:not(:disabled) {{ background:#ff6d00; }}
.btn-open {{ background:#21262d; color:#c9d1d9; border:1px solid #30363d; }}
.btn-open:hover {{ background:#30363d; }}
/* upload info */
.upload-bar {{ display:flex; align-items:center; gap:8px; padding:8px 12px; margin:0 12px 12px; background:#0d1117; border-radius:6px; font-size:12px; color:#8b949e; flex-wrap:wrap; border:1px solid #222; }}
.upload-bar.empty {{ justify-content:center; }}
.upload-bar.has-up {{ flex-direction:column; align-items:stretch; gap:10px; padding:10px 12px; }}
.upload-bar .tag-up {{ background:#2e7d32; color:#fff; padding:1px 7px; border-radius:3px; font-weight:600; }}
.upload-bar .tag-no {{ background:#4d1a1a; color:#f87171; padding:1px 7px; border-radius:3px; font-weight:600; }}
.up-header {{ display:flex; align-items:center; gap:8px; }}
.up-count {{ color:#888; font-size:12px; }}
.up-gallery {{ display:flex; flex-direction:column; gap:12px; }}
.up-group {{ display:flex; flex-direction:column; gap:5px; }}
.up-group-header {{ display:flex; align-items:center; }}
.up-group-imgs {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.up-item {{ display:flex; flex-direction:column; align-items:center; width:auto; }}
.up-thumb {{ width:100%; height:220px; border-radius:6px; overflow:hidden; background:#fff; cursor:pointer; position:relative; border:1px solid #333; }}
.up-thumb img {{ width:100%; height:100%; object-fit:contain; transition:transform .15s; }}
.up-thumb:hover img {{ transform:scale(1.06); }}
.up-label {{ color:#aaa; font-size:13px; margin-top:6px; text-align:center; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.badge-other {{ background:#424242; color:#fff; }}

</style></head><body>
<h1>AI 去背 贴图 OS <span class="v">v{__version__}</span></h1>
<div class="toolbar">
  <select id="dateSel" onchange="switchDate(this.value)">
{date_opts_html}
  </select>
	  <input id="search" placeholder="搜索 DX号…" oninput="filterCards()">
	  <button onclick="filterCards()" style="cursor:pointer;background:#4CAF50;color:#fff;border:none;border-radius:4px;margin-left:4px;">🔍 搜索</button>
  <button onclick="fetch('/refresh').then(function(r){{return r.json();}}).then(function(d){{showToast(d.msg);setTimeout(function(){{location.reload();}},500);}}).catch(function(){{location.reload();}});" title="清空缩略图缓存并重新扫描全部">🔄 刷新全部</button>
	  <label style="color:#eee;cursor:pointer;user-select:none;margin-left:8px;">
	    <input type="checkbox" id="selectAll" onchange="toggleSelectAll(this.checked)" style="width:18px;height:18px;accent-color:#4CAF50;vertical-align:middle;"> 全选
	  </label>
	  <button onclick="batchRembg()" id="batchBtn" style="cursor:pointer;background:#ff9800;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>⚡ 批量去背 (0)</button>
	  <button onclick="copyMissing()" title="复制当前日期缺图款号（缺AI图/缺去背）" style="background:#e91e63;">📋 复制缺图款号</button>
	  <button onclick="batchSticker()" id="batchStickerBtn" title="批量PS贴图（含B/W贴图与BW合成）" style="cursor:pointer;background:#7b1fa2;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>📎 批量贴图 (0)</button>
	  <button onclick="batchInvertRem()" id="batchInvertBtn" title="批量反相：对选中款的所有B/W/BW去背图生成黑版专用图（不会自动贴图）" style="cursor:pointer;background:#673ab7;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>🌑 批量反相 (0)</button>
	  <button onclick="copyNoSticker()" title="复制当前日期所有未生成成品的款号" style="background:#7b1fa2;">📋 复制缺贴图</button>
	  <span class="cnt" id="cnt">{len(projects)} 款</span>
	</div>
	<div class="grid" id="grid">{cards_html}</div>
<div id="toast" class="toast"></div>
<div id="preview" class="preview"><img id="previewImg" src=""></div>
  <script src="/check_rem.js"></script></body></html>"""

    # JS 文件
    def _serve_js(self):
        js_file = Path(__file__).parent / "check_rem.js"
        if js_file.exists():
            data = js_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send(404, b"JS NOT FOUND")

    # API：返回项目扫描数据（含 group_id / uid / stage）
    def _api_projects(self):
        self._send_json(scan_projects())

    # 缩略图
    def _serve_thumb(self, dx, kind, file):
        # 防目录穿越
        if "/" in file or "\\" in file or "/" in dx or "\\" in dx or not re.match(r"^DX\d+$", dx):
            self._send(400, b"bad"); return
        thumb = get_thumb(dx, kind, file)
        if not thumb:
            self._send(404, b"NO THUMB"); return
        data = thumb.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # 原始图（全分辨率，供悬停预览用）
    def _serve_original(self, dx, kind, file):
        if "/" in file or "\\" in file or "/" in dx or "\\" in dx or not re.match(r"^DX\d+$", dx):
            self._send(400, b"bad"); return
        sub = "01_AI" if kind == "ai" else "02_REM_BG" if kind == "rem" else "03_UPLOAD"
        src = BASE / dx / sub / file
        if not src.exists():
            self._send(404, b"NOT FOUND"); return
        data = src.read_bytes()
        ct = "image/png" if file.lower().endswith(".png") else "image/jpeg"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # 打开文件夹
    def _open_folder(self, dx, which):
        if not re.match(r"^DX\d+$", dx):
            self._send(400, b"bad dx"); return
        sub = "01_AI" if which == "ai" else "02_REM_BG" if which == "rem" else "03_UPLOAD"
        folder = BASE / dx / sub
        if folder.exists():
            try:
                os.startfile(str(folder))
            except Exception:
                subprocess.Popen(f'explorer.exe "{folder}"', shell=True)
            # 将文件夹窗口置顶前台
            try:
                self._activate_window_foreground(folder.name)
            except Exception:
                pass
            self._send(200, b"OK")
        else:
            self._send(404, b"NOT FOUND")

    def _activate_window_foreground(self, title_hint):
        """遍历资源管理器窗口，将标题匹配的窗口置顶前台（绕过后台进程前台锁）。"""
        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        VK_MENU = 0x12; KEYEVENTF_KEYUP = 2; SW_RESTORE = 9

        found = []

        def enum_cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(32)
            user32.GetClassNameW(hwnd, buf, 32)
            if buf.value not in ("CabinetWClass", "ExploreWClass"):
                return True
            length = user32.GetWindowTextLengthW(hwnd) + 1
            tbuf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, tbuf, length)
            if title_hint in tbuf.value:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        # 窗口可能尚未创建，重试至多 5 次
        if not found:
            for _ in range(5):
                found.clear()
                user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
                if found:
                    break
                time.sleep(0.15)

        if not found:
            return

        hwnd = found[0]
        # 模拟 Alt 键：释放前台锁，允许后台进程调用 SetForegroundWindow
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)

    # 删除单文件（送回收站）
    def _del_file(self, dx, which, file):
        if not re.match(r"^DX\d+$", dx) or "/" in file or "\\" in file:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        sub = "01_AI" if which == "ai" else "02_REM_BG" if which == "rem" else "03_UPLOAD"
        target = BASE / dx / sub / file
        if not target.exists():
            self._send_json({"ok": False, "msg": f"{file} 不存在"}); return
        ok = send_to_recycle_bin(str(target))
        # 删除关联缩略图缓存
        for tf in THUMB_DIR.glob(f"{dx}__{which}__{file}.*"):
            try: tf.unlink()
            except Exception: pass
        msg = f"已送回收站: {file}" if ok else "删除失败"
        self._send_json({"ok": ok, "msg": msg})

    # 重新去背（针对单张 AI 图）
    # HTTP 立即返回，美图在新控制台窗口异步跑；worker 负责同步逻辑 + 释放锁。
    def _rembg(self, dx, file):
        if not re.match(r"^DX\d+$", dx):
            self._send_json({"ok": False, "msg": "DX号非法"}); return
        if not file or "/" in file or "\\" in file:
            self._send_json({"ok": False, "msg": "图片文件参数非法"}); return
        # 检查是否已有任务在跑
        lock = TEMP_REMBG / ".rembg_lock"
        if lock.exists():
            if _is_rembg_lock_stale(lock):
                try: lock.unlink()
                except Exception: pass
                print("  [rembg] 检测到过期锁，已自动清除", flush=True)
            else:
                self._send_json({"ok": False, "msg": "已有去背任务在运行，请等其完成。如卡死可点「强制停止」", "can_stop": True}); return
        lock.write_text(json.dumps({"pid": os.getpid(), "ts": time.time(), "type": "single", "dx": dx, "file": file}), encoding="utf-8")
        # 启动后台 worker（最小化控制台窗口），HTTP 立即返回
        worker = Path(__file__).parent / "_rembg_worker.py"
        run_minimized([sys.executable, str(worker), dx, file], wait=False)
        self._send_json({"ok": True, "msg": f"{dx}/{file} 已启动美图去背，请勿动键鼠，完成后点刷新"})

    # 检查去背锁（供批量去背轮询）
    def _check_rembg_lock(self):
        lock = TEMP_REMBG / ".rembg_lock"
        locked = lock.exists()
        if locked and _is_rembg_lock_stale(lock):
            try: lock.unlink(); locked = False
            except Exception: pass
        self._send_json({"locked": locked})

    # 强制停止去背任务：杀美图+脚本进程，清锁
    def _rembg_stop(self):
        """强制停止卡死的去背任务：杀 XiuXiu.exe + wb_meitu_batch/_rembg_worker python，清锁。"""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process XiuXiu -ErrorAction SilentlyContinue | Stop-Process -Force; "
                 "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*wb_meitu_batch*' -or $_.CommandLine -like '*_rembg_worker*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                capture_output=True, timeout=10)
        except Exception as e:
            print(f"  [rembg_stop] 杀进程异常: {e}", flush=True)
        lock = TEMP_REMBG / ".rembg_lock"
        try:
            if lock.exists(): lock.unlink()
        except Exception: pass
        self._send_json({"ok": True, "msg": "已强制停止去背任务并清除锁，可重新点击去背"})

    # 批量去背（一次美图处理全部）
    def _batch_rembg(self):
        from urllib.parse import parse_qs
        qs = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        dx_str = qs.get("dx", [""])[0]
        if not dx_str:
            self._send_json({"ok": False, "msg": "缺少 dx 参数"}); return
        dx_list = [d.strip() for d in dx_str.split(",") if d.strip()]
        if not dx_list:
            self._send_json({"ok": False, "msg": "无效的 dx 参数"}); return

        # 对每个 DX，找所有 AI 生成图（B 和 W 都需要去背）
        dx_files = []
        for dx in dx_list:
            ai_dir = BASE / dx / "01_AI"
            if not ai_dir.is_dir():
                continue
            files = []
            for f in sorted(ai_dir.iterdir()):
                if f.is_file() and is_generated_ai(f.name, dx):
                    files.append(f.name)
            # 如果该 DX 已有 BW 合并图，就只处理 BW，跳过 B/W
            has_bw = any("_BW" in name for name in files)
            if has_bw:
                files = [name for name in files if "_BW" in name]
            dx_files.extend((dx, name) for name in files)

        if not dx_files:
            self._send_json({"ok": False, "msg": "没有找到需要去背的图"}); return

        # 异步执行（batch_rembg 会开美图 GUI）
        import threading
        def _run():
            lock = TEMP_REMBG / ".rembg_lock"
            try:
                lock.write_text(json.dumps({"pid": os.getpid(), "ts": time.time(), "type": "batch"}), encoding="utf-8")
                results = batch_rembg(dx_files)
                ok_count = sum(1 for r in results if r[2])
                fail_count = len(results) - ok_count
                msg = f"完成 {ok_count}/{len(results)}"
                if fail_count:
                    msg += f", {fail_count}个失败"
                result_file = TEMP_REMBG / "_batch_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump({"ok": True, "msg": msg, "results": [
                        {"dx": r[0], "ai_file": r[1], "ok": r[2], "msg": r[3]} for r in results
                    ]}, f, ensure_ascii=False)
            finally:
                if lock.exists():
                    lock.unlink()
        threading.Thread(target=_run, daemon=True).start()
        self._send_json({"ok": True, "msg": f"批量去背已启动，共 {len(dx_files)} 张"})

    # 批量去背结果查询
    def _batch_result(self):
        result_file = TEMP_REMBG / "_batch_result.json"
        lock = TEMP_REMBG / ".rembg_lock"
        if lock.exists():
            self._send_json({"done": False, "msg": "去背进行中…"})
        elif result_file.exists():
            try:
                data = json.loads(result_file.read_text(encoding="utf-8"))
                result_file.unlink()
                self._send_json({"done": True, **data})
            except Exception:
                self._send_json({"done": True, "ok": True, "msg": "完成", "results": []})
        else:
            self._send_json({"done": True, "ok": True, "msg": "无结果", "results": []})

    # 刷新全部（重新扫描）
    # 刷新全部：清空缩略图缓存与 scan_projects 缓存 → 重新扫描 → 前端刷新页面
    def _refresh(self):
        import shutil
        global _SCAN_PROJECTS_CACHE
        if THUMB_DIR.exists():
            shutil.rmtree(str(THUMB_DIR))
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        with _SCAN_PROJECTS_CACHE["lock"]:
            _SCAN_PROJECTS_CACHE["projects"] = None
            _SCAN_PROJECTS_CACHE["timestamp"] = 0
        self._send_json({"ok": True, "msg": "已清空缩略图并重新扫描，刷新页面查看"})

    @staticmethod
    def _register_uploads(dx):
        """扫描 03_UPLOAD 并注册贴图/BW 合成图元数据。"""
        if wb_meta is None:
            return
        up_dir = BASE / dx / "03_UPLOAD"
        rem_dir = BASE / dx / "02_REM_BG"
        if not up_dir.is_dir():
            return
        for f in sorted(up_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in IMG_EXT:
                continue
            name = f.name
            stem = f.stem
            # BW 合成图
            if stem == f"{dx}_白BW" or stem == f"{dx}_黑BW":
                is_black = stem == f"{dx}_黑BW"
                src_names = []
                src_uids = []
                suffixes = ("黑B", "黑W") if is_black else ("B", "W")
                for suffix in suffixes:
                    cut_name = f"{dx}_{suffix}_cut.png"
                    cut_path = rem_dir / cut_name
                    if cut_path.exists():
                        m = _meta_for(cut_path)
                        src_names.append(cut_name)
                        uid = m.get("uid")
                        if uid:
                            src_uids.append(uid)
                if src_uids and len(src_uids) == len(suffixes):
                    group_id = _meta_for(rem_dir / src_names[0]).get("group_id") or ""
                    try:
                        wb_meta.register_bw(f, uid=_new_uid(f), group_id=group_id,
                                            role="黑BW" if is_black else "白BW",
                                            source_uids=src_uids, source_files=src_names)
                    except Exception as e:
                        print(f"  [贴图流水线] BW元数据注册失败 {f}: {e}", flush=True)
                else:
                    wb_meta.ensure_meta(f, stage="bw", role="黑BW" if is_black else "白BW")
                continue

            # 贴图成品：DXxxxx_黑B_黑T.jpg / DXxxxx_B_白T.jpg 等
            m = re.match(rf"^{re.escape(dx)}_(.+?)_(白T|黑T)$", stem)
            if m:
                role, ttype = m.group(1), m.group(2)
                cut_name = f"{dx}_{role}_cut.png"
                cut_path = rem_dir / cut_name
                if cut_path.exists():
                    cut_meta = _meta_for(cut_path)
                    uid = cut_meta.get("uid")
                    group_id = cut_meta.get("group_id") or ""
                    if uid:
                        try:
                            wb_meta.register_sticker(f, uid=uid, group_id=group_id, role=role,
                                                     parent_uid=uid, cut_file=cut_name)
                        except Exception as e:
                            print(f"  [贴图流水线] 贴图元数据注册失败 {f}: {e}", flush=True)
                        continue
            # 兜底：至少保证 sidecar/uid_map 有条目
            try:
                wb_meta.ensure_meta(f, stage="sticker", role=_role_from_name(name, dx))
                wb_meta.register_image_in_map(BASE / dx, _new_uid(f), "", "sticker",
                                                _role_from_name(name, dx), str(f))
            except Exception as e:
                print(f"  [贴图流水线] 兜底元数据失败 {f}: {e}", flush=True)

    @staticmethod
    def _run_sticker_pipeline(dx, use_timeout=False):
        """运行完整贴图流水线：黑T专用 → 通用贴图 → BW 合成。返回 (ok, msg)。
        每次调用前先清理旧版自动生成的贴图/BW文件，确保反相或重跑后一定重新合成BW。
        use_timeout=True 时，每步 PS 脚本最多运行 STICKER_STEP_TIMEOUT 秒，超时会强制终止并返回失败。
        """
        sticker_script = Path(r"E:\Claude code\ps\ps_sticker_one.py")
        batch_script = Path(r"E:\Claude code\ps\ps_batch_one.py")
        black_script = Path(r"E:\Claude code\ps\process_black.py")
        if not sticker_script.exists():
            return False, "PS贴图脚本不存在"
        if not batch_script.exists():
            return False, "BW合成脚本不存在"

        rem_dir = BASE / dx / "02_REM_BG"
        up_dir = BASE / dx / "03_UPLOAD"
        has_black = rem_dir.is_dir() and any(
            "_黑" in f.name and f.name.lower().endswith("_cut.png")
            for f in rem_dir.iterdir()
        )

        # 清理旧的自动生成贴图/BW文件，避免 ps_batch.py 因文件已存在而跳过BW合成
        auto_patterns = [
            f"{dx}_白BW.jpg", f"{dx}_黑BW.jpg",
            f"{dx}_B_白T.jpg", f"{dx}_W_白T.jpg",
            f"{dx}_B_黑T.jpg", f"{dx}_W_黑T.jpg",
        ]
        if up_dir.is_dir():
            for name in auto_patterns:
                fp = up_dir / name
                if fp.exists():
                    try:
                        fp.unlink()
                        print(f"  [贴图流水线] 清理旧文件: {dx}/{name}", flush=True)
                    except Exception:
                        pass

        runner = _run_ps_script_with_timeout if use_timeout else lambda cmd, cwd=None, label="PS脚本": _run_ps_script_sync(cmd, cwd=cwd, label=label)

        # 1) 黑T专用贴图（如果存在黑B/黑W/黑BW）
        if has_black:
            if not black_script.exists():
                return False, "黑T贴图脚本(process_black.py)不存在"
            ok, msg = runner([sys.executable, str(black_script), dx], label="黑T贴图")
            if not ok:
                return False, f"黑T贴图失败: {dx} ({msg})"

        # 2) 通用 B/W/BW 贴图（有黑版对应文件时自动跳过黑T输出，只做白T）
        ok, msg = runner([sys.executable, str(sticker_script), dx], label="PS贴图")
        if not ok:
            return False, f"PS贴图失败: {dx} ({msg})"

        # 2.5) 额外随机 W 胚衣贴图（当前如 W3.psd），不影响原有贴图结果
        try:
            from w_mockup_extra import generate_w_template_mockup
            w_ok, w_msg = generate_w_template_mockup(dx, BASE, runner)
        except Exception as e:
            w_ok, w_msg = False, f"W胚衣贴图异常: {e}"
        print(f"  [贴图流水线] {w_msg}", flush=True)

        # 3) 用贴好的 B/W 合成 BW
        ok, msg = runner([sys.executable, str(batch_script), dx], label="BW合成")
        if not ok:
            return True, f"贴图完成，但BW合成失败: {dx} ({msg})"

        msg_prefix = "黑T+白T贴图+BW合成" if has_black else "PS贴图+BW合成"

        # 4) 注册贴图/BW 成品元数据
        Handler._register_uploads(dx)

        return True, f"{msg_prefix}完成: {dx}"

    # PS贴图：黑T优先用黑版专用文件 → 通用文件做白T → 合成BW
    def _ps_sticker(self, dx):
        if not re.match(r"^DX\d+$", dx):
            self._send_json({"ok": False, "msg": "DX号非法"}); return

        _ensure_sticker_worker()
        _STICKER_QUEUE.put({"dx": dx})
        with _STICKER_STATUS_LOCK:
            pending = _STICKER_STATUS["pending"] = _STICKER_QUEUE.qsize()
            current = _STICKER_STATUS["current"]
        msg = "已加入贴图队列"
        if current:
            msg += f"，当前正在处理 {current}"
        if pending > 1:
            msg += f"，前面还有 {pending - 1} 个任务"
        self._send_json({"ok": True, "queued": True, "pending": pending, "msg": msg})

    # 贴图队列状态查询（单张 + 批量共用）
    def _sticker_status(self):
        with _STICKER_STATUS_LOCK:
            running = _STICKER_STATUS["running"]
            pending = _STICKER_STATUS["pending"]
            current = _STICKER_STATUS["current"]
            last_result = _STICKER_STATUS["last_result"]

        if running or pending > 0:
            msg = "贴图队列运行中"
            if current:
                msg += f"：当前 {current}"
            if pending:
                msg += f"，还剩 {pending} 个任务"
            self._send_json({"done": False, "running": running, "pending": pending, "current": current, "msg": msg})
            return

        if last_result:
            with _STICKER_STATUS_LOCK:
                _STICKER_STATUS["last_result"] = None
            self._send_json({"done": True, "ok": last_result.get("ok", True), "msg": last_result.get("msg", ""), "results": last_result.get("results", [])})
            return

        self._send_json({"done": True, "ok": True, "msg": "无结果", "results": []})

    # BW合成（独立入口：仅用已贴好的 B/W 合成 BW）
    def _ps_batch(self, dx):
        if not re.match(r"^DX\d+$", dx):
            self._send_json({"ok": False, "msg": "DX号非法"}); return
        ps_script = Path(r"E:\\Claude code\\ps\\ps_batch_one.py")
        if not ps_script.exists():
            self._send_json({"ok": False, "msg": "BW合成脚本不存在"}); return
        # 保持立即返回，后台线程等待 PS 完成后注册元数据
        def _run_and_register():
            try:
                proc = run_minimized([sys.executable, str(ps_script), dx], wait=True)
                if proc.returncode == 0:
                    Handler._register_uploads(dx)
            except Exception as e:
                print(f"  [BW合成] 后台注册失败: {e}", flush=True)
        import threading
        threading.Thread(target=_run_and_register, daemon=True).start()
        self._send_json({"ok": True, "msg": f"已启动 BW合成: {dx}，PS将接管屏幕"})

    # 03_UPLOAD 贴图文件详情（按 BW / B / W 分组展示成品缩略图）
    def _upload_detail(self, dx, has_up):
        if not has_up:
            return '<div class="upload-bar empty"><span class="tag-no">\u23f3 \u672a\u8d34\u56fe</span></div>'
        up_dir = BASE / dx / "03_UPLOAD"
        if not up_dir.is_dir():
            return '<div class="upload-bar empty"><span class="tag-no">\u23f3 \u672a\u8d34\u56fe</span></div>'
        files = sorted(f for f in up_dir.iterdir() if f.suffix.lower() in ('.png','.jpg','.jpeg'))
        if not files:
            return '<div class="upload-bar empty"><span class="tag-no">\u23f3 \u672a\u8d34\u56fe</span></div>'

        # 按 BW / B / W / 其他 分组
        groups = {}
        for f in files:
            g = self._up_group(f.name, dx)
            groups.setdefault(g, []).append(f)
        group_order = ['BW', 'B', 'W', '其他']

        rows = []
        for g in group_order:
            if g not in groups:
                continue
            thumbs = []
            for f in sorted(groups[g], key=lambda x: x.name):
                thumb = get_thumb(dx, "up", f.name)
                if not thumb:
                    continue
                ts = int(f.stat().st_mtime)
                label = self._up_label(f.name, dx)
                thumbs.append(
                    f'<div class="up-item">'
                    f'<div class="up-thumb cell">'
                    f'<img src="/thumb?dx={dx}&kind=up&file={quote(f.name)}&t={ts}" onclick="openFolder(\'{dx}\',\'up\')">'
                    f'</div>'
                    f'<div class="up-label" title="{f.name}">{label}</div>'
                    f'</div>'
                )
            if not thumbs:
                continue
            badge_class = {'BW': 'badge-bw', 'B': 'badge-b', 'W': 'badge-w'}.get(g, 'badge-other')
            rows.append(
                f'<div class="up-group">'
                f'<div class="up-group-header"><span class="badge {badge_class}">{g}</span></div>'
                f'<div class="up-group-imgs">' + ''.join(thumbs) + '</div>'
                f'</div>'
            )

        gallery = '<div class="up-gallery">' + ''.join(rows) + '</div>'
        return f'<div class="upload-bar has-up"><div class="up-header"><span class="tag-up">\U0001f4ce \u5df2\u8d34\u56fe</span><span class="up-count">{len(files)} 张</span></div>{gallery}</div>'

    def _up_group(self, name, dx):
        """根据文件名判断成品属于 BW / B / W / 其他。"""
        stem = Path(name).stem
        if 'BW' in stem:
            return 'BW'
        if stem.startswith(f"{dx}_B_") or stem.endswith("_B"):
            return 'B'
        if stem.startswith(f"{dx}_W_") or stem.endswith("_W"):
            return 'W'
        return '其他'

    def _up_label(self, name, dx):
        """生成成品缩略图下方的小标签（如 白T / 黑T / 白 / 黑）。"""
        stem = Path(name).stem
        label = stem[len(dx):] if stem.startswith(dx) else stem
        label = label.strip('_')
        # 去掉分组标识，保留颜色/版型描述
        label = re.sub(r'^(B|W)_', '', label)
        label = re.sub(r'_?(BW)$', '', label)
        label = label.replace('_', ' ').strip()
        return label if label else '成品'

    # \u653e\u5927\u53bb\u80cc\u56fe\u52302046x2046
    def _upscale_rem(self, dx, file):
        if not re.match(r"^DX\d+$", dx) or "/" in file or "\\" in file:
            self._send_json({"ok": False, "msg": "\u53c2\u6570\u975e\u6cd5"}); return
        path = BASE / dx / "02_REM_BG" / file
        if not path.exists():
            self._send_json({"ok": False, "msg": "\u6587\u4ef6\u4e0d\u5b58\u5728"}); return
        try:
            img = Image.open(path)
            w, h = img.size
            if w == 2046 and h == 2046:
                self._send_json({"ok": True, "msg": "\u5df2\u662f2046x2046"}); return
            img = img.resize((2046, 2046), Image.LANCZOS)
            img.save(path)
            # \u6e05\u7f29\u7565\u56fe\u7f13\u5b58
            for tf in THUMB_DIR.glob(f"{dx}__rem__{file}.*"):
                try: tf.unlink()
                except: pass
            self._send_json({"ok": True, "msg": f"\u5df2\u653e\u5927: {w}x{h} \u2192 2046x2046"})
        except Exception as e:
            self._send_json({"ok": False, "msg": f"\u653e\u5927\u5931\u8d25: {e}"})

    # 反相去背图并自动跑黑T贴图（静态方法：实际执行逻辑，供队列 worker 调用）
    @staticmethod
    def _run_single_invert_sync(dx, file):
        if not re.match(r"^DX\d+$", dx) or "/" in file or "\\" in file:
            raise ValueError("参数非法")
        if "_黑" in file:
            raise ValueError("已是黑版专用图，无需反相")
        if not file.lower().endswith("_cut.png"):
            raise ValueError("仅支持 _cut.png 去背图")

        src = BASE / dx / "02_REM_BG" / file
        if not src.exists():
            raise FileNotFoundError(f"{file} 不存在")

        # 生成目标文件名：DX0255_B_cut.png -> DX0255_黑B_cut.png
        stem = file[:-len("_cut.png")]
        suffix = stem[len(dx)+1:] if stem.startswith(dx + "_") else ""
        if not suffix:
            raise ValueError("无法解析文件名后缀")
        dest_name = f"{dx}_黑{suffix}_cut.png"
        dest = BASE / dx / "02_REM_BG" / dest_name

        try:
            img = Image.open(src).convert("RGBA")
            r, g, b, a = img.split()
            rgb = Image.merge("RGB", (r, g, b))
            inv_rgb = ImageOps.invert(rgb)
            inv = Image.merge("RGBA", (*inv_rgb.split(), a))
            inv.save(dest)
        except Exception as e:
            raise RuntimeError(f"反相失败: {e}")

        # 注册黑版变体元数据
        if wb_meta is not None:
            try:
                src_meta = _meta_for(src)
                parent_uid = src_meta.get("uid")
                gid = src_meta.get("group_id") or ""
                black_role = f"黑{suffix}"
                if parent_uid:
                    wb_meta.register_rembg(dest, uid=_new_uid(dest), group_id=gid,
                                           role=black_role, parent_uid=parent_uid,
                                           ai_file=file)
                else:
                    wb_meta.ensure_meta(dest, group_id=gid, stage="rembg", role=black_role)
            except Exception as e:
                print(f"  [反相] 元数据注册失败 {dest}: {e}", flush=True)

        # 清缩略图缓存
        for tf in THUMB_DIR.glob(f"{dx}__rem__{dest_name}.*"):
            try: tf.unlink()
            except: pass

        # 仅生成黑版反相图，不自动跑贴图流水线；贴图由用户单独触发

    # 反相 HTTP 入口：加入统一队列，立即返回
    def _invert_rem(self, dx, file):
        if not re.match(r"^DX\d+$", dx) or "/" in file or "\\" in file:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        if "_黑" in file:
            self._send_json({"ok": False, "msg": "已是黑版专用图，无需反相"}); return
        if not file.lower().endswith("_cut.png"):
            self._send_json({"ok": False, "msg": "仅支持 _cut.png 去背图"}); return

        _ensure_invert_worker()
        _INVERT_QUEUE.put({"type": "single", "dx": dx, "file": file})
        with _INVERT_STATUS_LOCK:
            pending = _INVERT_STATUS["pending"] = _INVERT_QUEUE.qsize()
            current = _INVERT_STATUS["current"]
        msg = "已加入反相队列"
        if current:
            msg += f"，当前正在处理 {current}"
        if pending > 1:
            msg += f"，前面还有 {pending - 1} 个任务"
        self._send_json({"ok": True, "queued": True, "pending": pending, "msg": msg})

    # 批量反相 HTTP 入口：加入统一队列，立即返回
    def _batch_invert_rem(self):
        from urllib.parse import parse_qs
        qs = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        dx_str = qs.get("dx", [""])[0]
        if not dx_str:
            self._send_json({"ok": False, "msg": "缺少 dx 参数"}); return
        dx_list = [d.strip() for d in dx_str.split(",") if d.strip()]
        if not dx_list:
            self._send_json({"ok": False, "msg": "无效的 dx 参数"}); return

        _ensure_invert_worker()
        _INVERT_QUEUE.put({"type": "batch", "dx_list": dx_list})
        with _INVERT_STATUS_LOCK:
            pending = _INVERT_STATUS["pending"] = _INVERT_QUEUE.qsize()
            current = _INVERT_STATUS["current"]
        msg = f"批量反相已加入队列，共 {len(dx_list)} 款"
        if current:
            msg += f"，当前正在处理 {current}"
        if pending > 1:
            msg += f"，前面还有 {pending - 1} 个任务"
        self._send_json({"ok": True, "queued": True, "pending": pending, "count": len(dx_list), "msg": msg})

    # 反相队列结果查询（兼容单张 + 批量）
    def _batch_invert_result(self):
        with _INVERT_STATUS_LOCK:
            running = _INVERT_STATUS["running"]
            pending = _INVERT_STATUS["pending"]
            current = _INVERT_STATUS["current"]
            last_result = _INVERT_STATUS["last_result"]

        if running or pending > 0:
            msg = "反相队列运行中"
            if current:
                msg += f"：当前 {current}"
            if pending:
                msg += f"，还剩 {pending} 个任务"
            self._send_json({"done": False, "running": running, "pending": pending, "current": current, "msg": msg})
            return

        # 队列空闲：消费上次结果
        if last_result:
            with _INVERT_STATUS_LOCK:
                _INVERT_STATUS["last_result"] = None
            self._send_json({"done": True, "ok": last_result.get("ok", True), "msg": last_result.get("msg", ""), "results": last_result.get("results", [])})
            return

        self._send_json({"done": True, "ok": True, "msg": "无结果", "results": []})

    def _refresh_thumb(self, dx, stem):
        if not re.match(r"^DX\d+$", dx) or not stem or "/" in stem or "\\" in stem:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        rem_dir = BASE / dx / "02_REM_BG"
        cut_name = f"{stem}_cut.png"
        cut_path = rem_dir / cut_name
        if not cut_path.exists():
            # 仍然没有去背图
            self._send_json({"ok": True, "found": False, "msg": f"{stem} 还没有去背图"})
            return
        # 删旧缩略图缓存（若有）
        thumb_name = f"{dx}__rem__{cut_name}.jpg"
        thumb = THUMB_DIR / thumb_name
        if thumb.exists():
            try:
                thumb.unlink()
            except Exception:
                pass
        # 重新生成
        new_thumb = get_thumb(dx, "rem", cut_name)
        if new_thumb:
            cache_bust = int(time.time() * 1000)
            url = f"/thumb?dx={dx}&kind=rem&file={quote(cut_name)}&_={cache_bust}"
            # 返回尺寸，供前端决定是否显示放大按钮
            try:
                with Image.open(cut_path) as _img:
                    _w, _h = _img.size
            except Exception:
                _w, _h = 0, 0
            self._send_json({"ok": True, "found": True, "msg": "已刷新",
                             "url": url, "file": cut_name, "w": _w, "h": _h})
        else:
            self._send_json({"ok": False, "found": False, "msg": f"刷新失败：{cut_name} 无法读取"})

    # 改名：_B / _W / _BW 互转（如 DX0264_B → DX0264_W / DX0264_BW）
    def _rename_stem(self, dx, stem, target):
        if not re.match(r"^DX\d+$", dx) or not stem or "/" in stem or "\\" in stem:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        source = stem[-2:] if stem.endswith(("_B", "_W")) else (stem[-3:] if stem.endswith("_BW") else "")
        if source not in ("_B", "_W", "_BW"):
            self._send_json({"ok": False, "msg": "源文件名后缀必须是 _B/_W/_BW"}); return
        if target not in ("B", "W", "BW"):
            self._send_json({"ok": False, "msg": "目标必须是 B/W/BW"}); return
        if source == "_" + target:
            self._send_json({"ok": False, "msg": "源和目标相同"}); return
        prefix = stem[:-len(source)]  # DX0264
        new_stem = prefix + "_" + target
        ai_new = new_stem + ".png"
        rem_new = new_stem + "_cut.png"
        errors = []
        renamed = []
        # 改 AI 图
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            src = BASE / dx / "01_AI" / (stem + ext)
            if src.exists():
                dst = BASE / dx / "01_AI" / ai_new
                if dst.exists():
                    send_to_recycle_bin(str(dst))
                    errors.append(f"旧{ai_new}已送回收站")
                src.rename(dst)
                renamed.append(f"{stem}{ext}→{ai_new}")
                break
        # 改 REM_BG 图
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            src = BASE / dx / "02_REM_BG" / (stem + "_cut" + ext)
            if src.exists():
                dst = BASE / dx / "02_REM_BG" / rem_new
                if dst.exists():
                    send_to_recycle_bin(str(dst))
                    errors.append(f"旧{rem_new}已送回收站")
                src.rename(dst)
                renamed.append(f"{stem}_cut{ext}→{rem_new}")
                break
        if not renamed:
            self._send_json({"ok": False, "msg": f"{dx} 未找到 {stem} 相关文件"})
            return
        # 清理缩略图缓存
        for tf in THUMB_DIR.glob(f"{dx}__*__{stem}*"):
            try: tf.unlink()
            except: pass
        msg = "、".join(renamed) + ("。" + "；".join(errors) if errors else "")
        self._send_json({"ok": True, "msg": msg})

    # 修复文件名不匹配：扫描所有款，AI和REM_BG文件名自动对齐
    def _repair_names(self):
        """扫描所有 DX，修复文件名不一致问题：
           - REM_BG 有 _BW_cut.png 但 AI 仍是 _B.png → 把 AI 也改名为 _BW.png
           - AI 有 _BW.png 但 REM_BG 仍是 _B_cut.png → 把 REM_BG 也改名为 _BW_cut.png
        """
        fixed = []
        for d in sorted(BASE.iterdir()):
            if not d.is_dir() or not re.match(r"^DX\d+$", d.name):
                continue
            dx = d.name
            ai_dir = d / "01_AI"
            rem_dir = d / "02_REM_BG"
            if not ai_dir.is_dir() and not rem_dir.is_dir():
                continue

            # 收集 AI 文件名 stem（去后缀）
            ai_stems = set()
            if ai_dir.is_dir():
                for f in ai_dir.iterdir():
                    if f.is_file() and is_generated_ai(f.name, dx):
                        ai_stems.add(os.path.splitext(f.name)[0])

            # 收集 REM_BG stem（去 _cut.png 后缀）
            rem_stems = set()
            if rem_dir.is_dir():
                for f in rem_dir.iterdir():
                    if f.is_file() and f.name.endswith("_cut.png"):
                        rem_stems.add(f.name[:-len("_cut.png")])

            # 1. REM_BG 有 _BW_cut，但 AI 仍是 _B / _W → 改 AI
            for rs in rem_stems:
                if not rs.endswith("_BW"):
                    continue
                prefix = rs[:-3]  # 去掉 _BW
                ai_bw_stem = prefix + "_BW"
                if ai_bw_stem in ai_stems:
                    continue  # AI 已有 BW 版
                # 找 AI 的 _B 或 _W
                for alt in (prefix + "_B", prefix + "_W"):
                    if alt in ai_stems:
                        src = ai_dir / (alt + ".png")
                        dst = ai_dir / (ai_bw_stem + ".png")
                        if src.exists():
                            if dst.exists():
                                send_to_recycle_bin(str(dst))
                            src.rename(dst)
                            fixed.append(f"{dx}/{alt}.png→{ai_bw_stem}.png")
                            ai_stems.discard(alt)
                            ai_stems.add(ai_bw_stem)
                            break

            # 2. AI 有 _B / _W，但 REM_BG 有 _BW_cut（另一边已改）→ 同步改 REM_BG
            for a_stem in list(ai_stems):
                if not (a_stem.endswith("_B") or a_stem.endswith("_W")):
                    continue
                prefix = a_stem[:-2]
                bw_stem = prefix + "_BW"
                if bw_stem in rem_stems:
                    src = rem_dir / (a_stem + "_cut.png")
                    dst = rem_dir / (bw_stem + "_cut.png")
                    if src.exists():
                        if dst.exists():
                            send_to_recycle_bin(str(dst))
                        src.rename(dst)
                        fixed.append(f"{dx}/{a_stem}_cut.png→{bw_stem}_cut.png")
                        rem_stems.discard(a_stem)
                        rem_stems.add(bw_stem)

        if fixed:
            self._send_json({"ok": True, "msg": f"已修复 {len(fixed)} 处: {{', '.join(fixed[:10])}}{{'...' if len(fixed)>10 else ''}}"})
        else:
            self._send_json({"ok": True, "msg": "所有文件名已一致，无需修复"})

    # ── 辅助 ────────────────────────────────────────
    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, *a, **kw):
        pass


# ── 入口 ────────────────────────────────────────────
def main():
    # 先把 stdout/stderr 写入文件日志，避免最小化控制台后输出丢失
    _setup_file_logging()

    # 首次启动若发现遗留锁/未恢复config，自动清理
    if CONFIG_BACKUP.exists():
        _restore_config()
        print("  ⚠ 检测到上次未完成的去背任务，已恢复 config.json")
    lock = TEMP_REMBG / ".rembg_lock"
    if lock.exists():
        try: lock.unlink()
        except Exception: pass

    os.chdir(str(CHECK))
    url = f"http://localhost:{PORT}/"
    print(f"  AI vs 去背 对比预览  →  {url}")
    print(f"  点缩略图：打开文件夹   x：送回收站   [重新去背]：驱动美图")
    print(f"  关闭此窗口停止服务")

    # 启动反相队列工作线程（单张 + 批量统一串行处理）
    _ensure_invert_worker()

    # 启动 PS 贴图队列工作线程（单款 + 批量统一串行处理 + 超时兜底）
    _ensure_sticker_worker()

    # 后台预扫描：启动后立即全量扫描，把结果 warming 到缓存，
    # 这样用户首次打开首页时就是热缓存，几乎秒开。
    def _warm_cache():
        try:
            t0 = time.time()
            scan_projects()
            print(f"  [warm] 扫描完成，耗时 {time.time()-t0:.2f}s，结果已缓存", flush=True)
        except Exception as e:
            print(f"  [warm] 预扫描失败: {e}", flush=True)
    threading.Thread(target=_warm_cache, daemon=True).start()

    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        # 退出前确保 config 已恢复
        _restore_config()
        print("\n  已停止")


if __name__ == "__main__":
    main()
