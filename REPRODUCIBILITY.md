# Y2 控制台 — 复现与回滚指南

> 对应版本: `lovart_bridge.py v2.3.8` + `run_official_v53.py v6.1` + `wb_listing.py v1.3.13`
> 最后更新: 2026-07-04

---

## 1. 代码仓库

| 仓库 | 本地路径 | 远程 | 分支 | 作用 |
|------|----------|------|------|------|
| ZCodeProject | `C:\Users\Administrator\ZCodeProject` | `https://github.com/jordan23kevin/ZCodeProject.git` | `master` | Y2 控制台 Bridge + 前端页面 |
| lovart-official | `E:\Claude code\lovart-official` | `https://github.com/jordan23kevin/lovart-official.git` | `main` | Lovart 生图管线 |
| ps（贴图流水线） | `E:\Claude code\ps` | （未纳入本次推送） | — | PS 贴图 + BW 合成 |
| wb上款 | `E:\Claude code\wb上款` | `https://github.com/jordan23kevin/wb-listing.git` | `main` | 批量上款 |

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
```

### 2.2 安装/检查依赖

```bash
pip install flask Pillow requests pywin32 pythoncom numpy
```

### 2.3 配置检查

- 提示词文件必须存在：`E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
- `config/settings.py` 中的 `PROMPT_FILE` 指向上述文件。
- 密钥文件：`E:\Claude code\lovart-official\config\keys.json`（不提交到 Git，本地保留）。
- Photoshop 路径与各脚本中的 `PS_EXE` 一致（当前为 `D:\Program Files\Adobe Photoshop 2025 v26.0\Adobe Photoshop 2025\Photoshop.exe`）。

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
# ZCodeProject
cd C:\Users\Administrator\ZCodeProject
git fetch origin --tags
git checkout v2.3.8

# lovart-official
cd "E:\Claude code\lovart-official"
git fetch origin --tags
git checkout v6.1

# wb上款
cd "E:\Claude code\wb上款"
git fetch origin --tags
git checkout v1.3.13
```

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

## 6. 本次更新关键点（v2.3.8 / wb上款 v1.3.13）

| 问题 | 根因 | 解决方案 | 文件位置 |
|------|------|----------|----------|
| 上款进度显示 `280 / 41 (683%)` | `/api/upload/progress` 把历史已完成记录算进当前批次 | done_count / total_count 只统计当前选中的款号 | `lovart_bridge.py` |
| 上款页面进度信息不清晰 | 只显示 `done / total (pct%)` | 改为 `已上款 X / 总 Y  失败 Z  剩余 W` | `upload.html` |
| AI 生图对比页缓存旧图 | 重新生图后文件名不变，浏览器用缓存 | 缩略图/原图 URL 追加 `t=<mtime>` | `lovart_bridge.py` / `ai_review.html` |
| Edge 上款时弹前台 | Chromium CDP 命令激活窗口 | wb上款 v1.3.9+ 透明隐藏 + HWND_BOTTOM（v1.3.13 文档同步） | `wb上款 browser_kernel/service/edge_service.py` |
| 豆包传图失败 | 隐藏窗口后标签未激活，文件 input change 不触发 | prepare_edge + CDP activate + bring_to_front | `wb上款 wb_listing.py` |
| 登录态误判卡住 | LoginGuard DOM 信号太严格 | 增加 URL 兜底 | `wb上款 browser_kernel/auth/login_guard.py` |
| 文档版本不一致 | 代码迭代中文档未及时同步 | v2.3.8 / v1.3.13 统一所有 SKILL/CHANGELOG/ARCHITECTURE/REPRODUCIBILITY | 所有仓库根文档 |

---

## 7. 关键配置与外部依赖

- **Lovart API Key**: `E:\Claude code\lovart-official\config\keys.json`
- **提示词文件**: `E:\Claude code\lovart-official\config\POD AI VIRAL FACTORY v3.md`
- **Python 依赖**: `flask`, `Pillow`, `requests`, `pywin32`, `pythoncom`, `numpy`
- **Photoshop**: `D:\Program Files\Adobe Photoshop 2025 v26.0\Adobe Photoshop 2025\Photoshop.exe`
- **美图秀秀**: 去背流程需要，运行期间会接管屏幕

---

## 7. 调试日志

- Bridge 日志：`C:\Users\Administrator\ZCodeProject\bridge.log`
- Lovart 日志：`E:\Claude code\lovart-official\run_official_v53.log`（若脚本有输出）
- 失败任务：`E:\Claude code\lovart-official\.failed_tids.json`
- 处理记录：`E:\Claude code\lovart-official\.processed_track.json`

---

## 8. 提交历史

```bash
# ZCodeProject
git log --oneline -5

# lovart-official
cd "E:\Claude code\lovart-official" && git log --oneline -5
```
