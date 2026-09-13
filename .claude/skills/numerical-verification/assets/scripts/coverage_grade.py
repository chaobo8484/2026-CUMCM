#!/usr/bin/env python3
"""
coverage_grade.py — 数值验证覆盖定级（P0）

Hard Rules 对应（numerical-verification/SKILL.md）：
- 覆盖记成数据（范围×密度×种子），空格默认 OPEN
- 三级固定：SUPPORTED（全过含极端）/ OPEN / REFUTED（失败且复现→移交）
- near-miss 不四舍五入成过

Usage:
  python coverage_grade.py coverage.json --out report.json
  coverage.json 见 assets/templates/coverage-schema.json
"""
from __future__ import annotations
import argparse, json, pathlib, sys

def main():
    parser = argparse.ArgumentParser(description="覆盖定级")
    parser.add_argument("coverage", type=pathlib.Path, help="覆盖 JSON（按 schema）")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    try:
        cov = json.loads(args.coverage.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"覆盖文件不可解析: {e}", file=sys.stderr); sys.exit(1)

    probes = cov.get("probes", [])
    if not probes:
        print("无探针：无覆盖，无等级", file=sys.stderr); sys.exit(1)

    required_probe_keys = ("region", "density", "n", "seed", "extreme", "passed")
    malformed = [i for i, p in enumerate(probes) if any(k not in p for k in required_probe_keys)]

    extreme_probes = [p for p in probes if p.get("extreme")]
    failed = [p for p in probes if not p.get("passed") and not p.get("near_miss")]
    near_misses = [p for p in probes if p.get("near_miss")]
    unseeded = [p for p in probes if p.get("seed") is None]

    reproduced = cov.get("reproduced_failures", [])

    gates = {
        "schema_ok": len(malformed) == 0,
        "malformed_probes": malformed,
        "has_extreme": len(extreme_probes) > 0,
        "extreme_all_pass": bool(extreme_probes) and all(p.get("passed") for p in extreme_probes),
        "all_seeded": len(unseeded) == 0,
        "unseeded_probes": [probes.index(p) for p in unseeded],
        "has_near_miss": len(near_misses) > 0,
        "failures_reproduced": bool(not failed or reproduced),
    }

    if malformed or unseeded:
        verdict = "HOLD — 覆盖表缺字段或无种子，按 schema 补齐"
    elif failed and reproduced:
        verdict = "REFUTED — 失败已复现，移交 counterexample-search 找最小"
    elif failed and not reproduced:
        verdict = "HOLD — 有失败未独立复现，复现后再定级"
    elif not extreme_probes or not all(p.get("passed") for p in extreme_probes):
        verdict = "OPEN — 极端没探或没过，内部成绩不算数"
    else:
        verdict = "SUPPORTED — 探过点全过含极端（仍非证明）"

    report = {
        "assertion": cov.get("assertion", ""),
        "domain": cov.get("domain", ""),
        "tolerance": cov.get("tolerance"),
        "n_probes": len(probes),
        "n_extreme": len(extreme_probes),
        "n_failed": len(failed),
        "n_near_miss": len(near_misses),
        "gates": gates,
        "verdict": verdict,
        "next": ("指定下个探针（区域+方法）" if verdict.startswith("OPEN")
                 else ("找最小反例" if verdict.startswith("REFUTED") else "到证明的差距仍需落字")),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"coverage: probes={len(probes)} extreme={len(extreme_probes)} failed={len(failed)} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
