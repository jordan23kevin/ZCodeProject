# -*- coding: utf-8 -*-
"""白 T 恤样机贴图命令行入口。"""

from __future__ import annotations

import argparse

from . import __version__
from .config import (
    DEFAULT_BLEND_MODE,
    DEFAULT_CENTER_X,
    DEFAULT_QUALITY,
    DEFAULT_TARGET_HEIGHT,
    DEFAULT_TEMPLATE,
    DEFAULT_TOP_Y,
)
from .core import apply_mockup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 PNG 贴图自动合成到白 T 恤样机模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""示例:
  python -m white_t_mockup design.png output.jpg
  python -m white_t_mockup design.png output.jpg --blend-mode normal
""",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("design", help="输入贴图（透明底 PNG）")
    parser.add_argument("output", help="输出 JPG 路径")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"PSD 模板路径（默认: {DEFAULT_TEMPLATE}）",
    )
    parser.add_argument(
        "--top-y",
        type=int,
        default=DEFAULT_TOP_Y,
        help=f"贴图最高点 Y 坐标（默认: {DEFAULT_TOP_Y}）",
    )
    parser.add_argument(
        "--center-x",
        type=int,
        default=DEFAULT_CENTER_X,
        help=f"贴图水平中心 X 坐标（默认: {DEFAULT_CENTER_X}）",
    )
    parser.add_argument(
        "--target-height",
        type=int,
        default=DEFAULT_TARGET_HEIGHT,
        help=f"贴图目标高度（默认: {DEFAULT_TARGET_HEIGHT}）",
    )
    parser.add_argument(
        "--blend-mode",
        choices=["normal", "multiply", "screen", "overlay", "linear_burn"],
        default=DEFAULT_BLEND_MODE,
        help=f"贴图混合模式（默认: {DEFAULT_BLEND_MODE}）",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"JPG 质量（默认: {DEFAULT_QUALITY}）",
    )

    args = parser.parse_args()
    blend_mode = None if args.blend_mode == "normal" else args.blend_mode

    result = apply_mockup(
        design_path=args.design,
        output_path=args.output,
        template_path=args.template,
        top_y=args.top_y,
        center_x=args.center_x,
        target_height=args.target_height,
        blend_mode=blend_mode,
        quality=args.quality,
    )

    print(f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}")
    print(
        f"贴图参数: 大小={result['design_size']}, "
        f"左上角=({result['design_left']}, {result['design_top']}), "
        f"中心={result['design_center']}"
    )


if __name__ == "__main__":
    main()
