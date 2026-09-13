# -*- coding: utf-8 -*-
"""G6 投入效率×访问质量四象限：x=单元CPC（越低越好），y=浏览深度（越高越好），
气泡=总消费；中位线分象限，对应处置（保留扩量/查匹配/优化出价/降价暂停）。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
CPC_MED = summ["CPC"].median()
DEP_MED = summ["浏览深度"].median()

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 110 * MM))
size = np.sqrt(summ["总消费"].values)
size = 60 + 340 * (size - size.min()) / (size.max() - size.min())
colors = [PLAN_COLORS[p] for p in summ["方案ID"]]
ax.set_yscale("log")
ax.set_yticks([1, 2, 5, 10])
ax.set_yticklabels(["1", "2", "5", "10"])
ax.scatter(summ["CPC"], summ["浏览深度"], s=size, c=colors, alpha=0.85,
           edgecolors="white", linewidths=0.8, zorder=3)
OFF = {"7181": None, "8309": (6, 6, "left"), "4603": (-6, 6, "right"),
       "3555": (6, -13, "left"), "8329": (8, 8, "left"),
       "8310": (-8, -14, "right"), "0250": (10, 6, "left"),
       "6627": (6, -12, "left"), "3528": (6, 4, "left"),
       "3000": (-6, -13, "right"), "5700": (-8, 8, "right"),
       "0100": (6, -13, "left")}
for _, r in summ.iterrows():
    tail = str(int(r["推广单元ID"]))[-4:]
    if tail == "7181":
        ax.annotate(unit_short(r["推广单元ID"]), (r["CPC"], r["浏览深度"]),
                    xytext=(48, -24), textcoords="offset points", fontsize=7.5,
                    arrowprops=dict(arrowstyle="-", color="#666666", linewidth=0.6))
        continue
    dx, dy, ha = OFF[tail]
    ax.annotate(unit_short(r["推广单元ID"]), (r["CPC"], r["浏览深度"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=7.5, ha=ha)
ax.axvline(CPC_MED, color="#666666", linewidth=1.0, linestyle="--")
ax.axhline(DEP_MED, color="#666666", linewidth=1.0, linestyle="--")
ax.text(0.20, 0.96, "低成本·高质量：保留扩量", transform=ax.transAxes,
        ha="left", va="top", fontsize=8, color="#333333")
ax.text(0.98, 0.96, "高成本·高质量：优化出价", transform=ax.transAxes,
        ha="right", va="top", fontsize=8, color="#333333")
ax.text(0.02, 0.04, "低成本·低质量：检查匹配范围", transform=ax.transAxes,
        ha="left", va="bottom", fontsize=8, color="#333333")
ax.text(0.98, 0.04, "高成本·低质量：降价限额或暂停", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=8, color="#333333")
ax.set_xlabel("单元CPC（元/点击，越低越好）")
ax.set_ylabel("浏览深度（浏览量/点击量，对数轴，越高越好）")
ax.set_title("投入效率×访问质量四象限（虚线为12单元中位）", pad=10)
import matplotlib.patches as mpatches
ax.legend(handles=[mpatches.Patch(color=c, label=f"方案{p}")
                   for p, c in PLAN_COLORS.items()] +
                  [plt.Line2D([0], [0], marker="o", color="w",
                               markerfacecolor="#666666", markersize=7,
                               label="气泡大小=单元总消费额")],
          frameon=True, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5)
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g6_四象限")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G6 done, CPC中位=", round(CPC_MED, 4), "深度中位=", round(DEP_MED, 4))
