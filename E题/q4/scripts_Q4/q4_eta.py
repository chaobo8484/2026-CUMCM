import pathlib, pandas as pd, numpy as np
base = pathlib.Path(".")
subs = [x for x in base.iterdir() if x.is_dir()]
E = [x for x in subs if (x / "q4").exists()][0]
q4 = E / "q4"; dd = q4 / "data_Q4"
s3 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet3")][0]
s2 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet2")][0]
d3 = pd.read_csv(s3, encoding="utf-8-sig"); d2 = pd.read_csv(s2, encoding="utf-8-sig")

# --- eta平滑 C0=8.06 → 缩尾[0.210,2.782] → 收缩delta=0.5 ---
C0 = 8.06
g = d3.groupby("推广单元ID")
qbar = g.apply(lambda x: x["点击量"].sum() / x["消费额"].sum(), include_groups=False)
d3["qbar"] = d3["推广单元ID"].map(qbar)
d3["eta_raw"] = (d3["点击量"] / d3["消费额"].replace(0, np.nan)) / d3["qbar"]
# EB平滑：eta = [K + C0*qbar]/[C + C0]/qbar
d3["eta_eb"] = ((d3["点击量"] + C0 * d3["qbar"]) / (d3["消费额"] + C0)) / d3["qbar"]
lo, hi = 0.210, 2.782
d3["eta_win"] = d3["eta_eb"].clip(lo, hi)
for ddlt in [0.3, 0.5, 0.7]:
    d3["eta26_d%.1f" % ddlt] = ddlt * d3["eta_win"] + (1 - ddlt) * 1.0
pos = d3[d3["消费额"] > 0]
print("eta_eb median=%.4f p1=%.4f p99=%.4f | win range=[%.4f,%.4f]" % (
    pos["eta_eb"].median(), pos["eta_eb"].quantile(0.01), pos["eta_eb"].quantile(0.99),
    pos["eta_win"].min(), pos["eta_win"].max()))
# --- 浏览深度平滑 K0=8 ---
K0 = 8
dbar = g.apply(lambda x: x["浏览量"].sum() / x["点击量"].sum(), include_groups=False)
d3["dbar"] = d3["推广单元ID"].map(dbar)
d3["d"] = (d3["浏览量"] + K0 * d3["dbar"]) / (d3["点击量"] + K0)
kp = d3[d3["点击量"] > 0]
print("d median=%.4f" % kp["d"].median())
keep = ["关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量", "qbar",
        "eta_raw", "eta_eb", "eta_win", "eta26_d0.3", "eta26_d0.5", "eta26_d0.7", "dbar", "d"]
keep = [c for c in keep if c in d3.columns]
d3[keep].to_csv(dd / "eta_depth.csv", index=False, encoding="utf-8-sig")

# --- 非负分布滞后 R_t = b0 K_t + b1 K_{t-1} + b2 K_{t-2} ---
d2["date"] = pd.to_datetime(d2["日期"])
d2 = d2.sort_values("date").reset_index(drop=True)
kcol = [c for c in d2.columns if "点击" in c or "click" in c.lower()]
print("sheet2 cols:", list(d2.columns))
