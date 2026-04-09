"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings, validate_settings
from app.core.database import engine
from app.core.logging import setup_logging
from app.core.redis import redis_client
from app.core.storage import ensure_buckets, s3_client

logger = structlog.stdlib.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    validate_settings()
    logger.info("starting", env=settings.app_env)

    # Sentry
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_sample_rate,
            before_send=_sentry_before_send,
        )

    # S3 buckets
    try:
        ensure_buckets()
    except Exception as exc:
        logger.warning("minio_buckets_init_failed", error=str(exc))

    yield

    # Shutdown
    await redis_client.aclose()
    await engine.dispose()
    logger.info("shutdown_complete")


def _sentry_before_send(event, hint):
    """Filter PII from Sentry events."""
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        for key in list(headers.keys()):
            if key.lower() in ("authorization", "cookie", "x-api-key"):
                headers[key] = "[FILTERED]"
    return event


app = FastAPI(
    title="AI Fitness Coaching",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

# --- Routers ---
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# --- Health Check ---
@app.get("/health")
async def health_check():
    checks: dict[str, str] = {}

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # MinIO
    try:
        s3_client.list_buckets()
        checks["minio"] = "ok"
    except Exception:
        checks["minio"] = "error"

    # OpenAI status from Redis cache
    try:
        openai_status = await redis_client.get("openai_status")
        checks["openai"] = openai_status or "ok"
    except Exception:
        checks["openai"] = "unknown"

    if checks.get("database") == "error" or checks.get("redis") == "error":
        status = "down"
        http_status = 503
    elif checks.get("openai") in ("degraded", "error"):
        status = "degraded"
        http_status = 200
    else:
        status = "healthy"
        http_status = 200

    return JSONResponse(
        status_code=http_status,
        content={"status": status, "checks": checks, "version": "1.0.0"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
