# -*- coding: utf-8 -*-
"""
E题 问题2「关键词成本—效益五分类」图表组
设计/字体对齐 bid_budget_analysis.py：白底、去上右边框、浅灰网格、300dpi。
输出：E题/q2/charts_Q2/ 下 7 张 PNG
  Q2-1 成本—效益四象限   Q2-2 五类数量占比     Q2-3 各单元五类构成   Q2-4 各类投入贡献
  Q2-5 分类稳定性        Q2-6 类别指标分布     Q2-7 单元-类别热力图
数据源：E题/q2/data_Q2/*.csv（q2_keyword_classification.py 产物）
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager
from matplotlib.lines import Line2D

BASE = os.path.dirname(os.path.abspath(__file__))
Q2 = os.path.dirname(BASE)
D = os.path.join(Q2, "data_Q2")
OUT = os.path.join(Q2, "charts_Q2")
os.makedirs(OUT, exist_ok=True)
LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

# ---------------- 设计基座（同 bid_budget_analysis.py） ----------------
def set_cjk_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for n in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "PingFang SC"]:
        if n in have:
            plt.rcParams["font.sans-serif"] = [n]; plt.rcParams["axes.unicode_minus"] = False
            return n
    raise RuntimeError("无中文字体")
FONT = set_cjk_font()
BLUE, ORANGE, GREEN, PURPLE, PINK = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#c2185b"
INK, INK2, MUTED, GRID, REF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#9a9890"
GOLD, KEY, POT, PROB, INV = "#E69F00", "#0072B2", "#009E73", "#D55E00", "#999999"
CATS = ["黄金词", "重点词", "潜力词", "问题词", "无效词"]
CCOL = {"黄金词": GOLD, "重点词": KEY, "潜力词": POT, "问题词": PROB, "无效词": INV}
DPI = 300
plt.rcParams.update({"font.size": 10.5, "axes.unicode_minus": False, "savefig.dpi": DPI})

def new_fig(w=10.4, h=7.4):
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor="white")
    ax = fig.add_subplot(111); style(ax); return fig, ax

def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2); ax.spines[s].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.9); ax.set_axisbelow(True)

def footnote(ax, text, y=-0.155):
    ax.text(0.5, y, text, transform=ax.transAxes, ha="center", va="top", fontsize=7.5, color=MUTED)

def save(fig, name):
    import time
    p = os.path.join(OUT, name + ".png")
    for attempt in range(6):
        try:
            fig.savefig(p, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
            break
        except OSError:
            if attempt == 5:
                raise
            time.sleep(0.4)
    plt.close(fig); log("  已保存: " + p); return p

# ---------------- 数据 ----------------
def rd(n): return pd.read_csv(os.path.join(D, n), encoding="utf-8-sig")
rec = rd("q2_record_clean.csv")
act = rd("q2_active_topsis.csv")
cat = rd("q2_category_summary.csv").set_index("类别")
contrib = rd("q2_contribution.csv").set_index("类别")
C_THR, S_THR = 8.06, 0.3193

# ================================================================ Q2-1 成本—效益四象限
fig, ax = new_fig(10.6, 7.6)
X = np.log1p(act["消费额"].values)
Y = act["S"].values
sz = 12 + 60 * (np.log1p(act["点击量"].values) / np.log1p(act["点击量"].max()))
for c in ["潜力词", "问题词", "重点词", "黄金词"]:      # 先画大/低层，黄金词在上
    m = act["基准类别"].values == c
    ax.scatter(X[m], Y[m], s=sz[m], c=CCOL[c], alpha=0.55, edgecolors="none", zorder=3, label=c)
# 敏感词黑边
ms = act["敏感性"].values == "边界敏感词"
ax.scatter(X[ms], Y[ms], s=sz[ms] * 1.4, facecolors="none", edgecolors=INK, linewidths=0.7,
           zorder=4, label="边界敏感词")
ax.axvline(np.log1p(C_THR), color=INK2, ls="--", lw=1.4, zorder=2)
ax.axhline(S_THR, color=INK2, ls="--", lw=1.4, zorder=2)
ax.text(np.log1p(C_THR) + 0.08, ax.get_ylim()[1] * 0.985, f"成本阈值 {C_THR} 元", rotation=90,
        va="top", fontsize=9.5, color=MUTED)
ax.text(0.06, S_THR + 0.012, f"效益阈值 {S_THR}", fontsize=9.5, color=MUTED)
# 象限标注
ax.text(0.015, 0.975, "低成本·高效益\n黄金词", transform=ax.transAxes, ha="left", va="top",
        fontsize=11, color=GOLD)
ax.text(0.985, 0.975, "高成本·高效益\n重点词", transform=ax.transAxes, ha="right", va="top",
        fontsize=11, color=KEY)
ax.text(0.015, 0.025, "低成本·低效益\n潜力词", transform=ax.transAxes, ha="left", va="bottom",
        fontsize=11, color=POT)
ax.text(0.985, 0.025, "高成本·低效益\n问题词", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=11, color=PROB)
ax.set_xlabel("ln(1 + 全年消费额)   →  成本越高", fontsize=12.5, color=INK)
ax.set_ylabel("综合效益得分 S  →  效益越高", fontsize=12.5, color=INK)
ax.set_title("关键词成本—效益分类散点图（1337 条活跃记录）", fontsize=15, color=INK, pad=14)
leg = ax.legend(frameon=False, fontsize=10.5, loc="center left", bbox_to_anchor=(1.01, 0.5))
fig.subplots_adjust(left=0.09, right=0.80, top=0.90, bottom=0.14)
save(fig, "Q2-1_成本效益四象限")

# ================================================================ Q2-2 五类数量与占比
fig, ax = new_fig(10.4, 6.4)
cc = cat.reindex(CATS)
ypos = np.arange(len(CATS))[::-1]
bars = ax.barh(ypos, cc["记录数"].values, color=[CCOL[c] for c in CATS],
               edgecolor="white", lw=1.0, height=0.62, zorder=3)
for i, c in zip(ypos, CATS):
    n = int(cc.loc[c, "记录数"]); p = cc.loc[c, "占全部记录比例"]
    ax.text(n + 12, i, f"{n} 条（{p:.2f}%）", va="center", fontsize=11, color=INK)
ax.set_yticks(ypos); ax.set_yticklabels(CATS, fontsize=12)
ax.set_xlim(0, cc["记录数"].max() * 1.28)
ax.set_xlabel("关键词记录数（条）", fontsize=12.5, color=INK)
ax.set_title("五类关键词记录数量与占比（合计 2227 条）", fontsize=15, color=INK, pad=14)
fig.subplots_adjust(left=0.12, right=0.97, top=0.90, bottom=0.14)
save(fig, "Q2-2_五类数量占比")

# ================================================================ Q2-3 各单元五类构成（100%堆积）
uc = (rec.groupby(["方案ID", "推广单元ID", "基准类别"]).size()
        .unstack(fill_value=0).reindex(columns=CATS, fill_value=0))
tot = uc.sum(axis=1)
pct = uc.div(tot, axis=0) * 100
labels = [f"{p}·{u}" for p, u in pct.index]
fig, ax = new_fig(11.0, 7.2)
y = np.arange(len(pct))[::-1]
left = np.zeros(len(pct))
for c in CATS:
    v = pct[c].values
    ax.barh(y, v, left=left, color=CCOL[c], edgecolor="white", lw=0.8, height=0.66, zorder=3, label=c)
    for i, (l, vv) in enumerate(zip(left, v)):
        if vv >= 7:
            ax.text(l + vv / 2, y[i], f"{vv:.0f}", ha="center", va="center", fontsize=8.5,
                    color="white" if c in ("重点词", "问题词") else INK)
    left += v
for i, (yy, t) in enumerate(zip(y, tot.values)):
    ax.text(101, yy, f"{int(t)}条", va="center", fontsize=9.5, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10)
ax.set_xlim(0, 108); ax.set_xlabel("各类关键词在该推广单元内的占比（%）", fontsize=12.5, color=INK)
ax.set_title("各推广单元五类关键词构成（100%堆积，柱端为总记录数）", fontsize=15, color=INK, pad=14)
ax.legend(ncol=5, frameon=False, fontsize=10.5, loc="upper center", bbox_to_anchor=(0.5, -0.08))
fig.subplots_adjust(left=0.16, right=0.95, top=0.90, bottom=0.20)
save(fig, "Q2-3_各单元五类构成")

# ================================================================ Q2-4 各类投入与贡献
fig, axes = plt.subplots(1, 2, figsize=(11.4, 6.8), dpi=DPI, gridspec_kw={"wspace": 0.24})
a0, a1 = axes; style(a0); style(a1)
inds = ["消费额占比", "点击量占比", "浏览量占比"]
xlab = ["消费额", "点击量", "浏览量"]
xx = np.arange(3); wd = 0.15
for i, c in enumerate(CATS):
    vals = [contrib.loc[c, k] for k in inds]
    a0.bar(xx + (i - 2) * wd, vals, width=wd, color=CCOL[c], edgecolor="white", lw=0.5, label=c, zorder=3)
a0.set_yscale("log"); a0.set_ylim(3e-4, 300)
a0.set_xticks(xx); a0.set_xticklabels(xlab)
a0.set_ylabel("占全体的比例（%，对数刻度）", fontsize=11.5, color=INK)
a0.set_title("(a) 全集：重点词贡献 99% 以上", fontsize=12.5, color=INK, pad=10, loc="left")
a0.legend(frameon=False, fontsize=9.5, ncol=2, loc="upper right")
# (b) 剔除重点词
sub = contrib.drop(index="重点词")
for i, c in enumerate([c for c in CATS if c != "重点词"]):
    vals = [sub.loc[c, k] for k in inds]
    a1.bar(xx + (i - 1.5) * wd, vals, width=wd, color=CCOL[c], edgecolor="white", lw=0.5, label=c, zorder=3)
    for x, v in zip(xx + (i - 1.5) * wd, vals):
        a1.text(x, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8, color=INK2)
a1.set_xticks(xx); a1.set_xticklabels(xlab)
a1.set_ylabel("占全体的比例（%）", fontsize=11.5, color=INK)
a1.set_title("(b) 剔除重点词：黄金/潜力/问题/无效对比", fontsize=12.5, color=INK, pad=10, loc="left")
a1.legend(frameon=False, fontsize=9.5, loc="upper right")
fig.suptitle("各类别投入与流量贡献", fontsize=15, color=INK, y=0.97)
fig.subplots_adjust(left=0.075, right=0.98, top=0.87, bottom=0.14)
save(fig, "Q2-4_各类投入与贡献")

# ================================================================ Q2-5 分类稳定性（敏感性）
fig, axes = plt.subplots(1, 2, figsize=(11.4, 6.8), dpi=DPI, gridspec_kw={"wspace": 0.22})
a0, a1 = axes; style(a0); style(a1)
scen = ["基准等权", "流量优先", "质量优先"]
xx = np.arange(len(scen))
for i, c in enumerate(["黄金词", "重点词", "潜力词", "问题词"]):
    vals = [int((act["类别_" + s] == c).sum()) for s in scen]
    a0.bar(xx + (i - 1.5) * 0.2, vals, width=0.2, color=CCOL[c], edgecolor="white", lw=0.6, label=c, zorder=3)
    for x, v in zip(xx + (i - 1.5) * 0.2, vals):
        a0.text(x, v, str(v), ha="center", va="bottom", fontsize=8, color=INK2)
a0.set_xticks(xx); a0.set_xticklabels(scen, fontsize=11.5)
a0.set_ylabel("活跃记录数（条）", fontsize=11.5, color=INK)
a0.set_ylim(0, 560)
a0.set_title("(a) 三情景下四类数量", fontsize=12.5, color=INK, pad=10, loc="left")
a0.legend(frameon=False, fontsize=9.5, ncol=2, loc="upper left")
n_st = int(act["稳定词"].sum()); n_se = len(act) - n_st
a1.bar([0], [n_st], color=KEY, width=0.5, edgecolor="white", zorder=3, label="稳定词")
a1.bar([1], [n_se], color=PROB, width=0.5, edgecolor="white", zorder=3, label="边界敏感词")
for x, v in [(0, n_st), (1, n_se)]:
    a1.text(x, v + 10, f"{v} 条\n({v/len(act)*100:.2f}%)", ha="center", fontsize=11, color=INK)
a1.set_xticks([0, 1]); a1.set_xticklabels(["三种权重下类别一致", "至少一次变化"], fontsize=11)
a1.set_ylabel("活跃记录数（条）", fontsize=11.5, color=INK)
a1.set_ylim(0, max(n_st, n_se) * 1.35)
a1.set_title("(b) 稳定性构成", fontsize=12.5, color=INK, pad=10, loc="left")
fig.suptitle("分类稳定性：三组权重下 86.16% 的活跃记录类别不变", fontsize=15, color=INK, y=0.97)
fig.subplots_adjust(left=0.08, right=0.98, top=0.87, bottom=0.14)
save(fig, "Q2-5_分类稳定性")

# ================================================================ Q2-6 类别指标分布（桥接Q3）
fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.2), dpi=DPI, gridspec_kw={"hspace": 0.42, "wspace": 0.24})
metrics = [("S", "综合效益得分 S", False),
           ("消费额", "ln(1+消费额)", True),
           ("点击量", "ln(1+点击量)", True),
           ("浏览深度", "ln(1+浏览深度)", True)]
for ax, (col, ttl, logv) in zip(axes.ravel(), metrics):
    style(ax)
    data = []
    for c in ["黄金词", "重点词", "潜力词", "问题词"]:
        v = act.loc[act["基准类别"] == c, col].values
        data.append(np.log1p(v) if logv else v)
    bp = ax.boxplot(data, patch_artist=True, widths=0.55, showfliers=False,
                    medianprops=dict(color=INK, lw=1.4),
                    whiskerprops=dict(color=INK2), capprops=dict(color=INK2))
    for patch, c in zip(bp["boxes"], ["黄金词", "重点词", "潜力词", "问题词"]):
        patch.set_facecolor(CCOL[c]); patch.set_alpha(0.75); patch.set_edgecolor("white")
    ax.set_xticklabels(["黄金", "重点", "潜力", "问题"], fontsize=10.5)
    ax.set_title(ttl, fontsize=12, color=INK, pad=8, loc="left")
fig.suptitle("五类关键词关键指标分布（1337 条活跃记录）", fontsize=15, color=INK, y=0.97)
fig.subplots_adjust(left=0.075, right=0.98, top=0.90, bottom=0.10)
save(fig, "Q2-6_类别指标分布")

# ================================================================ Q2-7 单元-类别消费额热力图
hm = (rec.groupby(["方案ID", "推广单元ID", "基准类别"])["消费额"].sum()
        .unstack(fill_value=0).reindex(columns=CATS, fill_value=0))
hm_pct = hm.div(hm.sum(axis=1).replace(0, np.nan), axis=0) * 100
fig, ax = new_fig(10.8, 7.2)
M = hm_pct.values
im = ax.imshow(np.log1p(M), cmap="viridis", aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels(CATS, fontsize=11)
ylab = [f"{p}·{u}" for p, u in hm_pct.index]
ax.set_yticks(range(len(ylab))); ax.set_yticklabels(ylab, fontsize=10)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M[i, j]
        if v > 0.005:
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=9,
                    color="white" if np.log1p(v) > 3.2 else INK)
ax.grid(False)
cb = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.85)
cb.set_label("单元内该类消费占比（%，颜色=log1p）", fontsize=11, color=INK)
cb.ax.tick_params(labelsize=9.5, colors=INK2)
ax.set_title("推广单元—类别 消费额构成热力图（行内合计 100%）", fontsize=15, color=INK, pad=14)
fig.subplots_adjust(left=0.16, right=0.98, top=0.91, bottom=0.12)
save(fig, "Q2-7_单元类别热力图")

log("\nQ2 图表全部完成 -> " + OUT)
with open(os.path.join(OUT, "绘图日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
