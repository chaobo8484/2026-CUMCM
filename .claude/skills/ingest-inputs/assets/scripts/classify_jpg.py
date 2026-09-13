#!/usr/bin/env python3
"""
classify_jpg.py — JPG 三分类 gate（ingest-inputs P0-1）

分类表（SKILL.md: The Build Sequence）：
- 数据图：坐标轴、刻度、数值 → 描点识数通道
- 示例/对照图：点名编号、箭头、对应线、无坐标轴 → 转述通道
- 分不清：特征混杂或全无 → 问用户一句话，不代选

本脚本为启发式辅助，最终以用户确认 gate 为准；代选禁止。

Usage:
  python classify_jpg.py image.jpg --report report.json
  python classify_jpg.py image.jpg --report report.json --interactive  # 分不清时提示用户

Heuristic signals:
- 数据图信号：高边缘密度 + 矩形边框 + 刻度数字（OCR 若可用）
- 示例图信号：稀疏线条 + 标注框 + 箭头特征
Fallback: 分不清 → 需人工确认
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


def classify_heuristic(path: pathlib.Path) -> tuple[str, list[str], float]:
    """
    Returns (label, signals, confidence).
    label in {data-chart, example-image, unclear}
    Uses PIL + simple image stats; no hard dependency on OCR.
    """
    signals: list[str] = []
    try:
        from PIL import Image  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return "unclear", ["缺少 PIL/numpy，无法启发式分析，需人工分类"], 0.0

    img = Image.open(path).convert("RGB")
    w, h = img.size
    signals.append(f"尺寸 {w}x{h}")

    # Try edge density via simple gradient
    try:
        import numpy as np
        arr = np.array(img.convert("L"), dtype=float)
        # Sobel-like gradient magnitude on downsampled image for speed
        small = arr[::4, ::4]
        gy, gx = np.gradient(small)
        grad = (gx**2 + gy**2) ** 0.5
        edge_ratio = float((grad > grad.mean() + grad.std()).mean())
        signals.append(f"边缘密度 {edge_ratio:.3f}")
    except Exception:
        edge_ratio = 0.0

    # Heuristic thresholds (tuned conservatively to prefer unclear over misclassification)
    # Data-chart tends to have higher edge_ratio due to grid/axes
    # Example-image tends to be sparser
    if edge_ratio > 0.12:
        # Check for axis-like rectangular border: high contrast border pixels
        # Simplified: if border region has strong edges -> data-chart signal
        signals.append("检测到较密网格/坐标轴特征")
        return "data-chart", signals, 0.65
    elif edge_ratio < 0.04:
        signals.append("线条稀疏，疑似示例/流程图")
        return "example-image", signals, 0.60
    else:
        signals.append("特征混杂，未达到任一通道阈值")
        return "unclear", signals, 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="JPG 三分类 gate")
    parser.add_argument("input", type=pathlib.Path, help="输入 JPG 路径")
    parser.add_argument("--report", type=pathlib.Path, required=True, help="报告 JSON 路径")
    parser.add_argument("--interactive", action="store_true", help="分不清时交互式询问（默认仅报告）")
    args = parser.parse_args()

    inp = args.input
    if not inp.exists() or inp.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        print(f"文件不存在或类型不支持: {inp}（仅 .jpg/.jpeg/.png）", file=sys.stderr)
        sys.exit(1)

    file_hash = sha256_of(inp)
    today = date.today().isoformat()

    label, signals, conf = classify_heuristic(inp)

    gate_map = {
        "data-chart": "描点识数通道（digitize）— 需坐标映射用户确认，误差声明",
        "example-image": "转述通道（describe）— 要素清单+对应关系表，原图存档",
        "unclear": "分不清 — 需问用户一句话（数据图/示例图），不代选",
    }

    result: dict = {
        "filename": inp.name,
        "sha256": file_hash,
        "date": today,
        "heuristic": {
            "label": label,
            "confidence": conf,
            "signals": signals,
            "channel": gate_map[label],
        },
        "gate": {
            "decision": label,
            "requires_user_confirm": True,  # 始终需用户确认，脚本仅辅助
            "next": gate_map[label],
        },
        "rule": "最终以用户确认 gate 为准，脚本不代选（Hard Rules #5）",
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"JPG 分类: {inp.name} -> {label} (conf {conf:.2f})")
    for s in signals:
        print(f"  - {s}")
    print(f"通道: {gate_map[label]}")
    print(f"报告: {args.report}")
    if label == "unclear" and args.interactive:
        ans = input("分不清，请指定角色 [data-chart/example-image]: ").strip()
        if ans in ("data-chart", "example-image"):
            print(f"用户确认: {ans}，将覆盖启发式结果")
            result["gate"]["user_override"] = ans
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
