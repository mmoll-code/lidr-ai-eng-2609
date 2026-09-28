# Estimador CAG

CAG-based (Cache/Context-Augmented Generation) estimator for software development effort.

It injects a fixed set of example estimations into the LLM context and estimates new work by analogy.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose, when running the API with Redis
- An OpenAI or Anthropic API key

## Setup

```bash
uv sync
cp .env.example .env  # then fill in your API keys
```

## Run

Local API (needs Redis on `localhost:6379`):

```bash
uv run uvicorn app.main:app --reload
```

Full stack, including Redis:

```bash
docker compose up --build
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
  "generated_at": "2026-03-22T13:00:00+00:00",
  "finish_reason": "stop",
  "preprocessing": "none",
  "cache_hit": false,
  "latency_ms": 840,
  "validation": {
    "score": 1.0,
    "issues": []
  }
}
```

Optional request knobs: `preprocessing` (`none`, `inline_cleaning`, `two_phase`), `example_format` (`markdown`, `json`, `narrative`), `num_examples`, `use_examples`, `model`, `max_tokens`, `thinking_budget`, and `evaluate`.

Sending the same prompt twice returns `"cache_hit": true` on the second response while the cached text is still valid.

```bash
curl -s localhost:8000/api/v1/estimate -H 'Content-Type: application/json' \
  -d '{"transcription": "We need a small CRM with auth, contacts and roles. MVP six weeks."}'

docker compose exec redis redis-cli KEYS 'estimation:*'
```

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"transcription": "En la reunion con el cliente se discutio..."}'
```

OpenAPI docs: `http://localhost:8000/docs`

## Streaming

`POST /api/v1/estimate/stream` emits Server-Sent Events (`token`, then `done`).

HTML demo: [http://localhost:8000/static/sse_demo.html](http://localhost:8000/static/sse_demo.html)

```bash
curl -N -X POST http://localhost:8000/api/v1/estimate/stream \
  -H 'Content-Type: application/json' \
  -d '{"transcription": "We need a small CRM with auth, contacts and roles. MVP six weeks."}'
```

## Chat UI

Streamlit chat interface that streams a meeting transcription to the Estimator API.

The LLM API key stays in the backend `.env` — the UI only needs the API base URL.

1. Start the API (see **Run** above).
2. In another terminal:

```bash
uv run streamlit run ui/chat_app.py
```

Optional UI settings in `.env`:

- `ESTIMATOR_API_URL` — default `http://localhost:8000`
- `ESTIMATOR_REQUEST_TIMEOUT_SECONDS` — default `120`
- `PRIMARY_MODEL`, `FALLBACK_MODEL`, `CACHE_TTL` — shown in the sidebar

## Project structure

```
app/
├── main.py                 # FastAPI app, CORS, static files
├── config.py               # Settings loaded from .env
├── dependencies.py         # Redis cache and LLM wrapper singletons
├── routers/
│   └── estimations.py      # POST /estimate and /estimate/stream
├── schemas/
│   └── estimations.py      # Request/response models
├── services/
│   ├── llm_service.py      # Prompt knobs and two-phase preprocessing
│   ├── llm_wrapper.py      # LiteLLM fallback, cache, and cost
│   ├── cache.py            # Redis exact-match cache
│   ├── evaluation.py       # Structural checks on generated estimations
│   └── pricing.py          # Approximate USD cost estimation
├── context/
│   └── examples.py         # Canonical estimations injected into the prompt
├── fixtures/               # Sample transcriptions
└── static/sse_demo.html    # Browser SSE demo
ui/
├── chat_app.py             # Streamlit chat entrypoint
├── api_client.py           # HTTP client for blocking and streaming calls
└── config.py               # UI settings
Dockerfile
docker-compose.yml          # API plus Redis
```
