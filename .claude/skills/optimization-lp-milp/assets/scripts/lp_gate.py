#!/usr/bin/env python3
"""
lp_gate.py — LP/MILP 证书门禁（P0）

Hard Rules: 状态 optimal, MIP gap, 求解器 name+version, IIS/无界诊断

Usage:
  python lp_gate.py --status optimal --gap 0.0 --solver HiGHS --version 1.5.3 --out report.json
  或 --solution solution.json (含 status,gap,solver,version, infeasible_check)
"""
from __future__ import annotations
import argparse, json, pathlib, sys

def main():
    parser = argparse.ArgumentParser(description="LP/MILP 证书门禁")
    parser.add_argument("--status", type=str, default=None, choices=["optimal","feasible","infeasible","unbounded","time_limit"])
    parser.add_argument("--gap", type=float, default=None)
    parser.add_argument("--solver", type=str, default=None)
    parser.add_argument("--version", type=str, default=None)
    parser.add_argument("--solution", type=pathlib.Path, default=None)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    status = args.status; gap = args.gap; solver = args.solver; version = args.version
    if args.solution and args.solution.exists():
        data = json.loads(args.solution.read_text(encoding="utf-8"))
        status = data.get("status", status); gap = data.get("gap", gap); solver = data.get("solver", solver); version = data.get("version", version)
    gates = {
        "has_status": status is not None,
        "status_is_optimal": status == "optimal",
        "has_solver": bool(solver),
        "has_version": bool(version),
        "gap_ok": (gap is not None and gap == 0.0) if status == "optimal" else (gap is not None if status in ("feasible","time_limit") else True),
    }
    if status == "infeasible":
        gates["diagnosis"] = "需 IIS/松弛诊断，点名冲突约束"
        verdict = "HOLD — Infeasible，需诊断"
    elif status == "unbounded":
        gates["diagnosis"] = "缺界，找到它，不要封目标"
        verdict = "HOLD — Unbounded，缺界"
    elif status == "optimal" and (gap is not None and gap != 0.0):
        verdict = "HOLD — optimal 但 gap!=0，标签错误"
    elif not solver or not version:
        verdict = "HOLD — 求解器 name+version 未记录"
    elif status != "optimal":
        verdict = "HOLD — 未达 optimal"
    else:
        verdict = "PASS"
    report = {"status": status, "gap": gap, "solver": solver, "version": version, "gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"LP gate: status={status} gap={gap} solver={solver} {version} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
