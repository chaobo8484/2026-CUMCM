#!/usr/bin/env python3
"""
backend_probe.py — research-evidence Gate 0/1 通道定档探针

只探存在性，不读值、不打印、不落盘任何密钥。
Reads optional config (docs/agents/mathx-config.md), checks env var
FIRECRAWL_API_KEY existence, decides backend tier.

Usage:
  python backend_probe.py --task simple --out probe.json
  python backend_probe.py --task deep --config docs/agents/mathx-config.md --out probe.json
  python backend_probe.py --task deep --want firecrawl-advanced --out probe.json

Exit codes: 0 decided (any tier incl. none), 1 usage/config error.
Tier none/manual/generic/firecrawl-advanced. Default ceiling generic.
Firecrawl requires: key present + explicit opt-in + deep task.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

KEY_ENV = "FIRECRAWL_API_KEY"
VALID_BACKENDS = ("none", "manual", "generic", "firecrawl-advanced")


def read_config_backend(path: pathlib.Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r"evidence_backend:\s*([a-z\-]+)", text)
    if m and m.group(1) in VALID_BACKENDS:
        return m.group(1)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence backend tier probe")
    parser.add_argument("--task", choices=["simple", "deep"], required=True)
    parser.add_argument("--config", type=pathlib.Path, default=None)
    parser.add_argument("--want", choices=list(VALID_BACKENDS), default=None)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    configured = read_config_backend(args.config)
    want = args.want or configured or "generic"
    if want not in VALID_BACKENDS:
        print(f"unknown backend: {want}", file=sys.stderr)
        sys.exit(1)

    # Existence probe only. Never read or log the value.
    key_present = KEY_ENV in os.environ and bool(os.environ.get(KEY_ENV))

    # Ladder: firecrawl only when all three hold.
    firecrawl_eligible = key_present and want == "firecrawl-advanced" and args.task == "deep"

    if firecrawl_eligible:
        backend = "firecrawl-advanced"
        reason = "key present + explicit opt-in + deep task"
    elif want == "firecrawl-advanced":
        # Fall back, state why without leaking anything.
        causes = []
        if not key_present:
            causes.append("no-key")
        if args.task != "deep":
            causes.append("not-deep-task")
        backend = "generic"
        reason = f"firecrawl requested but {'+'.join(causes)}; fell back to generic"
    elif want in ("none", "manual", "generic"):
        backend = want
        reason = "configured/requested tier within default ceiling"
    else:
        backend = "generic"
        reason = "default ceiling"

    verdict = "OPEN" if backend == "none" else "READY"
    report = {
        "task": args.task,
        "configured_backend": configured,
        "requested_backend": args.want,
        "key_present": key_present,
        "key_source": f"env:{KEY_ENV}",
        "backend": backend,
        "reason": reason,
        "firecrawl_eligible": firecrawl_eligible,
        "verdict": verdict,
        "note": "key existence only; value never read, logged, or stored",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"backend={backend} key_present={key_present} [{verdict}]")
    print(f"reason: {reason}")
    print(f"report: {args.out}")


if __name__ == "__main__":
    main()
