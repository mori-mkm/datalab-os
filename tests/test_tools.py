import pandas as pd
import pytest

from datalab.schemas.problem import ProblemConfig
from datalab.tools.baseline import train_baseline
from datalab.tools.eda import run_eda
from datalab.tools.profiling import profile_dataset
from datalab.tools.review import review_experiments


def test_profiling(synthetic):
    df, problem = synthetic
    df = pd.concat([df, df.iloc[1:4]], ignore_index=True)  # 3 duplicates (rows without NaN)
    result = profile_dataset(df, "y")
    profile = result["profile"]
    assert profile["rows"] == 403 and profile["columns"] == 5
    assert profile["duplicates"] == 3
    assert profile["missing"]["x2"]["count"] == 20
    assert set(profile["target"]["counts"]) == {"0", "1"}
    assert profile["target"]["positive_label"] == 1
    assert 0 < profile["target"]["positive_rate"] < 1
    assert any("duplicated" in i for i in result["quality"]["issues"])


def test_profiling_rejects_non_binary_target(synthetic):
    df, _ = synthetic
    df["y"] = df["id"] % 3
    with pytest.raises(ValueError, match="binary"):
        profile_dataset(df, "y")


def test_eda(synthetic):
    df, _ = synthetic
    eda = run_eda(df, "y", exclude=["id"])
    assert set(eda["numeric_summary"]) == {"x1", "x2"}
    assert eda["categorical_summary"]["cat"]["n_unique"] == 2
    assert eda["correlations"]["with_target"][0]["feature"] == "x1"
    assert 0.3 < eda["target_rate"] < 0.7


def test_baseline_on_synthetic_data(synthetic):
    df, problem = synthetic
    exp = train_baseline(df, problem)["experiments"][0]
    assert exp["id"] == "baseline_logreg" and exp["seed"] == 1
    assert "id" not in exp["features"] and "y" not in exp["features"]
    assert exp["split"]["n_train"] + exp["split"]["n_test"] == len(df)
    assert set(exp["metrics"]) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert exp["metrics"]["roc_auc"] > 0.8  # the signal is strong by construction
    assert train_baseline(df, problem) == train_baseline(df, problem)  # deterministic given the seed


def test_review_approves_valid_experiment(synthetic):
    df, problem = synthetic
    result = review_experiments(problem, train_baseline(df, problem), run_eda(df, "y", exclude=["id"]))
    assert result.verdict == "APPROVED", [c for c in result.checks if not c.passed]


def test_review_rejects_undeclared_leak(synthetic):
    df, problem = synthetic
    df["leak"] = df["y"]
    result = review_experiments(problem, train_baseline(df, problem), run_eda(df, "y", exclude=["id"]))
    failed = {c.name: c.detail for c in result.checks if not c.passed}
    assert result.verdict == "REJECTED" and "leak" in failed["no_target_leakage"]


def test_review_rejects_declared_leakage_column_used_as_feature(synthetic):
    df, problem = synthetic
    experiments = train_baseline(df, problem)
    strict = ProblemConfig(**{**problem.model_dump(), "leakage_columns": ["x2"]})  # x2 was used by the model
    result = review_experiments(strict, experiments, run_eda(df, "y", exclude=["id"]))
    assert result.verdict == "REJECTED"
    assert "declared leakage" in next(c.detail for c in result.checks if c.name == "no_target_leakage")


@pytest.mark.parametrize(
    ("mutate", "failed_check"),
    [
        (lambda e: e.pop("split"), "train_test_split_exists"),
        (lambda e: e.update(seed=None), "seed_recorded"),
        (lambda e: e["metrics"].pop("f1"), "metrics_exist"),
    ],
)
def test_review_rejects_missing_methodology(synthetic, mutate, failed_check):
    df, problem = synthetic
    experiments = train_baseline(df, problem)
    mutate(experiments["experiments"][0])
    result = review_experiments(problem, experiments, run_eda(df, "y", exclude=["id"]))
    assert result.verdict == "REJECTED"
    assert failed_check in [c.name for c in result.checks if not c.passed]


def test_review_rejects_when_no_baseline(synthetic):
    _, problem = synthetic
    result = review_experiments(problem, {"experiments": []}, {})
    assert result.verdict == "REJECTED" and result.checks[0].name == "baseline_exists"
