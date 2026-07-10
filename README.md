# White T-Shirt Mockup Automation

白 T 恤样机贴图自动化工具。把透明底 PNG 设计图按固定参数合成到白 T 恤 PSD 模板，输出标准电商展示图。

## 特性

- **新版方法**：最终像素（宽/高） + 旋转（正=顺时针/负=逆时针） + 按有效像素最高点/中心点定位
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

### 使用模板预设（推荐）

```bash
# 列出已配置模板
python -m white_t_mockup --list-presets

# 用预设自动加载参数
python -m white_t_mockup design.png output.jpg --preset 白正2.jpg
```

### 手动指定新版参数

```bash
python -m white_t_mockup design.png output.jpg \
  --template "D:\Semems\1胚衣\白正2.jpg" \
  --final-w 546 \
  --final-h 546 \
  --rotate -2 \
  --effective-top-y 644 \
  --effective-center-x 670 \
  --blend-mode multiply
```

### 反黑/反白预处理

新版默认使用亮度反相（HSV Value Invert），保留颜色，只反转明暗：

```bash
# 适合黑色 T 恤
python -m white_t_mockup design.png out.jpg --preset 白正2.jpg --for-black-shirt

# 适合白色 T 恤
python -m white_t_mockup design.png out.jpg --preset 白正2.jpg --for-white-shirt

# 显式选择预处理方法
python -m white_t_mockup design.png out.jpg --preset 白正2.jpg --shirt-color black --prepare-method value_invert

# 回滚到旧剪影模式
python -m white_t_mockup design.png out.jpg --preset 白正2.jpg --shirt-color black --prepare-method silhouette
```

### 旧版方法（兼容 DX0533）

```bash
python -m white_t_mockup examples/dx0533/input/DX0533_BW_cut.png examples/dx0533/output/DX0533_BW_白T.jpg

# 或使用 scripts 下的兼容入口
python scripts/apply_mockup.py examples/dx0533/input/DX0533_BW_cut.png output.jpg
```

## 命令行参数

### 预设参数

| 参数 | 说明 |
|------|------|
| `--preset` | 使用已配置模板预设（自动加载参数） |
| `--list-presets` | 列出所有已配置模板 |

### 新版方法参数

| 参数 | 说明 |
|------|------|
| `--final-w` / `--final-h` | 贴图最终宽/高像素（PS 缩放后尺寸）。提供后启用新版方法 |
| `--rotate` | 旋转角度（正=顺时针/负=逆时针，同 PS） |
| `--effective-top-y` | 有效像素最高点 Y 坐标 |
| `--effective-center-x` | 有效像素水平中心 X 坐标 |

### 旧版方法参数（兼容）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top-y` | 449 | 贴图最高点 Y 坐标 |
| `--center-x` | 735 | 贴图水平中心 X 坐标 |
| `--final-w` / `--final-h` |  | 贴图最终宽/高像素（旧版缩放也用 final） |

### 公共参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--template` | `D:\Semems\1胚衣\白\W3.psd` | 模板路径（PSD 或 PNG） |
| `--blend-mode` | `multiply` | 贴图混合模式 |
| `--quality` | 95 | JPG 输出质量 |

## Python API

```python
from white_t_mockup import apply_mockup_transform

apply_mockup_transform(
    design_path="design.png",
    output_path="output.jpg",
    template_path=r"D:\Semems\1胚衣\白正2.jpg",
    final_w=546,
    final_h=546,
    rotation_degrees=-2.0,
    effective_top_y=644,
    effective_center_x=670,
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
│   ├── test_transform.py  # 新版 transform 方法单元测试
│   ├── test_prepare.py    # 反黑/反白预处理单元测试
│   └── test_presets.py    # 预设与命令行单元测试
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

## 模板预设

每张胚衣的参数（最终像素/旋转/定位/混合）统一记录在 [`docs/胚衣参数表_模板.csv`](docs/胚衣参数表_模板.csv)，贴图前自动同步到 `white_t_mockup/presets.json`。新增或修改胚衣时，用 Excel 编辑该 CSV 后告诉我即可，不再维护镜像文档。

## 版本

当前版本：`1.3.0`

## 文档索引

- [胚衣参数表模板（Excel/CSV）](docs/胚衣参数表_模板.csv)
- [架构说明](docs/ARCHITECTURE.md)
- [问题与解决方案](docs/TROUBLESHOOTING.md)
- [更新日志](CHANGELOG.md)
