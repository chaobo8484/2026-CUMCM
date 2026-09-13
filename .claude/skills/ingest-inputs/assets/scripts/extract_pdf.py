#!/usr/bin/env python3
"""
extract_pdf.py — PDF 文本层优先提取，扫描件检测（ingest-inputs P0-1）

Hard Rules:
- 文本层优先；无文本层标扫描件，不谎称精确提取
- 来源记录：文件名 + hash + 参数 + 日期

Usage:
  python extract_pdf.py input.pdf --out text.md --report report.json
Requires: PyPDF2 or pypdf (fallback to pdfminer.six if available)
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


def extract_with_pypdf(path: pathlib.Path) -> tuple[str, int, list[str]]:
    """Returns (text, n_pages, per_page_char_counts)."""
    try:
        from pypdf import PdfReader  # pypdf >=3
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return "", 0, []
    reader = PdfReader(str(path))
    pages_text: list[str] = []
    counts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages_text.append(t)
        counts.append(f"p{i+1}:{len(t)} chars")
    full = "\n\n--- Page Break ---\n\n".join(pages_text)
    return full, len(reader.pages), counts


def is_scanned(text: str, n_pages: int) -> bool:
    """Heuristic: avg chars per page < 50 -> likely scanned."""
    if n_pages == 0:
        return True
    avg = len(text.strip()) / max(n_pages, 1)
    return avg < 50


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF 文本层提取与扫描件检测")
    parser.add_argument("input", type=pathlib.Path, help="输入 PDF 路径")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出 Markdown/文本路径")
    parser.add_argument("--report", type=pathlib.Path, required=True, help="质量报告 JSON 路径")
    args = parser.parse_args()

    inp = args.input
    if not inp.exists() or inp.suffix.lower() != ".pdf":
        print(f"文件不存在或非 PDF: {inp}", file=sys.stderr)
        sys.exit(1)

    file_hash = sha256_of(inp)
    today = date.today().isoformat()

    text, n_pages, per_page = extract_with_pypdf(inp)

    if n_pages == 0 and not text:
        # No reader available
        print("未安装 pypdf/PyPDF2，无法提取。pip install pypdf", file=sys.stderr)
        print("已标记为待 OCR 扫描件通道", file=sys.stderr)
        scanned = True
        text = ""
    else:
        scanned = is_scanned(text, n_pages)

    # Quality report
    q: dict = {
        "n_pages": n_pages,
        "total_chars": len(text),
        "per_page_chars": per_page,
        "is_scanned": scanned,
        "extraction_method": "pypdf text layer" if not scanned or text else "none (needs OCR)",
        "warning": "扫描件：文本层为空，建议走 OCR 另行处理" if scanned else "",
        "source": {
            "filename": inp.name,
            "sha256": file_hash,
            "params": {"method": "text-layer-first"},
            "date": today,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    if scanned and len(text.strip()) < 50:
        # Do not fabricate: mark and output placeholder
        args.out.write_text(
            f"# PDF 提取结果 — {inp.name}\n\n> 检测为扫描件（每页平均字符 <50），文本层为空。\n> 本技能不做 OCR 工具链，已标记，建议转 OCR 通道后重跑。\n\n- 页数: {n_pages}\n- 总字符: {len(text)}\n",
            encoding="utf-8",
        )
    else:
        args.out.write_text(text, encoding="utf-8")

    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

    kind = "扫描件(需 OCR)" if scanned else "文本层"
    print(f"PDF 提取完成: {inp.name} -> {args.out} [{kind}, {n_pages} 页, {len(text)} 字符]")
    print(f"报告: {args.report}")


if __name__ == "__main__":
    main()
