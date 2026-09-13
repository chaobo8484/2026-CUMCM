# 大纲模板：国赛 2026（`template_version: 国赛2026`）

> 用法：复制到工作区，用 `versioned_write.py` 落盘为 `outline_v*.md`。每节按 Claim / Evidence / Link / Budget 四行填；填完按 `paper-outline` 第 3 步 gate 自检。
> 页序铁律（2026 修订稿）：p1 承诺书 → p2 编号页 → p3 摘要（≤1 页）→ p4 起正文（无目录，≤30 页）→ 附录（不限页，打印装订一起交）。电子版第一页必须是摘要页。

## Section: 0 摘要专用页（p3）

**Claim:** [一句话：用什么方法解决什么问题，关键结果数字]

**Evidence:** [正文核心图/表编号，摘要不展开推导]

**Link:** [摘要的每个断言在正文有对应节]

**Budget:** [1 页封顶，含标题和关键词，无需英文]

## Section: 1 问题重述

**Claim:** [赛题目标转述，无新断言]

**Evidence:** [赛题原文 + 数据来源]

**Link:** [引出问题分析的切入点]

**Budget:** [约 1 页]

## Section: 2 问题分析

**Claim:** [总思路一句话：分几个子问题、什么关系]

**Evidence:** [流程图（`diagram-schematic`）]

**Link:** [每个子问题指向模型节]

**Budget:** [约 1–2 页]

## Section: 3 模型假设

**Claim:** [假设清单，每条一句话，可检验]

**Evidence:** [TBD → 无；假设是声明不是证据]

**Link:** [假设支撑模型节的简化]

**Budget:** [约 0.5–1 页]

## Section: 4 符号说明

**Claim:** [符号表完备：文中每个符号有定义、单位]

**Evidence:** [TBD → 通读检查]

**Link:** [符号与模型节公式一致]

**Budget:** [表格，约 0.5 页]

## Section: 5–7 模型建立与求解（按子问题分节）

**Claim:** [本节模型断言，如方法 + 关键结论]

**Evidence:** [公式推导 / 计算代码 / 结果图/表编号，或 TBD → 主技能]

**Link:** [本节输出 feed 下节输入]

**Budget:** [合计约 12–18 页，大头在这里]

## Section: 8 结果分析与检验

**Claim:** [灵敏度/稳定性/对比基线的结论]

**Evidence:** [检验图/表，或 TBD → `numerical-verification`]

**Link:** [检验支撑评价节]

**Budget:** [约 2–3 页]

## Section: 9 模型的评价与推广

**Claim:** [优点/缺点/可推广场景，各一句话]

**Evidence:** [前文结果回指，不新增断言]

**Link:** [收束全文，无新坑]

**Budget:** [约 1 页]

## Section: 10 参考文献

**Claim:** [引用文内全标注，文末规范列出]

**Evidence:** [TBD → `citation-bibliography` 双向检查]

**Link:** [—]

**Budget:** [不计入 30 页正文上限，按 venue 要求排]

## Section: 附录

**Claim:** [支撑材料文件列表 + 全部可运行源程序；无程序则声明“本论文没有用到程序”]

**Evidence:** [TBD → 程序清单 + 运行验证]

**Link:** [—]

**Budget:** [页数不限]
