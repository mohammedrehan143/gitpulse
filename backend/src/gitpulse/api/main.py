"""FastAPI Application Entry Point for GitPulse Backend."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.gitpulse.api.routes import router
from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.services.repository_service import RepositoryService
from backend.src.gitpulse.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup database initialization and repository discovery."""
    logger.info("Initializing GitPulse database tables...")
    try:
        await init_db()
    except Exception as exc:
        logger.warning("Database initialization warning: %s", exc)

    logger.info("Initializing GitPulse repository inventory...")
    repo_service = RepositoryService()
    try:
        await repo_service.sync_repositories()
    except Exception as exc:
        logger.warning("Initial repository sync encountered error: %s", exc)

    periodic_task = None
    if settings.AUTO_DISCOVER_REPOSITORIES and settings.REPO_DISCOVERY_INTERVAL_MINUTES > 0:

        async def periodic_discovery():
            interval_seconds = settings.REPO_DISCOVERY_INTERVAL_MINUTES * 60
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    logger.info("Running periodic repository discovery refresh...")
                    await repo_service.sync_repositories()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Periodic repository discovery error: %s", exc)

        periodic_task = asyncio.create_task(periodic_discovery())

    yield

    if periodic_task:
        periodic_task.cancel()
        try:
            await periodic_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="GitPulse Analytics API",
    description="High-Throughput GitHub Activity Analytics & Velocity Serving Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware - permits configured origins, wildcard, and Vercel/Render preview/prod domains
cors_origins = (
    settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
async def root():
    """Root operational health and API discovery endpoint."""
    return {
        "status": "online",
        "service": "GitPulse Analytics API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "api_base": "/api/v1",
        "health_check": "/api/v1/health",
    }


@app.get("/health", tags=["system"])
async def system_health():
    """Top-level health check endpoint for cloud monitoring."""
    return {"status": "HEALTHY", "version": "0.1.0"}


# Include API Router
app.include_router(router)


def start() -> None:
    """Entry point to launch the uvicorn server."""
    port = int(os.environ.get("PORT", str(settings.server_port)))
    app_target = (
        "backend.src.gitpulse.api.main:app" if settings.GITPULSE_ENV == "development" else app
    )
    uvicorn.run(
        app_target,
        host="0.0.0.0",
        port=port,
        reload=settings.GITPULSE_ENV == "development",
    )


if __name__ == "__main__":
    start()
