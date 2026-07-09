# White T-Shirt Mockup Automation

白 T 恤样机贴图自动化工具。把透明底 PNG 设计图按固定参数合成到白 T 恤 PSD 模板，输出标准电商展示图。

## 特性

- 固定 DX0533 验证过的参数：位置、大小、混合模式
- 自动识别 PSD 模板中的背景层和手部前景遮罩
- 支持 `normal`、`multiply`、`screen`、`overlay`、`linear_burn` 混合模式
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

```bash
# 使用默认白 T 参数生成样机
python -m white_t_mockup examples/dx0533/input/DX0533_BW_cut.png examples/dx0533/output/DX0533_BW_白T.jpg

# 或使用 scripts 下的兼容入口
python scripts/apply_mockup.py examples/dx0533/input/DX0533_BW_cut.png output.jpg
```

## 命令行参数

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白\3.psd" \
  --top-y 449 \
  --center-x 735 \
  --target-height 677 \
  --blend-mode multiply \
  --quality 95
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--template` | `D:\Semems\1胚衣\白\3.psd` | PSD 模板路径 |
| `--top-y` | 449 | 贴图最高点 Y 坐标 |
| `--center-x` | 735 | 贴图水平中心 X 坐标 |
| `--target-height` | 677 | 贴图缩放后高度（像素） |
| `--blend-mode` | `multiply` | 贴图混合模式 |
| `--quality` | 95 | JPG 输出质量 |

## Python API

```python
from white_t_mockup import apply_mockup

apply_mockup(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白\3.psd",
    top_y=449,
    center_x=735,
    target_height=677,
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
│   └── test_core.py       # 单元测试
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

当前版本：`1.0.0`

## 文档索引

- [架构说明](docs/ARCHITECTURE.md)
- [问题与解决方案](docs/TROUBLESHOOTING.md)
- [更新日志](CHANGELOG.md)
