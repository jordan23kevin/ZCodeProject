# Lovart-WB 系统架构文档 v2.1.7

> 工程类型: 图像生产血缘数据库 + 控制面板 + 贴图成品流水线
> 遵循: B+ 四层血缘闭环架构

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Chrome 浏览器                                │
│  ┌─────────────────┐    ┌───────────────────────────────────────┐   │
│  │ lovart_control   │    │ AI vs 去背 vs 贴图成品 对比预览       │   │
│  │ (端口 8765)      │    │ (端口 8766 / check_rem.py)            │   │
│  └────────┬────────┘    └──────────────┬──────────────────────────┘   │
└───────────┼────────────────────────────┼──────────────────────────────┘
            │ HTTP/JSON                   │ HTTP/JSON
            ▼                             ▼
┌──────────────────────┐     ┌────────────────────────────────────────┐
│   lovart_bridge.py    │     │   check_rem.py v2.1.5                 │
│   v2.1.7 (Flask Server)│    │   (预览 + 去背 + 贴图触发 + 批量反相) │
│                       │     │   check_rem.js v2.1.5 (独立JS)        │
│   API端点:            │     │                                        │
│   /api/inbox          │     │   API端点:                             │
│   /api/generate       │     │   /thumb, /original                    │
│   /api/provenance     │     │   /rembg, /batch-rembg                │
│   /api/lineage/*      │     │   /invert-rem, /upscale-rem           │
│   /api/projects       │     │   /ps-sticker, /ps-batch              │
│   /upload             │     │   /refresh-thumb, /check_rem.js       │
│   /api/upload/*       │     │                                        │
│   /api/batch-upload   │     │                                        │
│   ...                 │     │                                        │
└────────┬─────────────┘     └──────────┬─────────────────────────────┘
         │                              │
         │    POST /api/lineage/register│   子进程调用 (最小化窗口)
         │                              ▼
         │                 ┌────────────────────────────────────────┐
         │                 │      PS 贴图流水线（E:\Claude code\ps） │
         │                 │  ┌────────────────────────────────────┐  │
         │                 │  │ 1. process_black.py  v2.1          │  │
         │                 │  │    黑T专用贴图 + BW合成              │  │
         │                 │  ├────────────────────────────────────┤  │
         │                 │  │ 2. ps_sticker_one.py →             │  │
         │                 │  │    wb_sticker_ps.py v2.1 通用白T贴图│  │
         │                 │  │    （检测到黑B/W/BW 时跳过黑T输出） │  │
         │                 │  ├────────────────────────────────────┤  │
         │                 │  │ 3. ps_batch_one.py →               │  │
         │                 │  │    ps_batch.py v1.3.0 合成 BW       │  │
         │                 │  └────────────────────────────────────┘  │
         │                 └────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Registry (数据核心)                         │
│  D:\Semems WB\.image_registry.json  (v4)                            │
│    ├── images: { MD5 → entry }                                       │
│    │     ├── source_md5, source_type (溯源)                           │
│    │     ├── derived_md5s, lineage_status                            │
│    │     ├── root_md5, root_name (原始来源)                           │
│    │     └── uid, group_id, events                                   │
│    ├── groups, uid_index, provenance.tree                            │
│    └── version: 4                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## 关键技术决策

### JS 独立文件（v2.0 关键改进）

check_rem.py 的 HTML 模板使用 Python f-string 生成，JS 代码中的 `{}` 与 f-string 语法冲突。
**解决方案**: 将 JavaScript 提取到独立 `check_rem.js` 文件，通过 `<script src="/check_rem.js">` 引入。
这彻底消除了 f-string 转义问题，使 JS 代码可独立开发和调试。

### 贴图流水线闭环（v2.1 关键改进）

用户之前需要手动「贴图」→「BW合成」两步，且黑T容易用错通用图。
**解决方案**: `/ps-sticker` 统一调度三段脚本：

1. `process_black.py` — 若存在 `DX_黑B/W/BW_cut.png`，先做黑T贴图+BW合成
2. `wb_sticker_ps.py` — 通用 B/W/BW 贴图；若检测到对应黑版文件，自动跳过黑T输出
3. `ps_batch.py` — 用已贴好的 B/W 合成最终 BW

前端「贴图」与「批量贴图」均调用完整流水线，一步出成品。

### 黑版专用优先策略

`02_REM_BG` 中若存在黑版专用文件，黑T贴图必须用它；没有才 fallback 到通用 `_cut.png`。
实现位置：`wb_sticker_ps.py::black_counterpart()` + `process_black.py`。

### 上款页面（v2.1.4）

原 Bridge 内的 PS贴图控制台使用率低，且贴图功能已在 `check_rem.py` 中通过 `/ps-sticker` 提供。
**解决方案**: 将 `/ps-sticker` 控制台替换为 `/upload` 上款页面，直接展示 `03_UPLOAD` 成品，
提供勾选 + 批量上传入口，后续可对接 `LOVART_UPLOAD_SCRIPT` 环境变量指向的外部上款脚本。

### 后台静默运行

Photoshop COM 默认 `Visible=True`，`WScript.Shell.Run` 默认前台打开，会打断用户。
**解决方案**:
- `psApp.Visible = False` 在 `wb_sticker_ps.py` / `process_black.py` / `ps_batch.py` 中统一设置
- `ps_batch.py::ps_open_both()` 使用 `shell.Run(..., 7, False)`（`SW_SHOWMINNOACTIVE`）
- `check_rem.py::run_minimized()` 对 Python 子进程使用 `STARTUPINFO` + `SW_SHOWMINNOACTIVE`
- `lovart_bridge.py::run_minimized()` 统一处理 Bridge 内启动的 `check_rem.py` / `ps_sticker_one.py` / `ps_batch_one.py`，点击控制面板按钮后窗口最小化到任务栏

### 悬停预览智能定位

原预览固定 `right+8` / `top`，当缩略图在屏幕下方时预览被截断。
**解决方案**: JS 中计算 `window.innerWidth/Height`，右边界溢出则放左侧，下边界溢出则向上对齐到 `window.innerHeight - previewH - 8`。

### 血缘引擎（B+ 四层架构）

```
Hook(实时) → Bridge写入 → Scanner(推断) → Reconciler(修复)
```

- **confirmed**: Hook 实时记录（去背成功后自动 POST）
- **inferred**: Scanner 文件名 stem 推断
- **missing**: 断链待修复

### 关键经验总结

| 问题 | 教训 | 预防 |
|------|------|------|
| f-string 嵌 JS | `{` `}` 转义极易出错 | JS 独立文件 |
| 文件代码重复 | sed/编辑操作导致重复 | 每次改完检查重复 |
| 缓存问题 | `__pycache__` 残留旧编译 | 删缓存后再测试 |
| 多行字符串 | JS 单引号不能跨行 | 始终用 `\n` 转义 |
| 黑T贴图用错源图 | 通用图与黑版图同名 | 文件名加入 `_黑` 前缀并优先检测 |
| PS 窗口抢焦点 | COM 默认 Visible=True | 启动后立即 `Visible = False` |

## 部署

```bash
pip install flask Pillow requests
# 启动 Bridge
cd C:\Users\Administrator\ZCodeProject
python lovart_bridge.py
# 或双击 D:\Semems WB\01_INBOX\lovart_bridge.bat

# 启动去背预览
cd D:\Semems WB\04_OS\engine
python check_rem.py

# 打开 http://127.0.0.1:8765 或 http://127.0.0.1:8766
```

## 可复现性清单

- 所有 Python 脚本依赖：`flask`, `Pillow`, `requests`, `win32com`, `pythoncom`, `numpy`
- Photoshop 路径：`D:\Program Files\Adobe Photoshop 2025 v26.0\Adobe Photoshop 2025\Photoshop.exe`
- 项目根目录：`D:\Semems WB\02_PROJECTS`
- 三个仓库独立提交，Tag 为 `v2.1`
