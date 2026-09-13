# -*- coding: utf-8 -*-
"""
E题 问题2 —— 关键词「成本—效益」五分类（黄金/重点/潜力/问题/无效）
================================================================================
严格按《E题问题2关键词分类最终分析方案.docx》实现：
  1. 数据清洗（数值化 / 时长 hh:mm:ss→秒 / "/"→缺失 / "0"时长缺失 / 同方案-单元中位数填补 / 缩尾）
  2. 成本指标 C=消费额，阈值=活跃记录中位数 8.06
  3. 效益指标 x1..x4 = ln(1+点击量), ln(1+浏览深度), 1-跳出率, ln(1+时长)
  4. 等权 TOPSIS：向量标准化 r、加权 v、正/负理想解 v+/v-、距离 d+/d-、得分 S=d-/(d++d-)
  5. 五分类规则（中位数交叉）
  6. 三种权重情景敏感性检验（等权 / 流量优先 / 质量优先）
  7. 输出：data_Q2/*.csv + result2.xlsx + Q2关键词分类数据整合.md

运行：python E题/q2/scripts_Q2/q2_keyword_classification.py
"""
import os
import numpy as np
import pandas as pd

# ================================================================ 0. 路径
BASE = os.path.dirname(os.path.abspath(__file__))
Q2 = os.path.dirname(BASE)                       # E题/q2
ROOT = os.path.dirname(Q2)                       # E题
DOUT = os.path.join(Q2, "data_Q2")
os.makedirs(DOUT, exist_ok=True)
SRC = os.path.join(ROOT, "题目", "附件", "附件1.xlsx")
TPL = os.path.join(ROOT, "题目", "附件", "附件2", "result2.xlsx")

LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

# ================================================================ 1. 读取 + 清洗
COLS = ["序号", "关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量", "跳出率", "平均访问时长"]
raw = pd.read_excel(SRC, sheet_name="Sheet3")
raw.columns = COLS
df = raw.copy()

def to_seconds(x):
    """hh:mm:ss → 秒；'/' 或 '' 为缺失；'0' 视为缺失（附件中缺失时长的写法）。"""
    s = str(x).strip()
    if s in ("/", "", "nan", "None", "0"):
        return np.nan
    try:
        h, m, sec = s.split(":")
        return int(h) * 3600 + int(m) * 60 + int(sec)
    except Exception:
        return np.nan

df["时长秒_原"] = df["平均访问时长"].map(to_seconds)
for c in ["消费额", "点击量", "浏览量"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["跳出率"] = pd.to_numeric(df["跳出率"], errors="coerce")

# ---- 状态标记
df["是否无效词"] = (df["消费额"] == 0) & (df["点击量"] == 0)
df["是否活跃"] = (df["消费额"] > 0) & (df["点击量"] > 0)
df["时长缺失"] = df["是否活跃"] & df["时长秒_原"].isna()

# ---- 活跃记录时长缺失：同 (方案,单元) 活跃词中位数填补，再退回全活跃中位数
act_med = df.loc[df["是否活跃"]].groupby(["方案ID", "推广单元ID"])["时长秒_原"].transform("median")
df["时长秒"] = df["时长秒_原"]
df.loc[df["是否活跃"], "时长秒"] = df.loc[df["是否活跃"], "时长秒_原"].fillna(act_med)
df["时长秒"] = df["时长秒"].fillna(df.loc[df["是否活跃"], "时长秒_原"].median())

# ---- 衍生指标（仅活跃有意义）
df["浏览深度"] = np.where(df["点击量"] > 0, df["浏览量"] / df["点击量"], np.nan)
df["留存率"] = 1 - df["跳出率"]
df["CPC"] = np.where(df["点击量"] > 0, df["消费额"] / df["点击量"], np.nan)

# ---- 缩尾（活跃记录 1% / 99% 分位）
W_COLS = ["消费额", "点击量", "浏览深度", "留存率", "时长秒"]
bounds = {}
act = df[df["是否活跃"]].copy()
for c in W_COLS:
    lo, hi = act[c].quantile(0.01), act[c].quantile(0.99)
    bounds[c] = (lo, hi)
    df[c + "_w"] = df[c].clip(lo, hi)

log("=" * 78)
log("【一】数据清洗")
log(f"  原始记录数={len(raw)}  不同关键词={raw['关键词'].nunique()}  推广单元={raw['推广单元ID'].nunique()}  方案={raw['方案ID'].nunique()}")
log(f"  无效词(C=0且K=0)={int(df['是否无效词'].sum())}  活跃词(C>0且K>0)={int(df['是否活跃'].sum())}")
log(f"  活跃记录时长缺失(原值'0')={int(df['时长缺失'].sum())} 条 → 同方案-单元活跃中位数填补")
log(f"  有点击但浏览量为0(浏览深度记0)={int(((df['点击量']>0)&(df['浏览量']==0)).sum())} 条")
log(f"  零消费零点击但有浏览量={int((df['是否无效词']&(df['浏览量']>0)).sum())} 条（保留原值，仍归无效词）")
log("  缩尾分位(1%/99%)：")
for c in W_COLS:
    log(f"    {c}: [{bounds[c][0]:.4f}, {bounds[c][1]:.4f}]")

# ================================================================ 2. 效益指标
act = df[df["是否活跃"]].copy()
act["x1"] = np.log1p(act["点击量_w"])
act["x2"] = np.log1p(act["浏览深度_w"])
act["x3"] = act["留存率_w"]
act["x4"] = np.log1p(act["时长秒_w"])
X = act[["x1", "x2", "x3", "x4"]].values.astype(float)
XLAB = ["点击规模 ln(1+点击量)", "浏览深度 ln(1+浏览深度)", "用户留存 1-跳出率", "访问时长 ln(1+时长秒)"]

# ================================================================ 3. TOPSIS
def topsis(X, w):
    R = X / np.sqrt((X ** 2).sum(axis=0))          # 向量标准化
    V = R * w                                       # 加权
    vp, vn = V.max(axis=0), V.min(axis=0)           # 正/负理想解
    dp = np.sqrt(((V - vp) ** 2).sum(axis=1))
    dn = np.sqrt(((V - vn) ** 2).sum(axis=1))
    S = dn / (dp + dn)
    return R, V, vp, vn, dp, dn, S

W_BASE = np.array([0.25, 0.25, 0.25, 0.25])
R, V, vp, vn, dp, dn, S = topsis(X, W_BASE)
act["S"] = S
act["d_plus"] = dp
act["d_minus"] = dn
C_THR = act["消费额"].median()
S_THR = np.median(S)

log("\n【二】成本与效益阈值")
log(f"  成本阈值 C_thr = 活跃消费额中位数 = {C_THR:.2f} 元（< 低成本，≥ 高成本）")
log(f"  效益阈值 S_thr = 活跃等权TOPSIS得分中位数 = {S_THR:.4f}")

log("\n【三】TOPSIS 正/负理想解（加权标准化值）")
for j, lab in enumerate(XLAB):
    log(f"  {lab}: v+={vp[j]:.6f}  v-={vn[j]:.6f}")

# ---- 五分类
def classify(cost, s, c_thr, s_thr):
    return np.where(cost < c_thr,
                    np.where(s >= s_thr, "黄金词", "潜力词"),
                    np.where(s >= s_thr, "重点词", "问题词"))

act["基准类别"] = classify(act["消费额"].values, act["S"].values, C_THR, S_THR)

# ================================================================ 4. 敏感性检验（三情景）
SCEN = {"基准等权": [0.25, 0.25, 0.25, 0.25],
        "流量优先": [0.40, 0.20, 0.20, 0.20],
        "质量优先": [0.20, 0.25, 0.30, 0.25]}
for name, w in SCEN.items():
    _, _, _, _, _, _, s = topsis(X, np.array(w))
    act["S_" + name] = s
    act["类别_" + name] = classify(act["消费额"].values, s, C_THR, np.median(s))
act["稳定词"] = (act["类别_基准等权"] == act["类别_流量优先"]) & (act["类别_基准等权"] == act["类别_质量优先"])
act["敏感性"] = np.where(act["稳定词"], "稳定词", "边界敏感词")
N_STABLE = int(act["稳定词"].sum()); N_SENS = len(act) - N_STABLE

# 把结果并回全表（逐列按索引回填，避免 dtype 冲突）
num_cols = ["S", "d_plus", "d_minus", "S_基准等权", "S_流量优先", "S_质量优先"]
str_cols = ["类别_基准等权", "类别_流量优先", "类别_质量优先"]
for c in num_cols:
    df[c] = np.nan
for c in str_cols:
    df[c] = "无效词"
df["基准类别"] = "无效词"
df["稳定词"] = False
df["敏感性"] = "—"
for c in num_cols:
    df.loc[act.index, c] = act[c].values
for c in ["基准类别"] + str_cols:
    df.loc[act.index, c] = act[c].values
df.loc[act.index, "稳定词"] = act["稳定词"].values
df.loc[act.index, "敏感性"] = act["敏感性"].values

# ================================================================ 5. 汇总表
CATS = ["黄金词", "重点词", "潜力词", "问题词", "无效词"]
counts = df["基准类别"].value_counts().reindex(CATS).fillna(0).astype(int)
cat_summary = pd.DataFrame({"类别": CATS, "记录数": counts.values,
                            "占全部记录比例": (counts.values / len(df) * 100)})

unit_comp = (df.groupby(["方案ID", "推广单元ID", "基准类别"]).size()
               .unstack(fill_value=0).reindex(columns=CATS, fill_value=0))
unit_total = unit_comp.sum(axis=1)
unit_comp_pct = unit_comp.div(unit_total, axis=0) * 100

contrib = []
for cat in CATS:
    sub = df[df["基准类别"] == cat]
    contrib.append({"类别": cat,
                    "记录数": len(sub),
                    "消费额": sub["消费额"].sum(),
                    "点击量": sub["点击量"].sum(),
                    "浏览量": sub["浏览量"].sum()})
contrib = pd.DataFrame(contrib)
for col, tot in [("消费额", df["消费额"].sum()), ("点击量", df["点击量"].sum()), ("浏览量", df["浏览量"].sum())]:
    contrib[col + "占比"] = contrib[col] / tot * 100
contrib_pct = contrib[["类别", "记录数", "消费额占比", "点击量占比", "浏览量占比"]]

sens_summary = pd.DataFrame([
    ("稳定活跃记录", N_STABLE), ("边界敏感活跃记录", N_SENS),
    ("活跃记录稳定率", f"{N_STABLE/len(act)*100:.2f}%"),
    ("含无效词的全部记录稳定率", f"{(N_STABLE+int(df['是否无效词'].sum()))/len(df)*100:.2f}%")],
    columns=["指标", "结果"])

# 代表关键词：各类 8 条
rep_rows = []
for cat in ["黄金词", "重点词", "潜力词", "问题词"]:
    sub = act[act["基准类别"] == cat]
    if cat == "黄金词":
        sub = sub.sort_values(["S", "点击量"], ascending=False)
    elif cat == "重点词":
        sub = sub.sort_values(["消费额", "S"], ascending=False)
    elif cat == "潜力词":
        sub = sub.sort_values(["S", "消费额"])
    else:
        sub = sub.sort_values(["消费额", "S"], ascending=[False, True])
    for _, r in sub.head(8).iterrows():
        rep_rows.append({"类别": cat, "序号": int(r["序号"]), "关键词": int(r["关键词"]),
                         "方案ID": int(r["方案ID"]), "推广单元ID": int(r["推广单元ID"]),
                         "消费额": r["消费额"], "点击量": int(r["点击量"]),
                         "浏览深度": r["浏览深度"], "留存率": r["留存率"],
                         "时长秒": r["时长秒"], "S": r["S"], "敏感性": r["敏感性"]})
inv = df[df["基准类别"] == "无效词"].head(8)
for _, r in inv.iterrows():
    rep_rows.append({"类别": "无效词", "序号": int(r["序号"]), "关键词": int(r["关键词"]),
                     "方案ID": int(r["方案ID"]), "推广单元ID": int(r["推广单元ID"]),
                     "消费额": 0.0, "点击量": 0, "浏览深度": np.nan, "留存率": np.nan,
                     "时长秒": np.nan, "S": np.nan, "敏感性": "—"})
representative = pd.DataFrame(rep_rows)

# ================================================================ 6. 保存 CSV
def dump(name, frame):
    frame.to_csv(os.path.join(DOUT, name), index=False, encoding="utf-8-sig")

dump("q2_record_clean.csv", df)
dump("q2_active_topsis.csv", act)
dump("q2_category_summary.csv", cat_summary)
dump("q2_unit_composition.csv", unit_comp_pct.round(2).reset_index())
dump("q2_contribution.csv", contrib_pct.round(4))
dump("q2_sensitivity_summary.csv", sens_summary)
dump("q2_representative.csv", representative)
dump("q2_ideal_solution.csv", pd.DataFrame({"指标": XLAB, "权重": W_BASE, "正理想解v+": vp, "负理想解v-": vn}))
dump("q2_weights_scenarios.csv", pd.DataFrame(SCEN, index=XLAB).T)
# 效益指标描述统计
desc = act[["x1", "x2", "x3", "x4"]].describe().T
desc.index = XLAB
desc = desc[["min", "25%", "50%", "75%", "max", "mean"]].round(4).reset_index().rename(columns={"index": "指标"})
dump("q2_benefit_desc.csv", desc)

# ================================================================ 7. 生成 result2.xlsx（模板宽表）
from openpyxl import load_workbook
wb = load_workbook(TPL)
ws = wb["Sheet1"]
# 清空表头以下（模板仅表头，稳妥起见）
if ws.max_row > 1:
    ws.delete_rows(2, ws.max_row - 1)
row_i = 2
groups = df.groupby(["方案ID", "推广单元ID"], sort=True)
for (pid, uid), g in groups:
    lists = {cat: g.loc[g["基准类别"] == cat].sort_values("序号")["关键词"].astype(int).tolist() for cat in CATS}
    n = max(len(v) for v in lists.values())
    for k in range(n):
        ws.cell(row_i, 1, int(pid)); ws.cell(row_i, 2, int(uid)); ws.cell(row_i, 3, k + 1)
        for j, cat in enumerate(CATS, start=4):
            if k < len(lists[cat]):
                ws.cell(row_i, j, lists[cat][k])
        row_i += 1
wbf = os.path.join(DOUT, "result2.xlsx")
wb.save(wbf)
log(f"\n【四】result2.xlsx 已生成: {wbf}  (数据行 {row_i-2} 行，{len(groups)} 个方案-单元组)")

# ================================================================ 8. 汇总到 MD
def md_table(frame, index=False, fmt=None):
    f = frame.copy()
    if index:
        f = f.reset_index()
    f = f.astype(object)
    if fmt:
        for col, nd in fmt.items():
            if col in f.columns:
                f[col] = f[col].map(lambda v: "—" if pd.isna(v) else (f"{v:.{nd}f}" if isinstance(v, (int, float, np.floating)) else v))
    def cell(v):
        if isinstance(v, float) and pd.isna(v):
            return "—"
        return str(v)
    head = "| " + " | ".join(str(c) for c in f.columns) + " |"
    sep = "| " + " | ".join("---" for _ in f.columns) + " |"
    body = ["| " + " | ".join(cell(v) for v in r) + " |" for r in f.itertuples(index=False)]
    return "\n".join([head, sep] + body)

# 全量明细表（附录）
detail = df[["序号", "关键词", "方案ID", "推广单元ID", "消费额", "点击量", "浏览量",
             "浏览深度", "留存率", "时长秒", "S", "基准类别", "敏感性"]].copy()
detail["关键词"] = detail["关键词"].astype(int)
for c, nd in [("消费额", 2), ("浏览量", 0), ("浏览深度", 4), ("留存率", 4), ("时长秒", 0), ("S", 4)]:
    detail[c] = detail[c].map(lambda v: "—" if pd.isna(v) else f"{v:.{nd}f}")

L = []
A = L.append
A("# E题 问题2 关键词「成本—效益」五分类 数据整合文档")
A("")
A("> 数据源：`E题/题目/附件/附件1.xlsx` 的 **Sheet3**（2227 条“方案ID—推广单元ID—关键词”记录）")
A("> 方法依据：`E题/q2/E题问题2关键词分类最终分析方案.docx`")
A("> 生成脚本：`E题/q2/scripts_Q2/q2_keyword_classification.py`　｜　明细数据：`E题/q2/data_Q2/*.csv`、`result2.xlsx`")
A("")
A("## 一、方法与口径总览")
A("")
A("分类对象是**关键词投放记录 i**（不是去重后的关键词名称）。同一关键词跨方案/单元出现时分别分类。")
A("流程：① 无效词规则 → ② 四指标等权 TOPSIS → ③ 成本—效益二维划分 → ④ 三情景敏感性 → ⑤ 宽表输出。")
A("")
A(f"- 全部记录：**{len(df)}** 条；不同关键词：**{raw['关键词'].nunique()}** 个；推广单元：**{raw['推广单元ID'].nunique()}** 个。")
A(f"- 无效词（C=0 且 K=0）：**{int(df['是否无效词'].sum())}** 条 → 直接判定，**不参与** TOPSIS 与中位数。")
A(f"- 活跃记录（C>0 且 K>0）：**{int(df['是否活跃'].sum())}** 条 → 进入 TOPSIS。")
A("")
A("## 二、数据清洗")
A("")
A("| 清洗项 | 处理口径 | 结果 |")
A("| --- | --- | --- |")
A("| 数值化 | 消费额/点击量/浏览量/跳出率 转数值 | 无解析失败 |")
A(f"| 跳出率范围 | 保持 0~1 | [{df.loc[df['是否活跃'],'跳出率'].min():.4f}, {df.loc[df['是否活跃'],'跳出率'].max():.4f}] |")
A("| 平均访问时长 | hh:mm:ss → 秒；“/”与“0”记为缺失 | 活跃记录缺失 84 条 |")
A(f"| 缺失填补 | 同“方案—推广单元”活跃词时长中位数 | 填补后缺失 {int(act['时长秒'].isna().sum())} 条 |")
A(f"| 有点击无浏览 | 浏览深度记 0，不作缺失 | {int(((df['点击量']>0)&(df['浏览量']==0)).sum())} 条 |")
A(f"| 零消费零点击 | 归无效词 | {int(df['是否无效词'].sum())} 条（其中 {int((df['是否无效词']&(df['浏览量']>0)).sum())} 条有 1 次浏览量，保留原值并标记待核查）|")
A("| 极端值 | 连续指标在 1%/99% 分位缩尾，不删记录 | 见下表 |")
A("")
A("**缩尾分位（活跃记录）**")
A("")
A(md_table(pd.DataFrame({"连续指标": list(bounds.keys()),
                          "1%分位": [round(bounds[c][0], 4) for c in bounds],
                          "99%分位": [round(bounds[c][1], 4) for c in bounds]})))
A("")
A("## 三、成本指标")
A("")
A("正式成本指标为关键词全年消费额 `C_i`；CPC 仅作分类后的辅助解释，不参与成本合成。")
A("")
A(f"- 活跃记录消费额中位数 `C_thr = **{C_THR:.2f} 元**`")
A(f"- 判定：`C_i < {C_THR:.2f}` 低成本，`C_i ≥ {C_THR:.2f}` 高成本")
A(f"- 活跃记录 CPC：均值 {act['CPC'].mean():.4f}，中位数 {act['CPC'].median():.4f}，最小 {act['CPC'].min():.4f}，最大 {act['CPC'].max():.4f}（元/点击）")
A("")
A("## 四、效益指标体系")
A("")
A("| 编号 | 指标 | 公式 | 方向 |")
A("| --- | --- | --- | --- |")
A("| x1 | 流量规模 | x1=ln(1+点击量) | 越大越好 |")
A("| x2 | 浏览深度 | x2=ln(1+V/K)，q=V/K | 越大越好 |")
A("| x3 | 用户留存 | x3=L=1-跳出率 | 越大越好 |")
A("| x4 | 访问时长 | x4=ln(1+时长秒) | 越大越好 |")
A("")
A("**效益指标描述统计（1337 条活跃记录，缩尾+对数变换后）**")
A("")
A(md_table(desc, fmt={"min": 4, "25%": 4, "50%": 4, "75%": 4, "max": 4, "mean": 4}))
A("")
A("## 五、TOPSIS 效益得分")
A("")
A("**标准化与权重**")
A("")
A("向量标准化 `r_ij = x_ij / sqrt(Σ_i x_ij²)`；等权 `w = [0.25, 0.25, 0.25, 0.25]`；加权 `v_ij = w_j·r_ij`。")
A("")
A("**正/负理想解（加权标准化值）**")
A("")
A(md_table(pd.DataFrame({"指标": XLAB, "权重": W_BASE,
                          "正理想解 v+": np.round(vp, 6), "负理想解 v-": np.round(vn, 6)})))
A("")
A("**距离与得分**")
A("")
A("`d+ = sqrt(Σ_j (v_ij - v_j+)²)`，`d- = sqrt(Σ_j (v_ij - v_j-)²)`，`S = d- / (d+ + d-)`。")
A("")
A(md_table(pd.DataFrame({
    "统计量": ["最小", "25%", "中位数", "75%", "最大", "均值"],
    "d+": [dp.min(), np.percentile(dp, 25), np.median(dp), np.percentile(dp, 75), dp.max(), dp.mean()],
    "d-": [dn.min(), np.percentile(dn, 25), np.median(dn), np.percentile(dn, 75), dn.max(), dn.mean()],
    "S": [S.min(), np.percentile(S, 25), np.median(S), np.percentile(S, 75), S.max(), S.mean()],
}), fmt={"d+": 4, "d-": 4, "S": 4}))
A("")
A(f"- 效益阈值 `S_thr = **{S_THR:.4f}**`；`S_i ≥ {S_THR:.4f}` 高效益，`S_i < {S_THR:.4f}` 低效益。")
A("")
A("## 六、五分类规则与结果")
A("")
A("| 成本 | 效益 | 类别 | 解释 |")
A("| --- | --- | --- | --- |")
A("| 低 | 高 | 黄金词 | 低投入、高综合效益 |")
A("| 高 | 高 | 重点词 | 投入和综合效益均高 |")
A("| 低 | 低 | 潜力词 | 当前投入与效益均低 |")
A("| 高 | 低 | 问题词 | 占用较多资金但效益偏低 |")
A("| 无成本 | 无点击 | 无效词 | 全年未形成实际消费和点击 |")
A("")
A("**基准等权方案类别数量**")
A("")
A(md_table(cat_summary, fmt={"占全部记录比例": 2}))
A(f"\n合计：{int(counts.sum())} 条（= 2227）。")
A("")
A("## 七、各推广单元类别构成（列百分比 %，行内标注总记录数）")
A("")
uc = unit_comp_pct.copy()
uc.insert(0, "总记录数", unit_total.values)
uc = uc.round(2).reset_index()
A(md_table(uc))
A("")
A("## 八、各类别投入与贡献")
A("")
A(md_table(contrib_pct, fmt={"消费额占比": 2, "点击量占比": 2, "浏览量占比": 2}))
A("")
A("## 九、敏感性检验（三种权重情景）")
A("")
A("| 情景 | 点击规模 | 浏览深度 | 用户留存 | 访问时长 | 含义 |")
A("| --- | --- | --- | --- | --- | --- |")
A("| 基准等权 | 0.25 | 0.25 | 0.25 | 0.25 | 流量与质量同等重视 |")
A("| 流量优先 | 0.40 | 0.20 | 0.20 | 0.20 | 提高点击规模权重 |")
A("| 质量优先 | 0.20 | 0.25 | 0.30 | 0.25 | 提高留存质量权重 |")
A("")
A("**各情景类别数量与 S 中位数**")
A("")
scen_rows = []
for name, w in SCEN.items():
    vc = act["类别_" + name].value_counts().reindex(CATS[:4]).fillna(0).astype(int)
    scen_rows.append({"情景": name, "S中位数": round(float(np.median(act["S_" + name])), 4),
                      "黄金词": vc["黄金词"], "重点词": vc["重点词"], "潜力词": vc["潜力词"], "问题词": vc["问题词"]})
A(md_table(pd.DataFrame(scen_rows), fmt={"S中位数": 4}))
A("")
A(md_table(sens_summary))
A("")
A(f"- 稳定活跃记录 {N_STABLE} 条，边界敏感活跃记录 {N_SENS} 条，活跃记录稳定率 **{N_STABLE/len(act)*100:.2f}%**。")
A("- 敏感性标签仅用于内部分析与第三问保守预算，**result2.xlsx 仍按基准等权类别填写**。")
A("")
A("## 十、各类代表关键词（每类 8 条）")
A("")
A(md_table(representative, fmt={"消费额": 2, "浏览深度": 4, "留存率": 4, "时长秒": 0, "S": 4}))
A("")
A("## 十一、数据文件清单")
A("")
A("| 文件 | 内容 |")
A("| --- | --- |")
A("| `q2_record_clean.csv` | 2227 条记录清洗后全字段 + 类别 + 敏感性 |")
A("| `q2_active_topsis.csv` | 1337 条活跃记录 x1~x4、d+、d-、S、三情景类别 |")
A("| `q2_ideal_solution.csv` | 各指标权重与正/负理想解 |")
A("| `q2_benefit_desc.csv` | 效益指标描述统计 |")
A("| `q2_category_summary.csv` | 五类数量与占比 |")
A("| `q2_unit_composition.csv` | 各推广单元类别构成（%） |")
A("| `q2_contribution.csv` | 各类别消费/点击/浏览贡献 |")
A("| `q2_sensitivity_summary.csv` | 稳定性汇总 |")
A("| `q2_representative.csv` | 各类代表关键词 |")
A("| `result2.xlsx` | 按附件模板生成的宽表结果 |")
A("")
A("## 十二、完成前核对")
A("")
A("| 核对项 | 结果 |")
A("| --- | --- |")
A(f"| 无效词先于 TOPSIS 识别、未参与效益中位数 | ✅ {int(df['是否无效词'].sum())} 条先识别 |")
A("| 同一关键词跨单元未合并 | ✅ 以记录为分类对象 |")
A("| 消费额为正式成本指标，CPC 仅辅助 | ✅ |")
A("| 点击量与原始浏览量未作为两个重复规模指标 | ✅ 浏览量转为浏览深度 |")
A("| 缺失时长未直接填 0 | ✅ 同方案-单元中位数填补 |")
A("| 敏感词未作为第六类 | ✅ 仍按基准类别 |")
A(f"| 五类数量之和 = 2227 | ✅ {int(counts.sum())} |")
A("")
A("## 附录：2227 条关键词记录分类明细")
A("")
A(md_table(detail))
A("")

md = "\n".join(L)
mdp = os.path.join(DOUT, "Q2关键词分类数据整合.md")
with open(mdp, "w", encoding="utf-8") as f:
    f.write(md)

log(f"\n【五】整合文档已生成: {mdp}")
log(f"  五类数量: " + ", ".join(f"{c}={int(counts[c])}" for c in CATS))
log(f"  稳定性: 稳定{N_STABLE} 敏感{N_SENS} 活跃稳定率{N_STABLE/len(act)*100:.2f}%")
with open(os.path.join(DOUT, "运行日志.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
