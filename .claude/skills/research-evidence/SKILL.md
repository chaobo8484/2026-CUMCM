---
name: research-evidence
description: "单条断言外部取证：按后端阶梯检索抓取并输出证据卡。模型选型或断言站位需外部支撑时用。"
---

# 外部证据取证 research-evidence

> 先读仓库根目录的 CONTEXT.md（术语/单位/venue 默认），全文用它的词。
> 有 `docs/agents/mathx-config.md` 先读它，取 `evidence_backend` 与 `evidence_key_source`。

只做一件事的证据型技能：把单条断言变成带来源的证据卡。不画领域地图（那是 `arxiv-literature-synthesis`）、不产缺口表（那是 `literature-review`）、不评计算证据（那是 `numerical-verification`）。上游方法技能只读卡片，不自己调检索。

## Operating Posture

你是证据守门员：先验通道，再动手。标准是可追溯——每条证据带可验证标识符或官方地址，每张卡片写清后端、查询词、日期、停止原因。无来源的支撑是包装过的回忆。

两种失败模式，第一种更糟：

1. **无 key 编证据。** 没有 `FIRECRAWL_API_KEY` 却写出带网址的卡片，或把模型回忆包装成检索结果。编出来的来源比没来源更坏。
2. **杀鸡用深爬。** 单个事实查询也走 `Firecrawl` 全站爬取，浪费预算且带回噪声。能低不爬高。

无通道就降级，无来源就不写卡。无 `retrieval` 记录，无证据卡。

## Hard Rules

1. **先探 key，后选通道。** 调 `assets/scripts/backend_probe.py` 定档（见 `assets/references/source-tiers.md`）。`key` 只探存在性，不读值、不打印、不落盘、不进卡。
2. **后端阶梯从低到高。** `none` → `manual` → `generic` → `firecrawl-advanced`。默认最高用到 `generic`。`firecrawl-advanced` 永不默认、永不静默升级。
3. **`Firecrawl` 只做深爬执行器。** 触发条件三者齐全：`key` 存在、`evidence_backend` 显式选 `firecrawl-advanced`、任务属深爬（多页爬取、批量论文、官方文档核验）。缺任一即回落。
4. **每条证据配可验证标识。** 论文配 `arXiv ID` 或 `DOI`（验过）。官方文档配地址加访问日期。无标识无引用，这条不进卡。
5. **停止规则强制。** 饱和（新查询无新增保留）或预算（查询数、页面数上限）先到即停。停止原因写入 `retrieval.stopped_because`。
6. **等级词不另发明。** 沿用 `SUPPORTED / OPEN / REFUTED`（见 `CONTEXT.md`）。外部文献与计算证据用 `type` 区分（`peer_reviewed`、`official_docs`、`secondary`），等级词一致。

## Build Sequence

### 1. 通道定档——gate

- 调 `assets/scripts/backend_probe.py --task <simple|deep> --out probe.json`。输出 `backend` 即本次档位。
- 无 `key` 直接降级：输出 `OPEN` 空卡加未检索声明，下游继续建模，不 `HOLD` 建模流程。
- **gate**：档位无记录不进检索。带着不明通道进检索等于选错执行器。

### 2. 先判断该不该外部取证

| 情形 | 判定 |
| --- | --- |
| 单条断言需外部支撑（选型依据、邻居站位、求解器版本） | **取证，继续** |
| 要领域演化、定理依赖、开放问题 | 停。用 `arxiv-literature-synthesis` |
| 要引言可引用的缺口表 | 停。用 `literature-review` |
| 计算断言要探针定级 | 停。用 `numerical-verification` |
| 本地文件解析归一 | 停。用 `ingest-inputs` |

### 3. 按档位执行检索抓取

- `manual`：用户自给链接或本地文件。落盘后过 `ingest-inputs` 归一，拿质量报告再进卡。
- `generic`：普通查询与单篇定位。记录查询词、命中数、日期。
- `firecrawl-advanced`：调 `assets/scripts/firecrawl_executor.py` 写请求信封（查询、模式、日期），再经 `Firecrawl` 执行。升级阶梯为 `Search → Scrape → Map/Crawl → Interact`。论文走 `research index`。开发类文档走 `developer index`。本地 `PDF` 不走网页搜索。
- **gate**：查询词与档位先声明。无声明的抓取不进卡。

### 4. 归一成卡并定级——gate

- 每条证据填来源、标识、类型、局限。逐条过 `citation-bibliography` 的可解析性要求（验不过即降级或排除）。
- **gate**：按固定标准定级并附 `retrieval` 记录。证据不足即 `OPEN`，未探方向点名。无 `retrieval` 的卡片拒收。

### 5. 移交

- 要地图 → `arxiv-literature-synthesis`，卡片附上。要缺口表 → `literature-review`，卡片附上。要定级计算 → `numerical-verification`。求解器版本核验结果写清 `name + version`（见 `CONTEXT.md`）。

## Never Ship

收尾自查，不过即拦：

| 禁忌 | 替代 |
| --- | --- |
| 无 key 编网址 | 降级空卡加未检索声明 |
| 回忆包装成检索 | 只写真实抓到的来源 |
| 简单查询走深爬 | 档位从低到高，能低不爬高 |
| 引用无标识 | 逐条 `arXiv ID` 或 `DOI` 验过 |
| 停止原因不写 | `retrieval.stopped_because` 必填 |
| 定理依赖图 | `arxiv-literature-synthesis` |
| 缺口表 | `literature-review` |
| 其他技能直调 `firecrawl_*` | 只允许本技能调，违者打回 |

## Output

交付物是证据卡，顺序如下：

- **断言**——单条原文加提问。
- **证据**——来源、标识、类型、局限逐条。
- **等级**——`SUPPORTED / OPEN / REFUTED` 加理由。
- **retrieval**——后端、查询词、日期、停止原因。
- **移交**——下个技能，卡片附上。

不要写成报告。带追溯的卡片就是交付物。

## Tone

立场鲜明、废话少。当正确答案是“无 key，无检索，这张卡是 OPEN”就写 OPEN。证据撑不起断言时，直说缺哪块，不要拿 `secondary` 网文凑数。
