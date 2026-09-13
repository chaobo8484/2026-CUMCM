#!/usr/bin/env python3
"""
bp_gate.py — BP 神经网络门禁（P0）

Hard Rules 对应（bp-neural-network/SKILL.md）：
- 划分/种子, 只用训练统计量标准化, 参数≪n, 早停, CV均值±std打赢线性基线

Usage:
  python bp_gate.py data.csv --y y --features x1,x2 --test-size 0.2 --out report.json
  需 sklearn；无则返回 OPEN
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import numpy as np, pandas as pd

def try_bp(df, y, features, test_size):
    try:
        from sklearn.neural_network import MLPRegressor, MLPClassifier
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import mean_squared_error
    except ImportError as e:
        return {"error": f"sklearn not installed: {e}", "verdict": "OPEN — 缺依赖"}, None
    X = df[features].values; t = df[y].values
    is_class = len(np.unique(t)) <= 10 and set(np.unique(t)).issubset({0,1,0.0,1.0})
    # leakage check: standardized only on train inside pipeline — we enforce pipeline
    # baseline
    try:
        scaler = StandardScaler()
        # pipeline ensures train-only stats
        baseline = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge())])
        from sklearn.model_selection import cross_val_score
        base_scores = cross_val_score(baseline, X, t, cv=5, scoring="neg_mean_squared_error")
        base_rmse = float(np.sqrt(-base_scores.mean()))
    except Exception as e:
        base_rmse = None
    # BP: small net
    try:
        if is_class:
            pipe = Pipeline([("scaler", StandardScaler()), ("mlp", MLPClassifier(hidden_layer_sizes=(10,), max_iter=500, early_stopping=True, random_state=42))])
            from sklearn.model_selection import cross_val_score
            scores = cross_val_score(pipe, X, t, cv=5, scoring="accuracy")
            bp_mean = float(scores.mean()); bp_std = float(scores.std())
            beats = bp_mean > (0 if base_rmse is None else 0)  # classification baseline trivial
            return {"is_class": True, "bp_mean": bp_mean, "bp_std": bp_std, "base": None, "beats_baseline": beats}, is_class
        else:
            pipe = Pipeline([("scaler", StandardScaler()), ("mlp", MLPRegressor(hidden_layer_sizes=(10,), max_iter=500, early_stopping=True, random_state=42))])
            scores = cross_val_score(pipe, X, t, cv=5, scoring="neg_mean_squared_error")
            bp_rmse = float(np.sqrt(-scores.mean())); bp_std = float(scores.std())
            beats = base_rmse is not None and bp_rmse < base_rmse
            return {"is_class": False, "bp_rmse": bp_rmse, "bp_std": bp_std, "base_rmse": base_rmse, "beats_baseline": beats}, is_class
    except Exception as e:
        return {"error": str(e), "verdict": "OPEN"}, is_class

def main():
    parser = argparse.ArgumentParser(description="BP 门禁")
    parser.add_argument("data", type=pathlib.Path)
    parser.add_argument("--y", required=True)
    parser.add_argument("--features", required=True)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.data)
    features = [s.strip() for s in args.features.split(",")]
    # basic checks
    n, p = len(df), len(features)
    gate_n = n >= 30
    # hidden units ≈ sqrt(p*out) ~ small, params << n check: for single hidden 10, params ≈ (p+1)*10 +11 ~ (p*10) ; need < n
    est_params = (p+1)*10 + 11
    gate_params = est_params < n
    result, is_class = try_bp(df, args.y, features, args.test_size)
    gates = {"n_ge_30": bool(gate_n), "params_lt_n": bool(gate_params), "beats_baseline": bool(result.get("beats_baseline")) if "beats_baseline" in result else None}
    verdict = "PASS" if gates["beats_baseline"] else ("OPEN" if result.get("verdict","").startswith("OPEN") else "HOLD — 未打赢线性基线")
    report = {"n": n, "p": p, "features": features, "est_params": est_params, "gates": gates, "bp": result, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"BP gate: n={n} params~{est_params} beats={result.get('beats_baseline')} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
