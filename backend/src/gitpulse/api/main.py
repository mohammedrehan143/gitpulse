"""FastAPI Application Entry Point for GitPulse Backend."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.gitpulse.api.routes import router
from backend.src.gitpulse.common.config import settings

app = FastAPI(
    title="GitPulse Analytics API",
    description="High-Throughput GitHub Activity Analytics & Velocity Serving Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(router)


def start() -> None:
    """Entry point to launch the uvicorn server."""
    uvicorn.run(
        "backend.src.gitpulse.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


if __name__ == "__main__":
    start()
