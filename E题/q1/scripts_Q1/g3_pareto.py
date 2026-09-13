# -*- coding: utf-8 -*-
"""G3 帕累托：总体1张 + 3重点单元各1张。
柱=关键词消费额（前N单列+其余合并为其他），折线=累计消费/点击占比。
双轴理由：左轴金额、右轴占比，量纲不同，帕累托标准画法，题注声明。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, PLAN_COLORS, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGD = os.path.join(ROOT, "charts_Q1")


def pareto(df, title, stem, topn=20, keycol="关键词"):
    d = df.sort_values("消费额", ascending=False).reset_index(drop=True)
    head = d.head(topn)
    tot_sp, tot_ck = d["消费额"].sum(), d["点击量"].sum()
    n_all = len(d)
    # 柱只画前N；累计线在前N位置取值后连到终点“全部”（标注长尾增量）
    xs = list(range(topn)) + [topn]
    cum_sp = (head["消费额"].cumsum().tolist() + [tot_sp])
    cum_sp = [v / tot_sp * 100 for v in cum_sp]
    cum_ck = (head["点击量"].cumsum().tolist() + [tot_ck])
    cum_ck = [v / tot_ck * 100 for v in cum_ck]

    fig, ax1 = plt.subplots(figsize=(FIG_W_FULL, 105 * MM))
    x = np.arange(topn)
    ax1.bar(x, head["消费额"].values, color=OI["blue"], edgecolor="white", zorder=2)
    ax1.set_ylabel("消费额（元）")
    ax1.set_xlim(-0.6, topn + 0.6)
    ax1.set_xticks(xs)
    ax1.set_xticklabels([str(k) for k in head[keycol].tolist()] + [f"全部{n_all}词"],
                        rotation=45, ha="right", fontsize=7)
    ax2 = ax1.twinx()
    ax2.plot(xs, cum_sp, color=OI["blue"], linewidth=1.8, marker="o",
             markersize=4, label="累计消费占比")
    ax2.plot(xs, cum_ck, color=OI["orange"], linewidth=1.5,
             linestyle="--", marker="s", markersize=4, label="累计点击占比")
    ax2.set_ylabel("累计占比（%）")
    ax2.set_ylim(0, 105)
    ax1.set_title(title + f"：前{topn}占消费{head['消费额'].sum()/tot_sp:.1%}",
                  pad=10)
    for i in range(min(3, topn)):
        ax1.annotate(f"{head['消费额'].iloc[i]:,.0f}元", (x[i], head["消费额"].iloc[i]),
                     xytext=(0, 4), textcoords="offset points",
                     ha="center", fontsize=7.5)
    h2, l2 = ax2.get_legend_handles_labels()
    ax2.legend(h2, l2, frameon=True, loc="center right", fontsize=8)
    ax1.grid(axis="y", linestyle="--", linewidth=0.4, color="#CCCCCC")
    fig.tight_layout()
    fig.savefig(stem + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
    fig.savefig(stem + ".png", dpi=300, bbox_inches="tight", transparent=False)
    plt.close(fig)
    print(stem, "Top%d消费占比=" % topn,
          round(head['消费额'].sum() / tot_sp, 4))


overall = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_pareto_overall.csv"))
pareto(overall, "关键词消费帕累托（总体）",
       os.path.join(FIGD, "q1_g3a_帕累托总体"), topn=20)
for uid in [9657930100, 9811363528, 9630806627]:
    df = pd.read_csv(os.path.join(ROOT, f"q1_pareto_unit_{uid}.csv"))
    pareto(df, f"关键词消费帕累托（单元{str(uid)[-4:]}）",
           os.path.join(FIGD, f"q1_g3b_帕累托单元{str(uid)[-4:]}"), topn=15)
