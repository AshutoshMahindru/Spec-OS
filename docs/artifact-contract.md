# Spec-OS Artifact Contract

## Document Bundle

Every successful ingest or merge produces a `<doc_id>/` directory with the same layout:

```text
<doc_id>/
  system_spec.json
  layers/
    structured.json
    graph.json
  canonical/
    canonical_model.json
    variable_registry.json
  domain/
    schema.json
    canonical_schema.json
    computation_graph.json
    api_contracts.json
  validation/
    graph_validation.json
    computation_validation.json
    reconciliation.json
    spec_score.json
    completeness.json
  system/
    variable_mapping.json
    execution_plan.json
    api_bindings.json
    embedding_status.json
  artifacts/
    ddl.sql
    mermaid.json
    roadmap.json
    traceability.json
```

## File Meanings

- `system_spec.json`: top-level contract that ties together canonical, schema, application, computation, runtime, validation, and source metadata
- `layers/structured.json`: cleaned sections, chunks, and source metadata; merged bundles keep `structured` and `chunks` empty and use `source_documents`
- `layers/graph.json`: extracted graph before canonical normalization
- `canonical/canonical_model.json`: normalized variables, metrics, entities, and relationships
- `canonical/variable_registry.json`: flattened variable registry used across reconciliation and schema work
- `domain/schema.json`: runtime storage models
- `domain/canonical_schema.json`: normalized schema projection used for generated spec folders
- `domain/computation_graph.json`: normalized metrics and available runtime inputs
- `domain/api_contracts.json`: generated API contracts
- `validation/*.json`: validation, reconciliation, completeness, and quality artifacts
- `system/variable_mapping.json`: variable-to-storage routing using canonical keys
- `system/execution_plan.json`: deterministic topological order plus issues if invalid
- `system/api_bindings.json`: API-to-schema model bindings
- `system/embedding_status.json`: requested backend, actual backend, availability, and persistence state
- `artifacts/ddl.sql`: starter relational DDL
- `artifacts/mermaid.json`: diagram-ready graph payloads
- `artifacts/roadmap.json`: engineering roadmap suggestion
- `artifacts/traceability.json`: source-section to artifact traceability rows

Imported spec-pack bundles use the same layout. When an upstream repo carries richer validation objects than the base contract, Spec-OS preserves them under `system_spec.json -> validation -> source_validation`.

## Spec Repo Modes

Modelling_Engine_SpecOS repos currently support two explicit entry modes:

- `--specos-repo-mode importer`: stable default; reads the checked-in RC artifact pack
- `--specos-repo-mode compiler`: experimental; recompiles the upstream artifact pack from phase specs before normalization

Both modes write the same on-disk bundle layout shown above and generate the same `<doc_id>_spec/` folder structure.

The CLI summary distinguishes them with:

- `status: "imported"` and `import_mode: "modelling_engine_specos"` for the stable importer path
- `status: "compiled"` and `import_mode: "modelling_engine_specos_compiler"` for the experimental compiler path
- `compiler_mode: "shadow_phase_spec_compiler"` only when the compiler path is used

`doc_type` remains `SPECOS_REPO` in both cases.

## Generated Spec Folder

Each bundle also produces a `<doc_id>_spec/` directory for downstream agents:

```text
<doc_id>_spec/
  AGENTS.md
  requirements.md
  architecture.md
  build_plan.md
  canonical_schema.json
  api_contracts.json
  computation_graph.json
  execution_plan.json
```

## Merge Behavior

Merged documents are first-class bundles:

- they receive a normal `system_spec.json`
- they appear in `GET /api/docs`
- they expose the same summary and artifact routes as single-doc ingests
- `layers/structured.json` stores `source_documents` rather than flattened merged sections
