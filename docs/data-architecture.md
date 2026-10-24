# GitPulse Data Architecture Specification

## 1. Medallion Data Pipeline Topology

```text
[Raw GitHub Events] ──► [Kafka Topic] ──► [Bronze: S3 Parquet Lake]
                                                    │
                                                    ▼
[Gold: Postgres Served Marts] ◄── [dbt] ◄── [Silver: Cleansed Iceberg]
```

## 2. Layers

### Bronze (Raw Events)
- Immutable, raw JSON payloads stored as Snappy-compressed Parquet files in MinIO bucket `gitpulse-lakehouse/raw/`.
- Partitioned by `year=YYYY/month=MM/day=DD/repo_id=...`.

### Silver (Cleansed & Deduplicated)
- Apache Iceberg tables with schema enforcement.
- Evaluated via `stg_github_events.sql` dbt models. Deduplicated using surrogate event hash.

### Gold (Analytical Marts)
- Transformed fact and dimensional tables:
  - `fct_repo_velocity`: Daily aggregates of commits, active authors, churn.
  - `fct_pr_cycle_time`: PR time-to-first-review, review-to-merge, and time-to-close.
  - `dim_contributors`: Contributor profiles and aggregate statistics.
