#!/usr/bin/env python3
"""
setup-fonts.py — cumcmthesis 官方字体一次检查/安装（latex-typesetting 国赛分支）

背景：cumcmthesis.cls 按文件名调用 simkai.ttf / simsun.ttc（Windows 自带）。
Linux / macOS 默认没有。两条路：

1. 零操作编译：starter 默认加载 cumcm-fonts.sty，缺官方字体时自动用
   系统现有中文字体回退（Songti SC / Noto Serif CJK SC / Fandol），直接编。
2. 官方原字形：从你的 Windows 机器（C:\\Windows\\Fonts）取回两文件，
   用本脚本一次装进系统字体目录（--copy-from + --dest userfonts），
   之后所有稿件都不用再往工作目录放字体。

Usage:
  python setup-fonts.py --out report.json
  python setup-fonts.py --copy-from <含两字体文件的目录> --dest userfonts --out report.json
  python setup-fonts.py --copy-from <含两字体文件的目录> --dest <稿件工作目录> --out report.json
"""
from __future__ import annotations
import argparse, json, os, pathlib, platform, shutil, subprocess, sys

WANTED = ("simsun.ttc", "simkai.ttf")


def user_font_dir() -> pathlib.Path:
    sysname = platform.system()
    if sysname == "Windows":
        return pathlib.Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    if sysname == "Darwin":
        return pathlib.Path.home() / "Library" / "Fonts"
    return pathlib.Path.home() / ".local" / "share" / "fonts"


def detect() -> dict:
    """系统级探测：fc-list（Linux/macOS）+ 常见字体目录文件名匹配。"""
    found: dict[str, list[str]] = {w: [] for w in WANTED}
    if shutil.which("fc-list"):
        try:
            out = subprocess.run(["fc-list", ":", "file"], capture_output=True,
                                 text=True, timeout=60).stdout.lower()
            for line in out.splitlines():
                base = line.rsplit("/", 1)[-1].strip().strip('"')
                for w in WANTED:
                    if base == w and line.strip() not in found[w]:
                        found[w].append(line.strip())
        except Exception:
            pass
    candidates: list[pathlib.Path] = []
    if platform.system() == "Windows":
        candidates.append(pathlib.Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    else:
        candidates += [pathlib.Path("/usr/share/fonts"),
                       pathlib.Path("/usr/local/share/fonts"),
                       pathlib.Path.home() / ".local" / "share" / "fonts",
                       pathlib.Path.home() / ".fonts",
                       pathlib.Path("/Library/Fonts"),
                       pathlib.Path.home() / "Library" / "Fonts"]
    for d in candidates:
        if not d.is_dir():
            continue
        try:
            for p in d.rglob("*"):
                if p.is_file() and p.name.lower() in WANTED:
                    s = str(p)
                    if s not in found[p.name.lower()]:
                        found[p.name.lower()].append(s)
        except (OSError, PermissionError):
            continue
    return found


def main():
    parser = argparse.ArgumentParser(description="cumcmthesis 官方字体检查/安装")
    parser.add_argument("--copy-from", type=pathlib.Path, default=None,
                        help="含 simsun.ttc / simkai.ttf 的来源目录")
    parser.add_argument("--dest", type=str, default=None,
                        help="userfonts（系统字体目录，每台机器一次）或目标目录路径")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    copied: list[str] = []
    if args.copy_from is not None:
        if not args.copy_from.is_dir():
            print(f"来源目录不存在: {args.copy_from}", file=sys.stderr); sys.exit(1)
        src = {}
        for p in args.copy_from.iterdir():
            if p.is_file() and p.name.lower() in WANTED:
                src[p.name.lower()] = p
        missing_src = [w for w in WANTED if w not in src]
        if missing_src:
            print(f"来源目录缺文件: {missing_src}", file=sys.stderr); sys.exit(1)
        dest = user_font_dir() if args.dest in (None, "userfonts") else pathlib.Path(args.dest)
        dest.mkdir(parents=True, exist_ok=True)
        for w, p in src.items():
            shutil.copy2(p, dest / w)
            copied.append(str(dest / w))
        if platform.system() == "Linux" and shutil.which("fc-cache"):
            subprocess.run(["fc-cache", "-f", str(dest)], capture_output=True, timeout=120)

    found = detect()
    exact_ok = all(found[w] for w in WANTED)
    gates = {
        "exact_fonts_systemwide": bool(exact_ok),
        "simsun": found["simsun.ttc"],
        "simkai": found["simkai.ttf"],
        "copied_this_run": copied,
        # 缺官方字体不 HOLD：cumcm-fonts.sty 自动回退，照常编译
        "fallback_covers": True,
    }
    if exact_ok:
        verdict = "PASS — 官方字体系统级可用，cls 原设置直编"
    elif copied:
        verdict = "PASS — 已安装，重编前确认 fc-list 能查到两文件"
    else:
        verdict = ("OPEN — 无官方字体，用 cumcm-fonts.sty 回退照常编译；"
                   "要原字形则 --copy-from <含两文件的目录> --dest userfonts 装一次")

    report = {"wanted": list(WANTED), "user_font_dir": str(user_font_dir()),
              "gates": gates, "verdict": verdict}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"fonts: simsun={len(found['simsun.ttc'])} simkai={len(found['simkai.ttf'])} [{verdict}]")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
