"""Stream & Batch Event Processor."""

from __future__ import annotations

from typing import Any


class StreamProcessor:
    """Processes inbound raw event streams and produces enriched window metrics."""

    def __init__(self):
        self.processed_count = 0
        self._seen_event_ids: set[str] = set()

    def process_raw_event(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        """Normalizes and enriches a raw GitHub event."""
        self.processed_count += 1
        event_id = str(
            raw_event.get("id") or raw_event.get("event_id") or f"gen_{self.processed_count}"
        )
        event_type = raw_event.get("type") or raw_event.get("event_type")

        actor = raw_event.get("actor", {})
        actor_login = actor.get("login") if isinstance(actor, dict) else str(actor)
        avatar_url = actor.get("avatar_url") if isinstance(actor, dict) else None

        self._seen_event_ids.add(event_id)

        return {
            "event_id": event_id,
            "event_type": event_type,
            "actor_login": actor_login,
            "actor_avatar_url": avatar_url,
            "created_at": raw_event.get("created_at"),
            "processed": True,
        }

    def deduplicate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filters out duplicate events using streaming watermarking set."""
        unique: list[dict[str, Any]] = []
        for e in events:
            eid = str(e.get("id") or e.get("event_id") or "")
            if eid and eid in self._seen_event_ids:
                continue
            if eid:
                self._seen_event_ids.add(eid)
            unique.append(e)
        return unique

    def get_watermark_stats(self) -> dict[str, int]:
        """Returns statistics on processed and tracked events."""
        return {
            "processed_count": self.processed_count,
            "unique_tracked_events": len(self._seen_event_ids),
        }
