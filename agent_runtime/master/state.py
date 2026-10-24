"""Master Orchestrator State Definitions.

Defines the centralized state schema for task coordination, wave execution,
and quality gate verification.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_runtime.shared.task_store import TaskState


class SubTask(BaseModel):
    id: str
    title: str
    domain: str  # "backend", "frontend", "shared"
    assigned_agent: str
    file_scope: list[str]
    state: TaskState = TaskState.READY
    acceptance_criteria: list[str]
    dependencies: list[str] = Field(default_factory=list)
    result_summary: str | None = None


class MasterState(BaseModel):
    epic_id: str
    user_prompt: str
    task_type: str  # "FEATURE", "BUG", "REFACTOR", "INFRASTRUCTURE", "INTEGRATION"
    state: TaskState = TaskState.READY
    subtasks: list[SubTask] = Field(default_factory=list)
    active_wave: int = 1
    total_waves: int = 3
    contract_signed: bool = False
    quality_gates_passed: bool = False
    review_approved: bool = False
    errors: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    execution_receipt: dict[str, Any] | None = None
