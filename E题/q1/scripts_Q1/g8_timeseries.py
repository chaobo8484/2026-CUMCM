# -*- coding: utf-8 -*-
"""G8 时序：a)日消费&日注册双轴（量纲不同，题注声明）+7日均线；
b)CPA日序列+7日均线+年均线。峰谷自动标注。"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from style_q1 import apply_style, OI, FIG_W_FULL, MM

apply_style()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGD = os.path.join(ROOT, "charts_Q1")
d = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_daily.csv"), parse_dates=["日期"])
d = d.sort_values("日期").reset_index(drop=True)
d["消费MA7"] = d["消费"].rolling(7, center=True).mean()
d["注册MA7"] = d["新注册数"].rolling(7, center=True).mean()
d["CPAMA7"] = d["CPA"].rolling(7, center=True).mean()
CPA_MEAN = d["消费"].sum() / d["新注册数"].sum()

# a) 消费 & 注册（双轴：左元、右人，量纲不同故双轴）
fig, ax1 = plt.subplots(figsize=(FIG_W_FULL, 100 * MM))
ax1.plot(d["日期"], d["消费"], color=OI["blue"], linewidth=1.0, alpha=0.5)
ax1.plot(d["日期"], d["消费MA7"], color=OI["blue"], linewidth=1.8)
ax1.set_ylabel("日消费（元）", color=OI["blue"])
ax2 = ax1.twinx()
ax2.plot(d["日期"], d["新注册数"], color=OI["orange"], linewidth=1.0, alpha=0.5)
ax2.plot(d["日期"], d["注册MA7"], color=OI["orange"], linewidth=1.8,
         linestyle="--")
ax2.set_ylabel("日注册（人）", color=OI["orange"])
rc = d.loc[d["消费"].idxmax()]
ax1.annotate(f"{rc['日期'].date()}消费峰\n{rc['消费']:.0f}元",
             (rc["日期"], rc["消费"]), xytext=(72, -62),
             textcoords="offset points", ha="center", fontsize=7.5,
             arrowprops=dict(arrowstyle="->", color="#666666", linewidth=0.8))
rr = d.loc[d["新注册数"].idxmax()]
ax2.annotate(f"{rr['日期'].date()}注册峰\n{rr['新注册数']:.0f}人",
             (rr["日期"], rr["新注册数"]), xytext=(-95, 32),
             textcoords="offset points", ha="center", fontsize=7.5,
             arrowprops=dict(arrowstyle="->", color="#666666", linewidth=0.8))
ax1.set_title("日消费与日注册协同变化（双轴：左右量纲不同）", pad=12)
ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
from matplotlib.lines import Line2D
ax1.legend(handles=[Line2D([0], [0], color=OI["blue"], linewidth=1.0,
                            alpha=0.5, label="日消费"),
                    Line2D([0], [0], color=OI["blue"], linewidth=1.8,
                            label="日消费（7日均线）"),
                    Line2D([0], [0], color=OI["orange"], linewidth=1.0,
                            alpha=0.5, label="日注册"),
                    Line2D([0], [0], color=OI["orange"], linewidth=1.8,
                            linestyle="--", label="日注册（7日均线）")],
           frameon=True, loc="upper right", fontsize=7.5)
ax1.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
fig.savefig(os.path.join(FIGD, "q1_g8a_消费注册时序.pdf"), dpi=300,
            bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(FIGD, "q1_g8a_消费注册时序.png"), dpi=300,
            bbox_inches="tight", transparent=False)
plt.close(fig)

# b) CPA（单天319.6极端值截断显示，主体才看得清）
fig, ax = plt.subplots(figsize=(FIG_W_FULL, 95 * MM))
ax.plot(d["日期"], d["CPA"], color=OI["grey"], linewidth=1.0, alpha=0.6)
ax.plot(d["日期"], d["CPAMA7"], color=OI["vermillion"], linewidth=1.8,
        label="CPA（7日均线）")
ax.axhline(CPA_MEAN, color="#333333", linewidth=1.2, linestyle="--",
           label=f"年均CPA {CPA_MEAN:.2f}元/人")
ax.set_ylim(0, 80)
r = d.loc[d["CPA"].idxmax()]
ax.text(0.02, 0.96,
        f"{r['日期'].date()}CPA={r['CPA']:.1f}元/人（注册仅{int(r['新注册数'])}人）"
        f"超出显示",
        transform=ax.transAxes, ha="left", va="top", fontsize=8, color="#333333")
ax.set_ylabel("CPA（元/人）")
ax.set_title("日CPA时间序列", pad=10)
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
ax.legend(frameon=True, loc="upper right", fontsize=8)
ax.grid(True, linestyle="--", linewidth=0.4, color="#CCCCCC")
fig.tight_layout()
fig.savefig(os.path.join(FIGD, "q1_g8b_CPA时序.pdf"), dpi=300,
            bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(FIGD, "q1_g8b_CPA时序.png"), dpi=300,
            bbox_inches="tight", transparent=False)
plt.close(fig)
print("G8 done, 年均CPA=", round(CPA_MEAN, 2))
