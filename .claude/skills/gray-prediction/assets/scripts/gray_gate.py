#!/usr/bin/env python3
"""
gray_gate.py — GM(1,1) 门禁（P0）

Hard Rules 对应（gray-prediction/SKILL.md）：
- n=4-10, 级比 σ(k) 落 (e^{-2/(n+1)}, e^{2/(n+1)}) 覆盖率
- 发展系数 |a|<0.3 合理性
- 后验差比 C<0.35/P>0.95 等级
- 步长 ≤3

Usage:
  python gray_gate.py series.csv --value-col value --out report.json --steps 3
  series.csv 需一列数值，等间隔
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import numpy as np, pandas as pd

def level_ratio_gate(x: np.ndarray):
    n = len(x)
    low = np.exp(-2/(n+1)); high = np.exp(2/(n+1))
    sigmas = x[:-1] / x[1:]
    inside = (sigmas > low) & (sigmas < high)
    coverage = float(inside.mean())
    return sigmas.tolist(), float(low), float(high), coverage, inside.tolist()

def gm11(x: np.ndarray):
    n = len(x)
    x1 = np.cumsum(x)
    z = 0.5*(x1[1:] + x1[:-1])
    B = np.vstack((-z, np.ones(n-1))).T
    Y = x[1:]
    # least squares
    try:
        a_b, *_ = np.linalg.lstsq(B, Y, rcond=None)
    except Exception as e:
        return None, str(e)
    a, b = float(a_b[0]), float(a_b[1])
    # whiteness solution
    x1_hat = np.zeros(n)
    x1_hat[0] = x[0]
    for k in range(1, n):
        x1_hat[k] = (x[0] - b/a)*np.exp(-a*k) + b/a if a != 0 else x1[k-1] + b
    x_hat = np.zeros(n)
    x_hat[0] = x[0]
    x_hat[1:] = x1_hat[1:] - x1_hat[:-1]
    resid = x - x_hat
    S1 = float(x.std(ddof=0))
    S2 = float(resid.std(ddof=0))
    C = S2/S1 if S1 else 0
    # P: P(|eps - mean| < 0.6745 S1)
    mean_eps = resid.mean()
    P = float(((np.abs(resid - mean_eps) < 0.6745*S1).mean()))
    mre = float(np.mean(np.abs(resid/x)))
    if C < 0.35 and P > 0.95:
        grade = "好"
    elif C > 0.65 or P < 0.70:
        grade = "拒绝"
    else:
        grade = "勉强"
    return {"a":a,"b":b,"x_hat":x_hat.tolist(),"resid":resid.tolist(),"S1":S1,"S2":S2,"C":C,"P":P,"mre":mre,"grade":grade}, None

def main():
    parser = argparse.ArgumentParser(description="GM(1,1) 门禁")
    parser.add_argument("data", type=pathlib.Path, help="时序 CSV")
    parser.add_argument("--value-col", required=True)
    parser.add_argument("--steps", type=int, default=3, help="预测步长 1-3")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.data)
    if args.value_col not in df.columns:
        print(f"列 {args.value_col} 不存在", file=sys.stderr); sys.exit(1)
    x = df[args.value_col].astype(float).values
    n = len(x)
    gate_n = 4 <= n <= 10
    sigmas, low, high, coverage, inside = level_ratio_gate(x)
    gm, err = gm11(x)
    if gm is None:
        print(f"拟合失败: {err}", file=sys.stderr); sys.exit(1)
    gate_a = abs(gm["a"]) < 0.3
    gate_steps = args.steps <= 3
    grade = gm["grade"]
    gates = {
        "n_4_10": bool(gate_n),
        "level_ratio_coverage_ge_0_8": bool(coverage >= 0.8),
        "a_lt_0_3": bool(gate_a),
        "steps_le_3": bool(gate_steps),
        "grade_not_reject": grade != "拒绝",
    }
    passed = all(gates.values())
    report = {
        "n": n, "values": x.tolist(),
        "level_ratio": {"sigmas": [round(s,4) for s in sigmas], "interval": [round(low,4), round(high,4)], "coverage": round(coverage,4), "inside": inside},
        "gm": {"a": round(gm["a"],4), "b": round(gm["b"],4), "C": round(gm["C"],4), "P": round(gm["P"],4), "mre": round(gm["mre"],4), "grade": grade},
        "steps_requested": args.steps,
        "gates": gates,
        "verdict": "PASS" if passed else "HOLD — 级比/等级/步长未过",
        "method": "GM(1,1) 累加最小二乘",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"GM(1,1): n={n} coverage={coverage:.2f} a={gm['a']:.4f} C={gm['C']:.4f} P={gm['P']:.4f} grade={grade} [{report['verdict']}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
