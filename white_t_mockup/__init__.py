# -*- coding: utf-8 -*-
"""白 T 恤样机贴图自动化工具包。"""

__version__ = "1.4.1"

from .core import (
    apply_mockup,
    apply_mockup_transform,
    apply_transform,
    find_effective_bbox,
    load_any_template,
    load_png_template,
    load_template,
    paste_with_blend,
    prepare_design_for_shirt,
    resize_design,
)

__all__ = [
    "apply_mockup",
    "apply_mockup_transform",
    "apply_transform",
    "find_effective_bbox",
    "load_any_template",
    "load_png_template",
    "load_template",
    "paste_with_blend",
    "prepare_design_for_shirt",
    "resize_design",
]
