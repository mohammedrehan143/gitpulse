"""GitPulse Task Store and Lifecycle State Machine.

Maintains formal task records, execution states, and the 9-point handoff contract.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TaskState(StrEnum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    IN_REVIEW = "IN_REVIEW"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    DONE = "DONE"


# Legal transitions matrix
VALID_TRANSITIONS: dict[TaskState, list[TaskState]] = {
    TaskState.BACKLOG: [TaskState.READY, TaskState.BLOCKED],
    TaskState.READY: [TaskState.IN_PROGRESS, TaskState.BLOCKED],
    TaskState.IN_PROGRESS: [TaskState.IN_REVIEW, TaskState.BLOCKED, TaskState.VERIFICATION_FAILED],
    TaskState.BLOCKED: [TaskState.READY, TaskState.IN_PROGRESS],
    TaskState.IN_REVIEW: [TaskState.DONE, TaskState.VERIFICATION_FAILED, TaskState.BLOCKED],
    TaskState.VERIFICATION_FAILED: [TaskState.IN_PROGRESS, TaskState.BLOCKED],
    TaskState.DONE: [],  # Terminal state
}


class HandoffContract(BaseModel):
    """The mandatory 9-point handoff contract between agents."""

    task_id: str = Field(..., description="Unique task identifier")
    objective: str = Field(..., description="Target objective")
    scope_and_ownership: list[str] = Field(..., description="Allowed file scope")
    context_and_docs: list[str] = Field(default_factory=list, description="Relevant documentation")
    dependencies: list[str] = Field(default_factory=list, description="Upstream dependencies")
    acceptance_criteria: list[str] = Field(..., description="Testable acceptance criteria")
    files_changed: list[str] = Field(default_factory=list, description="Manifest of modified files")
    tests_and_results: dict[str, Any] = Field(
        default_factory=dict, description="Test output and coverage"
    )
    blockers_and_risks: list[str] = Field(
        default_factory=list, description="Identified risks and blockers"
    )
    next_step: str = Field(..., description="Recommended next action or agent handoff")


class TaskRecord(BaseModel):
    """Full task record stored in the task store."""

    id: str
    title: str
    description: str
    assigned_agent: str
    state: TaskState = TaskState.BACKLOG
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    handoffs: list[HandoffContract] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


class TaskStore:
    """Persistent storage engine for multi-agent tasks."""

    def __init__(self, storage_path: Path | None = None):
        if storage_path is None:
            storage_path = Path("agent_runtime/.state_checkpoints/task_store.json")
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, TaskRecord] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.values():
                        task = TaskRecord(**item)
                        self._tasks[task.id] = task
            except Exception:
                self._tasks = {}

    def _save(self) -> None:
        serialized = {k: v.model_dump() for k, v in self._tasks.items()}
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        assigned_agent: str,
        initial_state: TaskState = TaskState.BACKLOG,
        metadata: dict[str, Any] | None = None,
    ) -> TaskRecord:
        """Create a new task in the store."""
        task = TaskRecord(
            id=task_id,
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            state=initial_state,
            metadata=metadata or {},
        )
        self._tasks[task_id] = task
        self._save()
        return task

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def list_tasks(self, state: TaskState | None = None) -> list[TaskRecord]:
        if state:
            return [t for t in self._tasks.values() if t.state == state]
        return list(self._tasks.values())

    def update_task_state(self, task_id: str, new_state: TaskState) -> TaskRecord:
        """Transitions task state validating against state transition graph."""
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found in store")

        current = task.state
        if current != new_state:
            allowed = VALID_TRANSITIONS.get(current, [])
            if new_state not in allowed:
                raise ValueError(
                    f"Illegal state transition from {current.value} to {new_state.value}. "
                    f"Allowed transitions: {[s.value for s in allowed]}"
                )

        if new_state == TaskState.VERIFICATION_FAILED:
            task.retry_count += 1
            if task.retry_count > task.max_retries:
                new_state = TaskState.BLOCKED
                task.metadata["blocked_reason"] = "Exceeded maximum retry attempts"

        task.state = new_state
        task.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return task

    def record_handoff(self, task_id: str, handoff: HandoffContract) -> TaskRecord:
        """Attach a verified 9-point handoff contract to the task record."""
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found in store")
        task.handoffs.append(handoff)
        task.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return task
