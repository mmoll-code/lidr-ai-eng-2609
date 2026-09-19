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

## Project structure

```
app/
├── main.py            # FastAPI app + routing
├── config.py          # Settings loaded from .env
├── routers/
│   └── estimations.py # Estimation endpoints
├── services/
│   └── llm_service.py # LLM provider integration
└── context/
    └── examples.py    # Static example estimations (CAG context)
```
