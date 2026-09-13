# -*- coding: utf-8 -*-
"""Q1绘图共享样式块：色板/字体/字号/线宽/尺寸/导出。所有G脚本import此块。"""
import matplotlib as mpl
import matplotlib.pyplot as plt

# 色盲安全：Okabe-Ito（分类≤8，尾部合并）；连续viridis
OI = {
    "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00",
    "purple": "#CC79A7", "grey": "#999999",
}
OI_LIST = [OI["blue"], OI["orange"], OI["green"], OI["vermillion"],
           OI["sky"], OI["purple"], OI["yellow"], OI["grey"]]
CMAP_SEQ = "viridis"

# 论文风语义色（与 bid_budget_analysis.py 一致）
INK = "#0b0b0b"        # 主文字/主线
INK2 = "#52514e"       # 次文字/轴脊
MUTED = "#898781"      # 弱化说明文字
GRID = "#e1e0d9"       # 浅网格
REF = "#9a9890"        # 参考线

FONT_CN = "Microsoft YaHei"  # 备选 SimHei；Linux审稿机回退 DejaVu Sans
MM = 1 / 25.4
FIG_W_FULL = 150 * MM   # 国赛通栏图宽
FIG_W_HALF = 110 * MM


def apply_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT_CN, "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "lines.linewidth": 1.5,
        "lines.markersize": 5,
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.7,
        "grid.color": GRID,
        "grid.linestyle": "-",
        "grid.alpha": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,  # TrueType子集嵌入
    })


def new_fig(w=FIG_W_FULL, h=95 * MM, dpi=300):
    """论文风：白底、无3D装饰、去上右边框、左下标轴与浅色网格统一（学习 bid_budget_analysis.py）。"""
    fig = plt.figure(figsize=(w, h), dpi=dpi, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=8.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)
    return fig, ax


def style_axes(ax):
    """对已存在的 axes（如 subplots 面板）统一套用论文风边框与网格。"""
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=8.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle="-", alpha=0.9)
    ax.set_axisbelow(True)
    return ax


def footnote(ax, text, y=-0.16, fontsize=7.5, color=MUTED):
    """图下脚注：口径、编码、显著性说明等。"""
    return ax.text(0.5, y, text, transform=ax.transAxes, ha="center", va="top",
                   fontsize=fontsize, color=color)


def save_fig(fig, name, outdir, retries=4):
    """PDF+PNG 双存（300dpi），带重试规避 Windows 下中文文件名偶发 EBUSY/EINVAL。"""
    import time
    import os
    p_pdf = os.path.join(outdir, name + ".pdf")
    p_png = os.path.join(outdir, name + ".png")
    for p in (p_pdf, p_png):
        for attempt in range(retries):
            try:
                fig.savefig(p, dpi=300, bbox_inches="tight", transparent=False)
                break
            except OSError:
                if attempt == retries - 1:
                    raise
                time.sleep(0.25)
    plt.close(fig)
    return p_pdf, p_png


def unit_short(uid):
    """单元ID后4位短标签，12个互异。"""
    return "单元" + str(int(uid))[-4:]


PLAN_COLORS = {  # 5方案分组色（Okabe-Ito前5）
    63563817: OI["blue"], 495403620: OI["orange"], 495817671: OI["green"],
    500635396: OI["vermillion"], 525368335: OI["purple"],
}
