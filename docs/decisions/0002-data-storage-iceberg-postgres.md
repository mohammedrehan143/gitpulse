# ADR 0002: Hybrid Storage Architecture (PostgreSQL & Apache Iceberg)

## Status
Accepted

## Context
GitPulse must satisfy two distinct access patterns:
1. Low-latency OLTP queries for API serving and dashboard rendering (< 50ms).
2. High-throughput historical analytical aggregations across billions of past GitHub events.

## Decision
We adopt a hybrid storage pattern:
- PostgreSQL 16 for metadata, repository settings, and pre-computed daily velocity aggregates.
- Apache Iceberg over MinIO / S3 object storage for raw immutable event lakes, backfilling, and dbt batch modeling.

## Consequences
- Positive: Sub-50ms dashboard response times via PostgreSQL.
- Positive: Low-cost horizontal scaling for raw event storage via MinIO Parquet files.
- Negative: Requires dual storage maintenance and ETL synchronization pipelines.
