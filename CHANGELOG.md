# Y2 一体化控制系统 — 更新日志

## v2.3.21 (2026-07-06) — 修复上款缩略图黑白错位 + 文件夹前台打开

### 🐛 修复

- **修复 WB 上款页面缩略图黑白错位**
  - 根因：`_get_upload_thumb` / `_get_ai_thumb` 使用 `re.sub(r'[^A-Za-z0-9_.-]', '_', filename)` 生成缓存文件名，
    把文件名中的中文（白/黑）统一替换成下划线，导致 `DX_B_白T.jpg` 与 `DX_B_黑T.jpg` 映射到同一个缓存文件。
  - 解决：safe_name 只替换 Windows 文件系统非法字符（`\ / * ? : " < > |`），保留中文；
    同时清空 `D:\Semems WB\_upload_thumbs` 与 `_ai_review_thumbs` 中的旧错误缓存，重新加载页面时自动重建正确缩略图。
  - 影响文件：`lovart_bridge.py`

- **修复点击上款图片/回收站按钮后文件夹不自动前台弹出**
  - 根因：`os.startfile` 打开已存在的资源管理器窗口时，Windows 不会强制激活窗口，导致窗口只在任务栏闪烁。
  - 解决：新增 `_open_folder_front()` 辅助函数，先用 `explorer.exe` 打开文件夹，再用 `win32gui` 查找对应的
    `CabinetWClass` 窗口，调用 `ShowWindow(SW_RESTORE)` + `SetForegroundWindow()` 强制置顶。
  - 影响文件：`lovart_bridge.py`

### 📚 文档与版本

- 版本号统一升级到 v2.3.21：`lovart_bridge.py`、`lovart_bridge.bat`、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md`、`REPRODUCIBILITY.md`。

---

## v2.3.20 (2026-07-06) — 集成 Temu 核价控制台并修复长页滚动回顶

### ✨ 新增

- **Temu 核价页面 (`/pricing`)**
  - 新增 `pricing.html` 前端页面，提供「完整自动核价」「仅核价不提交」「继续提交」「重试指定页」「导出结果」功能。
  - 新增 `/api/pricing/*` 后端端点：启动核价、停止、状态轮询、导出结果、下载 Excel、发送 "好了" 信号。
  - Bridge 通过子进程调用 `E:/Claude code/Temu自动化/核价/hengjia.py` 执行实际核价逻辑。
  - 核价结果输出到 `C:/Users/Administrator/Desktop/核价档案`，支持下载 `.xlsx`。

### 🔧 联动

- **联动 `temu-hengjia-engine v5.2.1`**
  - 修复长页核价时抽屉滚动回顶导致无法完成的问题。
  - 根因：`utils/js_helpers.py` 中 `__scanAndCheckPage` / `__fillPage` 每次被调用都执行 `sc.scrollTop = 0`。
  - 解决：移除 JS 内部重置，由 `core/engine.py` 在 `check_prices()` / `fill_prices()` 入口统一重置一次；后续循环调用从当前位置继续，直到真正到底。

### 📚 文档与版本

- 版本号统一升级到 v2.3.20：`lovart_bridge.py`、`lovart_bridge.bat`、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md`、`REPRODUCIBILITY.md`。

---

## v2.3.18 (2026-07-05) — WB 上款页面新增「复制未上款」按钮

### 🎨 UI

- **WB 上款页面 (`upload.html`) 新增「📋 复制未上款」按钮**
  - 一键复制当前未上款列表中的所有 DX 款号到剪贴板。
  - 复制内容按逗号分隔，便于粘贴到 Bridge 勾选框或其他系统。
  - 兼容 `navigator.clipboard` API，并提供 `document.execCommand('copy')` 兜底方案。
  - 支持当前筛选状态：若用户选择了日期或输入了搜索词，仅复制筛选后可见的未上款款号。

---

## v2.3.19 (2026-07-05) — 修复批量上款时弹出黑色控制台窗口

### 🐛 修复

- **修复批量上款 / 刷新在线已上款时弹出黑色控制台窗口**
  - 根因：`run_minimized()` 统一使用 `CREATE_NEW_CONSOLE` 启动子进程，`wb_listing.py` / `check_online_listed.py` 运行时都会弹出一个最小化的 CMD 黑窗。
  - 解决：`run_minimized()` 新增 `no_console` 参数；调用 `wb_listing.py` 与 `check_online_listed.py` 时传 `no_console=True`。
  - 使用 `CREATE_NO_WINDOW` 替代 `CREATE_NEW_CONSOLE`，并把 stdout/stderr 重定向到 `DEVNULL`。
  - 这两个脚本内部已把日志写入 `D:\Semems WB\_debug`，不依赖控制台窗口输出。

---

## v2.3.17 (2026-07-05) — Bridge 面板限制窗口大小 + 同步 wb上款 v1.3.20

### 🔧 联动

- **同步 wb上款 v1.3.20**
  - Edge 最小化策略联动：自动化运行期间 Edge 默认最小化到任务栏，减少视觉干扰。

### 🎨 UI

- **Bridge 面板限制窗口大小**
  - `lovart_bridge.bat` 启动 Chrome 时增加 `--window-size=1400,900`。
  - 避免 Bridge 面板默认最大化占据整个屏幕。

---

## v2.3.16 (2026-07-05) — 同步 wb上款 v1.3.19

### 🔧 联动

- **同步 wb上款 v1.3.19**
  - Edge 可见性配置联动：默认 `WB_EDGE_VISIBLE=1`，上款窗口默认可见。
  - 分类选择精确匹配联动：按当前月份精确匹配商品分类，避免跨月份误选。

---

## v2.3.15 (2026-07-05) — 修复单张去背无输出 + 批量去背 BW 过滤污染

### 🐛 修复

- **修复 DX0339_W 等单张去背后 02_REM_BG 无输出**
  - 根因：美图秀秀保存对话框路径未生效时，`_副本.png` 会落到 `WB_ROOT/_temp_rembg/save`，而 `check_rem.py` 只从 `TEMP_REMBG/{DX}/02_REM_BG` 收集 `_cut.png`，导致“保存了但不见图”。
  - 解决：
    - `engine/check_rem.py v2.2.6` 新增 `_collect_rembg_results()`，从 `TEMP_REMBG/{DX}/02_REM_BG`、`WB_ROOT/_temp_rembg/save`、`WB_ROOT/_temp_rembg/archive` 三个位置扫描 `_cut.png` / `_副本.png`。
    - 收集时自动把 `_副本.png` 改名为 `_cut.png` 并移动到真实 `02_REM_BG`。
    - `rembg_one_file` / `batch_rembg` 暂存时额外复制 `source_map.json` 与原始配对文件（如 `1B.png` / `1W.png`），让美图 `precheck_pairs` 正确识别 B/W 角色与配对完整性。

- **修复 `/batch-rembg` 的 BW 过滤跨 DX 污染 bug**
  - 根因：原实现用全局 `dx_files` 判断是否含 BW，导致前一个有 BW 的款会污染后续所有款，使后续款的 B/W 被错误跳过。
  - 解决：改为每个 DX 独立判断，只跳过该 DX 自己的 B/W。

- **增强 `_rembg_worker.py` 可观测性**
  - 工作进程输出重定向到 `D:\Semems WB\_debug\_rembg_worker_YYYYMMDD_HHMMSS.log`，方便定位“美图运行了但没出图”的问题。

---

## v2.3.14 (2026-07-04) — PS 批量贴图队列化 + 超时兜底

### 🐛 修复

- **修复批量贴图处理到一半停止**
  - 根因：前端 `batchSticker()` 逐个发送 `/ps-sticker` 并等待响应；某款 PS 脚本卡住时 HTTP 请求一直挂起，前端无法继续发后续请求。
  - 解决：
    - `engine/check_rem.py v2.2.5` 新增 PS 贴图任务队列 + 工作线程，单张/批量统一串行执行。
    - `/ps-sticker` 改为入队即返回；新增 `/sticker-status` 端点供前端轮询。
    - 每步 PS 脚本（黑T贴图 / 通用贴图 / BW合成）增加 5 分钟超时，超时强制终止并继续下一款。
    - 前端 `batchSticker()` 与 `psSticker()` 改为入队后轮询，不再被挂起请求阻塞。

---

## v2.3.13 (2026-07-04) — 修复单张去背失效

### 🐛 修复

- **补全缺失的 `engine/_rembg_worker.py`**
  - 单张「重新去背」按钮调用 `/rembg` 端点后，由 `_rembg_worker.py` 在后台驱动美图秀秀。
  - 之前该文件缺失，导致点击去背后锁文件写入但工作进程未启动，去背图不会生成。

- **修复 `rembg_one_file` 配对预检失败导致跳过**
  - 暂存目录现在会放入同 DX 的所有生成图，让美图脚本的 `precheck_pairs` 看到完整 B/W 配对。
  - 只 untrack 目标图 MD5，避免同 DX 其他已处理图被重复去背。

---

## v2.3.12 (2026-07-04) — 反相与贴图解耦

### 🔧 调整

- **AI 去背 贴图 OS 反相不再自动贴图（`engine/check_rem.py v2.2.3`）**
  - 单张「反相」与「批量反相」仅生成黑版专用去背图（`DX_黑B/W/BW_cut.png`）。
  - 反相完成后不再自动调用贴图流水线（黑T专用 → 通用贴图 → BW 合成）。
  - 贴图由用户单独点击「贴图」或「批量贴图」触发，给用户明确的控制权。

### 🎨 UI

- `engine/check_rem.js`
  - 单张/批量反相确认弹窗去掉"自动完成贴图+BW合成"表述。
  - 批量反相按钮 title 同步更新。

---

## v2.3.11 (2026-07-04) — 反相任务统一队列 + wb上款 v1.3.16 联动

### 🔧 调整

- **AI 去背 贴图 OS 反相流程队列化（`engine/check_rem.py v2.2.2`）**
  - 单张「反相」按钮与「批量反相」按钮统一进入同一个后台任务队列，串行执行。
  - 新增 `_invert_worker_loop` 工作线程，避免多个反相任务同时驱动 Photoshop 导致冲突。
  - `/invert-rem` 与 `/batch-invert-rem` 改为立即返回「已加入队列」与当前排队信息。
  - `/batch-invert-result` 同时兼容单张与批量反相的进度轮询。

### 🎨 UI

- `engine/check_rem.js`
  - 单张反相点击后改为轮询队列状态，完成后统一提示并刷新页面。
  - 批量反相保持原有轮询逻辑，兼容新的队列响应格式。

### 📚 文档与版本

- `lovart_bridge.py` / `SKILL.md` / `ARCHITECTURE.md` / `CHANGELOG.md` / `REPRODUCIBILITY.md` 升级到 v2.3.11。
- 与 wb上款 v1.3.16 联动版本对齐。

---

## v2.3.10 (2026-07-04) — WB 上款在线验证 + 与 wb上款 v1.3.14 联动

### ✨ 新增

- **WB 上款页面新增「刷新已上款」功能**
  - 新增 API 端点 `POST /api/upload/refresh-online-listed`，后台启动 `check_online_listed.py`。
  - `check_online_listed.py` 自动打开店小秘 Temu 在线产品页，切分页到 300 条/页，抓取所有 SKU 货号并提取 DX 款号。
  - 抓取结果写入 `D:\Semems WB\.wb_online_listed.json`。

### 🔧 调整

- **已上款状态权威来源变更**
  - `/upload` 页面现在以 `.wb_online_listed.json`（店小秘在线产品页实际数据）作为已上款判断的唯一权威来源。
  - `已上款货号_wb.md` 不再参与 `/upload` 已上款状态判断（仍保留供其他流程参考）。
  - `/api/upload/progress` 返回新增字段：`online_set`、`online_count`、`online_updated_at`。
  - `/api/upload/projects` 返回每个 project 的 `online_listed` 布尔字段。

### 🎨 UI

- `upload.html` 工具栏新增「🌐 刷新已上款」按钮。
- 已在线验证的款号卡片显示绿色 `✓ 在线` 徽章。
- 上款进度面板增加「在线已验证：X / 总 Y」显示。

---

## v2.3.9 (2026-07-04) — Lovart v6.1.1 联动对齐

### 📚 文档与版本

- **与 Lovart-official v6.1.1 对齐**：
  - v6.1.1 修复提示词缺少 concept：把 `POD AI VIRAL FACTORY v3.md` 当规则框架，前面自动拼接 concrete request。
  - v6.1.1 增强图片 URL 提取（artifacts / markdown / 带 query string 的纯链接）。
  - v6.1.1 新增无图诊断 `extract_agent_text`，失败原因写入日志。
  - v6.1.1 `agent_skill._request` 统一重试 3 次，连接层错误幂等重试。
- **Bridge 版本同步**：`lovart_bridge.py` / `SKILL.md` / `ARCHITECTURE.md` / `CHANGELOG.md` / `REPRODUCIBILITY.md` 全部升级到 v2.3.9。

---

## v2.3.8 (2026-07-04) — 文档同步 + wb上款联动版本对齐

### 📚 文档与版本

- **版本号统一升级到 v2.3.8**：`lovart_bridge.py` 启动横幅、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md`、`REPRODUCIBILITY.md` 全部对齐。
- **新增 REPRODUCIBILITY.md**：包含一键复现步骤、目录约定、版本回滚到 Tag 的方法、本次更新问题与解决记录。
- **wb上款联动版本对齐**：明确 Bridge v2.3.8 配合 `wb_listing.py v1.3.13` 使用，记录 Edge 透明隐藏、LoginGuard URL 兜底、豆包传图修复等联动点。

### 🔧 维护

- 无功能代码变更，纯文档与版本同步，确保生产环境可 100% 复现与回滚。

---

## v2.3.7 (2026-07-04) — 上款进度显示修复 + AI 对比缓存刷新

### 🐛 修复

- **上款进度数字异常（如 `280 / 41 (683%)`）**
  - 根因：`/api/upload/progress` 把历史已完成记录和当前选中款混在一起，`done_count` 被历史记录撑爆，`total_count` 却是本次选中数量。
  - 解决：API 现在只统计 `selected` 集合内的 `completed` 和 `failed`，`done_count`、`fail_count`、`total_count` 全部对齐当前批次。
  - 前端文案从 `X / Y (Z%)` 改为：`已上款 X / 总 Y  失败 Z  剩余 W`。

### ⚡ 优化

- **AI 生图对比页重新生图后自动刷新缓存**
  - `/api/ai-review/*` 接口在返回缩略图/原图 URL 时追加 `t=<mtime>` 参数。
  - 重新生成的 AI 图文件名不变但 `mtime` 更新，浏览器会重新加载，不再显示旧图。

### 🔧 调整

- **AI 重新生图日志实时输出**
  - 子进程环境增加 `PYTHONUNBUFFERED=1`，任务日志实时写入状态面板，避免缓冲导致延迟。

---

## v2.3.6 (2026-07-04) — 去背预览首次加载加速

### ⚡ 优化

- **去背预览首次打开不再慢**
  - 根因：`check_rem.py` 启动后首次访问首页需要全量扫描 300+ 个 DX 文件夹并渲染 HTML，耗时约 16 秒。
  - 解决：`check_rem.py` 启动后 1 秒自动在后台执行 `scan_projects()`，把结果 warming 到 30 秒缓存。
  - 效果：用户点击「去背预览」时，首页直接从缓存返回，和 AI 对比 / 上款一样秒开。

---

## v2.3.5 (2026-07-04) — 上款/去背预览打开速度优化

### ⚡ 优化

- **去背预览点击即开**
  - Bridge 启动时后台守护 `check_rem.py`（端口 8766），不再等用户点击才启动。
  - `/api/launch-check-rem` 简化为仅确认端口就绪，不启动进程、不等待扫描。
  - Y2 控制台「去背预览」按钮改为直接 `window.open`，与「AI 对比」按钮一致，瞬时打开新标签。

- **去背预览首页加载加速**
  - `check_rem.py::scan_projects()` 增加 30 秒内存缓存，避免每次刷新都全量扫描 DX 目录。
  - 「刷新全部」按钮会清空缓存，确保立即看到最新结果。

- **上款页面加载加速**
  - 缩略图增加 `loading="lazy"` + `decoding="async"`，首屏只加载可视区域图片。
  - 数据加载期间显示「加载中…」提示，减少空白等待感。

---

## v2.3.4 (2026-07-04) — 修复悬停预览图位置乱跳

### 🐛 修复

- **去背预览页面悬停放大图位置乱跳**
  - 根因：`check_rem.js` 用固定尺寸 `900px × 90vh` 预估预览图大小来定位，与实际渲染尺寸不一致，导致预览框忽上忽下、忽左忽右。
  - 解决：
    - 鼠标悬停后先隐藏预览框，等原图加载完成。
    - 读取 `#preview` 元素实际 `offsetWidth` / `offsetHeight` 后再计算位置。
    - 水平默认放缩略图右侧，右边放不下才放左侧。
    - 垂直仅在下方溢出时才向上平移必要距离，不再大幅跳动。
  - 文件：`D:\Semems WB\04_OS\engine\check_rem.js`（已同步到 `engine/check_rem.js`）。

---

## v2.3.3 (2026-07-04) — 修复上款按钮打不开

### 🐛 修复

- **Y2 控制台「上款」按钮打不开**
  - 现象：点击后浏览器访问 `http://localhost:8765/upload`，显示 `ERR_CONNECTION_REFUSED`。
  - 根因：Bridge 监听 `127.0.0.1:8765`，而当前系统 `localhost` 优先解析到 IPv6 `::1`，导致连接被拒绝。
  - 解决：`lovart_control.html` 中的「上款」按钮从绝对路径 `http://localhost:8765/upload` 改为相对路径 `/upload`，与当前 Y2 控制台保持同域（`127.0.0.1:8765`）。

---

## v2.3.2 (2026-07-04) — 修复去背预览启动崩溃 + 优化打开速度

### 🐛 修复

- **check_rem.py 启动崩溃**
  - 根因：`print()` 语句中包含 emoji（🔄），在 `chcp 936`（GBK）控制台输出时触发 `UnicodeEncodeError`。
  - 解决：移除该 emoji；同时强制 `stdout`/`stderr` 使用 UTF-8，避免后续生僻字符/emoji 再次导致崩溃。
  - 影响：点击 Y2 控制台「去背预览」后，`check_rem.py` 能正常监听 `8766` 端口，不再出现 `ERR_CONNECTION_REFUSED`。

### ⚡ 优化

- **去背预览打开速度**
  - 原逻辑会阻塞等待 `scan_projects()` 全部完成（最多 90 秒）才打开浏览器。
  - 新逻辑：端口 ready 后快速 ping 首页（最多 3 秒），立即打开浏览器；扫描在后台进行，页面逐步渲染。

### 🔧 调整

- 「去背预览」尝试在已有 Chrome 窗口中以新标签页打开（`webbrowser.open(url, new=2)`）。

---

## v2.3.1 (2026-07-04) — 日期分类统一按 DX 文件夹建立日期

### 🔧 调整

- **所有页面日期分类改为 DX 文件夹建立日期**
  - `/upload`、`/ai-review`、去背预览等页面的日期分组统一使用 `DXxxxx` 文件夹的 `st_ctime`（建立时间）。
  - 不再根据 `01_AI` / `02_REM_BG` / `03_UPLOAD` 内文件的最新 `mtime` 判断日期。
  - 避免重新生图、去背、贴图等操作更新文件后，款号被归到错误日期。

### 🗑️ 移除

- 移除 `_load_upload_date_map()` 及相关 `已上款货号_wb.md` 日期解析逻辑。
  - 上款记录仍用于判断「已上款 / 未上款」状态，不再参与日期分类。

---

## v2.3.0 (2026-07-04) — AI 生图对比 + 批量重新生图 + 统一提示词文件

### ✨ 新增

- **AI 生图对比页面 (`/ai-review`)**
  - 在同一页面并排展示原图与 AI 生成图，支持悬停放大。
  - 默认显示最新日期，可按日期/款号筛选。
  - 每款原图下方提供「重新生图」按钮，单张重跑 Lovart。
  - 每款原图提供复选框，支持批量勾选后一键「批量重新生图」。
  - AI 图下方提供删除按钮，移入回收站；回收站支持还原。

- **批量重新生图 API (`/api/ai-review/regenerate-batch`)**
  - 接收多张 `{dx, source_file}`，并发调用 Lovart。
  - 限制同一批次内文件名全局唯一，避免 `LOVART_REGEN_DX_MAP` 跨 DX 同名冲突。
  - 用 MD5 检测 INBOX 同名冲突，避免错用旧批次原图。
  - 新图输出到原 DX 文件夹，自动命名为 `DXxxxx_B2.png` / `DXxxxx_BW2.png` 等，不覆盖原图。

- **实时状态面板**
  - 显示任务状态、当前款号（可点击打开文件夹）、Key、已用时间、成功/失败张数、进度文字。
  - 可展开原始日志，带「复制」按钮，便于一键复制给 AI 分析。
  - 摘要区单独展示给人看的关键信息。
  - 状态徽章区分「已完成」「部分失败」「失败」，避免 completed + fail_count>0 的误导。

### 🔧 调整

- **统一提示词文件**
  - 重新生图与 Lovart 管线默认都读取 `E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`。
  - 不再把提示词硬编码到脚本，用户可随时优化该文件。

### 🐛 修复

- 重新生图时，若 INBOX 存在同名旧批次原图，会错误使用旧图导致生成到错误 DX。
  - **解决方案**: 复制前比较 MD5，同名不同图时移入 `_ai_trash/_inbox_conflicts/` 暂存，生图后不再自动恢复。
- 状态面板在「完成但全部失败」时仍显示「已完成」徽章。
  - **解决方案**: `display_status` 根据 `success_count`/`fail_count` 细化为 `completed`/`partial`/`error`。

---

## v2.2.1 (2026-07-03) — 去背预览入口优化 + 上款日期修复

### 🔧 调整

- **`check_rem.py` v2.1.7**
  - 移除原来的日期分类 landing 页（`/` 路径）
  - 根路径 `/` 直接 302 重定向到最新日期页面（如 `/260703/`）
  - 保留 `/<日期>/` 路由，页面顶部日期下拉框可切换日期
  - Y2 控制台点击「去背预览」后直接进入最新日期的 AI 去背 贴图 OS 页面
  - 日期下拉框样式与 WB 上款 页统一：加大 padding、圆角、字号，视觉更协调

### 🐛 修复

- **`lovart_bridge.py` v2.2.1**
  - 修复 `/upload` 页面款号日期全部归到 2026-07-03 的问题
  - `_scan_upload_projects` 的 `date` 优先读取 `D:\Semems WB\已上款货号_wb.md` 中的记录日期
  - 未记录的款回退到 **AI 生成图最新 mtime**（无 AI 时退去背图 mtime）
  - 与 `check_rem.py` 日期逻辑保持一致，避免 03_UPLOAD 成品被统一修改后日期失真

---

## v2.2.0 (2026-07-03) — UID/group_id 全链路溯源（去背图不再依赖文件名匹配）

### ✨ 新增

- **UID/group_id 元数据系统（v2.0，MD5 主键）**
  - 从 INBOX 原图开始分配全局唯一 `uid`（如 `UID_20250703_0001`）和组 ID `group_id`（如 `G_00001`）。
  - `uid`/`group_id` 贯穿全链路：原图 → AI 图 → 去背图 → 贴图成品 → BW 合成图 → 上款图。
  - 新增 `wb_meta.py` 共享模块，提供 sidecar 和 `uid_map.json` 读写 API。
  - **以 MD5 为主键**：`uid_map.json` 新增 `md5_index: {md5 → uid}`，sidecar 按 UID 命名。
    - 图片改名、移动、复制后，只要内容不变，仍可通过 MD5 找到元数据。
    - `wb_meta.reconcile_dx(dx_dir)` 可扫描实际文件，用 MD5 修正 uid_map 中的路径。
  - 元数据统一放在 `D:\Semems WB\05_META\DXxxxx\`，与图片分离：
    - `05_META/DXxxxx/uid_map.json`
    - `05_META/DXxxxx/sidecars/UID_xxx.meta.json`
  - `01_AI` / `02_REM_BG` / `03_UPLOAD` 只放图片，不放文档。

- **Bridge 生图阶段写入元数据**
  - `lovart_bridge.py` 生图前写入 `.generation_uid_manifest.json`，传给 Lovart 管线。
  - 生图后自动在 `02_PROJECTS/DXxxxx/` 下创建 `uid_map.json`，并为 AI 图生成 `.meta.json` sidecar。

- **Lovart 管线回写 UID**
  - `run_official_v53.py` 读取 `BRIDGE_UID_MANIFEST`，把 `uid`/`group_id` 写入 `source_map.json`。

- **去背/贴图/上款全链路传播**
  - `check_rem.py` / `wb_meitu_batch.py` / `WB去背 entrypoint/main.py`：去背输出自动注册到 `uid_map.json`。
  - `wb_sticker_ps.py` / `ps_batch.py` / `process_black.py`：贴图成品与 BW 合成图自动注册。
  - `wb_listing.py`：上款时优先按 `uid_map.json` 查找图片，fallback 到原文件名规则。

- **check_rem 前端按 group 聚合展示**
  - `check_rem.js` 读取 `group_id`，把 AI 图、去背图、贴图成品、BW 合成图、黑 T 变体按同一组展示。
  - 黑版变体不再显示为「无独立 AI」的孤立卡片，而是归并到对应 group。

- **迁移脚本**
  - 新增 `tools/migrate_uid_map.py`：一键为所有旧 DX 项目生成 `uid_map.json` 和 sidecar。
  - `check_rem.py` 启动扫描时自动对缺失元数据的项目调用迁移。

- **项目目录整理**
  - 辅助模块/脚本不再堆在仓库根目录：
    - `lib/wb_meta.py` — 共享元数据模块
    - `tools/migrate_uid_map.py` — 迁移脚本
    - `engine/check_rem.py` / `engine/check_rem.js` — 去背预览引擎副本（版本控制用）

### 🔧 架构调整

- **解决 Registry 双写冲突**
  - `WB去背/registry.py` 改为写入独立的 `.wb_rembg_registry.json`，不再覆盖 Bridge 的 `.image_registry.json`。
  - Bridge 的 `.image_registry.json` 成为唯一权威 v4 registry。

### 🐛 修复

- 去背图与 AI 图的关联不再依赖 `_cut.png` 文件名 stem，重命名后仍可正确配对。

---

## v2.1.9 (2026-07-02) — 强制重新上款开关 + 稳定版配合

### ✨ 新增

- **「强制重新上款」功能**
  - `/upload` 页面 toolbar 增加「强制重新上款」复选框
  - 勾选后点击批量上传，后端会自动从 `D:\Semems WB\已上款货号_wb.md` 删除对应款号
  - 删除后再启动 `wb_listing.py`，让已上款的款像未上款一样正常执行
  - 不修改 `wb_listing.py` 内部逻辑，保持 wb上款 v1.3.1-stable 稳定版本不变

### 🐛 修复

- **已上款记录格式兼容**
  - `_read_completed_md()` 同时识别 `- DXxxxx` 和 `* DXxxxx`
  - 修复历史记录读取失败导致 `/upload` 页面全部显示未上款的问题

### 🔧 稳定版配合

- 当前版本与 wb上款 `v1.3.1-stable` 配合：
  - wb上款保持简单稳定逻辑，不做强制重新上款判断
  - Bridge 负责强制重新上款的前置清理（删除已上款记录）

---

## v2.1.7 (2026-07-02) — 上款页面修复 + Chrome  detached

### 🐛 修复

- **上款页面默认最新日期**：打开 `/upload` 后日期下拉框自动选中最新日期
- **预览图加载加速**：
  - 移除后台全量预生成缩略图（反而占用资源拖慢服务器）
  - Flask 启动改为 `threaded=True`，可并发处理多个缩略图请求
- **批量上传未生效**：`/api/batch-upload` 已正确默认对接 `E:\Claude code\wb上款\wb_listing.py`，**需重启 Bridge 后生效**
- **批量上传逻辑调整**：改为只启动一次 `wb_listing.py`，以选中款中最早的 DX 为起点连续处理（避免多实例抢 CDP）
- **Chrome  detached**：`lovart_bridge.bat` 启动 Chrome 时通过 `cmd /c ... >nul 2>&1`  detach，关闭 CMD 窗口后 Chrome 不再被关闭

---

## v2.1.6 (2026-07-02) — 上款对接 wb_listing.py + 预览图加速

### 📤 上款对接

- `/api/batch-upload` 默认对接 `E:\Claude code\wb上款\wb_listing.py`
- 勾选款号后点击「批量上传」，按顺序逐个 DX 启动 `wb_listing.py DXxxxx`
- 避免同时启动多个浏览器实例导致状态冲突
- 仍可通过环境变量 `LOVART_UPLOAD_SCRIPT` 覆盖脚本路径

### ⚡ 上款页面预览图加速

- `/api/upload/projects` 扫描时**后台预生成缩略图**，减少页面加载等待
- `_get_upload_thumb()` 优化：仅在图片真正含透明像素时才合成白底
- 缩略图/原图响应添加 `Cache-Control: max-age=3600`，浏览器可缓存
- 修复 `upload.html` 批量上传后的页面刷新逻辑

---

## v2.1.5 (2026-07-02) — 修复反相后 BW 合成图不生成

### 🐛 修复

- **check_rem.py v2.1.5**
  - 修复：只反相单张图时，BW 合成图不会重新生成
  - 根因：`ps_batch.py` 检测到 `DX_*BW.jpg` 已存在时会跳过合成
  - 解决：`_run_sticker_pipeline()` 在运行前先清理旧的自动生成贴图/BW文件，确保每次反相或重跑都能重新贴图+合成BW
  - 清理范围：`DX_白BW.jpg` / `DX_黑BW.jpg` / `DX_B_白T.jpg` / `DX_W_白T.jpg` / `DX_B_黑T.jpg` / `DX_W_黑T.jpg`
  - 修复 `_ps_batch` 端点 DX 正则表达式错误（`DX\\d` → `DX\d`）

---

## v2.1.4 (2026-07-02) — 上款页面替换 PS贴图控制台

### 📤 新增：WB 上款页面

- **移除 PS贴图控制台**：原 `/ps-sticker` 页面及相关 API 已移除
- **新增 `/upload` 上款页面**：
  - 展示每款 `03_UPLOAD` 目录下的成品图片
  - 按 **BW / B / W** 分组显示，与 AI 去背 贴图 页面风格一致
  - 缩略图 220px 高度，等比缩放，白底合成
  - **鼠标悬停放大**：最大 900px，智能避让屏幕边缘
  - 每款卡片带勾选框，支持「全选」
  - **批量上传按钮**：勾选款号后点击，调用 `/api/batch-upload`
- **新增 API 端点**：
  - `GET /api/upload/projects` — 返回含 03_UPLOAD 成品的 DX 列表
  - `GET /api/upload/thumb?dx=DXxxx&file=...` — 返回缩略图
  - `GET /api/upload/original?dx=DXxxx&file=...` — 返回原图（悬停放大用）
  - `POST /api/batch-upload` — 接收 `{dx_list: [...]}`, 批量上款
  - `GET /api/open?dx=DXxxx&which=up` — 打开指定 DX 的 03_UPLOAD 文件夹
- **批量上传对接**：默认提示未配置脚本；可通过环境变量 `LOVART_UPLOAD_SCRIPT` 指定外部上款脚本路径

### 🏗️ 项目文件更新

```
C:\Users\Administrator\ZCodeProject\
├── upload.html             v2.1.4  上款页面（新增）
└── ps_sticker.html         已移除
```

---

## v2.1.3 (2026-07-02) — 批量反相 + 自动贴图/BW合成

### 🌑 批量反相

- **check_rem.py v2.1.3** 新增「批量反相」按钮
- 勾选多款后一键反相所有 B/W/BW 去背图，生成对应的 `DX_黑B/W/BW_cut.png` 黑版专用图
- 反相完成后**自动跑完整贴图流水线**：黑T专用贴图 → 通用白T贴图 → BW 合成
- 新增后端端点 `/batch-invert-rem` + `/batch-invert-result`，支持后台执行与前端进度轮询

---

## v2.1.2 (2026-07-02) — Bridge 子进程最小化

### 🪟 后台静默运行

- **Bridge 内一键启动 check_rem.py**：点击控制面板的「去背预览」后，弹出的命令提示行窗口现在也是**最小化运行**
- **PS 贴图 / BW 合成**：通过 Bridge 触发的贴图和 BW 合成子进程同样改为最小化窗口，不再突然弹出到前台
- **统一工具函数 `run_minimized()`**：在 `lovart_bridge.py` 中集中管理 Windows 最小化启动逻辑（`STARTUPINFO` + `SW_SHOWMINNOACTIVE` + `CREATE_NEW_CONSOLE`）
- **启动脚本版本同步**：`lovart_bridge.bat` 升级到 v2.1.2

---

## v2.1 (2026-07-02) — 贴图流水线 + 反相黑版 + UI 重构

### 🎨 UI/UX 重构

- **整体放大**：卡片、缩略图、文字、按钮全部放大，清晰易点击
- **去背缩略图完整显示**：不再叠加分辨率文字，图片完整展示
- **放大镜位置固定**：分辨率低于 2000×2000 时才出现，固定在每个去背图按钮栏最右侧，旁边显示当前分辨率
- **一键放大**：点击 🔍 自动将图片放大到 2046×2046（LANCZOS 插值）
- **反相按钮**：每张去背缩略图增加「反相」按钮，一键生成 `DX_黑B/W/BW_cut.png`，并自动重跑该款全部贴图 + BW 合成
- **成品展示重构**：`03_UPLOAD` 贴图成品按 BW / B / W 分组，一行两张缩略图，与 AI 图、去背图等宽，风格统一
- **黑版变体独立展示**：`_黑B` / `_黑W` / `_黑BW` 不再占用 AI/REM 配对位，独立并列显示
- **悬停放大图智能定位**：自动检测视口右/下边缘，放不下时向左/向上偏移，避免显示不全
- **变体图过滤**：无独立 AI 的「变体图」不再显示缩略图，保持界面清爽

### 📎 贴图流水线闭环

- **贴图即合成 BW**：点击「贴图」或「批量贴图」不再只做 B/W 贴图，而是自动完成 BW 合成
- **黑T专用优先**：`02_REM_BG` 中存在 `黑B/黑W/黑BW` 时，黑T贴图优先使用这些专用文件；没有时才 fallback 到通用 B/W/BW
- **黑版联动反相**：反相生成黑版专用图后，自动调用 `process_black.py` 完成黑T贴图与 BW 合成
- **流水线顺序**：黑T专用贴图 → 通用白T贴图 → BW 合成，全部通过 `/ps-sticker` 一键触发

### 🪟 后台静默运行

- **Photoshop 隐藏**：`wb_sticker_ps.py` / `process_black.py` / `ps_batch.py` 全部设置 `psApp.Visible = False`
- **PS 最小化打开**：`ps_batch.py` 使用 `WScript.Shell.Run(..., 7, False)`（`SW_SHOWMINNOACTIVE`），不抢焦点
- **去背/贴图 worker 最小化**：`check_rem.py` 通过 `run_minimized()` 启动子进程，命令行窗口不弹出到前台

### 📦 新增/拆分脚本

- `check_rem.js` v2.1 — 独立前端 JS，负责反相、放大、批量贴图、悬停定位等交互
- `ps_sticker_one.py` v2.1 — PS 贴图单款入口
- `ps_batch_one.py` v2.1 — BW 合成单款入口
- `process_black.py` v2.1 — 黑T专用贴图 + BW 合成

### 🚀 启动脚本纳入版本控制 + 最小化运行

- **`lovart_bridge.bat` 入库**：将 `D:\Semems WB\01_INBOX\lovart_bridge.bat` 复制到 `C:\Users\Administrator\ZCodeProject\lovart_bridge.bat`，纳入 GitHub 版本控制
- **Bridge 启动窗口最小化**：双击 `lovart_bridge.bat` 后，原窗口自动切换为最小化窗口运行，不干扰用户操作
- **`启动对比.bat` 最小化**：`D:\Semems WB\02_PROJECTS\01_CHECK_REM\启动对比.bat` 同样改为最小化运行
- **新增 `start_check_rem.bat`**：在 `D:\Semems WB\04_OS\engine\` 提供版本控制的 `check_rem.py` 最小化启动器

### 🔧 修复与改进

- `lovart_bridge.py` v2.1：支持 `--port` / `--host`，启动时写入 `bridge.pid`，供启动脚本优雅停止
- 启动脚本 `lovart_bridge.bat` v2.1：与 v2.1 Python 端对齐，防重复启动、日志轮转、优雅停止
- `.gitignore`：忽略 `bridge.pid` 与 `bridge.log.*.bak`

### 🐛 已解决疑难杂症

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 去背缩略图一半显示分辨率 | 分辨率文字直接覆盖在图片上 | 移除图片内文字，分辨率改在按钮栏显示 |
| 放大镜按钮位置混乱 | 按钮按 DOM 顺序排列 | 固定 🔍 为最后一个子元素 |
| 贴图只做 B/W 没合成 BW | 前端只调用 wb_sticker_ps.py | `/ps-sticker` 改为完整流水线：黑T → 白T → BW合成 |
| 黑T贴图用通用图导致错误 | 没有检测 `黑B/黑W/黑BW` 专用文件 | 存在黑版文件时通用图跳过黑T输出 |
| PS 窗口弹出干扰工作 | 默认 Visible=True / shell.Run 前台 | 全链路设置隐藏/最小化 |
| 已贴图缩略图太小 | 独立窄栏展示 | 与 AI/去背图等宽，一行两张 |
| 悬停放大图被截断 | 固定 right+8 / top 定位 | 检测视口边界，自动左/上偏移 |
| 反相后贴图未更新 | 只生成反相图，没触发后续流程 | 反相接口自动调用贴图+BW合成 |

---

## v2.0 (2026-07-02) — 血缘引擎 + 批量去背 + JS独立化

### 🚀 改进：启动脚本 `lovart_bridge.bat`

- **版本号统一**：标题和启动信息都改为 `v2.0`
- **防重复启动**：启动前检查 `http://127.0.0.1:8765/api/inbox`，若 Bridge 已在运行则直接打开浏览器并退出
- **优雅停止**：关闭 CMD 窗口时读取 `bridge.pid` 停止对应 Python 进程，避免残留；无 PID 时按端口兜底停止
- **日志轮转**：启动前自动备份旧 `bridge.log` 为 `bridge.log.YYYYMMDD_HHMMSS.bak`
- **启动参数支持**：
  - `--port <端口>`：自定义端口
  - `--host <地址>`：自定义监听地址
  - `--no-browser`：不自动打开 Chrome
  - 其他参数透传给 `lovart_bridge.py`
- **Python 端配合**：`lovart_bridge.py` 支持 `--port`/`--host`，启动时写入 `bridge.pid`

### 🧬 新增：数据血缘追踪系统（Lineage Engine）

- **Registry v4** — 新增 `source_md5`, `derived_md5s`, `lineage_status` 字段
- **Hook 注册入口** — `POST /api/lineage/register`，供外部工具调用
- **Scanner 扫描器** — 通过文件 stem 精确匹配，自动建立去背→AI、贴图→去背的溯源关系
- **AutoScan 后台线程** — 每 60 秒自动扫描新文件，建立血缘关系
- **check_rem.py Hook** — 去背成功后自动 POST 血缘记录到 Bridge
- **lineage_status** — `confirmed`（Hook 实时记录） vs `inferred`（Scanner 推断）

### ⚡ 新增：批量去背

- **全选按钮** — check_rem.py 工具栏新增勾选框
- **批量去背按钮** — 选中多个款，一次美图处理全部，无需逐个确认
- **`/batch-rembg` 端点** — 批量暂存 → 一次美图 → 逐个分配结果
- **锁轮询机制** — 批量任务通过 `.rembg_lock` 文件串行执行

### 🎨 界面改进

- 项目列表按日期分组（手风琴折叠，当天默认展开）
- 款号一致性检查（红色高亮 + 置顶显示不一致项目）
- 🔧 自动修复按钮（将错放文件移到正确 DX 文件夹）
- 修复记录写入目标文件夹 `_fix_log.json`
- 点击文件名打开对应子文件夹（01_AI / 02_REM_BG / 03_UPLOAD）
- 悬停预览 500px 放大图（白底合成）
- 回收站面板（网页上直接恢复文件）
- ✅ AI 生图 → 🖼 去背预览 一键跳转

### 🔧 修复

- ⭐ **JS独立文件** — 将 JS 从 f-string 模板中提取到独立 `check_rem.js` 文件，彻底消除 f-string 括号转义问题
- ⭐ **代码去重** — 删除文件中 701 行重复的 Handler 类定义，消除破损模板污染
- ⭐ **修复 JS 语法错误** — 修复 `renameStem`、`rembg` 函数中多行字符串导致的 SyntaxError
- 同名文件后缀自动大写（b→B, w→W, bw→BW）
- 预览图不再使用 PIL 缩放，直接返回原图
- 状态持久化：重启桥接后上次任务状态可见
- 中文变体文件（`黑B_cut.png`）不再误报缺 AI 图
- `_render_html` 模板 f-string 转义修复
- 浏览器统一使用 Chrome（Edge 不再弹出）
- 文件夹前台打开（`os.startfile`）

### 🐛 已解决疑难杂症

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 预览图不显示 | 懒加载 JS 未触发 | 改用直接 `src=` 加载 |
| 全选无反应 | f-string 模板中 `{{` 转义错误 | JS 独立文件，彻底隔离模板 |
| 复制缺图款号无效 | JS 文件有 `\n`/实际换行混用 | 统一使用 `\n` 转义序列 |
| 点击去背无反应 | `rembg` 函数多行字符串断裂 | 合并为单行字符串 |
| 预览显示 `{cards_html}` | f-string 表达式被加倍转义 | 恢复 `{cards_html}` 为单括号 |
| 打开两个浏览器 | Bridge 和 check_rem 都打开 Chrome | 统一由 Bridge 打开 |

### 🏗️ 项目文件

```
C:\Users\Administrator\ZCodeProject\
├── lovart_bridge.py        v2.1.7  Flask HTTP Bridge
├── lovart_control.html     v2.1.4  控制面板前端
├── upload.html             v2.1.7  上款页面
├── lovart_bridge.bat       v2.1.7  一键启动脚本
├── CHANGELOG.md            v2.1.7  更新日志
├── ARCHITECTURE.md         v2.1.7  系统架构文档
├── SKILL.md                v2.1.7  技能定义
└── .gitignore

D:\Semems WB\04_OS\engine\
├── check_rem.py            v2.1.5  AI vs 去背 vs 贴图成品 对比预览
├── check_rem.js            v2.1.5  独立前端 JavaScript
├── start_check_rem.bat     v2.1.1  check_rem.py 最小化启动器
├── _rembg_worker.py        v2.1  单张去背工作进程
└── rename_dx_folders.py    v2.0  DX文件夹重命名

E:\Claude code\ps\
├── wb_sticker_ps.py        v2.1  通用贴图（黑T优先检测）
├── ps_batch.py             v1.3.0  BW合成
├── ps_sticker_one.py       v2.1  单款贴图入口
├── ps_batch_one.py         v2.1  单款BW合成入口
└── process_black.py        v2.1  黑T专用贴图+BW合成
```

## v1.0 (2026-07-01) — 初始版本

- Flask Bridge 服务器，REST API
- HTML 控制面板，INBOX 图片网格预览
- 勾选图片启动 Lovart 生图
- UID + group_id 分配系统
- Registry v3
- Lovart 管线集成
- 文件回收站
- 一键启动脚本
