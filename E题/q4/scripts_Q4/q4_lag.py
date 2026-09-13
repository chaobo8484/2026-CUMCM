import pathlib, pandas as pd, numpy as np
from scipy.optimize import nnls
base = pathlib.Path(".")
subs = [x for x in base.iterdir() if x.is_dir()]
E = [x for x in subs if (x / "q4").exists()][0]
q4 = E / "q4"; dd = q4 / "data_Q4"
s1 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet1")][0]
s2 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet2")][0]
d1 = pd.read_csv(s1, encoding="utf-8-sig"); d2 = pd.read_csv(s2, encoding="utf-8-sig")
d1["date"] = pd.to_datetime(d1["日期"]); d2["date"] = pd.to_datetime(d2["日期"])
K = d1.groupby("date", as_index=False).agg(K=("点击量", "sum"))
m = pd.merge(d2[["date", "新注册数"]], K, on="date").sort_values("date").reset_index(drop=True)
m["K1"] = m["K"].shift(1); m["K2"] = m["K"].shift(2)
mm = m.dropna().reset_index(drop=True)
X = mm[["K", "K1", "K2"]].values; y = mm["新注册数"].values
beta, rnorm = nnls(X, y)
yhat = X @ beta
ss = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
res = dict(b0=float(beta[0]), b1=float(beta[1]), b2=float(beta[2]),
           total=float(beta.sum()), R2=float(ss), n=int(len(mm)))
pd.DataFrame([res]).to_csv(dd / "lag_nnls.csv", index=False, encoding="utf-8-sig")
mm.assign(Rhat=yhat).to_csv(dd / "lag_fit.csv", index=False, encoding="utf-8-sig")
out = ["LAG b0=%.4f b1=%.4f b2=%.4f total=%.4f R2=%.4f n=%d" % (
    res["b0"], res["b1"], res["b2"], res["total"], res["R2"], res["n"])]
# eta分位复核：不同口径
s3 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet3")][0]
d3 = pd.read_csv(s3, encoding="utf-8-sig")
C0 = 8.06
qbar = d3.groupby("推广单元ID").apply(lambda x: x["点击量"].sum() / x["消费额"].sum(), include_groups=False)
d3["qb"] = d3["推广单元ID"].map(qbar)
d3["eta"] = ((d3["点击量"] + C0 * d3["qb"]) / (d3["消费额"] + C0)) / d3["qb"]
for name, f in [("all", d3["eta"]), ("posC", d3.loc[d3["消费额"] > 0, "eta"]),
                ("posK", d3.loc[d3["点击量"] > 0, "eta"])]:
    v = f.replace([np.inf, -np.inf], np.nan).dropna()
    out.append("ETA %s n=%d p1=%.4f p99=%.4f med=%.4f" % (name, len(v), v.quantile(0.01), v.quantile(0.99), v.median()))
pathlib.Path(r"C:\Users\ZhangChaobo\AppData\Local\Temp\opencode\q4_lag.txt").write_text("\n".join(out), encoding="utf-8")
