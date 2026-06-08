# Meridian — Multi-Agent Research Intelligence API

Five specialized AI agents decompose your question, search the web in parallel, rank evidence semantically, detect contradictions, and stream a structured report — live.

## Architecture

```
POST /research  →  Planner → Researchers (parallel) → Extractor → Critic → Synthesizer
                                                                              ↓
GET /research/{id}  ←  structured JSON report
GET /research/{id}/stream  ←  live SSE events
```

| Agent | Role |
|-------|------|
| **Planner** | LLM decomposes query into 3–5 sub-questions |
| **Researcher** | Searches Wikipedia, arXiv, DuckDuckGo in parallel |
| **Extractor** | Ranks passages with fastembed cosine similarity |
| **Critic** | LLM finds contradictions and knowledge gaps |
| **Synthesizer** | LLM builds the final structured report |

## Quick Start (Local)

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY

pip install -e ".[dev]"

docker compose up -d postgres redis
alembic upgrade head

# Terminal 1: API
make dev

# Terminal 2: Worker
make worker
```

### Web UI

Open **http://localhost:8080** in your browser for a simple interactive UI.

API docs (Swagger) remain at **http://localhost:8080/docs**.

### Usage (API)

```bash
# Submit a research query
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest advances in quantum error correction?"}'

# Stream live progress (SSE)
curl -N http://localhost:8080/research/{id}/stream

# Fetch final report
curl http://localhost:8080/research/{id}
```

### Docker (all-in-one)

```bash
cp .env.example .env
# Set LLM_API_KEY

docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research` | Submit a research query (returns job ID) |
| `GET` | `/research/{id}` | Get job status and report |
| `GET` | `/research/{id}/stream` | SSE stream of pipeline events |
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check (Postgres, Redis, LLM) |
| `GET` | `/metrics` | Prometheus metrics |

## Configuration

See [`.env.example`](.env.example) for all settings. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `LLM_BASE_URL` | OpenAI-compatible API base URL |
| `LLM_API_KEY` | LLM provider API key |
| `LLM_MODEL` | Model name (e.g. `llama-3.3-70b-versatile`) |
| `API_KEY` | Optional client API key |

## Free Cloud Hosting

Deploy for **$0/month** on Render + Neon + Upstash + Groq.

See [docs/DEPLOY.md](docs/DEPLOY.md) for the full step-by-step guide.

## Development

```bash
make test     # Run tests
make lint     # Run ruff
make migrate  # Run Alembic migrations
```

## License

Apache 2.0
