# Lovart-WB 一体化控制系统 — 更新日志

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
