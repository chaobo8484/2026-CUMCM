#!/usr/bin/env python3
"""
figure_gate.py — 投稿图合规门禁（P2）

对应 publication-figure/SKILL.md 合规表机器可检部分：
- 光栅图：尺寸（按 spec 宽 + DPI 反推像素）与 DPI 下限（PIL，无则 OPEN）
- PDF：存在性；pdffonts 可用时查字体嵌入（无则 OPEN 说明）
- 题注五件套（--caption）：N/test/p/effect/CI 关键词齐否（statistical-plot 要求）

Usage:
  python figure_gate.py fig.png --width-mm 89 --dpi-floor 300 --out report.json [--caption "N=..."]
  python figure_gate.py fig.pdf --out report.json [--caption "..."]
"""
from __future__ import annotations
import argparse, json, pathlib, re, shutil, subprocess, sys

def check_raster(path: pathlib.Path, width_mm: float, dpi_floor: int) -> dict:
    try:
        from PIL import Image
    except ImportError:
        return {"raster_available": False, "verdict_hint": "OPEN — 缺 Pillow"}
    im = Image.open(path)
    w, h = im.size
    dpi = im.info.get("dpi", (None, None))[0]
    # expected px at spec width: mm/25.4*dpi_floor
    expect_px = width_mm / 25.4 * dpi_floor
    return {"size_px": [w, h], "dpi": dpi,
            "dpi_ge_floor": (dpi is None) or dpi >= dpi_floor,
            "width_ge_spec": w >= expect_px,
            "expected_px_at_spec": round(expect_px)}

def check_pdf_fonts(path: pathlib.Path) -> dict:
    if not shutil.which("pdffonts"):
        return {"fonts_available": False, "verdict_hint": "OPEN — 无 pdffonts，人工验嵌入"}
    try:
        r = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True, timeout=30)
        lines = r.stdout.splitlines()[2:]
        type3 = [l for l in lines if "Type 3" in l]
        unembedded = [l for l in lines if l.strip() and l.split() and "yes" not in l.lower().split()[-4:]]
        return {"type3": type3, "type3_free": len(type3) == 0, "raw": lines}
    except Exception as e:
        return {"fonts_available": False, "verdict_hint": f"OPEN — pdffonts 失败：{e}"}

def check_caption_five(cap: str | None) -> dict | None:
    if not cap:
        return None
    low = cap.lower()
    return {
        "has_n": bool(re.search(r"\bn\s*=\s*\d+", low)),
        "has_test": bool(re.search(r"t-test|anova|mann|wilcoxon|chi|检验", cap)),
        "has_p": bool(re.search(r"p\s*[=<]\s*0?\.\d+|p\s*<\s*0", low)),
        "has_effect": bool(re.search(r"cohen|d\s*=|r\s*=|or\s*=|δ|Δ|效应", cap)),
        "has_ci": bool(re.search(r"ci|置信区间|95%", low)),
    }

def main():
    parser = argparse.ArgumentParser(description="投稿图合规门禁")
    parser.add_argument("figure", type=pathlib.Path)
    parser.add_argument("--width-mm", type=float, default=89.0)
    parser.add_argument("--dpi-floor", type=int, default=300)
    parser.add_argument("--caption", type=str, default=None)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if not args.figure.exists():
        print(f"文件不存在: {args.figure}", file=sys.stderr); sys.exit(1)
    suffix = args.figure.suffix.lower()
    gates: dict = {"file": str(args.figure)}
    verdicts: list[str] = []

    if suffix in (".png", ".jpg", ".jpeg", ".tiff", ".tif"):
        r = check_raster(args.figure, args.width_mm, args.dpi_floor)
        gates.update(r)
        if r.get("raster_available") is False:
            verdicts.append("OPEN")
        elif not r.get("dpi_ge_floor", True):
            verdicts.append("HOLD — DPI 未达标")
        elif not r.get("width_ge_spec", True):
            verdicts.append(f"HOLD — 像素不足（spec {args.width_mm}mm@{args.dpi_floor}dpi 需约 {r.get('expected_px_at_spec')}px 宽）")
    elif suffix == ".pdf":
        f = check_pdf_fonts(args.figure)
        gates.update(f)
        if f.get("fonts_available") is False:
            verdicts.append("OPEN")
        elif not f.get("type3_free", True):
            verdicts.append("HOLD — 含 Type 3 点阵字体")
    elif suffix == ".svg":
        gates["vector"] = True
    else:
        print(f"不支持的类型: {suffix}", file=sys.stderr); sys.exit(1)

    five = check_caption_five(args.caption)
    if five is not None:
        gates["caption_five"] = five
        if not all(five.values()):
            missing = [k for k, v in five.items() if not v]
            verdicts.append(f"HOLD — 题注缺五件套：{missing}")

    verdict = "PASS" if not verdicts else ("; ".join(verdicts) if any(v.startswith("HOLD") for v in verdicts)
                                            else "OPEN — 工具缺失项人工补验")
    report = {"gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"figure: {gates} [{verdict}]")
    print(f"报告: {args.out}")

if __name__ == "__main__":
    main()
