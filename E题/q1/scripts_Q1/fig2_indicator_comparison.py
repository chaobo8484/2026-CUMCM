# -*- coding: utf-8 -*-
"""
fig2_indicator_comparison.png —— 三个评价指标的标准化结果对比（热力图）

对应论文图：各推广单元广告创意评价指标标准化结果
输出：figures/fig2_indicator_comparison.png

要点：
  CTR（正向）、跳出率（负向）、平均访问时长（正向）三者量纲不同，
  必须先【同向化 + Min-Max 标准化】到 [0,1] 同一尺度，再放到同一张图上比较。
  本图直接画标准化后的 Z 值，不使用原始量纲数据。

本脚本自包含，不依赖其他脚本，直接 python fig2_indicator_comparison.py 即可运行。
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
S2 = "#eb6834"
DPI = 300
TARGET = 8878077181          # 特殊推广单元 077181，图中高亮


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

# ============================================================================
# 2. 同向化 + Min-Max 标准化（本图的主角）
# ============================================================================
EVAL = [("CTR", "正向"), ("跳出率", "负向"), ("平均访问时长秒", "正向")]

X = ann[[k for k, _ in EVAL]].astype(float).values

X_dir = X.copy()
for j, (_, d) in enumerate(EVAL):
    if d == "负向":
        X_dir[:, j] = X[:, j].max() - X[:, j]        # 跳出率翻转：越低越好

Xmin, Xmax = X_dir.min(axis=0), X_dir.max(axis=0)
rng = np.where((Xmax - Xmin) == 0, 1.0, Xmax - Xmin)
Z = (X_dir - Xmin) / rng                             # 统一到 [0,1]

# 为方便阅读，按 TOPSIS 综合得分降序排列（复用同一套标准化与权重）
P = Z + 1e-6
P = P / P.sum(axis=0, keepdims=True)
E = -(1.0 / np.log(len(Z))) * (P * np.log(P)).sum(axis=0)
W = (1.0 - E) / (1.0 - E).sum()
V = Z * W
C = np.sqrt(((V - V.min(0)) ** 2).sum(1)) / (
    np.sqrt(((V - V.max(0)) ** 2).sum(1)) + np.sqrt(((V - V.min(0)) ** 2).sum(1)))

order = np.argsort(-C)                                # 按 C 降序
Zplot = Z[order]
ids = ann.index[order]

# ============================================================================
# 3. 绘图：热力图
# ============================================================================
fig, ax = plt.subplots(figsize=(5.6, 6.6))
fig.patch.set_facecolor(SURFACE)

im = ax.imshow(Zplot, cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")

ax.set_xticks(range(3))
ax.set_xticklabels(["CTR\n(正向)", "跳出率\n(负向)", "平均访问时长\n(正向)"], fontsize=9.5)
ax.set_yticks(range(len(ids)))
ax.set_yticklabels([str(int(u)) for u in ids], fontsize=8.5)

# 格内标注标准化值，深色底用白字
for i in range(Zplot.shape[0]):
    for j in range(Zplot.shape[1]):
        v = Zplot[i, j]
        ax.text(j, i, "%.3f" % v, ha="center", va="center", fontsize=8,
                color="#ffffff" if v > 0.55 else INK)

# 高亮特殊推广单元所在行
ti = list(ids).index(TARGET) if TARGET in list(ids) else -1
if ti >= 0:
    ax.add_patch(plt.Rectangle((-0.5, ti - 0.5), 3, 1, fill=False,
                               edgecolor=S2, linewidth=2.0, zorder=5))

ax.set_title("各推广单元广告创意评价指标标准化结果", fontsize=11.5, color=INK, pad=12)
ax.set_xlabel("评价指标（已同向化 + Min-Max 标准化，0～1）", fontsize=9.5, color=MUTED)
ax.tick_params(colors=INK2, length=0)
for s in ax.spines.values():
    s.set_visible(False)

cb = fig.colorbar(im, ax=ax, fraction=0.036, pad=0.04)
cb.set_label("标准化值 Z（越接近 1 越优）", fontsize=9, color=INK2)
cb.outline.set_visible(False)
cb.ax.tick_params(colors=INK2, labelsize=8.5)

savefig(fig, "fig2_indicator_comparison")

# 导出底层数据
tab = pd.DataFrame({"推广单元ID": [int(u) for u in ids],
                    "Z_CTR(正向)": Zplot[:, 0],
                    "Z_跳出率(负向同向化)": Zplot[:, 1],
                    "Z_平均访问时长(正向)": Zplot[:, 2],
                    "TOPSIS得分C": C[order]})
tab.to_csv(os.path.join(OUT_DAT, "图2_标准化指标数据.csv"),
           index=False, encoding="utf-8-sig", float_format="%.6f")
print("已保存: 图2_标准化指标数据.csv")
print("完成。输出目录: %s" % (OUT_FIG + ' / ' + OUT_DAT))
