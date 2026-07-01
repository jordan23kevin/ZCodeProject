---
name: lovart-wb
description: Lovart-WB 一体化 HTML 控制系统 — 管理 AI 生图、去背、贴图的完整生产流程
---

# Lovart-WB 控制面板

## 用途

统一管理以下流程的 HTML 控制面板系统：
1. **Lovart-official（AI 生图）** — 从 INBOX 生成设计图
2. **WB 美图去背（抠图）** — 手动/批量去背
3. **PSWB 贴图（合成）** — （预留）
4. **WB 上款（成品整理）** — （预留）

## 使用方式

### 启动
```bash
双击 D:\Semems WB\01_INBOX\lovart_bridge.bat
```
或手动：`python lovart_bridge.py` → 浏览器打开 `http://127.0.0.1:8765`

### 工作流
1. 将源图放入 `D:\Semems WB\01_INBOX\`
2. 打开控制面板 → 自动显示图片网格
3. 勾选图片 → 点击「开始 LOVART 生图」
4. 等待生图完成
5. 点击「🔍 去背预览」→ 进入对比页面
6. 检查去背质量 → 逐张或批量去背

### 关键功能
- **AI 生图** — 从 INBOX 勾选图片，一键调用 Lovart API
- **去背预览** — AI 图 vs 去背图并排对比
- **批量去背** — 勾选多个款，一次美图处理全部
- **血缘追踪** — 每张图自动记录来源（原图→AI→去背→贴图）
- **回收站管理** — 网页上恢复已删图片
- **款号一致性检查** — 自动检测错放文件并提供修复

## 架构

```
HTML 控制面板 ←HTTP→ Flask Bridge ←subprocess→ Lovart 管线
                              ←Hook→       check_rem.py
                              ←AutoScan→   文件系统
```

## 端口
- 控制面板: 8765
- 去背预览: 8766

## 注意事项
- 生图消耗 Lovart API 积分（~16 积分/张）
- 去背时美图秀秀接管屏幕，勿动键鼠
- 首次启动需安装依赖：`pip install flask Pillow requests`
