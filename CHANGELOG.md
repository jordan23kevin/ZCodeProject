# Changelog

## [Unreleased]

### Added
- `prepare_design_for_shirt()`：支持 `value_invert`（亮度反相，保留色相/饱和度）、`silhouette`（黑白剪影）、`none`（无处理）。
- `apply_mockup()` 与 `apply_mockup_transform()` 新增 `shirt_color` 和 `prepare_method` 参数。
- CLI 新增 `--shirt-color`、`--prepare-method`、`--for-black-shirt`、`--for-white-shirt`。

## [1.2.1] - 2026-07-09

### Added
- 新增 `3B.png` 胚衣模板预设：缩放 32%、逆时针旋转 3°、有效像素最高点 y=700、中心 x=777、Multiply 混合

### Changed
- 版本号升级为 1.2.1

## [1.2.0] - 2026-07-09

### Added
- 模板预设系统：`white_t_mockup/presets.json` 单独记录每张胚衣的参数
- CLI 新增 `--preset` 和 `--list-presets` 参数
- 新增 `3.psd`、`W4.png`、`1B.png` 三张模板的预设
- `config.py` 新增 `load_presets()`、`get_preset()`、`list_presets()`

### Changed
- 版本号升级为 1.2.0

## [1.1.0] - 2026-07-09

### Added
- 新版 transform 方法：缩放比例 + 顺时针旋转 + 按有效像素最高点/中心点定位
- 支持 PNG 单图层模板（无手部遮罩）
- `apply_mockup_transform()`、`apply_transform()`、`find_effective_bbox()`、`calculate_effective_position()`、`load_png_template()`、`load_any_template()` 等新函数
- CLI 自动判断新版/旧版方法（提供 `--scale` 即启用新版）
- 新增 `tests/test_transform.py`，覆盖缩放、旋转、有效像素定位、PNG 模板加载

### Changed
- 版本号升级为 1.1.0
- 文档全面更新（README、ARCHITECTURE、TROUBLESHOOTING、Skill）

## [1.0.0] - 2026-07-09

### Added
- 初始版本：白 T 恤样机贴图自动化工具
- 支持命令行与 Python API 两种调用方式
- 自动识别 PSD 模板中的背景层与手部前景遮罩
- 支持 normal、multiply、screen、overlay、linear_burn 混合模式
- 默认参数固化：top-y=449, center-x=735, target-height=677, blend-mode=multiply
- 附带 DX0533 完整示例（输入 PNG + 输出 JPG）
- 项目内 Kimi Code Skill：`.kimi/skills/white-t-mockup/SKILL.md`
- 单元测试覆盖核心函数
- 文档：README、ARCHITECTURE、TROUBLESHOOTING
