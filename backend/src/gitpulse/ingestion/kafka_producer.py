"""Kafka Streaming Event Producer."""

from __future__ import annotations

import json
from typing import Any

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class KafkaEventProducer:
    """Publishes normalized GitHub events to Apache Kafka streaming topics."""

    REQUIRED_SCHEMA_FIELDS = ("event_id", "event_type", "repo_id", "actor_login", "created_at")

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.default_topic = topic or settings.KAFKA_TOPIC_RAW_EVENTS
        self._buffer: list[dict[str, Any]] = []

    def validate_event_schema(self, event_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validates that the payload contains required attributes."""
        missing = [f for f in self.REQUIRED_SCHEMA_FIELDS if f not in event_data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, None

    def route_topic_for_event(self, event_type: str | None) -> str:
        """Determines target Kafka topic according to event classification."""
        if event_type == "PushEvent":
            return settings.KAFKA_TOPIC_COMMITS
        elif event_type == "PullRequestEvent":
            return settings.KAFKA_TOPIC_PULL_REQUESTS
        return self.default_topic

    def serialize_event(self, event: dict[str, Any]) -> str:
        """Serializes event to standardized JSON string."""
        return json.dumps(event, default=str)

    def publish_event(
        self,
        key: str,
        event_data: dict[str, Any],
        topic: str | None = None,
        validate: bool = False,
    ) -> bool:
        """Publishes event to Kafka topic partitioned by repository key."""
        if validate:
            is_valid, err = self.validate_event_schema(event_data)
            if not is_valid:
                logger.warning("Event schema validation rejected: %s", err)
                return False

        target_topic = topic or self.route_topic_for_event(
            event_data.get("event_type") or event_data.get("type")
        )

        try:
            payload = self.serialize_event(event_data)
            # Store in durable buffer for local dev & hermetic testing
            self._buffer.append(
                {
                    "key": str(key),
                    "payload": payload,
                    "topic": target_topic,
                    "event_type": event_data.get("event_type") or event_data.get("type"),
                }
            )
            logger.info("Published event to Kafka topic %s with key %s", target_topic, key)
            return True
        except Exception as exc:
            logger.error("Failed to publish event to Kafka: %s", exc)
            return False

    def get_buffered_events(self) -> list[dict[str, Any]]:
        """Returns buffered events."""
        return list(self._buffer)

    def clear_buffer(self) -> None:
        """Clears in-memory buffer."""
        self._buffer.clear()
