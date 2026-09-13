# 来源阶梯与执行器选用（research-evidence）

> `skills/research-evidence/SKILL.md` Build Sequence 0–2 的引用展开。档位从低到高，能低不爬高。

## 后端阶梯

| 档位 | 含义 | 适用 | 成本 |
|---|---|---|---|
| `none` | 无外部检索 | 无 key、无网、纯本地任务 | 零 |
| `manual` | 用户自给链接或文件 | 用户已给出来源，只需抓取归一 | 低 |
| `generic` | 模型或 MCP 自带通用搜索 | 普通查询、单篇论文定位 | 中 |
| `firecrawl-advanced` | `Firecrawl` 深爬 | 多页爬取、批量论文、官方文档核验 | 高，需 key |

`firecrawl-advanced` 准入三者齐全：`key` 存在、`evidence_backend` 显式选中、任务属深爬。缺任一即回落到 `generic` 或更低。

## Firecrawl 升级阶梯

`Search → Scrape → Map/Crawl → Interact`。按需逐级升级，不跳级。

| 场景 | 入口 |
|---|---|
| 普通网页研究 | `search` 加 `scrape` |
| 研究论文 | `research index` |
| 开发类问题（求解器、包文档） | `developer index` |
| 本地 `PDF` 或已落盘文档 | 不走网页搜索，走 `ingest-inputs` 解析 |

## 停止规则

饱和（新查询无新增保留）或预算（查询数、页面数上限，先定后跑）先到即停。停止原因写入 `retrieval.stopped_because`，可选值：`saturated`、`budget`、`no-backend`、`no-key`。

## 密钥约定

- 环境变量名默认 `FIRECRAWL_API_KEY`。脚本只探存在性，不读值、不打印、不落盘。
- 仓内只记来源（`env:FIRECRAWL_API_KEY`），永不记值。证据卡与复现日志只记后端名加日期。
