# -*- coding: utf-8 -*-
"""Q4 s6: 由官方口径(data_Q4_rev/plan.csv+summary.csv)生成 result4.xlsx双表 + 三图(覆盖charts_Q4)."""
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
REV = E / "q4" / "data_Q4_rev"
CH = E / "q4" / "charts_Q4"
CH.mkdir(parents=True, exist_ok=True)

plan = pd.read_csv(REV / "plan.csv", encoding="utf-8-sig")
summary = pd.read_csv(REV / "summary.csv", encoding="utf-8-sig")
plan["日期"] = pd.to_datetime(plan["日期"]).dt.strftime("%Y-%m-%d")
summary["日期"] = pd.to_datetime(summary["日期"]).dt.strftime("%Y-%m-%d")

main = pd.DataFrame({
    "日期": plan["日期"], "方案ID": plan["方案ID"].astype(int),
    "推广单元": plan["推广单元ID"].astype(int), "关键词": plan["关键词"].astype(int),
    "投入金额": plan["投入金额"], "预期展位": plan["展位预测"],
    "预期点击量": plan["预期点击量"], "预期浏览量": plan["预期浏览量"],
    "预期注册量": plan["预期注册量"]})
detail = pd.DataFrame({
    "日期": plan["日期"], "方案ID": plan["方案ID"].astype(int),
    "推广单元": plan["推广单元ID"].astype(int), "关键词": plan["关键词"].astype(int),
    "竞价代理值": plan["cpc"], "竞价下限": plan["cpc_lo"], "竞价上限": plan["cpc_hi"],
    "展现量": plan["预期展现量"], "展现量下限": plan["展现量下限"], "展现量上限": plan["展现量上限"],
    "展现位": plan["展位预测"], "展现位下限": plan["展位下限"], "展现位上限": plan["展位上限"],
    "点击量": plan["预期点击量"], "点击量下限": plan["点击量下限"], "点击量上限": plan["点击量上限"],
    "浏览量": plan["预期浏览量"], "浏览量下限": plan["浏览量下限"], "浏览量上限": plan["浏览量上限"],
    "注册量": plan["预期注册量"], "注册量下限": plan["注册量下限"], "注册量上限": plan["注册量上限"]})
with pd.ExcelWriter(REV / "result4.xlsx", engine="openpyxl") as xw:
    main.to_excel(xw, sheet_name="最优投放策略", index=False)
    detail.to_excel(xw, sheet_name="指标期望范围", index=False)
print("result4.xlsx:", len(main), "rows; detail cols:", len(detail.columns))
assert abs(main["投入金额"].sum() - 23488.02) < 1e-6
assert ((detail["注册量"] >= detail["注册量下限"]) & (detail["注册量"] <= detail["注册量上限"])).all()

dd = summary["日期"].str[5:].tolist()
fig, ax1 = plt.subplots(figsize=(8, 4.5))
ax1.bar(dd, summary["投入金额"], color="#4472C4")
ax1.set_ylabel("投入(元)")
ax2 = ax1.twinx()
ax2.plot(dd, summary["注册成本"], "o-", color="#ED7D31")
ax2.set_ylabel("注册成本(元/人)")
ax1.set_xlabel("日期(2026-09)")
plt.title("七日预算与预期注册成本")
plt.tight_layout()
plt.savefig(CH / "fig2_budget_cpa.png", dpi=150)
plt.close()

y = summary["预期注册"].to_numpy()
ylo = summary["注册_下限"].to_numpy()
yhi = summary["注册_上限"].to_numpy()
x = np.arange(len(dd))
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.fill_between(x, ylo, yhi, color="#2F6BFF", alpha=0.15, label="80%经验预测区间")
ax.plot(x, y, "o-", color="#2F6BFF", markersize=6, linewidth=2, label="中心预测")
ax.set_xticks(x)
ax.set_xticklabels(dd)
ax.set_xlabel("日期(2026-09)")
ax.set_ylabel("注册量")
ax.grid(True, alpha=0.3)
plt.title("2026年9月11日至17日预期注册量及区间")
plt.legend(loc="upper right")
plt.tight_layout()
plt.savefig(CH / "fig3_regs_interval.png", dpi=150)
plt.close()

tp = plan.groupby("类型", as_index=False).agg(投入=("投入金额", "sum"))
order = ["重点词", "潜力词", "黄金词"]
tp = tp.set_index("类型").reindex(order).reset_index()
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(tp["类型"], tp["投入"], color=["#4472C4", "#ED7D31", "#70AD47"])
ax.axhline(23488.02 * 0.15, color="red", linestyle="--", label="潜力词15%上限线")
for i, v in enumerate(tp["投入"]):
    ax.text(i, v, "%.0f" % v, ha="center", va="bottom")
ax.set_ylabel("投入(元)")
plt.title("不同关键词类型的预算分配")
plt.legend()
plt.tight_layout()
plt.savefig(CH / "fig4_type_alloc.png", dpi=150)
plt.close()
print("charts OK")
print("type mix:", dict(zip(tp["类型"], tp["投入"].round(2))))
print("S6 OK")
