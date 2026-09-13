# -*- coding: utf-8 -*-
"""
广告设计质量与创意的月度变化趋势 + 全年综合评价
数据源: ../题目/附件/附件1.xlsx

口径声明（严格遵守）:
  * 月度部分: 只使用 Sheet1 中【带真实日期、可按月真实聚合】的指标。
    Sheet1 无 跳出率 / 平均访问时长 / 浏览量, 故月度部分【不产出】这三者,
    也【不构造月度综合得分】(不做月度 TOPSIS)。
  * 全年部分: 跳出率、平均访问时长 只存在于 Sheet3(无日期, 全年关键词级汇总),
    故【仅用于全年综合评价】, 与 Sheet1 的年度 CTR 一同参与 熵权法 + TOPSIS。
  * 评价对象: 推广单元(12 个)。全表统一一套权重, 不做逐对象重新定权。
"""
import os
import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# 0. 全局设定
# ----------------------------------------------------------------------------
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "题目", "附件", "附件1.xlsx"))
OUT_FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "charts_Q1")
OUT_DAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

# 中文
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 配色（dataviz 规范: 光面 #fcfcfb, 分类槽位 1/2/3, 已通过 CVD 校验）
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
S1, S2, S3_ = "#2a78d6", "#eb6834", "#1baf7a"

DPI = 300
LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


def style_ax(ax):
    """简洁学术风格: 细实线网格, 退化坐标轴。"""
    ax.set_facecolor(SURFACE)
    ax.grid(True, which="major", color=GRID, linewidth=0.6, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=INK2, labelsize=9, width=0.8, length=3)


def savefig(fig, name):
    p = os.path.join(OUT_FIG, name)
    fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    log("  已保存: %s" % name)


def dur_to_sec(v):
    """'HH:MM:SS'(可能带前导空格) -> 秒; 缺失/异常 -> NaN。"""
    s = str(v).strip()
    parts = s.split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return np.nan
    return np.nan


# ----------------------------------------------------------------------------
# 1. 读取与结构核验
# ----------------------------------------------------------------------------
log("=" * 72)
log("1. 读取与结构核验")
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

# 核验: Sheet3 无日期, 且与 Sheet1 同属一批投放(全年同口径)
log("Sheet3 是否含日期字段: %s  -> 故跳出率/时长不可按月拆分"
    % any("日期" in str(c) or "date" in str(c).lower() for c in s3.columns))
log("同一性核验  点击量合计: Sheet1=%d  Sheet3=%d"
    % (s1["点击量"].sum(), s3["点击量"].sum()))
log("            消费额合计: Sheet1=%.2f  Sheet3=%.2f"
    % (s1["消费额"].sum(), s3["消费额"].sum()))
log("            方案ID集合一致: %s   推广单元ID集合一致: %s"
    % (sorted(s1["方案ID"].unique()) == sorted(s3["方案ID"].unique()),
       sorted(s1["推广单元ID"].unique()) == sorted(s3["推广单元ID"].unique())))
assert s1["点击量"].sum() == s3["点击量"].sum(), "Sheet1 与 Sheet3 不同口径, 不可联结"

# 字段可用性
br_raw = s3["跳出率"].astype(str).str.strip()
du_raw = s3["平均访问时长"].astype(str).str.strip()
log("跳出率   可用 %d / %d (缺失全部为 '/' 且对应 点击量==0)"
    % (pd.to_numeric(br_raw, errors="coerce").notna().sum(), len(s3)))
log("平均访问时长 可用 %d / %d ('0' 共 %d 行, 占权重 %.4f%%, 按字面作 0 秒)"
    % (du_raw.str.match(r"^\d{1,2}:\d{2}:\d{2}$").sum(), len(s3),
       (du_raw == "0").sum(),
       100.0 * s3.loc[du_raw == "0", "点击量"].sum() / s3["点击量"].sum()))

# ----------------------------------------------------------------------------
# 2. 月度汇总（仅 Sheet1 真实可按月计算的指标）
# ----------------------------------------------------------------------------
log("")
log("=" * 72)
log("2. 月度汇总（Sheet1，2025 全年，一行一个月）")
log("=" * 72)
s1 = s1.copy()
s1["月份"] = s1["日期"].dt.month

m = s1.groupby("月份").agg(
    展现量=("展现量", "sum"),
    点击量=("点击量", "sum"),
    消费额=("消费额", "sum"),
    上方位展现量=("上方位展现量", "sum"),
    上方位点击量=("上方位点击量", "sum"),
    上方首位展现量=("上方首位展现量", "sum"),
)
# 核心: 先汇总再相除, 绝不对日 CTR 求简单平均
m["CTR"] = m["点击量"] / m["展现量"]
m["平均点击成本CPC"] = m["消费额"] / m["点击量"]
# 补充: 同为真实可按月计算, 业务含义见 说明.md（不得称为跳出率/访问时长）
m["上方位CTR"] = m["上方位点击量"] / m["上方位展现量"]
m["首位展现率"] = m["上方首位展现量"] / m["上方位展现量"]
m = m.reindex(range(1, 13))
m.index.name = "月份"

core = m[["展现量", "点击量", "消费额", "CTR", "平均点击成本CPC"]].copy()
sup = m[["上方位展现量", "上方位点击量", "上方位CTR", "上方首位展现量", "首位展现率"]].copy()
core.to_csv(os.path.join(OUT_DAT, "表1_月度汇总.csv"), encoding="utf-8-sig", float_format="%.6f")
sup.to_csv(os.path.join(OUT_DAT, "表2_月度补充指标.csv"), encoding="utf-8-sig", float_format="%.6f")
log(core.assign(CTR=lambda d: d["CTR"].map("{:.2%}".format),
                CPC=lambda d: d["平均点击成本CPC"].map("{:.4f}".format)).to_string())
log("")
log("月度未产出: 跳出率 / 平均访问时长 —— Sheet1 无此二字段, 不可按月计算。")

# ----------------------------------------------------------------------------
# 3. 结构漂移诊断（可比口径）
# ----------------------------------------------------------------------------
log("")
log("=" * 72)
log("3. 投放结构漂移诊断")
log("=" * 72)
act = s1.pivot_table(index="推广单元ID", columns="月份", values="展现量", aggfunc="sum").fillna(0)
allm = act.index[(act > 0).all(axis=1)].tolist()
log("全年 12 个月均有投放的推广单元(可比子集): %s" % allm)
log("其余 %d 个单元存在整月零投放 -> 月度总量受投放组合变化驱动"
    % (len(act) - len(allm)))

struct = pd.DataFrame({
    "活跃月份数": (act > 0).sum(axis=1),
    "全年展现量": act.sum(axis=1).astype(int),
    "是否可比子集": [(u in allm) for u in act.index],
}).sort_values("全年展现量", ascending=False)
struct.index.name = "推广单元ID"
struct.to_csv(os.path.join(OUT_DAT, "表3_结构诊断.csv"), encoding="utf-8-sig")
log(struct.to_string())

sub = s1[s1["推广单元ID"].isin(allm)]
m_sub = sub.groupby("月份").agg(点击量=("点击量", "sum"), 展现量=("展现量", "sum"))
m_sub["CTR"] = m_sub["点击量"] / m_sub["展现量"]
m_sub = m_sub.reindex(range(1, 13))["CTR"]
cmpdf = pd.DataFrame({"全量CTR": m["CTR"], "可比子集CTR": m_sub})
cmpdf["结构效应(全量-子集)"] = cmpdf["全量CTR"] - cmpdf["可比子集CTR"]
cmpdf.to_csv(os.path.join(OUT_DAT, "表4_可比口径CTR对比.csv"), encoding="utf-8-sig", float_format="%.6f")
log("")
log("可比口径 CTR 对比:")
log(cmpdf.map(lambda v: "%.2f%%" % (v * 100)).to_string())

# ----------------------------------------------------------------------------
# 4. 全年评价：Sheet1 年度 CTR + Sheet3 年度跳出率/平均访问时长
# ----------------------------------------------------------------------------
log("")
log("=" * 72)
log("4. 全年综合评价（熵权法 + TOPSIS，评价对象 = 12 个推广单元）")
log("=" * 72)
s3 = s3.copy()
s3["_跳出率"] = pd.to_numeric(br_raw, errors="coerce")
s3["_秒"] = du_raw.map(dur_to_sec)

a1 = s1.groupby("推广单元ID").agg(
    全年展现量=("展现量", "sum"), 全年点击量=("点击量", "sum"), 全年消费额=("消费额", "sum"))


def wavg(g, col):
    """按点击量加权（权重字段存在时优先加权，不做无脑均值）。
    跳出率/时长的缺失行恰为 点击量==0，权重自然为 0，无需额外剔除。"""
    w, v = g["点击量"], g[col]
    ok = v.notna() & (w > 0)
    return np.nan if w[ok].sum() == 0 else float((v[ok] * w[ok]).sum() / w[ok].sum())


a3 = s3.groupby("推广单元ID").apply(
    lambda g: pd.Series({"跳出率": wavg(g, "_跳出率"), "平均访问时长秒": wavg(g, "_秒")}),
    include_groups=False)

ann = a1.join(a3)
ann["CTR"] = ann["全年点击量"] / ann["全年展现量"]
ann["平均点击成本CPC"] = ann["全年消费额"] / ann["全年点击量"]
ann = ann[["全年展现量", "全年点击量", "全年消费额", "CTR", "平均点击成本CPC",
           "跳出率", "平均访问时长秒"]].sort_values("全年点击量", ascending=False)
ann.index.name = "推广单元ID"
ann.to_csv(os.path.join(OUT_DAT, "表5_年度单元汇总.csv"), encoding="utf-8-sig", float_format="%.6f")
log(ann.round(4).to_string())

# --- 同向化 + Min-Max 标准化 --------------------------------
EVAL = [("CTR", "正向"), ("跳出率", "负向"), ("平均访问时长秒", "正向")]
X = ann[[k for k, _ in EVAL]].astype(float).values
n, mm = X.shape

X_dir = X.copy()
for j, (_, d) in enumerate(EVAL):
    if d == "负向":
        X_dir[:, j] = X[:, j].max() - X[:, j]          # 负向 -> 正向
Xmin, Xmax = X_dir.min(axis=0), X_dir.max(axis=0)
rng = np.where((Xmax - Xmin) == 0, 1.0, Xmax - Xmin)
Z = (X_dir - Xmin) / rng                                # Min-Max -> [0,1]

# --- 熵权法（全表一套权重） ---------------------------------
P = Z + 1e-6
P = P / P.sum(axis=0, keepdims=True)
k = 1.0 / np.log(n)
E = -k * (P * np.log(P)).sum(axis=0)
D = 1.0 - E
W = D / D.sum()

wt = pd.DataFrame({"指标": [k for k, _ in EVAL],
                   "方向": [d for _, d in EVAL],
                   "信息熵e": E, "差异系数d": D, "权重w": W})
wt.to_csv(os.path.join(OUT_DAT, "表6_熵权法权重.csv"), encoding="utf-8-sig", float_format="%.6f")
log("")
log("熵权法权重:")
log(wt.to_string(index=False))

# --- TOPSIS（同一套权重、同一正负理想解） -------------------
V = Z * W
ideal_best, ideal_worst = V.max(axis=0), V.min(axis=0)
d_best = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
d_worst = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))
C = d_worst / (d_best + d_worst)

res = pd.DataFrame({
    "推广单元ID": ann.index,
    "CTR": ann["CTR"].values,
    "跳出率": ann["跳出率"].values,
    "平均访问时长秒": ann["平均访问时长秒"].values,
    "综合得分C": C,
}).sort_values("综合得分C", ascending=False).reset_index(drop=True)
res.insert(0, "排名", np.arange(1, len(res) + 1))
res.to_csv(os.path.join(OUT_DAT, "表7_年度TOPSIS得分.csv"), encoding="utf-8-sig", float_format="%.6f")
log("")
log("全年综合评价结果:")
log(res.round(4).to_string(index=False))

# ----------------------------------------------------------------------------
# 5. 绘图
# ----------------------------------------------------------------------------
log("")
log("=" * 72)
log("5. 绘图")
log("=" * 72)
months = np.arange(1, 13)
xlab = ["%d月" % i for i in months]

# --- 图1 月度 CTR 趋势（单序列, 无需图例, 标注极值月） ---
fig, ax = plt.subplots(figsize=(7.4, 4.0))
fig.patch.set_facecolor(SURFACE)
y = m["CTR"].values * 100
ax.plot(months, y, "-o", color=S1, linewidth=1.8, markersize=5.5,
        markerfacecolor=S1, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)
imax, imin = int(np.argmax(y)), int(np.argmin(y))
for i, tag, col in ((imax, "最高", "#006300"), (imin, "最低", "#d03b3b")):
    ax.annotate("%s %d月\n%.2f%%" % (tag, months[i], y[i]),
                xy=(months[i], y[i]), xytext=(0, 16 if tag == "最高" else -30),
                textcoords="offset points", ha="center", fontsize=9, color=col,
                fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=col, linewidth=0.9))
ax.set_xticks(months)
ax.set_xticklabels(xlab)
ax.set_ylabel("CTR（点击量 / 展现量，%）", fontsize=10, color=INK2)
ax.set_title("图1  月度 CTR 变化趋势（2025 年，先汇总总量再相除）",
             fontsize=11.5, color=INK, pad=10)
ax.set_ylim(0, max(y) * 1.25)
style_ax(ax)
savefig(fig, "图1_月度CTR趋势.png")

# --- 图2 月度规模指标（小倍数, 规避双轴） ---
fig, axes = plt.subplots(3, 1, figsize=(7.4, 7.2), sharex=True)
fig.patch.set_facecolor(SURFACE)
panels = [("展现量", "展现量", S1, 1e4, "万次"),
          ("点击量", "点击量", S2, 1e3, "千次"),
          ("消费额", "消费额", S3_, 1e4, "万元")]
for ax, (col, lab, c, scale, unit) in zip(axes, panels):
    v = m[col].values / scale
    ax.plot(months, v, "-o", color=c, linewidth=1.8, markersize=5,
            markerfacecolor=c, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)
    i = int(np.argmax(v))
    ax.annotate("峰值 %d月  %.1f%s" % (months[i], v[i], unit), xy=(months[i], v[i]),
                xytext=(0, 12), textcoords="offset points", ha="center",
                fontsize=9, color=INK2, fontweight="bold")
    ax.set_ylabel("%s（%s）" % (lab, unit), fontsize=10, color=INK2)
    ax.set_ylim(0, max(v) * 1.28)
    style_ax(ax)
axes[-1].set_xticks(months)
axes[-1].set_xticklabels(xlab)
axes[0].set_title("图2  月度规模指标变化（展现量 / 点击量 / 消费额）",
                  fontsize=11.5, color=INK, pad=10)
fig.tight_layout(h_pad=1.6)
savefig(fig, "图2_月度规模指标.png")

# --- 图3 结构漂移诊断：全量 vs 可比子集 ---
fig, ax = plt.subplots(figsize=(7.4, 4.2))
fig.patch.set_facecolor(SURFACE)
ya = m["CTR"].values * 100
yb = m_sub.values * 100
ax.plot(months, ya, "-o", color=S1, linewidth=1.8, markersize=5.5,
        markerfacecolor=S1, markeredgecolor=SURFACE, markeredgewidth=1.2,
        label="全量 12 个推广单元", zorder=3)
ax.plot(months, yb, "-s", color=S2, linewidth=1.8, markersize=5.5,
        markerfacecolor=S2, markeredgecolor=SURFACE, markeredgewidth=1.2,
        label="可比子集（全年 12 个月均有投放）", zorder=3)
ax.fill_between(months, yb, ya, color=S1, alpha=0.08, zorder=1)
for arr, lab, col in ((ya, "全量", S1), (yb, "子集", S2)):
    ax.annotate("%s %.2f%%" % (lab, arr[-1]), xy=(12, arr[-1]), xytext=(-10, 12),
                textcoords="offset points", ha="right", fontsize=9.5,
                color=col, fontweight="bold")
ax.set_xticks(months)
ax.set_xticklabels(xlab)
ax.set_ylabel("CTR（%）", fontsize=10, color=INK2)
ax.set_title("图3  投放结构漂移诊断：全量与可比子集 CTR 对照",
             fontsize=11.5, color=INK, pad=10)
ax.legend(frameon=False, fontsize=9.5, labelcolor=INK2, loc="upper right")
style_ax(ax)
savefig(fig, "图3_结构漂移诊断.png")

# --- 图4 全年综合得分（单序列 -> 统一一色, 标注首末） ---
fig, ax = plt.subplots(figsize=(8.2, 4.4))
fig.patch.set_facecolor(SURFACE)
labels = [str(u) for u in res["推广单元ID"]]
sc = res["综合得分C"].values
bars = ax.bar(labels, sc, color=S1, width=0.62, zorder=3)
bars[0].set_color("#184f95")
bars[-1].set_color(MUTED)
ax.annotate("%.4f" % sc[0], xy=(0, sc[0]), xytext=(0, 5), textcoords="offset points",
            ha="center", fontsize=9.5, color="#184f95", fontweight="bold")
ax.annotate("%.4f" % sc[-1], xy=(len(sc) - 1, sc[-1]), xytext=(0, 5),
            textcoords="offset points", ha="center", fontsize=9.5,
            color=INK2, fontweight="bold")
ax.set_ylabel("TOPSIS 综合得分 C", fontsize=10, color=INK2)
ax.set_xlabel("推广单元ID（颜色深浅仅示首末，非数值映射）", fontsize=9.5, color=MUTED)
ax.set_title("图4  全年广告设计质量综合评价得分（熵权法 + TOPSIS，12 个推广单元）",
             fontsize=11.5, color=INK, pad=10)
ax.tick_params(axis="x", labelsize=8, rotation=35)
ax.set_ylim(0, max(sc.max() * 1.18, 1e-6))
style_ax(ax)
savefig(fig, "图4_年度综合得分.png")

# ----------------------------------------------------------------------------
# 6. 说明文档
# ----------------------------------------------------------------------------
mrows = []
for i in months:
    mrows.append("| %d月 | %s | %s | %s | %.2f%% | %.4f |"
                 % (i, format(int(m.loc[i, "展现量"]), ","),
                    format(int(m.loc[i, "点击量"]), ","),
                    format(m.loc[i, "消费额"], ",.2f"),
                    m.loc[i, "CTR"] * 100, m.loc[i, "平均点击成本CPC"]))
srows = []
for i in months:
    srows.append("| %d月 | %.2f%% | %.4f 元 |" % (i, m.loc[i, "上方位CTR"] * 100,
                                               m.loc[i, "平均点击成本CPC"]))
rrows = []
for _, r in res.iterrows():
    rrows.append("| %d | %s | %.2f%% | %.4f | %.1f | %.4f |"
                 % (r["排名"], r["推广单元ID"], r["CTR"] * 100, r["跳出率"],
                    r["平均访问时长秒"], r["综合得分C"]))

doc = """# 广告设计质量与创意的月度变化趋势 —— 口径说明与结果

数据源: `../题目/附件/附件1.xlsx`
输出目录: `output1/`

## 一、字段核验（先查结构，未假设列名）

| Sheet | 规模 | 粒度 | 字段 |
|---|---|---|---|
| Sheet1 | 2627 × 10 | **日 × 推广单元**，2025-01-01 ~ 2025-12-31（365 天） | 日期、方案ID、推广单元ID、展现量、点击量、消费额、上方位展现量、上方首位展现量、上方位点击量、上方位消费额 |
| Sheet2 | 365 × 2 | 日 | 日期、新注册数 |
| Sheet3 | 2227 × 9 | **关键词（无日期）** | 序号、关键词、方案ID、推广单元ID、消费额、点击量、浏览量、跳出率、平均访问时长 |

**Sheet3 是全年快照，不是月度数据**——它与 Sheet1 同属一批投放：
点击量合计两者均为 **834,815**，消费额 1,425,949.79 vs 1,425,949.81（浮点差 0.02），
方案ID 与推广单元ID 集合完全一致。据此判定为同口径全年汇总，可联结。

## 二、关键口径约束（未做替代、未做伪造）

**Sheet1 不含"跳出率""平均访问时长""浏览量"。** 这两个指标只存在于 Sheet3，而 Sheet3 无日期字段，
**无法拆分为月度**。因此：

* 月度部分**只使用** Sheet1 中带真实日期、可按月真实聚合的指标；
* **不产出**任何名为"月度跳出率""月度平均访问时长"的序列；
* **不构造月度综合得分**（不做月度 TOPSIS）；
* 跳出率、平均访问时长**仅用于全年综合评价**。

另有两个 Sheet1 可按月计算的指标（`表2`），其业务含义为：

* **上方位CTR** = 上方位点击量 / 上方位展现量。上方位是搜索结果页的顶部广告位，
  只有质量度与出价综合占优的创意才被分配到该位置；它度量"进入优质展位后的点击效率"。
* **首位展现率** = 上方首位展现量 / 上方位展现量。度量创意在顶部展位中争夺第 1 位的能力。

二者均为**展位分配效率**指标，**不是跳出率、不是平均访问时长**，不得混称。

## 三、月度汇总（表1）

计算方式：每月先汇总总量，再相除。`CTR_month = Σ点击量 / Σ展现量`，**未对日 CTR 求简单平均**。

| 月份 | 展现量 | 点击量 | 消费额(元) | CTR | CPC(元) |
|---|---|---|---|---|---|
%s

补充指标（表2）：

| 月份 | 上方位CTR | CPC(元) |
|---|---|---|
%s

## 四、投放结构漂移（重要，影响月度趋势解读）

12 个推广单元中仅 **%s** 在全年 12 个月均有投放；
其余单元存在整月零投放（例如方案 63563817 的 5 个单元在 1–4 月与 6 月完全无投放，
多个单元自 2025-05-21 起才上线）。

结果是**指标方向相反**：全量 CTR 由 1 月的 %.2f%% 降至 %d 月的 %.2f%%，
而同期上方位 CTR 由 %.2f%% 升至 %.2f%%。
月度总量变动主要来自**投放组合的变化**，而非创意质量本身。
`图3` 给出全量与可比子集的 CTR 对照，两者之差即结构效应，详见 `表4`。

**结论**：任何基于月度总量构造的"综合排名"都会把结构效应误读为质量变化，故本文不构造月度综合得分。

## 五、全年综合评价（熵权法 + TOPSIS）

* **评价对象**：12 个推广单元。
* **指标**：CTR（正向，Sheet1 年度）、跳出率（负向，Sheet3）、平均访问时长（正向，Sheet3）。
* **权重字段处理**：跳出率与平均访问时长按**点击量加权**聚合到单元级
  （缺失值恰为 点击量==0 的行，权重自然为 0）。未使用简单算术平均。
* **可比性**：12 个单元共用**同一套**权重与同一组正负理想解，未对任何对象单独重新定权。
* 数据说明：平均访问时长中 84 行记为 `'0'`，按字面作 0 秒，占点击权重 0.013%%，影响可忽略。

权重（表6）：

| 指标 | 方向 | 信息熵 e | 差异系数 d | 权重 w |
|---|---|---|---|---|
%s

结果（表7）：

| 排名 | 推广单元ID | CTR | 跳出率 | 平均访问时长(秒) | 综合得分 C |
|---|---|---|---|---|---|
%s

## 六、产物清单

| 文件 | 内容 |
|---|---|
| 表1_月度汇总.csv | 月度核心指标（展现量/点击量/消费额/CTR/CPC） |
| 表2_月度补充指标.csv | 上方位CTR、首位展现率（非跳出率/时长） |
| 表3_结构诊断.csv | 各单元活跃月份数与是否可比子集 |
| 表4_可比口径CTR对比.csv | 全量 vs 可比子集 CTR，及结构效应 |
| 表5_年度单元汇总.csv | 12 个单元年度指标（跳出率/时长按点击加权） |
| 表6_熵权法权重.csv | 熵权法权重 |
| 表7_年度TOPSIS得分.csv | 全年综合得分与排名 |
| 图1_月度CTR趋势.png | 月度 CTR 趋势，标注最高/最低月 |
| 图2_月度规模指标.png | 展现量/点击量/消费额小倍数图 |
| 图3_结构漂移诊断.png | 全量与可比子集 CTR 对照 |
| 图4_年度综合得分.png | 12 个单元全年综合得分 |

## 七、未做的事（明确声明）

1. 未产出月度跳出率、月度平均访问时长——数据不存在，不做替代或伪造。
2. 未构造月度 TOPSIS 综合得分——受结构漂移影响，月度综合排名不可比。
3. 未对日 CTR 求简单平均。
4. 未对跳出率/平均访问时长求简单算术平均，已按点击量加权。
""" % ("\n".join(mrows), "\n".join(srows), "、".join(str(u) for u in allm),
       m.loc[1, "CTR"] * 100, 12, m.loc[12, "CTR"] * 100,
       m.loc[1, "上方位CTR"] * 100, m.loc[12, "上方位CTR"] * 100,
       "\n".join("| %s | %s | %.6f | %.6f | **%.4f** |"
                 % (r["指标"], r["方向"], r["信息熵e"], r["差异系数d"], r["权重w"])
                 for _, r in wt.iterrows()),
       "\n".join(rrows))

with io.open(os.path.join(OUT_DAT, "说明.md"), "w", encoding="utf-8") as f:
    f.write(doc)
log("  已保存: 说明.md")

with io.open(os.path.join(OUT_DAT, "运行日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
log("  已保存: 运行日志.txt")
log("")
log("完成，全部产物在: %s" % (OUT_FIG + ' / ' + OUT_DAT))
