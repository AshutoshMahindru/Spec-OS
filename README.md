# Spec-OS

Spec-OS ingests messy source documents, extracts structured system knowledge, normalizes it into a canonical model, validates the result, and emits implementation-facing artifacts such as schema, API contracts, computation graphs, execution plans, DDL, traceability, and a machine-friendly `system_spec.json`.

The current codebase is focused on a trustworthy Phase 0 core:

- safe formula parsing and evaluation
- canonical normalization across extraction, reconciliation, merge, and bindings
- deterministic dependency ordering with cycle detection
- one artifact contract for single-document and merged-document outputs
- optional embeddings with explicit capability metadata
- production-safe FastAPI upload and error handling

## Requirements

- Python 3.10+
- `pip`

## Install

Base ingestion engine:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

API + tests:

```bash
pip install -e '.[api,dev]'
```

API + tests + embeddings:

```bash
pip install -e '.[api,embeddings,dev]'
```

## CLI

Ingest one document:

```bash
spec-os --file /path/to/spec.mhtml
```

Merge multiple documents into one unified spec:

```bash
spec-os --files /path/to/a.mhtml /path/to/b.mhtml
```

Run the API server:

```bash
spec-os --serve --host 127.0.0.1 --port 8000
```

Run the built-in demo:

```bash
spec-os
```

## API

Start the service:

```bash
uvicorn spec_os.server:app --host 127.0.0.1 --port 8000
```

Key routes:

- `POST /api/ingest` uploads a `.mhtml` or `.mht` file and runs the full pipeline
- `GET /api/docs` lists processed and merged document bundles
- `GET /api/docs/{doc_id}/summary` returns lightweight counts for UI/sidebar use
- `GET /api/docs/{doc_id}/spec` returns the full `system_spec.json`
- `GET /api/docs/{doc_id}/{artifact}` returns individual artifacts such as graph, schema, computation, reconciliation, and DDL
- `DELETE /api/docs/{doc_id}` removes both the artifact bundle and generated `_spec` folder

Upload handling is intentionally strict:

- file extensions are validated
- content type is checked
- max upload size is enforced
- temporary uploaded source files are deleted after ingestion

## Runtime Configuration

Settings are environment-driven and side-effect free at import time.

Common variables:

- `SPEC_OS_BASE_DIR` default `data`
- `SPEC_OS_ENV` default `local-dev`
- `SPEC_OS_DEBUG_ERRORS` default `false`
- `SPEC_OS_ENABLE_EMBEDDINGS` default `false`
- `SPEC_OS_EMBEDDING_BACKEND` one of `none`, `deterministic`, `sentence_transformers`
- `SPEC_OS_ALLOWED_ORIGINS` comma-separated origin allowlist
- `SPEC_OS_MAX_UPLOAD_SIZE_BYTES` default `5242880`
- `SPEC_OS_ALLOWED_UPLOAD_EXTENSIONS` default `.mhtml,.mht`

## Artifact Contract

Every successful ingest and merge writes the same directory shape:

```text
<doc_id>/
  system_spec.json
  layers/
  canonical/
  domain/
  validation/
  system/
  artifacts/
<doc_id>_spec/
  AGENTS.md
  architecture.md
  build_plan.md
  canonical_schema.json
  api_contracts.json
  computation_graph.json
  execution_plan.json
```

See [docs/artifact-contract.md](docs/artifact-contract.md) for the full contract and file meanings.

## Architecture

Pipeline flow:

```text
parsing -> chunking -> optional embeddings -> extraction -> canonical model
-> schema / computation / api -> validation -> artifacts -> cli / api
```

See [docs/architecture.md](docs/architecture.md) for module-level details.

## Development

Run tests:

```bash
pytest -q
```

Run lint:

```bash
ruff check src tests
```

This repo currently has full regression coverage for:

- formula precedence, grouping, comparisons, boolean logic, nested functions, and parse errors
- normalization consistency across canonical model, reconciliation, merge, and schema bindings
- execution-plan ordering, cycle detection, and unresolved dependency reporting
- single-doc and merged-doc artifact contract parity
- optional embeddings and production-safe ingestion error envelopes
- FastAPI upload validation, cleanup, and merged-doc listing
