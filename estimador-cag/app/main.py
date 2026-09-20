from fastapi import FastAPI

from app.routers import estimations

app = FastAPI(
    title="Estimador CAG API",
    description=(
        "CAG-based (Cache/Context-Augmented Generation) estimator for software "
        "development effort.\n\n"
        "It injects a fixed set of example estimations into the LLM context and "
        "estimates new work by analogy.\n\n"
        "## Endpoints\n\n"
        "- `POST /api/v1/estimate` — generate an effort estimation from a "
        "video-call transcription\n"
        "- `GET /health` — liveness check"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}
