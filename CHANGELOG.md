# Changelog

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
