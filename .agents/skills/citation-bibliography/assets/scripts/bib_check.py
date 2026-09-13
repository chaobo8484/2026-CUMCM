#!/usr/bin/env python3
"""
bib_check.py — 引用双向门禁（P1）

对应 citation-bibliography/SKILL.md：
- 体例单一声明；文→表键落地；表→文零悬空（或已批准延伸阅读）
- 必填字段按类型；作者名仍需人眼（本脚本只查有无，不审对错）
- DOI 格式抽查（https://doi.org/ 前缀 + 10. 前缀）；resolv 需联网，默认只验格式

Usage:
  TEX:  python bib_check.py --tex main.tex --bib refs.bib --out report.json [--log main.log] [--allowed-unused key1,key2]
  DOCX: python bib_check.py --bib refs.bib --cite-list "1,2,5" --out report.json
        （--cite-list 为文内出现的序号/键清单，逗号分隔）
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

REQUIRED = {
    "article": ("journal", "year"),
    "book": ("publisher", "year"),
    "inproceedings": ("booktitle", "year"),
    "online": ("url",),
    "misc": (),
}

def parse_bib(path: pathlib.Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: dict[str, dict] = {}
    # crude @type{key, ...} splitter (balanced-brace aware enough for gate use)
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        etype, key = m.group(1).lower(), m.group(2)
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        fields = set(re.findall(r"(\w+)\s*=", body))
        entries[key] = {"type": etype, "fields": fields, "has_doi": "doi" in fields,
                        "doi": (re.search(r"doi\s*=\s*[{\"]\s*([^}\"]+)", body).group(1).strip()
                                if "doi" in fields else "")}
    return entries

def main():
    parser = argparse.ArgumentParser(description="引用双向门禁")
    parser.add_argument("--tex", type=pathlib.Path, default=None)
    parser.add_argument("--bib", type=pathlib.Path, required=True)
    parser.add_argument("--log", type=pathlib.Path, default=None)
    parser.add_argument("--cite-list", type=str, default=None, help="DOCX 文内引用键清单")
    parser.add_argument("--allowed-unused", type=str, default="", help="已批准延伸阅读键")
    parser.add_argument("--style", type=str, default="", help="体例声明（GB/T 7714/APA/venue），仅记录")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if not args.bib.exists():
        print(f".bib 不存在: {args.bib}", file=sys.stderr); sys.exit(1)
    entries = parse_bib(args.bib)

    cited: set[str] = set()
    if args.tex and args.tex.exists():
        tex = args.tex.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\\cite\w*\{([^}]+)\}", tex):
            cited.update(k.strip() for k in m.group(1).split(",") if k.strip())
    if args.cite_list:
        cited.update(k.strip() for k in args.cite_list.split(",") if k.strip())

    allowed = {k.strip() for k in args.allowed_unused.split(",") if k.strip()}
    dangling = sorted(cited - set(entries))           # 文→表悬空
    unused = sorted(set(entries) - cited - allowed)   # 表→文悬空

    field_gaps = {}
    for key, e in entries.items():
        req = REQUIRED.get(e["type"], ())
        missing = [f for f in req if f not in e["fields"]]
        if missing:
            field_gaps[key] = {"type": e["type"], "missing": missing}

    doi_bad = {k: e["doi"] for k, e in entries.items()
               if e["doi"] and not re.match(r"(https?://(dx\.)?doi\.org/)?10\.\d+/", e["doi"])}

    log_undef: list[str] = []
    if args.log and args.log.exists():
        lt = args.log.read_text(encoding="utf-8", errors="replace")
        log_undef = sorted(set(re.findall(r"Citation `([^']+)' undefined", lt)))

    gates = {
        "no_dangling": len(dangling) == 0,
        "dangling": dangling,
        "no_unused": len(unused) == 0,
        "unused": unused,
        "fields_complete": len(field_gaps) == 0,
        "field_gaps": field_gaps,
        "doi_format_ok": len(doi_bad) == 0,
        "doi_bad": doi_bad,
        "log_undefined_zero": len(log_undef) == 0,
        "log_undefined": log_undef,
        "style_declared": bool(args.style),
    }
    failed = [k for k in ("no_dangling", "fields_complete", "doi_format_ok", "log_undefined_zero") if not gates[k]]
    if dangling or log_undef:
        verdict = "HOLD — 悬空引用未落地"
    elif field_gaps or doi_bad:
        verdict = "HOLD — 条目字段或 DOI 格式未齐"
    elif unused:
        verdict = "PASS-WITH-ITEMS — 未被引条目需批准为延伸阅读"
    else:
        verdict = "PASS"

    report = {"bib_entries": len(entries), "cited": sorted(cited), "style": args.style or "未声明",
              "gates": gates, "verdict": verdict,
              "note": "作者名仍需人眼；DOI 只验格式不 resolv（联网另查）"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"bib: entries={len(entries)} cited={len(cited)} dangling={dangling} unused={unused} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
