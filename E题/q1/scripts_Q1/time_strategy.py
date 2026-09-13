# -*- coding: utf-8 -*-
"""Q1投放策略与时间：统一口径计算 + A1~A6/B5 图 + 计算数据报告。
数据源：E题/clean_data/*_clean.csv（唯一源）。输出：q1/data_Q1/q1_time_*.csv + q1/charts_Q1/q1_t* + q1/data_Q1/计算数据报告_投放时间.md
口径：先汇总再相除；CPA仅公司日度；HE=假日均值/同星期对照均值-1；回归ln(R+1)。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from scipy import stats as sstats
import matplotlib.patheffects as pe
from style_q1 import (apply_style, OI, FIG_W_FULL, MM, INK, INK2, MUTED, GRID, REF,
                      new_fig, style_axes, save_fig)

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EROOT = os.path.dirname(ROOT)
CD = os.path.join(EROOT, "clean_data")
DOUT = os.path.join(ROOT, "data_Q1")
COUT = os.path.join(ROOT, "charts_Q1")
os.makedirs(DOUT, exist_ok=True)
os.makedirs(COUT, exist_ok=True)

# ---------- 0. 底表 ----------
s1 = pd.read_csv(os.path.join(CD, "sheet1_投放记录_clean.csv"), encoding="utf-8-sig")
s2 = pd.read_csv(os.path.join(CD, "sheet2_日注册_clean.csv"), encoding="utf-8-sig")
dim = pd.read_csv(os.path.join(CD, "dim_date_时间维度.csv"), encoding="utf-8-sig")
c_date, c_pid, c_uid = s1.columns[0], s1.columns[1], s1.columns[2]
c_imp, c_clk, c_spd = s1.columns[3], s1.columns[4], s1.columns[5]
s1[c_date] = pd.to_datetime(s1[c_date])
s2.columns = ["日期", "新注册数", "日总消费", "日CPA"] if s2.shape[1] == 4 else list(s2.columns)
s2["日期"] = pd.to_datetime(s2["日期"])
dim["日期"] = pd.to_datetime(dim["日期"])

daily = s1.groupby(c_date, as_index=False).agg({c_spd: "sum", c_clk: "sum", c_imp: "sum"})
daily.columns = ["日期", "日消费", "日点击", "日展现"]
# 每日活跃单元数（仅计当日消费额>0的单元） + 每日最大单元占比
act = s1.loc[s1[c_spd] > 0].groupby(c_date)[c_uid].nunique().reset_index()
act.columns = ["日期", "活跃单元数"]
sh = s1.groupby([c_date, c_uid])[c_spd].sum().reset_index()
sh.columns = ["日期", "单元", "消费"]
sh["日总"] = sh.groupby("日期")["消费"].transform("sum")
sh["占比"] = sh["消费"] / sh["日总"]
mx = sh.groupby("日期")["占比"].max().reset_index()
mx.columns = ["日期", "最大单元占比"]
daily = daily.merge(s2[["日期", "新注册数"]], on="日期", how="left")
daily = daily.merge(act, on="日期", how="left").merge(mx, on="日期", how="left")
daily = daily.merge(dim, on="日期", how="left")
daily = daily.sort_values("日期").reset_index(drop=True)
daily["CTR"] = daily["日点击"] / daily["日展现"].replace(0, np.nan)
daily["CPC"] = daily["日消费"] / daily["日点击"].replace(0, np.nan)
daily["CPA"] = daily["日消费"] / daily["新注册数"].replace(0, np.nan)
daily["消费MA7"] = daily["日消费"].rolling(7, center=True).mean()
daily["注册MA7"] = daily["新注册数"].rolling(7, center=True).mean()
daily["月份"] = daily["日期"].dt.month
TOTAL_SPEND, TOTAL_CLK = float(daily["日消费"].sum()), float(daily["日点击"].sum())
CPC_ALL = TOTAL_SPEND / TOTAL_CLK
print(f"对账: 总消费={TOTAL_SPEND:.2f} 总点击={TOTAL_CLK:.0f} CPC={CPC_ALL:.4f} 天数={len(daily)}")
print(f"日均活跃单元={daily['活跃单元数'].mean():.2f} 最大单元占比均值={daily['最大单元占比'].mean()*100:.1f}%")
peak = daily.loc[daily["日消费"].idxmax()]
print(f"消费峰: {peak['日期'].date()} {peak['日消费']:.2f}元 点击{peak['日点击']:.0f} CPA{peak['CPA']:.2f}")

# 单元投放天数（clean_data统一口径）
udays = s1.groupby(c_uid)[c_date].nunique().reset_index()
udays.columns = ["推广单元ID", "投放天数"]
us = s1.groupby(c_uid).agg(spd=(c_spd, "sum"), clk=(c_clk, "sum")).reset_index()
us.columns = ["推广单元ID", "消费", "点击"]
us["CPC"] = us["消费"] / us["点击"]
udays = udays.merge(us, on="推广单元ID")
udays["投放频率"] = udays["投放天数"] / 365
udays.to_csv(os.path.join(DOUT, "q1_time_unit_days.csv"), index=False, encoding="utf-8-sig")

# ---------- 1. 月度表A2 ----------
m = daily.groupby("月份").agg(消费=("日消费", "sum"), 点击=("日点击", "sum"),
      展现=("日展现", "sum"), 注册=("新注册数", "sum"), 天数=("日期", "count"),
      活跃单元=("活跃单元数", "mean"))
m["日均消费"] = m["消费"] / m["天数"]
m["CTR"] = m["点击"] / m["展现"]
m["CPC"] = m["消费"] / m["点击"]
m["日均注册"] = m["注册"] / m["天数"]
m["CPA"] = m["消费"] / m["注册"]
m.reset_index().to_csv(os.path.join(DOUT, "q1_time_monthly.csv"), index=False, encoding="utf-8-sig")

# ---------- 2. 星期表A3 + KW ----------
ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
w = daily.groupby("星期").agg(消费=("日消费", "sum"), 点击=("日点击", "sum"),
    展现=("日展现", "sum"), 注册=("新注册数", "sum"), 天数=("日期", "count"),
    活跃单元=("活跃单元数", "mean"), 日均消费=("日消费", "mean"), 日均注册=("新注册数", "mean"))
w["CTR"] = w["点击"] / w["展现"]
w["CPC"] = w["消费"] / w["点击"]
w["CPA"] = w["消费"] / w["注册"]
w = w.reindex(ORDER)
w.reset_index().to_csv(os.path.join(DOUT, "q1_time_weekday.csv"), index=False, encoding="utf-8-sig")
kw_rows = []
for var in ["日消费", "CPA", "CTR", "CPC", "活跃单元数"]:
    arr = [daily.loc[daily["星期"] == d, var].dropna().values for d in ORDER]
    H, p = sstats.kruskal(*arr).statistic, sstats.kruskal(*arr).pvalue
    kw_rows.append(dict(变量=var, H=H, p=p, 显著=(p < 0.05)))
kw = pd.DataFrame(kw_rows)
kw.to_csv(os.path.join(DOUT, "q1_time_weekday_kw.csv"), index=False, encoding="utf-8-sig")
print(kw.to_string(index=False))

# ---------- 3. 假日HE（同星期±4周对照） ----------
HOL = {"春节": pd.date_range("2025-01-28", "2025-02-04"),
       "清明节": pd.date_range("2025-04-04", "2025-04-06"),
       "劳动节": pd.date_range("2025-05-01", "2025-05-05"),
       "端午节": pd.date_range("2025-05-31", "2025-06-02"),
       "国庆中秋": pd.date_range("2025-10-01", "2025-10-08")}
didx = daily.set_index("日期")
he_rows = []
for name, dr in HOL.items():
    hd = didx.loc[didx.index.isin(dr)]
    ctrl = []
    for d in dr:
        wd = d.weekday()
        cands = daily[(daily["日期"] >= d - pd.Timedelta(days=28)) &
                      (daily["日期"] <= d + pd.Timedelta(days=28)) &
                      (daily["日期"].dt.weekday == wd) &
                      (daily["三态标签"] == "正常")]
        ctrl.append(cands)
    ctrl = pd.concat(ctrl).drop_duplicates() if ctrl else daily.iloc[0:0]
    row = {"假日": name, "天数": len(hd)}
    for col in ["日消费", "日点击", "日展现", "新注册数", "CPC", "CPA"]:
        hv = hd[col].mean()
        cv = ctrl[col].mean() if len(ctrl) else np.nan
        row[col + "_假日均值"] = hv
        row[col + "_对照均值"] = cv
        row[col + "_HE"] = (hv / cv - 1) if (cv and cv == cv and cv != 0) else np.nan
    he_rows.append(row)
he = pd.DataFrame(he_rows)
he.to_csv(os.path.join(DOUT, "q1_time_holiday_he.csv"), index=False, encoding="utf-8-sig")
print(he[[c for c in he.columns if c.endswith("_HE")]].round(4).to_string(index=False))

# ---------- 4. 滞后相关A5 ----------
lags = list(range(8))
rhos = []
C, R = daily["日消费"].values, daily["新注册数"].values
for L in lags:
    if L == 0:
        r = float(pd.Series(C).corr(pd.Series(R)))
    else:
        r = float(pd.Series(C[:-L]).corr(pd.Series(R[L:])))
    rhos.append(r)
lagdf = pd.DataFrame({"滞后日": lags, "Pearson_r": rhos})
lagdf.to_csv(os.path.join(DOUT, "q1_time_lagcorr.csv"), index=False, encoding="utf-8-sig")
print(lagdf.to_string(index=False))

# ---------- 5. 回归A6 ----------
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson
reg = daily.copy()
reg["t"] = np.arange(len(reg)) / (len(reg) - 1)
reg["lnR"] = np.log(reg["新注册数"] + 1)
reg["lnC"] = np.log(reg["日消费"] + 1)
reg["lnC1"] = np.log(reg["日消费"].shift(1) + 1)
reg["H"] = (reg["三态标签"] == "放假").astype(int)
wd_dum = pd.get_dummies(reg["星期"], prefix="W", drop_first=False)
# 以星期一为参照
wd_dum = wd_dum.drop(columns=["W_星期一"]) if "W_星期一" in wd_dum.columns else wd_dum.iloc[:, 1:]
X1 = pd.concat([reg[["lnC", "t", "H"]], wd_dum], axis=1).astype(float)
X1 = sm.add_constant(X1)
y = reg["lnR"].astype(float)
res1 = sm.OLS(y, X1).fit(cov_type="HAC", cov_kwds={"maxlags": 7, "use_correction": True})
reg2 = reg.iloc[1:].copy()
X2 = pd.concat([reg2[["lnC", "lnC1", "t", "H"]], wd_dum.loc[reg2.index]], axis=1).astype(float)
X2 = sm.add_constant(X2)
y2 = reg2["lnR"].astype(float)
res2 = sm.OLS(y2, X2).fit(cov_type="HAC", cov_kwds={"maxlags": 7, "use_correction": True})


def vif_table(X):
    return pd.DataFrame({"变量": X.columns,
        "VIF": [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]})


fit = pd.DataFrame([{"模型": "模型1_不含滞后", "n": int(res1.nobs), "R2": res1.rsquared,
    "adjR2": res1.rsquared_adj, "AIC": res1.aic, "BIC": res1.bic,
    "DW": durbin_watson(res1.resid)},
    {"模型": "模型2_含滞后1日", "n": int(res2.nobs), "R2": res2.rsquared,
    "adjR2": res2.rsquared_adj, "AIC": res2.aic, "BIC": res2.bic,
    "DW": durbin_watson(res2.resid)}])
fit.to_csv(os.path.join(DOUT, "q1_time_reg_fit.csv"), index=False, encoding="utf-8-sig")


def coef_df(res, name):
    ci = res.conf_int(alpha=0.05)
    return pd.DataFrame({"模型": name, "变量": res.params.index, "系数": res.params.values,
        "HAC标准误": res.bse.values, "p值": res.pvalues.values,
        "CI下": ci.iloc[:, 0].values, "CI上": ci.iloc[:, 1].values})


coef = pd.concat([coef_df(res1, "模型1"), coef_df(res2, "模型2")], ignore_index=True)
coef.to_csv(os.path.join(DOUT, "q1_time_reg_coef.csv"), index=False, encoding="utf-8-sig")
vif_table(X1).to_csv(os.path.join(DOUT, "q1_time_reg_vif1.csv"), index=False, encoding="utf-8-sig")
vif_table(X2).to_csv(os.path.join(DOUT, "q1_time_reg_vif2.csv"), index=False, encoding="utf-8-sig")
print(fit.round(4).to_string(index=False))
print(coef[coef["变量"].isin(["lnC", "lnC1", "t", "H", "const"])].round(4).to_string(index=False))
daily.to_csv(os.path.join(DOUT, "q1_time_daily.csv"), index=False, encoding="utf-8-sig")

# ================= 数据合理性核验 =================
# 与 bid_budget_analysis.py 相同的核验口径：先汇总再相除、除零记空、对账唯一数据源。
print("\n【数据合理性核验】")
_dd = daily.copy()
_dd["日期"] = pd.to_datetime(_dd["日期"])
_alldays = pd.DatetimeIndex(pd.date_range("2025-01-01", "2025-12-31"))
_missing = _alldays.difference(pd.Index(_dd["日期"]))
_extra = pd.Index(_dd["日期"]).difference(_alldays)
print(f"  天数={len(_dd)}  日期范围={_dd['日期'].min().date()}~{_dd['日期'].max().date()}")
print(f"  缺失自然日={len(_missing)}  多余日期={len(_extra)}  重复日期={int(_dd['日期'].duplicated().sum())}")
print(f"  对账: 总消费={_dd['日消费'].sum():.2f} (源={TOTAL_SPEND:.2f}, 差={_dd['日消费'].sum()-TOTAL_SPEND:+.4f})")
print(f"  对账: 总点击={_dd['日点击'].sum():.0f} (源={TOTAL_CLK:.0f}, 差={_dd['日点击'].sum()-TOTAL_CLK:+.0f})")
print(f"  对账: 总注册={_dd['新注册数'].sum():.0f} (源sheet2={pd.to_numeric(s2['新注册数'], errors='coerce').sum():.0f})")
_neg = int((_dd[["日消费", "日点击", "日展现", "新注册数"]] < 0).sum().sum())
_clk_gt_imp = int((_dd["日点击"] > _dd["日展现"]).sum())
_zero = {k: int((_dd[k] == 0).sum()) for k in ["日消费", "日点击", "日展现", "新注册数"]}
print(f"  负值行数={_neg}  点击>展现行数={_clk_gt_imp}  零值行数={_zero}")
print(f"  CTR/CPC/CPA 缺失数: {int(_dd['CTR'].isna().sum())}/{int(_dd['CPC'].isna().sum())}/{int(_dd['CPA'].isna().sum())}")
_lowr = _dd[_dd["新注册数"] <= 3]
print(f"  注册数≤3的日数={len(_lowr)} (CPA不稳的极端日, 建议用7日MA)")
if len(_lowr):
    _worst = _lowr.loc[_lowr["CPA"].idxmax()]
    print(f"    CPA极端值: {_worst['日期'].date()} 注册{_worst['新注册数']:.0f}人 → CPA={_worst['CPA']:.2f}元")
print(f"  三态标签: {_dd['三态标签'].value_counts().to_dict()}")
print(f"  星期×日数: {_dd['星期'].value_counts().reindex(ORDER).to_dict()}")
print(f"  月×日数范围: {_dd.groupby('月份')['日期'].nunique().min()}~{_dd.groupby('月份')['日期'].nunique().max()} 天/月")

# ================= 图 =================
# 图风格对齐 bid_budget_analysis.py：白底无3D、去上右边框、浅色网格、脚注、300dpi。

# A1 节奏：上下两幅共享x（消费 / 注册，各+MA7）
fig, axes = plt.subplots(2, 1, figsize=(FIG_W_FULL, 118 * MM), sharex=True)
for _ax in axes:
    style_axes(_ax)
axes[0].plot(daily["日期"], daily["日消费"], color=OI["grey"], lw=0.7, alpha=0.6, label="日消费")
axes[0].plot(daily["日期"], daily["消费MA7"], color=OI["blue"], lw=1.6, label="7日中心均线")
axes[0].set_ylabel("日消费（元）", color=INK)
axes[0].set_title("(a) 日消费节奏", fontsize=9.5, color=INK, pad=8)
axes[0].annotate(f"{peak['日期'].date()} 峰 {peak['日消费']:.0f}元",
                 (peak["日期"], peak["日消费"]), xytext=(8, 16),
                 textcoords="offset points", fontsize=8, color=INK,
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
axes[0].legend(frameon=False, fontsize=8, loc="upper left")
_rp = daily.loc[daily["新注册数"].idxmax()]
axes[1].plot(daily["日期"], daily["新注册数"], color=OI["grey"], lw=0.7, alpha=0.6, label="日注册")
axes[1].plot(daily["日期"], daily["注册MA7"], color=OI["orange"], lw=1.6, label="7日中心均线")
axes[1].set_ylabel("日注册（人）", color=INK)
axes[1].set_title("(b) 日注册节奏", fontsize=9.5, color=INK, pad=8)
axes[1].annotate(f"{_rp['日期'].date()} 峰 {_rp['新注册数']:.0f}人",
                 (_rp["日期"], _rp["新注册数"]), xytext=(8, 16),
                 textcoords="offset points", fontsize=8, color=INK,
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
axes[1].legend(frameon=False, fontsize=8, loc="upper left")
for _ax in axes:
    _ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    _ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
fig.suptitle("全年投放节奏与注册节奏（分轴绘制，量纲不同不共轴）", fontsize=11, color=INK)
fig.text(0.5, 0.015, "注：灰线为日度原始值，彩色线为 7 日中心移动平均；消费峰与注册峰分别标注。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=[0, 0.03, 1, 1])
save_fig(fig, "q1_t1_全年节奏", COUT)

# A2 月度双面板
mo = m.reset_index()
fig, axes = plt.subplots(1, 2, figsize=(FIG_W_FULL, 92 * MM))
ax = axes[0]
style_axes(ax)
bars = ax.bar(mo["月份"], mo["日均消费"], color=OI["blue"], edgecolor="white",
              linewidth=0.8, width=0.66, label="日均消费", zorder=3)
for _x, _v in zip(mo["月份"], mo["日均消费"]):
    ax.text(_x, _v, f"{_v:.0f}", ha="center", va="bottom", fontsize=7, color=INK2)
ax2 = ax.twinx()
ax2.plot(mo["月份"], mo["活跃单元"], "o-", color=OI["vermillion"], lw=1.6,
         markersize=4, label="月均活跃单元")
ax.set_xlabel("月份", color=INK)
ax.set_ylabel("日均消费（元）", color=OI["blue"])
ax2.set_ylabel("月均活跃单元数", color=OI["vermillion"])
ax.set_title("(a) 月度投入强度", fontsize=9.5, color=INK, pad=8)
ax.set_xticks(range(1, 13))
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_color(OI["vermillion"])
ax2.tick_params(colors=OI["vermillion"], labelsize=8)
ax = axes[1]
style_axes(ax)
ax.plot(mo["月份"], mo["CPC"], "o-", color=OI["blue"], lw=1.6, markersize=4, label="CPC")
ax.plot(mo["月份"], mo["CPA"], "s-", color=OI["vermillion"], lw=1.6, markersize=4, label="CPA")
for _x, _v in zip(mo["月份"], mo["CPC"]):
    ax.text(_x, _v, f"{_v:.2f}", ha="center", va="bottom", fontsize=6.5, color=OI["blue"])
for _x, _v in zip(mo["月份"], mo["CPA"]):
    ax.text(_x, _v, f"{_v:.1f}", ha="center", va="bottom", fontsize=6.5, color=OI["vermillion"])
ax.set_xlabel("月份", color=INK)
ax.set_ylabel("元", color=INK)
ax.set_title("(b) 月度 CPC 与 CPA", fontsize=9.5, color=INK, pad=8)
ax.set_xticks(range(1, 13))
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.suptitle("月度投放与效益", fontsize=11, color=INK)
fig.text(0.5, 0.015, "注：日均消费=月消费/月天数；CPA 为公司日度代理口径（不拆单元），先汇总再相除。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=[0, 0.03, 1, 1])
save_fig(fig, "q1_t2_月度投放效益", COUT)

# A3 星期分组柱
wv = w.reset_index()
fig, axes = plt.subplots(1, 2, figsize=(FIG_W_FULL, 92 * MM))
xw = np.arange(7)
labels_w = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
for _ax in axes:
    style_axes(_ax)
axes[0].bar(xw, wv["日均消费"], color=OI["blue"], edgecolor="white", linewidth=0.8, width=0.62)
for _x, _v in zip(xw, wv["日均消费"]):
    axes[0].text(_x, _v, f"{_v:.0f}", ha="center", va="bottom", fontsize=7, color=INK2)
axes[0].set_xticks(xw); axes[0].set_xticklabels(labels_w)
axes[0].set_ylabel("日均消费（元）", color=INK)
axes[0].set_title("(a) 星期 × 日均消费", fontsize=9.5, color=INK, pad=8)
axes[0].grid(axis="y")
axes[1].bar(xw, wv["CPA"], color=OI["vermillion"], edgecolor="white", linewidth=0.8, width=0.62)
for _x, _v in zip(xw, wv["CPA"]):
    axes[1].text(_x, _v, f"{_v:.1f}", ha="center", va="bottom", fontsize=7, color=INK2)
axes[1].set_xticks(xw); axes[1].set_xticklabels(labels_w)
axes[1].set_ylabel("CPA（元/人）", color=INK)
axes[1].set_title("(b) 星期 × CPA", fontsize=9.5, color=INK, pad=8)
axes[1].grid(axis="y")
kwtag = "KW: " + "  ".join([f"{r['变量']}{'**' if r['p']<0.01 else ('*' if r['p']<0.05 else 'ns')}" for _, r in kw.iterrows()])
fig.suptitle(f"星期效应（{kwtag}）", fontsize=11, color=INK)
fig.text(0.5, 0.015, "注：* p<0.05，** p<0.01（Kruskal-Wallis，ns 不显著）；CPC 与活跃单元数星期差异不显著，差异主要来自预算强度。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=[0, 0.05, 1, 1])
save_fig(fig, "q1_t3_星期效应", COUT)

# A4 假日HE分组条形
he_cols = ["日消费_HE", "日点击_HE", "日展现_HE", "新注册数_HE", "CPC_HE", "CPA_HE"]
he2 = he.set_index("假日")[he_cols]
he2.columns = ["消费", "点击", "展现", "注册", "CPC", "CPA"]
fig, ax = new_fig(FIG_W_FULL, 95 * MM)
x = np.arange(len(he2))
wd = 0.12
he_colors = [OI["blue"], OI["sky"], OI["grey"], OI["orange"], OI["vermillion"], OI["purple"]]
for i, (c, _col) in enumerate(zip(he2.columns, he_colors)):
    ax.bar(x + (i - 2.5) * wd, he2[c] * 100, width=wd, label=c, color=_col,
           edgecolor="white", linewidth=0.5)
ax.axhline(0, color=INK2, lw=1.0)
ax.set_xticks(x); ax.set_xticklabels(he2.index)
ax.set_ylabel("相对同星期对照变化率（%）", color=INK)
ax.set_title("假日效应：相对同星期对照的变化率 HE", fontsize=11, color=INK, pad=10)
ax.legend(ncol=6, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.10), frameon=False)
fig.text(0.5, 0.02, "注：HE = 假日日均值 / 同星期±4周正常日对照均值 − 1；消费/点击/展现/注册为流量强度，CPC/CPA 为成本效率。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.subplots_adjust(left=0.10, right=0.97, top=0.90, bottom=0.22)
save_fig(fig, "q1_t4_假日HE", COUT)

# A5 滞后柱
fig, ax = new_fig(FIG_W_FULL, 80 * MM)
ax.bar(lagdf["滞后日"], lagdf["Pearson_r"], color=OI["blue"], edgecolor="white",
       linewidth=0.8, width=0.62, zorder=3)
for i, v in enumerate(lagdf["Pearson_r"]):
    ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=8, color=INK,
            path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
ax.set_xlabel("滞后天数 l（Corr(C_t, R_{t+l})）", color=INK)
ax.set_ylabel("Pearson 相关系数", color=INK)
ax.set_title("投入与注册的同步与滞后关系", fontsize=11, color=INK, pad=10)
ax.set_xticks(lags)
ax.set_ylim(0, 1.0)
fig.text(0.5, 0.03, "注：l=0 当日相关最强(0.82)；l=1 回落(0.61)；l=6~7 回升系星期周期，不解释为因果。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.subplots_adjust(left=0.10, right=0.97, top=0.90, bottom=0.18)
save_fig(fig, "q1_t5_滞后相关", COUT)

# A6a forest（关键系数）
key = coef[coef["变量"].isin(["lnC", "lnC1", "t", "H"])].copy()
lab = {"lnC": "当日消费弹性", "lnC1": "滞后1日消费", "t": "线性趋势", "H": "总体假日"}
key["标签"] = key["模型"] + "_" + key["变量"].map(lab)
key = key.sort_values("系数")
fig, ax = new_fig(FIG_W_FULL, 80 * MM)
y = np.arange(len(key))
ax.errorbar(key["系数"], y, xerr=[key["系数"] - key["CI下"], key["CI上"] - key["系数"]],
            fmt="o", color=OI["blue"], ecolor=INK2, capsize=3, markersize=5)
ax.axvline(0, color=INK2, lw=1.0, ls="--")
ax.set_yticks(y)
ax.set_yticklabels(key["标签"])
ax.set_xlabel("系数（HAC 95% CI）", color=INK)
ax.set_title("回归关键系数 forest（正文用模型1）", fontsize=11, color=INK, pad=10)
fig.text(0.5, 0.03, "注：系数为 ln(注册+1) 对 ln(消费+1) 的半弹性；HAC(Newey-West, maxlags=7) 稳健标准误；正文使用模型1。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.subplots_adjust(left=0.22, right=0.97, top=0.90, bottom=0.18)
save_fig(fig, "q1_t6a_回归forest", COUT)

# A6b 诊断（模型1）：残差-拟合 / QQ / 残差时序 / 尺度位置
from scipy.stats import probplot
resid, fitted = res1.resid.values, res1.fittedvalues.values
fig, axes = plt.subplots(2, 2, figsize=(FIG_W_FULL, 106 * MM))
for _ax in axes.ravel():
    style_axes(_ax)
axes[0, 0].scatter(fitted, resid, s=10, alpha=0.5, color=OI["blue"])
axes[0, 0].axhline(0, color=INK2, lw=1)
axes[0, 0].set_title("(a) 残差-拟合", fontsize=9, color=INK)
axes[0, 0].set_xlabel("拟合值"); axes[0, 0].set_ylabel("残差")
(theo, ordered), (_slope, _icept, _r) = probplot(resid, dist="norm")
axes[0, 1].scatter(theo, ordered, s=10, alpha=0.5, color=OI["blue"])
axes[0, 1].plot(theo, _slope * np.array(theo) + _icept, color=INK2, lw=1.2)
axes[0, 1].set_title("(b) 正态 QQ", fontsize=9, color=INK)
axes[1, 0].plot(daily["日期"], resid, color=OI["vermillion"], lw=0.9)
axes[1, 0].axhline(0, color=INK2, lw=1)
axes[1, 0].set_title(f"(c) 残差时序（DW={durbin_watson(resid):.2f}，正自相关→用HAC）", fontsize=9, color=INK)
axes[1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
std_r = resid / np.std(resid)
axes[1, 1].scatter(fitted, np.sqrt(np.abs(std_r)), s=10, alpha=0.5, color=OI["blue"])
axes[1, 1].set_title("(d) 尺度-位置", fontsize=9, color=INK)
axes[1, 1].set_xlabel("拟合值"); axes[1, 1].set_ylabel("sqrt(|标准化残差|)")
fig.suptitle("模型1 回归诊断", fontsize=11, color=INK)
fig.tight_layout(rect=[0, 0, 1, 0.97])
save_fig(fig, "q1_t6b_回归诊断", COUT)

# B5 日集中度直方
fig, ax = new_fig(FIG_W_FULL, 80 * MM)
ax.hist(daily["最大单元占比"] * 100, bins=20, color=OI["blue"], edgecolor="white",
        linewidth=0.8, zorder=3)
mn = daily["最大单元占比"].mean() * 100
ax.axvline(mn, color=INK2, lw=1.5, ls="--")
ax.text(mn + 1, ax.get_ylim()[1] * 0.9, f"均值 {mn:.1f}%", fontsize=8, color=INK,
        path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
ax.set_xlabel("每日最大单元预算占比（%）", color=INK)
ax.set_ylabel("天数", color=INK)
ax.set_title("日度预算集中度分布", fontsize=11, color=INK, pad=10)
fig.text(0.5, 0.03, "注：每日取消费额最大单元的预算占比；均值约 " + f"{mn:.1f}%" + "，反映日度预算向头部单元集中。",
         ha="center", va="top", fontsize=7.5, color=MUTED)
fig.subplots_adjust(left=0.10, right=0.97, top=0.90, bottom=0.18)
save_fig(fig, "q1_b5_日集中度", COUT)

print("ALL TIME DONE")
