"""Experimental compiler-backed import for Modelling_Engine_SpecOS repos."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spec_os.artifacts import EmbeddingStatusModel, SystemSpecModel
from spec_os.compiler.emitters import (
    compile_api_contracts_artifact,
    compile_canonical_schema_artifact,
    compile_completeness_artifact,
    compile_computation_graph_artifact,
    compile_computation_validation_artifact,
    compile_document_lineage_artifact,
    compile_graph_validation_artifact,
    compile_issue_catalog_artifact,
    compile_reconciliation_artifact,
    compile_review_decisions_artifact,
    compile_roadmap_artifact,
    compile_spec_score_artifact,
    compile_system_spec_artifact,
    compile_traceability_artifact,
    compile_variable_mapping_artifact,
    compile_variable_registry_artifact,
)
from spec_os.compiler.specos_repo_loader import PHASE_FILES, load_specos_repo_ir
from spec_os.importers.modelling_engine_specos import (
    _build_source_documents,
    _load_manifest,
    _normalize_api_contracts,
    _normalize_canonical_model,
    _normalize_canonical_schema,
    _normalize_completeness,
    _normalize_computation_graph,
    _normalize_computation_validation,
    _normalize_execution_plan,
    _normalize_graph,
    _normalize_graph_validation,
    _normalize_reconciliation,
    _normalize_roadmap,
    _normalize_schema,
    _normalize_spec_score,
    _normalize_traceability,
    _normalize_variable_mapping,
    _normalize_variable_registry,
)
from spec_os.visualization import generate_mermaid_diagrams

COMPILER_MODE = "shadow_phase_spec_compiler"
IMPORT_MODE = "modelling_engine_specos_compiler"


def build_modelling_engine_specos_compiler_import(
    repo_path: str | Path,
    doc_id: str | None = None,
) -> dict[str, Any]:
    """Return a normalized Spec-OS bundle built from the phase-spec compiler."""
    repo_root = Path(repo_path).expanduser().resolve()
    manifest = _load_manifest(repo_root)
    ir = load_specos_repo_ir(repo_root)
    benchmark_doc_count = len(ir.phases["phase_1_foundation_contracts.specos.json"]["meta"]["benchmark_docs"])

    compiled = _compile_source_artifacts(ir, benchmark_doc_count)
    resolved_doc_id = doc_id or _default_compiler_doc_id(repo_root, manifest, ir)

    source_schema = {
        "planning_context": ir.phases["phase_1_foundation_contracts.specos.json"]["persistent_context_pack"].get(
            "shared_planning_context",
            {},
        ),
        "entities": compiled["canonical_schema"]["entities"],
    }
    normalized_variable_registry = _normalize_variable_registry(compiled["variable_registry"])
    normalized_api_contracts = _normalize_api_contracts(compiled["api_contracts"], source_schema)
    normalized_schema = _normalize_schema(source_schema, normalized_api_contracts, normalized_variable_registry)
    normalized_canonical_schema = _normalize_canonical_schema(
        normalized_schema,
        normalized_variable_registry,
        compiled["canonical_schema"],
    )
    normalized_execution_plan = _normalize_execution_plan(compiled["computation_graph"])
    normalized_computation_graph = _normalize_computation_graph(
        compiled["computation_graph"],
        normalized_variable_registry,
        compiled["variable_mapping"],
        normalized_execution_plan,
    )
    normalized_graph = _normalize_graph(compiled["computation_graph"])
    normalized_graph_validation = _normalize_graph_validation(compiled["graph_validation"])
    normalized_computation_validation = _normalize_computation_validation(compiled["computation_validation"])
    normalized_reconciliation = _normalize_reconciliation(compiled["reconciliation"], compiled["issue_catalog"])
    normalized_spec_score = _normalize_spec_score(compiled["spec_score"])
    normalized_completeness = _normalize_completeness(
        compiled["completeness"],
        compiled["spec_score"],
        compiled["issue_catalog"],
    )
    normalized_variable_mapping = _normalize_variable_mapping(compiled["variable_mapping"])
    normalized_canonical_model = _normalize_canonical_model(
        _canonical_model_source(ir),
        compiled["canonical_schema"],
        normalized_variable_registry,
        normalized_api_contracts,
    )
    normalized_traceability = _normalize_traceability(compiled["traceability"])
    normalized_roadmap = _normalize_roadmap(compiled["roadmap"])

    embedding_status = EmbeddingStatusModel.model_validate(
        {
            "enabled": False,
            "requested_backend": "none",
            "actual_backend": "none",
            "available": False,
            "stored": False,
            "reason": "compiled_spec_repo",
        }
    ).model_dump(mode="json")
    mermaid = generate_mermaid_diagrams(normalized_graph, normalized_computation_graph)
    source_documents = _build_source_documents(manifest)

    structured = {
        "structured": [],
        "chunks": [],
        "source_documents": source_documents,
        "source_repo": {
            "name": repo_root.name,
            "path": str(repo_root),
            "import_strategy": "phase_spec_compiler",
            "compiler_mode": COMPILER_MODE,
        },
        "phase_specs": manifest.get("phase_specs", [f"specos/{name}" for name in PHASE_FILES]),
    }
    ddl_sql = _load_optional_text(repo_root, manifest.get("text_artifacts", {}).get("ddl_sql"))
    system_spec = SystemSpecModel.model_validate(
        {
            "meta": {
                "doc_id": resolved_doc_id,
                "doc_type": "SPECOS_REPO",
                "spec_score": normalized_spec_score["score"],
                "ready_for_codegen": normalized_completeness["ready_for_codegen"],
                "embedding_backend": embedding_status["actual_backend"],
            },
            "sources": source_documents,
            "canonical": normalized_canonical_model,
            "data_model": {"schema": normalized_canonical_schema, "ddl": ddl_sql},
            "application": {"apis": normalized_api_contracts, "bindings": []},
            "computation": {
                "graph": normalized_computation_graph,
                "execution_plan": normalized_execution_plan,
            },
            "runtime": {
                "variable_mapping": normalized_variable_mapping,
                "embeddings": embedding_status,
                "source_repo": {
                    "name": repo_root.name,
                    "manifest_version": manifest["meta"]["version"],
                    "import_strategy": "phase_spec_compiler",
                    "compiler_mode": COMPILER_MODE,
                },
            },
            "validation": {
                "reconciliation": normalized_reconciliation,
                "completeness": normalized_completeness,
                "source_validation": {
                    "spec_score": compiled["spec_score"],
                    "completeness": compiled["completeness"],
                    "reconciliation": compiled["reconciliation"],
                    "issue_catalog": compiled["issue_catalog"],
                    "review_decisions": compiled["review_decisions"],
                    "graph_validation": compiled["graph_validation"],
                    "computation_validation": compiled["computation_validation"],
                    "document_lineage": compiled["document_lineage"],
                    "system_spec": compiled["source_system_spec"],
                },
            },
        }
    ).model_dump(mode="json")

    bundle = {
        "structured": structured,
        "graph": normalized_graph,
        "graph_validation": normalized_graph_validation,
        "canonical_model": normalized_canonical_model,
        "computation_validation": normalized_computation_validation,
        "schema": normalized_schema,
        "roadmap": normalized_roadmap,
        "traceability": normalized_traceability,
        "computation_graph": normalized_computation_graph,
        "api_contracts": normalized_api_contracts,
        "variable_registry": normalized_variable_registry,
        "canonical_schema": normalized_canonical_schema,
        "reconciliation": normalized_reconciliation,
        "variable_mapping": normalized_variable_mapping,
        "execution_plan": normalized_execution_plan,
        "api_bindings": [],
        "spec_score": normalized_spec_score,
        "completeness": normalized_completeness,
        "mermaid": mermaid,
        "ddl_sql": ddl_sql,
        "embedding_status": embedding_status,
        "system_spec": system_spec,
    }

    return {
        "doc_id": resolved_doc_id,
        "doc_type": "SPECOS_REPO",
        "bundle": bundle,
        "spec_folder_payload": {
            "schema": normalized_canonical_schema,
            "api_contracts": normalized_api_contracts,
            "computation_graph": normalized_computation_graph,
            "execution_plan": normalized_execution_plan,
        },
        "counts": {
            "graph_nodes": len(normalized_graph["nodes"]),
            "graph_edges": len(normalized_graph["edges"]),
            "schema_models": len(normalized_schema.get("models", [])),
            "schema_apis": len(normalized_schema.get("apis", [])),
            "traceability_rows": len(normalized_traceability),
            "metrics": len(normalized_computation_graph.get("metrics", [])),
            "apis": len(normalized_api_contracts),
            "variables": len(normalized_variable_registry.get("variables", [])),
            "reconciliation_issues": len(normalized_reconciliation.get("issues", [])),
            "spec_score": normalized_spec_score["score"],
            "ready_for_codegen": normalized_completeness["ready_for_codegen"],
        },
        "compiler_mode": COMPILER_MODE,
    }


def _compile_source_artifacts(ir: Any, benchmark_doc_count: int) -> dict[str, Any]:
    api_contracts = compile_api_contracts_artifact(ir)
    canonical_schema = compile_canonical_schema_artifact(ir)
    computation_graph = compile_computation_graph_artifact(ir)
    variable_registry = compile_variable_registry_artifact(ir)
    variable_mapping = compile_variable_mapping_artifact(ir)
    traceability = compile_traceability_artifact(ir)
    roadmap = compile_roadmap_artifact(ir)
    document_lineage = compile_document_lineage_artifact(ir)
    graph_validation = compile_graph_validation_artifact(ir, computation_graph)
    computation_validation = compile_computation_validation_artifact(ir, computation_graph)
    completeness = compile_completeness_artifact(ir, ir.inventory.counts, benchmark_doc_count)
    reconciliation = compile_reconciliation_artifact(ir, completeness, computation_graph, benchmark_doc_count)
    issue_catalog = compile_issue_catalog_artifact(ir, completeness, reconciliation)
    review_decisions = compile_review_decisions_artifact(ir)
    spec_score = compile_spec_score_artifact(
        ir,
        completeness,
        reconciliation,
        traceability,
        graph_validation,
        computation_validation,
        issue_catalog,
    )
    source_system_spec = compile_system_spec_artifact(ir)
    return {
        "api_contracts": api_contracts,
        "canonical_schema": canonical_schema,
        "computation_graph": computation_graph,
        "variable_registry": variable_registry,
        "variable_mapping": variable_mapping,
        "traceability": traceability,
        "roadmap": roadmap,
        "document_lineage": document_lineage,
        "graph_validation": graph_validation,
        "computation_validation": computation_validation,
        "completeness": completeness,
        "reconciliation": reconciliation,
        "issue_catalog": issue_catalog,
        "review_decisions": review_decisions,
        "spec_score": spec_score,
        "source_system_spec": source_system_spec,
    }


def _canonical_model_source(ir: Any) -> dict[str, Any]:
    context_pack = ir.phases["phase_1_foundation_contracts.specos.json"]["persistent_context_pack"]
    return {
        "canonical_stage_model": context_pack.get("canonical_stage_model", []),
        "requirement_families": context_pack.get("requirement_families", []),
        "shared_planning_context": context_pack.get("shared_planning_context", {}),
        "governance_state_machine": context_pack.get("governance_state_machine", {}),
        "api_namespace_model": context_pack.get("api_namespace_model", {}),
    }


def _default_compiler_doc_id(repo_root: Path, manifest: dict[str, Any], ir: Any) -> str:
    recommended = manifest.get("recommended_doc_id") or repo_root.name
    digest = hashlib.sha256()
    for filename in PHASE_FILES:
        digest.update(json.dumps(ir.phases[filename], sort_keys=True).encode("utf-8"))
    return f"{recommended}_compiler_{digest.hexdigest()[:8]}"


def _load_optional_text(repo_root: Path, relative_path: str | None) -> str:
    if not relative_path:
        return ""
    path = repo_root / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
