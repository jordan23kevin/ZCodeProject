# -*- coding: utf-8 -*-
"""白 T 恤样机贴图的默认配置参数。

所有参数从 DX0533 成品反推并固定为白 T 标准。
"""

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
