# 单面款贴图分流修复 — 位置说明（2026-07-10）

## 结论

「单面款（02_REM_BG 只有 W 或只有 B，含反黑 `_黑W` / 反白 `_白W`）误走平铺图贴图」的修复，**不在本仓库**，实际落在：

- 04_OS 仓库 `D:/Semems WB/04_OS`（GitHub `jordan23kevin/semems-wb-04os`）→ tag **`v2.2.7`**
- PS 脚本仓库 `E:/Claude code/ps`（GitHub `jordan23kevin/ps-compositing`）→ tag **`v2.4`**

## 为什么不在本仓改

- 本仓 `engine/check_rem.py` 与 04_OS 的 `engine/check_rem.py` 是**深度分叉**的两个版本（函数集 / 路由均不同）。
- 真正被 `lovart_bridge.bat` → `lovart_bridge.py` 守护线程拉起、监听端口 8766 的进程，命令行指向 `D:/Semems WB/04_OS/engine/check_rem.py`（已用 `Get-CimInstance Win32_Process` 验证）。
- 因此本仓 `engine/check_rem.py` 当前**不被运行**，保留为历史 / 参考副本；本次未对它做功能性改动。

## 复现 / 回滚

- 复现修复：04_OS 仓库 `git checkout v2.2.7`，ps 仓库 `git checkout v2.4`。
  - 重启 check_rem 需先 kill 旧 8766 进程由守护重拉（见 04_OS `.kimi/skills/wb-os/SKILL.md`「常见问题」第 7 条）。
- 回滚：04_OS `git reset --hard v2.2.6`（或更早 tag），ps `git reset --hard v2.3`。

## 涉及的功能要点（仅记录，代码在 04_OS / ps）

- `check_rem.py` 的 `_run_one_sticker(dx)` 按「去黑/白前缀后的真实面集合」判单面：只有 W 或只有 B → 模特图贴图（`white_t_mockup`）；含 BW/WB 或 B+W → 平铺图贴图。
- ps 脚本新增 `real_sides()` / `cleanup_stale_uploads()`，作为直接跑 PS / 历史残留场景的兜底。
