import pathlib, pandas as pd, numpy as np
base = pathlib.Path(".")
subs = [x for x in base.iterdir() if x.is_dir()]
E = [x for x in subs if (x / "q4").exists()][0]
q4 = E / "q4"
dd = q4 / "data_Q4"
dd.mkdir(exist_ok=True)

def find(pat, sub=None):
    root = E if sub is None else sub
    fs = [f for f in root.rglob(pat) if "~$" not in f.name]
    return fs

s1 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet1")][0]
s2 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet2")][0]
s3 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet3")][0]
d1 = pd.read_csv(s1, encoding="utf-8-sig"); d2 = pd.read_csv(s2, encoding="utf-8-sig"); d3 = pd.read_csv(s3, encoding="utf-8-sig")
d1["date"] = pd.to_datetime(d1["日期"]); d2["date"] = pd.to_datetime(d2["日期"])

# 1. 基数复核：2025-09-11~17
win = pd.date_range("2025-09-11", "2025-09-17")
sub = d1[d1["date"].isin(win)].copy()
unit = sub.groupby(["方案ID", "推广单元ID"], as_index=False).agg(
    Bjt=("消费额", "sum"), Kjt=("点击量", "sum"), Ejt=("展现量", "sum"))
unit["qjt"] = unit["Kjt"] / unit["Bjt"].replace(0, np.nan)
unit.to_csv(dd / "base_budget_0911_17.csv", index=False, encoding="utf-8-sig")
reg = d2[d2["date"].isin(win)]
tot = dict(cost=float(sub["消费额"].sum()), clicks=float(sub["点击量"].sum()),
           impr=float(sub["展现量"].sum()), regs=float(reg["新注册数"].sum()),
           fullyear=float(d1["消费额"].sum()))
pd.DataFrame([tot]).to_csv(dd / "base_totals.csv", index=False, encoding="utf-8-sig")

# 2. omega回测：以单元+月份+星期固定效应（排除目标周估计）预测当周，再与实际比较
# 简化：用目标周之外的2025年8-10月数据估计单元均值+星期效应（对数尺度CPC、Logit尺度CTR、原尺度展位）
cal = d1[(d1["date"] >= "2025-08-01") & (d1["date"] <= "2025-10-31")].copy()
cal = cal[~cal["date"].isin(win)]
cal["wd"] = cal["date"].dt.weekday
cal["cpc"] = cal["消费额"] / cal["点击量"].replace(0, np.nan)
cal["ctr"] = cal["点击量"] / cal["展现量"].replace(0, np.nan)
cal["pos"] = cal.get("平均展现位", cal.get("展现位", None))
tst = sub.copy(); tst["wd"] = tst["date"].dt.weekday
tst["cpc_a"] = tst["消费额"] / tst["点击量"].replace(0, np.nan)
tst["ctr_a"] = tst["点击量"] / tst["展现量"].replace(0, np.nan)
rows = []
uids = tst["推广单元ID"].unique()
for u in uids:
    c = cal[cal["推广单元ID"] == u]; a = tst[tst["推广单元ID"] == u]
    if len(c) == 0 or len(a) == 0:
        continue
    # CPC log尺度：单元均值+星期偏移
    lc = np.log(c["cpc"].replace(0, np.nan).dropna())
    if len(lc) == 0: continue
    mu = lc.mean()
    woff = {w: np.log(c.loc[c["wd"] == w, "cpc"].replace(0, np.nan).dropna()).mean() - mu
            for w in range(7) if (c["wd"] == w).sum() > 0}
    pa = a[["wd", "cpc_a", "ctr_a"]].copy()
    pa["greg_cpc"] = [float(np.exp(mu + woff.get(w, 0))) for w in pa["wd"]]
    # CTR logit尺度
    cc = c[(c["ctr"] > 0) & (c["ctr"] < 1)]
    if len(cc) > 0:
        lr = np.log(cc["ctr"] / (1 - cc["ctr"])); mu_r = lr.mean()
        woffr = {}
        for w in range(7):
            s = cc[cc["wd"] == w]
            if len(s) > 0:
                v = np.log(s["ctr"] / (1 - s["ctr"])).mean() - mu_r
                woffr[w] = v
        lr_pred = np.array([mu_r + woffr.get(w, 0) for w in pa["wd"]])
        pa["greg_ctr"] = 1 / (1 + np.exp(-lr_pred))
    else:
        pa["greg_ctr"] = np.nan
    pa["unit"] = u
    rows.append(pa)
pred = pd.concat(rows)
recs = []
for om in [0.3, 0.5, 0.7]:
    d = pred.copy()
    d["cal_cpc"] = om * d["cpc_a"] + (1 - om) * d["greg_cpc"]
    d["ape_cpc"] = (d["cal_cpc"] - d["cpc_a"]).abs() / d["cpc_a"]
    dd2 = d.dropna(subset=["greg_ctr", "ctr_a"])
    dd2["cal_ctr"] = om * dd2["ctr_a"] + (1 - om) * dd2["greg_ctr"]
    dd2["ape_ctr"] = (dd2["cal_ctr"] - dd2["ctr_a"]).abs() / dd2["ctr_a"]
    recs.append(dict(omega=om, mape_cpc=float(d["ape_cpc"].mean()),
                     mape_ctr=float(dd2["ape_ctr"].mean()), n=int(len(d))))
pd.DataFrame(recs).to_csv(dd / "omega_backtest.csv", index=False, encoding="utf-8-sig")

# 3. delta延续率：H1(1-6月)消费/点击→eta_raw，按单元qbar相对效率；H2(7-12月)同样；回归斜率即延续率
d3c = d3.copy()
# Sheet3是全年汇总无月份；改用Sheet1按单元聚合H1/H2的q做延续率代理：单元q的H1→H2自回归
d1m = d1.copy(); d1m["m"] = d1m["date"].dt.month
h1 = d1m[d1m["m"] <= 6].groupby("推广单元ID", as_index=False).agg(C=("消费额", "sum"), K=("点击量", "sum"))
h2 = d1m[d1m["m"] >= 7].groupby("推广单元ID", as_index=False).agg(C=("消费额", "sum"), K=("点击量", "sum"))
m = pd.merge(h1, h2, on="推广单元ID", suffixes=("_h1", "_h2"))
m["q_h1"] = m["K_h1"] / m["C_h1"]; m["q_h2"] = m["K_h2"] / m["C_h2"]
m = m.replace([np.inf, -np.inf], np.nan).dropna()
x = m["q_h1"].values; y = m["q_h2"].values
A = np.vstack([x, np.ones_like(x)]).T
slope, itc = np.linalg.lstsq(A, y, rcond=None)[0]
corr = float(np.corrcoef(x, y)[0, 1])
m.to_csv(dd / "delta_unit_q_h1h2.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([dict(slope=float(slope), intercept=float(itc), corr=corr, n=int(len(m)))]).to_csv(
    dd / "delta_backtest.csv", index=False, encoding="utf-8-sig")
print("OK", tot, recs, slope, corr)
