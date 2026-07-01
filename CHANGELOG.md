# Lovart-WB 一体化控制系统 — 更新日志

## v2.0 (2026-07-02) — 血缘引擎 + 批量去背 + JS独立化

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
├── lovart_bridge.py        v2.0  Flask HTTP Bridge
├── lovart_control.html     v2.0  控制面板前端
├── lovart_bridge.bat       v2.0  一键启动脚本
├── CHANGELOG.md            v2.0  更新日志
├── ARCHITECTURE.md         v2.0  系统架构文档
├── SKILL.md                v2.0  技能定义
└── .gitignore

D:\Semems WB\04_OS\engine\
├── check_rem.py            v2.0  AI vs 去背 对比预览
└── check_rem.js            v2.0  独立 JavaScript（解决转义问题）
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
