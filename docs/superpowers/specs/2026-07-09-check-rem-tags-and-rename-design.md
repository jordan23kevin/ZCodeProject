# check_rem 页面隐藏 pipeline 标签 + 扩展改名功能

## 背景

AI 去背 贴图 OS 页面（`engine/check_rem.py`）目前存在两个问题：

1. 卡片头部显示了三个状态标签 `🎨AI`、`✂️`、`📎`，用户希望隐藏。
2. 每行图片旁的改名按钮只能把 `_B` / `_W` 改成 `_BW`，用户希望支持 `_B`、`_W`、`_BW` 三者互转。

## 目标

- 隐藏卡片头部的 pipeline 状态标签。
- 把改名功能扩展为：`_B` ↔ `_W` ↔ `_BW` 互转。

## 设计决策

- **pipeline 标签**：采用 CSS `display:none` 隐藏，保留 HTML，便于以后恢复。
- **改名交互**：把现有的 `↗BW` 按钮改为下拉选单，只列出可行的目标后缀。
- **冲突处理**：目标文件已存在时，先送回收站，再执行改名，与现有 B/W→BW 逻辑保持一致。

## 改动清单

### 1. 隐藏 pipeline 标签

在 `engine/check_rem.py` 的 `<style>` 区（约 line 1490）给 `.pipeline` 追加 `display:none;`：

```css
.pipeline {{ display:none; align-items:center; gap:5px; font-size:12px; margin-left:6px; }}
```

或新增一行覆盖：

```css
.pipeline {{ display:none; }}
```

### 2. 前端改名下拉选单

在 `_half()` 内部，把按钮：

```html
<button class="ren-btn" onclick="event.stopPropagation();renameStem('{dx}','{pr["stem"]}')" title="改为BW合并图">↗BW</button>
```

改为下拉选单。渲染时根据当前 `stem` 后缀决定显示哪些选项：

- `_B`：显示 `→ W`、`→ BW`
- `_W`：显示 `→ B`、`→ BW`
- `_BW`：显示 `→ B`、`→ W`

示例 HTML：

```html
<select class="ren-sel" onchange="if(this.value){{renameStem('{dx}','{pr["stem"]}',this.value);}} this.selectedIndex=0;" title="改名为...">
  <option value="" selected>改名...</option>
  <option value="B">→ B</option>
  <option value="W">→ W</option>
</select>
```

### 3. 后端 `/rename` 端点扩展

`/rename` 路径处理时读取 `target` 参数：

```python
qs = parse_qs(parsed.query)
target = qs.get("target", [""])[0]
```

并传给 `_rename_stem(dx, stem, target)`。

### 4. `_rename_stem()` 逻辑扩展

当前函数签名：

```python
def _rename_stem(self, dx, stem):
```

改为：

```python
def _rename_stem(self, dx, stem, target):
```

修改内容：

- 校验 `stem` 必须以 `_B`、`_W` 或 `_BW` 结尾。
- 校验 `target` 必须是 `B`、`W` 或 `BW`。
- 禁止源和目标相同（如 `_B` 改到 `B`）。
- 计算新 stem：`prefix + "_" + target`。
- 按新 stem 生成 `ai_new` 和 `rem_new`。
- 搜索 AI/REM 文件时使用原 stem。
- 目标文件存在时，先 `send_to_recycle_bin`，再 `rename`。
- 缩略图缓存清理逻辑保持不变。

### 5. 前端 JS `renameStem()` 更新

把函数签名从：

```javascript
function renameStem(dx, stem){
```

改为：

```javascript
function renameStem(dx, stem, target){
```

调用 URL 增加 `target`：

```javascript
fetch('/rename?dx='+dx+'&stem='+encodeURIComponent(stem)+'&target='+encodeURIComponent(target))
```

### 6. 下拉选单 CSS

给 `.ren-sel` 加简单样式，保持与现有 `.ren-btn` 视觉一致：

```css
.ren-sel {{ display:inline; font-size:12px; padding:1px 3px; margin-left:3px; border-radius:2px;
            background:#4caf50; color:#fff; border:none; cursor:pointer; vertical-align:middle; }}
```

## 不变清单

- 真正缺 AI 图 / 缺去背的警告和排序逻辑不变。
- 黑版变体行不改。
- 贴图、BW 合成、打开文件夹等按钮不变。
- pipeline 标签的 HTML 保留，仅通过 CSS 隐藏。

## 验证标准

1. 页面刷新后，卡片头部不再显示 `🎨AI`、`✂️`、`📎` 三个标签。
2. `_B` 行出现下拉选单，可选改为 `_W` 或 `_BW`。
3. `_W` 行出现下拉选单，可选改为 `_B` 或 `_BW`。
4. `_BW` 行出现下拉选单，可选改为 `_B` 或 `_W`。
5. 改名后，对应的 AI 文件和 REM 文件都正确重命名。
6. 目标文件已存在时，旧文件被送回收站，新文件改名成功。
