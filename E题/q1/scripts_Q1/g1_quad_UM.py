# -*- coding: utf-8 -*-
"""图1 U–M四象限主图：x=利用率U，y=匹配度M，中位线分界；
颜色=方案，描边加粗=距分界<0.01的临界单元（结论需谨慎）。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, unit_short, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
U0, M0 = summ["利用率"].median(), summ["M匹配度"].median()
summ["临界"] = (summ[["利用率", "M匹配度"]].sub([U0, M0]).abs().min(axis=1) < 0.01)

fig, ax = plt.subplots(figsize=(FIG_W_FULL, 110 * MM))
OFF1 = {"3000": (-8, -14, "right"), "0250": None,
        "8310": (-12, 12, "right"), "8309": (6, -14, "left")}
for _, r in summ.iterrows():
    tail = str(int(r["推广单元ID"]))[-4:]
    if tail == "0250":  # 右侧空白处引线标，避开0100/3000标签
        ax.annotate(unit_short(r["推广单元ID"]), (r["利用率"], r["M匹配度"]),
                    xytext=(0.975, 0.945), textcoords="data", fontsize=8, ha="left",
                    va="center", fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color="#666666", linewidth=0.6))
        ax.scatter(r["利用率"], r["M匹配度"], s=150, c=PLAN_COLORS[r["方案ID"]],
                   alpha=0.9, edgecolors=OI["vermillion"], linewidths=2.0, zorder=3)
        continue
    dx, dy, ha = OFF1.get(tail, (6, 5, "left"))
    ax.scatter(r["利用率"], r["M匹配度"], s=150, c=PLAN_COLORS[r["方案ID"]],
               alpha=0.9, edgecolors=OI["vermillion"] if r["临界"] else "white",
               linewidths=2.0 if r["临界"] else 0.8, zorder=3)
    ax.annotate(unit_short(r["推广单元ID"]), (r["利用率"], r["M匹配度"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=8, ha=ha,
                fontweight="bold" if r["临界"] else "normal")
ax.axvline(U0, color="#666666", linewidth=1.0, linestyle="--")
ax.axhline(M0, color="#666666", linewidth=1.0, linestyle="--")
ax.text(0.99, 0.97, "Ⅰ 高利用·高匹配", transform=ax.transAxes,
        ha="right", va="top", fontsize=8.5, color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9", edgecolor="none"))
ax.text(0.01, 0.97, "Ⅱ 低利用·高匹配", transform=ax.transAxes,
        ha="left", va="top", fontsize=8.5, color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E3F2FD", edgecolor="none"))
ax.text(0.01, 0.03, "Ⅲ 低利用·低匹配", transform=ax.transAxes,
        ha="left", va="bottom", fontsize=8.5, color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FCE4EC", edgecolor="none"))
ax.text(0.99, 0.03, "Ⅳ 高利用·低匹配", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=8.5, color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF3E0", edgecolor="none"))
ax.set_xlim(0.35, 1.03)
ax.set_ylim(0.55, 1.0)
ax.set_xlabel(f"关键词利用率U（中位{U0:.4f}）")
ax.set_ylabel(f"投入—点击匹配度M（中位{M0:.4f}）")
ax.set_title("推广单元关键词管理U–M四象限", pad=10)
import matplotlib.patches as mpatches
ax.legend(handles=[mpatches.Patch(color=c, label=f"方案{p}")
                   for p, c in PLAN_COLORS.items()] +
                  [plt.Line2D([0], [0], marker="o", color="w",
                               markerfacecolor="#999999",
                               markeredgecolor=OI["vermillion"], markeredgewidth=2,
                               markersize=8, label="临界单元（距分界<0.01）")],
          frameon=True, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5)
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_图1_UM四象限")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("图1 done")
print(summ[summ["临界"]][["推广单元ID", "利用率", "M匹配度", "象限"]].to_string(index=False))
