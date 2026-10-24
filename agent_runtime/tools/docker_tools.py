"""GitPulse Docker & Container Management Tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class DockerTools:
    """Tooling interface for Docker Compose orchestration checks."""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = Path(workspace_root or ".").resolve()

    def _run_docker(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker"] + args,
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def validate_compose_config(self) -> dict[str, Any]:
        """Validates docker-compose.yml configuration."""
        compose_file = self.workspace_root / "docker-compose.yml"
        if not compose_file.exists():
            return {"valid": False, "error": "docker-compose.yml not found"}

        res = self._run_docker(["compose", "config", "-q"])
        return {
            "valid": res.returncode == 0,
            "error": res.stderr if res.returncode != 0 else None,
        }

    def get_service_status(self) -> dict[str, Any]:
        """Queries running container statuses."""
        res = self._run_docker(["compose", "ps", "--format", "json"])
        if res.returncode != 0:
            return {"active": False, "error": res.stderr}
        return {"active": True, "output": res.stdout}
