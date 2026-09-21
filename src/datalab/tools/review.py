"""Methodological review of the modeling output (Review capability)."""

from __future__ import annotations

from typing import Any

from datalab.schemas.problem import ProblemConfig
from datalab.schemas.review import ReviewCheck, ReviewResult
from datalab.tools.baseline import METRICS

LEAKAGE_CORR = 0.95  # |pearson r| between a used numeric feature and the target
SUSPICIOUS_AUC = 0.999


def review_experiments(problem: ProblemConfig, experiments: dict[str, Any], eda: dict[str, Any]) -> ReviewResult:
    runs = experiments.get("experiments", [])
    baseline = next((e for e in runs if e.get("id", "").startswith("baseline")), None)
    checks = [
        ReviewCheck(
            name="baseline_exists",
            passed=baseline is not None,
            detail="baseline experiment found" if baseline else "no baseline experiment",
        )
    ]
    if baseline is None:
        return ReviewResult.from_checks(checks)

    split = baseline.get("split") or {}
    checks.append(
        ReviewCheck(
            name="train_test_split_exists",
            passed=bool(split.get("n_train")) and bool(split.get("n_test")),
            detail=f"n_train={split.get('n_train')}, n_test={split.get('n_test')}",
        )
    )
    checks.append(
        ReviewCheck(
            name="seed_recorded",
            passed=isinstance(baseline.get("seed"), int),
            detail=f"seed={baseline.get('seed')}",
        )
    )
    metrics = baseline.get("metrics") or {}
    missing = [m for m in METRICS if metrics.get(m) is None]
    checks.append(
        ReviewCheck(
            name="metrics_exist",
            passed=not missing,
            detail="all metrics present" if not missing else f"missing metrics: {missing}",
        )
    )

    features = set(baseline.get("features", []))
    forbidden = features & {problem.target, *problem.leakage_columns}
    correlated = [
        f"{d['feature']} (r={d['pearson_r']:+.3f})"
        for d in eda.get("correlations", {}).get("with_target", [])
        if d["feature"] in features and abs(d["pearson_r"]) >= LEAKAGE_CORR
    ]
    perfect = (metrics.get("roc_auc") or 0) >= SUSPICIOUS_AUC
    problems = []
    if forbidden:
        problems.append(f"declared leakage/target used as feature: {sorted(forbidden)}")
    if correlated:
        problems.append(f"feature(s) almost identical to the target: {correlated}")
    if perfect:
        problems.append(f"suspiciously perfect roc_auc={metrics['roc_auc']:.4f}")
    checks.append(
        ReviewCheck(
            name="no_target_leakage",
            passed=not problems,
            detail="; ".join(problems) or "no declared leakage, no near-copy of the target, no perfect score",
        )
    )
    return ReviewResult.from_checks(checks)
