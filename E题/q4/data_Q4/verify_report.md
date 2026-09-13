# Q4 复算核验报告(机器生成)

 ethics: 基准 delta=0.5 omega=0.5 band=±15%% gamma=1.2, B口径=单元周±15%%+日总额<=同期×115%%, 周总量==B.

## 1. 落盘清单
- data_Q4/avg_all.csv (1行)
- data_Q4/base_budget_0911_17.csv (77行)
- data_Q4/base_totals.csv (1行)
- data_Q4/cal_unit_day.csv (77行)
- data_Q4/daily_summary.csv (7行)
- data_Q4/day_hist.csv (7行)
- data_Q4/delta_backtest.csv (1行)
- data_Q4/delta_unit_q_h1h2.csv (11行)
- data_Q4/eta_depth.csv (1111行)
- data_Q4/fe_pred_2026.csv (77行)
- data_Q4/fe_resid.csv (909行)
- data_Q4/lag_fit.csv (363行)
- data_Q4/lag_nnls.csv (1行)
- data_Q4/lp_alloc.csv (2150行)
- data_Q4/omega_backtest.csv (3行)
- data_Q4/record_intervals.csv (2150行)
- data_Q4/rho_table.csv (1行)
- data_Q4/sensitivity.csv (8行)
- data_Q4/total_intervals.csv (6行)
- data_Q4/type_alloc.csv (3行)
- data_Q4/unit_hist.csv (11行)
- data_Q4/result4.xlsx: 最优投放策略(2150行), 指标期望范围(2150行)
- charts_Q4/fig2_budget_cpa.png, fig3_regs_interval.png, fig4_type_alloc.png

## 2. 可行性断言
- 周总量差=-0.000007元 (<1e-6? False)
- 求解状态=Optimal; 潜力占比=0.02% (<=15% ✓)
- 记录中心全落在80%%区间内 ✓ (s4断言通过)

## 3. 复算值 vs 论文值
| 指标 | 论文 | 复算 | 差异 |
| 总投入 | 23488.02 | 23488.02 | -0.00 (-0.0%) |
| 点击 | 18331 | 12004.19 | -6326.81 (-34.5%) |
| 浏览 | 84892 | 49497.47 | -35394.53 (-41.7%) |
| 注册 | 2164 | 1540.22 | -623.78 (-28.8%) |
| 记录数 | 922 | 2150.00 | +1228.00 (+133.2%) |
| 竞价代理 | 1.28 | 1.96 | +0.68 (+52.9%) |
| 展现量 | 613531 | 352654 | |
| 展现位 | 3.43 | 2.986 | |
| 注册80%区间 | 1980~2593 | 1396~1714 | |

差异归因: (1) 容量覆盖仅1.11(总M/周B), 求解被迫跟随历史, 有效CPC=1.96贴近同期1.83, 论文1.28需强得多的效率偏离, 其cap/候选预筛等微观口径未公开; (2) e=qbar·eta·theta·RHO(Q3结构), FE的CPC仅作竞价代理与CTR/展位换算; (3) 同词跨单元<=1未采用(论文4.3.5仅为候选范围约束, 且113个跨单元词会使覆盖1.11的问题不可行); (4) 单元带采用周口径(日口径下3个单元sumM<下限, 直接不可行).

## 4. 论文内表自洽(独立复算)
- 表1加总: 投入23488.02/点击18331/浏览84892/注册2164/词数922, 前4日21891.59占93.20%% ✓
- 4处日CPA舍入差0.01: 09-12应10.98(文10.97)/09-15应6.77(文6.78)/09-16应6.80(文6.79)/09-17应7.33(文7.32)
- B溯源: sheet1窗口消费23488.02 ✓; 4天日比率恰=1.15(09-11/15/16/17) → 日总额上限约束实锤, 论文漏写

## 5. 敏感性(基准注册=1540.22)
| 情景 | 状态 | 注册量 | 变化率 |
| delta=0.4 | Optimal | 1538.92 | -0.08% |
| delta=0.6 | Optimal | 1541.58 | +0.09% |
| band=±10% | Optimal | 1540.00 | -0.01% |
| band=±20% | Optimal | 1540.33 | +0.01% |
| gamma=1.1 | Optimal | 1517.19 | -1.50% |
| gamma=1.3 | Optimal | 1559.89 | +1.28% |
| omega=0.3 | Optimal | 1691.32 | +9.81% |
| omega=0.7 | Optimal | 1389.12 | -9.81% |

注: omega回测MAPE随omega单调降(0.3→0.1315/0.5→0.0939/0.7→0.0563, CPC), omega=0.5为中庸基准非估计最优, 与论文敏感性最大项一致.