# -*- coding: utf-8 -*-
"""出价策略与预算 B1-B4：12单元B/Q/E四象限 + CPC对比 + 上方位溢价CTR + 日CPA。
数据源：E题/clean_data/*_clean.csv；输出：q1/data_Q1/q1_budget_*.csv + q1/charts_Q1/q1_b1~b4_*.pdf/png
口径：先汇总再相除；除零记空；零值保留；E=Q/B=整体CPC/单元CPC。
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # E题/q1
CD = os.path.join(os.path.dirname(ROOT), "E题", "clean_data") if os.path.basename(ROOT) == "q1" else None
# ROOT 实际就是 E题/q1，上级为 E题
EROOT = os.path.dirname(ROOT)
CD = os.path.join(EROOT, "clean_data")
DOUT = os.path.join(ROOT, "data_Q1")
COUT = os.path.join(ROOT, "charts_Q1")
os.makedirs(DOUT, exist_ok=True)
os.makedirs(COUT, exist_ok=True)

s1 = pd.read_csv(os.path.join(CD, "sheet1_投放记录_clean.csv"), encoding="utf-8-sig")
s2 = pd.read_csv(os.path.join(CD, "sheet2_日注册_clean.csv"), encoding="utf-8-sig")
c_date, c_pid, c_uid = s1.columns[0], s1.columns[1], s1.columns[2]
c_imp, c_clk, c_spd = s1.columns[3], s1.columns[4], s1.columns[5]
c_timp, c_tclk, c_tspd = s1.columns[6], s1.columns[8], s1.columns[9]
c_first = s1.columns[7]

TOTAL_SPEND = s1[c_spd].sum()
TOTAL_CLK = s1[c_clk].sum()
TOTAL_IMP = s1[c_imp].sum()
CPC_ALL = TOTAL_SPEND / TOTAL_CLK
print(f"对账: 总消费={TOTAL_SPEND:.2f} 总点击={TOTAL_CLK:.0f} 整体CPC={CPC_ALL:.4f}")

rows = []
for (pid, uid), d in s1.groupby([c_pid, c_uid]):
    spend, clk, imp = d[c_spd].sum(), d[c_clk].sum(), d[c_imp].sum()
    tspd, tclk, timp = d[c_tspd].sum(), d[c_tclk].sum(), d[c_timp].sum()
    first = d[c_first].sum()
    B = spend / TOTAL_SPEND
    Q = clk / TOTAL_CLK
    E = Q / B if B > 0 else np.nan
    cpc = spend / clk if clk > 0 else np.nan
    # 上方位 vs 非上方位
    o_spd, o_clk, o_imp = spend - tspd, clk - tclk, imp - timp
    cpc_top = tspd / tclk if tclk > 0 else np.nan
    cpc_other = o_spd / o_clk if o_clk > 0 else np.nan
    P = cpc_top / cpc_other if (cpc_other and cpc_other > 0) else np.nan
    ctr = clk / imp if imp > 0 else np.nan
    ctr_top = tclk / timp if timp > 0 else np.nan
    ctr_other = o_clk / o_imp if o_imp > 0 else np.nan
    rows.append(dict(方案ID=pid, 推广单元ID=uid, 总消费=spend, 总点击=clk, 总展现=imp,
                     预算份额B=B, 点击份额Q=Q, 相对效率E=E, CPC=cpc,
                     上方位消费=tspd, 上方位点击=tclk, 上方位展现=timp, 首位展现=first,
                     CPC_top=cpc_top, CPC_other=cpc_other, 溢价P=P,
                     CTR=ctr, CTR_top=ctr_top, CTR_other=ctr_other,
                     上方位消费占比=(tspd / spend if spend > 0 else np.nan),
                     投放天数=d[c_date].nunique()))

u = pd.DataFrame(rows).sort_values(["方案ID", "推广单元ID"]).reset_index(drop=True)
B0 = u["预算份额B"].median()
def _quad(r):
    if r["预算份额B"] >= B0 and r["相对效率E"] >= 1:
        return "Ⅰ高预算高效率"
    if r["预算份额B"] < B0 and r["相对效率E"] >= 1:
        return "Ⅱ低预算高效率"
    if r["预算份额B"] < B0:
        return "Ⅲ低预算低效率"
    return "Ⅳ高预算低效率"
u["象限"] = u.apply(_quad, axis=1)
u.to_csv(os.path.join(DOUT, "q1_budget_units.csv"), index=False, encoding="utf-8-sig")
print(f"B0中位数={B0:.6f} ({B0*100:.4f}%)")
print(u[["推广单元ID", "总消费", "预算份额B", "点击份额Q", "相对效率E", "CPC", "溢价P", "象限"]].to_string(index=False))

# 日CPA
s1d = s1.groupby(c_date, as_index=False).agg({c_spd: "sum", c_clk: "sum", c_imp: "sum"})
s1d.columns = ["日期", "日消费", "日点击", "日展现"]
s2d = s2.copy(); s2d.columns = ["日期", "新注册数", "日总消费", "日CPA_check"] if s2.shape[1] == 4 else list(s2.columns)
daily = s1d.merge(s2d[["日期", "新注册数"]], on="日期", how="left")
daily["日期"] = pd.to_datetime(daily["日期"])
daily = daily.sort_values("日期")
daily["CPA"] = daily["日消费"] / daily["新注册数"].replace(0, np.nan)
daily["CPA_7d"] = daily["CPA"].rolling(7, min_periods=1).mean()
daily.to_csv(os.path.join(DOUT, "q1_budget_daily.csv"), index=False, encoding="utf-8-sig")

# —— B1 四象限：x=B(%, log轴), y=E，等大点+方案色 ——
fig, ax = plt.subplots(figsize=(FIG_W_FULL, 115 * MM))
colors = [PLAN_COLORS.get(p, OI["grey"]) for p in u["方案ID"]]
ax.scatter(u["预算份额B"] * 100, u["相对效率E"], s=90, c=colors, alpha=0.9,
           edgecolors="white", linewidths=0.8, zorder=3)
ax.set_xscale("log")
ax.set_xticks([0.05, 0.2, 1, 5, 20, 60])
from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
OFF_B1 = {"7181": (8, 8), "4603": (8, 6), "3555": (8, 6), "3000": (8, 4),
          "8310": (8, -12), "8309": (-42, -14), "8329": (8, 2), "0250": (8, 6),
          "6627": (8, 6), "3528": (8, 4), "5700": (8, -12), "0100": (8, 6)}
for _, r in u.iterrows():
    tail = str(int(r["推广单元ID"]))[-4:]
    dx, dy = OFF_B1.get(tail, (5, 5))
    ax.annotate(unit_short(r["推广单元ID"]), (r["预算份额B"] * 100, r["相对效率E"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=7.5)
ax.axvline(B0 * 100, color="#666666", linewidth=1.0, linestyle="--")
ax.axhline(1.0, color="#666666", linewidth=1.0, linestyle="--")
ax.set_xlabel("预算份额 B（%，单元消费/总消费）")
ax.set_ylabel("相对点击效率 E（点击份额/预算份额）")
ax.set_title("预算份额—相对点击效率四象限（虚线：B中位数，E=1）", pad=10)
ax.text(0.02, 0.96, "Ⅱ低预算·高效率\n扩量候选", transform=ax.transAxes, ha="left", va="top", fontsize=8)
ax.text(0.98, 0.96, "Ⅰ高预算·高效率\n重点保持", transform=ax.transAxes, ha="right", va="top", fontsize=8)
ax.text(0.02, 0.06, "Ⅲ低预算·低效率\n限额测试", transform=ax.transAxes, ha="left", va="bottom", fontsize=8)
ax.text(0.98, 0.06, "Ⅳ高预算·低效率\n优先调整", transform=ax.transAxes, ha="right", va="bottom", fontsize=8)
import matplotlib.patches as mpatches
ax.legend(handles=[mpatches.Patch(color=c, label=f"方案{p}") for p, c in PLAN_COLORS.items()],
          frameon=True, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5)
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
fig.savefig(os.path.join(COUT, "q1_b1_预算效率四象限.pdf"), dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(COUT, "q1_b1_预算效率四象限.png"), dpi=300, bbox_inches="tight", transparent=False)
plt.close()
print("B1 done")

# —— B2 CPC对比：按CPC升序横向条形 + 整体线 ——
v = u.sort_values("CPC").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(FIG_W_FULL, 105 * MM))
y = np.arange(len(v))
bars = ax.barh(y, v["CPC"], color=[PLAN_COLORS.get(p, OI["grey"]) for p in v["方案ID"]], edgecolor="white")
ax.axvline(CPC_ALL, color="#333333", linewidth=1.2, linestyle="--")
ax.text(CPC_ALL + 0.03, len(v) - 0.4, f"整体CPC {CPC_ALL:.2f}元", va="center", ha="left", fontsize=8)
for i, r in v.iterrows():
    ax.text(r["CPC"] + 0.03, y[i], f"{r['CPC']:.2f} (E={r['相对效率E']:.2f})", va="center", ha="left", fontsize=7.5)
ax.set_yticks(y)
ax.set_yticklabels([unit_short(x) for x in v["推广单元ID"]])
ax.set_xlabel("单元CPC（元/点击，越低越好）")
ax.set_xlim(0, v["CPC"].max() * 1.45)
ax.set_title("各推广单元CPC对比（虚线为公司整体水平）", pad=10)
ax.invert_yaxis()
ax.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
fig.savefig(os.path.join(COUT, "q1_b2_单元CPC对比.pdf"), dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(COUT, "q1_b2_单元CPC对比.png"), dpi=300, bbox_inches="tight", transparent=False)
plt.close()
print("B2 done")

# —— B3 上方位溢价P + CTR_top vs CTR_other（双面板） ——
w = u.sort_values("溢价P").reset_index(drop=True)
fig, axes = plt.subplots(1, 2, figsize=(FIG_W_FULL, 105 * MM), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
y = np.arange(len(w))
ax.barh(y, w["溢价P"], color=OI["vermillion"], edgecolor="white")
ax.axvline(1.0, color="#333333", linewidth=1.0, linestyle="--")
for i, r in w.iterrows():
    if pd.notna(r["溢价P"]):
        ax.text(r["溢价P"] + 0.05, y[i], f"{r['溢价P']:.2f}×", va="center", ha="left", fontsize=7)
ax.set_yticks(y)
ax.set_yticklabels([unit_short(x) for x in w["推广单元ID"]])
ax.set_xlabel("溢价 P（CPC_top/CPC_other）")
ax.set_title("(a) 上方位成本溢价", fontsize=9)
ax.invert_yaxis()
ax.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
ax2 = axes[1]
yy = np.arange(len(w))
h = 0.36
ax2.barh(yy + h / 2, w["CTR_top"] * 100, height=h, color=OI["blue"], edgecolor="white", label="上方位CTR")
ax2.barh(yy - h / 2, w["CTR_other"] * 100, height=h, color=OI["orange"], edgecolor="white", label="非上方位CTR")
ax2.set_yticks(yy)
ax2.set_yticklabels([unit_short(x) for x in w["推广单元ID"]])
ax2.set_xlabel("CTR（%，对数轴）")
ax2.set_xscale("log")
ax2.set_xticks([0.2, 1, 5, 20, 80])
ax2.set_xticklabels(["0.2", "1", "5", "20", "80"])
ax2.set_title("(b) 上方位 vs 非上方位CTR", fontsize=9)
ax2.invert_yaxis()
ax2.legend(frameon=True, fontsize=7.5, loc="lower right")
ax2.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.suptitle("上方位竞价是否值得：成本溢价与点击率提升联合判断", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(COUT, "q1_b3_上方位溢价CTR.pdf"), dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(COUT, "q1_b3_上方位溢价CTR.png"), dpi=300, bbox_inches="tight", transparent=False)
plt.close()
print("B3 done")

# —— B4 日CPA + 7日均线 ——
fig, ax = plt.subplots(figsize=(FIG_W_FULL, 80 * MM))
ax.plot(daily["日期"], daily["CPA"], color="#999999", linewidth=0.8, alpha=0.7, label="日CPA")
ax.plot(daily["日期"], daily["CPA_7d"], color=OI["vermillion"], linewidth=1.6, label="7日均线")
ax.set_ylabel("CPA（元/注册）")
ax.set_title("公司日度注册成本CPA走势（整体代理指标，不拆单元）", pad=10)
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate()
ax.legend(frameon=True, fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(COUT, "q1_b4_日CPA走势.pdf"), dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(COUT, "q1_b4_日CPA走势.png"), dpi=300, bbox_inches="tight", transparent=False)
plt.close()
print("B4 done")
print("ALL DONE:", sorted([f for f in os.listdir(COUT) if "q1_b" in f]))
