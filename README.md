# GitPulse — GitHub Activity Analytics Data Engineering Platform & Multi-Agent Architecture

GitPulse is an enterprise-grade GitHub Activity Analytics and Engineering Intelligence Platform paired with an autonomous, strictly hierarchical Multi-Agent System (MAS). It ingests high-frequency GitHub event streams (commits, issues, pull requests, code reviews) directly into Supabase (PostgreSQL / SQLite fallback), executes recurring event ingestion using a lightweight native Python scheduler (zero Airflow or Docker dependency), generates AI developer velocity insights via Groq (`openai/gpt-oss-120b`), dispatches real-time Discord webhook alerts, and surfaces live developer velocity metrics through a FastAPI backend and a React/TypeScript dashboard.

---

## 1. High-Level System Architecture

```text
                                 ┌────────────────────────────────┐
                                 │   GitHub REST & GraphQL API    │
                                 └───────────────┬────────────────┘
                                                 │
                                                 ▼
                                 ┌────────────────────────────────┐
                                 │   GitPulse Ingestion Service   │
                                 │   (Rate Limit & Pagination)    │
                                 └───────────────┬────────────────┘
                                                 │
                                                 ▼
                                 ┌────────────────────────────────┐
                                 │      Apache Kafka (KRaft)      │
                                 │ (Topics: events, prs, commits) │
                                 └───────┬───────────────┬────────┘
                                         │               │
                         ┌───────────────┘               └───────────────┐
                         ▼                                               ▼
         ┌───────────────────────────────┐               ┌───────────────────────────────┐
         │     Apache Spark Streaming    │               │       PostgreSQL Storage      │
         │   (Windowing, Deduplication)  │               │   (Transactional & Metadata)  │
         └───────────────┬───────────────┘               └───────────────┬───────────────┘
                         │                                               │
                         ▼                                               ▼
         ┌───────────────────────────────┐               ┌───────────────────────────────┐
         │ Apache Iceberg / MinIO Lake   │               │     FastAPI Analytics API     │
         │  (dbt Dimensional Transforms) │               │   (REST Endpoints & Schemas)  │
         └───────────────────────────────┘               └───────────────┬───────────────┘
                                                                         │
                                                                         ▼
                                                         ┌───────────────────────────────┐
                                                         │   React 18 / Vite Dashboard   │
                                                         │ (Velocity Charts & Heatmaps)  │
                                                         └───────────────────────────────┘
```

---

## 2. Hierarchical Multi-Agent Architecture (MAS)

GitPulse utilizes a hierarchical agent organization to eliminate chaotic flat communications, prevent cross-domain file collision, and enforce strict delivery contracts.

```text
                               ┌─────────────────────────────┐
                               │     Master Orchestrator     │
                               │   (Strategic Coordinator)   │
                               └──────────────┬──────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │    Backend Orchestrator     │                   │    Frontend Orchestrator    │
      │   (Tactical Lead - Data)    │                   │    (Tactical Lead - Web)    │
      └──────────────┬──────────────┘                   └──────────────┬──────────────┘
                     │                                                 │
      ┌──────────────┴──────────────┐                   ┌──────────────┴──────────────┐
      │ - API Engineer              │                   │ - UI/UX Engineer            │
      │ - Ingestion Engineer        │                   │ - Frontend Engineer         │
      │ - Database Engineer         │                   │ - Dashboard Engineer        │
      │ - Kafka Engineer            │                   │ - API Integration Engineer  │
      │ - Spark Engineer            │                   │ - Accessibility Engineer    │
      │ - Airflow Engineer          │                   │ - Frontend Test Engineer    │
      │ - dbt Engineer              │                   └─────────────────────────────┘
      │ - Backend Test Engineer     │
      │ - Backend Security Engineer │
      └─────────────────────────────┘
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              ▼
                               ┌─────────────────────────────┐
                               │   Shared Cross-Cut Squad    │
                               │ - Software Architect        │
                               │ - Integration Engineer      │
                               │ - DevOps Engineer           │
                               │ - Independent Code Reviewer │
                               └─────────────────────────────┘
```

### Agent Roles & Delegations
- **Master Orchestrator**: Single top-level coordinator. Decomposes requirements into tickets, tracks lifecycle state (`BACKLOG` -> `READY` -> `IN_PROGRESS` -> `IN_REVIEW` -> `DONE`), enforces quality gates, and coordinates child orchestrators.
- **Backend Orchestrator**: Direct lead for ingestion, streaming, relational/lakehouse storage, transformation, and API routes. Coordinates 9 specialized backend engineers.
- **Frontend Orchestrator**: Direct lead for UI design systems, dashboard visualizations, state management, accessibility, and client test suites. Coordinates 6 specialized frontend engineers.
- **Shared Specialists**: Software Architect (system design & schemas), DevOps Engineer (infrastructure & CI/CD), Integration Engineer (cross-service contracts), and Independent Code Reviewer (strict verification).

---

## 3. Directory Layout

```text
gitpulse/
├── AGENTS.md                  # Master governance & agent specifications
├── README.md                  # System & architecture documentation
├── .gitignore                 # Git ignore rules
├── .env.example               # Environment variables specification
├── docker-compose.yml         # Container infrastructure stack
├── pyproject.toml             # Packaging, dependencies, and lint configs
├── Makefile                   # Developer CLI targets
│
├── .agents/                   # Agent Persona & Instruction Markdown Files
│   ├── master-orchestrator.md # L0 Coordinator instructions
│   ├── orchestrators/         # L1 Domain Orchestrators (Backend & Frontend)
│   ├── backend/               # 9 L2 Backend Specialized Engineers
│   ├── frontend/              # 6 L2 Frontend Specialized Engineers
│   ├── shared/                # 4 Shared Cross-Domain Specialists
│   ├── workflows/             # SOP workflows (Feature, Bugfix, Integration, Release)
│   ├── policies/              # Governance policies (Handoff, Ownership, Security, Gates)
│   └── tasks/                 # Task ledger, current execution, interface contracts
│
├── agent_runtime/             # Executable Python Orchestration Engine
│   ├── master/                # Master state machine, router, and graph
│   ├── backend/               # Backend sub-graph orchestrator
│   ├── frontend/              # Frontend sub-graph orchestrator
│   ├── shared/                # Task store, checkpoints, permissions, telemetry
│   ├── tools/                 # Tool implementations (Filesystem, Git, Test, Docker)
│   ├── tests/                 # Unit & integration tests for agent runtime
│   └── main.py                # Command-line interface for running the multi-agent system
│
├── backend/                   # FastAPI & Data Ingestion Backend
│   ├── src/gitpulse/          # Core modules: API, Ingestion, Storage, Services, Common
│   ├── migrations/            # Database schema migrations
│   └── tests/                 # Pytest test suite for backend
│
├── frontend/                  # React + TypeScript + Vite Dashboard
│   ├── src/                   # Components, Pages, Charts, Services, Hooks, Types
│   └── tests/                 # Frontend test suites
│
├── data_platform/             # Data Engineering Pipelines
│   ├── airflow/dags/          # Scheduled batch extraction & aggregation DAGs
│   ├── spark/                 # Spark streaming and batch aggregation jobs
│   ├── kafka/                 # Topic definitions and consumer configurations
│   ├── dbt/                   # dbt staging and mart models
│   ├── schemas/               # JSON Schema definitions for ingested events
│   └── storage/               # Apache Iceberg & MinIO client connectors
│
├── infra/                     # Infrastructure as Code
│   ├── docker/                # Production Dockerfiles (Backend, Frontend, Spark)
│   ├── prometheus/            # Metric scraping configuration
│   ├── grafana/               # Dashboards and visualization configs
│   └── otel/                  # OpenTelemetry collector configuration
│
├── docs/                      # Technical Documentation & RFCs
│   ├── architecture.md        # Core architecture guide
│   ├── data-architecture.md   # Data pipelines & lakehouse specs
│   ├── api-contracts.md       # OpenAPI & REST contracts
│   ├── database-schema.md     # Relational & analytical schemas
│   ├── agent-architecture.md  # Detailed Multi-Agent state machines
│   └── decisions/             # Architecture Decision Records (ADRs)
│
└── .github/workflows/         # CI/CD Workflows
    └── ci.yml                 # Automated test, lint, and security pipelines
```

---

## 4. Getting Started

### 4.1 Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker & Docker Compose
- Git

### 4.2 Quickstart & Local Setup

1. **Clone and Configure**:
   ```bash
   cp .env.example .env
   ```

2. **Install Python Runtime & Dependencies**:
   ```bash
   make install
   # Or manually:
   pip install -e ".[dev,streaming,storage]"
   ```

3. **Start Lightweight Ingestion Scheduler (Zero Docker / Airflow Needed)**:
   ```bash
   # Run the scheduler directly on Windows / Linux:
   python -m backend.src.gitpulse.scheduler

   # Or via make target:
   make scheduler

   # Custom interval (e.g., every 30 minutes) with Discord alerts:
   python -m backend.src.gitpulse.scheduler --interval 30 --notify
   ```
   - Automatically executes an ingestion cycle **immediately** on startup.
   - Repeats ingestion every 60 minutes (configurable via `REPO_DISCOVERY_INTERVAL_MINUTES` or `--interval`).
   - Discovers all repositories owned by authenticated GitHub token (`AUTO_DISCOVER_REPOSITORIES=true`).
   - Persists `GitHubEvent` and repository metadata directly into Supabase (or SQLite dev fallback).
   - Prevents overlapping ingestion runs via concurrency locking.
   - Graceful shutdown with `Ctrl+C`.

4. **Start the FastAPI Backend Server**:
   ```bash
   make backend-dev
   # Runs on http://localhost:8000 (Swagger docs at http://localhost:8000/docs)
   ```

5. **Start the Frontend Dashboard**:
   ```bash
   make frontend-dev
   # Runs on http://localhost:5173
   ```

6. **Run Test Suites**:
   ```bash
   make test
   # Runs all 53 backend and scheduler unit tests
   ```

---

## 5. Agent Communication & Quality Gates

All task transitions follow strict contractual handoffs:
`BACKLOG` -> `READY` -> `IN_PROGRESS` -> `IN_REVIEW` -> `DONE` (or `BLOCKED` / `VERIFICATION_FAILED`)

Every completion requires satisfying 4 Quality Gates:
1. **Gate 1 (Static Analysis)**: Clean passes on `ruff check`, `black --check`, `mypy`.
2. **Gate 2 (Automated Tests)**: Branch coverage >= 85% with all tests passing.
3. **Gate 3 (Security Audit)**: Zero secrets, zero High/Critical vulnerabilities.
4. **Gate 4 (Independent Peer Review)**: Review approval by `independent-code-reviewer`.
