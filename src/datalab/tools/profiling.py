"""Dataset loading, structural profiling and data-quality assessment (Data Engineering capabilities).

Profiling reads the data once; quality assessment works from the (small) profile only, so the two agents
never recompute each other's work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"dataset not found: {path}")
    return pd.read_csv(path)


def read_columns(path: Path) -> list[str]:
    """Header only: cheap schema check that does not load the data."""
    if not path.is_file():
        raise FileNotFoundError(f"dataset not found: {path}")
    return list(pd.read_csv(path, nrows=0).columns)


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
    """Structural profile: shape, dtypes, missing values, duplicates and the target distribution."""
    y, positive = binary_target(df, target, positive_label)
    n_rows = len(df)
    missing = df.isna().sum()
    counts = df[target].value_counts(dropna=False)
    return {
        "rows": n_rows,
        "columns": df.shape[1],
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "missing": {c: {"count": int(missing[c]), "pct": float(missing[c] / max(n_rows, 1))} for c in df.columns},
        "duplicates": int(df.duplicated().sum()),
        "target": {
            "column": target,
            "positive_label": positive,
            "counts": {str(k): int(v) for k, v in counts.items()},
            "positive_rate": float(y.mean()),
        },
    }


def assess_quality(profile: dict[str, Any]) -> dict[str, Any]:
    """Data-quality findings derived from a profile (no access to the data)."""
    n_rows = profile["rows"]
    missing = {c: m["count"] for c, m in profile["missing"].items()}
    duplicates = profile["duplicates"]
    target = profile["target"]
    rate = target["positive_rate"]
    missing_cells = sum(missing.values())

    issues: list[str] = []
    for col, n in missing.items():
        if n / max(n_rows, 1) > 0.3:
            issues.append(f"'{col}' has {n / n_rows:.0%} missing values")
    if duplicates:
        issues.append(f"{duplicates} duplicated rows")
    if min(rate, 1 - rate) < 0.1:
        issues.append(f"imbalanced target (positive rate {rate:.1%})")
    if missing.get(target["column"]):
        issues.append(f"{missing[target['column']]} rows have a missing target and are ignored in modeling")

    return {
        "missing_cells": missing_cells,
        "missing_pct": missing_cells / max(n_rows * profile["columns"], 1),
        "duplicate_rows": duplicates,
        "issues": issues,
    }
