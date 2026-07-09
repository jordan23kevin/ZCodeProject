# -*- coding: utf-8 -*-
"""白 T 恤样机贴图命令行入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .config import (
    DEFAULT_BLEND_MODE,
    DEFAULT_CENTER_X,
    DEFAULT_QUALITY,
    DEFAULT_TARGET_HEIGHT,
    DEFAULT_TEMPLATE,
    DEFAULT_TOP_Y,
    get_preset,
    list_presets,
)
from .core import apply_mockup, apply_mockup_transform


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 PNG 贴图自动合成到白 T 恤样机模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""示例:
  # 使用模板预设（自动加载该模板的参数）
  python -m white_t_mockup design.png output.jpg --preset 1B.png

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
    parser.add_argument("design", nargs="?", help="输入贴图（透明底 PNG）")
    parser.add_argument("output", nargs="?", help="输出 JPG 路径")
    parser.add_argument(
        "--template",
        default=None,
        help="模板路径（PSD 或 PNG）",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="使用已配置的模板预设（如 W4.png / 1B.png / 3.psd）",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="列出所有已配置的模板预设",
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
        default=None,
        help="顺时针旋转角度",
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
        default=None,
        help=f"[旧版] 贴图最高点 Y 坐标（默认: {DEFAULT_TOP_Y}）",
    )
    parser.add_argument(
        "--center-x",
        type=int,
        default=None,
        help=f"[旧版] 贴图水平中心 X 坐标（默认: {DEFAULT_CENTER_X}）",
    )
    parser.add_argument(
        "--target-height",
        type=int,
        default=None,
        help=f"[旧版] 贴图目标高度（默认: {DEFAULT_TARGET_HEIGHT}）",
    )

    # ---- 公共参数 ----
    parser.add_argument(
        "--blend-mode",
        choices=["normal", "multiply", "screen", "overlay", "linear_burn"],
        default=None,
        help=f"贴图混合模式（默认: {DEFAULT_BLEND_MODE}）",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=None,
        help=f"JPG 质量（默认: {DEFAULT_QUALITY}）",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_presets:
        print("已配置的模板预设：")
        for name in list_presets():
            print(f"  - {name}")
        return

    if not args.design or not args.output:
        parser.error("需要提供 design 和 output 参数")

    # 解析模板路径与参数（优先级：命令行 > 预设 > 默认）
    template_path = args.template
    params: dict = {}

    if args.preset:
        preset = get_preset(args.preset)
        if preset is None:
            parser.error(f"找不到预设: {args.preset}，可用预设: {list_presets()}")
        template_path = preset["path"]
        params = preset
    elif template_path:
        preset = get_preset(template_path)
        if preset is not None:
            params = preset

    if template_path is None:
        template_path = params.get("path", DEFAULT_TEMPLATE)

    method = params.get("method", "transform" if args.scale is not None else "legacy")

    blend_mode = args.blend_mode or params.get("blend_mode", DEFAULT_BLEND_MODE)
    quality = args.quality if args.quality is not None else DEFAULT_QUALITY
    blend_mode = None if blend_mode == "normal" else blend_mode

    if method == "transform":
        scale = args.scale if args.scale is not None else params.get("scale")
        rotate = args.rotate if args.rotate is not None else params.get("rotation_degrees", 0.0)
        top = args.effective_top_y if args.effective_top_y is not None else params.get("effective_top_y")
        center = args.effective_center_x if args.effective_center_x is not None else params.get("effective_center_x")

        missing = [k for k, v in {
            "--scale": scale,
            "--effective-top-y": top,
            "--effective-center-x": center,
        }.items() if v is None]
        if missing:
            parser.error(f"新版方法缺少参数: {missing}")

        result = apply_mockup_transform(
            design_path=args.design,
            output_path=args.output,
            template_path=template_path,
            scale=scale,
            rotation_degrees=rotate,
            effective_top_y=top,
            effective_center_x=center,
            blend_mode=blend_mode,
            quality=quality,
        )
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}"
        )
        print(
            f"模板: {Path(template_path).name}  缩放={result['scale']}, 旋转={result['rotation_degrees']}°, "
            f"有效像素最高点 y={result['effective_top']}, 中心 x={result['effective_center_x']}"
        )
    else:
        top = args.top_y if args.top_y is not None else params.get("top_y", DEFAULT_TOP_Y)
        center = args.center_x if args.center_x is not None else params.get("center_x", DEFAULT_CENTER_X)
        height = args.target_height if args.target_height is not None else params.get("target_height", DEFAULT_TARGET_HEIGHT)

        result = apply_mockup(
            design_path=args.design,
            output_path=args.output,
            template_path=template_path,
            top_y=top,
            center_x=center,
            target_height=height,
            blend_mode=blend_mode,
            quality=quality,
        )
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}"
        )
        print(
            f"模板: {Path(template_path).name}  大小={result['design_size']}, "
            f"左上角=({result['design_left']}, {result['design_top']}), "
            f"中心={result['design_center']}"
        )


if __name__ == "__main__":
    main()
