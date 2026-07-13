# Y2 控制台 — 复现与回滚指南

> 对应版本: `lovart_bridge.py v2.4.2` + `peiyi_mask.py v1.5.2` + `run_official_v53.py v6.1.1` + `wb_listing.py v2.2.2` + `check_online_listed.py v1.3.20` + `temu-hengjia-engine v5.2.1` + `temu-activity-engine v4.1.3` + 贴图流水线 `ps v2.0/v2.4/v2.5` + `white_t_mockup v1.8.0` + `04_OS wb_naming v2.3.0`
> 最后更新: 2026-07-13
> 贴图流水线已从 Photoshop 依赖全面转为纯软件（PIL），详见 `E:\Claude code\ps\PIPELINE.md`
> 遮罩生成子系统（peiyi_mask / peiyi_correct）新增 torch/transformers/scipy/skimage 依赖，详见第 12 节

---

## 1. 代码仓库

| 仓库 | 本地路径 | 远程 | 分支 | 作用 |
|------|----------|------|------|------|
| ZCodeProject | `C:\Users\Administrator\ZCodeProject` | `https://github.com/jordan23kevin/ZCodeProject.git` | `master` | Y2 控制台 Bridge + 前端页面 |
| lovart-official | `E:\Claude code\lovart-official` | `https://github.com/jordan23kevin/lovart-official.git` | `main` | Lovart 生图管线 |
| ps（贴图流水线） | `E:\Claude code\ps` | `https://github.com/jordan23kevin/ps-compositing.git` | `master` | 纯软件平铺贴花 + BW 合成（PIL，无 PS 依赖） |
| white_t_mockup（模特图位移贴图引擎） | `E:\Kimi Code\white_t_mockup` | `https://github.com/jordan23kevin/ZCodeProject.git` | `white-t-mockup` | 模特图 gradient 位移贴图（纯软件，与 Bridge 同仓不同分支） |
| 04_OS（贴图引擎与命名） | `D:\Semems WB\04_OS` | `https://github.com/jordan23kevin/semems-wb-04os.git` | `master` | wb_naming 命名规则 + w_mockup_extra 模特图渲染 |
| wb上款 | `E:\Claude code\wb上款` | `https://github.com/jordan23kevin/wb-listing.git` | `main` | 批量上款 |
| temu-hengjia-engine | `E:\Claude code\Temu自动化\核价` | `https://github.com/jordan23kevin/temu-hengjia-engine.git` | `main` | Temu 批量核价引擎 |
| temu-activity-engine | `E:\Claude code\Temu自动化\报活动` | `git@github.com:jordan23kevin/temu-baohuodong.git` | `master` | Temu 批量报活动 |

---

## 2. 一键复现步骤

### 2.1 拉取代码

```bash
# Bridge / 控制台
cd C:\Users\Administrator\ZCodeProject
git pull origin master

# Lovart 管线
cd "E:\Claude code\lovart-official"
git pull origin main

# wb上款
cd "E:\Claude code\wb上款"
git pull origin main

# Temu 核价引擎
cd "E:\Claude code\Temu自动化\核价"
git pull origin main

# Temu 报活动引擎
cd "E:\Claude code\Temu自动化\报活动"
git pull origin master

# 贴图流水线（平铺贴花 + BW 合成，纯软件）
cd "E:\Claude code\ps"
git pull origin master

# 模特图位移贴图引擎（与 Bridge 同仓，独立分支）
cd "E:\Kimi Code"
git pull origin white-t-mockup

# 贴图引擎与命名规则
cd "D:\Semems WB\04_OS"
git pull origin master
```

### 2.2 安装/检查依赖

```bash
# Bridge / 控制台 / 去背预览 / 贴图流水线共用
pip install flask Pillow requests pywin32 pythoncom numpy

# white_t_mockup（模特图位移贴图）额外需要 OpenCV
# 注意：本机 cv2 来自 E:/python_packages（系统包目录），运行时需注入：
#   set PYTHONPATH=E:/python_packages;E:/Kimi Code
pip install opencv-python

# 遮罩生成子系统（peiyi_mask / peiyi_correct）额外依赖
# torch / torchvision / transformers / scipy / scikit-image
# 注意：cv2 在本机来自 E:/python_packages；运行时必须注入 PYTHONPATH=E:/python_packages
pip install torch torchvision transformers scipy scikit-image opencv-python
```
> 贴图流水线（ps / white_t_mockup / 04_OS）已不再依赖 `pywin32` / `pythoncom` / Photoshop；
> `pywin32` / `pythoncom` 仅 Bridge 的窗口操作（夸克/Edge 误触防护）与美图去背流程使用。
> 遮罩生成涉及深度学习推理，首次运行需联网拉取 BiRefNet / fashn-human-parser 权重到 `~/.cache/huggingface`；
> 之后可离线（`local_files_only=True` 优先缓存）。GPU 可选，CPU 推理白W2 等单张约数秒。

### 2.3 配置检查

- 提示词文件必须存在：`E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
- `config/settings.py` 中的 `PROMPT_FILE` 指向上述文件。
- 密钥文件：`E:\Claude code\lovart-official\config\keys.json`（不提交到 Git，本地保留）。
- 贴图流水线已纯软件化，**不再需要 Photoshop**；重装 / 迁移 Photoshop 不影响贴图。
- 模特图贴图引擎 `white_t_mockup` 运行前需设置 `PYTHONPATH=E:/python_packages;E:/Kimi Code`（cv2 在 E:/python_packages）。
- 美图秀秀仍用于去背流程（与贴图无关）。

### 2.4 启动

```bash
# 方式一：一键启动（推荐）
双击 D:\Semems WB\01_INBOX\lovart_bridge.bat

# 方式二：手动启动 Bridge
cd C:\Users\Administrator\ZCodeProject
python lovart_bridge.py

# 方式三：手动启动去背预览
cd D:\Semems WB\04_OS\engine
python check_rem.py
```

浏览器访问：
- Y2 控制台：`http://127.0.0.1:8765`
- AI 生图对比：`http://127.0.0.1:8765/ai-review`
- Temu 核价：`http://127.0.0.1:8765/pricing`
- Temu 报活动：`http://127.0.0.1:8765/activity`
- 去背预览：`http://127.0.0.1:8766`

---

## 3. 目录约定

```
D:\Semems WB\01_INBOX          # 原图入口
D:\Semems WB\02_PROJECTS       # 项目目录
D:\Semems WB\02_PROJECTS\DXxxxx\01_AI      # AI 生成图
D:\Semems WB\02_PROJECTS\DXxxxx\02_REM_BG  # 去背图
D:\Semems WB\02_PROJECTS\DXxxxx\03_UPLOAD  # 贴图成品
D:\Semems WB\05_META           # UID / group_id 元数据（与图片分离）
D:\Semems WB\_ai_trash         # AI 图回收站
D:\Semems WB\.image_registry.json       # Bridge registry v4
D:\Semems WB\.wb_rembg_registry.json    # 去背 registry
```

---

## 4. 版本回滚

### 4.1 回滚到上一个版本

```bash
# 查看历史提交
git log --oneline -10

# 软回滚（保留工作区修改）
git reset --soft HEAD~1

# 硬回滚（丢弃工作区修改，慎用）
git reset --hard HEAD~1
```

### 4.2 回滚到指定 Tag

如果已打 Tag（推荐）：

```bash
# ZCodeProject（Bridge / 控制台）
cd C:\Users\Administrator\ZCodeProject
git fetch origin --tags
git checkout v2.3.22

# lovart-official
cd "E:\Claude code\lovart-official"
git fetch origin --tags
git checkout v6.1.1

# wb上款
cd "E:\Claude code\wb上款"
git fetch origin --tags
git checkout v2.2.1
```

### 4.3 回滚到「贴图流水线纯软件化」里程碑（2026-07-12）

本次将贴图流水线从 Photoshop 全面改为纯软件。四个相关仓库在该里程碑打了统一 Tag，便于一键回滚到该状态：

| 仓库 | 本地路径 | 分支 | 里程碑 Tag | 回滚命令 |
|------|----------|------|-----------|----------|
| ZCodeProject（Bridge） | `C:\Users\Administrator\ZCodeProject` | `master` | `pipeline-2026-07-12` | `git checkout pipeline-2026-07-12` |
| ps（贴图流水线） | `E:\Claude code\ps` | `master` | `pipeline-2026-07-12` | `git checkout pipeline-2026-07-12` |
| white_t_mockup（模特图引擎） | `E:\Kimi Code` | `white-t-mockup` | `pipeline-2026-07-12-wtm` | `git checkout pipeline-2026-07-12-wtm` |
| 04_OS（命名/引擎） | `D:\Semems WB\04_OS` | `master` | `pipeline-2026-07-12` | `git checkout pipeline-2026-07-12` |

> 回滚后执行第 2.4 节的启动步骤（双击 `D:\Semems WB\01_INBOX\lovart_bridge.bat`）即可恢复服务。
> 如要回到「仍依赖 Photoshop 的旧贴图流水线」，需在上述每个仓库回退到 `pipeline-2026-07-12` Tag 之前的提交（见各仓库 `git log`）。

### 4.3 回滚后重启

```bash
# 1. 停止 Bridge（若还在运行）
# 2. 重新拉取或 checkout 目标版本
# 3. 重新双击 lovart_bridge.bat 启动
```

---

## 5. 本次更新关键点（v2.3.6 / v6.1）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| 提示词无法热更新 | 提示词硬编码在 `settings.py` | 改为读取 `config/POD AI VIRAL FACTORY v3.md` | `lovart-official/config/settings.py` |
| 重新生图失败但显示完成 | 状态徽章只看完成不看失败数 | `display_status` 区分 completed/partial/error | `lovart_bridge.py` |
| 重新生图错用旧批次原图 | 仅按文件名找源图 | 复制前比较 MD5，冲突时暂移 | `lovart_bridge.py` |
| 重新生图覆盖旧 AI 图 | 输出文件名固定 | 自动递增 `_B2.png` / `_BW2.png` | `lovart_bridge.py` |
| 批量重新生图跨 DX 同名冲突 | `LOVART_REGEN_DX_MAP` 以文件名为 key | key 改为 `(dx, source_file)`，入参校验同名 | `lovart_bridge.py` |
| AI 生图对比页默认显示全部日期 | 前端未按最新日期过滤 | 默认显示最新日期，下拉可选 | `lovart_bridge.py` / `ai_review.html` |
| 日期分类随文件更新乱跳 | 按 AI/去背/贴图文件 mtime 判断日期 | 统一按 DX 文件夹建立日期 `st_ctime` 分类 | `lovart_bridge.py` / `check_rem.py` |
| 点击去背预览无响应 | check_rem print 中 emoji 在 GBK 控制台崩溃 | 移除 emoji + 强制 stdout UTF-8 | `check_rem.py` |
| 去背预览打开慢 | 启动后阻塞等待 scan_projects 90 秒 | 端口 ready 后快速 ping，立即开浏览器 | `lovart_bridge.py` |
| 上款按钮打不开 | 按钮使用 localhost:8765/upload，解析到 IPv6 | 改为相对路径 /upload | `lovart_control.html` |
| 悬停预览图位置乱跳 | 用固定 900x90vh 预估尺寸定位 | 等图片加载后用实际尺寸定位 | `check_rem.js` |
| 去背预览打开慢 | 点击后才启动 check_rem.py | Bridge 启动时守护 check_rem.py 常驻 | `lovart_bridge.py` |
| 去背预览首页加载慢 | 每次请求都全量扫描 | scan_projects 增加 30 秒缓存 | `check_rem.py` |
| 上款页面首屏卡顿 | 1600+ 张缩略图同时加载 | 缩略图 lazy loading + async decoding | `upload.html` |
| 去背预览首次加载慢 | check_rem 冷启动需 16s 全量扫描 | 启动后后台预扫描 warming 缓存 | `check_rem.py` |

---

## 6. 本次更新关键点（v2.3.17 / wb上款 v1.3.23 / Lovart v6.1.1）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| 单张去背后 02_REM_BG 无输出（如 DX0339_W） | 美图保存路径未切换，`_副本.png` 落到 `WB_ROOT/_temp_rembg/save`，check_rem 只扫描 `TEMP_REMBG/{DX}/02_REM_BG` | 新增 `_collect_rembg_results()`，从三个位置扫描 `_cut.png` / `_副本.png` 并归位改名 | `engine/check_rem.py` |
| 批量去背 B/W 被错误跳过 | `/batch-rembg` 用全局 `dx_files` 判断是否含 BW，前一个有 BW 的款污染后续所有款 | 每个 DX 独立判断，只跳过该 DX 自己的 B/W | `engine/check_rem.py` |
| 去背后无法定位问题 | `_rembg_worker.py` 控制台关闭后日志丢失 | worker 输出重定向到 `D:\Semems WB\_debug\_rembg_worker_YYYYMMDD_HHMMSS.log` | `engine/_rembg_worker.py` |
| 批量上款首个款黑T图错传白T位置 | 全局 `选择图片` 按钮顺序与表格行顺序不一致；颜色勾选后 DOM 重排 | 从目标表格行内部定位按钮；重新按颜色解析行索引；上传前颜色校验 | `wb上款/wb_listing.py` |
| 上款进度显示 `280 / 41 (683%)` | `/api/upload/progress` 把历史已完成记录算进当前批次 | done_count / total_count 只统计当前选中的款号 | `lovart_bridge.py` |
| 上款页面进度信息不清晰 | 只显示 `done / total (pct%)` | 改为 `已上款 X / 总 Y  失败 Z  剩余 W` | `upload.html` |
| AI 生图对比页缓存旧图 | 重新生图后文件名不变，浏览器用缓存 | 缩略图/原图 URL 追加 `t=<mtime>` | `lovart_bridge.py` / `ai_review.html` |
| Edge 上款时弹前台 | Chromium CDP 命令激活窗口 | wb上款 v1.3.9+ 透明隐藏 + HWND_BOTTOM（v1.3.13 文档同步） | `wb上款 browser_kernel/service/edge_service.py` |
| 豆包传图失败 | 隐藏窗口后标签未激活，文件 input change 不触发 | prepare_edge + CDP activate + bring_to_front | `wb上款 wb_listing.py` |
| 登录态误判卡住 | LoginGuard DOM 信号太严格 | 增加 URL 兜底 | `wb上款 browser_kernel/auth/login_guard.py` |
| 文档版本不一致 | 代码迭代中文档未及时同步 | v2.3.14 / v1.3.16 / v6.1.1 统一所有 SKILL/CHANGELOG/ARCHITECTURE/REPRODUCIBILITY | 所有仓库根文档 |
| 已上款状态不准确 | 仅依赖 `wb_listing.py` 本地记录 | v2.3.10：从店小秘在线产品页抓取 SKU 提取款号，作为唯一权威来源；v1.3.16 运行时校验 + 终检 | `lovart_bridge.py` / `wb上款/check_online_listed.py` / `wb上款/wb_listing.py` |
| 连续点击反相冲突 | ThreadingHTTPServer 使多个 `/invert-rem` 并发驱动 Photoshop | v2.2.2：单张 + 批量反相统一后台队列串行执行 | `engine/check_rem.py` / `engine/check_rem.js` |
| 反相后自动贴图不可控 | 反相流程内嵌 `_run_sticker_pipeline` | v2.2.3：反相只生成黑版去背图，贴图由用户单独触发 | `engine/check_rem.py` / `engine/check_rem.js` |
| 单张去背点击无反应 | `_rembg_worker.py` 文件缺失，`/rembg` 端点启动工作进程失败 | v2.2.4：补全 `_rembg_worker.py`；`rembg_one_file` 暂存同 DX 全部生成图通过配对预检 | `engine/_rembg_worker.py` / `engine/check_rem.py` |
| 批量贴图中途停止 | `/ps-sticker` 同步阻塞，某款 PS 卡住后前端无法继续 | v2.2.5：PS 贴图统一后台队列 + `/sticker-status` 轮询 + 每步 5 分钟超时 | `engine/check_rem.py` / `engine/check_rem.js` |
| Lovart 只回文字要 concept | 提示词只有规则框架，缺少 concrete request | v6.1.1 自动拼接 `_CONCEPT` + `--- DESIGN RULES ---` | `lovart-official/run_official_v53.py` / `config/settings.py` |
| 图片 URL 提取失败 | 只支持 artifacts 和简单正则 | v6.1.1 支持 artifacts / markdown / 带 query string 链接 | `lovart-official/utils/helpers.py` |
| 无图时无诊断 | 失败只记录 "未找到图片URL" | v6.1.1 新增 `extract_agent_text` 记录 agent 回复 | `lovart-official/utils/helpers.py` / `core/executor.py` |
| API 连接层偶发失败 | POST 只重试 1 次 | v6.1.1 `_request` 统一重试 3 次，幂等重试 | `lovart-official/skills/lovart-skill/agent_skill.py` |

---

## 7. 关键配置与外部依赖

- **Lovart API Key**: `E:\Claude code\lovart-official\config\keys.json`
- **提示词文件**: `E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
- **Python 依赖**: `flask`, `Pillow`, `requests`, `pywin32`, `pythoncom`, `numpy`（Bridge / 去背用）；`opencv-python`（white_t_mockup / 遮罩生成用，cv2 来自 `E:/python_packages`）
- **遮罩生成额外依赖**: `torch`, `torchvision`, `transformers`, `scipy`, `scikit-image`
- **HuggingFace 模型缓存**: `~/.cache/huggingface`（BiRefNet 人像分割权重、`fashn-ai/fashn-human-parser` SegFormer 权重）。首次运行自动下载；之后离线（`local_files_only=True`）可用。重装系统后需重新下载或备份此目录。
- **胚衣素材库**: `D:\Semems WB\03_MATERIAL\<分类>\`（W白 / W黑 / B白 / B黑），遮罩生成输出到同目录 `_mask_versions/<stem>/vNNN/`
- **Photoshop**: 贴图流水线已不再依赖；新装 / 迁移 Photoshop 不影响贴图。仅旧版脚本（`pipeline-2026-07-12` Tag 之前的提交）需要。
- **美图秀秀**: 去背流程需要，运行期间会接管屏幕（与贴图无关）

---

## 7. 调试日志

- Bridge 日志：`C:\Users\Administrator\ZCodeProject\bridge.log`
- Lovart 日志：`E:\Claude code\lovart-official\run_official_v53.log`（若脚本有输出）
- 失败任务：`E:\Claude code\lovart-official\.failed_tids.json`
- 处理记录：`E:\Claude code\lovart-official\.processed_track.json`

---

## 8. 本次更新关键点（v2.3.22）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| Temu 报活动无统一入口 | 报活动脚本独立运行，无 Web 控制台 | Bridge 新增 `/activity` 页面 + `/api/activity/*` 端点，子进程调用 `entrypoint/run.py` | `lovart_bridge.py` / `activity.html` |

---

## 9. 本次更新关键点（v2.3.21）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| WB 上款缩略图黑白错位 | ① `re.sub(r'[^A-Za-z0-9_.-]', '_', filename)` 把 `白`/`黑` 等中文统一替换为下划线，导致缓存文件名冲突；② 前端用源文件 mtime 作为缓存破坏参数，缩略图重建后浏览器仍用旧缓存 | ① safe_name 只替换 Windows 非法字符 `\ / * ? : " < > \|`，保留中文；② `/api/upload/projects` 返回 `thumb_mtime`，前端用其作为缩略图 URL 的 `t` 参数；清空旧缓存 | `lovart_bridge.py::_get_upload_thumb` / `_upload_thumb_path` / `_scan_upload_projects`、`upload.html` |
| 点击上款图片后文件夹不前台弹出 | `os.startfile` 复用已存在的资源管理器窗口时不强制激活 | 新增 `_open_folder_front()`，打开后通过 `win32gui` 查找 `CabinetWClass` 窗口并 `SetForegroundWindow()` | `lovart_bridge.py::_open_folder_front` / `api_open_dx` / `api_open_recycle` |

---

## 10. 本次更新关键点（v2.3.20 / temu-hengjia-engine v5.2.1）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| Temu 核价无统一入口 | 核价脚本独立运行，无 Web 控制台 | Bridge 新增 `/pricing` 页面 + `/api/pricing/*` 端点，子进程调用 `hengjia.py` | `lovart_bridge.py` / `pricing.html` |
| 核价时长页无法完成 | `utils/js_helpers.py` 中 JS 辅助函数每次 `_eval()` 都 `sc.scrollTop = 0` 重置到顶部 | 移除 JS 内部重置，由 `core/engine.py` 入口 `_reset_scroll()` 统一重置；循环调用从当前位置继续 | `temu-hengjia-engine/utils/js_helpers.py` / `core/engine.py` |
| 核价结果散落 | 输出目录不固定 | 统一输出到 `C:/Users/Administrator/Desktop/核价档案`，Bridge 提供下载 API | `lovart_bridge.py` |
| 版本号不一致 | `lovart_bridge.bat` 标题/横幅与 Python 端不一致 | 全部统一为 v2.3.20 | `lovart_bridge.py` / `lovart_bridge.bat` |

---

## 11. 贴图流水线纯软件化（2026-07-12）

将贴图流水线从 Photoshop COM 依赖全面改为纯 PIL / 纯软件，保证重装 / 迁移 Photoshop 后仍能 100% 复现。

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| BW 合成失败，缺 `白BW/黑BW` | Photoshop 2025 缺失旧版私有动作集「正反图」，`app.actionSets` 返回 undefined | 路线 B：用参考图 `DX0481` 像素级 PIL 复刻 `compose_bw_pil`（底图 1340×1785、圆直径 595、正面图宽度贴合圆圈 ≈44.4%、圆心 (1014,1449)、白边 5px、无阴影） | `ps/ps_batch.py` |
| 平铺图贴花依赖 Photoshop | 旧 `place_design.jsx` 走 win32com 调用 PS | 纯 PIL 仿射复刻（trim + 缩放 + 平移 + 绕中心旋转 + normal 合成），与 PS 版像素差 0.3–0.9（JPEG 重编码级） | `ps/wb_sticker_ps.py` |
| 点「贴图」卡在 PS 动作 | `process_black/white.py` 调缺失的 PS 动作 | `bw_synth` 改调 `ps_batch.process_dx`（纯 PIL）；移除 `win32com/pythoncom` 导入与 COM 死代码 | `ps/process_black.py`、`ps/process_white.py` |
| 用户误以为要 50% 缩放 | 口述规格与参考图不符 | 实测反向测量参考图，正面图实际占比 44.4%（宽度贴合圆圈），按此生成的图与 `DX0481` 像素一致 | `ps/ps_batch.py::compose_bw_pil` |
| 模特图贴图颜色失真 / 位移水波纹 | 旧 `multiply` 混合 + 硬死区位移导致折叠重影 | `white_t_mockup` 改 gradient 位移 + `_limit_gradient_2d` 防重影 + 布料同步明度（仅缩放 HSV 的 V）；软死区消除撕裂 | `E:\Kimi Code\white_t_mockup\core.py` |
| 命名不统一，跨脚本解析失败 | 各脚本硬编码命名规则 | 命名唯一出处 `D:\Semems WB\04_OS\engine\wb_naming.py`，生成与解析全局跟随 | `04_OS/engine/wb_naming.py` |

> 复现验证：纯软件重构后，`tasklist` 确认无 Photoshop 进程；DX0641 贴花 + BW 合计 <2 秒；BW 合成单张 0.3 秒。
> 详见 `E:\Claude code\ps\PIPELINE.md`（系统总览、环境依赖、十项问题方案表、100% 复现步骤、回滚）。

---

## 12. 遮罩生成子系统 — 复现与回滚（2026-07-13）

遮罩生成子系统全部位于 `ZCodeProject` 仓库内（`peiyi_mask.py` / `peiyi_correct.py` / `lovart_bridge.py` / `peiyi.html`），与贴图/上款流程共享同一 Bridge，无独立仓库。

### 12.1 一键复现遮罩

```bash
# 1. 确保依赖与模型已就位（见第 2.2 / 第 7 节）
# 2. 启动 Bridge（遮罩页面与 API 随 Bridge 一起生效）
双击 D:\Semems WB\01_INBOX\lovart_bridge.bat
# 3. 浏览器打开 http://127.0.0.1:8765/peiyi → 上传胚衣图 → 点「生成遮罩」

# 命令行独立生成（调试用，需 Python 3.11 + PYTHONPATH）
PY="C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe"
PYTHONPATH=E:/python_packages "$PY" - <<'PY'
import peiyi_mask
res = peiyi_mask.generate_masks(r'D:\Semems WB\03_MATERIAL\W白\白W2.jpg', category='W白')
print(res.get('version'), res.get('body_px'), res.get('occluder_px'))
PY
```

> 改 `peiyi_mask.py` / `peiyi_correct.py` 后由 `_peiyi_worker` 子进程每次新导入，**无需重启 Bridge**；改 `tpl_generator` 内联路径才需重启。

### 12.2 版本级回滚（遮罩本身）

每张胚衣的遮罩都有完整版本链，回滚不影响生产：

- **前端切换**：`peiyi.html` 打开某胚衣 → 版本列表选目标 `vNNN` → 点「使用此版本」(`/api/peiyi/use_version`)，仅更新 `latest.txt` 与生产路径文件。
- **删除废版**：非当前版本可点 🗑 删除 (`/api/peiyi/delete_version`)。
- **物理备份**：`_mask_versions/<stem>/vNNN/` 目录永不自动删除，必要时可手动复制还原。

### 12.3 代码级回滚（整个子系统）

遮罩子系统随 `ZCodeProject` 仓库演进，回滚到任意历史提交即可：

```bash
cd C:\Users/Administrator\ZCodeProject
git log --oneline -- peiyi_mask.py peiyi_correct.py | head -20   # 查看遮罩相关提交
git checkout <commit> -- peiyi_mask.py peiyi_correct.py           # 仅回滚遮罩脚本
# 或整体回退
git reset --hard <commit>                                         # 谨慎：丢弃后续全部改动
```

关键提交（按时间，最新在前）：

| 提交 | 内容 |
|------|------|
| `ac44677` | fix(mask): body shrink 2px + manual import preserve large occluders（v1.5.2） |
| `7d75c71` | fix(import_manual): 用户碰过的 AI 连通域整块替换为用户精确轮廓 |
| `4305247` | fix(peiyi_mask): v1.5.1 收窄 FG_DILATE 25→3/FG_CLOSE 8→5，杜绝遮罩外扩 |
| `7bea79a` | feat(peiyi_mask): v1.5.0 接入 FASHN 语义分割增强（可选，失败回退） |
| `c1ddeee` | feat(peiyi): 导入手动 PS 遮罩合并功能 |
| `df418db` | fix(correct): 预览→确认才存版本 + 删除版本功能 |
| `5eb2e67` | feat(peiyi): 方案B 点选扩散手动校正遮罩 |
| `1a0b13b` | feat(peiyi): 素材库页面新增「遮罩评分总表」+ /api/peiyi/scores |

### 12.4 模型权重备份（迁移/重装必做）

遮罩生成依赖 `~/.cache/huggingface` 下的 BiRefNet 与 fashn-human-parser 权重。重装系统或换机前请备份该目录，否则首次运行需联网重新下载：

```bash
# 备份
robocopy /E "%USERPROFILE%\.cache\huggingface" "D:\Semems WB\_backup_hf_cache"
# 恢复（到新机同名用户目录下）
robocopy /E "D:\Semems WB\_backup_hf_cache" "%USERPROFILE%\.cache\huggingface"
```

---

## 9. 提交历史

```bash
# ZCodeProject
git log --oneline -5

# lovart-official
cd "E:\Claude code\lovart-official" && git log --oneline -5

# temu-hengjia-engine
cd "E:\Claude code\Temu自动化\核价" && git log --oneline -5

# temu-activity-engine（本地项目）
cd "E:\Claude code\Temu自动化\报活动" && git log --oneline -5
```
