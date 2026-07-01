# Lovart-WB 一体化控制系统 — 更新日志

## v2.0 (2026-07-02) — 血缘引擎 + 批量去背

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

- 同名文件后缀自动大写（b→B, w→W, bw→BW）
- 预览图不再使用 PIL 缩放，直接返回原图
- 状态持久化：重启桥接后上次任务状态可见
- 中文变体文件（`黑B_cut.png`）不再误报缺 AI 图
- `_render_html` 模板 f-string 转义修复
- 浏览器统一使用 Chrome（Edge 不再弹出）

### 🏗️ 架构

- `lovart_bridge.py` v2.0 — Flask HTTP Bridge
- `lovart_control.html` — 控制面板前端
- `lovart_bridge.bat` — 一键启动脚本
- 统一端口：Bridge 8765，check_rem 8766

---

## v1.0 (2026-07-01) — 初始版本

### 基础功能

- Flask Bridge 服务器，REST API
- HTML 控制面板，INBOX 图片网格预览
- 勾选图片启动 Lovart 生图
- UID + group_id 分配系统
- Registry v3（`.image_registry.json`）
- Lovart 管线集成
- 文件回收站（本地回收站 + 系统回收站）
- 一键启动脚本
