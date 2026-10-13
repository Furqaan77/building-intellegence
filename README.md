# Building with RAG

Classroom RAG course seed: one FastAPI service with `POST /v1/query` and an OpenAI-compatible chat adapter (`GET /v1/models`, `POST /v1/chat/completions`). Open WebUI is a separate, trainer-supplied client. See [docs/architecture.md](docs/architecture.md).

## Run

```
uv sync
uv run uvicorn building_with_rag.main:app --host 127.0.0.1 --port 8000
uv run ruff check . && uv run pytest
```

Build the section corpus from the PDFs in `data/raw/` (writes `data/processed/*.jsonl`; safe to re-run):

```
uv run python -m building_with_rag.ingest
```

Copy `.env.example` to `.env` and fill values locally. The app starts with no credentials set.

## Environment notes

- `.env` is untracked. Secrets are never committed.
- `MONGODB_URI` is an Atlas free-tier (M0) connection string. The Atlas IP access list must allow your machine.
- `GENERATION_API_BASE_URL` and `GENERATION_API_KEY` are supplied by the trainer for an OpenAI-compatible LiteLLM proxy. Leave them blank in `.env.example`. Fill them in `.env` only when Story 3.1 needs them.
- A free Voyage key is rate limited, so Story 2.2 embedding takes about 40 minutes.
- If `CAPSTONE_API_KEY` is set, `/v1/*` requires it as a bearer token.
