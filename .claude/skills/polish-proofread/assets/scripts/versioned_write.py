#!/usr/bin/env python3
"""
versioned_write.py — 写作类迭代/追溯（P1-5）

对标 patent-disclosure 的 merger.md / correction_handler.md 轻量化：
- 检测是否已存在草稿 → 走 merge 分支而非覆盖
- 输出带时间戳版本 + revisions.md 修订记录
- 保留 diff 可追溯

Usage:
  python versioned_write.py --in draft.md --out-dir ./paper --base-name outline --message "导师意见：摘要压缩"
  产出：
    paper/outline_v20260906_1430.md
    paper/revisions.md  (追加一条)

也可用于 latex-typesetting / polish-proofread（改 --base-name / 扩展名）
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
from datetime import datetime


def sha256_of(path: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_latest(out_dir: pathlib.Path, base_name: str) -> pathlib.Path | None:
    candidates = sorted(out_dir.glob(f"{base_name}_v*.md")) + sorted(out_dir.glob(f"{base_name}_v*.tex"))
    if not candidates:
        return None
    # Sort by timestamp in filename descending
    return sorted(candidates)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="迭代式版本化写入")
    parser.add_argument("--in", dest="inp", type=pathlib.Path, required=True, help="本次新稿路径")
    parser.add_argument("--out-dir", type=pathlib.Path, required=True, help="输出目录")
    parser.add_argument("--base-name", type=str, required=True, help="基名，如 outline / paper / polish")
    parser.add_argument("--message", type=str, default="", help="本次修订说明（导师意见/审稿意见）")
    parser.add_argument("--ext", type=str, default=None, help="扩展名 .md/.tex，默认沿用输入文件扩展名")
    args = parser.parse_args()

    inp: pathlib.Path = args.inp
    if not inp.exists():
        print(f"输入不存在: {inp}", file=sys.stderr)
        sys.exit(1)

    out_dir: pathlib.Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = args.ext or inp.suffix or ".md"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{args.base_name}_v{timestamp}{ext}"

    # Check existing drafts
    latest = find_latest(out_dir, args.base_name)
    mode = "create" if latest is None else "iterate"

    content = inp.read_bytes()
    out_path.write_bytes(content)

    # Write revisions.md
    rev_path = out_dir / "revisions.md"
    is_new = not rev_path.exists()
    sha = sha256_of(out_path)
    prev_sha = sha256_of(latest) if latest else "—"

    # Simple diff hint: file size delta
    prev_size = latest.stat().st_size if latest else 0
    cur_size = out_path.stat().st_size
    delta = cur_size - prev_size

    header = ""
    if is_new:
        header = f"# Revisions — {args.base_name}\n\n> 首次创建起追溯，每次迭代追加一条，不覆盖旧稿。\n\n| 时间 | 模式 | 文件 | 大小变化 | sha | 说明 |\n|---|---|---|---|---|---|\n"

    row = f"| {timestamp} | {mode} | {out_path.name} | {delta:+d} bytes | {sha[:8]}… | {args.message or '—'} |\n"
    if is_new:
        rev_path.write_text(header + row, encoding="utf-8")
    else:
        with open(rev_path, "a", encoding="utf-8") as f:
            f.write(row)

    print(f"模式: {mode}（{'无旧稿，首次创建' if mode=='create' else f'基于 {latest.name} 迭代'}）")
    print(f"产出: {out_path} ({cur_size} bytes, sha {sha[:8]}…)")

    print(f"修订记录: {rev_path}")
    if latest:
        print(f"上一版: {latest} ({prev_sha[:8]}…)")
        print("提示：用 git diff 或 diff 工具对比两版，保留审稿意见可追溯。")
    else:
        print("提示：后续再次运行将自动进入 iterate 分支，不覆盖本版。")


if __name__ == "__main__":
    main()
