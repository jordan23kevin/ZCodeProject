# 建议零售价填写 Bridge 集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Y2 Bridge 中新增「Temu 建议零售价填写」独立页面与后端接口，一键启动 `E:/Claude code/WB Lovart/建议零售价.js` 并实时展示日志。

**Architecture:** 完全参照现有「报活动」功能的轻量模式：Flask 后端维护一个任务状态对象 + 子进程 + 日志采集线程，前端通过轮询 `/api/retail_price/status` 刷新状态与日志。核心自动化逻辑继续放在 `E:/Claude code/WB Lovart/建议零售价.js`。

**Tech Stack:** Python 3 (Flask), HTML/JS, Node.js + Playwright。

## Global Constraints

- 所有改动必须兼容现有 Bridge 服务，不得破坏核价/报活动/上款等功能。
- `建议零售价.js` 的核心算法（导航、填价、提交、翻页）不得修改，只允许增加 `--no-close-browser` 参数支持。
- 后端接口路径统一使用 `/api/retail_price/*`，页面路径为 `/retail_price`。
- 前端样式与 `pricing.html` / `activity.html` 保持一致（深色主题、状态徽章、实时日志框）。
- 手动测试即可，项目无现成单元测试框架。

---

## File Structure

| 文件 | 操作 | 职责 |
|---|---|---|
| `E:/Claude code/WB Lovart/建议零售价.js` | 修改 | 增加 `--no-close-browser` CLI 参数，Bridge 调用时出错也不关闭 Edge |
| `C:/Users/Administrator/ZCodeProject/retail_price.html` | 新建 | 前端独立页面：开始/停止按钮、状态、实时日志 |
| `C:/Users/Administrator/ZCodeProject/lovart_bridge.py` | 修改 | 新增 `retail_price_task` 状态、日志读取器、启动辅助函数、4 个 Flask 端点 |
| `C:/Users/Administrator/ZCodeProject/lovart_control.html` | 修改 | 主面板工具栏增加「建议零售价」入口按钮 |

---

## Task 1: 修改 `建议零售价.js` 支持 `--no-close-browser`

**Files:**
- Modify: `E:/Claude code/WB Lovart/建议零售价.js:1-5`（顶部增加参数解析注释/常量）
- Modify: `E:/Claude code/WB Lovart/建议零售价.js:512-519`（IIFE 顶部两处 `browser.close()`）

**Interfaces:**
- Consumes: CLI argument `--no-close-browser`
- Produces: 无新函数；行为变化：传参时错误路径不关闭 Edge

- [ ] **Step 1: 在文件顶部、注释之后添加参数解析**

```javascript
const keepOpen = process.argv.includes('--no-close-browser');
```

放在第 6 行 `const { chromium } = require('playwright');` 之后。

- [ ] **Step 2: 修改 IIFE 中两处错误关闭逻辑**

将：

```javascript
  const page = await step0_导航到商品列表(browser);
  if (!page) { await browser.close(); return; }
```

改为：

```javascript
  const page = await step0_导航到商品列表(browser);
  if (!page) { if (!keepOpen) await browser.close(); return; }
```

将：

```javascript
  const drawerOk = await step1_打开建议零售价抽屉(page);
  if (!drawerOk) { console.log('错误: 抽屉未打开'); await browser.close(); return; }
```

改为：

```javascript
  const drawerOk = await step1_打开建议零售价抽屉(page);
  if (!drawerOk) { console.log('错误: 抽屉未打开'); if (!keepOpen) await browser.close(); return; }
```

- [ ] **Step 3: 语法检查**

Run:

```bash
cd "E:/Claude code/WB Lovart" && node --check 建议零售价.js
```

Expected: 无输出（表示语法通过）。

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git add -A
git commit -m "feat(retail-price): support --no-close-browser flag in 建议零售价.js"
```

---

## Task 2: 创建 `retail_price.html` 前端页面

**Files:**
- Create: `C:/Users/Administrator/ZCodeProject/retail_price.html`

**Interfaces:**
- Consumes: `GET /api/retail_price/status`, `POST /api/retail_price/start`, `POST /api/retail_price/stop`
- Produces: 无；纯展示页面

- [ ] **Step 1: 创建完整 HTML 文件**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Temu 建议零售价填写</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#1a1a1a;color:#eee;padding:22px;min-height:100vh}
  h1{text-align:center;font-size:28px;margin:0 0 16px}
  .toolbar{text-align:center;margin-bottom:18px;position:sticky;top:0;background:#1a1a1a;padding:12px 0;z-index:20;border-bottom:1px solid #333}
  .toolbar button{padding:11px 20px;font-size:15px;border-radius:5px;border:1px solid #555;background:#2a2a2a;color:#eee;margin-left:8px;cursor:pointer;font-weight:600}
  .toolbar button:hover:not(:disabled){background:#333}
  .toolbar button:disabled{opacity:.45;cursor:not-allowed}
  .btn-green{background:#4CAF50;color:#fff;border:none}
  .btn-green:hover:not(:disabled){background:#388e3c}
  .btn-red{background:#e53935;color:#fff;border:none}
  .btn-red:hover:not(:disabled){background:#b71c1c}
  .panel{background:#252525;border:1px solid #444;border-radius:10px;padding:16px 20px;margin:0 auto 22px;max-width:1200px}
  .panel-title{font-size:18px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}
  .status-row{display:flex;gap:20px;flex-wrap:wrap;font-size:15px;color:#bbb;margin-bottom:10px}
  .status-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:12px;font-size:13px;font-weight:500;border:1px solid}
  .status-idle{background:#1b3a1b;color:#7ee787;border-color:#2e7d32}
  .status-running{background:#3d2e0b;color:#f7c843;border-color:#9e6a03}
  .status-completed{background:#1b3a1b;color:#7ee787;border-color:#2e7d32}
  .status-error{background:#3d0f0f;color:#f87171;border-color:#a42c2c}
  .spinner{display:inline-block;width:14px;height:14px;border:2px solid #8b949e;border-top-color:transparent;border-radius:50%;animation:spin .6s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .log-box{background:#0d0d0d;border:1px solid #333;border-radius:6px;padding:10px 14px;height:420px;overflow-y:auto;font-family:"Cascadia Code",Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap}
  .log-box .line{color:#8b949e}
  .log-box .line.ok{color:#7ee787}
  .log-box .line.warn{color:#f7c843}
  .log-box .line.error{color:#f87171}
</style>
</head>
<body>
<h1>Temu 建议零售价填写</h1>

<div class="toolbar">
  <button class="btn-green" onclick="startTask()" id="btnStart">🚀 开始填写</button>
  <button class="btn-red" onclick="stopTask()" id="btnStop" disabled>⏹ 停止</button>
</div>

<div class="panel">
  <div class="panel-title">
    <span>任务状态</span>
    <span id="statusBadge" class="status-badge status-idle"><span class="spinner" id="statusSpinner" style="display:none"></span><span id="statusLabel">就绪</span></span>
  </div>
  <div class="status-row">
    <span>启动时间: <b id="startTime">-</b></span>
    <span>总耗时: <b id="totalElapsed" class="num">0s</b></span>
  </div>
</div>

<div class="panel">
  <div class="panel-title">
    <span>实时日志</span>
    <button onclick="clearLog()" style="padding:5px 12px;font-size:13px;background:#9c27b0;color:#fff;border:none;border-radius:4px;cursor:pointer">清空</button>
  </div>
  <div id="logBox" class="log-box"></div>
</div>

<script>
function formatTime(d){
  if(!d)return '-';
  var x=new Date(d);
  return x.getFullYear()+'-'+(x.getMonth()+1).toString().padStart(2,'0')+'-'+x.getDate().toString().padStart(2,'0')+' '+x.getHours().toString().padStart(2,'0')+':'+x.getMinutes().toString().padStart(2,'0')+':'+x.getSeconds().toString().padStart(2,'0');
}
function formatDuration(s){
  if(s===undefined||s===null||s==='')return '-';
  s=parseInt(s,10);
  if(s<60)return s+'s';
  var m=Math.floor(s/60),sec=s%60;
  if(m<60)return m+'m '+sec+'s';
  var h=Math.floor(m/60);m=m%60;
  return h+'h '+m+'m';
}

var pollTimer=null;

function setStatus(status,label){
  var b=document.getElementById('statusBadge');
  b.className='status-badge status-'+status;
  document.getElementById('statusLabel').textContent=label;
  document.getElementById('statusSpinner').style.display=(status==='running'?'inline-block':'none');
  document.getElementById('btnStart').disabled=(status==='running');
  document.getElementById('btnStop').disabled=(status!=='running');
}

function appendLog(line,kind){
  var box=document.getElementById('logBox');
  var div=document.createElement('div');
  div.className='line '+(kind||'');
  div.textContent=line;
  box.appendChild(div);
  box.scrollTop=box.scrollHeight;
}
function clearLog(){
  document.getElementById('logBox').innerHTML='';
}

function startTask(){
  fetch('/api/retail_price/start',{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.error){appendLog('❌ '+d.error,'error');return;}
      appendLog('✅ '+d.msg,'ok');
      setStatus('running','填写中');
      beginPoll();
    }).catch(function(e){appendLog('❌ 请求失败: '+e,'error');});
}
function stopTask(){
  fetch('/api/retail_price/stop',{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      appendLog(d.msg||'已停止','warn');
      setStatus('idle','就绪');
    }).catch(function(e){appendLog('❌ 请求失败: '+e,'error');});
}

function beginPoll(){
  if(pollTimer)clearInterval(pollTimer);
  pollTimer=setInterval(pollStatus,1200);
  pollStatus();
}
function stopPoll(){
  if(pollTimer){clearInterval(pollTimer);pollTimer=null;}
}

function pollStatus(){
  fetch('/api/retail_price/status').then(function(r){return r.json();}).then(function(d){
    document.getElementById('startTime').textContent=formatTime(d.started_at);
    document.getElementById('totalElapsed').textContent=formatDuration(d.elapsed_sec);

    if(d.log && d.log.length){
      d.log.forEach(function(e){appendLog(e.line,e.kind);});
    }

    if(d.status==='running'){
      setStatus('running',d.task_label||'填写中');
    }else if(d.status==='error'){
      setStatus('error','出错');
      stopPoll();
    }else if(d.status==='completed'){
      setStatus('completed','完成');
      stopPoll();
    }else{
      setStatus('idle','就绪');
      stopPoll();
    }
  }).catch(function(e){console.log('poll error',e);});
}

setStatus('idle','就绪');
pollStatus();
</script>
</body>
</html>
```

- [ ] **Step 2: 静态检查文件存在且格式正确**

Run:

```bash
ls -la "C:/Users/Administrator/ZCodeProject/retail_price.html"
```

Expected: 文件存在，大小大于 0。

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git add retail_price.html
git commit -m "feat(retail-price): add retail_price.html frontend page"
```

---

## Task 3: 在 `lovart_bridge.py` 增加后端状态与辅助函数

**Files:**
- Modify: `C:/Users/Administrator/ZCodeProject/lovart_bridge.py:271-277`（新增常量）
- Modify: `C:/Users/Administrator/ZCodeProject/lovart_bridge.py:491-495`（新增状态与锁）
- Modify: `C:/Users/Administrator/ZCodeProject/lovart_bridge.py:3507-3610` 附近（新增辅助函数）

**Interfaces:**
- Consumes: `subprocess`, `threading`, `datetime`, `Path`
- Produces: `retail_price_task`, `retail_price_lock`, `_retail_price_log_reader(proc)`, `_start_retail_price_script(label)`

- [ ] **Step 1: 在常量区添加建议零售价路径**

在 `PRICING_OUTPUT_DIR = Path(r"C:\Users\Administrator\Desktop\核价档案")` 之后插入：

```python
# ============================================================================
# Temu 建议零售价填写项目路径
# ============================================================================
RETAIL_PRICE_DIR   = Path("E:/Claude code/WB Lovart")
RETAIL_PRICE_SCRIPT = RETAIL_PRICE_DIR / "建议零售价.js"
```

- [ ] **Step 2: 添加任务状态与锁**

在 `activity_lock = threading.Lock()` 之后、`_lock = threading.Lock()` 之前插入：

```python
# ============================================================================
# 建议零售价填写任务状态
# ============================================================================
retail_price_task = {
    "status": "idle",          # idle | running | completed | error | stopped
    "task_label": "",
    "started_at": None,
    "completed_at": None,
    "proc": None,
    "log": [],
    "log_index": 0,            # 前端已读取到的位置
    "elapsed_sec": 0,
}
retail_price_lock = threading.Lock()
```

- [ ] **Step 3: 在 activity 辅助函数附近添加日志读取器与启动函数**

在 `_start_activity_script` 函数结束（第 3610 行 `return {"success": True, "message": f"已启动 {label}"}, 200`）之后、`@app.route('/activity')` 之前插入：

```python
def _retail_price_log_reader(proc):
    """后台线程：读取建议零售价脚本 stdout/stderr 并写入 retail_price_task 日志。"""
    def _read_stream(stream, kind):
        try:
            for raw in iter(stream.readline, b""):
                line = None
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        line = raw.decode(enc, errors="strict").rstrip("\r\n")
                        break
                    except Exception:
                        continue
                if line is None:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                with retail_price_lock:
                    retail_price_task["log"].append({"line": line, "kind": kind})
        except Exception as e:
            with retail_price_lock:
                retail_price_task["log"].append({"line": f"日志读取异常: {e}", "kind": "error"})
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threads = []
    if proc.stdout:
        t = threading.Thread(target=_read_stream, args=(proc.stdout, ""), daemon=True)
        t.start()
        threads.append(t)
    if proc.stderr:
        t = threading.Thread(target=_read_stream, args=(proc.stderr, "error"), daemon=True)
        t.start()
        threads.append(t)

    rc = proc.wait()
    for t in threads:
        t.join(timeout=2)

    elapsed = 0
    if retail_price_task.get("started_at"):
        try:
            elapsed = int((datetime.now() - datetime.fromisoformat(retail_price_task["started_at"])).total_seconds())
        except Exception:
            pass

    with retail_price_lock:
        retail_price_task["elapsed_sec"] = elapsed
        if retail_price_task["status"] == "running":
            if rc == 0:
                retail_price_task["status"] = "completed"
                retail_price_task["task_label"] = "填写完成"
            else:
                retail_price_task["status"] = "error"
                retail_price_task["task_label"] = f"填写失败 (退出码 {rc})"
        retail_price_task["completed_at"] = datetime.now().isoformat()
        retail_price_task["proc"] = None


def _start_retail_price_script(label):
    """通用启动 Temu 建议零售价填写子进程。"""
    with retail_price_lock:
        if retail_price_task.get("status") == "running" and retail_price_task.get("proc") and retail_price_task["proc"].poll() is None:
            return {"error": "已有建议零售价任务在运行，请先停止"}, 409

        retail_price_task["status"] = "running"
        retail_price_task["task_label"] = label
        retail_price_task["started_at"] = datetime.now().isoformat()
        retail_price_task["completed_at"] = None
        retail_price_task["log"] = [{"line": f"[{datetime.now().strftime('%H:%M:%S')}] 启动: {label}", "kind": ""}]
        retail_price_task["log_index"] = 0
        retail_price_task["elapsed_sec"] = 0

    if not RETAIL_PRICE_DIR.exists():
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
        return {"error": f"建议零售价项目目录不存在: {RETAIL_PRICE_DIR}"}, 404

    if not RETAIL_PRICE_SCRIPT.exists():
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
        return {"error": f"建议零售价脚本不存在: {RETAIL_PRICE_SCRIPT}"}, 404

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.Popen(
            ["node", str(RETAIL_PRICE_SCRIPT), "--no-close-browser"],
            cwd=str(RETAIL_PRICE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        with retail_price_lock:
            retail_price_task["status"] = "error"
            retail_price_task["completed_at"] = datetime.now().isoformat()
            retail_price_task["proc"] = None
        return {"error": f"启动脚本失败: {e}"}, 500

    with retail_price_lock:
        retail_price_task["proc"] = proc

    threading.Thread(target=_retail_price_log_reader, args=(proc,), daemon=True).start()
    return {"ok": True, "msg": f"已启动 {label}"}, 200
```

- [ ] **Step 4: 语法检查**

Run:

```bash
cd "C:/Users/Administrator/ZCodeProject" && python -m py_compile lovart_bridge.py
```

Expected: 无输出（表示语法通过）。

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git add lovart_bridge.py
git commit -m "feat(retail-price): add backend state and helper functions"
```

---

## Task 4: 在 `lovart_bridge.py` 增加 Flask 端点

**Files:**
- Modify: `C:/Users/Administrator/ZCodeProject/lovart_bridge.py:3613-3690` 附近（在 activity 端点之后插入）

**Interfaces:**
- Consumes: `_start_retail_price_script`, `retail_price_task`, `retail_price_lock`
- Produces: `/retail_price`, `/api/retail_price/start`, `/api/retail_price/stop`, `/api/retail_price/status`

- [ ] **Step 1: 在 activity 状态接口之后添加 4 个新端点**

在 `api_activity_status` 函数结束（第 3690 行 `})` 之后）插入：

```python
@app.route('/retail_price')
def retail_price_page():
    """Temu 建议零售价填写页面。"""
    return send_file(str(Path(__file__).parent / 'retail_price.html'))


@app.route('/api/retail_price/start', methods=['POST'])
def api_retail_price_start():
    """启动 Temu 建议零售价填写脚本。"""
    resp, code = _start_retail_price_script("建议零售价填写")
    return jsonify(resp), code


@app.route('/api/retail_price/stop', methods=['POST'])
def api_retail_price_stop():
    """停止当前建议零售价填写任务。"""
    with retail_price_lock:
        proc = retail_price_task.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                return jsonify({"error": f"停止失败: {e}"}), 500
        retail_price_task["status"] = "stopped"
        retail_price_task["task_label"] = "已停止"
        retail_price_task["completed_at"] = datetime.now().isoformat()
        retail_price_task["proc"] = None
    return jsonify({"ok": True, "msg": "已停止"})


@app.route('/api/retail_price/status')
def api_retail_price_status():
    """获取建议零售价填写任务状态与增量日志。"""
    with retail_price_lock:
        idx = retail_price_task.get("log_index", 0)
        all_logs = retail_price_task.get("log", [])
        logs = all_logs[idx:]
        retail_price_task["log_index"] = len(all_logs)

        elapsed = 0
        if retail_price_task.get("status") == "running" and retail_price_task.get("started_at"):
            try:
                elapsed = int((datetime.now() - datetime.fromisoformat(retail_price_task["started_at"])).total_seconds())
            except Exception:
                pass

        raw_status = retail_price_task.get("status", "idle")
        display_status = "idle" if raw_status == "stopped" else raw_status

        return jsonify({
            "status": display_status,
            "task_label": retail_price_task.get("task_label", ""),
            "started_at": retail_price_task.get("started_at"),
            "completed_at": retail_price_task.get("completed_at"),
            "elapsed_sec": elapsed,
            "log": logs,
        })
```

- [ ] **Step 2: 语法检查**

Run:

```bash
cd "C:/Users/Administrator/ZCodeProject" && python -m py_compile lovart_bridge.py
```

Expected: 无输出。

- [ ] **Step 3: 启动 Bridge 并测试端点**

假设 Bridge 已在运行（或新起一个）：

```bash
# 如果未运行，先启动（在另一个窗口）
# cd "C:/Users/Administrator/ZCodeProject" && python lovart_bridge.py

# 测试状态接口
curl -s http://127.0.0.1:8765/api/retail_price/status | python -m json.tool
```

Expected: JSON 包含 `"status": "idle"`, `"log": []`。

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git add lovart_bridge.py
git commit -m "feat(retail-price): add Flask endpoints for retail price"
```

---

## Task 5: 在 `lovart_control.html` 增加入口按钮

**Files:**
- Modify: `C:/Users/Administrator/ZCodeProject/lovart_control.html:374-376`（在核价按钮后插入）

**Interfaces:**
- Consumes: 无
- Produces: 无新函数；纯 UI 入口

- [ ] **Step 1: 在主面板工具栏添加按钮**

找到：

```html
      <button class="btn" onclick="window.open('/pricing','_blank')" title="打开 Temu 核价页面">💰 核价</button>
      <button class="btn" onclick="window.open('/activity','_blank')" title="打开 Temu 报活动页面">🎉 报活动</button>
```

改为：

```html
      <button class="btn" onclick="window.open('/pricing','_blank')" title="打开 Temu 核价页面">💰 核价</button>
      <button class="btn" onclick="window.open('/retail_price','_blank')" title="打开 Temu 建议零售价填写页面">📝 建议零售价</button>
      <button class="btn" onclick="window.open('/activity','_blank')" title="打开 Temu 报活动页面">🎉 报活动</button>
```

- [ ] **Step 2: 静态检查**

Run:

```bash
grep -n "建议零售价" "C:/Users/Administrator/ZCodeProject/lovart_control.html"
```

Expected: 输出包含新按钮的一行。

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git add lovart_control.html
git commit -m "feat(retail-price): add entry button in main control panel"
```

---

## Task 6: 集成测试

**Files:**
- 无新增/修改文件

**Interfaces:**
- Consumes: Bridge 服务、Edge CDP、Temu 登录状态

- [ ] **Step 1: 启动 Bridge 服务**

Run:

```bash
cd "C:/Users/Administrator/ZCodeProject"
python lovart_bridge.py --no-browser
```

Expected: 服务启动，监听 `http://127.0.0.1:8765`。

- [ ] **Step 2: 打开主控制台并验证入口**

在浏览器打开 `http://127.0.0.1:8765`，检查：
- 工具栏出现「📝 建议零售价」按钮。
- 点击后在新标签页打开 `http://127.0.0.1:8765/retail_price`。

- [ ] **Step 3: 测试启动与日志**

确保 Edge 已以调试模式启动且已登录 Temu：

```batch
start msedge --remote-debugging-port=9222
```

在 `retail_price.html` 页面点击「开始填写」。

Expected:
- 状态变为「填写中」。
- 日志框出现 `启动: 建议零售价填写` 以及 Step 0 ~ Step 3 的输出。
- 脚本实际执行填价、提交、翻页流程。

- [ ] **Step 4: 测试停止按钮**

在任务运行中点击「停止」。

Expected:
- 状态变为「已停止」或最终完成/错误状态。
- 子进程被终止。

- [ ] **Step 5: 单独命令行运行验证**

Run:

```bash
cd "E:/Claude code/WB Lovart" && node 建议零售价.js
```

Expected: 脚本正常运行，行为与修改前一致（成功完成后不关闭 Edge）。

- [ ] **Step 6: 最终 Commit（如测试通过）**

```bash
cd "C:/Users/Administrator/ZCodeProject"
git log --oneline -5
```

Expected: 最近 5 条 commit 包含本次新增的所有 retail-price 相关提交。

---

## Self-Review

**1. Spec coverage:**

| 需求 | 对应任务 |
|---|---|
| 独立页面入口 | Task 2 + Task 5 |
| 一键启动 `建议零售价.js` | Task 4 (`/api/retail_price/start`) |
| 实时日志展示 | Task 2 + Task 3 + Task 4 |
| 停止任务 | Task 4 (`/api/retail_price/stop`) |
| `--no-close-browser` 支持 | Task 1 |
| 不与核价功能耦合 | 独立状态、独立端点、独立页面 |

**2. Placeholder scan:**

- 无 TBD/TODO/"实现 later"。
- 所有代码片段完整。
- 所有测试命令具体。

**3. Type consistency:**

- `retail_price_task` 字段与辅助函数、端点一致。
- 状态枚举：`idle|running|completed|error|stopped`。
- 日志条目格式统一为 `{"line": str, "kind": str}`。

**4. 已知限制/风险：**

- 手动测试需要真实登录 Temu 和 Edge CDP 环境，无法自动化。
- `node` 命令必须在系统 PATH 中，否则 `_start_retail_price_script` 会启动失败。
- 与 activity/pricing 类似，任务状态保存在内存中，Bridge 重启后丢失。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-retail-price-integration.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
