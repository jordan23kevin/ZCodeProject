# -*- coding: utf-8 -*-
"""贴图成品命名规则 —— 全系统唯一出处（single source of truth）。

★★★ 要改命名规则，只改这一个文件 ★★★
所有产图脚本（04_OS engine、E:\\Claude code\\ps）和读图脚本（元数据注册、
前端分组、清理逻辑）都从这里取规则。改完重启 bridge（kill 端口 8766）即可全局生效。

占位符说明：
  {dx}    款号，如 DX0650 / HX0001
  {side}  面：W=正面 / B=背面
  {color} 颜色：白 / 黑 / 蜜瓜橙 / 浅黄色 / 蓝绿色 / 灰蓝色 / 孔雀蓝 / 明黄色 / 草绿色 / 肉粉色

当前规则（用户定稿 2026-07-12，示例 DX0650）：
  平铺图（T恤平铺在场景里）：DX0650_W白T.jpg / DX0650_B黑T.jpg
  模特图（人穿着）        ：DX0650_白W.jpg  / DX0650_黑B.jpg
  BW 合成图（正背拼图）    ：DX0650_白BW.jpg / DX0650_黑BW.jpg
  卫衣英文色（2026-08-19 起，中文色名）：HX0001_W蜜瓜橙T.jpg / HX0001_蜜瓜橙W.jpg

平铺胚衣名单按品类区分（2026-08-19，品类由 SEMEMS_ROOT 推断）：
  T恤（wb，默认）  ：白W11 / 黑W11 / 白B12 / 黑B7
  卫衣（hoodie）    ：素材库每个颜色文件夹的「2 号图」即平铺胚衣
                     （白W2 / 黑W2 / 白B2 / 黑B2、英文色 W2 / B2；W=正面、B=背面；
                       1 号图=模特胚衣）。判定规则：stem 以 "2" 结尾。
"""

import os
import re

# ── ① 命名格式（改这里 = 改全局）────────────────────────────────
FLAT_FMT = "{dx}_{side}{color}T.jpg"   # 平铺图：DX0650_W白T.jpg
MODEL_FMT = "{dx}_{color}{side}.jpg"   # 模特图：DX0650_白W.jpg
BW_FMT = "{dx}_{color}BW.jpg"          # BW合成：DX0650_白BW.jpg

# 旧命名（仅用于解析/清理历史文件，产图不再使用，不要改）
LEGACY_FLAT_FMT = "{dx}_{side}_{color}T.jpg"  # DX0001_B_白T.jpg

# ── ② 平铺胚衣清单（决定一张胚衣出平铺图还是模特图）────────────
# 按品类区分（品类由 SEMEMS_ROOT 推断，check_rem 启动时注入；缺省 T恤 wb）。
# T恤（wb，用户指定 2026-07-12）：其余胚衣一律视为模特图
FLAT_STEMS = {"白W11", "黑W11", "白B12", "黑B7"}
# 卫衣（hoodie，用户确认 2026-08-19）：素材库每个颜色文件夹的「2 号图」即平铺胚衣
# （白W2/黑W2/白B2/黑B2、英文色 W2/B2；W=正面、B=背面；1 号图=模特胚衣）。
# 判定用通用规则（stem 以 "2" 结尾），覆盖全部 20 个分类、新增颜色无需改名单；
# 下表仅用于 flat_mandatory 的 (面,颜色) 固定平铺映射（当前贴图候选池只有黑白四色）。
_FLAT_STEMS_HOODIE = {"白W2", "黑W2", "白B2", "黑B2"}

# 各 (面, 颜色) 固定使用的平铺胚衣（素材库 stem 名）
FLAT_MANDATORY = {
    ("W", "白"): "白W11",
    ("W", "黑"): "黑W11",
    ("B", "白"): "白B12",
    ("B", "黑"): "黑B7",
}
_FLAT_MANDATORY_HOODIE = {
    ("W", "白"): "白W2",
    ("W", "黑"): "黑W2",
    ("B", "白"): "白B2",
    ("B", "黑"): "黑B2",
}

_SIDES = "WB"
# 颜色名体系：白/黑 单字 + 卫衣 8 英文色的中文名（用户 2026-08-19 提供）：
#   Melon Orange=蜜瓜橙、Straw Yellow=浅黄色、Blue Green=蓝绿色、Grey Blue=灰蓝色、
#   Peacock Blue=孔雀蓝、Light Yellow=明黄色、Grass Green=草绿色、flesh pink=肉粉色。
# 成品文件名 {color} 用这些中文名（如 HX0001_W蜜瓜橙T.jpg / HX0001_蜜瓜橙W.jpg）。
COLOR_NAMES = ("白", "黑", "蜜瓜橙", "浅黄色", "蓝绿色", "灰蓝色",
               "孔雀蓝", "明黄色", "草绿色", "肉粉色")
# color 正则（按长度降序，先长后短）
_COLORS_PAT = "(?:" + "|".join(re.escape(c) for c in sorted(COLOR_NAMES, key=len, reverse=True)) + ")"


def _current_cat() -> str:
    """按 SEMEMS_ROOT 推断当前品类（T恤 wb / 卫衣 hoodie；缺省 wb）。"""
    root = os.environ.get("SEMEMS_ROOT", "")
    return "hoodie" if "Hoodie" in root else "wb"


def flat_stems(cat: str | None = None) -> set:
    """当前品类的平铺胚衣 stem 集合（决定出平铺图还是模特图）。"""
    return _FLAT_STEMS_HOODIE if (cat or _current_cat()) == "hoodie" else FLAT_STEMS


def flat_mandatory(role: str, color: str, cat: str | None = None) -> str | None:
    """当前品类 (面, 颜色) 固定使用的平铺胚衣 stem；无则返回 None。"""
    table = _FLAT_MANDATORY_HOODIE if (cat or _current_cat()) == "hoodie" else FLAT_MANDATORY
    return table.get((role, color))


# ── 生成文件名 ────────────────────────────────────────────────
def flat_name(dx: str, side: str, color: str) -> str:
    """平铺图文件名，如 flat_name('DX0650','W','白') → DX0650_W白T.jpg"""
    return FLAT_FMT.format(dx=dx, side=side, color=color)


def model_name(dx: str, side: str, color: str) -> str:
    """模特图文件名，如 model_name('DX0650','W','白') → DX0650_白W.jpg"""
    return MODEL_FMT.format(dx=dx, side=side, color=color)


def bw_name(dx: str, color: str) -> str:
    """BW 合成图文件名，如 bw_name('DX0650','白') → DX0650_白BW.jpg"""
    return BW_FMT.format(dx=dx, color=color)


def is_flat_stem(stem: str, cat: str | None = None) -> bool:
    """该胚衣是否平铺图模板（决定出平铺命名还是模特命名）。按品类判断：
    T恤=白名单(FLAT_STEMS)；卫衣=素材库各颜色文件夹的「2 号图」（stem 以 "2" 结尾，
    W 开头=正面、B 开头=背面，如 白W2/黑W2/白B2/黑B2/W2/B2）。"""
    if (cat or _current_cat()) == "hoodie":
        return stem.endswith("2")
    return stem in FLAT_STEMS


def stem_of(name: str) -> str:
    """去掉扩展名（兼容 .jpg/.png 等）。"""
    return name.rsplit(".", 1)[0] if "." in name else name


# ── 解析文件名（解析规则从上面的格式串自动推导，改格式解析自动跟随）──
def _fmt_to_regex(fmt: str, dx: str) -> re.Pattern:
    """把格式串转成匹配 stem（不含 .jpg）的锚定正则，side/color 为命名组。"""
    r = re.escape(fmt)
    r = r.replace(r"\{dx\}", re.escape(dx))
    r = r.replace(r"\{side\}", rf"(?P<side>[{_SIDES}])")
    r = r.replace(r"\{color\}", rf"(?P<color>{_COLORS_PAT})")
    r = r.replace(r"\.jpg", "")
    return re.compile("^" + r + "$")


def classify(dx: str, name: str):
    """识别文件名属于哪类成品。

    返回 dict(kind='flat'|'model'|'bw', side, color, legacy)；识别不了返回 None。
    kind='flat' 且 legacy=True 表示旧平铺命名（DX0001_B_白T）。
    """
    stem = stem_of(name)
    m = _fmt_to_regex(FLAT_FMT, dx).match(stem)
    if m:
        return {"kind": "flat", "side": m.group("side"), "color": m.group("color"), "legacy": False}
    m = _fmt_to_regex(BW_FMT, dx).match(stem)
    if m:
        return {"kind": "bw", "side": None, "color": m.group("color"), "legacy": False}
    m = _fmt_to_regex(MODEL_FMT, dx).match(stem)
    if m:
        return {"kind": "model", "side": m.group("side"), "color": m.group("color"), "legacy": False}
    m = _fmt_to_regex(LEGACY_FLAT_FMT, dx).match(stem)
    if m:
        return {"kind": "flat", "side": m.group("side"), "color": m.group("color"), "legacy": True}
    return None


def role_from_name(name: str) -> str:
    """从文件名推断 role（元数据/分组用）。

    平铺：白→W/B，黑→黑W/黑B；模特：白W/黑B；BW：白BW/黑BW；去背图末段原样返回。
    """
    stem = stem_of(name)
    if stem.endswith("_cut"):
        stem = stem[:-4]
    dx = stem.split("_")[0] if "_" in stem else ""
    info = classify(dx, stem) if dx else None
    if info:
        side, color = info["side"], info["color"]
        if info["kind"] == "flat":
            return f"黑{side}" if color == "黑" else side
        if info["kind"] == "bw":
            return f"{color}BW"
        return f"{color}{side}"
    parts = stem.split("_")
    # 旧版模特命名（DX0650_W11_黑T，已停产，仅解析历史文件）
    if len(parts) >= 3 and parts[-1] in ("白T", "黑T"):
        side = parts[-2]
        return f"黑{side}" if parts[-1] == "黑T" else side
    if len(parts) >= 2:
        return parts[-1]
    return "?"


def group_of(dx: str, name: str) -> str:
    """前端画廊分组：W / B / BW / 其他。"""
    stem = stem_of(name)
    info = classify(dx, stem)
    if info:
        if info["kind"] == "bw":
            return "BW"
        return info["side"]
    # 旧命名兼容（带版本号，如 DX0611_W1_白T）
    role_part = re.sub(r"_(白T|黑T)$", "", stem)
    role_part = role_part[len(dx) + 1:] if role_part.startswith(dx + "_") else role_part
    role_part = re.sub(r"\d+$", "", role_part)
    if role_part in ("BW", "WB"):
        return "BW"
    if role_part in ("B", "W"):
        return role_part
    return "其他"


def label_of(dx: str, name: str) -> str:
    """成品缩略图下方的小标签（如 白T / 黑T / 白W / 黑B / 白BW）。"""
    stem = stem_of(name)
    info = classify(dx, stem)
    if info:
        if info["kind"] == "flat":
            return f"{info['color']}T"
        if info["kind"] == "bw":
            return f"{info['color']}BW"
        return f"{info['color']}{info['side']}"
    label = stem[len(dx):] if stem.startswith(dx) else stem
    label = label.strip("_")
    label = re.sub(r"^(B|W|BW|WB)\d*_", "", label)
    label = label.replace("_", " ").strip()
    return label if label else "成品"


def is_generated(dx: str, name: str) -> bool:
    """是否自动生成的贴图成品（重新贴图前的清理用；含新旧命名与 BW）。"""
    stem = stem_of(name)
    if classify(dx, stem):
        return True
    # 旧版带下划线/版本号的平铺与模特（DX0001_B_白T、DX0650_W11_黑T 等）
    return bool(re.match(rf"{re.escape(dx)}_.*_(白T|黑T)$", stem))


# ── glob 模式（批量清理用，从格式串推导）──────────────────────
def flat_glob(side: str, color: str, legacy: bool = False) -> str:
    fmt = LEGACY_FLAT_FMT if legacy else FLAT_FMT
    return fmt.replace("{dx}", "*").replace("{side}", side).replace("{color}", color).replace(".jpg", "*")


def bw_glob(color: str) -> str:
    return BW_FMT.replace("{dx}", "*").replace("{color}", color).replace(".jpg", "*")
