# Workflow: Release & Deployment SOP

## 1. Overview
The Release Workflow governs packaging, validation, tagging, and deployment of GitPulse across staging and production environments.

## 2. Release Prerequisites
A release candidate may only be initiated when:
1. All planned milestone tasks in `.agents/tasks/backlog.md` are marked `DONE`.
2. No outstanding `BLOCKED` or `VERIFICATION_FAILED` tasks remain in `.agents/tasks/current-task.md`.
3. All 4 Quality Gates are fully satisfied across backend and frontend repositories.

## 3. Release Sequence

### Step 1: Pre-Release Audit
- `master-orchestrator` initiates release verification ticket.
- `independent-code-reviewer` performs final codebase diff review.
- `backend-security-engineer` confirms vulnerability scan reports clean.

### Step 2: Build & Container Packaging
- `devops-engineer` triggers container builds:
  ```bash
  docker compose build --no-cache
  ```
- Verifies that Docker images for backend, frontend, and data processors build with zero errors.

### Step 3: Migration Dry-Run
- `database-engineer` executes migration dry-run on staging PostgreSQL instance:
  ```bash
  alembic upgrade head
  ```

### Step 4: End-to-End Smoke Test
- `integration-engineer` executes full smoke test suite against staging environment.

### Step 5: Git Tagging & Changelog
- Tag repository with semantic version (e.g. `v1.0.0`).
- Generate CHANGELOG.md summarizing delivered epics and bug fixes.
- Master Orchestrator publishes executive sign-off report.
