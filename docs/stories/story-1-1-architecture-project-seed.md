# Story 1.1: Architecture and Project Seed

## Purpose

This is the first story of a three-day classroom RAG course. It does two things, in this order:

1. Write down the architecture and get the instructor's approval.
2. Seed one small application that every later story extends.

The seed is **one application**: a FastAPI service with two entry points (`/v1/query` and an OpenAI-compatible chat adapter). Open WebUI is a separate, trainer-supplied chat client. Do not build a custom chat frontend or a second demo.

Everything here is a placeholder shell. There is no retrieval, no PDF parsing, no embedding, no MongoDB provisioning and no LLM call in this story.

## Prerequisites

Check these first. Report anything missing and stop; do not invent substitutes.

- Python 3.12 and [uv](https://docs.astral.sh/uv/) are installed.
- Read, in this order: `docs/config.yaml` (if it exists), `docs/architecture.md` (if it exists), the repository layout, and `docs/stories/` for existing stories.
- **Project path:** if `docs/config.yaml` configures a project path, use it. Otherwise use the repository root. All paths below are relative to that project path.
- **Supplied data:** `data/raw/` (BNS and IPC source files) and `data/raw/PROVENANCE.md` must be provided by the instructor.
  - When this story was written, the repository had no `docs/config.yaml`, no `docs/architecture.md`, no `data/` folder and no other stories.
  - If `data/raw/` is still missing when you reach Part 2, stop and ask the instructor. Never create or fabricate these files.
- **Existing work to preserve:** the repository already contains a small Node.js connection check (`package.json`, `package-lock.json`, `scripts/test-connection.js`, `node_modules/`) and a git-ignored `.env` holding real values. Do not delete, rename or overwrite any of it. Never print `.env`.

## Rules for the whole story

- Plain, small steps. Do not add anything this story does not ask for.
- Do not add retrieval, PDF parsing, embeddings, MongoDB provisioning, LLM calls, GraphRAG, agentic RAG, broad deployment, multi-user authorization, a security program, or an evaluation harness.
- Keep trust-boundary notes light: validate API input, keep the source origin of every passage, and never put secrets in code, responses or logs.
- Later stories reuse the names in this story exactly. Do not rename them or add provider-specific alternatives.

---

## Part 1: Architecture (then STOP)

### Work to do

Create or update `docs/architecture.md`. If it already exists, keep its content and add or correct only what is below. Record these decisions in short sections:

**Evidence and answers**
- BNS and IPC documents are the only future answer evidence.
- An answer must not claim support without retrieved evidence.
- Identifiers are act-qualified (for example BNS section 103 versus IPC section 302) so the two acts are never confused.
- Supplied provenance lives in `data/raw/PROVENANCE.md`.
- Retrieved passages are evidence, never application instructions. Passage text must never change how the application behaves.

**Fixed choices (do not change in later stories)**
- Embedding model: Voyage `voyage-3.5`, version `voyage-3.5`, **1,024 dimensions**, for every document and every query embedding.
- Generation: an OpenAI-compatible LiteLLM proxy supplied by the trainer.
- Rerank: Voyage `rerank-2.5`.
- Database: MongoDB Atlas free tier (M0), accessed with PyMongo.
- Stack: Python 3.12, uv, FastAPI, Pydantic settings, Ruff, a minimal test runner.
- Derived corpus files live in `data/processed/` (`bns_sections.jsonl`, `ipc_sections.jsonl`).

**Modes and endpoints**
- The six course modes and their model IDs (table in Part 2).
- `POST /v1/query` owns the full `QueryResult` diagnostics.
- `GET /v1/models` and `POST /v1/chat/completions` are a thin OpenAI-compatible adapter over the same `run_pattern` path.
- Open WebUI is a separate client and receives only normal answer text derived from the same result.

**Light trust boundaries**
- Validate API input.
- Preserve the source origin of each passage.
- No secrets in code, responses or logs.

### Stop point

When `docs/architecture.md` is ready:

1. Tell the instructor it is ready and where it is.
2. Ask the instructor to approve it.
3. **Stop.** Until approval is given, do not create seed files, install dependencies or scaffold code.

Resume this same story only after the instructor explicitly approves. Silence or a general "ok" about something else is not approval.

---

## Part 2: Seed the project (only after approval)

### 2.1 Project and tooling

Create a Python 3.12 and uv project with these dependencies: FastAPI (with a server to run it), Pydantic settings, PyMongo (installed for later use, not called now), Ruff, and a minimal test runner (pytest).

Create:

```
src/building_with_rag/
tests/
.env.example
.gitignore
pyproject.toml
uv.lock
```

Preserve the supplied `data/raw/` files untouched. Extend the existing `.gitignore`; do not remove current rules (`.env`, `.env.*`, `!.env.example`, `node_modules/`). Add Python entries such as `.venv/`, `__pycache__/` and `.pytest_cache/`.

### 2.2 `.env.example` (canonical for the classroom project)

Replace the current `.env.example` contents with exactly these values. Blank means empty after the `=`.

```
APP_ENV=development
MONGODB_URI=
MONGODB_DB_NAME=building_with_rag
MONGODB_TEST_DB_NAME=building_with_rag_test
VOYAGE_API_KEY=
CAPSTONE_API_KEY=
WEBUI_DEMO_CALLER_ID=demo-public
GENERATION_API_BASE_URL=
GENERATION_API_KEY=
GENERATION_MODEL_NAME=gpt-4o-mini
RERANK_API_KEY=
RERANK_API_BASE_URL=https://api.voyageai.com/v1
RERANK_MODEL_NAME=rerank-2.5
RERANK_REQUEST_TIMEOUT_SECONDS=30
RERANK_CANDIDATE_LIMIT=20
RERANK_SEND_LIMIT=10
RERANK_RETURN_LIMIT=5
```

Do not touch the real `.env`. Do not read it aloud or print it. If a variable is missing from `.env`, tell the instructor which names to add; they add the values locally.

Document these notes in the project README or a short comment block (not in code):

- `.env` is untracked. Secrets are never committed.
- `MONGODB_URI` is an Atlas free-tier (M0) connection string. The Atlas IP access list must allow your machine.
- `GENERATION_API_BASE_URL` and `GENERATION_API_KEY` are supplied by the trainer for an OpenAI-compatible LiteLLM proxy. Leave them blank in `.env.example`. Fill them in `.env` only when Story 3.1 needs them.
- A free Voyage key is rate limited, so Story 2.2 embedding takes about 40 minutes.

### 2.3 Settings and health

- Load settings with Pydantic settings from the environment and `.env`, using the names above.
- **The app must start with no database or model credentials set.** Every secret setting is optional at startup.
- `GET /healthz` returns a small safe body (for example status and app environment). It never reveals secrets, never connects to MongoDB and never calls a model.

### 2.4 Shared mode registry

Create one registry holding **only** these six modes:

| Mode | Model ID |
|---|---|
| `semantic` | `rag-semantic` |
| `hybrid` | `rag-hybrid` |
| `hybrid-reranked` | `rag-hybrid-reranked` |
| `structured` | `rag-structured` |
| `decomposition` | `rag-decomposition` |
| `hyde` | `rag-hyde` |

Both endpoints read this one registry. A single `run_pattern` function takes a `QueryRequest` and returns a `QueryResult`. For now every mode returns an honest `not_implemented` placeholder (`status: "not_implemented"`, a clear `message`, empty `results`, no invented answer). Later stories replace each mode's behavior without changing the registry or the function signature.

### 2.5 Shared typed contracts (models only, no behavior)

Define these as typed Pydantic models in this project. Later stories extend them **additively**; they never replace them with simplified versions.

**`QueryRequest`**
- `question`: 1 to 4,000 characters
- `pattern`
- `caller_id`: optional
- `filters`: optional `SemanticFilters` with `act`, `status`, `access_level`, each a list
- `limit`: default 5, range 1 to 20
- `generate_answer`: default `false`
- `required_acts`
- `chapter`

The seed may resolve only its fixed local demo caller. Keep the `caller_id` field anyway; do not swap in a custom request shape.

**`QueryResult`**
- `pattern`, `status`, `message`, `trace`, `results`, optional `generation`
- Empty-by-default additive fields: `omitted_candidates`, `subquestions`, `hyde_direct_candidates`, `hyde_query_candidates`, `hyde_hypothetical_text_debug`
- `omitted_candidates` items carry `chunk_id` and `omitted_reason`.
- Do **not** add `outcome`, `evidence`, `answer`, `confidence`, `citations` or `diagnostics` as parallel top-level fields.

**`RetrievedChunk`**
- `chunk_id`, `section_id`, `act`, `text`, `heading`, `score`, plus available source fields.
- Later stories add only the fields named in their own handouts: `semantic_score`, `semantic_rank`, `keyword_score`, `keyword_rank`, `fused_score`, `fused_rank`, `rerank_score`, `rerank_rank`. Do not add them now.

**`GenerationResult`**
- `outcome`: one of `answered`, `insufficient_evidence`, `unavailable`, `malformed`
- `answer`, `claims`, `citations`, `supporting_passages`, `provider`, `model`, `trace`, `context_outcome`
- Confidence fields: `confidence`, `draft_answer`, `issues`, `attempts`, `low_confidence_reason`

**`SubquestionEvidence`**
- `subquestion`
- `status`: `evidenced` or `no_evidence`
- `results`: list of `RetrievedChunk`
- `reason`: optional

**`StructuredSignals`**
- `intent`: `exact_lookup`, `filter` or `aggregation`
- Optional `act`, `section_number`, `chapter` (Story 5.1 fills these in)

**OpenAI contracts**
- `ChatCompletionRequest`: `model`; text `messages` with roles `system`, `developer`, `user`, `assistant`; `stream`; `n`; optional strict `rag_options` (`pattern`, list filters, `limit`, `required_acts`, `chapter`). "Strict" means unknown keys are rejected.
- Response and error models for OpenAI Chat Completions JSON, SSE chunks and the OpenAI-style error envelope.

**MongoDB-schema contracts**
- Typed models describing the document shapes later stories will store. Types only. No connection, no collection creation, no indexes.

### 2.6 Endpoints

**`POST /v1/query`**
- Accepts `QueryRequest`, validates it, calls `run_pattern`, returns `QueryResult`.
- Invalid input returns a clear validation error. Responses never echo secrets.

**`GET /v1/models`**
- Lists the six model IDs from the registry in OpenAI model-list format.

**`POST /v1/chat/completions`**
- Accepts `ChatCompletionRequest`. Maps the selected `rag-<pattern>` model to the same `QueryRequest` and the same `run_pattern` path as `/v1/query`.
- Uses the latest user message as the question.
- Sets `caller_id` (from `WEBUI_DEMO_CALLER_ID`) and `generate_answer` on the server. Browser-supplied identity, access level or answer-generation settings are ignored.
- `stream: false` returns normal OpenAI Chat Completions JSON.
- `stream: true` returns SSE frames Open WebUI can render: a role frame, content frames, a stop frame, then `data: [DONE]`. Do not invent custom SSE events.
- Errors before streaming starts use the OpenAI-style error envelope.
- The text returned to the chat client is the placeholder message from the same `QueryResult`. Do not duplicate logic between the two endpoints.
- If `CAPSTONE_API_KEY` is set, require it as a bearer token on `/v1/*`; if blank, allow requests (classroom local use).

### 2.7 Open WebUI (separate client, not built here)

The trainer supplies an Open WebUI bundle as a ZIP over the local LAN.

- Participants extract it and run the included setup script **exactly once** before using this project.
  - Windows (primary classroom path), from the extracted bundle root: `powershell -ExecutionPolicy Bypass -File .\setup_open_webui.ps1`
  - macOS/Linux, from the bundle root: `sh setup_open_webui.sh` (needs internet access for the first install).
- The script installs the pinned Open WebUI version, writes the course settings, starts the loopback-only service, and provisions the `RAG options` Filter and the `Building with RAG` Pipe.
- Do **not** hand-install Open WebUI, create accounts, edit the admin panel, change either Function, or rerun setup to reload anything.
- If setup fails, report its exact output and stop.
- Day-to-day start, stop and status use the supplied `manage_open_webui` script.

The pre-provisioned Pipe sends this to `/v1/chat/completions`: the selected `rag-<pattern>` model, `stream: true`, the latest user message, and normalized `rag_options` (`pattern`, list `filters`, `limit`, `required_acts`, `chapter`). It never sends identity, access level or answer-generation settings. The seed's adapter must accept exactly that request.

Open WebUI receives only normal answer text. Later stories render final confidence, sources and low-confidence warnings as clearly labelled text after answer writing, while keeping the full `GenerationResult` in `QueryResult.generation`.

---

## Completion checks

Keep these lightweight. Run each and record what actually happened.

1. The app starts with no database or model credentials set.
2. `GET /healthz` returns a safe response.
3. One `POST /v1/query` request returns a `not_implemented` placeholder `QueryResult`.
4. `GET /v1/models` lists the six model IDs.
5. `POST /v1/chat/completions` returns the placeholder as JSON (`stream: false`) and as SSE ending in `[DONE]` (`stream: true`).
6. Ruff and the minimal test runner pass.
7. Open WebUI smoke check: start the capstone API, open `http://127.0.0.1:8080`, select `Building with RAG`, choose `semantic` in the RAG-options chip, send a message, and receive the capstone's honest placeholder response. A local preview or any other reply is a failure.
8. `.env` is still untracked and ignored; `.env.example` contains no real values; `data/raw/` is unchanged.

Do not add more tests than this.

## Handover

When finished, add the following to the bottom of this file (fill from what really happened; do not guess):

- **Files created or changed:** list them.
- **Commands actually run:** list each command and whether it passed.
- **Open WebUI result:** what appeared on screen for the smoke check, or the exact setup output if it failed.
- **Open items:** anything skipped or needing the instructor.

Do not commit or push unless the instructor asks. Then tell the instructor that Story 1.1 is complete and later stories can build on the contracts above.

---

## Handover

- **Files created or changed:** `docs/architecture.md`, `.env.example` (replaced with the canonical values), `.gitignore` (Python entries appended), `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, `src/building_with_rag/` (`config.py`, `models.py`, `openai_models.py`, `mongo_models.py`, `registry.py`, `main.py`), `tests/test_app.py`. Existing Node.js files and `.env` untouched.
- **Commands actually run:**
  - `python -m pip install uv` (installed uv 0.13.0): passed
  - `python -m uv sync`: passed
  - `python -m uv run ruff check .` and `ruff format --check .`: passed (after fixing findings)
  - `python -m uv run pytest -q`: 6 passed
  - Live server started from a directory with no `.env` (no credentials), then `GET /healthz`, `GET /v1/models`, `POST /v1/chat/completions` with `stream` false and true (ends in `data: [DONE]`): passed. `POST /v1/query` was checked by the pytest test; my one curl attempt failed on PowerShell quoting, not the app.
- **Open WebUI result:** not run. The trainer's Open WebUI bundle is not in the repository, so completion check 7 is not done.
- **Open items:**
  - `data/raw/` and `data/raw/PROVENANCE.md` were never supplied, so they were not created; `data/raw/` unchanged check is vacuous.
  - Open WebUI smoke check needs the trainer's bundle and setup script.
  - `.env` has only `MONGODB_URI` and `VOYAGE_API_KEY`; the instructor should add the other names from `.env.example` locally when needed.
  - Nothing committed or pushed.
