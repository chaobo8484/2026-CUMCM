#!/usr/bin/env python3
"""
frame_extract.py — MP4 按声明 fps/时间戳抽帧转 JPG（ingest-inputs P0-1）

Hard Rules:
- 抽帧参数显式记录，随数据走
- 整段吞上下文禁止；抽帧后走 JPG 分类 gate

Usage:
  python frame_extract.py input.mp4 --fps 1 --out-dir frames/ --report report.json
  python frame_extract.py input.mp4 --timestamps 0,5,10 --out-dir frames/ --report report.json

Requires: opencv-python (cv2). If missing, reports and exits with guidance.
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


def main() -> None:
    parser = argparse.ArgumentParser(description="MP4 抽帧转 JPG")
    parser.add_argument("input", type=pathlib.Path, help="输入 MP4 路径")
    parser.add_argument("--fps", type=float, default=None, help="抽帧 fps（如 1 表示每秒 1 帧）")
    parser.add_argument("--timestamps", type=str, default=None, help="逗号分隔时间戳秒数，如 0,5,10（与 --fps 二选一）")
    parser.add_argument("--out-dir", type=pathlib.Path, required=True, help="输出帧目录")
    parser.add_argument("--report", type=pathlib.Path, required=True, help="报告 JSON 路径")
    args = parser.parse_args()

    inp = args.input
    if not inp.exists() or inp.suffix.lower() != ".mp4":
        print(f"文件不存在或非 MP4: {inp}", file=sys.stderr)
        sys.exit(1)
    if args.fps is None and args.timestamps is None:
        print("需指定 --fps 或 --timestamps 之一", file=sys.stderr)
        sys.exit(1)

    file_hash = sha256_of(inp)
    today = date.today().isoformat()

    try:
        import cv2  # type: ignore
    except ImportError:
        print("未安装 opencv-python: pip install opencv-python", file=sys.stderr)
        # Write report marking as blocked
        q = {
            "error": "opencv-python not installed",
            "source": {"filename": inp.name, "sha256": file_hash, "params": {"fps": args.fps, "timestamps": args.timestamps}, "date": today},
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(q, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    cap = cv2.VideoCapture(str(inp))
    if not cap.isOpened():
        print(f"无法打开视频: {inp}", file=sys.stderr)
        sys.exit(1)

    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps_src if fps_src else 0

    args.out_dir.mkdir(parents=True, exist_ok=True)

    extracted: list[dict] = []

    if args.timestamps is not None:
        timestamps = [float(x.strip()) for x in args.timestamps.split(",") if x.strip()]
        for ts in timestamps:
            frame_idx = int(ts * fps_src)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                print(f"警告: 时间戳 {ts}s 抽帧失败", file=sys.stderr)
                continue
            out_path = args.out_dir / f"frame_{ts:.2f}s.jpg"
            cv2.imwrite(str(out_path), frame)
            extracted.append({"timestamp": ts, "frame_idx": frame_idx, "file": out_path.name})
    else:
        # fps mode: sample every (fps_src / target_fps) frames
        assert args.fps is not None
        step = max(1, int(round(fps_src / args.fps)))
        idx = 0
        saved = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % step == 0:
                ts = idx / fps_src
                out_path = args.out_dir / f"frame_{ts:.2f}s.jpg"
                cv2.imwrite(str(out_path), frame)
                extracted.append({"timestamp": round(ts, 2), "frame_idx": idx, "file": out_path.name})
                saved += 1
            idx += 1

    cap.release()

    q = {
        "source_fps": fps_src,
        "frame_count": frame_count,
        "duration_sec": round(duration, 2),
        "extracted": extracted,
        "n_extracted": len(extracted),
        "next_step": "抽帧产物为 JPG，需走 classify_jpg.py 分类 gate（数据图/示例图/分不清）",
        "source": {
            "filename": inp.name,
            "sha256": file_hash,
            "params": {"fps": args.fps, "timestamps": args.timestamps},
            "date": today,
        },
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

    print(f"抽帧完成: {inp.name} -> {args.out_dir} ({len(extracted)} 帧, 源 {fps_src:.1f}fps, {duration:.1f}s)")
    print(f"报告: {args.report}")


if __name__ == "__main__":
    main()
