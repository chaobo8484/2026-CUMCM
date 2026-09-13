# -*- coding: utf-8 -*-
"""
广告关键词级描述统计与质量筛查（修订版）
================================================================
数据源: ../../clean_data/clean_data.xlsx「关键词」sheet (2227 行)

【修订说明 v2】
v1 曾用"跳出率非空且非0"过滤, 同时误删了两类词:
  ① 890 条零点击词(跳出率为 NaN) ② 124 条跳出率=0 的高质量词。
本版不再删行, 改为"分层 + 打标":
  * 词库全景 : 全部 2227 条(未启用 890 / 活跃 1337);
  * 质量指标 : 只用活跃 1337 条(含 124 条零跳出、403 条点击超浏览);
  * 异常标记 : 未启用词 / 零跳出 / 点击超浏览(V<K)。

【数据边界】
该表是「关键词 × 推广单元」横截面快照: 无日期(不可做月度)、无展现量(不可算 CTR);
「平均停留秒」已是整数秒。故只做 描述统计 + 消费集中度 + 数据质量筛查。

输出: charts_Q1/ 下 5 张 300dpi PNG + data_Q1/ 下 6 张 CSV
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, '..', '..', 'clean_data', 'clean_data.xlsx'))
OUT_FIG = os.path.join(BASE, "..", "charts_Q1")
OUT_DAT = os.path.join(BASE, "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

CORE_COVERAGE = 0.95
CPC_LIMIT = 10.0

C_BLUE, C_ORANGE = '#2a78d6', '#eb6834'
C_GREEN, C_CRIT = '#1baf7a', '#d03b3b'
C_GREY, C_GRID, C_AXIS = '#9a9890', '#e1e0d9', '#c3c2b7'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#898781'
SURFACE = '#ffffff'


def set_cjk_font():
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ['Microsoft YaHei', 'SimHei', 'SimSun', 'Noto Sans CJK SC',
                 'Source Han Sans SC', 'PingFang SC', 'WenQuanYi Micro Hei']:
        if name in have:
            plt.rcParams['font.sans-serif'] = [name]
            plt.rcParams['axes.unicode_minus'] = False
            print('中文字体 -> %s' % name)
            return name
    raise RuntimeError('未找到可用中文字体')


def style_ax(ax, grid_axis='y'):
    ax.set_facecolor(SURFACE)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(C_AXIS)
        ax.spines[s].set_linewidth(0.8)
    ax.grid(True, axis=grid_axis, color=C_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9, length=3, width=0.8)


def save(fig, name):
    import time
    p = os.path.join(OUT_FIG, name)
    for k in range(6):
        try:
            fig.savefig(p, dpi=300, bbox_inches='tight', facecolor=SURFACE)
            break
        except OSError:
            if k == 5:
                raise
            time.sleep(0.4)
    plt.close(fig)
    print('  已保存 -> %s' % name)


set_cjk_font()

# ============================================================ 1. 读取与分层
raw = pd.read_excel(SRC, sheet_name='关键词')
print('\nclean 关键词 sheet: %d 行 × %d 列 (词库全景)' % raw.shape)
NUM = ['消费额', '点击量', '浏览量', '跳出率', '平均停留秒', 'CPC', '浏览深度']
for c in NUM:
    raw[c] = pd.to_numeric(raw[c], errors='coerce')

raw['未启用词'] = raw['点击量'] <= 0
raw['零跳出'] = (raw['点击量'] > 0) & (raw['跳出率'] <= 0)
raw['点击超浏览'] = (raw['点击量'] > 0) & (raw['浏览量'] < raw['点击量'])

df = raw[raw['点击量'] > 0].reset_index(drop=True)     # 质量分析样本 = 活跃 1337
TOTAL = raw['消费额'].sum()
print('词库全景: %d 条 (未启用 %d + 活跃 %d)' % (len(raw), int(raw['未启用词'].sum()), len(df)))
print('活跃样本: %d 条, 零跳出 %d, 点击超浏览 %d' % (len(df), int(df['零跳出'].sum()), int(df['点击超浏览'].sum())))
print('总消费额 = %.2f 元 (未启用词消费 %.2f)' % (TOTAL, raw.loc[raw['未启用词'], '消费额'].sum()))

# ============================================================ 2. 数据质量体检（全库）
rows = []


def chk(name, mask, note, scope='全库'):
    base = raw if scope == '全库' else df
    assert mask.index.equals(base.index), '掩码与样本索引不一致'
    rows.append({'范围': scope, '检查项': name, '命中行数': int(mask.sum()),
                 '行数占比': '%.1f%%' % (100 * mask.mean()),
                 '涉及消费额': '%.2f' % base.loc[mask, '消费额'].sum(),
                 '消费占比': '%.2f%%' % (100 * base.loc[mask, '消费额'].sum() / TOTAL),
                 '说明': note})


chk('未启用词(点击=0, 消费=0)', raw['未启用词'], '词库配置冗余, 全年无点击无消费', '全库')
chk('零跳出(跳出率=0)', df['零跳出'], '留存最好的词, v1 曾被误删', '活跃')
chk('点击超浏览(浏览量<点击量)', df['点击超浏览'], '点了却未进站/未加载, 浏览深度<1; 不可截断/删除', '活跃')
chk('浏览量 = 0 且 点击 > 0', df['浏览量'] == 0, '点击超浏览的极端情形', '活跃')
chk('跳出率 = 100%', df['跳出率'] >= 1.0, '全部访问均单页跳出', '活跃')
chk('平均停留 ≤ 5 秒', df['平均停留秒'] <= 5, '停留极短, 疑似无效流量', '活跃')
chk('CPC > %.0f 元' % CPC_LIMIT, df['CPC'] > CPC_LIMIT, '单次点击成本异常偏高', '活跃')
chk('关键词ID 重复(跨单元)', df.duplicated('关键词ID', keep=False), '同词多个单元, 按行汇总会重复计数', '活跃')

qc = pd.DataFrame(rows)
qc.to_csv(os.path.join(OUT_DAT, '表2_数据质量体检.csv'), index=False, encoding='utf-8-sig')
print('\n===== 表2 数据质量体检 =====')
print(qc.to_string(index=False))

# ============================================================ 3. 描述统计（活跃）
desc = df[NUM].describe(percentiles=[.05, .25, .5, .75, .95]).T
desc['偏度'] = df[NUM].skew()
desc['变异系数'] = df[NUM].std() / df[NUM].mean()
desc = desc[['count', 'mean', 'std', 'min', '5%', '25%', '50%', '75%', '95%', 'max', '偏度', '变异系数']]
desc.columns = ['样本数', '均值', '标准差', '最小值', 'P5', 'P25', '中位数', 'P75', 'P95', '最大值', '偏度', '变异系数']
desc.index.name = '指标'
desc.round(4).to_csv(os.path.join(OUT_DAT, '表1_描述统计.csv'), encoding='utf-8-sig')
print('\n===== 表1 描述统计 (活跃 %d 条) =====' % len(df))
print(desc.round(3).to_string())

weight_cmp = []
for m in ['跳出率', '平均停留秒', 'CPC', '浏览深度']:
    s = df[m].mean()
    wc = np.average(df[m], weights=df['消费额'])
    wk = np.average(df[m], weights=df['点击量'])
    weight_cmp.append({'指标': m, '简单平均': s, '按消费额加权': wc, '按点击量加权': wk,
                       '消费加权相对偏差': (wc - s) / s, '点击加权相对偏差': (wk - s) / s})
pd.DataFrame(weight_cmp).round(4).to_csv(
    os.path.join(OUT_DAT, '表3_简单平均与加权平均对比.csv'), index=False, encoding='utf-8-sig')
print('\n===== 表3 简单平均 vs 加权平均 (活跃) =====')
print(pd.DataFrame(weight_cmp).round(4).to_string(index=False))

# ============================================================ 4. 消费集中度（词库全景 2227）
cost = raw['消费额'].sort_values(ascending=False).reset_index(drop=True)
cum = cost.cumsum() / TOTAL
n = len(cost); asc = cost.sort_values().values
gini = (2 * np.arange(1, n + 1) - n - 1).dot(asc) / (n * asc.sum())
share = {k: cum.iloc[k - 1] for k in (10, 30, 50, 100, 300)}
print('\n===== 消费集中度 (词库全景 %d) =====' % n)
print('基尼系数 = %.4f   (未启用词 %d 条消费=0)' % (gini, int(raw['未启用词'].sum())))
for k, v in share.items():
    print('  前%4d 个关键词累计消费 %.1f%%' % (k, v * 100))

# ============================================================ 5. 消费分层（活跃）
bins = [0, 1, 10, 100, 1000, np.inf]
labels = ['<1元', '1-10元', '10-100元', '100-1000元', '>1000元']
df = df.copy()
df['消费分层'] = pd.cut(df['消费额'], bins, labels=labels)
tier = df.groupby('消费分层', observed=True).agg(
    词数=('序号', 'size'), 消费额=('消费额', 'sum'),
    跳出率均值=('跳出率', 'mean'), 停留均值=('平均停留秒', 'mean'), CPC均值=('CPC', 'mean'))
tier['消费占比%'] = 100 * tier['消费额'] / TOTAL
tier.round(3).to_csv(os.path.join(OUT_DAT, '表4_消费分层质量对比.csv'), encoding='utf-8-sig')
print('\n===== 表4 消费分层与质量 (活跃) =====')
print(tier.round(3).to_string())
print('注: 未启用词 %d 条消费=0, 无质量数据, 未入分层。' % int(raw['未启用词'].sum()))

# ============================================================ 6. 核心词集筛查（活跃）
d = df.sort_values('消费额', ascending=False).reset_index(drop=True)
k_core = int((d['消费额'].cumsum() / TOTAL < CORE_COVERAGE).sum()) + 1
core = d.head(k_core).copy()
b_med, s_med = core['跳出率'].median(), core['平均停留秒'].median()
core['筛查结果'] = np.where((core['跳出率'] > b_med) & (core['平均停留秒'] < s_med),
                            '高消费低效', '正常')
risk = core['筛查结果'] == '高消费低效'
print('\n===== 核心词集筛查 =====')
print('核心词集 = 前 %d 个词, 合计消费 %.2f 元 (占总消费 %.2f%%)'
      % (k_core, core['消费额'].sum(), 100 * core['消费额'].sum() / TOTAL))
print('判为"高消费低效" 命中 %d 个词, 消费 %.2f 元 (占核心 %.2f%%, 占总消费 %.2f%%)'
      % (risk.sum(), core.loc[risk, '消费额'].sum(),
         100 * core.loc[risk, '消费额'].sum() / core['消费额'].sum(),
         100 * core.loc[risk, '消费额'].sum() / TOTAL))

cols = ['关键词ID', '方案ID', '推广单元ID', '消费额', '点击量', '浏览量',
        '跳出率', '平均停留秒', 'CPC', '浏览深度', '零跳出', '点击超浏览']
core.sort_values('消费额', ascending=False)[cols + ['筛查结果']].to_csv(
    os.path.join(OUT_DAT, '表5_核心词集与高消费低效词.csv'), index=False, encoding='utf-8-sig')
print('\n高消费低效词 Top10:')
print(core.loc[risk].sort_values('消费额', ascending=False)
      .head(10)[['关键词ID', '消费额', '点击量', '跳出率', '平均停留秒', 'CPC']].round(4).to_string(index=False))

cpc_bad = df.loc[df['CPC'] > CPC_LIMIT, cols].sort_values('CPC', ascending=False)
cpc_bad.to_csv(os.path.join(OUT_DAT, '表6_CPC异常关键词清单.csv'), index=False, encoding='utf-8-sig')
print('\n===== CPC 异常词 =====')
print('CPC > %.0f 元: %d 个词, 合计消费 %.2f 元 (占总消费 %.2f%%)'
      % (CPC_LIMIT, len(cpc_bad), cpc_bad['消费额'].sum(), 100 * cpc_bad['消费额'].sum() / TOTAL))

# ============================================================ 7. 出图
print('\n===== 出图 =====')


def clipped_hist(ax, s, bins, clip, xlabel, title):
    n_out = int((s > clip).sum())
    ax.hist(s[s <= clip], bins=bins, color=C_BLUE, alpha=0.85, edgecolor=SURFACE, linewidth=0.6, zorder=3)
    m = s.median()
    ax.axvline(m, color=INK2, linewidth=1.2, linestyle='--', zorder=4)
    ax.annotate('中位数 %.2f' % m, xy=(m, ax.get_ylim()[1]), xytext=(4, -12),
                textcoords='offset points', color=INK2, fontsize=8.5)
    if n_out:
        ax.annotate('%d 个值 > %g 未显示' % (n_out, clip), xy=(0.98, 0.92),
                    xycoords='axes fraction', ha='right', color=MUTED, fontsize=8)
    ax.set_xlabel(xlabel, color=INK2, fontsize=10)
    ax.set_ylabel('关键词数', color=INK2, fontsize=10)
    ax.set_title(title, color=INK, fontsize=11, pad=8)
    style_ax(ax, 'y')


fig, axes = plt.subplots(2, 2, figsize=(11, 7.4), facecolor=SURFACE)
clipped_hist(axes[0, 0], df['跳出率'], np.linspace(0, 1, 26), 1.0, '跳出率', '(a) 跳出率分布')
clipped_hist(axes[0, 1], df['平均停留秒'], np.arange(0, 610, 20), 600, '平均停留时长 (秒)', '(b) 平均停留时长分布')
valid_depth = df['浏览量'] >= df['点击量']
clipped_hist(axes[1, 0], df.loc[valid_depth, '浏览深度'], np.arange(0, 10.1, .25), 10,
             '浏览深度 (浏览量/点击量)', '(c) 浏览深度分布 (仅合法行)')
clipped_hist(axes[1, 1], df['CPC'], np.arange(0, 10.1, .2), 10, 'CPC (元)', '(d) 单次点击成本分布')
fig.suptitle('图1  核心指标的分布特征 (活跃词 n=%d；零跳出 124，点击超浏览 403 已保留)'
             % len(df), color=INK, fontsize=12, y=1.005)
fig.tight_layout()
save(fig, 'fig1_核心指标分布.png')

# ---- 图2 消费集中度（词库全景） ----
fig, ax = plt.subplots(figsize=(8.6, 5.2), facecolor=SURFACE)
rank = np.arange(1, len(cum) + 1)
ax.plot(rank, cum.values * 100, color=C_BLUE, linewidth=2, zorder=4)
ax.fill_between(rank, 0, cum.values * 100, color=C_BLUE, alpha=0.08, zorder=2)
ax.axhline(80, color=C_GRID, linewidth=1.2, linestyle='--', zorder=1)
ax.annotate('80% 消费线', xy=(1.05, 82), color=MUTED, fontsize=9)
for k_, v_ in share.items():
    ax.plot([k_], [v_ * 100], 'o', markersize=6, color=C_ORANGE,
            markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
    ax.annotate('前%d个词 %.1f%%' % (k_, v_ * 100), xy=(k_, v_ * 100),
                xytext=(7, -13), textcoords='offset points', color=INK2, fontsize=9)
ax.set_xscale('log')
ax.set_xlim(1, len(cum)); ax.set_ylim(0, 105)
ax.set_xticks([1, 10, 100, 1000]); ax.set_xticklabels(['1', '10', '100', '1000'])
ax.set_xlabel('关键词按消费额降序排名 (对数轴)', color=INK2, fontsize=10)
ax.set_ylabel('累计消费占比 (%)', color=INK2, fontsize=10)
ax.set_title('图2  消费额集中度 (词库全景 %d 条)\n基尼 %.4f；未启用词 %d 条零消费位于曲线末端'
             % (n, gini, int(raw['未启用词'].sum())), color=INK, fontsize=12, pad=10)
style_ax(ax, 'both')
save(fig, 'fig2_消费集中度.png')

# ---- 图3 消费分层与质量（活跃） ----
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), facecolor=SURFACE)
x = np.arange(len(tier))
for ax, col, color, ttl, ylab in [
        (axes[0], '跳出率均值', C_BLUE, '(a) 各消费层级的平均跳出率', '平均跳出率'),
        (axes[1], '停留均值', C_ORANGE, '(b) 各消费层级的平均停留时长', '平均停留时长 (秒)')]:
    ax.bar(x, tier[col].values, width=0.6, color=color, alpha=0.9, zorder=3)
    for i, v in enumerate(tier[col].values):
        ax.annotate('%.2f' % v if col == '跳出率均值' else '%.0f' % v,
                    xy=(i, v), xytext=(0, 4), textcoords='offset points', ha='center', color=INK2, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(tier.index, fontsize=9)
    ax.set_ylim(0, max(tier[col].max() * 1.22, 0.1))
    ax.set_ylabel(ylab, color=INK2, fontsize=10)
    ax.set_title(ttl, color=INK, fontsize=11, pad=8)
    style_ax(ax, 'y')
for i, (cnt, shr) in enumerate(zip(tier['词数'].values, tier['消费占比%'].values)):
    axes[0].annotate('%d词 / %.2f%%消费' % (cnt, shr), xy=(i, 0), xytext=(0, -32),
                     textcoords='offset points', ha='center', color=MUTED, fontsize=8.5)
axes[0].set_xlabel('消费额层级', color=INK2, fontsize=10, labelpad=30)
fig.suptitle('图3  消费额越高, 关键词质量越好 (高跳出词几乎不花钱)｜活跃词 %d 条' % len(df),
             color=INK, fontsize=12, y=1.03)
fig.tight_layout()
save(fig, 'fig3_消费分层与质量.png')

# ---- 图4 核心词集象限图 ----
fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
size = 20 + 1100 * (core['消费额'] / core['消费额'].max()) ** 0.5
ok = ~risk
ax.scatter(core.loc[ok, '跳出率'], core.loc[ok, '平均停留秒'], s=size[ok], color=C_BLUE,
           alpha=0.5, edgecolors='none', zorder=3, label='核心词集·正常 (%d个)' % ok.sum())
ax.scatter(core.loc[risk, '跳出率'], core.loc[risk, '平均停留秒'], s=size[risk], color=C_CRIT,
           alpha=0.9, edgecolors=SURFACE, linewidths=0.8, zorder=5,
           label='高消费低效 (%d个, %.2f万元)' % (risk.sum(), core.loc[risk, '消费额'].sum() / 1e4))
ax.axvline(b_med, color=C_AXIS, linewidth=1.1, linestyle='--', zorder=2)
ax.axhline(s_med, color=C_AXIS, linewidth=1.1, linestyle='--', zorder=2)
ax.annotate('组内跳出率中位 %.3f' % b_med, xy=(b_med, ax.get_ylim()[1]), xytext=(-6, -12),
            textcoords='offset points', ha='right', color=INK2, fontsize=9)
ax.annotate('组内停留中位 %.0f 秒' % s_med, xy=(ax.get_xlim()[1], s_med), xytext=(-6, 7),
            textcoords='offset points', ha='right', color=INK2, fontsize=9)
ax.annotate('低效区', xy=(1.0, 8), xytext=(-8, 0), textcoords='offset points', ha='right',
            va='bottom', color=C_CRIT, fontsize=11, alpha=0.55, fontweight='bold')
ax.set_xlim(0, 1.03); ax.set_ylim(0, core['平均停留秒'].max() * 1.1)
ax.set_xlabel('跳出率', color=INK2, fontsize=10)
ax.set_ylabel('平均停留时长 (秒)', color=INK2, fontsize=10)
ax.set_title('图4  核心词集(累计消费95%%, 共%d个词)的高消费低效词定位\n点面积 ∝ √消费额; 右下象限 = 跳出高 + 停留短' % k_core,
             color=INK, fontsize=12, pad=10)
ax.legend(frameon=False, fontsize=9.5, labelcolor=INK2, loc='upper right', markerscale=0.5)
style_ax(ax, 'both')
save(fig, 'fig4_高消费低效词象限图.png')

# ---- 图5 数据质量概览（重建） ----
n_inv = int(raw['未启用词'].sum()); n_act = len(df)
n_b0 = int(df['零跳出'].sum()); n_vk = int(df['点击超浏览'].sum())
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), facecolor=SURFACE)
# (a) 词库全景（互斥两类）
y = np.array([1, 0])
ax = axes[0]
vals = [n_inv, n_act]
cols_ = [C_GREY, C_BLUE]
names = ['未启用词\n(点击=0, 消费=0)', '活跃词\n(点击>0)']
ax.barh(y, vals, height=0.5, color=cols_, alpha=0.92, zorder=3)
for i, (v, yy) in enumerate(zip(vals, y)):
    ax.annotate('%d 条 (%.1f%%)' % (v, 100 * v / (n_inv + n_act)), xy=(v, yy), xytext=(6, 0),
                textcoords='offset points', va='center', color=INK2, fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9.5)
ax.set_xlim(0, max(vals) * 1.35)
ax.set_xlabel('关键词记录数 (条)', color=INK2, fontsize=10)
ax.set_title('(a) 词库全景：%d 条 = 未启用 + 活跃' % (n_inv + n_act), color=INK, fontsize=11, pad=8)
style_ax(ax, 'x')
# (b) 活跃词的标记率（可重叠）
ax = axes[1]
labs = ['零跳出\n(跳出率=0)', '点击超浏览\n(浏览量<点击量)']
vs = [n_b0, n_vk]
ax.barh([1, 0], vs, height=0.5, color=[C_GREEN, C_ORANGE], alpha=0.92, zorder=3)
for v, yy in zip(vs, [1, 0]):
    ax.annotate('%d 条 (占活跃 %.1f%%)' % (v, 100 * v / n_act), xy=(v, yy), xytext=(6, 0),
                textcoords='offset points', va='center', color=INK2, fontsize=10)
ax.set_yticks([1, 0]); ax.set_yticklabels(labs, fontsize=9.5)
ax.set_xlim(0, max(vs) * 1.45)
ax.set_xlabel('活跃词中的标记条数 (条)', color=INK2, fontsize=10)
ax.set_title('(b) 活跃词异常标记（可重叠）', color=INK, fontsize=11, pad=8)
style_ax(ax, 'x')
fig.suptitle('图5  数据质量概览（修订：v1 误删的零跳出与零点击词已恢复）', color=INK, fontsize=12, y=1.02)
fig.tight_layout()
save(fig, 'fig5_数据质量概览.png')

print('\n全部完成, 结果见 charts_Q1/ 与 data_Q1/ 目录。')
