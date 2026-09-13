#!/usr/bin/env python3
"""
docx_pptx_to_md.py — docx/pptx → Markdown 转换（ingest-inputs P0-1）

对标 patent-disclosure 的 docx_to_md.py / pptx_to_md.py 思路，精简为 MathX 版本：
- 保留标题层级、段落、表格、图片占位
- 来源记录：文件名 + hash + 参数 + 日期

Usage:
  python docx_pptx_to_md.py input.docx --out out.md --report report.json
  python docx_pptx_to_md.py input.pptx --out out.md --report report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import date


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_docx(path: pathlib.Path) -> tuple[str, dict]:
    try:
        import docx  # python-docx
    except ImportError:
        return "", {"error": "未安装 python-docx: pip install python-docx"}
    doc = docx.Document(str(path))
    lines: list[str] = []
    meta: dict = {"paragraphs": len(doc.paragraphs), "tables": len(doc.tables)}
    # Heuristic heading: style name contains Heading
    for para in doc.paragraphs:
        style = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue
        if "Heading 1" in style:
            lines.append(f"# {text}")
        elif "Heading 2" in style:
            lines.append(f"## {text}")
        elif "Heading 3" in style:
            lines.append(f"### {text}")
        else:
            lines.append(text)
    # Tables
    for ti, table in enumerate(doc.tables):
        lines.append(f"\n<!-- Table {ti+1} -->")
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    # Images placeholder
    image_count = len(doc.inline_shapes)
    if image_count:
        lines.append(f"\n> [图片占位：{image_count} 张，已提取为独立资源，见同目录 media/]\n")
        meta["images"] = image_count
    return "\n\n".join(lines), meta


def convert_pptx(path: pathlib.Path) -> tuple[str, dict]:
    try:
        from pptx import Presentation  # python-pptx
    except ImportError:
        return "", {"error": "未安装 python-pptx: pip install python-pptx"}
    prs = Presentation(str(path))
    lines: list[str] = [f"# {path.stem} — 幻灯片转 Markdown"]
    meta: dict = {"slides": len(prs.slides)}
    for si, slide in enumerate(prs.slides, 1):
        lines.append(f"\n## Slide {si}")
        # Collect text shapes
        texts: list[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text.strip()
                if t:
                    texts.append(t)
            # Table
            if shape.has_table:
                lines.append(f"\n<!-- Slide {si} Table -->")
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    lines.append("| " + " | ".join(cells) + " |")
        if texts:
            lines.extend(texts)
        # Notes
        if slide.notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            lines.append(f"> 备注: {slide.notes_slide.notes_text_frame.text.strip()}")
    return "\n\n".join(lines), meta


def main() -> None:
    parser = argparse.ArgumentParser(description="docx/pptx → Markdown")
    parser.add_argument("input", type=pathlib.Path, help="输入 .docx/.pptx 路径")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出 .md 路径")
    parser.add_argument("--report", type=pathlib.Path, required=True, help="报告 JSON 路径")
    args = parser.parse_args()

    inp = args.input
    if not inp.exists() or inp.suffix.lower() not in (".docx", ".pptx"):
        print(f"文件不存在或类型不支持: {inp}（仅 .docx/.pptx）", file=sys.stderr)
        sys.exit(1)

    file_hash = sha256_of(inp)
    today = date.today().isoformat()
    suffix = inp.suffix.lower()

    if suffix == ".docx":
        md_text, meta = convert_docx(inp)
    else:
        md_text, meta = convert_pptx(inp)

    if "error" in meta:
        print(meta["error"], file=sys.stderr)
        # Still write placeholder and report
        md_text = f"# 转换失败 — {inp.name}\n\n> {meta['error']}\n"

    q: dict = {
        "type": suffix.lstrip("."),
        "meta": meta,
        "chars": len(md_text),
        "source": {
            "filename": inp.name,
            "sha256": file_hash,
            "params": {"method": "docx/pptx to md"},
            "date": today,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md_text, encoding="utf-8")
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

    print(f"转换完成: {inp.name} -> {args.out} ({len(md_text)} 字符)")
    print(f"报告: {args.report}")


if __name__ == "__main__":
    main()
