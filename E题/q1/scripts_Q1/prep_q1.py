# -*- coding: utf-8 -*-
"""Q1预计算：12行单元汇总 + Jaccard矩阵 + 帕累托 + 日序列。输出CSV供各G脚本读取。
规则：CPC/浏览深度先汇总再相除；Top10不足10词记100%并标记；零词不删。"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # E题
ATT = os.path.join(ROOT, "题目", "附件")
HZ = os.path.join(ATT, "附件1_汇总")
CD = os.path.join(ROOT, "clean_data")
OUT = os.path.join(ROOT, "data_Q1")
os.makedirs(OUT, exist_ok=True)

s1_parts, s3_parts = [], []
for f in sorted(os.listdir(HZ)):
    if not (f.endswith(".xlsx") and not f.startswith("~")):
        continue
    a = pd.read_excel(os.path.join(HZ, f), sheet_name="投放日报")
    b = pd.read_excel(os.path.join(HZ, f), sheet_name="关键词")
    s1_parts.append(a)
    s3_parts.append(b)
s1 = pd.concat(s1_parts, ignore_index=True)
s3 = pd.concat(s3_parts, ignore_index=True)
s1["日期"] = pd.to_datetime(s1["日期"])
s2 = pd.read_csv(os.path.join(CD, "sheet2_日注册_clean.csv"))
s2["日期"] = pd.to_datetime(s2["日期"])
dim = pd.read_csv(os.path.join(CD, "dim_date_时间维度.csv"))
dim["日期"] = pd.to_datetime(dim["日期"])

TOTAL_SPEND = s1["消费额"].sum()
rows = []
key_sets = {}
for (pid, uid), d in sorted(s3.groupby(["方案ID", "推广单元ID"]),
                            key=lambda kv: (kv[0][0], kv[0][1])):
    d = d.copy()
    N = len(d)
    active = (d["消费额"] > 0) & (d["点击量"] > 0)
    A = int(active.sum())
    U = A / N
    spend, clk = d["消费额"].sum(), d["点击量"].sum()
    view = d["浏览量"].sum()
    cpc = spend / clk if clk > 0 else np.nan
    depth = view / clk if clk > 0 else np.nan
    qmask = (d["点击量"] > 0) & (d["浏览量"] > 0) & d["跳出率"].notna() \
        & d["平均访问时长(秒)"].notna()
    bounce_med = d.loc[qmask, "跳出率"].median()
    dur_med = d.loc[qmask, "平均访问时长(秒)"].median()
    # Top10（同一批高消费词）
    dspend = d[d["消费额"] > 0].sort_values("消费额", ascending=False)
    Nplus = len(dspend)
    top10 = dspend.head(10)
    full10 = Nplus >= 10
    t10_sp = top10["消费额"].sum() / spend if spend > 0 else np.nan
    t10_ck = top10["点击量"].sum() / clk if clk > 0 else np.nan
    gap = t10_sp - t10_ck
    # HHI（仅消费>0词）
    sh = dspend["消费额"].values / spend
    hhi = float((sh ** 2).sum())
    hhi_s = (hhi - 1 / Nplus) / (1 - 1 / Nplus) if Nplus > 1 else 1.0
    # Sheet1侧
    t = s1[(s1["方案ID"] == pid) & (s1["推广单元ID"] == uid)]
    imp, up_imp, first_imp = t["展现量"].sum(), t["上方位展现量"].sum(), \
        t["上方首位展现量"].sum()
    up_spend = t["上方位消费额"].sum()
    days = t["日期"].nunique()
    bud = spend / TOTAL_SPEND
    # M：单元内消费份额与点击份额分布重合度
    c = d["消费额"].values / spend
    p = d["点击量"].values / clk
    M = float(1 - 0.5 * np.abs(c - p).sum())
    rows.append(dict(方案ID=pid, 推广单元ID=uid, N=N, A=A, 利用率=U, M匹配度=M,
                     总消费=spend, 总点击=clk, CPC=cpc, 总浏览=view,
                     浏览深度=depth, 跳出中位=bounce_med, 时长中位=dur_med,
                     Nplus=Nplus, Top10满10=int(full10),
                     Top10消费占比=t10_sp, Top10点击占比=t10_ck, Gap=gap,
                     HHI=hhi, HHI星=hhi_s, 投放天数=days,
                     上方位展现占比=up_imp / imp, 首位占比=first_imp / imp,
                     上方位消费占比=up_spend / spend, 预算份额=bud))
    key_sets[(pid, uid)] = set(d["关键词"].tolist())

summ = pd.DataFrame(rows).sort_values(["方案ID", "推广单元ID"]).reset_index(drop=True)
# 四象限（中位分界；临界单元在绘图脚本中标注）
U0, M0 = summ["利用率"].median(), summ["M匹配度"].median()


def quad(r):
    if r["利用率"] >= U0 and r["M匹配度"] >= M0:
        return "Ⅰ高利用高匹配"
    if r["利用率"] < U0 and r["M匹配度"] >= M0:
        return "Ⅱ低利用高匹配"
    if r["利用率"] < U0 and r["M匹配度"] < M0:
        return "Ⅲ低利用低匹配"
    return "Ⅳ高利用低匹配"


summ["象限"] = summ.apply(quad, axis=1)
print("U0=", round(U0, 4), "M0=", round(M0, 4))
summ.to_csv(os.path.join(OUT, "q1_unit_summary.csv"), index=False, encoding="utf-8-sig")

# Jaccard 12×12
keys = list(key_sets.keys())
labels = [f"{p}|{u}" for p, u in keys]
jm = pd.DataFrame(np.eye(len(keys)), index=labels, columns=labels)
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        a, b = key_sets[keys[i]], key_sets[keys[j]]
        v = len(a & b) / len(a | b)
        jm.iloc[i, j] = jm.iloc[j, i] = v
jm.to_csv(os.path.join(OUT, "q1_jaccard.csv"), encoding="utf-8-sig")
tri = jm.where(np.triu(np.ones(jm.shape), 1).astype(bool)).stack()
print("Jaccard p75=", round(tri.quantile(0.75), 4), " max=", round(tri.max(), 4))
for (pid, uid) in keys:
    lab = f"{pid}|{uid}"
    others = tri[[i for i in tri.index if lab in i]]
    print(lab, "Jmax=", round(others.max(), 4))

summ["Jmax"] = [tri[[i for i in tri.index if f"{r.方案ID}|{r.推广单元ID}" in i]].max()
                for r in summ.itertuples()]
summ.to_csv(os.path.join(OUT, "q1_unit_summary.csv"), index=False, encoding="utf-8-sig")

# 总体帕累托（关键词去重）
g = s3.groupby("关键词").agg(消费额=("消费额", "sum"), 点击量=("点击量", "sum"))
g = g.sort_values("消费额", ascending=False).reset_index()
g["累计消费占比"] = g["消费额"].cumsum() / g["消费额"].sum()
g["累计点击占比"] = g["点击量"].cumsum() / g["点击量"].sum()
g.to_csv(os.path.join(OUT, "q1_pareto_overall.csv"), index=False, encoding="utf-8-sig")
print("总体Top10=", round(g["消费额"].head(10).sum() / g["消费额"].sum(), 4),
      "Top50=", round(g["消费额"].head(50).sum() / g["消费额"].sum(), 4))

# 重点单元帕累托
for uid in [9657930100, 9811363528, 9630806627]:
    d = s3[s3["推广单元ID"] == uid].sort_values("消费额", ascending=False).reset_index(drop=True)
    d["累计消费占比"] = d["消费额"].cumsum() / d["消费额"].sum()
    d["累计点击占比"] = d["点击量"].cumsum() / d["点击量"].sum()
    d.to_csv(os.path.join(OUT, f"q1_pareto_unit_{uid}.csv"), index=False, encoding="utf-8-sig")

# 日序列
daily = s1.groupby("日期").agg(消费=("消费额", "sum"), 点击=("点击量", "sum"),
                               展现=("展现量", "sum")).reset_index()
daily = daily.merge(s2[["日期", "新注册数"]], on="日期", how="left")
daily["CPA"] = daily["消费"] / daily["新注册数"]
daily["CTR"] = daily["点击"] / daily["展现"]
daily = daily.merge(dim, on="日期", how="left")
daily.to_csv(os.path.join(OUT, "q1_daily.csv"), index=False, encoding="utf-8-sig")

print(summ[["方案ID", "推广单元ID", "N", "A", "利用率", "CPC", "Top10消费占比",
            "Top10点击占比", "Gap", "HHI星", "Jmax"]].round(4).to_string())
print("U中位=", round(summ["利用率"].median(), 4),
      "HHI*中位=", round(summ["HHI星"].median(), 4),
      "CPC中位=", round(summ["CPC"].median(), 4))
