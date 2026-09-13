# -*- coding: utf-8 -*-
"""Q4 s3 lib: 输入装配 + 周耦合LP. 供 s3/s4/s5 复用.
e_ijt = qbar_j * eta26_ij(delta) * theta_t * RHO(omega)."""
import pathlib
import pandas as pd
import numpy as np
import pulp

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
DD = E / "q4" / "data_Q4"
B = 23488.02


def load_inputs():
    eta = pd.read_csv(DD / "eta_depth.csv", encoding="utf-8-sig")
    fe = pd.read_csv(DD / "fe_pred_2026.csv", encoding="utf-8-sig")
    base = pd.read_csv(DD / "base_budget_0911_17.csv", encoding="utf-8-sig")
    dayh = pd.read_csv(DD / "day_hist.csv", encoding="utf-8-sig")
    uh = pd.read_csv(DD / "unit_hist.csv", encoding="utf-8-sig")
    lag = pd.read_csv(DD / "lag_nnls.csv", encoding="utf-8-sig").iloc[0]
    base["日期"] = pd.to_datetime(base["日期"]).dt.strftime("%Y-%m-%d")
    dayh["日期"] = pd.to_datetime(dayh["日期"]).dt.strftime("%Y-%m-%d")
    dayh["ymd26"] = pd.to_datetime(dayh["日期"]).dt.strftime("2026-%m-%d")
    d1f = pd.read_csv(E / "clean_data" / "sheet1_投放记录_clean.csv", encoding="utf-8-sig")
    uhf = d1f.groupby(["方案ID", "推广单元ID"], as_index=False).agg(
        Ks=("点击量", "sum"), Cs=("消费额", "sum"))
    avg_all = float(d1f["点击量"].sum() / d1f["消费额"].sum())
    qbar_full = {(int(r["方案ID"]), int(r["推广单元ID"])):
                 (float(r["Ks"] / r["Cs"]) if float(r["Cs"]) > 0 else avg_all)
                 for _, r in uhf.iterrows()}
    dayh["day_q"] = dayh["hist_click"] / dayh["hist_cost"]
    dayh["theta"] = dayh["day_q"] / avg_all
    return dict(eta=eta, fe=fe, base=base, dayh=dayh, uh=uh, lag=lag,
                avg_all=avg_all, qbar_full=qbar_full)


def build_cal(inp, omega=0.5):
    base, fe = inp["base"], inp["fe"]
    hist = base.set_index(["日期", "方案ID", "推广单元ID"])
    rows = []
    for _, r in fe.iterrows():
        d26, u, sch = r["日期"], int(r["推广单元ID"]), int(r["方案ID"])
        d25 = "2025-" + d26[5:]
        h = hist.loc[(d25, sch, u)] if (d25, sch, u) in hist.index else None
        cpc_h = float(h["Bjt"] / h["Kjt"]) if h is not None and float(h["Kjt"]) > 0 else np.nan
        ctr_h = float(h["Kjt"] / h["Ejt"]) if h is not None and float(h["Ejt"]) > 0 else np.nan
        cpc_c = float(r["cpc_hat"]) if np.isnan(cpc_h) else omega * cpc_h + (1 - omega) * float(r["cpc_hat"])
        ctr_c = float(r["ctr_hat"]) if np.isnan(ctr_h) else omega * ctr_h + (1 - omega) * float(r["ctr_hat"])
        rows.append(dict(日期=d26, 方案ID=sch, 推广单元ID=u, cpc_cal=cpc_c,
                         ctr_cal=ctr_c, pos_hat=float(r["pos_hat"]),
                         Bjt_hist=float(h["Bjt"]) if h is not None else 0.0))
    return pd.DataFrame(rows)


def rho_hat(inp, omega=0.5):
    dayh, lag = inp["dayh"], inp["lag"]
    obs = float(dayh["hist_reg"].sum() / dayh["hist_click"].sum())
    return omega * float(lag["total"]) + (1 - omega) * obs


def solve_week(inp, cal, RHO, delta=0.5, gamma=1.2, beta=0.15,
               band=0.15, day_cap_mult=1.15, week_total=B, msg=0):
    eta, dayh, uh = inp["eta"], inp["dayh"], inp["uh"]
    qbar_full, avg_all = inp["qbar_full"], inp["avg_all"]
    theta_map = dict(zip(dayh["ymd26"], dayh["theta"]))
    day_cap = {r["ymd26"]: float(r["hist_cost"]) for _, r in dayh.iterrows()}
    unit_week = {(int(r["方案ID"]), int(r["推广单元ID"])): float(r["B_week"])
                 for _, r in uh.iterrows()}
    eta_c = eta.copy()
    eta_c["eta_use"] = delta * eta_c["eta_win"] + (1 - delta) * 1.0
    prob = pulp.LpProblem("Q4_week", pulp.LpMaximize)
    vb, meta, day_keys, unit_keys = {}, {}, {}, {}
    for _, u in cal.iterrows():
        d26, sch, unit = u["日期"], int(u["方案ID"]), int(u["推广单元ID"])
        Bh = float(u["Bjt_hist"])
        theta_t = float(theta_map[d26])
        qb = float(qbar_full.get((sch, unit), avg_all))
        cand = eta_c[(eta_c["方案ID"] == sch) & (eta_c["推广单元ID"] == unit)]
        for _, r in cand.iterrows():
            M = min(float(r["w"]) * Bh * gamma, 0.3 * Bh)
            if M < 0.01 or not np.isfinite(M) or M <= 0:
                continue
            qijt = qb * float(r["eta_use"]) * theta_t
            key = (d26, sch, unit, int(r["关键词ID"]))
            vb[key] = pulp.LpVariable("b_%s_%d_%d_%d" % (d26.replace("-", ""), sch, unit, key[3]),
                                      lowBound=0, upBound=M)
            meta[key] = dict(eta26=float(r["eta_use"]), d=float(r["d"]),
                             类别=str(r["类别"]), M=M, e=qijt * RHO, qijt=qijt,
                             cpc=float(u["cpc_cal"]), ctr=float(u["ctr_cal"]),
                             pos=float(u["pos_hat"]))
            day_keys.setdefault(d26, []).append(key)
            unit_keys.setdefault((sch, unit), []).append(key)
    prob += pulp.lpSum(meta[k]["e"] * vb[k] for k in vb)
    prob += pulp.lpSum(vb[k] for k in vb) == week_total
    for (sch, unit), ks in unit_keys.items():
        Uw = unit_week.get((sch, unit), 0.0)
        if Uw <= 0:
            prob += pulp.lpSum(vb[k] for k in ks) == 0
            continue
        lo = min((1 - band) * Uw, sum(meta[k]["M"] for k in ks) * 0.999)
        prob += pulp.lpSum(vb[k] for k in ks) >= lo - 1e-6
        prob += pulp.lpSum(vb[k] for k in ks) <= (1 + band) * Uw + 1e-6
    for d26, ks in day_keys.items():
        prob += pulp.lpSum(vb[k] for k in ks) <= day_cap_mult * day_cap[d26] + 1e-6
    for d26, ks in day_keys.items():
        pot = [k for k in ks if meta[k]["类别"] == "潜力词"]
        if pot:
            prob += pulp.lpSum(vb[k] for k in pot) <= beta * pulp.lpSum(vb[k] for k in ks) + 1e-9
    prob.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=600))
    status = pulp.LpStatus[prob.status]
    rows = []
    for k in vb:
        v = float(pulp.value(vb[k]))
        if v is None or v <= 1e-6:
            continue
        m = meta[k]
        Kh = v * m["qijt"]
        rows.append(dict(日期=k[0], 方案ID=k[1], 推广单元ID=k[2], 关键词=k[3],
                         类别=m["类别"], 投入金额=v, 预期展位=m["pos"],
                         预期点击量=Kh, 预期浏览量=m["d"] * Kh,
                         预期注册量=RHO * Kh, cpc_cal=m["cpc"],
                         ctr_cal=m["ctr"], eta26=m["eta26"], qijt=m["qijt"]))
    alloc = pd.DataFrame(rows).sort_values(["日期", "方案ID", "推广单元ID", "关键词"])
    return alloc, status
