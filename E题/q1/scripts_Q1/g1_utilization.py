# -*- coding: utf-8 -*-
"""G1 各单元配置关键词数 vs 活跃关键词数（横向分组条形，柱端标利用率U）。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
summ = summ.sort_values("利用率").reset_index(drop=True)
U_MED = summ["利用率"].median()

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 95 * MM))
y = np.arange(len(summ))
h = 0.36
cfg_c = [OI["grey"]] * len(summ)
act_c = [PLAN_COLORS[p] for p in summ["方案ID"]]
ax.barh(y + h / 2, summ["N"], height=h, color=cfg_c, edgecolor="white", label="配置关键词数")
ax.barh(y - h / 2, summ["A"], height=h, color=act_c, edgecolor="white", label="活跃关键词数")
for i, r in summ.iterrows():
    below = r["利用率"] < U_MED
    ax.text(r["N"] + 18, y[i] + h / 2, f"U={r['利用率']:.1%}",
            va="center", ha="left", fontsize=8,
            color=OI["vermillion"] if below else "#333333",
            fontweight="bold" if below else "normal")
ax.set_yticks(y)
ax.set_yticklabels([unit_short(u) for u in summ["推广单元ID"]])
ax.set_xlabel("关键词数（条）")
ax.set_title("各推广单元配置关键词数与活跃关键词数对比（按利用率U升序）", pad=10)
ax.set_xlim(0, summ["N"].max() * 1.28)
ax.legend(handles=[mpatches.Patch(color="grey", label="配置关键词数"),
                   mpatches.Patch(color=OI["blue"], label="活跃关键词数（颜色=方案）")] +
                  [mpatches.Patch(color=c, label=f"方案{p}")
                   for p, c in PLAN_COLORS.items()],
          frameon=True, loc="lower right", ncols=2, fontsize=7.5)
ax.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g1_利用率条形")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G1 done, U中位=", round(U_MED, 4))
