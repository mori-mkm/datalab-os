import json
import re

import pandas as pd
import pytest
from langgraph.graph.state import CompiledStateGraph

from datalab.graphs.organization import UNITS, get_graph, graph_metadata, topology
from datalab.graphs.spec import AgentSpec, DepartmentSpec
from datalab.graphs.topology import build_topology
from datalab.schemas.event import EventType
from datalab.schemas.problem import load_problem

DEPARTMENTS = {
    "data_engineering": ["engineering_lead", "data_profiler", "data_quality_analyst"],
    "analytics": ["analytics_lead", "eda_analyst", "hypothesis_analyst"],
    "modeling": ["ds_lead", "baseline_modeler", "model_evaluator"],
}
EXECUTION_ORDER = [
    "head_ds",
    *[f"{d}.{a}" for d, agents in DEPARTMENTS.items() for a in agents],
    "review",
    "report",
]


def _fingerprint(service, run_id):
    return [(e.event_type, e.node_id, e.target, e.status) for e in service.bus.history(run_id)]


# ---------------------------------------------------------------- structure


def test_each_department_is_a_real_compiled_subgraph():
    subgraphs = dict(get_graph().get_subgraphs())
    assert set(subgraphs) == set(DEPARTMENTS)
    for name, sub in subgraphs.items():
        assert isinstance(sub, CompiledStateGraph)
        drawn = sub.get_graph()
        assert [n for n in drawn.nodes if not n.startswith("__")] == DEPARTMENTS[name]
        internal = [(e.source, e.target) for e in drawn.edges if not e.source.startswith("__") and not e.target.startswith("__")]
        assert sorted(internal) == sorted(zip(DEPARTMENTS[name], DEPARTMENTS[name][1:]))
    # and they are nodes of the organization graph, not inlined into it
    assert {"data_engineering", "analytics", "modeling"} <= set(get_graph().nodes)


def test_metadata_hierarchy():
    meta = graph_metadata()
    ids = [n["id"] for n in meta["nodes"]]
    assert len(ids) == len(set(ids))
    by_id = {n["id"]: n for n in meta["nodes"]}
    assert [i for i in ids if by_id[i]["parent_id"] is None] == ["head_ds", *DEPARTMENTS, "review", "report"]
    for dept, agents in DEPARTMENTS.items():
        assert by_id[dept]["type"] == "department" and by_id[dept]["agent"] is None
        children = [n["id"] for n in meta["nodes"] if n["parent_id"] == dept]
        assert children == [f"{dept}.{a}" for a in agents]
        assert all(by_id[c]["type"] == "agent" and by_id[c]["agent"] == c.split(".")[1] for c in children)
    assert by_id["head_ds"]["type"] == "orchestrator"
    assert by_id["review"]["type"] == "review" and by_id["report"]["type"] == "report"


def test_metadata_edges_are_executable_and_classified():
    meta = graph_metadata()
    ids = {n["id"] for n in meta["nodes"]}
    edges = {(e["source"], e["target"]): e["kind"] for e in meta["edges"]}
    assert all(s in ids and t in ids for (s, t) in edges)
    internal = [(s, t) for (s, t), k in edges.items() if k == "internal"]
    assert len(internal) == 6 and all(s.split(".")[0] == t.split(".")[0] for s, t in internal)
    handoffs = [(s, t) for (s, t), k in edges.items() if k == "handoff"]
    assert handoffs == [
        ("head_ds", "data_engineering.engineering_lead"),
        ("data_engineering.data_quality_analyst", "analytics.analytics_lead"),
        ("analytics.hypothesis_analyst", "modeling.ds_lead"),
        ("modeling.model_evaluator", "review"),
        ("review", "report"),
    ]
    assert not any(s in DEPARTMENTS or t in DEPARTMENTS for s, t in edges)  # containers never take part in edges
    assert all(e["id"] == f"{e['source']}->{e['target']}" for e in meta["edges"])


def test_topology_is_read_from_the_compiled_graph_and_rejects_drift():
    assert [n.id for n in topology().nodes if n.parent_id] == [f"{d}.{a}" for d, ag in DEPARTMENTS.items() for a in ag]
    drifted = tuple(u for u in UNITS if not (isinstance(u, DepartmentSpec) and u.id == "analytics"))
    with pytest.raises(RuntimeError, match="disagree"):
        build_topology(get_graph(), drifted)  # a spec that is not in the compiled graph must not be served


def test_node_ids_are_validated_and_unique():
    noop = lambda ctx, state: {}  # noqa: E731
    for bad in ["Has.Dot", "has:colon", "1starts_with_digit", "spaced id", ""]:
        with pytest.raises(ValueError, match="invalid node id"):
            AgentSpec(bad, "x", "x", noop)
    with pytest.raises(ValueError, match="duplicate"):
        DepartmentSpec("d", "D", "r", (AgentSpec("a", "A", "r", noop), AgentSpec("a", "A2", "r", noop)))
    with pytest.raises(ValueError, match="no agents"):
        DepartmentSpec("d", "D", "r", ())
    ids = [n["id"] for n in graph_metadata()["nodes"]]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?", i) for i in ids)


def test_child_agents_refuse_to_run_without_their_prerequisites(service, settings):
    from datalab.agents import analytics_lead, data_quality_analyst, ds_lead, hypothesis_analyst, model_evaluator
    from datalab.services.context import RunContext
    from datalab.state import new_state

    problem = load_problem(settings.configs_dir / "problem.example.yaml")
    state = new_state("r", problem, str(problem.resolved_dataset(settings.root)), "real")
    ctx = RunContext("r", settings.workspace_dir, "real", service.bus, settings)
    for agent in (data_quality_analyst, analytics_lead, hypothesis_analyst, ds_lead, model_evaluator):
        with pytest.raises(RuntimeError, match="needs"):
            agent.run(ctx, state)  # each one names what it is missing instead of computing on nothing


# ---------------------------------------------------------------- execution


def test_demo_workflow_executes_every_child_agent_in_order(service):
    info = service.run_sync("demo")
    events = service.bus.history(info.run_id)
    started = [e.node_id for e in events if e.event_type == EventType.agent_started and e.node_id not in DEPARTMENTS]
    completed = [e.node_id for e in events if e.event_type == EventType.agent_completed and e.node_id not in DEPARTMENTS]
    assert started == completed == EXECUTION_ORDER
    assert info.status == "completed" and info.current_phase == "report"
    assert events[0].event_type == EventType.run_started and events[-1].event_type == EventType.run_completed
    # demo artifacts are per child and clearly labelled
    owners = {e.data["artifact"]: e.node_id for e in events if e.event_type == EventType.artifact_created}
    assert owners["data_profiler.demo.json"] == "data_engineering.data_profiler"
    assert owners["report.md"] == "report"
    assert "DEMO WORKFLOW" in (service.settings.workspace_dir / info.run_id / "report.md").read_text(encoding="utf-8")


def test_department_lifecycle_wraps_its_children(service):
    info = service.run_sync("demo")
    events = service.bus.history(info.run_id)
    index = lambda t, n: next(i for i, e in enumerate(events) if e.event_type == t and e.node_id == n)  # noqa: E731
    for dept, agents in DEPARTMENTS.items():
        first, last = f"{dept}.{agents[0]}", f"{dept}.{agents[-1]}"
        assert index(EventType.agent_started, dept) < index(EventType.agent_started, first)
        assert index(EventType.agent_completed, last) < index(EventType.agent_completed, dept)
        container = [e for e in events if e.node_id == dept]
        assert [(e.event_type, e.status) for e in container] == [
            (EventType.agent_started, "running"),
            (EventType.agent_completed, "completed"),
        ]
        assert all(e.department == dept for e in events if e.node_id and e.node_id.startswith(dept))
        assert all(e.agent is None for e in container)


def test_every_edge_gets_a_started_then_completed_handoff(service):
    info = service.run_sync("demo")
    events = service.bus.history(info.run_id)
    for edge in graph_metadata()["edges"]:
        kinds = [e.event_type for e in events if e.node_id == edge["source"] and e.target == edge["target"]]
        assert kinds == [EventType.handoff_started, EventType.handoff_completed], edge["id"]
    assert {e.node_id for e in events if e.node_id} <= {n["id"] for n in graph_metadata()["nodes"]}


def test_event_sequence_is_deterministic(service):
    assert _fingerprint(service, service.run_sync("demo").run_id) == _fingerprint(service, service.run_sync("demo").run_id)


def test_concurrent_runs_do_not_mix_their_events(service):
    import time

    first, second = service.start("demo"), service.start("demo")
    deadline = time.time() + 30
    while time.time() < deadline and any(service.get(r.run_id).status == "running" or service.get(r.run_id).status == "waiting" for r in (first, second)):
        time.sleep(0.02)
    a, b = (_fingerprint(service, r.run_id) for r in (first, second))
    assert a == b and a[-1][0] == EventType.run_completed
    assert {e.run_id for e in service.bus.history(first.run_id)} == {first.run_id}


def test_real_workflow_traverses_children_and_attributes_artifacts(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.example.yaml"))
    assert info.status == "completed" and info.review_verdict == "APPROVED"
    events = service.bus.history(info.run_id)
    started = [e.node_id for e in events if e.event_type == EventType.agent_started and e.node_id not in DEPARTMENTS]
    assert started == EXECUTION_ORDER
    owners = {e.data["artifact"]: e.node_id for e in events if e.event_type == EventType.artifact_created}
    assert owners == {
        "problem.yaml": "head_ds",
        "data_profile.json": "data_engineering.data_profiler",
        "data_quality.json": "data_engineering.data_quality_analyst",
        "eda.json": "analytics.eda_analyst",
        "hypotheses.json": "analytics.hypothesis_analyst",
        "experiments.json": "modeling.baseline_modeler",
        "model_evaluation.json": "modeling.model_evaluator",
        "review.json": "review",
        "report.md": "report",
    }
    run_dir = settings.workspace_dir / info.run_id
    assert all((run_dir / name).is_file() for name in owners)
    assert sorted(info.artifacts) == sorted(owners)
    experiment = json.loads((run_dir / "experiments.json").read_text())["experiments"][0]
    assert experiment["metrics"]["roc_auc"] > 0.5 and experiment["seed"] == 42
    assert "roc_auc" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_real_workflow_on_a_small_synthetic_dataset_produces_data_driven_artifacts(service, settings, tmp_path):
    """End-to-end proof on a small (~200-row) synthetic dataset: every stage produces a real, data-derived
    artifact (not a placeholder), and the run reaches a terminal status."""
    problem = load_problem(settings.configs_dir / "problem.small.yaml")
    csv_path = problem.resolved_dataset(settings.root)
    df = pd.read_csv(csv_path)
    assert 100 <= len(df) <= 300  # the dataset this test is meant to exercise

    info = service.run_sync("real", problem)
    assert info.status == "completed" and info.review_verdict == "APPROVED"
    events = service.bus.history(info.run_id)
    started = [e.node_id for e in events if e.event_type == EventType.agent_started and e.node_id not in DEPARTMENTS]
    assert started == EXECUTION_ORDER  # all 5 stages ran, in order: engineering, analytics, modeling, review, report

    owners = {e.data["artifact"]: e.node_id for e in events if e.event_type == EventType.artifact_created}
    assert set(owners) == {
        "problem.yaml",
        "data_profile.json",
        "data_quality.json",
        "eda.json",
        "hypotheses.json",
        "experiments.json",
        "model_evaluation.json",
        "review.json",
        "report.md",
    }
    run_dir = settings.workspace_dir / info.run_id
    assert all((run_dir / name).is_file() for name in owners)

    # artifacts reflect the actual CSV content, not a canned/placeholder value
    profile = json.loads((run_dir / "data_profile.json").read_text())
    assert profile["rows"] == len(df) and profile["columns"] == df.shape[1]
    assert profile["target"]["positive_rate"] == pytest.approx((df["churned"] == 1).mean())
    experiment = json.loads((run_dir / "experiments.json").read_text())["experiments"][0]
    original_auc = experiment["metrics"]["roc_auc"]
    assert experiment["split"]["n_train"] + experiment["split"]["n_test"] == len(df)
    assert "roc_auc" in (run_dir / "report.md").read_text(encoding="utf-8")

    # perturb the dataset and re-run: a computed (not hardcoded) metric must change
    flipped = df.copy()
    flipped["churned"] = 1 - flipped["churned"]
    perturbed_csv = tmp_path / "perturbed.csv"
    flipped.to_csv(perturbed_csv, index=False)
    perturbed_problem = problem.model_copy(update={"dataset_path": str(perturbed_csv)})
    perturbed_info = service.run_sync("real", perturbed_problem)
    perturbed_run_dir = settings.workspace_dir / perturbed_info.run_id
    perturbed_experiment = json.loads((perturbed_run_dir / "experiments.json").read_text())["experiments"][0]
    assert perturbed_experiment["metrics"]["roc_auc"] != original_auc


def test_agent_completed_carries_tools_when_the_agent_sets_them_absent_otherwise(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.example.yaml"))
    completed = {
        e.node_id: e.data.get("tools")
        for e in service.bus.history(info.run_id)
        if e.event_type == EventType.agent_completed
    }
    assert completed["data_engineering.data_profiler"] == ["pandas.read_csv", "profile_dataset"]
    assert completed["modeling.model_evaluator"] == ["evaluate_model"]
    assert completed["review"] == ["review_experiments"]
    assert completed["head_ds"] is None  # no _tools set: absent, never an empty-list error


def test_real_workflow_is_functionally_equivalent_to_the_flat_poc(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.example.yaml"))
    run_dir = settings.workspace_dir / info.run_id
    metrics = json.loads((run_dir / "experiments.json").read_text())["experiments"][0]["metrics"]
    assert round(metrics["roc_auc"], 3) == 0.741 and round(metrics["f1"], 3) == 0.421  # same as the PoC baseline
    evaluation = json.loads((run_dir / "model_evaluation.json").read_text())
    assert evaluation["selected_model"] == "baseline_logreg" and evaluation["complete"] is True
    assert "verdict" not in evaluation  # the evaluator never approves or rejects


def test_model_evaluator_does_not_decide_the_review(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.leaky.yaml"))
    events = service.bus.history(info.run_id)
    evaluator_done = next(e for e in events if e.node_id == "modeling.model_evaluator" and e.event_type == EventType.agent_completed)
    assert evaluator_done.status == "completed"  # descriptive evaluation happily completes on a leaky run...
    assert info.status == "rejected" and info.review_verdict == "REJECTED"  # ...the independent review rejects it


def test_leaky_workflow_runs_all_departments_then_rejects_at_review(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.leaky.yaml"))
    events = service.bus.history(info.run_id)
    assert [e.node_id for e in events if e.event_type == EventType.agent_started and e.node_id not in DEPARTMENTS] == EXECUTION_ORDER
    assert all(e.status == "completed" for e in events if e.node_id in DEPARTMENTS and e.event_type == EventType.agent_completed)
    review = [e for e in events if e.node_id == "review" and e.status == "rejected"]
    assert review and "no_target_leakage" in review[0].message
    assert events[-1].event_type == EventType.run_rejected and events[-1].status == "rejected"
    assert "REJECTED" in (settings.workspace_dir / info.run_id / "report.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- failures


def test_failure_in_a_first_child_marks_child_and_department_and_stops(service, settings):
    problem = load_problem(settings.configs_dir / "problem.example.yaml").model_copy(update={"leakage_columns": ["nope"]})
    info = service.run_sync("real", problem)
    events = service.bus.history(info.run_id)
    assert info.status == "error" and "nope" in info.error
    tail = [(e.event_type, e.node_id, e.status) for e in events[-3:]]
    assert tail == [
        (EventType.agent_failed, "data_engineering.engineering_lead", "error"),
        (EventType.agent_failed, "data_engineering", "error"),
        (EventType.run_failed, None, "error"),
    ]
    assert not any(e.node_id and e.node_id.startswith(("analytics", "modeling", "review")) for e in events)


def test_failure_in_a_middle_child_keeps_earlier_children_completed(service, settings, tmp_path):
    csv = tmp_path / "three_class.csv"
    pd.DataFrame({"a": range(30), "y": [0, 1, 2] * 10}).to_csv(csv, index=False)
    problem = load_problem(settings.configs_dir / "problem.example.yaml").model_copy(
        update={"dataset_path": str(csv), "target": "y", "id_columns": []}
    )
    info = service.run_sync("real", problem)
    events = service.bus.history(info.run_id)
    status = {e.node_id: e.status for e in events if e.status and e.node_id}
    assert info.status == "error"
    assert status["data_engineering.engineering_lead"] == "completed"
    assert status["data_engineering.data_profiler"] == "error" and status["data_engineering"] == "error"
    assert "data_engineering.data_quality_analyst" not in status
    assert "must be binary" in next(e for e in events if e.event_type == EventType.agent_failed).message


def test_failure_in_a_top_level_node(service, settings):
    problem = load_problem(settings.configs_dir / "problem.example.yaml").model_copy(update={"dataset_path": "data/raw/missing.csv"})
    info = service.run_sync("real", problem)
    events = service.bus.history(info.run_id)
    assert info.status == "error" and "missing.csv" in info.error
    assert [(e.event_type, e.node_id) for e in events[-2:]] == [(EventType.agent_failed, "head_ds"), (EventType.run_failed, None)]
