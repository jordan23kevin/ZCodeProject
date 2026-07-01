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
│                       │  │   check_rem.js       │
│   API端点:            │  │   (独立JS文件)        │
│   /api/inbox          │  │                      │
│   /api/generate       │  │   API端点:            │
│   /api/provenance     │  │   /thumb             │
│   /api/lineage/*      │  │   /rembg             │
│   /api/projects       │  │   /batch-rembg       │
│   ...                 │  │   /check_rem.js      │
└──────────┬───────────┘  │   ...                 │
           │              └──────────┬───────────┘
           │    POST /api/lineage/register
           ▼                         ▼
┌────────────────────────────────────────────────────────┐
│              Registry (数据核心)                        │
│  D:\Semems WB\.image_registry.json  (v4)               │
│    ├── images: { MD5 → entry }                         │
│    │     ├── source_md5, source_type (溯源)             │
│    │     ├── derived_md5s, lineage_status              │
│    │     ├── root_md5, root_name (原始来源)             │
│    │     └── uid, group_id, events                     │
│    ├── groups, uid_index, provenance.tree              │
│    └── version: 4                                      │
└────────────────────────────────────────────────────────┘
```

## 关键技术决策

### JS 独立文件（v2.0 关键改进）

check_rem.py 的 HTML 模板使用 Python f-string 生成，JS 代码中的 `{}` 与 f-string 语法冲突。
**解决方案**: 将 JavaScript 提取到独立 `check_rem.js` 文件，通过 `<script src="/check_rem.js">` 引入。
这彻底消除了 f-string 转义问题，使 JS 代码可独立开发和调试。

### 血缘引擎（B+ 四层架构）

```
Hook(实时) → Bridge写入 → Scanner(推断) → Reconciler(修复)
```

- **confirmed**: Hook 实时记录（去背成功后自动 POST）
- **inferred**: Scanner 文件名 stem 推断
- **missing**: 断链待修复

### 关键经验总结

| 问题 | 教训 | 预防 |
|------|------|------|
| f-string 嵌 JS | `{` `}` 转义极易出错 | JS 独立文件 |
| 文件代码重复 | sed/编辑操作导致重复 | 每次改完检查重复 |
| 缓存问题 | `__pycache__` 残留旧编译 | 删缓存后再测试 |
| 多行字符串 | JS 单引号不能跨行 | 始终用 `\n` 转义 |

## 部署

```bash
pip install flask Pillow requests
双击 D:\Semems WB\01_INBOX\lovart_bridge.bat
# 打开 http://127.0.0.1:8765
```
