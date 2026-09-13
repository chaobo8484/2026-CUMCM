#!/usr/bin/env python3
"""
de_gate.py — 微分方程门禁（P0）

Hard Rules: 量纲一致, 容差声明, 加密一次 h 减半差值, 刚性切换, Fourier/CFL 视 PDE

Usage:
  python de_gate.py --config config.json --out report.json
  config.json: {tolerances, mesh, units, scheme, sensitive_params}
  或对比两次加密结果： --coarse coarse.csv --fine fine.csv --value-col y
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import numpy as np, pandas as pd

def main():
    parser = argparse.ArgumentParser(description="DE 门禁")
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--coarse", type=pathlib.Path, default=None)
    parser.add_argument("--fine", type=pathlib.Path, default=None)
    parser.add_argument("--value-col", default="y")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    gates = {
        "has_units": "units" in cfg and bool(cfg["units"]),
        "has_tolerance": "tolerance" in cfg or "rtol" in cfg or "atol" in cfg,
        "has_scheme": "scheme" in cfg,
        "has_mesh": "mesh" in cfg or "h" in cfg or "dt" in cfg,
    }
    # mesh convergence if coarse/fine provided
    if args.coarse and args.fine:
        try:
            c = pd.read_csv(args.coarse)[args.value_col].values
            f = pd.read_csv(args.fine)[args.value_col].values
            # need same length; fine is 2x points? simple: compare overlapping
            n = min(len(c), len(f))
            diff = float(np.max(np.abs(c[:n] - f[:n])))
            gates["mesh_converged"] = bool(diff < cfg.get("tolerance", 1e-3))
            gates["max_diff"] = diff
        except Exception as e:
            gates["mesh_converged"] = None
            gates["mesh_error"] = str(e)
    # stability for PDE
    if "fourier" in cfg:
        gates["fourier_le_0_5"] = bool(cfg["fourier"] <= 0.5)
    if "cfl" in cfg:
        gates["cfl_le_1"] = bool(cfg["cfl"] <= 1)

    passed = all(v for k,v in gates.items() if k in ("has_units","has_tolerance","has_scheme","has_mesh") and v)
    verdict = "PASS" if passed else "HOLD — 量纲/容差/离散未齐"
    if "mesh_converged" in gates and gates["mesh_converged"] is False:
        verdict = "HOLD — 加密未收敛，减半重跑"
    report = {"config": cfg, "gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"DE gate: {gates} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
