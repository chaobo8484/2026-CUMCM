# -*- coding: utf-8 -*-
"""Q4 s2: eta EB平滑(C0=8.06,缩尾[0.210,2.782],delta=0.5收缩) + 浏览深度(K0=8)
+ 非负分布滞后NNLS + delta延续率回测. 输出 eta_depth/lag_nnls/lag_fit/delta_*.csv"""
import pathlib
import pandas as pd
import numpy as np
from scipy.optimize import nnls

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
DD = E / "q4" / "data_Q4"
DD.mkdir(parents=True, exist_ok=True)

C0, K0, DELTA = 8.06, 8, 0.5
LO, HI = 0.210, 2.782

d1 = pd.read_csv(E / "clean_data" / "sheet1_投放记录_clean.csv", encoding="utf-8-sig")
d2 = pd.read_csv(E / "clean_data" / "sheet2_日注册_clean.csv", encoding="utf-8-sig")
d3 = pd.read_csv(E / "clean_data" / "sheet3_关键词_clean.csv", encoding="utf-8-sig")
d1["日期"] = pd.to_datetime(d1["日期"])
d2["日期"] = pd.to_datetime(d2["日期"])

# --- 候选集: Q2基准类别 黄金/重点/潜力 (兼容带/不带"词"后缀) ---
q2rec = pd.read_csv(E / "q2" / "data_Q2" / "q2_record_clean.csv", encoding="utf-8-sig")
catcol = "基准类别"
cats = set(q2rec[catcol].dropna().unique())
keep_cats = [c for c in cats if c in ("黄金词", "重点词", "潜力词", "黄金", "重点", "潜力")]
norm = {"黄金": "黄金词", "重点": "重点词", "潜力": "潜力词",
        "黄金词": "黄金词", "重点词": "重点词", "潜力词": "潜力词"}
q2rec["cat_norm"] = q2rec[catcol].map(norm)
cand = q2rec[q2rec["cat_norm"].isin(("黄金词", "重点词", "潜力词"))].copy()
print("Q2 cats:", sorted(map(str, cats)), "| cand rows:", len(cand))
# 连接键 (方案ID,推广单元ID,关键词): q2_record_clean.关键词 == sheet3.关键词ID
key_cand = set(zip(cand["方案ID"].astype(int), cand["推广单元ID"].astype(int),
                   cand["关键词"].astype(int)))

# --- qbar: 全年单元点击/消费 (sheet1), avg_all兜底 ---
uh = d1.groupby(["方案ID", "推广单元ID"], as_index=False).agg(
    Ks=("点击量", "sum"), Cs=("消费额", "sum"))
uh["qbar"] = np.where(uh["Cs"] > 0, uh["Ks"] / uh["Cs"], np.nan)
avg_all = float(d1["点击量"].sum() / d1["消费额"].sum())
qbar_map = {(int(r["方案ID"]), int(r["推广单元ID"])): float(r["qbar"])
            for _, r in uh.iterrows()}

# --- g3: sheet3按(方案,单元,词)聚合 ---
g3 = d3.groupby(["方案ID", "推广单元ID", "关键词ID"], as_index=False).agg(
    C=("消费额", "sum"), K=("点击量", "sum"), V=("浏览量", "sum"))
g3["in_cand"] = [((int(a), int(b), int(c)) in key_cand)
                 for a, b, c in zip(g3["方案ID"], g3["推广单元ID"], g3["关键词ID"])]
g3c = g3[g3["in_cand"]].copy()
g3c["qbar"] = [qbar_map.get((int(a), int(b)), avg_all)
               for a, b in zip(g3c["方案ID"], g3c["推广单元ID"])]
g3c["eta_raw"] = (g3c["K"] / g3c["C"].replace(0, np.nan)) / g3c["qbar"]
g3c["eta_eb"] = ((g3c["K"] + C0 * g3c["qbar"]) / (g3c["C"] + C0)) / g3c["qbar"]
g3c["eta_win"] = g3c["eta_eb"].clip(LO, HI)
for dl in [0.3, 0.5, 0.7]:
    g3c["eta26_d%.1f" % dl] = dl * g3c["eta_win"] + (1 - dl) * 1.0
g3c["eta26"] = g3c["eta26_d0.5"]
print("cand_kw=%d eta_eb med=%.4f p1=%.4f p99=%.4f" % (
    len(g3c), g3c["eta_eb"].median(),
    g3c["eta_eb"].quantile(0.01), g3c["eta_eb"].quantile(0.99)))

# --- 浏览深度 K0=8 ---
gg = d3.groupby("推广单元ID")
dbar = gg.apply(lambda x: x["浏览量"].sum() / x["点击量"].sum()
                if x["点击量"].sum() > 0 else np.nan, include_groups=False)
g3c["dbar"] = g3c["推广单元ID"].map(dbar)
g3c["d"] = (g3c["V"] + K0 * g3c["dbar"]) / (g3c["K"] + K0)
# 类别 + 单元内历史消费份额w
cls_map = {(int(r["方案ID"]), int(r["推广单元ID"]), int(r["关键词"])): r["cat_norm"]
           for _, r in cand.iterrows()}
g3c["类别"] = [(cls_map.get((int(a), int(b), int(c)), "")) for a, b, c in
               zip(g3c["方案ID"], g3c["推广单元ID"], g3c["关键词ID"])]
totC = g3c.groupby(["方案ID", "推广单元ID"])["C"].transform("sum")
g3c["w"] = np.where(totC > 0, g3c["C"] / totC, 0.0)
g3c.to_csv(DD / "eta_depth.csv", index=False, encoding="utf-8-sig")

# --- 非负分布滞后 R_t=b0 K_t+b1 K_{t-1}+b2 K_{t-2} (NNLS, 全网日) ---
K = d1.groupby("日期", as_index=False).agg(K=("点击量", "sum"))
m = pd.merge(d2[["日期", "新注册数"]], K, on="日期").sort_values("日期").reset_index(drop=True)
m["K1"] = m["K"].shift(1)
m["K2"] = m["K"].shift(2)
mm = m.dropna().reset_index(drop=True)
X = mm[["K", "K1", "K2"]].to_numpy()
y = mm["新注册数"].to_numpy()
beta, _ = nnls(X, y)
yhat = X @ beta
r2 = 1 - float(((y - yhat) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
res = dict(b0=float(beta[0]), b1=float(beta[1]), b2=float(beta[2]),
           total=float(beta.sum()), R2=float(r2), n=int(len(mm)))
pd.DataFrame([res]).to_csv(DD / "lag_nnls.csv", index=False, encoding="utf-8-sig")
mm.assign(Rhat=yhat).to_csv(DD / "lag_fit.csv", index=False, encoding="utf-8-sig")
print("LAG b0=%.4f b1=%.4f b2=%.4f total=%.4f R2=%.4f n=%d" % (
    res["b0"], res["b1"], res["b2"], res["total"], res["R2"], res["n"]))

# --- delta延续率: H1(1-6月)vsH2(7-12月)单元q自回归 ---
d1m = d1.copy()
d1m["m"] = d1m["日期"].dt.month
h1 = d1m[d1m["m"] <= 6].groupby("推广单元ID", as_index=False).agg(
    C=("消费额", "sum"), K=("点击量", "sum"))
h2 = d1m[d1m["m"] >= 7].groupby("推广单元ID", as_index=False).agg(
    C=("消费额", "sum"), K=("点击量", "sum"))
mg = pd.merge(h1, h2, on="推广单元ID", suffixes=("_h1", "_h2"))
mg["q_h1"] = mg["K_h1"] / mg["C_h1"]
mg["q_h2"] = mg["K_h2"] / mg["C_h2"]
mg = mg.replace([np.inf, -np.inf], np.nan).dropna()
A = np.vstack([mg["q_h1"].to_numpy(), np.ones(len(mg))]).T
slope, itc = np.linalg.lstsq(A, mg["q_h2"].to_numpy(), rcond=None)[0]
corr = float(np.corrcoef(mg["q_h1"], mg["q_h2"])[0, 1])
mg.to_csv(DD / "delta_unit_q_h1h2.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([dict(slope=float(slope), intercept=float(itc),
                   corr=corr, n=int(len(mg)))]).to_csv(
    DD / "delta_backtest.csv", index=False, encoding="utf-8-sig")
print("DELTA slope=%.4f itc=%.4f corr=%.4f n=%d" % (slope, itc, corr, len(mg)))
print("S2 OK")
