# 价格申报视角批量处理子系统（order_price）— 方法实现与问题记录

> 对应版本：`lovart_bridge.py v2.5.0`
> 最后更新：2026-07-28
> 关联文档：`CHANGELOG.md` (v2.5.0)、`ARCHITECTURE.md` (v2.5.0 变更)、`REPRODUCIBILITY.md`（运行环境）、`SKILL.md`（能力描述）

---

## 1. 概述

在 Y2 控制台新增「📉 价格申报」独立页面，自动按**核价底价**批量处理 Temu 卖家后台「待卖家确认」列表里的调价单。

Temu「价格申报视角」(`agentseller.temu.com/main/adjust-price-manage/order-price`) 里，每条调价单有「调整后申报价格」。业务规则是：

- **建议价 ≥ 核价底价** → 应该「接受」（点「调整」→ 确认），让系统采用新低价。
- **建议价 < 核价底价** → 应该「拒绝」（保留原价），拒绝原因统一填「价格过低」。

子系统提供两条流水线，都通过 Bridge 控制共用 Edge（调试端口 9222）完成，绝不另开浏览器：

| 动作 | 触发 | 行为 |
|------|------|------|
| 只读扫描预览 | `/api/order_price/scan` | 不点任何按钮，按底价给出 `接受/拒绝/跳过` 汇总 + 各站底价/接受最低价/拒绝最高价 |
| 自动接受（≥底价） | `/api/order_price/auto` | 逐条点「调整」→ 弹窗点「确认」；低于底价保持原样 |
| 批量拒绝（<底价） | `/api/order_price/reject` | 逐个勾选 → 批量拒绝 → 填原因 → 确认 → 真正拒绝 |

入口页面：`order_price.html`（由 `lovart_control.html` 导航栏「📉 价格申报」按钮打开）。

---

## 2. 架构

```
┌──────────────────┐   HTTP/JSON    ┌────────────────────────────┐
│ order_price.html │ ─────────────▶ │ Flask Bridge (8765)         │
│ (扫描/自动/拒绝)  │ ◀───────────── │  /api/order_price/{scan,    │
│ 后台轮询 status   │   实时进度     │   auto,reject,status,enter} │
└──────────────────┘               └──────────┬─────────────────┘
                                               │ playwright sync_api
                                               │ connect_over_cdp
                                               ▼
                                    ┌──────────────────────────┐
                                    │ 共用 Edge (CDP 9222)      │
                                    │ edge-cdp-profile (Temu登录)│
                                    │ 价格申报视角标签页         │
                                    └──────────────────────────┘
```

### 2.1 三大层次

1. **前端 `order_price.html`**：扫描预览面板（表头 `站点/核价底价/接受/拒绝/跳过/接受最低价/拒绝最高价`）+ 「🔍 扫描预览」「▶️ 自动执行」「🗑️ 批量拒绝」三按钮；自动执行/批量拒绝走后台线程，前端每 600ms 轮询 `/api/order_price/status` 实时显示日志与每条通过价格。
2. **后端 Flask 路由 + 后台线程**：`api_order_price_scan`（同步只读）、`api_order_price_auto` / `api_order_price_reject`（立即返回 `task_id`，后台线程跑）、`api_order_price_status`（轮询日志/结果/`passed`/`rejected`）。任务状态存 `OP_TASKS` 字典（带 `threading.Lock`）。
3. **Playwright 控制层**：`_ensure_edge_cdp` 连共用 Edge；`_op_open_tab` / `_op_setup` 进页面并注入 JS；`_op_scan` / `_op_auto` / `_op_reject` 三大流程；`ORDER_PRICE_JS` 注入的 `window._op_*` 助手做表格解析与 DOM 操作。

### 2.2 关键设计点

- **共用 Edge，绝不另开**：`_ensure_edge_cdp(p, log, timeout=40)` 优先连 9222；若已有 Edge 在跑但没 9222 则报错不重开；完全没 Edge 才用 `msedge --remote-debugging-port=9222 --user-data-dir=C:\edge-cdp-profile` 重开那一个（DETACHED + NEW_PROCESS_GROUP）。
- **页面进入自动化**：`_op_setup` ① 点「待卖家确认」标签（已选中则跳过）② 把每页条数设为 200（已是 200 则跳过）③ 注入 `ORDER_PRICE_JS` 助手。
- **后台执行 + 轮询**：长任务不阻塞 HTTP，前端实时看到进度，避免「等全部跑完才出结果」。

---

## 3. 方法实现

### 3.1 核价底价配置 `ORDER_PRICE_FLOOR`

权威来源是 Temu 核价仓 `config/prices.py` 的 `PRICE_MAP`。字典放在 `lovart_bridge.py`：

| 站点 | 底价 | 站点 | 底价 |
|------|------|------|------|
| 波兰 | 52 | 丹麦 | 84 |
| 匈牙利 | 56 | 斯洛文尼亚 | 84 |
| 立陶宛 | 56 | 奥地利 | 86 |
| 德国 | 63 | 荷兰 | 89 |
| 捷克 | 65 | 罗马尼亚 | 100 |
| 斯洛伐克 | 67 | 瑞典 | 134 |
| 葡萄牙 | 76 | 芬兰 | 142 |
| 西班牙 | 85 | **意大利** | **115** |
| 比利时 | 85 | | |
| 法国 | 70 | | |

> 意大利底价 115 于 2026-07-27 由用户确认加入（最初未配置、留人工；后定为 100，最终改为 115）。

### 3.2 价格解析 `_parse_price(s)`

Temu 欧洲站价格用本地格式，直接 `float()` 会算错（如 `€ 60,50` → 6050）。处理函数：

1. 去掉非数字/逗号/点字符（如 `€ `、`空格`）。
2. 同时含 `.` 和 `,`：看谁在右边 → 右边的是小数位。
   - `1.234,56`（逗号是小数）→ 去点去逗号→`1234.56`
   - `1,234.56`（点是小数）→ 去逗号→`1234.56`
3. 只有 `,`：`1,234` 纯千分位 → 去逗号；`60,50` 逗号作小数 → 替换为 `.`。
4. 其余（只有 `.` 或纯数字）→ 直接 `float`。

### 3.3 扫描 `api_order_price_scan` / `_op_scan`

- `_op_scan` 翻完所有页（最多 60 页，每页 200 条），收集 `_op_rows()` 返回的行，按 `order` 去重（翻页会重复读同一行）。
- `_op_rows()` 识别「同时含『调整』『不调整』链接」的 `<tr>` 为数据行，按表头动态定位「单号/站点/调整后申报价格」列（扛结构微调）。
- 聚合：每个站点统计 `accept/reject/skip`，并记录该站 `accept_min`（接受最低价）、`reject_max`（拒绝最高价）。
- **只读**，不点任何按钮。

### 3.4 自动接受 `api_order_price_auto` / `_op_auto`

逐条处理「建议价 ≥ 底价」的订单：

```
for 每页:
    解析行 → _op_decide 判定
    拒绝行: 仅计数(skip)，不点击
    accept行(未尝试过):
        记 attempted → 点「调整」(window._op_click)
        → 轮询等确认弹窗出现(modal_count>baseline)
        → 点最顶层「确认」(window._op_confirm_modal)
        → 等弹窗关闭 → 该条完成
        → 验证行从列表消失；消失则 accept+1，记录 passed(订单/站点/价格/底价)
```

**`attempted` 守卫**是防弹窗叠加的核心：已点过「调整」的订单记进集合，下一轮扫描不再重复点，杜绝「点一次弹一个确认框」的死循环。

### 3.5 批量拒绝 `api_order_price_reject` / `_op_reject`

逐个勾选低于底价的订单并批量拒绝（**绝不点全选**）：

```
1) 扫描本页 → 找出 _op_decide==reject 的行 → 逐行 window._op_check(order, true) 勾选
   （按单号精确匹配，点可见 label 触发 React onChange；每勾一个记 rejected）
2) 校验 实际勾选数 == 计划数；为 0 则中止（防误点批量拒绝）
3) 点「批量拒绝」(window._op_click_batch_reject) → 右侧面板 TB_innerRight 打开
4) 用 Playwright textarea.fill("价格过低") 逐行填原因 → 轮询 _op_all_reason_filled 验证全满
5) 点面板外「拒绝」提交按钮(window._op_click_reject) → 弹出最终「拒绝调价」确认弹窗
6) 点最终弹窗「拒绝」(window._op_click_reject_final) 真正提交
7) 验证被拒订单从列表消失
```

> 注意：原因必须**填满所有框**才能提交，否则 Temu 报「原因不能为空」并拦截。

### 3.6 前端实时进度

`order_price.html` 的 `doAuto()` / `doReject()` 发 POST 拿到 `task_id`，启动 `setInterval` 每 600ms 调 `/api/order_price/status?task_id=`，把 `log`（实时日志，含每通过一条的价格行）与 `passed`/`rejected` 列表渲染出来——不等任务结束就能看到每条结果。

---

## 4. 开发过程中遇到的问题及解决方案

> 本节是血泪踩坑集，后续维护/回滚时务必对照。

### 4.1 欧洲逗号小数 → 决策全反
- **现象**：德国 `€ 60,50` 被 `float("60,50")` 当成 6050，导致「≥底价」判定全部反转，该接受的没接受、该拒绝的误接受。
- **根因**：欧洲用逗号作小数位，直接 `float()` 会抛错或被错误处理。
- **解决**：`_parse_price` 按「逗号/点谁是小数位」分情况清洗（见 §3.2）。所有价格解析统一走它。

### 4.2 确认弹窗叠加死循环（最严重）
- **现象**：自动接受跑着跑着，Edge 上叠了 19 个确认弹窗，页面卡死。
- **根因**：旧实现每轮重扫整页，若某行点击「调整」后**还没消失**，下一轮又找到它再次点「调整」→ 又弹一个确认框。
- **解决**：引入 `attempted` 集合，每个订单只点一次「调整」；确认弹窗若关不掉，兜底点「取消」(`_op_dismiss_cancel`) 清理。实测每订单点击次数 = 1。

### 4.3 拒绝原因填不进 React 受控组件
- **现象**：填了原因、点「一键复制」、点「拒绝」，Temu 拦截报「原因不能为空」。
- **根因**：右侧面板 textarea 是 React 受控组件，用原生 `el.value = ...` + dispatch `input` 事件，值没真正进 React state（即便加了 `_valueTracker` 重置也不一定灵）；「一键复制」复制的是空值。
- **解决**：改用 Playwright 真实输入 `textarea.fill("价格过低")`（模拟键盘输入，React `onChange` 必触发），再轮询 `_op_all_reason_filled` 验证全部填满，填满才点拒绝。**弃用「填首行 + 一键复制」方案**（面板 textarea 对该方案不生效）。

### 4.4 原因框计数虚高（MDL_ 嵌套重复匹配）
- **现象**：诊断显示 `total=33, 空 22`（实际只勾了 3 个，应 total=3）。
- **根因**：`_op_reason_fields` 跨 `MDL_` 弹窗收集 textarea，而最终确认弹窗 DOM 嵌套了 5 层同名 `MDL_` 类（`outerWrapper`/`container`/`innerWrapper`/`inner`/`body`），每层 `querySelectorAll('textarea')` 把同一批框重复匹配一次 → 5×6=30，加上面板 3 个 = 33。
- **解决**：`_op_reason_fields` 只收右侧面板 `TB_innerRight` 内的 textarea（填原因 + 验证都在这个语境），不再跨 `MDL_` 弹窗收集。

### 4.5 面板内「拒绝」按钮点不到
- **现象**：填完原因后，代码死活点不到「拒绝」提交按钮，流程卡住。
- **根因**：真正的提交按钮在右侧面板 `TB_innerRight` **之外**（诊断显示 `inPanel: false`），旧 `_op_click_reject` 只在面板内找。
- **解决**：`_op_click_reject` 改为在 **document 范围**找可见的「拒绝」按钮（排除「批量拒绝」、`disabled`、不可见）。

### 4.6 最终弹窗是 MDL_ 类，旧检测识别不到
- **现象**：点了面板「拒绝」却检测不到最终弹窗，误判失败。
- **根因**：最终确认弹窗是 `MDL_` 类，而 `_op_modal_count` 只认 `modal/Modal/dialog/Dialog`。
- **解决**：新增 `_op_final_modal_present`，专门识别含「拒绝调价」字样的 `MDL_` 弹窗，用于第 5/6 步检测。

### 4.7 最终弹窗提交按钮叫「拒绝」不是「确认」
- **现象**：最终弹窗里找不到「确认」按钮（旧 `_op_confirm_modal` 点不到），提交失败。
- **根因**：该弹窗（「已选 N 个调价单，拒绝调价？」）的提交按钮文本是**「拒绝」**，而自动接受流程里用的确认弹窗按钮是「确认」——两个流程按钮文案不同。
- **解决**：`_op_click_reject_final` 点「拒绝」按钮（而非「确认」）。第 6 步走 `_op_final_modal_present` → `_op_click_reject_final`。

### 4.8 Temu 最终确认弹窗自动额外加调价单
- **现象**：勾选 51 个后点拒绝，最终弹窗显示「已选 **55** 个调价单，拒绝调价？为确保活动价格低于日常价格，已自动为您添加 4 个未选中调价单」。
- **根因**：Temu 在最后一步自动追加它认为也该拒绝的单（本次是 4 个意大利，原本没勾）。
- **处理**：先核对那 4 个是否真低于底价。本次 4 个意大利价 14.50/36.59/83.93/60.12 均 < 115，用户确认「意大利也一起拒绝」→ 直接确认全部 55 个。若追加的单不该拒，应在弹窗里逐行点「移除」只留自己勾的。
- **教训**：批量拒绝最终弹窗是「全要拒 or 全不拒」，执行前必须核对追加项，不要盲目点。

### 4.9 拒绝后列表不刷新
- **现象**：拒绝后主列表仍显示 69 行（旧数据残留），误以为没处理完。
- **根因**：Temu 该列表不会自动刷新，拒绝后数据残留前端。
- **解决**：处理完提示用户 **按 F5 刷新** 后再复核；刷新后真实只剩 14 行，且需要拒绝的已为 0——证明拒绝成功。

---

## 5. 运行环境与复现

详见 `REPRODUCIBILITY.md`。要点：

- **Bridge Python**：`C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe`（自带 `playwright` sync_api），运行时需 `PYTHONPATH=E:/python_packages`。
- **Edge**：共用调试端口 **9222**，用户数据目录 `C:\edge-cdp-profile`（Temu 登录保留）。绝不另开第二个 Edge。
- **启动**：`D:\Semems WB\01_INBOX\lovart_bridge.bat`（自带杀旧 8765 + 常驻）。
- **页面**：`http://127.0.0.1:8765/order-price`。
- **依赖**：`flask` + `playwright`（sync_api）。`pywin32`/`pythoncom` 仅窗口操作与美图去背用。

---

## 6. 回滚

- 本版本已打 Git tag **`v2.5.0`**（`git tag v2.5.0` + `git push origin v2.5.0`）。
- 回滚到任意历史版本：`git checkout <tag>` 或 `git revert`。代码版本号在 `lovart_bridge.py` 头部，与 tag 一致。
- 核价底价改动（意大利 115）如要回退，改 `ORDER_PRICE_FLOOR` 字典即可，属纯数据配置，无副作用。
