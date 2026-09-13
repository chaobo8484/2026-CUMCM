# -*- coding: utf-8 -*-
"""HHI独立图：各单元标准化HHI*横向条形（降序），颜色=所属象限，
柱端标注M值；虚线为HHI*中位。HHI只描述集中，是否合理看M对照。"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from style_q1 import apply_style, unit_short, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
summ = summ.sort_values("HHI星", ascending=True).reset_index(drop=True)
QCOL = {"Ⅰ": OI["green"], "Ⅱ": OI["blue"], "Ⅲ": OI["vermillion"], "Ⅳ": OI["orange"]}
QNAME = {"Ⅰ": "Ⅰ高利用高匹配", "Ⅱ": "Ⅱ低利用高匹配",
         "Ⅲ": "Ⅲ低利用低匹配", "Ⅳ": "Ⅳ高利用低匹配"}
MED = summ["HHI星"].median()

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 100 * MM))
import numpy as np
y = np.arange(len(summ))
cols = [QCOL[q[0]] for q in summ["象限"]]
ax.barh(y, summ["HHI星"], height=0.55, color=cols, edgecolor="white", zorder=2)
for i, r in summ.iterrows():
    ax.text(r["HHI星"] + 0.015, y[i], f"M={r['M匹配度']:.3f}",
            va="center", ha="left", fontsize=8, color="#333333")
ax.axvline(MED, color="#666666", linewidth=1.0, linestyle="--")
ax.text(MED + 0.008, len(summ) - 0.4, f"中位{MED:.3f}",
        va="center", ha="left", fontsize=8, color="#333333")
ax.set_yticks(y)
ax.set_yticklabels([unit_short(u) for u in summ["推广单元ID"]])
ax.set_xlabel("标准化HHI*（费用集中度，越高越集中）")
ax.set_title("各单元费用集中度HHI*（颜色=U–M象限，柱端为M值对照）", pad=10)
ax.set_xlim(0, summ["HHI星"].max() * 1.32)
ax.legend(handles=[mpatches.Patch(color=c, label=QNAME[k]) for k, c in QCOL.items()],
          frameon=True, loc="lower right", fontsize=8)
ax.grid(axis="x", linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_附表_HHI")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("done")
