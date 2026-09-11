# -*- coding: utf-8 -*-
"""E题附件1数据清洗脚本（可复现）.

输入 : E题/附件/附件1.xlsx
输出 : E题/clean_data/ 下 4份CSV(UTF-8-SIG) + clean_data.xlsx(4个sheet) + 时间维度表
规则 : 见 E题/清洗报告.md; 伪缺失'/' -> 空值, 绝不插补; 比率分母为零记空.
运行 : python E题/clean_data/build_clean_data.py  (仓库根目录)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "E题" / "附件" / "附件1.xlsx"
OUT = ROOT / "E题" / "clean_data"
OUT.mkdir(parents=True, exist_ok=True)

ROUND = 4

# ---- 2025年法定节假日三态标签（放假/补班/正常），落稿前请对照国务院原文再核对 ----
HOLIDAYS = set(pd.to_datetime([
    "2025-01-01",  # 元旦
    *pd.date_range("2025-01-28", "2025-02-04"),  # 春节
    *pd.date_range("2025-04-04", "2025-04-06"),  # 清明
    *pd.date_range("2025-05-01", "2025-05-05"),  # 劳动节
    *pd.date_range("2025-05-31", "2025-06-02"),  # 端午
    *pd.date_range("2025-10-01", "2025-10-08"),  # 国庆+中秋
]).date)
MAKEUP_WORK = set(pd.to_datetime([
    "2025-01-26", "2025-02-08",  # 春节调休上班
    "2025-04-27",  # 劳动节调休上班
    "2025-09-28", "2025-10-11",  # 国庆调休上班
]).date)


def miss_table(df, name):
    """逐列缺失数量与缺失率."""
    t = pd.DataFrame({"缺失数": df.isna().sum(), "缺失率": (df.isna().mean() * 100).round(2)})
    print(f"--- {name} 缺失统计 ---")
    print(t.to_string())
    print()
    return t


def div(a, b):
    """分母为零记空（NA），否则保留4位小数."""
    r = pd.to_numeric(a / b.replace(0, pd.NA), errors="coerce")
    return r.round(ROUND)


def check_logic(s1):
    """逻辑一致性校验：层级包含与消费↔点击对应关系（应全为0，结果仅作质量证据）。"""
    rules = {
        "点击>展现": s1["点击量"] > s1["展现量"],
        "上方位展现>总展现": s1["上方位展现量"] > s1["展现量"],
        "首位>上方位": s1["上方首位展现量"] > s1["上方位展现量"],
        "上方位点击>总点击": s1["上方位点击量"] > s1["点击量"],
        "上方位消费>总消费": s1["上方位消费额"] > s1["消费额"],
        "有消费无点击": (s1["消费额"] > 0) & (s1["点击量"] == 0),
        "有点击无消费": (s1["点击量"] > 0) & (s1["消费额"] == 0),
    }
    print("--- 逻辑一致性校验（应全为0） ---")
    for label, m in rules.items():
        print(f"{label}: {int(m.sum())}")
    print()
    return rules


def main():
    raw1 = pd.read_excel(SRC, sheet_name=0)
    raw2 = pd.read_excel(SRC, sheet_name=1)
    raw3 = pd.read_excel(SRC, sheet_name=2)

    # ---------- Sheet1 投放记录 ----------
    s1 = raw1.copy()
    s1.columns = ["日期", "方案ID", "推广单元ID", "展现量", "点击量", "消费额",
                  "上方位展现量", "上方首位展现量", "上方位点击量", "上方位消费额"]
    miss_table(s1, "Sheet1清洗前")
    s1["日期"] = pd.to_datetime(s1["日期"]).dt.strftime("%Y-%m-%d")
    for c in ["方案ID", "推广单元ID"]:
        s1[c] = s1[c].astype("int64").astype(str)
    s1["CTR"] = div(s1["点击量"], s1["展现量"])
    s1["上方位展现占比"] = div(s1["上方位展现量"], s1["展现量"])
    s1["首位展现占比"] = div(s1["上方首位展现量"], s1["展现量"])
    s1["上方位点击占比"] = div(s1["上方位点击量"], s1["点击量"])
    s1["上方位消费占比"] = div(s1["上方位消费额"], s1["消费额"])
    check_logic(s1)  # 逻辑一致性校验（本题全0，仅作质量证据）
    miss_table(s1, "Sheet1清洗后")

    # ---------- Sheet2 日注册 + 日总消费/CPA ----------
    s2 = raw2.copy()
    s2.columns = ["日期", "新注册数"]
    miss_table(s2, "Sheet2清洗前")
    s2["日期"] = pd.to_datetime(s2["日期"]).dt.strftime("%Y-%m-%d")
    daily_cost = raw1.copy()
    daily_cost.columns = ["日期", "方案ID", "推广单元ID", "展现量", "点击量", "消费额",
                          "上方位展现量", "上方首位展现量", "上方位点击量", "上方位消费额"]
    daily_cost["日期"] = pd.to_datetime(daily_cost["日期"]).dt.strftime("%Y-%m-%d")
    daily_cost = daily_cost.groupby("日期", as_index=False)["消费额"].sum().rename(columns={"消费额": "日总消费"})
    s2 = s2.merge(daily_cost, on="日期", how="left")
    s2["日CPA"] = div(s2["日总消费"], s2["新注册数"])
    miss_table(s2, "Sheet2清洗后")

    # ---------- Sheet3 关键词 ----------
    s3 = raw3.copy()
    s3.columns = ["序号", "关键词ID", "方案ID", "推广单元ID", "消费额", "点击量",
                  "浏览量", "跳出率", "平均访问时长"]
    miss_table(s3, "Sheet3清洗前")
    for c in ["关键词ID", "方案ID", "推广单元ID"]:
        s3[c] = s3[c].astype("int64").astype(str)
    s3["跳出率"] = pd.to_numeric(s3["跳出率"].replace("/", pd.NA), errors="coerce").round(ROUND)
    s3["平均停留秒"] = (pd.to_timedelta(s3["平均访问时长"].astype(str).str.strip().replace("/", pd.NA),
                                       errors="coerce").dt.total_seconds().round(0).astype("Int64"))
    s3 = s3.drop(columns=["平均访问时长"])
    s3["是否零点击词"] = ((s3["消费额"] == 0) & (s3["点击量"] == 0)).astype(int)
    s3["CPC"] = div(s3["消费额"], s3["点击量"])
    s3["浏览深度"] = div(s3["浏览量"], s3["点击量"])
    miss_table(s3, "Sheet3清洗后")

    # ---------- 时间维度表 ----------
    dates = pd.date_range("2025-01-01", "2025-12-31")
    week = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    dim = pd.DataFrame({"日期": dates.strftime("%Y-%m-%d")})
    dim["星期"] = [week[d.weekday()] for d in dates]
    dim["月份"] = dates.month
    dim["是否周末"] = (dates.weekday >= 5).astype(int)
    dim["三态标签"] = ["放假" if d.date() in HOLIDAYS else ("补班" if d.date() in MAKEUP_WORK else "正常")
                       for d in dates]
    miss_table(dim, "时间维度表")

    # ---------- 对账 ----------
    print(f"对账: Sheet1消费总额={raw1.iloc[:, 5].sum():.2f}  Sheet3消费总额={raw3.iloc[:, 4].sum():.2f}  "
          f"清洗后Sheet1={s1['消费额'].sum():.2f}")
    print(f"需关注: 零点击词={(s3['是否零点击词'] == 1).sum()}  "
          f"有展现零点击行={((s1['展现量'] > 0) & (s1['点击量'] == 0)).sum()}  "
          f"有点击零浏览词={(((s3['点击量'] > 0) & (s3['浏览量'] == 0))).sum()}")

    # ---------- 落盘 ----------
    for df, name in [(s1, "sheet1_投放记录_clean"), (s2, "sheet2_日注册_clean"),
                     (s3, "sheet3_关键词_clean"), (dim, "dim_date_时间维度")]:
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT / "clean_data.xlsx", engine="openpyxl") as w:
        s1.to_excel(w, sheet_name="投放记录", index=False)
        s2.to_excel(w, sheet_name="日注册", index=False)
        s3.to_excel(w, sheet_name="关键词", index=False)
        dim.to_excel(w, sheet_name="时间维度", index=False)
    print("输出完成:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    sys.exit(main())
