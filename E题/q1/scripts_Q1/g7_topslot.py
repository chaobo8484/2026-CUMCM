# -*- coding: utf-8 -*-
"""G7 抢位花费与预算份额：横向分组条形（上方位消费占比 / 预算份额），
柱端标首位展现占比；虚线为总体上方位消费占比。柱从0起。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, unit_short, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
summ = summ.sort_values("上方位消费占比").reset_index(drop=True)

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 100 * MM))
y = np.arange(len(summ))
h = 0.36
ax.barh(y + h / 2, summ["上方位消费占比"] * 100, height=h,
        color=OI["vermillion"], edgecolor="white", label="上方位消费占比")
ax.barh(y - h / 2, summ["预算份额"] * 100, height=h,
        color=OI["blue"], edgecolor="white", label="预算份额（单元消费/总消费）")
for i, r in summ.iterrows():
    ax.text(r["上方位消费占比"] * 100 + 0.6, y[i] + h / 2,
            f"首位{r['首位占比']:.1%}", va="center", ha="left", fontsize=7.5,
            color="#333333")
ax.set_yticks(y)
ax.set_yticklabels([unit_short(u) for u in summ["推广单元ID"]])
ax.set_xlabel("占比（%）")
ax.set_title("各单元上方位消费占比、首位占比与预算份额", pad=10)
ax.set_xlim(0, max(summ["上方位消费占比"].max() * 100 * 1.35, 12))
ax.axvline(70.35, color="#666666", linewidth=1.0, linestyle="--")
ax.set_ylim(-0.8, 12.4)
ax.text(71.5, 11.75, "总体上方位消费占比70.4%",
        va="center", ha="left", fontsize=8, color="#333333")
ax.legend(frameon=True, loc="lower right", fontsize=8)
ax.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g7_抢位条形")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G7 done")
