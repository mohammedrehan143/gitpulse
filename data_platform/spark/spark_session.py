"""Apache Spark Session Builder with S3/MinIO & Iceberg support."""

from __future__ import annotations


class SparkSessionBuilder:
    """Configures SparkSession with MinIO S3 endpoint and Apache Iceberg catalog."""

    @staticmethod
    def get_spark_config() -> dict[str, str]:
        return {
            "spark.app.name": "GitPulse-Distributed-Engine",
            "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            "spark.sql.catalog.gitpulse_lake": "org.apache.iceberg.spark.SparkCatalog",
            "spark.sql.catalog.gitpulse_lake.type": "hadoop",
            "spark.sql.catalog.gitpulse_lake.warehouse": "s3a://gitpulse-lakehouse/warehouse",
            "spark.hadoop.fs.s3a.endpoint": "http://localhost:9000",
            "spark.hadoop.fs.s3a.access.key": "minioadmin",
            "spark.hadoop.fs.s3a.secret.key": "minioadmin",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        }
