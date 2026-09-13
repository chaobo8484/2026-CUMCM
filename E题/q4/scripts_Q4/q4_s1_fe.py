# -*- coding: utf-8 -*-
"""Q4 s1: CPC(log)/CTR(logit)/展位(原尺度) 固定效应回归 y=b0+alpha_j+mu_m+nu_w.
估计样本 2025-08-01~10-31 剔除 09-11~17; 预测 2026-09-11~17 逐单元逐日.
月份取9月效应, 零消费单元用全网均值兜底. 输出 fe_pred_2026/fe_resid/omega_backtest."""
import pathlib
import pandas as pd
import numpy as np

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
DD = E / "q4" / "data_Q4"
DD.mkdir(parents=True, exist_ok=True)

d1 = pd.read_csv(E / "clean_data" / "sheet1_投放记录_clean.csv", encoding="utf-8-sig")
d1["日期"] = pd.to_datetime(d1["日期"])
WIN = pd.date_range("2025-09-11", "2025-09-17")
cal = d1[(d1["日期"] >= "2025-08-01") & (d1["日期"] <= "2025-10-31")].copy()
cal = cal[~cal["日期"].isin(WIN)].copy()
cal["wd"] = cal["日期"].dt.weekday
cal["mm"] = cal["日期"].dt.month
cal["cpc"] = cal["消费额"] / cal["点击量"].replace(0, np.nan)
cal["ctr"] = cal["点击量"] / cal["展现量"].replace(0, np.nan)
cal["pos"] = np.where(
    cal["展现量"] > 0,
    (cal["上方首位展现量"] + (cal["上方位展现量"] - cal["上方首位展现量"]) * 2.5
     + (cal["展现量"] - cal["上方位展现量"]) * 4.0) / cal["展现量"], np.nan)


def ols_fe(df, ycol, key_cols=("推广单元ID", "mm", "wd")):
    """y ~ 1 + unit + month + weekday, lstsq. 返回 coef dict 与拟合残差."""
    sub = df[["推广单元ID", "mm", "wd", ycol]].dropna().copy()
    units = sorted(sub["推广单元ID"].unique())
    months = sorted(sub["mm"].unique())
    wds = sorted(sub["wd"].unique())
    u_idx = {u: i for i, u in enumerate(units)}
    m_idx = {m: i for i, m in enumerate(months)}
    w_idx = {w: i for i, w in enumerate(wds)}
    n = len(sub)
    # 约束: 首单元/首月/首星期效应为0 (基准组), 列: const + (U-1) + (M-1) + (W-1)
    U, M, W = len(units), len(months), len(wds)
    p = 1 + (U - 1) + (M - 1) + (W - 1)
    X = np.zeros((n, p))
    X[:, 0] = 1.0
    uu = sub["推广单元ID"].map(u_idx).to_numpy()
    mmv = sub["mm"].map(m_idx).to_numpy()
    ww = sub["wd"].map(w_idx).to_numpy()
    for i in range(n):
        if uu[i] > 0:
            X[i, 1 + uu[i] - 1] = 1.0
        if mmv[i] > 0:
            X[i, 1 + (U - 1) + mmv[i] - 1] = 1.0
        if ww[i] > 0:
            X[i, 1 + (U - 1) + (M - 1) + ww[i] - 1] = 1.0
    y = sub[ycol].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    resid = y - yhat
    info = dict(beta=beta, units=units, months=months, wds=wds,
                U=U, M=M, W=W, resid=resid, yhat=yhat, n=n,
                r2=1 - float(((y - yhat) ** 2).sum()) / float(((y - y.mean()) ** 2).sum()))
    return info, sub


def predict_fe(info, unit, month, wd, glob_fallback):
    beta, units, months, wds = info["beta"], info["units"], info["months"], info["wds"]
    U, M, W = info["U"], info["M"], info["W"]
    if unit not in units:
        return glob_fallback
    x = np.zeros_like(beta)
    x[0] = 1.0
    ui = units.index(unit)
    if ui > 0:
        x[1 + ui - 1] = 1.0
    if month in months:
        mi = months.index(month)
        if mi > 0:
            x[1 + (U - 1) + mi - 1] = 1.0
    else:  # 非估计月份 -> 用9月效应(若9月非基准则对应列)
        if 9 in months:
            mi = months.index(9)
            if mi > 0:
                x[1 + (U - 1) + mi - 1] = 1.0
    if wd in wds:
        wi = wds.index(wd)
        if wi > 0:
            x[1 + (U - 1) + (M - 1) + wi - 1] = 1.0
    return float(x @ beta)


# --- 估计 ---
cal["lcpc"] = np.log(cal["cpc"].replace(0, np.nan))
valid_ctr = cal[(cal["ctr"] > 0) & (cal["ctr"] < 1)].copy()
valid_ctr["lctr"] = np.log(valid_ctr["ctr"] / (1 - valid_ctr["ctr"]))
cal_pos = cal.copy()

info_cpc, sub_cpc = ols_fe(cal, "lcpc")
info_ctr, sub_ctr = ols_fe(valid_ctr, "lctr")
info_pos, sub_pos = ols_fe(cal_pos, "pos")
print("FE n: cpc=%d r2=%.4f | ctr=%d r2=%.4f | pos=%d r2=%.4f" % (
    info_cpc["n"], info_cpc["r2"], info_ctr["n"], info_ctr["r2"],
    info_pos["n"], info_pos["r2"]))

# 残差存档 (供Bootstrap)
resid = pd.DataFrame({
    "resid_lcpc": pd.Series(info_cpc["resid"]),
    "resid_lctr": pd.Series(info_ctr["resid"]),
    "resid_pos": pd.Series(info_pos["resid"]),
})
resid.to_csv(DD / "fe_resid.csv", index=False, encoding="utf-8-sig")

# --- 预测 2026-09-11~17 (月份效应取9月) ---
units_win = sorted(d1[d1["日期"].isin(WIN)]["推广单元ID"].unique())
sch_of = d1.drop_duplicates("推广单元ID").set_index("推广单元ID")["方案ID"].to_dict()
dates26 = pd.date_range("2026-09-11", "2026-09-17")
g_lcpc = float(np.nanmean(info_cpc["yhat"]))
g_lctr = float(np.nanmean(info_ctr["yhat"]))
g_pos = float(np.nanmean(info_pos["yhat"]))
rows = []
for u in units_win:
    for dt in dates26:
        wd = int(dt.weekday())
        lc = predict_fe(info_cpc, u, 9, wd, g_lcpc)
        lr = predict_fe(info_ctr, u, 9, wd, g_lctr)
        ps = predict_fe(info_pos, u, 9, wd, g_pos)
        rows.append(dict(日期=dt.strftime("%Y-%m-%d"), 方案ID=int(sch_of[u]),
                         推广单元ID=int(u), wd=wd,
                         cpc_hat=float(np.exp(lc)),
                         ctr_hat=float(1 / (1 + np.exp(-lr))),
                         pos_hat=float(ps)))
pred = pd.DataFrame(rows)
pred.to_csv(DD / "fe_pred_2026.csv", index=False, encoding="utf-8-sig")

# --- omega回测 (沿用q4_p0口径: 单元均值+星期偏移greg, cal=om*actual+(1-om)*greg) ---
tst = d1[d1["日期"].isin(WIN)].copy()
tst["wd"] = tst["日期"].dt.weekday
tst["cpc_a"] = tst["消费额"] / tst["点击量"].replace(0, np.nan)
tst["ctr_a"] = tst["点击量"] / tst["展现量"].replace(0, np.nan)
greg_rows = []
for u in units_win:
    c = cal[cal["推广单元ID"] == u]
    a = tst[tst["推广单元ID"] == u]
    if len(c) == 0 or len(a) == 0:
        continue
    lc = np.log(c["cpc"].replace(0, np.nan).dropna())
    if len(lc) == 0:
        continue
    mu = lc.mean()
    woff = {w: np.log(c.loc[c["wd"] == w, "cpc"].replace(0, np.nan).dropna()).mean() - mu
            for w in range(7) if (c["wd"] == w).sum() > 0}
    pa = a[["wd", "cpc_a", "ctr_a"]].copy()
    pa["greg_cpc"] = [float(np.exp(mu + woff.get(w, 0))) for w in pa["wd"]]
    cc = c[(c["ctr"] > 0) & (c["ctr"] < 1)]
    if len(cc) > 0:
        lr = np.log(cc["ctr"] / (1 - cc["ctr"]))
        mu_r = lr.mean()
        woffr = {w: np.log(cc.loc[cc["wd"] == w, "ctr"] / (1 - cc.loc[cc["wd"] == w, "ctr"])).mean() - mu_r
                 for w in range(7) if (cc["wd"] == w).sum() > 0}
        pa["greg_ctr"] = 1 / (1 + np.exp(-np.array([mu_r + woffr.get(w, 0) for w in pa["wd"]])))
    else:
        pa["greg_ctr"] = np.nan
    greg_rows.append(pa)
greg = pd.concat(greg_rows)
recs = []
for om in [0.3, 0.5, 0.7]:
    g = greg.copy()
    g["cal_cpc"] = om * g["cpc_a"] + (1 - om) * g["greg_cpc"]
    g["ape_cpc"] = (g["cal_cpc"] - g["cpc_a"]).abs() / g["cpc_a"]
    g2 = g[(g["ctr_a"] > 0) & g["greg_ctr"].notna()].copy()
    g2["cal_ctr"] = om * g2["ctr_a"] + (1 - om) * g2["greg_ctr"]
    g2["ape_ctr"] = (g2["cal_ctr"] - g2["ctr_a"]).abs() / g2["ctr_a"]
    recs.append(dict(omega=om, mape_cpc=float(g["ape_cpc"].mean()),
                     mape_ctr=float(g2["ape_ctr"].mean()),
                     n_cpc=int(len(g)), n_ctr=int(len(g2))))
pd.DataFrame(recs).to_csv(DD / "omega_backtest.csv", index=False, encoding="utf-8-sig")
print("S1 OK pred_rows=%d" % len(pred))
for r in recs:
    print("OM %.1f mape_cpc=%.4f mape_ctr=%.4f n=%d/%d" % (
        r["omega"], r["mape_cpc"], r["mape_ctr"], r["n_cpc"], r["n_ctr"]))
print("cpc_hat mean=%.4f ctr_hat mean=%.5f pos_hat mean=%.3f" % (
    pred["cpc_hat"].mean(), pred["ctr_hat"].mean(), pred["pos_hat"].mean()))
