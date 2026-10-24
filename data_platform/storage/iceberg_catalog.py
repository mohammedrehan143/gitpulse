"""Apache Iceberg REST Catalog Client Configuration."""

from typing import Dict


class IcebergCatalogConfig:
    """Iceberg catalog properties for connecting to MinIO S3 Lakehouse."""

    @staticmethod
    def get_catalog_properties() -> Dict[str, str]:
        return {
            "type": "rest",
            "uri": "http://localhost:8181",
            "warehouse": "s3://gitpulse-lakehouse/warehouse",
            "s3.endpoint": "http://localhost:9000",
            "s3.access-key-id": "minioadmin",
            "s3.secret-access-key": "minioadmin",
            "s3.path-style-access": "true",
        }
