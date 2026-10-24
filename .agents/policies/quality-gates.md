# Policy: Quality Gates & Verification Standards

## 1. Overview
No task, pull request, or release candidate in GitPulse may transition to `DONE` without systematically passing all four Quality Gates. Quality gates are evaluated programmatically and validated by the `independent-code-reviewer` and `master-orchestrator`.

```text
       ┌───────────────┐
       │ Work Complete │
       └───────┬───────┘
               ▼
┌───────────────────────────────┐
│ Gate 1: Static Analysis       │ ──► [FAIL] ──► VERIFICATION_FAILED
│ (ruff, black, mypy, tsc)      │
└──────────────┬────────────────┘
               ▼ [PASS]
┌───────────────────────────────┐
│ Gate 2: Automated Testing     │ ──► [FAIL] ──► VERIFICATION_FAILED
│ (pytest, vitest, cov >= 85%)  │
└──────────────┬────────────────┘
               ▼ [PASS]
┌───────────────────────────────┐
│ Gate 3: Security & Secrets    │ ──► [FAIL] ──► BLOCKED / VERIFICATION_FAILED
│ (detect-secrets, bandit)      │
└──────────────┬────────────────┘
               ▼ [PASS]
┌───────────────────────────────┐
│ Gate 4: Independent Review    │ ──► [FAIL] ──► VERIFICATION_FAILED
│ (independent-code-reviewer)   │
└──────────────┬────────────────┘
               ▼ [PASS]
       ┌───────────────┐
       │  Status: DONE │
       └───────────────┘
```

---

## 2. Gate 1: Static Analysis & Linting
- **Python**:
  - `ruff check backend/ agent_runtime/` reports zero errors.
  - `black --check backend/ agent_runtime/` reports zero formatting diffs.
  - `mypy backend/ agent_runtime/` reports zero typing errors.
- **TypeScript**:
  - `tsc --noEmit` reports zero compile-time errors.
  - `eslint frontend/src/` reports zero errors.

## 3. Gate 2: Automated Testing & Coverage
- **Backend**:
  - `pytest backend/tests/ --cov=backend/src --cov-fail-under=85` runs with 100% assertions green and minimum 85% branch coverage.
- **Frontend**:
  - `npm --prefix frontend test` runs with 100% assertions green.
- **Agent Runtime**:
  - `pytest agent_runtime/tests/` passes with 100% green tests.

## 4. Gate 3: Security & Secrets Audit
- **Zero Secrets**: Automated scanner confirms no API keys, tokens, or plaintext credentials in diffs.
- **Static Security**: Bandit/Trivy scans report zero High or Critical vulnerabilities.
- **Signature Verification**: All webhook intake routes include HMAC validation logic.

## 5. Gate 4: Independent Peer Review
- Conducted strictly by `independent-code-reviewer`.
- Validates architectural compliance, clean abstractions, boundary preservation, and absence of regressions.
- Explicit sign-off receipt written to `.agents/tasks/current-task.md`.

---

## 6. Failure Recovery & Retry Protocol
- If any gate fails:
  1. Task state immediately transitions to `VERIFICATION_FAILED`.
  2. Failure logs and exact error messages are recorded in `agent_runtime/shared/task_store.py`.
  3. Bounded retry counter increments (Max retries: 3).
  4. If retries exceed 3, task transitions to `BLOCKED` and triggers escalation to Master Orchestrator.
