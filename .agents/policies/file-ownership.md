# Policy: File Ownership & Access Boundaries

## 1. Ownership Principles
1. **Single-Writer Rule**: Only one agent may hold write permission for a specific file during any execution phase.
2. **Boundary Sandboxing**: Domain agents may not write to files outside their designated domain.
3. **Escalation on Conflict**: If an agent requires modifications outside its authorized scope, it must return a handoff requesting the relevant domain orchestrator or Master Orchestrator to delegate that portion.

## 2. Global Ownership Matrix

| Directory / File Path | Permitted Writers | Read-Only Access |
| :--- | :--- | :--- |
| `.agents/tasks/*` | `master-orchestrator`, `software-architect` | All Agents |
| `.agents/policies/*` | `master-orchestrator`, `software-architect` | All Agents |
| `backend/src/gitpulse/api/*` | `api-engineer` | `backend-orchestrator`, `backend-test-engineer` |
| `backend/src/gitpulse/ingestion/*` | `ingestion-engineer`, `kafka-engineer` | `backend-orchestrator`, `backend-test-engineer` |
| `backend/src/gitpulse/storage/*` | `database-engineer` | `backend-orchestrator`, `api-engineer` |
| `backend/src/gitpulse/services/*` | `spark-engineer`, `api-engineer` | `backend-orchestrator` |
| `backend/src/gitpulse/common/*` | `backend-security-engineer`, `backend-orchestrator` | All Backend Agents |
| `backend/migrations/*` | `database-engineer` | `backend-orchestrator` |
| `backend/tests/*` | `backend-test-engineer` | `backend-orchestrator` |
| `frontend/src/components/*` | `frontend-engineer`, `ui-ux-engineer` | `frontend-orchestrator`, `frontend-test-engineer` |
| `frontend/src/charts/*` | `dashboard-engineer` | `frontend-orchestrator`, `frontend-test-engineer` |
| `frontend/src/services/*` | `api-integration-engineer` | `frontend-orchestrator`, `frontend-engineer` |
| `frontend/src/types/*` | `api-integration-engineer`, `software-architect` | All Frontend Agents |
| `frontend/tests/*` | `frontend-test-engineer` | `frontend-orchestrator` |
| `data_platform/airflow/*` | `airflow-engineer` | `backend-orchestrator` |
| `data_platform/spark/*` | `spark-engineer` | `backend-orchestrator` |
| `data_platform/kafka/*` | `kafka-engineer` | `backend-orchestrator` |
| `data_platform/dbt/*` | `dbt-engineer` | `backend-orchestrator` |
| `infra/*`, `docker-compose.yml`, `Makefile` | `devops-engineer` | All Agents |
| `docs/*` | `software-architect` | All Agents |
| `agent_runtime/*` | `master-orchestrator`, `software-architect` | All Agents |

## 3. Enforcement Engine
The programmatic runtime in `agent_runtime/shared/permissions.py` enforces this table at runtime. Any filesystem tool call attempting unauthorized file writes raises a `PermissionDeniedError` and immediately records an audit fault in telemetry.
