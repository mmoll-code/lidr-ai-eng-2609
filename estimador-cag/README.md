# Estimador CAG

CAG-based (Cache/Context-Augmented Generation) estimator for software development effort.

It injects a fixed set of example estimations into the LLM context and estimates new work by analogy.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
cp .env.example .env  # then fill in your API keys
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health`

## Estimate endpoint

`POST /api/v1/estimate` — generate a software estimation from a video-call transcription.

**Request**

```json
{
  "transcription": "En la reunión con el cliente se discutió la necesidad de..."
}
```

**Response**

```json
{
  "estimation": "## Estimación: ...\n\n### Desglose de tareas:\n...",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150
  },
  "estimated_cost_usd": 0.000045,
  "generated_at": "2026-03-22T13:00:00+00:00"
}
```

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"transcription": "En la reunion con el cliente se discutio..."}'
```

OpenAPI docs: `http://localhost:8000/docs`

## Project structure

```
app/
├── main.py            # FastAPI app + routing
├── config.py          # Settings loaded from .env
├── routers/
│   └── estimations.py # Estimation endpoints
├── schemas/
│   └── estimations.py # Request/response Pydantic models
├── services/
│   ├── llm_service.py # LLM provider integration
│   └── pricing.py     # Approximate USD cost estimation
└── context/
    └── examples.py    # Static example estimations (CAG context)
```
