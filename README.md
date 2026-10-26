# GitPulse — GitHub Activity Analytics & Data Science Intelligence Platform

GitPulse is an enterprise-grade GitHub Activity Analytics, Data Engineering, and Data Science Intelligence Platform paired with an autonomous, strictly hierarchical Multi-Agent System (MAS). It ingests high-frequency GitHub event streams (commits, issues, pull requests, code reviews) directly into Supabase (PostgreSQL / SQLite fallback), executes recurring incremental ingestion using a lightweight native Python pipeline (zero Airflow or Docker dependency), trains and serves 4 independent Data Science ML models (Activity Forecasting, Anomaly Detection, Issue Resolution Duration, PR First-Review Delay), generates AI developer velocity insights via Groq (`openai/gpt-oss-120b`), dispatches real-time Discord webhook alerts, and surfaces predictive analytics through a FastAPI backend and a React/TypeScript dashboard.

---

## 1. High-Level System Architecture

```text
                                 ┌────────────────────────────────┐
                                 │   GitHub REST & GraphQL API    │
                                 └───────────────┬────────────────┘
                                                 │
                                                 ▼
                                 ┌────────────────────────────────┐
                                 │    Data Ingestion Pipeline     │
                                 │  (Incremental, Idempotent,     │
                                 │   Quality Validation Checks)   │
                                 └───────────────┬────────────────┘
                                                 │
                                                 ▼
                                 ┌────────────────────────────────┐
                                 │   PostgreSQL / SQLite Storage  │
                                 │   - pull_requests (normalized) │
                                 │   - issues (normalized)        │
                                 │   - github_events & commits    │
                                 │   - pipeline_runs (audit)      │
                                 └───────┬───────────────┬────────┘
                                         │               │
                         ┌───────────────┘               └───────────────┐
                         ▼                                               ▼
         ┌───────────────────────────────┐               ┌───────────────────────────────┐
         │     Data Science ML Engines   │               │     FastAPI Analytics API     │
         │ - Module A: Activity Forecast │               │ - Velocity & Ingestion Routes │
         │ - Module B: Anomaly Detection │◄──────────────┤ - Intelligence Endpoints      │
         │ - Module C: Issue Turnaround  │  (Persisted   │ - Inference & Simulation APIs │
         │ - Module D: PR Review Delay   │   Joblib ML)  │ - Real-Time WebSockets        │
         └───────────────────────────────┘               └───────────────┬───────────────┘
                                                                         │
                                                                         ▼
                                                         ┌───────────────────────────────┐
                                                         │   React 18 / Vite Dashboard   │
                                                         │ - Velocity & Activity Streams │
                                                         │ - 4 Data Science ML Panels    │
                                                         │ - Interactive Simulators      │
                                                         └───────────────────────────────┘
```

---

## 2. Four Data Science Analytical Modules

### Module A: Developer Activity Forecasting
- **Objective**: Forecast future daily repository activity trajectory across 7-day and 14-day horizons.
- **Methodology**: Autoregressive ML regressor (`Ridge` with Lags 1, 2, 3, 7, 14, rolling statistics `rolling_mean_7`, `rolling_std_7`, calendar features `day_of_week`, `is_weekend`) compared against Seasonal-Naive (7-day cycle) and Moving Average baselines.
- **Leakage Prevention & Evaluation**: Evaluated using chronological holdouts. Reports MAE, RMSE, and improvement over baseline. Computes residual-based 95% uncertainty intervals.

### Module B: Repository Anomaly Detection
- **Objective**: Surface anomalous activity spikes or drop-offs across commits, PRs, and issues without alarm spam.
- **Methodology**: Temporal rolling Median Absolute Deviation (MAD) modified z-score algorithm with safe zero-variance smoothing and multivariate Isolation Forest.
- **Leakage Prevention & Temporal Ordering**: Strictly computes baseline medians on prior $[t-W, t-1]$ days (zero future leakage). Distinguishes ordinary fluctuations in low-activity repos from confirmed incidents.

### Module C: Issue Resolution Time Prediction
- **Objective**: Estimate resolution turnaround in hours for candidate GitHub issues.
- **Features at Creation Time**: Title length, description length, code snippet flags, label one-hot tags (`bug`, `critical`, `enhancement`, `documentation`), creation weekday, and point-in-time open backlog workload.
- **Censoring Handling & Baseline**: Excludes open issues from training duration calculation to eliminate downward bias; compares candidate regressors (`Ridge`, `RandomForest`, `HistGradientBoosting`) with $\log(1+y)$ target transform against historical median baseline. Persisted with versioned metadata via `joblib`.

### Module D: Pull-Request Review Delay Analysis
- **Objective**: Understand factors driving review turnaround and estimate time to first qualifying review.
- **Features at PR Creation**: `additions`, `deletions`, `total_lines_changed`, `changed_files`, title/body length, weekday, concurrent PR workload.
- **Statistical & Censoring Analysis**: Calculates Spearman rank correlations and size-bracket turnaround medians (Small, Medium, Large, XL). Right-censored unreviewed PRs tracked and reported explicitly. Employs `HistGradientBoosting` ensemble to predict first-review delay.


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

## 5. Cloud Deployment (Vercel & Render)

GitPulse is ready for production cloud hosting:
- **Frontend SPA**: Deployable to [Vercel](https://vercel.com) via monorepo root or `frontend` subdirectory (`vercel.json`, `.vercelignore`).
- **FastAPI Backend**: Deployable to [Render](https://render.com) via 1-click Blueprint (`render.yaml`) or manual web service with automatic PostgreSQL dialect adaptation (`postgresql+asyncpg://`) and SQLite fallback.

For complete step-by-step instructions and environment variable settings, see the **[Cloud Deployment Guide](docs/DEPLOYMENT.md)**.

---

## 6. Agent Communication & Quality Gates

All task transitions follow strict contractual handoffs:
`BACKLOG` -> `READY` -> `IN_PROGRESS` -> `IN_REVIEW` -> `DONE` (or `BLOCKED` / `VERIFICATION_FAILED`)

Every completion requires satisfying 4 Quality Gates:
1. **Gate 1 (Static Analysis)**: Clean passes on `ruff check`, `black --check`, `mypy`.
2. **Gate 2 (Automated Tests)**: Branch coverage >= 85% with all tests passing.
3. **Gate 3 (Security Audit)**: Zero secrets, zero High/Critical vulnerabilities.
4. **Gate 4 (Independent Peer Review)**: Review approval by `independent-code-reviewer`.
