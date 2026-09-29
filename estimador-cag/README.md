# Estimador CAG

Software effort estimator that renders a versioned prompt from a project description, project type, detail level, and output format.

Responses are cached in Redis by exact prompt match, and a LiteLLM router falls back to a secondary provider.

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

`POST /api/v1/estimate` — generate a free-text software estimation.

All four request fields are required. `description` must be between 20 and 80000 characters.

- `project_type`: `mobile_app`, `web_saas`, `internal_tool`, `data_pipeline`
- `detail_level`: `summary`, `medium`, `detailed`
- `output_format`: `phases_table`, `line_items`, `narrative`

**Request**

```json
{
  "description": "A small B2B SaaS to manage employee equipment loans across teams.",
  "project_type": "web_saas",
  "detail_level": "medium",
  "output_format": "phases_table"
}
```

**Response**

```json
{
  "text": "## Estimation\n\n| phase | duration_weeks | cost_eur | confidence_pct |\n...",
  "prompt_version": "v1"
}
```

The response is free text plus the prompt template version. Token usage and cache status stay inside the LLM wrapper.

```bash
curl -s localhost:8000/api/v1/estimate -H 'Content-Type: application/json' \
  -d '{"description":"We need a small CRM with auth, contacts and roles. MVP six weeks.","project_type":"web_saas","detail_level":"medium","output_format":"phases_table"}'

docker compose exec redis redis-cli KEYS 'estimation:*'
```

OpenAPI docs: `http://localhost:8000/docs`

## Streaming

`POST /api/v1/estimate/stream` emits Server-Sent Events (`token`, then `done`).

HTML demo: [http://localhost:8000/static/sse_demo.html](http://localhost:8000/static/sse_demo.html)

```bash
curl -N -X POST http://localhost:8000/api/v1/estimate/stream \
  -H 'Content-Type: application/json' \
  -d '{"description":"We need a small CRM with auth, contacts and roles. MVP six weeks.","project_type":"web_saas","detail_level":"medium","output_format":"phases_table"}'
```

## Chat UI

Streamlit chat interface that streams a project description to the Estimator API. The sidebar sets project type, detail level, and output format.

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
├── prompts/
│   ├── loader.py           # Jinja2 renderer for versioned prompts
│   └── estimation/v1/      # system, user, and examples templates
├── services/
│   ├── llm_wrapper.py      # LiteLLM fallback, cache, and cost
│   ├── cache.py            # Redis exact-match cache
│   └── pricing.py          # Approximate USD cost estimation
├── fixtures/               # Sample project descriptions
└── static/sse_demo.html    # Browser SSE demo
ui/
├── chat_app.py             # Streamlit chat entrypoint
├── api_client.py           # HTTP client for blocking and streaming calls
└── config.py               # UI settings
Dockerfile
docker-compose.yml          # API plus Redis
```
