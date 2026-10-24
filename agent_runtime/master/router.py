"""Master Orchestrator Task Router & Decomposition Engine.

Analyzes incoming task directives, classifies scope, resolves dependencies,
and generates structured subtask work packets.
"""

from __future__ import annotations

import re
from typing import List, Tuple
from agent_runtime.master.state import MasterState, SubTask
from agent_runtime.shared.task_store import TaskState


class TaskRouter:
    """Intelligent task decomposition and routing logic."""

    @staticmethod
    def classify_task_type(prompt: str) -> str:
        prompt_lower = prompt.lower()
        words = set(re.findall(r"\b\w+\b", prompt_lower))
        if any(w in words for w in ["fix", "bug", "error", "defect", "broken", "fail"]):
            return "BUG"
        if any(w in words for w in ["docker", "compose", "ci", "deploy"]) or "github actions" in prompt_lower:
            return "INFRASTRUCTURE"
        if any(w in words for w in ["refactor", "cleanup", "reorganize", "deprecate"]):
            return "REFACTOR"
        if any(w in words for w in ["contract", "e2e", "integration", "cross-domain"]) or "cross-domain" in prompt_lower:
            return "INTEGRATION"
        return "FEATURE"

    @staticmethod
    def decompose_epic(epic_id: str, prompt: str) -> Tuple[List[SubTask], bool]:
        """Decomposes prompt into ordered subtasks and determines contract requirement."""
        task_type = TaskRouter.classify_task_type(prompt)
        prompt_lower = prompt.lower()

        subtasks: List[SubTask] = []
        requires_contract = False

        needs_backend = any(w in prompt_lower for w in [
            "api", "backend", "fastapi", "kafka", "spark", "dbt", "postgres",
            "database", "ingestion", "pipeline", "endpoint", "webhook"
        ]) or task_type == "FEATURE"

        needs_frontend = any(w in prompt_lower for w in [
            "ui", "frontend", "react", "dashboard", "chart", "component",
            "page", "view", "css", "vite", "web"
        ]) or task_type == "FEATURE"

        if needs_backend and needs_frontend:
            requires_contract = True

        if requires_contract:
            subtasks.append(
                SubTask(
                    id=f"{epic_id}-CONTRACT",
                    title="Define and Approve Domain Interface Contract",
                    domain="shared",
                    assigned_agent="software-architect",
                    file_scope=[".agents/tasks/contracts.md", "docs/api-contracts.md"],
                    acceptance_criteria=[
                        "REST endpoint and schema specifications documented",
                        "Kafka event schema published in contracts.md",
                    ],
                )
            )

        if needs_backend:
            subtasks.append(
                SubTask(
                    id=f"{epic_id}-BE",
                    title="Implement Backend Data Pipelines and Serving Routes",
                    domain="backend",
                    assigned_agent="backend-orchestrator",
                    file_scope=["backend/*", "data_platform/*"],
                    acceptance_criteria=[
                        "Backend routes conform to contracts.md",
                        "Branch test coverage >= 85%",
                        "Zero high severity security findings",
                    ],
                    dependencies=[f"{epic_id}-CONTRACT"] if requires_contract else [],
                )
            )

        if needs_frontend:
            subtasks.append(
                SubTask(
                    id=f"{epic_id}-FE",
                    title="Implement Frontend Dashboard Components & Visualizations",
                    domain="frontend",
                    assigned_agent="frontend-orchestrator",
                    file_scope=["frontend/*"],
                    acceptance_criteria=[
                        "Consumes verified backend contract",
                        "Interactive charts rendered with error states",
                        "Zero WCAG 2.1 AA accessibility violations",
                    ],
                    dependencies=[f"{epic_id}-BE"] if (needs_backend and not prompt_lower.startswith("mock")) else [],
                )
            )

        # Verification Subtask
        subtasks.append(
            SubTask(
                id=f"{epic_id}-VERIFY",
                title="Cross-Domain Integration & Independent Peer Review",
                domain="shared",
                assigned_agent="independent-code-reviewer",
                file_scope=[".agents/tasks/current-task.md"],
                acceptance_criteria=[
                    "Automated tests passing with 100% green assertions",
                    "Independent code reviewer sign-off obtained",
                ],
                dependencies=[t.id for t in subtasks],
            )
        )

        return subtasks, requires_contract
