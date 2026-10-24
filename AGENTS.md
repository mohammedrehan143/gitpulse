# GitPulse Multi-Agent Architecture & Governance Guide

## 1. System Overview

**GitPulse** is a high-throughput GitHub Activity Analytics and Data Engineering Platform. It ingests raw GitHub event streams (commits, pull requests, issues, review timelines), streams them through Apache Kafka, processes analytical aggregates via Apache Spark and dbt, stores persistent state in Supabase (PostgreSQL) and ClickHouse, serves analytics via FastAPI, and presents real-time developer velocity metrics through a React/TypeScript dashboard.

To engineer, test, maintain, and evolve GitPulse at scale, the engineering organization operates under an autonomous, strict, hierarchical **Multi-Agent System (MAS)**:

```
                          ┌─────────────────────────────┐
                          │     Master Orchestrator     │
                          │   (Strategic Coordinator)   │
                          └──────────────┬──────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
  ┌─────────────────────────────┐                 ┌─────────────────────────────┐
  │    Backend Orchestrator     │                 │    Frontend Orchestrator    │
  │   (Tactical Lead - Data)    │                 │    (Tactical Lead - Web)    │
  └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                 │                                               │
  ┌──────────────┴──────────────┐                 ┌──────────────┴──────────────┐
  │ - API Engineer              │                 │ - UI/UX Engineer            │
  │ - Ingestion Engineer        │                 │ - Frontend Engineer         │
  │ - Database Engineer         │                 │ - Dashboard Engineer        │
  │ - Kafka Engineer            │                 │ - API Integration Engineer  │
  │ - Spark Engineer            │                 │ - Accessibility Engineer    │
  │ - Airflow Engineer          │                 │ - Frontend Test Engineer    │
  │ - dbt Engineer              │                 └─────────────────────────────┘
  │ - Backend Test Engineer     │
  │ - Backend Security Engineer │
  └─────────────────────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │   Shared Cross-Cut Squad    │
                          │ - Software Architect        │
                          │ - Integration Engineer      │
                          │ - DevOps Engineer           │
                          │ - Independent Code Reviewer │
                          └─────────────────────────────┘
```

---

## 2. Hierarchical Chain of Command

### 2.1 Level 0: The Master Orchestrator (`.agents/master-orchestrator.md`)
- **Authority**: Ultimate technical authority on task intake, prioritization, cross-domain arbitration, and milestone delivery.
- **Direct Subordinates**: Backend Orchestrator, Frontend Orchestrator, Software Architect, Independent Code Reviewer.
- **Responsibilities**:
  - Decomposes high-level epics and PRDs into actionable domain contracts (`.agents/tasks/contracts.md`).
  - Assigns sub-tasks to Backend and Frontend Orchestrators.
  - Monitors state transitions in the global Task Store (`agent_runtime/shared/task_store.py`).
  - Resolves integration deadlock between backend and frontend contracts.
  - Enforces final Quality Gates before any release tag or branch merge.

### 2.2 Level 1: Domain Orchestrators
#### A. Backend Orchestrator (`.agents/orchestrators/backend-orchestrator.md`)
- **Authority**: Direct manager of all backend, data pipeline, storage, analytics, and security tasks.
- **Direct Subordinates**: Ingestion Engineer, Kafka Engineer, Spark Engineer, Database Engineer, dbt Engineer, Airflow Engineer, API Engineer, Backend Test Engineer, Backend Security Engineer.
- **Responsibilities**:
  - Deconstructs backend contracts into technical work packets.
  - Schedules execution waves (e.g., Database migrations -> Kafka streaming -> API routes).
  - Validates test coverage (>= 85%) and security scan passes before reporting completion to the Master Orchestrator.

#### B. Frontend Orchestrator (`.agents/orchestrators/frontend-orchestrator.md`)
- **Authority**: Direct manager of client design systems, web dashboards, state management, and accessibility.
- **Direct Subordinates**: UI/UX Engineer, Frontend Engineer, Dashboard Engineer, API Integration Engineer, Accessibility Engineer, Frontend Test Engineer.
- **Responsibilities**:
  - Translates visual specifications and API contracts into modular UI components and data visualizations.
  - Coordinates parallel UI component drafting, state wiring, chart rendering, and WCAG 2.1 AA audits.
  - Enforces frontend test suites (unit, integration, visual regression) before reporting to Master Orchestrator.

### 2.3 Level 2: Specialized Engineering Agents
Every specialized agent operates strictly within its designated file boundaries and domain scope. Cross-domain alterations without orchestrator delegation are prohibited.

---

## 3. Agent Roster & Domain Matrix

| Agent Identifier | Category | File Authority / Scope | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| `master-orchestrator` | Executive | `.agents/tasks/*`, `agent_runtime/master/*` | Epic decomposition, cross-team sync, release sign-off |
| `backend-orchestrator` | Domain Lead | `backend/*`, `agent_runtime/backend/*` | Backend squad work distribution, pipeline validation |
| `frontend-orchestrator`| Domain Lead | `frontend/*`, `agent_runtime/frontend/*` | Frontend squad work distribution, UI validation |
| `api-engineer` | Backend | `backend/src/gitpulse/api/*` | FastAPI routes, dependency injection, OpenAPI schemas |
| `ingestion-engineer` | Backend | `backend/src/gitpulse/ingestion/*` | GitHub REST/GraphQL collectors, rate-limit handlers |
| `database-engineer` | Backend | `backend/src/gitpulse/storage/*`, `backend/migrations/*` | Supabase (Postgres) / ClickHouse schemas, Alembic migrations, indexes |
| `kafka-engineer` | Backend | `backend/src/gitpulse/ingestion/kafka_producer.py`, Kafka topics | Topic topologies, partitioning, serialization, avro/json |
| `spark-engineer` | Backend | `backend/src/gitpulse/services/processor.py`, Spark jobs | PySpark stream aggregation, watermarking, windowing |
| `airflow-engineer` | Backend | `backend/dags/*`, batch scheduling | Data pipelines, DAG orchestration, SLA monitoring |
| `dbt-engineer` | Backend | `backend/dbt/*`, transform models | Analytical views, dimensional models, staging/mart layers |
| `backend-test-engineer`| Backend | `backend/tests/*` | Pytest fixtures, unit/mock tests, integration test runs |
| `backend-security-engineer`| Backend | Security policies, auth middleware, scan configs | OWASP auditing, secrets protection, token validation |
| `ui-ux-engineer` | Frontend | `frontend/src/components/design-system/*`, styling | Wireframes, color tokens, typography, component specs |
| `frontend-engineer` | Frontend | `frontend/src/components/*`, `frontend/src/App.tsx` | React 18+ component trees, layout structure, hooks |
| `dashboard-engineer` | Frontend | `frontend/src/components/charts/*`, `frontend/src/pages/*` | ECharts/Recharts, commit velocity heatmaps, PR funnels |
| `api-integration-engineer`| Frontend | `frontend/src/services/*`, query hooks | Axios/Fetch clients, React Query, WebSocket client, caching |
| `accessibility-engineer` | Frontend | A11y tests, ARIA tags, contrast tokens | WCAG 2.1 AA compliance, keyboard navigation, axe scans |
| `frontend-test-engineer`| Frontend | `frontend/tests/*`, `*.test.tsx` | Vitest, React Testing Library, Playwright E2E suites |
| `software-architect` | Shared | System architecture, schema contracts, RFCs | End-to-end design, data integrity, architecture review |
| `integration-engineer` | Shared | E2E contract verification, proxy configs | Backend-Frontend bridge, mocking, cross-service smoke |
| `devops-engineer` | Shared | `docker-compose.yml`, `Makefile`, CI/CD | Container orchestration, environment isolation, deploy |
| `independent-code-reviewer`| Shared | All pull requests & file diffs | Objective code review, linting, complexity checks |

---

## 4. Communication & Delegation Protocol

1. **Top-Down Delegation**:
   - Master Orchestrator creates task record in `.agents/tasks/current-task.md`.
   - Domain Orchestrators pull active task, decompose into sub-tasks, and generate Agent Execution Tickets.
   - Engineering Agents receive tickets containing:
     - `TaskID`: Unique identifier (e.g., `BE-TASK-104`).
     - `Context`: Directives, references, and preconditions.
     - `FileScope`: Exact files allowed for modification.
     - `AcceptanceCriteria`: Testable verification rules.

2. **Bottom-Up Reporting**:
   - Upon completion, Engineering Agents generate an Execution Receipt containing modified files, unit test results, and potential warnings.
   - Domain Orchestrator validates the receipt, runs integration checks, and updates state in `agent_runtime/shared/task_store.py`.
   - Domain Orchestrator submits completion report to Master Orchestrator.

3. **Cross-Domain Communication (Contract-First)**:
   - Backend and Frontend agents never communicate directly via informal channels.
   - Cross-domain interactions require an explicit contract stored in `.agents/tasks/contracts.md`.
   - Software Architect approves contract revisions. Integration Engineer executes automated contract tests.

---

## 5. Quality Gates & Enforcement

No task may transition to `DONE` without satisfying all four gates:

1. **Gate 1: Static Analysis & Linting**:
   - Python: `ruff check backend/ agent_runtime/`, `black --check backend/`, `mypy backend/`
   - TypeScript: `eslint frontend/src`, `tsc --noEmit`
2. **Gate 2: Automated Testing**:
   - Backend: Unit & integration test suite passing with >= 85% branch coverage.
   - Frontend: Vitest suites passing with 100% assertions green.
3. **Gate 3: Security & Secrets Audit**:
   - No hardcoded API keys, tokens, or plaintext credentials.
   - Bandit/Trivy scans report zero High or Critical vulnerabilities.
4. **Gate 4: Independent Peer Review**:
   - Independent Code Reviewer verifies compliance with `.agents/policies/coding-standards.md` and `.agents/policies/file-ownership.md`.

---

## 6. Directory Layout & Artifact Map

```
gitpulse/
├── AGENTS.md                  # This master governance document
├── README.md                  # Developer & architecture onboarding
├── docker-compose.yml         # Multi-service infrastructure
├── pyproject.toml             # Python packaging & dependencies
├── Makefile                   # Orchestration & developer CLI
│
├── .agents/                   # Agent Personas, Policies, Workflows
│   ├── master-orchestrator.md # L0 Coordinator
│   ├── orchestrators/         # L1 Domain Leads
│   ├── backend/               # L2 Backend Engineers
│   ├── frontend/              # L2 Frontend Engineers
│   ├── shared/                # Cross-Cutting Specialists
│   ├── workflows/             # Standard Operating Procedures
│   ├── policies/              # Governance & Quality Policies
│   └── tasks/                 # Current Ledger & Interface Contracts
│
├── agent_runtime/             # Programmatic Python Orchestration Engine
│   ├── master/                # Master state graph & router
│   ├── backend/               # Backend sub-graph orchestrator
│   ├── frontend/              # Frontend sub-graph orchestrator
│   ├── shared/                # State store, telemetry, permissions
│   └── tools/                 # Execution tools (git, fs, test, docker)
│
├── backend/                   # GitPulse Core Data Engineering & API
│   ├── src/gitpulse/          # FastAPI, Ingestion, Kafka, Storage
│   └── tests/                 # Backend pytest test suite
│
└── frontend/                  # GitPulse Modern React Dashboard
    ├── src/                   # Components, Pages, Services, Visualizations
    └── tests/                 # Vitest / React Testing Library suites
```
