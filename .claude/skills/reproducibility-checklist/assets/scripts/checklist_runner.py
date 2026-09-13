#!/usr/bin/env python3
"""
checklist_runner.py — 交稿门禁机器可检项 runner（P0）

对应 reproducibility-checklist/SKILL.md 的技术项：机器能跑的跑出证据，
必须人审的标 NOT-CHECKED 并点名主技能，永不悄悄通过。

Machine-checked:
- lockfile: requirements.txt / pyproject.toml / environment.yml 存在且非空
- seeds-in-code: .py 内出现 seed/random_state/np.random.seed（计数+文件）
- placeholders: TODO/DUMMY/LOREM/TBD/XXX 全文 grep（tex/md/py）
- anonymity (venue=国赛): 学校/学院/姓名/赛区/学号 模式 grep（tex/md/docx 名）
- pdf-size (if --pdf given): ≤20MB
- undefined-refs: .log 内 Undefined control sequence / Citation .* undefined / [?] 计数
Human-only → NOT-CHECKED with owner:
  clean-build, rerun-headline, data-manifest, exhibit-trace, caption-standalone,
  citation-bothways, glossary, claim-entailment, counterarguments, limitations,
  paper↔electronic consistency, page-order, appendix-programs, support-zip

Usage:
  python checklist_runner.py --project ./paper-proj --venue 国赛 --pdf paper.pdf --out report.json
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

PLACEHOLDERS = ("TODO", "DUMMY", "LOREM", "TBD", "XXX")
ANON_PATTERNS = ("大学", "学院", "学校", "赛区", "学号", "姓名", "参赛队")
TEXT_SUFFIXES = (".tex", ".md", ".txt", ".bib")
HUMAN_ITEMS = {
    "clean-build": "latex-typesetting",
    "rerun-headline": "modeling-skill",
    "data-manifest": "ingest-inputs",
    "exhibit-trace": "figure-table-generation",
    "caption-standalone": "figure-table-generation",
    "citation-bothways": "citation-bibliography",
    "glossary": "polish-proofread",
    "claim-entailment": "paper-outline",
    "counterarguments": "paper-outline",
    "limitations": "paper-outline",
    "paper-electronic-consistency": "latex-typesetting",
    "page-order": "paper-outline",
    "appendix-programs": "latex-typesetting",
    "support-zip": "latex-typesetting",
}

def grep_files(root: pathlib.Path, patterns: tuple[str, ...], suffixes: tuple[str, ...]) -> list[dict]:
    hits: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in suffixes:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            continue  # binary or bad encoding: skip, do not fabricate
        for i, line in enumerate(text.splitlines(), 1):
            for pat in patterns:
                if pat in line:
                    hits.append({"file": str(p.relative_to(root)), "line": i, "pattern": pat,
                                 "excerpt": line.strip()[:120]})
                    break
    return hits

def main():
    parser = argparse.ArgumentParser(description="交稿门禁机器可检项 runner")
    parser.add_argument("--project", type=pathlib.Path, required=True, help="稿件项目目录")
    parser.add_argument("--venue", type=str, default="国赛", help="MCM/国赛/journal")
    parser.add_argument("--pdf", type=pathlib.Path, default=None, help="待检 PDF（查 ≤20MB）")
    parser.add_argument("--log", type=pathlib.Path, default=None, help="LaTeX 构建日志（查 undefined）")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    root = args.project
    if not root.exists():
        print(f"项目目录不存在: {root}", file=sys.stderr); sys.exit(1)

    items: dict[str, dict] = {}

    # 1. lockfile
    lockfiles = [p for p in ("requirements.txt", "pyproject.toml", "environment.yml")
                 if (root / p).exists() and (root / p).stat().st_size > 0]
    items["lockfile"] = {"status": "PASS" if lockfiles else "FAIL", "evidence": lockfiles or "无 lockfile",
                         "owner": "reproducibility-checklist"}

    # 2. seeds in code
    seed_hits = []
    for p in sorted(root.rglob("*.py")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"seed|random_state|np\.random\.seed|torch\.manual_seed", line, re.I):
                seed_hits.append({"file": str(p.relative_to(root)), "line": i})
                break  # one per file is enough
    items["seeds-in-code"] = {"status": "PASS" if seed_hits else "NOT-CHECKED",
                              "evidence": seed_hits or "无 .py 含种子声明",
                              "owner": "modeling-skill"}

    # 3. placeholders
    ph = grep_files(root, PLACEHOLDERS, TEXT_SUFFIXES + (".py",))
    items["placeholders-zero"] = {"status": "PASS" if not ph else "FAIL",
                                  "evidence": ph or "零残留", "owner": "latex-typesetting"}

    # 4. anonymity (国赛 only)
    if args.venue == "国赛":
        anon = grep_files(root, ANON_PATTERNS, TEXT_SUFFIXES)
        items["anonymity"] = {"status": "PASS" if not anon else "HOLD",
                              "evidence": anon or "grep 零命中", "owner": "latex-typesetting"}
    else:
        items["anonymity"] = {"status": "NOT-CHECKED", "evidence": f"venue={args.venue} 不适用",
                              "owner": "latex-typesetting"}

    # 5. pdf size
    if args.pdf:
        if args.pdf.exists():
            size = args.pdf.stat().st_size
            items["pdf-size"] = {"status": "PASS" if size <= 20 * 1024 * 1024 else "HOLD",
                                 "evidence": f"{size} bytes (≤20MB)", "owner": "latex-typesetting"}
        else:
            items["pdf-size"] = {"status": "FAIL", "evidence": f"PDF 不存在: {args.pdf}",
                                 "owner": "latex-typesetting"}
    else:
        items["pdf-size"] = {"status": "NOT-CHECKED", "evidence": "未给 --pdf",
                             "owner": "latex-typesetting"}

    # 6. undefined refs in log
    if args.log and args.log.exists():
        log_text = args.log.read_text(encoding="utf-8", errors="replace")
        undef = sorted(set(re.findall(r"Citation `[^']+' undefined|Undefined control sequence.*|There were undefined references", log_text)))
        bracket_q = log_text.count("[?]")
        items["undefined-refs"] = {"status": "PASS" if not undef and bracket_q == 0 else "FAIL",
                                   "evidence": undef + ([f"[?]×{bracket_q}"] if bracket_q else []) or "零警告",
                                   "owner": "citation-bibliography"}
    else:
        items["undefined-refs"] = {"status": "NOT-CHECKED", "evidence": "未给 --log",
                                   "owner": "citation-bibliography"}

    # 7. human-only items
    for key, owner in HUMAN_ITEMS.items():
        items[key] = {"status": "NOT-CHECKED", "evidence": "需人工审读", "owner": owner}

    # verdict: HOLD if anonymity/placeholders/pdf-size HOLD/FAIL on blocking items;
    # data/rerun are human → PASS-WITH-ITEMS when machine items pass
    machine_fail = [k for k, v in items.items() if v["status"] in ("HOLD", "FAIL")]
    not_checked = [k for k, v in items.items() if v["status"] == "NOT-CHECKED"]
    if any(items[k]["status"] == "HOLD" for k in ("anonymity", "pdf-size")) or items["placeholders-zero"]["status"] == "FAIL":
        verdict = "HOLD"
    elif machine_fail or not_checked:
        verdict = "PASS-WITH-ITEMS"
    else:
        verdict = "PASS"

    report = {"project": str(root), "venue": args.venue, "items": items,
              "machine_fail": machine_fail, "not_checked": not_checked,
              "verdict": verdict, "method": "checklist_runner machine subset"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"checklist: machine_fail={machine_fail} not_checked={len(not_checked)} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
