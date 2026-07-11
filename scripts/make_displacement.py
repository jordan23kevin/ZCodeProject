# -*- coding: utf-8 -*-
"""从胚衣 PSD/PNG 背景层生成 displacement 灰度图（去色→提对比→高斯平滑）。

用法：
  python scripts/make_displacement.py <胚衣路径> [输出路径] [对比度] [模糊半径]
默认输出 D:/Semems/1胚衣/_disp/<胚衣名>_disp.png；对比度默认 1.8，模糊半径默认 4.0。
"""
import sys
from pathlib import Path

from PIL import ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from white_t_mockup.core import load_any_template


def make_disp(template_path, out_path, contrast=1.8, blur=4.0):
    bg, fg, fg_pos, canvas_size = load_any_template(template_path)
    gray = bg.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    gray = gray.filter(ImageFilter.GaussianBlur(blur))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    gray.save(out_path)
    print(f"saved {out_path} size={gray.size}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/make_displacement.py <胚衣路径> [输出] [对比度] [模糊半径]")
        sys.exit(1)
    tpl = sys.argv[1]
    name = Path(tpl).stem
    out = sys.argv[2] if len(sys.argv) > 2 else f"D:/Semems/1胚衣/_disp/{name}_disp.png"
    contrast = float(sys.argv[3]) if len(sys.argv) > 3 else 1.8
    blur = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
    make_disp(tpl, out, contrast, blur)
