# Changelog

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
