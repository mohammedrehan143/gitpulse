"""Stream & Batch Event Processor."""

from __future__ import annotations

from typing import Any


class StreamProcessor:
    """Processes inbound raw event streams and produces enriched window metrics."""

    def __init__(self):
        self.processed_count = 0

    def process_raw_event(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        """Normalizes and enriches a raw GitHub event."""
        self.processed_count += 1
        event_id = raw_event.get("id") or raw_event.get("event_id")
        event_type = raw_event.get("type") or raw_event.get("event_type")

        actor = raw_event.get("actor", {})
        actor_login = actor.get("login") if isinstance(actor, dict) else str(actor)
        avatar_url = actor.get("avatar_url") if isinstance(actor, dict) else None

        return {
            "event_id": str(event_id),
            "event_type": event_type,
            "actor_login": actor_login,
            "actor_avatar_url": avatar_url,
            "created_at": raw_event.get("created_at"),
            "processed": True,
        }
