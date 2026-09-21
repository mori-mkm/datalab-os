"""Model evaluation summary (Model Evaluator).

Descriptive only: which experiment is selected, whether the expected metrics exist and how the model compares
with a majority-class predictor. It does NOT judge methodology (leakage, split, seed): that verdict belongs
to the independent Review Lead (`tools/review.py`).
"""

from __future__ import annotations

from typing import Any

from datalab.tools.baseline import METRICS

PRIMARY_METRIC = "roc_auc"


def evaluate_model(experiments: list[dict[str, Any]], dataset_profile: dict[str, Any]) -> dict[str, Any]:
    if not experiments:
        raise ValueError("no experiment to evaluate")
    selected = max(experiments, key=lambda e: e["metrics"].get(PRIMARY_METRIC) or float("-inf"))
    metrics = selected["metrics"]
    missing = [m for m in METRICS if metrics.get(m) is None]
    rate = dataset_profile["target"]["positive_rate"]
    majority = max(rate, 1 - rate)  # accuracy of always predicting the most frequent class
    accuracy = metrics.get("accuracy")
    return {
        "selected_model": selected["id"],
        "primary_metric": PRIMARY_METRIC,
        "metrics": metrics,
        "complete": not missing,
        "missing_metrics": missing,
        "majority_class_accuracy": majority,
        "accuracy_lift_vs_majority": None if accuracy is None else accuracy - majority,
        "n_experiments": len(experiments),
    }
