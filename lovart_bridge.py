#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y2 Bridge Server v2.4.2
=======================
Flask HTTP 桥接服务 — 连接 Y2 控制台与本地 Lovart 管线 + 文件系统

架构: HTML ←HTTP/JSON→ Flask Bridge ←subprocess→ Lovart-official pipeline
                                    ←文件IO→   INBOX / DX 目录 / Registry

变更 v2.4.2：
  - 新增遮罩生成子系统（胚衣制作 / 人物前景遮挡）：
    * 新增 /peiyi 页面 + 19 个 /api/peiyi/* 端点（upload/list/scores/material/versions/
      version_file/use_version/open/delete/reindex/meta/mask/correct_*/working_file/
      delete_version/import_manual）。
    * 「生成遮罩」按钮 → _peiyi_worker.py mask → peiyi_mask.generate_masks（BiRefNet + LAB 聚类
      + FASHN 语义分割，v1.5.2），输出存档到 03_MATERIAL/<分类>/_mask_versions/<stem>/vNNN/。
    * 联动 tpl_generator.generate_tpl_for_material 生成 _tpl 扭曲素材；贴图时 white_t_mockup
      自动传入 --occluder（即 *_occluder.png）盖到印花上层。
    * 手动校正（点选扩散）+ 导入手动 PS 遮罩合并（peiyi_correct.py）。
    * 评分总表 /api/peiyi/scores（低分排前标红）。

变更 v2.4.1：
  - 建议零售价填写新增「🔍 诊断结构」网页按钮：复用现有「👌 好了」信号机制，
    免手动建 go.signal 文件即可触发 --diagnose 模式。
  - _start_retail_price_script 增加 diagnose 参数，diagnose=True 时 node 命令附加 --diagnose。
  - 新增 /api/retail_price/start_diagnose 端点；建议零售价.js 诊断结果同时写入 建议零售价_diagnose.json。

变更 v2.4.0：
  - 刷新已上款改为增量游标模式（联动 check_online_listed.py v1.4.0）：
    * json 新增 ordered_list / last_oldest_dx 字段，日常刷新翻到上次边界款为止，集合相减自动移除下架款
    * 首次运行全量建库；深度清理模式全量覆盖重置边界
    * /api/upload/refresh-online-listed 支持 ?mode=incremental|deep
  - 修复「刷新已上款」前端轮询提前停止：停止条件改为检测 online_updated_at 变化，不再 9 秒假完成
  - 新增「🧹 深度清理」按钮（全量覆盖，移除所有下架款）
  - /api/upload/projects 返回 online_mode

变更 v2.3.23：
  - 同步 wb上款 v2.2.2：
    * 修复 EdgeService 窗口操作误匹配夸克/Chrome 等 Chromium 浏览器的问题。
    * `_find_edge_windows()` 增加 `msedge.exe` 进程名校验，不再按类名误操作夸克窗口。
    * `show_for_user()` / `prepare_for_interaction()` / `hide_for_automation()` / `hide_at_bottom()`
      全部按 Edge 自身进程树执行，避免把夸克透明窗口提到前台或恢复不透明导致遮挡屏幕。
  - Bridge 自身代码无改动，仅更新依赖版本与文档。

变更 v2.3.22：
  - 集成 Temu 报活动控制台 (`/activity`) 与报活动引擎 v4.1.3。
  - 新增 `/api/activity/*` 端点：启动报活动、停止、状态轮询。
  - 新增 `activity.html` 前端页面，支持启动/停止、状态徽章、实时日志、当前步骤与已完成步骤展示。
  - `lovart_control.html` 工具栏新增「报活动」按钮，可在新标签页打开 `/activity`。
  - `/api/activity/status` 按 contract 返回 `{status, log: [str], state_info}`，state.json 不存在时返回空 state_info。

变更 v2.3.21：
  - 修复 WB 上款页面缩略图黑白错位。
    * 根因：`_get_upload_thumb` / `_get_ai_thumb` 用 `re.sub(r'[^A-Za-z0-9_.-]', '_', filename)` 把
      文件名中的中文统一替换为下划线，导致 `DX_B_白T.jpg` 与 `DX_B_黑T.jpg` 生成同一个缓存文件名。
    * 解决：safe_name 只替换 Windows 文件系统非法字符（`\ / * ? : " < > |`），保留中文。
    * 清理：`D:\Semems WB\_upload_thumbs` 与 `_ai_review_thumbs` 中的错误缓存已清空，重新加载页面会自动重建正确缩略图。
  - 修复点击上款图片/回收站按钮后文件夹不自动前台弹出的问题。
    * 根因：`os.startfile` 打开已存在的资源管理器窗口时不会强制激活。
    * 解决：新增 `_open_folder_front()`，使用 `explorer.exe` 打开并在打开后通过 `win32gui` 查找窗口、
      `ShowWindow(SW_RESTORE)` + `SetForegroundWindow()` 强制置顶。

变更 v2.3.20：
  - 集成 Temu 核价控制台 (`/pricing`) 与 Hermes 核价引擎。
  - 新增 `/api/pricing/*` 端点：启动核价、停止、状态轮询、导出结果、下载 Excel、发送 "好了" 信号。
  - 新增 `pricing.html` 前端页面，支持完整自动核价 / 仅核价不提交 / 继续提交 / 重试指定页 / 导出结果。
  - 修复长页核价时滚动回顶导致无法完成的问题（联动 temu-hengjia-engine v5.2.1）。
  - 核价结果输出到 `C:/Users/Administrator/Desktop/核价档案`。

变更 v2.3.19：
  - `upload.html`（WB 上款页面）新增「📋 复制未上款」按钮。
  - 一键复制当前未上款列表中的所有 DX 款号到剪贴板（逗号分隔）。
  - 兼容 `navigator.clipboard` 与 `document.execCommand('copy')` 兜底。

变更 v2.3.17：
  - `lovart_bridge.bat` 启动 Chrome 增加 `--window-size=1400,900`，避免 Bridge 面板默认最大化占据整个屏幕。
  - 同步 wb上款 v1.3.20：Edge 自动化期间默认最小化到任务栏。

变更 v2.3.16：
  - 同步 wb上款 v1.3.19：
    * Edge 窗口默认可见（WB_EDGE_VISIBLE=1），便于上款过程人工观察与调试。
    * 分类选择精确匹配当前月份，避免跨月份分类误选。

变更 v2.3.15：
  - AI 去背 贴图 OS (`engine/check_rem.py v2.2.6`)：
    * 修复 DX0339_W 等单张去背后 02_REM_BG 无输出：美图保存路径未切换时，结果会落到 `_temp_rembg/save`。
      check_rem.py 现在从 `TEMP_REMBG/{DX}/02_REM_BG`、`WB_ROOT/_temp_rembg/save`、`WB_ROOT/_temp_rembg/archive`
      三个位置收集 `_cut.png` / `_副本.png`，并把 `_副本.png` 改名为 `_cut.png`。
    * `rembg_one_file` / `batch_rembg` 暂存时额外复制 `source_map.json` 与原始配对文件（1B.png / 1W.png 等），
      让美图 `precheck_pairs` 正确识别 B/W 角色与配对完整性。
    * 修复 `/batch-rembg` 的 BW 过滤 bug：原实现按全局 `dx_files` 判断是否含 BW，导致前一个有 BW 的款会污染后续所有款；
      现在每个 DX 独立判断，只跳过该 DX 自己的 B/W。
    * `engine/_rembg_worker.py` 增加文件日志，输出写入 `D:\Semems WB\_debug\_rembg_worker_YYYYMMDD_HHMMSS.log`。

变更 v2.3.14：
  - AI 去背 贴图 OS (`engine/check_rem.py v2.2.4`)：
    * 修复单张「重新去背」点击后无响应/不生成去背图的问题
    * 补全缺失的 `engine/_rembg_worker.py`：负责在后台运行美图去背并清理锁文件
    * `rembg_one_file` 暂存时把同 DX 所有生成图都放进临时目录，避免美图配对预检跳过

变更 v2.3.12：
  - AI 去背 贴图 OS (`engine/check_rem.py v2.2.3`)：
    * 反相与贴图解耦：反相只生成黑版专用去背图，不再自动调用贴图流水线
    * 贴图由用户单独点击「贴图」或「批量贴图」触发
    * 前端提示文案同步更新，去掉"自动贴图+BW合成"表述

变更 v2.3.11：
  - AI 去背 贴图 OS (`engine/check_rem.py v2.2.2`)：
    * 单张「反相」与「批量反相」统一进入同一个后台任务队列，串行执行
    * 避免连续点击多个反相时并发驱动 Photoshop 导致冲突
    * `/invert-rem` 与 `/batch-invert-rem` 改为立即返回「已加入队列」
    * 前端 `check_rem.js` 轮询 `/batch-invert-result` 获取完成状态
  - 与 wb上款 v1.3.16 联动版本对齐（运行时在线校验 + 终检）

变更 v2.3.10：
  - WB 上款页面新增「刷新已上款」功能：
    * 调用 wb上款 v1.3.14 的 check_online_listed.py
    * 从店小秘 Temu 在线产品页抓取 SKU，提取 DX 款号
    * 在线已上款成为 /upload 页面已上款状态的唯一权威来源
    * 新增 /api/upload/refresh-online-listed 端点
    * upload.html 增加刷新按钮、在线验证徽章、进度面板在线计数
  - 与 wb上款 v1.3.14 联动版本对齐

变更 v2.3.9：
  - 文档与版本同步：更新 SKILL.md / CHANGELOG.md / ARCHITECTURE.md / REPRODUCIBILITY.md
  - 明确与 wb上款 v1.3.13 联动：Edge 透明隐藏、LoginGuard URL 兜底、豆包传图修复
  - 新增 REPRODUCIBILITY.md：一键复现、回滚到 Tag、问题与解决记录

变更 v2.3.7：
  - 修复 /api/upload/progress 计数/百分比异常：只按当前选中的款号统计 done/fail/total
    避免历史已完成记录把 done_count 撑爆 total_count，导致 "280 / 41 (683%)" 这种显示
  - upload.html 进度文案改为：已上款 X / 总 Y  失败 Z  剩余 W，信息更直观
  - AI 生图对比页 (/ai-review) 缩略图 URL 增加 mtime 参数，重新生图后浏览器自动刷新缓存
  - AI 重新生图任务输出使用 PYTHONUNBUFFERED=1，日志实时可见

变更 v2.3.6：
  - check_rem.py 启动后 1 秒自动后台预扫描，把 scan_projects 结果 warming 到缓存
  - 用户首次打开去背预览首页时即可享受热缓存，无需等待 10+ 秒扫描

变更 v2.3.5：
  - Bridge 启动时后台守护 check_rem.py（端口 8766），「去背预览」点击即开
  - 简化 /api/launch-check-rem：不再启动进程/等待扫描，只兜底确认端口就绪
  - 去背预览按钮改为直接 window.open，与 AI 对比按钮一致，瞬时响应
  - 上款页面图片增加 loading="lazy" + decoding="async"，减少初始加载压力
  - 上款页面加载时显示「加载中…」提示，避免空白等待
  - check_rem.py scan_projects 增加 30 秒缓存，大幅提升首页刷新速度

变更 v2.3.4：
  - 修复去背预览页面悬停放大图位置乱跳：
    原 JS 用固定 900x90vh 估算预览图尺寸来定位，与实际渲染尺寸不符。
  - 新逻辑：等原图加载后读取 preview 元素实际 offsetWidth/offsetHeight 再定位；
    水平默认放缩略图右侧，溢出则放左侧；垂直仅做必要平移，不再大幅跳动。

变更 v2.3.3：
  - 修复 Y2 控制台「上款」按钮打不开：原链接使用 http://localhost:8765/upload，
    在 IPv6/localhost 解析异常或 Bridge 仅监听 127.0.0.1 时触发 ERR_CONNECTION_REFUSED。
  - 改为相对路径 /upload，确保与当前 Y2 控制台同域（127.0.0.1:8765），避免 localhost 解析问题。

变更 v2.3.2：
  - 修复 check_rem.py 启动崩溃：print 语句中的 emoji（🔄）在 GBK 控制台导致 UnicodeEncodeError
  - 强制 check_rem.py stdout/stderr 使用 UTF-8，避免 Windows GBK 控制台打印生僻字符/emoji 崩溃
  - 优化「去背预览」启动速度：移除阻塞式 90 秒预扫描，端口 ready 后快速 ping 并立即打开浏览器
  - 「去背预览」尝试在已有 Chrome 窗口中以新标签页打开（new=2）

变更 v2.3.1：
  - Y2 控制台所有日期分类统一按 DX 文件夹建立日期（st_ctime）
  - /upload、/ai-review、去背预览等页面不再按 AI/去背/贴图文件最后更新时间分类
  - 移除 _load_upload_date_map，简化日期来源

变更 v2.3.0：
  - 新增 AI 生图对比页面 (/ai-review)：在同一界面并排对比原图与 AI 生成图
  - 支持单张重新生图，输出到原 DX 文件夹（新图自动命名 DXxxxx_B2.png 等，不覆盖旧图）
  - 支持批量重新生图：勾选多张原图一键并发重跑，调用 Lovart 正常并发能力
  - 重新生图使用 MD5 检测 INBOX 同名冲突，避免错用旧批次原图
  - 状态面板实时显示：款号、Key、已用时间、成功/失败张数、进度、可展开原始日志
  - 状态面板区分「已完成」「部分失败」「失败」，避免 completed + fail_count>0 误导
  - 重新生图与 Lovart 管线统一读取 config/POD AI VIRAL FACTORY v3.md 提示词文件
  - AI 生图对比页默认显示最新日期
  - Y2 控制台所有日期分类统一按 DX 文件夹建立日期（st_ctime），不再按文件最后更新时间

变更 v2.2.1：
  - 修复 /upload 页面款号日期全部归到同一天的问题

变更 v2.2.0：
  - UID/group_id 全链路溯源：从 INBOX 开始绑定唯一 UID 和组 ID
  - 生图阶段写入 .generation_uid_manifest.json 并传给 Lovart
  - 为 AI 图、去背图、贴图成品、BW 合成图生成 .meta.json sidecar
  - 每个 DX 目录维护 uid_map.json，不依赖文件名即可回溯同一组图片
  - 解决 WB去背/registry.py 与 Bridge 双写 .image_registry.json 的冲突
  - WB去背 registry 改为独立写入 .wb_rembg_registry.json

变更 v2.1.9：
  - 新增「强制重新上款」开关
  - /api/batch-upload 支持 force=true，自动从 已上款货号_wb.md 删除对应款号后再启动 wb_listing.py
  - 不修改 wb_listing.py 内部逻辑，保持 wb上款 v1.3.1-stable 稳定版本不变

变更 v2.1.8：
  - /api/batch-upload 改为 --only 精确上款：勾选哪款就上哪款，不会继续后续款
  - 新增 /api/upload/progress 端点，读取 wb_listing.py 写入的 .wb_upload_progress.json
  - /upload 页面拆分为「未上款 / 已上款」两个区域，已上款自动沉底
  - 上款页面新增进度条、当前款、已用时间、平均耗时、预计剩余时间
  - 默认选中最新日期，勾选框仅对未上款卡片生效
  - 修复缩略放大图在屏幕下方时显示不全的问题

变更 v2.1.7：
  - /upload 页面默认选中最新日期
  - 移除后台预生成缩略图（反而拖慢），改用 Flask threaded=True 并发处理缩略图请求
  - 修复批量上传仍提示未配置脚本的问题（代码已更新，需重启 Bridge 生效）
  - /api/batch-upload 改为只启动一次 wb_listing.py，以选中款中最早的 DX 为起点连续处理
  - 修复 lovart_bridge.bat：Chrome 启动时 detached，关闭 CMD 后 Chrome 不再被关闭

变更 v2.1.6：
  - /api/batch-upload 默认对接 E:\Claude code\wb上款\wb_listing.py
  - 批量上款按顺序逐个 DX 启动 wb_listing.py，避免浏览器状态冲突
  - 优化 /upload 页面缩略图加载速度：后台预生成、透明检测、Cache-Control 缓存
  - 修复 upload.html 批量上传后页面刷新逻辑

变更 v2.1.4：
  - 移除 PS贴图控制台，替换为「上款」页面 (/upload)
  - 上款页面展示每款 03_UPLOAD 成品缩略图，按 BW/B/W 分组
  - 支持勾选款号，批量上传按钮，对接 /api/batch-upload
  - 新增 /api/upload/projects、/api/upload/thumb、/api/upload/original 端点
  - 图片显示逻辑与 AI 去背 贴图 页一致：缩略图 + 鼠标悬停放大

变更 v2.1.2：
  - Bridge 内一键启动 check_rem.py / PS贴图 / BW合成 时，子进程窗口最小化，不抢焦点
  - 新增 run_minimized() 工具函数，统一 Windows 最小化启动逻辑

变更 v2.1：
  - 支持命令行参数 --port / --host，便于启动脚本自定义端口
  - 启动时写入 bridge.pid，供 lovart_bridge.bat 优雅停止服务

变更 v2.0：
  - Registry v4 / 血缘引擎 / AutoScan / Lineage API
  - lovart_control.html 控制面板 v2.0

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
import argparse
import socket
from urllib.request import urlopen
from urllib.error import URLError
from ctypes import wintypes
from pathlib import Path
from datetime import datetime
import urllib.parse

try:
    from flask import Flask, jsonify, request, send_file, abort, make_response
except ImportError:
    print("ERROR: Flask not installed. Run: pip install flask")
    sys.exit(1)

# 加载 UID 元数据模块（Bridge 项目内 lib/ 目录）
_WB_META_PATH = Path(__file__).parent / "lib"
if str(_WB_META_PATH) not in sys.path:
    sys.path.insert(0, str(_WB_META_PATH))
try:
    import wb_meta
except Exception as e:
    print(f"WARN: wb_meta 模块加载失败: {e}")
    wb_meta = None

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

HOVER_CACHE    = INBOX_DIR / "_hover_cache"  # 悬停预览缩略图缓存
UID_MANIFEST_FILE = BASE_DIR / ".generation_uid_manifest.json"  # 传给 Lovart 的 UID 清单

AI_TRASH_DIR   = BASE_DIR / "_ai_trash"        # AI 图回收站
AI_THUMB_DIR   = BASE_DIR / "_ai_review_thumbs"  # AI 对比页缩略图缓存

# Lovart 处理记录文件：重新生图时需要清除对应 hash，否则 Lovart 会跳过
LOVART_TRACK_FILE = Path("E:/Claude code/lovart-official/.processed_track.json")

# ============================================================================
# Temu 核价（Hermes）项目路径
# ============================================================================
PRICING_DIR        = Path("E:/Claude code/Temu自动化/核价")
PRICING_ENTRYPOINT = PRICING_DIR / "entrypoint"
PRICING_MAIN       = PRICING_DIR / "hengjia.py"
PRICING_STATE_FILE = PRICING_DIR / "hengjia_state.json"
PRICING_OUTPUT_DIR = Path(r"C:\Users\Administrator\Desktop\核价档案")

# ============================================================================
# Temu 建议零售价填写项目路径
# ============================================================================
RETAIL_PRICE_DIR   = Path("E:/Claude code/WB Lovart")
RETAIL_PRICE_SCRIPT = RETAIL_PRICE_DIR / "建议零售价.js"

# ============================================================================
# Temu 报活动项目路径
# ============================================================================
ACTIVITY_DIR        = 'E:/Claude code/Temu自动化/报活动'
ACTIVITY_ENTRYPOINT = ACTIVITY_DIR + '/entrypoint/run.py'
ACTIVITY_STATE_FILE = ACTIVITY_DIR + '/state/state.json'

# ============================================================================
# 胚衣制作（素材库）路径
# ============================================================================
MATERIAL_DIR   = BASE_DIR / "03_MATERIAL"
# 四大分类：白(W正/B背) / 黑(W正/B背)
PEIYI_CATEGORIES = {
    "W白": MATERIAL_DIR / "W白",
    "B白": MATERIAL_DIR / "B白",
    "W黑": MATERIAL_DIR / "W黑",
    "B黑": MATERIAL_DIR / "B黑",
}
# 各分类底色（JPG 输出）：白胚衣用白底、黑胚衣用黑底
PEIYI_BG = {
    "W白": (255, 255, 255),
    "B白": (255, 255, 255),
    "W黑": (0, 0, 0),
    "B黑": (0, 0, 0),
}
PEIYI_SIZE = (1340, 1785)   # 目标分辨率
PEIYI_DPI  = (72, 72)       # 目标 DPI
PEIYI_ALLOWED_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')
# 遮罩功能生成的侧车文件后缀：这些不显示在素材库画廊，只在“预览遮罩”时单独查看
PEIYI_MASK_SUFFIXES = (
    '_occluder.png', '_occluder_mask.png', '_body_mask.png',
    '_parse.png', '_alpha.png',
)
# 每张素材侧车(.meta.json)记录的5个贴图参数，与 胚衣参数表_模板.csv 第5-9列一致
PEIYI_META_FIELDS = [
    ("width", "缩放后宽(px)", 0),
    ("height", "缩放后高(px)", 0),
    ("rotation", "旋转角度(负=逆/正=顺)", 0),
    ("highest_y", "最高像素点y", 0),
    ("center_x", "中心点x", 670),   # 670 = 1340 画布宽中点
]
PEIYI_META_KEYS = [k for k, _, _ in PEIYI_META_FIELDS]

# 贴图（AI 去背贴图）相关常量
TPL_ROOT = Path(r"D:\Semems\1胚衣\_tpl")          # _tpl/<款名>/ 扭曲素材根
CSV_PATH = Path(r"E:\Kimi Code\docs\胚衣参数表_模板.csv")
MOCKUP_PY = Path(r"C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe")
MOCKUP_ROOT = Path(r"E:/Kimi Code")              # white_t_mockup 所在目录（运行 -m white_t_mockup）
PY_PACKAGES = "E:/python_packages"
MOCKUP_OUT = BASE_DIR / "03_MOCKUP_OUT"          # 贴图成品输出
ZCODE_PROJECT = Path(__file__).resolve().parent  # 本文件所在目录（peiyi_mask / tpl_generator 在此）


def _single_thread_env(base_env):
    """准备子进程环境：禁用 OpenMP/MKL 多线程，并清理无效 PATH 项（如 cv2 留下的裸驱动器号）。"""
    env = dict(base_env)
    # cv2 初始化会往 PATH 追加形如 "E;" 的裸驱动器号，导致子进程 Python 找不到 DLL 而静默退出
    raw_path = env.get("PATH", "")
    cleaned = []
    for p in raw_path.split(os.pathsep):
        p = p.strip()
        if not p:
            continue
        # 丢弃纯驱动器号项（如 "E" 或 "E:"）
        if len(p.rstrip(":")) == 1 and p[0].isalpha():
            continue
        cleaned.append(p)
    env["PATH"] = os.pathsep.join(cleaned)
    env.update({
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        # 彻底关闭 cv2 内部多线程：后台/服务进程里 cv2 的 warp/remap 等多线程操作
        # 偶发段错误（静默 rc!=0、无输出），关闭后所有 cv2 子进程稳定
        "OPENCV_DISABLE_THREADING": "1",
    })
    return env
MOCKUP_OUT.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 工具函数：处理 Lovart 去重记录
# ============================================================================
def _compute_sha256(path: str) -> str:
    """计算文件 SHA256（与 Lovart run_official_v53.py 一致）"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_lovart_track() -> list:
    """读取 Lovart 处理记录 track 文件"""
    if not LOVART_TRACK_FILE.exists():
        return []
    try:
        return json.loads(LOVART_TRACK_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []


def _save_lovart_track(track: list):
    """写入 Lovart 处理记录 track 文件"""
    try:
        LOVART_TRACK_FILE.write_text(json.dumps(track, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[WARN] 保存 Lovart track 失败: {e}", flush=True)


def _remove_from_lovart_track(img_path: Path) -> int:
    """从 Lovart track 中移除指定图片的 hash / name+size 记录，强制下次重新处理。
    返回移除的条目数。"""
    if not img_path.exists():
        return 0
    try:
        img_hash = _compute_sha256(str(img_path))
        img_size = img_path.stat().st_size
        img_name = img_path.name
    except Exception:
        return 0
    track = _load_lovart_track()
    orig_len = len(track)

    def _matches(e):
        # hash 唯一标识（优先）
        if img_hash and e.get("hash") == img_hash:
            return True
        # 兼容旧记录：同名同尺寸也清除，避免换批次后仍被误判为已处理
        if e.get("name") == img_name and e.get("size") == img_size:
            return True
        return False

    track = [e for e in track if not _matches(e)]
    removed = orig_len - len(track)
    if removed:
        _save_lovart_track(track)
    return removed


# ============================================================================
# 工具函数：Windows 下最小化启动子进程（不抢焦点）
# ============================================================================
def run_minimized(cmd, cwd=None, wait=False, no_console=False):
    """以最小化/不激活窗口启动子进程，用于 check_rem / PS 贴图等任务。

    参数:
      no_console: True 时使用 CREATE_NO_WINDOW，不弹控制台黑窗，同时把 stdout/stderr 重定向到 DEVNULL。
                  适用于 wb_listing.py / check_online_listed.py 这种自己有日志文件的后台任务。
    """
    import subprocess
    import ctypes
    from ctypes import wintypes

    STARTUPINFO = subprocess.STARTUPINFO
    SW_SHOWMINNOACTIVE = 7
    STARTF_USESHOWWINDOW = 1

    si = STARTUPINFO()
    si.dwFlags |= STARTF_USESHOWWINDOW
    si.wShowWindow = SW_SHOWMINNOACTIVE

    kwargs = {
        "startupinfo": si,
    }
    if no_console:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    else:
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    if cwd:
        kwargs["cwd"] = str(cwd)

    proc = subprocess.Popen(cmd, **kwargs)
    if wait:
        proc.wait()
        return proc
    return proc


def _port_ready(host, port, timeout=2):
    """检查指定端口是否已监听。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def _check_rem_daemon():
    """后台守护线程：Bridge 启动后保持 check_rem.py（端口 8766）常驻运行。

    使用 CREATE_NO_WINDOW 启动，避免依赖桌面窗口（无头/后台环境下也能拉起）；
    输出重定向到 check_rem_daemon.log 便于排查。每 5 秒检测一次端口，
    若 check_rem 崩溃退出会自动重拉，实现自愈。
    """
    import subprocess
    script = Path("D:/Semems WB/04_OS/engine/check_rem.py")
    if not script.exists():
        print("  [check_rem daemon] 脚本不存在，跳过守护", flush=True)
        return
    log_path = script.parent / "check_rem_daemon.log"
    while True:
        try:
            if not _port_ready("127.0.0.1", 8766, timeout=3):
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                try:
                    env = dict(os.environ)
                    env["OPEN_BROWSER"] = "0"
                    logf = open(log_path, "a", encoding="utf-8")
                    logf.write(f"[{ts}] 端口 8766 未就绪，启动 check_rem.py ...\n")
                    logf.flush()
                    proc = subprocess.Popen(
                        [sys.executable, str(script)],
                        cwd=str(script.parent),
                        env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        stdout=logf,
                        stderr=subprocess.STDOUT,
                    )
                    print(f"  [check_rem daemon] 已启动 check_rem.py (PID={proc.pid})", flush=True)
                except Exception as e:
                    print(f"  [check_rem daemon] 启动失败: {e}", flush=True)
            time.sleep(5)
        except Exception:
            time.sleep(5)


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
            status = saved.get("status", "")
            if status in ("completed", "error", "idle"):
                task_state = saved
            elif status == "running":
                # 进程已不在，标记为中断
                saved["status"] = "error"
                saved["progress"] = "⚠️ 上次任务未完成（服务重启中断）"
                saved["completed_at"] = datetime.now().isoformat()
                saved["log"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 服务重启，任务中断")
                task_state = saved
        except Exception:
            pass


# ============================================================================
# 核价任务状态（Hermes / Temu 核价）
# ============================================================================
pricing_task = {
    "status": "idle",          # idle | running | completed | error | stopped
    "mode": None,              # full | no-submit | continue | retry | export
    "task_label": "",
    "started_at": None,
    "completed_at": None,
    "proc": None,
    "log": [],
    "log_index": 0,            # 前端已读取到的位置
    "processed_pages": 0,
    "elapsed_sec": 0,
    "page_records": [],
}
pricing_lock = threading.Lock()


# ============================================================================
# 报活动任务状态
# ============================================================================
activity_task = {
    "status": "idle",          # idle | running | completed | error | stopped
    "started_at": None,
    "completed_at": None,
    "proc": None,
    "log": [],
    "log_index": 0,            # 前端已读取到的位置
}
activity_lock = threading.Lock()


# ============================================================================
# 建议零售价填写任务状态
# ============================================================================
retail_price_task = {
    "status": "idle",          # idle | running | completed | error | stopped
    "task_label": "",
    "started_at": None,
    "completed_at": None,
    "proc": None,
    "log": [],
    "log_index": 0,            # 前端已读取到的位置
    "elapsed_sec": 0,
}
retail_price_lock = threading.Lock()


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


def ensure_registry_v4(reg: dict) -> dict:
    """确保 registry 包含 v4 字段（含溯源信息）"""
    v = reg.get("version", 1)
    # v3 fields
    reg.setdefault("groups", {})
    reg.setdefault("uid_index", {})
    reg.setdefault("name_index", {})
    # v4 provenance fields
    reg.setdefault("provenance", {"tree": {}, "broken": []})
    if v < 4:
        reg["version"] = 4
        # 为所有现有图片添加溯源字段
        for md5, entry in reg.get("images", {}).items():
            _add_provenance_fields(entry)
    return reg


# ── 溯源字段 ────────────────────────────────────────

PROVENANCE_FIELDS = {
    "source_md5": "",       # 来源图片的 MD5
    "source_type": "",      # inbox | ai_gen | rembg | upload
    "root_md5": "",         # 最原始 INBOX 图片的 MD5
    "root_name": "",        # 最原始 INBOX 文件名
    "derived_md5s": [],     # 由此图片衍生出的 MD5 列表
    "lineage_status": "",   # confirmed | inferred | missing
}


def _add_provenance_fields(entry: dict):
    """为单条图片记录添加溯源字段"""
    for field, default in PROVENANCE_FIELDS.items():
        entry.setdefault(field, default)


def _register_provenance(reg: dict, child_md5: str, parent_md5: str, source_type: str,
                          lineage_status: str = "inferred"):
    """记录 child_md5 由 parent_md5 通过 source_type 方式生成。
    
    lineage_status:
      confirmed - Hook 实时记录（可信）
      inferred  - Scanner 推断（需验证）
      missing   - 断链
    """
    child = reg["images"].get(child_md5)
    parent = reg["images"].get(parent_md5)
    if not child or not parent:
        return

    _add_provenance_fields(child)
    _add_provenance_fields(parent)

    child["source_md5"] = parent_md5
    child["source_type"] = source_type
    child["lineage_status"] = lineage_status
    # root_md5 继承：如果 parent 有 root_md5 则继承，否则 parent 自己就是 root
    child["root_md5"] = parent.get("root_md5") or parent_md5
    child["root_name"] = parent.get("root_name") or parent.get("inbox_original_name") or parent.get("original_name", "")

    # 在 parent 的 derived 列表中添加 child
    if parent_md5 not in parent["derived_md5s"]:
        parent["derived_md5s"].append(child_md5)

    # 更新 provenance tree 索引
    tree = reg.setdefault("provenance", {}).setdefault("tree", {})
    tree.setdefault(parent_md5, [])
    if child_md5 not in tree[parent_md5]:
        tree[parent_md5].append(child_md5)


# ── 批量扫描：建立现有文件的溯源链 ─────────────────

def scan_provenance():
    """扫描所有 DX 文件夹，通过文件 stem 精确匹配建立血缘关系。
    
    规则（不改文件名，用现有命名语义）：
      AI:       DX{N}_{role}.png                   → 父级 = INBOX 原图（source_map）
      去背:     DX{N}_{role}_cut.png                → 父级 = AI 图（去掉 _cut）
      去背变体:  DX{N}_{Chinese}{role}_cut.png      → 父级 = AI 图（去掉中文+_cut）
      贴图:     DX{N}_{role}_XXX.jpg                → 父级 = 去背图（如存在），否则 = AI 图
    """
    reg = load_registry()
    reg = ensure_registry_v4(reg)
    count = 0

    # 加载 Lovart registry（用于 AI → 原图）
    lovart_reg = {}
    lr_path = Path("D:/Semems WB/WB_REGISTRY/registry.json")
    if lr_path.exists():
        try:
            with open(lr_path, 'r', encoding='utf-8') as f:
                lovart_reg = json.load(f)
        except Exception:
            pass

    # 预计算：同一 DX 内所有文件的 md5 索引（dx_dir内的相对文件名 → md5）
    # 避免重复 compute_md5
    def _index_dir(dirpath):
        idx = {}
        if dirpath.exists():
            for f in os.listdir(dirpath):
                fp = dirpath / f
                if fp.is_file():
                    idx[f] = compute_md5(str(fp))
        return idx

    for d in sorted(os.listdir(PROJECTS_DIR)):
        if not d.startswith('DX'):
            continue
        ai_dir = PROJECTS_DIR / d / "01_AI"
        rem_dir = PROJECTS_DIR / d / "02_REM_BG"
        up_dir  = PROJECTS_DIR / d / "03_UPLOAD"

        ai_idx = _index_dir(ai_dir)
        rem_idx = _index_dir(rem_dir)
        up_idx = _index_dir(up_dir)

        # ── 1) AI 图 → INBOX 原图 ──
        sm_path = PROJECTS_DIR / d / "source_map.json"
        src_id_map = {}
        if sm_path.exists():
            try:
                with open(sm_path, 'r', encoding='utf-8') as f:
                    sm = json.load(f)
                for src in sm.get("sources", []):
                    src_id_map[src.get("file", "")] = src.get("src_id", "")
            except Exception:
                pass

        for fname, md5 in ai_idx.items():
            if md5 not in reg.get("images", {}):
                continue
            entry = reg["images"].get(md5, {})
            _add_provenance_fields(entry)
            if entry.get("source_md5"):
                continue

            # source_map → Lovart registry → original name
            src_id = src_id_map.get(fname, "")
            if src_id and src_id in lovart_reg:
                orig_name = lovart_reg[src_id].get("original_name", "")
                orig_md5 = reg.get("name_index", {}).get(orig_name, "")
                if orig_md5 and orig_md5 in reg.get("images", {}):
                    _register_provenance(reg, md5, orig_md5, "ai_gen")
                    count += 1
                    continue

            # 后备：inbox_original_name 匹配
            for img_md5, img_info in reg.get("images", {}).items():
                if img_info.get("inbox_original_name") and img_info["inbox_original_name"] in fname:
                    _register_provenance(reg, md5, img_md5, "ai_gen")
                    count += 1
                    break

        # ── 2) 去背图 → AI 图 ──
        # 规则: DX{N}_{role}_cut.png → 去掉 _cut → DX{N}_{role}.png
        #       DX{N}_黑{role}_cut.png → 去掉中文再去掉 _cut → DX{N}_{role}.png
        for fname, md5 in rem_idx.items():
            if md5 not in reg.get("images", {}):
                continue
            entry = reg["images"].get(md5, {})
            _add_provenance_fields(entry)
            if entry.get("source_md5"):
                continue

            stem = fname[:-len("_cut.png")] if fname.endswith("_cut.png") else fname.rsplit('.', 1)[0]
            # 尝试直接匹配: stem → AI 图
            ai_stem = re.sub(r'[\u4e00-\u9fff]+', '', stem)
            ai_candidate = f"{ai_stem}.png"
            if ai_candidate in ai_idx:
                ai_md5 = ai_idx[ai_candidate]
                if ai_md5 in reg.get("images", {}):
                    _register_provenance(reg, md5, ai_md5, "rembg")
                    count += 1
                    continue

        # ── 3) 贴图图 → 去背图 / AI 图 ──
        # 规则: DX{N}_{role}_XXX.jpg → 去掉中文后缀 → DX{N}_{role}
        #       先找 DX{N}_{role}_cut.png（去背），再找 DX{N}_{role}.png（AI）
        for fname, md5 in up_idx.items():
            if md5 not in reg.get("images", {}):
                continue
            entry = reg["images"].get(md5, {})
            _add_provenance_fields(entry)
            if entry.get("source_md5"):
                continue

            # 提取基础 stem：去掉文件后缀和中文部分
            stem = fname.rsplit('.', 1)[0]
            base_stem = re.sub(r'[\u4e00-\u9fff].*$', '', stem)

            # 优先找去背图
            cut_candidate = f"{base_stem}_cut.png"
            if cut_candidate in rem_idx:
                cut_md5 = rem_idx[cut_candidate]
                if cut_md5 in reg.get("images", {}):
                    _register_provenance(reg, md5, cut_md5, "upload")
                    count += 1
                    continue

            # 其次找 AI 图
            ai_candidate = f"{base_stem}.png"
            if ai_candidate in ai_idx:
                ai_md5 = ai_idx[ai_candidate]
                if ai_md5 in reg.get("images", {}):
                    _register_provenance(reg, md5, ai_md5, "upload")
                    count += 1
                    continue

    save_registry(reg)
    return count


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
    pattern = re.compile(r'^(\d+)([bw]+)(\.(png|jpg|jpeg|webp))$', re.IGNORECASE)
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


def send_to_recycle_bin(path: str) -> bool:
    """将指定文件直接送入系统回收站（可手动还原）"""
    try:
        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = 0
        fileop.wFunc = FO_DELETE
        fileop.pFrom = str(path) + "\0"
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION
        return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop)) == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# AI 图回收站（用于 ai-review 页面临时删除/还原）
# ---------------------------------------------------------------------------

def _ai_trash_meta_path(dx: str) -> Path:
    """返回某 DX 的回收站元数据文件路径"""
    return AI_TRASH_DIR / dx / ".trash_meta.json"


def move_ai_to_trash(dx: str, filename: str) -> tuple:
    """将 AI 图从 01_AI 移到回收站。返回 (ok, msg)"""
    if not re.match(r"^DX\d+$", dx):
        return False, "无效的 DX 编号"
    safe = os.path.basename(filename)
    src = PROJECTS_DIR / dx / "01_AI" / safe
    if not src.exists():
        return False, f"文件不存在: {dx}/01_AI/{safe}"

    AI_TRASH_DIR.mkdir(parents=True, exist_ok=True)
    trash_dx = AI_TRASH_DIR / dx
    trash_dx.mkdir(parents=True, exist_ok=True)
    dst = trash_dx / safe

    # 防重名
    if dst.exists():
        stem, ext = os.path.splitext(safe)
        dst = trash_dx / f"{stem}_{int(time.time())}{ext}"

    try:
        shutil.move(str(src), str(dst))
    except Exception as e:
        return False, f"移动失败: {e}"

    # 记录元数据
    meta = {}
    meta_path = _ai_trash_meta_path(dx)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta[dst.name] = {
        "original_path": f"02_PROJECTS/{dx}/01_AI/{safe}",
        "deleted_at": datetime.now().isoformat(),
        "dx": dx,
    }
    try:
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    # 清理 AI 对比缩略图缓存（使用与 _get_ai_thumb 一致的 safe_name）
    thumb_safe = re.sub(r'[\\/*?:"<>|]', '_', safe)
    for tf in AI_THUMB_DIR.glob(f"{dx}__{thumb_safe}.*"):
        try:
            tf.unlink()
        except Exception:
            pass

    return True, f"{safe} 已移入 AI 回收站"


def restore_ai_from_trash(dx: str, filename: str) -> tuple:
    """从回收站还原 AI 图到 01_AI。返回 (ok, msg)"""
    if not re.match(r"^DX\d+$", dx):
        return False, "无效的 DX 编号"
    safe = os.path.basename(filename)
    src = AI_TRASH_DIR / dx / safe
    if not src.exists():
        return False, f"回收站中不存在: {safe}"

    ai_dir = PROJECTS_DIR / dx / "01_AI"
    ai_dir.mkdir(parents=True, exist_ok=True)
    dst = ai_dir / safe

    # 防重名
    if dst.exists():
        stem, ext = os.path.splitext(safe)
        dst = ai_dir / f"{stem}_restored{ext}"

    try:
        shutil.move(str(src), str(dst))
    except Exception as e:
        return False, f"还原失败: {e}"

    # 清理元数据
    meta_path = _ai_trash_meta_path(dx)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.pop(safe, None)
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return True, f"{safe} 已还原到 {dx}/01_AI"


def list_ai_trash() -> list:
    """列出 AI 回收站中的所有文件"""
    items = []
    if not AI_TRASH_DIR.exists():
        return items
    for dx_dir in sorted(AI_TRASH_DIR.iterdir()):
        if not dx_dir.is_dir() or not re.match(r"^DX\d+$", dx_dir.name):
            continue
        dx = dx_dir.name
        meta = {}
        meta_path = _ai_trash_meta_path(dx)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        for f in sorted(dx_dir.iterdir()):
            if not f.is_file() or f.name.startswith("."):
                continue
            info = meta.get(f.name, {})
            items.append({
                "dx": dx,
                "filename": f.name,
                "deleted_at": info.get("deleted_at", ""),
                "preview_url": f"/api/ai-review/trash-thumb?dx={dx}&file={f.name}",
            })
    return items


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
# 上款（Upload）：扫描 03_UPLOAD 并提供缩略图
# ---------------------------------------------------------------------------

UPLOAD_THUMB_DIR = BASE_DIR / "_upload_thumbs"
UPLOAD_PROGRESS_FILE = BASE_DIR / ".wb_upload_progress.json"
UPLOAD_RECORD_MD = BASE_DIR / "已上款货号_wb.md"
ONLINE_LISTED_FILE = BASE_DIR / ".wb_online_listed.json"

def _dx_dir_date(d: Path) -> str:
    """返回 DX 文件夹建立日期（YYMMDD），所有日期分类统一用建立时间。"""
    try:
        return time.strftime("%y%m%d", time.localtime(d.stat().st_ctime))
    except Exception:
        return ""


def _scan_upload_projects():
    """扫描所有 DX 的 03_UPLOAD，返回 [{dx, date, files:[{name,mtime}]}]
    date 统一按 DX 文件夹建立日期分类，不再按文件最后更新时间。
    """
    projects = []
    if not PROJECTS_DIR.exists():
        return projects
    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir() or not re.match(r"^DX\d+$", d.name):
            continue
        up_dir = d / "03_UPLOAD"
        if not up_dir.is_dir():
            continue
        dx = d.name
        files = []
        for f in sorted(up_dir.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.webp'):
                continue
            src_mtime = int(f.stat().st_mtime)
            thumb = _upload_thumb_path(dx, f.name)
            thumb_mtime = int(thumb.stat().st_mtime) if thumb.exists() else src_mtime
            files.append({"name": f.name, "mtime": src_mtime, "thumb_mtime": thumb_mtime})
        if not files:
            continue
        dx_date = _dx_dir_date(d)
        projects.append({"dx": dx, "date": dx_date, "files": files})
    return projects


def _scan_ai_review_projects():
    """扫描所有 DX 项目的 01_AI 目录，直接在同一目录内配对原图与 AI 生成图。

    约定：每个 DX/01_AI 中同时存放原图（如 1BW.png）和生成图（如 DX0283_BW.png）。
    配对方式：
      1. 优先读取 source_map.json，并用 Lovart registry 根据 src_id 找到 original_name。
      2. 回退到 uid_map / sidecar 元数据。
      3. 再回退按 role 后缀从 01_AI 中找同 role 的原图。

    返回结构：
    [
      {
        "dx": "DX0287",
        "date": "260703",
        "groups": [
          {
            "group_id": "G_00123",
            "design_number": 1,
            "role": "BW",
            "source_file": "1BW.png",
            "ai_file": "DX0287_BW.png",
            "ai_exists": True,
            "paired": True
          }
        ]
      }
    ]
    """
    projects = []
    if not PROJECTS_DIR.exists():
        return projects

    INBOX_NAME_RE = re.compile(r'^(\d+)(B|W|BW|WB)\.(png|jpg|jpeg|webp)$', re.IGNORECASE)

    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir() or not re.match(r"^DX\d+$", d.name):
            continue
        dx = d.name
        ai_dir = d / "01_AI"
        if not ai_dir.is_dir():
            continue

        # 读取目录内所有图片，同时记录 mtime 用于前端缓存刷新
        all_files = []
        file_mtimes = {}
        for f in sorted(ai_dir.iterdir()):
            if not f.is_file():
                continue
            if not f.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
            if '_副本' in f.name or '已归档' in f.name or '原图' in f.name:
                continue
            all_files.append(f.name)
            try:
                file_mtimes[f.name] = int(f.stat().st_mtime)
            except Exception:
                file_mtimes[f.name] = 0

        # 分离原图与 AI 生成图
        source_files = [f for f in all_files if INBOX_NAME_RE.match(f)]
        ai_files = [f for f in all_files if not INBOX_NAME_RE.match(f) and f.startswith(f"{dx}_")]

        if not ai_files:
            continue

        # 加载 source_map + Lovart registry，建立 ai_file -> source_file
        sm_map = {}
        sm_path = d / "source_map.json"
        if sm_path.exists():
            try:
                lovart_reg_path = Path("D:/Semems WB/WB_REGISTRY/registry.json")
                lovart_reg = {}
                if lovart_reg_path.exists():
                    try:
                        with open(lovart_reg_path, 'r', encoding='utf-8') as lf:
                            lovart_reg = json.load(lf)
                    except Exception:
                        lovart_reg = {}

                with open(sm_path, 'r', encoding='utf-8') as f:
                    sm = json.load(f)
                for src in sm.get("sources", []):
                    ai_file = src.get("file", "")
                    orig = src.get("original_name", "")
                    src_id = src.get("src_id", "")
                    if not orig and src_id and src_id in lovart_reg:
                        orig = lovart_reg[src_id].get("original_name", "")
                    if ai_file:
                        sm_map[ai_file] = orig
            except Exception:
                pass

        groups = []
        paired_ai = set()

        # 1. source_map / Lovart registry 精确配对
        for ai_file in ai_files:
            source_name = sm_map.get(ai_file, "")
            role = _role_from_ai_name(ai_file, dx)
            if source_name and source_name in source_files:
                paired_ai.add(ai_file)
                groups.append({
                    "group_id": "",
                    "design_number": _design_number_from_inbox(source_name),
                    "role": role,
                    "source_file": source_name,
                    "source_mtime": file_mtimes.get(source_name, 0),
                    "ai_file": ai_file,
                    "ai_mtime": file_mtimes.get(ai_file, 0),
                    "ai_exists": True,
                    "paired": True,
                })

        # 2. uid_map / sidecar 配对（覆盖或补充）
        if wb_meta is not None:
            try:
                uid_map_data = wb_meta.read_uid_map(d)
                images = uid_map_data.get("images", {})
                source_entries = {}
                ai_entries = {}
                for uid, info in images.items():
                    stage = info.get("stage", "")
                    file_path = Path(info.get("file", "")).name
                    role = info.get("role", "")
                    group_id = info.get("group_id", "")
                    if stage in ("inbox",) and file_path and INBOX_NAME_RE.match(file_path):
                        source_entries[uid] = {"role": role, "group_id": group_id, "file": file_path}
                    elif stage in ("ai", "ai_gen") and file_path:
                        ai_entries[uid] = {"role": role, "group_id": group_id, "file": file_path}

                for uid, src_info in source_entries.items():
                    ai_info = ai_entries.get(uid)
                    if not ai_info:
                        continue
                    source_name = src_info["file"]
                    ai_file = ai_info["file"]
                    if ai_file not in ai_files or source_name not in source_files:
                        continue
                    if ai_file in paired_ai:
                        # 更新已有条目
                        for g in groups:
                            if g["ai_file"] == ai_file:
                                g["source_file"] = source_name
                                g["group_id"] = src_info.get("group_id", "")
                                g["paired"] = True
                                break
                    else:
                        paired_ai.add(ai_file)
                        groups.append({
                            "group_id": src_info.get("group_id", ""),
                            "design_number": _design_number_from_inbox(source_name),
                            "role": src_info.get("role", ""),
                            "source_file": source_name,
                            "source_mtime": file_mtimes.get(source_name, 0),
                            "ai_file": ai_file,
                            "ai_mtime": file_mtimes.get(ai_file, 0),
                            "ai_exists": True,
                            "paired": True,
                        })
            except Exception as e:
                print(f"[AIReview] {dx} uid_map 配对失败: {e}")

        # 3. 把仍未配对的 AI 图按 role 后缀找同 role 原图（最后的回退）
        for ai_file in ai_files:
            if ai_file in paired_ai:
                continue
            role = _role_from_ai_name(ai_file, dx)
            candidates = [f for f in source_files if _role_from_inbox(f) == role]
            source_name = candidates[0] if candidates else ""
            if source_name:
                paired_ai.add(ai_file)
            groups.append({
                "group_id": "",
                "design_number": _design_number_from_inbox(source_name),
                "role": role,
                "source_file": source_name,
                "source_mtime": file_mtimes.get(source_name, 0),
                "ai_file": ai_file,
                "ai_mtime": file_mtimes.get(ai_file, 0),
                "ai_exists": True,
                "paired": source_name != "",
            })

        if not groups:
            continue

        # 合并同一 source_file + role 的多个 AI 变体
        merged = {}
        for g in groups:
            key = (g.get("source_file", ""), g.get("role", "").upper())
            if key not in merged:
                merged[key] = {
                    "group_id": g.get("group_id", ""),
                    "design_number": g.get("design_number", 0),
                    "role": g.get("role", ""),
                    "source_file": g.get("source_file", ""),
                    "source_mtime": g.get("source_mtime", 0),
                    "ai_files": [],
                    "ai_mtimes": [],
                    "paired": False,
                    "ai_exists": False,
                }
            mg = merged[key]
            if g.get("ai_file"):
                mg["ai_files"].append(g["ai_file"])
                mg["ai_mtimes"].append(g.get("ai_mtime", 0))
            if g.get("paired"):
                mg["paired"] = True
            if g.get("ai_exists"):
                mg["ai_exists"] = True
            if g.get("group_id") and not mg["group_id"]:
                mg["group_id"] = g["group_id"]
        groups = list(merged.values())

        # 排序：已配对在前，再按编号、role
        role_order = {"BW": 0, "B": 1, "W": 2, "WB": 3}
        groups.sort(key=lambda g: (
            0 if g["paired"] else 1,
            g["design_number"],
            role_order.get(g["role"].upper(), 99)
        ))

        # 日期统一取 DX 文件夹建立日期
        dx_date = _dx_dir_date(d)

        projects.append({
            "dx": dx,
            "date": dx_date,
            "groups": groups,
        })

    # 排序：未配对/缺图的排前面，其次按日期降序
    projects.sort(key=lambda p: (
        0 if any(not g["paired"] or not g["ai_exists"] for g in p["groups"]) else 1,
        p["date"]
    ), reverse=True)

    return projects


def _role_from_inbox(filename: str) -> str:
    """从 INBOX 文件名提取 role，如 12BW.png -> BW"""
    if not filename:
        return ""
    m = re.match(r'^(\d+)(B|W|BW|WB)\.(png|jpg|jpeg|webp)$', filename, re.IGNORECASE)
    if m:
        return m.group(2).upper()
    return ""

def _design_number_from_inbox(filename: str) -> int:
    """从 INBOX 文件名提取编号，如 12B.png -> 12"""
    if not filename:
        return 0
    m = re.match(r"^(\d+)(B|W|BW|WB)\.(png|jpg|jpeg|webp)$", filename, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def _role_from_ai_name(filename: str, dx: str) -> str:
    """从 AI 文件名推断 role，如 DX0287_BW.png -> BW, DX0287_B2.png -> B"""
    if not filename:
        return ""
    stem, _ = os.path.splitext(filename)
    prefix = f"{dx}_"
    if stem.startswith(prefix):
        suffix = stem[len(prefix):]
        m = re.match(r'^([BW]+)\d*$', suffix, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return ""


def _upload_thumb_path(dx: str, filename: str) -> Path:
    """返回 03_UPLOAD 缩略图缓存文件路径（不检查是否存在、不生成）。"""
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return UPLOAD_THUMB_DIR / f"{dx}__{safe_name}.jpg"


def _get_upload_thumb(dx: str, filename: str):
    """返回 03_UPLOAD 缩略图路径（不存在或源文件已更新则重新生成 220px 高）。
    优先使用已缓存缩略图；透明 PNG 则合成白底。"""
    if "/" in filename or "\\" in filename or not re.match(r"^DX\d+$", dx):
        return None
    src = PROJECTS_DIR / dx / "03_UPLOAD" / filename
    if not src.exists():
        return None
    UPLOAD_THUMB_DIR.mkdir(parents=True, exist_ok=True)
    thumb_file = _upload_thumb_path(dx, filename)
    # 缓存有效：缩略图存在且严格比源文件新（mtime 相等时认为可能已更新，重新生成）
    if thumb_file.exists():
        try:
            if thumb_file.stat().st_mtime > src.stat().st_mtime:
                return thumb_file
        except Exception:
            pass
    try:
        from PIL import Image
        img = Image.open(src)
        # 仅当真正存在透明通道时才合成白底，否则直接转 RGB
        if img.mode == 'RGBA':
            # 检查是否有透明像素，若无则直接转 RGB
            alpha = img.getchannel('A')
            if alpha.getextrema()[0] == 255:
                img = img.convert('RGB')
            else:
                bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(bg, img).convert('RGB')
        elif img.mode == 'P':
            img = img.convert('RGBA')
            bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img).convert('RGB')
        else:
            img = img.convert('RGB')
        w, h = img.size
        target_h = 220
        new_w = max(1, int(w * target_h / h))
        img = img.resize((new_w, target_h), Image.LANCZOS)
        img.save(str(thumb_file), "JPEG", quality=85, optimize=True)
        return thumb_file
    except Exception as e:
        print(f"[UploadThumbError] {dx}/{filename}: {e}")
        return None


def _get_ai_thumb(dx: str, filename: str, source: str = "01_AI"):
    """返回 01_AI 或回收站中 AI 图的缩略图路径（不存在则生成 300px 高）。
    source: '01_AI' 或 'trash'"""
    if "/" in filename or "\\" in filename or not re.match(r"^DX\d+$", dx):
        return None
    if source == "trash":
        src = AI_TRASH_DIR / dx / filename
    else:
        src = PROJECTS_DIR / dx / "01_AI" / filename
    if not src.exists():
        return None
    AI_THUMB_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
    thumb_file = AI_THUMB_DIR / f"{dx}__{safe_name}.jpg"
    if thumb_file.exists() and thumb_file.stat().st_mtime > src.stat().st_mtime:
        return thumb_file
    try:
        from PIL import Image
        img = Image.open(src)
        if img.mode == 'RGBA':
            alpha = img.getchannel('A')
            if alpha.getextrema()[0] == 255:
                img = img.convert('RGB')
            else:
                bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(bg, img).convert('RGB')
        elif img.mode == 'P':
            img = img.convert('RGBA')
            bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img).convert('RGB')
        else:
            img = img.convert('RGB')
        w, h = img.size
        target_h = 300
        new_w = max(1, int(w * target_h / h))
        img = img.resize((new_w, target_h), Image.LANCZOS)
        img.save(str(thumb_file), "JPEG", quality=85, optimize=True)
        return thumb_file
    except Exception as e:
        print(f"[AIReviewThumbError] {dx}/{filename}: {e}")
        return None


def _get_ai_original(dx: str, filename: str):
    """返回 01_AI 中 AI 图的原图路径"""
    if "/" in filename or "\\" in filename or not re.match(r"^DX\d+$", dx):
        return None
    src = PROJECTS_DIR / dx / "01_AI" / filename
    if not src.exists():
        return None
    return src


# ---------------------------------------------------------------------------
# 修复错放文件：把去背/贴图文件移到正确的 DX 文件夹
# ---------------------------------------------------------------------------

def _find_target_dx(filename: str, current_dx: str) -> str:
    """从文件名中提取目标 DX 编号。如 DX0178_B_副本.png → 0178
    提取失败返回空字符串。
    """
    m = re.search(r'(DX\d+)', filename, re.IGNORECASE)
    if m:
        candidate = m.group(1).upper()
        if candidate != current_dx and (PROJECTS_DIR / candidate).exists():
            return candidate
    return ""


@app.route('/api/fix-mismatch', methods=['POST'])
def api_fix_mismatch():
    """修复指定 DX 中的错放文件：
    - 文件名含正确 DX 编号 → 直接移过去
    - 文件名不含 → 无法自动修复，跳过
    - 在目标文件夹写入修复记录
    """
    data = request.get_json(silent=True) or {}
    dx_id = data.get("dx_id", "")
    if not dx_id.startswith("DX") or not (PROJECTS_DIR / dx_id).exists():
        return jsonify({"ok": False, "error": "无效的 DX 编号"}), 400

    rem_dir = PROJECTS_DIR / dx_id / "02_REM_BG"
    report = {"moved": [], "skipped": [], "errors": []}
    log_entries = []  # 写入修复记录

    if not rem_dir.exists():
        return jsonify({"ok": True, "report": report, "msg": "没有 02_REM_BG 目录"})

    for f in list(rem_dir.iterdir()):
        if not f.is_file():
            continue
        if f.name.startswith(f"{dx_id}_"):
            continue
        target_dx = _find_target_dx(f.name, dx_id)
        if not target_dx:
            report["skipped"].append({"file": f.name, "reason": "无法识别目标 DX"})
            continue
        target_rem = PROJECTS_DIR / target_dx / "02_REM_BG"
        if not target_rem.exists():
            target_rem.mkdir(parents=True, exist_ok=True)
        dst = target_rem / f.name
        if dst.exists():
            stem, ext = os.path.splitext(f.name)
            dst = target_rem / f"{stem}_{int(time.time())}{ext}"
        try:
            shutil.move(str(f), str(dst))
            entry = {
                "file": dst.name,
                "from": f"{dx_id}/02_REM_BG",
                "to": f"{target_dx}/02_REM_BG",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            report["moved"].append(entry)
            log_entries.append(entry)
        except Exception as e:
            report["errors"].append({"file": f.name, "error": str(e)})

    # 写入修复记录到目标文件夹
    if log_entries:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        for entry in log_entries:
            target_dx = entry["to"].split("/")[0]
            log_path = PROJECTS_DIR / target_dx / "_fix_log.json"
            logs = []
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8') as lf:
                        logs = json.load(lf)
                except Exception:
                    logs = []
            logs.append(entry)
            with open(log_path, 'w', encoding='utf-8') as lf:
                json.dump(logs, lf, indent=2, ensure_ascii=False)

    msg_parts = []
    if report["moved"]:
        msg_parts.append(f"已移动 {len(report['moved'])} 个文件")
    if report["skipped"]:
        msg_parts.append(f"跳过 {len(report['skipped'])} 个")
    if report["errors"]:
        msg_parts.append(f"错误 {len(report['errors'])} 个")
    msg = ", ".join(msg_parts) if msg_parts else "无需修复"

    return jsonify({"ok": True, "report": report, "msg": msg})


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
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not f.startswith('_')]

    groups = {}
    pattern = re.compile(r'^(\d+)(B|W|BW|WB)\.(png|jpg|jpeg|webp)$', re.IGNORECASE)
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
        if not fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) or fname.startswith('_'):
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
        ext = safe_name.lower()
        if ext.endswith('.jpg') or ext.endswith('.jpeg'):
            ct = 'image/jpeg'
        elif ext.endswith('.webp'):
            ct = 'image/webp'
        else:
            ct = 'image/png'
        return send_file(str(filepath), mimetype=ct, max_age=3600)
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
    """返回当前任务状态（含派生字段，便于前端展示）"""
    data = dict(task_state)

    # 运行时长
    started = data.get("started_at")
    completed = data.get("completed_at")
    now = datetime.now()
    elapsed = 0
    if started:
        try:
            start_dt = datetime.fromisoformat(started)
            end_dt = datetime.fromisoformat(completed) if completed else now
            elapsed = max(0, (end_dt - start_dt).total_seconds())
        except Exception:
            pass
    data["elapsed_seconds"] = int(elapsed)

    # 从日志解析成功/失败数量
    success_count = 0
    fail_count = 0
    current_key = ""
    current_dx = ""
    output_folder = ""
    for line in data.get("log", []):
        m = re.search(r'生成\s*(\d+)\s*张[,，]\s*失败\s*(\d+)\s*张', line)
        if m:
            success_count = int(m.group(1))
            fail_count = int(m.group(2))
        m = re.search(r'Key#(\d+)', line)
        if m:
            current_key = f"Key#{m.group(1)}"
        # 当前 DX：从输出路径或任务进度里找
        m = re.search(r'输出到\s+(DX\d+)/01_AI', line)
        if m:
            current_dx = m.group(1)
        # Lovart 输出日志：name -> DXxxx/01_AI/name.png
        m = re.search(r'->\s*(DX\d+)/01_AI/', line)
        if m:
            current_dx = m.group(1)

    # 目标 DX：重新生图时 Bridge 已指定，优先使用，避免同名文件猜错
    # reuse_dx 可能是 str（单文件）或 dict（批量）。批量时跳过单 DX 输出文件夹逻辑。
    target_dx = data.get("reuse_dx") or data.get("target_dx") or ""
    if target_dx and isinstance(target_dx, str) and (PROJECTS_DIR / target_dx / "01_AI").exists():
        output_folder = target_dx
        if not current_dx:
            current_dx = target_dx

    # 兜底：根据 selected_files + source_map 找到最终输出 DX。
    # 批量重新生图时跳过此猜测，避免返回无关 DX。
    is_batch = data.get("batch") is True
    if data.get("status") in ("completed", "error") and not output_folder and not is_batch:
        for dx in sorted(os.listdir(PROJECTS_DIR)) if PROJECTS_DIR.exists() else []:
            if not dx.startswith("DX"):
                continue
            ai_dir = PROJECTS_DIR / dx / "01_AI"
            if not ai_dir.exists():
                continue
            for src in data.get("selected_files", []):
                if (ai_dir / src).exists():
                    output_folder = dx
                    break
            if output_folder:
                break

    # 批量任务：若未从日志解析到 current_dx，使用 affected_dx 中第一个
    if is_batch and not current_dx:
        affected = data.get("affected_dx", [])
        if affected:
            current_dx = affected[0]

    # 运行状态细化：completed 但有失败时，前端需要明确感知
    display_status = data.get("status", "idle")
    if display_status == "completed":
        if fail_count > 0 and success_count == 0:
            display_status = "error"
        elif fail_count > 0 and success_count > 0:
            display_status = "partial"

    data["success_count"] = success_count
    data["fail_count"] = fail_count
    data["current_key"] = current_key
    data["current_dx"] = current_dx or output_folder
    data["output_folder"] = output_folder
    data["display_status"] = display_status

    # 最新日志（最多 20 条）
    data["latest_log"] = data.get("log", [])[-20:]

    resp = jsonify(data)
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
            ai_src_map = {}  # AI 文件名 → 原图名
            if sm_path.exists():
                try:
                    with open(sm_path, 'r', encoding='utf-8') as f:
                        source_map = json.load(f)
                    # 从 Lovart 注册表查找原图名
                    lovart_reg_path = Path("D:/Semems WB/WB_REGISTRY/registry.json")
                    if lovart_reg_path.exists():
                        with open(lovart_reg_path, 'r', encoding='utf-8') as lf:
                            lovart_reg = json.load(lf)
                        for src in source_map.get("sources", []):
                            ai_file = src.get("file", "")
                            src_id = src.get("src_id", "")
                            if ai_file and src_id and src_id in lovart_reg:
                                orig = lovart_reg[src_id].get("original_name", "")
                                if orig:
                                    ai_src_map[ai_file] = orig
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
                "ai_src_map": ai_src_map,  # AI文件名 → 原图名
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
        os.startfile(str(target))
        return jsonify({"ok": True, "path": str(target)})
    except Exception:
        return jsonify({"error": "打开失败"}), 500


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
    """打开本地回收站目录（前台显示）"""
    try:
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        _open_folder_front(TRASH_DIR)
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


# ============================================================================
# AI 生图对比页面 API
# ============================================================================

@app.route('/ai-review')
def ai_review_page():
    """AI 生图对比页面"""
    html_file = Path(__file__).parent / "ai_review.html"
    if html_file.exists():
        return send_file(str(html_file))
    return "<h1>ai_review.html not found</h1><p>请确保 ai_review.html 与 bridge.py 在同一目录</p>", 404


@app.route('/api/ai-review/projects')
def api_ai_review_projects():
    """返回所有 DX 的 INBOX 原图与 01_AI 生成图配对列表"""
    try:
        projects = _scan_ai_review_projects()
        dates = sorted({p["date"] for p in projects if p["date"]}, reverse=True)
        return jsonify({"ok": True, "projects": projects, "dates": dates, "total": len(projects)})
    except Exception as e:
        import traceback
        print(f"[AIReview] /api/ai-review/projects 错误: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/ai-review/thumb')
def api_ai_review_thumb():
    """返回 01_AI 中 AI 图的缩略图"""
    dx = request.args.get("dx", "").strip()
    filename = request.args.get("file", "").strip()
    if not re.match(r"^DX\d+$", dx) or not filename:
        return "bad params", 400
    thumb = _get_ai_thumb(dx, filename, source="01_AI")
    if not thumb:
        return "no thumb", 404
    r = make_response(send_file(str(thumb), mimetype="image/jpeg"))
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


@app.route('/api/ai-review/original')
def api_ai_review_original():
    """返回 01_AI 中 AI 图的原图（供悬停放大）"""
    dx = request.args.get("dx", "").strip()
    filename = request.args.get("file", "").strip()
    if not re.match(r"^DX\d+$", dx) or not filename:
        return "bad params", 400
    src = _get_ai_original(dx, filename)
    if not src:
        return "not found", 404
    ct = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    r = make_response(send_file(str(src), mimetype=ct))
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


@app.route('/api/ai-review/trash-thumb')
def api_ai_review_trash_thumb():
    """返回回收站中 AI 图的缩略图"""
    dx = request.args.get("dx", "").strip()
    filename = request.args.get("file", "").strip()
    if not re.match(r"^DX\d+$", dx) or not filename:
        return "bad params", 400
    thumb = _get_ai_thumb(dx, filename, source="trash")
    if not thumb:
        return "no thumb", 404
    r = make_response(send_file(str(thumb), mimetype="image/jpeg"))
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


def _stage_source_for_regen(source_path: Path) -> tuple:
    """把 DX/01_AI 中的原图临时复制到 INBOX，处理同名冲突。

    返回: (inbox_path, inbox_conflict_path, error_message)
    - inbox_path: INBOX 中的目标路径
    - inbox_conflict_path: 被移走的冲突文件路径（无冲突时为 None）
    - error_message: 失败时的错误信息（成功时为 None）
    """
    source_file = source_path.name
    inbox_path = INBOX_DIR / source_file
    inbox_conflict_path = None
    try:
        source_md5 = compute_md5(str(source_path))
        if inbox_path.exists():
            inbox_md5 = compute_md5(str(inbox_path))
            if inbox_md5 and inbox_md5 != source_md5:
                conflict_dir = AI_TRASH_DIR / "_inbox_conflicts"
                conflict_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                conflict_name = f"{Path(source_file).stem}_{ts}{Path(source_file).suffix}"
                inbox_conflict_path = conflict_dir / conflict_name
                shutil.move(str(inbox_path), str(inbox_conflict_path))
                log(f"INBOX 同名冲突已移走: {source_file} -> {inbox_conflict_path.name}")
        shutil.copy2(str(source_path), str(inbox_path))
        return inbox_path, inbox_conflict_path, None
    except Exception as e:
        return inbox_path, inbox_conflict_path, f"复制原图到 INBOX 失败: {e}"


def _restore_inbox_after_regen(inbox_path: Path, inbox_conflict_path: Path = None):
    """重新生图结束后清理临时原图，冲突文件保留在暂存区。"""
    source_file = inbox_path.name
    try:
        if inbox_path.exists():
            try:
                inbox_path.unlink()
                log(f"INBOX 临时原图已清理: {source_file}")
            except Exception as e:
                log(f"WARN: 清理 INBOX 临时原图失败: {e}")
        if inbox_conflict_path and inbox_conflict_path.exists():
            log(f"INBOX 冲突文件保留在回收站: {inbox_conflict_path.name}")
    except Exception as e:
        log(f"WARN: 恢复/清理 INBOX 失败 {source_file}: {e}")


def _cleanup_duplicate_sources(dx: str, source_file: str):
    """删除 Lovart 归档源图时产生的重复副本（如 17bw(2).png）。"""
    try:
        ai_dir = PROJECTS_DIR / dx / "01_AI"
        original = ai_dir / source_file
        if not original.exists():
            return
        orig_md5 = compute_md5(str(original))
        stem = Path(source_file).stem
        for f in ai_dir.iterdir():
            if not f.is_file():
                continue
            if re.match(rf'^{re.escape(stem)}\(\d+\)\.png$', f.name, re.IGNORECASE):
                try:
                    if compute_md5(str(f)) == orig_md5:
                        f.unlink()
                        log(f"删除重复源图副本: {f.name}")
                except Exception:
                    pass
    except Exception as e:
        log(f"WARN: 清理重复源图副本失败: {e}")


@app.route('/api/ai-review/regenerate', methods=['POST'])
def api_ai_review_regenerate():
    """对指定 01_AI 中的原图重新生图（会重新生成其所在整组）。"""
    global task_state
    data = request.get_json(silent=True) or {}
    dx = data.get("dx", "").strip()
    source_file = data.get("source_file", "").strip()

    if not dx or not source_file:
        return jsonify({"ok": False, "error": "缺少 dx 或 source_file"}), 400
    if not re.match(r"^DX\d+$", dx):
        return jsonify({"ok": False, "error": "无效的 DX 编号"}), 400

    source_path = PROJECTS_DIR / dx / "01_AI" / source_file
    if not source_path.exists():
        return jsonify({"ok": False, "error": f"{dx}/01_AI 中不存在 {source_file}"}), 404

    with _lock:
        if task_state["status"] == "running":
            return jsonify({"ok": False, "error": "已有生图任务正在运行，请等待完成"}), 409

    inbox_path, inbox_conflict_path, err = _stage_source_for_regen(source_path)
    if err:
        return jsonify({"ok": False, "error": err}), 500

    # 找到该文件所在 group
    inbox_groups = group_inbox_files()
    target_group = None
    for g in inbox_groups:
        if any(img["filename"] == source_file for img in g["images"]):
            target_group = g
            break
    if not target_group:
        # 复制错了，清理掉；如有冲突文件则移回
        try:
            if inbox_path.exists():
                inbox_path.unlink()
            if inbox_conflict_path and inbox_conflict_path.exists():
                shutil.move(str(inbox_conflict_path), str(inbox_path))
        except Exception:
            pass
        return jsonify({"ok": False, "error": f"无法确定 {source_file} 的分组"}), 400

    # 清除 Lovart 处理记录里该原图的 hash，强制重新生成
    try:
        removed = _remove_from_lovart_track(inbox_path)
        if removed:
            log(f"已清除 {removed} 条 Lovart 处理记录，强制重新生图: {source_file}")
    except Exception as e:
        log(f"WARN: 清除 Lovart 处理记录失败: {e}")

    # 启动后台生图任务
    task_id = f"TASK_REGEN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with _lock:
        task_state = {
            "status": "starting",
            "display_status": "starting",
            "progress": "初始化重新生图...",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "log": [],
            "selected_files": [source_file],
            "groups_processed": 0,
            "groups_total": 1,
            "task_id": task_id,
            "reuse_dx": dx,
        }
        _save_state()

    def _regen_wrapper():
        try:
            _run_generation([source_file], task_id, reuse_dx=dx)
        except Exception as e:
            log(f"重新生图任务异常: {e}")
        finally:
            _restore_inbox_after_regen(inbox_path, inbox_conflict_path)
            _cleanup_duplicate_sources(dx, source_file)

    t = threading.Thread(target=_regen_wrapper, daemon=True)
    t.start()

    return jsonify({
        "ok": True,
        "task_id": task_id,
        "msg": f"已启动重新生图：{dx}/{source_file}（整组 {len(target_group['images'])} 张）",
    })


@app.route('/api/ai-review/regenerate-batch', methods=['POST'])
def api_ai_review_regenerate_batch():
    """批量重新生图：支持勾选多个 01_AI 原图，利用 Lovart 并发生成。

    请求体：{items: [{dx, source_file}]}
    限制：同一批次内所有 source_file 必须全局唯一（不允许跨 DX 同名），
          因为 LOVART_REGEN_DX_MAP 以文件名为 key。
    """
    global task_state
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])

    if not items or not isinstance(items, list):
        return jsonify({"ok": False, "error": "缺少 items"}), 400

    # 校验每个条目
    seen_files = set()
    dup_files = set()
    validated = []
    for item in items:
        dx = str(item.get("dx", "")).strip()
        source_file = str(item.get("source_file", "")).strip()
        if not dx or not source_file:
            continue
        if not re.match(r"^DX\d+$", dx):
            return jsonify({"ok": False, "error": f"无效的 DX 编号: {dx}"}), 400
        source_path = PROJECTS_DIR / dx / "01_AI" / source_file
        if not source_path.exists():
            return jsonify({"ok": False, "error": f"{dx}/01_AI 中不存在 {source_file}"}), 404
        if source_file in seen_files:
            dup_files.add(source_file)
        seen_files.add(source_file)
        validated.append({"dx": dx, "source_file": source_file, "source_path": source_path})

    if not validated:
        return jsonify({"ok": False, "error": "没有有效的重新生图项"}), 400
    if dup_files:
        return jsonify({
            "ok": False,
            "error": f"同一批次内不允许同名文件（跨 DX）：{', '.join(sorted(dup_files))}"
        }), 409

    with _lock:
        if task_state["status"] == "running":
            return jsonify({"ok": False, "error": "已有生图任务正在运行，请等待完成"}), 409

    # 准备 INBOX：复制所有源文件，处理同名冲突
    staged = []  # [{dx, source_file, inbox_path, conflict_path}]
    try:
        for v in validated:
            inbox_path, inbox_conflict_path, err = _stage_source_for_regen(v["source_path"])
            if err:
                # 回滚已复制的文件
                for s in staged:
                    _restore_inbox_after_regen(s["inbox_path"], s["conflict_path"])
                return jsonify({"ok": False, "error": err}), 500
            staged.append({
                "dx": v["dx"],
                "source_file": v["source_file"],
                "inbox_path": inbox_path,
                "conflict_path": inbox_conflict_path,
            })
    except Exception as e:
        for s in staged:
            _restore_inbox_after_regen(s["inbox_path"], s["conflict_path"])
        return jsonify({"ok": False, "error": f"准备 INBOX 失败: {e}"}), 500

    # 校验 INBOX 分组（至少每个文件都能被识别到）
    inbox_groups = group_inbox_files()
    inbox_files_set = {s["source_file"] for s in staged}
    matched_files = set()
    for g in inbox_groups:
        for img in g["images"]:
            if img["filename"] in inbox_files_set:
                matched_files.add(img["filename"])
    if len(matched_files) != len(inbox_files_set):
        missing = inbox_files_set - matched_files
        for s in staged:
            _restore_inbox_after_regen(s["inbox_path"], s["conflict_path"])
        return jsonify({"ok": False, "error": f"以下文件无法确定分组: {', '.join(sorted(missing))}"}), 400

    # 清除 Lovart 处理记录
    for s in staged:
        try:
            removed = _remove_from_lovart_track(s["inbox_path"])
            if removed:
                log(f"已清除 {removed} 条 Lovart 处理记录，强制重新生图: {s['source_file']}")
        except Exception as e:
            log(f"WARN: 清除 Lovart 处理记录失败 {s['source_file']}: {e}")

    # 启动后台生图任务
    selected_files = [s["source_file"] for s in staged]
    regen_map = {s["source_file"]: s["dx"] for s in staged}
    affected_dx = sorted({s["dx"] for s in staged})
    task_id = f"TASK_REGEN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with _lock:
        task_state = {
            "status": "starting",
            "display_status": "starting",
            "progress": f"初始化批量重新生图 {len(selected_files)} 张...",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "log": [],
            "selected_files": selected_files,
            "groups_processed": 0,
            "groups_total": len(selected_files),
            "task_id": task_id,
            "reuse_dx": regen_map,
            "batch": True,
            "affected_dx": affected_dx,
        }
        _save_state()

    def _batch_regen_wrapper():
        try:
            _run_generation(selected_files, task_id, reuse_dx=regen_map)
        except Exception as e:
            log(f"批量重新生图任务异常: {e}")
        finally:
            for s in staged:
                _restore_inbox_after_regen(s["inbox_path"], s["conflict_path"])
                _cleanup_duplicate_sources(s["dx"], s["source_file"])

    t = threading.Thread(target=_batch_regen_wrapper, daemon=True)
    t.start()

    return jsonify({
        "ok": True,
        "task_id": task_id,
        "msg": f"已启动批量重新生图：{len(selected_files)} 张，涉及 {len(affected_dx)} 个 DX（{', '.join(affected_dx)}）",
    })


@app.route('/api/ai-review/delete-ai', methods=['POST'])
def api_ai_review_delete_ai():
    """将 AI 图移入回收站"""
    data = request.get_json(silent=True) or {}
    dx = data.get("dx", "").strip()
    filename = data.get("file", "").strip()
    if not dx or not filename:
        return jsonify({"ok": False, "error": "缺少 dx 或 file"}), 400
    ok, msg = move_ai_to_trash(dx, filename)
    if ok:
        return jsonify({"ok": True, "msg": msg})
    return jsonify({"ok": False, "error": msg}), 500


@app.route('/api/ai-review/restore-ai', methods=['POST'])
def api_ai_review_restore_ai():
    """从回收站还原 AI 图"""
    data = request.get_json(silent=True) or {}
    dx = data.get("dx", "").strip()
    filename = data.get("file", "").strip()
    if not dx or not filename:
        return jsonify({"ok": False, "error": "缺少 dx 或 file"}), 400
    ok, msg = restore_ai_from_trash(dx, filename)
    if ok:
        return jsonify({"ok": True, "msg": msg})
    return jsonify({"ok": False, "error": msg}), 500


@app.route('/api/ai-review/trash')
def api_ai_review_trash():
    """返回 AI 图回收站列表"""
    try:
        items = list_ai_trash()
        return jsonify({"ok": True, "items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/ai-review/empty-trash', methods=['POST'])
def api_ai_review_empty_trash():
    """永久清空 AI 图回收站"""
    if not AI_TRASH_DIR.exists():
        return jsonify({"ok": True, "count": 0, "msg": "回收站为空"})
    count = 0
    errors = []
    for dx_dir in list(AI_TRASH_DIR.iterdir()):
        if not dx_dir.is_dir():
            continue
        for f in list(dx_dir.iterdir()):
            if not f.is_file():
                continue
            try:
                f.unlink()
                count += 1
            except Exception as e:
                errors.append(f"{dx_dir.name}/{f.name}: {e}")
        # 尝试删除空目录
        try:
            dx_dir.rmdir()
        except Exception:
            pass
    # 尝试删除根目录
    try:
        AI_TRASH_DIR.rmdir()
    except Exception:
        pass
    msg = f"已清空 {count} 个文件"
    if errors:
        msg += f"，{len(errors)} 个失败"
    return jsonify({"ok": True, "count": count, "errors": errors, "msg": msg})


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


@app.route('/api/provenance')
def api_provenance():
    """查询单张图片的血缘链（溯源）"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "请提供 ?q=filename_or_md5"}), 400

    reg = load_registry()
    reg = ensure_registry_v4(reg)

    # 按 MD5、文件名或 UID 查找
    target_md5 = q
    if q in reg.get("uid_index", {}):
        target_md5 = reg["uid_index"][q]
    elif q in reg.get("name_index", {}):
        target_md5 = reg["name_index"].get(q, q)
    elif q not in reg.get("images", {}):
        # 尝试通过 inbox_original_name 匹配
        for md5, entry in reg.get("images", {}).items():
            if entry.get("inbox_original_name") == q or entry.get("original_name") == q:
                target_md5 = md5
                break

    target = reg["images"].get(target_md5)
    if not target:
        return jsonify({"query": q, "error": "未找到"}), 404

    # 构建血缘链：从 root 到当前
    chain = []
    md5 = target_md5
    while md5 and md5 in reg.get("images", {}):
        entry = reg["images"][md5]
        chain.append({
            "md5": md5,
            "name": entry.get("current_name", ""),
            "path": entry.get("current_path", ""),
            "type": entry.get("source_type", "inbox" if not entry.get("source_md5") else entry["source_type"]),
            "uid": entry.get("uid", ""),
            "role": entry.get("role", ""),
            "root_name": entry.get("root_name", ""),
        })
        md5 = entry.get("source_md5", "")
        if not md5:
            break

    # 衍生图片
    derived = []
    for d_md5 in target.get("derived_md5s", []):
        if d_md5 in reg.get("images", {}):
            dentry = reg["images"][d_md5]
            derived.append({
                "md5": d_md5,
                "name": dentry.get("current_name", ""),
                "path": dentry.get("current_path", ""),
                "type": dentry.get("source_type", ""),
                "uid": dentry.get("uid", ""),
            })

    return jsonify({
        "query": q,
        "target": {
            "md5": target_md5,
            "name": target.get("current_name", ""),
            "path": target.get("current_path", ""),
            "uid": target.get("uid", ""),
            "role": target.get("role", ""),
            "inbox_original": target.get("inbox_original_name", ""),
            "source_type": target.get("source_type", ""),
            "source_md5": target.get("source_md5", ""),
            "root_name": target.get("root_name", ""),
            "root_md5": target.get("root_md5", ""),
        },
        "chain": chain,
        "derived": derived,
    })


@app.route('/api/scan-provenance', methods=['POST'])
def api_scan_provenance():
    """扫描所有 DX 文件夹，建立/更新溯源关系"""
    try:
        count = scan_provenance()
        return jsonify({"ok": True, "count": count, "msg": f"已建立 {count} 条溯源关系"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 统一血缘注册入口（供 check_rem / 贴图等外部工具 Hook 调用） ──

@app.route('/api/lineage/register', methods=['POST'])
def api_lineage_register():
    """外部工具调用此接口记录血缘关系。
    
    Payload:
      child_path: str  - 输出文件的全路径
      parent_path: str - 输入文件的全路径  
      stage: str       - rembg | upload | ai_gen
    """
    data = request.get_json(silent=True) or {}
    child_path = data.get("child_path", "")
    parent_path = data.get("parent_path", "")
    stage = data.get("stage", "")
    uid = data.get("uid", "")
    group_id = data.get("group_id", "")
    role = data.get("role", "")

    if not child_path or not parent_path or not stage:
        return jsonify({"ok": False, "error": "需要 child_path, parent_path, stage"}), 400
    if stage not in ("rembg", "upload", "ai_gen"):
        return jsonify({"ok": False, "error": f"不支持的 stage: {stage}"}), 400

    child_path = Path(child_path)
    parent_path = Path(parent_path)
    if not child_path.exists():
        return jsonify({"ok": False, "error": f"child_path 不存在: {child_path}"}), 400
    if not parent_path.exists():
        return jsonify({"ok": False, "error": f"parent_path 不存在: {parent_path}"}), 400

    try:
        child_md5 = compute_md5(str(child_path))
        parent_md5 = compute_md5(str(parent_path))

        reg = load_registry()
        reg = ensure_registry_v4(reg)

        # 如果 registry 中没有这两个文件，先注册
        for md5_val, fpath in [(child_md5, child_path), (parent_md5, parent_path)]:
            if md5_val not in reg.get("images", {}):
                fname = fpath.name
                # 用相对路径
                try:
                    rel = fpath.relative_to(BASE_DIR)
                    rel_str = str(rel).replace('\\', '/')
                except ValueError:
                    rel_str = str(fpath)
                reg["images"][md5_val] = {
                    "md5": md5_val,
                    "current_name": fname,
                    "current_path": rel_str,
                    "events": [{
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "event": "lineage_register",
                        "detail": f"来自 Hook: {stage}",
                    }],
                }
                _add_provenance_fields(reg["images"][md5_val])

        _register_provenance(reg, child_md5, parent_md5, stage, lineage_status="confirmed")
        save_registry(reg)

        # 同步更新 uid_map / sidecar（如果提供了 UID 或能从 sidecar 读取到）
        if wb_meta:
            try:
                parent_meta = wb_meta.read_meta(parent_path)
                effective_uid = uid or (parent_meta.get("uid") if parent_meta else "")
                effective_gid = group_id or (parent_meta.get("group_id") if parent_meta else "")
                effective_role = role or (parent_meta.get("role") if parent_meta else "")
                if effective_uid and effective_gid:
                    dx_dir = child_path.parent.parent
                    if dx_dir.name.startswith("DX"):
                        stage_key = stage  # rembg/upload/ai_gen
                        if stage == "upload":
                            stage_key = "sticker"
                        wb_meta.register_image_in_map(
                            dx_dir, effective_uid, effective_gid, stage_key,
                            effective_role, str(child_path),
                            parent_uid=effective_uid,
                            source_file=str(parent_path),
                        )
                        wb_meta.ensure_meta(
                            child_path, uid=effective_uid, group_id=effective_gid,
                            stage=stage_key, role=effective_role,
                            parent_uid=effective_uid, source_file=str(parent_path),
                        )
            except Exception as e:
                # 不阻断原有血缘注册
                print(f"[lineage/register] uid_map 同步失败: {e}")

        return jsonify({
            "ok": True,
            "msg": f"已记录 {stage} 血缘: {child_path.name} ← {parent_path.name}",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/launch-check-rem', methods=['POST'])
def api_launch_check_rem():
    """确保去背预览服务（端口 8766）已就绪，并返回状态。

    实际页面打开由前端直接执行 window.open，这里只负责兜底拉起 check_rem.py。
    check_rem.py 通常由 Bridge 启动时的守护线程保持常驻。
    """
    # 兜底：若守护线程还没把 check_rem 拉起来，等最多 2 秒
    if not _port_ready("127.0.0.1", 8766, timeout=2):
        return jsonify({"ok": False, "error": "去背预览服务未就绪，请稍后再试"}), 503
    return jsonify({"ok": True, "msg": "去背预览服务已就绪"})


@app.route('/upload')
def upload_page():
    """上款页面：展示 03_UPLOAD 成品并批量上传"""
    html_file = Path(__file__).parent / "upload.html"
    if html_file.exists():
        return send_file(str(html_file))
    return "<h1>upload.html not found</h1>", 404


@app.route('/api/upload/projects')
def api_upload_projects():
    """返回所有含 03_UPLOAD 成品的 DX 列表，并标记是否在线已上款"""
    projects = _scan_upload_projects()
    online_set = _read_online_listed()
    for p in projects:
        p["online_listed"] = p.get("dx", "") in online_set
    return jsonify({"ok": True, "projects": projects, "online_updated_at": _online_listed_updated_at(), "online_mode": _online_listed_mode()})


@app.route('/api/upload/thumb')
def api_upload_thumb():
    """返回 03_UPLOAD 缩略图"""
    dx = request.args.get("dx", "")
    filename = request.args.get("file", "")
    if not re.match(r"^DX\d+$", dx) or not filename:
        return "bad params", 400
    thumb = _get_upload_thumb(dx, filename)
    if not thumb:
        return "no thumb", 404
    r = make_response(send_file(str(thumb), mimetype="image/jpeg"))
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


@app.route('/api/upload/original')
def api_upload_original():
    """返回 03_UPLOAD 原图（供悬停放大）"""
    dx = request.args.get("dx", "")
    filename = request.args.get("file", "")
    if not re.match(r"^DX\d+$", dx) or not filename:
        return "bad params", 400
    src = PROJECTS_DIR / dx / "03_UPLOAD" / filename
    if not src.exists():
        return "not found", 404
    ct = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    r = make_response(send_file(str(src), mimetype=ct))
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


@app.route('/api/upload/delete', methods=['POST'])
def api_upload_delete():
    """将 03_UPLOAD 中的成品图删除到系统回收站"""
    data = request.get_json(force=True, silent=True) or {}
    dx = (data.get("dx") or request.args.get("dx", "")).strip()
    filename = (data.get("file") or request.args.get("file", "")).strip()
    if not re.match(r"^DX\d+$", dx) or not filename or "/" in filename or "\\" in filename:
        return jsonify({"ok": False, "error": "参数非法"}), 400
    target = PROJECTS_DIR / dx / "03_UPLOAD" / filename
    if not target.exists():
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    ok = send_to_recycle_bin(str(target))
    if ok:
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
        for tf in UPLOAD_THUMB_DIR.glob(f"{dx}__{safe_name}.*"):
            try:
                tf.unlink()
            except Exception:
                pass
    return jsonify({"ok": ok, "msg": f"已送回收站: {filename}" if ok else "删除失败"})


def _read_completed_md():
    """读取 已上款货号_wb.md 中的所有 DX 货号（已弃用，仅兼容旧逻辑）"""
    md = BASE_DIR / "已上款货号_wb.md"
    if not md.exists():
        return set()
    try:
        with open(md, "r", encoding="utf-8") as f:
            return set(
                line.strip().lstrip("- *").strip()
                for line in f
                if line.strip().startswith("DX")
                or line.strip().startswith("- DX")
                or line.strip().startswith("* DX")
            )
    except Exception:
        return set()


def _read_online_listed():
    """读取店小秘在线产品页抓取的已上款 DX 集合（唯一权威来源）"""
    if not ONLINE_LISTED_FILE.exists():
        return set()
    try:
        data = json.loads(ONLINE_LISTED_FILE.read_text(encoding="utf-8"))
        dx_set = data.get("dx_set", []) or []
        return set(str(dx).upper() for dx in dx_set if str(dx).upper().startswith("DX"))
    except Exception:
        return set()


def _online_listed_updated_at():
    """返回在线已上款数据最后更新时间"""
    if not ONLINE_LISTED_FILE.exists():
        return None
    try:
        data = json.loads(ONLINE_LISTED_FILE.read_text(encoding="utf-8"))
        return data.get("updated_at")
    except Exception:
        return None


def _online_listed_mode():
    """返回在线已上款数据上次刷新的模式（quick/deep），供前端显示"""
    if not ONLINE_LISTED_FILE.exists():
        return None
    try:
        data = json.loads(ONLINE_LISTED_FILE.read_text(encoding="utf-8"))
        return data.get("mode")
    except Exception:
        return None


def _remove_from_completed_md(dx_list):
    """强制重新上款时，从 已上款货号_wb.md 中删除指定 DX 货号行。
    返回实际删除了哪些款号。"""
    md = BASE_DIR / "已上款货号_wb.md"
    if not md.exists():
        return []
    targets = set(dx_list)
    removed = []
    try:
        with open(md, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            # 匹配 '- DXxxxx' 或 '* DXxxxx'
            if stripped.startswith("- DX") or stripped.startswith("* DX"):
                dx = stripped.lstrip("- *").strip()
                if dx in targets:
                    removed.append(dx)
                    continue
            new_lines.append(line)
        if removed:
            with open(md, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception as e:
        print(f"[batch-upload] 删除已上款记录失败: {e}", flush=True)
    return removed


@app.route('/api/upload/progress')
def api_upload_progress():
    """返回 wb_listing.py 写入的上款进度 JSON，并合并历史已完成记录"""
    data = {
        "ok": True,
        "running": False,
        "started_at": None,
        "finished_at": None,
        "selected": [],
        "pending": [],
        "completed": [],
        "failed": [],
        "current": None,
        "current_start": None,
        "total_count": 0,
        "done_count": 0,
        "fail_count": 0,
        "per_dx": {},
    }
    if UPLOAD_PROGRESS_FILE.exists():
        try:
            with open(UPLOAD_PROGRESS_FILE, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # 只统计当前选中款范围内的完成/失败，避免历史记录把 done_count 撑爆 total_count
    selected_set = set(data.get("selected", []))
    failed_set = set(data.get("failed", [])) & selected_set
    online_set = _read_online_listed()
    # 店小秘在线产品页为唯一权威来源；同时保留当前运行中的 completed（wb_listing.py 实时写入）
    completed_set = (set(data.get("completed", [])) | online_set) & selected_set

    data["completed"] = sorted(completed_set)
    data["failed"] = sorted(failed_set)
    data["pending"] = sorted(selected_set - completed_set - failed_set)
    data["done_count"] = len(completed_set)
    data["fail_count"] = len(failed_set)
    data["total_count"] = len(selected_set)

    # 在线已上款信息（权威来源）
    data["online_set"] = sorted(online_set & selected_set)
    data["online_count"] = len(online_set & selected_set)
    data["online_updated_at"] = _online_listed_updated_at()

    return jsonify(data)


@app.route('/api/upload/refresh-online-listed', methods=['POST'])
def api_upload_refresh_online_listed():
    """启动 check_online_listed.py，从店小秘在线产品页刷新真正已上款的 DX 集合

    mode=incremental（默认）：日常增量，翻到上次边界款为止，集合相减自动移除下架款；首次运行全量建库
    mode=deep：深度清理，翻完所有页，全量覆盖（准确移除所有已下架款，并重置边界）
    """
    mode = (request.args.get("mode") or "incremental").lower()
    if mode not in ("incremental", "deep"):
        mode = "incremental"

    lock_file = BASE_DIR / ".check_online_listed.lock"
    if lock_file.exists():
        return jsonify({
            "ok": False,
            "error": "已有刷新任务在运行，请等待完成"
        }), 429

    default_script = r"E:\Claude code\wb上款\check_online_listed.py"
    script_path = Path(default_script)
    if not script_path.exists():
        return jsonify({
            "ok": False,
            "error": f"刷新脚本不存在: {default_script}"
        }), 404

    try:
        proc = run_minimized([sys.executable, str(script_path), "--mode", mode], wait=False, no_console=True)
        mode_label = "深度清理" if mode == "deep" else "增量刷新"
        return jsonify({
            "ok": True,
            "msg": f"已开始刷新在线已上款（{mode_label}），完成后页面自动刷新",
            "pid": proc.pid,
            "mode": mode,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"启动刷新脚本失败: {e}"
        }), 500


def _open_folder_front(folder_path: Path):
    """打开文件夹并尝试强制资源管理器窗口前台显示。"""
    folder = str(folder_path)
    # 允许当前进程创建/激活前台窗口
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass

    # 使用 explorer.exe 打开，避免 os.startfile 复用已最小化窗口时不激活
    try:
        subprocess.Popen(['explorer.exe', folder])
    except Exception:
        try:
            os.startfile(folder)
        except Exception:
            subprocess.Popen(f'explorer.exe "{folder}"', shell=True)

    # 尝试找到新打开的资源管理器窗口并置顶
    try:
        import win32gui
        import win32con
        import time

        folder_name = folder_path.name
        best_hwnd = None

        def _enum(hwnd, _):
            nonlocal best_hwnd
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            # 资源管理器窗口标题通常包含文件夹名；也可用类名 CabinetWClass
            if folder_name in title and 'CabinetWClass' in win32gui.GetClassName(hwnd):
                best_hwnd = hwnd
                return False
            return True

        # 轮询最多 1 秒，等待窗口创建
        for _ in range(10):
            time.sleep(0.1)
            win32gui.EnumWindows(_enum, None)
            if best_hwnd:
                break

        if best_hwnd:
            win32gui.ShowWindow(best_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(best_hwnd)
    except Exception:
        pass


@app.route('/api/open')
def api_open_dx():
    """打开指定 DX 的子文件夹（ai/rem/up）"""
    dx = request.args.get("dx", "")
    which = request.args.get("which", "")
    if not re.match(r"^DX\d+$", dx) or which not in ("ai", "rem", "up"):
        return jsonify({"ok": False, "error": "参数非法"}), 400
    sub = {"ai": "01_AI", "rem": "02_REM_BG", "up": "03_UPLOAD"}[which]
    folder = PROJECTS_DIR / dx / sub
    if folder.exists():
        _open_folder_front(folder)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "文件夹不存在"}), 404


@app.route('/api/open-file')
def api_open_file():
    """打开指定 DX 子目录中的文件所在文件夹，并选中该文件。

    参数：
      dx: DX 编号
      file: 文件名
      sub: 子目录（默认 01_AI，可选 02_REM_BG / 03_UPLOAD / INBOX）
    """
    dx = request.args.get("dx", "").strip()
    filename = request.args.get("file", "").strip()
    sub = request.args.get("sub", "01_AI").strip()

    if not dx or not filename:
        return jsonify({"ok": False, "error": "缺少 dx 或 file"}), 400
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"ok": False, "error": "非法文件名"}), 400

    if sub == "INBOX":
        folder = INBOX_DIR
    elif sub in ("01_AI", "02_REM_BG", "03_UPLOAD") and re.match(r"^DX\d+$", dx):
        folder = PROJECTS_DIR / dx / sub
    else:
        return jsonify({"ok": False, "error": "非法 sub 参数"}), 400

    target = folder / filename
    if not target.exists():
        return jsonify({"ok": False, "error": f"文件不存在: {target}"}), 404

    try:
        # /select 参数会打开文件夹并高亮选中指定文件，保证前台显示
        subprocess.Popen(
            ['explorer.exe', '/select,', str(target)],
            shell=False,
        )
        return jsonify({"ok": True, "path": str(target)})
    except Exception as e:
        # 回退：仅打开文件夹
        try:
            os.startfile(str(folder))
            return jsonify({"ok": True, "path": str(folder), "fallback": True})
        except Exception:
            return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/batch-upload', methods=['POST'])
def api_batch_upload():
    """批量上款：调用 E:\Claude code\wb上款\wb_listing.py 逐个 DX 上款。
    可通过环境变量 LOVART_UPLOAD_SCRIPT 覆盖脚本路径。
    """
    data = request.get_json(silent=True) or {}
    dx_list = data.get("dx_list", [])
    force = data.get("force", False)
    if not dx_list:
        return jsonify({"ok": False, "error": "请指定DX号"}), 400

    default_script = r"E:\Claude code\wb上款\wb_listing.py"
    upload_script = os.environ.get("LOVART_UPLOAD_SCRIPT", default_script)
    script_path = Path(upload_script)
    if not script_path.exists():
        return jsonify({
            "ok": False,
            "error": f"上款脚本不存在: {upload_script}"
        }), 404

    # 强制重新上款：先从已上款记录中删除对应款号，让 wb_listing.py 正常执行
    removed = []
    if force:
        removed = _remove_from_completed_md(dx_list)

    # wb_listing.py --only 模式：只处理勾选的确切款号，不会继续后续款
    valid_dx = []
    for dx in dx_list:
        dx_folder = PROJECTS_DIR / dx
        if dx_folder.exists() and (dx_folder / "03_UPLOAD").exists():
            valid_dx.append(dx)

    if not valid_dx:
        return jsonify({"ok": False, "error": "勾选的款均无 03_UPLOAD 成品"}), 400

    args = [sys.executable, str(script_path)]
    for dx in valid_dx:
        args.extend(["--only", dx])

    try:
        # wait=False: wb_listing.py 运行时间较长，API 立即返回，后台执行
        # no_console=True: 不弹控制台黑窗（wb_listing.py 自己写日志到 D:\Semems WB\_debug）
        run_minimized(args, wait=False, no_console=True)
    except Exception as e:
        print(f"[batch-upload] 启动 {valid_dx} 失败: {e}", flush=True)
        return jsonify({"ok": False, "error": f"启动脚本失败: {e}"}), 500

    msg = f"已启动 wb上款脚本，精确处理 {len(valid_dx)} 个款：{', '.join(valid_dx)}"
    if force:
        msg = f"【强制重新上款】已删除已上款记录中的 {len(removed)} 个款，并启动处理：{', '.join(valid_dx)}"
    return jsonify({
        "ok": True,
        "msg": msg,
        "script": str(script_path),
        "selected": valid_dx,
        "force": force,
        "removed": removed,
    })


# ============================================================================
# Temu 核价（Hermes）集成
# ============================================================================

def _read_pricing_state():
    """读取 Hermes 核价状态文件，失败返回空字典。"""
    if not PRICING_STATE_FILE.exists():
        return {}
    try:
        return json.loads(PRICING_STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[pricing] 读取状态失败: {e}", flush=True)
        return {}


def _pricing_log_reader(proc, mode):
    """后台线程：读取核价脚本 stdout/stderr 并写入 pricing_task 日志。"""
    def _read_stream(stream, kind):
        try:
            for raw in iter(stream.readline, b""):
                # Hermes 脚本在 PIPE 下受 PYTHONIOENCODING=utf-8 影响输出 UTF-8；优先 UTF-8，失败回退 GBK
                line = None
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        line = raw.decode(enc, errors="strict").rstrip("\r\n")
                        break
                    except Exception:
                        continue
                if line is None:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                with pricing_lock:
                    pricing_task["log"].append({"line": line, "kind": kind})
        except Exception as e:
            with pricing_lock:
                pricing_task["log"].append({"line": f"日志读取异常: {e}", "kind": "error"})
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threads = []
    if proc.stdout:
        t = threading.Thread(target=_read_stream, args=(proc.stdout, ""), daemon=True)
        t.start()
        threads.append(t)
    if proc.stderr:
        t = threading.Thread(target=_read_stream, args=(proc.stderr, "error"), daemon=True)
        t.start()
        threads.append(t)

    # 等待进程结束
    rc = proc.wait()
    for t in threads:
        t.join(timeout=2)

    elapsed = 0
    if pricing_task.get("started_at"):
        try:
            elapsed = int((datetime.now() - datetime.fromisoformat(pricing_task["started_at"])).total_seconds())
        except Exception:
            pass

    with pricing_lock:
        pricing_task["elapsed_sec"] = elapsed
        state = _read_pricing_state()
        pricing_task["page_records"] = state.get("page_records", [])
        pricing_task["processed_pages"] = len(pricing_task["page_records"])
        if pricing_task["status"] == "running":
            if rc == 0:
                pricing_task["status"] = "completed"
                pricing_task["task_label"] = f"{mode} 完成"
            else:
                pricing_task["status"] = "error"
                pricing_task["task_label"] = f"{mode} 退出码 {rc}"
        pricing_task["completed_at"] = datetime.now().isoformat()
        pricing_task["proc"] = None


def _start_pricing_script(mode, args, label):
    """通用启动 Hermes 核价子进程。"""
    with pricing_lock:
        if pricing_task.get("status") == "running" and pricing_task.get("proc") and pricing_task["proc"].poll() is None:
            return {"error": "已有核价任务在运行，请先停止"}, 409

        pricing_task["status"] = "running"
        pricing_task["mode"] = mode
        pricing_task["task_label"] = label
        pricing_task["started_at"] = datetime.now().isoformat()
        pricing_task["completed_at"] = None
        pricing_task["log"] = [{"line": f"[{datetime.now().strftime('%H:%M:%S')}] 启动: {label}", "kind": ""}]
        pricing_task["log_index"] = 0
        pricing_task["processed_pages"] = 0
        pricing_task["elapsed_sec"] = 0
        pricing_task["page_records"] = []

    if not PRICING_DIR.exists():
        return {"error": f"核价项目目录不存在: {PRICING_DIR}"}, 404

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.Popen(
            args,
            cwd=str(PRICING_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        with pricing_lock:
            pricing_task["status"] = "error"
            pricing_task["task_label"] = f"启动失败: {e}"
            pricing_task["completed_at"] = datetime.now().isoformat()
            pricing_task["proc"] = None
        return {"error": f"启动脚本失败: {e}"}, 500

    with pricing_lock:
        pricing_task["proc"] = proc

    threading.Thread(target=_pricing_log_reader, args=(proc, mode), daemon=True).start()
    return {"ok": True, "msg": f"已启动 {label}"}, 200


@app.route('/pricing')
def pricing_page():
    """Temu 核价页面。"""
    return send_file(str(Path(__file__).parent / 'pricing.html'))


@app.route('/api/pricing/start', methods=['POST'])
def api_pricing_start():
    """启动完整核价或仅核价不提交。

    body: {"mode": "full" | "no-submit"}
    """
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "full")
    if mode == "no-submit":
        args = [get_python(), str(PRICING_MAIN), "--no-submit"]
        label = "仅核价不提交"
    else:
        args = [get_python(), str(PRICING_MAIN)]
        label = "完整自动核价"
    resp, code = _start_pricing_script(mode, args, label)
    return jsonify(resp), code


@app.route('/api/pricing/continue', methods=['POST'])
def api_pricing_continue():
    """从已填价状态继续提交。"""
    script = PRICING_ENTRYPOINT / "continue_run.py"
    if not script.exists():
        return jsonify({"error": f"脚本不存在: {script}"}), 404
    resp, code = _start_pricing_script("continue", [get_python(), str(script)], "继续提交")
    return jsonify(resp), code


@app.route('/api/pricing/retry', methods=['POST'])
def api_pricing_retry():
    """重试指定页。body: {"pages": "2 5"}。"""
    data = request.get_json(silent=True) or {}
    pages = data.get("pages", "").strip()
    if not pages:
        return jsonify({"error": "请输入页码"}), 400
    script = PRICING_ENTRYPOINT / "retry_pages.py"
    if not script.exists():
        return jsonify({"error": f"脚本不存在: {script}"}), 404
    pages_list = pages.split()
    args = [get_python(), str(script)] + pages_list
    resp, code = _start_pricing_script("retry", args, f"重试页 {pages}")
    return jsonify(resp), code


@app.route('/api/pricing/export', methods=['POST'])
def api_pricing_export():
    """导出核价结果到 Excel。"""
    script = PRICING_ENTRYPOINT / "export_prices.py"
    if not script.exists():
        return jsonify({"error": f"脚本不存在: {script}"}), 404
    resp, code = _start_pricing_script("export", [get_python(), str(script)], "导出核价结果")
    return jsonify(resp), code


@app.route('/api/pricing/stop', methods=['POST'])
def api_pricing_stop():
    """停止当前核价任务。"""
    with pricing_lock:
        proc = pricing_task.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                return jsonify({"error": f"停止失败: {e}"}), 500
        pricing_task["status"] = "stopped"
        pricing_task["task_label"] = "已停止"
        pricing_task["completed_at"] = datetime.now().isoformat()
        pricing_task["proc"] = None
    return jsonify({"ok": True, "msg": "已停止核价任务"})


@app.route('/api/pricing/status')
def api_pricing_status():
    """获取核价任务状态、增量日志和分页记录。"""
    with pricing_lock:
        state = _read_pricing_state()
        page_records = state.get("page_records", [])
        processed = len(page_records)

        # 计算运行时长
        elapsed = pricing_task.get("elapsed_sec", 0)
        if pricing_task.get("status") == "running" and pricing_task.get("started_at"):
            try:
                elapsed = int((datetime.now() - datetime.fromisoformat(pricing_task["started_at"])).total_seconds())
            except Exception:
                pass

        # 返回未读取过的日志（使用绝对长度作为下标，避免追加日志时漏读）
        idx = pricing_task.get("log_index", 0)
        all_logs = pricing_task.get("log", [])
        logs = all_logs[idx:]
        pricing_task["log_index"] = len(all_logs)

        return jsonify({
            "status": pricing_task.get("status", "idle"),
            "mode": pricing_task.get("mode"),
            "task_label": pricing_task.get("task_label", ""),
            "task": pricing_task.get("task_label", ""),
            "started_at": pricing_task.get("started_at"),
            "completed_at": pricing_task.get("completed_at"),
            "processed_pages": processed,
            "elapsed_sec": elapsed,
            "page_records": page_records,
            "log": logs,
        })


@app.route('/api/pricing/result-files')
def api_pricing_result_files():
    """列出 OUTPUT_DIR 中的核价 Excel 结果文件。"""
    files = []
    if PRICING_OUTPUT_DIR.exists():
        for p in sorted(PRICING_OUTPUT_DIR.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True):
            size = p.stat().st_size
            size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            files.append({
                "name": p.name,
                "path": str(p),
                "size": size_str,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            })
    return jsonify({"files": files})


@app.route('/api/pricing/download')
def api_pricing_download():
    """下载核价结果 Excel 文件。"""
    filename = request.args.get("file", "").strip()
    if not filename:
        return jsonify({"error": "请指定文件名"}), 400
    # 安全校验：只取文件名，不允许路径穿越
    filename = os.path.basename(filename)
    if not filename.endswith(".xlsx"):
        return jsonify({"error": "仅支持 .xlsx 文件"}), 400
    path = PRICING_OUTPUT_DIR / filename
    if not path.exists():
        return jsonify({"error": "文件不存在"}), 404
    return send_file(str(path), as_attachment=True, download_name=filename)


@app.route('/api/pricing/signal', methods=['POST'])
def api_pricing_signal():
    """创建 go.signal 文件，通知 Hermes 脚本用户已准备好开始核价。"""
    signal_path = PRICING_DIR / "go.signal"
    try:
        signal_path.write_text("go", encoding="utf-8")
        exists = signal_path.exists()
        return jsonify({"ok": True, "msg": "已发送 '好了' 信号，核价脚本将继续运行", "path": str(signal_path), "exists": exists})
    except Exception as e:
        return jsonify({"error": f"创建 signal 文件失败: {e}"}), 500


# ============================================================================
# Temu 报活动集成
# ============================================================================

def _read_activity_state():
    """读取报活动状态文件，失败或不存在返回空字典。"""
    path = Path(ACTIVITY_STATE_FILE)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[activity] 读取状态失败: {e}", flush=True)
        return {}


def _activity_log_reader(proc):
    """后台线程：读取报活动脚本 stdout/stderr 并写入 activity_task 日志。"""
    def _read_stream(stream, kind):
        try:
            for raw in iter(stream.readline, b""):
                line = None
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        line = raw.decode(enc, errors="strict").rstrip("\r\n")
                        break
                    except Exception:
                        continue
                if line is None:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                with activity_lock:
                    if kind == "error":
                        activity_task["log"].append(f"[ERR] {line}")
                    else:
                        activity_task["log"].append(line)
        except Exception as e:
            with activity_lock:
                activity_task["log"].append(f"[ERR] 日志读取异常: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threads = []
    if proc.stdout:
        t = threading.Thread(target=_read_stream, args=(proc.stdout, ""), daemon=True)
        t.start()
        threads.append(t)
    if proc.stderr:
        t = threading.Thread(target=_read_stream, args=(proc.stderr, "error"), daemon=True)
        t.start()
        threads.append(t)

    rc = proc.wait()
    for t in threads:
        t.join(timeout=2)

    with activity_lock:
        if activity_task["status"] == "running":
            if rc == 0:
                activity_task["status"] = "completed"
            else:
                activity_task["status"] = "error"
        activity_task["completed_at"] = datetime.now().isoformat()
        activity_task["proc"] = None


def _start_activity_script(label):
    """通用启动 Temu 报活动子进程。"""
    with activity_lock:
        if activity_task.get("status") == "running" and activity_task.get("proc") and activity_task["proc"].poll() is None:
            return {"success": False, "message": "已有报活动任务在运行，请先停止"}, 409

        activity_task["status"] = "running"
        activity_task["started_at"] = datetime.now().isoformat()
        activity_task["completed_at"] = None
        activity_task["log"] = [f"[{datetime.now().strftime('%H:%M:%S')}] 启动: {label}"]
        activity_task["log_index"] = 0

    if not os.path.exists(ACTIVITY_DIR):
        with activity_lock:
            activity_task["status"] = "error"
            activity_task["completed_at"] = datetime.now().isoformat()
        return {"success": False, "message": f"报活动项目目录不存在: {ACTIVITY_DIR}"}, 404

    if not os.path.exists(ACTIVITY_ENTRYPOINT):
        with activity_lock:
            activity_task["status"] = "error"
            activity_task["completed_at"] = datetime.now().isoformat()
        return {"success": False, "message": f"报活动入口脚本不存在: {ACTIVITY_ENTRYPOINT}"}, 404

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.Popen(
            [get_python(), ACTIVITY_ENTRYPOINT],
            cwd=ACTIVITY_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        with activity_lock:
            activity_task["status"] = "error"
            activity_task["completed_at"] = datetime.now().isoformat()
            activity_task["proc"] = None
        return {"success": False, "message": f"启动脚本失败: {e}"}, 500

    with activity_lock:
        activity_task["proc"] = proc

    threading.Thread(target=_activity_log_reader, args=(proc,), daemon=True).start()
    return {"success": True, "message": f"已启动 {label}"}, 200


def _retail_price_log_reader(proc):
    """后台线程：读取建议零售价脚本 stdout/stderr 并写入 retail_price_task 日志。"""
    def _read_stream(stream, kind):
        try:
            for raw in iter(stream.readline, b""):
                line = None
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        line = raw.decode(enc, errors="strict").rstrip("\r\n")
                        break
                    except Exception:
                        continue
                if line is None:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                with retail_price_lock:
                    retail_price_task["log"].append({"line": line, "kind": kind})
        except Exception as e:
            with retail_price_lock:
                retail_price_task["log"].append({"line": f"日志读取异常: {e}", "kind": "error"})
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threads = []
    if proc.stdout:
        t = threading.Thread(target=_read_stream, args=(proc.stdout, ""), daemon=True)
        t.start()
        threads.append(t)
    if proc.stderr:
        t = threading.Thread(target=_read_stream, args=(proc.stderr, "error"), daemon=True)
        t.start()
        threads.append(t)

    rc = proc.wait()
    for t in threads:
        t.join(timeout=2)

    with retail_price_lock:
        elapsed = 0
        if retail_price_task.get("started_at"):
            try:
                elapsed = int((datetime.now() - datetime.fromisoformat(retail_price_task["started_at"])).total_seconds())
            except Exception:
                pass

        retail_price_task["elapsed_sec"] = elapsed
        if retail_price_task["status"] == "running":
            if rc == 0:
                retail_price_task["status"] = "completed"
                retail_price_task["task_label"] = "填写完成"
            else:
                retail_price_task["status"] = "error"
                retail_price_task["task_label"] = f"填写失败 (退出码 {rc})"
        retail_price_task["completed_at"] = datetime.now().isoformat()
        retail_price_task["proc"] = None


def _start_retail_price_script(label, diagnose=False):
    """通用启动 Temu 建议零售价填写子进程。diagnose=True 时附加 --diagnose 参数（仅 dump 抽屉结构，不填写/不提交）。"""
    with retail_price_lock:
        if retail_price_task.get("status") == "running" and retail_price_task.get("proc") and retail_price_task["proc"].poll() is None:
            return {"error": "已有建议零售价任务在运行，请先停止"}, 409

        retail_price_task["status"] = "running"
        retail_price_task["task_label"] = label
        retail_price_task["started_at"] = datetime.now().isoformat()
        retail_price_task["completed_at"] = None
        retail_price_task["log"] = [{"line": f"[{datetime.now().strftime('%H:%M:%S')}] 启动: {label}", "kind": ""}]
        retail_price_task["log_index"] = 0
        retail_price_task["elapsed_sec"] = 0

    if not RETAIL_PRICE_DIR.exists():
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
            retail_price_task["proc"] = None
        return {"error": f"建议零售价项目目录不存在: {RETAIL_PRICE_DIR}"}, 404

    if not RETAIL_PRICE_SCRIPT.exists():
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
            retail_price_task["proc"] = None
        return {"error": f"建议零售价脚本不存在: {RETAIL_PRICE_SCRIPT}"}, 404

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        node_args = ["node", str(RETAIL_PRICE_SCRIPT), "--no-close-browser"]
        if diagnose:
            # --diagnose 插在脚本名之后、--no-close-browser 之前，保持参数顺序清晰
            node_args.insert(2, "--diagnose")
        proc = subprocess.Popen(
            node_args,
            cwd=str(RETAIL_PRICE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
            retail_price_task["proc"] = None
        return {"error": f"启动脚本失败: {e}"}, 500

    with retail_price_lock:
        retail_price_task["proc"] = proc

    threading.Thread(target=_retail_price_log_reader, args=(proc,), daemon=True).start()
    return {"ok": True, "msg": f"已启动 {label}"}, 200


@app.route('/activity')
def activity_page():
    """Temu 报活动页面。"""
    return send_file(str(Path(__file__).parent / 'activity.html'))


@app.route('/api/activity/start', methods=['POST'])
def api_activity_start():
    """启动 Temu 报活动脚本。"""
    resp, code = _start_activity_script("报活动")
    return jsonify(resp), code


@app.route('/api/activity/stop', methods=['POST'])
def api_activity_stop():
    """停止当前报活动任务。"""
    with activity_lock:
        proc = activity_task.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                return jsonify({"success": False, "message": f"停止失败: {e}"}), 500
        activity_task["status"] = "stopped"
        activity_task["completed_at"] = datetime.now().isoformat()
        activity_task["proc"] = None
    return jsonify({"success": True})


@app.route('/api/activity/status')
def api_activity_status():
    """获取报活动任务状态、增量日志和状态文件信息。"""
    with activity_lock:
        state_info = _read_activity_state()

        # 返回未读取过的日志（按 contract 返回字符串数组）
        idx = activity_task.get("log_index", 0)
        all_logs = activity_task.get("log", [])
        logs = []
        for entry in all_logs[idx:]:
            if isinstance(entry, dict):
                logs.append(entry.get("line", ""))
            else:
                logs.append(str(entry))
        activity_task["log_index"] = len(all_logs)

        # 计算运行时长
        elapsed = 0
        if activity_task.get("status") == "running" and activity_task.get("started_at"):
            try:
                elapsed = int((datetime.now() - datetime.fromisoformat(activity_task["started_at"])).total_seconds())
            except Exception:
                pass

        # 状态映射：stopped 对前端显示为 idle
        raw_status = activity_task.get("status", "idle")
        display_status = "idle" if raw_status == "stopped" else raw_status

        # state_info 不存在时返回 None，保持 graceful
        if not state_info:
            state_info = None

        return jsonify({
            "status": display_status,
            "started_at": activity_task.get("started_at"),
            "elapsed_sec": elapsed,
            "log": logs,
            "state_info": {
                "current_step": state_info.get("current_step"),
                "completed_steps": state_info.get("completed_steps", []),
                "errors": state_info.get("errors", []),
                "meta": state_info.get("meta", {}),
            } if state_info else None,
        })


@app.route('/retail_price')
def retail_price_page():
    """Temu 建议零售价填写页面。"""
    return send_file(str(Path(__file__).parent / 'retail_price.html'))


@app.route('/api/retail_price/start', methods=['POST'])
def api_retail_price_start():
    """启动 Temu 建议零售价填写脚本。"""
    resp, code = _start_retail_price_script("建议零售价填写")
    return jsonify(resp), code


@app.route('/api/retail_price/start_diagnose', methods=['POST'])
def api_retail_price_start_diagnose():
    """启动 Temu 建议零售价诊断：仅 dump 抽屉结构，不填写/不提交。复用「👌 好了」信号触发。"""
    resp, code = _start_retail_price_script("建议零售价诊断", diagnose=True)
    return jsonify(resp), code


@app.route('/api/retail_price/stop', methods=['POST'])
def api_retail_price_stop():
    """停止当前建议零售价填写任务。"""
    with retail_price_lock:
        proc = retail_price_task.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                retail_price_task["status"] = "error"
                retail_price_task["task_label"] = "停止失败"
                retail_price_task["proc"] = None
                retail_price_task["log"].append({"line": f"[{datetime.now().strftime('%H:%M:%S')}] 停止失败: {e}", "kind": "error"})
                return jsonify({"error": f"停止失败: {e}"}), 500
        retail_price_task["status"] = "stopped"
        retail_price_task["task_label"] = "已停止"
        retail_price_task["completed_at"] = datetime.now().isoformat()
        retail_price_task["proc"] = None
    return jsonify({"ok": True, "msg": "已停止"})


@app.route('/api/retail_price/status')
def api_retail_price_status():
    """获取建议零售价填写任务状态与增量日志。"""
    with retail_price_lock:
        idx = retail_price_task.get("log_index", 0)
        all_logs = retail_price_task.get("log", [])
        logs = all_logs[idx:]
        retail_price_task["log_index"] = len(all_logs)

        elapsed = 0
        if retail_price_task.get("status") == "running" and retail_price_task.get("started_at"):
            try:
                elapsed = int((datetime.now() - datetime.fromisoformat(retail_price_task["started_at"])).total_seconds())
            except Exception:
                pass

        raw_status = retail_price_task.get("status", "idle")
        display_status = "idle" if raw_status == "stopped" else raw_status

        return jsonify({
            "status": display_status,
            "task_label": retail_price_task.get("task_label", ""),
            "started_at": retail_price_task.get("started_at"),
            "completed_at": retail_price_task.get("completed_at"),
            "elapsed_sec": elapsed,
            "log": logs,
        })


@app.route('/api/retail_price/signal', methods=['POST'])
def api_retail_price_signal():
    """创建 go.signal 文件，通知脚本用户已准备好。"""
    signal_path = RETAIL_PRICE_DIR / "go.signal"
    try:
        signal_path.write_text("", encoding="utf-8")
        return jsonify({"ok": True, "msg": "已发送'好了'信号"})
    except Exception as e:
        return jsonify({"error": f"创建信号文件失败: {e}"}), 500


# ============================================================================
# 胚衣制作（素材库）
# ============================================================================

@app.route('/peiyi')
def peiyi_page():
    """胚衣制作页面：分类上传素材，自动处理为 1340×1785 @ 72DPI。"""
    return send_file(str(Path(__file__).parent / 'peiyi.html'))


def _peiyi_max_index(dest_dir, prefix: str) -> int:
    """返回该分类文件夹中已存在的最大序号（黑W12.jpg -> 12），用于按进入顺序命名。"""
    max_idx = 0
    plen = len(prefix)
    if dest_dir.exists():
        for fn in os.listdir(dest_dir):
            low = fn.lower()
            if low.endswith('.jpg') and low.startswith(prefix.lower()):
                num_part = fn[plen:-4]
                if num_part.isdigit():
                    max_idx = max(max_idx, int(num_part))
    return max_idx


def _peiyi_process_image(src_path: str, category: str, dest_path: str):
    """读取源图，强制拉伸到 1340×1785，合成底色，以 72 DPI 存为 JPG。"""
    from PIL import Image, ImageOps
    bg = PEIYI_BG.get(category, (255, 255, 255))
    with Image.open(src_path) as im:
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
            base = Image.new('RGB', im.size, bg)
            if im.mode == 'P':
                im = im.convert('RGBA')
            base.paste(im, (0, 0), im)
            im = base
        else:
            im = im.convert('RGB')
        # 强制拉伸铺满目标尺寸（用户确认：允许变形）
        im = im.resize(PEIYI_SIZE, Image.LANCZOS)
        im.save(dest_path, 'JPEG', dpi=PEIYI_DPI, quality=92)


@app.route('/api/peiyi/upload', methods=['POST'])
def api_peiyi_upload():
    """批量上传素材：按 category 自动处理并存入对应文件夹。"""
    category = request.form.get('category', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': f'未知分类: {category}'}), 400
    files = request.files.getlist('files')
    if not files:
        return jsonify({'ok': False, 'error': '未收到文件'}), 400

    dest_dir = PEIYI_CATEGORIES[category]
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 按进入顺序命名：颜色 + 面 + 序号（黑W1, 黑W2 ...；白B1 ...）
    prefix = (category[1] if len(category) > 1 else '') + category[0]
    next_idx = _peiyi_max_index(dest_dir, prefix) + 1

    results = []
    ok_count = 0
    for f in files:
        orig = f.filename or 'material'
        if not orig.lower().endswith(PEIYI_ALLOWED_EXT):
            results.append({'file': orig, 'ok': False, 'error': '不支持的图片格式'})
            continue
        tmp = dest_dir / (f'_tmp_{datetime.now().strftime("%H%M%S%f")}_{os.path.splitext(orig)[1]}')
        f.save(str(tmp))
        try:
            out_name = f'{prefix}{next_idx}.jpg'
            next_idx += 1
            out_path = dest_dir / out_name
            # 保险：序号理论上递增不会撞，仍做兜底顺延
            while out_path.exists():
                out_name = f'{prefix}{next_idx}.jpg'
                next_idx += 1
                out_path = dest_dir / out_name
            _peiyi_process_image(str(tmp), category, str(out_path))
            results.append({'file': orig, 'ok': True, 'saved': out_path.name})
            ok_count += 1
        except Exception as e:
            results.append({'file': orig, 'ok': False, 'error': str(e)})
        finally:
            try:
                os.remove(str(tmp))
            except OSError:
                pass

    return jsonify({'ok': True, 'category': category, 'saved': ok_count, 'results': results})


def _peiyi_read_meta(dest_dir, name):
    """读取与图片同名的 .meta.json 侧车，返回5个参数字典；不存在/损坏返回 None。"""
    stem, _ = os.path.splitext(name)
    mp = dest_dir / (stem + '.meta.json')
    if not mp.exists():
        return None
    try:
        data = json.loads(mp.read_text(encoding='utf-8'))
        return {k: data.get(k) for k in PEIYI_META_KEYS}
    except Exception:
        return None


@app.route('/api/peiyi/list')
def api_peiyi_list():
    """列出各分类已存素材（用于画廊预览），含每张图的贴图参数 meta。"""
    category = request.args.get('category', '')
    if category and category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    cats = [category] if category else list(PEIYI_CATEGORIES.keys())
    out = {}
    for c in cats:
        d = PEIYI_CATEGORIES[c]
        items = []
        if d.exists():
            for fn in os.listdir(d):
                # 只把“原图”纳入画廊：① 允许的图像格式；② 非临时文件；③ 非遮罩侧车
                lfn = fn.lower()
                ext = os.path.splitext(lfn)[1]
                if ext not in PEIYI_ALLOWED_EXT:
                    continue
                if fn.startswith('_tmp_'):
                    continue
                if any(lfn.endswith(s) for s in PEIYI_MASK_SUFFIXES):
                    continue
                fp = d / fn
                try:
                    st = fp.stat()
                    meta = _peiyi_read_meta(d, fn)
                    unfilled = (meta is None)   # 尚未填写五项数据
                    if unfilled:
                        meta = {k: default for k, _, default in PEIYI_META_FIELDS}
                    # 遮罩状态（body_mask / occluder_mask / occluder / parse）
                    stem, _ = os.path.splitext(fn)
                    occ_mask_path = d / (stem + '_occluder_mask.png')
                    occ_path = d / (stem + '_occluder.png')
                    occ_px = None
                    has_mask = False
                    if occ_mask_path.exists():
                        has_mask = True
                        try:
                            occ_arr = np.array(Image.open(str(occ_mask_path)))
                            occ_px = int((occ_arr > 0).sum())
                        except Exception:
                            occ_px = None
                    elif occ_path.exists():
                        has_mask = True
                    mask_urls = {}
                    for suffix, key in [
                        ('_occluder.png', 'occluder'),
                        ('_occluder_mask.png', 'occluder_mask'),
                        ('_body_mask.png', 'body_mask'),
                        ('_parse.png', 'parse'),
                    ]:
                        mp = d / (stem + suffix)
                        if mp.exists():
                            mask_urls[key] = f'/api/peiyi/material/{urllib.parse.quote(c)}/{urllib.parse.quote(mp.name)}'
                    # 最新一版遮罩评分（用于图片墙角标），读不到则 None
                    score_info = _peiyi_latest_score(d, stem)
                    items.append({
                        'name': fn,
                        'size': st.st_size,
                        # URL 编码文件名/分类，避免中文路径导致浏览器无法加载图片
                        'url': f'/api/peiyi/material/{urllib.parse.quote(c)}/{urllib.parse.quote(fn)}',
                        'modified': datetime.fromtimestamp(st.st_mtime).isoformat(),
                        'meta': meta,
                        'unfilled': unfilled,
                        'has_mask': has_mask,
                        'occluder_px': occ_px,
                        'mask_urls': mask_urls,
                        'score': score_info,
                        '_mtime': st.st_mtime,
                    })
                except OSError:
                    pass
            # 排序：① 未填写五项数据的排最前；② 同组内按修改时间倒序（后进入排前面）
            items.sort(key=lambda e: (0 if e['unfilled'] else 1, -e['_mtime']))
            for e in items:
                e.pop('_mtime', None)
        out[c] = items
    return jsonify({'ok': True, 'categories': out})


def _peiyi_latest_score(category_dir, stem):
    """读取某胚衣最新一版的评分（来自 _mask_versions/<stem>/latest.txt → vNNN/score.json）。
    返回 dict 或 None（尚无版本/读取失败）。任何异常都吞掉，绝不影响列表页。"""
    try:
        vroot = Path(category_dir) / "_mask_versions" / stem
        latest_f = vroot / "latest.txt"
        if not latest_f.exists():
            return None
        latest = latest_f.read_text(encoding="utf-8").strip()
        sf = vroot / latest / "score.json"
        if not sf.exists():
            return None
        import json as _json
        data = _json.loads(sf.read_text(encoding="utf-8"))
        m = data.get("metrics", {}) or {}
        return {
            "version": data.get("version", latest),
            "timestamp": data.get("timestamp", ""),
            "algorithm_version": data.get("algorithm_version", ""),
            "score": data.get("score"),
            "occ_ratio": m.get("occ_ratio"),
            "body_coverage": m.get("body_coverage"),
            "is_person": m.get("is_person"),
            "flat_lay": m.get("flat_lay"),
            "flags": data.get("flags", []) or [],
        }
    except Exception:
        return None


@app.route('/api/peiyi/scores')
def api_peiyi_scores():
    """汇总所有胚衣最新一版的评分（低分可一眼标红）。
    评分在“生成遮罩”时写入 _mask_versions/<stem>/vNNN/score.json。"""
    category = request.args.get('category', '')
    if category and category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    cats = [category] if category else list(PEIYI_CATEGORIES.keys())
    rows = []
    for c in cats:
        d = PEIYI_CATEGORIES[c]
        if not d.exists():
            continue
        for fn in os.listdir(d):
            lfn = fn.lower()
            ext = os.path.splitext(lfn)[1]
            if ext not in PEIYI_ALLOWED_EXT:
                continue
            if fn.startswith('_tmp_'):
                continue
            if any(lfn.endswith(s) for s in PEIYI_MASK_SUFFIXES):
                continue
            stem, _ = os.path.splitext(fn)
            info = _peiyi_latest_score(d, stem)
            row = {'category': c, 'name': fn, 'stem': stem, 'has_score': info is not None}
            if info:
                row.update(info)
            rows.append(row)
    # 排序：有分数按分数升序（低分排最前，问题胚衣一眼可见），无分数排最后
    def _key(r):
        sc = r.get('score')
        return (0, sc) if (r.get('has_score') and isinstance(sc, (int, float))) else (1, 0)
    rows.sort(key=_key)
    return jsonify({'ok': True, 'rows': rows})


@app.route('/api/peiyi/material/<category>/<path:filename>')
def api_peiyi_material(category, filename):
    """返回已存素材（原图 / 遮罩侧车）。

    遮罩文件会被“重新生成遮罩”覆盖更新，因此此处禁用浏览器缓存
    （Cache-Control: no-store, no-cache），确保预览/画廊实时反映最新内容；
    并按真实扩展名返回正确 MIME（PNG 遮罩不再被当成 JPEG，避免渲染异常）。
    """
    if category not in PEIYI_CATEGORIES:
        abort(404)
    safe = os.path.basename(filename)
    fp = PEIYI_CATEGORIES[category] / safe
    if not fp.exists():
        abort(404)
    ext = os.path.splitext(safe)[1].lower().lstrip('.')
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'webp': 'image/webp', 'bmp': 'image/bmp'}
    mime = mime_map.get(ext, 'image/jpeg')
    resp = send_file(str(fp), mimetype=mime, max_age=0)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


# 版本文件名后缀 → 预览键（与 _mask_versions/<stem>/vNNN/ 内的侧车一致）
_PEIYI_VERSION_FILE_KEYS = [
    ('_occluder.png', 'occluder'),
    ('_occluder_mask.png', 'occluder_mask'),
    ('_body_mask.png', 'body_mask'),
    ('_parse.png', 'parse'),
    ('_alpha.png', 'alpha'),
]


@app.route('/api/peiyi/versions/<category>/<stem>')
def api_peiyi_versions(category, stem):
    """列出某胚衣的所有遮罩版本（每个版本的分数/时间/指标/各层遮罩图URL/是否当前）。
    数据来自 _mask_versions/<stem>/vNNN/ + latest.txt。"""
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    stem = os.path.basename(stem)
    d = PEIYI_CATEGORIES[category]
    vroot = d / "_mask_versions" / stem
    current = None
    versions = []
    if vroot.exists():
        latest_f = vroot / "latest.txt"
        if latest_f.exists():
            try:
                current = latest_f.read_text(encoding="utf-8").strip()
            except Exception:
                current = None
        for vd in sorted(vroot.iterdir()):
            if not (vd.is_dir() and vd.name.startswith('v')):
                continue
            info = {}
            sf = vd / "score.json"
            if sf.exists():
                try:
                    info = json.loads(sf.read_text(encoding="utf-8"))
                except Exception:
                    info = {}
            urls = {}
            for suffix, key in _PEIYI_VERSION_FILE_KEYS:
                if (vd / (stem + suffix)).exists():
                    urls[key] = (f'/api/peiyi/version_file/{urllib.parse.quote(category)}'
                                 f'/{urllib.parse.quote(stem)}/{urllib.parse.quote(vd.name)}'
                                 f'/{urllib.parse.quote(stem + suffix)}')
            versions.append({
                'version': vd.name,
                'score': info.get('score'),
                'timestamp': info.get('timestamp', ''),
                'algorithm_version': info.get('algorithm_version', ''),
                'flags': info.get('flags', []) or [],
                'metrics': info.get('metrics', {}) or {},
                'is_current': (vd.name == current),
                'urls': urls,
            })
    return jsonify({'ok': True, 'category': category, 'stem': stem,
                    'current': current, 'versions': versions})


@app.route('/api/peiyi/version_file/<category>/<stem>/<version>/<path:filename>')
def api_peiyi_version_file(category, stem, version, filename):
    """返回某胚衣某版本目录里的遮罩图片（禁用缓存，按真实扩展名给 MIME）。"""
    if category not in PEIYI_CATEGORIES:
        abort(404)
    stem = os.path.basename(stem)
    version = os.path.basename(version)
    safe = os.path.basename(filename)
    fp = PEIYI_CATEGORIES[category] / "_mask_versions" / stem / version / safe
    if not fp.exists():
        abort(404)
    ext = os.path.splitext(safe)[1].lower().lstrip('.')
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'webp': 'image/webp', 'bmp': 'image/bmp'}
    mime = mime_map.get(ext, 'image/png')
    resp = send_file(str(fp), mimetype=mime, max_age=0)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/api/peiyi/use_version', methods=['POST'])
def api_peiyi_use_version():
    """把选中版本的遮罩文件复制回素材库标准路径（=退回/切换到该版本），并更新 latest.txt。
    生产贴图读的是标准路径，因此这一步立即决定以后用哪一版。"""
    data = request.get_json(force=True, silent=True) or {}
    category = data.get('category', '')
    stem = os.path.basename(data.get('stem', ''))
    version = os.path.basename(data.get('version', ''))
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    if not stem or not version:
        return jsonify({'ok': False, 'error': '缺少 stem/version'}), 400
    d = PEIYI_CATEGORIES[category]
    vdir = d / "_mask_versions" / stem / version
    if not vdir.exists():
        return jsonify({'ok': False, 'error': '版本不存在'}), 404
    copied = []
    for suffix, _ in _PEIYI_VERSION_FILE_KEYS:
        src = vdir / (stem + suffix)
        if src.exists():
            try:
                shutil.copy2(str(src), str(d / (stem + suffix)))
                copied.append(suffix)
            except Exception as e:
                return jsonify({'ok': False, 'error': f'复制失败 {suffix}: {e}'}), 500
    try:
        (d / "_mask_versions" / stem / "latest.txt").write_text(version, encoding="utf-8")
    except Exception as e:
        return jsonify({'ok': False, 'error': f'更新 latest.txt 失败: {e}'}), 500
    return jsonify({'ok': True, 'category': category, 'stem': stem,
                    'version': version, 'copied': copied})


def _explorer_select_file(path):
    """在资源管理器中打开 path 所在文件夹并【选中】该文件（Windows 最可靠方式）。

    为什么不用 explorer /select,：该命令对带空格/中文的路径解析极不稳定，
    一旦解析失败就会回退到“文档库”。这里改用系统底层
    SHOpenFolderAndSelectItems（专业软件通用做法），彻底避开该坑。
    返回 True 表示已成功触发；全部失败时返回 False。
    """
    import os
    import ctypes
    from ctypes import wintypes, POINTER, byref, c_void_p, c_uint
    path = os.path.normpath(str(path))
    folder = os.path.dirname(path)
    # 方法1：ctypes 调用 Shell 接口精准选中文件（无空格/中文坑）
    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        # 必须先初始化 COM（STA），否则 Shell 接口会报“尚未调用 CoInitialize”
        init_hr = ole32.CoInitialize(None)
        try:
            shell32.SHParseDisplayName.argtypes = [
                wintypes.LPCWSTR, c_void_p, POINTER(c_void_p), c_uint, POINTER(c_uint)
            ]
            shell32.SHParseDisplayName.restype = ctypes.HRESULT
            shell32.SHOpenFolderAndSelectItems.argtypes = [
                c_void_p, c_uint, POINTER(c_void_p), c_uint
            ]
            shell32.SHOpenFolderAndSelectItems.restype = ctypes.HRESULT
            pidl = c_void_p()
            attrs = c_uint()
            hr = shell32.SHParseDisplayName(path, None, byref(pidl), 0, byref(attrs))
            if hr == 0 and pidl:
                try:
                    shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
                    return True
                finally:
                    ole32.CoTaskMemFree(pidl)
        finally:
            # 仅有本函数成功初始化时才反初始化，避免误关别的模块已初始化的 COM
            if init_hr == 0:
                ole32.CoUninitialize()
    except Exception:
        pass
    # 方法2：兜底 explorer /select,（带引号，正确处理空格/中文）
    try:
        subprocess.Popen(f'explorer.exe /select,"{path}"', shell=True)
        return True
    except Exception:
        pass
    # 方法3：兜底只打开正确文件夹（至少不会跑到“文档”）
    try:
        os.startfile(folder)
        return True
    except Exception:
        pass
    try:
        subprocess.Popen(f'explorer.exe "{folder}"', shell=True)
        return True
    except Exception:
        return False


@app.route('/api/peiyi/open', methods=['POST'])
def api_peiyi_open():
    """在文件资源管理器中打开该素材所在文件夹并选中该文件（仅本机/localhost 生效）。"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    fp = PEIYI_CATEGORIES[category] / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    try:
        ok = _explorer_select_file(str(fp))
        return jsonify({'ok': ok, 'path': str(fp)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/peiyi/delete', methods=['POST'])
def api_peiyi_delete():
    """删除某个已存素材。"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    fp = PEIYI_CATEGORIES[category] / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    try:
        os.remove(str(fp))
        # 同时删除该素材的遮罩/参数侧车文件
        stem, _ = os.path.splitext(safe)
        for suffix in ['.meta.json', '_occluder.png', '_occluder_mask.png', '_body_mask.png', '_parse.png', '_alpha.png']:
            try:
                (fp.parent / (stem + suffix)).unlink(missing_ok=True)
            except Exception:
                pass
        return jsonify({'ok': True, 'msg': f'{safe} 已删除'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/peiyi/reindex', methods=['POST'])
def api_peiyi_reindex():
    """把某分类文件夹内所有图片按进入顺序（修改时间）重新编号为 黑W1, 黑W2 ...。
    用于手动拖入、尚未按规则命名的图片。两遍重命名避免同名冲突。"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    d = PEIYI_CATEGORIES[category]
    if not d.exists():
        return jsonify({'ok': True, 'renamed': 0, 'msg': '空文件夹'})
    prefix = (category[1] if len(category) > 1 else '') + category[0]

    files = [fn for fn in os.listdir(d)
             if fn.lower().endswith('.jpg') and not fn.startswith('_tmp_')]
    files.sort(key=lambda fn: os.path.getmtime(str(d / fn)))

    # 第一遍：全部移到临时名，腾出目标名
    tmp_map = []
    for i, fn in enumerate(files):
        tmp = f'_re_{i}_{fn}'
        os.rename(str(d / fn), str(d / tmp))
        tmp_map.append((tmp, i + 1))
    # 第二遍：临时名 -> 黑W1, 黑W2 ...
    renamed = 0
    for tmp, idx in tmp_map:
        new_name = f'{prefix}{idx}.jpg'
        dest = d / new_name
        n = idx
        while dest.exists():
            n += 1
            dest = d / f'{prefix}{n}.jpg'
        os.rename(str(d / tmp), str(dest))
        renamed += 1
    return jsonify({'ok': True, 'renamed': renamed, 'prefix': prefix,
                    'msg': f'已重新编号为 {prefix}1..{prefix}{renamed}'})


@app.route('/api/peiyi/meta', methods=['POST'])
def api_peiyi_meta():
    """保存单张素材的5个贴图参数到同名 .meta.json 侧车（与 胚衣参数表_模板.csv 第5-9列一致）。"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    if not (d / safe).exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    stem, _ = os.path.splitext(safe)
    meta = {}
    for k, _, default in PEIYI_META_FIELDS:
        v = data.get(k)
        if v is None or v == '':
            meta[k] = default
        else:
            try:
                meta[k] = float(v)
            except (TypeError, ValueError):
                meta[k] = default
    (d / (stem + '.meta.json')).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return jsonify({'ok': True, 'meta': meta})


@app.route('/api/peiyi/mask', methods=['POST'])
def api_peiyi_mask():
    """为单张胚衣素材生成三层遮罩 + _tpl 扭曲素材。

    返回 JSON 在原有 masks 基础上新增 tpl 字段（_tpl 生成状态）。
    """
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    # 隔离到子进程执行（cv2/OpenMP 偶发崩溃会拖垮主服务，故必须隔离）
    try:
        MOCKUP_OUT.mkdir(parents=True, exist_ok=True)
        env = _single_thread_env(os.environ)
        env["PYTHONPATH"] = f"{ZCODE_PROJECT};{PY_PACKAGES}"
        out_log = MOCKUP_OUT / "_mask_stdout.log"
        err_log = MOCKUP_OUT / "_mask_stderr.log"
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        with open(out_log, "w", encoding="utf-8", errors="replace") as of, \
             open(err_log, "w", encoding="utf-8", errors="replace") as ef:
            r = subprocess.run(
                [str(MOCKUP_PY), str(ZCODE_PROJECT / "_peiyi_worker.py"), "mask", str(fp), category,
                 str(out_log) + ".json"],
                cwd=str(ZCODE_PROJECT), env=env,
                stdin=subprocess.DEVNULL, stdout=of, stderr=ef,
                timeout=600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                startupinfo=startupinfo,
            )
        raw = out_log.read_text(encoding="utf-8", errors="replace").strip()
        err = err_log.read_text(encoding="utf-8", errors="replace").strip()
        res_path = str(out_log) + ".json"
        if r.returncode != 0 or not Path(res_path).exists():
            return jsonify({'ok': False,
                            'error': f'subprocess rc={r.returncode}: {err[-800:]}',
                            'trace': raw[-800:]}), 500
        res = json.loads(Path(res_path).read_text(encoding="utf-8", errors="replace"))
        return jsonify(res), (200 if res.get('ok') else 500)
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}', 'trace': _tb.format_exc()[-1500:]}), 500


@app.route('/api/peiyi/correct_preview', methods=['POST'])
def api_peiyi_correct_preview():
    """预览校正效果（不保存，返回临时区状态）"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')
    click_x = data.get('x')
    click_y = data.get('y')
    mode = data.get('mode', 'add_occ')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    if click_x is None or click_y is None:
        return jsonify({'ok': False, 'error': '缺少点击坐标 x, y'}), 400
    if mode not in ('add_occ', 'remove_occ', 'add_body'):
        return jsonify({'ok': False, 'error': f'未知模式: {mode}'}), 400

    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404

    try:
        import peiyi_correct
        result = peiyi_correct.preview_correction(str(fp), click_x, click_y, mode=mode)
        if result.get('ok'):
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/peiyi/correct_confirm', methods=['POST'])
def api_peiyi_correct_confirm():
    """确认临时遮罩并归档为新版本"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404

    try:
        import peiyi_correct
        result = peiyi_correct.confirm_correction(str(fp))
        if result.get('ok'):
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/peiyi/correct_cancel', methods=['POST'])
def api_peiyi_correct_cancel():
    """放弃临时修改"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404

    try:
        import peiyi_correct
        result = peiyi_correct.cancel_correction(str(fp))
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/peiyi/correct_check', methods=['POST'])
def api_peiyi_correct_check():
    """检查是否有未确认的临时修改"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404

    try:
        import peiyi_correct
        result = peiyi_correct.check_working_status(str(fp))
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/peiyi/working_file/<category>/<stem>/<path:filename>')
def api_peiyi_working_file(category, stem, filename):
    """提供 _working 临时目录的预览图"""
    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(filename)
    fp = PEIYI_CATEGORIES[category] / "_mask_versions" / stem / "_working" / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    return send_file(str(fp))


@app.route('/api/peiyi/delete_version', methods=['POST'])
def api_peiyi_delete_version():
    """删除指定版本（不能删除当前正在使用的版本）"""
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    stem = data.get('stem', '')
    version = data.get('version', '')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    if not stem or not version:
        return jsonify({'ok': False, 'error': '缺少 stem 或 version'}), 400

    d = PEIYI_CATEGORIES[category]
    try:
        import peiyi_correct
        result = peiyi_correct.delete_version(d, stem, version)
        if result.get('ok'):
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/peiyi/import_manual', methods=['POST'])
def api_peiyi_import_manual():
    """导入 PS 手动遮罩，与 AI 遮罩合并。

    POST JSON: { "category": "W白", "name": "白W2.jpg" }
    手动遮罩文件位置: 素材目录/白W2_manual.png 或 _mask_versions/白W2/白W2.png
    """
    data = request.get_json(silent=True) or {}
    category = data.get('category', '')
    name = data.get('name', '')

    if category not in PEIYI_CATEGORIES:
        return jsonify({'ok': False, 'error': '未知分类'}), 400
    safe = os.path.basename(name)
    d = PEIYI_CATEGORIES[category]
    fp = d / safe
    if not fp.exists():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404

    try:
        import peiyi_correct
        result = peiyi_correct.import_manual_mask(str(fp))
        if result.get('ok'):
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


# ============================================================================
# 贴图（AI 去背贴图）：自动按胚衣数据 + 遮罩 + 扭曲精准贴入
# ============================================================================
def _resolve_peiyi_embryo(category, name):
    """素材库图片路径、款名 stem、衫色（按分类名含 黑/白 推断）。"""
    safe = os.path.basename(name)
    fp = PEIYI_CATEGORIES[category] / safe
    stem = fp.stem
    color = "black" if "黑" in category else "white"
    return fp, stem, color


def _find_category_for_stem(stem):
    """按款名 stem 在四大分类里反查 category + 文件名。"""
    for cat, d in PEIYI_CATEGORIES.items():
        if not d.exists():
            continue
        cand = d / f"{stem}.jpg"
        if cand.exists():
            return cat, cand.name
        cand = d / stem
        if cand.exists():
            return cat, cand.name
    return None, None


def _load_presets():
    """同步 CSV→presets.json（若 CSV 更新）并读取 templates。"""
    try:
        sys.path.insert(0, str(Path(r"E:/Kimi Code/scripts")))
        import sync_presets_from_csv
        sync_presets_from_csv.sync_if_stale()
    except Exception:
        pass
    p = Path(r"E:/Kimi Code/white_t_mockup/presets.json")
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("templates", {})
    except Exception:
        return {}


def _preset_key_for_stem(stem, presets):
    if stem in presets:
        return stem
    for k, v in presets.items():
        if Path(v.get("path", "")).stem == stem:
            return k
    return None


def _embryo_fields(category, name, presets):
    """读取5个贴图字段：素材库 .meta.json 优先，CSV→presets 兜底。

    注意：meta 未填写的字段必须显式视为「缺失」（None），不能用 670 这类
    魔法默认值占位，否则会挡住 presets 的同名字段（如中心点x）。
    """
    meta = _peiyi_read_meta(PEIYI_CATEGORIES[category], name) or {}

    def _num(v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    fw = _num(meta.get("width"))
    fh = _num(meta.get("height"))
    rot = _num(meta.get("rotation"))
    ty = _num(meta.get("highest_y"))
    cx = _num(meta.get("center_x"))

    stem = Path(name).stem
    pkey = _preset_key_for_stem(stem, presets)
    p = presets.get(pkey) if pkey else None
    if p:
        if fw is None:
            fw = _num(p.get("final_w"))
        if fh is None:
            fh = _num(p.get("final_h"))
        if rot is None:
            rot = _num(p.get("rotation_degrees"))
        if ty is None:
            ty = _num(p.get("effective_top_y"))
        if cx is None:
            cx = _num(p.get("effective_center_x"))
    # 兜底默认值（仅在所有来源都缺失时）
    fw = fw or 0.0
    fh = fh or 0.0
    rot = rot or 0.0
    ty = ty or 0.0
    cx = cx if cx is not None else 670.0
    return {"final_w": fw, "final_h": fh, "rotation": rot, "top_y": ty, "center_x": cx}


def _ensure_tpl(stem, fp):
    """确保 _tpl/<款名>/ 存在（自动生成扭曲素材）。返回 tpl_dir 或 None。"""
    tpl_dir = TPL_ROOT / stem
    if (tpl_dir / "mask.png").exists():
        return tpl_dir
    try:
        import tpl_generator
        out_dir, cov, hint, src = tpl_generator.generate_tpl_for_material(str(fp), TPL_ROOT)
        return out_dir
    except Exception as e:
        print(f"[贴图] _tpl 生成失败 {stem}: {e}", flush=True)
        return None


def _ensure_occluder(fp, category):
    """若素材库图片尚未生成 body/occluder 遮罩，则生成（best-effort，超时/失败不阻塞贴图）。"""
    occ = fp.parent / (fp.stem + "_occluder.png")
    if occ.exists():
        return occ
    try:
        env = _single_thread_env(os.environ)
        env["PYTHONPATH"] = f"{ZCODE_PROJECT};{PY_PACKAGES}"
        code = (
            "import peiyi_mask,sys\n"
            "r=peiyi_mask.generate_masks(sys.argv[1], category=sys.argv[2])\n"
            "print('OK' if r.get('ok') else 'FAIL', str(r.get('error',''))[:200])\n"
        )
        r = subprocess.run(
            [str(MOCKUP_PY), "-c", code, str(fp), category],
            cwd=str(MOCKUP_ROOT), env=env, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        print(f"[贴图] 遮罩生成: {r.stdout.strip()[-200:]} {r.stderr.strip()[-200:]}", flush=True)
    except Exception as e:
        print(f"[贴图] 遮罩生成跳过 {fp.name}: {e}", flush=True)
    return occ if occ.exists() else None


def _remove_white_bg(path):
    """把近白底的 PNG 转透明底（适用于白底/纯色底设计图）。"""
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("RGBA")
        a = np.array(im)
        rgb = a[..., :3].astype(np.int16)
        white = (rgb[:, :, 0] > 240) & (rgb[:, :, 1] > 240) & (rgb[:, :, 2] > 240)
        a[white, 3] = 0
        Image.fromarray(a).save(path)
    except Exception:
        pass


def _run_white_t_mockup(design_path, out_path, preset_key, fp, fields, tpl_dir, color, occluder):
    env = _single_thread_env(os.environ)
    env["PYTHONPATH"] = f"{MOCKUP_ROOT};{PY_PACKAGES}"
    # 彻底关闭 cv2 内部多线程：后台进程里 cv2 的 warp/remap 多线程偶发段错误，
    # 关闭后基本不再崩溃（白 T 恤合成依赖 displacement 扭曲，最易触发）
    env["OPENCV_DISABLE_THREADING"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"

    cmd = [str(MOCKUP_PY), "-m", "white_t_mockup", str(design_path), str(out_path)]
    if preset_key:
        cmd += ["--preset", preset_key]
    else:
        cmd += ["--template", str(fp)]
    cmd += [
        "--final-w", str(int(fields["final_w"])),
        "--final-h", str(int(fields["final_h"])),
        "--rotate", str(fields["rotation"]),
        "--effective-top-y", str(int(fields["top_y"])),
        "--effective-center-x", str(int(fields["center_x"])),
        "--disp-strength", "12",
        "--shadow-opacity", "0.22",
        "--highlight-opacity", "0.22",
    ]
    if tpl_dir:
        cmd += ["--tpl-dir", str(tpl_dir)]
    cmd += ["--for-black-shirt" if color == "black" else "--for-white-shirt"]
    if occluder:
        cmd += ["--occluder", str(occluder)]

    dbg = MOCKUP_OUT / "_mockup_run.log"
    try:
        with open(dbg, "w", encoding="utf-8") as f:
            f.write("CMD: " + " ".join(cmd) + "\n")
            f.write("CWD: " + str(MOCKUP_ROOT) + "\n")
            f.write("PYTHONPATH: " + env["PYTHONPATH"] + "\n")
            f.write("OPENCV_DISABLE_THREADING: " + env.get("OPENCV_DISABLE_THREADING", "") + "\n")
    except Exception:
        pass

    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    last = None
    import time as _t
    for attempt in range(1, 4):
        out_log = MOCKUP_OUT / f"_mockup_stdout_{attempt}.log"
        err_log = MOCKUP_OUT / f"_mockup_stderr_{attempt}.log"
        try:
            with open(out_log, "w", encoding="utf-8", errors="replace") as of, \
                 open(err_log, "w", encoding="utf-8", errors="replace") as ef:
                r = subprocess.run(
                    cmd, cwd=str(MOCKUP_ROOT), env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=of, stderr=ef,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    startupinfo=startupinfo,
                )
        except Exception as e:
            import traceback as _tb
            r = type("_R", (), {"returncode": -1, "stdout": "",
                                "stderr": f"[bridge] 启动异常: {_tb.format_exc()}"})()
        try:
            r.stdout = out_log.read_text(encoding="utf-8", errors="replace")
        except Exception:
            r.stdout = ""
        try:
            r.stderr = err_log.read_text(encoding="utf-8", errors="replace")
        except Exception:
            r.stderr = ""
        try:
            with open(dbg, "a", encoding="utf-8") as f:
                f.write(f"attempt {attempt}: rc={r.returncode} stderr={r.stderr[:200]}\n")
        except Exception:
            pass
        last = r
        if r.returncode == 0:
            break
        _t.sleep(2)  # cv2 偶发段错误，重试常能成功
    return last


@app.route('/api/mockup', methods=['POST'])
def api_mockup():
    """贴图：自动读取胚衣5字段 + 遮罩 + 扭曲，精准贴入。

    入参（multipart）：
      design         : 贴图素材文件（建议透明底 PNG；白底图可勾选 auto_remove_bg）
      template       : 胚衣标识，支持 "分类/文件名"（如 W白/白W3.jpg）或款名；
                        多个用逗号分隔即批量贴图
      auto_remove_bg : '1' 表示把白底设计图去背
    """
    try:
        design = request.files.get('design')
        if not design:
            return jsonify({'ok': False, 'error': '未收到贴图素材'}), 400
        templates = (request.form.get('template') or '').strip()
        if not templates:
            return jsonify({'ok': False, 'error': '未指定胚衣'}), 400
        names = [t.strip() for t in templates.split(',') if t.strip()]
        auto_bg = request.form.get('auto_remove_bg') == '1'

        MOCKUP_OUT.mkdir(parents=True, exist_ok=True)
        des_path = MOCKUP_OUT / f"_des_{datetime.now().strftime('%H%M%S%f')}.png"
        design.save(str(des_path))
        if auto_bg:
            _remove_white_bg(des_path)

        presets = _load_presets()
        results = []
        for t in names:
            if '/' in t:
                category, name = t.split('/', 1)
            else:
                category, name = _find_category_for_stem(t)
            if not category or category not in PEIYI_CATEGORIES:
                results.append({'template': t, 'ok': False, 'error': '未找到该胚衣（请检查素材库分类）'})
                continue
            fp, stem, color = _resolve_peiyi_embryo(category, name)
            if not fp.exists():
                results.append({'template': t, 'ok': False, 'error': f'素材库图片不存在: {fp.name}'})
                continue
            fields = _embryo_fields(category, name, presets)
            if not fields['final_w'] or not fields['final_h']:
                results.append({'template': t, 'ok': False,
                                'error': '该胚衣缺少缩放后宽/高（请在素材库填写，或检查胚衣参数表）'})
                continue
            pkey = _preset_key_for_stem(stem, presets)
            tpl_dir = _ensure_tpl(stem, fp)
            occ = _ensure_occluder(fp, category)
            out_path = MOCKUP_OUT / f"{stem}_{datetime.now().strftime('%H%M%S%f')}.jpg"
            r = _run_white_t_mockup(des_path, out_path, pkey, fp, fields, tpl_dir, color, occ)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or '')[-600:]
                results.append({'template': t, 'ok': False, 'error': err})
                continue
            results.append({
                'template': t, 'ok': True,
                'url': f"/api/mockup/result/{out_path.name}",
                'fields': fields, 'color': color,
                'used_tpl': tpl_dir is not None, 'used_occluder': occ is not None,
                'preset': pkey,
            })
        return jsonify({'ok': any(x['ok'] for x in results), 'results': results})
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}', 'trace': _tb.format_exc()[-1500:]}), 500


@app.route('/api/mockup/result/<path:filename>')
def api_mockup_result(filename):
    safe = os.path.basename(filename)
    fp = MOCKUP_OUT / safe
    if not fp.exists() or fp.resolve().parent != MOCKUP_OUT.resolve():
        abort(404)
    return send_file(str(fp), mimetype='image/jpeg', max_age=0)


# ============================================================================
# 后台生图任务
# ============================================================================

def _run_generation(selected_files: list, task_id: str, reuse_dx: str = None):
    """后台执行 Lovart 管线"""
    global task_state
    start_ts = datetime.now()

    reg = load_registry()
    reg = ensure_registry_v4(reg)

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
                uid_map[fname] = uid

        save_registry(reg)
        log(f"已分配 {len(uid_map)} 个 UID，{len(group_map)} 个 group_id")

        # ── 1b. 写入 UID manifest ─────────────────
        try:
            manifest = {"version": 1, "generated_at": datetime.now().isoformat(), "items": {}}
            for fname, uid in uid_map.items():
                gid = None
                role = ""
                for g in matched:
                    for img in g["images"]:
                        if img["filename"] == fname:
                            gid = group_map[g["group_number"]]
                            role = img["suffix"]
                            break
                    if gid is not None:
                        break
                manifest["items"][fname] = {
                    "uid": uid,
                    "group_id": gid,
                    "role": role,
                }
            UID_MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"已写入 UID manifest: {UID_MANIFEST_FILE.name}")
        except Exception as e:
            log(f"WARN: UID manifest 写入失败: {e}")

        # INBOX sidecar：wb_meta 以 DX 为根目录，INBOX 文件无法推断 DX，跳过。
        # 元数据已通过 UID manifest 传给 Lovart，不影响溯源。

            # ── 2. 运行 Lovart 管线（不移走未选中文件，Lovart 自带 SHA256 去重） ──
        task_state["status"] = "running"
        task_state["progress"] = "正在运行 Lovart 生图管线..."
        log("启动 Lovart 管线...")
        _save_state()

        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH
        env["LOVART_INSECURE_SSL"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        env["BRIDGE_UID_MANIFEST"] = str(UID_MANIFEST_FILE)
        # 强制生成：用户点“开始 Lovart 生图”即明确要生图，忽略去重
        # （原图编号会复用, 每批从1开始, 否则正常生图会被旧记录误拦）
        env["LOVART_FORCE"] = "1"
        # 重新生图时使用统一提示词文件，并传入目标 DX 复用映射
        if task_id and task_id.startswith("TASK_REGEN_"):
            prompt_path = LOVART_DIR / "config" / "POD AI VIRAL FACTORY v3.md"
            if prompt_path.exists():
                env["LOVART_PROMPT_FILE"] = str(prompt_path)
            # reuse_dx 可以是单个 DX（str）或 filename -> dx 映射（dict）
            if reuse_dx:
                if isinstance(reuse_dx, dict):
                    regen_map = {fname: reuse_dx[fname] for fname in selected_files if fname in reuse_dx}
                else:
                    regen_map = {fname: reuse_dx for fname in selected_files}
                if regen_map:
                    env["LOVART_REGEN_DX_MAP"] = json.dumps(regen_map)

        proc = subprocess.Popen(
            [get_python(), "run_official_v53.py"],
            cwd=str(LOVART_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            env=env,
        )

        # 逐行读取输出，更新进度（完整透传 Lovart 输出，避免“静默完成”看不出原因）
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            log(line[:400])
            task_state["progress"] = line[:200]

        proc.wait()

        # ── 4. 更新 registry ────────────────────────────────────
        log("更新注册表，建立溯源关系...")
        reg = load_registry()
        reg = ensure_registry_v4(reg)

        # 扫描 Lovart 生成的 DX 文件夹，关联 group + 建立溯源
        if PROJECTS_DIR.exists():
            cutoff = start_ts.timestamp()
            for d in sorted(os.listdir(PROJECTS_DIR)):
                if not d.startswith('DX'):
                    continue
                ai_dir = PROJECTS_DIR / d / "01_AI"
                if not ai_dir.exists():
                    continue

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

                for src in sm.get("sources", []):
                    src_id = src.get("src_id", "")
                    role = src.get("role", "")
                    target_file = src.get("file", "")
                    uid = src.get("uid", "")
                    gid = src.get("group_id", "")

                    # 优先按 uid 匹配注册表；否则回退 role+group_id
                    img_info = None
                    if uid:
                        md5_key = reg.get("uid_index", {}).get(uid, "")
                        img_info = reg.get("images", {}).get(md5_key)
                    if not img_info and gid and role:
                        for mk, info in reg.get("images", {}).items():
                            if info.get("role") == role and info.get("group_id") == gid:
                                img_info = info
                                break
                    if not img_info:
                        for mk, info in reg.get("images", {}).items():
                            if info.get("role") == role and \
                               info.get("group_id") in group_map.values():
                                img_info = info
                                break

                    if img_info:
                        # 更新注册表
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

                        # 写入 AI sidecar 与 uid_map
                        if wb_meta:
                            try:
                                ai_path = PROJECTS_DIR / d / "01_AI" / target_file
                                if ai_path.exists():
                                    inbox_name = img_info.get("inbox_original_name", "")
                                    wb_meta.register_ai(
                                        ai_path,
                                        uid=img_info.get("uid", uid),
                                        group_id=img_info.get("group_id", gid),
                                        role=role,
                                        parent_uid=img_info.get("uid", uid),
                                        inbox_file=f"01_INBOX/{inbox_name}" if inbox_name else None,
                                    )
                            except Exception as e:
                                log(f"WARN: AI sidecar 写入失败 {target_file}: {e}")

        # 建立溯源关系（AI 图 → INBOX 原图）
        lovart_reg_path = Path("D:/Semems WB/WB_REGISTRY/registry.json")
        lovart_reg = {}
        if lovart_reg_path.exists():
            try:
                with open(lovart_reg_path, 'r', encoding='utf-8') as f:
                    lovart_reg = json.load(f)
            except Exception:
                pass

        for md5_key, img_info in reg.get("images", {}).items():
            if img_info.get("source_type") or not img_info.get("group_id"):
                continue
            gid = img_info.get("group_id")
            if gid not in group_map.values():
                continue
            # 这张 AI 图刚生成，找它的 INBOX 源图
            inbox_name = img_info.get("inbox_original_name", "")
            src_md5 = reg.get("name_index", {}).get(inbox_name, "")
            if src_md5 and src_md5 in reg.get("images", {}):
                _register_provenance(reg, md5_key, src_md5, "ai_gen")

        save_registry(reg)
        log("注册表更新完成（含溯源关系）")

        # ── 6. 完成 ─────────────────────────────────────────────
        task_state["status"] = "completed"
        task_state["completed_at"] = datetime.now().isoformat()
        task_state["progress"] = f"任务结束：处理 {len(matched)} 组 / {len(uid_map)} 张"
        if proc.returncode != 0:
            task_state["progress"] += f" (管线退出码: {proc.returncode})"
        log(f"⏹ 任务 {task_id} 结束 (处理 {len(uid_map)} 张, {len(matched)} 组)")
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
    parser = argparse.ArgumentParser(description="Y2 Bridge Server")
    parser.add_argument("--port", type=int, default=8765, help="Bridge 服务端口 (默认 8765)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址 (默认 127.0.0.1)")
    args = parser.parse_args()

    # 恢复上次的任务状态（如果是已完成/错误状态）
    _load_state()

    # 自动大写 INBOX 文件名后缀
    renamed = auto_uppercase_inbox()
    if renamed:
        # 重新扫描分组（更新 registry 的 name_index）
        reg = load_registry()
        reg = ensure_registry_v4(reg)
        for fname in os.listdir(INBOX_DIR):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not fname.startswith('_'):
                reg["name_index"][fname] = ""
        save_registry(reg)

    print("╔══════════════════════════════════════════╗")
    print("║   Y2 Bridge Server v2.3.22              ║")
    if renamed:
        print(f"║   AutoUppercase: {renamed} files          ║")
    print("║                                         ║")
    print(f"║   INBOX:   {INBOX_DIR}")
    print(f"║   Output:  {PROJECTS_DIR}")
    print(f"║   Lovart:  {LOVART_SCRIPT}")
    print("║                                         ║")
    print(f"║   Open:  http://{args.host}:{args.port}")
    print("║   AutoScan: every 60s                   ║")
    print("╚══════════════════════════════════════════╝")

    # 后台自动溯源扫描（每 60 秒）
    def _auto_scan_loop():
        while True:
            time.sleep(60)
            try:
                n = scan_provenance()
                if n:
                    print(f"  [AutoScan] 新增 {n} 条血缘关系", flush=True)
            except Exception:
                pass

    t = threading.Thread(target=_auto_scan_loop, daemon=True)
    t.start()

    # 后台守护 check_rem.py（端口 8766），让「去背预览」点击即开
    t2 = threading.Thread(target=_check_rem_daemon, daemon=True)
    t2.start()

    # 写入 PID 文件，供启动脚本优雅停止服务
    pid_path = Path(__file__).resolve().parent / "bridge.pid"
    try:
        pid_path.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass

    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    finally:
        try:
            if pid_path.exists():
                pid_path.unlink()
        except Exception:
            pass
