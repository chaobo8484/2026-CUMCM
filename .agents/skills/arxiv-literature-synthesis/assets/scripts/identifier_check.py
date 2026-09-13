#!/usr/bin/env python3
"""
identifier_check.py — 文献标识符格式门禁（P1）

对应 arxiv-literature-synthesis / literature-review Hard Rules：
无标识符无引用。默认离线只验格式（arXiv 新/旧式、DOI 前缀），
--resolve 时联网逐条 resolv（需 requests，无则 OPEN 说明）。

Usage:
  python identifier_check.py refs.json --out report.json [--resolve]
  refs.json: [{"id": "2401.12345|xXiv|doi:10.../10...", "title": "..."}]
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

ARXIV_NEW = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD = re.compile(r"^[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$")
DOI = re.compile(r"^(https?://(dx\.)?doi\.org/)?10\.\d{4,}/.+")

def classify(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", s, flags=re.I)
    if ARXIV_NEW.match(s) or ARXIV_OLD.match(s):
        return "arxiv"
    if DOI.match(raw.strip()) or DOI.match("10." + s):
        return "doi"
    return "unknown"

def main():
    parser = argparse.ArgumentParser(description="文献标识符门禁")
    parser.add_argument("refs", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--resolve", action="store_true", help="联网 resolv（需 requests）")
    args = parser.parse_args()

    try:
        refs = json.loads(args.refs.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"refs 不可解析: {e}", file=sys.stderr); sys.exit(1)

    rows = []
    for r in refs:
        rid = r.get("id", "")
        kind = classify(rid)
        rows.append({"id": rid, "title": r.get("title", ""), "kind": kind,
                     "format_ok": kind != "unknown", "resolved": None})

    if args.resolve:
        try:
            import requests  # type: ignore
        except ImportError:
            for row in rows:
                row["resolved"] = "OPEN — 缺 requests，装后重跑 resolv"
        else:
            for row in rows:
                if row["kind"] == "doi":
                    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", row["id"], flags=re.I)
                    try:
                        resp = requests.head(f"https://doi.org/{doi}", timeout=10, allow_redirects=True)
                        row["resolved"] = bool(resp.status_code < 400)
                    except Exception as e:
                        row["resolved"] = f"OPEN — 网络失败：{e}"
                elif row["kind"] == "arxiv":
                    aid = row["id"].split("arXiv:")[-1] if "arXiv:" in row["id"] else row["id"]
                    try:
                        resp = requests.get(f"https://export.arxiv.org/api/query?id_list={aid}", timeout=15)
                        row["resolved"] = "<entry" in resp.text
                    except Exception as e:
                        row["resolved"] = f"OPEN — 网络失败：{e}"
                else:
                    row["resolved"] = False

    bad = [r for r in rows if not r["format_ok"]]
    unresolved = [r for r in rows if r["resolved"] is False]
    gates = {"all_format_ok": len(bad) == 0, "bad": bad,
             "all_resolved": len(unresolved) == 0 if args.resolve else None,
             "unresolved": unresolved, "resolved_checked": bool(args.resolve)}
    if bad:
        verdict = f"HOLD — {len(bad)} 条标识符格式不过（无标识不进地图）"
    elif args.resolve and unresolved:
        verdict = f"HOLD — {len(unresolved)} 条 resolv 失败，排除或修正"
    else:
        verdict = "PASS" + ("" if args.resolve else "（仅格式；resolv 另跑 --resolve）")

    report = {"n": len(rows), "rows": rows, "gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"identifiers: n={len(rows)} bad={len(bad)} unresolved={len(unresolved)} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
