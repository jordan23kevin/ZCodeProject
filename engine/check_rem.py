"""01_CHECK_REM v2.2.3 — AI图 vs 去背图 vs 贴图成品 对比预览（本地服务）

仿 01_CHECK (check_sync.py) 的网页预览，但对比的是每个 DX 款的
01_AI 生成图、02_REM_BG 去背图、03_UPLOAD 贴图成品，方便人工判断
去背质量、贴图完整度与黑T专用图优先级。

功能 v2.2.8（黑衫白墨打底显色）：
  - 「反黑」（单张 _invert_rem / 批量 batch_invert_rem）改为 black_shirt_print_optimize：
    自适应浓度白墨打底 add_white_underbase（越暗白墨越厚 max0.9/min0.05，阈值130，
    edge_feather5，boost_sat0.35 保饱和色）+ 轻度暗部提亮。模拟真实 DTG 黑衫
    『先喷白墨再喷彩色』，使极暗区域在黑布上可见，同时保留全部原色、不漂成白。
  - 取代旧版『非透明像素涂纯白/纯黑剪影』，以及 v2.2.7 的纯提亮（救不了近黑设计：
    PS place_design.jsx 从不铺白底，纯黑印黑布物理不可见）。白墨打底烘进 _黑W_cut.png
    本身，无需改 PS 脚本即可显色。白版仍走 enhance_dark_print_for_black_shirt(shirt=white)
    压暗亮部保色。
  - 实测 DX0635：近黑像素 64万→4413、接近白(>245)=0、红字 (101,16,23)→(127,52,59) 保色。
  - 注意：本进程常驻，改 check_rem.py 后须 kill 端口 8766 进程由 bridge 守护重拉才生效。

功能 v2.2.7：
  - 修复单面款（02_REM_BG 只有 W 或只有 B）被误判走平铺图贴图的问题：
    _run_one_sticker 改为按「去掉 黑/白 前缀后的真实面集合」判定单面。
    只有 W（即使含 _黑W/_白W 这类反黑/反白专用图）或只有 B → 模特图贴图（white_t_mockup 胚衣）；
    含 BW/WB 或同时有 B+W → 平铺图贴图。has_black/has_white 仅保留给平铺流程内部使用。
    现象样例：DX0611（W + _黑W + _白W）此前产出 _W_白T/_W_黑T 平铺图，修复后改出 _W1_白T 等模特图。
  - PS 脚本（ps-compositing 仓库）增加单面款旧产物兜底清理：
    wb_sticker_ps.py / process_black.py / process_white.py 贴图前按真实面数清理 03_UPLOAD
    中已不存在的互补面胚衣图与旧 BW 平铺图；ps_batch.py 合成 BW 前对单面款跳过并删除残留平铺图。
  - 记录运行注意事项：lovart_bridge.bat 重启不会带走已运行的 check_rem 子进程，
    修改 check_rem.py 后需先 kill 旧进程，由 lovart_bridge 守护线程重拉才会加载新代码。

功能 v2.2.6：
  - Photoshop 贴图速度优化（保证效果前提下）：
    - wb_sticker_ps.py / process_black.py 单 DX 内复用 COM 会话，缓存胚衣文档
    - 同一设计图按正/背缩放后只打开一次，复用设计图文档贴到白/黑胚衣
    - ps_batch.py 一次打开 B/W 正背图，连续执行白/黑动作后统一关闭
    - 用主动轮询替代硬编码 sleep，减少空等

功能 v2.2.5：
  - 修复黑版专用图反相后不重新贴图的问题：支持版本号后缀（黑B2 / 黑W1 / 黑BW3 等）
  - process_black.py 与 wb_sticker_ps.py 统一使用 parse_side_suffix 解析 B/W/BW/WB 及其版本号

功能 v2.2.3：
  - 批量贴图与批量反相彻底分离：批量贴图不再处理黑版文件/不再反相，仅做白T贴图+BW合成
  - Photoshop 生命周期改为「按任务集一次性开启」：单款点贴图做完该款关闭；勾选多款批量贴图全部做完再关闭
  - Photoshop 改为后台隐藏运行，不再弹出/最大化窗口干扰前台
  - 页面顶部新增「PS 任务摘要」状态条，实时轮询显示当前贴图/BW合成/反相进度
  - 贴图旋转角度从 +1°（顺时针）改为 -1°（逆时针）
  - 已存在的贴图/BW文件会被直接覆盖，方便重新贴图

功能 v2.2.2：
  - 支持版本号后缀：B1/B2、W1/W2、BW1/WB1 等均视为同一 base_role 的不同版本
  - 同 base_role 多版本横向排列展示，便于对比挑选最佳版本
  - 移除 pipeline 状态标签（🎨AI / ✂️ / 📎）
  - 改名支持任意目标后缀（如 B → BW / RED1 / W2 等）
  - 贴图成品分组兼容带版本号的文件名

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
  - 修复反相后 BW 合成图不生成的问题：贴图流水线会先清理旧的自动生成贴图/BW文件，再重新贴图+合成BW
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
__version__ = "2.2.8"
VERSION = __version__
import os, re, json, time, hashlib, ctypes, subprocess, sys, shutil, requests, io, threading, numpy as np
from pathlib import Path
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from PIL import Image
import cv2
from ctypes import wintypes

# 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 控制台打印 emoji/生僻字时崩溃
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

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

# 磁盘缓存：服务重启后首次加载可秒开，避免重新扫描 300+ 款
_SCAN_DISK_CACHE_FILE = CHECK / "_scan_cache.json"
_SCAN_DISK_CACHE_TTL = 3600  # 1 小时

# Photoshop 任务锁：同一时刻只跑一套贴图/BW 任务，防止多线程同时操作 PS
_PS_TASK_LOCK = threading.Lock()

# Photoshop / 后台任务状态摘要（供 Web 页面轮询）
_PS_STATUS = {
    "running": False,
    "task": "",
    "current_dx": "",
    "progress": "",
    "detail": "",
    "updated_at": 0,
}
_PS_STATUS_LOCK = threading.Lock()


def _set_ps_status(running=False, task="", current_dx="", progress="", detail=""):
    """更新 PS / 后台任务状态，detail 可包含更详细的说明。"""
    with _PS_STATUS_LOCK:
        _PS_STATUS["running"] = running
        _PS_STATUS["task"] = task
        _PS_STATUS["current_dx"] = current_dx
        _PS_STATUS["progress"] = progress
        _PS_STATUS["detail"] = detail
        _PS_STATUS["updated_at"] = time.time()


def _clear_ps_status():
    """清空 PS / 后台任务状态。"""
    _set_ps_status(False, "", "", "", "")


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
    """旧项目迁移条件：无 uid_map 或 uid_map 为空。
    有 uid_map 即视为已迁移，不再逐文件检查 sidecar（加速扫描）。"""
    if wb_meta is None:
        return False
    return not _uid_map_exists(dx_dir)


def _meta_for(file_path):
    """读取单文件 sidecar，失败或禁用时返回空 dict"""
    if wb_meta is None:
        return {}
    try:
        m = wb_meta.read_meta(file_path)
        return m or {}
    except Exception:
        return {}


def _parse_stem(stem, dx):
    """把 DXxxxx_XN 解析为 (base_stem, version, base_role)；N 为数字版本号。
    支持 _cut 后缀、黑版前缀（黑B/黑W/黑BW）。"""
    if not stem.startswith(dx + "_"):
        return stem, "", ""
    suffix = stem[len(dx)+1:]
    if suffix.endswith("_cut"):
        suffix = suffix[:-4]
    m = re.match(r'^(.*?)(\d+)$', suffix)
    if m:
        base_suffix, version = m.group(1), m.group(2)
    else:
        base_suffix, version = suffix, ""
    base_stem = f"{dx}_{base_suffix}"
    return base_stem, version, base_suffix


def _role_from_name(fname, dx):
    """从文件名推断基础 role（元数据不可用时回退）；DXxxxx_XN → X"""
    stem, _ = os.path.splitext(fname)
    _, _, base_role = _parse_stem(stem, dx)
    return base_role or "?"


def _new_uid(path):
    """为新输出文件生成稳定 UID（基于文件 MD5）"""
    if wb_meta is None:
        return None
    try:
        return f"UID_UPLOAD_{wb_meta.compute_md5(path)[:16]}"
    except Exception:
        return None


def scan_projects(force=False):
    """返回 [{dx, pairs:[...], black_variants:[...]}]。
    优先读内存缓存，再读磁盘缓存，最后才全量扫描。"""
    global _SCAN_PROJECTS_CACHE
    with _SCAN_PROJECTS_CACHE["lock"]:
        if not force and _SCAN_PROJECTS_CACHE["projects"] is not None:
            if time.time() - _SCAN_PROJECTS_CACHE["timestamp"] < _SCAN_PROJECTS_TTL:
                return _SCAN_PROJECTS_CACHE["projects"]

    # 尝试磁盘缓存（服务重启后首次加载可秒开）
    if not force:
        try:
            if _SCAN_DISK_CACHE_FILE.exists():
                data = json.loads(_SCAN_DISK_CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - data.get("timestamp", 0) < _SCAN_DISK_CACHE_TTL:
                    projects = data["projects"]
                    with _SCAN_PROJECTS_CACHE["lock"]:
                        _SCAN_PROJECTS_CACHE["projects"] = projects
                        _SCAN_PROJECTS_CACHE["timestamp"] = time.time()
                    return projects
        except Exception:
            pass

    projects = _scan_projects_impl()
    with _SCAN_PROJECTS_CACHE["lock"]:
        _SCAN_PROJECTS_CACHE["projects"] = projects
        _SCAN_PROJECTS_CACHE["timestamp"] = time.time()
    # 写入磁盘缓存
    try:
        _SCAN_DISK_CACHE_FILE.write_text(
            json.dumps({"timestamp": time.time(), "projects": projects}, ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass
    return projects


def _scan_projects_impl():
    """实际全量扫描：返回项目列表。"""
    projects = []
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not re.match(r"^DX\d+$", d.name):
            continue
        dx = d.name
        ai_dir = d / "01_AI"
        rem_dir = d / "02_REM_BG"

        # 先收集文件列表，用于和 uid_map 做快速对比
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

        # 迁移旧项目：uid_map 不存在/为空或任意 AI/rembg 文件缺少 sidecar
        if _need_migrate_dx(d):
            try:
                wb_meta.migrate_dx(d)
            except Exception as e:
                print(f"  [wb_meta] 迁移 {dx} 失败: {e}", flush=True)

        # 读取 uid_map 并建立路径索引：每个 DX 只读一次，避免扫描时逐文件算 MD5
        path_to_meta = {}
        if wb_meta is not None:
            try:
                uid_map = wb_meta.read_uid_map(d)
                for entry in uid_map.get("images", {}).values():
                    rel = entry.get("file")
                    if rel:
                        path_to_meta[rel] = entry
            except Exception as e:
                print(f"  [scan] 读取 uid_map 失败 {dx}: {e}", flush=True)

        def _meta_for_path(path):
            """用相对路径从本款 uid_map 索引中查元数据；找不到再回退。"""
            if wb_meta is None:
                return {}
            try:
                rel = str(path.relative_to(d))
                entry = path_to_meta.get(rel)
                if entry:
                    return dict(entry)
            except Exception:
                pass
            return _meta_for(path)

        ai_meta_by_file = {}
        rem_meta_by_file = {}
        if wb_meta is not None:
            for af in ai_files:
                ai_meta_by_file[af] = _meta_for_path(ai_dir / af)
            for rf in rem_files:
                rem_meta_by_file[rf] = _meta_for_path(rem_dir / rf)

        # 以 AI 图为主键配对；剩余的 _cut.png（无对应AI图）也单列
        rem_by_stem = {}
        for rf in rem_files:
            stem = rf[:-len("_cut.png")]  # 去掉 _cut.png 后缀（含扩展名）
            rem_by_stem.setdefault(stem, []).append(rf)

        pairs = []
        covered_rem = set()
        for af in ai_files:
            stem = os.path.splitext(af)[0]
            base_stem, version, base_role = _parse_stem(stem, dx)
            ai_meta = ai_meta_by_file.get(af, {})
            ai_uid = ai_meta.get("uid")
            group_id = ai_meta.get("group_id") or ""
            role = ai_meta.get("role") or base_role

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
                "base_stem": base_stem,
                "version": version,
                "base_role": base_role,
                "ai_file": af,
                "rem_file": matched[0] if matched else None,
                "group_id": group_id or rem_meta.get("group_id", ""),
                "ai_uid": ai_uid,
                "rem_uid": rem_meta.get("uid") if matched else None,
                "ai_stage": ai_meta.get("stage", "ai"),
                "rem_stage": rem_meta.get("stage", "rembg") if matched else None,
                "role": role,
            })

        # 黑版变体：_黑B/_黑W/_黑BW 等（含版本号 _黑B1），group_id 强制归属到对应 pair 以支持前端分组
        black_variants = []
        for rf in sorted(rem_files):
            if rf in covered_rem or "_黑" not in rf:
                continue
            stem = rf[:-len("_cut.png")]
            base_stem, version, base_role = _parse_stem(stem, dx)
            m = rem_meta_by_file.get(rf, {})
            group_id = ""
            parent_uid = m.get("parent_uid")
            # 优先按 parent_uid 或 rem_uid 找到对应 pair
            if parent_uid:
                for pr in pairs:
                    if pr.get("ai_uid") == parent_uid or pr.get("rem_uid") == parent_uid:
                        group_id = pr.get("group_id", "")
                        break
            # 再按基础文件名（DXxxxx_黑B1 → DXxxxx_B1）回退
            if not group_id:
                plain_stem = stem.replace("黑", "", 1)
                for pr in pairs:
                    if pr["stem"] == plain_stem:
                        group_id = pr.get("group_id", "")
                        break
            # 再按 base_stem（DXxxxx_黑B → DXxxxx_B）回退
            if not group_id:
                plain_base = base_stem.replace("黑", "", 1)
                for pr in pairs:
                    if pr.get("base_stem") == plain_base:
                        group_id = pr.get("group_id", "")
                        break
            # 都匹配不到才使用自身元数据
            if not group_id:
                group_id = m.get("group_id", "")
            black_variants.append({
                "stem": stem,
                "base_stem": base_stem,
                "version": version,
                "base_role": base_role,
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
            base_stem, version, base_role = _parse_stem(stem, dx)
            m = rem_meta_by_file.get(rf, {})
            pairs.append({
                "stem": stem,
                "base_stem": base_stem,
                "version": version,
                "base_role": base_role,
                "ai_file": None,
                "rem_file": rf,
                "group_id": m.get("group_id", ""),
                "ai_uid": None,
                "rem_uid": m.get("uid"),
                "ai_stage": None,
                "rem_stage": m.get("stage", "rembg"),
                "role": m.get("role") or base_role,
            })

        # 该款的日期统一按 DX 文件夹建立日期（YYMMDD）分类，不按文件 mtime
        try:
            dx_date = time.strftime("%y%m%d", time.localtime(d.stat().st_ctime))
        except Exception:
            dx_date = ""

        projects.append({"dx": dx, "date": dx_date, "pairs": pairs, "black_variants": black_variants})

    return projects


def _invalidate_scan_cache():
    """文件变更后清空 scan_projects 缓存，下次请求重新扫描。"""
    global _SCAN_PROJECTS_CACHE
    with _SCAN_PROJECTS_CACHE["lock"]:
        _SCAN_PROJECTS_CACHE["projects"] = None
        _SCAN_PROJECTS_CACHE["timestamp"] = 0
    try:
        if _SCAN_DISK_CACHE_FILE.exists():
            _SCAN_DISK_CACHE_FILE.unlink()
    except Exception:
        pass


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

    # 4. 暂存该单张 AI 图到 _temp_rembg/{DX}/01_AI/
    staging_root = TEMP_REMBG / dx / "01_AI"
    if staging_root.exists():
        shutil.rmtree(str(staging_root), ignore_errors=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(ai_path), str(staging_root / ai_file))
    staged_md5 = [file_md5(str(ai_path))]

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

    # 6. 从 track 移除该图 md5（仅让美图重跑此图，不影响血缘 registry 中的 AI 图 MD5）
    removed = _untrack_md5(staged_md5, dx=dx)

    # 7. 真实驱动美图（新控制台窗口，接管屏幕）
    if not MEITU_SCRIPT.exists():
        _restore_config()
        _restore_one_backup(cut_name, backup_dir, rem_dir)
        shutil.rmtree(str(TEMP_REMBG / dx), ignore_errors=True)
        return False, f"美图脚本不存在: {MEITU_SCRIPT}"

    print(f"  [重去背] {dx}/{ai_file}: 暂存1张, 启动美图...", flush=True)
    print(f"  ⚠ 美图将接管屏幕，请勿动键鼠，等待脚本结束。", flush=True)
    try:
        proc = run_minimized(
            [sys.executable, str(MEITU_SCRIPT)],
            cwd=str(MEITU_SCRIPT.parent),
        )
        ok = proc.returncode == 0
    except Exception as e:
        ok = False
        print(f"  [重去背] {dx}/{ai_file} 美图运行异常: {e}", flush=True)

    # 8. 收尾：恢复 config（无论成功失败）
    _restore_config()

    # 8b. 美图脚本的输出路径是 dirname(subdir)/02_REM_BG = _temp_rembg/{DX}/02_REM_BG
    #     （不是真实目录！因为 subdir 在暂存目录里）。所以要把暂存目录里的新 _cut.png
    #     收集、移动到真实的 02_REM_BG，否则会被当成"没产出"而还原旧图覆盖新图。
    temp_out_dir = TEMP_REMBG / dx / "02_REM_BG"
    if temp_out_dir.is_dir():
        for f in temp_out_dir.glob("*_cut.png"):
            dest = rem_dir / f.name
            rem_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                send_to_recycle_bin(str(dest))  # 先清理同名占位
            shutil.move(str(f), str(dest))
            print(f"  [重去背] 收集新结果 → {dest}", flush=True)
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
    except subprocess.TimeoutExpired:
        ok = False
        print("  [批量去背] 美图超时", flush=True)
    except Exception as e:
        ok = False
        print(f"  [批量去背] 美图异常: {e}", flush=True)
    finally:
        _restore_config()

    # 5. 从临时目录收集结果到真实 DX 文件夹
    for dx, ai_file, stem, cut_name, ai_path, rem_dir, backup_dir, had_old, ai_uid, group_id, role in staged:
        # 从 _temp_rembg/{DX}/02_REM_BG 收集新生成的 _cut.png
        temp_out_dir = TEMP_REMBG / dx / "02_REM_BG"
        if temp_out_dir.is_dir():
            for f in temp_out_dir.glob("*_cut.png"):
                dest = rem_dir / f.name
                rem_dir.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    send_to_recycle_bin(str(dest))
                shutil.move(str(f), str(dest))
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


# ── 暗部/亮部智能显色（替代旧版纯白/纯黑剪影）────────────────────────
def enhance_dark_print_for_black_shirt(design, shirt="black",
        dark_boost=0.55, protect_threshold=140, min_brightness=20,
        sat_compensation=0.3, smooth_radius=9):
    """黑衫/白衫智能显色：仅处理暗部(黑衫)或亮部(白衫)，完整保留颜色。
    替代旧版『非透明像素变纯白/纯黑』剪影。shirt='black' 提亮暗部；shirt='white' 压暗亮部。
    design: PIL RGBA 图。返回 PIL RGBA 图。
    """
    if getattr(design, "mode", None) != "RGBA":
        design = design.convert("RGBA")
    arr = np.array(design)
    rgb = arr[..., :3].astype(np.float32)
    alpha = arr[..., 3].astype(np.float32) / 255.0
    valid = alpha > 0.01
    if not valid.any():
        return design
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    L_norm = L / 255.0
    thresh_norm = protect_threshold / 255.0
    if shirt == "black":
        weight = np.clip((thresh_norm - L_norm) / thresh_norm, 0.0, 1.0)
        target_gamma = max(0.15, 1.0 - dark_boost * 0.7)
        L_target = 255.0 * np.power(L_norm, target_gamma)
        min_mask = (L < min_brightness) & valid
        L_target[min_mask] = np.maximum(L_target[min_mask], min_brightness)
    else:
        weight = np.clip((L_norm - thresh_norm) / (1.0 - thresh_norm), 0.0, 1.0)
        target_gamma = max(0.15, 1.0 + dark_boost * 0.7)
        L_target = 255.0 * np.power(L_norm, target_gamma)
        max_mask = (L > (255 - min_brightness)) & valid
        L_target[max_mask] = np.minimum(L_target[max_mask], 255 - min_brightness)
    weight = weight * alpha
    if smooth_radius > 0:
        sr = int(smooth_radius) | 1
        weight = cv2.GaussianBlur(weight, (sr, sr), 0)
    weight = np.clip(weight, 0.0, 1.0)
    L_final = L * (1 - weight) + L_target * weight
    sat_gain = 1.0 + sat_compensation * weight
    A_final = np.clip((A - 128.0) * sat_gain + 128.0, 0.0, 255.0)
    B_final = np.clip((B - 128.0) * sat_gain + 128.0, 0.0, 255.0)
    lab_final = np.stack([L_final, A_final, B_final], axis=-1).astype(np.uint8)
    bgr = cv2.cvtColor(lab_final, cv2.COLOR_LAB2BGR)
    rgb_final = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    out = np.dstack([rgb_final, arr[..., 3]])
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def add_white_underbase(design, max_white_opacity=0.9, min_white_opacity=0.05,
                        transition_threshold=130, edge_feather=5, boost_sat=0.35):
    """自适应浓度白墨打底（黑衫显色）：越暗白墨越厚，亮/饱和色保留原色。
    模拟真实 DTG 黑衫印花『先喷白墨、再喷彩色』，使极暗区域在黑布上可见，
    同时避免全铺白底导致颜色漂白。design: PIL RGBA 图。返回 PIL RGBA 图。
    """
    if getattr(design, "mode", None) != "RGBA":
        design = design.convert("RGBA")
    arr = np.array(design)
    rgb = arr[..., :3].astype(np.float32)
    alpha = arr[..., 3].astype(np.float32) / 255.0
    valid = alpha > 0.01
    if not valid.any():
        return design
    rgb_u = rgb.astype(np.uint8)
    gray = cv2.cvtColor(rgb_u, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_u, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[..., 1] / 255.0
    th = transition_threshold / 255.0
    white_mask = np.clip((th - gray) / th, 0.0, 1.0)            # 越暗越 1
    white_alpha = min_white_opacity + white_mask * (max_white_opacity - min_white_opacity)
    white_alpha = white_alpha * alpha
    if edge_feather > 0:
        k = int(edge_feather) * 2 + 1
        white_alpha = cv2.GaussianBlur(white_alpha, (k, k), 0)
    white_alpha = np.clip(white_alpha, 0.0, 1.0)
    white = np.ones_like(rgb) * 255.0
    keep = np.clip(gray + boost_sat * sat, 0.0, 1.0)            # 暗但饱和的颜色多保留原色
    color_on_white = white * (1 - keep)[..., None] + rgb * keep[..., None]
    final = rgb * (1 - white_alpha)[..., None] + color_on_white * white_alpha[..., None]
    final = np.clip(final, 0, 255).astype(np.uint8)
    out = np.dstack([final, arr[..., 3]])
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def black_shirt_print_optimize(design):
    """黑衫终极显色流水线：自适应白墨打底 + 轻度暗部提亮 + 饱和补偿。"""
    step1 = add_white_underbase(design)
    step2 = enhance_dark_print_for_black_shirt(
        step1, shirt="black", dark_boost=0.25, protect_threshold=160,
        min_brightness=20, sat_compensation=0.2
    )
    return step2


# ── 批量反相：对多个 DX 的非黑版 _cut.png 反相并跑贴图流水线 ────────────────────────
def batch_invert_rem(dx_list, mode="black"):
    """批量反相：对选中 DX 的所有非黑版/非白版 _cut.png 反相生成黑版或白版专用图，
    然后自动跑完整平铺图贴图流水线（黑T/白T专用 → 通用贴图 → BW 合成）。
    mode: 'black' 生成 _黑* 白色剪影；'white' 生成 _白* 黑色剪影。
    所有需要贴图的款会一次性交给 _run_sticker_task，PS 全程只开一次。
    dx_list: [dx, ...]
    返回: [{dx, files:[{src,dest}], sticker_ok, sticker_msg, ok, msg}, ...]
    """
    results = []
    sticker_queue = []
    sticker_index = {}
    for dx in dx_list:
        rem_dir = BASE / dx / "02_REM_BG"
        if not rem_dir.is_dir():
            results.append({"dx": dx, "files": [], "sticker_ok": False,
                            "sticker_msg": "02_REM_BG 不存在", "ok": False,
                            "msg": f"{dx}: 02_REM_BG 不存在"})
            continue

        files = []
        errors = []
        prefix = "黑" if mode == "black" else "白"
        skip_markers = ("_黑", "_白")
        for f in sorted(rem_dir.iterdir()):
            name = f.name
            if not name.lower().endswith("_cut.png"):
                continue
            if any(m in name for m in skip_markers):
                continue
            # 解析后缀：DXxxxx_B / DXxxxx_W / DXxxxx_BW
            stem = name[:-len("_cut.png")]
            suffix = stem[len(dx)+1:] if stem.startswith(dx + "_") else ""
            if not suffix:
                continue
            dest_name = f"{dx}_{prefix}{suffix}_cut.png"
            dest = rem_dir / dest_name
            try:
                img = Image.open(f).convert("RGBA")
                # 智能显色：黑版走白墨打底流水线(极暗也显色)+保色；白版压暗亮部+保色
                if mode == "black":
                    inv = black_shirt_print_optimize(img)
                else:
                    inv = enhance_dark_print_for_black_shirt(img, shirt="white")
                role = f"黑{suffix}" if mode == "black" else f"白{suffix}"
                inv.save(dest)
                files.append({"src": name, "dest": dest_name})
                # 注册变体元数据
                if wb_meta is not None:
                    try:
                        src_meta = _meta_for(f)
                        parent_uid = src_meta.get("uid")
                        gid = src_meta.get("group_id") or ""
                        if parent_uid:
                            wb_meta.register_rembg(dest, uid=_new_uid(dest), group_id=gid,
                                                   role=role, parent_uid=parent_uid,
                                                   ai_file=name)
                        else:
                            wb_meta.ensure_meta(dest, group_id=gid, stage="rembg", role=role)
                    except Exception as e:
                        print(f"  [批量反相] 元数据注册失败 {dest}: {e}", flush=True)
                # 清缩略图缓存
                for tf in THUMB_DIR.glob(f"{dx}__rem__{dest_name}.*"):
                    try: tf.unlink()
                    except: pass
            except Exception as e:
                errors.append(f"{name}: {e}")

        if not files and errors:
            results.append({"dx": dx, "files": files, "sticker_ok": False,
                            "sticker_msg": "", "ok": False,
                            "msg": f"{dx}: 反相失败 - " + "; ".join(errors)})
            continue
        if not files:
            results.append({"dx": dx, "files": files, "sticker_ok": False,
                            "sticker_msg": "", "ok": True,
                            "msg": f"{dx}: 无需要反相的图"})
            continue

        # 先占位，贴图流水线统一跑完后再回填
        sticker_index[dx] = len(results)
        results.append({"dx": dx, "files": files, "errors": errors})
        sticker_queue.append(dx)

    if sticker_queue:
        sticker_results = Handler._run_sticker_task(sticker_queue)
        sticker_map = {dx: (ok, msg) for dx, ok, msg in sticker_results}
        for dx in sticker_queue:
            idx = sticker_index.get(dx)
            if idx is None:
                continue
            r = results[idx]
            errors = r.pop("errors", [])
            ok, msg = sticker_map.get(dx, (False, "未执行平铺图/模特图贴图"))
            r["sticker_ok"] = ok
            r["sticker_msg"] = msg
            r["ok"] = ok and not errors
            err_part = ("; 错误: " + "; ".join(errors)) if errors else ""
            r["msg"] = f"{dx}: 反相 {len(r['files'])} 张, " + ("平铺图/模特图贴图完成" if ok else f"贴图流程异常: {msg}") + err_part
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
        elif path == "/ps-status":
            self._ps_status()
        elif path == "/ps-sticker":
            self._ps_sticker(dx)
        elif path == "/ps-batch":
            self._ps_batch(dx)
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

        def _role_prefix(base_stem):
            """DXxxxx_B → DXxxxx"""
            return base_stem.rsplit("_", 1)[0] if "_" in base_stem else base_stem

        # 卡片HTML（缺图的款排前面，其余按DX号）
        # "缺图"仅包括：缺AI图、缺去背（单面 B/W 不再视为缺图）
        def _has_missing(proj):
            for pr in proj["pairs"]:
                if pr["ai_file"] is None or pr["rem_file"] is None:
                    return True
            return False
        projects = sorted(projects, key=lambda p: (
            0 if _has_missing(p) else 1, p["dx"]
        ))
        cards = []
        for p in projects:
            dx = p["dx"]
            rows = []
            # 对同类款的分组：按 base_role 聚合，支持 B1/B2、W1/W2、BW1/WB1 等多版本
            from collections import defaultdict
            pairs_by_role = defaultdict(list)
            for pr in p["pairs"]:
                pairs_by_role[pr.get("base_role", "?")].append(pr)
            bw_pairs = pairs_by_role.get("BW", []) + pairs_by_role.get("WB", [])
            b_pairs  = pairs_by_role.get("B", [])
            w_pairs  = pairs_by_role.get("W", [])
            other_roles = [r for r in pairs_by_role if r not in ("BW", "WB", "B", "W")]
            other_pairs = []
            for r in sorted(other_roles):
                other_pairs.extend(pairs_by_role[r])

            def _sort_versions(prs):
                def key(pr):
                    v = pr.get("version", "")
                    if v == "":
                        return (0, 0)
                    try:
                        return (1, int(v))
                    except Exception:
                        return (1, v)
                return sorted(prs, key=key)

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
                        <img src="/thumb?dx={dx}&kind=ai&file={quote(ai_file)}&t={ai_ts}" onclick="openFolder('{dx}','ai')" loading="lazy" decoding="async">
                        <span class="tag">AI</span></div>
                        <div class="btn-bar">
                        <button class="del" onclick="delImg('{dx}','ai','{ai_file}','{dx}-{stem}-ai')" title="删除AI图">×</button>
                        <button class="rmbg" onclick="rembg('{dx}','{ai_file}')" title="重新去背">🔄</button>
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                else:
                    ai_c = f'''<div class="cell-wrap"><div class="cell missing" id="{dx}-{stem}-ai">
                        <span>⚠ 缺AI图</span>
                        <span class="tag">AI</span></div>
                        <div class="btn-bar">
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
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
                    is_special = '_黑' in rem_file or '_白' in rem_file
                    inv_btn = ''
                    if not is_special:
                        inv_btn = (
                            f'<button class="invert black" onclick="invertRem(\'{dx}\',\'{rem_file}\',\'{stem}\',\'{dx}-{stem}-rem\',\'black\')" title="生成黑版白色剪影贴图">反黑</button>'
                            f'<button class="invert white" onclick="invertRem(\'{dx}\',\'{rem_file}\',\'{stem}\',\'{dx}-{stem}-rem\',\'white\')" title="生成白版黑色剪影贴图">反白</button>'
                        )
                    rem_c = f'''<div class="cell-wrap"><div class="cell" id="{dx}-{stem}-rem">
                        <img id="img-{dx}-{stem}-rem" src="/thumb?dx={dx}&kind=rem&file={quote(rem_file)}&t={rem_ts}" onclick="openFolder('{dx}','rem')" loading="lazy" decoding="async">
                        <span class="tag">REM</span></div>
                        <div class="btn-bar">
                        <button class="del" onclick="delImg('{dx}','rem','{rem_file}','{dx}-{stem}-rem')" title="删除去背图">×</button>
                        <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="刷新预览图">↻</button>
                        {inv_btn}
                        {up_btn}{dim_hint}
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                else:
                    rem_c = f'''<div class="cell-wrap"><div class="cell missing" id="{dx}-{stem}-rem">
                        <span id="img-{dx}-{stem}-rem">⚠ 缺去背</span>
                        <span class="tag">REM</span></div>
                        <div class="btn-bar">
                        <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="重新扫描去背图">↻</button>
                        <span class="btn-stem">{stem}</span>
                        </div></div>'''
                return f'<div class="pair-imgs">{ai_c}{rem_c}</div>'

            def _render_version_blocks(dx, prs):
                """把同一 base_role 的多个版本横向排列"""
                blocks = []
                for pr in _sort_versions(prs):
                    v = pr.get("version", "")
                    v_label = "原" if v == "" else f"v{v}"
                    rename_btn = f'<button class="ren-btn" onclick="event.stopPropagation();renameStemOptions(\'{dx}\',\'{pr["stem"]}\',this)" title="改名">改名</button>'
                    blocks.append(
                        f'<div class="version-block" data-stem="{pr["stem"]}">'
                        f'<div class="version-label">{v_label} {rename_btn}</div>'
                        f'{_render_cells(dx, pr)}</div>'
                    )
                return f'<div class="versions-row">{ "".join(blocks) }</div>'

            # — BW 行（独立，紫色badge，支持 BW/WB 多版本）—
            bw_by_prefix = defaultdict(list)
            for pr in bw_pairs:
                bw_by_prefix[_role_prefix(pr.get("base_stem", pr["stem"]))].append(pr)
            for prefix in sorted(bw_by_prefix):
                prs = bw_by_prefix[prefix]
                gid = prs[0].get("group_id", "")
                rows.append(
                    f'<div class="pair version-group" data-group-id="{gid}" data-base-role="BW" data-prefix="{prefix}">'
                    f'<div class="stem"><span class="badge badge-bw">BW</span> {prefix}</div>'
                    f'{_render_version_blocks(dx, prs)}</div>')

            # — B+W 配对行（左右并排，每侧支持多版本）—
            b_by_prefix = defaultdict(list)
            for pr in b_pairs:
                b_by_prefix[_role_prefix(pr.get("base_stem", pr["stem"]))].append(pr)
            w_by_prefix = defaultdict(list)
            for pr in w_pairs:
                w_by_prefix[_role_prefix(pr.get("base_stem", pr["stem"]))].append(pr)
            grouped_prefixes = sorted(set(b_by_prefix) | set(w_by_prefix))
            for prefix in grouped_prefixes:
                b_prs = b_by_prefix.get(prefix, [])
                w_prs = w_by_prefix.get(prefix, [])

                def _half(dx, prs, badge_class, badge_text):
                    if not prs:
                        return ""
                    return f'''<div class="bw-half" data-base-role="{badge_text}" data-prefix="{prefix}">
                            <div class="stem"><span class="badge {badge_class}">{badge_text}</span> {prefix}</div>
                            {_render_version_blocks(dx, prs)}
                        </div>'''

                left  = _half(dx, b_prs, "badge-b", "B")
                right = _half(dx, w_prs, "badge-w", "W")
                rows.append(f'<div class="bw-group">{left}{right}</div>')

            # — 其他（任意 role）按 base_stem 分组展示多版本 —
            other_by_base = defaultdict(list)
            for pr in other_pairs:
                other_by_base[pr.get("base_stem", pr["stem"])].append(pr)
            for base_stem in sorted(other_by_base):
                prs = other_by_base[base_stem]
                role = prs[0].get("base_role", base_stem)
                gid = prs[0].get("group_id", "")
                rows.append(
                    f'<div class="pair version-group" data-group-id="{gid}" data-base-role="{role}" data-base-stem="{base_stem}">'
                    f'<div class="stem"><span class="badge badge-other">{role}</span> {base_stem}</div>'
                    f'{_render_version_blocks(dx, prs)}</div>')

            # — 黑版变体行（按 base_stem 分组，支持 _黑B1 等多版本）—
            def _render_black_cell(dx, bv):
                stem = bv["stem"]
                rem_file = bv["rem_file"]
                gid = bv.get("group_id", "")
                rem_uid = bv.get("rem_uid") or ""
                rem_path = BASE / dx / "02_REM_BG" / rem_file
                rem_ts = int(rem_path.stat().st_mtime) if rem_path.exists() else 0
                tag = stem[len(dx)+1:] if stem.startswith(dx + "_") else "REM"
                return f'''<div class="cell-wrap black-variant" data-group-id="{gid}" data-rem-uid="{rem_uid}" data-stem="{stem}"><div class="cell" id="{dx}-{stem}-rem">
                    <img id="img-{dx}-{stem}-rem" src="/thumb?dx={dx}&kind=rem&file={quote(rem_file)}&t={rem_ts}" onclick="openFolder('{dx}','rem')" loading="lazy" decoding="async">
                    <span class="tag">{tag}</span></div>
                    <div class="btn-bar">
                    <button class="del" onclick="delImg('{dx}','rem','{rem_file}','{dx}-{stem}-rem')" title="删除去背图">×</button>
                    <button class="refr" onclick="refreshRem('{dx}','{stem}','{dx}-{stem}-rem')" title="刷新预览图">↻</button>
                    <span class="btn-stem">{stem}</span>
                    </div></div>'''

            black_variants = p.get("black_variants", [])
            black_by_base = defaultdict(list)
            for bv in black_variants:
                black_by_base[bv.get("base_stem", bv["stem"])].append(bv)
            for base_stem in sorted(black_by_base):
                bvs = black_by_base[base_stem]
                role = bvs[0].get("base_role", "黑版")
                gid = bvs[0].get("group_id", "")
                blocks = []
                for bv in _sort_versions(bvs):
                    v = bv.get("version", "")
                    v_label = "原" if v == "" else f"v{v}"
                    blocks.append(
                        f'<div class="version-block black-variant-block" data-stem="{bv["stem"]}">'
                        f'<div class="version-label">{v_label}</div>'
                        f'{_render_black_cell(dx, bv)}</div>'
                    )
                rows.append(
                    f'<div class="pair black-variant-row" data-kind="black-variant" data-group-id="{gid}">'
                    f'<div class="stem"><span class="badge badge-other">{role}</span></div>'
                    f'<div class="versions-row">{ "".join(blocks) }</div></div>')

            rows_html = "\n".join(rows)
            up_dir = BASE / dx / "03_UPLOAD"
            has_up = up_dir.is_dir() and any(f for f in up_dir.iterdir() if f.suffix.lower() in ('.png','.jpg','.jpeg'))
            up_detail = self._upload_detail(dx, has_up)
            cards.append(f'''<div class="card" data-dx="{dx}">
                <div class="card-head">
                    <input type="checkbox" class="dx-check" data-dx="{dx}" onchange="updateBatchBtn()" style="width:16px;height:16px;accent-color:#4CAF50;cursor:pointer;">
                    <span class="dxname" onclick="copyDx('{dx}')" title="点击复制款号">{dx}</span>

                    <span class="card-act">
                        <button class="btn-ps" onclick="psSticker('{dx}')" title="贴图：单面款走模特图贴图，其它走平铺图贴图+BW合成">📎 贴图</button>
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
.versions-row {{ display:flex; flex-wrap:wrap; gap:12px; align-items:flex-start; }}
.version-block {{ display:flex; flex-direction:column; gap:3px; min-width:220px; flex:0 0 auto; max-width:100%; }}
.version-label {{ color:#888; font-size:11px; text-align:center; display:flex; align-items:center; justify-content:center; gap:4px; }}
.bw-group {{ display:flex; flex-wrap:wrap; gap:10px; }}
.bw-half {{ flex:1 1 0; min-width:220px; max-width:100%; }}
.black-variant-block {{ min-width:160px; }}
.cell-wrap {{ display:flex; flex-direction:column; min-width:0; }}
.cell {{ width:100%; height:220px; max-height:220px; background:#fff; border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center; position:relative; box-sizing:border-box; }}
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
.btn-bar .invert.black {{ background:#311b92; }}
.btn-bar .invert.black:hover {{ background:#1a237e; }}
.btn-bar .invert.white {{ background:#9575cd; color:#000; }}
.btn-bar .invert.white:hover {{ background:#7e57c2; color:#fff; }}
.btn-bar .upscale {{ background:#4caf50; color:#fff; font-size:14px; padding:3px 9px; }}
.btn-bar .upscale:hover {{ background:#2e7d32; }}
.btn-bar .dim-hint {{ color:#888; font-size:11px; margin-left:3px; white-space:nowrap; }}
.btn-stem {{ color:#666; font-size:11px; margin-left:auto; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:110px; flex-shrink:1; }}
.badge {{ display:inline-block; font-size:12px; font-weight:bold; padding:2px 7px; border-radius:3px; margin-right:4px; }}
.badge-bw {{ background:#9c27b0; color:#fff; }}
.badge-b {{ background:#555; color:#fff; }}
.badge-w {{ background:#e0e0e0; color:#333; }}
.ps-btn {{ display:inline-flex; align-items:center; gap:2px; font-size:12px; padding:2px 10px; border-radius:4px; cursor:pointer; background:#7b1fa2; color:#fff; border:none; line-height:24px; white-space:nowrap; margin-left:auto; }}
.ps-btn:hover {{ background:#9c27b0; }}
.ps-btn.ps-done {{ background:#2e7d32; }}
.ps-btn.ps-done:hover {{ background:#388e3c; }}
.ren-btn {{ display:inline; font-size:12px; padding:1px 5px; margin-left:3px; border-radius:2px;
           background:#4caf50; color:#fff; border:none; cursor:pointer; vertical-align:middle; }}
.ren-btn:hover {{ background:#388e3c; }}
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
#backToTop {{ position:fixed; right:22px; bottom:28px; z-index:998; width:46px; height:46px; border-radius:50%; border:none; background:#2196F3; color:#fff; font-size:22px; cursor:pointer; box-shadow:0 2px 10px rgba(0,0,0,.5); display:none; align-items:center; justify-content:center; transition:opacity .2s, transform .1s; }}
#backToTop:hover {{ background:#1976D2; transform:scale(1.08); }}
#backToTop.show {{ display:flex; }}
#psStatus {{ display:none; align-items:center; gap:8px; margin-left:10px; padding:6px 12px; border-radius:4px; background:#1a237e; color:#fff; font-size:13px; font-weight:600; animation:psPulse 1.5s infinite; }}
#psStatus.show {{ display:flex; }}
#psStatus .dot {{ width:8px; height:8px; border-radius:50%; background:#00e676; }}
@keyframes psPulse {{ 0% {{ opacity:.85; }} 50% {{ opacity:1; }} 100% {{ opacity:.85; }} }}

</style></head><body>
<h1>AI 去背 贴图 OS <span class="v">v{__version__}</span></h1>
<div class="toolbar">
  <select id="dateSel" onchange="switchDate(this.value)">
{date_opts_html}
  </select>
	  <input id="search" placeholder="搜索 DX号…" oninput="filterCards()">
	  <button onclick="filterCards()" style="cursor:pointer;background:#4CAF50;color:#fff;border:none;border-radius:4px;margin-left:4px;">🔍 搜索</button>
  <button onclick="fetch('/refresh').then(function(r){{return r.json();}}).then(function(d){{showToast(d.msg);setTimeout(function(){{location.reload();}},500);}}).catch(function(){{location.reload();}});" title="重新扫描全部（自动跳过未变更的缩略图）">🔄 刷新全部</button>
	  <label style="color:#eee;cursor:pointer;user-select:none;margin-left:8px;">
	    <input type="checkbox" id="selectAll" onchange="toggleSelectAll(this.checked)" style="width:18px;height:18px;accent-color:#4CAF50;vertical-align:middle;"> 全选
	  </label>
	  <button onclick="batchRembg()" id="batchBtn" style="cursor:pointer;background:#ff9800;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>⚡ 批量去背 (0)</button>
	  <button onclick="copyMissing()" title="复制当前日期缺图款号（缺AI图/缺去背）" style="background:#e91e63;">📋 复制缺图款号</button>
	  <button onclick="batchSticker()" id="batchStickerBtn" title="批量贴图：单面款走模特图贴图，其它走平铺图贴图+BW合成，不处理黑版文件，不反相" style="cursor:pointer;background:#7b1fa2;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>📎 批量贴图 (0)</button>
	  <button onclick="batchInvertRem('black')" id="batchInvertBtn" title="批量反黑：对选中款的所有B/W/BW去背图生成黑版专用图，并自动平铺图贴图+BW合成" style="cursor:pointer;background:#311b92;color:#fff;border:none;border-radius:4px;font-weight:bold;" disabled>🌑 批量反黑 (0)</button>
	  <button onclick="batchInvertRem('white')" id="batchInvertWhiteBtn" title="批量反白：对选中款的所有B/W/BW去背图生成白版专用图，并自动平铺图贴图+BW合成" style="cursor:pointer;background:#9575cd;color:#000;border:none;border-radius:4px;font-weight:bold;" disabled>☀ 批量反白 (0)</button>
	  <button onclick="copyNoSticker()" title="复制当前日期所有未生成成品的款号" style="background:#7b1fa2;">📋 复制缺贴图</button>
	  <span id="psStatus"><span class="dot"></span><span id="psStatusText">PS 空闲</span></span>
	  <span class="cnt" id="cnt">{len(projects)} 款</span>
	</div>
	<div class="grid" id="grid">{cards_html}</div>
<div id="toast" class="toast"></div>
<div id="preview" class="preview"><img id="previewImg" src=""></div>
<button id="backToTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}});" title="回到顶部">⬆</button>
  <script src="/check_rem.js?v={__version__}"></script></body></html>"""

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
        if ok:
            _invalidate_scan_cache()
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
        TEMP_REMBG.mkdir(parents=True, exist_ok=True)
        lock = TEMP_REMBG / ".rembg_lock"
        if lock.exists():
            self._send_json({"ok": False, "msg": "已有去背任务在运行，请等其完成"}); return
        lock.write_text(f"{dx}\t{file}", encoding="utf-8")
        # 启动后台 worker（最小化控制台窗口），HTTP 立即返回
        worker = Path(__file__).parent / "_rembg_worker.py"
        run_minimized([sys.executable, str(worker), dx, file], wait=False)
        self._send_json({"ok": True, "msg": f"{dx}/{file} 已启动美图去背，请勿动键鼠，完成后点刷新"})

    # 检查去背锁（供批量去背轮询）
    def _check_rembg_lock(self):
        lock = TEMP_REMBG / ".rembg_lock"
        locked = lock.exists()
        self._send_json({"locked": locked})

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
            files = [f.name for f in sorted(ai_dir.iterdir())
                     if f.is_file() and is_generated_ai(f.name, dx)]
            # 如果该 DX 已有 BW 合并图，就只处理 BW，不单独处理 B/W
            if any("_BW" in name for name in files):
                files = [name for name in files if "_BW" in name]
            dx_files.extend((dx, name) for name in files)

        if not dx_files:
            self._send_json({"ok": False, "msg": "没有找到需要去背的图"}); return

        # 异步执行（batch_rembg 会开美图 GUI）
        import threading
        TEMP_REMBG.mkdir(parents=True, exist_ok=True)
        def _run():
            lock = TEMP_REMBG / ".rembg_lock"
            try:
                lock.write_text("batch", encoding="utf-8")
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
    # 刷新全部：清空 scan_projects 缓存 → 前端刷新页面（缩略图由 get_thumb 按 mtime 懒加载/更新）
    def _refresh(self):
        # 不再清空缩略图：get_thumb 会根据源文件 mtime 自动重新生成有变更的缩略图。
        # 清空缓存后立即重新扫描并预热缓存，让前端刷新时直接命中内存缓存。
        _invalidate_scan_cache()  # 同时清空内存与磁盘缓存
        try:
            scan_projects(force=True)
        except Exception as e:
            print(f"  [refresh] 预热扫描失败: {e}", flush=True)
        self._send_json({"ok": True, "msg": "已重新扫描，刷新页面查看"})

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
    def _run_one_sticker(dx, skip_black=False):
        """运行单个 DX 的贴图流水线。
        - 单面款（02_REM_BG 里只有 W 或只有 B）：走模特图贴图（white_t_mockup 胚衣）。
        - 其它（BW / 同时有 B+W / 含黑版）：走平铺图贴图（PS 贴图 + BW 合成）。
        返回 (ok, msg)。不退出 Photoshop，由外层任务统一控制 PS 生命周期。
        skip_black=True 时平铺图流程会跳过黑T贴图（用于批量贴图）。"""
        rem_dir = BASE / dx / "02_REM_BG"
        up_dir = BASE / dx / "03_UPLOAD"

        # 判断是否为单面新流程：按「去掉 黑/白 前缀后的真实面集合」判定。
        # 只有 W 或只有 B（即使含 _黑W/_白W 这类反黑/反白专用图，本质仍是同一面）→ 模特图贴图；
        # 含 BW/WB 或同时有 B+W → 平铺图贴图。
        # has_black / has_white 仍保留，供平铺流程决定是否跑黑T/白T专用贴图。
        side_re = re.compile(r'^(BW|WB|B|W)(\d*)$', re.IGNORECASE)
        real_sides = set()
        has_black = False
        has_white = False
        if rem_dir.is_dir():
            for f in rem_dir.iterdir():
                if not f.is_file() or not f.name.lower().endswith("_cut.png"):
                    continue
                stem = f.stem[:-4]  # 去掉 _cut
                if not stem.startswith(dx + "_"):
                    continue
                if "_黑" in f.name:
                    has_black = True
                if "_白" in f.name:
                    has_white = True
                suffix = stem[len(dx) + 1:]
                plain = suffix[1:] if (suffix.startswith("黑") or suffix.startswith("白")) else suffix
                m = side_re.match(plain)
                side = m.group(1).upper() if m else None
                if side in ("BW", "WB"):
                    real_sides.update(("B", "W"))
                elif side in ("B", "W"):
                    real_sides.add(side)
        if skip_black:
            has_black = False

        single_role = None
        if real_sides == {"W"}:
            single_role = "W"
        elif real_sides == {"B"}:
            single_role = "B"

        # 清理旧的自动生成平铺图/模特图贴图/BW文件，确保再次贴图时一定重新生成并覆盖
        if up_dir.is_dir():
            for fp in up_dir.iterdir():
                if not fp.is_file():
                    continue
                name = fp.name
                low = name.lower()
                if low.endswith((".png", ".jpg", ".jpeg")):
                    stem = Path(name).stem
                    if (re.match(rf"{re.escape(dx)}_.*_(白T|黑T)$", stem) or
                            re.match(rf"{re.escape(dx)}_(白BW|黑BW)", stem)):
                        try:
                            fp.unlink()
                            print(f"  [贴图流水线] 清理旧文件: {dx}/{name}", flush=True)
                        except Exception:
                            pass

        # 单面新流程：直接调用 white_t_mockup 做模特图贴图
        if single_role:
            # 枚举 02_REM_BG 里该面的 _cut，按文件名颜色路由到对应颜色胚衣：
            #   黑*_cut → 只贴黑T；白*_cut → 只贴白T；无颜色 _cut → 两色都贴。
            # 专用优先：黑/白专用 cut 各自贴对应色；无颜色 cut 只贴未被专用覆盖的色。
            cuts = []  # (color, path)；color in {"黑", "白", None}
            for f in rem_dir.iterdir():
                if not f.is_file() or not f.name.lower().endswith("_cut.png"):
                    continue
                stem = f.stem[:-4]
                if not stem.startswith(dx + "_"):
                    continue
                suffix = stem[len(dx) + 1:]
                color = "黑" if suffix.startswith("黑") else ("白" if suffix.startswith("白") else None)
                plain = suffix[1:] if color else suffix
                m = side_re.match(plain)
                side = m.group(1).upper() if m else None
                if side == single_role:
                    cuts.append((color, f))
            if not cuts:
                return False, f"02_REM_BG 无 {single_role} 面去背图"
            covered = {c for c, _ in cuts if c}
            try:
                from w_mockup_extra import generate_single_side_mockup
                results = []
                for color, path in cuts:
                    if color:
                        oc = color
                    else:
                        rest = [x for x in ("白", "黑") if x not in covered]
                        if not rest:
                            continue  # 黑白都已有专用 cut，无颜色 cut 跳过
                        oc = None if len(rest) == 2 else rest[0]
                    ok, msg = generate_single_side_mockup(
                        dx, BASE, single_role, run_minimized,
                        cut_path=path, only_color=oc,
                    )
                    results.append((ok, msg))
                ok = any(ok for ok, _ in results)
                msg = "; ".join(m for _, m in results)
            except Exception as e:
                ok, msg = False, f"模特图贴图({single_role})异常: {e}"
            print(f"  [模特图贴图] {msg}", flush=True)
            if ok:
                Handler._register_uploads(dx)
                msg = f"模特图贴图({single_role})完成: {dx}"
            return ok, msg

        # 平铺图流程：黑T专用 → 白T专用 → 通用贴图 → BW 合成
        sticker_script = Path(r"E:\Claude code\ps\ps_sticker_one.py")
        batch_script = Path(r"E:\Claude code\ps\ps_batch_one.py")
        black_script = Path(r"E:\Claude code\ps\process_black.py")
        white_script = Path(r"E:\Claude code\ps\process_white.py")
        if not sticker_script.exists():
            return False, "平铺图贴图脚本不存在"
        if not batch_script.exists():
            return False, "BW合成脚本不存在"

        ok = True
        msg = ""
        # 1) 黑T专用平铺图贴图（如果存在黑B/黑W/黑BW且未禁用）
        if has_black:
            if not black_script.exists():
                ok, msg = False, "平铺图黑T贴图脚本(process_black.py)不存在"
            else:
                try:
                    proc0 = run_minimized([sys.executable, str(black_script), dx])
                    if proc0.returncode != 0:
                        ok, msg = False, f"平铺图黑T贴图执行失败: {dx}"
                except Exception as e:
                    ok, msg = False, f"平铺图黑T贴图启动失败: {e}"

        # 2) 白T专用平铺图贴图（如果存在白B/白W/白BW）
        if ok and has_white:
            if not white_script.exists():
                ok, msg = False, "平铺图白T贴图脚本(process_white.py)不存在"
            else:
                try:
                    proc0 = run_minimized([sys.executable, str(white_script), dx])
                    if proc0.returncode != 0:
                        ok, msg = False, f"平铺图白T贴图执行失败: {dx}"
                except Exception as e:
                    ok, msg = False, f"平铺图白T贴图启动失败: {e}"

        # 3) 通用 B/W/BW 平铺图贴图（有黑版/白版对应文件时自动跳过对应输出）
        if ok:
            try:
                proc1 = run_minimized([sys.executable, str(sticker_script), dx])
                if proc1.returncode != 0:
                    ok, msg = False, f"平铺图贴图执行失败: {dx}"
            except Exception as e:
                ok, msg = False, f"平铺图贴图启动失败: {e}"

        # 4) 用贴好的 B/W 合成 BW
        if ok:
            try:
                proc2 = run_minimized([sys.executable, str(batch_script), dx])
                if proc2.returncode != 0:
                    ok, msg = True, f"平铺图贴图完成，但BW合成执行失败: {dx}"
            except Exception as e:
                ok, msg = True, f"平铺图贴图完成，但BW合成启动失败: {e}"

        if ok and not msg:
            parts = []
            if has_black:
                parts.append("黑T")
            if has_white:
                parts.append("白T")
            msg_prefix = "平铺图贴图（含" + "+".join(parts) + "+BW合成）" if parts else "平铺图贴图+BW合成"
            # 5) 注册贴图/BW 成品元数据
            Handler._register_uploads(dx)
            msg = f"{msg_prefix}完成: {dx}"

        return ok, msg

    def _run_sticker_task(dx_list, skip_black=False):
        """按顺序跑完一组 DX 的贴图流水线，PS 全程只开一次，全部做完再退出。
        返回 [(dx, ok, msg), ...]。"""
        quit_ps_script = Path(r"E:\Claude code\ps\quit_ps.py")
        results = []
        acquired = False
        task_name = "批量平铺图贴图" if len(dx_list) > 1 else "平铺图贴图"
        try:
            acquired = _PS_TASK_LOCK.acquire(blocking=True, timeout=-1)
            if not acquired:
                return [(dx, False, "Photoshop 正被其他任务占用") for dx in dx_list]

            _set_ps_status(True, task_name, "", f"0/{len(dx_list)}", f"共 {len(dx_list)} 款: {', '.join(dx_list)}")
            print(f"\n[PS任务] 开始{task_name}，共 {len(dx_list)} 款: {', '.join(dx_list)}", flush=True)
            for idx, dx in enumerate(dx_list, 1):
                _set_ps_status(True, task_name, dx, f"{idx}/{len(dx_list)}", f"正在处理 {dx}")
                ok, msg = Handler._run_one_sticker(dx, skip_black=skip_black)
                results.append((dx, ok, msg))
                status = "✅" if ok else "❌"
                print(f"  {status} {dx}: {msg}", flush=True)
            _set_ps_status(True, task_name, "", f"{len(dx_list)}/{len(dx_list)}", "全部完成，正在退出 Photoshop")
            print(f"[PS任务] 全部完成，准备退出 Photoshop\n", flush=True)
        finally:
            if acquired:
                if quit_ps_script.exists():
                    try:
                        run_minimized([sys.executable, str(quit_ps_script)], wait=True, timeout=60)
                    except Exception as e:
                        print(f"  [PS任务] 退出PS失败: {e}", flush=True)
                _clear_ps_status()
                _PS_TASK_LOCK.release()
        return results

    # 贴图入口：单面款走模特图贴图，其它走平铺图贴图+BW合成
    def _ps_sticker(self, dx):
        if not dx:
            self._send_json({"ok": False, "msg": "DX号非法"}); return
        dx_list = [d.strip() for d in dx.split(",") if re.match(r"^DX\d+$", d.strip())]
        if not dx_list:
            self._send_json({"ok": False, "msg": "DX号非法"}); return
        # 批量贴图默认跳过黑T专用贴图（避免处理已有的黑版文件），单款贴图保留黑T
        qs = parse_qs(urlparse(self.path).query) if '?' in self.path else {}
        skip_black = len(dx_list) > 1 or qs.get("skip_black", [""])[0] == "1"
        results = Handler._run_sticker_task(dx_list, skip_black=skip_black)
        ok_all = all(r[1] for r in results)
        msgs = "; ".join(f"{r[0]}: {r[2]}" for r in results)
        self._send_json({"ok": ok_all, "msg": msgs})

    # BW合成（独立入口：仅用已贴好的 B/W 合成 BW）
    def _ps_batch(self, dx):
        if not re.match(r"^DX\d+$", dx):
            self._send_json({"ok": False, "msg": "DX号非法"}); return
        ps_script = Path(r"E:\\Claude code\\ps\\ps_batch_one.py")
        quit_ps_script = Path(r"E:\\Claude code\\ps\\quit_ps.py")
        if not ps_script.exists():
            self._send_json({"ok": False, "msg": "BW合成脚本不存在"}); return
        # 保持立即返回，后台线程获取 PS 锁后再运行，避免与贴图任务冲突
        def _run_and_register():
            acquired = False
            try:
                acquired = _PS_TASK_LOCK.acquire(blocking=True)
                _set_ps_status(True, "BW合成", dx, "", f"正在合成 {dx} 的 BW 图")
                proc = run_minimized([sys.executable, str(ps_script), dx], wait=True)
                if proc.returncode == 0:
                    Handler._register_uploads(dx)
            except Exception as e:
                print(f"  [BW合成] 后台注册失败: {e}", flush=True)
            finally:
                if acquired:
                    if quit_ps_script.exists():
                        try:
                            print(f"  [BW合成] 正在退出 Photoshop...", flush=True)
                            run_minimized([sys.executable, str(quit_ps_script)], wait=True, timeout=30)
                        except Exception as e:
                            print(f"  [BW合成] 退出PS失败: {e}", flush=True)
                    _clear_ps_status()
                    _PS_TASK_LOCK.release()
        import threading
        threading.Thread(target=_run_and_register, daemon=True).start()
        self._send_json({"ok": True, "msg": f"已启动 BW合成: {dx}，后台运行中"})

    # 返回当前 PS / 后台任务状态摘要
    def _ps_status(self):
        with _PS_STATUS_LOCK:
            data = dict(_PS_STATUS)
        # 若状态超过 30 秒未更新，自动视为已结束（防止异常未清状态）
        if data.get("running") and time.time() - data.get("updated_at", 0) > 30:
            data["running"] = False
            data["detail"] = "状态已超时，可能已结束"
        self._send_json(data)

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
                    f'<img src="/thumb?dx={dx}&kind=up&file={quote(f.name)}&t={ts}" onclick="openFolder(\'{dx}\',\'up\')" loading="lazy" decoding="async">'
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
        """根据文件名判断成品属于 BW / B / W / 其他；支持 B1/W2/BW1/WB1 等版本号。"""
        stem = Path(name).stem
        # 去掉 _白T/_黑T 后提取基础 role
        role_part = re.sub(r'_(白T|黑T)$', '', stem)
        role_part = role_part[len(dx)+1:] if role_part.startswith(dx + "_") else role_part
        role_part = re.sub(r'\d+$', '', role_part)
        if role_part in ('BW', 'WB'):
            return 'BW'
        if role_part == 'B':
            return 'B'
        if role_part == 'W':
            return 'W'
        return '其他'

    def _up_label(self, name, dx):
        """生成成品缩略图下方的小标签（如 白T / 黑T / 白 / 黑 / v1）。"""
        stem = Path(name).stem
        label = stem[len(dx):] if stem.startswith(dx) else stem
        label = label.strip('_')
        # 去掉基础分组标识（含版本号），保留颜色/版型/版本描述
        label = re.sub(r'^(B|W|BW|WB)\d*_', '', label)
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

    # 反相去背图并自动跑贴图流水线
    def _invert_rem(self, dx, file):
        from urllib.parse import parse_qs
        if not re.match(r"^DX\d+$", dx) or "/" in file or "\\" in file:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        if not file.lower().endswith("_cut.png"):
            self._send_json({"ok": False, "msg": "仅支持 _cut.png 去背图"}); return

        qs = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        mode = qs.get("mode", ["black"])[0].lower()
        if mode not in ("black", "white"):
            self._send_json({"ok": False, "msg": "mode 必须是 black 或 white"}); return

        # 已是对应专用图则无需再反
        if mode == "black" and "_黑" in file:
            self._send_json({"ok": False, "msg": "已是黑版专用图，无需反黑"}); return
        if mode == "white" and "_白" in file:
            self._send_json({"ok": False, "msg": "已是白版专用图，无需反白"}); return
        # 从另一版专用图再反没有意义（剪影再反还是剪影），也跳过
        if (mode == "black" and "_白" in file) or (mode == "white" and "_黑" in file):
            self._send_json({"ok": False, "msg": "请从原始 B/W/BW 去背图执行反相"}); return

        src = BASE / dx / "02_REM_BG" / file
        if not src.exists():
            self._send_json({"ok": False, "msg": f"{file} 不存在"}); return

        # 生成目标文件名：DX0255_B_cut.png -> DX0255_黑B_cut.png / DX0255_白B_cut.png
        stem = file[:-len("_cut.png")]
        suffix = stem[len(dx)+1:] if stem.startswith(dx + "_") else ""
        if not suffix:
            self._send_json({"ok": False, "msg": "无法解析文件名后缀"}); return
        prefix = "黑" if mode == "black" else "白"
        dest_name = f"{dx}_{prefix}{suffix}_cut.png"
        dest = BASE / dx / "02_REM_BG" / dest_name

        try:
            img = Image.open(src).convert("RGBA")
            # 智能显色：黑版走白墨打底流水线(极暗也显色)+保色；白版压暗亮部+保色
            if mode == "black":
                inv = black_shirt_print_optimize(img)
            else:
                inv = enhance_dark_print_for_black_shirt(img, shirt="white")
            role = f"黑{suffix}" if mode == "black" else f"白{suffix}"
            inv.save(dest)
        except Exception as e:
            self._send_json({"ok": False, "msg": f"反相失败: {e}"}); return

        # 注册变体元数据
        if wb_meta is not None:
            try:
                src_meta = _meta_for(src)
                parent_uid = src_meta.get("uid")
                gid = src_meta.get("group_id") or ""
                if parent_uid:
                    wb_meta.register_rembg(dest, uid=_new_uid(dest), group_id=gid,
                                           role=role, parent_uid=parent_uid,
                                           ai_file=file)
                else:
                    wb_meta.ensure_meta(dest, group_id=gid, stage="rembg", role=role)
            except Exception as e:
                print(f"  [反相] 元数据注册失败 {dest}: {e}", flush=True)

        # 清缩略图缓存
        for tf in THUMB_DIR.glob(f"{dx}__rem__{dest_name}.*"):
            try: tf.unlink()
            except: pass

        # 反相后重跑该款完整贴图+BW合成流水线
        results = Handler._run_sticker_task([dx])
        ok, msg = results[0][1], results[0][2]
        self._send_json({"ok": ok, "msg": f"已生成 {dest_name}，{msg}"})

    # 批量反相：对选中 DX 的所有原始 _cut.png 反相，并跑完整贴图流水线
    def _batch_invert_rem(self):
        from urllib.parse import parse_qs
        qs = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        dx_str = qs.get("dx", [""])[0]
        mode = qs.get("mode", ["black"])[0].lower()
        if mode not in ("black", "white"):
            self._send_json({"ok": False, "msg": "mode 必须是 black 或 white"}); return
        if not dx_str:
            self._send_json({"ok": False, "msg": "缺少 dx 参数"}); return
        dx_list = [d.strip() for d in dx_str.split(",") if d.strip()]
        if not dx_list:
            self._send_json({"ok": False, "msg": "无效的 dx 参数"}); return

        lock = TEMP_REMBG / ".invert_lock"
        if lock.exists():
            self._send_json({"ok": False, "msg": "已有批量反相任务在运行，请等其完成"}); return

        label = "批量反黑" if mode == "black" else "批量反白"

        def _run():
            try:
                lock.write_text("batch", encoding="utf-8")
                _set_ps_status(True, label, "", f"0/{len(dx_list)}", f"共 {len(dx_list)} 款，先反相去背图再平铺图贴图+BW合成")
                results = batch_invert_rem(dx_list, mode=mode)
                ok_count = sum(1 for r in results if r["ok"])
                fail_count = len(results) - ok_count
                msg = f"完成 {ok_count}/{len(results)}"
                if fail_count:
                    msg += f", {fail_count}个失败"
                result_file = TEMP_REMBG / "_batch_invert_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump({"ok": True, "msg": msg, "results": results}, f, ensure_ascii=False)
            finally:
                _clear_ps_status()
                if lock.exists():
                    lock.unlink()

        import threading
        threading.Thread(target=_run, daemon=True).start()
        self._send_json({"ok": True, "msg": f"{label}已启动，共 {len(dx_list)} 款，将自动反相并平铺图贴图+BW合成"})

    # 批量反相结果查询
    def _batch_invert_result(self):
        result_file = TEMP_REMBG / "_batch_invert_result.json"
        lock = TEMP_REMBG / ".invert_lock"
        if lock.exists():
            self._send_json({"done": False, "msg": "批量反相进行中…"})
        elif result_file.exists():
            try:
                data = json.loads(result_file.read_text(encoding="utf-8"))
                result_file.unlink()
                self._send_json({"done": True, **data})
            except Exception:
                self._send_json({"done": True, "ok": True, "msg": "完成", "results": []})
        else:
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

    # 改名：任意后缀转换（如 DX0264_B → DX0264_BW / DX0264_RED1，对应 _cut 也改名）
    def _rename_stem(self, dx, stem, target=""):
        if not re.match(r"^DX\d+$", dx) or not stem or "/" in stem or "\\" in stem:
            self._send_json({"ok": False, "msg": "参数非法"}); return
        target = (target or "").strip()
        # 兼容旧逻辑：未传 target 且 stem 以 _B/_W 结尾时默认改为 _BW
        if not target:
            if stem.endswith("_B") or stem.endswith("_W"):
                target = "BW"
            else:
                self._send_json({"ok": False, "msg": "请指定新后缀"}); return
        # target 允许中文、字母、数字、下划线、连字符
        if not re.match(r'^[\u4e00-\u9fa5A-Za-z0-9_\-]+$', target) or ".." in target:
            self._send_json({"ok": False, "msg": "新后缀非法"}); return
        prefix = dx  # DX0264
        new_stem = f"{prefix}_{target}"
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
        # 同步 uid_map 中的文件路径（scan_projects 不再每次全量对账）
        if wb_meta is not None:
            try:
                wb_meta.reconcile_dx(BASE / dx)
            except Exception as e:
                print(f"  [rename] 对账 {dx} 失败: {e}", flush=True)
        # 文件改名后清空扫描缓存，下次请求重新索引
        _invalidate_scan_cache()
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
    # 首次启动若发现遗留锁/未恢复config，自动清理
    if CONFIG_BACKUP.exists():
        _restore_config()
        print("  ⚠ 检测到上次未完成的去背任务，已恢复 config.json")
    TEMP_REMBG.mkdir(parents=True, exist_ok=True)
    lock = TEMP_REMBG / ".rembg_lock"
    if lock.exists():
        try: lock.unlink()
        except Exception: pass

    os.chdir(str(CHECK))
    url = f"http://localhost:{PORT}/"
    print(f"  AI vs 去背 对比预览  →  {url}")
    print(f"  点缩略图：打开文件夹   x：送回收站   [重新去背]：驱动美图")
    print(f"  关闭此窗口停止服务")

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
