# -*- coding: utf-8 -*-
"""Q4 s3: 基准情景 (delta=0.5, omega=0.5, band=15%, gamma=1.2) 求解 + 落盘.
约束(B口径): 周总量==B; 单元周±band; 日总额<=1.15*同期; M; 潜力<=15%日."""
import pathlib
import pandas as pd
from q4_s3_lib import DD, B, load_inputs, build_cal, rho_hat, solve_week

inp = load_inputs()
cal = build_cal(inp, omega=0.5)
cal.to_csv(DD / "cal_unit_day.csv", index=False, encoding="utf-8-sig")
RHO = rho_hat(inp, omega=0.5)
pd.DataFrame([dict(omega=0.5, delta=0.5, rho_hat=RHO)]).to_csv(
    DD / "rho_table.csv", index=False, encoding="utf-8-sig")
print("RHO=%.5f avg_all=%.5f" % (RHO, inp["avg_all"]))

alloc, status = solve_week(inp, cal, RHO, msg=0)
print("status:", status)
alloc.to_csv(DD / "lp_alloc.csv", index=False, encoding="utf-8-sig")
ds = alloc.groupby("日期", as_index=False).agg(
    投入=("投入金额", "sum"), 词数=("关键词", "count"),
    点击=("预期点击量", "sum"), 浏览=("预期浏览量", "sum"), 注册=("预期注册量", "sum"))
ds["注册成本"] = ds["投入"] / ds["注册"]
ds.to_csv(DD / "daily_summary.csv", index=False, encoding="utf-8-sig")
tp = alloc.groupby("类别", as_index=False).agg(投入=("投入金额", "sum"))
tp["占比"] = tp["投入"] / tp["投入"].sum()
tp.to_csv(DD / "type_alloc.csv", index=False, encoding="utf-8-sig")
print(ds.to_string(index=False))
print(tp.to_string(index=False))
print("TOTAL cost=%.2f clicks=%.2f views=%.2f regs=%.2f rows=%d eff_cpc=%.4f" % (
    alloc["投入金额"].sum(), alloc["预期点击量"].sum(), alloc["预期浏览量"].sum(),
    alloc["预期注册量"].sum(), len(alloc),
    alloc["投入金额"].sum() / alloc["预期点击量"].sum()))
day_cap = {r["ymd26"]: float(r["hist_cost"]) for _, r in inp["dayh"].iterrows()}
for _, r in ds.iterrows():
    print(r["日期"], "ratio=%.4f" % (r["投入"] / day_cap[r["日期"]]))
print("S3 OK")
