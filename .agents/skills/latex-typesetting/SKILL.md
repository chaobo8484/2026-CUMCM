---
name: latex-typesetting
description: "把内容填入官方 LaTeX 模板并编译出 PDF，按报错日志迭代修错。需 Word 协作稿时走 DOCX 分支。"
disable-model-invocation: true
---
# LaTeX 排版与模板填充

> 先读仓库根目录的 CONTEXT.md（术语/单位/venue 默认），全文用它的词。

人触发的生产型技能，只做一件事：官方模板分块填内容，对编译日志迭代到干净 PDF；用户不用 TEX 时走 DOCX 分支。不设计论文逻辑（那是 `paper-outline`），不画图（那是 `publication-figure` / `figure-table-generation`）。

## Operating Posture

用户键入时运行，模板和内容在手。产品是编过的文档加报错日志的解决轨迹。标准是干净构建：零错误、要紧警告零残留、PDF 100% 目检过。

两种失败模式，第一种更糟：

1. **动模板骨架。** 改 class 的边距字体标题样式来“修”版式。骨架是 venue 的法——版式疼靠删内容解决，不靠换风格。
2. **警告瞎。** 编一次，40 个警告不看，发货。未定义引用挂 [?]、引用挂 [?]、overfull 框把字顶进边距——个个都在日志里。

无干净日志声明不交 PDF。警告没过目，文档没完工。

## Hard Rules

1. **骨架冻结。** 模板 class、前导区结构、样式文件，除内容占位不动。骨架任何改动先回滚，或先经用户明确同意。
2. **一块一编译。** 填一节（或一图/一表插入），编译，读日志，修，循环。第一次编译前全篇倒进去，60 个错无地图。
3. **日志自上而下，先修第一个错。** LaTeX 级联——第一个错生出后面二十个。按序修，重编，循环。错误数下降是进度指标。
4. **占位跟踪，一个不留。** 模板 TODO、dummy、lorem ipsum——交付前 grep。投稿版里活着的占位是没读过文档的自证。
5. **图/表走文件，永不粘贴。** \includegraphics/\input 指版本化资源；宽度相对（\linewidth 分数），绝不用跨模板即碎的绝对英寸。
6. **国赛 venue 走专用合规块，以 `cumcmthesis.cls` v2.7 为准。** A4 白纸，页边距上下左右 ≥2.5cm（cls 已设 25mm，冻结不动），左侧装订预留；页码从摘要页起、页脚中部、阿拉伯数字从 1 连续编号；正文无目录、不超过 30 页；电子版第一页必须是摘要页（`[withoutpreface,bwprint]` 构建；承诺书/编号专用页只进纸质版构建）；电子版单文件 PDF 优先、≤20MB、不压缩（第十条）。逐项对照 `assets/references/2026-spec-checklist.md` 划掉。
7. **输出格式先定，TEX 与 DOCX 不混。** 投稿终稿走 TEX→PDF；协作草稿走 DOCX（`python-docx` 直编优先，`pandoc` 转换必跑 `assets/scripts/docx_gate.py` 重验）。DOCX 样式走内置（`Heading`/`Normal`/`Caption`），映射见 `assets/references/docx-mapping.md`。国赛终稿仍以 PDF 为准，DOCX 只做过程稿。

## Build Sequence

### 0. 选输出格式——gate

- 问一句：终稿投 PDF 还是协作要 DOCX。`venue` 投稿/国赛终稿默认 TEX；组内传阅、导师批注默认 DOCX。
- **gate**：格式定死再动手。两边同时填等于两份稿，选一边。

### 1. 填前盘点

- TEX：模板 `cumcmthesis.cls` v2.7 clean + 字体回退包 `cumcm-fonts.sty`（随技能分发，见 `assets/templates/cumcmthesis/`，冻结不动；用稿时整个目录随稿走），编译器强制 XeLaTeX（cls 非 XeLaTeX 直接报错；推荐 `latexmk -xelatex`），文献 `thebibliography` 简式为主，占位清单 grep 摘出。字体零操作：有官方字体（`Times New Roman/Arial + simkai/simsun`）直编；Linux/macOS 缺官方字体时 `cumcm-fonts.sty` 自动回退照常编译。要官方原字形才跑一次 `assets/scripts/setup-fonts.py` 装进系统字体目录。字体替换警告必须认领。
- 国赛 starter 为 `assets/templates/cumcm-paper.tex`（2026 章节顺序 + AI 声明 + 附录支撑材料双分支已内置），常用片段见 `assets/templates/snippets-cookbook.md`。
- DOCX：生产方式二选一（`python-docx` 直编 / `pandoc` 转换），样式映射见 `assets/references/docx-mapping.md`。
- 空模板基线先编过：内容进来前必须干净构建。基线坏了赖内容，整轮白费。

### 2. 分块填

- 顺序：front matter → 按大纲节 → 浮动体（图/表文件齐了才进）→ 文献 → 附录。每块一编。
- 数学：display 公式被引用才编号；标签命名空间（fig:/tab:/eq:/sec:）；交叉引用 \ref/\cref，永不手写数字。

### 3. 杀日志——gate

> 门禁兜底：调 `assets/scripts/texlog_parse.py <main.log>` 先找首错与分类计数（错误/未定义/`overfull>5pt`/字体替换/引擎误用），再自上而下修。交稿前再跑 `assets/scripts/preflight-2026.py` 验 2026 合规（匿名/无目录/页数/声明/占位）。

- TEX **gate**：全构建（含 bibtex/biber 若干遍）零错误收尾；剩余警告逐个 triage（overfull > 5pt 修，未定义引用归零，字体替换认领）。
- DOCX **gate**：调 `assets/scripts/docx_gate.py`（样式内置、题注 `图/表 n` 连续、占位清零、标题属性设好）。`pandoc` 转来的稿必重验，公式与题注常漂移。
- 100% 目检：浮动体位置合理，无 widow/orphan 扎眼，题注编号连续，PDF 元数据（标题/作者）设好。

### 4. 迭代检测 + 移交

- **是否已存在稿件 gate**：检查输出目录是否已有 `paper_v*.tex` / `paper_v*.pdf`。有则走 `iterate` 分支——调 `assets/scripts/versioned_write.py --in 新稿 --out-dir <out> --base-name paper --ext .tex --message "修订说明"`，产出时间戳版本 + `revisions.md` 追加，不覆盖旧稿；版本间用 `git diff` / `diff` 留痕。
- PDF + 日志摘要 + 剩余风险备注（如“图 3 终版尺寸要重导出”）。下步：引用不干净去 `citation-bibliography`，文字去 `polish-proofread`，门禁去 `reproducibility-checklist`。

## Never Ship

| 禁忌 | 替代 |
| --- | --- |
| 改骨架风格 | 删内容适配 |
| 整篇第一次编译 | 一块一编译 |
| 先修第 34 个错 | 自上而下，先修第一个 |
| 占位活到交付 | grep 清零再交 |
| 图宽绝对值 | 相对 \linewidth 分数 |
| 警告不读 | 逐个 triage |
| 国赛稿出现身份/学校/赛区信息 | 匿名 grep 全文清零（第六条、第十一条 + `2026-spec-checklist.md`），否则 HOLD |
| 国赛电子版混入承诺书/编号页 | 双构建分离：纸质版含、电子版 `[withoutpreface,bwprint]` 第一页摘要页（第十条） |
| 国赛正文出现目录/超 30 页 | 删目录、删内容适配，`preflight-2026.py` 验过 |
| 国赛缺 AI 声明/支撑材料声明 | 按 `cumcm-paper.tex` 双分支二选一填实，无也明示 |
| DOCX 直接格式刷屏 | 内置样式，`docx_gate.py` 验过 |
| DOCX 题注手写编号 | `图/表 n` 连续，引用对读 |
| DOCX 公式图片无替代文本 | OMML 或图片加替代文本 |

## Output

- **PDF**——干净构建，目检过（TEX 分支）。
- **DOCX**——门禁报告 + 目检（DOCX 分支，过程稿）。
- **日志轨迹**——踩过的错和修法，警告 triage。
- **占位 grep**——零残留，证据展示。
- **移交**——下个技能点名。

## Tone

立场鲜明、废话少。当正确答案是“模板没病——你这节超 3 页，删”就直说。日志 12 个 overfull 框，修框，不要零错误就宣布胜利。

模板文件见 `assets/templates/cumcm-paper.tex`（国赛 starter，`cumcmthesis.cls` v2.7 随 `assets/templates/cumcmthesis/` 分发并冻结；改动前先核对 venue spec）。常用片段见 `assets/templates/snippets-cookbook.md`，合规检查单见 `assets/references/2026-spec-checklist.md`。旧自写 `ctexart` 骨架已归档为 `assets/templates/_archived-ctexart-skeleton.tex`，不再作为默认模板。
