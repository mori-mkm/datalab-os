"""Baseline model: Logistic Regression with a stratified hold-out split (Data Science capability)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datalab.schemas.problem import ProblemConfig
from datalab.tools.profiling import binary_target

BASELINE_ID = "baseline_logreg"


def train_baseline(df: pd.DataFrame, problem: ProblemConfig) -> dict[str, Any]:
    y_all, positive = binary_target(df, problem.target, problem.positive_label)
    df = df[y_all.notna()]
    y = y_all[y_all.notna()].astype(int)

    dropped = {
        "target": problem.target,
        "id_columns": problem.id_columns,
        "declared_leakage": problem.leakage_columns,
    }
    drop = {problem.target, *problem.id_columns, *problem.leakage_columns}
    X = df[[c for c in df.columns if c not in drop]]
    numeric = list(X.select_dtypes(include="number").columns)
    categorical = [c for c in X.columns if c not in numeric]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=problem.test_size, random_state=problem.seed, stratify=y
    )
    pipeline = Pipeline(
        [
            (
                "prep",
                ColumnTransformer(
                    [
                        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
                        (
                            "cat",
                            Pipeline(
                                [
                                    ("impute", SimpleImputer(strategy="most_frequent")),
                                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                                ]
                            ),
                            categorical,
                        ),
                    ]
                ),
            ),
            ("model", LogisticRegression(max_iter=1000, random_state=problem.seed)),
        ]
    )
    pipeline.fit(X_train, y_train)
    pred = pipeline.predict(X_test)
    proba = pipeline.predict_proba(X_test)[:, 1]

    experiment = {
        "id": BASELINE_ID,
        "model": "LogisticRegression",
        "params": {"max_iter": 1000, "random_state": problem.seed},
        "features": list(X.columns),
        "dropped": dropped,
        "split": {
            "method": "train_test_split",
            "stratified": True,
            "test_size": problem.test_size,
            "n_train": len(X_train),
            "n_test": len(X_test),
        },
        "seed": problem.seed,
        "positive_label": positive,
        "metrics": {
            "accuracy": accuracy_score(y_test, pred),
            "precision": precision_score(y_test, pred, zero_division=0),
            "recall": recall_score(y_test, pred, zero_division=0),
            "f1": f1_score(y_test, pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, proba),
        },
    }
    return {"experiments": [experiment], "selected_model": BASELINE_ID}
