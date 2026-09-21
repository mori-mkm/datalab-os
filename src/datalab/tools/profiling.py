"""Dataset loading and profiling (Data Engineering capability)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"dataset not found: {path}")
    return pd.read_csv(path)


def binary_target(df: pd.DataFrame, target: str, positive_label: Any = None) -> tuple[pd.Series, Any]:
    """Return (0/1 series aligned to df.index, positive label). Rows with a missing target get NaN."""
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not in dataset (columns: {list(df.columns)})")
    values = sorted(df[target].dropna().unique())
    if len(values) != 2:
        raise ValueError(f"target '{target}' must be binary, found {len(values)} distinct values")
    if positive_label is None:
        positive = values[-1]
    else:
        positive = next((v for v in values if str(v) == str(positive_label)), None)
        if positive is None:
            raise ValueError(f"positive_label {positive_label!r} not among target values {values}")
    y = (df[target] == positive).astype(float).where(df[target].notna())
    return y, positive


def profile_dataset(df: pd.DataFrame, target: str, positive_label: Any = None) -> dict[str, Any]:
    y, positive = binary_target(df, target, positive_label)
    n_rows = len(df)
    missing = df.isna().sum()
    duplicates = int(df.duplicated().sum())
    counts = df[target].value_counts(dropna=False)
    positive_rate = float(y.mean())

    issues: list[str] = []
    for col, n in missing[missing / max(n_rows, 1) > 0.3].items():
        issues.append(f"'{col}' has {n / n_rows:.0%} missing values")
    if duplicates:
        issues.append(f"{duplicates} duplicated rows")
    if min(positive_rate, 1 - positive_rate) < 0.1:
        issues.append(f"imbalanced target (positive rate {positive_rate:.1%})")
    if df[target].isna().any():
        issues.append(f"{int(df[target].isna().sum())} rows have a missing target and are ignored in modeling")

    return {
        "profile": {
            "rows": n_rows,
            "columns": df.shape[1],
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "missing": {c: {"count": int(missing[c]), "pct": float(missing[c] / max(n_rows, 1))} for c in df.columns},
            "duplicates": duplicates,
            "target": {
                "column": target,
                "positive_label": positive,
                "counts": {str(k): int(v) for k, v in counts.items()},
                "positive_rate": positive_rate,
            },
        },
        "quality": {
            "missing_cells": int(missing.sum()),
            "missing_pct": float(missing.sum() / max(df.size, 1)),
            "duplicate_rows": duplicates,
            "issues": issues,
        },
    }
