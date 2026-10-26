# GitPulse Cloud Deployment Guide: Vercel & Render

This guide outlines the production deployment of GitPulse:
- **Frontend**: [Vercel](https://vercel.com) (React 18 + TypeScript + Vite SPA)
- **Backend**: [Render](https://render.com) (FastAPI + Uvicorn + SQLAlchemy Async)

---

## 1. Architecture & Network Topology

```
  ┌─────────────────────────────────┐
  │         User Browser            │
  └───────────────┬─────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼ (HTTPS)           ▼ (HTTPS & WSS)
┌───────────────┐   ┌───────────────────────────────┐
│ Vercel        │   │ Render                        │
│ Frontend SPA  │   │ FastAPI Analytics API         │
│ (*.vercel.app)│   │ (*.onrender.com)              │
└───────────────┘   └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ Supabase / Render PostgreSQL  │
                    │ (or SQLite cloud storage)     │
                    └───────────────────────────────┘
```

---

## 2. Deploying the Backend to Render

### Option A: 1-Click Blueprint Deployment (`render.yaml`)

1. Push your GitPulse repository to GitHub / GitLab.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Connect your repository. Render automatically reads [`render.yaml`](../render.yaml) from the repo root.
4. Render will configure the Web Service with the following defaults:
   - **Service Name**: `gitpulse-api`
   - **Runtime**: Python 3.11.9
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && pip install -e .`
   - **Start Command**: `uvicorn backend.src.gitpulse.api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/v1/health`
5. Click **Apply**.

---

### Option B: Manual Web Service Creation

If you prefer configuring the Web Service manually:

1. Click **New +** -> **Web Service** in Render.
2. Select your GitPulse repository.
3. Configure the settings:
   - **Name**: `gitpulse-api`
   - **Region**: Oregon (or your preferred region)
   - **Branch**: `main`
   - **Root Directory**: *(Leave blank)*
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && pip install -e .`
   - **Start Command**: `uvicorn backend.src.gitpulse.api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/v1/health`
4. Under **Advanced**, add the following **Environment Variables**:

| Variable | Recommended Value | Notes |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Enforces Python 3.11 runtime |
| `PYTHONPATH` | `.` | Ensures imports resolve correctly |
| `GITPULSE_ENV` | `production` | Disables hot reload in prod |
| `LOG_LEVEL` | `INFO` | Standard application logging |
| `DATABASE_URL` | `sqlite+aiosqlite:///./gitpulse.db` *(or PostgreSQL URL)* | Supports Render Postgres, Supabase, Neon |
| `CORS_ORIGINS` | `*` *(or your Vercel URL)* | Allows cross-origin API calls from Vercel |
| `GITHUB_TOKEN` | `ghp_...` *(your token)* | For higher GitHub API rate limits |
| `GROQ_API_KEY` | `gsk_...` *(optional)* | Enables AI insights via Groq |
| `AUTO_DISCOVER_REPOSITORIES` | `true` | Auto-detects repositories on startup |

> [!TIP]
> **PostgreSQL Auto-Dialect Conversion**:
> If you attach a Render PostgreSQL database or paste a connection URL from Supabase / Neon, it typically begins with `postgres://` or `postgresql://`. GitPulse automatically converts this to `postgresql+asyncpg://` so that async SQLAlchemy connects cleanly with zero configuration.

5. Click **Create Web Service**.
6. Note your Render URL (e.g., `https://gitpulse-api.onrender.com`).

---

## 3. Deploying the Frontend to Vercel

You can deploy the frontend from either the repository root or the `frontend` subfolder. Both workflows are pre-configured.

### Option A: Monorepo Root Deployment (Recommended)

1. In the [Vercel Dashboard](https://vercel.com/dashboard), click **Add New...** -> **Project**.
2. Import your GitPulse repository.
3. Leave **Root Directory** as `./` (default).
4. Vercel automatically detects the root [`package.json`](../package.json) and [`vercel.json`](../vercel.json):
   - **Build Command**: `npm --prefix frontend install && npm --prefix frontend run build`
   - **Output Directory**: `frontend/dist`
5. Under **Environment Variables**, add:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://gitpulse-api.onrender.com` | Your deployed Render backend URL |
| `VITE_WS_BASE_URL` | `wss://gitpulse-api.onrender.com/api/v1/ws` | *(Optional)* Auto-derived from `VITE_API_BASE_URL` if omitted |

6. Click **Deploy**.

---

### Option B: Subdirectory Deployment (`frontend`)

1. When importing the project in Vercel, click **Edit** next to **Root Directory**.
2. Select the `frontend` directory.
3. Vercel automatically detects [`frontend/vercel.json`](../frontend/vercel.json) and `vite`:
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add the same Environment Variables (`VITE_API_BASE_URL`).
5. Click **Deploy**.

---

## 4. Cross-Origin (CORS) & WebSockets

### CORS Setup
The FastAPI backend in `backend/src/gitpulse/api/main.py` is configured with:
- Wildcard support for `settings.CORS_ORIGINS`
- Dynamic origin matching for `r"https://.*\.vercel\.app"` (covers production and preview URLs)
- Dynamic origin matching for `r"https://.*\.onrender\.com"`

You do not need to update backend CORS every time Vercel generates a new preview deployment.

### Real-Time WebSockets
The frontend's API layer (`frontend/src/services/api.ts`) automatically transforms your `VITE_API_BASE_URL`:
- `https://gitpulse-api.onrender.com` -> `wss://gitpulse-api.onrender.com/api/v1/ws/repos/...`
- Handles trailing slashes, relative paths, and missing `/api/v1` suffixes automatically.

---

## 5. Verification Checklist

Once both services are deployed:

1. **Verify Backend Health**:
   ```bash
   curl https://gitpulse-api.onrender.com/
   # Returns: {"status":"online","service":"GitPulse Analytics API","version":"0.1.0",...}

   curl https://gitpulse-api.onrender.com/api/v1/health
   # Returns: {"status":"HEALTHY","version":"0.1.0",...}
   ```

2. **Verify Interactive API Docs**:
   Open `https://gitpulse-api.onrender.com/docs` in your browser to verify OpenAPI Swagger documentation.

3. **Verify Frontend**:
   Open your Vercel deployment URL (e.g., `https://gitpulse.vercel.app`):
   - The repository selector should populate with discovered repositories (`apache/spark`, `fastapi/fastapi`, `facebook/react`).
   - Velocity metrics and charts should render without CORS or console errors.
   - The WebSocket connection status in DevTools Network tab should indicate `101 Switching Protocols` to `wss://gitpulse-api.onrender.com/api/v1/ws/repos/...`.
