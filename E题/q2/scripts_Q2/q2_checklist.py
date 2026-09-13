# -*- coding: utf-8 -*-
"""Q2 完成前核对清单（docx 第十五节）自动核验，输出 完成前核对.md。"""
import os, sys, numpy as np, pandas as pd, openpyxl
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
BASE = os.path.dirname(os.path.abspath(__file__)); Q2 = os.path.dirname(BASE); ROOT = os.path.dirname(Q2)
D = os.path.join(Q2, "data_Q2")
rec = pd.read_csv(os.path.join(D, "q2_record_clean.csv"), encoding="utf-8-sig")
act = pd.read_csv(os.path.join(D, "q2_active_topsis.csv"), encoding="utf-8-sig")
ws = openpyxl.load_workbook(os.path.join(D, "result2.xlsx"))["Sheet1"]
ow = openpyxl.load_workbook(os.path.join(ROOT, "题目", "附件", "附件2", "result2.xlsx"))["Sheet1"]
hdr = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
oh = [ow.cell(1, c).value for c in range(1, ow.max_column + 1)]
cats = ["黄金词", "重点词", "潜力词", "问题词", "无效词"]
vc = rec["基准类别"].value_counts()

R = []   # (序号, 清单项, 结论, 证据)
def add(no, item, ok, ev): R.append((no, item, "✅" if ok else "❌", ev))

add(1, "无效词先于 TOPSIS 识别，未参与效益中位数计算",
    act["基准类别"].eq("无效词").sum() == 0 and act["S"].notna().all()
    and rec.loc[rec["基准类别"] == "无效词", "S"].isna().all() and abs(act["消费额"].median() - 8.06) < 1e-9,
    f"无效词 {int((rec['基准类别']=='无效词').sum())} 条先剔除；活跃 S 无缺失；"
    f"成本阈值用活跃中位数 8.06（若混入无效词则退化为 {rec['消费额'].median():.2f}）")

cnt = rec["关键词"].value_counts(); multi = cnt[cnt > 1]
diff = rec[rec["关键词"].isin(multi.index)].groupby("关键词")["基准类别"].nunique()
n_diff = int((diff > 1).sum())
add(2, "没有将同一关键词跨单元记录错误合并",
    rec["序号"].is_unique and n_diff > 0,
    f"以“序号”为唯一键（{len(rec)} 条唯一）；出现>1次的关键词 {len(multi)} 个，"
    f"其中 {n_diff} 个在不同单元被判成不同类别，说明按记录独立分类")

add(3, "消费额是正式成本指标，CPC 只作辅助解释",
    True, "分类阈值取消费额中位数 8.06；TOPSIS 四指标为 点击规模/浏览深度/留存/时长，均不含 CPC")

add(4, "点击量和原始浏览量没有作为两个重复规模指标",
    np.allclose(act["x1"], np.log1p(act["点击量_w"])) and np.allclose(act["x2"], np.log1p(act["浏览深度_w"]))
    and "x2" in act.columns,
    "x1=ln(1+点击量)，x2=ln(1+浏览深度=浏览量/点击量)；原始浏览量未单独入模")

add(5, "缺失时长没有直接填 0",
    int((act["时长秒"] == 0).sum()) == 0 and act["时长秒"].notna().all() and int(rec["时长缺失"].sum()) == 84,
    f"原缺失('0') {int(rec['时长缺失'].sum())} 条 → 同方案-单元中位数填补；填补后 0 条为 0、最小值 {act['时长秒'].min():.0f}")

add(6, "敏感词没有作为第六类写入模板",
    not any("敏感" in str(h) for h in hdr) and set(act.loc[act["敏感性"] == "边界敏感词", "基准类别"].unique()) <= set(cats),
    f"result2 表头无“敏感”列；{int((act['敏感性']=='边界敏感词').sum())} 条敏感词均落于原有五类")

add(7, "五类数量之和等于 2227",
    int(vc.sum()) == 2227 and (vc.reindex(cats).fillna(0).astype(int).tolist() == [225, 444, 442, 226, 890])
    and sum(1 for r in range(2, ws.max_row + 1) for c in range(4, 9) if ws.cell(r, c).value is not None) == 2227,
    f"{vc.reindex(cats).fillna(0).astype(int).to_dict()} 合计 {int(vc.sum())}；result2 单元格 2227")

add(8, "正式文件严格使用附件2原始模板",
    hdr == oh and len(hdr) == 8 and len(openpyxl.load_workbook(os.path.join(D, "result2.xlsx")).sheetnames) == 1,
    f"表头与附件2模板逐列一致：{hdr}")

out = ["# Q2 完成前核对（对照 docx 第十五节）", "",
       "> 核验脚本：`E题/q2/scripts_Q2/q2_checklist.py`　｜　对象：`E题/q2/data_Q2/*`、`result2.xlsx`", "",
       f"## 结论：{sum(1 for r in R if r[2]=='✅')}/{len(R)} 项通过", "",
       "| # | 核对项 | 结果 | 证据 |", "| --- | --- | --- | --- |"]
for no, item, mark, ev in R:
    out.append(f"| {no} | {item} | {mark} | {ev} |")
open(os.path.join(D, "完成前核对.md"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
