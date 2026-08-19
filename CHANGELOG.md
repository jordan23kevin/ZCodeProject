# Y2 一体化控制系统 — 更新日志

## engine 副本 v2.6.5 (2026-08-19) — 单面款批量贴图黑白专用 cut 路由修复

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.5 + `engine/w_mockup_extra.py` v2.6.1。
- 卫衣单面款批量贴图黑T 时用专用图时用通用图（碰 `cuts[:1]` 运气）→ 修复：base cut 固定取通用，`plan_single_side_jobs` 按颜色自动选专用 cut（黑T→_黑*、白T→_白*、英文色→通用）。
- 详见 04_OS/docs/CHANGELOG.md v2.6.5。

## engine 副本 v2.6.4 (2026-08-19) — 卫衣反黑/反白专用贴图

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.4。
- `_run_one_sticker` 平铺流程：卫衣（hoodie）跳过 process_black.py / process_white.py（T恤 老胚衣脚本），反黑/反白专用 cut 由 ps_sticker_one（ps 链 v2.6.2）统一处理——黑胚衣用黑贴图、白胚衣用白贴图、英文色用默认。
- 详见 04_OS/docs/CHANGELOG.md v2.6.4。

## engine 副本 v2.6.3 (2026-08-19) — 「仅本张」B 面源 cut 修复

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.3。
- `_resticker`：BW/WB 款 B 面成品点「仅本张」之前报"缺少源去背图"无声失败（`BW_cut` 只加入 W 面候选）；现不分面一律加入 BW cut 候选，B 面黑白+英文色全部可重贴。
- 详见 04_OS/docs/CHANGELOG.md v2.6.3。

## engine 副本 v2.6.2 (2026-08-19) — 「重新贴图（仅本张）」品类正确化

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.2。
- `_resticker` flat 分支修复两条 T恤 泄漏路径：① 黑白专用 cut 写死 T恤 老胚衣（`D:\Semems\1胚衣\黑正2.jpg`）→ 统一走素材库五参（卫衣=白W2/黑W2…）；② 英文色平铺图 `flat_torso` KeyError → 用 ps 链 `_flat_torso_paths`（全部颜色）。仅 T恤 黑白专用 cut 保留旧行为。
- 详见 04_OS/docs/CHANGELOG.md v2.6.2。

## peiyi_correct v1.8.2 (2026-08-19) — 手动遮罩导入兼容英文色带空格胚衣名

- `peiyi_correct.py` `import_manual_mask`：manual 探测候选扩展为 6 个——素材目录 `{stem}_manual.png` / `{stem去空格}_manual.png` + `_mask_versions/{stem}` / `_mask_versions/{stem去空格}` 下的 `_manual.png` 与 `.png`。
- 背景：英文色胚衣名带前导空格（` B2.jpg` → stem=` B2`），此前探测 ` B2_manual.png`，而用户手动保存的遮罩是不带空格的 `B2_manual.png` → 报"未找到手动遮罩文件，请保存为 B2_manual.png 到素材目录"（文件明明存在）。
- 验证：`import_manual_mask("D:\Semems Hoodie\03_MATERIAL\B Melon Orange\ B2.jpg")` → 找到 `B2_manual.png`、合并归档 v002 成功（B Melon Orange 素材目录）。
- 注：ps 链 `wb_sticker_ps._apply_manual_top` 与 `white_t_mockup/core.py` 同步同款 strip 兼容（ps v2.6.0）。

## engine 副本 v2.6.1 (2026-08-19) — 03_UPLOAD 成品按衫色分行支持全部颜色

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.1。
- `_upload_detail`：成品按衫色分行扩展到全部颜色——黑/白优先，其余（蜜瓜橙/孔雀蓝…）各自成行，英文色不再堆「其他」；行内正/背/BW 横排并排。
- T恤 行为不变；bridge 本体未改动（仍 v2.6.1）。

## engine 副本 v2.6.0 (2026-08-19) — 卫衣贴图出全部带五参颜色

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.6.0、`engine/w_mockup_extra.py` v2.6、`engine/wb_naming.py` 颜色体系扩展。
- **卫衣 all_colors**：贴素材库该面所有带五参的颜色（W 系 10 色、B 系随五参动态），每色平铺+模特各 1 张；英文色经 `_EN_COLOR_TO_CN` 映射中文色名，成品 `HX0001_W蜜瓜橙T.jpg` / `HX0001_蜜瓜橙W.jpg`。
- `wb_naming.COLOR_NAMES`：白/黑 + 蜜瓜橙/淡黄色/蓝绿色/灰蓝色/孔雀蓝/浅黄色/草绿色/肉粉色；`classify` 支持中文色名解析。
- T恤 行为不变（only_color 白/黑 路由）。
- bridge 本体未改动（仍 v2.6.1）。

## engine 副本 v1.14 (2026-08-19) — wb_naming 卫衣平铺判定通用化

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/wb_naming.py` 卫衣平铺判定改为通用规则 **`stem.endswith("2")`**。
- 卫衣素材库**全部 20 个颜色文件夹**的「2 号图」均为平铺胚衣（W=正面、B=背面；1 号=模特），覆盖白/黑 + 8 英文色（`W2/B2`），新增颜色无需改名单。
- 全库扫描验证：20 张 2 号图全部识别为平铺、20 张 1 号图为模特，0 不一致；T恤 名单不受影响。
- `engine/check_rem.py`/`engine/w_mockup_extra.py` 未改动（仍 v2.5.1 / v2.5，resticker 与贴图规划调 `is_flat_stem` 自动跟随新规则）。
- bridge 本体未改动（仍 v2.6.1）。

## engine 副本 v2.5.1 (2026-08-19) — 卫衣「2 号图」识别为平铺胚衣

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.5.1、`engine/w_mockup_extra.py` v2.5、`engine/wb_naming.py` 平铺名单品类化。
- **wb_naming 平铺胚衣名单按品类**：T恤=白W11/黑W11/白B12/黑B7；卫衣=各颜色文件夹 2 号图（白W2/黑W2/白B2/黑B2，用户确认）。新增 `flat_stems(cat)`/`flat_mandatory(role,color,cat)`，`is_flat_stem` 按品类判断；原常量保留兼容。
- 卫衣单面款贴图固定出平铺图（`HXxxxx_W黑T.jpg` 等，2 号胚衣）+ 随机 1 张模特图，与 T恤 行为一致。
- 配套：ps 仓库 `config.py` `FLAT_TORSO` 品类化（卫衣=白W2 等，ps-compositing 提交）。
- bridge 本体未改动（仍 v2.6.1）。

## engine 副本 v2.5.0 (2026-08-19) — 页面标品类 + 贴图素材按品类（SEMEMS_ROOT）

- 与 04_OS 生产副本字节一致（协议硬规则②）：`engine/check_rem.py` v2.5.0、`engine/w_mockup_extra.py` v2.4。
- **页面标品类**：卫衣实例(8767)标题/`<h1>` 显示「（卫衣）」，T恤实例(8766)显示「（T恤）」，搜索框 placeholder 用 HX/DX。
- **贴图素材按品类**：`check_rem.py` 启动注入 `SEMEMS_ROOT=当前品类根`；`w_mockup_extra.py` 的 `MATERIAL_DIR = SEMEMS_ROOT/03_MATERIAL`（卫衣自动用 `D:\Semems Hoodie\03_MATERIAL`），修复卫衣贴图错用 T恤 胚衣。
- 配套：ps 仓库 `config.py` 的 `SOURCE_BASE`/`MATERIAL_BASE` 同读 SEMEMS_ROOT（ps-compositing 提交）。
- bridge 本体未改动（仍 v2.6.1）。

## engine/check_rem.py 副本 v2.4.0 (2026-08-19) — 批量去背按品类注入 REM_PREFIX

- 与 04_OS 生产副本字节一致（协议硬规则②）。修复卫衣「批量去背」不弹美图：`batch_rembg` 调美图前注入 `REM_PREFIX=PREFIX`（DX/HX），否则美图脚本拿默认 DX 前缀扫不到 HX* 暂存直接退出；单张重去背此前已有注入，本次对齐。
- bridge 本体未改动（仍 v2.6.1）；本提交仅同步 `engine/check_rem.py` 副本。

## v2.6.1 (2026-08-19) — 多品类去背预览实例独立（修复卫衣串到 T恤）

- **问题**：Temu 工作台点「去背预览」选卫衣标签却打开 T恤 去背预览页。根因：前端 `launchCheckRem()` 硬编码 8766、后端 `check_rem.py` 写死 DX/T恤根、bridge 守护只拉一个 8766。
- **改动**：
  - `lovart_bridge.py` 守护线程改为 `_CHECK_REM_INSTANCES=[("wb",8766),("hoodie",8767)]` 双实例自愈；`/api/launch-check-rem` 接收 `cat` 返回对应端口；AI 生图完成刷新通知按品类端口分发。
  - `lovart_control.html` 的 `launchCheckRem()` 按 `IS_HOODIE` 开 8766/8767 并传 `cat`。
  - `engine/check_rem.py`（与 04_OS 副本字节一致）支持 `--cat/--port`，扫描/校验按品类前缀（DX/HX）隔离。
  - `wb_meitu_batch.py` 扫描/数字提取/自动命名读 `REM_PREFIX` 环境变量（缺省 DX，卫衣 HX）。
- **验证**：wb@8766 命中 2795 DX 款、hoodie@8767 命中 0 款且互不可见；四端口（8765/8766/8767/8777）均 200。

## v2.6.0 (2026-08-07) — Temu 流量加速器批量开启子系统

- **功能**：控制台新增「🚀 流量加速」页面（`/traffic` + `traffic.html`）。登录进入 flux-analysis 后点「好了」，脚本接管：逐页 全选 → 批量开启 → 抽屉内按**核价底价规则**选档位（P−L≥底价选最大让价；破价≤10 元选最少让价；破价>10 元判不通过记录 SPU）→ 自动提交（含 MDL 确认框）→ 翻下一页直到最后。每条记录实时写入 `E:\Kimi Code\temu分析\流量加速器记录.xlsx`（openpyxl）。
- **部分通过处理**：关抽屉 → 按 SPU 只勾选通过的商品 → 重开抽屉选档提交；全部不通过则跳过本页；价格不通过的 SPU 汇总展示在页面上由人工处理。
- **停止机制**：`TRAFFIC_STOP` 全局 Event + `/api/traffic/stop` + 前端「⏹ 停止」按钮，当前步骤结束后安全退出，已提交的页不受影响。
- **翻页策略**：已开启商品不离开列表，每轮必点「下一页」，杜绝重复全选触发「部分商品不可开启」弹窗（该弹窗出现时也自动点「过滤并继续」）。
- **僵尸抽屉修复（关键）**：抽屉关闭后元素带 transform 滑出屏幕右侧仍留 DOM，重开后 `querySelector` 第一个匹配会拿到旧抽屉，导致选档/提交/取消全打错目标。所有抽屉操作统一改为选「与视口相交 >50px 的可见抽屉」（`_TRAFFIC_VISIBLE_DRAWER_FIND_JS`），`_traffic_select_spus` 排除抽屉内行。
- **关抽屉可靠性**：真实点击（不加 force，等按钮稳定，防坐标抖动点空 + 绕开 isTrusted 拦截）→ JS 点击 + 二次确认弹窗处理 → 刷新兜底（刷新前 dump 弹窗诊断）。弹窗选择器补 `[class*='MDL']`（Temu 弹窗非 Modal/Dialog），并跳过「确认要批量开启流量加速器吗」提交确认框防误提交。
- **记录文件**：CSV 改 xlsx 解决乱码/单列问题，存放 `E:\Kimi Code` 不放 C 盘。
- **启动脚本**：`lovart_bridge.bat` v2.4.0 改为先杀 8765/8766 旧进程再启动，保证加载最新代码。
- **详细文档**：方法实现与全部踩坑记录见 `docs/traffic_accelerator_automation.md`。

## v2.5.1 (2026-08-05) — 强制重新上款同步清除标题缓存

- **问题**：「强制重新上款」只删除 `已上款货号_wb.md` 记录，但 `wb_listing.py` 命中 `标题缓存_wb.md` 会跳过豆包，旧标题被原样复用，新提示词（v6）不会生效。
- **改动**：`/api/batch-upload` force 分支新增 `_remove_from_title_cache(dx_list)`，删已上款记录的同时清除对应 SKU 的标题缓存块，强制重新走豆包用最新提示词生成标题；接口返回新增 `cache_removed` 字段，提示语标明清缓存数量。
- **配套**：wb上款侧 `wb_listing.py` 豆包提示词已升级 v6（英文 170-180 字符硬区间、印花细节提取、句骨架+正反示例、输出自检）；`clean_en_punctuation()` 新增连字符/短横线变体（`- ‐ ‑ – — ― −`）清洗兜底；新增 `strip_foreign_letters()` 外语字母清洗（变音字母转 ASCII，希腊/西里尔/日文等删除），`validate_titles` 加 4.6/4.7 校验保证触发自动修复。

## v2.5.0 (2026-07-28) — 价格申报视角批量处理子系统（Temu 待卖家确认）

> 在 Y2 控制台新增「📉 价格申报」独立页面，自动按**核价底价**批量处理 Temu「待卖家确认」列表里的调价单。
> 涉及文件：`lovart_bridge.py`（+1013 行：ORDER_PRICE_FLOOR / ORDER_PRICE_JS / _op_* 流程 / 5 个 API 端点 / 后台线程）、
> `order_price.html`（新页面）、`lovart_control.html`（导航按钮）。

### ✨ 新功能

- **只读扫描预览**（`/api/order_price/scan`）：不点任何按钮，按核价底价给出 `接受/拒绝/跳过` 汇总，并逐站展示
  `核价底价 / 接受最低价 / 拒绝最高价`，让用户在自动执行前先核对。
- **自动接受（≥底价）**（`/api/order_price/auto`）：仅对「建议价 ≥ 核价底价」的订单逐条 `点「调整」→ 弹窗点「确认」`，
  每条处理完才进下一条；低于底价的保持原样（留人工）。后台线程执行，前端每 600ms 轮询 `/api/order_price/status`，
  **每通过一条立刻实时列出通过价格**。
- **批量拒绝（<底价）**（`/api/order_price/reject`）：**逐个勾选**低于底价的订单（绝不点全选），点「批量拒绝」→
  右侧面板逐行填原因「价格过低」→ 点面板外「拒绝」→ 最终「拒绝调价」确认弹窗点「拒绝」真正提交。
- **核价底价字典 `ORDER_PRICE_FLOOR`**：与 Temu 核价仓 `PRICE_MAP` 对齐，含意大利 115（2026-07-27 用户确认加入）。
- **共用 Edge（端口 9222）**：复用 `_ensure_edge_cdp`，自动连/起共用调试端口的 Edge，绝不另开第二个 Edge；
  进入页面自动点「待卖家确认」+ 设每页 200 条。
- **欧洲价格格式兼容**：`_parse_price` 正确处理 `€ 60,50`（逗号小数）、`1.234,56`、`1,234.56`、`1,234` 等格式。

### 🐛 关键修复（开发过程中踩坑，详见 `docs/order_price_automation.md`）

| 问题 | 根因 | 解决方案 |
|---|------|----------|
| 自动接受时确认弹窗叠加死循环（点一次「调整」弹一个确认框，堆了 19 个） | 每轮重扫整页，行未消失就再次点「调整」 | `attempted` 集合记已点订单，每条只点一次；确认弹窗兜底点「取消」清理 |
| 批量拒绝原因填不进（被 Temu 拦下「原因不能为空」） | 面板 textarea 是 React 受控组件，原生 `value` setter 不触发 onChange | 改用 Playwright `textarea.fill("价格过低")` 真实输入，React state 必更新 |
| 原因框「未填满」误判（空 22/33，实际才 3 个） | 最终确认弹窗 DOM 多层嵌套同名 `MDL_` 类，每层 `querySelectorAll('textarea')` 重复匹配 | `_op_reason_fields` 只收右侧面板 `TB_innerRight` 内的 textarea |
| 面板内「拒绝」按钮点不到 | 真正的提交按钮在面板 `TB_innerRight` 之外 | `_op_click_reject` 改为 document 范围找可见「拒绝」按钮（排除「批量拒绝」） |
| 点了「拒绝」却检测不到最终弹窗 | 最终弹窗是 `MDL_` 类，旧 `_op_modal_count` 只认 `modal/Modal/dialog/Dialog` | 新增 `_op_final_modal_present` 单独识别含「拒绝调价」字样的 `MDL_` 弹窗 |
| 最终弹窗提交按钮点不到 | 该弹窗提交按钮文本是「拒绝」不是「确认」 | `_op_click_reject_final` 点「拒绝」按钮（而非 `_op_confirm_modal` 的「确认」） |
| 欧洲逗号小数导致决策全反（德国 `€ 60,50` 被算成 6050） | 直接 `float()` 处理含逗号字符串 | `_parse_price` 按「逗号/点谁是小数位」分情况清洗 |
| 拒绝后列表不刷新、误以为没处理完 | Temu 该列表不会自动刷新，拒绝后数据残留 | 处理完提示用户 **F5 刷新** 后再复核 |

### 验证

- 纯逻辑单测（MockPage 模拟弹窗生命周期）：`attempted` 守卫使每订单「调整」点击次数 = 1，断言通过。
- 实跑：成功将 55 个（立陶宛 29.10 + 意大利 9.30/13.06/37.20 等低于底价单）从「待卖家确认」列表拒绝消失，复核确认。
- `py_compile` 通过；`/order-price` HTTP 200；scan/auto/reject/status 路由均注册。

---

## v2.4.3 (2026-07-13) — DX 文件夹名加角色后缀（W/B/BW）

> 点「开始lovart生图」自动在 `D:\Semems WB\02_PROJECTS` 建 `DX` 文件夹时，按**同组图片类型**在文件夹名后拼角色后缀，一眼区分正面/背面/双面款。
> 涉及文件：`run_official_v53.py`（生成 + 失败重试 + 编号计数）、`lovart_bridge.py`（21 处 DX 正则 + 日志进度解析）、`04_OS/shared/wb_meta.py` 与 `ps/wb_meta.py`（DX 文件夹扫描）。

### ✨ 新功能

- **DX 文件夹名加角色后缀**（取代原「DW/DB/BW 子文件夹」方案，改为更轻量的后缀法）：
  | 同组图片类型 | 文件夹名 | 示例 |
  |---|---|---|
  | 只有正面图(W) | `DX{N}` + `W` | `DX0169W` |
  | 只有背面图(B) | `DX{N}` + `B` | `DX0169B` |
  | 有 BW 图，或同时有 W 和 B（正反同组） | `DX{N}` + `BW` | `DX0169BW` |
  - **编号共用一个序列**：所有图共用 `DX` 编号（`DX0170W`、`DX0171B`、`DX0172BW`… 一个接一个），只在名字后拼后缀；旧的**不带后缀** DX 文件夹继续兼容（正则放行）。
  - **只在同批次内合并**：同一批次里编号一致的 W+B 合并进 `DX{N}BW`；INBOX 编号会复用，因此**不跨批次**去合并旧图（避免把新批次同编号图错塞进旧 DX）。
  - **取消跨批次 partner 复用**：单 B/W 组一律开新 DX，不再通过 hash/文件名找旧 DX 的配对方（根治 DX0455 混入 4 个不同 src_id 事故）。

### 🐛 关键修复

| 问题 | 根因 | 解决方案 |
|---|------|----------|
| 加后缀后系统认不出新文件夹（编号撞车、贴图/BW合成扫不到新图） | 4 个文件共 ~25 处 `^DX\d+$` 正则只认「DX+数字」，不匹配 `DX0169W` | 全部改为 `^DX\d+(?:BW\|B\|W)?$` 放行可选后缀（含 2 份 wb_meta.py 的 DX 扫描） |
| 加后缀后 `dx_num = int(dx_name[2:])` 对 `DX0169W` 报错 | `dx_name[2:]` = `"0169W"` 非整数 | 改为 `int(re.match(r'DX(\d+)', dx_name).group(1))` 只取数字段 |
| 加后缀后生图进度跟踪失效 | 日志解析 `输出到 (DX\d+)/01_AI` 对 `DX0287W` 匹配失败（W 卡在 `DX\d+` 与 `/01_AI` 之间） | 捕获组改为 `(DX\d+(?:BW\|B\|W)?)` 包含可选后缀 |
| 失败重试新建的 DX 不带后缀、与新规则不一致 | `recover_failed` 函数独立分配编号、未加后缀 | 按文件名后缀补加（纯W→W/纯B→B/其余→BW），保持全链路一致 |

### 验证

- 正则单测：`DX0169`/`DX0169W`/`DX0169B`/`DX0169BW` 全识别；`DX0169W` 编号正确提取 `0169`；日志 `输出到 DX0287W/01_AI` 正确解析 `DX0287W`。
- 端到端：在 `02_PROJECTS` 临时建 `DX9999W` → Bridge `/api/upload/projects` 正确列出；删除后消失。

## v2.4.2 (2026-07-13) — 遮罩生成子系统（自动 + 手动校正 + PS 遮罩合并）

> 本版本在「胚衣制作」页新增完整的**人物前景遮挡遮罩生成**能力：自动识别衣服主体（body）与遮挡物（手/戒指/头发/手持物等 occluder），供贴图时把印花藏到这些前景后面，避免「印花盖在手上/戒指/头发上」。
> 涉及文件：`peiyi_mask.py`（v1.5.0→v1.5.2）、`peiyi_correct.py`（新增）、`lovart_bridge.py`（新增 /api/peiyi/* 共 19 个端点）、`peiyi.html`（新增「胚衣制作」页 + 校正抽屉 + 评分总表）、`tpl_generator.py`（`generate_tpl_for_material` 接遮罩生成 _tpl）。
> 接入链路：「生成遮罩」按钮 → `bridge /api/peiyi/mask` → `_peiyi_worker.py mask` → `tpl_generator.generate_tpl_for_material` 生成 `_tpl` 扭曲素材；贴图时 `white_t_mockup` 自动传入 `--occluder`（即 `*_occluder.png`）盖到最上层。

### ✨ 新功能

- **自动遮罩生成（peiyi_mask.py v1.5.2）** — 三阶段流水线：
  1. **BiRefNet 人像分割**（`transformers.AutoModelForImageSegmentation`，人像 matte）→ `person_mask`
  2. **LAB 色度聚类拆分**（`_color_cluster_split`）：把人物区域按 a/b 色度 KMeans 聚类，区分「衣服主体(body)」与「手/头发/首饰/手持物(occluder)」；前景扩展（闭运算+膨胀）包住紧贴人体的杯子/手持物（BiRefNet 常把手持物当非人排除→洞，印花会透杯）
  3. **FASHN 语义分割增强（v1.5.0 可选，失败自动回退）**：`fashn-ai/fashn-human-parser`（SegFormer 18 类）补强——`top`(3)=衣身（更贴合、治 15px 外扩、body 不进最终合成零风险）；`hands/arms/hair/face/jewelry/bag`(戒指)/帽子/围巾=遮挡物。懒加载 + `local_files_only=True` 优先离线缓存，断网/无代理实测 2s 成功；失败自动回退原 BiRefNet+聚类方法，绝不影响遮罩生成。
  - 模型已缓存 `~/.cache/huggingface`，离线可用。
- **版本归档（v1.4）**：每次生成存 `<素材目录>/_mask_versions/<stem>/vNNN/`（5 文件 + `score.json`），`history.json` + `latest.txt`；标准路径始终指向最新，生产不受影响。
  - 5 文件：`*_occluder.png` / `*_occluder_mask.png` / `*_body_mask.png` / `*_parse.png`（绿=衣身 红=遮挡物 可视化）/ `*_alpha.png`
- **评分总表**：`peiyi.html` 顶部「📊 遮罩评分总表」+ 后端 `/api/peiyi/scores`（读 `latest.txt→vNNN/score.json` 汇总，低分排最前标红）。
- **手动校正（peiyi_correct.py，方案 B 点选扩散）**：LAB 色度 + 边缘约束的连通域生长（flood fill），点「② 分层预览」图自动换算到原图坐标，支持「加遮挡 / 加衣身 / 减遮挡」。
- **预览→确认才存版本**：改三步流程——`correct_preview`(不存) → `correct_confirm`(归档) → `correct_cancel`(删临时)；`_working` 临时目录承载预览图，避免点一下就生成废版。
- **版本删除**：`delete_version`（非当前版本可删）。
- **导入手动 PS 遮罩合并（import_manual_mask）**：读取用户保存的 PS 遮罩 PNG（alpha>30 即判定为用户画笔），与 AI 遮罩结合。最终逻辑：找用户画笔**触碰过的 AI 连通域标签 → 整块替换为用户精确轮廓**；AI 没碰的区域保留；`final_body` 限制在 AI 原衣身范围内，防止手动导入反而把衣身撑大。

### 🐛 开发过程中遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 文件/位置 |
|---|------|------|----------|-----------|
| 1 | 自动生成的遮罩比真实物体边缘**粗暴外扩 ~15px**（白W12 手臂、白W11 衣服边界） | `_color_cluster_split` 中 `FG_DILATE_ITERS=25` 把边缘外推过多 | v1.5.1 收窄 `FG_DILATE_ITERS 25→3`、`FG_CLOSE_ITERS 8→5` | `peiyi_mask.py` |
| 2 | 衣身区域整体仍比真实衣服轮廓胖一圈（v024） | 前面一系列膨胀/闭运算累积把边界外推 2–5px | v1.5.2 新增 `BODY_SHRINK_ITERS=2`，保存前对 body 统一向内腐蚀 2px | `peiyi_mask.py` |
| 3 | 点选扩散每点都报 `x` | 用户点在原图而非分层预览图；参数太严 | 提示点「② 分层预览」图；`COLOR_TOLERANCE 18→20`、`MIN 200→100`、`MAX 500K→1.2M`、`SOBEL_WEIGHT 0.3→0.2` | `peiyi_correct.py` |
| 4 | 点一下就生成废版，版本泛滥 | 旧逻辑点选即落盘 | 改预览→确认→放弃三步流程，`_working` 临时区承载 | `peiyi_correct.py` + `lovart_bridge.py` |
| 5 | 合并用户 PS 遮罩后把 T 恤整片算进遮挡物 | 误把用户白W2.png（89% 透明、画的是手部遮挡物）当「衣身风格」 | 改为**纯叠加**：只认用户画的（alpha>30），不做任何元素分析；用户只需把 AI 漏掉的遮挡物画上去 | `peiyi_correct.py::import_manual_mask` |
| 6 | 白色背景被误判为用户画笔 | 旧逻辑用 `(r+g+b)/3>100` 把白背景算入 | 只用 `alpha>30` 判定用户画笔，排除背景 | `peiyi_correct.py` |
| 7 | 用户画的完整杯子只加了边缘，中间被裁掉 | 旧逻辑用 `person_mask` 裁剪用户画笔，杯子等手持物不在人像范围内 | 去掉 `person_mask` 限制，用户画的区域原样保留 | `peiyi_correct.py` |
| 8 | 合并后边缘又扩大像素 | 旧逻辑对 AI occluder 做 `ndi.binary_dilation(person_mask, 20)` 膨胀 | 去掉该 20px 膨胀 | `peiyi_correct.py` |
| 9 | AI 粗糙边缘盖过用户精确画笔（杯子轮廓发虚） | AI occluder 自带 3px 膨胀边（~51K px），把用户精确画笔完全覆盖 | AI occluder 缩 3px 去膨胀；用户画笔保持像素精度，空白处再补 AI | `peiyi_correct.py` |
| 10 | 用户碰过的整块 AI 连通域被删，导致头发/手臂误删 | 旧逻辑把用户画笔触碰的整块 AI 遮挡物（含相连头发）全删 | 改为仅替换用户画笔附近 20px 范围内的 AI 像素，远处头发/手臂保留 | `peiyi_correct.py` |
| 11 | 手动导入后衣身反而比 AI 原衣身更大 | 被替换下来的像素回到衣身，超出 AI 原范围 | `final_body = final_body & ai_body`，约束在 AI 原衣身内 | `peiyi_correct.py` |
| 12 | FASHN 在无代理/断网环境加载卡死 | 默认联网拉模型 | 懒加载 + `local_files_only=True` 优先离线缓存；失败回退原方法 | `peiyi_mask.py::_get_fashn` |

### 📚 文档与版本

- 版本号统一：`lovart_bridge.py` → **v2.4.2**；`peiyi_mask.py` → **v1.5.2**；`peiyi_correct.py` 随 v1.5.x 迭代。
- 本版本**纯新增遮罩子系统 + 前端页面**，未改动原有生图/去背/贴图/上款/Temu 流程；重启 bridge 后 `/peiyi` 页面与全部 `/api/peiyi/*` 端点生效（改 `peiyi_mask.py`/`peiyi_correct.py` 由 `_peiyi_worker` 子进程每次新导入，无需重启；改 `tpl_generator` 内联路径需重启 bridge）。

---

## v2.4.0 (2026-07-07) — 刷新已上款增量游标 + 轮询修复 + 深度清理

### ✨ 新功能

- **刷新已上款增量游标模式**（联动 check_online_listed.py v1.4.0）
  - `.wb_online_listed.json` 新增 `ordered_list`（上次前N条有序款号）+ `last_oldest_dx`（边界游标）字段
  - 日常刷新（incremental）：翻到上次边界款为止，`removed = set(prev_ordered) - fresh_set` 集合相减自动移除下架款；首次无边界则全量建库
  - 深度清理（deep）：全量翻完所有页覆盖，重置边界，清理盲区
  - `/api/upload/refresh-online-listed` 支持 `?mode=incremental|deep`，`/api/upload/projects` 返回 `online_mode`
- **「🧹 深度清理」按钮**：全量覆盖移除所有下架款（约2分钟）

### 🐛 修复

- **「刷新已上款」前端轮询提前停止**：原停止条件 `online_count` 连续3次不变，无上款任务时 count 恒0导致9~12秒假完成；改为检测 `online_updated_at` 变化，json 真正更新才停止，最长等6分钟

### 📚 文档与版本

- 版本号 v2.3.23 → v2.4.0：`lovart_bridge.py`、`lovart_bridge.bat`、`upload.html`
- 依赖：`check_online_listed.py v1.4.0` + `wb_listing.py v2.2.4`

---

## v2.3.23 (2026-07-06) — 同步 wb上款 v2.2.2 窗口隔离修复

### 🐛 修复

- **上款时夸克/Chrome 窗口被误操作**
  - 同步 wb上款 v2.2.2：`browser_kernel/service/edge_service.py` 增加进程名校验与 Edge 进程树遍历。
  - `_find_edge_windows()` 不再只按 `Chrome_WidgetWin_1/2` 类名匹配，额外校验进程名必须为 `msedge.exe`。
  - `show_for_user()` / `prepare_for_interaction()` / `hide_for_automation()` / `hide_at_bottom()` 全部按 Edge 自身进程树执行。
  - 解决上款时夸克透明窗口被提到前台、遮挡屏幕中间的问题。
- 同步 check_online_listed.py v1.3.20：修复「刷新已上款」选择 300 条/页未生效的问题。
  - `switch_pagination()` 增加 loading 检测与切换结果校验（页大小 / 行数）。
  - 多策略重试（JS 操作 vxe-table / 原生 select、Playwright 点击、纯 JS 点击），确保真正加载约 300 行后再提取。
  - 解决 DX0448/DX0449/DX0450 等已上款款号仍被分到未上款的问题。

### 📚 文档与版本

- 版本号统一升级到 v2.3.23：`lovart_bridge.py`、`lovart_bridge.bat`、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md`、`REPRODUCIBILITY.md`。
- 依赖版本同步：`wb_listing.py v2.2.2` + `check_online_listed.py v1.3.20`。

---

## v2.3.22 (2026-07-06) — 集成 Temu 报活动控制台

### ✨ 新增

- **Temu 报活动页面 (`/activity`)**
  - 新增 `activity.html` 前端页面，提供「启动报活动」「停止」功能，实时展示当前步骤、已完成步骤、进度条与日志。
  - 新增 `/api/activity/*` 后端端点：启动报活动、停止、状态轮询。
  - Bridge 通过子进程调用 `E:/Claude code/Temu自动化/报活动/entrypoint/run.py` 执行实际报活动逻辑（v4.1.3 九步流程）。
  - 状态通过读取 `E:/Claude code/Temu自动化/报活动/state/state.json` 同步，支持显示 `current_step`、`completed_steps`、`errors`、`meta`。
  - `lovart_control.html` 工具栏新增「🎉 报活动」按钮，可在新标签页打开 `/activity`。

### 📚 文档与版本

- 版本号统一升级到 v2.3.22：`lovart_bridge.py`、`lovart_bridge.bat`、`SKILL.md`、`ARCHITECTURE.md`、`CHANGELOG.md`、`REPRODUCIBILITY.md`。

---

## v2.3.21 (2026-07-06) — 修复上款缩略图黑白错位 + 文件夹前台打开

### 🐛 修复

- **彻底修复 WB 上款页面缩略图黑白错位**
  - 根因 1：`_get_upload_thumb` 使用 `re.sub(r'[^A-Za-z0-9_.-]', '_', filename)` 生成缓存文件名，
    把文件名中的中文（白/黑）统一替换成下划线，导致 `DX_B_白T.jpg` 与 `DX_B_黑T.jpg` 映射到同一个缓存文件。
  - 解决 1：safe_name 只替换 Windows 文件系统非法字符（`\ / * ? : " < > |`），保留中文；
    同时清空 `D:\Semems WB\_upload_thumbs` 与 `_ai_review_thumbs` 中的旧错误缓存，重新加载页面时自动重建正确缩略图。
  - 根因 2：前端缩略图 URL 使用源文件 `mtime` 作为缓存破坏参数，但缩略图是后端独立生成的；
    源文件未变时，即使缩略图缓存已重建，浏览器仍会复用旧的错误缩略图。
  - 解决 2：`/api/upload/projects` 新增返回每个文件的 `thumb_mtime`；前端 `upload.html` 用 `thumb_mtime` 作为
    缩略图 URL 的 `t` 参数，确保缩略图重建后浏览器立即刷新。
  - 影响文件：`lovart_bridge.py`、`upload.html`

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
