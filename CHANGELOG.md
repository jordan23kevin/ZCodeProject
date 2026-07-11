# Changelog

## [1.6.0] - 2026-07-12

### Added
- **黑衫白墨打底 `prepare_method="white_underbase"`（新默认）**：`add_white_underbase()` 自适应浓度白墨打底（越暗白墨越厚 max0.9/min0.05，transition_threshold=130，edge_feather=5，boost_sat=0.35 保饱和色）+ `black_shirt_print_optimize()`（白墨打底 → 轻度 dark_boost=0.25 提亮 + 饱和补偿）。模拟真实 DTG 黑衫『先喷白墨、再喷彩色』，使极暗区域在黑布上可见，同时保留全部原色、不漂成白。
- `__init__.py` 导出 `add_white_underbase` / `black_shirt_print_optimize` / `enhance_dark_print_for_black_shirt`。

### Fixed
- **`add_white_underbase()` 缺 `import cv2`**：函数内用 cv2 但未导入（cv2 仅在 `enhance_dark_print_for_black_shirt` 懒加载），直接调用会 `NameError: name 'cv2' is not defined`。已在函数内补懒加载。

### Changed
- 黑衫默认预处理 `dark_boost` → **`white_underbase`**（core.py `prepare_design_for_shirt` / `apply_mockup` / `apply_mockup_transform` 默认值 + cli.py `--prepare-method` 默认 + `--for-black-shirt` 路由）。
- cli.py `--prepare-method` choices 增加 `white_underbase`。
- 白衫 `white_underbase` / `dark_boost` 均为 no-op（保持原色）。

### Root Cause（为什么换 white_underbase）
- 旧『反黑』两条路都废：`silhouette` 把非透明像素涂纯白（颜色全丢）；`value_invert` 做 HSV 明度反相（亮色变黑）。
- 即便 dark_boost 保住颜色、提亮暗部，也救不了**接近纯黑**的设计：PS 贴图脚本 `place_design.jsx` 只把设计图 duplicate 到黑衫胚衣、保留透明，**从不铺白底**。纯黑印黑布物理不可见（实测 DX0635 图 51% 像素近黑）。
- white_underbase 在贴图前把白墨打底**烘进设计图本身**，无需改 PS 脚本即可显色。
- 实测（DX0635 真实图）：近黑(0-20)像素 64万→4413；接近白(>245)=0（不漂白）；红字 (101,16,23)→(127,52,59) 保色。

### Notes
- **两套黑衫流程都已接 white_underbase**：① `white_t_mockup`（效果图生成，E:/Kimi Code）；② `check_rem.py`（AI 去背贴图页『反黑』按钮 → `_黑W_cut.png` → PS place_design 平铺图，D:/Semems WB 运行版）。check_rem.py 内联了同款 add_white_underbase/black_shirt_print_optimize。
- **check_rem 是常驻进程**：改 check_rem.py 后须 kill 端口 8766 进程，由 lovart_bridge 守护线程重拉才生效（重启 lovart_bridge.bat 不会带走它）。
- 回滚锚点：`v1.5.0`。

## [1.5.0] - 2026-07-12

### Added
- **原样保色贴图模式**（`--preserve-color`）：只做几何扭曲（displacement + 遮罩裁剪），完全不改颜色/亮度/饱和度。自动关闭反色/显色（prepare_method=none）、阴影正片叠底（shadow=0）、高光叠加（highlight=0）、降饱和（sat=1.0）、降亮度（bri=1.0）、边缘模糊（realism=False），混合模式 normal。褶皱立体感仅由 displacement 位移扭曲体现。
- `enhance_dark_print_for_black_shirt()`（dark_boost）：黑衫智能显色算法。仅提亮暗部保留原色、保护亮部(>140)，模拟 DTG 白墨打底效果。默认 prepare_method。

### Fixed
- **cli.py 保色模式参数传递 bug**：`apply_mockup_transform()` / `apply_mockup()` 调用处使用 `args.shadow_opacity`/`args.highlight_opacity` 而非本地重写变量，导致 `--preserve-color` 模式下 shadow/highlight=0 不生效（bridge 写死的 0.35/0.25 照旧压暗）。
- **cli.py 缺失 saturation/brightness 参数传递**：`--preserve-color` 设置的 sat=1.0/bri=1.0 未传给渲染函数。
- **cli.py realism 在保色模式下仍生效**：保色模式应连边缘模糊也跳过。
- **`transfer_shadow_highlight()` shadow 归一化**：shadow 从全局暗度改为"相对褶皱阴影"（p85 基准，SHADOW_FLOOR=0.55），不再整体压暗印花。
- **`apply_realism()` 预乘 alpha 感知高斯模糊**：修复白字边缘锯齿，默认 blur_radius=0.4。

### Changed
- 生产默认 shadow_opacity / highlight_opacity：0.35/0.25 → **0.22/0.22**（cli.py + core.py + bridge 同步）。
- `apply_realism()` 默认 saturation=0.97, brightness=1.0, blur_radius=0.4（原来降亮度过大）。
- 诊断方法论：测量印花亮度必须用设计图自身 alpha 锁定白字核心像素（基线 #f9），不能用整图 lum≥阈值（会混入衬衫白背景/灰褶皱，产生雷同假象）。

### Notes
- **重要：两条渲染链** — ① `lovart_bridge.py /api/mockup`（手动贴图，hardcode --shadow/--highlight）；② `check_rem.py → w_mockup_extra.py`（自动贴图，用 presets.json）。改参数需两处同步。
- **w_mockup_extra.py 黑衫贴图**：从 `--blend-mode screen`（仅改混合，无 dark_boost）→ `--preserve-color`（原样保色，几何变形 only）。
- 回滚锚点：`v1.4.1`。

## [1.4.1] - 2026-07-10

### Fixed
- 黑 T 默认混合模式由 multiply 改为 **normal**（按衫色自动：黑 T normal / 白 T multiply；显式 `--blend-mode` 仍优先）。黑 T 贴透明底印花用 Normal 保留图案原色、Opacity 100，衣服明暗交给模板管线的 shadow/highlight/布纹层透出（POD 推荐基础方式）。修正黑 T 反白印花被 multiply 压暗、糊成一团的问题（DX0654 实测：multiply 糊、screen 过曝泛光、normal 原色清晰且融入）。`white_t_mockup/cli.py` 混合模式解析重排到衫色确定之后。回滚锚点：`v1.4.0`。

## [1.4.0] - 2026-07-10

### Added
- 自然度模板管线（工业级 mockup）：`apply_displacement()`（numpy 双线性 remap，按置换图灰度偏移、mask 限区）+ `transfer_shadow_highlight()`（阴影 Multiply / 高光 Overlay 转移到印花，限印花∩衣服区）。`apply_mockup_transform()` / `apply_mockup()` 新增 `tpl_dir / disp_strength / shadow_opacity / highlight_opacity`；目录含 `mask.png` 即自动启用。黑 T 真实感权重：阴影 40 / 高光 20 / 置换 30 / 布纹 10。
- 真实感三件套：`apply_realism()`（降饱和 / 降亮度 / 边缘柔化）+ `overlay_texture()`（布纹透出）。CLI `--no-realism / --blur / --texture-opacity`。
- 模板素材自动生成：`scripts/make_template_assets.py`（OpenCV GrabCut + 暗度先验分割衣服，产出 `_tpl/<款>/{source,mask,disp,shadow,highlight}.png + metadata.json + _preview/`）。黑 T 与黑发 / 短裤同色易混，自动 mask 需按 `_preview` 人工复核（metadata `needs_manual_fix` 已标）。
- CLI 模板管线参数：`--tpl-dir / --disp-strength / --shadow-opacity / --highlight-opacity`；未传 `--tpl-dir` 时自动探测 `胚衣根/_tpl/<款名>/`。

### Changed
- `--disp-strength` 默认 8 → 12（黑 W5 实测 12 比 8 更贴褶皱且无伪影）。
- 模板库目录约定：`D:/Semems/1胚衣/_tpl/<款名>/`（一张模板供所有印花复用）。

### Notes
- 自动分割质量 < 人工 PS；黑 T 明暗信号弱，displacement 效果克制属正常。回滚锚点：`v1.3.1`（f83700a）。

## [1.3.0] - 2026-07-10

### Changed
- 贴图缩放改用 **final 像素模型**：CSV 直接填「缩放后宽px/缩放后高px」（PS 里贴图层最终像素），代码 `resize((final_w, final_h))` 再旋转，原图固定 2048×2048，100% 复现 PS。取代旧的「缩放百分比 + 水平校准kx/垂直校准ky（native 标定）」三列。
- 胚衣参数统一收敛到 `docs/胚衣参数表_模板.csv` 一份；删除 `docs/胚衣参数表.md` 镜像及 README/ARCHITECTURE/SKILL 里的参数快照表，避免多处同步。`scripts/sync_presets_from_csv.py` 只同步 CSV → `white_t_mockup/presets.json`。
- 旋转角度列沿用正负约定（负=逆时针 / 正=顺时针，同 PS），去掉「旋转方向」列。
- CLI：`--scale` 改为 `--final-w/--final-h`，删除 `--target-height`（legacy 旧版缩放也用 final）。

### Fixed
- 修正「把 PS 置入后显示尺寸当成 Transform 100% 基准尺寸」的算法误判；所谓 kx/ky=1.333 只是 2730/2048 的巧合，不是算法。

## [Unreleased]

### Added
- `prepare_design_for_shirt()`：支持 `value_invert`（亮度反相，保留色相/饱和度）、`silhouette`（黑白剪影）、`none`（无处理）。
- `apply_mockup()` 与 `apply_mockup_transform()` 新增 `shirt_color` 和 `prepare_method` 参数。
- CLI 新增 `--shirt-color`、`--prepare-method`、`--for-black-shirt`、`--for-white-shirt`。

## [1.2.1] - 2026-07-09

### Added
- 新增 `3B.png` 胚衣模板预设：缩放 32%、逆时针旋转 3°、有效像素最高点 y=700、中心 x=777、Multiply 混合

### Changed
- 版本号升级为 1.2.1

## [1.2.0] - 2026-07-09

### Added
- 模板预设系统：`white_t_mockup/presets.json` 单独记录每张胚衣的参数
- CLI 新增 `--preset` 和 `--list-presets` 参数
- 新增 `3.psd`、`W4.png`、`1B.png` 三张模板的预设
- `config.py` 新增 `load_presets()`、`get_preset()`、`list_presets()`

### Changed
- 版本号升级为 1.2.0

## [1.1.0] - 2026-07-09

### Added
- 新版 transform 方法：缩放比例 + 顺时针旋转 + 按有效像素最高点/中心点定位
- 支持 PNG 单图层模板（无手部遮罩）
- `apply_mockup_transform()`、`apply_transform()`、`find_effective_bbox()`、`calculate_effective_position()`、`load_png_template()`、`load_any_template()` 等新函数
- CLI 自动判断新版/旧版方法（提供 `--scale` 即启用新版）
- 新增 `tests/test_transform.py`，覆盖缩放、旋转、有效像素定位、PNG 模板加载

### Changed
- 版本号升级为 1.1.0
- 文档全面更新（README、ARCHITECTURE、TROUBLESHOOTING、Skill）

## [1.0.0] - 2026-07-09

### Added
- 初始版本：白 T 恤样机贴图自动化工具
- 支持命令行与 Python API 两种调用方式
- 自动识别 PSD 模板中的背景层与手部前景遮罩
- 支持 normal、multiply、screen、overlay、linear_burn 混合模式
- 默认参数固化：top-y=449, center-x=735, target-height=677, blend-mode=multiply
- 附带 DX0533 完整示例（输入 PNG + 输出 JPG）
- 项目内 Kimi Code Skill：`.kimi/skills/white-t-mockup/SKILL.md`
- 单元测试覆盖核心函数
- 文档：README、ARCHITECTURE、TROUBLESHOOTING
