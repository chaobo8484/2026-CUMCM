#!/usr/bin/env python3
"""
topsis_gate.py — 熵权 TOPSIS 门禁（P0-2）

Hard Rules 对应（evaluation-entropy-topsis/SKILL.md）：
- 方向声明 + 正向化显式
- 熵权 w 加总 1，四位小数
- TOPSIS 贴近度 C_i 排序
- 稳健性：逐个剔除 + 权重扰动

Usage:
  python topsis_gate.py data.csv --directions +,-,target:7 --target-values ,,7 --out report.json
  data.csv: 第一列为schemes名，其余列为指标
  --directions: 每列方向，+ 效益型, - 成本型, target 中间型（需配合 --target-values）
  示例：
    schemes,营收,污染,满意度
    A,100,20,8
    B,120,30,6
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd


def forward_transform(X: np.ndarray, directions: list[str], target_vals: list[float | None]) -> np.ndarray:
    m, n = X.shape
    Xp = np.zeros_like(X, dtype=float)
    for j in range(n):
        col = X[:, j]
        d = directions[j].strip()
        if d == "+":
            Xp[:, j] = col
        elif d == "-":
            # cost -> max - x (strictly positive handling: if max==min, handle zero variance later)
            Xp[:, j] = col.max() - col
            # If all equal, becomes zero -> flag later
        elif d.startswith("target"):
            # intermediate: 1 / (1 + |x - x*|)
            xv = target_vals[j]
            if xv is None:
                print(f"中间型指标第 {j+1} 列缺少 target 值", file=sys.stderr)
                sys.exit(1)
            Xp[:, j] = 1.0 / (1.0 + np.abs(col - xv))
        else:
            print(f"未知方向 '{d}'，用 + 或 - 或 target", file=sys.stderr)
            sys.exit(1)
    return Xp


def entropy_weights(Xp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (e, d, w). Xp is m x n positive after forward."""
    m, n = Xp.shape
    # Check zero variance or zero column sum
    col_sums = Xp.sum(axis=0)
    # p_ij
    # Handle zero column sum: if any col sum 0, that column is all zero after transform -> zero variance
    p = np.zeros_like(Xp, dtype=float)
    for j in range(n):
        if col_sums[j] == 0:
            p[:, j] = 0
        else:
            p[:, j] = Xp[:, j] / col_sums[j]
    # e_j = -(1/ln m) * sum p ln p, convention 0*ln0=0
    # Handle m==1 edge
    if m <= 1:
        e = np.zeros(n)
    else:
        k = 1.0 / np.log(m)
        e = np.zeros(n)
        for j in range(n):
            col_p = p[:, j]
            # 0*ln0 =0
            mask = col_p > 0
            e[j] = -k * np.sum(col_p[mask] * np.log(col_p[mask]))
    d = 1 - e
    d_sum = d.sum()
    if d_sum == 0:
        # All columns zero variance -> uniform? But per Hard Rules, zero variance should be removed.
        print("警告：所有列差异系数为 0（零方差），熵权无定义。请删除常量列。", file=sys.stderr)
        w = np.ones(n) / n
    else:
        w = d / d_sum
    return e, d, w


def topsis(Xp: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns (D_plus, D_minus, C, ranking_indices_desc)."""
    # Vector normalization
    norm = np.sqrt((Xp**2).sum(axis=0))
    # Avoid div by zero
    norm = np.where(norm == 0, 1, norm)
    Z = Xp / norm
    V = Z * w  # broadcasting
    v_plus = V.max(axis=0)
    v_minus = V.min(axis=0)
    D_plus = np.sqrt(((V - v_plus) ** 2).sum(axis=1))
    D_minus = np.sqrt(((V - v_minus) ** 2).sum(axis=1))
    denom = D_plus + D_minus
    # Handle denom 0 (duplicate rows)
    C = np.where(denom == 0, 0.5, D_minus / denom)
    ranking = np.argsort(-C)
    return D_plus, D_minus, C, ranking


def main() -> None:
    parser = argparse.ArgumentParser(description="熵权 TOPSIS 门禁")
    parser.add_argument("data", type=pathlib.Path, help="决策矩阵 CSV，第一列为schemes名")
    parser.add_argument("--directions", type=str, required=True, help="逗号分隔方向，如 +,-,+,target")
    parser.add_argument("--target-values", type=str, default=None, help="逗号分隔目标值，中间型必填，其余留空，如 ,,7.0")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出报告 JSON 路径")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    if df.shape[1] < 3:
        print("需要至少 1 列schemes名 + 2 列指标", file=sys.stderr)
        sys.exit(1)
    schemes = df.iloc[:, 0].astype(str).tolist()
    X = df.iloc[:, 1:].values.astype(float)
    m, n = X.shape
    if m < 3:
        print(f"schemes数 m={m} <3，排序无意义（Hard Rules）", file=sys.stderr)
    if n < 2:
        print(f"指标数 n={n} <2", file=sys.stderr)

    directions = [s.strip() for s in args.directions.split(",")]
    if len(directions) != n:
        print(f"directions 长度 {len(directions)} != 指标数 {n}", file=sys.stderr)
        sys.exit(1)
    target_vals: list[float | None] = [None] * n
    if args.target_values:
        parts = [s.strip() for s in args.target_values.split(",")]
        # Pad to n
        parts += [""] * (n - len(parts))
        for i, p in enumerate(parts[:n]):
            if p == "" or p.lower() == "none":
                target_vals[i] = None
            else:
                try:
                    target_vals[i] = float(p)
                except ValueError:
                    print(f"target 值解析失败: {p}", file=sys.stderr)
                    sys.exit(1)

    # Zero variance check
    zero_var_cols = [df.columns[1 + j] for j in range(n) if X[:, j].max() == X[:, j].min()]
    if zero_var_cols:
        print(f"警告：零方差列 {zero_var_cols} 熵权无定义，建议删除", file=sys.stderr)

    Xp = forward_transform(X, directions, target_vals)
    e, d, w = entropy_weights(Xp)

    # Gate: weights sum 1
    assert abs(w.sum() - 1.0) < 1e-9

    D_plus, D_minus, C, ranking = topsis(Xp, w)

    # Check duplicate rows gate
    dup_gate = (D_plus + D_minus) > 0
    if not dup_gate.all():
        print("警告：存在重复行schemes，D+ + D- =0，请合并重复行", file=sys.stderr)

    # Robustness: leave-one-out and weight perturbation
    loo_flips: list[dict] = []
    winner = int(ranking[0])
    for j in range(n):
        # Remove column j
        mask = [k for k in range(n) if k != j]
        if not mask:
            continue
        Xp_sub = Xp[:, mask]
        w_sub_e, w_sub_d, w_sub = entropy_weights(Xp_sub)
        Dp2, Dm2, C2, rank2 = topsis(Xp_sub, w_sub)
        if int(rank2[0]) != winner:
            loo_flips.append({"removed": df.columns[1 + j], "new_winner": schemes[int(rank2[0])], "old_winner": schemes[winner]})

    # Weight perturbation ±10% on top-2 weights
    sorted_w_idx = np.argsort(-w)
    perturb_flips: list[dict] = []
    for idx in sorted_w_idx[:2]:
        for delta in [0.10, -0.10]:
            w_pert = w.copy()
            w_pert[idx] *= (1 + delta)
            w_pert = w_pert / w_pert.sum()
            _, _, C_pert, rank_pert = topsis(Xp, w_pert)
            if int(rank_pert[0]) != winner:
                perturb_flips.append({"perturbed": df.columns[1 + idx], "delta": delta, "new_winner": schemes[int(rank_pert[0])]})

    report: dict = {
        "m": m,
        "n": n,
        "schemes": schemes,
        "indicators": list(df.columns[1:]),
        "directions": directions,
        "target_values": target_vals,
        "zero_variance_columns": zero_var_cols,
        "forward_method": "效益型原值; 成本型 max-x; 中间型 1/(1+|x-x*|)",
        "weights": {
            df.columns[1 + j]: {"e": round(float(e[j]), 4), "d": round(float(d[j]), 4), "w": round(float(w[j]), 4)}
            for j in range(n)
        },
        "w_sum": round(float(w.sum()), 4),
        "w_dominant": df.columns[1 + int(sorted_w_idx[0])] if n else None,
        "topsis": {
            schemes[i]: {"D_plus": round(float(D_plus[i]), 4), "D_minus": round(float(D_minus[i]), 4), "C": round(float(C[i]), 4)}
            for i in range(m)
        },
        "ranking": [schemes[int(r)] for r in ranking],
        "C_ranking": [round(float(C[int(r)]), 4) for r in ranking],
        "robustness": {
            "leave_one_out_flips": loo_flips,
            "weight_perturb_flips": perturb_flips,
            "winner": schemes[winner],
        },
        "gates": {
            "w_sum_1": bool(abs(w.sum() - 1.0) < 1e-6),
            "no_zero_variance": bool(len(zero_var_cols) == 0),
            "no_duplicate_rows": bool(dup_gate.all()),
        },
        "method": "entropy weights + vector normalization TOPSIS",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"熵权 TOPSIS: m={m} n={n} 权重和={w.sum():.4f}")
    print(f"权重: { {df.columns[1+j]: round(float(w[j]),4) for j in range(n)} }")
    print(f"排序: {report['ranking']}")
    if loo_flips:
        print("剔除翻盘:")
        for fl in loo_flips:
            print(f"  去掉 {fl['removed']} -> 赢家 {fl['new_winner']}")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
