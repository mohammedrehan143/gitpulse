"""Apache Iceberg REST Catalog Client Configuration."""

from __future__ import annotations


class IcebergCatalogConfig:
    """Iceberg catalog properties for connecting to MinIO S3 Lakehouse."""

    @staticmethod
    def get_catalog_properties() -> dict[str, str]:
        return {
            "type": "rest",
            "uri": "http://localhost:8181",
            "warehouse": "s3://gitpulse-lakehouse/warehouse",
            "s3.endpoint": "http://localhost:9000",
            "s3.access-key-id": "minioadmin",
            "s3.secret-access-key": "minioadmin",
            "s3.path-style-access": "true",
        }

    @staticmethod
    def get_lakehouse_table_definitions() -> list[dict[str, str]]:
        """Returns schemas and partitioning keys for lakehouse tables."""
        return [
            {
                "table_name": "raw_events",
                "partition_spec": "identity(repo_id), days(created_at)",
                "file_format": "PARQUET",
            },
            {
                "table_name": "fct_commit_velocity",
                "partition_spec": "identity(repo_name), days(metric_date)",
                "file_format": "PARQUET",
            },
        ]
