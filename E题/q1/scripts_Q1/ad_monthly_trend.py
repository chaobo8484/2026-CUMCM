# -*- coding: utf-8 -*-
"""
广告设计质量与创意的月度变化趋势分析
================================================================
数据源: ../题目/附件/附件1.xlsx

【Sheet 结构核验结果(实测, 非假设)】
  Sheet1  日期 × 方案ID × 推广单元ID   2627 行 × 10 列
          字段: 日期, 方案ID, 推广单元ID, 展现量, 点击量, 消费额,
                上方位展现量, 上方首位展现量, 上方位点击量, 上方位消费额
          日期范围 2025-01-01 ~ 2025-12-31, 365 个自然日全覆盖  → 真·日粒度时序
  Sheet2  日期 × 新注册数              365 行 × 2 列
  Sheet3  序号, 关键词, 方案ID, 推广单元ID, 消费额, 点击量, 浏览量,
          跳出率, 平均访问时长        2227 行 × 9 列
          ** 无日期列 **, 粒度是「关键词 × 推广单元」的横截面快照

【关键结论: 为什么本脚本不用 跳出率 / 平均访问时长】
  实测 Sheet3 按单元汇总的点击量, 与 Sheet1 全年按单元汇总的点击量
  逐单元完全相等(12/12 个单元比值均为 1.0), 证明 Sheet3 是**整年快照**,
  不是任何单个时点的切片。它没有月份维度, 因此:
      - 跳出率      → 无法拆到月, 只能得到 12 个相同的全年常数
      - 平均访问时长 → 同上
  两者若强行入模, 在 12 个月上零方差, 熵权法权重必然退化为 0,
  既不产生信息, 也无法在论文中解释。故本脚本将其剔除, 并在
  第 0 节用可复现的检验把这一限制固化下来(供论文"数据说明"引用)。

  注意: Sheet1 与 Sheet3 的方案ID/推广单元ID 是同一套(5 个方案, 12 个单元),
  只是 Sheet3 少了时间维度 —— 属于"缺一个维度", 不是"粒度粗细不同",
  因此无法靠重采样或分组聚合补齐。

【据此确定的评价体系(全部来自 Sheet1, 均为真实月度值)】
  CTR        = Σ点击量 / Σ展现量            正向  创意吸引力
  上方位CTR   = Σ上方位点击量 / Σ上方位展现量  正向  优质位置上的创意吸引力
  CPC        = Σ消费额 / Σ点击量            负向  流量获取效率
  (CTR 为核心指标; 后两者是为使综合评分不退化为恒等变换而引入的真实月度字段)

【可比性处理(对应要求 5)】
  12 个月 × 3 指标的矩阵上 **一次性** 完成:
  同向化 → 全局 Min-Max(分子分母都是全部 12 个月的极差) →
  一套熵权 → 一组正/负理想解。
  绝不对每个月单独重算一套标准。

输出: output/ 下 3 张 300dpi PNG + 3 张 CSV
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- 路径
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, "..", "..", "题目", "附件", "附件1.xlsx"))
OUT_FIG = os.path.join(BASE, "..", "charts_Q1")
OUT_DAT = os.path.join(BASE, "..", "data_Q1")
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_DAT, exist_ok=True)

# ---------------------------------------------------------------- 配色
C_BLUE, C_ORANGE, C_GREEN = '#2a78d6', '#eb6834', '#3f8f5b'
C_MAX, C_MIN = '#d03b3b', '#6b7280'
C_GRID, C_AXIS = '#e1e0d9', '#c3c2b7'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#898781'
SURFACE = '#ffffff'

MONTH_LABELS = ['%d月' % m for m in range(1, 13)]


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
    raise RuntimeError('未找到可用中文字体, 请安装 SimHei 或 Microsoft YaHei')


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
    p = os.path.join(OUT_FIG, name)
    fig.savefig(p, dpi=300, bbox_inches='tight', facecolor=SURFACE)
    plt.close(fig)
    print('  已保存 -> %s' % name)


set_cjk_font()

# ============================================================ 0. 读取 + 结构核验
print('\n' + '=' * 70)
print('0. 读取数据并核验 Sheet 结构')
print('=' * 70)

if not os.path.exists(SRC):
    raise FileNotFoundError('找不到数据文件: %s' % SRC)

xl = pd.ExcelFile(SRC)
print('Sheet 列表: %s' % xl.sheet_names)
for sn in xl.sheet_names:
    _d = pd.read_excel(SRC, sheet_name=sn, nrows=0)
    _n = len(pd.read_excel(SRC, sheet_name=sn))
    print('  %-8s %5d 行 × %2d 列 | %s' % (sn, _n, len(_d.columns), ', '.join(_d.columns)))

s1 = pd.read_excel(SRC, sheet_name='Sheet1')

# 字段存在性断言 —— 后面所有代码只依赖这些真实列名
NEED = ['日期', '方案ID', '推广单元ID', '展现量', '点击量', '消费额',
        '上方位展现量', '上方首位展现量', '上方位点击量', '上方位消费额']
missing = [c for c in NEED if c not in s1.columns]
if missing:
    raise KeyError('Sheet1 缺少预期字段: %s (实际字段: %s)' % (missing, list(s1.columns)))

s1['日期'] = pd.to_datetime(s1['日期'], errors='coerce')
for c in NEED[1:]:
    s1[c] = pd.to_numeric(s1[c], errors='coerce')
if s1[NEED].isna().any().any():
    raise ValueError('Sheet1 存在无法解析的空值或非数值:\n%s' % s1[NEED].isna().sum())

print('\nSheet1 日期范围: %s ~ %s (共 %d 个自然日)'
      % (s1['日期'].min().date(), s1['日期'].max().date(), s1['日期'].nunique()))
print('方案ID %d 个 | 推广单元ID %d 个'
      % (s1['方案ID'].nunique(), s1['推广单元ID'].nunique()))

# ---- 0b. 固化「Sheet3 无日期」这一限制(可复现证据, 供论文引用) -------
print('\n-- 0b. Sheet3 时间维度核验 --')
s3 = pd.read_excel(SRC, sheet_name='Sheet3')
date_like = []
for c in s3.columns:
    # 纯数值列直接跳过 —— 否则 pd.to_datetime 会把整数当成 1970 年起的纳秒时间戳
    if pd.api.types.is_numeric_dtype(s3[c]):
        continue
    if not (s3[c].astype(str).str.contains(r'\d{4}[-/年]', regex=True, na=False).mean() > 0.95):
        continue
    p = pd.to_datetime(s3[c], errors='coerce', format='mixed')
    # 解析成功率要高、取值要多样、且年份需落在合理区间
    ok = p.notna() & p.dt.year.between(2000, 2100)
    if ok.mean() > 0.95 and p[ok].nunique() > 12:
        date_like.append(c)
print('Sheet3 字段: %s' % ', '.join(s3.columns))
print('Sheet3 中的日期型字段: %s' % (date_like if date_like else '无'))

_agg1 = s1.groupby(['方案ID', '推广单元ID'])['点击量'].sum()
_agg3 = s3.groupby(['方案ID', '推广单元ID'])['点击量'].sum()
_cmp = pd.concat([_agg1.rename('Sheet1全年'), _agg3.rename('Sheet3快照')], axis=1)
_cmp['比值'] = _cmp['Sheet3快照'] / _cmp['Sheet1全年']
print('Sheet3 各单元点击量 / Sheet1 各单元全年点击量:')
print(_cmp.round(4).to_string())
_all_one = np.allclose(_cmp['比值'].values, 1.0)
print('→ 比值是否全部为 1.0: %s' % _all_one)
if _all_one:
    print('→ 判定: Sheet3 是**整年快照**, 无月份维度。')
    print('→ 因此 跳出率 / 平均访问时长 **不纳入月度评价体系**。')
    print('   (Sheet3 的 平均访问时长 为 "00:03:16" 字符串格式, 含 "/" 缺失标记 890 处;')
    print('    跳出率 为小数格式, 同样含 "/" 缺失 890 处。若日后拿到带日期的版本,')
    print('    可直接用本脚本第 2 节的 parse_hms() 转换为秒后按 Σ点击量 加权聚合。)')
_cmp.round(4).to_csv(os.path.join(OUT_DAT, '表0_Sheet3粒度核验.csv'), encoding='utf-8-sig')


def parse_hms(v):
    """'00:03:16' -> 196 秒。'/' 或空 -> NaN。备用, 本次评价体系未使用。"""
    s = str(v).strip()
    if s in ('/', '', 'nan', 'NaN'):
        return np.nan
    parts = s.split(':')
    if len(parts) != 3:
        return np.nan
    try:
        h, m, sec = (float(x) for x in parts)
    except ValueError:
        return np.nan
    return h * 3600 + m * 60 + sec


# ============================================================ 1. 月度汇总
print('\n' + '=' * 70)
print('1. 按月份汇总(2025 年, 一行 = 一个月)')
print('=' * 70)

s1 = s1.set_index('日期')
monthly = s1.resample('MS').agg(
    展现量=('展现量', 'sum'),
    点击量=('点击量', 'sum'),
    消费额=('消费额', 'sum'),
    上方位展现量=('上方位展现量', 'sum'),
    上方位点击量=('上方位点击量', 'sum'),
    上方首位展现量=('上方首位展现量', 'sum'),
)
monthly.insert(0, '月份', MONTH_LABELS)
# 日均展现量: 分母是当月**实际有投放记录的自然日数**, 不是行数
_days = s1.reset_index().groupby(pd.Grouper(key='日期', freq='MS'))['日期'].nunique()
monthly['投放天数'] = _days.values
monthly['日均展现量'] = monthly['展现量'] / monthly['投放天数'].values
monthly['投放单元数'] = s1.groupby(pd.Grouper(freq='MS'))['推广单元ID'].nunique().values
if (monthly['日均展现量'] <= 0).any():
    raise ValueError('日均展现量出现非正值, 请检查日期列')

# —— 比率型指标一律 Σ分子/Σ分母, 绝不对日 CTR 求简单平均 ——
monthly['CTR'] = monthly['点击量'] / monthly['展现量']
monthly['上方位CTR'] = monthly['上方位点击量'] / monthly['上方位展现量']
monthly['CPC'] = monthly['消费额'] / monthly['点击量']
monthly['首位展现率'] = monthly['上方首位展现量'] / monthly['展现量']

# 防除零自检
if (monthly[['展现量', '点击量', '上方位展现量']] == 0).any().any():
    raise ZeroDivisionError('存在分母为 0 的月份, 无法计算比率指标')

print(monthly.round(6).to_string(index=False))

_monthly_out = monthly[['月份', '展现量', '点击量', '消费额', '上方位展现量',
                        '上方位点击量', '上方首位展现量', 'CTR', '上方位CTR',
                        'CPC', '首位展现率', '投放天数', '日均展现量', '投放单元数']]
_monthly_out.round(6).to_csv(os.path.join(OUT_DAT, '表1_月度汇总.csv'),
                             index=False, encoding='utf-8-sig')

print('\n核心指标季度/全年对比(验证 Σ/Σ 口径):')
print('  全年 CTR = Σ点击量 / Σ展现量 = %d / %d = %.6f'
      % (monthly['点击量'].sum(), monthly['展现量'].sum(),
         monthly['点击量'].sum() / monthly['展现量'].sum()))

# ============================================================ 2. 同向化 + Min-Max
print('\n' + '=' * 70)
print('2. 指标同向化 + 全局 Min-Max 标准化(12 个月统一口径)')
print('=' * 70)

# 指标字典: 列名 -> (方向, 说明)
INDICATORS = {
    'CTR': ('+', '点击率 = Σ点击量/Σ展现量, 反映创意吸引力'),
    '上方位CTR': ('+', '上方位点击率 = Σ上方位点击量/Σ上方位展现量'),
    'CPC': ('-', '单次点击成本 = Σ消费额/Σ点击量, 越低越好'),
}
COLS = list(INDICATORS)
raw = monthly[COLS].astype(float).values          # 12 × 3, 未标准化原始值
n_month, n_ind = raw.shape

# 2a. 同向化: 负向指标取极差反向
oriented = raw.copy()
for j, c in enumerate(COLS):
    if INDICATORS[c][0] == '-':
        oriented[:, j] = -raw[:, j]

# 2b. 全局 Min-Max —— 极差取自全部 12 个月, 保证月份之间可比
mins, maxs = oriented.min(axis=0), oriented.max(axis=0)
rng = maxs - mins
if (rng == 0).any():
    dead = [COLS[j] for j in range(n_ind) if rng[j] == 0]
    raise ValueError('指标 %s 在 12 个月上零方差, 无法标准化' % dead)
Z = (oriented - mins) / rng

# 平移一个极小量, 避免熵权法中 ln(0) (对结果影响可忽略, 此处落于 1e-4 量级)
EPS = 1e-4
Z_safe = Z + EPS

print('原始值范围:')
for j, c in enumerate(COLS):
    print('  %-8s [%s]  原始 min=%.6f  max=%.6f  → 归一后 [0,1]'
          % (c, INDICATORS[c][0], raw[:, j].min(), raw[:, j].max()))

print('\n标准化矩阵 Z (行=月份, 列=指标):')
zdf = pd.DataFrame(Z, index=MONTH_LABELS, columns=['%s%s' % (c, '(+' if INDICATORS[c][0] == '+' else '(-') + ')' for c in COLS])
print(zdf.round(4).to_string())

# ============================================================ 3. 熵权法
print('\n' + '=' * 70)
print('3. 熵权法确定权重(一套权重适用于全部 12 个月)')
print('=' * 70)

P = Z_safe / Z_safe.sum(axis=0, keepdims=True)     # 列归一 → 概率矩阵
k = 1.0 / np.log(n_month)
E = -k * (P * np.log(P)).sum(axis=0)               # 信息熵, ∈[0,1]
D = 1.0 - E                                        # 差异系数
if D.sum() <= 0:
    W = np.full(n_ind, 1.0 / n_ind)
    print('警告: 全部指标差异系数为 0, 退化为等权')
else:
    W = D / D.sum()

wdf = pd.DataFrame({'指标': COLS,
                    '方向': [INDICATORS[c][0] for c in COLS],
                    '信息熵e': E,
                    '差异系数d': D,
                    '权重w': W}).sort_values('权重w', ascending=False)
print(wdf.round(6).to_string(index=False))
print('权重合计 = %.6f' % W.sum())

# ============================================================ 4. TOPSIS
print('\n' + '=' * 70)
print('4. TOPSIS 综合评价')
print('=' * 70)

def topsis(Zmat, weights):
    """给定标准化矩阵与权重, 返回 (贴近度, D+, D-)。

    正理想解取各列最大、负理想解取各列最小 —— 因为 Z 已完成同向化,
    所以"越大越好"对所有列一致成立。
    """
    V_ = Zmat * weights
    best, worst = V_.max(axis=0), V_.min(axis=0)
    d_plus = np.sqrt(((V_ - best) ** 2).sum(axis=1))
    d_minus = np.sqrt(((V_ - worst) ** 2).sum(axis=1))
    return d_minus / (d_plus + d_minus), d_plus, d_minus


score, D_plus, D_minus = topsis(Z, W)              # 相对贴近度 ∈[0,1]
score100 = score * 100

result = pd.DataFrame({
    '月份': MONTH_LABELS,
    'CTR': raw[:, 0],
    '上方位CTR': raw[:, 1],
    'CPC': raw[:, 2],
    'D+': D_plus,
    'D-': D_minus,
    '综合得分': score100,
}).sort_values('综合得分', ascending=False).reset_index(drop=True)
result.insert(0, '排名', np.arange(1, n_month + 1))

print(result.round(4).to_string(index=False))

best_m = int(np.argmax(score))
worst_m = int(np.argmin(score))
print('\n得分最高月份: %s (%.2f 分)' % (MONTH_LABELS[best_m], score100[best_m]))
print('得分最低月份: %s (%.2f 分)' % (MONTH_LABELS[worst_m], score100[worst_m]))

# 稳健性对照: 等权 vs 熵权, 看排序是否一致 (论文里可作灵敏度分析)
score_eq, _, _ = topsis(Z, np.full(n_ind, 1.0 / n_ind))
# Spearman 秩相关 = 先取秩再算 Pearson, 这样不依赖 scipy
_r1 = pd.Series(score100).rank().values
_r2 = pd.Series(score_eq).rank().values
rho = float(np.corrcoef(_r1, _r2)[0, 1])
print('熵权得分与等权得分的 Spearman 秩相关 = %.4f' % rho)

# 输出
score_tbl = pd.DataFrame({'月份': MONTH_LABELS, 'CTR': raw[:, 0], '上方位CTR': raw[:, 1],
                          'CPC': raw[:, 2], 'D+': D_plus, 'D-': D_minus,
                          '综合得分': score100, '等权得分': score_eq * 100})
score_tbl.round(6).to_csv(os.path.join(OUT_DAT, '表3_月度综合得分.csv'),
                          index=False, encoding='utf-8-sig')
pd.concat([wdf.reset_index(drop=True),
           pd.DataFrame({'指标': ['—'], '方向': ['—'], '信息熵e': [np.nan],
                         '差异系数d': [np.nan], '权重w': [W.sum()]})]
          ).round(6).to_csv(os.path.join(OUT_DAT, '表2_熵权法权重.csv'),
                            index=False, encoding='utf-8-sig')

# ============================================================ 5. 绘图
print('\n' + '=' * 70)
print('5. 绘图')
print('=' * 70)

x = np.arange(1, 13)

# ---- 图1: CTR 月度变化 ------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 4.4))
style_ax(ax)
ax.plot(x, raw[:, 0] * 100, color=C_BLUE, linewidth=2.0, marker='o',
        markersize=6.5, markerfacecolor=SURFACE, markeredgewidth=1.8,
        markeredgecolor=C_BLUE, zorder=3, label='CTR')
ax.axhline(raw[:, 0].mean() * 100, color=MUTED, linestyle='--',
           linewidth=1.1, zorder=2, label='全年均值 %.2f%%' % (raw[:, 0].mean() * 100))
for i in (best_m, worst_m):
    ax.annotate('%s\n%.2f%%' % (MONTH_LABELS[i], raw[i, 0] * 100),
                xy=(x[i], raw[i, 0] * 100), xytext=(0, 12),
                textcoords='offset points', ha='center', fontsize=8.5,
                color=INK, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(MONTH_LABELS)
ax.set_xlabel('月份', fontsize=10, color=INK2)
ax.set_ylabel('CTR (%)', fontsize=10, color=INK2)
ax.set_title('2025 年广告点击率(CTR)月度变化趋势\nCTR = Σ点击量 / Σ展现量',
             fontsize=12, color=INK, pad=12, fontweight='bold')
ax.legend(frameon=False, fontsize=9, loc='upper right')
ax.set_ylim(0, raw[:, 0].max() * 100 * 1.22)
fig.tight_layout()
save(fig, '图1_CTR月度变化.png')

# ---- 图2: 月度综合得分 ------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 4.6))
style_ax(ax)
ax.plot(x, score100, color=C_BLUE, linewidth=2.2, marker='o', markersize=7,
        markerfacecolor=SURFACE, markeredgewidth=2.0, markeredgecolor=C_BLUE,
        zorder=3, label='综合得分')
ax.axhline(score100.mean(), color=MUTED, linestyle='--', linewidth=1.1,
           zorder=2, label='年均得分 %.2f' % score100.mean())

# 标注最高 / 最低月
ax.scatter([x[best_m]], [score100[best_m]], s=170, color=C_MAX, zorder=4,
           edgecolor=SURFACE, linewidth=1.6)
ax.scatter([x[worst_m]], [score100[worst_m]], s=170, color=C_MIN, zorder=4,
           edgecolor=SURFACE, linewidth=1.6)
ax.annotate('最高: %s\n%.2f 分' % (MONTH_LABELS[best_m], score100[best_m]),
            xy=(x[best_m], score100[best_m]), xytext=(10, 18),
            textcoords='offset points', fontsize=9.5, color=C_MAX,
            fontweight='bold',
            arrowprops=dict(arrowstyle='-', color=C_MAX, linewidth=1.1))
ax.annotate('最低: %s\n%.2f 分' % (MONTH_LABELS[worst_m], score100[worst_m]),
            xy=(x[worst_m], score100[worst_m]), xytext=(8, -34),
            textcoords='offset points', fontsize=9.5, color=C_MIN,
            fontweight='bold',
            arrowprops=dict(arrowstyle='-', color=C_MIN, linewidth=1.1))

ax.set_xticks(x)
ax.set_xticklabels(MONTH_LABELS)
ax.set_xlabel('月份', fontsize=10, color=INK2)
ax.set_ylabel('综合得分', fontsize=10, color=INK2)
ax.set_title('2025 年广告设计质量与创意的月度综合得分\n'
             '熵权法 + TOPSIS(12 个月统一口径)',
             fontsize=12, color=INK, pad=12, fontweight='bold')
ax.set_xlim(0.4, 12.6)
ax.set_ylim(score100.min() - (score100.max() - score100.min()) * 0.28,
            score100.max() + (score100.max() - score100.min()) * 0.30)
ax.legend(frameon=False, fontsize=9, loc='lower right')
fig.tight_layout()
save(fig, '图2_月度综合得分.png')

# ---- 图3: 三指标标准化对比(消除量纲后才能同框) -----------------------
fig, axes = plt.subplots(3, 1, figsize=(8.4, 8.0), sharex=True)
names = ['CTR (+)', '上方位CTR (+)', 'CPC (−, 已同向化)']
colors = [C_BLUE, C_GREEN, C_ORANGE]
for j, (ax, nm, cl) in enumerate(zip(axes, names, colors)):
    style_ax(ax)
    ax.plot(x, Z[:, j], color=cl, linewidth=1.9, marker='s', markersize=5,
            markerfacecolor=SURFACE, markeredgewidth=1.6, markeredgecolor=cl,
            zorder=3)
    ax.set_ylabel('归一化值', fontsize=9, color=INK2)
    ax.set_ylim(-0.08, 1.16)
    # 指标名与权重合并到同一行, 避免右上角标签与曲线重叠
    ax.text(0.012, 1.02, '%s   熵权 w=%.4f' % (nm, W[j]), transform=ax.transAxes,
            fontsize=10, color=INK, fontweight='bold', va='bottom')
    ax.set_xticks(x)
axes[-1].set_xticklabels(MONTH_LABELS)
axes[-1].set_xlabel('月份', fontsize=10, color=INK2)
axes[0].set_title('三项评价指标的月度标准化值(Min-Max, 全局口径)',
                  fontsize=12, color=INK, pad=12, fontweight='bold')
fig.tight_layout()
save(fig, '图3_三指标标准化对比.png')

print('\n' + '=' * 70)
print('6. 稳健性与结构诊断 —— 解读得分前必看')
print('=' * 70)

_corr = pd.DataFrame(raw, columns=COLS).corr()
print('三项指标月度值之间的 Pearson 相关:')
print(_corr.round(4).to_string())

_rank_eq = pd.Series(score_eq).rank().values
_rank_en = pd.Series(score100).rank().values
if abs(rho) < 0.5:
    print('\n[警告] 熵权排序与等权排序的 Spearman 秩相关仅 %.4f, 说明月排名对'
          '权重高度敏感,' % rho)
    print('       即"谁拿第一"主要由权重决定, 而不是数据本身。')
    print('       根因是三项指标两两冲突(见上表负相关), 它们并非相互独立的质量维度。')

# 投放结构诊断: 点击量中来自上方位(优质位)的占比
_top_click_share = (monthly['上方位点击量'] / monthly['点击量']).values
print('\n上方位点击占比(点击量中来自优质位的比例)月度变化:')
print('  ' + '  '.join('%s %.1f%%' % (MONTH_LABELS[i], _top_click_share[i] * 100)
                       for i in range(n_month)))
_delta = _top_click_share[-1] - _top_click_share[0]
print('  1月 %.1f%% → 12月 %.1f%%, 变动 %+.1f 个百分点'
      % (_top_click_share[0] * 100, _top_click_share[-1] * 100, _delta * 100))
if abs(_delta) > 0.3:
    print('\n[警告] 全年投放结构发生大幅漂移: 上方位点击占比从 %.1f%% 升到 %.1f%%。'
          % (_top_click_share[0] * 100, _top_click_share[-1] * 100))
    print('       展现量同时从 %d/月 涨到 %d/月, 在投单元数从 %d 个涨到 %d 个。'
          % (monthly['展现量'].iloc[0], monthly['展现量'].iloc[-1],
             monthly['投放单元数'].iloc[0], monthly['投放单元数'].iloc[-1]))
    print('       这不是"创意质量"的变化, 而是媒介投放策略的结构性切换:')
    print('       展现量被摊薄 → 全站CTR下降; 预算向上方位集中 → 上方位CTR上升。')
    print('       建议在论文中把 1-2月 与 5-12月 作为两种投放结构分别讨论,')
    print('       或只在结构相对稳定的区间内比较月度创意表现。')

diag = pd.DataFrame({
    '月份': MONTH_LABELS,
    'CTR': raw[:, 0],
    '上方位CTR': raw[:, 1],
    'CPC': raw[:, 2],
    '上方位点击占比': _top_click_share,
    '综合得分': score100,
    '等权得分': score_eq * 100,
})
diag.round(6).to_csv(os.path.join(OUT_DAT, '表4_结构诊断.csv'),
                     index=False, encoding='utf-8-sig')

print('\n全部完成。输出目录: %s' % (OUT_FIG + ' / ' + OUT_DAT))
