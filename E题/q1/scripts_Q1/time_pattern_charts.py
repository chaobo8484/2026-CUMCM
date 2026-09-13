# -*- coding: utf-8 -*-
"""
Q1「投放策略与时间规律」图表组  ——  设计/字体对齐 bid_budget_analysis.py
================================================================================
数据源: E题/clean_data/*_clean.csv (与 time_strategy.py 完全同一口径)
        先汇总再相除; CPA 为公司日度代理; HE=假日均值/同星期±4周正常日对照均值-1

输出: E题/q1/charts_time/  下 9 张 300dpi PNG
  F1 全年投放节奏与单元启停       F2 月度投入-产出-成本矩阵      F3 日度预算集中度
  F4 星期效应                     F5 月度成本效率趋势           F6 投入-注册同步与滞后
  F7 回归净效应forest             F8 假日效应HE                 F9 假日窗口事件研究
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
from matplotlib.ticker import FuncFormatter
from scipy import stats as sstats
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

# ================================================================ 0. 路径
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))            # E题
CD = os.path.join(ROOT, "clean_data")
OUT = os.path.join(os.path.dirname(BASE), "charts_time")
os.makedirs(OUT, exist_ok=True)
LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

# ================================================================ 1. 设计基座 (对齐 bid_budget_analysis.py)
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

# 语义色 (同 bid_budget_analysis.py)
BLUE, ORANGE, GREEN, PURPLE, PINK = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#c2185b"
INK, INK2, MUTED, GRID, REF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#9a9890"
GREY = "#8a8a8a"
DPI = 300
plt.rcParams.update({"font.size": 10.5, "axes.unicode_minus": False,
                     "pdf.fonttype": 42, "savefig.dpi": DPI})

def new_fig(w=10.4, h=7.4):
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor="white")
    ax = fig.add_subplot(111)
    _style(ax)
    return fig, ax

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

def footnote(ax, text, y=-0.155):
    return ax.text(0.5, y, text, transform=ax.transAxes, ha="center", va="top",
                   fontsize=9, color=MUTED)

def save(fig, name):
    p = os.path.join(OUT, name + ".png")
    fig.savefig(p, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    log("  已保存: %s" % p)
    return p

def _overlap(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0]); dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if (dx > 0 and dy > 0) else 0.0

def place_labels(ax, xs, ys, labels, sizes=None, fontsize=9.5, avoid=()):
    fig = ax.figure; fig.canvas.draw()
    px = fig.dpi / 72.0
    h = fontsize * 1.35 * px; pad = 5.0 * px
    occupied = []
    for x, y in zip(xs, ys):
        pxx, pyy = ax.transData.transform((x, y))
        r = np.sqrt((sizes[list(xs).index(x)] if sizes is not None else 60) / np.pi) * px
        occupied.append((pxx - r, pyy - r, pxx + r, pyy + r))
    rnd = fig.canvas.get_renderer()
    for art in avoid:
        bb = art.get_window_extent(rnd)
        occupied.append((bb.x0 - 2, bb.y0 - 2, bb.x1 + 2, bb.y1 + 2))
    axbox = ax.get_window_extent()
    cands = [(1, 0, "left", "center"), (-1, 0, "right", "center"),
             (0, 1, "center", "bottom"), (0, -1, "center", "top"),
             (0.72, 0.72, "left", "bottom"), (-0.72, 0.72, "right", "bottom"),
             (0.72, -0.72, "left", "top"), (-0.72, -0.72, "right", "top")]
    for i, (x, y, lab) in enumerate(zip(xs, ys, labels)):
        pxx, pyy = ax.transData.transform((x, y))
        w = len(str(lab)) * fontsize * 0.63 * px
        best, bc = None, None
        for dx, dy, ha, va in cands:
            cx, cy = pxx + dx * pad, pyy + dy * pad
            x0 = cx if ha == "left" else (cx - w if ha == "right" else cx - w / 2)
            y0 = cy if va == "bottom" else (cy - h if va == "top" else cy - h / 2)
            box = (x0, y0, x0 + w, y0 + h)
            c = sum(_overlap(box, o) for o in occupied)
            if (x0 < axbox.x0 + 1 or x0 + w > axbox.x1 - 1 or
                    y0 < axbox.y0 + 1 or y0 + h > axbox.y1 - 1):
                c += 1e7
            if bc is None or c < bc:
                bc, best = c, (dx * pad, dy * pad, ha, va, box)
            if c == 0:
                break
        ox, oy, ha, va, box = best
        occupied.append(box)
        t = ax.annotate(str(lab), (x, y), xytext=(ox, oy), textcoords="offset pixels",
                        ha=ha, va=va, fontsize=fontsize, color=INK, zorder=6)
        t.set_path_effects([pe.withStroke(linewidth=2.4, foreground="white")])

# ================================================================ 2. 数据
s1 = pd.read_csv(os.path.join(CD, "sheet1_投放记录_clean.csv"), encoding="utf-8-sig")
s2 = pd.read_csv(os.path.join(CD, "sheet2_日注册_clean.csv"), encoding="utf-8-sig")
dim = pd.read_csv(os.path.join(CD, "dim_date_时间维度.csv"), encoding="utf-8-sig")
cD, cP, cU, cI, cK, cC = s1.columns[0], s1.columns[1], s1.columns[2], s1.columns[3], s1.columns[4], s1.columns[5]
s1[cD] = pd.to_datetime(s1[cD])
s2.columns = ["日期", "新注册数", "日总消费", "日CPA"] if s2.shape[1] == 4 else list(s2.columns)
s2["日期"] = pd.to_datetime(s2["日期"])
dim["日期"] = pd.to_datetime(dim["日期"])

daily = s1.groupby(cD, as_index=False).agg({cC: "sum", cK: "sum", cI: "sum"})
daily.columns = ["日期", "日消费", "日点击", "日展现"]
act = s1.loc[s1[cC] > 0].groupby(cD)[cU].nunique().reset_index(); act.columns = ["日期", "活跃单元数"]
sh = s1.groupby([cD, cU])[cC].sum().reset_index(); sh.columns = ["日期", "单元", "消费"]
share = sh["消费"] / sh.groupby("日期")["消费"].transform("sum")
mx = share.groupby(sh["日期"]).max().reset_index(); mx.columns = ["日期", "最大单元占比"]
daily = (daily.merge(s2[["日期", "新注册数"]], on="日期", how="left")
              .merge(act, on="日期", how="left").merge(mx, on="日期", how="left")
              .merge(dim, on="日期", how="left").sort_values("日期").reset_index(drop=True))
daily["CTR"] = daily["日点击"] / daily["日展现"].replace(0, np.nan)
daily["CPC"] = daily["日消费"] / daily["日点击"].replace(0, np.nan)
daily["CPA"] = daily["日消费"] / daily["新注册数"].replace(0, np.nan)
daily["消费MA7"] = daily["日消费"].rolling(7, center=True).mean()
daily["月份"] = daily["日期"].dt.month
TOTAL = daily["日消费"].sum(); TOTCLK = daily["日点击"].sum()
log(f"对账 总消费={TOTAL:.2f} 总点击={TOTCLK:.0f} 整体CPC={TOTAL/TOTCLK:.4f} 天数={len(daily)}")

HOL = {"春节": pd.date_range("2025-01-28", "2025-02-04"),
       "清明节": pd.date_range("2025-04-04", "2025-04-06"),
       "劳动节": pd.date_range("2025-05-01", "2025-05-05"),
       "端午节": pd.date_range("2025-05-31", "2025-06-02"),
       "国庆中秋": pd.date_range("2025-10-01", "2025-10-08")}
HOL_ALL = [pd.Timestamp("2025-01-01")] + [d for r in HOL.values() for d in r]

# 月度
m = daily.groupby("月份").agg(消费=("日消费", "sum"), 点击=("日点击", "sum"), 展现=("日展现", "sum"),
                              注册=("新注册数", "sum"), 天数=("日期", "count"), 活跃单元=("活跃单元数", "mean"))
m["日均消费"] = m["消费"] / m["天数"]; m["CTR"] = m["点击"] / m["展现"]
m["CPC"] = m["消费"] / m["点击"]; m["日均注册"] = m["注册"] / m["天数"]; m["CPA"] = m["消费"] / m["注册"]

# 星期
ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WLAB = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
w = daily.groupby("星期").agg(日均消费=("日消费", "mean"), 日均注册=("新注册数", "mean"),
                              点击=("日点击", "sum"), 展现=("日展现", "sum"), 消费=("日消费", "sum"),
                              注册=("新注册数", "sum"), 活跃单元=("活跃单元数", "mean")).reindex(ORDER)
w["CTR"] = w["点击"] / w["展现"]; w["CPC"] = w["消费"] / w["点击"]; w["CPA"] = w["消费"] / w["注册"]

# ================================================================ 3. F1 全年投放节奏与单元启停
fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.0), sharex=True, dpi=DPI,
                         gridspec_kw={"height_ratios": [2, 1], "hspace": 0.13})
for a in axes:
    style(a)
for name, r in HOL.items():
    for a in axes:
        a.axvspan(r[0], r[-1], color=ORANGE, alpha=0.10, lw=0, zorder=1)
axes[0].plot(daily["日期"], daily["日消费"], color=GREY, lw=0.7, alpha=0.55, zorder=2, label="日消费")
axes[0].plot(daily["日期"], daily["消费MA7"], color=BLUE, lw=2.2, zorder=4, label="7日中心移动平均")
pk = daily.loc[daily["日消费"].idxmax()]
axes[0].annotate(f"{pk['日期'].strftime('%m月%d日')} 峰 {pk['日消费']:.0f}元",
                 (pk["日期"], pk["日消费"]), xytext=(-14, 26), textcoords="offset points",
                 fontsize=10.5, color=INK, ha="center",
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=1.0),
                 path_effects=[pe.withStroke(linewidth=2.8, foreground="white")], zorder=7)
axes[0].set_ylabel("日消费额（元）", fontsize=12.5, color=INK)
axes[0].set_title("(a) 日投放强度：2月底—3月高峰，6—7月低位，8月再扩量，11—12月回升",
                  fontsize=12.5, color=INK, pad=10, loc="left")
axes[0].legend(frameon=False, fontsize=10.5, loc="upper right")
axes[1].fill_between(daily["日期"], 0, daily["活跃单元数"], color=ORANGE, alpha=0.25, lw=0, zorder=2)
axes[1].plot(daily["日期"], daily["活跃单元数"], color=ORANGE, lw=1.3, drawstyle="steps-mid", zorder=3)
mon_mean = daily.groupby("月份")["活跃单元数"].mean()
axes[1].plot([daily.loc[daily["月份"] == mm, "日期"].mean() for mm in mon_mean.index],
             mon_mean.values, "o", color=INK, ms=6, zorder=5, label="月均活跃单元")
axes[1].axhline(6.39, color=REF, ls="--", lw=1.2, zorder=2)
axes[1].text(daily["日期"].iloc[2], 6.6, "全年均值 6.39", fontsize=9.5, color=MUTED)
axes[1].set_ylim(0, 13)
axes[1].set_ylabel("日活跃推广单元数（个）", fontsize=12.5, color=INK)
axes[1].set_title("(b) 推广单元启停：由个位数逐步扩到 12 个（7—8月最广）",
                  fontsize=12.5, color=INK, pad=8, loc="left")
axes[1].legend(frameon=False, fontsize=10.5, loc="upper left")
axes[1].xaxis.set_major_locator(mdates.MonthLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
for a in axes:
    a.grid(True, color=GRID, lw=0.7)
fig.suptitle("全年投放节奏与推广单元启停", fontsize=15, color=INK, y=0.965)
fig.text(0.5, 0.02, "注：橙底为法定假日窗口（春节/清明/劳动/端午/国庆中秋）；活跃单元=当日消费额>0 的推广单元数；"
                    "灰线为日度原始值，蓝线为 7 日中心移动平均。", ha="center", va="top",
         fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.085, right=0.98, top=0.90, bottom=0.11)
save(fig, "F1_全年投放节奏与单元启停")

# ================================================================ 4. F2 月度投入-产出-成本矩阵
fig, ax = new_fig(10.4, 7.4)
x = m["日均消费"].values; y = m["日均注册"].values
cpa = m["CPA"].values; sz = m["活跃单元"].values
sc = ax.scatter(x, y, s=90 + 900 * (sz - sz.min()) / (sz.max() - sz.min()),
                c=cpa, cmap="viridis", alpha=0.9, edgecolors="white", linewidths=1.3, zorder=4)
cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.86)
cb.set_label("月度 CPA（元/注册，越黄越贵）", fontsize=11, color=INK)
cb.ax.tick_params(labelsize=9.5, colors=INK2)
# OLS 拟合
b1, b0 = np.polyfit(x, y, 1)
xx = np.linspace(x.min() * 0.9, x.max() * 1.05, 50)
ax.plot(xx, b0 + b1 * xx, color=INK2, lw=1.5, ls="--", zorder=3,
        label=f"月均拟合（斜率 {b1:.3f} 注册/元）")
r = np.corrcoef(x, y)[0, 1]
ax.set_xlabel("月度日均消费（元，投入强度）", fontsize=12.5, color=INK)
ax.set_ylabel("月度日均注册（人，产出）", fontsize=12.5, color=INK)
ax.set_title("月度投入—产出—成本矩阵", fontsize=15, color=INK, pad=14)
ax.text(0.985, 0.03, f"月度 日均消费~日均注册  r = {r:.3f}", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=10.5, color=MUTED)
fig.canvas.draw()
place_labels(ax, x, y, [f"{mm}月" for mm in m.index],
             sizes=90 + 900 * (sz - sz.min()) / (sz.max() - sz.min()), fontsize=10.5)
ax.legend(frameon=False, fontsize=10.5, loc="upper left")
footnote(ax, "注：气泡面积∝月均活跃单元数，颜色为月度 CPA；3月高投入且 CPA 偏高，6月与8月 CPA 最高（扩量未换来相称注册）。")
fig.subplots_adjust(left=0.09, right=0.98, top=0.90, bottom=0.13)
save(fig, "F2_月度投入产出成本矩阵")

# ================================================================ 5. F3 日度预算集中度
fig, axes = plt.subplots(1, 2, figsize=(11.0, 7.0), dpi=DPI, gridspec_kw={"wspace": 0.22})
a0, a1 = axes; style(a0); style(a1)
a0.plot(daily["日期"], daily["最大单元占比"] * 100, color=GREY, lw=0.7, alpha=0.6, zorder=2)
a0.plot(daily["日期"], (daily["最大单元占比"].rolling(30, center=True).mean()) * 100,
        color=PINK, lw=2.0, zorder=4, label="30日移动平均")
mn = daily["最大单元占比"].mean() * 100
a0.axhline(mn, color=REF, ls="--", lw=1.2)
a0.text(daily["日期"].iloc[3], mn + 1.5, f"全年均值 {mn:.1f}%", fontsize=9.5, color=MUTED)
a0.set_ylim(0, 100)
a0.set_ylabel("每日最大单元预算占比（%）", fontsize=12.5, color=INK)
a0.set_title("(a) 预算集中度时序", fontsize=12.5, color=INK, pad=10, loc="left")
a0.legend(frameon=False, fontsize=10.5, loc="lower right")
a0.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
a0.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
a1.hist(daily["最大单元占比"] * 100, bins=20, color=BLUE, edgecolor="white", lw=0.8, zorder=3)
a1.axvline(mn, color=INK, ls="--", lw=1.6)
a1.text(mn + 1.5, a1.get_ylim()[1] * 0.92, f"均值 {mn:.1f}%", fontsize=10.5, color=INK,
        path_effects=[pe.withStroke(linewidth=2.6, foreground="white")])
a1.set_xlabel("每日最大单元预算占比（%）", fontsize=12.5, color=INK)
a1.set_ylabel("天数", fontsize=12.5, color=INK)
a1.set_title("(b) 集中度分布", fontsize=12.5, color=INK, pad=10, loc="left")
fig.suptitle("日度预算集中度：预算是否过度依赖头部单元", fontsize=15, color=INK, y=0.965)
fig.text(0.5, 0.02, f"注：每日取消费额最大单元的预算占比；全年均值 {mn:.1f}%，"
                    "即约七成日预算压在单一单元上。", ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.075, right=0.98, top=0.88, bottom=0.13)
save(fig, "F3_日度预算集中度")

# ================================================================ 6. F4 星期效应
kw = {}
for var in ["日消费", "CPA", "CTR", "CPC", "活跃单元数"]:
    arr = [daily.loc[daily["星期"] == d, var].dropna().values for d in ORDER]
    kw[var] = sstats.kruskal(*arr).pvalue
fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.0), dpi=DPI, gridspec_kw={"hspace": 0.42, "wspace": 0.25})
xw = np.arange(7)
_kwkey = {"日均消费": "日消费", "CPA": "CPA", "CPC": "CPC", "CTR": "CTR"}
for ax, col, colr, unit, ttl in [
        (axes[0, 0], "日均消费", BLUE, "元", "(a) 星期 × 日均消费"),
        (axes[0, 1], "CPA", ORANGE, "元/注册", "(b) 星期 × CPA"),
        (axes[1, 0], "CPC", GREEN, "元/点击", "(c) 星期 × CPC"),
        (axes[1, 1], "CTR", PURPLE, "%", "(d) 星期 × CTR")]:
    style(ax)
    vals = w[col].values * (100 if col == "CTR" else 1)
    ax.bar(xw, vals, color=colr, width=0.64, edgecolor="white", lw=0.8, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.2f}" if col in ("CPC", "CTR") else f"{v:.0f}",
                ha="center", va="bottom", fontsize=9, color=INK2)
    p = kw[_kwkey[col]]
    tag = "p<0.001" if p < 0.001 else f"p={p:.4f}"
    sig = "显著" if p < 0.05 else "不显著"
    ax.set_xticks(xw); ax.set_xticklabels(WLAB)
    ax.set_ylabel(f"{col}（{unit}）", fontsize=11.5, color=INK)
    ax.set_title(f"{ttl}   [KW {tag} {sig}]", fontsize=12, color=INK, pad=8, loc="left")
    ax.set_ylim(0, vals.max() * 1.20)
fig.suptitle("星期效应：差异主要来自预算强度，而非启用单元数", fontsize=15, color=INK, y=0.97)
fig.text(0.5, 0.02, "注：KW 为 Kruskal–Wallis 检验；活跃单元数星期差异不显著（p=0.998，未画图）；"
                    "周六 CPA 最高，周一投入与 CPA 均最低。", ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.10)
save(fig, "F4_星期效应")

# ================================================================ 7. F5 月度成本效率趋势
fig, axes = plt.subplots(1, 2, figsize=(11.0, 7.0), dpi=DPI, gridspec_kw={"wspace": 0.22})
a0, a1 = axes; style(a0); style(a1)
mo = m.reset_index()
a0.plot(mo["月份"], mo["CPC"], "o-", color=BLUE, lw=2.0, ms=6, label="CPC 单次点击成本")
a0.plot(mo["月份"], mo["CPA"], "s-", color=ORANGE, lw=2.0, ms=6, label="CPA 单次注册成本")
for _, rr in mo.iterrows():
    a0.text(rr["月份"], rr["CPC"] + 0.06, f"{rr['CPC']:.2f}", ha="center", fontsize=8.5, color=BLUE)
    a0.text(rr["月份"], rr["CPA"] + 0.06, f"{rr['CPA']:.1f}", ha="center", fontsize=8.5, color=ORANGE)
a0.set_xticks(range(1, 13)); a0.set_xlabel("月份", fontsize=12.5, color=INK)
a0.set_ylabel("成本（元）", fontsize=12.5, color=INK)
a0.set_ylim(0, max(mo["CPA"].max(), mo["CPC"].max()) * 1.22)
a0.set_title("(a) 月度 CPC 与 CPA", fontsize=12.5, color=INK, pad=10, loc="left")
a0.legend(frameon=False, fontsize=10.5, loc="upper right")
a1.plot(mo["月份"], mo["CTR"] * 100, "D-", color=GREEN, lw=2.0, ms=5.5)
for _, rr in mo.iterrows():
    a1.text(rr["月份"], rr["CTR"] * 100 + 0.12, f"{rr['CTR']*100:.2f}", ha="center", fontsize=8.5, color=INK2)
a1.set_xticks(range(1, 13)); a1.set_xlabel("月份", fontsize=12.5, color=INK)
a1.set_ylabel("CTR 点击率（%）", fontsize=12.5, color=INK)
a1.set_ylim(0, mo["CTR"].max() * 100 * 1.22)
a1.set_title("(b) 月度 CTR", fontsize=12.5, color=INK, pad=10, loc="left")
fig.suptitle("月度成本效率趋势：4月最省、6月最贵、5月起 CTR 结构性走低", fontsize=15, color=INK, y=0.965)
fig.text(0.5, 0.02, "注：先汇总再相除口径；CPA 为公司日度代理（不拆到单元）。",
         ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.075, right=0.98, top=0.88, bottom=0.13)
save(fig, "F5_月度成本效率趋势")

# ================================================================ 8. F6 投入-注册同步与滞后
fig, axes = plt.subplots(1, 2, figsize=(11.0, 7.0), dpi=DPI, gridspec_kw={"wspace": 0.22})
a0, a1 = axes; style(a0); style(a1)
C, R = daily["日消费"].values, daily["新注册数"].values
a0.scatter(C, R, s=22, color=BLUE, alpha=0.55, edgecolors="none", zorder=3)
bb, aa = np.polyfit(C, R, 1)
xx = np.linspace(C.min(), C.max(), 50)
a0.plot(xx, aa + bb * xx, color=ORANGE, lw=2.0, zorder=5)
rr = np.corrcoef(C, R)[0, 1]
a0.text(0.03, 0.95, f"Pearson r = {rr:.3f}\nOLS 斜率 = {bb:.4f} 人/元", transform=a0.transAxes,
        ha="left", va="top", fontsize=10.5, color=INK)
a0.set_xlabel("当日广告消费额（元）", fontsize=12.5, color=INK)
a0.set_ylabel("当日新增注册数（人）", fontsize=12.5, color=INK)
a0.set_title("(a) 当日投入—注册同步关系", fontsize=12.5, color=INK, pad=10, loc="left")
lags = list(range(8))
rhos = [float(pd.Series(C).corr(pd.Series(R))) if L == 0 else float(pd.Series(C[:-L]).corr(pd.Series(R[L:]))) for L in lags]
cols = [BLUE if L == 0 else (ORANGE if L == 1 else GREY) for L in lags]
a1.bar(lags, rhos, color=cols, width=0.62, edgecolor="white", lw=0.8, zorder=3)
for i, v in enumerate(rhos):
    a1.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=9, color=INK,
            path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])
a1.set_xticks(lags)
a1.set_xlabel("滞后天数 l：Corr(消费$_t$, 注册$_{t+l}$)", fontsize=12.5, color=INK)
a1.set_ylabel("Pearson 相关系数", fontsize=12.5, color=INK)
a1.set_ylim(0, 1.0)
a1.set_title("(b) 同步与滞后相关", fontsize=12.5, color=INK, pad=10, loc="left")
fig.suptitle("投入与注册的同步及滞后关系（相关，非因果）", fontsize=15, color=INK, y=0.965)
fig.text(0.5, 0.02, "注：l=0 当日相关最强（0.818）；l=1 回落至 0.610；l=6~7 回升系星期周期，"
                    "不宜解释为广告一周后再生效。", ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.075, right=0.98, top=0.88, bottom=0.13)
save(fig, "F6_投入注册同步与滞后")

# ================================================================ 9. F7 回归净效应 forest
reg = daily.copy()
reg["t"] = np.arange(len(reg)) / (len(reg) - 1)
reg["lnR"] = np.log(reg["新注册数"] + 1); reg["lnC"] = np.log(reg["日消费"] + 1)
reg["lnC1"] = np.log(reg["日消费"].shift(1) + 1); reg["H"] = (reg["三态标签"] == "放假").astype(int)
wd = pd.get_dummies(reg["星期"], prefix="W", drop_first=False).drop(columns=["W_星期一"])
X1 = sm.add_constant(pd.concat([reg[["lnC", "t", "H"]], wd], axis=1).astype(float))
res1 = sm.OLS(reg["lnR"].astype(float), X1).fit(cov_type="HAC", cov_kwds={"maxlags": 7, "use_correction": True})
reg2 = reg.iloc[1:].copy()
X2 = sm.add_constant(pd.concat([reg2[["lnC", "lnC1", "t", "H"]], wd.loc[reg2.index]], axis=1).astype(float))
res2 = sm.OLS(reg2["lnR"].astype(float), X2).fit(cov_type="HAC", cov_kwds={"maxlags": 7, "use_correction": True})
lab = {"lnC": "当日消费弹性", "lnC1": "滞后1日消费", "t": "线性时间趋势", "H": "总体假日"}
rows = []
for res, mname in [(res1, "模型1"), (res2, "模型2")]:
    ci = res.conf_int(alpha=0.05)
    for v in [x for x in ["lnC", "lnC1", "t", "H"] if x in res.params.index]:
        rows.append(dict(模型=mname, 变量=v, 标签=f"{mname} · {lab[v]}", 系数=res.params[v],
                         低=ci.loc[v, 0], 高=ci.loc[v, 1], p=res.pvalues[v]))
fr = pd.DataFrame(rows).iloc[::-1].reset_index(drop=True)
fig, ax = new_fig(10.4, 6.6)
yy = np.arange(len(fr))
colr = {"模型1": BLUE, "模型2": ORANGE}
for i, rrr in fr.iterrows():
    c = colr[rrr["模型"]]
    ax.plot([rrr["低"], rrr["高"]], [i, i], color=c, lw=2.2, zorder=3)
    ax.plot(rrr["系数"], i, "o", color=c, ms=8, markeredgecolor="white", markeredgewidth=1.2, zorder=4)
    ax.text(rrr["高"] + 0.02, i, f"{rrr['系数']:.3f}" + ("*" if rrr["p"] < 0.05 else f" (p={rrr['p']:.3f})"),
            va="center", fontsize=9.5, color=INK)
ax.axvline(0, color=INK2, ls="--", lw=1.2, zorder=2)
ax.set_yticks(yy); ax.set_yticklabels(fr["标签"])
ax.set_xlabel("系数（HAC Newey–West 95% 置信区间）", fontsize=12.5, color=INK)
ax.set_title("回归净效应：控制趋势、星期与假日后仍显著", fontsize=15, color=INK, pad=14)
ax.set_xlim(fr[["低", "高"]].min().min() - 0.15, fr[["高", "低"]].max().max() + 0.30)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color=BLUE, lw=2.2, marker="o", label="模型1 不含滞后"),
                   Line2D([], [], color=ORANGE, lw=2.2, marker="o", label="模型2 含滞后1日")],
          frameon=False, fontsize=10.5, loc="lower right")
footnote(ax, "注：因变量 ln(注册+1)，自变量 ln(消费+1)；HAC(maxlags=7) 稳健标准误；* 表示 p<0.05。"
             "当日消费弹性显著为正，趋势与假日净效应不显著。")
fig.subplots_adjust(left=0.24, right=0.97, top=0.90, bottom=0.15)
save(fig, "F7_回归净效应forest")
log(f"回归: 模型1 adjR2={res1.rsquared_adj:.4f} AIC={res1.aic:.2f} DW={durbin_watson(res1.resid):.3f}")

# ================================================================ 10. F8 假日效应 HE
HE = []
for name, r in HOL.items():
    hd = daily[daily["日期"].isin(r)]
    ctrl = []
    for dd in r:
        cands = daily[(daily["日期"] >= dd - pd.Timedelta(days=28)) &
                      (daily["日期"] <= dd + pd.Timedelta(days=28)) &
                      (daily["日期"].dt.weekday == dd.weekday()) & (daily["三态标签"] == "正常")]
        ctrl.append(cands)
    ctrl = pd.concat(ctrl).drop_duplicates()
    row = {"假日": name, "天数": len(hd)}
    for col in ["日消费", "日点击", "日展现", "新注册数"]:
        row[col] = hd[col].mean() / ctrl[col].mean() - 1
    row["CPC"] = hd["CPC"].mean() / ctrl["CPC"].mean() - 1
    row["CPA"] = hd["CPA"].mean() / ctrl["CPA"].mean() - 1
    HE.append(row)
HE = pd.DataFrame(HE).set_index("假日")
ind_cols = ["日消费", "日点击", "日展现", "新注册数", "CPC", "CPA"]
ind_lab = ["消费", "点击", "展现", "注册", "CPC", "CPA"]
ind_col = [BLUE, ORANGE, GREEN, PURPLE, PINK, GREY]
fig, ax = new_fig(11.0, 7.2)
xx = np.arange(len(HE)); wdt = 0.13
for i, (c, lb, cc) in enumerate(zip(ind_cols, ind_lab, ind_col)):
    ax.bar(xx + (i - 2.5) * wdt, HE[c].values * 100, width=wdt, label=lb, color=cc,
           edgecolor="white", lw=0.6, zorder=3)
ax.axhline(0, color=INK2, lw=1.1, zorder=4)
ax.set_xticks(xx)
ax.set_xticklabels([f"{n}\n({int(HE.loc[n,'天数'])}天)" for n in HE.index], fontsize=11)
ax.set_ylabel("相对同星期对照变化率 HE（%）", fontsize=12.5, color=INK)
ax.set_title("假日效应：相对同星期±4周正常日对照的变化率", fontsize=15, color=INK, pad=14)
ax.legend(ncol=6, frameon=False, fontsize=10.5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
ax.annotate("端午：消费仅降33%，\n点击降61% → CPC 涨74%",
            (xx[3] + 2.5 * wdt, HE.loc["端午节", "CPC"] * 100), xytext=(-8, 26),
            textcoords="offset points", fontsize=10, color=PINK, ha="center",
            arrowprops=dict(arrowstyle="->", color=PINK, lw=1.0),
            path_effects=[pe.withStroke(linewidth=2.6, foreground="white")], zorder=7)
footnote(ax, "注：HE = 假日均值 / 同星期±4周正常日对照均值 − 1；消费/点击/展现/注册为流量强度，"
             "CPC/CPA 为成本效率。春节、清明、劳动、国庆均大幅缩量；端午缩量不足致 CPC 显著上升。", y=-0.13)
fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.20)
save(fig, "F8_假日效应HE")
for _, rrr in HE.iterrows():
    log(f"  HE {rrr.name}: 消费{rrr['日消费']*100:+.1f}% 点击{rrr['日点击']*100:+.1f}% "
        f"注册{rrr['新注册数']*100:+.1f}% CPC{rrr['CPC']*100:+.1f}% CPA{rrr['CPA']*100:+.1f}%")

# ================================================================ 11. F9 假日窗口事件研究
fig, axes = plt.subplots(2, 3, figsize=(12.0, 7.6), dpi=DPI, gridspec_kw={"hspace": 0.45, "wspace": 0.24})
axes = axes.ravel()
hol_cols = [BLUE, ORANGE, GREEN, PURPLE, PINK]
for ax, (name, r), cc in zip(axes[:5], HOL.items(), hol_cols):
    style(ax)
    sdate, edate = r[0], r[-1]
    ctx = pd.date_range(sdate - pd.Timedelta(days=7), edate + pd.Timedelta(days=8))
    ctrl = daily[(daily["日期"] >= sdate - pd.Timedelta(days=28)) &
                 (daily["日期"] <= edate + pd.Timedelta(days=28)) & (daily["三态标签"] == "正常")]
    wd_mean = ctrl.groupby(ctrl["日期"].dt.weekday)[["日消费", "新注册数"]].mean()
    rel, rcons, rreg = [], [], []
    for dd in ctx:
        if dd not in daily["日期"].values:
            continue
        row = daily.loc[daily["日期"] == dd].iloc[0]
        base = wd_mean.loc[dd.weekday()]
        rel.append((dd - sdate).days)
        rcons.append(row["日消费"] / base["日消费"])
        rreg.append(row["新注册数"] / base["新注册数"])
    ax.axvspan(0, (edate - sdate).days, color=cc, alpha=0.12, lw=0)
    ax.axhline(1.0, color=REF, ls="--", lw=1.1, zorder=2)
    ax.plot(rel, rcons, "o-", color=BLUE, lw=1.8, ms=3.8, label="日消费")
    ax.plot(rel, rreg, "s-", color=ORANGE, lw=1.8, ms=3.8, label="日注册")
    ax.set_title(f"{name}（{int(HE.loc[name,'天数'])}天）", fontsize=12, color=INK, pad=6, loc="left")
    ax.set_ylim(0, max(1.6, np.nanmax(rcons + rreg) * 1.12))
    ax.set_xticks([-7, -3, 0, 3, 7, 11] if (edate - sdate).days >= 7 else [-7, -3, 0, 3, 7])
    ax.set_xlabel("相对假日开始的天数", fontsize=10.5, color=INK)
    ax.set_ylabel("相对同星期对照的比值", fontsize=10.5, color=INK)
    ax.text(0.03, 0.05, f"假日窗口: 0~{(edate-sdate).days}", transform=ax.transAxes,
            fontsize=9, color=MUTED)
axes[0].legend(frameon=False, fontsize=10, loc="upper right")
axL = axes[5]
axL.axis("off")
axL.text(0.0, 0.92, "读图说明", fontsize=12.5, color=INK, va="top")
axL.text(0.0, 0.78,
         "• 比值 = 当日指标 / 同星期(±4周)正常日均值\n"
         "• 阴影 = 法定假日窗口（相对天数 0~L）\n"
         "• 比值 < 1：投放/注册低于平日\n"
         "• 春节、清明、劳动、国庆假期内\n"
         "  消费与注册同步塌陷（缩量合理）\n"
         "• 端午窗口内消费比值明显高于\n"
         "  点击/注册比值 → CPC 被抬高，\n"
         "  缩量力度不足是主要问题",
         fontsize=10, color=INK2, va="top", linespacing=1.6)
fig.suptitle("假日窗口事件研究：假日及前后 7 天的投放与注册轨迹", fontsize=15, color=INK, y=0.98)
fig.text(0.5, 0.02, "注：以各假日开始日为相对 0；对照为窗口期±4周内同星期的“正常”工作日；"
                    "比值>1 表示高于平日。", ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.065, right=0.98, top=0.90, bottom=0.10)
save(fig, "F9_假日窗口事件研究")

log("\nALL DONE -> %s" % OUT)
with open(os.path.join(OUT, "绘图日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
