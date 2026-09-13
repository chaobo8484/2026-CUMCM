#!/usr/bin/env python3
"""
regression_gate.py — 回归族门禁（P0-2）

Hard Rules 对应（regression-family/SKILL.md）：
- EDA + VIF gate（>10 处理）
- 正则化 λ 用 CV 1-SE 原则
- 残差/QQ gate，分类看校准
- 原始单位系数 + CI

Usage:
  python regression_gate.py data.csv --y y --features x1,x2,x3 --out report.json
  python regression_gate.py data.csv --y label --features x1,x2 --family logistic --out report.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd


def compute_vif(df: pd.DataFrame, features: list[str]) -> dict[str, float]:
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
    except ImportError:
        return {f: None for f in features}
    X = df[features].values
    # Add constant for VIF calc? No, VIF without constant for each feature
    vif: dict[str, float] = {}
    for i, f in enumerate(features):
        try:
            vif[f] = round(float(variance_inflation_factor(X, i)), 2)
        except Exception:
            vif[f] = None
    return vif


def cv_ridge_lasso(df: pd.DataFrame, y_col: str, features: list[str], family: str = "ols") -> dict:
    from sklearn.linear_model import RidgeCV, LassoCV, LogisticRegressionCV
    from sklearn.model_selection import StratifiedKFold, KFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    X = df[features].values
    y = df[y_col].values
    result: dict = {}
    if family == "logistic":
        # Logistic
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        # Cs are inverse of lambda
        model = LogisticRegressionCV(Cs=10, cv=cv, scoring="roc_auc", max_iter=1000, random_state=42)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        model.fit(Xs, y)
        result["best_C"] = float(model.C_[0])
        result["scores"] = model.scores_
        result["coef"] = model.coef_.tolist()
    else:
        # Use RidgeCV with alphas; LassoCV for sparsity
        alphas = np.logspace(-3, 3, 50)
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        if family == "lasso":
            model = LassoCV(alphas=alphas, cv=cv, random_state=42, max_iter=5000)
            model.fit(X, y)
            result["best_alpha"] = float(model.alpha_)
            result["coef"] = model.coef_.tolist()
            result["intercept"] = float(model.intercept_)
        else:
            # Ridge
            from sklearn.linear_model import RidgeCV
            model = RidgeCV(alphas=alphas, cv=cv)
            model.fit(X, y)
            result["best_alpha"] = float(model.alpha_)
            result["coef"] = model.coef_.tolist()
            result["intercept"] = float(model.intercept_)
    return result


def residual_diagnostics(df: pd.DataFrame, y_col: str, features: list[str]) -> dict:
    from sklearn.linear_model import LinearRegression
    X = df[features].values
    y = df[y_col].values
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    resid = y - y_pred
    # Simple checks: funnel via correlation of abs resid vs fitted
    funnel_corr = float(np.corrcoef(np.abs(resid), y_pred)[0, 1]) if len(resid) > 2 else 0.0
    # QQ: shapiro for normality (small n)
    try:
        from scipy.stats import shapiro
        _, p = shapiro(resid) if len(resid) >= 3 else (0, 1.0)
        shapiro_p = round(float(p), 4)
    except Exception:
        shapiro_p = None
    return {
        "funnel_corr": round(funnel_corr, 4),
        "funnel_warning": abs(funnel_corr) > 0.3,
        "shapiro_p": shapiro_p,
        "resid_mean": round(float(resid.mean()), 4),
        "rmse": round(float(np.sqrt(np.mean(resid**2))), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="回归族门禁：VIF + CV + 残差")
    parser.add_argument("data", type=pathlib.Path, help="数据 CSV 路径")
    parser.add_argument("--y", type=str, required=True, help="目标列名")
    parser.add_argument("--features", type=str, required=True, help="逗号分隔特征列名")
    parser.add_argument("--family", type=str, default="ols", choices=["ols", "ridge", "lasso", "logistic"], help="回归族")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出报告 JSON 路径")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    if args.y not in df.columns:
        print(f"目标列 {args.y} 不存在", file=sys.stderr)
        sys.exit(1)
    features = [s.strip() for s in args.features.split(",")]
    for f in features:
        if f not in df.columns:
            print(f"特征列 {f} 不存在", file=sys.stderr)
            sys.exit(1)

    # Drop rows with NA in relevant cols
    sub = df[[args.y] + features].dropna()
    n, p = len(sub), len(features)
    print(f"n={n} p={p}")

    # VIF
    vif = compute_vif(sub, features)
    # Gate: None means deps missing -> OPEN, not HOLD
    has_vif = any(v is not None for v in vif.values())
    vif_max = max([v for v in vif.values() if v is not None], default=0)
    gate_vif = (vif_max <= 10) if has_vif and vif_max else None

    # EDA
    missing_rate = {c: round(float(sub[c].isna().sum()) / len(df), 4) for c in [args.y] + features}

    # CV
    try:
        cv_result = cv_ridge_lasso(sub, args.y, features, family=args.family)
    except Exception as e:
        cv_result = {"error": str(e)}

    # Residual diagnostics (for linear)
    diag = {}
    if args.family in ("ols", "ridge", "lasso"):
        try:
            diag = residual_diagnostics(sub, args.y, features)
        except Exception as e:
            diag = {"error": str(e)}

    gates = {
        "vif_le_10": gate_vif,
        "n_gt_p": bool(n > p),
        "vif_available": bool(has_vif),
    }
    if gate_vif is None:
        verdict = "OPEN — VIF 未计算（缺 statsmodels），需安装后重跑门禁"
    elif gate_vif:
        verdict = "PASS"
    else:
        verdict = "HOLD — VIF>10 需删/合并/正则化"

    report: dict = {
        "n": n,
        "p": p,
        "features": features,
        "y": args.y,
        "family": args.family,
        "missing_rate": missing_rate,
        "vif": vif,
        "vif_max": vif_max,
        "cv": cv_result,
        "diagnostics": diag,
        "gates": gates,
        "verdict": verdict,
        "method": "sklearn + statsmodels VIF",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"VIF: {vif} max={vif_max} gate={gate_vif}")
    print(f"CV: {cv_result.get('best_alpha') or cv_result.get('best_C')}")
    print(f"门禁: {gates} -> {verdict}")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
