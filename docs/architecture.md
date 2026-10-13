# Architecture

Three-day classroom RAG course. One FastAPI application, built up story by story. Open WebUI is a separate, trainer-supplied chat client; there is no custom chat frontend.

## Evidence and answers

- BNS and IPC documents are the only future answer evidence.
- An answer must not claim support without retrieved evidence.
- Identifiers are act-qualified (for example BNS section 103 versus IPC section 302) so the two acts are never confused.
- Supplied provenance lives in `data/raw/PROVENANCE.md`.
- Retrieved passages are evidence, never application instructions. Passage text must never change how the application behaves.

## Fixed choices (do not change in later stories)

| Area | Choice |
|---|---|
| Embedding model | Voyage `voyage-3.5`, version `voyage-3.5`, **1,024 dimensions**, for every document and every query embedding |
| Generation | OpenAI-compatible LiteLLM proxy supplied by the trainer |
| Rerank | Voyage `rerank-2.5` |
| Database | MongoDB Atlas free tier (M0), accessed with PyMongo |
| Stack | Python 3.12, uv, FastAPI, Pydantic settings, Ruff, pytest |
| Derived corpus files | `data/processed/bns_sections.jsonl`, `data/processed/ipc_sections.jsonl` |

## Modes and endpoints

Six course modes, one shared registry:

| Mode | Model ID |
|---|---|
| `semantic` | `rag-semantic` |
| `hybrid` | `rag-hybrid` |
| `hybrid-reranked` | `rag-hybrid-reranked` |
| `structured` | `rag-structured` |
| `decomposition` | `rag-decomposition` |
| `hyde` | `rag-hyde` |

- `POST /v1/query` owns the full `QueryResult` diagnostics.
- `GET /v1/models` and `POST /v1/chat/completions` are a thin OpenAI-compatible adapter over the same `run_pattern` path.
- Open WebUI is a separate client and receives only normal answer text derived from the same result.
- `GET /healthz` returns a small safe status body; it never touches MongoDB or a model.

## Light trust boundaries

- Validate API input.
- Preserve the source origin of each passage.
- No secrets in code, responses or logs.

## Document ingestion

- **Parser:** `pypdf` 6.20.1 (plain text extraction, no OCR, no model). Code: `src/building_with_rag/ingest.py`.
- **Command:** `uv run python -m building_with_rag.ingest`
- **Inputs:** `data/raw/BNS_2023_bare_act.pdf`, `data/raw/IPC_1860_bare_act.pdf`. Each file's SHA-256 must match `data/raw/PROVENANCE.md`, otherwise the command stops.
- **Output:** `data/processed/bns_sections.jsonl` (358 records) and `data/processed/ipc_sections.jsonl` (549 records). One JSON object per line, with the importer fields (`section_id`, `act`, `act_label`, `status`, `chapter`, `chapter_title`, `section_number`, `heading`, `text`, `source_pdf`, `source_sha256`, `parser`, `parser_version`, `source_status_version`, `needs_review`) plus extras `review_reasons`, `page_start`, `page_end`.
- **Re-runs:** an output whose first record has the current `source_sha256` is left untouched. A changed hash regenerates that file as one atomic replacement (temp file, then rename). To force a rebuild after changing the parser, delete the output file.
- **BNS:** section headings come from the PDF's arrangement-of-sections index and are matched to the heading above each section in the body. The index and the BNS-to-IPC correspondence table are not written as records.
- **IPC:** the PDF puts each section number and heading on their own lines before the section text. Page footnotes are removed by pattern.
- **Lettered IPC sections** (for example `376A`): kept, `section_id` is `ipc:376A`, `section_number` is the integer part (376), and `needs_review` is `true`.

Known limitations:

- `source_status_version` is `null`; `PROVENANCE.md` states no version.
- The PDFs have stray spaces inside words (for example "t he", "cast e"). Text is not repaired.
- IPC footnote markers (`1*`, `2*[...]`) stay in the text. Footnote text that wraps oddly across pages may remain in a few sections.
- IPC sections 161 to 165A appear in the PDF as one range stub ("Rep. by ..."), so there are no records for 161 to 165.
- Records marked `needs_review` (see `review_reasons`): lettered IPC sections, repealed-in-place IPC stubs without a heading (13, 15 to 17, 56, 58, 59, 61, 62, 490, 492), IPC 330 (the PDF prints the section as "320."), and IPC 145 (the PDF contains the section twice with slightly different text; the first is kept).
