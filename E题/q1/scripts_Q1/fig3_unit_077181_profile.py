# -*- coding: utf-8 -*-
"""
fig3_unit_077181_profile.png —— 特殊推广单元 077181 的指标画像

对应论文图：特殊推广单元077181与其他推广单元指标表现对比
输出：figures/fig3_unit_077181_profile.png
      figures/图3_数据表.csv

要点：
  077181 的 TOPSIS 贴近度出现 C = 1.0000，需单独分析。
  本图把它与其余 11 个单元放在同一标准化尺度下逐指标对比，
  判断它是否三项均达到正理想解。
  图中称其为"特殊推广单元"，不修改其任何数据。

数据表字段：推广单元ID、CTR、CTR排名、跳出率、跳出率排名、
           平均访问时长、平均访问时长排名、TOPSIS得分、TOPSIS排名

本脚本自包含，不依赖其他脚本，直接 python fig3_unit_077181_profile.py 即可运行。
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

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["svg.fonttype"] = "none"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
S1, S2, S3_ = "#2a78d6", "#eb6834", "#1baf7a"
HOT = "#184f95"
DPI = 300
TARGET = 8878077181          # 特殊推广单元 077181


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


def dur_to_sec(v):
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

s1 = pd.read_excel(SRC, sheet_name="Sheet1")
s3 = pd.read_excel(SRC, sheet_name="Sheet3")
s3.columns = [c.strip() for c in s3.columns]
assert s1["点击量"].sum() == s3["点击量"].sum(), "Sheet1/Sheet3 口径不一致"

s3["_跳出率"] = pd.to_numeric(s3["跳出率"].astype(str).str.strip(), errors="coerce")
s3["_秒"] = s3["平均访问时长"].astype(str).str.strip().map(dur_to_sec)

a1 = s1.groupby("推广单元ID").agg(
    全年展现量=("展现量", "sum"), 全年点击量=("点击量", "sum"))


def wavg(g, col):
    w, v = g["点击量"], g[col]
    ok = v.notna() & (w > 0)
    return np.nan if w[ok].sum() == 0 else float((v[ok] * w[ok]).sum() / w[ok].sum())


a3 = s3.groupby("推广单元ID").apply(
    lambda g: pd.Series({"跳出率": wavg(g, "_跳出率"), "平均访问时长秒": wavg(g, "_秒")}),
    include_groups=False)

ann = a1.join(a3)
ann["CTR"] = ann["全年点击量"] / ann["全年展现量"]
ann = ann.sort_values("全年点击量", ascending=False)
assert TARGET in set(ann.index), "特殊推广单元 %d 不在数据中" % TARGET

# ============================================================================
# 2. 同向化 + 标准化 + 熵权 + TOPSIS
# ============================================================================
EVAL = [("CTR", "正向"), ("跳出率", "负向"), ("平均访问时长秒", "正向")]

X = ann[[k for k, _ in EVAL]].astype(float).values
n = X.shape[0]

X_dir = X.copy()
for j, (_, d) in enumerate(EVAL):
    if d == "负向":
        X_dir[:, j] = X[:, j].max() - X[:, j]

Xmin, Xmax = X_dir.min(axis=0), X_dir.max(axis=0)
rng = np.where((Xmax - Xmin) == 0, 1.0, Xmax - Xmin)
Z = (X_dir - Xmin) / rng

P = Z + 1e-6
P = P / P.sum(axis=0, keepdims=True)
E = -(1.0 / np.log(n)) * (P * np.log(P)).sum(axis=0)
W = (1.0 - E) / (1.0 - E).sum()

V = Z * W
d_best = np.sqrt(((V - V.max(0)) ** 2).sum(axis=1))
d_worst = np.sqrt(((V - V.min(0)) ** 2).sum(axis=1))
C = d_worst / (d_best + d_worst)

res = pd.DataFrame({
    "推广单元ID": ann.index,
    "CTR": ann["CTR"].values,
    "跳出率": ann["跳出率"].values,
    "平均访问时长秒": ann["平均访问时长秒"].values,
    "Z_CTR": Z[:, 0], "Z_跳出率": Z[:, 1], "Z_平均访问时长": Z[:, 2],
    "TOPSIS得分C": C,
}).sort_values("TOPSIS得分C", ascending=False).reset_index(drop=True)
res.insert(0, "排名", np.arange(1, len(res) + 1))

# ============================================================================
# 3. 绘图：三指标并排水平条形图（小倍数），077181 高亮
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.5))
fig.patch.set_facecolor(SURFACE)

panels = [("Z_CTR", "CTR（正向）", S1),
          ("Z_跳出率", "跳出率（负向，已同向化）", S2),
          ("Z_平均访问时长", "平均访问时长（正向）", S3_)]

# 按 C 升序排列，使最优单元落在顶部
ord3 = res.sort_values("TOPSIS得分C", ascending=True).reset_index(drop=True)
ylab3 = [str(int(u)) for u in ord3["推广单元ID"]]

for ax, (col, title, c) in zip(axes, panels):
    v = ord3[col].values
    cols = [HOT if u == TARGET else c for u in ord3["推广单元ID"]]
    bars = ax.barh(range(len(v)), v, color=cols, height=0.66, zorder=3)
    for k, b in enumerate(bars):
        ax.text(v[k] + 0.025, b.get_y() + b.get_height() / 2, "%.3f" % v[k],
                va="center", fontsize=7.8, color=INK2)
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(ylab3 if ax is axes[0] else [""] * len(v), fontsize=8)
    ax.set_xlim(0, 1.22)
    ax.set_xlabel("标准化值 Z", fontsize=9, color=MUTED)
    ax.set_title(title, fontsize=10, color=INK, pad=8)
    style_ax(ax)

axes[0].set_ylabel("推广单元 ID", fontsize=9.5, color=MUTED)

# 指出 077181 三项标准化值均为 1.000，恰为正理想解
trow = ord3.index[ord3["推广单元ID"] == TARGET][0]
tz = ord3.loc[trow, ["Z_CTR", "Z_跳出率", "Z_平均访问时长"]].values
axes[0].annotate("%d：三指标 Z 均为 %.3f\n恰为正理想解（C = %.4f）"
                 % (TARGET, tz.min(), ord3.loc[trow, "TOPSIS得分C"]),
                 xy=(1.0, trow), xytext=(-8, -46), textcoords="offset points",
                 fontsize=8.6, color=HOT, fontweight="bold", ha="right",
                 arrowprops=dict(arrowstyle="-", color=HOT, linewidth=0.9))
axes[0].legend(handles=[Patch(facecolor=HOT, label="特殊推广单元 077181"),
                        Patch(facecolor=S1, label="其他推广单元")],
               frameon=False, fontsize=8, labelcolor=INK2, loc="lower right")

fig.suptitle("特殊推广单元077181与其他推广单元指标表现对比",
             fontsize=12, color=INK, y=1.02)
fig.tight_layout(w_pad=1.2)
savefig(fig, "fig3_unit_077181_profile")

# ============================================================================
# 4. 输出配套数据表
# ============================================================================
tbl = pd.DataFrame({
    "推广单元ID": res["推广单元ID"].astype(int).values,
    "CTR": res["CTR"].values,
    "CTR排名": res["CTR"].rank(ascending=False, method="min").astype(int).values,
    "跳出率": res["跳出率"].values,
    "跳出率排名": res["跳出率"].rank(ascending=True, method="min").astype(int).values,
    "平均访问时长(秒)": res["平均访问时长秒"].values,
    "平均访问时长排名": res["平均访问时长秒"].rank(
        ascending=False, method="min").astype(int).values,
    "TOPSIS得分C": res["TOPSIS得分C"].values,
    "TOPSIS排名": res["排名"].values,
})

csv = os.path.join(OUT_DAT, "图3_数据表.csv")
tbl.to_csv(csv, index=False, encoding="utf-8-sig", float_format="%.6f")
print("已保存: 图3_数据表.csv")
print(tbl.to_string(index=False))
print("完成。输出目录: %s" % (OUT_FIG + ' / ' + OUT_DAT))
