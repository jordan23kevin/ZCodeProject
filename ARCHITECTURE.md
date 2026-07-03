# Y2 系统架构文档 v2.3.1

> 工程类型: 图像生产血缘数据库 + 控制面板 + 贴图成品流水线 + AI 生图对比复审
> 遵循: B+ 四层血缘闭环架构

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Chrome 浏览器                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ lovart_control   │    │ AI 生图对比     │    │ AI vs 去背 vs   │  │
│  │ (端口 8765)      │    │ /ai-review      │    │ 贴图成品 对比   │  │
│  │                  │    │ (端口 8765)     │    │ (端口 8766)     │  │
│  └────────┬────────┘    └────────┬───────┘    └────────┬────────┘  │
└───────────┼──────────────────────┼─────────────────────┼───────────┘
            │ HTTP/JSON            │ HTTP/JSON           │ HTTP/JSON
            ▼                      ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────────────────────────┐
│   lovart_bridge.py   │  │   lovart_bridge.py   │  │   check_rem.py v2.2.0                 │
│   v2.3.0 (Flask      │  │   重新生图 API:      │  │   (预览 + 去背 + 贴图触发 + 批量反相) │
│       Server)        │  │   /api/ai-review/*   │  │   check_rem.js v2.2.0 (独立JS)        │
│                      │  │   /api/ai-review/    │  │                                        │
│   API端点:           │  │       regenerate     │  │   API端点:                             │
│   /api/inbox         │  │   /api/ai-review/    │  │   /thumb, /original                    │
│   /api/generate      │  │       regenerate-    │  │   /rembg, /batch-rembg                │
│   /api/provenance    │  │       batch          │  │   /invert-rem, /upscale-rem           │
│   /api/lineage/*     │  │                      │  │   /ps-sticker, /ps-batch              │
│   /api/projects      │  │                      │  │   /refresh-thumb, /check_rem.js       │
│   /upload            │  │                      │  │                                        │
│   /api/upload/*      │  │                      │  │                                        │
│   /api/batch-upload  │  │                      │  │                                        │
│   ...                │  │                      │  │                                        │
└────────┬─────────────┘  └────────┬─────────────┘  └──────────┬─────────────────────────────┘
         │                              │
         │    POST /api/lineage/register│   子进程调用 (最小化窗口)
         │    (+ uid/group_id)          ▼
         │                 ┌────────────────────────────────────────┐
         │                 │      PS 贴图流水线（E:\Claude code\ps） │
         │                 │  ┌────────────────────────────────────┐  │
         │                 │  │ 1. process_black.py  v2.2          │  │
         │                 │  │    黑T专用贴图 + BW合成              │  │
         │                 │  ├────────────────────────────────────┤  │
         │                 │  │ 2. ps_sticker_one.py →             │  │
         │                 │  │    wb_sticker_ps.py v2.2 通用白T贴图│  │
         │                 │  │    （检测到黑B/W/BW 时跳过黑T输出） │  │
         │                 │  ├────────────────────────────────────┤  │
         │                 │  │ 3. ps_batch_one.py →               │  │
         │                 │  │    ps_batch.py v2.2 合成 BW         │  │
         │                 │  └────────────────────────────────────┘  │
         │                 └────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     UID / group_id 元数据层                          │
│  D:\Semems WB\05_META\DXxxxx\uid_map.json                            │
│    ├── groups:    { group_id → [uid, ...] }                          │
│    ├── images:    { uid → { stage, role, file, md5, parent_uid } }   │
│    └── md5_index: { md5 → uid }                                      │
│                                                                      │
│  D:\Semems WB\05_META\DXxxxx\sidecars\UID_xxx.meta.json              │
│    └── { uid, group_id, stage, role, md5, parent_uid, source_file }  │
│                                                                      │
│  01_AI / 02_REM_BG / 03_UPLOAD 只放图片，不放元数据文档              │
│                                                                      │
│  共享模块: C:\Users\Administrator\ZCodeProject\lib\wb_meta.py      │
│  （同步部署到 WB去背、PS、wb上款各项目根目录）                       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Registry (数据核心)                         │
│  D:\Semems WB\.image_registry.json  (v4)  ← Bridge 唯一写入         │
│    ├── images: { MD5 → entry }                                       │
│    │     ├── source_md5, source_type (溯源)                           │
│    │     ├── derived_md5s, lineage_status                            │
│    │     ├── root_md5, root_name (原始来源)                           │
│    │     └── uid, group_id, events                                   │
│    ├── groups, uid_index, provenance.tree                            │
│    └── version: 4                                                    │
│                                                                      │
│  D:\Semems WB\.wb_rembg_registry.json  ← WB去背 独立写入            │
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

### 日期分类按 DX 文件夹建立日期（v2.3.1）

**问题**: 原系统按 `01_AI` / `02_REM_BG` / `03_UPLOAD` 内文件的最新 `mtime` 判断款号所属日期。
重新生图、去背、贴图等操作会更新文件 `mtime`，导致款号被错误归到最新日期。

**解决方案**:
- 所有页面的日期分类统一使用 `DXxxxx` 文件夹的 `st_ctime`（建立时间）。
- 实现位置：`lovart_bridge.py::_dx_dir_date()`、`check_rem.py::scan_projects()`。
- 移除 `_load_upload_date_map()`，上款记录仅用于「已上款 / 未上款」状态判断。

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

### UID/group_id 全链路溯源（v2.2.0）

**问题**: 原系统通过文件名 stem 匹配去背图与 AI 图（`DXxxxx_B.png` ↔ `DXxxxx_B_cut.png`），一旦重命名或出现重名就会断链。

**解决方案**:
1. **INBOX 阶段**：Bridge 为每张原图分配 `uid` + `group_id`，写入 INBOX sidecar 和 `.generation_uid_manifest.json`。
2. **AI 阶段**：Lovart 读取 manifest，把 `uid`/`group_id` 写回 `source_map.json`，并为 AI 图生成 sidecar。
3. **去背/贴图/BW 阶段**：各脚本读取输入图 sidecar，把输出图注册到同一 `uid`/`group_id`，写入自己的 sidecar。
4. **展示阶段**：`check_rem.js` 按 `group_id` 聚合显示，不再依赖文件名解析。

**数据文件**（统一放在 `D:\Semems WB\05_META\`，与图片分离）:
- `05_META/DXxxxx/uid_map.json`：该 DX 下所有图片的 UID 关系总表。
  - `md5_index: {md5 → uid}`：以内容 MD5 为主键，图片改名/移动/复制后仍能找到。
  - `images: {uid → entry}`：每个条目包含 `md5`、`file`、`stage`、`role`、`group_id`。
- `05_META/DXxxxx/sidecars/UID_xxx.meta.json`：按 UID 命名的 sidecar，不依赖原文件名。

**原则**:
- `01_AI` / `02_REM_BG` / `03_UPLOAD` 只放图片，不放元数据文档。
- 所有元数据文档专门放 `05_META`，以后溯源去 `05_META` 找即可。
- **MD5 为主键**：即使图片被改名、移动、复制，只要内容不变，就能通过 `md5_index` 找到同一组关系。

**共享模块**: `wb_meta.py` 位于 Bridge `lib/` 目录，并同步部署到 WB去背/PS/wb上款各项目根目录，统一 sidecar/uid_map 操作。

**迁移脚本**: `tools/migrate_uid_map.py` 可一键为所有旧 DX 项目重建元数据到 `05_META`。

**迁移/对账**:
- 旧项目无 sidecar 时，自动调用 `wb_meta.migrate_dx(dx_dir)` 基于 `source_map.json` + 文件名推断补录到 `05_META`。
- 图片改名/移动后，`wb_meta.reconcile_dx(dx_dir)` 会扫描实际文件，用 MD5 修正 uid_map 里的路径。

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

完整复现/回滚步骤见 [`REPRODUCIBILITY.md`](./REPRODUCIBILITY.md)。

要点：
- 两个主仓库：`ZCodeProject`（Bridge / 控制台）和 `lovart-official`（生图管线）
- 当前 Tag：`ZCodeProject v2.3.0`、`lovart-official v6.1`
- Python 依赖：`flask`, `Pillow`, `requests`, `pywin32`, `pythoncom`, `numpy`
- Photoshop 路径：`D:\Program Files\Adobe Photoshop 2025 v26.0\Adobe Photoshop 2025\Photoshop.exe`
- 项目根目录：`D:\Semems WB\02_PROJECTS`
- 提示词文件：`E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
