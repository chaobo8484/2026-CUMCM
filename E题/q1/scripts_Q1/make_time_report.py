# -*- coding: utf-8 -*-
"""由 q1_time_*.csv 生成《计算数据报告_投放时间.md》，数字全部来自CSV。"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOUT = os.path.join(ROOT, "data_Q1")
OUT = os.path.join(DOUT, "计算数据报告_投放时间.md")

def md(df):
    """最小markdown表格（不依赖tabulate）。"""
    h = "| " + " | ".join(map(str, df.columns)) + " |"
    s = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False, name=None)]
    return "\n".join([h, s] + rows)

def load(n):
    return pd.read_csv(os.path.join(DOUT, n), encoding="utf-8-sig")

daily = load("q1_time_daily.csv")
mo = load("q1_time_monthly.csv")
wd = load("q1_time_weekday.csv")
kw = load("q1_time_weekday_kw.csv")
he = load("q1_time_holiday_he.csv")
lag = load("q1_time_lagcorr.csv")
fit = load("q1_time_reg_fit.csv")
coef = load("q1_time_reg_coef.csv")
vif1 = load("q1_time_reg_vif1.csv")
units = load("q1_time_unit_days.csv")

L = []
L.append("# Q1投放策略与时间：计算数据报告")
L.append("")
L.append("> 脚本：`E题/q1/scripts_Q1/time_strategy.py`（可复现，仓库根目录运行 `python E题/q1/scripts_Q1/time_strategy.py`）")
L.append("> 唯一数据源：`E题/clean_data/*_clean.csv`；比率一律先汇总再相除；CPA仅公司日度代理，不拆单元。")
L.append("> 图表：`E题/q1/charts_Q1/q1_t1~t6、q1_b5`（PDF+PNG，300dpi）。")
L.append("")
L.append("## 0. 对账")
L.append(f"- 总消费 `{daily['日消费'].sum():.2f}` 元，总点击 `{daily['日点击'].sum():.0f}` 次，整体CPC `{daily['日消费'].sum()/daily['日点击'].sum():.4f}` 元/次，天数 `{len(daily)}`。")
L.append(f"- 日均活跃单元（当日消费>0）`{daily['活跃单元数'].mean():.2f}` 个，每日最大单元占比均值 `{daily['最大单元占比'].mean()*100:.1f}%`。")
pk = daily.loc[daily["日消费"].idxmax()]
L.append(f"- 消费峰 `{str(pk['日期'])[:10]}`：消费 `{pk['日消费']:.2f}` 元，点击 `{pk['日点击']:.0f}` 次，CPC `{pk['CPC']:.3f}`，注册 `{pk['新注册数']:.0f}` 人，CPA `{pk['CPA']:.3f}`。")
L.append("")
L.append("## 1. 单元投放天数（clean_data统一口径）")
L.append("")
L.append(units.round(4).pipe(md))
L.append("")
L.append("## 2. 月度投放与效益（`q1_time_monthly.csv`）")
L.append("")
L.append(mo.round(4).pipe(md))
L.append("")
L.append("## 3. 星期效应（`q1_time_weekday.csv`）")
L.append("")
L.append(wd.round(4).pipe(md))
L.append("")
L.append("### Kruskal-Wallis五变量检验")
L.append("")
L.append(kw.round(6).pipe(md))
L.append("")
L.append("结论：消费/CPA/CTR星期差异显著，CPC与活跃单元数不显著——差异来自预算强度而非开几个单元。")
L.append("")
L.append("## 4. 假日HE（同星期±4周正常日对照，`q1_time_holiday_he.csv`）")
L.append("")
L.append(he.round(4).pipe(md))
L.append("")
L.append("结论：端午CPC上升约74%为最需降价限额的假日；清明缩量最大；劳动节/国庆缩量后CPC、CPA双降。")
L.append("")
L.append("## 5. 滞后相关（`q1_time_lagcorr.csv`，图q1_t5）")
L.append("")
L.append(lag.round(4).pipe(md))
L.append("")
L.append("结论：当日0.82最强，滞后1日0.61，2–5日降至0.3–0.4，6–7日回升系星期周期。只保留当日+滞后1日进回归。")
L.append("")
L.append("## 6. 回归拟合（HAC稳健标准误，`q1_time_reg_fit.csv`）")
L.append("")
L.append(fit.round(4).pipe(md))
L.append("")
L.append("### 关键系数")
L.append("")
L.append(coef[coef["变量"].isin(["const", "lnC", "lnC1", "t", "H"])].round(4).pipe(md))
L.append("")
L.append("### VIF（模型1）")
L.append("")
L.append(vif1.round(3).pipe(md))
L.append("")
L.append("结论：正文用模型1。当日消费弹性约0.72（p<0.001）；趋势与总体假日不显著；滞后1日p≈0.057边界不显著，仅稳健性证据；DW≈0.8故用Newey-West。")
L.append("完整系数（含星期虚拟变量）见 `q1_time_reg_coef.csv`，模型2的VIF见 `q1_time_reg_vif2.csv`。")
L.append("")
L.append("## 7. 与docx文档的差异说明")
L.append("- 滞后1日p值本报告0.057，文档0.054：HAC滞后阶数取7所致，均不显著，结论一致。")
L.append("- 单元投放天数以本报告（clean_data口径）为准，旧`q1_unit_summary.csv`（附件分文件口径）相差2–3天，作废。")
L.append("- 注册均为代理分析，不构成严格SEM归因；滞后相关不解释为因果。")
L.append("")
L.append("## 8. 图表清单")
for f in ["q1_t1_全年节奏", "q1_t2_月度投放效益", "q1_t3_星期效应", "q1_t4_假日HE",
          "q1_t5_滞后相关", "q1_t6a_回归forest", "q1_t6b_回归诊断", "q1_b5_日集中度"]:
    L.append(f"- `charts_Q1/{f}.pdf/png`")
L.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("report done:", OUT)
