# Story 2.1: Document Ingestion

## Purpose

Turn the supplied BNS and IPC PDFs into a small, inspectable, section-level corpus: one JSON record per section, in two JSONL files. This story follows Story 1.1 and extends the same application. It stops at the JSONL files.

Out of scope: MongoDB, embeddings, vector indexes, retrieval and answer generation (later stories). Do not add them, and do not add or rename any setting in `.env.example`.

## Prerequisites

Check these first. Report anything missing and stop; do not invent substitutes.

- Story 1.1 is complete: the uv project, `src/building_with_rag/`, `tests/`, `.env.example`.
- Read, in this order: `docs/config.yaml` (if it exists), `docs/architecture.md`, `docs/stories/story-1-1-architecture-project-seed.md`, the existing code, and `data/raw/`.
- **Project path:** if `docs/config.yaml` configures one, use it. Otherwise use the repository root. All paths below are relative to it.
- **Inputs (supplied, never modified):**
  - `data/raw/BNS_2023_bare_act.pdf`
  - `data/raw/IPC_1860_bare_act.pdf`
  - `data/raw/PROVENANCE.md`
- If any input is missing or its SHA-256 differs from `PROVENANCE.md`, report it and stop. Do not repair, re-download or replace the PDFs.
- Do not edit, rename or delete the PDFs or `PROVENANCE.md`. Do not touch `.env`; never print it.

Known layout when this story was written (confirm by inspection, do not assume):

- The BNS PDF opens with an index and a section-correspondence table (BNS to repealed IPC sections). These are context, not sections of the Act. Do not turn them into section records.
- The IPC PDF contains footnote markers (such as `1*` and `2*[India]`) inside the text.
- Both PDFs repeat headers, and sections can continue across pages.

## Rules

- Plain, small steps. Add only what this story asks for.
- Extract sections without rewriting their meaning. Normalise whitespace and remove repeated page headers only; never paraphrase, summarise or "fix" legal wording.
- If content is uncertain, scanned (no extractable text), or a section boundary is ambiguous, set `needs_review` to `true` on that record and say so in the handover. Do not silently repair it.
- Do not invent unknown provenance or field values. Where a field cannot be determined, use `null` for optional values, or flag `needs_review`; never guess.
- Keep BNS and IPC records strictly separate even where section numbers match.

## Work to do

### 1. Parser dependency

Choose a suitable PDF parsing library and add it with uv (`uv add ...`) so `pyproject.toml` and `uv.lock` are updated. Prefer a plain-text extractor over anything that needs OCR or a model. Record the choice in `docs/architecture.md` (see step 5).

### 2. Extraction command

Add a small module with a command-line entry, for example `uv run python -m building_with_rag.ingest`. It reads the two PDFs and writes the two output files. Keep it to a few small functions: read pages, clean text, find chapters and sections, write records.

Handling rules:

- **Repeated page headers and spacing:** detect lines that repeat across many pages and drop them; collapse stray spaces and line breaks inside paragraphs.
- **Multi-page sections:** a section runs from its heading to the next section heading (or chapter heading); join text across page breaks.
- **Duplicate extraction:** if the same section number appears twice for the same act and the text is identical, keep one. If the two differ, keep the first and set `needs_review` on it.
- **Chapters:** track the current chapter number (for example `I`) and title as headings are met, and attach them to each section.
- **Skipping non-section content:** index pages, the correspondence table, preambles and schedules that are not sections are not written as records.

### 3. Output records

Write to:

- `data/processed/bns_sections.jsonl`
- `data/processed/ipc_sections.jsonl`

One JSON object per line, UTF-8, with these fields (compatible with the later importer):

| Field | Rule |
|---|---|
| `section_id` | `bns:<number>` or `ipc:<number>` |
| `act` | `BNS_2023` or `IPC_1860` exactly |
| `act_label` | Human-readable act name, for example "Bharatiya Nyaya Sanhita, 2023" |
| `status` | `in_force` (BNS) or `repealed` (IPC) exactly |
| `chapter` | String, for example `I` |
| `chapter_title` | Chapter title text |
| `section_number` | Integer |
| `heading` | Section heading text |
| `text` | Section body, cleaned as above |
| `source_pdf` | PDF file name, for example `BNS_2023_bare_act.pdf` |
| `source_sha256` | SHA-256 of that PDF, matching `PROVENANCE.md` |
| `parser` | Name of the library used |
| `parser_version` | Its installed version |
| `source_status_version` | From `PROVENANCE.md` where it states one; otherwise `null`. Do not invent it. |
| `needs_review` | `true` or `false` |

Page references (for example first and last page) may be kept as extra fields, but they do not replace any field above.

IPC sections with a letter suffix (for example `376A`) do not fit an integer `section_number`. Do not drop or merge them silently: keep the record, use the integer part as `section_number` only if `section_id` can still be unique (for example `ipc:376A`), and set `needs_review` to `true`. Record how you handled this in `docs/architecture.md`.

### 4. Safe re-runs

- Write each output to a temporary file first, then replace the target in one step, so a failed run never leaves a half-written corpus.
- Re-running must not append duplicates. If an existing output was produced from the same `source_sha256`, leave it as it is.
- If a source hash differs from what the existing output records, regenerate that file as one full replacement. Never mix records from two source versions.
- Do not overwrite a supplied valid corpus unnecessarily.

### 5. Document it

Update `docs/architecture.md` (keep existing content). Add a short "Document ingestion" section with: the parser choice and version, the output format and location, the exact command, and known limitations (for example footnote markers, lettered sections, anything flagged `needs_review`). Add the command to `README.md`.

## How later chunking will use this

Later chunking works from these section records and must preserve the parent section. Each chunk keeps `section_id`, `act`, `status`, `section_number`, `chapter`, `heading`, `source_pdf` and `source_sha256` from its parent, so every retrieved passage can be traced to its act-qualified section and source file. Chunks never merge text from different sections or acts.

## Completion checks

Keep these small. Run each and record what actually happened.

1. Run the command once; both JSONL files exist and are non-empty.
2. Every record has all required fields with the exact values above (`act`, `status`, `section_id` format, integer `section_number`, string `chapter`), and no record has empty `text`.
3. Inspect a few representative records in each output against the matching PDF, including at least one section that spans pages, if one exists.
4. Spot-check known sections: for example BNS section 103 (murder punishment) and IPC section 302 appear in the right files with the right `act` and `status`.
5. Run the command a second time; record counts are unchanged and no duplicates appear (the file may be left untouched).
6. `ruff check` and `pytest` pass. Add at most one or two small tests (for example, the record format of a tiny hand-made sample); do not build a validation framework or difference report.
7. The PDFs and `PROVENANCE.md` are unchanged; `.env` is untouched.

## Handover

When finished, add the following to the bottom of this file, filled from what really happened:

- **Inputs and outputs:** the files read and the files written.
- **Files created or changed:** list them.
- **Commands actually run:** each command and whether it passed.
- **What was generated:** record counts per act, and how many are marked `needs_review`, with reasons.
- **What was checked:** which sections you inspected against which PDF pages.
- **Open items:** anything skipped or needing the instructor.

Do not commit or push unless the instructor asks.

---

## Handover

- **Inputs and outputs:** read `data/raw/BNS_2023_bare_act.pdf`, `data/raw/IPC_1860_bare_act.pdf` and `data/raw/PROVENANCE.md` (hashes matched). Wrote `data/processed/bns_sections.jsonl` (358 records) and `data/processed/ipc_sections.jsonl` (549 records).
- **Files created or changed:** `src/building_with_rag/ingest.py`, `tests/test_ingest.py`, `pyproject.toml` and `uv.lock` (added `pypdf`), `docs/architecture.md`, `README.md`, `data/processed/*.jsonl`.
- **Commands actually run:** `python -m uv add pypdf` (passed); `python -m uv run python -m building_with_rag.ingest` several times while developing, then once from a clean `data/processed/` (wrote both files) and once more (both reported "up to date" and the file hashes were identical); `ruff check` and `ruff format` (passed); `pytest` (8 passed).
- **What was generated:** BNS 358 records, sections 1 to 358 with none missing, 0 marked `needs_review`. IPC 549 records: 506 plain-number sections plus 43 lettered ones, 56 marked `needs_review`. The reasons are 43 lettered section numbers, repealed-in-place stubs with no heading, IPC 330 (the PDF prints "320."), and IPC 145 (duplicate with different text). IPC 161 to 165 have no records because the PDF shows them as one range stub.
- **What was checked:** BNS 1, 2 (multi-page definitions), 7 and 26 (headings that differ slightly from the index), 103. IPC 4 (spans pages 2 and 3), 302, 330, 376A, 479. Checked against the extracted PDF text. Also confirmed no record has empty text, and no record text contains leftover "Subs. by"/"Ins. by" footnote wording. I did not open the PDFs visually.
- **Open items:**
  - Instructor to decide whether `data/processed/` should be committed or git-ignored; it is currently untracked and not ignored.
  - IPC footnote markers and PDF word-spacing artifacts are left as they are (see `docs/architecture.md`).
  - Nothing committed or pushed.
