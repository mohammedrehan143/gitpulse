"""Kafka Consumer Group Configuration and Offset Manager."""

from typing import Dict, List


class KafkaConsumerGroupConfig:
    """Configures high-throughput, fault-tolerant Kafka consumer groups."""

    @staticmethod
    def get_consumer_properties(group_id: str = "gitpulse-stream-processors") -> Dict[str, str]:
        return {
            "bootstrap.servers": "localhost:9092",
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": "false",
            "max.poll.interval.ms": "300000",
            "session.timeout.ms": "45000",
        }
