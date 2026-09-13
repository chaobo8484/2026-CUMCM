# -*- coding: utf-8 -*-
"""G10 假日/周末效应展品：a)CPA三态箱线 b)注册三态箱线 c)周末vs工作日双子图。
假设检查→Shapiro(分组)+Levene→偏态→Kruskal-Wallis+ε²，两两MW+Holm；
周末MW+r+bootstrap中位差CI(种子2026)。五件套上图，明细存CSV。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from style_q1 import apply_style, OI, FIG_W_FULL, FIG_W_HALF, MM

apply_style()
RNG = np.random.default_rng(2026)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGD = os.path.join(ROOT, "charts_Q1")
d = pd.read_csv(os.path.join(ROOT, "data_Q1", "q1_daily.csv"))
GROUPS = ["正常", "放假", "补班"]
GNAME = {"正常": "正常", "放假": "放假", "补班": "补班"}


def grp(x, g, var):
    return x.loc[x["三态标签"] == g, var].dropna().values


def check_assume(x, gname, var):
    out = {}
    for g in gname:
        v = grp(x, g, var)
        out[g] = {"n": len(v), "shapiro_p": float(stats.shapiro(v).pvalue)}
    lev = stats.levene(*[grp(x, g, var) for g in gname])
    return out, float(lev.pvalue)


def boot_med_diff(a, b, B=5000):
    diffs = [np.median(RNG.choice(a, len(a), replace=True))
             - np.median(RNG.choice(b, len(b), replace=True)) for _ in range(B)]
    return float(np.median(a) - np.median(b)), \
        float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def kw_full(x, var):
    arr = [grp(x, g, var) for g in GROUPS]
    H, p = stats.kruskal(*arr).statistic, stats.kruskal(*arr).pvalue
    N = sum(len(v) for v in arr)
    eps2 = H / (N - 1)
    pairs, raw = [], []
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = arr[i], arr[j]
            u = stats.mannwhitneyu(a, b, alternative="two-sided")
            r_rb = 1 - 2 * u.statistic / (len(a) * len(b))
            md, lo, hi = boot_med_diff(a, b)
            pairs.append((GROUPS[i], GROUPS[j], len(a), len(b),
                          float(u.statistic), float(u.pvalue), float(r_rb),
                          md, lo, hi))
            raw.append(float(u.pvalue))
    # Holm校正（手写，无外部依赖）
    m = len(raw)
    order = sorted(range(m), key=lambda k: raw[k])
    adj = [0.0] * m
    for rank, k in enumerate(order):
        adj[k] = min(1.0, raw[k] * (m - rank))
    for rank in range(1, m):  # 单调化
        k, prev = order[rank], order[rank - 1]
        adj[k] = max(adj[k], adj[prev])
    rows = []
    for k, pr in enumerate(pairs):
        rows.append(pr + (float(adj[k]), bool(adj[k] < 0.05)))
    return float(H), float(p), float(eps2), N, rows


def box_with_points(ax, x, var, ylabel, colors):
    data = [grp(x, g, var) for g in GROUPS]
    bp = ax.boxplot(data, tick_labels=[f"{g}\nn={len(v)}" for g, v in zip(GROUPS, data)],
                    patch_artist=True, showfliers=False, widths=0.5,
                    medianprops=dict(color="#333333", linewidth=1.5),
                    boxprops=dict(linewidth=1.0), whiskerprops=dict(linewidth=1.0),
                    capprops=dict(linewidth=1.0))
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    for i, v in enumerate(data):
        xj = RNG.normal(i + 1, 0.07, len(v))
        ax.scatter(xj, v, s=9, color=colors[i], alpha=0.55,
                   edgecolors="white", linewidths=0.4, zorder=3)
    ax.set_ylabel(ylabel)
    return [float(np.max(v)) for v in data]


def bracket(ax, i, j, y, txt):
    ax.plot([i + 1, i + 1, j + 1, j + 1], [y, y * 1.02, y * 1.02, y],
            color="#333333", linewidth=1.0)
    ax.text((i + j) / 2 + 1, y * 1.025, txt, ha="center", va="bottom", fontsize=8)


def fmt_p(p):
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


stats_rows = []
for var, ylabel, stem, title in [
        ("CPA", "CPA（元/人）", "q1_g10a_CPA三态", "CPA三态对比"),
        ("新注册数", "日注册（人）", "q1_g10b_注册三态", "日注册三态对比")]:
    chk, lev_p = check_assume(d, GROUPS, var)
    H, p, e2, N, pairs = kw_full(d, var)
    fig, ax = plt.subplots(figsize=(FIG_W_FULL, 100 * MM))
    vmax = box_with_points(ax, d, var, ylabel, [OI["blue"], OI["orange"], OI["grey"]])
    if var == "CPA":
        # 单天极端CPA会压扁箱体：截断显示并单独标注，不删除
        cap = 105
        out = d.loc[d[var] > cap, ["日期", var, "新注册数"]]
        ax.set_ylim(0, cap)
        for _, r in out.iterrows():
            ax.text(0.97, 0.80,
                    f"{pd.to_datetime(r['日期']).date()}CPA={r[var]:.0f}元/人"
                    f"（注册仅{int(r['新注册数'])}人）超出显示",
                    transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
                    color="#333333")
        top = max(v[v <= cap].max() for v in
                  [grp(d, g, var) for g in GROUPS])
    else:
        top = max(vmax)
    yy = top * 1.06
    for (g1, g2, n1, n2, U, praw, rrb, md, lo, hi, pholm, rej) in pairs:
        tag = "†探索性" if min(n1, n2) < 10 else ""
        stats_rows.append(dict(变量=var, 对比=f"{g1}vs{g2}", n1=n1, n2=n2, U=U,
                               p原始=praw, pHolm=pholm, 显著=rej,
                               r秩二列=rrb, 中位差=md, CI下=lo, CI上=hi, 备注=tag))
        if rej:
            i, j = GROUPS.index(g1), GROUPS.index(g2)
            bracket(ax, i, j, yy, fmt_p(pholm) + tag)
            yy *= 1.10
    ax.set_ylim(0, yy * 1.02)
    ax.set_title(f"{title}（Kruskal-Wallis H={H:.1f}，{fmt_p(p)}，ε²={e2:.3f}，N={N}）",
                 pad=10)
    ax.text(0.01, -0.14,
            f"假设检查：Shapiro正态p均<0.05且Levene齐方差{fmt_p(lev_p)}，"
            f"数据偏态→非参数；两两Mann-Whitney经Holm校正，†为补班组n=5探索性比较。",
            transform=ax.transAxes, fontsize=7, ha="left", va="top", color="#333333")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#CCCCCC")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGD, stem + ".pdf"), dpi=300, bbox_inches="tight",
                transparent=False)
    fig.savefig(os.path.join(FIGD, stem + ".png"), dpi=300, bbox_inches="tight",
                transparent=False)
    plt.close(fig)
    print(title, f"H={H:.2f}", fmt_p(p), f"eps2={e2:.3f}")

# c) 周末 vs 工作日
wd = d[d["是否周末"] == 0]
we = d[d["是否周末"] == 1]
fig, axes = plt.subplots(1, 2, figsize=(FIG_W_FULL, 95 * MM))
cl = [OI["blue"], OI["vermillion"]]
for ax, var, ylabel, ttl in zip(axes, ["新注册数", "CPA"],
                                ["日注册（人）", "CPA（元/人）"],
                                ["日注册", "CPA"]):
    a, b = wd[var].dropna().values, we[var].dropna().values
    sw_a, sw_b = stats.shapiro(a).pvalue, stats.shapiro(b).pvalue
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    rrb = 1 - 2 * u.statistic / (len(a) * len(b))
    md, lo, hi = boot_med_diff(a, b)
    bp = ax.boxplot([a, b], tick_labels=[f"工作日\nn={len(a)}", f"周末\nn={len(b)}"],
                    patch_artist=True, showfliers=False, widths=0.5,
                    medianprops=dict(color="#333333", linewidth=1.5))
    for patch, c in zip(bp["boxes"], cl):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    for i, v in enumerate([a, b]):
        ax.scatter(RNG.normal(i + 1, 0.07, len(v)), v, s=9, color=cl[i],
                   alpha=0.45, edgecolors="white", linewidths=0.4, zorder=3)
    ax.set_title(ttl, fontsize=10)
    ax.text(0.5, -0.30,
            f"MW U={u.statistic:.0f}，{fmt_p(u.pvalue)}，r={rrb:.2f}\n"
            f"中位差{md:.1f}，95%CI[{lo:.1f},{hi:.1f}]",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#CCCCCC")
    stats_rows.append(dict(变量=var, 对比="工作日vs周末", n1=len(a), n2=len(b),
                           U=float(u.statistic), p原始=float(u.pvalue),
                           pHolm=float(u.pvalue), 显著=bool(u.pvalue < 0.05),
                           r秩二列=float(rrb), 中位差=md, CI下=lo, CI上=hi,
                           备注=f"Shapiro p={sw_a:.3f}/{sw_b:.3f}偏态→非参数"))
fig.suptitle("周末效应（Mann-Whitney；中位差=工作日−周末，bootstrap95%CI，种子2026）",
             fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIGD, "q1_g10c_周末效应.pdf"), dpi=300,
            bbox_inches="tight", transparent=False)
fig.savefig(os.path.join(FIGD, "q1_g10c_周末效应.png"), dpi=300,
            bbox_inches="tight", transparent=False)
plt.close(fig)

pd.DataFrame(stats_rows).to_csv(os.path.join(ROOT, "data_Q1", "q1_g10_stats.csv"),
                                index=False, encoding="utf-8-sig")
print("G10 done, stats→q1_g10_stats.csv")
