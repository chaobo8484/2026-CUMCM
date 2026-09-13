# -*- coding: utf-8 -*-
"""Q4 s4 v2: Bootstrap2000 -> 逐记录80%经验区间 -> result4.xlsx双表 + 总量区间.
单循环: 分记录块抽样, 批次内以"抽样均值对准模型中心"做比例校正 (保形状、定中心),
再求10%/90%分位; 总量区间由校正后抽样加总的分位给出. seed=2026."""
import gc
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(r"C:\Users\ZhangChaobo\Desktop\CUMCM2026Problems")
E = ROOT / "E题"
DD = E / "q4" / "data_Q4"
RNG = np.random.default_rng(2026)
NBOOT = 2000

alloc = pd.read_csv(DD / "lp_alloc.csv", encoding="utf-8-sig")
resid = pd.read_csv(DD / "fe_resid.csv", encoding="utf-8-sig")
lagfit = pd.read_csv(DD / "lag_fit.csv", encoding="utf-8-sig")
d3 = pd.read_csv(E / "clean_data" / "sheet3_关键词_clean.csv", encoding="utf-8-sig")

p_cpc = resid["resid_lcpc"].dropna().to_numpy()
p_ctr = resid["resid_lctr"].dropna().to_numpy()
p_pos = resid["resid_pos"].dropna().to_numpy()
kd = d3[(d3["点击量"] > 0) & (d3["浏览量"] > 0)].copy()
kd["ld"] = np.log(kd["浏览量"] / kd["点击量"])
kd["ld_u"] = kd.groupby("推广单元ID")["ld"].transform("mean")
p_dep = (kd["ld"] - kd["ld_u"]).dropna().to_numpy()
lf = lagfit[(lagfit["Rhat"] > 5) & (lagfit["新注册数"] > 0)].copy()
p_reg = np.log(lf["新注册数"] / lf["Rhat"]).dropna().to_numpy()
# 乘性池去偏: E[exp]=1
for _n in ["p_cpc", "p_dep", "p_reg"]:
    v = eval(_n)
    exec(f"{_n} = v - float(np.log(np.mean(np.exp(v))))")
print("pools: cpc=%d ctr=%d pos=%d depth=%d reg=%d" % (
    len(p_cpc), len(p_ctr), len(p_pos), len(p_dep), len(p_reg)))

b = alloc["投入金额"].to_numpy()
K0 = alloc["预期点击量"].to_numpy()
d0 = alloc["预期浏览量"].to_numpy() / np.maximum(K0, 1e-12)
cpc0 = alloc["cpc_cal"].to_numpy()
ctr0 = np.clip(alloc["ctr_cal"].to_numpy(), 1e-6, 1 - 1e-6)
pos0 = alloc["预期展位"].to_numpy()
RHO = float(alloc["预期注册量"].sum() / alloc["预期点击量"].sum())
N = len(alloc)
lc0 = np.log(ctr0 / (1 - ctr0))
bid_c = b / np.maximum(K0, 1e-12)
imp_c = K0 / np.maximum(ctr0, 1e-9)
V_c = alloc["预期浏览量"].to_numpy()
R_c = alloc["预期注册量"].to_numpy()
CEN = [bid_c, imp_c, pos0, K0, V_c, R_c]

qlo = np.empty((N, 6))
qhi = np.empty((N, 6))
TOT = {k: np.zeros(NBOOT) for k in (1, 3, 4, 5)}  # imp/clk/vie/reg 总量抽样(跨块累加)
TOT_POS = np.zeros(NBOOT)  # 投入加权展位分子
CH, JW = 250, 250
B_TOT = float(b.sum())


def draw(pool, size):
    return RNG.choice(pool, size=size, replace=True)


for j0 in range(0, N, JW):
    j1 = min(N, j0 + JW)
    BB = [np.empty((NBOOT, j1 - j0)) for _ in range(6)]
    for s in range(0, NBOOT, CH):
        m = min(CH, NBOOT - s)
        sl = np.s_[j0:j1]
        E1 = draw(p_cpc, (m, j1 - j0))
        E2 = draw(p_ctr, (m, j1 - j0))
        E3 = draw(p_pos, (m, j1 - j0))
        E4 = draw(p_dep, (m, j1 - j0))
        E5 = draw(p_reg, (m, j1 - j0))
        BB[0][s:s + m] = cpc0[sl][None, :] * np.exp(E1)
        ck = K0[sl][None, :] * np.exp(-E1)
        ct = 1 / (1 + np.exp(-(lc0[sl][None, :] + E2)))
        BB[3][s:s + m] = ck
        BB[1][s:s + m] = ck / np.maximum(ct, 1e-9)
        BB[2][s:s + m] = pos0[sl][None, :] + E3
        BB[4][s:s + m] = ck * d0[sl][None, :] * np.exp(E4)
        BB[5][s:s + m] = ck * RHO * np.exp(E5)
        del E1, E2, E3, E4, E5, ck, ct
    for k in range(6):
        mu = BB[k].mean(axis=0, keepdims=True)
        mu = np.where(mu == 0, 1.0, mu)
        BB[k] = BB[k] / mu * CEN[k][j0:j1][None, :]
        qlo[j0:j1, k] = np.percentile(BB[k], 10, axis=0)
        qhi[j0:j1, k] = np.percentile(BB[k], 90, axis=0)
        if k in TOT:
            TOT[k] += BB[k].sum(axis=1)
    TOT_POS += (b[j0:j1][None, :] * BB[2]).sum(axis=1)
    del BB
    gc.collect()

names = ["bid", "imp", "pos", "clk", "vie", "reg"]
cn = ["竞价代理值", "展现量", "展现位", "点击量", "浏览量", "注册量"]
rng_df = pd.DataFrame({"日期": alloc["日期"], "方案ID": alloc["方案ID"],
                       "推广单元": alloc["推广单元ID"], "关键词": alloc["关键词"]})
for i, c in enumerate(cn):
    rng_df[c + "_中心"] = CEN[i]
    rng_df[c + "_下限"] = qlo[:, i]
    rng_df[c + "_上限"] = qhi[:, i]
rng_df.to_csv(DD / "record_intervals.csv", index=False, encoding="utf-8-sig")

trows = []
clk_tot = TOT[3]
bid_tot = B_TOT / np.maximum(clk_tot, 1e-12)
pos_tot = TOT_POS / B_TOT
TD = {0: bid_tot, 1: TOT[1], 2: pos_tot, 3: TOT[3], 4: TOT[4], 5: TOT[5]}
TC = {0: B_TOT / float(K0.sum()), 1: float(imp_c.sum()),
      2: float((b * pos0).sum() / B_TOT), 3: float(K0.sum()),
      4: float(V_c.sum()), 5: float(R_c.sum())}
for i, c in enumerate(cn):
    v = TD[i]
    trows.append(dict(指标=c, 中心预测=TC[i],
                      下限=float(np.percentile(v, 10)),
                      上限=float(np.percentile(v, 90))))
tiv = pd.DataFrame(trows)
tiv.to_csv(DD / "total_intervals.csv", index=False, encoding="utf-8-sig")
print(tiv.to_string(index=False))

main = pd.DataFrame({
    "日期": alloc["日期"], "方案ID": alloc["方案ID"],
    "推广单元": alloc["推广单元ID"], "关键词": alloc["关键词"],
    "投入金额": alloc["投入金额"], "预期展位": alloc["预期展位"],
    "预期点击量": alloc["预期点击量"], "预期浏览量": alloc["预期浏览量"],
    "预期注册量": alloc["预期注册量"]})
with pd.ExcelWriter(DD / "result4.xlsx", engine="openpyxl") as xw:
    main.to_excel(xw, sheet_name="最优投放策略", index=False)
    rng_df.to_excel(xw, sheet_name="指标期望范围", index=False)
print("result4.xlsx rows:", len(main))
# 中心落在区间内断言
assert bool(((rng_df[[c + "_中心" for c in cn]].to_numpy() >= qlo - 1e-9).all()
             and (rng_df[[c + "_中心" for c in cn]].to_numpy() <= qhi + 1e-9).all()))
print("S4 OK")
