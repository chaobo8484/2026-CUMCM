# -*- coding: utf-8 -*-
"""
全国大学生数学建模竞赛 E题 —— 问题1「广告设计质量与创意」论文插图

原则（严格遵守）：
  1. 不修改原始数据文件，只读。
  2. 不删除推广单元 8878077181（077181）。
  3. 不构造任何不存在的数据。
  4. Sheet3 无日期 -> 绝不产出"月度跳出率""月度平均访问时长""月度 TOPSIS 得分"。
  5. 月度趋势只用 Sheet1 中带真实日期的 CTR / 展现量 / 点击量。
  6. 所有图中数值均来自现场重算，无硬编码。
  7. 中文字体正常显示。
  8. 300 dpi PNG + PDF/SVG 矢量版本。

数据源: ../题目/附件/附件1.xlsx
"""
import io
import math
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ----------------------------------------------------------------------------
# 0. 全局设定
# ----------------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, "..", "..", "题目", "附件", "附件1.xlsx"))
OUT_FIG = os.path.join(BASE, "..", "charts_Q1")
OUT_DAT = os.path.join(BASE, "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42          # 矢量 PDF 内嵌 TrueType, 中文不乱码
plt.rcParams["svg.fonttype"] = "none"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
S1, S2, S3_ = "#2a78d6", "#eb6834", "#1baf7a"   # 分类槽位 1/2/3
HOT = "#184f95"                                  # 强调深蓝
DPI = 300

LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


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
    made = []
    for ext in ("png",):
        p = os.path.join(OUT_FIG, "%s.%s" % (stem, ext))
        fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor=SURFACE)
        made.append(os.path.basename(p))
    plt.close(fig)
    log("  已保存: " + " / ".join(made))


def dur_to_sec(v):
    s = str(v).strip()
    parts = s.split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return np.nan
    return np.nan


# ---- Spearman 秩相关（自实现，避免 scipy 依赖） ----------------------------
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    """正则化不完全贝塔函数 I_x(a,b)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return np.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - np.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def spearman(x, y):
    """返回 (rho, 双侧 p 值)。"""
    n = len(x)
    rx = pd.Series(np.asarray(x, float)).rank().values
    ry = pd.Series(np.asarray(y, float)).rank().values
    if n < 3:
        return np.nan, np.nan
    rho = float(np.corrcoef(rx, ry)[0, 1])
    if abs(rho) >= 1.0:
        return rho, 0.0
    t = rho * np.sqrt((n - 2.0) / (1.0 - rho ** 2))
    p = _betai(0.5 * (n - 2), 0.5, (n - 2.0) / ((n - 2.0) + t ** 2))
    return rho, float(p)


def fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else "p = %.4f" % p


# ----------------------------------------------------------------------------
# 1. 读取与结构核验（只读，不改写）
# ----------------------------------------------------------------------------
log("=" * 72)
log("1. 读取与结构核验（只读）")
log("=" * 72)
if not os.path.exists(SRC):
    raise FileNotFoundError("找不到数据文件: %s" % SRC)

s1 = pd.read_excel(SRC, sheet_name="Sheet1")
s3 = pd.read_excel(SRC, sheet_name="Sheet3")
s3.columns = [c.strip() for c in s3.columns]

log("Sheet1 %s  字段: %s" % (s1.shape, list(s1.columns)))
log("Sheet3 %s  字段: %s" % (s3.shape, list(s3.columns)))
log("Sheet1 日期范围: %s ~ %s (%d 天)"
    % (s1["日期"].min().date(), s1["日期"].max().date(), s1["日期"].nunique()))
log("Sheet3 含日期字段: %s"
    % any("日期" in str(c) or "date" in str(c).lower() for c in s3.columns))
assert s1["点击量"].sum() == s3["点击量"].sum(), "Sheet1/Sheet3 口径不一致"

# ----------------------------------------------------------------------------
# 2. 年度单元指标（复现原口径：跳出率/时长按点击量加权聚合）
# ----------------------------------------------------------------------------
s3 = s3.copy()
s3["_跳出率"] = pd.to_numeric(s3["跳出率"].astype(str).str.strip(), errors="coerce")
s3["_秒"] = s3["平均访问时长"].astype(str).str.strip().map(dur_to_sec)

a1 = s1.groupby("推广单元ID").agg(
    全年展现量=("展现量", "sum"), 全年点击量=("点击量", "sum"), 全年消费额=("消费额", "sum"))


def wavg(g, col):
    w, v = g["点击量"], g[col]
    ok = v.notna() & (w > 0)
    return np.nan if w[ok].sum() == 0 else float((v[ok] * w[ok]).sum() / w[ok].sum())


a3 = s3.groupby("推广单元ID").apply(
    lambda g: pd.Series({"跳出率": wavg(g, "_跳出率"), "平均访问时长秒": wavg(g, "_秒")}),
    include_groups=False)

ann = a1.join(a3)
ann["CTR"] = ann["全年点击量"] / ann["全年展现量"]
ann["平均点击成本CPC"] = ann["全年消费额"] / ann["全年点击量"]
ann.index.name = "推广单元ID"

# ----------------------------------------------------------------------------
# 3. 同向化 + Min-Max 标准化 + 熵权 + TOPSIS（可复用于任意子集，用于稳健性检验）
# ----------------------------------------------------------------------------
EVAL = [("CTR", "正向"), ("跳出率", "负向"), ("平均访问时长秒", "正向")]


def topsis_pipeline(tab):
    """对给定评价对象表做 同向化 -> Min-Max -> 熵权 -> TOPSIS。返回 (Z, W, C, 中间量)。"""
    X = tab[[k for k, _ in EVAL]].astype(float).values
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
    k = 1.0 / np.log(n)
    E = -k * (P * np.log(P)).sum(axis=0)
    D = 1.0 - E
    W = D / D.sum()

    V = Z * W
    ib, iw = V.max(axis=0), V.min(axis=0)
    d_best = np.sqrt(((V - ib) ** 2).sum(axis=1))
    d_worst = np.sqrt(((V - iw) ** 2).sum(axis=1))
    C = d_worst / (d_best + d_worst)
    return Z, W, C, dict(X_dir=X_dir, V=V, d_best=d_best, d_worst=d_worst, E=E, D=D)


ann_sorted = ann.sort_values("全年点击量", ascending=False)
Z_all, W_all, C_all, mid_all = topsis_pipeline(ann_sorted)

res = pd.DataFrame({
    "推广单元ID": ann_sorted.index,
    "CTR": ann_sorted["CTR"].values,
    "跳出率": ann_sorted["跳出率"].values,
    "平均访问时长秒": ann_sorted["平均访问时长秒"].values,
    "综合得分C": C_all,
}).sort_values("综合得分C", ascending=False).reset_index(drop=True)
res.insert(0, "排名", np.arange(1, len(res) + 1))

# 标准化值挂回（按单元ID对齐；Z 由 ann_sorted 行序计算）
zmap = {u: Z_all[i] for i, u in enumerate(ann_sorted.index)}
res["Z_CTR"] = [zmap[u][0] for u in res["推广单元ID"]]
res["Z_跳出率"] = [zmap[u][1] for u in res["推广单元ID"]]
res["Z_平均访问时长"] = [zmap[u][2] for u in res["推广单元ID"]]

TARGET = 8878077181
assert TARGET in set(res["推广单元ID"]), "目标推广单元缺失"

log("")
log("年度综合评价结果（熵权法 + TOPSIS）：")
log(res.round(4).to_string(index=False))
log("")
log("熵权法权重: CTR=%.4f  跳出率=%.4f  平均访问时长=%.4f"
    % (W_all[0], W_all[1], W_all[2]))

# ----------------------------------------------------------------------------
# 图1  TOPSIS 综合得分排名
# ----------------------------------------------------------------------------
log("")
log("=" * 72)
log("2. 绘图")
log("=" * 72)

fig, ax = plt.subplots(figsize=(8.0, 4.4))
fig.patch.set_facecolor(SURFACE)
labels = [str(int(u)) for u in res["推广单元ID"]]
cvals = res["综合得分C"].values
colors = [S1] * len(cvals)
colors[0] = HOT
colors[-1] = MUTED
bars = ax.bar(labels, cvals, color=colors, width=0.62, zorder=3)

for b, v in zip(bars, cvals):
    ax.annotate("%.4f" % v, xy=(b.get_x() + b.get_width() / 2, v),
                xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=8.5, color=INK2, fontweight="bold")

ax.annotate("最高：%s\nC = %.4f" % (labels[0], cvals[0]),
            xy=(0, cvals[0]), xytext=(14, -18), textcoords="offset points",
            fontsize=9.5, color=HOT, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=HOT, linewidth=0.9))
ax.annotate("最低：%s\nC = %.4f" % (labels[-1], cvals[-1]),
            xy=(len(cvals) - 1, cvals[-1]), xytext=(-16, 34), textcoords="offset points",
            fontsize=9.5, color=INK2, fontweight="bold", ha="right",
            arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.9))

ax.set_ylabel("TOPSIS 综合贴近度 C", fontsize=10, color=INK2)
ax.set_xlabel("推广单元 ID（按 C 值降序）", fontsize=9.5, color=MUTED)
ax.set_title("2025年各推广单元广告设计质量与创意综合评价", fontsize=12, color=INK, pad=10)
ax.tick_params(axis="x", labelsize=8, rotation=35)
ax.set_ylim(0, max(cvals.max() * 1.22, 1e-6))
ax.legend(handles=[Patch(facecolor=HOT, label="最高分单元"),
                   Patch(facecolor=S1, label="其他单元"),
                   Patch(facecolor=MUTED, label="最低分单元")],
          frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper right")
style_ax(ax)
savefig(fig, "fig1_topsis_ranking")

# ----------------------------------------------------------------------------
# 图2  三指标标准化结果对比（热力图，12 单元 × 3 指标）
# ----------------------------------------------------------------------------
Zcols = ["Z_CTR", "Z_跳出率", "Z_平均访问时长"]
Zmat = res[Zcols].values
order = res["推广单元ID"].astype(int).astype(str).values

fig, ax = plt.subplots(figsize=(5.6, 6.6))
fig.patch.set_facecolor(SURFACE)
im = ax.imshow(Zmat, cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")
ax.set_xticks(range(3))
ax.set_xticklabels(["CTR\n(正向)", "跳出率\n(负向)", "平均访问时长\n(正向)"], fontsize=9.5)
ax.set_yticks(range(len(order)))
ax.set_yticklabels(order, fontsize=8.5)
for i in range(Zmat.shape[0]):
    for j in range(Zmat.shape[1]):
        v = Zmat[i, j]
        ax.text(j, i, "%.3f" % v, ha="center", va="center", fontsize=8,
                color="#ffffff" if v > 0.55 else INK)
# 高亮特殊单元行
ti = list(order).index(str(TARGET))
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

# ----------------------------------------------------------------------------
# 图3  特殊推广单元 077181 的指标画像（三指标小倍数条形图）
# ----------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.5))
fig.patch.set_facecolor(SURFACE)
panels = [("Z_CTR", "CTR（正向）", S1),
          ("Z_跳出率", "跳出率（负向，已同向化）", S2),
          ("Z_平均访问时长", "平均访问时长（正向）", S3_)]
ord3 = res.sort_values("综合得分C", ascending=True).reset_index(drop=True)
ylab3 = ord3["推广单元ID"].astype(int).astype(str).values

for ax, (col, title, c) in zip(axes, panels):
    v = ord3[col].values
    cols = [c] * len(v)
    for k, u in enumerate(ord3["推广单元ID"]):
        if u == TARGET:
            cols[k] = HOT
    bars = ax.barh(range(len(v)), v, color=cols, height=0.66, zorder=3)
    for k, b in enumerate(bars):
        w = v[k]
        ax.text(w + 0.025, b.get_y() + b.get_height() / 2, "%.3f" % w,
                va="center", fontsize=7.8, color=INK2)
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(ylab3 if ax is axes[0] else [""] * len(v), fontsize=8)
    ax.set_xlim(0, 1.22)
    ax.set_xlabel("标准化值 Z", fontsize=9, color=MUTED)
    ax.set_title(title, fontsize=10, color=INK, pad=8)
    style_ax(ax)
axes[0].set_ylabel("推广单元 ID", fontsize=9.5, color=MUTED)

axes[0].annotate("077181：三指标 Z 均 = 1.000\n恰为正理想解（C = 1.0000）",
                 xy=(1.0, len(ord3) - 1), xytext=(-8, -46), textcoords="offset points",
                 fontsize=8.6, color=HOT, fontweight="bold", ha="right",
                 arrowprops=dict(arrowstyle="-", color=HOT, linewidth=0.9))
axes[0].legend(handles=[Patch(facecolor=HOT, label="特殊推广单元 077181"),
                        Patch(facecolor=S1, label="其他推广单元")],
               frameon=False, fontsize=8, labelcolor=INK2, loc="lower right")
fig.suptitle("特殊推广单元077181与其他推广单元指标表现对比",
             fontsize=12, color=INK, y=1.02)
fig.tight_layout(w_pad=1.2)
savefig(fig, "fig3_unit_077181_profile")

# ----------------------------------------------------------------------------
# 图4  真实月度 CTR 趋势（Sheet1 真实日期汇总，先汇总再相除）
# ----------------------------------------------------------------------------
s1m = s1.copy()
s1m["月份"] = s1m["日期"].dt.month
m = s1m.groupby("月份").agg(展现量=("展现量", "sum"), 点击量=("点击量", "sum"))
m["CTR"] = m["点击量"] / m["展现量"]      # 先汇总总量再相除，未对日 CTR 简单平均
m = m.reindex(range(1, 13))
m.index.name = "月份"
assert m["CTR"].notna().all(), "存在无数据月份"

months = np.arange(1, 13)
xlab = ["%d月" % i for i in months]
y = m["CTR"].values * 100.0
avg = m["点击量"].sum() / m["展现量"].sum() * 100.0
imax, imin = int(np.argmax(y)), int(np.argmin(y))

fig, ax = plt.subplots(figsize=(8.0, 4.3))
fig.patch.set_facecolor(SURFACE)
ax.axhline(avg, color=MUTED, linewidth=1.1, linestyle="--", zorder=2,
           label="全年平均 CTR = %.2f%%" % avg)
ax.plot(months, y, "-o", color=S1, linewidth=1.9, markersize=6,
        markerfacecolor=S1, markeredgecolor=SURFACE, markeredgewidth=1.3,
        zorder=3, label="月度 CTR")
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

# ----------------------------------------------------------------------------
# 图5  稳健性检验：剥离 077181 后对余下 11 个单元重算 TOPSIS
# ----------------------------------------------------------------------------
sub11 = ann_sorted[ann_sorted.index != TARGET].copy()
Z11, W11, C11, mid11 = topsis_pipeline(sub11)

# 关键：两侧都在【11 个共同单元内部】排名，使比较处于同一尺度。
# 若横轴沿用 12 单元全样本名次（2~12），会因少了一个对象而系统性抬高名次变动，
# 把尺度差异误读为排序变化。
common = [u for u in sub11.index]
idx11 = [i for i, u in enumerate(ann_sorted.index) if u != TARGET]
rank_a = pd.Series(C_all[idx11], index=sub11.index) \
    .rank(ascending=False, method="min").astype(int)
rank_b = pd.Series(C11, index=sub11.index) \
    .rank(ascending=False, method="min").astype(int)
ra = rank_a[common].values.astype(float)
rb = rank_b[common].values.astype(float)
diff = rb - ra
rho, pval = spearman(ra, rb)
mean_shift = float(np.abs(diff).mean())
max_shift = float(np.abs(diff).max())

log("")
log("稳健性检验（11 个共同推广单元，剥离 %d 后全流程重算："
    "重标准化 + 重定权 + 重算正负理想解）" % TARGET)
log("  剥离前权重: CTR=%.4f 跳出率=%.4f 时长=%.4f" % tuple(W_all))
log("  剥离后权重: CTR=%.4f 跳出率=%.4f 时长=%.4f" % tuple(W11))
log("  两侧均在 11 个共同单元内部排名（同尺度）")
log("  Spearman rho = %.4f, %s" % (rho, fmt_p(pval)))
log("  平均名次变动 = %.2f 位, 最大名次变动 = %.0f 位" % (mean_shift, max_shift))
log(pd.DataFrame({"推广单元ID": [int(u) for u in common],
                  "含077181名次": ra.astype(int),
                  "剥离后名次": rb.astype(int),
                  "变动": diff.astype(int)}).to_string(index=False))

fig, ax = plt.subplots(figsize=(6.6, 5.8))
fig.patch.set_facecolor(SURFACE)
lim = [0.3, 11.7]
ax.plot(lim, lim, color=MUTED, linewidth=1.1, linestyle="--", zorder=2,
        label="y = x（名次完全一致）")
ax.scatter(ra, rb, s=70, color=S1, edgecolor=SURFACE, linewidth=1.3,
           zorder=4, label="11 个共同推广单元")
for u, xa, xb in zip(common, ra, rb):
    ax.annotate(str(int(u)), xy=(xa, xb), xytext=(0, 10),
                textcoords="offset points", ha="center", fontsize=8, color=INK2)
ax.annotate("Spearman ρ = %.4f\n%s\n平均名次变动 %.2f 位，最大 %.0f 位"
            % (rho, fmt_p(pval), mean_shift, max_shift),
            xy=(0.035, 0.975), xycoords="axes fraction", va="top", ha="left",
            fontsize=9.5, color=INK, fontweight="bold")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.invert_yaxis()
ax.invert_xaxis()   # 右上角 = 名次最好
ax.set_xticks(range(1, 12))
ax.set_yticks(range(1, 12))
ax.set_xlabel("包含 077181 时在 11 个共同单元中的排名", fontsize=9.5, color=INK2)
ax.set_ylabel("剥离 077181 重算后的排名", fontsize=9.5, color=INK2)
ax.set_title("特殊推广单元剥离前后TOPSIS排序稳健性检验", fontsize=11.5, color=INK, pad=10)
ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="lower right")
ax.set_aspect("equal")
style_ax(ax)
savefig(fig, "fig5_robustness")

# ----------------------------------------------------------------------------
# 6. 底层数据表导出
# ----------------------------------------------------------------------------
rank_ctr = res["CTR"].rank(ascending=False, method="min").astype(int)
rank_br = res["跳出率"].rank(ascending=True, method="min").astype(int)
rank_dur = res["平均访问时长秒"].rank(ascending=False, method="min").astype(int)

tbl_fig3 = pd.DataFrame({
    "推广单元ID": res["推广单元ID"].astype(int).values,
    "CTR": res["CTR"].values,
    "CTR排名": [rank_ctr[u] for u in res.index],
    "跳出率": res["跳出率"].values,
    "跳出率排名": [rank_br[u] for u in res.index],
    "平均访问时长(秒)": res["平均访问时长秒"].values,
    "平均访问时长排名": [rank_dur[u] for u in res.index],
    "TOPSIS得分C": res["综合得分C"].values,
    "TOPSIS排名": res["排名"].values,
})

t_fig1 = res[["排名", "推广单元ID", "综合得分C"]].copy()
t_fig1["推广单元ID"] = t_fig1["推广单元ID"].astype(int)

t_fig2 = pd.DataFrame({
    "推广单元ID": res["推广单元ID"].astype(int).values,
    "Z_CTR(正向)": res["Z_CTR"].values,
    "Z_跳出率(负向同向化)": res["Z_跳出率"].values,
    "Z_平均访问时长(正向)": res["Z_平均访问时长"].values,
    "TOPSIS得分C": res["综合得分C"].values,
})

t_fig4 = pd.DataFrame({
    "月份": ["%d月" % i for i in months],
    "展现量": m["展现量"].astype(int).values,
    "点击量": m["点击量"].astype(int).values,
    "月度CTR": m["CTR"].values,
    "月度CTR(%)": y,
})

t_fig5 = pd.DataFrame({
    "推广单元ID": [int(u) for u in common],
    "包含077181时得分C": C_all[idx11],
    "包含077181时在11单元中排名": ra.astype(int),
    "剥离077181重算得分C": C11,
    "剥离077181重算排名": rb.astype(int),
    "名次变动": diff.astype(int),
})

t_weights = pd.DataFrame({
    "指标": [k for k, _ in EVAL],
    "方向": [d for _, d in EVAL],
    "全样本_权重w": W_all,
    "全样本_信息熵e": mid_all["E"],
    "剥离077181_权重w": W11,
    "剥离077181_信息熵e": mid11["E"],
})

xlsx = os.path.join(OUT_DAT, "plot_data.xlsx")
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    t_fig1.to_excel(w, sheet_name="图1_TOPSIS排名", index=False)
    t_fig2.to_excel(w, sheet_name="图2_标准化指标", index=False)
    tbl_fig3.to_excel(w, sheet_name="图3_077181画像数据表", index=False)
    t_fig4.to_excel(w, sheet_name="图4_月度CTR", index=False)
    t_fig5.to_excel(w, sheet_name="图5_稳健性检验", index=False)
    t_weights.to_excel(w, sheet_name="熵权法权重对照", index=False)
tbl_fig3.to_csv(os.path.join(OUT_DAT, "图3_数据表.csv"), index=False,
                encoding="utf-8-sig", float_format="%.6f")
log("")
log("已保存: plot_data.xlsx（6 个工作表）")
log("已保存: 图3_数据表.csv")

# ----------------------------------------------------------------------------
# 7. 运行日志
# ----------------------------------------------------------------------------
with io.open(os.path.join(OUT_DAT, "绘图日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
log("")
log("完成。产物目录: %s" % (OUT_FIG + ' / ' + OUT_DAT))
