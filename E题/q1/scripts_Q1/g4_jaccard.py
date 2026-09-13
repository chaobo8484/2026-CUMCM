# -*- coding: utf-8 -*-
"""G4 12×12关键词集合Jaccard重叠热力图（viridis；对角线屏蔽；仅标注≥0.05）。
结论口径：结构性风险/待核查，不武断归因。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, unit_short, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jm = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_jaccard.csv"), index_col=0)
uids = [lab.split("|")[1] for lab in jm.index]
short = [unit_short(u) for u in uids]
mat = jm.values.copy()
np.fill_diagonal(mat, np.nan)

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 125 * MM))
im = ax.imshow(mat, cmap="viridis", vmin=0, vmax=0.45)
for i in range(len(short)):
    for j in range(len(short)):
        v = mat[i, j]
        if np.isnan(v) or v < 0.05:
            continue
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                color="white" if v > 0.22 else "black")
ax.set_xticks(range(len(short)))
ax.set_yticks(range(len(short)))
ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(short, fontsize=8)
ax.set_title("推广单元关键词集合Jaccard重叠矩阵（仅标注≥0.05）", pad=10)
cbar = fig.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("Jaccard系数")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g4_重叠热力")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G4 done")
