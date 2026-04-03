# Spec-OS Architecture

## Core Flow

Spec-OS follows a layered pipeline:

```text
source document
  -> parse_mhtml
  -> clean_html
  -> chunk_text
  -> optional embeddings
  -> classify_document
  -> route_extraction
  -> build_canonical_model
  -> build schema / computation graph / api contracts
  -> validate graph / computation / reconciliation / completeness
  -> write artifact bundle + generated spec folder
```

## Key Modules

- `src/spec_os/parsing/` parses MHTML and cleans structured content
- `src/spec_os/extraction/` classifies and extracts graph nodes by document family
- `src/spec_os/canonical/model.py` turns raw graph output into normalized variables, metrics, entities, and relationships
- `src/spec_os/computation/parser.py` and `src/spec_os/computation/formula.py` provide safe formula parsing and evaluation
- `src/spec_os/computation/dag.py` derives the execution graph and deterministic execution plan
- `src/spec_os/schema/` derives storage-facing schema and starter DDL
- `src/spec_os/validation/` checks structural integrity, reconciliation, completeness, and quality
- `src/spec_os/artifacts/store.py` is the shared artifact contract and filesystem access layer
- `src/spec_os/orchestration/pipeline.py` coordinates end-to-end ingest and multi-doc merge
- `src/spec_os/server.py` exposes the bundle through FastAPI

## Hardening Decisions

### Formula Engine

The old evaluator was flat and left-to-right. The current engine uses a real parser with:

- operator precedence
- parentheses
- unary operators
- comparison operators
- boolean operators
- nested function calls
- explicit syntax and evaluation errors

### Dependency Planning

Execution planning is now a real topological sort. The plan records:

- deterministic `execution_steps`
- cycle issues
- unresolved dependency issues when available inputs are declared

### Artifact Contract

Single-document and merged-document outputs now write the same bundle structure. That makes server listing, summary, and artifact retrieval work the same way for both flows.

### Optional Embeddings

Embeddings are now capability-driven:

- disabled by default
- explicitly configured through settings
- recorded in artifact metadata
- skipped cleanly when unavailable

### API Hardening

The server now applies:

- origin allowlists
- upload size and type validation
- temporary upload cleanup
- stable error envelopes without raw trace leakage in production mode
