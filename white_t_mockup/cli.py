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
        help="使用已配置的模板预设（如 白正2.jpg / 白B1.png / 黑W5.png）",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="列出所有已配置的模板预设",
    )

    # ---- 新版方法参数 ----
    parser.add_argument(
        "--final-w",
        type=int,
        default=None,
        help="贴图最终宽度像素（PS 缩放后宽；提供后启用新版方法）",
    )
    parser.add_argument(
        "--final-h",
        type=int,
        default=None,
        help="贴图最终高度像素（PS 缩放后高）",
    )
    parser.add_argument(
        "--rotate",
        type=float,
        default=None,
        help="旋转角度（正=顺时针/负=逆时针，同 PS）",
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
    # ---- 公共参数 ----
    parser.add_argument(
        "--blend-mode",
        choices=["normal", "multiply", "screen", "overlay", "linear_burn"],
        default=None,
        help=f"贴图混合模式（默认: {DEFAULT_BLEND_MODE}）",
    )
    parser.add_argument(
        "--prepare-method",
        choices=["value_invert", "silhouette", "none", "dark_boost", "white_underbase", "matting", "unpremultiply"],
        default="white_underbase",
        help="预处理方法（默认: white_underbase 黑衫白墨打底显色；dark_boost 仅提亮；"
             "matting 按目标布料色填充透明区（旧版）; "
             "unpremultiply 去预乘去光晕（保色模式默认）;"
             "value_invert/silhouette 为旧反相逻辑）",
    )
    shirt_group = parser.add_mutually_exclusive_group()
    shirt_group.add_argument(
        "--shirt-color",
        choices=["black", "white"],
        default=None,
        help="目标 T 恤颜色，启用预处理（黑衫优化/反白）",
    )
    shirt_group.add_argument(
        "--for-black-shirt",
        action="store_true",
        help="快捷开关：等价于 --shirt-color black --prepare-method white_underbase（黑衫白墨打底显色）",
    )
    shirt_group.add_argument(
        "--for-white-shirt",
        action="store_true",
        help="快捷开关：等价于 --shirt-color white --prepare-method value_invert",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=None,
        help=f"JPG 质量（默认: {DEFAULT_QUALITY}）",
    )
    # ---- 真实感（自然度）参数 ----
    parser.add_argument(
        "--no-realism",
        action="store_true",
        help="关闭真实感处理（降饱和/亮度/模糊 + 布纹透出），用于对比原效果",
    )
    parser.add_argument(
        "--preserve-color",
        action="store_true",
        help="原样保色贴图：色相/饱和度零偏差，仅由【布料同步明度】按同位置布料"
             "明暗调制印花明度(V)，实现『印花与布料同光同暗』；关闭反色/显色、"
             "旧阴影正片叠底/高光叠加(会偏色)、降饱和。褶皱立体感由 displacement"
             "位移扭曲 + 布料同步明度共同体现，与衣服无色差。",
    )
    parser.add_argument(
        "--blur",
        type=float,
        default=0.4,
        help="印花边缘高斯模糊半径 px（默认 0.4，预乘alpha感知，0 关闭）",
    )
    parser.add_argument(
        "--texture-opacity",
        type=float,
        default=0.25,
        help="布纹透出叠加透明度（默认 0.25，0 关闭）",
    )
    # ---- 模板管线（自然褶皱：displacement + shadow/highlight 转移）----
    parser.add_argument(
        "--tpl-dir",
        default=None,
        help="模板衍生素材目录（含 mask/disp/shadow/highlight.png）；不传则自动探测 胚衣根/_tpl/<款名>/",
    )
    parser.add_argument(
        "--disp-strength",
        type=float,
        default=12.0,
        help="置换最大像素偏移（默认 12.0）",
    )
    parser.add_argument(
        "--disp-smooth",
        type=float,
        default=80.0,
        help="位移图高斯平滑 sigma（默认 80）：只保留大褶皱形变，消除小褶皱水波纹；0=不平滑",
    )
    parser.add_argument(
        "--disp-dead-zone",
        type=float,
        default=15.0,
        help="位移死区（灰度级，默认 15）：|disp-128| 小于此值的区域不扭曲",
    )
    parser.add_argument(
        "--disp-mode",
        choices=["isotropic", "gradient"],
        default="isotropic",
        help="位移模式：isotropic=旧各向同性鼓包(平移)；gradient=沿褶皱切线 2D 梯度位移(贴合褶皱形态)",
    )
    parser.add_argument(
        "--shadow-opacity",
        type=float,
        default=0.22,
        help="阴影转移(Multiply)透明度（默认 0.22，已归一化为相对褶皱阴影，不再整体压暗印花）",
    )
    parser.add_argument(
        "--highlight-opacity",
        type=float,
        default=0.22,
        help="高光转移(Overlay)透明度（默认 0.22）",
    )
    parser.add_argument(
        "--occlusion-strength",
        type=float,
        default=1.0,
        help="褶皱折入隐藏强度（读 _tpl/occlusion.png，1.0=完全按遮挡隐藏，0=关闭）",
    )
    parser.add_argument(
        "--occlusion-min-vis",
        type=float,
        default=0.0,
        help="褶皱折入区域最低可见度（0=可完全隐藏；黑衫建议 0.25，防止露出黑底形成黑斑）",
    )
    # ---- 布料同步明度（印花与布料同光同暗，H/S 零偏差）----
    parser.add_argument(
        "--no-fabric-shading",
        action="store_true",
        help="关闭布料同步明度（默认开启）：开启时仅缩放印花明度(V)使其严格跟随"
             "同位置布料明暗，色相/饱和度零偏差，深褶处自然隐没；关闭则退回旧阴影转移。",
    )
    parser.add_argument(
        "--shading-blur",
        type=float,
        default=4.0,
        help="布料明暗场高斯平滑 sigma（默认 4）：仅用于抗锯齿，值越小暗缝越不向外扩散；"
             "深缝判定由局部对比完成，与本品无关。",
    )
    # ---- 顶层遮挡物（胚衣遮罩 *_occluder.png）：贴图被前景遮挡物盖住，更真实 ----
    parser.add_argument(
        "--occluder",
        default=None,
        help="顶层遮挡物 PNG（如 *_occluder.png）：贴图会被遮挡物盖住，模拟真实前后景关系",
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

    # 模板衍生素材目录：命令行 > 预设 > 自动探测 胚衣根/_tpl/<款名>/
    tpl_dir = args.tpl_dir or params.get("tpl_dir")
    if tpl_dir is None and template_path:
        _cand = Path(template_path).parent.parent / "_tpl" / Path(template_path).stem
        if (_cand / "mask.png").exists():
            tpl_dir = str(_cand)

    method = params.get("method", "transform" if args.final_w is not None else "legacy")

    quality = args.quality if args.quality is not None else DEFAULT_QUALITY

    shirt_color = args.shirt_color
    prepare_method = args.prepare_method

    if args.for_black_shirt:
        shirt_color = "black"
        prepare_method = "white_underbase"
    elif args.for_white_shirt:
        shirt_color = "white"
        prepare_method = "value_invert"

    # 真实感颜色参数（默认与 core 一致：微降饱和 0.97、亮度 1.0）
    saturation = 0.97
    brightness = 1.0
    shadow_opacity = args.shadow_opacity
    highlight_opacity = args.highlight_opacity

    # ---- 原样保色模式：几何贴合 + 布料 matting，颜色/亮度完全不变 ----
    if args.preserve_color:
        prepare_method = "unpremultiply"  # 去预乘去光晕，消除黑底/白底 PNG 边缘偏色
        saturation = 1.0             # 不降饱和
        brightness = 1.0             # 不改亮度
        shadow_opacity = 0.0         # 关阴影正片叠底（不压暗）
        highlight_opacity = 0.0      # 关高光叠加（不提亮）
        # 若未显式指定 shirt_color，从模板路径推断（白/黑），便于生产流水线自动适配
        if shirt_color is None and template_path:
            p = str(template_path).lower()
            if "white" in p or "白" in p:
                shirt_color = "white"
            elif "black" in p or "黑" in p:
                shirt_color = "black"

    # 混合模式：显式 --blend-mode > 保色(normal) > 按衫色默认（黑T screen / 白T multiply）> preset 默认
    if args.blend_mode:
        blend_mode = args.blend_mode
    elif args.preserve_color:
        blend_mode = "normal"        # 普通叠加，原色贴上，无色差
    elif shirt_color == "black":
        blend_mode = "normal"
    elif shirt_color == "white":
        blend_mode = "multiply"
    else:
        blend_mode = params.get("blend_mode", DEFAULT_BLEND_MODE)
    blend_mode = None if blend_mode == "normal" else blend_mode

    if method == "transform":
        final_w = args.final_w if args.final_w is not None else params.get("final_w")
        final_h = args.final_h if args.final_h is not None else params.get("final_h")
        rotate = args.rotate if args.rotate is not None else params.get("rotation_degrees", 0.0)
        top = args.effective_top_y if args.effective_top_y is not None else params.get("effective_top_y")
        center = args.effective_center_x if args.effective_center_x is not None else params.get("effective_center_x")

        missing = [k for k, v in {
            "--final-w": final_w,
            "--final-h": final_h,
            "--effective-top-y": top,
            "--effective-center-x": center,
        }.items() if v is None]
        if missing:
            parser.error(f"新版方法缺少参数（请在 CSV 补齐「缩放后宽px/缩放后高px」）: {missing}")

        result = apply_mockup_transform(
            design_path=args.design,
            output_path=args.output,
            template_path=template_path,
            final_w=final_w,
            final_h=final_h,
            rotation_degrees=rotate,
            effective_top_y=top,
            effective_center_x=center,
            blend_mode=blend_mode,
            quality=quality,
            shirt_color=shirt_color,
            prepare_method=prepare_method,
            realism=not args.no_realism and not args.preserve_color,
            blur_radius=args.blur,
            texture_opacity=args.texture_opacity,
            tpl_dir=tpl_dir,
            disp_strength=args.disp_strength,
            disp_smooth=args.disp_smooth,
            disp_dead_zone=args.disp_dead_zone,
            disp_mode=args.disp_mode,
            saturation=saturation,
            brightness=brightness,
            shadow_opacity=shadow_opacity,
            highlight_opacity=highlight_opacity,
            occluder=args.occluder,
            occlusion_strength=args.occlusion_strength,
            occlusion_min_visibility=args.occlusion_min_vis,
            fabric_shading=not args.no_fabric_shading,
            shading_blur=args.shading_blur,
        )
        mode_tag = " [保色]" if args.preserve_color else ""
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}{mode_tag}"
        )
        print(
            f"模板: {Path(template_path).name}  最终像素={result['final_w']}x{result['final_h']}, 旋转={result['rotation_degrees']}°, "
            f"有效像素最高点 y={result['effective_top']}, 中心 x={result['effective_center_x']}"
        )
        if result.get("template_pipeline"):
            _occ = " + occlusion(褶皱隐藏)" if result.get("occlusion_applied") else ""
            print(f"模板管线: displacement + shadow/highlight{_occ}  (tpl_dir={tpl_dir})")
    else:
        top = args.top_y if args.top_y is not None else params.get("top_y", DEFAULT_TOP_Y)
        center = args.center_x if args.center_x is not None else params.get("center_x", DEFAULT_CENTER_X)
        final_w = args.final_w if args.final_w is not None else params.get("final_w")
        final_h = args.final_h if args.final_h is not None else params.get("final_h")
        if final_w is None or final_h is None:
            parser.error("旧版方法缺少 final_w/final_h（请在 CSV 补齐「缩放后宽px/缩放后高px」）")

        result = apply_mockup(
            design_path=args.design,
            output_path=args.output,
            template_path=template_path,
            top_y=top,
            center_x=center,
            final_w=final_w,
            final_h=final_h,
            blend_mode=blend_mode,
            quality=quality,
            shirt_color=shirt_color,
            prepare_method=prepare_method,
            tpl_dir=tpl_dir,
            disp_strength=args.disp_strength,
            disp_smooth=args.disp_smooth,
            disp_dead_zone=args.disp_dead_zone,
            shadow_opacity=shadow_opacity,
            highlight_opacity=highlight_opacity,
            occluder=args.occluder,
            occlusion_strength=args.occlusion_strength,
            occlusion_min_visibility=args.occlusion_min_vis,
            fabric_shading=not args.no_fabric_shading,
            shading_blur=args.shading_blur,
        )
        mode_tag = " [保色]" if args.preserve_color else ""
        print(
            f"已保存: {args.output}  尺寸: {result['output_size']}  混合模式: {result['blend_mode']}{mode_tag}"
        )
        print(
            f"模板: {Path(template_path).name}  大小={result['design_size']}, "
            f"左上角=({result['design_left']}, {result['design_top']}), "
            f"中心={result['design_center']}"
        )
        if result.get("template_pipeline"):
            _occ = " + occlusion(褶皱隐藏)" if result.get("occlusion_applied") else ""
            print(f"模板管线: displacement + shadow/highlight{_occ}  (tpl_dir={tpl_dir})")


if __name__ == "__main__":
    main()
