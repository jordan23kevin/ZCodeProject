# Lovart-WB 系统架构文档 v2.0

> 工程类型: 图像生产血缘数据库 + 控制面板
> 遵循: B+ 四层血缘闭环架构

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Chrome 浏览器                          │
│  ┌─────────────────┐    ┌───────────────────────────┐   │
│  │ lovart_control   │    │ AI vs 去背 对比预览       │   │
│  │ (端口 8765)      │    │ (端口 8766 / check_rem.py)│   │
│  └────────┬────────┘    └──────────┬────────────────┘   │
└───────────┼────────────────────────┼────────────────────┘
            │ HTTP/JSON              │ HTTP/JSON
            ▼                        ▼
┌──────────────────────┐  ┌──────────────────────┐
│   lovart_bridge.py    │  │   check_rem.py       │
│   (Flask Server)      │  │   (预览 + 去背)      │
│                       │  │                      │
│   API端点:            │  │   API端点:            │
│   /api/inbox          │  │   /thumb             │
│   /api/generate       │  │   /rembg             │
│   /api/provenance     │  │   /batch-rembg       │
│   /api/lineage/*      │  │   /open, /del        │
│   /api/projects       │  │   ...                │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │ (Hook)
           │    POST /api/lineage/register
           ▼                         ▼
┌────────────────────────────────────────────────────────┐
│              Registry (数据核心)                        │
│                                                        │
│  D:\Semems WB\.image_registry.json  (v4)               │
│    ├── images: { MD5 → entry }                         │
│    │     ├── source_md5, source_type (溯源)             │
│    │     ├── derived_md5s, lineage_status              │
│    │     ├── root_md5, root_name (原始来源)             │
│    │     └── uid, group_id, events                     │
│    ├── groups: { group_id → group }                    │
│    ├── uid_index: { uid → md5 }                        │
│    ├── provenance.tree (亲子索引)                       │
│    └── version: 4                                      │
│                                                        │
│  D:\Semems WB\WB_REGISTRY\registry.json                │
│    └── Lovart 管线自身的 SHA256 注册表                  │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│              文件系统 (数据存储)                         │
│                                                        │
│  D:\Semems WB\                                         │
│    ├── 01_INBOX\           源图输入                     │
│    │     ├── 回收站\        本地回收站                   │
│    │     └── _hover_cache\  悬停预览缓存                 │
│    ├── 02_PROJECTS\        DX 项目目录                  │
│    │     ├── DX0001\                                    │
│    │     │     ├── 01_AI\         AI 生成图              │
│    │     │     ├── 02_REM_BG\     去背图                 │
│    │     │     ├── 03_UPLOAD\     贴图/上传              │
│    │     │     ├── source_map.json                      │
│    │     │     └── _fix_log.json  修复记录               │
│    │     ├── DX0002\                                    │
│    │     └── ...                                        │
│    ├── 04_OS\              引擎/工具                     │
│    │     ├── engine\                                    │
│    │     │     ├── check_rem.py   去背预览服务           │
│    │     │     ├── check_sync.py  同步检查               │
│    │     │     └── _rembg_worker.py                     │
│    │     └── scripts\         脚本工具集                 │
│    ├── 01_CHECK_REM\        缩略图缓存                   │
│    ├── WB_REGISTRY\         Lovart 注册表               │
│    ├── WB_SAFE_FS\          安全文件系统                 │
│    └── _temp_rembg\         去背暂存                     │
└────────────────────────────────────────────────────────┘
```

---

## 血缘引擎（B+ 四层架构）

```
            Hook (实时)          Scanner (推断)       Reconciler (修复)
               │                     │                     │
               ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Bridge API Server                        │
│  POST /api/lineage/register (confirmed)                      │
│  POST /api/scan-provenance (inferred)                        │
│  AutoScan 60s (后台线程)                                     │
└─────────────────────────────────────────────────────────────┘
```

### 血缘链路

```
原图(INBOX) ──Lovart──→ AI图(DX/01_AI) ──去背──→ 去背图(DX/02_REM_BG) ──贴图──→ 贴图图(DX/03_UPLOAD)
  MD5: aaa         MD5: bbb           MD5: ccc             MD5: ddd
```

### lineage_status 可信度

| 状态 | 来源 | 说明 |
|------|------|------|
| `confirmed` | Hook 实时记录 | 工具执行后主动通知 |
| `inferred` | Scanner 推断 | 文件名 stem 匹配 |
| `missing` | Reconciler 标记 | 断链待修复 |

---

## 部署要求

### 环境

- Python 3.11+
- Windows 10/11
- Chrome 浏览器

### Python 依赖

```
flask>=3.0
Pillow>=10.0
requests>=2.0
```

安装：`pip install flask Pillow requests`

### 路径

```
Python:     C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe
PYTHONPATH: E:/python_packages
Chrome:     C:/Program Files/Google/Chrome/Application/chrome.exe
```

---

## 启动方式

### 方式一：双击 `lovart_bridge.bat`（推荐）
```
D:\Semems WB\01_INBOX\lovart_bridge.bat
```

### 方式二：手动启动
```bash
cd C:\Users\Administrator\ZCodeProject
PYTHONPATH=E:/python_packages python lovart_bridge.py
# 打开 http://127.0.0.1:8765
```

### 去背预览（独立）
```bash
cd D:\Semems WB\04_OS\engine
PYTHONPATH=E:/python_packages python check_rem.py
# 或从控制面板点击 🔍 去背预览
```

---

## 端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Lovart-WB Bridge | 8765 | 控制面板 + API |
| check_rem.py | 8766 | AI vs 去背对比预览 |
| lovart-official | (无) | CLI 管线 |

---

## 数据流示例

### AI 生图
```
用户勾选 INBOX 图片 → 点击生图
  → Bridge 分配 UID/group_id → 写入 registry
  → 调用 Lovart 管线（run_official_v53.py）
  → 管线输出 DX*/01_AI/
  → Bridge 更新 registry（路径 + 溯源）
  → AutoScan 60s 自动补充血缘
```

### 去背（单张）
```
用户在 check_rem 页面点击 🔄
  → check_rem 驱动美图秀秀 GUI
  → 成功后 Hook → POST /api/lineage/register
  → Bridge 记录 confirmed 血缘
```

### 批量去背
```
用户勾选多个 DX 款 → 点击 ⚡ 批量去背
  → 一次暂存所有 AI 图
  → 一次美图处理全部
  → 逐条 Hook 记录血缘
```

---

## 疑难解答

### 预览图不显示
1. 按 `Ctrl+Shift+R` 强制刷新
2. F12 → Network → 勾选 Disable cache
3. 删除 `__pycache__` 目录后重启
4. 确保只用一个 Chrome 标签页

### 文件跳号
```
max_dx_num 在 WB_REGISTRY/registry.json 中
修正：python -c "import json;..."
```

### 端口被占用
```bash
netstat -ano | findstr 8765
taskkill /F /PID <PID>
```
