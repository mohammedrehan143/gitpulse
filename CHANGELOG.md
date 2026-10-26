# GitPulse Changelog

All notable changes to the GitPulse Engineering Intelligence Platform are documented in this file.

---

## [v1.0.0] - 2026-10-26 — Production Cloud Release & UI Overhaul

### Added
- **Multi-Cloud Deployment**:
  - Render Blueprint (`render.yaml`) with Python 3.11.9 runtime pinning (`.python-version`), Uvicorn entry points, and health checks.
  * Dual-mode Vercel configuration supporting both repository root monorepo and `frontend` subdirectory setups with `.vercelignore` and root `package.json`.
  * Comprehensive cloud deployment guide in `docs/DEPLOYMENT.md`.
- **Engineering Intelligence UI & Groq AI Velocity Copilot**:
  * Dark glassmorphic design system overhaul on deep canvas `#090d16` with ambient glow and translucent cards.
  * `AIInsightsCard`: Groq AI Copilot powered by `openai/gpt-oss-120b` for instant cycle time diagnosis and bottleneck detection.
  * Real-time WebSocket connection status beacon (`Live Feed Connected` / `Stream Paused`).
  * Searchable and filterable repository explorer supporting 37+ automatically discovered repositories plus ad-hoc repository tracking.
  * Gradient bar charts for daily commit velocity with hover tooltips and peak velocity highlights.
  * Dual-bar PR throughput chart comparing Opened vs Merged with clearance rate calculation.
  * Real-time activity stream table with WebSocket live event prepending, event-type colored badges, and actor avatars.
- **Relational Storage & Schema Integrity**:
  * Dual SQLite and PostgreSQL autoincrement primary keys using SQLAlchemy `BigInteger().with_variant(Integer, "sqlite")`.
  * Automatic PostgreSQL async dialect adapter converting `postgres://` and `postgresql://` URIs to `postgresql+asyncpg://`.
  * Automatic fallback from unconfigured database placeholder templates to local SQLite.
  * Direct database querying in `/api/v1/repos/{owner}/{repo}/events` with synthetic fallback for un-ingested repos.

### Changed
- Refactored `Dashboard.tsx` to subscribe to live WebSocket feeds and support dynamic timeframe filtering (`7D`, `14D`, `30D`, `90D`).
- Upgraded CORS middleware with dynamic regex matching across all Vercel edge preview/production domains (`*.vercel.app`) and Render endpoints.

### Verified
- 55/55 Pytest unit & integration tests green.
- 8/8 Vitest frontend test suites green.
- Production TypeScript bundle compiled with 0 errors.
- Clean passes on `ruff check` and `black --check` across 50 Python modules.

---

## [v0.9.0] - 2026-10-24 — Native Scheduler & Ingestion Streamlining

### Added
- Native asyncio Python scheduler (`backend/src/gitpulse/scheduler.py`) running recurring 60-minute ingestion cycles with concurrency locking.
- Automatic GitHub repository discovery via authenticated `/user/repos` endpoint.
- Direct persistence pipeline into Supabase relational storage (`GitHubEvent`, `Repository`).
