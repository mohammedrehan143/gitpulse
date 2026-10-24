# GitPulse Architecture Guide

## 1. System Mission
GitPulse delivers real-time visibility into GitHub engineering activity and developer velocity at high scale. It processes thousands of webhook and polling events per second without bottlenecking or data loss.

## 2. Core Subsystems

### 2.1 Ingestion Subsystem (`backend/src/gitpulse/ingestion/`)
- Ingests events via webhook push (`POST /api/v1/webhooks/github`) or polling crawlers.
- Enforces HMAC SHA-256 webhook authenticity checks.
- Adheres to rate limits and buffers bursts through Apache Kafka.

### 2.2 Streaming & Processing Subsystem (`data_platform/kafka/`, `data_platform/spark/`)
- Apache Kafka topics act as the durable event bus with key-based partitioning (`repo_id`).
- PySpark Structured Streaming processes windowed rollups (e.g. 10-minute watermark, daily velocity aggregations).

### 2.3 Storage Subsystem (`backend/src/gitpulse/storage/`, `data_platform/storage/`)
- PostgreSQL 16 stores transactional repository state, webhook configurations, and served aggregates.
- MinIO / Apache Iceberg stores raw Parquet lakehouse archives for analytical queries and historical backfills.

### 2.4 Serving Subsystem (`backend/src/gitpulse/api/`)
- FastAPI REST server provides typed endpoints for velocity metrics and paginated event streams.
- WebSocket feeds emit real-time commit pushes to connected dashboards.

### 2.5 Web Dashboard (`frontend/`)
- React 18 + Vite responsive single-page application.
- Real-time commit velocity charts and WCAG 2.1 AA accessible activity grids.
