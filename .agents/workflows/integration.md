# Workflow: Integration & Contract Verification SOP

## 1. Purpose
Ensures that backend APIs and data streams seamlessly satisfy the interface, data model, and latency expectations of frontend components and downstream analytics sinks.

## 2. Integration Pipeline Flow

```text
[Backend API & Stream Ready]
             │
             ▼
[Contract Verification Phase]
   - Validate OpenAPI JSON schema against docs/api-contracts.md
   - Verify TypeScript client interfaces in frontend/src/types/
             │
             ▼
[Integration Test Execution]
   - integration-engineer executes mock/live end-to-end suite
   - Verifies HTTP status codes, pagination headers, and payload structures
             │
             ▼
[Outcome Decision]
   ├── PASS ──► Release to Frontend Orchestrator / User Acceptance
   └── FAIL ──► Transition to VERIFICATION_FAILED
                Emit blocker report to Master Orchestrator
```

## 3. Discrepancy Arbitration
When a contract mismatch is identified:
1. `integration-engineer` flags exact mismatch (e.g. `Field 'commit_count' expected integer, received null`).
2. Task state transitions to `VERIFICATION_FAILED`.
3. `master-orchestrator` convenes `software-architect`, `backend-orchestrator`, and `frontend-orchestrator`.
4. The contract in `.agents/tasks/contracts.md` is updated and signed off before code remediation begins.
