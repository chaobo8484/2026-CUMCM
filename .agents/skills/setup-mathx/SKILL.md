---
name: setup-mathx
description: "第一次用先跑我：绑定数据目录、模板版本、绘图后端和证据后端，写进 docs/agents/ 供其余技能读取。"
disable-model-invocation: true
---

# Setup-MathX：一次绑定，处处复用

用户键入时运行，每个项目一次。问四个问题，答案写进 `docs/agents/mathx-config.md`，停。其他技能有这个文件就读它，不再重问。

## The four questions

四个问题一轮问完，各带推荐默认。等回答再落盘。

```
❓ **Q1** — **数据目录**: 分析数据放在哪里？(推荐: ./data, 原始与处理后分 raw/ + processed/)

❓ **Q2** — **模板与输出格式**: 目标 venue 与模板？(推荐: 按 paper-outline 的 venue 判断: MCM 用官方 mcmthesis, 国赛用 GB/T 7714 模板, 期刊用 venue 模板; 无论文需求填 none；中文内容默认 `XeLaTeX`，否则 `pdfLaTeX` 见 `CONTEXT.md:21`；终稿 PDF 用 TEX，协作草稿用 DOCX 见 `latex-typesetting`)

❓ **Q3** — **绘图后端**: 静态图风格与交互需求？(推荐: Matplotlib + Okabe-Ito 静态为主, 探索期加 Plotly)

❓ **Q4** — **证据后端**: 外部取证走哪档？(推荐: none; 自给链接选 manual; 通用搜索选 generic; Firecrawl 是高级选项，仅深爬用，需自备 key 存环境变量，仓内只记名不存值)
```

## Write the config

在项目里建 `docs/agents/mathx-config.md`，内容如下（一字不差）：

```markdown
# mathx-config (written by setup-mathx, <date>)

- data_dir: <answer 1> (raw/ + processed/ convention)
- venue_template: <answer 2> (name + version, or none)
- latex_compiler: <XeLaTeX|pdfLaTeX> (中文内容 XeLaTeX，否则 pdfLaTeX)
- output_format: <TEX|DOCX> (终稿 PDF 用 TEX，协作草稿用 DOCX)
- plot_backend: <answer 3> (static style block location + interactive yes/no)
- evidence_backend: <answer 4> (none | manual | generic | firecrawl-advanced)
- evidence_key_source: env:FIRECRAWL_API_KEY (name only, never the value)
- glossary: project terms differing from CONTEXT.md (empty at setup, grows via use)
```

然后三行告诉用户：记了什么、其他技能会读它、答案变了重跑 `/setup-mathx`。停——不要顺手开始建模、搭大纲、画图。

## Tone

快而行政。本技能是额外开销；压到最小。四个问题，一个文件，完事。
