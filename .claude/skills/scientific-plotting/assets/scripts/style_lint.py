#!/usr/bin/env python3
"""
style_lint.py — 绘图脚本风格门禁（P2）

对应 scientific-plotting/SKILL.md Hard Rules：
- 禁 jet/rainbow/hsv 与红绿关键编码（源码级拦截）
- savefig 必须带 dpi + bbox（论文 PNG ≥300dpi）
- 样式块复用信号：rcParams 或 style.use 出现即算复用声明

Usage:
  python style_lint.py plot.py --out report.json [--dpi-floor 300]
  只做源码静态检查，不运行绘图；视觉（灰度/bbox）仍需人眼。
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

BANNED_CMAPS = ("jet", "rainbow", "hsv", "nipy_spectral", "gist_rainbow")
BANNED_CRITICAL = (re.compile(r"color\s*=\s*['\"](red|green)['\"]"),)

def main():
    parser = argparse.ArgumentParser(description="绘图风格门禁")
    parser.add_argument("script", type=pathlib.Path, help="绘图 .py 脚本")
    parser.add_argument("--dpi-floor", type=int, default=300)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if not args.script.exists():
        print(f"脚本不存在: {args.script}", file=sys.stderr); sys.exit(1)
    text = args.script.read_text(encoding="utf-8", errors="replace")
    low = text.lower()

    banned = sorted({c for c in BANNED_CMAPS if re.search(rf"cmap\s*=\s*['\"]{c}['\"]", low)})
    redgreen = bool(any(p.search(low) for p in BANNED_CRITICAL))
    has_savefig = "savefig" in low
    dpi_vals = [int(x) for x in re.findall(r"dpi\s*=\s*(\d+)", low)]
    dpi_ok = bool(dpi_vals) and all(v >= args.dpi_floor for v in dpi_vals) if has_savefig else None
    bbox = "bbox_inches" in low
    style_block = ("rcparams" in low) or ("style.use" in low)
    vector = bool(re.search(r"savefig\(.*\.(pdf|svg)", low))

    gates = {
        "no_banned_cmap": len(banned) == 0,
        "banned_found": banned,
        "no_redgreen_critical": not redgreen,
        "has_savefig": has_savefig,
        "dpi_ge_floor": dpi_ok,
        "dpi_values": dpi_vals,
        "bbox_checked": bbox,
        "style_block_reused": style_block,
        "vector_export": vector,
    }
    if banned or redgreen:
        verdict = f"HOLD — 禁用色板/编码：{banned}；换 Okabe-Ito/viridis"
    elif has_savefig and dpi_ok is False:
        verdict = f"HOLD — DPI<{args.dpi_floor}，重导出"
    elif not has_savefig:
        verdict = "OPEN — 无 savefig，疑似未落盘脚本"
    else:
        verdict = "PASS — 源码风格过；灰度/bbox 仍需人眼"

    report = {"script": str(args.script), "gates": gates, "verdict": verdict,
              "note": "静态检查不运行代码；视觉验收仍按 SKILL 目检"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"style: banned={banned} dpi={dpi_vals} vector={vector} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
