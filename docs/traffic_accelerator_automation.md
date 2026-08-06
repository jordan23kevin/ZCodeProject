# Temu 流量加速器批量开启子系统（traffic）— 方法实现与踩坑记录

> 版本：v2.6.0（2026-08-07）
> 代码：`lovart_bridge.py`（traffic 段约 5056 行起）+ `traffic.html`
> 页面：`https://agentseller-eu.temu.com/main/flux-analysis`（商品流量 → 流量加速器）

## 1. 功能概述

在 Y2 控制台新增「🚀 流量加速」独立页面（`/traffic`）。流程与核价一致：

1. 点「① 打开 Temu 后台」：复用已打开的 Temu 标签页（按 URL 含 `flux-analysis` 定位），没有就新开并跳转。
2. 用户登录并进入「流量加速器」页面后，点「② 👌 好了」。
3. 脚本接管：切到「流量加速器待开启」筛选 → 逐页 全选 → 批量开启 → 抽屉内按**核价底价规则**选档位 → 提交 → 翻下一页，直到最后一页。
4. 每条记录（SPU/站点/申报价/核价底价/选择档位/让价/最终价格/结果）实时追加到
   `E:\Kimi Code\temu分析\流量加速器记录.xlsx`（openpyxl）。
5. 页面上有「⏹ 停止」按钮，随时安全停止（已提交的页不受影响）。

## 2. 后端 API（均在 lovart_bridge.py）

| 端点 | 说明 |
|---|---|
| `/traffic` | 页面（traffic.html） |
| `/api/traffic/open` (POST) | 打开/复用 Temu 流量加速器标签页 |
| `/api/traffic/start` (POST) | 用户点「好了」后启动后台接管线程，返回 task_id |
| `/api/traffic/stop` (POST) | 置位 `TRAFFIC_STOP`，循环在当前步骤结束后安全退出 |
| `/api/traffic/status` (GET) | 前端轮询日志/进度/结果 |

任务状态存 `TRAFFIC_TASKS` 字典；停止信号为全局 `threading.Event()`（`TRAFFIC_STOP`），
工作线程在关键节点调 `_traffic_check_stop()`，置位时抛 `_TrafficStopped` 退出。

页面控制层复用 `_ensure_edge_cdp` 连接共用 Edge 调试端口 **9222**（绝不另开第二个 Edge）；
`TRAFFIC_URL_HINTS = ["flux-analysis", "flux"]` 用于定位标签页。

## 3. 核心业务规则（用户确认，勿改）

### 3.1 档位选择规则（`_traffic_analyze_rows`）

设 P = 日常申报价(CNY)，floor = 站点核价底价（沿用 `ORDER_PRICE_FLOOR`），L = 档位让价：

1. 有选项满足 **P − L ≥ floor** → 选**让价最大**的（有效价最接近底价，加权最高）；
2. 否则若最便宜档满足 **P − L ≥ floor − 10** → 选让价最少的（破价 10 元以内）；
3. 否则（破价超过 10 元）→ **价格不通过**，记录 SPU。

- 「流量加速时效」默认不动。
- 续期类商品没有开关，不处理。

### 3.2 每页处理流程（`_traffic_batch_enable`）

1. 全选（优先点 `thead` 的全选框）→ 点「批量开启流量加速器」。
2. 若弹「部分商品不可开启流量加速器，要过滤并继续吗？」→ 自动点「过滤并继续」。
3. 抽屉弹出后 `_traffic_read_rows` + `_traffic_analyze_rows` **只分析不点击**。
4. **全部通过** → 直接 `_traffic_apply_decisions` 选档 → `_traffic_submit_drawer` 提交。
5. **部分通过** → 关抽屉 → `_traffic_select_spus` 按 SPU **只勾选通过的商品** →
   重新点「批量开启」开抽屉 → 选档 → 提交。（抽屉必须打开才能拿到档位价格，无法预选）
6. **全部不通过** → 关抽屉，跳过本页。

### 3.3 翻页策略（`_traffic_loop`）

已开启的商品**不会**离开「待开启」列表，因此每轮处理完（无论是否提交）**必须直接点「下一页」**，
绝不留在当前页重复全选——重复全选会选到已开启商品，触发「部分商品不可开启」弹窗。
翻页点 `li[class*='PGT_next']`，`nextDisabled` 时结束。

### 3.4 提交确认

点「立即加速」后弹 `MDL_` 确认框「确认要批量开启流量加速器吗？」→ 自动点「确认」。

## 4. 关键 DOM 结构（Temu 卖家后台组件库）

| 元素 | 选择器 | 备注 |
|---|---|---|
| 抽屉 | `div[class*='Drawer_content']` | **关闭后元素不消失，滑出屏幕右侧留在 DOM** |
| 抽屉数据行 | 含「SPU ID」的 `tr` | SPU/站点/申报价/档位都在行内 |
| 档位单选 | `label[class*='RD_outerWrapper']` | 文本首行是档位名，含 ¥让价 |
| 列表复选框 | `label[class*='CBX_outerWrapper']` | 是 label 不是 div；勾选态看 `data-checked` 属性 |
| 弹窗 | `[class*='MDL']` | **不是 Modal/Dialog！** 如 `MDL_container_5-120-1` |
| 分页 | `li[class*='PGT_next']` / `li[class*='PGT_pagerItemActive']` | |
| 待开启筛选卡 | `div[class*='quick-overdue-filter_card']` | 选中态 = 橙色边框 `rgb(255, 103, 2)` |
| 抽屉底部按钮 | `button`：取消 / 立即加速 / 一键填写 | 立即加速在**所有行都选好档位后**才可用 |

## 5. 踩坑记录（问题 → 根因 → 解决方案）

### 5.1 「当前页已无商品」死循环（v1 翻页策略错误）

- **现象**：第 1 页处理完后日志一直刷「当前页已无商品，回到第 1 页继续」。
- **根因**：已开启商品不离开列表；留在当前页重复全选会选到已开启商品，
  触发「部分商品不可开启」弹窗，流程卡死回退。
- **解决**：翻页策略改为每轮必点「下一页」，绝不回退（见 3.3）。

### 5.2 记录文件乱码 / 全在一列

- **现象**：早期写 CSV，Excel 打开乱码且所有数据挤在一列。
- **解决**：改用 openpyxl 写 xlsx（`E:\Kimi Code\temu分析\流量加速器记录.xlsx`），
  并按要求放在 `E:\Kimi Code` 下而非 C 盘。做过一次历史数据去重（741→91 条）。

### 5.3 关抽屉误判 ①：按 DOM 存在判断

- **现象**：用户手动点「取消」抽屉明明关了，脚本却说「无法正常关闭」并刷新页面。
- **根因**：抽屉关闭有滑出动画，动画期间元素仍在 DOM；`querySelector` 存在性判断失效。
- **解决**：先改成按 `getBoundingClientRect` 尺寸判断（引出 5.4）。

### 5.4 关抽屉误判 ②：僵尸抽屉（本功能最重要的坑）

- **现象**：尺寸判断后依然误判「未关闭」。
- **根因**（只读观察实测）：抽屉关闭后元素**带着 `transform: translate(1400px)` 滑到屏幕
  右边外面，永久留在 DOM**，`rect` 仍返回 1400×1308。
- **解决**：抽屉「开着」= **与视口的相交像素宽高都 > 50px**（滑出屏幕的残留相交为 0）。
  统一封装为 `_TRAFFIC_VISIBLE_DRAWER_FIND_JS` / `_TRAFFIC_HAS_VISIBLE_DRAWER_JS`。

### 5.5 僵尸抽屉导致操作打错目标（隐蔽且致命）

- **现象**：部分通过的页重开抽屉后，日志显示 27 个档位全部选成功，却报
  「未找到可点的立即加速按钮」，然后抽屉关不掉只能刷新。
- **根因**：原地关抽屉→重开后 DOM 里有**两个** `Drawer_content`：僵尸（第一个）+ 真抽屉
  （第二个）。所有操作都用 `querySelector` 取第一个 → 27 个档位全点进了僵尸抽屉
  （日志正常），真抽屉一个没选、按钮禁用；点「取消」也点的僵尸的。
  刷新页面能成功，正是因为刷新清掉了僵尸。
- **解决**：**所有**抽屉操作（打开检测 / `_traffic_read_rows` / `_traffic_click_option` /
  `_traffic_submit_drawer` / 关抽屉）统一改用「屏幕上可见的那个抽屉」；
  `_traffic_select_spus` 排除抽屉内的行（否则 30 主列表 + 30 僵尸混成 60 行）。

### 5.6 点「取消」关不掉抽屉

- **根因 A**：取消按钮坐标**高速抖动**（x 在 1302 和 2702 间振荡），`force=True` 点击
  跳过稳定性等待，按过期坐标点空。
- **根因 B**：JS `el.click()` 被页面反自动化校验（`event.isTrusted`）吞掉。
- **解决**：关抽屉三级兜底改为 ① Playwright **真实点击（不加 force）**：等按钮稳定、
  滚动进视口再点，最接近人手 → ② JS 点击 + 二次确认弹窗处理 → ③ 刷新页面
  （刷新前 `_traffic_dump_dialogs` 把所有可见弹窗文本+按钮写日志留证）。

### 5.7 弹窗选择器漏检 `MDL_` 前缀

- **现象**：「弹窗诊断」一直报「没有可见弹窗」，但元素采样显示 `MDL_container` 盖住了按钮。
- **根因**：Temu 弹窗 class 是 `MDL_` 前缀，选择器只匹配 `Modal/Dialog/dialog`。
- **解决**：弹窗检测/诊断选择器补 `[class*='MDL']`；二次确认处理**跳过文本含
  「批量开启流量加速器」的提交确认框**，绝不误点它的「确认」把不该提交的商品提交了。

### 5.8 「部分商品不可开启」弹窗

- **现象**：全选选到已开启商品时弹「要过滤并继续吗？」（列出可开启/不可开启明细）。
- **解决**：开抽屉后固定检查该弹窗，自动点「过滤并继续」。

### 5.9 停止机制

- **需求**：用户关掉网页脚本还在跑，无法停止。
- **解决**：`TRAFFIC_STOP` 全局 Event + `/api/traffic/stop` + 前端「⏹ 停止」按钮 +
  循环/选档/分析关键节点 `_traffic_check_stop()`。

### 5.10 启动脚本与「无效或已过期的任务ID」

- **问题 A**：旧版 `lovart_bridge.bat` 检测到 8765 已占用就直接退出，永远加载不到新代码。
- **解决**：bat v2.4.0 改为**先杀掉旧进程再启动**（8765 bridge + 8766 check_rem 同理）。
- **问题 B**：bridge 重启后前端还轮询旧 task_id，报「无效或已过期的任务ID」。
  属正常现象，重新开始任务即可。
- **铁律**：**用户任务在跑时绝不重启 bridge**（判断依据：bridge.log 里
  `/api/traffic/status` 轮询是否还在）。重启杀过任务会导致抽屉状态残留，需要刷新恢复。

## 6. 记录文件格式（流量加速器记录.xlsx）

列：`时间 / SPU / 站点 / 申报价(CNY) / 核价底价 / 选择档位 / 让价 / 最终价格 / 结果`

- 结果取值：`通过` / `价格不通过` / `待人工核对（点击未确认：...）`。
- 每行选档即写（`_traffic_record`，openpyxl 逐行追加，文件不存在则建表头）。
- 价格不通过的 SPU 在页面上汇总展示（逗号分隔），由用户手动处理，脚本不点「立即加速」。

## 7. 运行环境

- Python 3.11（`C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`）
- `PYTHONPATH=E:/python_packages`（playwright、openpyxl 均在此目录）
- 共用 Edge（已登录 Temu，调试端口 9222 由 `_ensure_edge_cdp` 保证）
- 详细复现/回滚见 `REPRODUCIBILITY.md` 第 13 节。
