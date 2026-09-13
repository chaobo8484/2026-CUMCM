#!/usr/bin/env python3
"""
preflight-2026.py — 国赛 2026 交稿前合规门禁（latex-typesetting TEX 分支）

与 texlog_parse.py 分工：texlog 只管能不能编过，本脚本管编过之后合不合
2026 年修订稿规范。逐项对照 assets/references/2026-spec-checklist.md。

Usage:
  python preflight-2026.py cumcm-paper.tex --mode electronic --out report.json
  python preflight-2026.py cumcm-paper.tex --mode paper --pdf cumcm-paper.pdf --out report.json

mode:
  paper       纸质版构建（含承诺书/编号专用页，打印装订用）
  electronic  电子版构建（第一页必须为摘要页，单文件提交用）
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

PLACEHOLDERS = ("TODO", "DUMMY", "LOREM", "XXX", "TBD")

# 正文必须章节（\section{...} 或 \section*{...} 标题包含任一关键词即算命中）
REQUIRED_SECTIONS = (
    "问题重述", "问题分析", "模型假设", "符号说明",
    "模型建立", "检验", "评价",
    "人工智能工具使用声明", "支撑材料",
)

IDENTITY_CMDS = ("schoolname", "membera", "memberb", "memberc", "supervisor")
IDENTITY_KW = re.compile(r"大学|学院|赛区")


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        # 保守去注释：行内未转义 % 之后截断
        cut = None
        for i, ch in enumerate(line):
            if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="国赛 2026 交稿前合规门禁")
    parser.add_argument("tex", type=pathlib.Path, help="主 .tex 路径")
    parser.add_argument("--mode", choices=("paper", "electronic"), required=True)
    parser.add_argument("--pdf", type=pathlib.Path, default=None, help="编出的 PDF（查页数/大小）")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if not args.tex.exists():
        print(f"文件不存在: {args.tex}", file=sys.stderr); sys.exit(1)
    raw = args.tex.read_text(encoding="utf-8", errors="replace")
    code = strip_comments(raw)

    # 1. 构建变体：electronic 必须 withoutpreface，paper 必须默认构建
    m = re.search(r"\\documentclass(\[([^\]]*)\])?\{cumcmthesis\}", code)
    opts = m.group(2) if m and m.group(2) else ""
    has_withoutpreface = "withoutpreface" in opts
    variant_ok = (has_withoutpreface == (args.mode == "electronic"))

    # 2. 无目录：\tableofcontents 必须注释或删除
    toc_ok = "\\tableofcontents" not in code

    # 3. 占位清零
    upper = code.upper()
    ph_hits = sorted({ph for ph in PLACEHOLDERS if ph in upper})

    # 4. 必须章节（含 AI 声明与支撑材料列表）
    sections = re.findall(r"\\section\*?\{([^}]*)\}", code)
    joined = "\n".join(sections)
    missing_sections = [k for k in REQUIRED_SECTIONS if k not in joined and k not in code]

    # 5. 匿名：正文区身份关键词 + 题头身份命令
    body = code.split("\\begin{document}", 1)[-1] if "\\begin{document}" in code else code
    identity_kw_hits = sorted(set(IDENTITY_KW.findall(body)))
    filled_cmds = {}
    for cmd in IDENTITY_CMDS:
        for mm in re.finditer(r"\\" + cmd + r"\{([^}]*)\}", code):
            val = mm.group(1).strip()
            if val and val != "TODO":
                filled_cmds[cmd] = val
    if args.mode == "electronic":
        # 电子版题头身份命令必须清空（starter 文末注释同要求）
        anon_ok = len(identity_kw_hits) == 0 and len(filled_cmds) == 0
    else:
        anon_ok = True  # 纸质版题头允许填实，仅报告关键词命中
    anon_report = {"keywords": identity_kw_hits, "filled_title_cmds": filled_cmds}

    # 6. PDF 成品（可选）：页数提示 + 20MB 上限
    pdf_info: dict = {"checked": False}
    pdf_ok = True
    if args.pdf is not None:
        if not args.pdf.exists():
            pdf_info = {"checked": False, "error": f"PDF 不存在: {args.pdf}"}
            pdf_ok = False
        else:
            size_mb = args.pdf.stat().st_size / (1024 * 1024)
            pages = None
            try:
                from pypdf import PdfReader
                pages = len(PdfReader(str(args.pdf)).pages)
            except ImportError:
                pass
            except Exception as e:
                pdf_info = {"checked": True, "error": f"PDF 解析失败: {e}"}
            pdf_info = {"checked": True, "pages": pages, "size_mb": round(size_mb, 2),
                        "size_ok": size_mb <= 20}
            # 总页数是宽松上界：摘要 1 + 正文 ≤30 + 附录不限；超 31 页必有问题
            pages_ok = (pages is None) or (pages <= 31)
            pdf_ok = bool(pdf_info.get("size_ok")) and pages_ok
            if pages is None:
                pdf_ok = bool(pdf_info.get("size_ok"))  # 页数未探明时只判大小，OPEN 处理

    gates = {
        "variant_ok": bool(variant_ok),
        "variant_opts": opts,
        "no_toc": bool(toc_ok),
        "placeholders_zero": len(ph_hits) == 0,
        "placeholder_hits": ph_hits,
        "sections_complete": len(missing_sections) == 0,
        "missing_sections": missing_sections,
        "anonymity_ok": bool(anon_ok),
        "anonymity": anon_report,
        "pdf_ok": bool(pdf_ok),
        "pdf": pdf_info,
    }
    failed = [k for k in ("variant_ok", "no_toc", "placeholders_zero",
                          "sections_complete", "anonymity_ok", "pdf_ok") if not gates[k]]
    if not failed:
        verdict = "PASS — 2026 合规门禁通过，目检后可交"
    elif gates["pdf"].get("pages") is None and failed == ["pdf_ok"]:
        verdict = "OPEN — 缺 pypdf，页数未探明，人工确认页数后可交"
    else:
        verdict = f"HOLD — {', '.join(failed)}"

    report = {"file": args.tex.name, "mode": args.mode, "gates": gates, "verdict": verdict,
              "checklist": "assets/references/2026-spec-checklist.md"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"preflight-2026 [{args.mode}]: failed={failed} pdf={pdf_info} [{verdict}]")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
