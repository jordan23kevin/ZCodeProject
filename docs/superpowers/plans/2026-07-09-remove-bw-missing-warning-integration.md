# 去背/贴图 OS 页面移除 B/W 缺半警告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `engine/check_rem.py` 中移除只有单面 B 或单面 W 时显示的 `⚠ 缺B` / `⚠ 缺W` 警告，让单面贴图不再被视为缺图。

**Architecture:** 将 `_has_missing()` 提取为模块级函数以便测试；`_half()` 在缺失侧返回空字符串；新增 `.bw-group`/`.bw-half` flex 样式使 B/W 并排、单边占满；更新按钮 tooltip。

**Tech Stack:** Python 3, PIL, pytest, 内置 http.server

## Global Constraints

- 只修改 `engine/check_rem.py`，不动 JS/其他文件。
- 保留真正的缺图警告：`⚠ 缺AI图`、`⚠ 缺去背`。
- 单面 B/W 的 DX 不再排到最前面，也不再被“复制缺图款号”收录。
- 新增代码需与现有 `check_rem.py` 的缩进、字符串风格保持一致。

---

## File Structure

- **Modify:** `engine/check_rem.py`
  - 提取 `_has_missing()` 到模块级（约 line 1247 附近）。
  - 修改 `_half()` 的缺失分支（约 line 1354 附近）。
  - 在 `<style>` 区追加 `.bw-group`、`.bw-half` CSS（约 line 1473 附近）。
  - 更新“复制缺图款号”按钮 tooltip（约 line 1543 附近）。
- **Create:** `tests/test_check_rem.py`
  - 对提取后的 `_has_missing()` 进行单元测试。

---

### Task 1: 提取 `_has_missing()` 并添加单元测试

**Files:**
- Modify: `engine/check_rem.py:1247-1257`
- Create: `tests/test_check_rem.py`

**Interfaces:**
- Consumes: `projects` 字典结构（来自 `scan_projects()`）。
- Produces: 模块级函数 `_has_missing(projects)`，返回 `bool`。

- [ ] **Step 1: 在 `engine/check_rem.py` 中把 `_has_missing()` 提取到模块级**

  在 `_render_html()` 外部（例如文件靠后的工具函数区域，或紧邻 `_render_html()` 上方）添加：

  ```python
  def _has_missing(proj):
      """判断一个 project 是否真正缺图（只检查 AI/REM 文件缺失，不检查 B/W 配对）。"""
      for pr in proj["pairs"]:
          if pr["ai_file"] is None or pr["rem_file"] is None:
              return True
      return False
  ```

  然后删除 `_render_html()` 内部的同名嵌套函数，并把调用处改为直接使用模块级函数：

  ```python
  projects = sorted(projects, key=lambda p: (0 if _has_missing(p) else 1, p["dx"]))
  ```

- [ ] **Step 2: 创建 `tests/test_check_rem.py`**

  ```python
  import sys
  import os

  sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))

  from check_rem import _has_missing


  def _pair(stem, ai_file, rem_file):
      return {
          "stem": stem,
          "ai_file": ai_file,
          "rem_file": rem_file,
          "group_id": "",
          "ai_uid": None,
          "rem_uid": None,
          "ai_stage": "ai",
          "rem_stage": "rembg" if rem_file else None,
          "role": "B" if stem.endswith("_B") else "W" if stem.endswith("_W") else "BW",
      }


  def test_has_missing_single_b_is_not_missing():
      proj = {
          "dx": "DX0001",
          "pairs": [_pair("DX0001_B", "DX0001_B.png", "DX0001_B_cut.png")],
      }
      assert _has_missing(proj) is False


  def test_has_missing_single_w_is_not_missing():
      proj = {
          "dx": "DX0001",
          "pairs": [_pair("DX0001_W", "DX0001_W.png", "DX0001_W_cut.png")],
      }
      assert _has_missing(proj) is False


  def test_has_missing_missing_ai_is_missing():
      proj = {
          "dx": "DX0001",
          "pairs": [_pair("DX0001_B", None, "DX0001_B_cut.png")],
      }
      assert _has_missing(proj) is True


  def test_has_missing_missing_rem_is_missing():
      proj = {
          "dx": "DX0001",
          "pairs": [_pair("DX0001_B", "DX0001_B.png", None)],
      }
      assert _has_missing(proj) is True


  def test_has_missing_both_b_and_w_complete_is_not_missing():
      proj = {
          "dx": "DX0001",
          "pairs": [
              _pair("DX0001_B", "DX0001_B.png", "DX0001_B_cut.png"),
              _pair("DX0001_W", "DX0001_W.png", "DX0001_W_cut.png"),
          ],
      }
      assert _has_missing(proj) is False
  ```

- [ ] **Step 3: 运行测试，确保通过**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  python -m pytest tests/test_check_rem.py -v
  ```
  Expected: 5 passed

- [ ] **Step 4: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py tests/test_check_rem.py
  git commit -m "refactor(check_rem): extract _has_missing and drop B/W pairing check"
  ```

---

### Task 2: 移除 `_half()` 的 B/W 缺半警告并添加 CSS

**Files:**
- Modify: `engine/check_rem.py:1354-1372`
- Modify: `engine/check_rem.py:1440-1485`（`<style>` 区域）

**Interfaces:**
- Consumes: `_half()` 调用时传入的 `pr`（可能为 `None`）。
- Produces: `pr is None` 时返回空字符串；存在时渲染不变。

- [ ] **Step 1: 修改 `_half()`，缺失侧返回空字符串**

  把：
  ```python
                def _half(dx, pr, badge_class, badge_text, missing_text):
                    if pr:
                        gid = pr.get("group_id", "")
                        return f'''<div class="bw-half" data-group-id="{gid}" data-ai-uid="{pr.get("ai_uid") or ""}" data-rem-uid="{pr.get("rem_uid") or ""}" data-stem="{pr["stem"]}">
                            <div class="stem"><span class="badge {badge_class}">{badge_text}</span>
                                <button class="ren-btn" onclick="event.stopPropagation();renameStem('{dx}','{pr["stem"]}')" title="改为BW合并图">↗BW</button></div>
                            {_render_cells(dx, pr)}
                        </div>'''
                    else:
                        return f'''<div class="bw-half">
                            <div class="stem"><span class="badge {badge_class}">{badge_text}</span></div>
                            <div class="cell missing" style="height:200px;"><span>{missing_text}</span></div>
                        </div>'''
  ```

  改为：
  ```python
                def _half(dx, pr, badge_class, badge_text):
                    if not pr:
                        return ""
                    gid = pr.get("group_id", "")
                    return f'''<div class="bw-half" data-group-id="{gid}" data-ai-uid="{pr.get("ai_uid") or ""}" data-rem-uid="{pr.get("rem_uid") or ""}" data-stem="{pr["stem"]}">
                        <div class="stem"><span class="badge {badge_class}">{badge_text}</span>
                            <button class="ren-btn" onclick="event.stopPropagation();renameStem('{dx}','{pr["stem"]}')" title="改为BW合并图">↗BW</button></div>
                        {_render_cells(dx, pr)}
                    </div>'''
  ```

  同时把调用处从：
  ```python
                left  = _half(dx, b_pr, "badge-b", "B", "⚠ 缺B")
                right = _half(dx, w_pr, "badge-w", "W", "⚠ 缺W")
  ```
  改为：
  ```python
                left  = _half(dx, b_pr, "badge-b", "B")
                right = _half(dx, w_pr, "badge-w", "W")
  ```

- [ ] **Step 2: 在 `<style>` 区追加 flex 样式**

  在 `.badge-w` 规则之后（约 line 1476）插入：

  ```css
  .bw-group { display:flex; gap:10px; }
  .bw-half { flex:1; min-width:0; }
  ```

- [ ] **Step 3: 运行测试，确保没有回归**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  python -m pytest tests/test_check_rem.py -v
  ```
  Expected: 5 passed

- [ ] **Step 4: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py
  git commit -m "feat(check_rem): hide missing B/W half and add flex layout"
  ```

---

### Task 3: 更新“复制缺图款号”按钮 tooltip

**Files:**
- Modify: `engine/check_rem.py:1543`

**Interfaces:**
- Consumes: 无。
- Produces: 按钮 `title` 文案变更。

- [ ] **Step 1: 修改 tooltip 文案**

  把：
  ```html
  <button onclick="copyMissing()" title="复制当前日期缺图款号（缺AI图/缺去背/缺B/W配对）" style="background:#e91e63;">📋 复制缺图款号</button>
  ```
  改为：
  ```html
  <button onclick="copyMissing()" title="复制当前日期缺图款号（缺AI图/缺去背）" style="background:#e91e63;">📋 复制缺图款号</button>
  ```

- [ ] **Step 2: 运行测试，确保没有回归**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  python -m pytest tests/test_check_rem.py -v
  ```
  Expected: 5 passed

- [ ] **Step 3: 提交**

  ```bash
  cd C:/Users/Administrator/ZCodeProject
  git add engine/check_rem.py
  git commit -m "docs(check_rem): update copyMissing tooltip to remove B/W pairing mention"
  ```

---

### Task 4: 手动验证

**Files:**
- 无新增/修改。

- [ ] **Step 1: 启动服务并打开页面**

  Run:
  ```bash
  cd C:/Users/Administrator/ZCodeProject
  python -m engine.check_rem
  ```

  在浏览器打开 `http://localhost:8766/`。

- [ ] **Step 2: 检查单面 B/W 款号**

  找到只有 `_B` 或只有 `_W` 的 DX 卡片，确认：
  - 不显示 `⚠ 缺B` 或 `⚠ 缺W`。
  - 存在的一侧正常显示 AI/REM 缩略图。
  - 卡片没有排在最前面（除非同时真的缺 AI/REM）。

- [ ] **Step 3: 检查“复制缺图款号”**

  点击页面顶部“📋 复制缺图款号”按钮，确认复制的 DX 列表中不包含只有单面 B/W 的款号。

- [ ] **Step 4: 检查真正的缺图警告仍然生效**

  找到缺 AI 图或缺去背的 DX，确认：
  - 仍然显示 `⚠ 缺AI图` 或 `⚠ 缺去背`。
  - 这些款号仍然被“复制缺图款号”收录。

---

## Spec Coverage

| Spec 要求 | 对应 Task |
|---|---|
| 去掉 `⚠ 缺B` / `⚠ 缺W` 显示 | Task 2 |
| 单面 B/W 不再被视为缺图 | Task 1 |
| 缺失侧隐藏，存在侧占满整行 | Task 2（`_half()` 返回空字符串 + flex CSS） |
| 保留 `⚠ 缺AI图` / `⚠ 缺去背` | Task 1（`_has_missing` 逻辑）+ Task 4 手动验证 |
| 更新按钮 tooltip | Task 3 |

## Placeholder Scan

- 无 `TBD` / `TODO` / `implement later` / `fill in details`。
- 所有代码块均为实际可运行代码。
- 所有命令均包含期望输出。
