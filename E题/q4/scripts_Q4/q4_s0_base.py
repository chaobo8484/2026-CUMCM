# -*- coding: utf-8 -*-
"""Q4 s0: 基数复核 2025-09-11~17. 输出到 q4/data_Q4. 绝对路径,utf-8-sig."""
import pathlib
import pandas as pd
import numpy as np

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
Q4 = E / "q4"
DD = Q4 / "data_Q4"
DD.mkdir(parents=True, exist_ok=True)

s1 = E / "clean_data" / "sheet1_投放记录_clean.csv"
s2 = E / "clean_data" / "sheet2_日注册_clean.csv"
d1 = pd.read_csv(s1, encoding="utf-8-sig")
d2 = pd.read_csv(s2, encoding="utf-8-sig")
d1["日期"] = pd.to_datetime(d1["日期"])
d2["日期"] = pd.to_datetime(d2["日期"])

WIN = pd.date_range("2025-09-11", "2025-09-17")
win = d1[d1["日期"].isin(WIN)].copy()
reg = d2[d2["日期"].isin(WIN)].copy()

# 单元x日基数
unit_day = win.groupby(["日期", "方案ID", "推广单元ID"], as_index=False).agg(
    Bjt=("消费额", "sum"), Kjt=("点击量", "sum"), Ejt=("展现量", "sum"),
    Eup=("上方位展现量", "sum"), Etop=("上方首位展现量", "sum"))
unit_day["qjt"] = unit_day["Kjt"] / unit_day["Bjt"].replace(0, np.nan)
unit_day["cpc"] = unit_day["Bjt"] / unit_day["Kjt"].replace(0, np.nan)
unit_day["ctr"] = unit_day["Kjt"] / unit_day["Ejt"].replace(0, np.nan)
unit_day["pjt"] = np.where(
    unit_day["Ejt"] > 0,
    (unit_day["Etop"] + (unit_day["Eup"] - unit_day["Etop"]) * 2.5
     + (unit_day["Ejt"] - unit_day["Eup"]) * 4.0) / unit_day["Ejt"], np.nan)
unit_day = unit_day.sort_values(["日期", "方案ID", "推广单元ID"])
unit_day.to_csv(DD / "base_budget_0911_17.csv", index=False, encoding="utf-8-sig")

# 总量
tot = dict(cost=float(win["消费额"].sum()), clicks=float(win["点击量"].sum()),
           impr=float(win["展现量"].sum()), regs=float(reg["新注册数"].sum()),
           fullyear=float(d1["消费额"].sum()), win_rows=int(len(win)))
pd.DataFrame([tot]).to_csv(DD / "base_totals.csv", index=False, encoding="utf-8-sig")

# 分日历史 (含注册,对账用)
day_cost = win.groupby("日期", as_index=False).agg(
    hist_cost=("消费额", "sum"), hist_click=("点击量", "sum"), hist_impr=("展现量", "sum"))
day_reg = reg[["日期", "新注册数"]].rename(columns={"新注册数": "hist_reg"})
day_hist = pd.merge(day_cost, day_reg, on="日期", how="left").sort_values("日期")
day_hist.to_csv(DD / "day_hist.csv", index=False, encoding="utf-8-sig")

# 单元窗口汇总 + 85%/115%带
unit_hist = win.groupby(["方案ID", "推广单元ID"], as_index=False).agg(
    B_week=("消费额", "sum"), K_week=("点击量", "sum"), E_week=("展现量", "sum"))
unit_hist["lo85"] = unit_hist["B_week"] * 0.85
unit_hist["hi115"] = unit_hist["B_week"] * 1.15
unit_hist = unit_hist.sort_values(["方案ID", "推广单元ID"])
unit_hist.to_csv(DD / "unit_hist.csv", index=False, encoding="utf-8-sig")

# 断言
assert abs(tot["cost"] - 23488.02) < 0.01, tot
assert abs(day_hist["hist_cost"].sum() - 23488.02) < 0.01
print("S0 OK cost=%.2f clicks=%d impr=%d regs=%d units=%d unit_days=%d" % (
    tot["cost"], tot["clicks"], tot["impr"], tot["regs"],
    unit_hist.shape[0], unit_day.shape[0]))
print(day_hist.to_string(index=False))
