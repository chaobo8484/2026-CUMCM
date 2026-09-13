# -*- coding: utf-8 -*-
"""
Q2-3b 各推广单元五类构成 —— 方案A：左“按记录数”、右“按消费额”双面板
只新增输出 Q2-3b，不覆盖、不重画原 Q2-3。
设计/字体对齐 bid_budget_analysis.py。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__)); Q2 = os.path.dirname(BASE)
D = os.path.join(Q2, "data_Q2"); OUT = os.path.join(Q2, "charts_Q2")
os.makedirs(OUT, exist_ok=True)

def set_cjk_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for n in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "PingFang SC"]:
        if n in have:
            plt.rcParams["font.sans-serif"] = [n]; plt.rcParams["axes.unicode_minus"] = False; return n
set_cjk_font()
GOLD, KEY, POT, PROB, INV = "#E69F00", "#0072B2", "#009E73", "#D55E00", "#999999"
CCOL = {"黄金词": GOLD, "重点词": KEY, "潜力词": POT, "问题词": PROB, "无效词": INV}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
CATS = ["黄金词", "重点词", "潜力词", "问题词", "无效词"]
DPI = 300
plt.rcParams.update({"font.size": 10.5, "axes.unicode_minus": False, "savefig.dpi": DPI})

rec = pd.read_csv(os.path.join(D, "q2_record_clean.csv"), encoding="utf-8-sig")

# 计数构成 / 消费构成
cnt = (rec.groupby(["推广单元ID", "基准类别"]).size().unstack(fill_value=0).reindex(columns=CATS, fill_value=0))
spd = (rec.groupby(["推广单元ID", "基准类别"])["消费额"].sum().unstack(fill_value=0).reindex(columns=CATS, fill_value=0))
tot_cnt = cnt.sum(axis=1); tot_spd = spd.sum(axis=1)
order = tot_cnt.sort_values(ascending=False).index          # 按记录数降序，两面板同序
cnt = cnt.loc[order]; spd = spd.loc[order]
pct_c = cnt.div(tot_cnt.loc[order], axis=0) * 100
pct_s = spd.div(tot_spd.loc[order].replace(0, np.nan), axis=0) * 100

TOT_CNT, TOT_SPD = tot_cnt.sum(), tot_spd.sum()

def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(INK2); ax.spines[s].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.9); ax.set_axisbelow(True)

def stack(ax, pct, totals, endfmt, title):
    style(ax)
    y = np.arange(len(pct))[::-1]
    left = np.zeros(len(pct))
    for c in CATS:
        v = pct[c].fillna(0).values
        ax.barh(y, v, left=left, color=CCOL[c], edgecolor="white", lw=0.8, height=0.7, zorder=3, label=c)
        for i, (l, vv) in enumerate(zip(left, v)):
            if vv >= 8:
                ax.text(l + vv / 2, y[i], f"{vv:.0f}", ha="center", va="center", fontsize=8.5,
                        color="white" if c in ("重点词", "问题词") else INK)
        left += v
    for i, (yy, t) in enumerate(zip(y, totals.values)):
        ax.text(102, yy, endfmt(t), va="center", fontsize=9, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{u}{'  *' if tot_cnt[u] < 10 else ''}" for u in pct.index], fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel(title, fontsize=11.5, color=INK)
    ax.grid(axis="x")

fig, axes = plt.subplots(1, 2, figsize=(12.6, 7.4), dpi=DPI, gridspec_kw={"wspace": 0.30})
stack(axes[0], pct_c, tot_cnt, lambda t: f"{int(t)}条", "各类关键词占该单元记录数（%）")
stack(axes[1], pct_s, tot_spd, lambda t: (f"{t/1e4:.1f}万" if t >= 1e4 else f"{t:,.0f}元"),
      "各类关键词占该单元消费额（%）")
axes[0].set_title("(a) 按记录数：无效/潜力词占大块", fontsize=13, color=INK, pad=10, loc="left")
axes[1].set_title("(b) 按消费额：几乎全部集中在重点词", fontsize=13, color=INK, pad=10, loc="left")

# 对比标注
u_long = order[0]; u_head = tot_spd.loc[order].idxmax()
rc = tot_cnt[u_long] / TOT_CNT * 100; rs = tot_spd[u_long] / TOT_SPD * 100
hc = tot_cnt[u_head] / TOT_CNT * 100; hs = tot_spd[u_head] / TOT_SPD * 100
axes[1].annotate(f"{u_long}：{rc:.1f}% 记录 / 仅 {rs:.1f}% 花费\n{u_head}：{hc:.1f}% 记录 / 高达 {hs:.1f}% 花费",
                 xy=(0.985, 0.03), xycoords="axes fraction", ha="right", va="bottom",
                 fontsize=10, color=INK,
                 bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID))
axes[0].legend(ncol=5, frameon=False, fontsize=10, loc="upper center", bbox_to_anchor=(1.12, -0.06))
fig.suptitle("各推广单元五类关键词构成：记录数 vs 消费额（同一单元两种口径对比）", fontsize=15, color=INK, y=0.98)
fig.subplots_adjust(left=0.09, right=0.985, top=0.90, bottom=0.15)
p = os.path.join(OUT, "Q2-3b_各单元五类构成_数量vs消费.png")
import time
for attempt in range(6):
    try:
        fig.savefig(p, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
        break
    except OSError:
        if attempt == 5:
            raise
        time.sleep(0.4)
plt.close(fig)
print("已保存:", p)
