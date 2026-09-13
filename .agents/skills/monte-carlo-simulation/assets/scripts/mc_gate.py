#!/usr/bin/env python3
"""
mc_gate.py — Monte Carlo 门禁（P0）

Hard Rules: 分布+来源, 相关性声明, 种子向量化, 收敛 ±2SE 对 log10(N), 稀有命中≥100

Usage:
  python mc_gate.py samples.csv --value-col est --se-col se --n-col N --out report.json --seed 42
  或 --trace trace.json (含 Ns, estimates, ses)
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import numpy as np, pandas as pd

def main():
    parser = argparse.ArgumentParser(description="MC 收敛门禁")
    parser.add_argument("data", type=pathlib.Path, help="trace CSV/JSON")
    parser.add_argument("--value-col", default="estimate")
    parser.add_argument("--se-col", default="se")
    parser.add_argument("--n-col", default="N")
    parser.add_argument("--hits-col", default=None, help="稀有事件命中数列")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    # Load
    if args.data.suffix == ".json":
        trace = json.loads(args.data.read_text(encoding="utf-8"))
        Ns = trace.get("Ns", []); ests = trace.get("estimates", []); ses = trace.get("ses", [])
    else:
        df = pd.read_csv(args.data)
        Ns = df[args.n_col].tolist() if args.n_col in df.columns else []
        ests = df[args.value_col].tolist() if args.value_col in df.columns else []
        ses = df[args.se_col].tolist() if args.se_col in df.columns else []
        hits = df[args.hits_col].tolist() if args.hits_col and args.hits_col in df.columns else None
    if not Ns or not ests:
        print("需 Ns / estimates 列", file=sys.stderr); sys.exit(1)
    Ns = np.array(Ns, dtype=float); ests = np.array(ests, dtype=float); ses = np.array(ses, dtype=float) if len(ses) else np.zeros_like(Ns)
    # Gate: last doubling interval flat? Check |est_last - est_prev| < 2*se_last
    if len(ests) >= 2:
        flat = abs(ests[-1] - ests[-2]) < 2*ses[-1]
    else:
        flat = False
    # Rare hits gate
    rare_gate = None
    if args.hits_col:
        df2 = pd.read_csv(args.data)
        if args.hits_col in df2.columns:
            rare_gate = bool(df2[args.hits_col].iloc[-1] >= 100)
    gates = {
        "has_seed": args.seed is not None,
        "has_trace": bool(len(Ns)>=2),
        "last_doubling_flat": bool(flat),
        "rare_hits_ge_100": rare_gate,
    }
    # verdict
    if not args.seed:
        verdict = "HOLD — 无种子不可复现"
    elif not flat:
        verdict = "HOLD — 收敛未平，继续翻倍"
    elif rare_gate is False:
        verdict = "HOLD — 稀有命中<100，需加 N 或重要性抽样"
    else:
        verdict = "PASS"
    report = {
        "Ns": Ns.tolist(), "estimates": ests.tolist(), "ses": ses.tolist(),
        "seed": args.seed,
        "gates": gates,
        "verdict": verdict,
        "method": "MC ±2SE 对 log10(N)",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"MC gate: flat={flat} seed={args.seed} rare={rare_gate} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
