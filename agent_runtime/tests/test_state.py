"""Tests for TaskStore, TaskState transitions, and HandoffContracts."""

import pytest
from pathlib import Path
from agent_runtime.shared.task_store import (
    HandoffContract,
    TaskRecord,
    TaskState,
    TaskStore,
)


def test_task_creation_and_retrieval(tmp_path: Path):
    store = TaskStore(storage_path=tmp_path / "test_tasks.json")
    task = store.create_task(
        task_id="TASK-001",
        title="Test Task",
        description="Verify task store",
        assigned_agent="backend-orchestrator",
        initial_state=TaskState.BACKLOG,
    )

    assert task.id == "TASK-001"
    assert task.state == TaskState.BACKLOG

    retrieved = store.get_task("TASK-001")
    assert retrieved is not None
    assert retrieved.id == "TASK-001"
    assert retrieved.assigned_agent == "backend-orchestrator"


def test_legal_state_transitions(tmp_path: Path):
    store = TaskStore(storage_path=tmp_path / "test_tasks.json")
    store.create_task(
        task_id="TASK-002",
        title="Transition Task",
        description="Verify lifecycle",
        assigned_agent="api-engineer",
        initial_state=TaskState.BACKLOG,
    )

    # BACKLOG -> READY -> IN_PROGRESS -> IN_REVIEW -> DONE
    t1 = store.update_task_state("TASK-002", TaskState.READY)
    assert t1.state == TaskState.READY

    t2 = store.update_task_state("TASK-002", TaskState.IN_PROGRESS)
    assert t2.state == TaskState.IN_PROGRESS

    t3 = store.update_task_state("TASK-002", TaskState.IN_REVIEW)
    assert t3.state == TaskState.IN_REVIEW

    t4 = store.update_task_state("TASK-002", TaskState.DONE)
    assert t4.state == TaskState.DONE


def test_illegal_state_transition_raises_error(tmp_path: Path):
    store = TaskStore(storage_path=tmp_path / "test_tasks.json")
    store.create_task(
        task_id="TASK-003",
        title="Illegal Transition Task",
        description="Verify rejection",
        assigned_agent="kafka-engineer",
        initial_state=TaskState.BACKLOG,
    )

    # BACKLOG directly to DONE is illegal
    with pytest.raises(ValueError, match="Illegal state transition"):
        store.update_task_state("TASK-003", TaskState.DONE)


def test_record_handoff_contract(tmp_path: Path):
    store = TaskStore(storage_path=tmp_path / "test_tasks.json")
    store.create_task(
        task_id="TASK-004",
        title="Handoff Task",
        description="Verify 9-point contract",
        assigned_agent="ingestion-engineer",
        initial_state=TaskState.READY,
    )

    handoff = HandoffContract(
        task_id="TASK-004",
        objective="Extract GitHub commits",
        scope_and_ownership=["backend/src/gitpulse/ingestion/github_client.py"],
        context_and_docs=["docs/api-contracts.md"],
        dependencies=[],
        acceptance_criteria=["Pagination handled", "Rate limit preserved"],
        files_changed=["backend/src/gitpulse/ingestion/github_client.py"],
        tests_and_results={"tests_passed": 5},
        blockers_and_risks=[],
        next_step="Send to kafka-engineer",
    )

    updated = store.record_handoff("TASK-004", handoff)
    assert len(updated.handoffs) == 1
    assert updated.handoffs[0].task_id == "TASK-004"
    assert updated.handoffs[0].tests_and_results["tests_passed"] == 5
