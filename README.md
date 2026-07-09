# White T-Shirt Mockup Automation

白 T 恤样机贴图自动化工具。把透明底 PNG 设计图按固定参数合成到白 T 恤 PSD 模板，输出标准电商展示图。

## 特性

- **新版方法**：缩放比例 + 顺时针旋转 + 按有效像素最高点/中心点定位
- 支持 PSD（带手部遮罩）和 PNG（单图层）两种模板
- 支持 `normal`、`multiply`、`screen`、`overlay`、`linear_burn` 混合模式
- 兼容 DX0533 旧版定位参数
- 命令行 + Python API 两种调用方式
- 附带 DX0533 完整示例

## 安装

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 开发依赖（含 pytest）
pip install -r requirements-dev.txt
```

## 快速开始

### 新版方法（推荐）

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白\W4.png" \
  --scale 0.40 \
  --rotate 1 \
  --effective-top-y 490 \
  --effective-center-x 780 \
  --blend-mode multiply
```

### 旧版方法（兼容 DX0533）

```bash
python -m white_t_mockup examples/dx0533/input/DX0533_BW_cut.png examples/dx0533/output/DX0533_BW_白T.jpg

# 或使用 scripts 下的兼容入口
python scripts/apply_mockup.py examples/dx0533/input/DX0533_BW_cut.png output.jpg
```

## 命令行参数

### 新版方法参数

| 参数 | 说明 |
|------|------|
| `--scale` | 贴图缩放比例（如 0.40 = 40%）。提供后启用新版方法 |
| `--rotate` | 顺时针旋转角度 |
| `--effective-top-y` | 有效像素最高点 Y 坐标 |
| `--effective-center-x` | 有效像素水平中心 X 坐标 |

### 旧版方法参数（兼容）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top-y` | 449 | 贴图最高点 Y 坐标 |
| `--center-x` | 735 | 贴图水平中心 X 坐标 |
| `--target-height` | 677 | 贴图缩放后高度（像素） |

### 公共参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--template` | `D:\Semems\1胚衣\白\3.psd` | 模板路径（PSD 或 PNG） |
| `--blend-mode` | `multiply` | 贴图混合模式 |
| `--quality` | 95 | JPG 输出质量 |

## Python API

```python
from white_t_mockup import apply_mockup_transform

apply_mockup_transform(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白\W4.png",
    scale=0.40,
    rotation_degrees=1.0,
    effective_top_y=490,
    effective_center_x=780,
    blend_mode="multiply",
    quality=95,
)
```

## 项目结构

```
.
├── white_t_mockup/        # 核心 Python 包
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py             # 命令行入口
│   ├── core.py            # 合成核心逻辑
│   └── config.py          # 默认参数
├── scripts/
│   └── apply_mockup.py    # 兼容旧用法的单文件入口
├── tests/
│   ├── test_core.py       # 旧版方法单元测试
│   └── test_transform.py  # 新版 transform 方法单元测试
├── examples/
│   └── dx0533/            # DX0533 示例输入输出
├── docs/
│   ├── ARCHITECTURE.md    # 架构说明
│   └── TROUBLESHOOTING.md # 问题与解决方案
├── .kimi/
│   └── skills/
│       └── white-t-mockup/
│           └── SKILL.md   # Kimi Code Skill
├── requirements.txt
├── requirements-dev.txt
├── VERSION
└── CHANGELOG.md
```

## 测试

```bash
pytest
```

## 版本

当前版本：`1.1.0`

## 文档索引

- [架构说明](docs/ARCHITECTURE.md)
- [问题与解决方案](docs/TROUBLESHOOTING.md)
- [更新日志](CHANGELOG.md)
