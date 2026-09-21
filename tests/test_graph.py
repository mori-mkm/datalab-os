import json

from datalab.graphs.organization import EDGES, NODES, graph_metadata
from datalab.schemas.event import EventType
from datalab.schemas.problem import load_problem

NODE_IDS = ["head_ds", "data_engineering", "analytics", "modeling", "review", "report"]


def test_metadata_is_derived_from_the_compiled_graph():
    meta = graph_metadata()
    assert [n["id"] for n in meta["nodes"]] == NODE_IDS == [n.id for n in NODES]
    assert [(e["source"], e["target"]) for e in meta["edges"]] == EDGES
    assert len(EDGES) == len(NODE_IDS) - 1


def test_demo_workflow_runs_every_node_in_order(service):
    info = service.run_sync("demo")
    events = service.bus.history(info.run_id)
    started = [e.department for e in events if e.event_type == EventType.agent_started]
    completed = [e.department for e in events if e.event_type == EventType.agent_completed]
    assert started == completed == NODE_IDS
    assert events[0].event_type == EventType.run_started and events[-1].event_type == EventType.run_completed
    # every edge gets a handoff_started followed by a handoff_completed
    for source, target in EDGES:
        kinds = [e.event_type for e in events if e.department == source and e.target == target]
        assert kinds == [EventType.handoff_started, EventType.handoff_completed]
    assert all(name.endswith(".demo.json") or name == "report.md" for name in info.artifacts)
    assert "DEMO WORKFLOW" in (service.settings.workspace_dir / info.run_id / "report.md").read_text(encoding="utf-8")


def test_real_workflow_persists_all_artifacts(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.example.yaml"))
    assert info.status == "completed" and info.review_verdict == "APPROVED"
    run_dir = settings.workspace_dir / info.run_id
    for name in ["problem.yaml", "data_profile.json", "eda.json", "experiments.json", "review.json", "report.md"]:
        assert (run_dir / name).is_file(), name
    created = [e.data["artifact"] for e in service.bus.history(info.run_id) if e.event_type == EventType.artifact_created]
    assert sorted(created) == sorted(info.artifacts)
    assert json.loads((run_dir / "experiments.json").read_text())["experiments"][0]["metrics"]["roc_auc"] > 0.5
    assert "source: deterministic" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_real_workflow_with_hidden_leak_is_rejected(service, settings):
    info = service.run_sync("real", load_problem(settings.configs_dir / "problem.leaky.yaml"))
    events = service.bus.history(info.run_id)
    assert info.status == "rejected" and info.review_verdict == "REJECTED"
    assert events[-1].event_type == EventType.run_rejected
    review_node = [e for e in events if e.department == "review" and e.status == "rejected"]
    assert review_node  # the review node itself is marked rejected
    assert "REJECTED" in (settings.workspace_dir / info.run_id / "report.md").read_text(encoding="utf-8")


def test_failing_node_emits_agent_failed_and_run_failed(service, settings):
    problem = load_problem(settings.configs_dir / "problem.example.yaml").model_copy(update={"dataset_path": "data/raw/missing.csv"})
    info = service.run_sync("real", problem)
    events = service.bus.history(info.run_id)
    assert info.status == "error" and "missing.csv" in info.error
    assert [e.event_type for e in events][-2:] == [EventType.agent_failed, EventType.run_failed]
    assert events[-2].department == "head_ds" and events[-2].status == "error"
