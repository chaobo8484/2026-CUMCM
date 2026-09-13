# -*- coding: utf-8 -*-
"""
fig4_monthly_ctr_trend.png —— 2025年广告点击吸引效果月度变化趋势

对应论文图：2025年广告点击吸引效果月度变化趋势
输出：figures/fig4_monthly_ctr_trend.png

要点：
  只使用 Sheet1 中【带真实日期】的字段。先按月份汇总总量，再相除：
      月度CTR = Σ当月点击量 / Σ当月展现量
  绝不直接对每天 CTR 求简单平均。

  重要：Sheet3 无日期字段，因此本图【不包含】月度跳出率、月度平均访问时长，
  也不构造"月度创意 TOPSIS 得分"——这些数据不存在。

  另注：月度总量受投放组合变化（结构漂移）影响，CTR 下降不等于创意质量退化。
  12个推广单元中仅 9628223555、9630806627 全年 12 个月均有投放。

本脚本自包含，不依赖其他脚本，直接 python fig4_monthly_ctr_trend.py 即可运行。
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ============================================================================
# 0. 全局设置：路径 / 中文字体 / 配色
# ============================================================================
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, "..", "..", "题目", "附件", "附件1.xlsx"))  # 数据源，只读
OUT_FIG = os.path.join(BASE, "..", "charts_Q1")
OUT_DAT = os.path.join(BASE, "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["svg.fonttype"] = "none"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
S1 = "#2a78d6"
DPI = 300


def style_ax(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, which="major", color=GRID, linewidth=0.6, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=INK2, labelsize=9, width=0.8, length=3)


def savefig(fig, stem):
    """只输出 300dpi PNG。"""
    for ext in ("png",):
        fig.savefig(os.path.join(OUT_FIG, "%s.%s" % (stem, ext)),
                    dpi=DPI, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print("已保存: %s.png" % stem)


# ============================================================================
# 1. 读取 Sheet1（唯一含真实日期的表）
# ============================================================================
if not os.path.exists(SRC):
    raise FileNotFoundError("找不到数据文件: %s" % SRC)

s1 = pd.read_excel(SRC, sheet_name="Sheet1")
print("Sheet1 %s，日期范围 %s ~ %s"
      % (s1.shape, s1["日期"].min().date(), s1["日期"].max().date()))

# ============================================================================
# 2. 按月汇总：先汇总总量，再相除
# ============================================================================
s1 = s1.copy()
s1["月份"] = s1["日期"].dt.month

m = s1.groupby("月份").agg(展现量=("展现量", "sum"), 点击量=("点击量", "sum"))
m["CTR"] = m["点击量"] / m["展现量"]          # 关键：先汇总再相除，不对日 CTR 取均值
m = m.reindex(range(1, 13))
m.index.name = "月份"
assert m["CTR"].notna().all(), "存在无数据月份，无法绘制完整 12 个月"

months = np.arange(1, 13)
xlab = ["%d月" % i for i in months]
y = m["CTR"].values * 100.0
avg = m["点击量"].sum() / m["展现量"].sum() * 100.0
imax, imin = int(np.argmax(y)), int(np.argmin(y))
print("全年平均 CTR = %.4f%%；最高 %d月 %.2f%%；最低 %d月 %.2f%%"
      % (avg, months[imax], y[imax], months[imin], y[imin]))

# ============================================================================
# 3. 绘图
# ============================================================================
fig, ax = plt.subplots(figsize=(8.0, 4.3))
fig.patch.set_facecolor(SURFACE)

# 全年平均 CTR 参考虚线
ax.axhline(avg, color=MUTED, linewidth=1.1, linestyle="--", zorder=2,
           label="全年平均 CTR = %.2f%%" % avg)

# 月度 CTR 折线，12 个月全部显示
ax.plot(months, y, "-o", color=S1, linewidth=1.9, markersize=6,
        markerfacecolor=S1, markeredgecolor=SURFACE, markeredgewidth=1.3,
        zorder=3, label="月度 CTR")

# 标出全年最高 / 最低月份
for i, tag, col, dy in ((imax, "最高", "#006300", 16), (imin, "最低", "#d03b3b", -34)):
    ax.annotate("%s：%d月\n%.2f%%" % (tag, months[i], y[i]),
                xy=(months[i], y[i]), xytext=(0, dy), textcoords="offset points",
                ha="center", fontsize=9, color=col, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=col, linewidth=0.9))

ax.set_xticks(months)
ax.set_xticklabels(xlab)
ax.set_ylabel("月度 CTR（%）", fontsize=10, color=INK2)
ax.set_xlabel("月份（2025 年）", fontsize=9.5, color=MUTED)
ax.set_title("2025年广告点击吸引效果月度变化趋势", fontsize=12, color=INK, pad=10)
ax.set_ylim(0, max(y) * 1.30)
ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="upper right")
style_ax(ax)
savefig(fig, "fig4_monthly_ctr_trend")

# ============================================================================
# 4. 输出底层数据
# ============================================================================
tab = pd.DataFrame({
    "月份": xlab,
    "展现量": m["展现量"].astype(int).values,
    "点击量": m["点击量"].astype(int).values,
    "月度CTR": m["CTR"].values,
    "月度CTR(%)": y,
})
tab.to_csv(os.path.join(OUT_DAT, "图4_月度CTR数据.csv"),
           index=False, encoding="utf-8-sig", float_format="%.6f")
print("已保存: 图4_月度CTR数据.csv")
print(tab.to_string(index=False))
print("完成。输出目录: %s" % (OUT_FIG + ' / ' + OUT_DAT))
