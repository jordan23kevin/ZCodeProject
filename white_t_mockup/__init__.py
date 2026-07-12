# -*- coding: utf-8 -*-
"""白 T 恤样机贴图自动化工具包。"""

__version__ = "1.8.0"

from .core import (
    add_white_underbase,
    apply_mockup,
    apply_mockup_transform,
    apply_transform,
    black_shirt_print_optimize,
    enhance_dark_print_for_black_shirt,
    find_effective_bbox,
    load_any_template,
    load_png_template,
    load_template,
    paste_with_blend,
    prepare_design_for_shirt,
    resize_design,
)

__all__ = [
    "add_white_underbase",
    "apply_mockup",
    "apply_mockup_transform",
    "apply_transform",
    "black_shirt_print_optimize",
    "enhance_dark_print_for_black_shirt",
    "find_effective_bbox",
    "load_any_template",
    "load_png_template",
    "load_template",
    "paste_with_blend",
    "prepare_design_for_shirt",
    "resize_design",
]
