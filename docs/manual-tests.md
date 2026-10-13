# Manual tests

## Story 1.1 — Architecture and Project Seed

**What it adds:** a FastAPI seed with `/healthz`, `POST /v1/query`, and an OpenAI-compatible adapter (`GET /v1/models`, `POST /v1/chat/completions`) over six placeholder modes.

Start the API first: `uv run uvicorn building_with_rag.main:app --host 127.0.0.1 --port 8000`. If `CAPSTONE_API_KEY` is set in `.env`, add `-H "Authorization: Bearer $CAPSTONE_API_KEY"` to the `/v1/*` commands. Commands use POSIX shell quoting (Git Bash, macOS, Linux).

```sh
# 1. Health
curl -s http://127.0.0.1:8000/healthz

# 2. Query (success)
curl -s -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the punishment for murder?", "pattern": "semantic"}'

# 3. Query (invalid input: empty question)
curl -s -i -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "", "pattern": "semantic"}'

# 4. Model list
curl -s http://127.0.0.1:8000/v1/models

# 5. Every selectable mode
for m in semantic hybrid hybrid-reranked structured decomposition hyde; do
  curl -s -X POST http://127.0.0.1:8000/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"What is murder?\", \"pattern\": \"$m\"}"; echo
done

# 6. Chat (JSON)
curl -s -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rag-semantic", "stream": false, "messages": [{"role": "user", "content": "What is murder?"}]}'

# 7. Chat (streaming)
curl -s -N -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rag-hyde", "stream": true, "messages": [{"role": "user", "content": "What is murder?"}]}'

# 8. Chat (unknown model)
curl -s -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rag-unknown", "messages": [{"role": "user", "content": "hi"}]}'
```

Expected:
1. `{"status":"ok","app_env":"development"}`; no secrets.
2. `status` is `not_implemented`, `pattern` is `semantic`, `message` says the mode is not implemented, `results` is `[]`, and no answer is invented.
3. HTTP `422` with a `detail` list naming `question`.
4. Six models: `rag-semantic`, `rag-hybrid`, `rag-hybrid-reranked`, `rag-structured`, `rag-decomposition`, `rag-hyde`.
5. Six JSON results, each `status: "not_implemented"` with its own `pattern`.
6. A `chat.completion` whose message content is `The 'semantic' mode is not implemented yet.`
7. SSE frames: a role frame, a content frame with `The 'hyde' mode is not implemented yet.`, a `finish_reason: "stop"` frame, then `data: [DONE]`.
8. HTTP `404` with an OpenAI-style `{"error": {..., "code": "model_not_found"}}`.
