import pandas as pd
import pytest

from datalab.schemas.problem import ProblemConfig
from datalab.tools.baseline import select_features, train_baseline
from datalab.tools.eda import derive_hypotheses, summarize_features
from datalab.tools.evaluation import evaluate_model
from datalab.tools.profiling import assess_quality, profile_dataset, read_columns
from datalab.tools.review import review_experiments


def _eda(df: pd.DataFrame) -> dict:
    return summarize_features(df, "y", features=[c for c in df.columns if c not in ("y", "id")])


# ------------------------------------------------------------ profiling / quality


def test_profiling(synthetic):
    df, _ = synthetic
    df = pd.concat([df, df.iloc[1:4]], ignore_index=True)  # 3 duplicates (rows without NaN)
    profile = profile_dataset(df, "y")
    assert profile["rows"] == 403 and profile["columns"] == 5
    assert profile["duplicates"] == 3
    assert profile["missing"]["x2"]["count"] == 20
    assert set(profile["target"]["counts"]) == {"0", "1"}
    assert profile["target"]["positive_label"] == 1
    assert 0 < profile["target"]["positive_rate"] < 1
    assert "quality" not in profile and "issues" not in profile  # quality is a separate responsibility


def test_quality_is_derived_from_the_profile_alone(synthetic):
    df, _ = synthetic
    df = pd.concat([df, df.iloc[1:4]], ignore_index=True)
    df.loc[df.index[5:205], "cat"] = None  # ~50% missing (rows 1-3 stay identical to their duplicates)
    quality = assess_quality(profile_dataset(df, "y"))
    assert quality["duplicate_rows"] == 3
    assert quality["missing_cells"] == 200 + 20
    assert any("'cat' has" in i for i in quality["issues"]) and any("duplicated" in i for i in quality["issues"])


def test_quality_flags_imbalance_and_missing_target(synthetic):
    df, _ = synthetic
    df.loc[df.index[:390], "y"] = 0
    df.loc[df.index[390:395], "y"] = None
    issues = assess_quality(profile_dataset(df, "y"))["issues"]
    assert any("imbalanced" in i for i in issues) and any("missing target" in i for i in issues)


def test_profiling_rejects_non_binary_target(synthetic):
    df, _ = synthetic
    df["y"] = df["id"] % 3
    with pytest.raises(ValueError, match="binary"):
        profile_dataset(df, "y")


def test_read_columns_only_reads_the_header(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    assert read_columns(csv) == ["a", "b", "c"]
    with pytest.raises(FileNotFoundError):
        read_columns(tmp_path / "missing.csv")


# ------------------------------------------------------------ eda / hypotheses


def test_eda(synthetic):
    df, _ = synthetic
    eda = summarize_features(df, "y", features=["x1", "x2", "cat"])
    assert set(eda["numeric_summary"]) == {"x1", "x2"}
    assert eda["categorical_summary"]["cat"]["n_unique"] == 2
    assert eda["correlations"]["with_target"][0]["feature"] == "x1"
    assert 0.3 < eda["target_rate"] < 0.7
    assert "hypotheses" not in eda  # derived by a different agent


def test_hypotheses_are_associations_derived_from_the_eda(synthetic):
    df, _ = synthetic
    hypotheses = derive_hypotheses(_eda(df))
    assert hypotheses and "x1" in hypotheses[0] and "linearly associated" in hypotheses[0]
    assert not any("cause" in h.lower() for h in hypotheses)
    weak = {"correlations": {"with_target": [{"feature": "z", "pearson_r": 0.01}]}}
    assert derive_hypotheses(weak) == ["No numeric feature has |r| >= 0.1 with the target; expect a weak linear baseline."]


# ------------------------------------------------------------ modeling


def test_select_features(synthetic):
    df, problem = synthetic
    features, dropped = select_features(list(df.columns), problem)
    assert features == ["x1", "x2", "cat"] and dropped["id_columns"] == ["id"] and dropped["target"] == "y"


def test_baseline_on_synthetic_data(synthetic):
    df, problem = synthetic
    exp = train_baseline(df, problem)["experiments"][0]
    assert exp["id"] == "baseline_logreg" and exp["seed"] == 1
    assert "id" not in exp["features"] and "y" not in exp["features"]
    assert exp["split"]["n_train"] + exp["split"]["n_test"] == len(df)
    assert set(exp["metrics"]) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert exp["metrics"]["roc_auc"] > 0.8  # the signal is strong by construction
    assert train_baseline(df, problem) == train_baseline(df, problem)  # deterministic given the seed


def test_baseline_honours_the_leads_feature_plan(synthetic):
    df, problem = synthetic
    exp = train_baseline(df, problem, features=["x1"])["experiments"][0]
    assert exp["features"] == ["x1"]


def test_model_evaluator_is_descriptive(synthetic):
    df, problem = synthetic
    experiments = train_baseline(df, problem)["experiments"]
    evaluation = evaluate_model(experiments, profile_dataset(df, "y"))
    rate = evaluation["majority_class_accuracy"]
    assert evaluation["selected_model"] == "baseline_logreg" and evaluation["complete"] is True
    assert 0.5 <= rate < 1 and evaluation["accuracy_lift_vs_majority"] == pytest.approx(experiments[0]["metrics"]["accuracy"] - rate)
    assert "verdict" not in evaluation and "leakage" not in str(evaluation).lower()
    experiments[0]["metrics"]["f1"] = None
    incomplete = evaluate_model(experiments, profile_dataset(df, "y"))
    assert incomplete["complete"] is False and incomplete["missing_metrics"] == ["f1"]
    with pytest.raises(ValueError):
        evaluate_model([], profile_dataset(df, "y"))


# ------------------------------------------------------------ review


def test_review_approves_valid_experiment(synthetic):
    df, problem = synthetic
    result = review_experiments(problem, train_baseline(df, problem), _eda(df))
    assert result.verdict == "APPROVED", [c for c in result.checks if not c.passed]


def test_review_rejects_undeclared_leak(synthetic):
    df, problem = synthetic
    df["leak"] = df["y"]
    result = review_experiments(problem, train_baseline(df, problem), _eda(df))
    failed = {c.name: c.detail for c in result.checks if not c.passed}
    assert result.verdict == "REJECTED" and "leak" in failed["no_target_leakage"]


def test_review_rejects_declared_leakage_column_used_as_feature(synthetic):
    df, problem = synthetic
    experiments = train_baseline(df, problem)
    strict = ProblemConfig(**{**problem.model_dump(), "leakage_columns": ["x2"]})  # x2 was used by the model
    result = review_experiments(strict, experiments, _eda(df))
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
    result = review_experiments(problem, experiments, _eda(df))
    assert result.verdict == "REJECTED"
    assert failed_check in [c.name for c in result.checks if not c.passed]


def test_review_rejects_when_no_baseline(synthetic):
    _, problem = synthetic
    result = review_experiments(problem, {"experiments": []}, {})
    assert result.verdict == "REJECTED" and result.checks[0].name == "baseline_exists"
