#!/usr/bin/env python3
"""
firecrawl_executor.py — Firecrawl 深爬请求信封（research-evidence Tier 3 专用）

Only callable from research-evidence. Other skills calling it directly
is a violation (checked by scripts/ci/check_evidence_refs.py).

Behavior:
- Gate: FIRECRAWL_API_KEY must exist in env (existence only).
  Missing -> exit 2, writes error envelope, fabricates nothing.
- Present: writes a request envelope (query, mode, date) for the agent
  to execute via MCP/API. This script never fabricates sources.
- Key value is never read, printed, or stored.

Usage:
  python firecrawl_executor.py --query "GM(1,1) applicability" --mode search --out envelope.json
  modes: search | scrape | crawl (escalation Search -> Scrape -> Map/Crawl)
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import date

KEY_ENV = "FIRECRAWL_API_KEY"
VALID_MODES = ("search", "scrape", "crawl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Firecrawl deep-crawl request envelope")
    parser.add_argument("--query", required=True)
    parser.add_argument("--mode", choices=list(VALID_MODES), default="search")
    parser.add_argument("--index", choices=["auto", "research", "developer"], default="auto")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    key_present = KEY_ENV in os.environ and bool(os.environ.get(KEY_ENV))
    today = date.today().isoformat()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if not key_present:
        envelope = {
            "backend": "firecrawl-advanced",
            "status": "BLOCKED",
            "error": f"no-key: {KEY_ENV} not set; degraded, fabricate nothing",
            "query": args.query,
            "mode": args.mode,
            "date": today,
            "next": "fall back to generic/manual/none per backend_probe.py tier",
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)
        print(f"BLOCKED: {KEY_ENV} not set; envelope written with no results", file=sys.stderr)
        print(f"envelope: {args.out}", file=sys.stderr)
        sys.exit(2)

    envelope = {
        "backend": "firecrawl-advanced",
        "status": "READY-FOR-MCP",
        "query": args.query,
        "mode": args.mode,
        "index": args.index,
        "date": today,
        "key_source": f"env:{KEY_ENV}",
        "results": [],
        "instruction": (
            "Execute via Firecrawl MCP/API with the above query+mode. "
            "Append real sources to results; never invent URLs. "
            "Escalate Search -> Scrape -> Map/Crawl only as needed."
        ),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    print(f"envelope ready: mode={args.mode} index={args.index} {today}")
    print(f"envelope: {args.out}")


if __name__ == "__main__":
    main()
