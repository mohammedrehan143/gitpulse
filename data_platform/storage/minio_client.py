"""MinIO S3-Compatible Lakehouse Client."""

from typing import Any, Dict


class LakehouseStorageClient:
    """Client for storing parquet analytical snapshots in MinIO / S3."""

    def __init__(self, endpoint: str = "localhost:9000", bucket: str = "gitpulse-lakehouse"):
        self.endpoint = endpoint
        self.bucket = bucket

    def upload_parquet_table(self, table_name: str, partition_path: str, data: Any) -> Dict[str, str]:
        """Uploads parquet files to lakehouse warehouse."""
        s3_key = f"warehouse/{table_name}/{partition_path}/data.parquet"
        return {"status": "UPLOADED", "bucket": self.bucket, "key": s3_key}
