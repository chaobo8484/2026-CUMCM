# -*- coding: utf-8 -*-
"""Q3 FINAL: C0=8.06 + winsorize 1-99%, pulp equality attempt + day realloc, history same caliber, sens beta/gamma/C0/alpha/pos."""
import pathlib, pandas as pd, numpy as np, pulp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

base = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
s1 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet1"))
s2 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet2"))
s3 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet3"))
r2real = next(f for f in base.rglob("result2.xlsx") if "data_Q2" in str(f))
q3dir = next(d for d in base.rglob("*") if d.is_dir() and d.name == "q3")
data_out = q3dir / "data_Q3"; data_out.mkdir(exist_ok=True)
chart_out = q3dir / "charts_Q3"; chart_out.mkdir(exist_ok=True)

d1 = pd.read_csv(s1, encoding="utf-8-sig"); d2 = pd.read_csv(s2, encoding="utf-8-sig")
d3 = pd.read_csv(s3, encoding="utf-8-sig")
d1["日期"] = pd.to_datetime(d1["日期"]).dt.strftime("%Y-%m-%d")
d2["日期"] = pd.to_datetime(d2["日期"]).dt.strftime("%Y-%m-%d")
r2 = pd.read_excel(r2real)
targets = [f"2025-02-0{d}" for d in range(1, 9)] + [f"2025-08-0{d}" for d in range(1, 9)]

C0_BASE = 8.06
# candidate map
cand_map, cls_of = {}, {}
for _, r in r2.iterrows():
    key = (int(r["方案ID"]), int(r["推广单元"]))
    for c in ["黄金词", "重点词", "潜力词"]:
        if pd.notna(r[c]):
            kw = int(r[c]); cand_map.setdefault(key, {})[kw] = c; cls_of[(key[0], key[1], kw)] = c
g3 = d3.groupby(["方案ID", "推广单元ID", "关键词ID"], as_index=False).agg(C=("消费额", "sum"), K=("点击量", "sum"), V=("浏览量", "sum"))
g3["d"] = np.where(g3["K"] > 0, g3["V"] / g3["K"], 0.0)
unit_hist = d1.groupby(["方案ID", "推广单元ID"], as_index=False).agg(Ks=("点击量", "sum"), Cs=("消费额", "sum"))
unit_hist["qbar"] = np.where(unit_hist["Cs"] > 0, unit_hist["Ks"] / unit_hist["Cs"], 0)
qbar_map = {(int(r["方案ID"]), int(r["推广单元ID"])): float(r["qbar"]) for _, r in unit_hist.iterrows()}
avg_all = float(d1["点击量"].sum() / d1["消费额"].sum())
dayK = d1.groupby("日期", as_index=False).agg(K=("点击量", "sum"), C=("消费额", "sum"))
dayK["q"] = np.where(dayK["C"] > 0, dayK["K"] / dayK["C"], 0)
dayK["theta"] = dayK["q"] / avg_all
reg_map = {r["日期"]: float(r["新注册数"]) for _, r in d2.iterrows()}
dayK["R"] = dayK["日期"].map(reg_map); dayK["rho"] = np.where(dayK["K"] > 0, dayK["R"] / dayK["K"], 0)
theta_map = dict(zip(dayK["日期"], dayK["theta"])); rho_map = dict(zip(dayK["日期"], dayK["rho"]))
bt = d1[d1["日期"].isin(targets)].groupby(["日期", "方案ID", "推广单元ID"], as_index=False).agg(B=("消费额", "sum"), E=("展现量", "sum"), Eup=("上方位展现量", "sum"), Etop=("上方首位展现量", "sum"))
bt["pjt"] = np.where(bt["E"] > 0, (bt["Etop"] + (bt["Eup"] - bt["Etop"]) * 2.5 + (bt["E"] - bt["Eup"]) * 4.0) / bt["E"], np.nan)

def build_static(C0):
    rows = []
    for (sch, unit), kwmap in cand_map.items():
        qbar = qbar_map.get((sch, unit), avg_all)
        sub = g3[(g3["方案ID"] == sch) & (g3["推广单元ID"] == unit)]
        sub = sub[sub["关键词ID"].isin(list(kwmap.keys()))]
        totC = float(sub["C"].sum())
        for _, r in sub.iterrows():
            kw = int(r["关键词ID"]); C = float(r["C"]); K = float(r["K"])
            eta_raw = (K / C) / qbar if C > 0 and qbar > 0 else 0.0
            eta_sm = (C / (C + C0)) * eta_raw + (C0 / (C + C0)) * 1.0 if qbar > 0 else 0.0
            rows.append({"方案ID": sch, "推广单元ID": unit, "关键词ID": kw, "类": kwmap[kw], "C": C, "K": K, "V": float(r["V"]), "d": float(r["d"]), "qbar": qbar, "eta_raw": eta_raw, "eta_sm": eta_sm, "w": (C / totC if totC > 0 else 0.0)})
    st = pd.DataFrame(rows)
    lo, hi = st["eta_sm"].quantile(0.01), st["eta_sm"].quantile(0.99)
    st["eta"] = st["eta_sm"].clip(lo, hi)
    return st, lo, hi

st, lo, hi = build_static(C0_BASE)
st.to_csv(data_out / "static_params_v2.csv", index=False, encoding="utf-8-sig")
eta_desc = st[["eta_raw", "eta_sm", "eta"]].describe()

def solve_day(day, st_, beta=0.15, gamma=1.20):
    units = bt[bt["日期"] == day]; units = units[units["B"] > 0]
    if len(units) == 0: return pd.DataFrame()
    theta = float(theta_map.get(day, 1.0)); rho = float(rho_map.get(day, 0.0))
    prob = pulp.LpProblem(f"Q3_{day}", pulp.LpMaximize)
    vb, vx, co = {}, {}, {}
    for _, u in units.iterrows():
        sch, unit, B = int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"])
        cand = st_[(st_["方案ID"] == sch) & (st_["推广单元ID"] == unit)]
        for _, r in cand.iterrows():
            kw = int(r["关键词ID"]); M = min(float(r["w"]) * B * gamma, 0.3 * B)
            if M < 0.01: continue
            e = float(r["qbar"]) * float(r["eta"]) * theta * rho
            k = (sch, unit, kw)
            b = pulp.LpVariable(f"b_{sch}_{unit}_{kw}", lowBound=0, upBound=M)
            x = pulp.LpVariable(f"x_{sch}_{unit}_{kw}", cat="Binary")
            vb[k] = b; vx[k] = x; co[k] = e
            prob += b <= M * x
    for _, u in units.iterrows():
        sch, unit, B = int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"])
        pl = [vb[k] for k in vb if k[0] == sch and k[1] == unit and cls_of.get((sch, unit, k[2])) == "潜力词"]
        if pl: prob += pulp.lpSum(pl) <= beta * B
    for _, u in units.iterrows():
        sch, unit, B = int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"])
        bl = [vb[k] for k in vb if k[0] == sch and k[1] == unit]
        if bl: prob += pulp.lpSum(bl) <= B + 1e-6
    bykw = defaultdict(list)
    for k in vb: bykw[k[2]].append(vx[k])
    for kw, xs in bykw.items():
        if len(xs) > 1: prob += pulp.lpSum(xs) <= 1
    prob += pulp.lpSum([co[k] * vb[k] for k in vb])
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
    rows = []
    for _, u in units.iterrows():
        sch, unit, B, pjt = int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"]), u["pjt"]
        for k in [kk for kk in vb if kk[0] == sch and kk[1] == unit]:
            bv = pulp.value(vb[k])
            if bv is None: bv = 0
            if bv > 1e-6:
                kw = k[2]
                sr = st_[ (st_["方案ID"] == sch) & (st_["推广单元ID"] == unit) & (st_["关键词ID"] == kw)].iloc[0]
                Kh = float(sr["qbar"]) * float(sr["eta"]) * theta * bv
                rows.append({"日期": day, "方案ID": sch, "推广单元ID": unit, "关键词ID": kw, "类": cls_of[(sch, unit, kw)], "投入金额": bv, "预期展位": float(pjt) if pd.notna(pjt) else np.nan, "预期点击量": Kh, "预期浏览量": float(sr["d"]) * Kh, "预期注册量": rho * Kh, "qbar": float(sr["qbar"]), "eta": float(sr["eta"]), "theta": theta, "rho": rho})
    return pd.DataFrame(rows)

all_rows = [solve_day(d, st) for d in targets]
res = pd.concat([x for x in all_rows if len(x) > 0], ignore_index=True)
# day realloc to 30% cap to reach 100%
realloc = []
for day in targets:
    ud = bt[bt["日期"] == day]; dayB = float(ud["B"].sum())
    spent = float(res[res["日期"] == day]["投入金额"].sum()) if len(res) > 0 else 0.0
    left = dayB - spent
    if left > 1e-6:
        theta = float(theta_map.get(day, 1.0)); rho = float(rho_map.get(day, 1.0))
        cur = res[res["日期"] == day].set_index(["方案ID", "推广单元ID", "关键词ID"])["投入金额"].to_dict() if len(res) > 0 else {}
        sp = defaultdict(float); pot = defaultdict(float)
        for k, v in cur.items(): sp[(k[0], k[1])] += v
        for k, v in cur.items():
            if cls_of.get((k[0], k[1], k[2])) == "潜力词": pot[(k[0], k[1])] += v
        pool = []
        for _, u in ud.iterrows():
            sch, unit, B = int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"])
            if B <= 0: continue
            cand = st[(st["方案ID"] == sch) & (st["推广单元ID"] == unit)]
            for _, r in cand.iterrows():
                kw = int(r["关键词ID"]); k = (sch, unit, kw); curv = cur.get(k, 0.0)
                cap30 = 0.3 * B - curv
                if r["类"] == "潜力词": cap = min(cap30, max(0, 0.15 * B - pot[(sch, unit)]), B - sp[(sch, unit)], left)
                else: cap = min(cap30, B - sp[(sch, unit)], left)
                if cap > 1e-9: pool.append((float(r["qbar"]) * float(r["eta"]) * theta * rho, sch, unit, kw, float(r["qbar"]), float(r["eta"]), float(r["d"]), u["pjt"], cap, r["类"]))
        pool.sort(reverse=True)
        for (_, sch, unit, kw, qb, et, dd, pjt, cap, cls) in pool:
            if left <= 1e-9: break
            take = min(cap, left)
            if take <= 1e-9: continue
            Kh = qb * et * theta * take
            realloc.append({"日期": day, "方案ID": sch, "推广单元ID": unit, "关键词ID": kw, "类": cls, "投入金额": take, "预期展位": float(pjt) if pd.notna(pjt) else np.nan, "预期点击量": Kh, "预期浏览量": dd * Kh, "预期注册量": rho * Kh, "qbar": qb, "eta": et, "theta": theta, "rho": rho})
            left -= take; sp[(sch, unit)] += take
            if cls == "潜力词": pot[(sch, unit)] += take
if realloc:
    res = pd.concat([res, pd.DataFrame(realloc)], ignore_index=True)
    res = res.groupby(["日期", "方案ID", "推广单元ID", "关键词ID", "类", "预期展位", "qbar", "eta", "theta", "rho"], as_index=False).agg(投入金额=("投入金额", "sum"), 预期点击量=("预期点击量", "sum"), 预期浏览量=("预期浏览量", "sum"), 预期注册量=("预期注册量", "sum"))
res.to_csv(data_out / "opt_detail_v2.csv", index=False, encoding="utf-8-sig")
r3 = res[["日期", "方案ID", "推广单元ID", "关键词ID", "投入金额", "预期展位", "预期点击量", "预期浏览量", "预期注册量"]].rename(columns={"推广单元ID": "推广单元", "关键词ID": "关键词"})
r3.to_excel(data_out / "result3.xlsx", index=False)
summ = res.groupby("日期", as_index=False).agg(投入=("投入金额", "sum"), 词数=("关键词ID", "count"), 点击=("预期点击量", "sum"), 浏览=("预期浏览量", "sum"), 注册=("预期注册量", "sum"))
summ = summ.merge(bt.groupby("日期", as_index=False).agg(预算=("B", "sum")), on="日期", how="right").fillna(0)
summ = summ.merge(dayK[["日期", "theta"]], on="日期", how="left")
orig = d1[d1["日期"].isin(targets)].groupby("日期", as_index=False).agg(原消费=("消费额", "sum"), 原点击=("点击量", "sum"))
orig["原注册"] = orig["日期"].map(reg_map)
summ = summ.merge(orig, on="日期", how="left")
summ.to_csv(data_out / "daily_summary_v2.csv", index=False, encoding="utf-8-sig")
# history same caliber
hr = []
for _, u in bt.iterrows():
    day, sch, unit, B = u["日期"], int(u["方案ID"]), int(u["推广单元ID"]), float(u["B"])
    if B <= 0: continue
    cand = st[(st["方案ID"] == sch) & (st["推广单元ID"] == unit)]
    theta = float(theta_map.get(day, 1.0)); rho = float(rho_map.get(day, 0.0))
    for _, r in cand.iterrows():
        bH = B * float(r["w"])
        if bH <= 0: continue
        Kh = float(r["qbar"]) * float(r["eta"]) * theta * bH
        hr.append({"日期": day, "投入H": bH, "点击H": Kh, "注册H": rho * Kh})
hist = pd.DataFrame(hr)
hist_day = hist.groupby("日期", as_index=False).agg(预算=("投入H", "sum"), 历史点击=("点击H", "sum"), 历史注册=("注册H", "sum"))
hist_day["历史成本"] = hist_day["预算"] / hist_day["历史注册"]
opt_day = summ[["日期", "投入", "点击", "注册"]].rename(columns={"投入": "优化投入", "点击": "优化点击", "注册": "优化注册"})
comp = hist_day.merge(opt_day, on="日期", how="outer").fillna(0)
comp["优化成本"] = comp["优化投入"] / comp["优化注册"]
comp["注册提升"] = (comp["优化注册"] - comp["历史注册"]) / comp["历史注册"]
comp.to_csv(data_out / "compare_daily_v2.csv", index=False, encoding="utf-8-sig")
# sensitivity: beta/gamma quick (pulp), C0 quick (rebuild+resolve), alpha note, pos scenarios
sens = []
base_tot = float(res["预期注册量"].sum())
for beta in [0.10, 0.20]:
    t = sum(solve_day(d, st, beta=beta)["预期注册量"].sum() if len(solve_day(d, st, beta=beta)) > 0 else 0 for d in targets)
    sens.append(("beta", beta, t))
sens.append(("beta", 0.15, float(sum(solve_day(d, st)["预期注册量"].sum() if len(solve_day(d, st)) > 0 else 0 for d in targets))))
# NOTE: pulp-only totals exclude realloc; report both
for gamma in [1.10, 1.30]:
    t = sum(solve_day(d, st, gamma=gamma)["预期注册量"].sum() if len(solve_day(d, st, gamma=gamma)) > 0 else 0 for d in targets)
    sens.append(("gamma", gamma, t))
for C0 in [4.03, 16.12, 50.0]:
    stx, _, _ = build_static(C0)
    t = sum(solve_day(d, stx)["预期注册量"].sum() if len(solve_day(d, stx)) > 0 else 0 for d in targets)
    sens.append(("C0", C0, t))
sens_df = pd.DataFrame(sens, columns=["param", "value", "regs_pulp"])
sens_df.to_csv(data_out / "sensitivity_v2.csv", index=False, encoding="utf-8-sig")
# position scenarios
def wpjt(non_top, other):
    df = bt.copy()
    df["p"] = np.where(df["E"] > 0, (df["Etop"] + (df["Eup"] - df["Etop"]) * non_top + (df["E"] - df["Eup"]) * other) / df["E"], np.nan)
    sub = df.dropna(subset=["p"])
    return float((sub["p"] * sub["E"]).sum() / sub["E"].sum()), sub[["日期", "方案ID", "推广单元ID", "p", "E"]]
means = {}
for name, a, b in [("A", 2.0, 3.5), ("base", 2.5, 4.0), ("C", 3.0, 5.0)]:
    m, _ = wpjt(a, b); means[name] = m
_, base_p = wpjt(2.5, 4.0); _, a_p = wpjt(2.0, 3.5); _, c_p = wpjt(3.0, 5.0)
from scipy.stats import spearmanr
bidx = base_p.set_index(["日期", "方案ID", "推广单元ID"])["p"]
aidx = a_p.set_index(["日期", "方案ID", "推广单元ID"])["p"].loc[bidx.index]
cidx = c_p.set_index(["日期", "方案ID", "推广单元ID"])["p"].loc[bidx.index]
sp_a = float(spearmanr(bidx, aidx)[0])
sp_c = float(spearmanr(bidx, cidx)[0])
# charts
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
d = dayK[dayK["日期"].isin(targets)].copy()
fig, ax = plt.subplots(figsize=(10, 4)); ax.bar(d["日期"], d["theta"], color="steelblue"); ax.axhline(1, color="red", linestyle="--"); ax.set_title("theta by date (baseline=1)"); ax.set_xticks(range(len(d))); ax.set_xticklabels(d["日期"], rotation=45, ha="right")
plt.tight_layout(); plt.savefig(chart_out / "fig1_theta.png", dpi=150); plt.close()
c = comp.sort_values("日期"); x = np.arange(len(c)); w = 0.35
fig, ax = plt.subplots(figsize=(10, 4)); ax.bar(x - w / 2, c["历史点击"], width=w, label="history"); ax.bar(x + w / 2, c["优化点击"], width=w, label="opt"); ax.set_xticks(x); ax.set_xticklabels([s[5:] for s in c["日期"]], rotation=45, ha="right"); ax.legend(); ax.set_title("clicks history vs opt (same budget)")
plt.tight_layout(); plt.savefig(chart_out / "fig2_clicks.png", dpi=150); plt.close()
fig, axs = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
axs[0].plot(c["日期"], c["历史点击"], marker="o", label="hist"); axs[0].plot(c["日期"], c["优化点击"], marker="s", label="opt"); axs[0].legend(); axs[0].set_title("clicks")
axs[1].plot(c["日期"], c["历史注册"], marker="o", label="hist"); axs[1].plot(c["日期"], c["优化注册"], marker="s", label="opt"); axs[1].legend(); axs[1].set_title("regs")
axs[2].plot(c["日期"], c["历史成本"], marker="o", label="hist"); axs[2].plot(c["日期"], c["优化成本"], marker="s", label="opt"); axs[2].legend(); axs[2].set_title("cost/reg")
plt.xticks(rotation=45, ha="right"); plt.tight_layout(); plt.savefig(chart_out / "fig3_hist_vs_opt.png", dpi=150); plt.close()
fig, ax = plt.subplots(figsize=(8, 4)); ax.hist(st["eta_raw"], bins=50, alpha=0.5, label="raw"); ax.hist(st["eta"], bins=50, alpha=0.5, label="smooth+win"); ax.legend(); ax.set_title("eta raw vs final C0=8.06 clip " + format(lo, ".3f") + "-" + format(hi, ".3f"))
plt.tight_layout(); plt.savefig(chart_out / "fig_eta_dist.png", dpi=150); plt.close()
L = []
L.append(f"avg={avg_all:.4f} C0=8.06 clip=[{lo:.3f},{hi:.3f}]")
L.append(eta_desc.to_string())
L.append(f"FINAL totalB={comp['预算'].sum():.2f} spent={comp['优化投入'].sum():.2f} rows={len(res)} histC={comp['历史点击'].sum():.1f} optC={comp['优化点击'].sum():.1f} histR={comp['历史注册'].sum():.1f} optR={comp['优化注册'].sum():.1f} lift={(comp['优化注册'].sum()-comp['历史注册'].sum())/comp['历史注册'].sum()*100:.2f}% costH={comp['预算'].sum()/comp['历史注册'].sum():.2f} costO={comp['预算'].sum()/comp['优化注册'].sum():.2f}")
L.append(comp.to_string(index=False)); L.append(sens_df.to_string(index=False))
L.append(f"pos means A/base/C = {means['A']:.3f}/{means['base']:.3f}/{means['C']:.3f} spearman A={sp_a:.3f} C={sp_c:.3f}")
L.append("TOP02-01:"); L.append(res[res["日期"] == "2025-02-01"].sort_values("投入金额", ascending=False).head(5).to_string(index=False))
L.append("TOP08-01:"); L.append(res[res["日期"] == "2025-08-01"].sort_values("投入金额", ascending=False).head(6).to_string(index=False))
pathlib.Path("C:/Users/ZhangChaobo/AppData/Local/Temp/opencode/final_v2.txt").write_text("\n".join(L), encoding="utf-8")
print("DONE_FINAL")
