"""GitPulse State Checkpoints Engine.

Saves point-in-time snapshots of execution graphs and task states for durability,
replayability, and crash recovery.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CheckpointManager:
    """Manages snapshot creation, inspection, and rollback of multi-agent states."""

    def __init__(self, checkpoint_dir: Path | None = None):
        if checkpoint_dir is None:
            checkpoint_dir = Path("agent_runtime/.state_checkpoints")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        checkpoint_id: str,
        task_id: str,
        agent_id: str,
        state_data: dict[str, Any],
        step_number: int = 1,
    ) -> Path:
        """Persists state data to disk."""
        snapshot = {
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "step_number": step_number,
            "timestamp": datetime.now(UTC).isoformat(),
            "state_data": state_data,
        }
        file_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        return file_path

    def load_checkpoint(self, task_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        """Loads a specific checkpoint from disk."""
        file_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def list_checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        """Lists all checkpoints associated with a task."""
        results = []
        for file in sorted(self.checkpoint_dir.glob(f"{task_id}_*.json")):
            with open(file, encoding="utf-8") as f:
                results.append(json.load(f))
        return results

    def get_latest_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Returns the most recent checkpoint for a task."""
        checkpoints = self.list_checkpoints(task_id)
        if not checkpoints:
            return None
        return checkpoints[-1]
