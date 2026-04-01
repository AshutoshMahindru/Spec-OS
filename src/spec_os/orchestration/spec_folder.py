"""Generate the agent-ready ``<doc_id>_spec/`` folder."""

from __future__ import annotations

import json
from pathlib import Path

_AGENTS_MD = """\
# AGENTS.md

## System: Spec Compiler for Business Systems

### Rules
- Never infer missing schema
- Always use variable_registry.json as source of truth
- APIs must map to canonical_schema
- Follow execution_plan.json strictly

### Commands
- Build backend from api_contracts.json
- Build DB from canonical_schema.json
- Build computation engine from computation_graph.json

### Constraints
- No variable without storage mapping
- No API without schema binding
- No metric without dependencies
"""

_REQUIREMENTS_MD = """\
# requirements.md

## Core Capability
Multi-document ingestion -> unified executable spec

## Features
- MHTML ingestion
- Graph extraction
- Schema generation
- API extraction
- Computation DAG

## Acceptance
- Spec completeness = true
- No blocking issues
"""

_ARCHITECTURE_MD = """\
# architecture.md

## Layers
- Ingestion
- Extraction
- Normalization
- Reconciliation
- Integration
- Completeness

## Flow
Documents -> Graph -> Spec -> Code
"""

_BUILD_PLAN_MD = """\
# build_plan.md

## Phase 1
- Schema
- DB

## Phase 2
- APIs
- Services

## Phase 3
- Computation engine

## Phase 4
- UI integration
"""


def generate_spec_folder(base_dir: Path, doc_id: str, merged_outputs: dict) -> Path:
    """Write the ``<doc_id>_spec/`` folder and return its path."""
    spec_dir = base_dir / f"{doc_id}_spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    (spec_dir / "AGENTS.md").write_text(_AGENTS_MD)
    (spec_dir / "requirements.md").write_text(_REQUIREMENTS_MD)
    (spec_dir / "architecture.md").write_text(_ARCHITECTURE_MD)
    (spec_dir / "build_plan.md").write_text(_BUILD_PLAN_MD)

    for key, filename in (
        ("schema", "canonical_schema.json"),
        ("api_contracts", "api_contracts.json"),
        ("computation_graph", "computation_graph.json"),
        ("execution_plan", "execution_plan.json"),
    ):
        (spec_dir / filename).write_text(json.dumps(merged_outputs.get(key, {}), indent=2))

    return spec_dir
