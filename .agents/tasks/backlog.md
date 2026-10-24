# GitPulse Product & Engineering Backlog

## Milestone 1: Multi-Agent Architecture & Runtime Foundation (Status: DONE)
- [x] **MAS-101**: Establish hierarchical agent roles, boundaries, and governance policies.
- [x] **MAS-102**: Define task lifecycle states and 9-point handoff contract specification.
- [x] **MAS-103**: Implement executable LangGraph-compatible agent runtime in `agent_runtime/`.
- [x] **MAS-104**: Implement unit and integration tests for state transitions, permissions, and routing.

## Milestone 2: Core Ingestion & Streaming Backbone (Status: DONE)
- [x] **DATA-201**: Implement GitHub Events Ingestion Client with pagination and rate limit handling.
- [x] **DATA-202**: Setup Apache Kafka topics, partition strategies, and Avro/JSON event producers.
- [x] **DATA-203**: Author PySpark Structured Streaming consumer for deduplication and windowed aggregations.
- [x] **DATA-204**: Configure MinIO / Apache Iceberg Lakehouse storage connectors.

## Milestone 3: Storage, Modeling & Analytics Serving (Status: DONE)
- [x] **STOR-301**: Design PostgreSQL schema for repositories, events, and developer metrics with Alembic migrations.
- [x] **STOR-302**: Author dbt models (staging, intermediate, and marts) for commit velocity and PR turnaround.
- [x] **STOR-303**: Author Airflow batch scheduling DAGs for daily aggregate rollups.
- [x] **API-301**: Implement FastAPI REST endpoints for repository analytics and commit velocity queries.

## Milestone 4: Modern React Analytics Dashboard (Status: DONE)
- [x] **UI-401**: Build React 18 + Vite application shell with responsive layout and design tokens.
- [x] **UI-402**: Implement interactive velocity and commit frequency charts using open-source charting library.
- [x] **UI-403**: Build repository metrics summary cards and recent activity tables.
- [x] **UI-404**: Execute WCAG 2.1 AA accessibility audit and comprehensive test suite.
