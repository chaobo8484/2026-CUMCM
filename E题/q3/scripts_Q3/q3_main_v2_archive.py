# -*- coding: utf-8 -*-
"""Q3 main: params + MILP(pulp) + history baseline + sensitivity. ASCII-path safe."""
import pathlib, pandas as pd, numpy as np
import pulp, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
def find_one(pred):
    for f in base.rglob("*"):
        try:
            if f.is_file() and pred(f):
                return f
        except Exception:
            pass
    return None

s1 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet1"))
s2 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet2"))
s3 = next(f for f in base.rglob("*.csv") if f.name.startswith("sheet3"))
r2real = next(f for f in base.rglob("result2.xlsx") if "data_Q2" in str(f))
# q3 out dir
q3dir = next(d for d in base.rglob("*") if d.is_dir() and d.name == "q3")
data_out = q3dir / "data_Q3"; data_out.mkdir(exist_ok=True)
chart_out = q3dir / "charts_Q3"; chart_out.mkdir(exist_ok=True)

d1 = pd.read_csv(s1, encoding="utf-8-sig")
d2 = pd.read_csv(s2, encoding="utf-8-sig")
d3 = pd.read_csv(s3, encoding="utf-8-sig")
d1["日期"] = pd.to_datetime(d1["日期"]).dt.strftime("%Y-%m-%d")
d2["日期"] = pd.to_datetime(d2["日期"]).dt.strftime("%Y-%m-%d")
r2 = pd.read_excel(r2real)

targets = [f"2025-02-0{d}" for d in range(1,9)] + [f"2025-08-0{d}" for d in range(1,9)]

# ---- candidate per (scheme,unit) ----
cand_map = {}  # (scheme,unit) -> {kw: cls}
cls_of = {}
for _, r in r2.iterrows():
    key = (int(r["方案ID"]), int(r["推广单元"]))
    for c in ["黄金词","重点词","潜力词"]:
        v = r[c]
        if pd.notna(v):
            kw = int(v)
            cand_map.setdefault(key, {})[kw] = c
            cls_of[(key[0], key[1], kw)] = c
# sheet3 agg per (scheme,unit,kw)
g3 = d3.groupby(["方案ID","推广单元ID","关键词ID"], as_index=False).agg(
    C=("消费额","sum"), K=("点击量","sum"), V=("浏览量","sum"))
g3["d"] = np.where(g3["K"]>0, g3["V"]/g3["K"], 0.0)
# unit history qbar from sheet1 (all dates)
unit_hist = d1.groupby(["方案ID","推广单元ID"], as_index=False).agg(Ks=("点击量","sum"), Cs=("消费额","sum"))
unit_hist["qbar"] = np.where(unit_hist["Cs"]>0, unit_hist["Ks"]/unit_hist["Cs"], 0)
qbar_map = {(int(r["方案ID"]),int(r["推广单元ID"])): float(r["qbar"]) for _,r in unit_hist.iterrows()}
avg_all = d1["点击量"].sum()/d1["消费额"].sum()
# date params
dayK = d1.groupby("日期", as_index=False).agg(K=("点击量","sum"), C=("消费额","sum"))
dayK["q"] = np.where(dayK["C"]>0, dayK["K"]/dayK["C"], 0)
dayK["theta"] = dayK["q"]/avg_all
reg_map = {r["日期"]: float(r["新注册数"]) for _,r in d2.iterrows()}
dayK["R"] = dayK["日期"].map(reg_map)
dayK["rho"] = np.where(dayK["K"]>0, dayK["R"]/dayK["K"], 0)
theta_map = dict(zip(dayK["日期"], dayK["theta"]))
rho_map = dict(zip(dayK["日期"], dayK["rho"]))
# position proxy p_jt
d1["p"] = np.where(d1["展现量"]>0,
    (d1["上方首位展现量"]*1.0 + (d1["上方位展现量"]-d1["上方首位展现量"])*2.5 + (d1["展现量"]-d1["上方位展现量"])*4.0)/d1["展现量"], np.nan)
# budgets Bjt from sheet1 on target dates
bt = d1[d1["日期"].isin(targets)].groupby(["日期","方案ID","推广单元ID"], as_index=False).agg(
    B=("消费额","sum"), E=("展现量","sum"), Eup=("上方位展现量","sum"), Etop=("上方首位展现量","sum"))
bt["pjt"] = np.where(bt["E"]>0, (bt["Etop"]*1.0+(bt["Eup"]-bt["Etop"])*2.5+(bt["E"]-bt["Eup"])*4.0)/bt["E"], np.nan)
totalB = bt["B"].sum()

# build records per (t,j,kw)
C0 = 50.0  # smoothing pseudo cost
recs = []  # list of dicts per (t,j,kw) static part (no t except theta/rho/B)
# static per (j,kw): C,K,V,d,qbar,eta,w
static = []
for (sch, unit), kwmap in cand_map.items():
    qbar = qbar_map.get((sch,unit), avg_all)
    sub = g3[(g3["方案ID"]==sch)&(g3["推广单元ID"]==unit)]
    sub = sub[sub["关键词ID"].isin(list(kwmap.keys()))]
    totC = sub["C"].sum()
    for _, r in sub.iterrows():
        kw = int(r["关键词ID"]); C=float(r["C"]); K=float(r["K"]); V=float(r["V"])
        d = float(r["d"]) if r["K"]>0 else 0.0
        # smoothed eta
        eta_raw = (K/C)/qbar if C>0 and qbar>0 else 0.0
        eta = ((K+qbar*C0)/(C+C0))/qbar if qbar>0 else 0.0
        w = (C/totC) if totC>0 else 0.0
        static.append({"方案ID":sch,"推广单元ID":unit,"关键词ID":kw,"类":kwmap[kw],
                       "C":C,"K":K,"V":V,"d":d,"qbar":qbar,"eta_raw":eta_raw,"eta":eta,"w":w,"totC":totC})

st = pd.DataFrame(static)
st.to_csv(data_out/"static_params.csv", index=False, encoding="utf-8-sig")

def solve_day(day, beta=0.15, gamma=1.20, verbose=False):
    """Solve one day jointly across units with mutex. Returns df rows with b."""
    units = bt[bt["日期"]==day]
    units = units[units["B"]>0]
    if len(units)==0:
        return pd.DataFrame()
    theta = float(theta_map.get(day,1.0)); rho = float(rho_map.get(day,0.0))
    prob = pulp.LpProblem(f"Q3_{day}", pulp.LpMaximize)
    vars_b = {}; vars_x = {}
    coeffs = {}
    # build per unit candidate list
    for _, u in units.iterrows():
        sch=int(u["方案ID"]); unit=int(u["推广单元ID"]); B=float(u["B"])
        cand = st[(st["方案ID"]==sch)&(st["推广单元ID"]==unit)]
        for _, r in cand.iterrows():
            kw=int(r["关键词ID"])
            M = min(float(r["w"])*B*gamma, 0.3*B)
            if M < 0.01:
                continue
            e = float(r["qbar"])*float(r["eta"])*theta*rho  # regs per yuan
            key=(sch,unit,kw)
            b = pulp.LpVariable(f"b_{sch}_{unit}_{kw}", lowBound=0, upBound=M)
            x = pulp.LpVariable(f"x_{sch}_{unit}_{kw}", cat="Binary")
            vars_b[key]=b; vars_x[key]=x; coeffs[key]=e
            prob += b <= M*x
    # potential cap per unit
    for _, u in units.iterrows():
        sch=int(u["方案ID"]); unit=int(u["推广单元ID"]); B=float(u["B"])
        plist=[vars_b[k] for k in vars_b if k[0]==sch and k[1]==unit and cls_of.get((sch,unit,k[2]))=="潜力词"]
        if plist:
            prob += pulp.lpSum(plist) <= beta*B
    # budget per unit (<= to keep feasible; equality checked later)
    for _, u in units.iterrows():
        sch=int(u["方案ID"]); unit=int(u["推广单元ID"]); B=float(u["B"])
        bl=[vars_b[k] for k in vars_b if k[0]==sch and k[1]==unit]
        if bl:
            prob += pulp.lpSum(bl) <= B + 1e-6
    # mutex: same kw in multiple units
    from collections import defaultdict
    bykw=defaultdict(list)
    for k in vars_b: bykw[k[2]].append(vars_x[k])
    for kw, xs in bykw.items():
        if len(xs)>1:
            prob += pulp.lpSum(xs) <= 1
    # objective: max regs; tie-break small preference to spend (to hit 100%)
    prob += pulp.lpSum([coeffs[k]*vars_b[k] for k in vars_b])
    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=120))
    rows=[]
    for _, u in units.iterrows():
        sch=int(u["方案ID"]); unit=int(u["推广单元ID"]); B=float(u["B"]); pjt=u["pjt"]
        for k in [kk for kk in vars_b if kk[0]==sch and kk[1]==unit]:
            bval = pulp.value(vars_b[k])
            if bval is None: bval=0
            if bval>1e-6:
                kw=k[2]
                srow = st[(st["方案ID"]==sch)&(st["推广单元ID"]==unit)&(st["关键词ID"]==kw)].iloc[0]
                Khat = float(srow["qbar"])*float(srow["eta"])*theta*bval
                Vhat = float(srow["d"])*Khat
                Rhat = rho*Khat
                rows.append({"日期":day,"方案ID":sch,"推广单元ID":unit,"关键词ID":kw,"类":cls_of[(sch,unit,kw)],
                             "投入金额":bval,"预期展位":float(pjt) if pd.notna(pjt) else np.nan,
                             "预期点击量":Khat,"预期浏览量":Vhat,"预期注册量":Rhat,
                             "qbar":float(srow["qbar"]),"eta":float(srow["eta"]),"theta":theta,"rho":rho})
    return pd.DataFrame(rows)

# baseline solve
all_rows=[]
for day in targets:
    dfd = solve_day(day, beta=0.15, gamma=1.20)
    all_rows.append(dfd)
res = pd.concat(all_rows, ignore_index=True) if len(all_rows)>0 else pd.DataFrame()
# budget completion check; redistribute remainder same day if any unit left money due to caps
# (spec 9.1: allow realloc to other feasible units same day)
# Our per-day joint solve already maximizes total regs under <=B, remainder is structural (caps). Report it.
res.to_csv(data_out/"opt_detail.csv", index=False, encoding="utf-8-sig")
# result3.xlsx 9 cols
colmap = {"日期":"日期","方案ID":"方案ID","推广单元ID":"推广单元","关键词ID":"关键词","投入金额":"投入金额",
          "预期展位":"预期展位","预期点击量":"预期点击量","预期浏览量":"预期浏览量","预期注册量":"预期注册量"}
r3 = res[[c for c in colmap]].rename(columns=colmap) if len(res)>0 else pd.DataFrame(columns=list(colmap.values()))
r3.to_excel(data_out/"result3.xlsx", index=False)
# daily summary
summ = res.groupby("日期", as_index=False).agg(投入=("投入金额","sum"),词数=("关键词ID","count"),
    点击=("预期点击量","sum"),浏览=("预期浏览量","sum"),注册=("预期注册量","sum"))
summ = summ.merge(bt.groupby("日期", as_index=False).agg(预算=("B","sum")), on="日期", how="right").fillna(0)
summ = summ.merge(dayK[["日期","theta"]], on="日期", how="left")
# original regs per day
orig = d1[d1["日期"].isin(targets)].groupby("日期", as_index=False).agg(原消费=("消费额","sum"),原点击=("点击量","sum"))
orig["原注册"] = orig["日期"].map(reg_map)
summ = summ.merge(orig, on="日期", how="left")
summ["估计提升"] = np.where(summ["原注册"]>0, (summ["注册"]-summ["原注册"])/summ["原注册"], np.nan)
summ.to_csv(data_out/"daily_summary.csv", index=False, encoding="utf-8-sig")

# ---- history baseline ----
hist_rows=[]
for _, u in bt.iterrows():
    day=u["日期"]; sch=int(u["方案ID"]); unit=int(u["推广单元ID"]); B=float(u["B"])
    if B<=0: continue
    cand = st[(st["方案ID"]==sch)&(st["推广单元ID"]==unit)]
    theta=float(theta_map.get(day,1.0)); rho=float(rho_map.get(day,0.0)); pjt=u["pjt"]
    for _, r in cand.iterrows():
        bH = B*float(r["w"])
        if bH<=0: continue
        Khat=float(r["qbar"])*float(r["eta"])*theta*bH
        hist_rows.append({"日期":day,"方案ID":sch,"推广单元ID":unit,"关键词ID":int(r["关键词ID"]),
            "投入H":bH,"点击H":Khat,"注册H":rho*Khat})
hist = pd.DataFrame(hist_rows)
hist_day = hist.groupby("日期", as_index=False).agg(预算=("投入H","sum"),历史点击=("点击H","sum"),历史注册=("注册H","sum"))
hist_day["历史成本"] = np.where(hist_day["历史注册"]>0, hist_day["预算"]/hist_day["历史注册"], np.nan)
opt_day = summ[["日期","投入","点击","注册"]].rename(columns={"投入":"优化投入","点击":"优化点击","注册":"优化注册"})
comp = hist_day.merge(opt_day, on="日期", how="outer").fillna(0)
comp["优化成本"] = np.where(comp["优化注册"]>0, comp["优化投入"]/comp["优化注册"], np.nan)
comp["注册提升"] = np.where(comp["历史注册"]>0, (comp["优化注册"]-comp["历史注册"])/comp["历史注册"], np.nan)
comp.to_csv(data_out/"compare_daily.csv", index=False, encoding="utf-8-sig")
totB=float(comp["预算"].sum()); totHC=float(comp["历史点击"].sum()); totHR=float(comp["历史注册"].sum())
totOC=float(comp["优化点击"].sum()); totOR=float(comp["优化注册"].sum())

# ---- sensitivity ----
sens=[]
for beta in [0.10,0.15,0.20]:
    tot=0
    for day in targets:
        dfd=solve_day(day, beta=beta, gamma=1.20)
        tot+=dfd["预期注册量"].sum() if len(dfd)>0 else 0
    sens.append(("beta",beta,tot))
for gamma in [1.10,1.20,1.30]:
    tot=0
    for day in targets:
        dfd=solve_day(day, beta=0.15, gamma=gamma)
        tot+=dfd["预期注册量"].sum() if len(dfd)>0 else 0
    sens.append(("gamma",gamma,tot))
sens_df=pd.DataFrame(sens, columns=["param","value","regs"])
sens_df.to_csv(data_out/"sensitivity.csv", index=False, encoding="utf-8-sig")
base_regs = float(sens_df[(sens_df.param=="beta")&(sens_df.value==0.15)]["regs"].iloc[0])
sens_df["rel"]=(sens_df["regs"]-base_regs)/base_regs

# ---- charts ----
plt.rcParams["font.sans-serif"]=["DejaVu Sans"]
fig,ax=plt.subplots(figsize=(10,4))
d=dayK[dayK["日期"].isin(targets)].copy()
ax.bar(d["日期"], d["theta"], color="steelblue")
ax.axhline(1, color="red", linestyle="--")
ax.set_title("theta by date (baseline=1)")
ax.set_xticklabels(d["日期"], rotation=45, ha="right")
plt.tight_layout(); plt.savefig(chart_out/"fig1_theta.png", dpi=150); plt.close()
fig,ax=plt.subplots(figsize=(10,4))
c=comp.sort_values("日期")
x=np.arange(len(c)); w=0.35
ax.bar(x-w/2, c["历史点击"], width=w, label="history clicks")
ax.bar(x+w/2, c["优化点击"], width=w, label="opt clicks")
ax.set_xticks(x); ax.set_xticklabels([s[5:] for s in c["日期"]], rotation=45, ha="right")
ax.legend(); ax.set_title("clicks history vs opt (same budget)")
plt.tight_layout(); plt.savefig(chart_out/"fig2_clicks.png", dpi=150); plt.close()
fig,axs=plt.subplots(3,1,figsize=(10,9), sharex=True)
axs[0].plot(c["日期"], c["历史点击"], marker="o", label="hist clicks")
axs[0].plot(c["日期"], c["优化点击"], marker="s", label="opt clicks")
axs[0].legend(); axs[0].set_title("clicks")
axs[1].plot(c["日期"], c["历史注册"], marker="o", label="hist regs")
axs[1].plot(c["日期"], c["优化注册"], marker="s", label="opt regs")
axs[1].legend(); axs[1].set_title("regs")
axs[2].plot(c["日期"], c["历史成本"], marker="o", label="hist cost/reg")
axs[2].plot(c["日期"], c["优化成本"], marker="s", label="opt cost/reg")
axs[2].legend(); axs[2].set_title("cost per reg (lower better)")
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(chart_out/"fig3_hist_vs_opt.png", dpi=150); plt.close()

# ---- summary txt ----
L=[]
L.append(f"avg_all(q)={avg_all:.4f}")
L.append(f"totalB={totB:.2f} optRows={len(res)} optClicks={totOC:.1f} optRegs={totOR:.2f}")
L.append(f"histClicks={totHC:.1f} histRegs={totHR:.2f} lift={(totOR-totHR)/totHR*100:.1f}% costH={totB/totHR:.2f} costO={totB/totOR:.2f}")
L.append("=== daily theta/rho ===")
for _,r in dayK[dayK["日期"].isin(targets)].iterrows():
    L.append(f"{r['日期']} theta={r['theta']:.3f} rho={r['rho']:.4f} R={r['R']:.0f} K={r['K']:.0f}")
L.append("=== daily summary (opt vs orig) ===")
L.append(summ.to_string(index=False))
L.append("=== compare hist vs opt ===")
L.append(comp.to_string(index=False))
L.append("=== sensitivity ===")
L.append(sens_df.to_string(index=False))
L.append("=== top5 02-01 ===")
t1=res[res["日期"]=="2025-02-01"].sort_values("投入金额",ascending=False).head(5)
L.append(t1.to_string(index=False) if len(t1)>0 else "empty")
L.append("=== top6 08-01 ===")
t2=res[res["日期"]=="2025-08-01"].sort_values("投入金额",ascending=False).head(6)
L.append(t2.to_string(index=False) if len(t2)>0 else "empty")
L.append(f"candidate units={st[['方案ID','推广单元ID']].drop_duplicates().shape[0]} staticRows={len(st)}")
pathlib.Path("C:/Users/ZhangChaobo/AppData/Local/Temp/opencode/summary_q3.txt").write_text("\n".join(L), encoding="utf-8")

# ---- day-level realloc to reach 100% spend (spec 9.1) ----
from collections import defaultdict as _dd
_realloc_rows = []
for _day in targets:
    _ud = bt[bt["日期"]==_day]
    _dayB = float(_ud["B"].sum())
    _spent = float(res[res["日期"]==_day]["投入金额"].sum()) if len(res)>0 else 0.0
    _left = _dayB - _spent
    if _left > 1e-6:
        _theta = float(theta_map.get(_day,1.0)); _rho = float(rho_map.get(_day,0.0))
        _cur = res[res["日期"]==_day].set_index(["方案ID","推广单元ID","关键词ID"])["投入金额"].to_dict() if len(res)>0 else {}
        _pot = _dd(float); _sp = _dd(float)
        for _k,_v in _cur.items():
            _sp[(_k[0],_k[1])] += _v
            if cls_of.get((_k[0],_k[1],_k[2]))=="潜力词": _pot[(_k[0],_k[1])] += _v
        _pool=[]
        for _,_u in _ud.iterrows():
            _sch,_unit,_B=int(_u["方案ID"]),int(_u["推广单元ID"]),float(_u["B"])
            if _B<=0: continue
            _cand=st[(st["方案ID"]==_sch)&(st["推广单元ID"]==_unit)].copy()
            for _,_r in _cand.iterrows():
                _kw=int(_r["关键词ID"]); _k=(_sch,_unit,_kw)
                _curv=_cur.get(_k,0.0)
                _cap30=0.3*_B-_curv
                if _r["类"]=="潜力词": _cap=min(_cap30, max(0,0.15*_B-_pot[(_sch,_unit)]), _B-_sp[(_sch,_unit)], _left)
                else: _cap=min(_cap30, _B-_sp[(_sch,_unit)], _left)
                if _cap>1e-9:
                    _e=float(_r["qbar"])*float(_r["eta"])*_theta*_rho
                    _pool.append((_e,_sch,_unit,_kw,float(_r["qbar"]),float(_r["eta"]),float(_r["d"]),_u["pjt"],_cap,_r["类"]))
        _pool.sort(reverse=True)
        for (_e,_sch,_unit,_kw,_qb,_et,_ddv,_pjt,_cap,_cls) in _pool:
            if _left<=1e-9: break
            _take=min(_cap,_left)
            if _take<=1e-9: continue
            _Kh=_qb*_et*_theta*_take; _Vh=_ddv*_Kh; _Rh=_rho*_Kh
            _realloc_rows.append({"日期":_day,"方案ID":_sch,"推广单元ID":_unit,"关键词ID":_kw,"类":_cls,
                "投入金额":_take,"预期展位":float(_pjt) if pd.notna(_pjt) else np.nan,
                "预期点击量":_Kh,"预期浏览量":_Vh,"预期注册量":_Rh,
                "qbar":_qb,"eta":_et,"theta":_theta,"rho":_rho})
            _left-=_take
            _sp[(_sch,_unit)]+=_take
            if _cls=="潜力词": _pot[(_sch,_unit)]+=_take
if _realloc_rows:
    res = pd.concat([res, pd.DataFrame(_realloc_rows)], ignore_index=True)
    # merge same (day,unit,kw) duplicates from realloc
    res = res.groupby(["日期","方案ID","推广单元ID","关键词ID","类","预期展位","qbar","eta","theta","rho"], as_index=False).agg(
        投入金额=("投入金额","sum"),预期点击量=("预期点击量","sum"),预期浏览量=("预期浏览量","sum"),预期注册量=("预期注册量","sum"))
    res.to_csv(data_out/"opt_detail.csv", index=False, encoding="utf-8-sig")
    r3 = res[["日期","方案ID","推广单元ID","关键词ID","投入金额","预期展位","预期点击量","预期浏览量","预期注册量"]].rename(
        columns={"推广单元ID":"推广单元","关键词ID":"关键词","投入金额":"投入金额","预期展位":"预期展位","预期点击量":"预期点击量","预期浏览量":"预期浏览量","预期注册量":"预期注册量"})
    r3.to_excel(data_out/"result3.xlsx", index=False)
    summ = res.groupby("日期", as_index=False).agg(投入=("投入金额","sum"),词数=("关键词ID","count"),
        点击=("预期点击量","sum"),浏览=("预期浏览量","sum"),注册=("预期注册量","sum"))
    summ = summ.merge(bt.groupby("日期", as_index=False).agg(预算=("B","sum")), on="日期", how="right").fillna(0)
    summ = summ.merge(dayK[["日期","theta"]], on="日期", how="left")
    orig = d1[d1["日期"].isin(targets)].groupby("日期", as_index=False).agg(原消费=("消费额","sum"),原点击=("点击量","sum"))
    orig["原注册"] = orig["日期"].map(reg_map)
    summ = summ.merge(orig, on="日期", how="left")
    summ["估计提升"] = np.where(summ["原注册"]>0, (summ["注册"]-summ["原注册"])/summ["原注册"], np.nan)
    summ.to_csv(data_out/"daily_summary.csv", index=False, encoding="utf-8-sig")
    opt_day = summ[["日期","投入","点击","注册"]].rename(columns={"投入":"优化投入","点击":"优化点击","注册":"优化注册"})
    comp = hist_day.merge(opt_day, on="日期", how="outer").fillna(0)
    comp["优化成本"] = np.where(comp["优化注册"]>0, comp["优化投入"]/comp["优化注册"], np.nan)
    comp["注册提升"] = np.where(comp["历史注册"]>0, (comp["优化注册"]-comp["历史注册"])/comp["历史注册"], np.nan)
    comp.to_csv(data_out/"compare_daily.csv", index=False, encoding="utf-8-sig")
    totOC=float(comp["优化点击"].sum()); totOR=float(comp["优化注册"].sum())
    # refresh charts fig2/fig3 with new comp
    import matplotlib.pyplot as plt
    c=comp.sort_values("日期")
    fig,ax=plt.subplots(figsize=(10,4))
    x=np.arange(len(c)); w=0.35
    ax.bar(x-w/2, c["历史点击"], width=w, label="history clicks")
    ax.bar(x+w/2, c["优化点击"], width=w, label="opt clicks")
    ax.set_xticks(x); ax.set_xticklabels([s[5:] for s in c["日期"]], rotation=45, ha="right")
    ax.legend(); ax.set_title("clicks history vs opt (same budget)")
    plt.tight_layout(); plt.savefig(chart_out/"fig2_clicks.png", dpi=150); plt.close()
    fig,axs=plt.subplots(3,1,figsize=(10,9), sharex=True)
    axs[0].plot(c["日期"], c["历史点击"], marker="o", label="hist clicks")
    axs[0].plot(c["日期"], c["优化点击"], marker="s", label="opt clicks")
    axs[0].legend(); axs[0].set_title("clicks")
    axs[1].plot(c["日期"], c["历史注册"], marker="o", label="hist regs")
    axs[1].plot(c["日期"], c["优化注册"], marker="s", label="opt regs")
    axs[1].legend(); axs[1].set_title("regs")
    axs[2].plot(c["日期"], c["历史成本"], marker="o", label="hist cost/reg")
    axs[2].plot(c["日期"], c["优化成本"], marker="s", label="opt cost/reg")
    axs[2].legend(); axs[2].set_title("cost per reg (lower better)")
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    plt.savefig(chart_out/"fig3_hist_vs_opt.png", dpi=150); plt.close()
    # sensitivity with realloc-aware greedy? keep pulp-based sens as is; recompute base totals
    L2=[]
    L2.append(f"REALLOC_DONE totalB={float(comp['预算'].sum()):.2f} optSpent={float(comp['优化投入'].sum()):.2f} optClicks={totOC:.1f} optRegs={totOR:.2f} histRegs={float(comp['历史注册'].sum()):.1f} lift={(totOR-float(comp['历史注册'].sum()))/float(comp['历史注册'].sum())*100:.1f}% rows={len(res)}")
    pathlib.Path("C:/Users/ZhangChaobo/AppData/Local/Temp/opencode/realloc_summary.txt").write_text("\n".join(L2), encoding="utf-8")
    print("REALLOC_DONE", L2[0])

print("DONE")
