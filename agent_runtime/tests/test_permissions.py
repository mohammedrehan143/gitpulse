"""Tests for file ownership and permissions sandboxing."""

from pathlib import Path

import pytest

from agent_runtime.shared.permissions import PermissionDeniedError, PermissionManager


def test_permission_manager_allows_authorized_paths():
    pm = PermissionManager(workspace_root=Path("."))

    # backend-orchestrator can write to backend files
    assert pm.can_write("backend-orchestrator", "backend/src/gitpulse/api/routes.py")
    assert pm.can_write("backend-orchestrator", "data_platform/kafka/topics.json")

    # frontend-orchestrator can write to frontend files
    assert pm.can_write("frontend-orchestrator", "frontend/src/App.tsx")
    assert pm.can_write("frontend-orchestrator", "frontend/src/charts/CommitVelocityChart.tsx")

    # api-engineer can write to api routes
    assert pm.can_write("api-engineer", "backend/src/gitpulse/api/routes.py")

    # devops-engineer can write to docker-compose and infra
    assert pm.can_write("devops-engineer", "docker-compose.yml")
    assert pm.can_write("devops-engineer", "infra/prometheus/prometheus.yml")


def test_permission_manager_blocks_unauthorized_cross_domain_writes():
    pm = PermissionManager(workspace_root=Path("."))

    # frontend-orchestrator CANNOT write to backend
    assert not pm.can_write("frontend-orchestrator", "backend/src/gitpulse/api/routes.py")

    # backend-orchestrator CANNOT write to frontend
    assert not pm.can_write("backend-orchestrator", "frontend/src/App.tsx")

    # api-engineer CANNOT write to kafka producer directly
    assert not pm.can_write("api-engineer", "backend/src/gitpulse/ingestion/kafka_producer.py")


def test_check_write_permission_raises_exception():
    pm = PermissionManager(workspace_root=Path("."))

    with pytest.raises(PermissionDeniedError) as exc_info:
        pm.check_write_permission("ui-ux-engineer", "backend/src/gitpulse/storage/models.py")

    assert "ui-ux-engineer" in str(exc_info.value)
    assert "backend/src/gitpulse/storage/models.py" in str(exc_info.value)
