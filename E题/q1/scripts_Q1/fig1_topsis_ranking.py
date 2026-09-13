# -*- coding: utf-8 -*-
"""
fig1_topsis_ranking.png —— 12个推广单元 TOPSIS 综合得分排名

对应论文图：2025年各推广单元广告设计质量与创意综合评价
输出：figures/fig1_topsis_ranking.png

方法链路（与原分析完全一致）：
  Sheet1 年度 CTR（正向） + Sheet3 跳出率（负向）/平均访问时长（正向）
  -> 同向化 -> Min-Max 标准化 -> 熵权法定权 -> TOPSIS 综合贴近度 C

本脚本自包含，不依赖其他脚本，直接 python fig1_topsis_ranking.py 即可运行。
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================================================================
# 0. 全局设置：路径 / 中文字体 / 配色
# ============================================================================
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, "..", "..", "题目", "附件", "附件1.xlsx"))  # 数据源，只读
OUT_FIG = os.path.join(BASE, "..", "charts_Q1")
OUT_DAT = os.path.join(BASE, "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]  # 中文字体
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42        # PDF 内嵌 TrueType，中文不乱码
plt.rcParams["svg.fonttype"] = "none"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
S1, S2, S3_ = "#2a78d6", "#eb6834", "#1baf7a"    # 分类槽位 1/2/3
HOT = "#184f95"                                   # 强调深蓝
DPI = 300


def style_ax(ax):
    """简洁学术风格：细实线网格 + 退化坐标轴。"""
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


def dur_to_sec(v):
    """'HH:MM:SS' -> 秒；缺失/异常 -> NaN。"""
    parts = str(v).strip().split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return np.nan
    return np.nan


# ============================================================================
# 1. 读取数据并构建 12 个推广单元的年度指标表
# ============================================================================
if not os.path.exists(SRC):
    raise FileNotFoundError("找不到数据文件: %s" % SRC)

s1 = pd.read_excel(SRC, sheet_name="Sheet1")     # 日 × 推广单元，含真实日期
s3 = pd.read_excel(SRC, sheet_name="Sheet3")     # 关键词级，无日期（全年快照）
s3.columns = [c.strip() for c in s3.columns]

# 口径核验：两表同属一批投放，方可联结
assert s1["点击量"].sum() == s3["点击量"].sum(), "Sheet1/Sheet3 口径不一致"

s3["_跳出率"] = pd.to_numeric(s3["跳出率"].astype(str).str.strip(), errors="coerce")
s3["_秒"] = s3["平均访问时长"].astype(str).str.strip().map(dur_to_sec)

a1 = s1.groupby("推广单元ID").agg(
    全年展现量=("展现量", "sum"), 全年点击量=("点击量", "sum"))


def wavg(g, col):
    """按点击量加权聚合。缺失行恰为 点击量==0，权重自然为 0。"""
    w, v = g["点击量"], g[col]
    ok = v.notna() & (w > 0)
    return np.nan if w[ok].sum() == 0 else float((v[ok] * w[ok]).sum() / w[ok].sum())


a3 = s3.groupby("推广单元ID").apply(
    lambda g: pd.Series({"跳出率": wavg(g, "_跳出率"), "平均访问时长秒": wavg(g, "_秒")}),
    include_groups=False)

ann = a1.join(a3)
ann["CTR"] = ann["全年点击量"] / ann["全年展现量"]
ann = ann.sort_values("全年点击量", ascending=False)

# ============================================================================
# 2. 同向化 -> Min-Max 标准化 -> 熵权法 -> TOPSIS
# ============================================================================
EVAL = [("CTR", "正向"), ("跳出率", "负向"), ("平均访问时长秒", "正向")]

X = ann[[k for k, _ in EVAL]].astype(float).values
n = X.shape[0]

# 2.1 同向化：负向指标翻转，使全部指标"越大越优"
X_dir = X.copy()
for j, (_, d) in enumerate(EVAL):
    if d == "负向":
        X_dir[:, j] = X[:, j].max() - X[:, j]

# 2.2 Min-Max 标准化到 [0, 1]
Xmin, Xmax = X_dir.min(axis=0), X_dir.max(axis=0)
rng = np.where((Xmax - Xmin) == 0, 1.0, Xmax - Xmin)
Z = (X_dir - Xmin) / rng

# 2.3 熵权法：离散度越大 -> 信息熵越小 -> 权重越高
P = Z + 1e-6
P = P / P.sum(axis=0, keepdims=True)
E = -(1.0 / np.log(n)) * (P * np.log(P)).sum(axis=0)
D = 1.0 - E
W = D / D.sum()
print("熵权法权重: CTR=%.4f  跳出率=%.4f  平均访问时长=%.4f" % tuple(W))

# 2.4 TOPSIS：与正理想解越近、与负理想解越远，则 C 越大
V = Z * W
ideal_best, ideal_worst = V.max(axis=0), V.min(axis=0)
d_best = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
d_worst = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))
C = d_worst / (d_best + d_worst)

res = pd.DataFrame({"推广单元ID": ann.index, "综合得分C": C}) \
    .sort_values("综合得分C", ascending=False).reset_index(drop=True)
res.insert(0, "排名", np.arange(1, len(res) + 1))
print(res.round(4).to_string(index=False))

# ============================================================================
# 3. 绘图
# ============================================================================
fig, ax = plt.subplots(figsize=(8.0, 4.4))
fig.patch.set_facecolor(SURFACE)

labels = [str(int(u)) for u in res["推广单元ID"]]
cvals = res["综合得分C"].values
colors = [S1] * len(cvals)
colors[0] = HOT            # 最高分单元
colors[-1] = MUTED         # 最低分单元
bars = ax.bar(labels, cvals, color=colors, width=0.62, zorder=3)

# 柱顶标注 C 值，保留 4 位小数
for b, v in zip(bars, cvals):
    ax.annotate("%.4f" % v, xy=(b.get_x() + b.get_width() / 2, v),
                xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=8.5, color=INK2, fontweight="bold")

# 明确标出最高 / 最低推广单元
ax.annotate("最高：%s\nC = %.4f" % (labels[0], cvals[0]),
            xy=(0, cvals[0]), xytext=(14, -18), textcoords="offset points",
            fontsize=9.5, color=HOT, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=HOT, linewidth=0.9))
ax.annotate("最低：%s\nC = %.4f" % (labels[-1], cvals[-1]),
            xy=(len(cvals) - 1, cvals[-1]), xytext=(-16, 34),
            textcoords="offset points", fontsize=9.5, color=INK2,
            fontweight="bold", ha="right",
            arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.9))

ax.set_ylabel("TOPSIS 综合贴近度 C", fontsize=10, color=INK2)
ax.set_xlabel("推广单元 ID（按 C 值降序）", fontsize=9.5, color=MUTED)
ax.set_title("2025年各推广单元广告设计质量与创意综合评价",
             fontsize=12, color=INK, pad=10)
ax.tick_params(axis="x", labelsize=8, rotation=35)
ax.set_ylim(0, max(cvals.max() * 1.22, 1e-6))
ax.legend(handles=[Patch(facecolor=HOT, label="最高分单元"),
                   Patch(facecolor=S1, label="其他单元"),
                   Patch(facecolor=MUTED, label="最低分单元")],
          frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper right")
style_ax(ax)
savefig(fig, "fig1_topsis_ranking")
print("完成。输出目录: %s" % (OUT_FIG + ' / ' + OUT_DAT))
