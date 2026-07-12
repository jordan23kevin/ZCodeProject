# check_rem 隐藏 pipeline 标签 + 扩展改名功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `engine/check_rem.py` 中隐藏卡片头部的 `🎨AI/✂️/📎` pipeline 标签，并把 stem 改名功能扩展为 `_B`、`_W`、`_BW` 三者互转。

**Architecture:** 用 CSS `display:none` 隐藏 pipeline；把 `_half()` 里的 `↗BW` 按钮改成下拉选单；后端 `/rename` 增加 `target` 参数并扩展 `_rename_stem()` 支持六种转换；前端 `renameStem()` 同步增加 `target` 参数。

**Tech Stack:** Python 3, PIL, pytest, 内置 http.server, HTML/CSS/JS

## Global Constraints

- 只修改 `engine/check_rem.py`。
- 保留 pipeline 标签的 HTML，仅通过 CSS 隐藏。
- 冲突处理：目标文件已存在时，先送回收站，再执行改名。
- 下拉选单只显示可行的目标后缀（源不能改到自身）。
- 新增代码需与现有 `check_rem.py` 的缩进、字符串风格保持一致。

---

## File Structure

- **Modify:** `engine/check_rem.py`
  - 在 `<style>` 区隐藏 `.pipeline`（约 line 1490）。
  - 在 `_half()` 内把 `↗BW` 按钮改成下拉选单（约 line 1357）。
  - 在 `do_GET` 的 `/rename` 分支读取 `target` 参数（约 line 1196）。
  - 扩展 `_rename_stem(self, dx, stem, target)`（约 line 2262）。
  - 在 `<script>` 区更新 `renameStem()` 函数。

---

### Task 1: 隐藏 pipeline 标签

**Files:**
- Modify: `engine/check_rem.py:1490`

**Interfaces:**
- Consumes: 无。
- Produces: `.pipeline` 元素不再显示。

- [ ] **Step 1: 在 `<style>` 区追加 `.pipeline` 隐藏规则**

  找到 `.pipeline` 规则（约 line 1490）：

  ```css
  .pipeline {{ display:flex; align-items:center; gap:5px; font-size:12px; margin-left:6px; }}
  ```

  改为：

  ```css
  .pipeline {{ display:none; align-items:center; gap:5px; font-size:12px; margin-left:6px; }}
  ```

- [ ] **Step 2: 启动服务并验证标签已隐藏**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  .venv/Scripts/python -m engine.check_rem
  ```

  在另一个终端：
  ```bash
  curl -sL http://127.0.0.1:8766/ | grep -o "🎨AI\|✂️\|📎" | sort | uniq -c
  ```
  Expected: 无输出（三个 emoji 都不出现）。

- [ ] **Step 3: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py
  git commit -m "feat(check_rem): hide pipeline status tags via CSS"
  ```

---

### Task 2: 扩展后端 `_rename_stem()` 支持 B/W/BW 互转

**Files:**
- Modify: `engine/check_rem.py:1196-1197`（`/rename` 分支读取 target）
- Modify: `engine/check_rem.py:2262-2303`（`_rename_stem` 函数）

**Interfaces:**
- Consumes: HTTP query params `dx`, `stem`, `target`。
- Produces: `_rename_stem(self, dx, stem, target)` 支持 `target ∈ {"B", "W", "BW"}`。

- [ ] **Step 1: 在 `/rename` 分支读取 `target` 参数**

  找到 `/rename` 处理（约 line 1196-1197）：

  ```python
  elif path == "/rename":
      self._rename_stem(dx, stem)
  ```

  改为：

  ```python
  elif path == "/rename":
      target = qs.get("target", [""])[0]
      self._rename_stem(dx, stem, target)
  ```

- [ ] **Step 2: 修改 `_rename_stem` 函数签名和校验逻辑**

  把：
  ```python
  def _rename_stem(self, dx, stem):
      if not re.match(r"^DX\d+$", dx) or not stem or "/" in stem or "\\" in stem:
          self._send_json({"ok": False, "msg": "参数非法"}); return
      if not (stem.endswith("_B") or stem.endswith("_W")):
          self._send_json({"ok": False, "msg": "只有B/W可以改为BW"}); return
      prefix = stem[:-2]  # DX0264
      new_stem = prefix + "_BW"
  ```

  改为：

  ```python
  def _rename_stem(self, dx, stem, target):
      if not re.match(r"^DX\d+$", dx) or not stem or "/" in stem or "\\" in stem:
          self._send_json({"ok": False, "msg": "参数非法"}); return
      source = stem[-2:] if stem.endswith(("_B", "_W")) else (stem[-3:] if stem.endswith("_BW") else "")
      if source not in ("_B", "_W", "_BW"):
          self._send_json({"ok": False, "msg": "源文件名后缀必须是 _B/_W/_BW"}); return
      if target not in ("B", "W", "BW"):
          self._send_json({"ok": False, "msg": "目标必须是 B/W/BW"}); return
      if source == "_" + target:
          self._send_json({"ok": False, "msg": "源和目标相同"}); return
      prefix = stem[:-len(source)]  # DX0264
      new_stem = prefix + "_" + target
  ```

- [ ] **Step 3: 运行现有测试，确保没有回归**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  .venv/Scripts/python -m pytest tests/test_check_rem.py -v
  ```
  Expected: 5 passed

- [ ] **Step 4: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py
  git commit -m "feat(check_rem): extend rename endpoint to support B/W/BW conversion"
  ```

---

### Task 3: 前端下拉选单 + JS 更新

**Files:**
- Modify: `engine/check_rem.py:1357`（`_half()` 内按钮改下拉）
- Modify: `engine/check_rem.py:1480-1483` 附近（`.ren-btn` CSS 区域，新增 `.ren-sel`）
- Modify: `engine/check_rem.py` 的 `<script>` 区 `renameStem()` 函数

**Interfaces:**
- Consumes: `_rename_stem()` 现在需要 `target`。
- Produces: 前端 `renameStem(dx, stem, target)` 会带 `target` 调用 `/rename`。

- [ ] **Step 1: 在 `_half()` 内根据当前后缀生成下拉选单**

  找到按钮代码（约 line 1357）：

  ```python
  <button class="ren-btn" onclick="event.stopPropagation();renameStem('{dx}','{pr["stem"]}')" title="改为BW合并图">↗BW</button>
  ```

  替换为：

  ```python
  opts = []
  if pr["stem"].endswith("_B"):
      opts = [("W", "→ W"), ("BW", "→ BW")]
  elif pr["stem"].endswith("_W"):
      opts = [("B", "→ B"), ("BW", "→ BW")]
  elif pr["stem"].endswith("_BW"):
      opts = [("B", "→ B"), ("W", "→ W")]
  opt_html = "".join(f'<option value="{k}">{v}</option>' for k, v in opts)
  ```

  并在 HTML 中插入：

  ```python
  f'<select class="ren-sel" onchange="event.stopPropagation(); if(this.value){{renameStem(\'{dx}\',\'{pr["stem"]}\',this.value);}} this.selectedIndex=0;" title="改名为...">'
  f'<option value="" selected>改名...</option>{opt_html}</select>'
  ```

  注意字符串转义：因为外层是 f-string 三引号，内部 `"renameStem(...)'` 里的单引号要转义成 `\'`。

- [ ] **Step 2: 添加 `.ren-sel` CSS**

  在 `.ren-btn` 规则之后（约 line 1482-1483）插入：

  ```css
  .ren-sel {{ display:inline; font-size:12px; padding:1px 3px; margin-left:3px; border-radius:2px;
              background:#4caf50; color:#fff; border:none; cursor:pointer; vertical-align:middle; }}
  ```

- [ ] **Step 3: 更新 JS `renameStem()`**

  找到：
  ```javascript
  function renameStem(dx,stem){
    var msg='将 '+dx+'/'+stem+' 改为BW？\n文件: '+stem+'.png → '+stem.slice(0,-2)+'_BW.png\n去背: '+stem+'_cut.png → '+stem.slice(0,-2)+'_BW_cut.png';
    if(!confirm(msg))return;
    fetch('/rename?dx='+dx+'&stem='+encodeURIComponent(stem)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok) setTimeout(function(){ location.reload(); },1500);});
  }
  ```

  改为：

  ```javascript
  function renameStem(dx,stem,target){
    var newStem = stem.slice(0, stem.lastIndexOf('_')+1) + target;
    var msg='将 '+dx+'/'+stem+' 改为 '+newStem+'？\n文件: '+stem+'.png → '+newStem+'.png\n去背: '+stem+'_cut.png → '+newStem+'_cut.png';
    if(!confirm(msg))return;
    fetch('/rename?dx='+dx+'&stem='+encodeURIComponent(stem)+'&target='+encodeURIComponent(target)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok) setTimeout(function(){ location.reload(); },1500);});
  }
  ```

- [ ] **Step 4: 运行测试，确保没有回归**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  .venv/Scripts/python -m pytest tests/test_check_rem.py -v
  ```
  Expected: 5 passed

- [ ] **Step 5: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py
  git commit -m "feat(check_rem): add rename target dropdown and update JS"
  ```

---

### Task 4: 端到端验证

**Files:**
- 无新增/修改。

- [ ] **Step 1: 重启服务**

  先杀掉旧进程：
  ```powershell
  Get-NetTCPConnection -LocalPort 8766 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique | Where-Object { $_ -gt 4 } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
  ```

  然后启动：
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  .venv/Scripts/python -m engine.check_rem
  ```

- [ ] **Step 2: 验证 pipeline 标签已隐藏**

  ```bash
  curl -sL http://127.0.0.1:8766/ | grep -o "🎨AI\|✂️\|📎" | sort | uniq -c
  ```
  Expected: 无输出。

- [ ] **Step 3: 验证改名下拉选单 HTML**

  ```bash
  curl -sL http://127.0.0.1:8766/ | grep -o 'class="ren-sel"' | wc -l
  ```
  Expected: 非零（等于有改名权限的 pair 数量）。

  ```bash
  curl -sL http://127.0.0.1:8766/ | grep -o '<option value="BW">→ BW</option>' | wc -l
  ```
  Expected: 非零。

- [ ] **Step 4: 手动改名验证**

  在浏览器打开 `http://127.0.0.1:8766/`，对某个 `_B` 款选择 `→ W`，确认：
  - 弹出确认框内容正确。
  - 改名后页面刷新。
  - `01_AI` 和 `02_REM_BG` 中对应文件都已重命名。
  - 如果目标 `_W` 已存在，旧 `_W` 文件被送进回收站。

---

## Spec Coverage

| Spec 要求 | 对应 Task |
|---|---|
| 隐藏 `🎨AI/✂️/📎` pipeline 标签 | Task 1 |
| 改名支持 `_B` ↔ `_W` ↔ `_BW` | Task 2 + Task 3 |
| 下拉选单只显示可行目标 | Task 3 |
| 冲突时送回收站 | Task 2 |

## Placeholder Scan

- 无 `TBD` / `TODO` / `implement later` / `fill in details`。
- 所有代码块均为实际可运行代码。
- 所有命令均包含期望输出。
