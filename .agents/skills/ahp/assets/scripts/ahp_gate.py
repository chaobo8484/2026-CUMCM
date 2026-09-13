#!/usr/bin/env python3
"""
ahp_gate.py — AHP 判断矩阵权重与一致性门禁（P0-2）

Hard Rules 对应（ahp/SKILL.md）：
- Saaty 1-9 标度，倒数强制
- CR < 0.1 门禁，定位最不一致三元组
- 权重来自确认矩阵用代码算主特征向量

RI 标准表：n=1..8 -> 0,0,0.58,0.90,1.12,1.24,1.32,1.41

Usage:
  python ahp_gate.py matrix.csv --out report.json
  matrix.csv 为 n x n 判断矩阵，含表头可选；第一列可为行标签

  示例 3x3：
  ,C1,C2,C3
  C1,1,3,5
  C2,1/3,1,2
  C3,1/5,1/2,1

  支持分数形式 1/3 自动解析
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from fractions import Fraction

import numpy as np

RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def parse_entry(s: str) -> float:
    s = str(s).strip()
    if "/" in s:
        try:
            return float(Fraction(s))
        except ValueError:
            pass
    return float(s)


def load_matrix(path: pathlib.Path) -> tuple[np.ndarray, list[str]]:
    import pandas as pd
    df = pd.read_csv(path, header=0, dtype=str, keep_default_na=False)
    first_col = str(df.columns[0])
    labels: list[str] = []
    mat = None  # type: ignore
    if first_col.startswith("Unnamed") or first_col.strip() == "":
        # Labeled matrix with header row like ",C1,C2,C3"
        labels = df.iloc[:, 0].tolist()
        mat = df.iloc[:, 1:].values
    else:
        # Could be labeled (first col is row labels) or unlabeled
        vals = df.iloc[:, 0].tolist()
        col_labels = list(df.columns)
        # Check if first column values are labels (non-numeric)
        has_labels = False
        for v in vals:
            try:
                parse_entry(v)
            except ValueError:
                has_labels = True
                break
            if str(v).strip() in col_labels:
                has_labels = True
                break
        if has_labels:
            labels = vals
            mat = df.iloc[:, 1:].values
            # Also handle case where df has extra col due to header mismatch
            # If mat is not square but df without first col is square, use it
            if mat.shape[0] != mat.shape[1] and df.shape[1] == df.shape[0]:
                # No row labels, header is actual data header
                labels = list(df.columns)
                mat = df.values
        else:
            # Unlabeled: entire df is matrix, header row is first data row?
            # Check if df columns look numeric or header-like
            try:
                for c in df.columns:
                    parse_entry(c)
                # Columns are numeric -> header was actually data, need to include it
                # Reload without header
                df2 = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
                mat = df2.values
                labels = [f"C{i+1}" for i in range(mat.shape[0])]
            except ValueError:
                # Columns are labels
                labels = list(df.columns)
                mat = df.values

    # Parse to float
    n = mat.shape[0]
    if mat.shape[0] != mat.shape[1]:
        print(f"矩阵非方阵: {mat.shape}", file=sys.stderr)
        sys.exit(1)
    A = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            try:
                A[i, j] = parse_entry(mat[i, j])
            except Exception as e:
                print(f"无法解析 ({i},{j})='{mat[i,j]}': {e}", file=sys.stderr)
                sys.exit(1)
    if not labels or len(labels) != n:
        labels = [f"C{i+1}" for i in range(n)]
    return A, labels


def check_reciprocal(A: np.ndarray, tol: float = 1e-6) -> list[str]:
    warnings: list[str] = []
    n = A.shape[0]
    for i in range(n):
        if abs(A[i, i] - 1.0) > tol:
            warnings.append(f"对角元 ({i},{i})={A[i,i]} != 1")
        for j in range(i + 1, n):
            if abs(A[i, j] * A[j, i] - 1.0) > tol:
                warnings.append(f"倒数 violation: ({i},{j})={A[i,j]} * ({j},{i})={A[j,i]} = {A[i,j]*A[j,i]:.4f} !=1")
    return warnings


def ahp_weights(A: np.ndarray) -> tuple[np.ndarray, float]:
    # Principal eigenvector method
    eigvals, eigvecs = np.linalg.eig(A)
    # Find max real eigenvalue
    idx = int(np.argmax(eigvals.real))
    lam_max = float(eigvals[idx].real)
    vec = eigvecs[:, idx].real
    # Ensure positive
    vec = np.abs(vec)
    w = vec / vec.sum()
    return w, lam_max


def most_inconsistent_triplet(A: np.ndarray) -> tuple[int, int, int, float]:
    """Find (i,j,k) where |a_ij * a_jk - a_ik| is largest."""
    n = A.shape[0]
    best = (0, 1, 2, 0.0)
    max_diff = -1.0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if i == j or j == k or i == k:
                    continue
                diff = abs(A[i, j] * A[j, k] - A[i, k])
                if diff > max_diff:
                    max_diff = diff
                    best = (i, j, k, diff)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="AHP 门禁：权重 + CR + 最不一致三元组")
    parser.add_argument("matrix", type=pathlib.Path, help="判断矩阵 CSV 路径")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="输出报告 JSON 路径")
    parser.add_argument("--labels", type=str, default=None, help="逗号分隔标签覆盖")
    args = parser.parse_args()

    A, labels = load_matrix(args.matrix)
    if args.labels:
        labels = [s.strip() for s in args.labels.split(",")]
    n = A.shape[0]

    reciprocal_warnings = check_reciprocal(A)
    w, lam_max = ahp_weights(A)
    CI = (lam_max - n) / (n - 1) if n > 1 else 0.0
    RI = RI_TABLE.get(n, 1.49)
    CR = CI / RI if RI != 0 else 0.0
    passed = CR < 0.1

    i, j, k, diff = most_inconsistent_triplet(A)

    report: dict = {
        "n": n,
        "labels": labels,
        "matrix": A.tolist(),
        "weights": {labels[idx]: round(float(w[idx]), 4) for idx in range(n)},
        "lambda_max": round(float(lam_max), 4),
        "CI": round(float(CI), 4),
        "RI": RI,
        "CR": round(float(CR), 4),
        "CR_pass": passed,
        "reciprocal_warnings": reciprocal_warnings,
        "most_inconsistent_triplet": {
            "indices": [i, j, k],
            "labels": [labels[i], labels[j], labels[k]],
            "a_ij": round(float(A[i, j]), 4),
            "a_jk": round(float(A[j, k]), 4),
            "a_ik": round(float(A[i, k]), 4),
            "diff": round(float(diff), 4),
            "suggestion": f"重议 ({labels[i]} vs {labels[k]})，当前 {A[i,k]:.3f} 与链式 {A[i,j]*A[j,k]:.3f} 偏差最大",
        },
        "verdict": "PASS" if passed else "HOLD — 请重议最不一致三元组后重算",
        "method": "principal eigenvector (numpy.linalg.eig)",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    status = "PASS" if passed else "HOLD"
    print(f"AHP 门禁: n={n} lambda_max={lam_max:.4f} CI={CI:.4f} CR={CR:.4f} [{status}]")
    print(f"权重: {report['weights']}")
    if reciprocal_warnings:
        print("倒数警告:")
        for wmsg in reciprocal_warnings:
            print(f"  - {wmsg}")
    if not passed:
        print(f"最不一致三元组: {labels[i]}-{labels[j]}-{labels[k]} diff={diff:.4f}")
    print(f"报告: {args.out}")


if __name__ == "__main__":
    main()
