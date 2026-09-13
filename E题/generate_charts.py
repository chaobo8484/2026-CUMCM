import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ── 读数据 ──────────────────────────────────────────────────────────────────
s1 = pd.read_csv('clean_data/sheet1_投放记录_clean.csv', encoding='utf-8-sig', parse_dates=['日期'])
s2 = pd.read_csv('clean_data/sheet2_日注册_clean.csv',  encoding='utf-8-sig', parse_dates=['日期'])
dim = pd.read_csv('clean_data/dim_date_时间维度.csv',    encoding='utf-8-sig', parse_dates=['日期'])

# 日粒度汇总 sheet1
daily = s1.groupby('日期').agg(
    日展现量=('展现量', 'sum'),
    日点击量=('点击量', 'sum'),
    日消费额=('消费额', 'sum'),
    上方位展现量=('上方位展现量', 'sum'),
    上方位点击量=('上方位点击量', 'sum'),
    上方位消费额=('上方位消费额', 'sum'),
).reset_index()
daily['日CTR']    = daily['日点击量'] / daily['日展现量'].replace(0, np.nan)
daily['上位展现占比'] = daily['上方位展现量'] / daily['日展现量'].replace(0, np.nan)
daily['上位消费占比'] = daily['上方位消费额'] / daily['日消费额'].replace(0, np.nan)

# 合并
base = daily.merge(s2, on='日期').merge(dim, on='日期')
base['CPA'] = base['日消费额'] / base['新注册数'].replace(0, np.nan)
base['千次展现注册'] = base['新注册数'] / base['日展现量'] * 1000
base['月'] = base['日期'].dt.month

OUT = 'charts/'
import os; os.makedirs(OUT, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# 一、投放策略合理性
# ═══════════════════════════════════════════════════════════════════════════

# 图1-1  上方位展现占比 vs 日CTR 散点（月份着色）
fig, ax = plt.subplots(figsize=(8, 5))
cmap = plt.cm.tab10
months = base['月'].unique()
for m in sorted(months):
    sub = base[base['月'] == m]
    ax.scatter(sub['上位展现占比'], sub['日CTR'], label=f'{m}月',
               alpha=0.7, s=35, color=cmap((m-1)/12))
ax.set_xlabel('上方位展现占比')
ax.set_ylabel('日点击率 CTR')
ax.set_title('上方位展现占比 vs 日点击率（各月）')
ax.legend(ncol=3, fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT + '1_1_上位展现占比_vs_CTR.png', dpi=150)
plt.close()

# 图1-2  各方案每元消费带来的注册数（策略ROI对比）
scheme = s1.groupby('方案ID').agg(消费额=('消费额','sum'), 点击量=('点击量','sum')).reset_index()
reg_total = s2['新注册数'].sum()
spend_total = s2['日总消费'].sum()
scheme['占消费比'] = scheme['消费额'] / spend_total
# 只取消费额前10方案
top10 = scheme.nlargest(10, '消费额')
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].barh(top10['方案ID'].astype(str), top10['消费额'], color='steelblue')
axes[0].set_xlabel('总消费额 (元)')
axes[0].set_title('TOP10方案 消费额分布')
axes[0].invert_yaxis()
axes[1].barh(top10['方案ID'].astype(str), top10['占消费比']*100, color='coral')
axes[1].set_xlabel('占总消费比例 (%)')
axes[1].set_title('TOP10方案 消费占比')
axes[1].invert_yaxis()
fig.tight_layout()
fig.savefig(OUT + '1_2_方案消费分布.png', dpi=150)
plt.close()

# 图1-3  上方位消费占比随月份变化（策略位置偏好）
monthly = base.groupby('月').agg(
    上位消费占比=('上位消费占比','mean'),
    日CTR=('日CTR','mean'),
    CPA=('CPA','mean')
).reset_index()
fig, ax1 = plt.subplots(figsize=(8, 4))
ax2 = ax1.twinx()
ax1.bar(monthly['月'], monthly['上位消费占比']*100, alpha=0.6, color='steelblue', label='上方位消费占比(%)')
ax2.plot(monthly['月'], monthly['CPA'], 'o-', color='crimson', label='月均CPA(元)')
ax1.set_xlabel('月份')
ax1.set_ylabel('上方位消费占比 (%)', color='steelblue')
ax2.set_ylabel('月均CPA (元)', color='crimson')
ax1.set_title('上方位消费占比 与 月均CPA 逐月对比')
ax1.set_xticks(range(1,13))
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper right', fontsize=9)
fig.tight_layout()
fig.savefig(OUT + '1_3_上位消费占比_月均CPA.png', dpi=150)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════
# 二、投放效益与时间变化规律
# ═══════════════════════════════════════════════════════════════════════════

# 图2-1  日注册数 & 日消费额 双轴时序
fig, ax1 = plt.subplots(figsize=(14, 4))
ax2 = ax1.twinx()
ax1.fill_between(base['日期'], base['新注册数'], alpha=0.4, color='steelblue', label='日注册数')
ax2.plot(base['日期'], base['日消费额'], color='darkorange', linewidth=1, label='日消费额(元)')
ax1.set_ylabel('日注册数', color='steelblue')
ax2.set_ylabel('日消费额 (元)', color='darkorange')
ax1.set_title('日注册数 & 日消费额 全年趋势')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax1.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate()
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper left', fontsize=9)
fig.tight_layout()
fig.savefig(OUT + '2_1_日注册_消费_时序.png', dpi=150)
plt.close()

# 图2-2  日CPA 时序 + 7日滚动均线
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(base['日期'], base['CPA'], color='gray', linewidth=0.8, alpha=0.6, label='日CPA')
ax.plot(base['日期'], base['CPA'].rolling(7).mean(), color='crimson', linewidth=1.8, label='7日滚动均线')
ax.set_ylabel('CPA (元/注册)')
ax.set_title('每次注册成本(CPA) 全年走势')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate()
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT + '2_2_CPA时序.png', dpi=150)
plt.close()

# 图2-3  月度箱线图：CPA分布
fig, ax = plt.subplots(figsize=(10, 5))
data_by_month = [base[base['月']==m]['CPA'].dropna().values for m in range(1,13)]
bp = ax.boxplot(data_by_month, labels=[f'{m}月' for m in range(1,13)],
                patch_artist=True, medianprops=dict(color='red', linewidth=2))
colors = plt.cm.Blues(np.linspace(0.3, 0.8, 12))
for patch, c in zip(bp['boxes'], colors):
    patch.set_facecolor(c)
ax.set_ylabel('CPA (元/注册)')
ax.set_title('各月CPA分布箱线图')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(OUT + '2_3_月度CPA箱线图.png', dpi=150)
plt.close()

# 图2-4  星期维度：各weekday平均注册数 & 平均CPA
base['星期序'] = pd.to_datetime(base['日期']).dt.dayofweek  # 0=Monday
weekday_labels = ['周一','周二','周三','周四','周五','周六','周日']
wd = base.groupby('星期序').agg(均注册=('新注册数','mean'), 均CPA=('CPA','mean')).reset_index()
fig, ax1 = plt.subplots(figsize=(8, 4))
ax2 = ax1.twinx()
ax1.bar(wd['星期序'], wd['均注册'], alpha=0.6, color='steelblue', label='平均注册数')
ax2.plot(wd['星期序'], wd['均CPA'], 'o-', color='crimson', label='平均CPA(元)')
ax1.set_xticks(range(7)); ax1.set_xticklabels(weekday_labels)
ax1.set_ylabel('平均注册数', color='steelblue')
ax2.set_ylabel('平均CPA (元)', color='crimson')
ax1.set_title('一周各天的平均注册数 & 平均CPA')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper left', fontsize=9)
fig.tight_layout()
fig.savefig(OUT + '2_4_星期效应.png', dpi=150)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════
# 三、假日效应
# ═══════════════════════════════════════════════════════════════════════════

# 图3-1  三态标签下的注册数 & CPA 箱线图
label_order = ['放假', '正常', '调休']
label_cn = {'放假':'节假日', '正常':'工作日', '调休':'调休'}
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
colors_map = {'放假':'#e74c3c', '正常':'#3498db', '调休':'#f39c12'}
for i, (col, ylabel) in enumerate([('新注册数','日注册数'), ('CPA','CPA (元/注册)')]):
    data = [base[base['三态标签']==lbl][col].dropna().values for lbl in label_order]
    bp = axes[i].boxplot(data, labels=[label_cn[l] for l in label_order],
                         patch_artist=True, medianprops=dict(color='black', linewidth=2))
    for patch, lbl in zip(bp['boxes'], label_order):
        patch.set_facecolor(colors_map[lbl])
    axes[i].set_ylabel(ylabel)
    axes[i].set_title(f'三态标签 × {ylabel}')
    axes[i].grid(axis='y', alpha=0.3)
fig.suptitle('节假日 / 工作日 / 调休 效应对比', fontsize=13)
fig.tight_layout()
fig.savefig(OUT + '3_1_假日效应箱线图.png', dpi=150)
plt.close()

# 图3-2  假日窗口放大：节假日前后±5天 CPA走势（春节为例）
# 找春节（1月末/2月初 三态标签==放假 的连续段第一个）
holiday_dates = base[base['三态标签']=='放假']['日期'].sort_values()
# 找最长连续假期段（春节）
groups = (holiday_dates.diff() != pd.Timedelta('1D')).cumsum()
biggest_group = groups.value_counts().idxmax()
chunyun = holiday_dates[groups == biggest_group]
start, end = chunyun.min(), chunyun.max()
window_start = start - pd.Timedelta('7D')
window_end   = end   + pd.Timedelta('7D')
win = base[(base['日期'] >= window_start) & (base['日期'] <= window_end)].copy()

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(win['日期'], win['CPA'], 'o-', color='steelblue', linewidth=1.5, markersize=4)
ax.axvspan(start, end, alpha=0.15, color='red', label='节假日区间')
ax.axvline(start, color='red', linestyle='--', linewidth=1)
ax.axvline(end,   color='red', linestyle='--', linewidth=1)
ax.set_ylabel('CPA (元/注册)')
ax.set_title('最长节假日窗口（±7天）CPA走势')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT + '3_2_节假日窗口CPA.png', dpi=150)
plt.close()

# 图3-3  各月假日 vs 非假日 平均日注册对比（分组柱状图）
base['是否放假'] = base['三态标签'].map({'放假':'节假日','调休':'调休','正常':'工作日'})
grp = base.groupby(['月','是否放假'])['新注册数'].mean().reset_index()
pivot = grp.pivot(index='月', columns='是否放假', values='新注册数').fillna(0)
pivot = pivot.reindex(columns=[c for c in ['工作日','调休','节假日'] if c in pivot.columns])
fig, ax = plt.subplots(figsize=(11, 5))
pivot.plot(kind='bar', ax=ax, color=['#3498db','#f39c12','#e74c3c'], alpha=0.85, width=0.7)
ax.set_xlabel('月份')
ax.set_ylabel('平均日注册数')
ax.set_title('各月：工作日 / 调休 / 节假日 平均日注册对比')
ax.set_xticklabels([f'{m}月' for m in range(1,13)], rotation=0)
ax.legend(title='日期类型')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(OUT + '3_3_各月假日注册对比.png', dpi=150)
plt.close()

print("所有图表已保存至 charts/ 目录")
print("生成图表：")
for f in sorted(os.listdir(OUT)):
    print(f"  {f}")
