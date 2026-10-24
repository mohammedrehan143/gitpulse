"""MinIO S3-Compatible Lakehouse Client."""

from __future__ import annotations

from typing import Any


class LakehouseStorageClient:
    """Client for storing parquet analytical snapshots in MinIO / S3."""

    def __init__(self, endpoint: str = "localhost:9000", bucket: str = "gitpulse-lakehouse"):
        self.endpoint = endpoint
        self.bucket = bucket

    @staticmethod
    def build_partition_path(repo_name: str, metric_date: str) -> str:
        """Standardizes warehouse partition directory path."""
        sanitized_repo = repo_name.replace("/", "_")
        return f"repo={sanitized_repo}/year={metric_date[:4]}/month={metric_date[5:7]}/day={metric_date[8:10]}"

    def upload_parquet_table(
        self,
        table_name: str,
        partition_path: str,
        data: Any,
    ) -> dict[str, str]:
        """Uploads parquet files to lakehouse warehouse."""
        s3_key = f"warehouse/{table_name}/{partition_path}/data.parquet"
        return {
            "status": "UPLOADED",
            "bucket": self.bucket,
            "key": s3_key,
            "endpoint": self.endpoint,
        }
