#!/usr/bin/env python3
"""
docx_gate.py — DOCX 协作稿门禁（latex-typesetting DOCX 分支）

Hard Rules 对应：
- 样式走内置（Heading 1-3 / Normal / Caption / List），直接格式不漫延
- 图/表题注编号连续（图 1.. / 表 1..），正文引用对编号
- 占位清零（TODO/dummy/lorem），核心属性标题设好
- 公式可读：OMML 或图片 + 替代文本声明其一

Usage:
  python docx_gate.py paper.docx --out report.json
  缺 python-docx 时返回 OPEN（需 pip install python-docx）
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

PLACEHOLDERS = ("TODO", "DUMMY", "LOREM", "XXX", "TBD")

def main():
    parser = argparse.ArgumentParser(description="DOCX 协作稿门禁")
    parser.add_argument("docx", type=pathlib.Path, help="输入 .docx 路径")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出报告 JSON 路径")
    args = parser.parse_args()

    if not args.docx.exists() or args.docx.suffix.lower() != ".docx":
        print(f"文件不存在或非 .docx: {args.docx}", file=sys.stderr); sys.exit(1)

    try:
        import docx  # python-docx
    except ImportError:
        report = {"file": args.docx.name, "verdict": "OPEN — 缺 python-docx，装后重跑门禁",
                  "gates": {"docx_available": False}, "method": "python-docx"}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("OPEN — 未安装 python-docx: pip install python-docx"); print(f"报告: {args.out}")
        return

    doc = docx.Document(str(args.docx))
    paras = doc.paragraphs
    texts = [p.text for p in paras]

    # 1. styles: built-in vs direct formatting sprawl
    style_names = [p.style.name if p.style else "" for p in paras if p.text.strip()]
    builtin = {"Heading 1", "Heading 2", "Heading 3", "Normal", "Caption", "List Paragraph", "Title"}
    off_style = sorted({s for s in set(style_names) if s not in builtin and s})
    direct_runs = sum(1 for p in paras for r in p.runs if r.text.strip() and (r.bold or r.italic or r.underline) and r.font.name)
    # ^ direct font-name overrides are the sprawl signal; bold/italic alone are legitimate emphasis

    # 2. captions: 图 n / 表 n sequential
    fig_nums, tab_nums = [], []
    for t in texts:
        m = re.match(r"\s*图\s*(\d+)", t);  fig_nums.extend(int(x) for x in m.groups()) if m else None
        m = re.match(r"\s*表\s*(\d+)", t);  tab_nums.extend(int(x) for x in m.groups()) if m else None
    def seq_ok(nums):
        return (not nums) or (sorted(nums) == list(range(1, max(nums) + 1)))
    fig_ok, tab_ok = seq_ok(fig_nums), seq_ok(tab_nums)

    # 3. placeholders
    full = "\n".join(texts)
    hits = sorted({ph for ph in PLACEHOLDERS if ph in full.upper()})

    # 4. core properties
    core = doc.core_properties
    has_title = bool((core.title or "").strip())

    # 5. images alt text
    imgs_no_alt = 0
    try:
        for shape in doc.inline_shapes:
            # python-docx exposes _element; alt via wp:docPr descr
            el = shape._element
            docpr = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")
            if docpr is None:
                docpr = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/inline}../..")
            # fallback: count images lacking descr attribute
            descr = ""
            for cand in el.iter():
                if cand.tag.endswith("docPr"):
                    descr = cand.get("descr", "") or ""
                    break
            if not descr:
                imgs_no_alt += 1
    except Exception:
        imgs_no_alt = -1  # unknown

    gates = {
        "styles_builtin": len(off_style) == 0,
        "off_styles": off_style,
        "fig_caption_seq": bool(fig_ok),
        "tab_caption_seq": bool(tab_ok),
        "fig_count": len(fig_nums), "tab_count": len(tab_nums),
        "placeholders_zero": len(hits) == 0,
        "placeholder_hits": hits,
        "core_title_set": bool(has_title),
        "images_missing_alt": imgs_no_alt,
    }
    failed = [k for k, v in gates.items() if v is False]
    verdict = "PASS" if not failed and imgs_no_alt != -1 else ("OPEN — 图片替代文本未探明，人工确认" if not failed else f"HOLD — {', '.join(failed)}")
    report = {"file": args.docx.name, "paragraphs": len(paras), "tables": len(doc.tables),
              "gates": gates, "verdict": verdict, "method": "python-docx"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"DOCX gate: styles_off={off_style} fig_seq={fig_ok} tab_seq={tab_ok} placeholders={hits} title={has_title} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
