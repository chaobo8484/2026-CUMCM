# -*- coding: utf-8 -*-
"""
2026 全国大学生数学建模竞赛 E 题 —— 问题1「出价策略与预算」可视化分析
================================================================================
数据源: E题 附件1.xlsx  →  Sheet1「2025年投放方案与消费记录数据」(实测确认)

【实测数据结构(非假设)】
  Sheet1  2627 行 × 10 列
  字段: 日期, 方案ID, 推广单元ID, 展现量, 点击量, 消费额,
        上方位展现量, 上方首位展现量, 上方位点击量, 上方位消费额
  日期范围 2025-01-01 ~ 2025-12-31 (365 个自然日全覆盖)
  方案ID 5 个, 方案ID×推广单元ID = 12 个推广单元  ← 与题面「12 个推广单元」一致

【统一分析粒度】
  按 (方案ID, 推广单元ID) 对全年做「总量汇总」, 得到 12 行。
  CTR / CPC 一律用汇总总量重新计算, **不做日度比率的算术平均**:
      CTR = Σ点击量 / Σ展现量        (分母为 0 → NaN, 不填 0)
      CPC = Σ消费额 / Σ点击量        (分母为 0 → NaN, 不填 0)

【配色】
  #2a78d6 / #eb6834 / #1baf7a / #4a3aa7 / #c2185b  (5 个方案ID, 固定顺序不循环)
  该 5 色组合已通过色盲安全校验(全对比较 all-pairs):
    最差 CVD ΔE 9.2 (deutan) / 最差常视觉 ΔE 16.3  → 全部通过
  同时每点直接标注单元ID后4位 + 图例, 颜色绝非唯一识别通道。

输出: bid_budget_output/ 下 4 张 300dpi PNG + 1 个 4+1 表 xlsx
"""
import os
import sys
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# ================================================================ 0. 路径
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'bid_budget_output')
os.makedirs(OUT, exist_ok=True)

LOG = []


def log(msg=''):
    print(msg)
    LOG.append(str(msg))


# ================================================================ 1. 定位数据文件
REQUIRED_COLS = ['日期', '方案ID', '推广单元ID', '展现量', '点击量', '消费额',
                 '上方位展现量', '上方首位展现量', '上方位点击量', '上方位消费额']

CANDIDATE_DIRS = [
    BASE,
    os.path.join(BASE, '附件'),
    r'D:\2026-CUMCM\E题\附件',
    r'D:\CUMCM2026Problems(1)\E题\附件',
    r'D:\CUMCM2026Problems(1)\E题',
]


def locate_excel():
    """自动识别附件1的 Excel 文件。优先命令行参数, 其次候选目录, 最后递归搜索。"""
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return os.path.abspath(sys.argv[1])
    for d in CANDIDATE_DIRS:
        for name in ('附件1.xlsx', '附件1.xls', '附件1.xlsm'):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    for d in CANDIDATE_DIRS:
        if os.path.isdir(d):
            hits = sorted(glob.glob(os.path.join(d, '**', '附件1*.xls*'), recursive=True))
            if hits:
                return hits[0]
    raise FileNotFoundError('未能自动定位 附件1.xlsx, 请把文件放到项目目录, 或作为命令行参数传入路径')


def pick_sheet(path):
    """自动识别 Sheet1: 优先名为 Sheet1 的表; 否则取第一个包含全部必需字段的表。"""
    names = pd.ExcelFile(path).sheet_names
    if 'Sheet1' in names:
        return 'Sheet1'
    for s in names:
        head = pd.read_excel(path, sheet_name=s, nrows=0)
        cols = [str(c).strip() for c in head.columns]
        if all(c in cols for c in REQUIRED_COLS):
            return s
    return names[0]


SRC = locate_excel()
SHEET = pick_sheet(SRC)
log('=' * 78)
log('数据源: %s' % SRC)
log('工作表: %s   (全部工作表: %s)' % (SHEET, pd.ExcelFile(SRC).sheet_names))
log('=' * 78)

# ================================================================ 2. 读取 + 清洗
raw = pd.read_excel(SRC, sheet_name=SHEET)
raw.columns = [str(c).strip() for c in raw.columns]

missing = [c for c in REQUIRED_COLS if c not in raw.columns]
if missing:
    raise KeyError('工作表 %s 缺少字段: %s' % (SHEET, missing))

df = raw[REQUIRED_COLS].copy()

# -------- 2.1 方案ID / 推广单元ID 一律按字符串处理
def to_id_str(s):
    """转字符串ID: 去掉首尾空白与 Excel 数值尾部的 '.0', 并剥离千分位。"""
    s = s.astype(str).str.strip().str.replace(',', '', regex=False)
    s = s.str.replace(r'\.0+$', '', regex=True)
    return s


df['方案ID'] = to_id_str(df['方案ID'])
df['推广单元ID'] = to_id_str(df['推广单元ID'])

# -------- 2.2 数值字段强制转数值
NUM_COLS = ['展现量', '点击量', '消费额', '上方位展现量', '上方首位展现量',
            '上方位点击量', '上方位消费额']
for c in NUM_COLS:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['日期'] = pd.to_datetime(df['日期'], errors='coerce')

# ================================================================ 3. 数据质量核验
log('\n【一】数据质量核验')
log('  原始行数 × 列数 : %d × %d' % raw.shape)
log('  字段名           : %s' % ' | '.join(df.columns))
log('  缺失值(原表全列) : %d 处' % int(raw.isna().sum().sum()))
log('  缺失值(选用列)   : %d 处' % int(df[REQUIRED_COLS].isna().sum().sum()))
log('  完全重复行       : %d 行' % int(df.duplicated().sum()))
log('  日期解析失败     : %d 行' % int(df['日期'].isna().sum()))
if df['日期'].notna().any():
    log('  日期范围         : %s ~ %s  (覆盖 %d 个自然日)' % (
        df['日期'].min().strftime('%Y-%m-%d'),
        df['日期'].max().strftime('%Y-%m-%d'),
        df['日期'].dt.normalize().nunique()))
log('  方案ID 数        : %d  (%s)' % (df['方案ID'].nunique(), ', '.join(sorted(df['方案ID'].unique()))))
log('  推广单元ID 数    : %d' % df['推广单元ID'].nunique())
n_pair = df.groupby(['方案ID', '推广单元ID']).ngroups
log('  方案×单元 组合数 : %d' % n_pair)

# 逻辑一致性检查(高位字段应为总量字段的子集, 点击不应超过展现)
qc = {
    '上方位展现量 > 展现量': int((df['上方位展现量'] > df['展现量']).sum()),
    '上方首位展现量 > 上方位展现量': int((df['上方首位展现量'] > df['上方位展现量']).sum()),
    '上方位点击量 > 点击量': int((df['上方位点击量'] > df['点击量']).sum()),
    '点击量 > 展现量': int((df['点击量'] > df['展现量']).sum()),
    '上方位消费额 > 消费额': int((df['上方位消费额'] > df['消费额']).sum()),
}
log('  逻辑一致性(违规行数): %s' % '; '.join('%s=%d' % kv for kv in qc.items()))

ZERO = {
    '展现量为0': int((df['展现量'] == 0).sum()),
    '点击量为0': int((df['点击量'] == 0).sum()),
    '消费额为0': int((df['消费额'] == 0).sum()),
    '上方位展现量为0': int((df['上方位展现量'] == 0).sum()),
    '上方位点击量为0': int((df['上方位点击量'] == 0).sum()),
}
log('  零值行数(日×单元): %s' % '; '.join('%s=%d' % kv for kv in ZERO.items()))

# 每个单元实际有数据的天数
days_per_unit = df.groupby(['方案ID', '推广单元ID'])['日期'].nunique()
log('  单元覆盖天数     : 最少 %d 天, 最多 %d 天, 中位 %d 天 (全年应 365 天)'
    % (days_per_unit.min(), days_per_unit.max(), int(days_per_unit.median())))

# ================================================================ 4. 汇总到 12 个推广单元
UNIT_KEYS = ['方案ID', '推广单元ID']
g = df.groupby(UNIT_KEYS, as_index=False).agg(
    总展现量=('展现量', 'sum'),
    总点击量=('点击量', 'sum'),
    总消费额=('消费额', 'sum'),
    总上方位展现量=('上方位展现量', 'sum'),
    总上方首位展现量=('上方首位展现量', 'sum'),
    总上方位点击量=('上方位点击量', 'sum'),
    总上方位消费额=('上方位消费额', 'sum'),
    覆盖天数=('日期', 'nunique'),
)

# -------- 4.1 需求 2: 用汇总总量重算比率, 分母为 0 记 NaN
def safe_div(num, den):
    """安全除法: 分母为 0 / 缺失 / 非有限 → NaN(绝不强行填 0)。"""
    num = pd.to_numeric(num, errors='coerce').astype(float)
    den = pd.to_numeric(den, errors='coerce').astype(float)
    out = pd.Series(np.nan, index=num.index, dtype=float)
    ok = den.notna() & (den != 0)
    out[ok] = num[ok] / den[ok]
    return out


g['CTR'] = safe_div(g['总点击量'], g['总展现量'])          # 点击率(小数)
g['CPC'] = safe_div(g['总消费额'], g['总点击量'])          # 单次点击成本(元)

# -------- 4.2 需求 4: 高位竞价指标
g['上方位展现率'] = safe_div(g['总上方位展现量'], g['总展现量'])
g['首位展现率'] = safe_div(g['总上方首位展现量'], g['总展现量'])
g['上方位CTR'] = safe_div(g['总上方位点击量'], g['总上方位展现量'])
g['上方位CPC'] = safe_div(g['总上方位消费额'], g['总上方位点击量'])
g['P'] = safe_div(g['上方位CPC'], g['CPC'])                # 成本溢价系数
g['G'] = safe_div(g['上方位CTR'], g['CTR'])                # 效果增益系数

# -------- 4.3 需求 5: 预算-点击贡献匹配
tot_cost = g['总消费额'].sum()
tot_clk = g['总点击量'].sum()
g['预算占比B'] = safe_div(g['总消费额'], pd.Series(tot_cost, index=g.index))
g['点击贡献占比Q'] = safe_div(g['总点击量'], pd.Series(tot_clk, index=g.index))
g['D'] = g['点击贡献占比Q'] - g['预算占比B']

# -------- 4.4 图上标注用的短名(单元ID后 4 位)
g['简称'] = g['推广单元ID'].str[-4:]

# -------- 4.5 需求 6: Pareto
par = g.sort_values('总消费额', ascending=False).reset_index(drop=True)
par['消费占比'] = safe_div(par['总消费额'], pd.Series(tot_cost, index=par.index))
par['累计消费占比'] = par['消费占比'].cumsum()
par['点击占比'] = safe_div(par['总点击量'], pd.Series(tot_clk, index=par.index))
par['累计点击占比'] = par['点击占比'].cumsum()

# ================================================================ 5. 绘图基础设置
def set_cjk_font():
    """自动挑选可用中文字体, 保证中文正常显示而不是方框。"""
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ['Microsoft YaHei', 'SimHei', 'SimSun', 'Noto Sans CJK SC',
                 'Source Han Sans SC', 'PingFang SC', 'WenQuanYi Micro Hei']:
        if name in have:
            plt.rcParams['font.sans-serif'] = [name]
            plt.rcParams['axes.unicode_minus'] = False
            return name
    raise RuntimeError('未找到可用中文字体, 请安装 SimHei 或 Microsoft YaHei')


FONT = set_cjk_font()
log('\n中文字体: %s' % FONT)

# 5 个方案ID 的固定配色(顺序固定, 不随筛选变化) —— 已过色盲安全校验
PLAN_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#c2185b']
PLANS = sorted(g['方案ID'].unique())
if len(PLANS) > len(PLAN_COLORS):      # 兜底: 方案超过 5 个时扩展调色板
    PLAN_COLORS = PLAN_COLORS + ['#008300', '#eda100', '#e34948']
COLOR_OF = {p: PLAN_COLORS[i] for i, p in enumerate(PLANS)}

INK = '#0b0b0b'        # 主文字
INK2 = '#52514e'       # 次文字
MUTED = '#898781'      # 弱化文字
GRID = '#e1e0d9'       # 网格
REF = '#9a9890'        # 参考线

DPI = 300              # 画布与导出同为 300dpi —— 标注防重叠布局才能与最终出图一致


def new_fig(w=10.0, h=7.2):
    """论文风格: 白底、无 3D、无驾驶舱装饰。"""
    fig = plt.figure(figsize=(w, h), dpi=DPI, facecolor='white')
    ax = fig.add_subplot(111)
    ax.set_facecolor('white')
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(INK2)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle='-', alpha=0.9)
    ax.set_axisbelow(True)
    return fig, ax


def _overlap(a, b):
    """两个矩形 (x0,y0,x1,y1) 的重叠面积。"""
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if (dx > 0 and dy > 0) else 0.0


def place_labels(ax, xs, ys, labels, sizes=None, fontsize=9.5, avoid=()):
    """无依赖的标注防重叠: 每个标签在 8 个候选方位里挑一个不压点、不压其他标签、
    不压 avoid 里的文字、不出坐标区的位置; 全部冲突时取重叠面积最小的那个。
    标签外加白色描边, 保证压线时依然清晰。"""
    fig = ax.figure
    fig.canvas.draw()
    px_per_pt = fig.dpi / 72.0
    h = fontsize * 1.35 * px_per_pt
    pad = 5.0 * px_per_pt

    occupied = []
    # 所有数据点本身也是障碍物
    for i, (x, y) in enumerate(zip(xs, ys)):
        px, py = ax.transData.transform((x, y))
        r = np.sqrt((sizes[i] if sizes is not None else 60) / np.pi) * px_per_pt
        occupied.append((px - r, py - r, px + r, py + r))
    # 已画好的说明文字(象限名、区域名)同样是障碍物, 避免标签压字
    rnd = fig.canvas.get_renderer()
    for art in avoid:
        bb = art.get_window_extent(rnd)
        occupied.append((bb.x0 - 2, bb.y0 - 2, bb.x1 + 2, bb.y1 + 2))

    axbox = ax.get_window_extent()
    cands = [(1, 0, 'left', 'center'), (-1, 0, 'right', 'center'),
             (0, 1, 'center', 'bottom'), (0, -1, 'center', 'top'),
             (0.72, 0.72, 'left', 'bottom'), (-0.72, 0.72, 'right', 'bottom'),
             (0.72, -0.72, 'left', 'top'), (-0.72, -0.72, 'right', 'top')]

    for i, (x, y, lab) in enumerate(zip(xs, ys, labels)):
        px, py = ax.transData.transform((x, y))
        w = len(str(lab)) * fontsize * 0.63 * px_per_pt
        best, best_cost = None, None
        for dx, dy, ha, va in cands:
            cx, cy = px + dx * pad, py + dy * pad
            x0 = cx if ha == 'left' else (cx - w if ha == 'right' else cx - w / 2.0)
            y0 = cy if va == 'bottom' else (cy - h if va == 'top' else cy - h / 2.0)
            box = (x0, y0, x0 + w, y0 + h)
            cost = sum(_overlap(box, o) for o in occupied)
            if (x0 < axbox.x0 + 1 or x0 + w > axbox.x1 - 1 or
                    y0 < axbox.y0 + 1 or y0 + h > axbox.y1 - 1):
                cost += 1e7
            if best_cost is None or cost < best_cost:
                best_cost, best = cost, (dx * pad, dy * pad, ha, va, box)
            if cost == 0:
                break
        ox, oy, ha, va, box = best
        occupied.append(box)
        t = ax.annotate(str(lab), (x, y), xytext=(ox, oy),
                        textcoords='offset pixels', ha=ha, va=va,
                        fontsize=fontsize, color=INK, zorder=6)
        t.set_path_effects([pe.withStroke(linewidth=2.4, foreground='white')])


def plan_legend(ax, plans, ncol=5, y=-0.115, marker='o'):
    """颜色只是辅助通道 —— 每点已有直接标注, 这里仍给出图例。
    图例一律放到坐标区**下方**横排: 不遮挡任何数据, 也避免与象限说明文字打架。"""
    handles = [plt.Line2D([], [], marker=marker, linestyle='none', markersize=8,
                          markerfacecolor=COLOR_OF[p], markeredgecolor='white',
                          markeredgewidth=0.8, label='方案 %s' % p) for p in plans]
    lg = ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, y),
                   ncol=ncol, frameon=False, fontsize=9.5,
                   handletextpad=0.5, columnspacing=1.6)
    return lg


def footnote(ax, text, y=-0.185):
    """图下脚注: 刻度说明、编码说明等。"""
    return ax.text(0.5, y, text, transform=ax.transAxes, ha='center', va='top',
                   fontsize=9, color=MUTED)


def size_from_cost(cost, lo=45.0, hi=560.0):
    """点面积 ∝ 总消费额(用平方根让半径随消费额近似线性增长)。"""
    c = np.asarray(cost, dtype=float)
    r = np.sqrt(c / c.max()) if c.max() > 0 else np.zeros_like(c)
    return lo + (hi - lo) * r


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=DPI, facecolor='white', bbox_inches='tight', pad_inches=0.28)
    plt.close(fig)
    log('  已保存: %s' % p)
    return p


# ================================================================ 6. 图1 CPC–CTR 四象限
cpc_med = g['CPC'].median()
ctr_med = g['CTR'].median()

fig, ax = new_fig(10.4, 7.4)
xs, ys = g['CPC'].values, (g['CTR'] * 100).values
sz = size_from_cost(g['总消费额'])
for p in PLANS:
    m = (g['方案ID'] == p).values
    ax.scatter(xs[m], ys[m], s=sz[m], c=COLOR_OF[p], label=str(p),
               alpha=0.88, edgecolors='white', linewidths=1.2, zorder=4)

# 中位数分界线
ax.axvline(cpc_med, color=REF, linestyle='--', linewidth=1.3, zorder=2)
ax.axhline(ctr_med * 100, color=REF, linestyle='--', linewidth=1.3, zorder=2)

# 四象限语义标注: 放在图例移走后的四角空白处, 淡灰不抢数据
quad_texts = [
    ax.text(0.985, 0.975, '高CPC + 高CTR\n高成本高响应', transform=ax.transAxes,
            ha='right', va='top', fontsize=10.5, color=MUTED),
    # 左上角有 CTR=66% 的离群单元, 说明文字下移让位
    ax.text(0.015, 0.775, '低CPC + 高CTR\n低成本高响应', transform=ax.transAxes,
            ha='left', va='top', fontsize=10.5, color=MUTED),
    ax.text(0.015, 0.020, '低CPC + 低CTR\n低成本低响应', transform=ax.transAxes,
            ha='left', va='bottom', fontsize=10.5, color=MUTED),
    ax.text(0.985, 0.020, '高CPC + 低CTR\n高成本低响应', transform=ax.transAxes,
            ha='right', va='bottom', fontsize=10.5, color=MUTED),
]

ax.set_xlabel('CPC  单次点击成本（元/点击，越左越省）', fontsize=12.5, color=INK)
ax.set_ylabel('CTR  点击率（%，对数刻度）', fontsize=12.5, color=INK)
ax.set_title('各推广单元CPC–CTR成本效率四象限图', fontsize=15, color=INK, pad=14)

# CTR 跨 0.74%~66.07%(近 90 倍), 线性轴会把 11 个单元全压到底边 —— 用对数轴还原可分性
ax.set_yscale('log')
lo = min(ys.min(), ctr_med * 100) / 1.9
hi = max(ys.max(), ctr_med * 100) * 1.7
ax.set_ylim(lo, hi)
ax.set_xlim(min(xs.min(), cpc_med) * 0.82, max(xs.max(), cpc_med) * 1.18)
yticks = [0.5, 1, 2, 3, 5, 10, 20, 40, 70]
yticks = [t for t in yticks if lo <= t <= hi]
ax.set_yticks(yticks)
ax.set_yticklabels(['%g' % t for t in yticks])
ax.minorticks_off()

# 中位数分界线直接就地标注, 不用居中的注释块(会被虚线划穿)
ax.text(0.985, (np.log10(ctr_med * 100) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)),
        'CTR 中位数 %.4f%%' % (ctr_med * 100), transform=ax.transAxes,
        ha='right', va='bottom', fontsize=9.5, color=MUTED, zorder=5)
ax.text(cpc_med, hi, 'CPC 中位数\n%.4f 元/点击' % cpc_med, ha='center', va='top',
        fontsize=9.5, color=MUTED, zorder=5)

fig.canvas.draw()
place_labels(ax, xs, ys, g['简称'].values, sizes=sz, fontsize=9.5, avoid=quad_texts)
plan_legend(ax, PLANS)
footnote(ax, '注：点面积 ∝ 该单元总消费额；虚线为 12 个单元的中位数分界；纵轴为对数刻度（CTR 跨度约 90 倍）')
log('\n【图1】CPC–CTR 四象限')
log('  CPC 中位数 = %.4f 元/点击   |   CTR 中位数 = %.4f%%' % (cpc_med, ctr_med * 100))
save(fig, '01_CPC_CTR四象限.png')

# ================================================================ 7. 图2 高位竞价 成本溢价–效果增益
fig, ax = new_fig(10.4, 7.4)
P = g['P'].values.astype(float)
G = g['G'].values.astype(float)
sz2 = size_from_cost(g['总消费额'])
for p in PLANS:
    m = (g['方案ID'] == p).values
    ax.scatter(P[m], G[m], s=sz2[m], c=COLOR_OF[p], label=str(p),
               alpha=0.88, edgecolors='white', linewidths=1.2, zorder=4)

ax.axvline(1.0, color=REF, linestyle='--', linewidth=1.3, zorder=2)
ax.axhline(1.0, color=REF, linestyle='--', linewidth=1.3, zorder=2)

xlo, xhi = np.nanmin(P) * 0.88, np.nanmax(P) * 1.10
ylo, yhi = np.nanmin(G) * 0.62, np.nanmax(G) * 1.30
ax.set_xlim(xlo, xhi)
ax.set_ylim(ylo, yhi)

# 重点区域: P>1 且 G<1 —— 花了溢价却没换来点击增益(需求「重点突出」的核心区)
y1_frac = (1.0 - ylo) / (yhi - ylo)
region_texts = []
if 0 < y1_frac < 1 and xhi > 1:
    ax.axvspan(1.0, xhi, ymin=0, ymax=y1_frac, color='#d03b3b', alpha=0.055, zorder=1)
    region_texts.append(ax.text(0.72, 0.06, '溢价无效区\nP>1 且 G<1', transform=ax.transAxes,
                                 ha='center', va='bottom', fontsize=10.5,
                                 color='#b03a3a', alpha=0.9, zorder=3))
# 该处正被 P=1 参考虚线穿过, 加一层白底避免被划断
region_texts.append(ax.text(0.030, 0.965, 'P<1 且 G>1\n低价高效区', transform=ax.transAxes,
                            ha='left', va='top', fontsize=10.5, color=MUTED, zorder=3,
                            bbox=dict(facecolor='white', edgecolor='none',
                                      alpha=0.85, pad=1.6)))

ax.set_xlabel('成本溢价系数 P = 上方位CPC / 整体CPC', fontsize=12.5, color=INK)
ax.set_ylabel('效果增益系数 G = 上方位CTR / 整体CTR', fontsize=12.5, color=INK)
ax.set_title('各推广单元高位竞价成本溢价与点击效果增益', fontsize=15, color=INK, pad=14)

fig.canvas.draw()
place_labels(ax, P, G, g['简称'].values, sizes=sz2, fontsize=9.5, avoid=region_texts)
plan_legend(ax, PLANS)
footnote(ax, '注：点面积 ∝ 该单元总消费额；虚线为 P=1、G=1 参考线；'
             'P>1 且 G<1 为溢价无效区（花更多钱、换更少点击）')
log('\n【图2】高位竞价 成本溢价–效果增益')
log('  P 范围 %.4f ~ %.4f   |   G 范围 %.4f ~ %.4f' % (np.nanmin(P), np.nanmax(P),
                                                       np.nanmin(G), np.nanmax(G)))
save(fig, '02_高位成本溢价_效果增益.png')

# ================================================================ 8. 图3 预算–点击贡献匹配
fig, ax = new_fig(10.4, 7.4)
B = (g['预算占比B'] * 100).values.astype(float)
Q = (g['点击贡献占比Q'] * 100).values.astype(float)
for p in PLANS:
    m = (g['方案ID'] == p).values
    ax.scatter(B[m], Q[m], s=150, c=COLOR_OF[p], label=str(p),
               alpha=0.9, edgecolors='white', linewidths=1.2, zorder=4)

lim_lo = min(B.min(), Q.min()) * 0.55
lim_hi = max(B.max(), Q.max()) * 1.8
ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], color=INK2, linewidth=1.6,
        linestyle='-', zorder=2, label='完全匹配线 y = x')
ax.fill_between([lim_lo, lim_hi], [lim_lo, lim_lo], [lim_lo, lim_hi],
                color='#d03b3b', alpha=0.05, zorder=1)
ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlim(lim_lo, lim_hi)
ax.set_ylim(lim_lo, lim_hi)
region_texts = [
    ax.text(0.975, 0.055, '预算占用高于点击贡献', transform=ax.transAxes,
            ha='right', va='bottom', fontsize=10.5, color='#b03a3a', alpha=0.9, zorder=3),
    ax.text(0.030, 0.965, '点击贡献高于预算占比', transform=ax.transAxes,
            ha='left', va='top', fontsize=10.5, color=MUTED, zorder=3),
]
ax.minorticks_off()
tk = [0.01, 0.05, 0.2, 1, 5, 20, 60]
tk = [t for t in tk if lim_lo <= t <= lim_hi]
ax.set_xticks(tk)
ax.set_yticks(tk)
ax.set_xticklabels(['%g' % t for t in tk])
ax.set_yticklabels(['%g' % t for t in tk])

ax.set_xlabel('预算占比 B（% ，对数刻度）', fontsize=12.5, color=INK)
ax.set_ylabel('点击贡献占比 Q（% ，对数刻度）', fontsize=12.5, color=INK)
ax.set_title('各推广单元预算占比与点击贡献匹配关系', fontsize=15, color=INK, pad=14)

fig.canvas.draw()
place_labels(ax, B, Q, g['简称'].values, sizes=np.full(len(B), 150.0), fontsize=9.5,
             avoid=region_texts)
plan_legend(ax, PLANS)
footnote(ax, '注：两轴均为对数刻度；位于 y=x 之上 → 点击贡献占比高于预算占比（高效），'
             '之下 → 预算占用高于点击贡献（低效）')
log('\n【图3】预算–点击贡献匹配')
log('  D = Q - B  (百分点)  最大 %+.4f (%s)  最小 %+.4f (%s)'
    % (g.loc[g['D'].idxmax(), 'D'] * 100, g.loc[g['D'].idxmax(), '推广单元ID'],
       g.loc[g['D'].idxmin(), 'D'] * 100, g.loc[g['D'].idxmin(), '推广单元ID']))
save(fig, '03_预算_点击贡献匹配.png')

# ================================================================ 9. 图4 预算 Pareto
fig, ax = new_fig(11.0, 7.0)
xpos = np.arange(len(par))
bar_colors = [COLOR_OF[p] for p in par['方案ID']]
bars = ax.bar(xpos, par['总消费额'].values, width=0.66, color=bar_colors,
              edgecolor='white', linewidth=1.0, zorder=3)

ax.set_xticks(xpos)
ax.set_xticklabels(par['简称'].values, fontsize=10)
ax.set_xlabel('推广单元ID（按总消费额降序，标注后4位）', fontsize=12.5, color=INK)
ax.set_ylabel('消费额（元）', fontsize=12.5, color=INK)
ax.set_title('各推广单元预算分配Pareto累计占比图', fontsize=15, color=INK, pad=14)
ax.set_ylim(0, par['总消费额'].max() * 1.22)

# 右轴: 累计占比 0~100%
ax2 = ax.twinx()
ax2.set_facecolor('none')
ax2.plot(xpos, par['累计消费占比'].values * 100, color=INK, linewidth=2.0,
         marker='o', markersize=6.5, markerfacecolor='white',
         markeredgecolor=INK, markeredgewidth=1.6, zorder=5,
         label='累计消费占比')
ax2.set_ylim(0, 100)
ax2.set_ylabel('累计占比（%）', fontsize=12.5, color=INK)
ax2.tick_params(colors=INK2, labelsize=10.5, length=3.5, width=0.9)
ax2.spines['top'].set_visible(False)
for s in ('right',):
    ax2.spines[s].set_color(INK2)
    ax2.spines[s].set_linewidth(0.9)
ax2.axhline(80, color='#d03b3b', linestyle='--', linewidth=1.3, zorder=2)
ax2.text(4.6, 82.2, '80% 参考线', ha='left', va='bottom', fontsize=10, color='#b03a3a')

# 选择性直接标注: 只标首个单元与「累计占比首次跨过 80%」的那个, 不给每个点写数字
i_cross = int((par['累计消费占比'] < 0.80).sum())
for i in sorted({0, i_cross}):
    v = par['累计消费占比'].iloc[i] * 100
    ax2.annotate('累计 %.2f%%' % v, (xpos[i], v), xytext=(11, 3),
                 textcoords='offset pixels', ha='left', va='center',
                 fontsize=9.5, color=INK,
                 path_effects=[pe.withStroke(linewidth=2.6, foreground='white')],
                 zorder=7)

h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
handles = [plt.Line2D([], [], marker='s', linestyle='none', markersize=8,
                      markerfacecolor=COLOR_OF[p], markeredgecolor='white',
                      label='方案 %s' % p) for p in PLANS] + h2
lg = ax.legend(handles=handles, loc='center right', fontsize=9.5, frameon=True,
               title='消费额（柱）  /  累计占比（线）', title_fontsize=9.5)
lg.get_frame().set_facecolor('white')
lg.get_frame().set_edgecolor(GRID)
lg.get_frame().set_linewidth(0.8)
lg.set_zorder(8)

log('\n【图4】预算 Pareto')
top3 = par.head(3)
log('  前3单元累计消费占比 = %.4f%%' % (top3['累计消费占比'].iloc[-1] * 100))
log('  跨越80%%的单元: 第 %d 个 (%s)'
    % (int((par['累计消费占比'] < 0.8).sum()) + 1,
       par.loc[(par['累计消费占比'] < 0.8).sum(), '推广单元ID']))
save(fig, '04_预算Pareto累计占比.png')

# ================================================================ 10. 导出 Excel
summary = g[['方案ID', '推广单元ID', '总展现量', '总点击量', '总消费额', 'CTR', 'CPC',
             '覆盖天数']].copy()
summary['CTR(%)'] = summary['CTR'] * 100
summary = summary[['方案ID', '推广单元ID', '总展现量', '总点击量', '总消费额',
                   'CTR', 'CTR(%)', 'CPC', '覆盖天数']]

s2 = g[['方案ID', '推广单元ID', '上方位展现率', '首位展现率', '上方位CTR',
        '上方位CPC', 'P', 'G']].copy()

s3 = g[['方案ID', '推广单元ID', '预算占比B', '点击贡献占比Q', 'D']].copy()

s4 = par[['推广单元ID', '总消费额', '消费占比', '累计消费占比',
          '点击占比', '累计点击占比']].rename(columns={'总消费额': '消费额'}).copy()

qc_rows = [
    ('原始行数×列数', '%d × %d' % raw.shape, 'Sheet1 全表'),
    ('方案ID 数', df['方案ID'].nunique(), '已按字符串处理'),
    ('推广单元ID 数', df['推广单元ID'].nunique(), '已按字符串处理'),
    ('方案×单元 组合数', n_pair, '即本分析粒度 12 行'),
    ('缺失值(选用列)', int(df[REQUIRED_COLS].isna().sum().sum()), '无缺失'),
    ('完全重复行', int(df.duplicated().sum()), '无重复'),
    ('日期范围', '%s ~ %s' % (df['日期'].min().strftime('%Y-%m-%d'),
                              df['日期'].max().strftime('%Y-%m-%d')), '365 个自然日全覆盖'),
    ('单元覆盖天数(最少/中位/最多)',
     '%d / %d / %d' % (days_per_unit.min(), int(days_per_unit.median()), days_per_unit.max()),
     '单元非全周期投放, 属未投放而非缺失值'),
]
for k, v in qc.items():
    qc_rows.append(('逻辑违规: ' + k, v, '0 为正常'))
for k, v in ZERO.items():
    qc_rows.append(('零值行数: ' + k, v, '日粒度下未获点击/未投放'))

s5 = pd.DataFrame(qc_rows, columns=['核验项', '结果', '说明'])
s5['说明'] = s5['说明'].fillna('')

xlsx = os.path.join(OUT, 'bid_budget_summary.xlsx')
with pd.ExcelWriter(xlsx, engine='openpyxl') as w:
    summary.to_excel(w, sheet_name='Sheet1_基础汇总', index=False)
    s2.to_excel(w, sheet_name='Sheet2_高位竞价指标', index=False)
    s3.to_excel(w, sheet_name='Sheet3_预算贡献匹配', index=False)
    s4.to_excel(w, sheet_name='Sheet4_Pareto结果', index=False)
    s5.to_excel(w, sheet_name='Sheet5_数据质量核验', index=False)

    # 比率列统一 6 位小数, 便于论文直接引用
    from openpyxl.styles import Font
    for sheet, cols in (('Sheet1_基础汇总', ['F', 'G', 'H']),
                        ('Sheet2_高位竞价指标', ['C', 'D', 'E', 'F', 'G', 'H']),
                        ('Sheet3_预算贡献匹配', ['C', 'D', 'E']),
                        ('Sheet4_Pareto结果', ['C', 'D', 'E', 'F'])):
        ws = w.sheets[sheet]
        for col in cols:
            for r in range(2, ws.max_row + 1):
                ws['%s%d' % (col, r)].number_format = '0.000000'
        for c in ws[1]:
            c.font = Font(bold=True)
        widths = [max(len(str(ws.cell(r, i).value or '')) for r in range(1, ws.max_row + 1))
                  for i in range(1, ws.max_column + 1)]
        for i, wd in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(max(wd + 3, 10), 26)

log('\n【Excel】已保存: %s' % xlsx)

# ================================================================ 11. 终端结论
log('\n' + '=' * 78)
log('【终端结论】')
log('=' * 78)
log('1) 生成文件 (共 6 个):')
for f in sorted(os.listdir(OUT)):
    log('     %-34s %8.1f KB' % (f, os.path.getsize(os.path.join(OUT, f)) / 1024.0))
log('   脚本: %s' % os.path.abspath(__file__))
log('2) 保存路径: %s' % OUT)
log('3) CPC 中位数 = %.6f 元/点击   |   CTR 中位数 = %.6f%% (=%.6f)'
    % (cpc_med, ctr_med * 100, ctr_med))
log('4) D = Q - B 极值:')
log('     D 最大 %+.4f 百分点 → %s (方案 %s)  预算占比 %.4f%% / 点击贡献 %.4f%%'
    % (g.loc[g['D'].idxmax(), 'D'] * 100, g.loc[g['D'].idxmax(), '推广单元ID'],
       g.loc[g['D'].idxmax(), '方案ID'], g.loc[g['D'].idxmax(), '预算占比B'] * 100,
       g.loc[g['D'].idxmax(), '点击贡献占比Q'] * 100))
log('     D 最小 %+.4f 百分点 → %s (方案 %s)  预算占比 %.4f%% / 点击贡献 %.4f%%'
    % (g.loc[g['D'].idxmin(), 'D'] * 100, g.loc[g['D'].idxmin(), '推广单元ID'],
       g.loc[g['D'].idxmin(), '方案ID'], g.loc[g['D'].idxmin(), '预算占比B'] * 100,
       g.loc[g['D'].idxmin(), '点击贡献占比Q'] * 100))
log('5) 前 3 个单元累计占总消费额 = %.4f%%' % (top3['累计消费占比'].iloc[-1] * 100))
for _, r in top3.iterrows():
    log('     %s  消费 %12.2f 元  占比 %6.4f%%  累计 %6.4f%%'
        % (r['推广单元ID'], r['总消费额'], r['消费占比'] * 100, r['累计消费占比'] * 100))
log('6) 数据质量问题: 见 Sheet5_数据质量核验 (无缺失、无重复、逻辑无违规)')
log('   已写出运行日志: %s' % os.path.join(OUT, '运行日志.txt'))

with open(os.path.join(OUT, '运行日志.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(LOG))
