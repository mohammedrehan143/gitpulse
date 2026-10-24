"""Tests for TaskRouter task classification and decomposition."""

from agent_runtime.master.router import TaskRouter


def test_classify_task_types():
    assert TaskRouter.classify_task_type("Fix 500 error on commit ingestion") == "BUG"
    assert (
        TaskRouter.classify_task_type("Update docker compose configuration for Kafka KRaft")
        == "INFRASTRUCTURE"
    )
    assert (
        TaskRouter.classify_task_type("Refactor storage layer to use connection pooling")
        == "REFACTOR"
    )
    assert (
        TaskRouter.classify_task_type("Verify E2E contract between backend and dashboard")
        == "INTEGRATION"
    )
    assert (
        TaskRouter.classify_task_type("Add repository developer velocity analytics dashboard")
        == "FEATURE"
    )


def test_decompose_feature_generates_backend_frontend_and_contract():
    prompt = "Build repository velocity analytics endpoint and React dashboard chart"
    subtasks, requires_contract = TaskRouter.decompose_epic("EPIC-TEST-01", prompt)

    assert requires_contract is True
    domains = [t.domain for t in subtasks]
    assert "backend" in domains
    assert "frontend" in domains
    assert "shared" in domains

    # Verify contract subtask is created
    contract_subtask = next(t for t in subtasks if t.assigned_agent == "software-architect")
    assert ".agents/tasks/contracts.md" in contract_subtask.file_scope


def test_decompose_backend_only_prompt():
    prompt = "Add Kafka streaming consumer for GitHub push events"
    subtasks, requires_contract = TaskRouter.decompose_epic("EPIC-TEST-02", prompt)

    be_tasks = [t for t in subtasks if t.domain == "backend"]
    assert len(be_tasks) >= 1
