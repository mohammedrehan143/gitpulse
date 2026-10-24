# Workflow: Bug Fixing SOP

## 1. Overview
This SOP defines the rapid triage, reproduction, isolation, fix verification, and regression prevention protocol for defects in GitPulse.

## 2. Protocol Steps

### Step 1: Reproduction & Triage (Master Orchestrator)
1. Ingest bug report (error log, stack trace, failed assertion, or user symptom).
2. Classify domain impact:
   - Backend defect -> `backend-orchestrator`
   - Frontend defect -> `frontend-orchestrator`
   - Cross-domain / contract mismatch -> `integration-engineer` + Master
3. Mark task as `IN_PROGRESS` with high priority in `.agents/tasks/current-task.md`.

### Step 2: Failing Test First (Test Engineers)
1. Before any code is touched, author a minimal failing test reproducing the exact failure mode:
   - Backend: Pytest regression test in `backend/tests/` reproducing failure.
   - Frontend: Vitest test in `frontend/tests/` reproducing failure.
2. Confirm test fails in red state (`FAILED`).

### Step 3: Targeted Remediation (Specialist Engineer)
1. Domain Orchestrator assigns the appropriate specialist based on root cause.
2. Specialist applies minimal, targeted surgical fix strictly within authorized file scope.
3. Verify previously failing test now passes in green state (`PASSED`).

### Step 4: Regression & Quality Check
1. Run full test suite to guarantee zero regression:
   ```bash
   pytest backend/tests/
   npm --prefix frontend test
   ```
2. Verify all 4 Quality Gates pass.

### Step 5: Independent Review & Closure
1. `independent-code-reviewer` validates that fix addresses the root cause without side effects.
2. Master Orchestrator updates task to `DONE` and documents the bugfix in the execution log.
