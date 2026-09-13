#!/usr/bin/env python3
"""
ga_gate.py — 遗传算法门禁（P0）

Hard Rules: 编码+修复+适应度, 多轮≥5, 收敛曲线, 同预算随机/贪心基线, 可行性代码验

Usage:
  python ga_gate.py --config config.json --results campaign.json --sense min --out report.json
  config.json 需含: encoding, repair, fitness_expr, n_rounds, population, generations
  campaign.json (深门禁必需): {rounds: [{best, feasible, trace_best: [...], trace_mean: [...]}],
    baseline_random, baseline_greedy}
  无 --results 时仅验配置，verdict 为 OPEN（campaign 产物未交）。
"""
from __future__ import annotations
import argparse, json, pathlib, sys

def main():
    parser = argparse.ArgumentParser(description="GA 门禁")
    parser.add_argument("--config", type=pathlib.Path, required=True, help="GA 配置 JSON")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--results", type=pathlib.Path, default=None, help="campaign 产物 JSON")
    parser.add_argument("--sense", type=str, default="min", choices=["min", "max"],
                        help="适应度方向：min 越小越好，max 越大越好")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    required = ["encoding","repair","fitness_expr","n_rounds","population","generations"]
    missing = [k for k in required if k not in cfg]
    n_rounds = cfg.get("n_rounds", 0)
    generations = cfg.get("generations", 0)
    gates: dict = {
        "has_encoding": "encoding" not in missing,
        "has_repair": "repair" not in missing and bool(cfg.get("repair")),
        "has_fitness": "fitness_expr" not in missing,
        "n_rounds_ge_5": bool(n_rounds >= 5),
        "has_population": "population" in cfg,
        "has_generations": "generations" in cfg,
    }
    campaign: dict = {}
    if args.results and args.results.exists():
        try:
            data = json.loads(args.results.read_text(encoding="utf-8"))
            rounds = data.get("rounds", [])
            campaign["n_rounds_logged"] = len(rounds)
            gates["rounds_match_config"] = (len(rounds) == n_rounds) if n_rounds else None
            # feasibility: every round feasible
            feas = [bool(r.get("feasible")) for r in rounds]
            gates["all_feasible"] = bool(feas and all(feas))
            # convergence trace: each round has best/mean arrays of length generations
            trace_ok = True
            for r in rounds:
                tb, tm = r.get("trace_best", []), r.get("trace_mean", [])
                if not tb or not tm or (generations and (len(tb) != generations or len(tm) != generations)):
                    trace_ok = False
                    break
            gates["has_convergence_trace"] = bool(trace_ok and rounds)
            # spread: worst vs best across rounds
            bests = [r.get("best") for r in rounds if isinstance(r.get("best"), (int, float))]
            if bests:
                lo, hi = min(bests), max(bests)
                campaign["best"] = lo if args.sense == "min" else hi
                campaign["worst"] = hi if args.sense == "min" else lo
                campaign["spread"] = hi - lo
            # baselines, direction-aware
            better = (lambda a, b: a < b) if args.sense == "min" else (lambda a, b: a > b)
            beats = []
            for key in ("baseline_random", "baseline_greedy"):
                if key in data and "best" in campaign and isinstance(data[key], (int, float)):
                    beats.append(bool(better(campaign["best"], data[key])))
            gates["beats_baseline"] = bool(beats and all(beats)) if beats else None
            campaign["baselines_compared"] = [k for k in ("baseline_random", "baseline_greedy") if k in data]
        except Exception as e:
            gates["results_parseable"] = False
            campaign["parse_error"] = str(e)
    else:
        gates["has_campaign"] = False

    config_ok = all(gates[k] for k in ("has_encoding", "has_repair", "has_fitness", "n_rounds_ge_5"))
    if missing or not gates["n_rounds_ge_5"]:
        verdict = "HOLD — 配置缺字段或轮数不足"
    elif not args.results or gates.get("has_campaign") is False:
        verdict = "OPEN — 无 campaign 产物，仅配过配置；交 rounds+trace+基线后重跑"
    elif gates.get("results_parseable") is False:
        verdict = "HOLD — campaign 产物不可解析"
    elif not gates.get("all_feasible"):
        verdict = "HOLD — 存在不可行轮次，修修复算子"
    elif not gates.get("has_convergence_trace"):
        verdict = "HOLD — 缺收敛带（每轮每代 best/mean）"
    elif gates.get("beats_baseline") is False:
        verdict = "HOLD — 未打赢同预算基线，交付基线并说明"
    elif config_ok:
        verdict = "PASS"
    else:
        verdict = "HOLD — 配置门禁未过"

    report = {
        "config": cfg,
        "missing_fields": missing,
        "sense": args.sense,
        "campaign": campaign,
        "gates": gates,
        "verdict": verdict,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"GA gate: missing={missing} rounds={n_rounds} feasible={gates.get('all_feasible')} "
          f"trace={gates.get('has_convergence_trace')} beats={gates.get('beats_baseline')} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
