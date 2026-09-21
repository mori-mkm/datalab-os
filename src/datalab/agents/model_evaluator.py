"""Model Evaluator: descriptive evaluation of the experiments (model_evaluation.json).

It checks the metrics exist and compares against a majority-class predictor. It does not approve or reject
anything: methodological approval (leakage, split, seed) is the independent Review Lead's job.
"""

from __future__ import annotations

from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.evaluation import evaluate_model


def run(ctx: RunContext, state: DataLabState) -> dict:
    if not state["experiments"]:
        raise RuntimeError("model_evaluator needs the experiments from the baseline_modeler")
    ctx.status("Evaluating experiments")
    evaluation = evaluate_model(state["experiments"], state["dataset_profile"])
    m = evaluation["metrics"]
    ctx.status(f"Selected {evaluation['selected_model']}: roc_auc={m['roc_auc']:.3f}, f1={m['f1']:.3f}")
    name = ctx.save_json("model_evaluation.json", evaluation)
    return {
        "model_evaluation": evaluation,
        "selected_model": evaluation["selected_model"],
        "artifacts": {name: name},
    }
