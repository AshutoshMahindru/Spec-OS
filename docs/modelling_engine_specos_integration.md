# Modelling_Engine_SpecOS Integration

Canonical source: Modelling_Engine_SpecOS
Execution engine: Spec-OS

## Implemented bridge

- `src/spec_os/importers/modelling_engine_specos.py` loads the RC artifact pack and normalizes it into the standard Spec-OS bundle layout.
- `src/spec_os/compiler/modelling_engine_specos.py` exposes an experimental compiler-backed path that regenerates the same upstream artifact pack from the phase specs before normalizing it into the standard bundle layout.
- `src/spec_os/orchestration/pipeline.py` exposes `ingest_specos_repo(repo_path, doc_id=None, mode="importer")`.
- `src/spec_os/cli.py` exposes `--specos-repo` and `--specos-repo-mode` for importing or compiling a repo checkout without first converting it to MHTML.

## Current mapping

- `artifacts/spec_os_import_manifest.json` in the spec repo is the preferred import entrypoint.
- `artifacts/api_contracts.json` -> `domain/api_contracts.json`
- `artifacts/schema.json` + `artifacts/canonical_schema.json` -> `domain/schema.json` and `domain/canonical_schema.json`
- `artifacts/computation_graph.json` + `artifacts/variable_registry.json` + `artifacts/variable_mapping.json` -> `domain/computation_graph.json` and `system/execution_plan.json`
- `validation/*.json` -> native `validation/*.json`, with richer source details preserved in `system_spec.json -> validation -> source_validation`

## Repo modes

- `importer` is the stable default. It reads the checked-in RC artifact pack and returns `status: "imported"` with `import_mode: "modelling_engine_specos"`.
- `compiler` is experimental and opt-in. It recompiles the artifact pack from the phase specs, then normalizes that result into the standard Spec-OS bundle. It returns `status: "compiled"`, `import_mode: "modelling_engine_specos_compiler"`, and `compiler_mode: "shadow_phase_spec_compiler"`.
- Both modes write the same Spec-OS bundle layout and the same `<doc_id>_spec/` folder shape.
- The compiler path is for shadow validation and comparison work. It is not the authoritative production path yet.

## Current commands

Stable importer:

```bash
python -m spec_os.cli \
  --specos-repo /path/to/Modelling_Engine_SpecOS \
  --data-dir /path/to/output
```

Experimental compiler:

```bash
python -m spec_os.cli \
  --specos-repo /path/to/Modelling_Engine_SpecOS \
  --specos-repo-mode compiler \
  --data-dir /path/to/output
```

## Current status

- importer path is stable and remains the default
- compiler path exists beside it as an opt-in experimental entrypoint
- compiler parity is green against the checked-in RC pack, but cutover has not happened
- any future promotion should be gated by importer-vs-compiler diff review rather than replacing the importer implicitly
