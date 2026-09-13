# -*- coding: utf-8 -*-
"""
Q2 补充图（不改动、不覆盖任何已有图）
================================================================================
Q2-8 黄金词小样本诊断   —— 回应 P1-1（黄金词盘子极小、高效益来自 1~2 次点击）
Q2-9 分类稳健性补充     —— 回应 P2-1（阈值边界敏感）+ 方法间一致性

设计基座对齐 q2_charts.py / bid_budget_analysis.py：
白底 / 去上右边框 / 浅灰网格 / Microsoft YaHei / 300dpi
配色：Okabe-Ito 色盲安全（黄金#E69F00 重点#0072B2 潜力#009E73 问题#D55E00 无效#999999）
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__)); Q2 = os.path.dirname(BASE)
D = os.path.join(Q2, "data_Q2"); OUT = os.path.join(Q2, "charts_Q2")
os.makedirs(OUT, exist_ok=True)

def set_cjk_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for n in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "PingFang SC"]:
        if n in have:
            plt.rcParams["font.sans-serif"] = [n]; plt.rcParams["axes.unicode_minus"] = False; return n
set_cjk_font()

GOLD, KEY, POT, PROB, INV = "#E69F00", "#0072B2", "#009E73", "#D55E00", "#999999"
BLUE, ORANGE, PINK, PURPLE = "#2a78d6", "#eb6834", "#c2185b", "#4a3aa7"
INK, INK2, MUTED, GRID, REF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#9a9890"
GREY = "#8a8a8a"
CCOL = {"黄金词": GOLD, "重点词": KEY, "潜力词": POT, "问题词": PROB, "无效词": INV}
CATS4 = ["黄金词", "重点词", "潜力词", "问题词"]
DPI = 300
plt.rcParams.update({"font.size": 10.5, "axes.unicode_minus": False, "savefig.dpi": DPI})

def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2); ax.spines[s].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.9); ax.set_axisbelow(True)
    return ax

def save(fig, name):
    p = os.path.join(OUT, name + ".png")
    fig.savefig(p, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.28)
    plt.close(fig); print("  已保存:", p)

def rd(n): return pd.read_csv(os.path.join(D, n), encoding="utf-8-sig")

rec = rd("q2_record_clean.csv")
act = rd("q2_active_topsis.csv")
C_THR, S_THR = 8.06, 0.3193

# ================================================================ 复算管线（已验证与原始 S 完全一致）
SRC = os.path.normpath(os.path.join(Q2, "..", "题目", "附件", "附件1.xlsx"))
COLS = ["序号", "关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量", "跳出率", "平均访问时长"]

def build():
    df = pd.read_excel(SRC, sheet_name="Sheet3"); df.columns = COLS
    def to_s(x):
        s = str(x).strip()
        if s in ("/", "", "nan", "None", "0"): return np.nan
        try:
            h, m, sec = s.split(":"); return int(h) * 3600 + int(m) * 60 + int(sec)
        except Exception: return np.nan
    df["时长秒_原"] = df["平均访问时长"].map(to_s)
    for c in ["消费额", "点击量", "浏览量"]: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["跳出率"] = pd.to_numeric(df["跳出率"], errors="coerce")
    df["是否活跃"] = (df["消费额"] > 0) & (df["点击量"] > 0)
    am = df.loc[df["是否活跃"]].groupby(["方案ID", "推广单元ID"])["时长秒_原"].transform("median")
    df["时长秒"] = df["时长秒_原"]
    df.loc[df["是否活跃"], "时长秒"] = df.loc[df["是否活跃"], "时长秒_原"].fillna(am)
    df["时长秒"] = df["时长秒"].fillna(df.loc[df["是否活跃"], "时长秒_原"].median())
    df["浏览深度"] = np.where(df["点击量"] > 0, df["浏览量"] / df["点击量"], np.nan)
    df["留存率"] = 1 - df["跳出率"]
    return df

def classify(sub, W=np.array([.25] * 4)):
    """对给定活跃子集重算缩尾→TOPSIS→中位数切分，返回带 S/类别 的子集"""
    sub = sub.copy()
    for c in ["消费额", "点击量", "浏览深度", "留存率", "时长秒"]:
        lo, hi = sub[c].quantile(0.01), sub[c].quantile(0.99)
        sub[c + "_w"] = sub[c].clip(lo, hi)
    sub["x1"] = np.log1p(sub["点击量_w"]); sub["x2"] = np.log1p(sub["浏览深度_w"])
    sub["x3"] = sub["留存率_w"]; sub["x4"] = np.log1p(sub["时长秒_w"])
    X = sub[["x1", "x2", "x3", "x4"]].values.astype(float)
    R = X / np.sqrt((X ** 2).sum(0)); V = R * W
    vp, vn = V.max(0), V.min(0)
    dp = np.sqrt(((V - vp) ** 2).sum(1)); dn = np.sqrt(((V - vn) ** 2).sum(1))
    sub["S"] = dn / (dp + dn)
    ct, st = sub["消费额"].median(), sub["S"].median()
    hic = sub["消费额"] >= ct; his = sub["S"] >= st
    sub["cat"] = np.where(his, np.where(hic, "重点词", "黄金词"),
                          np.where(hic, "问题词", "潜力词"))
    return sub, ct, st

d0 = build()
act0 = d0[d0["是否活跃"]].copy()
KS = [1, 3, 5, 10, 20]

# 校验复算一致性
chk, _, _ = classify(act0)
m = chk[["序号", "S"]].merge(act[["序号", "S"]], on="序号", suffixes=("_n", "_o"))
print("复算校验: n=%d 相关=%.8f 最大差=%.8f" % (len(m), np.corrcoef(m.S_n, m.S_o)[0, 1],
                                              (m.S_n - m.S_o).abs().max()))

gold = act[act["基准类别"] == "黄金词"].copy()
print("黄金词 %d 条  消费合计 %.2f 元  点击中位 %.1f  点击<=1占比 %.1f%%  点击<=3占比 %.1f%%"
      % (len(gold), gold["消费额"].sum(), gold["点击量"].median(),
         (gold["点击量"] <= 1).mean() * 100, (gold["点击量"] <= 3).mean() * 100))

# ================================================================ Q2-8 黄金词小样本诊断（2×2）
fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4), dpi=DPI,
                         gridspec_kw={"wspace": 0.24, "hspace": 0.42})
for a in axes.ravel(): style(a)

# (a) 点击量(对数) × 留存率
ax = axes[0, 0]
oth = act[act["基准类别"] != "黄金词"]
ax.scatter(oth["点击量"], oth["留存率"], s=14, color=GREY, alpha=0.35,
           edgecolors="none", zorder=3, label="其他活跃词 (%d)" % len(oth))
ax.scatter(gold["点击量"], gold["留存率"], s=26, color=GOLD, alpha=0.85,
           edgecolors="white", linewidths=0.4, zorder=4, label="黄金词 (%d)" % len(gold))
ax.axvspan(0.7, 3.5, color=PINK, alpha=0.09, lw=0, zorder=1)
ax.axvline(3.5, color=PINK, ls="--", lw=1.3, zorder=2)
ax.text(3.7, 0.03, "点击 ≤ 3", fontsize=9.5, color=PINK)
ax.set_xscale("log"); ax.set_xlim(0.7, act["点击量"].max() * 1.6); ax.set_ylim(-0.02, 1.05)
ax.set_xlabel("全年点击量（次，对数轴）", fontsize=11.5, color=INK)
ax.set_ylabel("用户留存率 1 − 跳出率", fontsize=11.5, color=INK)
ax.set_title("(a) 黄金词的“高留存”集中在极低点击", fontsize=12, color=INK, pad=9, loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower right")

# (b) 黄金词点击量 ECDF
ax = axes[0, 1]
v = np.sort(gold["点击量"].values)
y = np.arange(1, len(v) + 1) / len(v)
ax.step(v, y * 100, where="post", color=GOLD, lw=2.2, zorder=4)
ax.fill_between(v, 0, y * 100, step="post", color=GOLD, alpha=0.13, zorder=2)
for k, c in [(1, INK2), (3, PINK)]:
    p = (gold["点击量"] <= k).mean() * 100
    ax.axvline(k, color=c, ls="--", lw=1.3, zorder=3)
    ax.annotate("≤%d 次：%.1f%%（%d 条）" % (k, p, int((gold["点击量"] <= k).sum())),
                xy=(k, p), xytext=(10, -4), textcoords="offset points", fontsize=9.2, color=c)
ax.set_xscale("log"); ax.set_xlim(0.9, max(v.max(), 30) * 1.3); ax.set_ylim(0, 105)
ax.set_xlabel("全年点击量（次，对数轴）", fontsize=11.5, color=INK)
ax.set_ylabel("累计占比（%）", fontsize=11.5, color=INK)
ax.set_title("(b) 黄金词点击量累积分布", fontsize=12, color=INK, pad=9, loc="left")

# (c) 原 225 条黄金词在门槛下的存活
ax = axes[1, 0]
surv = []
for k in KS:
    s = gold[gold["点击量"] >= k]
    surv.append({"k": k, "n": len(s), "spend": s["消费额"].sum()})
sd = pd.DataFrame(surv)
xx = np.arange(len(KS))
ax.bar(xx - 0.19, sd["n"].values, width=0.38, color=GOLD, edgecolor="white", lw=0.8,
       zorder=3, label="幸存黄金词数")
for x_, v_ in zip(xx - 0.19, sd["n"].values):
    ax.text(x_, v_ + 4, "%d" % v_, ha="center", fontsize=9.5, color=INK)
ax.set_ylim(0, len(gold) * 1.25); ax.set_ylabel("原黄金词条数（条）", fontsize=11.5, color=GOLD)
ax2 = ax.twinx()
ax2.bar(xx + 0.19, sd["spend"].values, width=0.38, color=KEY, alpha=0.75,
        edgecolor="white", lw=0.8, zorder=3, label="幸存词消费额")
for x_, v_ in zip(xx + 0.19, sd["spend"].values):
    ax2.text(x_, v_ + 12, "%.0f" % v_, ha="center", fontsize=8.5, color=KEY)
ax2.set_ylim(0, gold["消费额"].sum() * 1.25); ax2.set_ylabel("合计消费额（元）", fontsize=11.5, color=KEY)
ax2.tick_params(colors=KEY, labelsize=10); ax2.spines["top"].set_visible(False)
ax.set_xticks(xx); ax.set_xticklabels(["≥%d" % k for k in KS], fontsize=11)
ax.set_xlabel("最小点击门槛（次）", fontsize=11.5, color=INK)
ax.set_title("(c) 原 225 条黄金词的幸存量（随门槛递减）", fontsize=12, color=INK, pad=9, loc="left")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper right")

# (d) 设门槛后“重分类”的象限规模
ax = axes[1, 1]
thr = []
for k in KS:
    s2, ct, st = classify(act0[act0["点击量"] >= k])
    thr.append({"k": k, "n": len(s2), "Cthr": ct, "Sthr": st,
                **{c: int((s2["cat"] == c).sum()) for c in CATS4}})
thr = pd.DataFrame(thr)
wd = 0.2
for i, c in enumerate(CATS4):
    ax.bar(xx + (i - 1.5) * wd, thr[c].values, width=wd, color=CCOL[c],
           edgecolor="white", lw=0.6, zorder=3, label=c)
    for x_, v_ in zip(xx + (i - 1.5) * wd, thr[c].values):
        ax.text(x_, v_ + 6, str(int(v_)), ha="center", fontsize=7.5, color=INK2)
ax.set_xticks(xx); ax.set_xticklabels(["≥%d" % k for k in KS], fontsize=11)
ax.set_ylim(0, max(thr[CATS4].values.max() * 1.30, 10))
ax.set_xlabel("最小点击门槛（次）", fontsize=11.5, color=INK)
ax.set_ylabel("重分类后各类记录数（条）", fontsize=11.5, color=INK)
ax.set_title("(d) 设门槛后重分类（TOPSIS/中位数全部重算）", fontsize=12, color=INK, pad=9, loc="left")
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
fig.suptitle("黄金词小样本诊断：黄金词仅 225 条、合计消费 %.0f 元，" 
             "且 72.4%% 的点击 ≤ 3 次" % gold["消费额"].sum(), fontsize=14, color=INK, y=0.985)
fig.text(0.5, 0.005, "注：(a)(b) 横轴为对数轴；(c) 固定原 225 条黄金词、只加点击门槛；"
                     "(d) 每换一个门槛即对四指标缩尾、TOPSIS 与两个中位数阈值全部重算，故各类为新划分结果。",
         ha="center", va="top", fontsize=9, color=MUTED)
fig.subplots_adjust(left=0.075, right=0.955, top=0.905, bottom=0.085)
save(fig, "Q2-8_黄金词小样本诊断")
print("\n原黄金词存活:", sd.round(2).to_dict("records"))
print("门槛重分类:\n", thr.round(3).to_string(index=False))

# ================================================================ Q2-9 分类稳健性补充
fig, axes = plt.subplots(1, 3, figsize=(13.6, 5.0), dpi=DPI,
                         gridspec_kw={"wspace": 0.28})
for a in axes: style(a)

# (a) S 分布 + 阈值 ±5% 带
ax = axes[0]
Sv = act["S"].values
ax.hist(Sv, bins=48, color=BLUE, alpha=0.75, edgecolor="white", lw=0.5, zorder=3)
lo, hi = S_THR * 0.95, S_THR * 1.05
nb = int(((Sv >= lo) & (Sv <= hi)).sum())
ax.axvspan(lo, hi, color=PINK, alpha=0.16, lw=0, zorder=2)
ax.axvline(S_THR, color=INK, ls="--", lw=1.6, zorder=4)
ax.annotate("阈值 %.4f" % S_THR, xy=(S_THR, ax.get_ylim()[1]), xytext=(6, -12),
            textcoords="offset points", fontsize=9.5, color=INK)
ax.annotate("±5%% 带内 %d 条（%.1f%%）\n其中约 48%% 会因方法/权重改类" % (nb, 100 * nb / len(Sv)),
            xy=(0.98, 0.95), xycoords="axes fraction", ha="right", va="top",
            fontsize=9.5, color=PINK)
ax.set_xlabel("综合效益得分 S", fontsize=12, color=INK)
ax.set_ylabel("活跃记录数（条）", fontsize=12, color=INK)
ax.set_title("(a) 效益阈值附近的记录密度", fontsize=12, color=INK, pad=10, loc="left")

# (b) 阈值缩放 → 四类数量
ax = axes[1]
fs = np.linspace(0.90, 1.10, 21)
cnt = {c: [] for c in CATS4}
for f in fs:
    st = S_THR * f
    hic = act["消费额"].values >= C_THR; his = act["S"].values >= st
    for c, mask in zip(CATS4, [his & ~hic, his & hic, ~his & ~hic, ~his & hic]):
        cnt[c].append(int(mask.sum()))
for c in CATS4:
    ax.plot(fs * 100, cnt[c], "o-", color=CCOL[c], lw=2.0, ms=4.5, label=c, zorder=4)
ax.axvline(100, color=INK2, ls="--", lw=1.2, zorder=2)
ax.set_xlabel("效益阈值相对基准的缩放（%）", fontsize=12, color=INK)
ax.set_ylabel("记录数（条）", fontsize=12, color=INK)
ax.set_title("(b) 效益阈值 ±10% 下的类别数量", fontsize=12, color=INK, pad=10, loc="left")
ax.legend(frameon=False, fontsize=9, ncol=2, loc="center right")
rng = {c: (min(cnt[c]), max(cnt[c])) for c in CATS4}
ax.text(0.02, 0.03, "摆动幅度：\n" + "  ".join("%s %d~%d" % (c[:2], *rng[c]) for c in CATS4),
        transform=ax.transAxes, fontsize=8.5, color=MUTED)

# (c) 三情景两两一致率
ax = axes[2]
scen = ["基准等权", "流量优先", "质量优先"]
lab = {s: s for s in scen}
pairs = [(0, 1), (0, 2), (1, 2)]
vals = []
for i, j in pairs:
    a = act["类别_" + scen[i]].values; b = act["类别_" + scen[j]].values
    vals.append((a == b).mean() * 100)
bars = ax.bar(range(3), vals, width=0.55,
              color=[KEY, GOLD, POT], edgecolor="white", lw=0.8, zorder=3)
for i, v in enumerate(vals):
    ax.text(i, v + 0.6, "%.2f%%" % v, ha="center", fontsize=11, color=INK)
ax.axhline(86.16, color=PINK, ls="--", lw=1.4, zorder=2)
ax.text(2.45, 86.6, "三情景全一致 86.16%", ha="right", fontsize=9.5, color=PINK)
ax.set_xticks(range(3))
ax.set_xticklabels(["%s\nvs %s" % (lab[scen[i]], lab[scen[j]]) for i, j in pairs], fontsize=10)
ax.set_ylim(0, 100)
ax.set_ylabel("类别完全一致的活跃记录占比（%）", fontsize=12, color=INK)
ax.set_title("(c) 方法/权重情景间的一致性", fontsize=12, color=INK, pad=10, loc="left")
fig.suptitle("分类稳健性补充：权重情景间一致率 ≥ %.1f%%，阈值 ±5%% 带内仅 %.1f%% 记录敏感"
             % (min(vals), 100 * nb / len(Sv)), fontsize=14, color=INK, y=1.02)
fig.text(0.5, -0.06, "注：面板(a)记录 S 的分布密度；面板(b)固定成本阈值 8.06 元、只缩放效益阈值；"
                     "面板(c) 为三组权重情景两两的类别一致率（含 890 条无效词）。",
         ha="center", va="top", fontsize=9, color=MUTED)
save(fig, "Q2-9_分类稳健性补充")

# ================================================================ 附：口径待核查清单（P1-4）
flag = rec[(rec["消费额"] == 0) & (rec["点击量"] == 0) & (rec["浏览量"] > 0)].copy()
flag["口径待核查"] = "零消费零点击但有浏览量，保留原值并标记待核查"
flag[["序号", "关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量", "跳出率", "口径待核查"]] \
    .to_csv(os.path.join(D, "q2_口径待核查清单.csv"), index=False, encoding="utf-8-sig")
print("\n口径待核查记录 %d 条 ->" % len(flag), "q2_口径待核查清单.csv")
print(flag[["序号", "关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量"]].to_string(index=False))
print("\n完成。")
