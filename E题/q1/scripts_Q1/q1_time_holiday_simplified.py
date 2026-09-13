# -*- coding: utf-8 -*-
"""
Q1「时间与假日效应·简化分析」完整方案
================================================================================
设计基座 100% 沿用 time_pattern_charts.py（白底 / 去上右边框 / 浅灰网格 /
Microsoft YaHei / 标题15pt / 轴标签12.5pt / 刻度10.5pt / 标注9.5pt / 300dpi）。
数据源：data_Q1/q1_time_daily.csv（365 天，三态日历 正常332/放假28/补班5）。

产出（均为新文件名，不覆盖任何已有图/表）：
  图 F10 时间·周末·假日效应四联图      （对应 docx 图1）
  图 F1b 日度消费与注册标准化趋势      （对应 docx 图2）
  图 F11 模型设定对比 + NW稳健性
  图 F7b 回归净效应forest（简化主模型）
  表 q1_time_spec_compare.csv          模型对比（简化A/修正B/完整C/完整D）
  表 q1_time_coef_main.csv             主模型+修正模型+滞后 系数表
  表 q1_time_fit_main.csv              主模型检验（VIF/经典F/HAC F/DW）
  表 q1_time_robustness.csv            稳健性汇总
  表 q1_time_nw_lag_sensitivity.csv    Newey-West 滞后阶数敏感性
  表 q1_time_per1k.csv                 每千元注册（两口径）
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as pe
from matplotlib import font_manager
from matplotlib.lines import Line2D
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor as _vif

BASE = os.path.dirname(os.path.abspath(__file__))
Q1 = os.path.dirname(BASE)
OUT_FIG = os.path.join(Q1, "charts_Q1")
OUT_DAT = os.path.join(Q1, "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

# ================================================================ 1. 设计基座（沿用原图）
def set_cjk_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
                 "Source Han Sans SC", "PingFang SC", "WenQuanYi Micro Hei"]:
        if name in have:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("未找到可用中文字体")
FONT = set_cjk_font()

BLUE, ORANGE, GREEN, PURPLE, PINK = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#c2185b"
INK, INK2, MUTED, GRID, REF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#9a9890"
GREY = "#8a8a8a"
DPI = 300
plt.rcParams.update({"font.size": 10.5, "axes.unicode_minus": False,
                     "pdf.fonttype": 42, "savefig.dpi": DPI})

def _style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2); ax.spines[s].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)

def style(ax):
    _style(ax); return ax

def new_fig(w=10.4, h=7.4):
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor="white")
    ax = fig.add_subplot(111); _style(ax)
    return fig, ax

def save(fig, name):
    p = os.path.join(OUT_FIG, name + ".png")
    fig.savefig(p, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    log("  已保存: %s" % p)
    return p

def foot(ax, text, y=-0.155):
    return ax.text(0.5, y, text, transform=ax.transAxes, ha="center", va="top",
                   fontsize=9, color=MUTED)

# ================================================================ 2. 数据
d = pd.read_csv(os.path.join(OUT_DAT, "q1_time_daily.csv"))
d.columns = ["date", "spend", "click", "imp", "reg", "act", "maxshr", "weekday",
             "month", "iswe", "tag", "CTR", "CPC", "CPA", "spMA7", "rgMA7"]
d["date"] = pd.to_datetime(d["date"])
d = d.sort_values("date").reset_index(drop=True)
d["t"] = np.arange(1, len(d) + 1)
d["lnR"] = np.log(d["reg"] + 1); d["lnC"] = np.log(d["spend"] + 1)
d["lnC1"] = d["lnC"].shift(1)
d["H"] = (d["tag"] == "放假").astype(int)
d["MK"] = (d["tag"] == "补班").astype(int)
d["W"] = d["iswe"].astype(int)
d["Wc"] = ((d["iswe"] == 1) & (d["MK"] == 0)).astype(int)
d["isMon"] = (d["weekday"] == "星期一").astype(int)
WD = pd.get_dummies(d["weekday"], prefix="Wd", drop_first=True).astype(float)
d = pd.concat([d, WD], axis=1)
WDCOLS = list(WD.columns)
WLAB = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
HOL = {"春节": ("2025-01-28", "2025-02-04"), "清明节": ("2025-04-04", "2025-04-06"),
       "劳动节": ("2025-05-01", "2025-05-05"), "端午节": ("2025-05-31", "2025-06-02"),
       "国庆中秋": ("2025-10-01", "2025-10-08")}
log("[数据] %d 天；三态 %s" % (len(d), d["tag"].value_counts().to_dict()))

# 是否周末/假日 的 3 类（补班归工作日）
def d3(row):
    if row["tag"] == "放假":
        return "法定节假日"
    if row["MK"] == 1:
        return "工作日"
    return "周末" if row["iswe"] == 1 else "工作日"
d["日型"] = d.apply(d3, axis=1)

# ================================================================ 3. 模型
def hac(X, y, nl=7):
    return sm.OLS(y.astype(float), sm.add_constant(X.astype(float))).fit(
        cov_type="HAC", cov_kwds={"maxlags": nl, "use_correction": True})

SPECS = {
    "A_简化(docx主模型)": ["lnC", "t", "W", "H"],
    "B_修正(补班+周一)": ["lnC", "t", "Wc", "MK", "isMon", "H"],
    "C_完整6星期": ["lnC", "t", "H"] + WDCOLS,
    "D_完整+补班+周一": ["lnC", "t", "H", "MK", "isMon"] + WDCOLS,
}

def classicF(m, k):
    n = m.nobs
    return (m.rsquared / k) / ((1 - m.rsquared) / (n - k - 1))

fits = {}
for name, cols in SPECS.items():
    fits[name] = (hac(d[cols], d["lnR"]), cols)

# ---- 表：模型对比 ----
rows = []
for name, (m, cols) in fits.items():
    k = len(cols)
    wk = "W" if "W" in cols else ("Wc" if "Wc" in cols else None)
    wcoef = m.params[wk] if wk else np.nan
    wp = m.pvalues[wk] if wk else np.nan
    rows.append({"设定": name, "变量数k": k, "R2": m.rsquared, "adjR2": m.rsquared_adj,
                 "AIC": m.aic, "BIC": m.bic, "经典F": classicF(m, k),
                 "消费弹性lnC": m.params["lnC"], "p_lnC": m.pvalues["lnC"],
                 "周末系数": wcoef, "p_周末": wp,
                 "周末注册变化%": (np.exp(wcoef) - 1) * 100 if not np.isnan(wcoef) else np.nan,
                 "假日H": m.params["H"], "p_假日": m.pvalues["H"]})
spec_cmp = pd.DataFrame(rows)
spec_cmp.round(6).to_csv(os.path.join(OUT_DAT, "q1_time_spec_compare.csv"),
                         index=False, encoding="utf-8-sig")
log("\n===== 表 模型对比 =====")
log(spec_cmp.round(4).to_string(index=False))

# ---- 表：主模型系数（A / B / A+滞后1日）----
mA = fits["A_简化(docx主模型)"][0]
mB = fits["B_修正(补班+周一)"][0]
d2 = d.iloc[1:].copy()
mL = hac(d2[["lnC", "lnC1", "t", "W", "H"]], d2["lnR"])
LAB = {"const": "常数项", "lnC": "当日消费弹性 lnC", "lnC1": "滞后1日消费 lnC1",
       "t": "时间趋势 T(原始序号)", "W": "周末 W", "Wc": "周末(非补班) Wc",
       "MK": "补班 MK", "isMon": "周一 isMon", "H": "法定节假日 H"}
rows = []
for nm, m in [("A_简化主模型", mA), ("A2_简化+滞后1日", mL), ("B_修正", mB)]:
    ci = m.conf_int(alpha=0.05)
    for v in m.params.index:
        if v.startswith("Wd_"):
            continue
        rows.append({"模型": nm, "变量": LAB.get(v, v), "系数": m.params[v],
                     "HAC标准误": m.bse[v], "t值": m.tvalues[v], "p值": m.pvalues[v],
                     "CI下": ci.loc[v, 0], "CI上": ci.loc[v, 1]})
coef_main = pd.DataFrame(rows)
coef_main.round(6).to_csv(os.path.join(OUT_DAT, "q1_time_coef_main.csv"),
                          index=False, encoding="utf-8-sig")
log("\n===== 表 主模型系数 =====")
log(coef_main.round(4).to_string(index=False))

# ---- 表：主模型检验 ----
Xa = sm.add_constant(d[SPECS["A_简化(docx主模型)"]].astype(float))
vifs = {c: _vif(Xa.values, i) for i, c in enumerate(Xa.columns)}
fit_main = pd.DataFrame([
    {"项目": "样本量 n", "值": "%d" % mA.nobs},
    {"项目": "R2", "值": "%.4f" % mA.rsquared},
    {"项目": "调整R2", "值": "%.4f" % mA.rsquared_adj},
    {"项目": "经典 F 检验", "值": "F=%.2f（p<0.001）" % classicF(mA, 4)},
    {"项目": "HAC 稳健 F", "值": "F=%.2f" % float(mA.fvalue)},
    {"项目": "Durbin-Watson", "值": "%.3f" % durbin_watson(mA.resid)},
    {"项目": "VIF(lnC)", "值": "%.3f" % vifs["lnC"]},
    {"项目": "VIF(t)", "值": "%.3f" % vifs["t"]},
    {"项目": "VIF(W)", "值": "%.3f" % vifs["W"]},
    {"项目": "VIF(H)", "值": "%.3f" % vifs["H"]},
    {"项目": "稳健标准误", "值": "Newey-West，滞后 7 阶"},
])
fit_main.to_csv(os.path.join(OUT_DAT, "q1_time_fit_main.csv"), index=False, encoding="utf-8-sig")
log("\n===== 表 主模型检验 =====")
log(fit_main.to_string(index=False))

# ---- 表：稳健性汇总 ----
def summ(label, m):
    wk = "W" if "W" in m.params.index else ("Wc" if "Wc" in m.params.index else None)
    return {"设定": label,
            "消费弹性lnC": m.params["lnC"], "p_lnC": m.pvalues["lnC"],
            "趋势T": m.params["t"], "p_T": m.pvalues["t"],
            "周末": m.params[wk] if wk else np.nan, "p_周末": m.pvalues[wk] if wk else np.nan,
            "假日H": m.params["H"], "p_假日": m.pvalues["H"],
            "R2": m.rsquared, "adjR2": m.rsquared_adj}
rob = [summ("基准·简化A", mA),
       summ("修正·补班+周一(B)", mB),
       summ("剔消费峰 3/19", hac(d[d.date != "2025-03-19"][SPECS["A_简化(docx主模型)"]],
                                d[d.date != "2025-03-19"]["lnR"])),
       summ("剔春节 1/28-2/4", hac(d[~d.date.between("2025-01-28", "2025-02-04")][SPECS["A_简化(docx主模型)"]],
                                  d[~d.date.between("2025-01-28", "2025-02-04")]["lnR"])),
       summ("剔补班 5 天", hac(d[d.MK == 0][["lnC", "t", "W", "H"]], d[d.MK == 0]["lnR"])),
       summ("+月度固定效应", hac(pd.concat([d[["lnC", "t", "W", "H"]],
                                            pd.get_dummies(d["month"], prefix="M", drop_first=True).astype(float)],
                                           axis=1), d["lnR"])),
       summ("NW滞后=14", hac(d[SPECS["A_简化(docx主模型)"]], d["lnR"], nl=14)),
       summ("NW滞后=21", hac(d[SPECS["A_简化(docx主模型)"]], d["lnR"], nl=21))]
rob = pd.DataFrame(rob)
rob.round(6).to_csv(os.path.join(OUT_DAT, "q1_time_robustness.csv"), index=False, encoding="utf-8-sig")
log("\n===== 表 稳健性汇总 =====")
log(rob.round(4).to_string(index=False))

# ---- 表：NW 滞后阶数敏感性 ----
rows = []
for nl in [0, 1, 7, 14, 21]:
    m = hac(d[SPECS["A_简化(docx主模型)"]], d["lnR"], nl=nl)
    rows.append({"NW滞后阶数": nl, "p_lnC": m.pvalues["lnC"], "p_T": m.pvalues["t"],
                 "p_周末W": m.pvalues["W"], "p_假日H": m.pvalues["H"],
                 "lnC": m.params["lnC"], "T": m.params["t"], "W": m.params["W"], "H": m.params["H"]})
nw = pd.DataFrame(rows)
nw.round(6).to_csv(os.path.join(OUT_DAT, "q1_time_nw_lag_sensitivity.csv"),
                   index=False, encoding="utf-8-sig")
log("\n===== 表 NW 滞后阶数敏感性 =====")
log(nw.round(4).to_string(index=False))

# ---- 表：每千元注册（两口径）----
def p1k(sub):
    return sub["reg"].sum() / sub["spend"].sum() * 1000
def p1k_mean(sub):
    return (sub["reg"] / sub["spend"] * 1000).mean()
norm = d[d["tag"] == "正常"]
rows = []
for lbl, sub in [("工作日（日历，docx用）", d[d.iswe == 0]), ("周末（日历，docx用）", d[d.iswe == 1]),
                 ("普通工作日（正常）", norm[norm.iswe == 0]), ("普通周末（正常）", norm[norm.iswe == 1]),
                 ("非节假日", d[d.tag != "放假"]), ("法定节假日", d[d.tag == "放假"])]:
    rows.append({"分组": lbl, "天数": len(sub),
                 "每千元注册_日均口径(docx)": p1k_mean(sub), "每千元注册_汇总口径(项目)": p1k(sub)})
per1k = pd.DataFrame(rows)
per1k.round(2).to_csv(os.path.join(OUT_DAT, "q1_time_per1k.csv"), index=False, encoding="utf-8-sig")
log("\n===== 表 每千元注册（两口径）=====")
log(per1k.round(2).to_string(index=False))

# ================================================================ 4. 图 F10 四联图（docx 图1）
fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6), dpi=DPI,
                         gridspec_kw={"hspace": 0.42, "wspace": 0.24})
for a in axes.ravel():
    style(a)

# (a) 月度标准化
ma = d.groupby("month").agg(消费=("spend", "mean"), 注册=("reg", "mean"))
z = lambda s: (s - s.mean()) / s.std()
ax = axes[0, 0]
ax.plot(ma.index, z(ma["消费"]), "o-", color=BLUE, lw=2.0, ms=5.5, label="月均广告投入（标准化）")
ax.plot(ma.index, z(ma["注册"]), "s--", color=ORANGE, lw=2.0, ms=5.0, label="月均新增注册（标准化）")
ax.axhline(0, color=REF, lw=1.0, ls=":")
ax.set_xticks(range(1, 13))
ax.set_xlabel("月份", fontsize=12.5, color=INK)
ax.set_ylabel("标准化值（z-score）", fontsize=12.5, color=INK)
ax.set_title("(a) 月均投入与注册同向波动", fontsize=12.5, color=INK, pad=10, loc="left")
ax.legend(frameon=False, fontsize=10, loc="lower left")

# (b) 工作日 vs 周末 每千元注册（docx 口径：日均比值求均值，日历分组）
ax = axes[0, 1]
labs = ["普通工作日", "普通周末"]
vals = [p1k_mean(d[d.iswe == 0]), p1k_mean(d[d.iswe == 1])]
ax.bar([0, 1], vals, width=0.55, color=[BLUE, ORANGE], edgecolor="white", lw=0.9, zorder=3)
for i, v in enumerate(vals):
    ax.text(i, v, "%.1f" % v, ha="center", va="bottom", fontsize=11, color=INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(labs, fontsize=11)
ax.set_ylim(0, max(vals) * 1.25)
ax.set_ylabel("每千元投入注册数（人）", fontsize=12.5, color=INK)
ax.set_title("(b) 工作日 vs 周末：每千元投入注册", fontsize=12.5, color=INK, pad=10, loc="left")
ax.annotate("周末比工作日 %.1f%%" % ((vals[1] / vals[0] - 1) * 100),
            xy=(0.5, max(vals) * 1.16), ha="center", fontsize=10.5, color=INK2)

# (c) 非假日 vs 假日（docx 口径）
ax = axes[1, 0]
labs = ["非节假日", "法定节假日"]
vals = [p1k_mean(d[d.tag != "放假"]), p1k_mean(d[d.tag == "放假"])]
ax.bar([0, 1], vals, width=0.55, color=[BLUE, PINK], edgecolor="white", lw=0.9, zorder=3)
for i, v in enumerate(vals):
    ax.text(i, v, "%.1f" % v, ha="center", va="bottom", fontsize=11, color=INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(labs, fontsize=11)
ax.set_ylim(0, max(vals) * 1.25)
ax.set_ylabel("每千元投入注册数（人）", fontsize=12.5, color=INK)
ax.set_title("(c) 非节假日 vs 法定节假日", fontsize=12.5, color=INK, pad=10, loc="left")
ax.annotate("假日比非假日 %+.1f%%" % ((vals[1] / vals[0] - 1) * 100),
            xy=(0.5, max(vals) * 1.16), ha="center", fontsize=10.5, color=INK2)

# (d) lnC-lnR 按日型着色
ax = axes[1, 1]
colmap = {"工作日": BLUE, "周末": ORANGE, "法定节假日": PINK}
for typ in ["工作日", "周末", "法定节假日"]:
    s = d[d["日型"] == typ]
    ax.scatter(s["lnC"], s["lnR"], s=20, color=colmap[typ], alpha=0.5,
               edgecolors="none", zorder=3, label="%s (n=%d)" % (typ, len(s)))
    if len(s) > 5:
        b, a0 = np.polyfit(s["lnC"], s["lnR"], 1)
        xs = np.linspace(s["lnC"].min(), s["lnC"].max(), 30)
        ax.plot(xs, a0 + b * xs, color=colmap[typ], lw=1.8, zorder=4)
ax.set_xlabel("日消费对数 $\\ln(C_t+1)$", fontsize=12.5, color=INK)
ax.set_ylabel("日注册对数 $\\ln(R_t+1)$", fontsize=12.5, color=INK)
ax.set_title("(d) 投入—注册关系（按日型）", fontsize=12.5, color=INK, pad=10, loc="left")
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
fig.suptitle("图1  时间·周末·假日效应的四个观察角度", fontsize=15, color=INK, y=0.975)
fig.text(0.5, 0.012,
         "注：面板(b)(c)采用与文档一致的『日均比值求均值』口径（每千元注册＝日均 1000×注册/消费）；"
         "若按项目『先汇总再相除』口径则为 工作日60.3 / 周末57.4、非假日59.6 / 假日70.2。",
         ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.075, right=0.985, top=0.90, bottom=0.11)
save(fig, "F10_时间周末假日效应四联图")

# ================================================================ 5. 图 F1b 日度标准化趋势（docx 图2）
fig, ax = new_fig(12.4, 4.8)
ax2 = ax
for name, (s0, s1) in HOL.items():
    ax.axvspan(pd.Timestamp(s0), pd.Timestamp(s1), color=ORANGE, alpha=0.10, lw=0, zorder=1)
zs = lambda s: (s - s.mean()) / s.std()
ax.plot(d["date"], zs(d["spend"]), color=BLUE, lw=1.5, zorder=4, label="日消费（标准化）")
ax.plot(d["date"], zs(d["reg"]), color=ORANGE, lw=1.5, zorder=4, label="日注册（标准化）")
ax.axhline(0, color=REF, lw=1.0, ls=":")
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
ax.set_ylabel("标准化值（z-score）", fontsize=12.5, color=INK)
ax.set_title("2025 年日消费与日注册量标准化趋势", fontsize=15, color=INK, pad=14)
ax.legend(frameon=False, fontsize=10.5, loc="upper left", ncol=2)
foot(ax, "注：两条曲线均经 z-score 标准化，只比较变化方向；橙底为法定假日窗口（春节/清明/劳动/端午/国庆中秋）。", y=-0.20)
fig.subplots_adjust(left=0.075, right=0.985, top=0.88, bottom=0.16)
save(fig, "F1b_日度消费注册标准化趋势")

# ================================================================ 6. 图 F11 设定对比 + NW 稳健性
fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.6), dpi=DPI,
                         gridspec_kw={"wspace": 0.30})
for a in axes:
    style(a)

# 左：forest  A vs B（日型类效应）
ax = axes[0]
rowdef = [("H", "法定节假日 H"), ("W", "周末"), ("MK", "补班"), ("isMon", "周一")]
rows = []
for key, lab in rowdef:
    for nm, m in [("A", mA), ("B", mB)]:
        k = key if key in m.params.index else ("Wc" if key == "W" and "Wc" in m.params.index else None)
        if k is None:
            continue
        ci = m.conf_int(alpha=0.05)
        rows.append(dict(lab=lab, model=nm, coef=m.params[k], lo=ci.loc[k, 0],
                         hi=ci.loc[k, 1], p=m.pvalues[k]))
fr = pd.DataFrame(rows)
order = ["法定节假日 H", "周末", "补班", "周一"]
ypos = {lab: i for i, lab in enumerate(order[::-1])}
colr = {"A": BLUE, "B": ORANGE}
off = {"A": 0.16, "B": -0.16}
for _, r in fr.iterrows():
    y = ypos[r["lab"]] + off[r["model"]]
    ax.plot([r["lo"], r["hi"]], [y, y], color=colr[r["model"]], lw=2.2, zorder=3)
    ax.plot(r["coef"], y, "o", color=colr[r["model"]], ms=7.5,
            markeredgecolor="white", markeredgewidth=1.2, zorder=4)
    ax.text(r["hi"] + 0.012, y, "%.3f%s" % (r["coef"], "*" if r["p"] < 0.05 else ""),
            va="center", fontsize=9, color=INK)
ax.axvline(0, color=INK2, ls="--", lw=1.2, zorder=2)
ax.set_yticks(list(ypos.values())); ax.set_yticklabels(list(ypos.keys()))
ax.set_xlabel("系数（HAC 95% 置信区间）", fontsize=12.5, color=INK)
ax.set_title("(a) 设定对比：简化A vs 修正B", fontsize=12.5, color=INK, pad=10, loc="left")
ax.set_xlim(fr["lo"].min() - 0.06, fr["hi"].max() + 0.12)
ax.legend(handles=[Line2D([], [], color=BLUE, lw=2.2, marker="o", label="A 简化（周末=日历周末）"),
                   Line2D([], [], color=ORANGE, lw=2.2, marker="o", label="B 修正（剔补班+周一单列）")],
          frameon=False, fontsize=9.5, loc="lower left")
ax.text(0.99, 0.02, "消费弹性 lnC：A=0.739、B=0.739（两设定一致，未画）",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=MUTED)

# 右：NW 滞后阶数敏感性
ax = axes[1]
lags = nw["NW滞后阶数"].values
for col, lab, cc in [("p_T", "时间趋势 T", GREY), ("p_周末W", "周末 W", ORANGE),
                     ("p_假日H", "法定节假日 H", PINK)]:
    ax.plot(lags, nw[col].values, "o-", color=cc, lw=2.0, ms=6, label=lab, zorder=4)
ax.axhline(0.05, color=PURPLE, ls="--", lw=1.4, zorder=3)
ax.text(lags[-1], 0.052, "5% 显著性线", ha="right", va="bottom", fontsize=9, color=PURPLE)
ax.set_xticks(lags)
ax.set_xlabel("Newey–West 滞后阶数", fontsize=12.5, color=INK)
ax.set_ylabel("p 值", fontsize=12.5, color=INK)
ax.set_ylim(0, 0.42)
ax.set_title("(b) 显著性对稳健标准误的敏感性", fontsize=12.5, color=INK, pad=10, loc="left")
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
ax.text(0.99, 0.02, "lnC 在所有滞后阶数下 p<0.001（未画）", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=9, color=MUTED)
fig.suptitle("模型设定与稳健性：周末显著性依赖补班/周一处理与 NW 阶数", fontsize=15, color=INK, y=0.975)
fig.subplots_adjust(left=0.11, right=0.985, top=0.86, bottom=0.15)
save(fig, "F11_模型设定对比与稳健性")

# ================================================================ 7. 图 F7b 回归净效应 forest（简化主模型口径）
rows = []
for nm, m in [("A_简化主模型", mA), ("A2_简化+滞后1日", mL)]:
    ci = m.conf_int(alpha=0.05)
    for v in ["lnC", "lnC1", "t", "W", "H"]:
        if v in m.params.index:
            rows.append(dict(模型=nm, 变量=v, 标签="%s · %s" % ("简化主模型" if nm.startswith("A_") else "简化+滞后1日", LAB[v]),
                             系数=m.params[v], 低=ci.loc[v, 0], 高=ci.loc[v, 1], p=m.pvalues[v]))
fr = pd.DataFrame(rows).iloc[::-1].reset_index(drop=True)
fig, ax = new_fig(10.4, 6.6)
colr = {"A_简化主模型": BLUE, "A2_简化+滞后1日": ORANGE}
for i, r in fr.iterrows():
    c = colr[r["模型"]]
    ax.plot([r["低"], r["高"]], [i, i], color=c, lw=2.2, zorder=3)
    ax.plot(r["系数"], i, "o", color=c, ms=8, markeredgecolor="white", markeredgewidth=1.2, zorder=4)
    ax.text(r["高"] + 0.02, i, "%.3f" % r["系数"] + ("*" if r["p"] < 0.05 else " (p=%.3f)" % r["p"]),
            va="center", fontsize=9.5, color=INK)
ax.axvline(0, color=INK2, ls="--", lw=1.2, zorder=2)
ax.set_yticks(np.arange(len(fr))); ax.set_yticklabels(fr["标签"])
ax.set_xlabel("系数（HAC Newey–West 95% 置信区间）", fontsize=12.5, color=INK)
ax.set_title("回归净效应（简化主模型口径）", fontsize=15, color=INK, pad=14)
ax.set_xlim(fr[["低", "高"]].min().min() - 0.12, fr[["高", "低"]].max().max() + 0.28)
ax.legend(handles=[Line2D([], [], color=BLUE, lw=2.2, marker="o", label="简化主模型（不含滞后）"),
                   Line2D([], [], color=ORANGE, lw=2.2, marker="o", label="简化+滞后1日")],
          frameon=False, fontsize=10, loc="lower right")
foot(ax, "注：因变量 $\\ln(R+1)$，核心自变量 $\\ln(C+1)$，控制原始时间趋势、周末与法定节假日；"
         "HAC(maxlags=7) 稳健标准误；* 表示 p<0.05。", y=-0.18)
fig.subplots_adjust(left=0.26, right=0.97, top=0.90, bottom=0.16)
save(fig, "F7b_回归净效应forest_简化主模型")

# ================================================================ 8. 复现说明
with open(os.path.join(OUT_DAT, "时间与假日效应_简化分析_运行日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
log("\n全部完成。")
