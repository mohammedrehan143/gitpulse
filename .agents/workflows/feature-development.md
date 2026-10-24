# Workflow: Feature Development SOP

## 1. Overview
This Standard Operating Procedure (SOP) governs the end-to-end lifecycle of new feature development across the GitPulse multi-agent hierarchy.

```text
[User Prompt / Epic]
        │
        ▼
[Master Orchestrator] ──► Intake, Decompose, Check Task Store
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼
[Software Architect]  [DevOps Engineer]      [Contract Draft]
   (ADR / Specs)       (Infra / Topics)     (.agents/tasks/contracts.md)
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────┐
        │  Wave 1: Backend Domain Execution           │
        │  (backend-orchestrator)                     │
        │  DB Models -> Ingestion -> Kafka -> API     │
        └──────────────────────┬──────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────┐
        │  Wave 2: Frontend Domain Execution          │
        │  (frontend-orchestrator)                    │
        │  API Hooks -> Components -> Charts -> A11y  │
        └──────────────────────┬──────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────┐
        │  Wave 3: Verification & Review              │
        │  - integration-engineer (E2E Contract test) │
        │  - backend & frontend test suites (>=85%)   │
        │  - independent-code-reviewer (Gate 4 sign)  │
        └──────────────────────┬──────────────────────┘
                               ▼
                    [Master Orchestrator]
                   (Mark DONE & Report)
```

## 2. Step-by-Step Procedure

### Phase 1: Intake & Decomposition
1. **Master Orchestrator** reads user specification.
2. Creates task entry in `.agents/tasks/current-task.md` with state `BACKLOG` -> `READY`.
3. If cross-cutting contracts are impacted:
   - Invokes `software-architect` to formalize request/response schema in `.agents/tasks/contracts.md`.

### Phase 2: Backend Implementation Wave
1. Master Orchestrator delegates backend packet to `backend-orchestrator`.
2. Backend Orchestrator sets subtask to `IN_PROGRESS` and sequences:
   - `database-engineer`: Schema migrations.
   - `kafka-engineer`: Topic configs and serializers.
   - `ingestion-engineer` & `spark-engineer`: Pipeline processors.
   - `api-engineer`: REST endpoints and Pydantic schemas.
   - `backend-test-engineer` & `backend-security-engineer`: Testing & audits.
3. Backend Orchestrator submits completion receipt to Master Orchestrator.

### Phase 3: Frontend Implementation Wave
1. Master Orchestrator delegates frontend packet to `frontend-orchestrator`.
2. Frontend Orchestrator sets subtask to `IN_PROGRESS` and sequences:
   - `api-integration-engineer`: Typed hooks based on verified contract.
   - `ui-ux-engineer` & `frontend-engineer`: Layouts and components.
   - `dashboard-engineer`: Charts and visualizations.
   - `accessibility-engineer`: WCAG 2.1 AA keyboard/contrast review.
   - `frontend-test-engineer`: Vitest and component tests.
3. Frontend Orchestrator submits completion receipt to Master Orchestrator.

### Phase 4: Integration, Audit & Sign-off
1. `integration-engineer` runs cross-domain end-to-end contract validation.
2. `independent-code-reviewer` reviews git diff against quality gates.
3. Master Orchestrator transitions task state to `DONE` and outputs final delivery report.
