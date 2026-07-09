# Y2 Bridge / Lovart Bridge —— Kimi 客户端接手说明

> 生成时间：2026-07-08
> 对应项目：`C:\Users\Administrator\ZCodeProject`
> 一键入口：`D:\Semems WB\01_INBOX\lovart_bridge.bat`
> 当前版本：代码里混用 v2.4.1 / v2.3.22 / v2.4.0，需先统一（见下方「当前状态」）

---

## 1. 这是什么

Y2 Bridge 是一个 **Flask HTTP 本地服务**，监听 `127.0.0.1:8765`，把一堆外部脚本和工具打包成一个网页控制面板：

- AI 生图（调用 Lovart 官方管线）
- AI 生图对比 / 重新生图
- WB 美图去背预览（端口 8766）
- PS 贴图 + BW 合成
- WB 上款（批量上传到店小秘）
- Temu 核价（`/pricing`）
- Temu 报活动（`/activity`）
- Temu 建议零售价填写（`/retail_price`，v2.4.1 新增，未完全收尾）

整个系统的数据/图片约定在 `D:\Semems WB\` 下，核心代码在 `C:\Users\Administrator\ZCodeProject`。

---

## 2. 目录地图

### 2.1 项目代码（Git 仓库）

| 路径 | 作用 |
|------|------|
| `C:\Users\Administrator\ZCodeProject\lovart_bridge.py` | **主服务**，~4300 行 Flask，所有 API 和页面路由都在这里 |
| `C:\Users\Administrator\ZCodeProject\lovart_bridge.bat` | 旧启动脚本（已被 `D:\Semems WB\01_INBOX\lovart_bridge.bat` 替代） |
| `C:\Users\Administrator\ZCodeProject\lovart_control.html` | 主控制台首页 |
| `C:\Users\Administrator\ZCodeProject\ai_review.html` | AI 生图对比页 |
| `C:\Users\Administrator\ZCodeProject\upload.html` | 上款页 |
| `C:\Users\Administrator\ZCodeProject\pricing.html` | Temu 核价页 |
| `C:\Users\Administrator\ZCodeProject\activity.html` | Temu 报活动页 |
| `C:\Users\Administrator\ZCodeProject\retail_price.html` | Temu 建议零售价页（v2.4.1 新增） |
| `C:\Users\Administrator\ZCodeProject\engine\check_rem.py` | 去背预览服务，端口 8766 |
| `C:\Users\Administrator\ZCodeProject\engine\check_rem.js` | 去背页面前端 JS |
| `C:\Users\Administrator\ZCodeProject\engine\_rembg_worker.py` | 单张去背后台进程 |
| `C:\Users\Administrator\ZCodeProject\lib\wb_meta.py` | **UID/group_id 元数据共享模块**，被 Bridge / 去背 / PS / 上款共同导入 |
| `C:\Users\Administrator\ZCodeProject\tools\migrate_uid_map.py` | 旧项目迁移到 05_META 元数据 |

### 2.2 外部仓库（不在 ZCodeProject Git 里）

| 路径 | 远程 | 作用 |
|------|------|------|
| `E:\Claude code\lovart-official` | `github.com/jordan23kevin/lovart-official` | Lovart 生图管线，入口 `run_official_v53.py` |
| `E:\Claude code\ps` | 未纳入 Git | PS 贴图 + BW 合成流水线 |
| `E:\Claude code\wb上款` | `github.com/jordan23kevin/wb-listing` | 批量上款 |
| `E:\Claude code\Temu自动化\核价` | `github.com/jordan23kevin/temu-hengjia-engine` | Temu 核价引擎 |
| `E:\Claude code\Temu自动化\报活动` | `github.com/jordan23kevin/temu-baohuodong` | Temu 报活动引擎 |
| `E:\Claude code\WB Lovart\建议零售价.js` | 无 | **建议零售价 Node 脚本，不在 Git 中** |

### 2.3 数据目录

```
D:\Semems WB\
├── 01_INBOX              # 原图入口
├── 02_PROJECTS\DXxxxx    # 按款号分的项目
│   ├── 01_AI             # AI 生成图
│   ├── 02_REM_BG         # 去背图
│   └── 03_UPLOAD         # 贴图成品
├── 04_OS\engine          # check_rem.py 也可以放这里运行
├── 05_META\DXxxxx        # uid_map.json + sidecars（元数据与图片分离）
├── _ai_trash             # AI 图回收站
├── _debug                # 各脚本日志
├── .image_registry.json          # Bridge 血缘注册表 v4
├── .wb_rembg_registry.json       # 去背注册表
├── .wb_upload_progress.json      # 上款进度
└── .wb_online_listed.json        # 已上款增量游标数据
```

---

## 3. 怎么启动

### 推荐方式

双击：

```
D:\Semems WB\01_INBOX\lovart_bridge.bat
```

这个 bat 会：
1. 最小化自己重新启动（避免黑窗）
2. 切到 `C:\Users\Administrator\ZCodeProject`
3. 检查 `127.0.0.1:8765` 是否已有服务在跑
4. 旋转旧日志
5. 后台启动 `python lovart_bridge.py --port 8765 --host 127.0.0.1`
6. 等待服务就绪
7. 打开 Chrome 窗口 `1400x900`
8. 窗口关闭时自动 kill 进程

### 手动方式

```bash
cd "C:\Users\Administrator\ZCodeProject"
python lovart_bridge.py
# 或指定端口
python lovart_bridge.py --port 8765 --host 127.0.0.1
```

### 去背预览

```bash
cd "D:\Semems WB\04_OS\engine"
python check_rem.py
```

但实际上 **Bridge 启动时会自动守护 check_rem.py**（`_check_rem_daemon`），所以通常不用手动启动。

---

## 4. 当前状态（重要，接手先处理）

### 4.1 版本号不一致

`lovart_bridge.py` 文件头注释是 **v2.4.1**，启动横幅还打印 **v2.3.22**，`SKILL.md` 写 **v2.3.23**，`CHANGELOG.md` 最新条目只到 **v2.4.0**。

**建议**：先把版本号统一成 v2.4.1，并补一条 CHANGELOG v2.4.1 条目（建议零售价功能）。

### 4.2 有未提交修改

```
M engine/check_rem.js
M engine/check_rem.py
M lovart_bridge.py
M retail_price.html
```

共 4 个文件有改动，142 行新增、28 行删除。建议先 `git diff` 审查，决定是否提交。这些修改涉及：
- 建议零售价的 diagnose 模式
- check_rem 守护进程日志
- 图片格式扩展（jpg/jpeg/webp）

### 4.3 建议零售价功能未完全收尾

v2.4.1 新增了 `/retail_price` 页面和相关 API，但：
- `建议零售价.js` 在 `E:\Claude code\WB Lovart\` **不在 Git 里**
- 真实 Edge/Temu 流程未跑过
- 日志格式用了 `{"line", "kind"}` dict，与 activity 的字符串格式不一致

---

## 5. 核心模块怎么读

### 5.1 lovart_bridge.py 快速导航

文件很长（~4300 行），但结构清晰：

| 区域 | 大致行号 | 内容 |
|------|---------|------|
| 常量区 | 开头 ~300 行 | 路径、端口、外部脚本位置 |
| 工具函数 | ~300 ~1200 行 | MD5/SHA256、子进程最小化、文件夹前台打开、回收站 |
| Registry | ~1200 ~1800 行 | `.image_registry.json` 读写、血缘扫描 |
| 任务状态 | ~1800 ~2200 行 | `task_state`、`pricing_task`、`activity_task`、`retail_price_task` |
| 页面/API | ~2200 ~末尾 | Flask 路由，按 `/`、 `/ai-review`、 `/upload`、 `/pricing`、 `/activity`、 `/retail_price` 分组 |

### 5.2 check_rem.py 快速导航

| 区域 | 内容 |
|------|------|
| 常量/配置 | 端口 8766、路径、PS/美图参数 |
| `scan_projects()` | 扫描所有 DX 项目，30 秒内存缓存 |
| 去背相关 | `/rembg`、 `/batch-rembg`、 `_rembg_worker.py` 调用 |
| 贴图相关 | `/ps-sticker`、 `/ps-batch`、 `/sticker-status` |
| 反相相关 | `/invert-rem`、 `/batch-invert-rem` |
| 其他 | 放大、回收站、修复文件名、一致性检查 |

### 5.3 wb_meta.py

这个是全链路溯源的根基：
- `md5_file(path)` / `sha256_file(path)`
- `register_inbox()`、`register_ai()`、`register_rembg()`、`register_sticker()`、`register_upload()`
- `migrate_dx()`：旧项目无 sidecar 时自动补录
- `reconcile_dx()`：图片改名/移动后用 MD5 修正路径

**任何涉及 05_META、uid_map.json、sidecar 的改动都要先读这个文件。**

---

## 6. 踩过的坑与解决方法

### 6.1 版本与文档不一致

- **现象**：用户看到面板标题、日志、文档说的版本号不一样。
- **根因**：改功能时只改了代码某处，没同步横幅/CHANGELOG/SKILL.md。
- **解决**：发版时全局搜索版本号字符串，统一替换；CHANGELOG 必须同步写。

### 6.2 缩略图黑白错位

- **现象**：上款页面白 T 和黑 T 的缩略图显示成同一张。
- **根因**：缓存文件名生成时用 `re.sub(r'[^A-Za-z0-9_.-]', '_', filename)` 把中文替换成下划线，`白T` 和 `黑T` 冲突。
- **解决**：`safe_name()` 只替换 Windows 非法字符 `\ / * ? : " < > |`，保留中文；同时 API 返回 `thumb_mtime`，前端用缩略图自身 mtime 作为缓存破坏参数。
- **位置**：`lovart_bridge.py::_get_upload_thumb`、`_upload_thumb_path`、`_scan_upload_projects`；`upload.html`

### 6.3 文件夹打开不前台显示

- **现象**：点击「打开文件夹」弹不出窗口。
- **根因**：`os.startfile` 复用已有资源管理器窗口时不强制激活。
- **解决**：`_open_folder_front()` 先用 `explorer.exe` 打开，再用 `win32gui` 找 `CabinetWClass` 窗口并 `SetForegroundWindow`。
- **位置**：`lovart_bridge.py::_open_folder_front`

### 6.4 批量上款弹黑色 CMD 窗口

- **现象**：点击批量上款会闪黑窗。
- **根因**：`subprocess.Popen` 默认创建控制台窗口。
- **解决**：`run_minimized()` 新增 `no_console=True`，用 `CREATE_NO_WINDOW` 启动，stdout/stderr 重定向到 `DEVNULL`。
- **位置**：`lovart_bridge.py::run_minimized`

### 6.5 去背预览启动崩溃

- **现象**：`check_rem.py` 启动后端口 8766 没起来。
- **根因**：`chcp 936`（GBK）控制台下 `print()` 里的 emoji 触发 `UnicodeEncodeError`。
- **解决**：移除 print 中的 emoji，强制 `stdout`/`stderr` 用 UTF-8。
- **位置**：`engine/check_rem.py`

### 6.6 去背预览打开慢

- **现象**：点击「去背预览」要等很久才出页面。
- **根因 1**：Bridge 等 `scan_projects()` 90 秒才开浏览器。
- **解决 1**：端口 ready 后快速 ping，3 秒内打开浏览器，扫描在后台进行。
- **根因 2**：每次请求首页都全量扫描。
- **解决 2**：`scan_projects()` 加 30 秒内存缓存。
- **根因 3**：冷启动首次扫描 300+ DX 文件夹要 16 秒。
- **解决 3**：启动后 1 秒后台线程预扫描 warming 缓存。
- **位置**：`lovart_bridge.py::_check_rem_daemon`；`engine/check_rem.py::scan_projects`

### 6.7 上款按钮打不开

- **现象**：Y2 控制台「上款」按钮没反应。
- **根因**：按钮用 `http://localhost:8765/upload`，但系统 `localhost` 解析到 IPv6 `::1`，Bridge 只监听 IPv4 `127.0.0.1`。
- **解决**：改为相对路径 `/upload`。
- **位置**：`lovart_control.html`

### 6.8 日期分类乱跳

- **现象**：同一个 DX 款号在不同日期分组里反复出现。
- **根因**：原系统按 `01_AI` / `02_REM_BG` / `03_UPLOAD` 内文件的 `mtime` 判断日期，去背/贴图会更新 mtime。
- **解决**：统一按 `DXxxxx` 文件夹的 `st_ctime`（建立时间）分类；复制/移动 DX 文件夹会改变建立时间，需避免。
- **位置**：`lovart_bridge.py::_dx_dir_date()`、`engine/check_rem.py::scan_projects()`

### 6.9 批量去背 B/W 被错误跳过

- **现象**：某款有 BW 文件，导致后面所有款都被跳过 B/W 去背。
- **根因**：`/batch-rembg` 用全局 `dx_files` 判断是否含 BW，前一个款的 BW 污染后续款。
- **解决**：每个 DX 独立判断，只跳过该 DX 自己的 B/W。
- **位置**：`engine/check_rem.py`

### 6.10 黑 T 贴图用错源图

- **现象**：黑 T 贴图用了通用白 T 源图。
- **根因**：通用图和黑版图同名，没有优先检测黑版专用文件。
- **解决**：文件名加 `_黑` 前缀，贴图流水线先检测 `DX_黑B/W/BW_cut.png`，存在则优先使用。
- **位置**：`engine/check_rem.py`、PS 脚本 `process_black.py`、`wb_sticker_ps.py`

### 6.11 PS 窗口抢焦点

- **现象**：贴图时 Photoshop 窗口弹到最前面打断工作。
- **根因**：Photoshop COM 默认 `Visible=True`。
- **解决**：所有 PS 脚本统一设置 `psApp.Visible = False`；`ps_batch.py` 用 `shell.Run(..., 7, False)`（最小化不激活）。
- **位置**：PS 流水线各脚本

### 6.12 f-string 嵌 JS 大括号冲突

- **现象**：`check_rem.py` 里直接写 JS 时大括号 `{}` 和 Python f-string 冲突。
- **根因**：f-string 把 JS 对象字面量当成占位符。
- **解决**：JS 全部抽到独立 `check_rem.js` 文件，通过 `<script src="/check_rem.js">` 引入。
- **位置**：`engine/check_rem.js`

### 6.13 重新生图覆盖旧图 / 用错源图

- **现象**：重新生图后旧 AI 图被覆盖，或用了别的批次的同名原图。
- **根因**：输出文件名固定为 `_B.png` / `_BW.png`；找源图只按文件名。
- **解决**：输出自动递增 `_B2.png` / `_BW2.png`；复制前比较 MD5，冲突时暂移；批量重新生图 key 改为 `(dx, source_file)`。
- **位置**：`lovart_bridge.py` 重新生图相关函数

### 6.14 上款进度显示异常

- **现象**：进度显示 `280 / 41 (683%)`。
- **根因**：`/api/upload/progress` 把历史已完成记录算进当前批次。
- **解决**：`done_count / total_count` 只统计当前选中的款号。
- **位置**：`lovart_bridge.py::api_upload_progress`

### 6.15 刷新已上款 300 条/页切换不生效

- **现象**：选择 300 条/页后页面仍停留在 50 条，漏判已上款。
- **根因**：`switch_pagination()` 点击后只固定 sleep 4 秒，未等 loading 结束，也未校验是否切换成功。
- **解决**：增加 loading 检测、切换后校验页大小和行数、多策略重试。
- **位置**：`wb上款/check_online_listed.py v1.3.20`

### 6.16 上款时夸克/Chrome 窗口被误操作

- **现象**：批量上款时夸克浏览器自动启动/透明窗口遮挡屏幕。
- **根因**：Edge 与夸克/Chrome 同为 Chromium 内核，窗口类名相同；`EdgeService.show_for_user()` 按类名兜底时误操作。
- **解决**：`wb上款 browser_kernel/service/edge_service.py` 增加进程名校验，只操作 `msedge.exe`。
- **位置**：`E:\Claude code\wb上款\browser_kernel\service\edge_service.py`

### 6.17 核价长页滚动回顶

- **现象**：Temu 核价时长页无法完成，每次滚动都被拉回顶部。
- **根因**：`utils/js_helpers.py` 的 JS 辅助函数每次 `_eval()` 都重置 `scrollTop = 0`。
- **解决**：JS 内部不再重置，由 `core/engine.py` 入口统一重置一次，后续从当前位置继续。
- **位置**：`temu-hengjia-engine/utils/js_helpers.py`、`core/engine.py`

### 6.18 任务状态仅内存保存

- **现象**：Bridge 重启后不知道之前核价/报活动/建议零售价任务跑没跑完。
- **根因**：`pricing_task` / `activity_task` / `retail_price_task` 只存在内存里。
- **缓解**：核价读 `hengjia_state.json`，报活动读 `state/state.json`，已上款读 `.wb_online_listed.json`；建议零售价目前还没有持久化状态文件。

---

## 7. 环境依赖检查清单

接手或排错时，先确认：

- [ ] Python 3.11 在 `C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`
- [ ] 依赖：`pip install flask Pillow requests pywin32 pythoncom numpy`
- [ ] Chrome 在 `C:\Program Files\Google\Chrome\Application\chrome.exe`
- [ ] Photoshop 在 `D:\Program Files\Adobe Photoshop 2025 v26.0\Adobe Photoshop 2025\Photoshop.exe`
- [ ] Lovart 密钥：`E:\Claude code\lovart-official\config\keys.json`
- [ ] 提示词文件：`E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
- [ ] Edge 调试模式已启动（核价/报活动/建议零售价需要）：`msedge --remote-debugging-port=9222`
- [ ] Node.js 在 PATH 中（建议零售价脚本需要）
- [ ] `E:\python_packages` 在 PYTHONPATH 中

---

## 8. 日志与调试

| 日志 | 路径 |
|------|------|
| Bridge 主日志 | `C:\Users\Administrator\ZCodeProject\bridge.log` |
| 去背预览日志 | `D:\Semems WB\04_OS\engine\check_rem.log`（若手动启动） |
| 去背 worker 日志 | `D:\Semems WB\_debug\_rembg_worker_YYYYMMDD_HHMMSS.log` |
| Lovart 生图日志 | `E:\Claude code\lovart-official\run_official_v53.log` |
| Lovart 失败任务 | `E:\Claude code\lovart-official\.failed_tids.json` |
| Lovart 处理记录 | `E:\Claude code\lovart-official\.processed_track.json` |
| 上款进度 | `D:\Semems WB\.wb_upload_progress.json` |
| 已上款数据 | `D:\Semems WB\.wb_online_listed.json` |
| check_rem 守护日志 | `engine/check_rem_daemon.log` |

**排错口诀**：服务起不来先看 `bridge.log`；去背页出不来先看 `check_rem` 相关日志；上款/核价/报活动问题先去对应外部脚本日志找原因。

---

## 9. 后续工作建议（按优先级）

1. **统一版本号**：把 `lovart_bridge.py` 横幅、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md` 统一为 v2.4.1，并补 CHANGELOG 条目。
2. **审查并提交当前 4 个未提交文件**：确认修改正确后 `git add -A && git commit`。
3. **收尾建议零售价功能**：
   - 确认 `E:\Claude code\WB Lovart\建议零售价.js` 已支持 `--no-close-browser`
   - 在真实 Edge + Temu 环境下跑一遍 `/retail_price`
   - 决定是否统一 retail_price 日志格式与 activity/pricing
4. **清理旧日志**：`bridge.log.*.bak` 已经非常多，可定期删除或按日期归档。
5. **如需新功能**：先读 `docs/superpowers/plans/` 和 `docs/superpowers/specs/` 里的计划文档；项目已用 Subagent-Driven Development 模式管理。

---

## 10. 必读文档索引

| 文档 | 路径 | 读它来了解什么 |
|------|------|----------------|
| 本接手说明 | `C:\Users\Administrator\ZCodeProject\交接说明_Kimi客户端.md` | 整体状态、坑、下一步 |
| 架构与关键决策 | `C:\Users\Administrator\ZCodeProject\ARCHITECTURE.md` | 系统架构、血缘引擎、UID 溯源、历次关键改进 |
| 复现与回滚 | `C:\Users\Administrator\ZCodeProject\REPRODUCIBILITY.md` | 仓库列表、依赖、目录约定、版本回滚 |
| 功能清单 | `C:\Users\Administrator\ZCodeProject\SKILL.md` | 当前支持的功能、启动方式、工作流 |
| 版本日志 | `C:\Users\Administrator\ZCodeProject\CHANGELOG.md` | 每次版本改了什么 |
| 元数据模块 | `C:\Users\Administrator\ZCodeProject\lib\wb_meta.py` | UID/group_id 怎么生成和管理 |
| 零售价格集成计划 | `C:\Users\Administrator\ZCodeProject\docs\superpowers\plans\2026-07-07-retail-price-integration.md` | 最新未完成的功能是怎么设计的 |
| 零售价格设计 | `C:\Users\Administrator\ZCodeProject\docs\superpowers\specs\2026-07-07-retail-price-design.md` | 需求背景、接口、前端设计 |

---

## 11. 给 Kimi 客户端的一句话

> 这是一个「用 Flask 桥接多个外部自动化脚本」的本地控制面板项目，核心代码在 `lovart_bridge.py`，数据约定在 `D:\Semems WB\`，元数据共享模块是 `lib/wb_meta.py`。改任何功能前先查 `bridge.log`，改去背相关先查 `engine/check_rem.py`，改上款/核价/报活动相关还要同步看 `E:\Claude code\` 下的外部仓库。
