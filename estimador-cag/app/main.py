from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import estimations


def configure_logging() -> None:
    """Set up structlog: JSON in production, human-readable in development."""
    settings = get_settings()
    if settings.app_env == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    configure_logging()
    log = structlog.get_logger()
    settings = get_settings()
    log.info("application_started", environment=settings.app_env)
    yield
    log.info("application_shutdown")


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in get_settings().cors_allow_origins.split(",") if origin.strip()]


app = FastAPI(
    title="Estimador CAG API",
    description=(
        "CAG-based (Cache/Context-Augmented Generation) estimator for software "
        "development effort.\n\n"
        "It injects a fixed set of example estimations into the LLM context and "
        "estimates new work by analogy. Responses are cached in Redis by exact "
        "prompt match, and a LiteLLM router falls back to a secondary provider.\n\n"
        "## Endpoints\n\n"
        "- `POST /api/v1/estimate` — generate an effort estimation from a "
        "video-call transcription\n"
        "- `POST /api/v1/estimate/stream` — stream the estimation as Server-Sent Events\n"
        "- `GET /health` — liveness check"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "estimations",
            "description": "Software effort estimation endpoints",
        },
        {
            "name": "health",
            "description": "Service health and liveness checks",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(estimations.router, prefix="/api/v1")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
    }
