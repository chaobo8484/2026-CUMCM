# -*- coding: utf-8 -*-
"""G9 周期：a)按星期平均注册柱状（从0起）；b)星期×月份日均注册热力（viridis）。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, OI, FIG_W_FULL, FIG_W_HALF, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGD = os.path.join(ROOT, "charts_Q1")
d = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_daily.csv"), parse_dates=["日期"])
ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# a) 星期平均注册
w = d.groupby("星期")["新注册数"].mean().reindex(ORDER)
fig, ax = plt.subplots(figsize=(FIG_W_HALF + 20 * MM, 90 * MM))
bars = ax.bar(range(7), w.values, color=OI["blue"], edgecolor="white", zorder=2)
for i, v in enumerate(w.values):
    ax.text(i, v + 4, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(range(7))
ax.set_xticklabels([s.replace("星期", "周") for s in ORDER])
ax.set_ylabel("平均注册（人/天）")
ax.set_title("星期效应：平均日注册", pad=10)
ax.set_ylim(0, w.max() * 1.18)
ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
fig.savefig(os.path.join(FIGD, "q1_g9a_星期注册.pdf"), dpi=300,
            bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(FIGD, "q1_g9a_星期注册.png"), dpi=300,
            bbox_inches="tight", transparent=False)
plt.close(fig)

# b) 星期×月份热力
piv = d.pivot_table(index="星期", columns="月份", values="新注册数", aggfunc="mean")
piv = piv.reindex(ORDER)
fig, ax = plt.subplots(figsize=(FIG_W_FULL, 100 * MM))
im = ax.imshow(piv.values, cmap="viridis", aspect="auto")
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        if np.isnan(v):
            continue
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                color="white" if v > piv.values.max() * 0.55 else "black")
ax.set_xticks(range(piv.shape[1]))
ax.set_xticklabels([f"{m}月" for m in piv.columns])
ax.set_yticks(range(7))
ax.set_yticklabels([s.replace("星期", "周") for s in ORDER])
ax.set_title("星期×月份日均注册热力", pad=10)
cbar = fig.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("日均注册（人/天）")
fig.tight_layout()
fig.savefig(os.path.join(FIGD, "q1_g9b_星期月份热力.pdf"), dpi=300,
            bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(FIGD, "q1_g9b_星期月份热力.png"), dpi=300,
            bbox_inches="tight", transparent=False)
plt.close(fig)
print("G9 done")
