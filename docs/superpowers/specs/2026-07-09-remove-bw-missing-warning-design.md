# 去背/贴图 OS 页面移除 B/W 缺半警告

## 背景

AI 去背 贴图 OS 页面（`engine/check_rem.py`）目前会对只有 B 没有 W、或只有 W 没有 B 的款号显示红色警告：

- `⚠ 缺B`
- `⚠ 缺W`

由于业务上现在允许单面贴图（只有 B 或只有 W），这种警告已经失去意义，反而会把这些正常款号误判为“缺图”，导致：

1. 卡片被排序到页面最前面；
2. 被“📋 复制缺图款号”按钮收录。

## 目标

去掉 B/W 配对缺失的红色警告，让单面 B 或单面 W 的款号不再被视为缺图。

## 设计决策

- **展示方式**：当某个 DX 只有 B 或只有 W 时，缺失侧隐藏，存在的那一侧占满整行。
- **实现方式**：缺失侧返回空字符串，并给 B+W 行增加 flex 并排 CSS。
- **保留警告**：真正缺 AI 图（`⚠ 缺AI图`）和缺去背（`⚠ 缺去背`）的警告保持不变。

## 改动清单

### 1. `_has_missing()`（`engine/check_rem.py`，约 line 1247）

只保留以下两种“缺图”判定：

- `pr["ai_file"] is None`
- `pr["rem_file"] is None`

删除以下 B/W 配对判定：

- `_B` 缺少对应 `_W`
- `_W` 缺少对应 `_B`

### 2. `_half()`（`engine/check_rem.py`，约 line 1354）

当 `pr is None` 时，直接返回空字符串，不再渲染：

```html
<div class="cell missing" style="height:200px;"><span>⚠ 缺B</span></div>
```

或

```html
<div class="cell missing" style="height:200px;"><span>⚠ 缺W</span></div>
```

### 3. CSS（`engine/check_rem.py` 的 `<style>` 区追加）

```css
.bw-group { display:flex; gap:10px; }
.bw-half { flex:1; min-width:0; }
```

效果：

- B/W 都存在时，左右并排；
- 只有单边时，存在的一侧占满整行。

### 4. 按钮 tooltip（`engine/check_rem.py`，约 line 1543）

从：

```
复制当前日期缺图款号（缺AI图/缺去背/缺B/W配对）
```

改为：

```
复制当前日期缺图款号（缺AI图/缺去背）
```

## 不变清单

- `engine/check_rem.js` 的 `copyMissing()` 仍通过 `innerHTML.indexOf('⚠ 缺')` 抓取缺图款。由于 B/W 警告字符串被删除，单面款自然不会被复制，逻辑仍然正确，无需修改。
- `⚠ 缺AI图` 和 `⚠ 缺去背` 的警告文案、样式、排序逻辑全部保留。

## 验证标准

1. 单面 B 或单面 W 的 DX 不再显示 `⚠ 缺B` / `⚠ 缺W`。
2. 单面 B 或单面 W 的 DX 不再被排到页面最前面。
3. “复制缺图款号”不再收录只有单面 B/W 的款号。
4. 缺 AI 图 / 缺去背的款号仍然正常显示警告并被收录。
