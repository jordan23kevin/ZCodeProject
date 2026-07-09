# -*- coding: utf-8 -*-
"""白 T 恤样机贴图的默认配置参数。

所有参数从 DX0533 成品反推并固定为白 T 标准。
每张胚衣模板的独立参数记录在 presets.json 中。
"""

import json
from pathlib import Path

# 默认模板路径
DEFAULT_TEMPLATE = r"D:\Semems\1胚衣\白\3.psd"

# 贴图定位参数
DEFAULT_TOP_Y = 449          # 贴图最高像素点的 Y 坐标
DEFAULT_CENTER_X = 735       # 贴图水平中心点的 X 坐标
DEFAULT_TARGET_HEIGHT = 677  # 贴图缩放后的目标高度（像素）

# 默认混合模式：正片叠底
DEFAULT_BLEND_MODE = "multiply"

# 输出质量
DEFAULT_QUALITY = 95

# 支持的混合模式
SUPPORTED_BLEND_MODES = ("normal", "multiply", "screen", "overlay", "linear_burn")

# 每张模板的预设参数文件
PRESETS_PATH = Path(__file__).parent / "presets.json"


def load_presets() -> dict:
    """加载所有模板的预设参数。"""
    if not PRESETS_PATH.exists():
        return {"templates": {}}
    with PRESETS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_preset(template_name: str) -> dict | None:
    """
    根据模板文件名获取预设参数。

    template_name: 模板文件名（如 "W4.png"）或完整路径
    """
    name = Path(template_name).name
    presets = load_presets()
    return presets.get("templates", {}).get(name)


def list_presets() -> list[str]:
    """返回所有已配置模板的名称。"""
    presets = load_presets()
    return list(presets.get("templates", {}).keys())
