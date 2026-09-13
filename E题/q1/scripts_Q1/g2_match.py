# -*- coding: utf-8 -*-
"""G2 Top10消费占比—Top10点击占比散点 + 45°线 + ±5pp容许带；气泡=总消费。
消费词不足10个的单元空心标出，不参与横向判定。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 110 * MM))
x = summ["Top10消费占比"].values
y = summ["Top10点击占比"].values
size = np.sqrt(summ["总消费"].values)
size = 60 + 340 * (size - size.min()) / (size.max() - size.min())
colors = [PLAN_COLORS[p] for p in summ["方案ID"]]

lo, hi = 0.5, 1.07  # 右上留白给(1,1)角落标注
xs = np.linspace(lo, hi, 100)
ax.fill_between(xs, xs - 0.05, xs + 0.05, color="#EEEEEE", zorder=0)
ax.plot(xs, xs, color="#333333", linewidth=1.2, label="45°线：投入与点击匹配")
OFF2 = {"5700": (12, -2, "left"), "8309": (-62, -14, "right")}
for i, r in summ.iterrows():
    if r["Top10满10"] == 1:
        ax.scatter(x[i], y[i], s=size[i], c=colors[i], alpha=0.85,
                   edgecolors="white", linewidths=0.8, zorder=3)
    else:
        ax.scatter(x[i], y[i], s=size[i], facecolors="none",
                   edgecolors=OI["grey"], linewidths=1.2, zorder=3)
    tail = str(int(r["推广单元ID"]))[-4:]
    if tail in ("7181", "0250"):  # 同为(1,1)空心点，后面合并标注
        continue
    dx, dy, ha = OFF2.get(tail, (5, 5, "left"))
    ax.annotate(unit_short(r["推广单元ID"]), (x[i], y[i]),
                xytext=(dx, dy), textcoords="offset points", fontsize=7.5, ha=ha)
# (1,1)两空心点重合，合并为一条引线标注
ax.annotate("单元7181/0250（消费词不足10）", (1.0, 1.0),
            xytext=(14, 16), textcoords="offset points", fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color="#666666", linewidth=0.6))
ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_xlabel("Top10消费占比（同批高消费词）")
ax.set_ylabel("Top10点击占比（同批词）")
ax.set_title("Top10投入—点击匹配散点（阴影为±5个百分点容许带）", pad=10)
from matplotlib.lines import Line2D
handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=OI["grey"],
                   markersize=7, label="消费词不足10（占比100%，不横向比较）"),
           Line2D([0], [0], marker="o", color="w", markerfacecolor="#333333",
                   markersize=7, label="气泡大小=单元总消费额")]
ax.legend(handles=ax.get_legend_handles_labels()[0] + handles,
          frameon=True, loc="lower right", fontsize=7.5)
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g2_匹配散点")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G2 done")
