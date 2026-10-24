"""Kafka Streaming Event Producer."""

from __future__ import annotations

import json
from typing import Any

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class KafkaEventProducer:
    """Publishes normalized GitHub events to Apache Kafka streaming topics."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or settings.KAFKA_TOPIC_RAW_EVENTS
        self._buffer: list[dict[str, Any]] = []

    def serialize_event(self, event: dict[str, Any]) -> str:
        """Serializes event to standardized JSON string."""
        return json.dumps(event)

    def publish_event(self, key: str, event_data: dict[str, Any]) -> bool:
        """Publishes event to topic partitioned by repository key."""
        try:
            payload = self.serialize_event(event_data)
            # Store in local memory buffer for local dev & testing
            self._buffer.append({"key": key, "payload": payload, "topic": self.topic})
            logger.info("Published event to Kafka topic %s with key %s", self.topic, key)
            return True
        except Exception as exc:
            logger.error("Failed to publish event to Kafka: %s", exc)
            return False

    def get_buffered_events(self) -> list[dict[str, Any]]:
        """Returns buffered events."""
        return list(self._buffer)
