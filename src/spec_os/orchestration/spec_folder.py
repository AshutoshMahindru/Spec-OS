"""Generate the agent-ready ``<doc_id>_spec/`` folder."""

from __future__ import annotations

import json
from pathlib import Path


def _agents_md(merged_outputs: dict) -> str:
    """Generate AGENTS.md populated with actual spec data."""
    schema = merged_outputs.get("schema", {})
    api_contracts = merged_outputs.get("api_contracts", [])
    computation_graph = merged_outputs.get("computation_graph", {})

    entity_count = len(schema.get("entities", schema.get("models", [])))
    api_count = len(api_contracts) if isinstance(api_contracts, list) else 0
    metric_count = len(computation_graph.get("metrics", []))

    api_endpoints = ", ".join(
        c.get("endpoint", "?") for c in (api_contracts or [])[:8]
    ) or "none extracted"
    model_names = ", ".join(
        m.get("name", "?") for m in schema.get("entities", schema.get("models", []))[:8]
    ) or "none extracted"

    return f"""\
# AGENTS.md

## System: Spec Compiler for Business Systems

### Spec Summary
- **Schema entities**: {entity_count}
- **API contracts**: {api_count}
- **Computation metrics**: {metric_count}

### Rules
- Never infer missing schema
- Always use variable_registry.json as source of truth
- APIs must map to canonical_schema
- Follow execution_plan.json strictly

### Available Schema Models
{model_names}

### Available API Endpoints
{api_endpoints}

### Commands
- Build backend from api_contracts.json
- Build DB from canonical_schema.json
- Build computation engine from computation_graph.json

### Constraints
- No variable without storage mapping
- No API without schema binding
- No metric without dependencies
"""


def _requirements_md(merged_outputs: dict) -> str:
    """Generate requirements.md with actual completeness data."""
    computation_graph = merged_outputs.get("computation_graph", {})
    api_contracts = merged_outputs.get("api_contracts", [])
    schema = merged_outputs.get("schema", {})

    metric_names = [m.get("metric", "?") for m in computation_graph.get("metrics", [])]
    api_endpoints = [c.get("endpoint", "?") for c in (api_contracts or [])[:10]]
    model_names = [m.get("name", "?") for m in schema.get("entities", schema.get("models", []))[:10]]

    metrics_block = "\n".join(f"- {m}" for m in metric_names[:10]) or "- None extracted"
    apis_block = "\n".join(f"- {e}" for e in api_endpoints) or "- None extracted"
    models_block = "\n".join(f"- {n}" for n in model_names) or "- None extracted"

    return f"""\
# requirements.md

## Core Capability
Multi-document ingestion -> unified executable spec

## Features
- MHTML ingestion
- Graph extraction
- Schema generation
- API extraction
- Computation DAG

## Extracted Metrics
{metrics_block}

## Extracted API Endpoints
{apis_block}

## Extracted Data Models
{models_block}

## Acceptance
- Spec completeness = true
- No blocking issues
"""


def _architecture_md(merged_outputs: dict) -> str:
    """Generate architecture.md with pipeline layer summary."""
    schema = merged_outputs.get("schema", {})
    entity_count = len(schema.get("entities", schema.get("models", [])))
    api_count = len(merged_outputs.get("api_contracts", []) or [])
    metric_count = len(merged_outputs.get("computation_graph", {}).get("metrics", []))

    return f"""\
# architecture.md

## Layers
- Ingestion (MHTML parse + HTML clean)
- Extraction (classify + route + graph build)
- Normalization (canonical model + variable registry)
- Domain Modelling (schema: {entity_count} entities, APIs: {api_count}, metrics: {metric_count})
- Reconciliation (cross-layer validation)
- Integration (artifact bundle + spec folder)
- Completeness (quality scoring)

## Flow
Documents -> Graph -> Canonical Model -> Domain Artifacts -> Validated Spec -> Code
"""


def _build_plan_md(merged_outputs: dict) -> str:
    """Generate build_plan.md with data-driven phase summaries."""
    schema = merged_outputs.get("schema", {})
    api_contracts = merged_outputs.get("api_contracts", [])
    execution_plan = merged_outputs.get("execution_plan", {})

    model_names = [m.get("name", "?") for m in schema.get("entities", schema.get("models", []))[:6]]
    api_endpoints = [c.get("endpoint", "?") for c in (api_contracts or [])[:6]]
    exec_steps = execution_plan.get("execution_steps", [])

    models_block = "\n".join(f"- {n}" for n in model_names) or "- Generate from canonical_schema.json"
    apis_block = "\n".join(f"- {e}" for e in api_endpoints) or "- Generate from api_contracts.json"
    exec_block = "\n".join(
        f"- Step {s.get('step', '?')}: {s.get('compute', '?')}" for s in exec_steps[:8]
    ) or "- Execute from execution_plan.json"

    return f"""\
# build_plan.md

## Phase 1 - Schema & Database
{models_block}

## Phase 2 - API Services
{apis_block}

## Phase 3 - Computation Engine
{exec_block}

## Phase 4 - UI Integration & Validation
- Cross-document reconciliation
- Traceability matrix verification
- Execution-readiness review
"""


def generate_spec_folder(base_dir: Path, doc_id: str, merged_outputs: dict) -> Path:
    """Write the ``<doc_id>_spec/`` folder and return its path."""
    spec_dir = base_dir / f"{doc_id}_spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    (spec_dir / "AGENTS.md").write_text(_agents_md(merged_outputs))
    (spec_dir / "requirements.md").write_text(_requirements_md(merged_outputs))
    (spec_dir / "architecture.md").write_text(_architecture_md(merged_outputs))
    (spec_dir / "build_plan.md").write_text(_build_plan_md(merged_outputs))

    for key, filename in (
        ("schema", "canonical_schema.json"),
        ("api_contracts", "api_contracts.json"),
        ("computation_graph", "computation_graph.json"),
        ("execution_plan", "execution_plan.json"),
    ):
        (spec_dir / filename).write_text(json.dumps(merged_outputs.get(key, {}), indent=2))

    return spec_dir
