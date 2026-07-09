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
from .core import apply_mockup, apply_mockup_transform


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 PNG 贴图自动合成到白 T 恤样机模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""示例:
  # 新版方法：缩放 + 旋转 + 有效像素定位
  python -m white_t_mockup design.png output.jpg \\
      --template "D:\\Semems\\1胚衣\\白\\W4.png" \\
      --scale 0.40 --rotate 1 \\
      --effective-top-y 490 --effective-center-x 780

  # 旧版方法：固定高度 + 顶部/中心定位（兼容 DX0533）
  python -m white_t_mockup design.png output.jpg
""",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("design", help="输入贴图（透明底 PNG）")
    parser.add_argument("output", help="输出 JPG 路径")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"模板路径（PSD 或 PNG，默认: {DEFAULT_TEMPLATE}）",
    )

    # ---- 新版方法参数 ----
    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help="贴图缩放比例（如 0.40 = 40%%）。提供后启用新版方法",
    )
    parser.add_argument(
        "--rotate",
        type=float,
        default=0.0,
        help="顺时针旋转角度（默认: 0）",
    )
    parser.add_argument(
        "--effective-top-y",
        type=int,
        default=None,
        help="有效像素最高点 Y 坐标",
    )
    parser.add_argument(
        "--effective-center-x",
        type=int,
        default=None,
        help="有效像素水平中心 X 坐标",
    )

    # ---- 旧版方法参数（兼容） ----
    parser.add_argument(
        "--top-y",
        type=int,
        default=DEFAULT_TOP_Y,
        help=f"[旧版] 贴图最高点 Y 坐标（默认: {DEFAULT_TOP_Y}）",
    )
    parser.add_argument(
        "--center-x",
        type=int,
        default=DEFAULT_CENTER_X,
        help=f"[旧版] 贴图水平中心 X 坐标（默认: {DEFAULT_CENTER_X}）",
    )
    parser.add_argument(
        "--target-height",
        type=int,
        default=DEFAULT_TARGET_HEIGHT,
        help=f"[旧版] 贴图目标高度（默认: {DEFAULT_TARGET_HEIGHT}）",
    )

    # ---- 公共参数 ----
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
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    blend_mode = None if args.blend_mode == "normal" else args.blend_mode

    if args.scale is not None:
        # 新版方法
        if args.effective_top_y is None or args.effective_center_x is None:
            parser.error("使用 --scale 时必须同时提供 --effective-top-y 和 --effective-center-x")
        result = apply_mockup_transform(
            design_path=args.design,
            output_path=args.output,
            template_path=args.template,
            scale=args.scale,
            rotation_degrees=args.rotate,
            effective_top_y=args.effective_top_y,
            effective_center_x=args.effective_center_x,
            blend_mode=blend_mode,
            quality=args.quality,
        )
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}"
        )
        print(
            f"贴图参数: 缩放={result['scale']}, 旋转={result['rotation_degrees']}°, "
            f"有效像素最高点 y={result['effective_top']}, 中心 x={result['effective_center_x']}, "
            f"左上角=({result['design_left']}, {result['design_top']})"
        )
    else:
        # 旧版方法（兼容）
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
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}"
        )
        print(
            f"贴图参数: 大小={result['design_size']}, "
            f"左上角=({result['design_left']}, {result['design_top']}), "
            f"中心={result['design_center']}"
        )


if __name__ == "__main__":
    main()
