"""Basic exploratory analysis (Analytics capability)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from datalab.tools.profiling import binary_target

TOP_K = 5


def run_eda(df: pd.DataFrame, target: str, positive_label: Any = None, exclude: list[str] = []) -> dict[str, Any]:
    y, positive = binary_target(df, target, positive_label)
    features = df.drop(columns=[target, *[c for c in exclude if c in df.columns]])
    numeric = features.select_dtypes(include="number")
    categorical = features.select_dtypes(exclude="number")

    numeric_summary = {
        col: {
            "mean": s.mean(),
            "std": s.std(),
            "min": s.min(),
            "median": s.median(),
            "max": s.max(),
            "missing_pct": float(s.isna().mean()),
        }
        for col, s in numeric.items()
    }

    categorical_summary: dict[str, Any] = {}
    for col, s in categorical.items():
        top = s.value_counts().head(TOP_K)
        categorical_summary[col] = {
            "n_unique": int(s.nunique()),
            "missing_pct": float(s.isna().mean()),
            "top": [
                {"value": str(v), "count": int(n), "positive_rate": float(y[s == v].mean())} for v, n in top.items()
            ],
        }

    with_target = [
        {"feature": col, "pearson_r": float(r)}
        for col, r in numeric.corrwith(y).dropna().items()
    ]
    with_target.sort(key=lambda d: abs(d["pearson_r"]), reverse=True)

    pairs: list[dict[str, Any]] = []
    corr = numeric.corr()
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            if pd.notna(corr.loc[a, b]):
                pairs.append({"a": a, "b": b, "pearson_r": float(corr.loc[a, b])})
    pairs.sort(key=lambda d: abs(d["pearson_r"]), reverse=True)

    hypotheses = [
        f"'{d['feature']}' is linearly associated with the target (r={d['pearson_r']:+.2f}); candidate predictor."
        for d in with_target[:3]
        if abs(d["pearson_r"]) >= 0.1
    ] or ["No numeric feature has |r| >= 0.1 with the target; expect a weak linear baseline."]

    return {
        "target_rate": float(y.mean()),
        "positive_label": positive,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "correlations": {"with_target": with_target, "top_feature_pairs": pairs[:TOP_K]},
        "hypotheses": hypotheses,
    }
