# -*- coding: utf-8 -*-
"""Q3 charts restyle: borrow bid_budget_analysis design language, NO footnote gray line."""
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

base = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
q3dir = next(d for d in base.rglob("*") if d.is_dir() and d.name == "q3")
data_out = q3dir / "data_Q3"
chart_out = q3dir / "charts_Q3"
chart_out.mkdir(exist_ok=True)

# ---- design tokens from bid_budget_analysis.py ----
def set_cjk_font():
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
                 "Source Han Sans SC", "PingFang SC", "WenQuanYi Micro Hei"]:
        if name in have:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    return "DejaVu Sans"

FONT = set_cjk_font()
HIST = "#2a78d6"   # history / Feb
OPT = "#eb6834"    # opt / Aug
GREEN = "#1baf7a"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"
REF = "#9a9890"
DPI = 300

def new_fig(w=10.4, h=7.4):
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)
    return fig, ax

def bottom_legend(ax, handles, ncol=2, y=-0.14):
    return ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, y),
                     ncol=ncol, frameon=False, fontsize=10,
                     handletextpad=0.5, columnspacing=1.8)

def save(fig, name):
    p = chart_out / name
    fig.savefig(str(p), dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    print("saved %s" % p)

comp = pd.read_csv(data_out / "compare_daily_v2.csv", encoding="utf-8-sig")
st = pd.read_csv(data_out / "static_params_v2.csv", encoding="utf-8-sig")
# theta source: recompute order from compare file dates
dates = comp["日期"].tolist()

# ============ fig1_theta: Feb blue, Aug orange ============
theta_map = {"2025-02-01": 0.666, "2025-02-02": 0.708, "2025-02-03": 0.713, "2025-02-04": 0.699,
             "2025-02-05": 0.710, "2025-02-06": 0.656, "2025-02-07": 0.676, "2025-02-08": 0.812,
             "2025-08-01": 2.072, "2025-08-02": 2.007, "2025-08-03": 1.412, "2025-08-04": 1.381,
             "2025-08-05": 1.432, "2025-08-06": 1.556, "2025-08-07": 1.473, "2025-08-08": 1.422}
tvals = [theta_map[d] for d in dates]
colors = [HIST if d.startswith("2025-02") else OPT for d in dates]
fig, ax = new_fig(10.4, 6.6)
bars = ax.bar(range(len(dates)), tvals, width=0.62, color=colors, edgecolor="white", linewidth=1.0, zorder=3)
ax.axhline(1.0, color=REF, linestyle="--", linewidth=1.3, zorder=2)
ax.set_xticks(range(len(dates)))
ax.set_xticklabels([d[5:] for d in dates], rotation=45, ha="right")
ax.set_ylabel("日期修正系数", fontsize=12.5, color=INK)
ax.set_title("目标日期投放效率修正系数", fontsize=15, color=INK, pad=14)
ax.set_ylim(0, max(tvals) * 1.18)
for i, v in enumerate(tvals):
    t = ax.text(i, v + 0.04, "%.3f" % v, ha="center", va="bottom", fontsize=8.5, color=INK, zorder=6)
    t.set_path_effects([pe.withStroke(linewidth=2.4, foreground="white")])
h1 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=HIST, markeredgecolor="white", label="2月目标日")
h2 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=OPT, markeredgecolor="white", label="8月目标日")
bottom_legend(ax, [h1, h2], ncol=2)
save(fig, "fig1_theta.png")

# ============ fig2_clicks: grouped bars ============
c = comp.sort_values("日期").reset_index(drop=True)
x = np.arange(len(c)); w = 0.38
fig, ax = new_fig(10.4, 6.8)
b1 = ax.bar(x - w / 2, c["历史点击"], width=w, color=HIST, edgecolor="white", linewidth=1.0, label="历史比例", zorder=3, alpha=0.92)
b2 = ax.bar(x + w / 2, c["优化点击"], width=w, color=OPT, edgecolor="white", linewidth=1.0, label="优化方案", zorder=3, alpha=0.92)
ax.set_xticks(x)
ax.set_xticklabels([s[5:] for s in c["日期"]], rotation=45, ha="right")
ax.set_ylabel("点击量（次）", fontsize=12.5, color=INK)
ax.set_title("同预算下历史比例与优化方案点击量比较", fontsize=15, color=INK, pad=14)
h1 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=HIST, markeredgecolor="white", label="历史比例")
h2 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=OPT, markeredgecolor="white", label="优化方案")
bottom_legend(ax, [h1, h2], ncol=2)
save(fig, "fig2_clicks.png")

# ============ fig3: 3-row lines ============
fig = plt.figure(figsize=(10.4, 9.2), dpi=DPI, facecolor="white")
axs = []
for k in range(3):
    ax = fig.add_subplot(3, 1, k + 1)
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.9)
    ax.set_axisbelow(True)
    axs.append(ax)
xs = [s[5:] for s in c["日期"]]
axs[0].plot(xs, c["历史点击"], color=HIST, linewidth=2.0, marker="o", markersize=6, markerfacecolor="white", markeredgecolor=HIST, markeredgewidth=1.6, label="历史点击")
axs[0].plot(xs, c["优化点击"], color=OPT, linewidth=2.0, marker="s", markersize=6, markerfacecolor="white", markeredgecolor=OPT, markeredgewidth=1.6, label="优化点击")
axs[0].set_title("逐日点击量（越高越好）", fontsize=12.5, color=INK)
axs[0].set_ylabel("次", color=INK)
axs[1].plot(xs, c["历史注册"], color=HIST, linewidth=2.0, marker="o", markersize=6, markerfacecolor="white", markeredgecolor=HIST, markeredgewidth=1.6, label="历史注册")
axs[1].plot(xs, c["优化注册"], color=OPT, linewidth=2.0, marker="s", markersize=6, markerfacecolor="white", markeredgecolor=OPT, markeredgewidth=1.6, label="优化注册")
axs[1].set_title("逐日注册量（越高越好）", fontsize=12.5, color=INK)
axs[1].set_ylabel("人", color=INK)
axs[2].plot(xs, c["历史成本"], color=HIST, linewidth=2.0, marker="o", markersize=6, markerfacecolor="white", markeredgecolor=HIST, markeredgewidth=1.6, label="历史成本")
axs[2].plot(xs, c["优化成本"], color=OPT, linewidth=2.0, marker="s", markersize=6, markerfacecolor="white", markeredgecolor=OPT, markeredgewidth=1.6, label="优化成本")
axs[2].set_title("单位注册成本（越低越好）", fontsize=12.5, color=INK)
axs[2].set_ylabel("元/人", color=INK)
for ax in axs:
    for lab in ax.get_xticklabels():
        lab.set_rotation(45); lab.set_ha("right")
fig.suptitle("同预算下历史比例与优化方案逐日效益比较", fontsize=15, color=INK, y=0.99)
fig.tight_layout(rect=(0, 0.06, 1, 0.96))
h1 = plt.Line2D([], [], color=HIST, linewidth=2.0, marker="o", markerfacecolor="white", markeredgecolor=HIST, label="历史比例")
h2 = plt.Line2D([], [], color=OPT, linewidth=2.0, marker="s", markerfacecolor="white", markeredgecolor=OPT, label="优化方案")
fig.legend(handles=[h1, h2], loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2, frameon=False, fontsize=10)
p = chart_out / "fig3_hist_vs_opt.png"
fig.savefig(str(p), dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
plt.close(fig)
print("saved %s" % p)

# ============ fig_eta_dist ============
fig, ax = new_fig(10.0, 6.2)
ax.hist(st["eta_raw"], bins=50, color=HIST, alpha=0.55, edgecolor="white", linewidth=0.8, label="原始", zorder=3)
ax.hist(st["eta"], bins=50, color=OPT, alpha=0.65, edgecolor="white", linewidth=0.8, label="平滑+缩尾", zorder=4)
ax.set_xlabel("关键词相对效率", fontsize=12.5, color=INK)
ax.set_ylabel("关键词个数", fontsize=12.5, color=INK)
ax.set_title("关键词效率平滑前后分布（$C_0=8.06$，1-99%截尾）", fontsize=15, color=INK, pad=14)
h1 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=HIST, markeredgecolor="white", alpha=0.7, label="原始")
h2 = plt.Line2D([], [], marker="s", linestyle="none", markersize=8, markerfacecolor=OPT, markeredgecolor="white", alpha=0.8, label="平滑+缩尾")
bottom_legend(ax, [h1, h2], ncol=2)
save(fig, "fig_eta_dist.png")
print("ALL_DONE font=%s" % FONT)
