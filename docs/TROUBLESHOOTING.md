# 问题与解决方案

## 1. psd-tools 图层顺序与视觉层级不一致

**现象**  
`psd-tools` 迭代图层时声称顺序是 top → bottom，但实际模板中：
- 图层 0：占满画布的背景（模特底图）
- 图层 1：小 bbox 的手部前景遮罩

如果简单按迭代索引取 `layers[0]` 当背景、`layers[-1]` 当遮罩，会把两者搞反。

**原因**  
PSD 文件的实际图层命名/顺序由 Photoshop 生成，psd-tools 的迭代顺序并不总是与视觉层级一致。

**解决方案**  
在 `core.load_template()` 中按 `bbox` 识别：
- `bbox == (0, 0, width, height)` 的图层为背景
- 其余图层为前景遮罩

这样不依赖图层索引，换模板也能自适应。

## 2. 手部遮罩位置偏移

**现象**  
如果把手部遮罩直接贴在 `(0, 0)`，手会跑到左上角，设计图会错误地覆盖到手上。

**原因**  
前景遮罩图层在 PSD 中的 bbox 是 `(657, 1011, 1340, 1381)`，不是从画布原点开始。

**解决方案**  
使用 `fg_layer.bbox[:2]` 获取原位置，粘贴时传入该坐标。

## 3. 混合模式选择

**现象**  
用普通 alpha 粘贴时，设计图颜色鲜艳但像贴纸；用 Multiply 时颜色更暗但融入衣褶。

**对比**  

| 模式 | 效果 | 适用场景 |
|------|------|----------|
| normal | 颜色鲜艳，边缘清晰 | 需要强对比、卡通风格 |
| multiply | 贴图随衣褶明暗起伏，更自然 | 水彩、复古、写实风格 |

**结论**  
DX0533 鲸鱼图为水彩风格，最终选择 **Multiply** 作为白 T 标准。

## 4. 输入 PNG 不透明导致黑底/白底

**现象**  
如果输入设计图不是透明底，合成后会出现黑色或白色方块覆盖 T 恤。

**解决方案**  
确保输入 PNG 的 alpha 通道正确。可用 Photoshop/GIMP/Remove.bg 等工具先抠图。

## 5. 旋转方向

**现象**  
PIL 的 `Image.rotate(angle)` 正角度表示逆时针旋转，而用户说的"顺时针旋转 1°"需要传负角度。

**解决方案**  
`apply_transform()` 中调用 `rotate(-rotation_degrees, expand=True)`，确保顺时针方向正确，并用 `expand=True` 避免旋转后内容被裁切。

## 6. 有效像素定位

**现象**  
贴图缩放/旋转后，透明边缘会让整体尺寸变大。如果按整张设计图的尺寸定位，实际图案位置会偏移。

**解决方案**  
`find_effective_bbox()` 通过 alpha 通道（阈值 10）找出非透明像素边界框，再以边界框的最高点和水平中心为基准定位，保证图案落在用户指定的坐标上。

## 7. 模板类型混用

**现象**  
PSD 模板有手部遮罩层，PNG 模板没有。如果对所有模板都尝试粘贴手部遮罩，PNG 模板会报错。

**解决方案**  
`load_any_template()` 按文件后缀分发：PSD 走 `load_template()`，PNG 走 `load_png_template()`（前景返回 None）。`apply_mockup_transform()` 在前景不为 None 时才粘贴遮罩。

## 8. 复现性保障

**措施**  
- 所有默认参数写入 `config.py` 和 `VERSION` 文件
- 每张胚衣模板的参数独立写入 `white_t_mockup/presets.json`
- 使用 `requirements.txt` 固定依赖版本
- 提供 DX0533 示例输入输出，可用 pytest 做回归验证
- Git tag 标记每个稳定版本

## 9. 模板预设与模板尺寸变化

**现象**  
不同胚衣（如 `W3.psd`、`W4.png`、`1B.png`、`3B.png`、`4B.png`）的缩放、旋转、最高点、中心点都不一样；同一张 PNG 模板在不同时间也可能被替换成不同像素尺寸。如果把模板参数或画布尺寸硬编码进代码或测试，换胚衣或模板更新后就会失败。

**解决方案**  
- 每张胚衣的参数单独记录在 `white_t_mockup/presets.json`，CLI 用 `--preset <模板文件名>` 或 `--template` 文件名自动匹配。
- 新增胚衣时新增一条 preset，不要复用其他胚衣参数。
- 测试不要断言固定画布尺寸（如 `1728 × 2304`），应读取当前模板实际尺寸后再断言。

## 10. 缩放算法演进与参数来源单一化（v1.3.0）

**踩过的坑**
- 早期用「缩放百分比 + 逐款 kx/ky 校准」复现 PS（kx/ky = native/2048）。三款标定曾反复猜错（统一成黑正2→黑W5→白正2），根因是把 PS「置入后显示尺寸」当成了「Transform 100% 基准尺寸」；所谓 1.333 只是 2730/2048 的巧合，不是算法。
- CSV 曾分「旋转方向 + 旋转角度」两列，易填错；参数同时写在 CSV、`胚衣参数表.md`、README/ARCHITECTURE/SKILL 四五处，每次改要各处同步，经常不同步。CSV 偶尔"乱码"实为终端用 GBK 显示 UTF-8，文件本身（带 BOM）没坏。

**最终方案**
- **final 像素模型**：CSV 直接填「缩放后宽px/缩放后高px」（PS 里贴图层最终像素），`apply_transform_ps()` 直接 `resize((final_w, final_h))` 再 `rotate(-deg, expand=True)`，原图固定 2048×2048，final 即目标像素，100% 复现 PS，无需 native/kx/ky。
- **旋转角度单列带符号**：负=逆时针、正=顺时针（与 PS / `apply_transform` 一致），去掉「旋转方向」列。
- **参数单一来源**：只维护 `docs/胚衣参数表_模板.csv`；贴图前 `sync_if_stale()`（或 `python scripts/sync_presets_from_csv.py --force`）自动同步到 `white_t_mockup/presets.json`，代码只读 presets.json。不再生成 md 镜像，不再在 README/ARCHITECTURE/SKILL 写参数快照。
- 三款 final 标定值：白正2 546×546、黑正2 545×583、黑W5 544×602；其余款在 PS 量最终像素后填入 CSV 即可。

**回滚**
- 每个稳定版打 git tag（如 `v1.3.0`）。回滚：`git revert <commit>` 撤销某次改动，或 `git checkout v1.3.0 -- <文件>` 取回旧版文件。
