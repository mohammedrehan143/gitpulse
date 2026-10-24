"""GitPulse File Permissions & Sandboxing Engine.

Enforces strict file ownership boundaries specified in .agents/policies/file-ownership.md.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional


class PermissionDeniedError(Exception):
    """Raised when an agent attempts to access or modify a file outside its scope."""

    def __init__(self, agent_id: str, path: str, operation: str, reason: str):
        self.agent_id = agent_id
        self.path = path
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Permission Denied: Agent '{agent_id}' is not authorized to perform '{operation}' "
            f"on path '{path}'. Reason: {reason}"
        )


# Mapping of agent identifiers to allowed write glob patterns (relative to repo root)
AGENT_WRITE_PERMISSIONS: Dict[str, List[str]] = {
    # Orchestrators
    "master-orchestrator": [
        ".agents/tasks/*",
        ".agents/policies/*",
        "agent_runtime/master/*",
        "agent_runtime/shared/*",
        "docs/decisions/*",
    ],
    "backend-orchestrator": [
        "backend/*",
        "data_platform/*",
        "agent_runtime/backend/*",
        ".agents/tasks/current-task.md",
    ],
    "frontend-orchestrator": [
        "frontend/*",
        "agent_runtime/frontend/*",
        ".agents/tasks/current-task.md",
    ],

    # Backend Specialists
    "api-engineer": [
        "backend/src/gitpulse/api/*",
        "docs/api-contracts.md",
    ],
    "ingestion-engineer": [
        "backend/src/gitpulse/ingestion/*",
        "data_platform/schemas/*",
    ],
    "database-engineer": [
        "backend/src/gitpulse/storage/*",
        "backend/migrations/*",
        "docs/database-schema.md",
    ],
    "kafka-engineer": [
        "backend/src/gitpulse/ingestion/kafka_producer.py",
        "data_platform/kafka/*",
    ],
    "spark-engineer": [
        "backend/src/gitpulse/services/processor.py",
        "data_platform/spark/*",
    ],
    "airflow-engineer": [
        "data_platform/airflow/dags/*",
    ],
    "dbt-engineer": [
        "data_platform/dbt/*",
    ],
    "backend-test-engineer": [
        "backend/tests/*",
    ],
    "backend-security-engineer": [
        "backend/src/gitpulse/common/security.py",
        ".agents/policies/security-rules.md",
    ],

    # Frontend Specialists
    "ui-ux-engineer": [
        "frontend/src/components/design-system/*",
        "frontend/src/styles/*",
        "frontend/src/layouts/*",
    ],
    "frontend-engineer": [
        "frontend/src/App.tsx",
        "frontend/src/main.tsx",
        "frontend/src/components/*",
        "frontend/src/layouts/*",
    ],
    "dashboard-engineer": [
        "frontend/src/charts/*",
        "frontend/src/pages/*",
    ],
    "api-integration-engineer": [
        "frontend/src/services/*",
        "frontend/src/hooks/*",
        "frontend/src/types/*",
    ],
    "accessibility-engineer": [
        "frontend/src/components/*",
        "frontend/tests/a11y/*",
    ],
    "frontend-test-engineer": [
        "frontend/tests/*",
        "frontend/src/**/*.test.tsx",
        "frontend/src/**/*.test.ts",
    ],

    # Shared Specialists
    "software-architect": [
        "docs/*",
        ".agents/tasks/contracts.md",
    ],
    "integration-engineer": [
        "agent_runtime/tests/integration/*",
        "docs/api-contracts.md",
        "tests/e2e/*",
    ],
    "devops-engineer": [
        "docker-compose.yml",
        "Makefile",
        "infra/*",
        ".github/workflows/*",
        ".env.example",
    ],
    "independent-code-reviewer": [
        ".agents/tasks/current-task.md",
    ],
}


class PermissionManager:
    """Validates and enforces file permissions across the multi-agent hierarchy."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = Path(workspace_root or ".").resolve()

    def normalize_path(self, target_path: str | Path) -> str:
        """Converts absolute or relative path to a standardized relative posix path."""
        p = Path(target_path)
        if p.is_absolute():
            try:
                rel = p.resolve().relative_to(self.workspace_root)
            except ValueError:
                # Path outside workspace
                return p.as_posix()
            return rel.as_posix()
        return p.as_posix()

    def can_write(self, agent_id: str, target_path: str | Path) -> bool:
        """Checks if agent is allowed to write or delete target_path."""
        normalized = self.normalize_path(target_path)
        allowed_patterns = AGENT_WRITE_PERMISSIONS.get(agent_id, [])

        for pattern in allowed_patterns:
            # Handle directory wildcards like backend/* matching backend/foo/bar.py
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if normalized == prefix or normalized.startswith(prefix + "/"):
                    return True
            if fnmatch.fnmatch(normalized, pattern):
                return True
        return False

    def check_write_permission(self, agent_id: str, target_path: str | Path) -> None:
        """Raises PermissionDeniedError if agent cannot write to target_path."""
        if not self.can_write(agent_id, target_path):
            norm = self.normalize_path(target_path)
            raise PermissionDeniedError(
                agent_id=agent_id,
                path=norm,
                operation="write",
                reason=f"Path '{norm}' is outside the authorized ownership scope for agent '{agent_id}'.",
            )
