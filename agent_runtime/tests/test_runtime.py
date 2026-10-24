"""Tests for MasterGraphOrchestrator, Checkpoints, and Quality Gates."""

from pathlib import Path

from agent_runtime.master.graph import MasterGraphOrchestrator
from agent_runtime.shared.checkpoints import CheckpointManager
from agent_runtime.shared.task_store import TaskState, TaskStore
from agent_runtime.shared.telemetry import TelemetryLogger
from agent_runtime.tools.test_tools import TestTools


def test_master_graph_orchestrator_execution(tmp_path: Path):
    task_store = TaskStore(storage_path=tmp_path / "tasks.json")
    telemetry = TelemetryLogger(log_dir=tmp_path / "telemetry")
    checkpoints = CheckpointManager(checkpoint_dir=tmp_path / "checkpoints")

    orchestrator = MasterGraphOrchestrator(
        task_store=task_store,
        telemetry=telemetry,
        checkpoints=checkpoints,
    )

    result = orchestrator.run_epic(
        prompt="Implement GitHub commit velocity analytics API and React metrics card",
        epic_id="EPIC-TEST-E2E",
    )

    assert result.epic_id == "EPIC-TEST-E2E"
    assert result.state in (TaskState.DONE, TaskState.IN_REVIEW)
    assert len(result.subtasks) >= 3

    # Verify task was saved in TaskStore
    stored_task = task_store.get_task("EPIC-TEST-E2E")
    assert stored_task is not None
    assert stored_task.id == "EPIC-TEST-E2E"

    # Verify checkpoints were created
    cps = checkpoints.list_checkpoints("EPIC-TEST-E2E")
    assert len(cps) >= 1

    # Verify telemetry recorded events
    events = telemetry.get_events(task_id="EPIC-TEST-E2E")
    assert len(events) >= 1
    event_types = [e["event_type"] for e in events]
    assert "EPIC_INITIATED" in event_types


def test_quality_gates_evaluation():
    test_tools = TestTools()
    eval_result = test_tools.evaluate_quality_gates(test_path="agent_runtime/tests")

    assert "gate_1_syntax_compilation" in eval_result
    assert "gate_2_automated_tests" in eval_result
    assert "gate_3_security_audit" in eval_result
    assert eval_result["gate_3_security_audit"]["passed"] is True
