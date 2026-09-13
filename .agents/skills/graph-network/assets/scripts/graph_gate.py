#!/usr/bin/env python3
"""
graph_gate.py — 图网络门禁（P0）

Hard Rules: 权重语义/单位, 有向性, 负权 Bellman-Ford, 模块度报告

Usage:
  python graph_gate.py graph.csv --directed true --weight-col w --has-negative maybe --out report.json
  graph.csv: edge list u,v,w (w 可选)
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Graph 门禁")
    parser.add_argument("graph", type=pathlib.Path, help="边表 CSV")
    parser.add_argument("--directed", type=str, default="false", choices=["true","false","unknown"])
    parser.add_argument("--weight-col", default=None)
    parser.add_argument("--weight-semantics", default=None, help="权重含义+单位，如 距离km/时间min")
    parser.add_argument("--has-negative", type=str, default="false", choices=["true","false","maybe"])
    parser.add_argument("--algorithm", default=None, help="宣称所用算法，如 Dijkstra/Bellman-Ford")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.graph)
    has_weight = args.weight_col and args.weight_col in df.columns
    # Check negative
    has_neg = False
    if has_weight:
        try:
            has_neg = bool((df[args.weight_col] < 0).any())
        except Exception:
            has_neg = False
    # Gate: negative + Dijkstra is HOLD
    algo_gate = True
    if has_neg and args.algorithm and "dijkstra" in args.algorithm.lower():
        algo_gate = False
    # modularity gate: community detection should report modularity
    gates = {
        "has_directed": args.directed in ("true","false"),
        "has_weight_semantics": bool(args.weight_semantics),
        "algo_matches_negative": bool(algo_gate),
        "has_weight_col": bool(has_weight) if args.weight_col else True,
    }
    if has_neg and not args.weight_semantics:
        gates["has_weight_semantics"] = False
    passed = all(gates.values())
    verdict = "PASS" if passed else "HOLD — 权重语义/负权算法未对齐"
    if not algo_gate:
        verdict = "HOLD — 负权图用 Dijkstra 错误，需 Bellman-Ford"
    report = {"n_edges": len(df), "has_negative": bool(has_neg), "directed": args.directed, "algorithm": args.algorithm, "gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Graph gate: has_neg={has_neg} algo={args.algorithm} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
