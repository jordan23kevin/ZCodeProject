# 建议零售价填写 — Bridge 集成设计

## 背景与目标

在 Y2 Bridge 面板中新增「Temu 建议零售价填写」功能入口，让用户可以一键启动 `E:/Claude code/WB Lovart/建议零售价.js`，并在 Bridge 页面内查看实时日志与任务状态。

该功能与已有的「核价」功能相互独立：

- 核价：Temu 核价流程，由 `E:/Claude code/Temu自动化/核价/hengjia.py` 实现。
- 建议零售价填写：Temu 商品列表抽屉中批量填写建议零售价，由 `E:/Claude code/WB Lovart/建议零售价.js` 实现。

## 核心逻辑（已由 `建议零售价.js` 实现）

1. 通过 Playwright 连接 Edge CDP（`http://127.0.0.1:9222`）。
2. 导航到「商品管理 → 商品列表」。
3. 点击「建议零售价待填写」按钮打开抽屉。
4. 将抽屉分页设置为每页 50 条。
5. 对当前页每个商品：读取「日常价格范围」，取最大值 +1，填入「建议零售价」输入框。
6. 勾选表头全选 checkbox。
7. 点击「提交已选(N项)」。
8. 处理两次确认弹窗。
9. 等待页面刷新后重复下一页，最多 20 页。

## 集成方案

采用与「核价」一致的「独立页面 + 状态/日志/停止接口」模式，但保持功能完全独立。

### 文件变更

| 文件 | 操作 | 说明 |
|---|---|---|
| `E:/Claude code/WB Lovart/建议零售价.js` | 修改 | 增加 `--no-close-browser` 参数，Bridge 调用时保留 Edge 不关闭 |
| `C:/Users/Administrator/ZCodeProject/retail_price.html` | 新建 | 独立页面：开始/停止按钮、状态、实时日志 |
| `C:/Users/Administrator/ZCodeProject/lovart_bridge.py` | 修改 | 新增 `/api/retail_price/start\|stop\|status` 与任务状态管理 |
| `C:/Users/Administrator/ZCodeProject/lovart_control.html` | 修改 | 主面板增加「建议零售价填写」入口链接 |

### 后端设计

新增状态对象 `retail_price_task`：

```python
retail_price_task = {
    "status": "idle",        # idle|running|completed|error|stopped
    "task_label": "",
    "started_at": None,
    "completed_at": None,
    "proc": None,
    "log": [],
    "log_index": 0,
    "elapsed_sec": 0,
}
```

新增锁：`retail_price_lock = threading.Lock()`

新增常量：

```python
RETAIL_PRICE_DIR   = Path("E:/Claude code/WB Lovart")
RETAIL_PRICE_SCRIPT = RETAIL_PRICE_DIR / "建议零售价.js"
```

新增接口：

- `GET /retail_price` → 返回 `retail_price.html`
- `POST /api/retail_price/start` → 启动 `node 建议零售价.js --no-close-browser`
- `POST /api/retail_price/stop` → 终止当前任务
- `GET /api/retail_price/status` → 返回状态 + 增量日志

日志采集：

- 启动脚本时创建子进程，并通过后台线程读取 stdout/stderr。
- 每行日志写入 `retail_price_task["log"]`，并标记 kind（空 / `ok` / `warn` / `error`）。
- 前端每 1.2s 调用 `/api/retail_price/status`，使用 `log_index` 机制只获取增量日志。

任务结束判定：

- 后台线程在子进程退出后读取返回码。
- 返回码为 0 时状态置为 `completed`。
- 返回码非 0 或启动失败时状态置为 `error`。
- 用户点击停止时状态置为 `stopped`。

### 前端设计

`retail_price.html` 复用 `pricing.html` 的深色主题与组件样式，但只保留最小集合：

- 标题：Temu 建议零售价填写
- 工具栏：「开始填写」「停止」按钮
- 状态面板：状态徽章、启动时间、耗时
- 实时日志框：支持自动滚动

交互：

- 点击「开始填写」调用 `/api/retail_price/start`，成功后进入轮询。
- 点击「停止」调用 `/api/retail_price/stop`。
- 轮询 `/api/retail_price/status` 刷新状态与日志。
- 任务非 running 时停止轮询。

`lovart_control.html` 在主面板工具栏增加入口按钮，紧挨着「核价」按钮之后：

```html
<button class="btn" onclick="window.open('/retail_price','_blank')" title="打开 Temu 建议零售价填写页面">📝 建议零售价</button>
```

点击后在新标签页打开 `/retail_price`。

### 脚本改动

`建议零售价.js` 增加参数解析：

```javascript
const keepOpen = process.argv.includes('--no-close-browser');
```

在主函数末尾：

```javascript
if (!keepOpen) {
  await browser.close();
} else {
  console.log('[Bridge] 任务完成，保持 Edge 打开');
}
```

Bridge 启动时传 `--no-close-browser`，避免把用户的 Edge 关掉；单独命令行运行时不传，行为保持原样。

## 错误处理

1. 启动前检查 `建议零售价.js` 是否存在，不存在返回 404。
2. 启动失败（如 `node` 不存在、脚本语法错误）返回 500 并记录错误日志。
3. 停止时先 `proc.terminate()`，等待 3s；若仍未退出则 `proc.kill()`。
4. 脚本退出码非 0 时状态置为 `error`，并展示最后几行日志。
5. 已有任务在运行时再次点击开始，返回 409 或友好提示。

## 前置条件

- Edge 已以调试模式启动（`--remote-debugging-port=9222`）。
- 已登录 Temu Agent Center。
- Node.js 与 Playwright 已安装并可运行 `node 建议零售价.js`。

## 测试验证

1. 主控制台出现「建议零售价填写」入口。
2. 新页面能正常打开，显示「开始填写」「停止」按钮。
3. 点击「开始填写」后，后端成功启动脚本，前端显示实时日志。
4. 日志中出现 Step 0 ~ Step 3 与翻页循环的输出。
5. 点击「停止」能终止任务，状态变为 `stopped`。
6. 单独运行 `cd "E:/Claude code/WB Lovart" && node 建议零售价.js` 行为不变，任务结束后关闭 Edge。

## 非目标

- 不修改建议零售价核心算法（仍由 `建议零售价.js` 负责）。
- 不与核价功能共享页面或任务状态。
- 不增加历史记录、Excel 导出、结果文件下载等额外功能。
