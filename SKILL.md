---
name: lovart-wb
description: Lovart-WB 一体化 HTML 控制系统 v2.1 — 管理 AI 生图、去背、贴图成品的完整生产流程
---

# Lovart-WB 控制面板

## 用途

统一管理以下流程的 HTML 控制面板系统：
1. **Lovart-official（AI 生图）** — 从 INBOX 生成设计图
2. **WB 美图去背（抠图）** — 手动/批量去背
3. **PSWB 贴图（合成）** — 白T/黑T贴图 + BW 合成
4. **WB 上款（成品整理）** — 输出到 `03_UPLOAD`

## 使用方式

### 启动
```bash
# 一键启动（推荐）
双击 D:\Semems WB\01_INBOX\lovart_bridge.bat

# 手动启动 Bridge
python C:\Users\Administrator\ZCodeProject\lovart_bridge.py

# 手动启动去背预览
python D:\Semems WB\04_OS\engine\check_rem.py
```

浏览器打开 `http://127.0.0.1:8765`（Bridge）或 `http://127.0.0.1:8766`（去背预览）。

### 工作流
1. 将源图放入 `D:\Semems WB\01_INBOX\`
2. 打开 Bridge 控制面板 → 自动显示图片网格
3. 勾选图片 → 点击「开始 LOVART 生图」
4. 等待生图完成
5. 点击「🔍 去背预览」→ 进入 `check_rem.py` 对比页面
6. 检查去背质量 → 逐张或批量去背
7. 检查贴图成品 → 点击「📎 贴图」一键完成 B/W 贴图 + BW 合成

### 关键功能
- **AI 生图** — 从 INBOX 勾选图片，一键调用 Lovart API
- **去背预览** — AI 图 vs 去背图 vs 贴图成品并排对比
- **批量去背** — 勾选多个款，一次美图处理全部
- **一键贴图+BW合成** — 黑T优先用黑版专用文件，白T用通用文件，最后自动合成 BW
- **反相黑版** — 点击「反相」自动生成 `DX_黑B/W/BW_cut.png` 并自动重跑贴图
- **一键放大** — 去背图分辨率不足 2000×2000 时显示 🔍，点击放大到 2046×2046
- **血缘追踪** — 每张图自动记录来源（原图→AI→去背→贴图）
- **回收站管理** — 网页上恢复已删图片
- **款号一致性检查** — 自动检测错放文件并提供修复

## 架构

```
HTML 控制面板 ←HTTP→ Flask Bridge ←subprocess→ Lovart 管线
                              ←Hook→       check_rem.py
                              ←subprocess→  PS 贴图流水线
                              ←AutoScan→   文件系统
```

## 端口
- 控制面板: 8765
- 去背预览: 8766

## 注意事项
- 生图消耗 Lovart API 积分（~16 积分/张）
- 去背时美图秀秀接管屏幕，勿动键鼠
- 贴图/BW合成时 PS 会隐藏/最小化，但仍会占用键鼠，请等待完成
- 首次启动需安装依赖：`pip install flask Pillow requests pywin32 pythoncom numpy`
- 确保 Photoshop 路径与 `config.py` / 脚本中的 `PS_EXE` 一致
