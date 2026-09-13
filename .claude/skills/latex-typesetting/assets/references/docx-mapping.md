# LaTeX → DOCX 结构映射（latex-typesetting DOCX 分支）

> 协作草稿用 DOCX，投稿终稿仍走 TEX→PDF（venue 要求，见 `CONTEXT.md`）。本文件只定映射，不堆正文。

| LaTeX | DOCX |
|---|---|
| `\section` / `\subsection` / `\subsubsection` | `Heading 1` / `Heading 2` / `Heading 3`（内置样式，禁直接改字号） |
| 正文 | `Normal` |
| `\caption`（图/表） | `Caption` 样式，`图 n` / `表 n` 从 1 连续编号 |
| `\ref` / `\cref` | 手工交叉引用文字，编号与题注对上（`docx_gate.py` 校验题注序列，正文引用人工对读） |
| `thebibliography` / `.bib` | 文末参考文献表（手工或 Word 引文域），仍走 `citation-bibliography` 双向计数 |
| display 公式 | `OMML` 公式对象优先；复杂公式转图片 + 替代文本写清含义 |
| `\includegraphics` | 内嵌图片 + 替代文本；宽度相对页面，不用绝对磅数硬撑 |

生产方式二选一，写明：

- `python-docx` 直编（样式可控，推荐协作稿）。
- `pandoc` 转换（`pandoc paper.tex -o paper.docx`，转后必跑 `docx_gate.py` + 人工对读，公式与题注常漂移）。

国赛/期刊终稿 gate：电子版以 PDF 为准（见本技能 Hard Rules 6），DOCX 只做过程稿。
