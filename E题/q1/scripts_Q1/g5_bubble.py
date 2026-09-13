# -*- coding: utf-8 -*-
"""G5 综合气泡（主图）：x=利用率U，y=CPC（轴反向，越靠上成本越低），
大小=总消费，颜色=标准化HHI*；中位线分象限，右上为高效区。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
U_MED, CPC_MED = summ["利用率"].median(), summ["CPC"].median()

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 115 * MM))
size = np.sqrt(summ["总消费"].values)
size = 60 + 380 * (size - size.min()) / (size.max() - size.min())
sc = ax.scatter(summ["利用率"], summ["CPC"], s=size, c=summ["HHI星"],
                cmap="viridis", vmin=0, vmax=0.7, alpha=0.9,
                edgecolors="white", linewidths=0.8, zorder=3)
y0, _ = ax.get_ylim()  # 正常方向：y0为低CPC端
ax.add_patch(mpatches.Rectangle((U_MED, y0), 1.02 - U_MED, CPC_MED - y0,
                                color="#F2F2F2", zorder=0))
ax.text(U_MED + 0.015, y0 + 0.05, "高效区（高利用·低CPC）",
        ha="left", va="bottom", fontsize=8, color="#333333")
OFFSETS = {"8310": (-6, -13, "right"), "7181": (-6, 4, "right")}
for _, r in summ.iterrows():
    tail = str(int(r["推广单元ID"]))[-4:]
    dx, dy, ha = OFFSETS.get(tail, (5, 4, "left"))
    ax.annotate(unit_short(r["推广单元ID"]), (r["利用率"], r["CPC"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=7.5, ha=ha)
ax.axvline(U_MED, color="#666666", linewidth=1.0, linestyle="--")
ax.axhline(CPC_MED, color="#666666", linewidth=1.0, linestyle="--")
ax.set_xlim(0.35, 1.02)
ax.set_xlabel("关键词利用率U")
ax.set_ylabel("单元CPC（元/点击；纵轴已反向，越靠上成本越低）")
ax.invert_yaxis()
ax.set_title("推广单元关键词利用率—投入效率综合气泡", pad=10)
cbar = fig.colorbar(sc, ax=ax, shrink=0.85)
cbar.set_label("标准化HHI*（费用集中度）")
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_g5_综合气泡")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("G5 done, U中位=", round(U_MED, 4), "CPC中位=", round(CPC_MED, 4))
