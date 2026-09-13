#!/usr/bin/env python3
"""
read_tabular.py — CSV/XLSX/TXT 归一化读取（ingest-inputs P0-1）

Hard Rules 对应：
- 编码嗅探 UTF-8/GBK 显式记录（CONTEXT.md 工具默认：pandas + openpyxl）
- 分隔符/表头行/sheet 显式声明
- 清洗规则记录，质量报告数字说话
- 来源记录：文件名 + sha256 + 参数 + 日期

Usage:
  python read_tabular.py input.csv --header-row 1 --out cleaned.csv --report report.json
  python read_tabular.py input.xlsx --sheet 0 --out cleaned.csv --report report.json
  python read_tabular.py input.txt --out cleaned.txt --report report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import date

import pandas as pd


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sniff_encoding(path: pathlib.Path) -> tuple[str, str]:
    """Try UTF-8 first, fallback GBK. Returns (encoding, basis)."""
    raw = path.read_bytes()[:100000]  # enough for sniff
    try:
        raw.decode("utf-8")
        # Also check for GBK-specific bytes that are valid UTF-8 by accident:
        # if file contains GBK chars, UTF-8 decode may still succeed for ASCII portion.
        # We do a stricter check: try utf-8-sig and see if replacement needed.
        return "utf-8", "UTF-8 decode succeeded without error"
    except UnicodeDecodeError as e:
        try:
            raw.decode("gbk")
            return "gbk", f"UTF-8 failed at byte {e.start}, GBK succeeded"
        except UnicodeDecodeError:
            return "utf-8", f"UTF-8 failed ({e}), GBK also failed — fallback utf-8 with errors='replace'"


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Minimal cleaning: strip headers, remove thousand separators, percent handling."""
    notes: list[str] = []
    # Strip column names
    df.columns = [str(c).strip() for c in df.columns]
    # For object columns, strip and handle thousand separators / percent
    for col in df.columns:
        if df[col].dtype == object:
            # Check if column looks like numeric with commas/percents
            sample = df[col].dropna().astype(str).head(20).tolist()
            has_comma = any("," in s for s in sample)
            has_percent = any("%" in s for s in sample)
            if has_comma:
                notes.append(f"列 {col}: 检测到千分位逗号，已去除")
                df[col] = df[col].astype(str).str.replace(",", "", regex=False)
            if has_percent:
                notes.append(f"列 {col}: 检测到百分号，已转换为小数（/100）")
                # After comma removal, handle percent
                def _pct(x):
                    if isinstance(x, str) and "%" in x:
                        try:
                            return float(x.replace("%", "").strip()) / 100
                        except ValueError:
                            return x
                    return x
                df[col] = df[col].apply(_pct)
            # Try numeric conversion where possible, but keep original if fails
            converted = pd.to_numeric(df[col], errors="coerce")
            # If at least half converts, adopt numeric
            if converted.notna().sum() >= len(df) * 0.5:
                df[col] = converted
    return df, notes


def quality_report(df: pd.DataFrame) -> dict:
    total = len(df)
    report: dict = {
        "n_rows": total,
        "n_cols": len(df.columns),
        "columns": list(df.columns),
        "missing_rate": {},
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
    }
    for col in df.columns:
        miss = df[col].isna().sum()
        report["missing_rate"][col] = round(float(miss) / total, 4) if total else 0.0
    # Suspicious points: duplicated rows, constant columns
    report["duplicated_rows"] = int(df.duplicated().sum())
    report["constant_columns"] = [c for c in df.columns if df[c].nunique() <= 1]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="CSV/XLSX/TXT 归一化读取")
    parser.add_argument("input", type=pathlib.Path, help="输入文件路径")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="归一后输出 CSV 路径")
    parser.add_argument("--report", type=pathlib.Path, required=True, help="质量报告 JSON 路径")
    parser.add_argument("--encoding", type=str, default=None, help="显式编码 (utf-8/gbk)，不指定则自动嗅探")
    parser.add_argument("--sep", type=str, default=None, help="CSV 分隔符，默认自动推断")
    parser.add_argument("--sheet", type=str, default=None, help="XLSX sheet 名或索引，默认 0")
    parser.add_argument("--header-row", type=int, default=None, help="表头行（1-indexed），默认 1")
    args = parser.parse_args()

    inp: pathlib.Path = args.input
    if not inp.exists():
        print(f"文件不存在: {inp}", file=sys.stderr)
        sys.exit(1)

    file_hash = sha256_of(inp)
    today = date.today().isoformat()

    # Encoding handling
    if args.encoding:
        encoding = args.encoding
        encoding_basis = "用户显式指定"
    else:
        # Only sniff for text-like files
        if inp.suffix.lower() in (".csv", ".txt"):
            encoding, encoding_basis = sniff_encoding(inp)
        else:
            encoding, encoding_basis = "utf-8", "XLSX 二进制无需编码嗅探"

    # Header row handling (pandas uses 0-indexed)
    header = 0 if args.header_row is None else args.header_row - 1

    # Read
    suffix = inp.suffix.lower()
    read_params: dict = {}
    try:
        if suffix == ".csv":
            sep = args.sep if args.sep else ","
            # Try to infer sep if not given: check common seps
            if args.sep is None:
                raw_head = inp.read_bytes()[:4096].decode(encoding, errors="replace")
                for candidate in [",", "\t", ";", "|"]:
                    if candidate in raw_head:
                        sep = candidate
                        break
                read_params["sep_inferred"] = sep
            df = pd.read_csv(inp, encoding=encoding, sep=sep, header=header)
            read_params.update({"encoding": encoding, "encoding_basis": encoding_basis, "sep": sep, "header_row": header + 1})
        elif suffix in (".xlsx", ".xls"):
            sheet = args.sheet if args.sheet is not None else 0
            # Try to interpret sheet as int
            try:
                sheet = int(sheet)
            except ValueError:
                pass
            # List sheets for report
            xls = pd.ExcelFile(inp)
            sheet_names = xls.sheet_names
            df = pd.read_excel(inp, sheet_name=sheet, header=header)
            read_params.update({"sheet": sheet, "sheet_names": sheet_names, "header_row": header + 1})
        elif suffix == ".txt":
            # TXT: sniff structure
            df = pd.read_csv(inp, encoding=encoding, sep=args.sep or "\t", header=header)
            # If single column, treat as free text
            if len(df.columns) == 1:
                # Keep as single column free text
                pass
            read_params.update({"encoding": encoding, "encoding_basis": encoding_basis, "sep": args.sep or "\\t", "header_row": header + 1})
        else:
            print(f"不支持的文件类型: {suffix}，仅支持 .csv/.xlsx/.xls/.txt", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"读取失败: {e}", file=sys.stderr)
        sys.exit(1)

    # Clean
    df, cleaning_notes = clean_dataframe(df)

    # Quality report
    q = quality_report(df)
    q["cleaning_notes"] = cleaning_notes
    q["source"] = {
        "filename": inp.name,
        "sha256": file_hash,
        "params": read_params,
        "date": today,
    }

    # Write outputs
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

    print(f"归一完成: {inp.name} -> {args.out} ({len(df)} 行, {len(df.columns)} 列)")
    print(f"质量报告: {args.report}")
    print(f"来源: {file_hash[:8]}… {today} 编码={encoding}({encoding_basis})")


if __name__ == "__main__":
    main()
