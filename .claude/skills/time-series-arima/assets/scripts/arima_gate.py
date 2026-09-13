#!/usr/bin/env python3
"""
arima_gate.py — ARIMA/SARIMA 门禁（P0-2）

Hard Rules 对应（time-series-arima/SKILL.md）：
- n >=30, 等间隔
- 平稳性 ADF 检验定 d/D
- 残差 Ljung-Box p>0.05
- 滚动回测对朴素基线
- 预测带 80%/95% 区间

Usage:
  python arima_gate.py series.csv --date-col date --value-col value --out report.json
  series.csv 需含时间与数值列，等间隔
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd


def adf_test(series: pd.Series) -> dict:
    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        return {"error": "statsmodels not installed: pip install statsmodels", "stat": None, "p": None}
    # Drop NA
    s = series.dropna()
    if len(s) < 10:
        return {"error": "样本过少无法 ADF", "stat": None, "p": None}
    try:
        stat, p, *_ = adfuller(s, autolag="AIC")
        return {"stat": round(float(stat), 4), "p": round(float(p), 4), "stationary": p < 0.05}
    except Exception as e:
        return {"error": str(e), "stat": None, "p": None}


def ljung_box(resid: np.ndarray, lags: int = 10) -> dict:
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
    except ImportError:
        return {"error": "statsmodels not installed", "p": None}
    try:
        result = acorr_ljungbox(resid, lags=[lags], return_df=True)
        p = float(result["lb_pvalue"].iloc[0])
        return {"lags": lags, "p": round(p, 4), "white": p > 0.05}
    except Exception as e:
        return {"error": str(e), "p": None}


def fit_arima(series: pd.Series, order: tuple[int, int, int], seasonal_order: tuple[int, int, int, int] | None = None) -> dict:
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        return {"error": "statsmodels not installed"}
    try:
        if seasonal_order and seasonal_order != (0, 0, 0, 0):
            model = SARIMAX(series, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
        else:
            model = SARIMAX(series, order=order, enforce_stationarity=False, enforce_invertibility=False)
        res = model.fit(disp=False)
        return {
            "aic": round(float(res.aic), 2),
            "bic": round(float(res.bic), 2),
            "aicc": round(float(res.aic + (2 * res.params.shape[0] * (res.params.shape[0] + 1)) / max(len(series) - res.params.shape[0] - 1, 1)), 2),
            "params": res.params.to_dict(),
            "resid": res.resid.values,
            "fitted": res.fittedvalues.values,
        }
    except Exception as e:
        return {"error": str(e)}


def naive_forecast(series: pd.Series, h: int, seasonal_period: int | None = None) -> np.ndarray:
    """Seasonal naive if period given, else naive (last value)."""
    if seasonal_period and len(series) >= seasonal_period:
        # Use last seasonal_period values repeated
        last_season = series.values[-seasonal_period:]
        reps = (h // seasonal_period) + 1
        return np.tile(last_season, reps)[:h]
    return np.full(h, series.values[-1])


def rolling_backtest(series: pd.Series, order: tuple[int, int, int], seasonal_order: tuple[int, int, int, int] | None, h: int = 5) -> dict:
    """Last 20% as test, rolling one-step? Simplified: fit on train, forecast h, compare to naive."""
    n = len(series)
    test_h = max(h, n // 5)
    train = series.iloc[:-test_h]
    test = series.iloc[-test_h:]
    fit = fit_arima(train, order, seasonal_order)
    if "error" in fit:
        return {"error": fit["error"]}
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        if seasonal_order and seasonal_order != (0, 0, 0, 0):
            model = SARIMAX(train, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
        else:
            model = SARIMAX(train, order=order, enforce_stationarity=False, enforce_invertibility=False)
        res = model.fit(disp=False)
        pred = res.get_forecast(steps=test_h)
        mean = pred.predicted_mean.values
        rmse = float(np.sqrt(np.mean((mean - test.values) ** 2)))
        mae = float(np.mean(np.abs(mean - test.values)))
        naive = naive_forecast(train, test_h, seasonal_period=seasonal_order[3] if seasonal_order else None)
        rmse_naive = float(np.sqrt(np.mean((naive - test.values) ** 2)))
        return {"rmse": round(rmse, 4), "mae": round(mae, 4), "rmse_naive": round(rmse_naive, 4), "beats_naive": rmse < rmse_naive}
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="ARIMA 门禁：ADF + 拟合 + 残差 + 回测")
    parser.add_argument("data", type=pathlib.Path, help="时序 CSV 路径")
    parser.add_argument("--date-col", type=str, default=None, help="日期列名")
    parser.add_argument("--value-col", type=str, required=True, help="数值列名")
    parser.add_argument("--order", type=str, default="1,1,1", help="ARIMA order p,d,q 如 1,1,1")
    parser.add_argument("--seasonal-order", type=str, default="0,0,0,0", help="季节阶数 P,D,Q,s 如 1,1,1,12")
    parser.add_argument("--h", type=int, default=5, help="预测步长")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出报告 JSON 路径")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    if args.value_col not in df.columns:
        print(f"数值列 {args.value_col} 不存在，可用列: {list(df.columns)}", file=sys.stderr)
        sys.exit(1)
    # Handle date col
    if args.date_col and args.date_col in df.columns:
        try:
            df[args.date_col] = pd.to_datetime(df[args.date_col])
            df = df.sort_values(args.date_col)
        except Exception:
            pass
    series = df[args.value_col].astype(float)
    n = len(series)
    print(f"序列长度 n={n}")

    # Gate: n >=30
    gate_n = n >= 30
    if not gate_n:
        print(f"警告：n={n} <30，建议考虑 gray-prediction (Hard Rules #1)", file=sys.stderr)

    # ADF on raw and diff 1
    adf_raw = adf_test(series)
    adf_diff = adf_test(series.diff().dropna())

    order = tuple(int(x) for x in args.order.split(","))
    seasonal_order = tuple(int(x) for x in args.seasonal_order.split(","))
    if len(seasonal_order) != 4:
        print("seasonal-order 需 4 个数 P,D,Q,s", file=sys.stderr)
        sys.exit(1)

    # Fit
    fit = fit_arima(series, order, seasonal_order if seasonal_order != (0, 0, 0, 0) else None)
    lb = {"p": None, "white": None}
    if "resid" in fit:
        # Drop NaN residuals (initial)
        resid = pd.Series(fit["resid"]).dropna().values
        lags = min(10, max(n // 5, 5))
        lb = ljung_box(resid, lags=lags)

    # Backtest
    bt = rolling_backtest(series, order, seasonal_order if seasonal_order != (0, 0, 0, 0) else None, h=args.h)

    # Forecast with intervals
    forecast: dict = {}
    if "error" not in fit:
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            if seasonal_order != (0, 0, 0, 0):
                model = SARIMAX(series, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
            else:
                model = SARIMAX(series, order=order, enforce_stationarity=False, enforce_invertibility=False)
            res = model.fit(disp=False)
            pred = res.get_forecast(steps=args.h)
            mean = pred.predicted_mean.values
            ci80 = pred.conf_int(alpha=0.20).values  # 80%
            ci95 = pred.conf_int(alpha=0.05).values  # 95%
            forecast = {
                "mean": [round(float(x), 4) for x in mean],
                "ci80_low": [round(float(x[0]), 4) for x in ci80],
                "ci80_high": [round(float(x[1]), 4) for x in ci80],
                "ci95_low": [round(float(x[0]), 4) for x in ci95],
                "ci95_high": [round(float(x[1]), 4) for x in ci95],
            }
        except Exception as e:
            forecast = {"error": str(e)}

    gates = {
        "n_ge_30": gate_n,
        "adf_stationary_or_diff": adf_raw.get("stationary") or adf_diff.get("stationary"),
        "resid_white": lb.get("white"),
        "beats_naive": bt.get("beats_naive"),
    }
    # Overall verdict
    passed = all(v for v in [gate_n, lb.get("white")] if v is not None)

    report: dict = {
        "n": n,
        "order": order,
        "seasonal_order": seasonal_order,
        "adf_raw": adf_raw,
        "adf_diff1": adf_diff,
        "fit": {k: v for k, v in fit.items() if k not in ("resid", "fitted")},
        "ljung_box": lb,
        "backtest": bt,
        "forecast_h": args.h,
        "forecast": forecast,
        "gates": gates,
        "verdict": "PASS" if passed else "HOLD — 检查残差/回测/平稳性",
        "method": "statsmodels SARIMAX",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"ADF raw p={adf_raw.get('p')} diff p={adf_diff.get('p')}")
    print(f"Ljung-Box p={lb.get('p')} white={lb.get('white')}")
    print(f"回测 RMSE={bt.get('rmse')} vs naive {bt.get('rmse_naive')} beats={bt.get('beats_naive')}")
    print(f"门禁: {gates} -> {report['verdict']}")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
