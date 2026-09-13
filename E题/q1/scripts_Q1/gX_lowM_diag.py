# -*- coding: utf-8 -*-
"""附表 典型低M单元诊断：3个最低M单元，各自Top10词的消费份额vs点击份额并排柱；
子图标题带HHI*/Top10双占比/Gap。只解释M为什么低，不做跨单元排名。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style_q1 import apply_style, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summ = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_unit_summary.csv"))
ATT = os.path.join(ROOT, "题目", "附件", "附件1_汇总")
parts = []
for f in sorted(os.listdir(ATT)):
    if f.endswith(".xlsx") and not f.startswith("~"):
        parts.append(pd.read_excel(os.path.join(ATT, f), sheet_name="关键词"))
s3 = pd.concat(parts, ignore_index=True)

units = summ.sort_values("M匹配度").head(3)
fig, axes = plt.subplots(3, 1, figsize=(FIG_W_FULL, 150 * MM), sharey=False)
for ax, (_, r) in zip(axes, units.iterrows()):
    uid = r["推广单元ID"]
    d = s3[s3["推广单元ID"] == uid].sort_values("消费额", ascending=False).head(10)
    tot_sp, tot_ck = r["总消费"], r["总点击"]
    cs = d["消费额"].values / tot_sp * 100
    ps = d["点击量"].values / tot_ck * 100
    x = np.arange(len(d))
    w = 0.38
    ax.bar(x - w / 2, cs, width=w, color=OI["blue"], edgecolor="white",
           label="消费份额")
    ax.bar(x + w / 2, ps, width=w, color=OI["orange"], edgecolor="white",
           label="点击份额")
    for i, (c, p) in enumerate(zip(cs, ps)):
        if c - p > 2:  # 消费明显超点击的词标差值
            ax.text(i, max(c, p) + 0.4, f"+{c-p:.1f}pp", ha="center",
                    va="bottom", fontsize=7, color=OI["vermillion"])
    ax.set_xticks(x)
    ax.set_xticklabels([str(k) for k in d["关键词"].tolist()], fontsize=7)
    ax.set_ylabel("份额（%）")
    ax.set_title(f"单元{str(int(uid))[-4:]}：M={r['M匹配度']:.3f}，"
                 f"HHI*={r['HHI星']:.3f}，Top10占消费{r['Top10消费占比']:.1%}、"
                 f"占点击{r['Top10点击占比']:.1%}，Gap={r['Gap']:+.1%}",
                 fontsize=9, pad=6)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#CCCCCC")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=True, loc="lower center",
           bbox_to_anchor=(0.5, -0.01), ncols=2, fontsize=8)
fig.suptitle("典型低M单元Top10关键词消费—点击份额诊断", fontsize=10)
fig.tight_layout()
STEM = os.path.join(ROOT, "charts_Q1", "q1_附表_低M诊断")
fig.savefig(STEM + ".pdf", dpi=300, bbox_inches="tight", transparent=False)
fig.savefig(STEM + ".png", dpi=300, bbox_inches="tight", transparent=False)
print("done")
