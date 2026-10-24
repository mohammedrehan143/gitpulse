"""GitPulse Telemetry & Audit Trail Engine.

Records structured execution logs, state transitions, quality gate outcomes,
and operational metrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class TelemetryLogger:
    """Structured telemetry logger storing JSONL events to disk."""

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path("agent_runtime/.telemetry_logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.log_dir / "events.jsonl"

    def record_event(
        self,
        event_type: str,
        agent_id: str,
        task_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Appends a structured event object to the telemetry log."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "task_id": task_id,
            "details": details or {},
        }
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def get_events(
        self,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves and filters events from the telemetry file."""
        if not self.events_file.exists():
            return []

        results = []
        with open(self.events_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if task_id and entry.get("task_id") != task_id:
                        continue
                    if agent_id and entry.get("agent_id") != agent_id:
                        continue
                    if event_type and entry.get("event_type") != event_type:
                        continue
                    results.append(entry)
                except Exception:
                    continue
        return results
