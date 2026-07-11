# 交接（HANDOFF）— 本会话：T 恤印花「自然度」+ 贴图正确性

> 给完全没有上下文的新会话看。读完应能直接接手。本文档覆盖旧版 HANDOFF（旧版讲 `WB_PRINT_ADAPTER v1.0` / CSV 乱码，属另一条任务线、在 `D:\Semems WB\04_OS` 子仓，与本会话无关；本会话全程在 `E:\Kimi Code\white_t_mockup`）。

---

## 0. 一句话定位

`white_t_mockup`（在 `E:/Kimi Code`，git → `jordan23kevin/ZCodeProject.git`，分支 `white-t-mockup`）：把 AI 生成的透明底印花自动贴到白/黑 T 胚衣上。本会话主攻两件事：

1. **自然度**：让印花跟随衣服褶皱、明暗、布纹（displacement + shadow/highlight 转移 + 布纹），不再像贴纸。
2. **贴图正确性**：按贴图文件名选胚衣颜色、黑/白 T 用不同混合模式、**不擅自反相**。

---

## 1. 关键环境与路径（别混）

| 角色 | 路径 |
|------|------|
| 代码 / git 仓（本工作目录） | `E:/Kimi Code`（包 `white_t_mockup/`、脚本 `scripts/`） |
| venv（跑都用它） | `E:/Kimi Code/psd_env/Scripts/python.exe -m white_t_mockup …` |
| 胚衣 | `D:/Semems/1胚衣/黑/`、`D:/Semems/1胚衣/白/`（PNG 单图或 PSD） |
| 自然度模板库 | `D:/Semems/1胚衣/_tpl/<款名>/{source,mask,disp,shadow,highlight}.png + metadata.json + _preview/` |
| 参数唯一来源 | `E:/Kimi Code/docs/胚衣参数表_模板.csv` → `scripts/sync_presets_from_csv.py` → `white_t_mockup/presets.json` |
| 印花来源 | `D:/Semems WB/02_PROJECTS/DXxxxx/02_REM_BG/*_cut.png` |
| **批量实际入口（重要）** | `D:/Semems WB/01_INBOX/lovart_bridge.bat` → 系统 Python311 + `C:/Users/Administrator/ZCodeProject/lovart_bridge.py` |

> **white_t_mockup 跑的就是本仓 `E:/Kimi Code`**（本次已核实）：`lovart_bridge.py`（`C:/Users/Administrator/ZCodeProject`，`MOCKUP_ROOT=E:/Kimi Code`）调 `white_t_mockup` 时把 `PYTHONPATH` 设成 `E:/Kimi Code;E:/python_packages`。所以本仓改动**立即生效**（每次贴图新开子进程读盘），无需 git pull、无需重启 bridge。
>
> 但 **check_rem.py 不在本仓**：它在 `D:/Semems WB/04_OS/engine/check_rem.py`（运行版，无 git）与 `C:/Users/Administrator/ZCodeProject/engine/check_rem.py`（master 分支，版本滞后）。改 check_rem.py 后须 kill 端口 8766 常驻进程，由 bridge 守护线程重拉才生效（重启 lovart_bridge.bat 不带走它）。

---

## 2. 已完成（均已 commit + push 到 GitHub）

### v1.4.0（commit `02f899c`）自然度模板管线
- `white_t_mockup/core.py`：
  - `apply_displacement()`：numpy 双线性 remap，按置换图灰度偏移、`mask` 限区。
  - `transfer_shadow_highlight()`：阴影 Multiply / 高光 Overlay 转移到印花，限「印花 ∩ 衣服区」。
  - `apply_realism()` 三件套（降饱和 / 降亮度 / 高斯模糊）+ `overlay_texture()`（布纹透出）。
  - `apply_mockup_transform()` 与 `apply_mockup()`（legacy）都接入模板管线：`tpl_dir` 含 `mask.png` 即自动启用。
- `white_t_mockup/cli.py`：新增 `--tpl-dir / --disp-strength（默认 12）/ --shadow-opacity（0.35）/ --highlight-opacity（0.25）`；未传 `--tpl-dir` 自动探测 `胚衣根/_tpl/<款名>/`。
- `scripts/make_template_assets.py`：OpenCV **GrabCut + 暗度先验**从合成模特图自动生成 `_tpl/<款>/{mask,disp,shadow,highlight}.png + metadata.json + _preview/`（`psd_env` 已装 `opencv-python-headless 5.0.0.93`）。
- 黑 W5 首套素材已生成 `D:/Semems/1胚衣/_tpl/黑W5/`：mask 覆盖率 38%，主体（躯干+两袖+领口）准；瑕疵 = 左下短裤局部误入 + 领口发丝（已写进 `metadata.json needs_manual_fix`）。

### v1.4.1（commit `e504c7c`）fix
- 黑 T 默认混合模式 `multiply` → **`normal`**（按衫色自动：黑 T normal / 白 T multiply；显式 `--blend-mode` 仍优先）。`cli.py` 混合模式解析重排到「衫色确定之后」。

### v1.5.0 黑衫智能显色（dark_boost）
- 新增 `enhance_dark_print_for_black_shirt()`：LAB 空间仅提亮暗部、保留全部原色、保护亮部(>140)。当时设为黑衫默认 prepare_method，取代会丢色的旧 `silhouette`(涂白) / `value_invert`(HSV明度反相→亮色变黑)。

### v1.6.0（当前）黑衫白墨打底（white_underbase，新默认）
- 新增 `add_white_underbase()` + `black_shirt_print_optimize()`：自适应浓度白墨打底（越暗白墨越厚）+ 轻度提亮，模拟真实 DTG 黑衫『先喷白墨再喷彩色』，使极暗区域在黑布可见、保留原色、不漂白。
- 黑衫默认 `dark_boost` → **`white_underbase`**（core + cli + `--for-black-shirt` 路由）。白衫 no-op。
- **根因**：dark_boost 救不了近黑设计——PS 贴图 `place_design.jsx` 从不铺白底，纯黑印黑布物理不可见。white_underbase 把白墨打底烘进设计图本身，无需改 PS。
- **两套黑衫流程都接了**：① 本仓 `white_t_mockup`；② `D:/Semems WB/04_OS/engine/check_rem.py`（AI去背贴图页『反黑』→`_黑W_cut.png`→PS平铺图）内联同款算法。
- 实测 DX0635：近黑像素 64万→4413、不漂白、红字保色。

### 回滚锚点（tag 都在远端）
`v1.3.1`（`f83700a`，final 像素版）/ `v1.4.0`（`02f899c`）/ `v1.4.1`（`e504c7c`）/ `v1.5.0`（dark_boost）/ `v1.6.0`（white_underbase）。搞砸就 `git checkout v1.6.0 -- <文件>` 或整库回退到 tag。

---

## 3. 实测结论（`DX0654_W_cut.png` 贴黑 W5，`final 614×614 / top 470 / center 716`）

| 混合 + 预处理 | 效果 |
|------|------|
| `multiply` | 狗 / 星星糊成一团深黑（黑 T 用 multiply 是错的） |
| `screen` | 过曝泛光、印花浮在衣服上 |
| `normal` + 反相（`--for-black-shirt`） | 清晰，但狗变紫红（反相色，不是原色）→ **用户否决** |
| **`normal` + 不反相**（`--blend-mode normal --prepare-method none`） | **正确**：狗原色（黑棕腊肠）、字黄/粉、星彩，融入黑 T ✓ |

---

## 4. 当前卡点

1. **批量跑的不是本仓**。`lovart_bridge.bat → C:/Users/Administrator/ZCodeProject/lovart_bridge.py`。本仓改动需那份 `git pull` 才进批量，且要查它的贴图调用是否强制 `value_invert`、混合模式对不对。**用户没让动生产代码，别擅自去改**（刚因「自作多情加功能」被骂）。
2. 黑 W5 自动 mask 有瑕疵（短裤 / 领口）。工业级需人工 PS 修一次 mask 后固化复用；用户认可的流程是「自动生成初版 → 人工修 mask → 固化模板」，但具体三态（`mask_auto / mask_manual / mask_final`）升级用户提过方案、**未拍板实施**。
3. 黑 W5 实测用的 `final/top/center` 是估的（黑 W5 在 `presets.json` 是 `legacy`，`effective_*` 字段未必准）。正式批量以 CSV / presets 为准。

---

## 5. 下一步计划（候选，等用户确认，别擅自动）

- 是否同步生产代码：`C:/Users/Administrator/ZCodeProject` 执行 `git pull` 到 `v1.4.1`，并检查贴图调用「不强制反相、混合按衫色」。**等用户开口**。
- 模板三态升级：`mask_auto / mask_manual / mask_final` 不覆盖人工、mask 质量评分 + 疑似错误区域标记、`_preview` 加「印花测试合成」、环境检测记录（SAM/BiRefNet/torchvision/OpenCV fallback）。用户提过完整方案，没让立刻做。
- 黑 T 彩色印花原色 trade-off：深色图案在黑底会发暗（印花本身需为黑底设计），策略待用户定。

---

## 6. 踩过的坑 / 红线（绝对不要再踩）

1. **不要擅自加反相 / 不要 `--for-black-shirt`**。规则：看 `02_REM_BG` 贴图文件名 —— 含「黑」贴黑 T 专用图、含「白」贴白 T 专用图、都不含（如 `DX0654_W_cut.png`）→ 两色通用、**原色**贴。反相由用户自己做专用图，代码默认不反相（不传 `--shirt-color` 就不反相）。**这是用户最强硬的点。**
2. **黑 T 别用 `multiply`**（印花糊）。黑 T `normal` / 白 T `multiply`（`v1.4.1` 已按衫色自动）。
3. **`黑W5.psd` 没有干净衣服层**：背景层是合成模特图（人+衣服+背景糊一层），另一层 214×412 是小 logo。别从 PSD 提 disp；用 `make_template_assets.py` 从 PNG 自动分割，或人工 PS 做 mask。
4. **黑 T 明暗信号弱**，displacement 效果克制属正常；`disp-strength` 别超 ~15（会扭出伪影），12 是甜区。
5. **批量入口不是本仓**：改代码前确认改的是生产实际跑的那份（`C:/Users/Administrator/ZCodeProject`），否则改了白改。
6. **别自作多情加功能 / 加文档**：用户明确「少文档、统一 CSV」「要不要反相我自己操作」。新增功能 / 文档前先问。本 HANDOFF 是用户主动要求才写。
7. **CSV 是 single source of truth**；改前确认 Excel 已关（否则 `EBUSY`）；中文写文件用 UTF-8（Windows Git Bash 终端 print 中文会 GBK 乱码，但文件本身没坏，看内容用 `Read`，别信终端）。
8. **commit 精确 add**，不带 untracked：`_compare/_test/_demo *.jpg`、`AGENTS.md`、`HANDOFF.md`、`contaminated_dx.json`、`content_trace.csv`、`split_*`、`scripts/make_displacement.py` 都不带。git mutation（commit / push / tag）用户已授权本 workflow。
9. 项目 `AGENTS.md`：禁 superpowers skill、禁 plan mode，FAST MODE 直接做、短回复、结论 / 操作 / 结果。启动读 `C:/Users/Administrator/.kimi-code/AGENTS.md`。
10. `psd_env` 原只有 `numpy + pillow`，本会话装了 `opencv-python-headless`（分割用）；**无** SAM / rembg / torch，自动分割只能到 GrabCut 级（< 人工 PS）。
11. `tests/test_presets.py` 11 个旧名失败是既有遗留，别动。

---

## 7. 常用命令

```bash
cd "E:/Kimi Code"

# 跑贴图（黑 T：--blend-mode normal，不要 --for-black-shirt）
psd_env/Scripts/python.exe -m white_t_mockup <印花.png> <out.jpg> \
  --template "D:/Semems/1胚衣/黑/黑W5.png" \
  --final-w 614 --final-h 614 --rotate 0 \
  --effective-top-y 470 --effective-center-x 716 \
  --blend-mode normal --prepare-method none

# 生成模板素材（自动生成 mask/disp/shadow/highlight + _preview）
psd_env/Scripts/python.exe scripts/make_template_assets.py --src "D:/Semems/1胚衣/黑/黑W5.png"

# 同步参数（CSV → presets.json）
psd_env/Scripts/python.exe scripts/sync_presets_from_csv.py --force

# 测试
psd_env/Scripts/python.exe -m pytest tests/

# 黑 W5 模板 mask 质量预览
#   D:/Semems/1胚衣/_tpl/黑W5/_preview/mask_overlay.jpg
```

---

## 8. 未 commit 的工作区

核心代码都已在 `v1.4.1`。untracked 含本 `HANDOFF.md`、若干 `_demo / _compare` jpg、`AGENTS.md`、`split_*`、`scripts/make_displacement.py` 等 —— 按规则都不进 commit，除非用户明确要求。

---

*新会话请先看 §6 红线（尤其 1 / 5 / 6），再按 §5 与用户确认推进。*
