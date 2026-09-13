import pathlib, pandas as pd, numpy as np
base = pathlib.Path(".")
subs = [x for x in base.iterdir() if x.is_dir()]
E = [x for x in subs if (x / "q4").exists()][0]
q4 = E / "q4"; dd = q4 / "data_Q4"
s1 = [f for f in E.rglob("*.csv") if f.name.startswith("sheet1")][0]
d1 = pd.read_csv(s1, encoding="utf-8-sig"); d1["date"] = pd.to_datetime(d1["日期"])
win = pd.date_range("2025-09-11", "2025-09-17")
cal = d1[(d1["date"] >= "2025-08-01") & (d1["date"] <= "2025-10-31")]
cal = cal[~cal["date"].isin(win)].copy(); cal["wd"] = cal["date"].dt.weekday
cal["cpc"] = cal["消费额"] / cal["点击量"].replace(0, np.nan)
cal["ctr"] = cal["点击量"] / cal["展现量"].replace(0, np.nan)
tst = d1[d1["date"].isin(win)].copy(); tst["wd"] = tst["date"].dt.weekday
tst["cpc_a"] = tst["消费额"] / tst["点击量"].replace(0, np.nan)
tst["ctr_a"] = tst["点击量"] / tst["展现量"].replace(0, np.nan)
rows = []
for u in tst["推广单元ID"].unique():
    c = cal[cal["推广单元ID"] == u]; a = tst[tst["推广单元ID"] == u]
    if len(c) == 0 or len(a) == 0: continue
    lc = np.log(c["cpc"].replace(0, np.nan).dropna())
    if len(lc) == 0: continue
    mu = lc.mean()
    woff = {w: np.log(c.loc[c["wd"] == w, "cpc"].replace(0, np.nan).dropna()).mean() - mu
            for w in range(7) if (c["wd"] == w).sum() > 0}
    pa = a[["wd", "cpc_a", "ctr_a"]].copy()
    pa["greg_cpc"] = [float(np.exp(mu + woff.get(w, 0))) for w in pa["wd"]]
    cc = c[(c["ctr"] > 0) & (c["ctr"] < 1)]
    if len(cc) > 0:
        lr = np.log(cc["ctr"] / (1 - cc["ctr"])); mu_r = lr.mean()
        woffr = {w: np.log(cc.loc[cc["wd"] == w, "ctr"] / (1 - cc.loc[cc["wd"] == w, "ctr"])).mean() - mu_r
                 for w in range(7) if (cc["wd"] == w).sum() > 0}
        pa["greg_ctr"] = 1 / (1 + np.exp(-np.array([mu_r + woffr.get(w, 0) for w in pa["wd"]])))
    else:
        pa["greg_ctr"] = np.nan
    rows.append(pa)
pred = pd.concat(rows)
recs = []
for om in [0.3, 0.5, 0.7]:
    d = pred.copy()
    d["cal_cpc"] = om * d["cpc_a"] + (1 - om) * d["greg_cpc"]
    d["ape_cpc"] = (d["cal_cpc"] - d["cpc_a"]).abs() / d["cpc_a"]
    dd2 = d[(d["ctr_a"] > 0) & d["greg_ctr"].notna()].copy()
    dd2["cal_ctr"] = om * dd2["ctr_a"] + (1 - om) * dd2["greg_ctr"]
    dd2["ape_ctr"] = (dd2["cal_ctr"] - dd2["ctr_a"]).abs() / dd2["ctr_a"]
    recs.append(dict(omega=om, mape_cpc=float(d["ape_cpc"].mean()),
                     mape_ctr=float(dd2["ape_ctr"].mean()), n_cpc=int(len(d)), n_ctr=int(len(dd2))))
pd.DataFrame(recs).to_csv(dd / "omega_backtest.csv", index=False, encoding="utf-8-sig")
out = "\n".join("OM %.1f mape_cpc=%.4f mape_ctr=%.4f n=%d/%d" % (
    r["omega"], r["mape_cpc"], r["mape_ctr"], r["n_cpc"], r["n_ctr"]) for r in recs)
pathlib.Path(r"C:\Users\ZhangChaobo\AppData\Local\Temp\opencode\q4_om.txt").write_text(out, encoding="utf-8")
