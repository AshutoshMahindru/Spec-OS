"""Import a Modelling_Engine_SpecOS repo into the standard Spec-OS bundle."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from spec_os.api.contracts import bind_api_to_schema
from spec_os.artifacts import (
    EmbeddingStatusModel,
    ExecutionPlanModel,
    ReconciliationModel,
    SystemSpecModel,
    TraceabilityRowModel,
)
from spec_os.helpers import normalize_name
from spec_os.schema.enrichment import enrich_schema_types
from spec_os.visualization import generate_mermaid_diagrams

DEFAULT_IMPORT_MANIFEST: dict[str, Any] = {
    "meta": {
        "version": "1.0",
        "consumer": "Spec-OS",
        "import_strategy": "artifact_pack",
    },
    "recommended_doc_id": "modelling_engine_specos_rc",
    "phase_specs": [
        "specos/phase_1_foundation_contracts.specos.json",
        "specos/phase_2_planning_spine_inputs.specos.json",
        "specos/phase_3_assumptions_compute.specos.json",
        "specos/phase_4_financial_outputs.specos.json",
        "specos/phase_5_interpretation_trust.specos.json",
        "specos/phase_6_migration_verification_rollout.specos.json",
    ],
    "json_artifacts": {
        "canonical_model": "artifacts/canonical_model.json",
        "canonical_schema": "artifacts/canonical_schema.json",
        "schema": "artifacts/schema.json",
        "api_contracts": "artifacts/api_contracts.json",
        "computation_graph": "artifacts/computation_graph.json",
        "variable_registry": "artifacts/variable_registry.json",
        "variable_mapping": "artifacts/variable_mapping.json",
        "traceability": "artifacts/traceability.json",
        "roadmap": "artifacts/roadmap.json",
        "document_lineage": "artifacts/document_lineage.json",
        "system_spec": "artifacts/system_spec.json",
        "graph_validation": "validation/graph_validation.json",
        "computation_validation": "validation/computation_validation.json",
        "completeness": "validation/completeness.json",
        "reconciliation": "validation/reconciliation.json",
        "issue_catalog": "validation/issue_catalog.json",
        "review_decisions": "validation/review_decisions.json",
        "spec_score": "validation/spec_score.json",
    },
    "text_artifacts": {
        "ddl_sql": "artifacts/ddl.sql",
    },
}


def build_modelling_engine_specos_import(repo_path: str | Path, doc_id: str | None = None) -> dict[str, Any]:
    """Return a normalized Spec-OS bundle built from a SpecOS repo checkout."""
    repo_root = Path(repo_path).expanduser().resolve()
    manifest = _load_manifest(repo_root)

    source = {
        name: _load_json(repo_root / relative_path)
        for name, relative_path in manifest["json_artifacts"].items()
    }
    source_text = {
        name: _load_text(repo_root / relative_path)
        for name, relative_path in manifest["text_artifacts"].items()
    }

    resolved_doc_id = doc_id or _default_doc_id(repo_root, manifest, source["spec_score"])
    api_contracts = _normalize_api_contracts(source["api_contracts"], source["schema"])
    schema = _normalize_schema(source["schema"], api_contracts, source["variable_registry"])
    variable_registry = _normalize_variable_registry(source["variable_registry"])
    canonical_schema = _normalize_canonical_schema(schema, variable_registry, source["canonical_schema"])
    execution_plan = _normalize_execution_plan(source["computation_graph"])
    computation_graph = _normalize_computation_graph(
        source["computation_graph"],
        variable_registry,
        source["variable_mapping"],
        execution_plan,
    )
    graph = _normalize_graph(source["computation_graph"])
    graph_validation = _normalize_graph_validation(source["graph_validation"])
    computation_validation = _normalize_computation_validation(source["computation_validation"])
    issue_catalog = source["issue_catalog"]
    reconciliation = _normalize_reconciliation(source["reconciliation"], issue_catalog)
    spec_score = _normalize_spec_score(source["spec_score"])
    completeness = _normalize_completeness(source["completeness"], source["spec_score"], issue_catalog)
    variable_mapping = _normalize_variable_mapping(source["variable_mapping"])
    api_bindings = bind_api_to_schema(api_contracts, schema)
    canonical_model = _normalize_canonical_model(
        source["canonical_model"],
        source["canonical_schema"],
        variable_registry,
        api_contracts,
    )
    traceability = _normalize_traceability(source["traceability"])
    roadmap = _normalize_roadmap(source["roadmap"])
    embedding_status = EmbeddingStatusModel.model_validate(
        {
            "enabled": False,
            "requested_backend": "none",
            "actual_backend": "none",
            "available": False,
            "stored": False,
            "reason": "imported_spec_repo",
        }
    ).model_dump(mode="json")
    mermaid = generate_mermaid_diagrams(graph, computation_graph)
    source_documents = _build_source_documents(manifest)
    structured = {
        "structured": [],
        "chunks": [],
        "source_documents": source_documents,
        "source_repo": {
            "name": repo_root.name,
            "path": str(repo_root),
            "import_strategy": manifest["meta"]["import_strategy"],
        },
        "phase_specs": manifest["phase_specs"],
    }
    system_spec = SystemSpecModel.model_validate(
        {
            "meta": {
                "doc_id": resolved_doc_id,
                "doc_type": "SPECOS_REPO",
                "spec_score": spec_score["score"],
                "ready_for_codegen": completeness["ready_for_codegen"],
                "embedding_backend": embedding_status["actual_backend"],
            },
            "sources": source_documents,
            "canonical": canonical_model,
            "data_model": {"schema": canonical_schema, "ddl": source_text["ddl_sql"]},
            "application": {"apis": api_contracts, "bindings": api_bindings},
            "computation": {"graph": computation_graph, "execution_plan": execution_plan},
            "runtime": {
                "variable_mapping": variable_mapping,
                "embeddings": embedding_status,
                "source_repo": {
                    "name": repo_root.name,
                    "manifest_version": manifest["meta"]["version"],
                },
            },
            "validation": {
                "reconciliation": reconciliation,
                "completeness": completeness,
                "source_validation": {
                    "spec_score": source["spec_score"],
                    "completeness": source["completeness"],
                    "reconciliation": source["reconciliation"],
                    "issue_catalog": issue_catalog,
                    "review_decisions": source["review_decisions"],
                    "graph_validation": source["graph_validation"],
                    "computation_validation": source["computation_validation"],
                },
            },
        }
    ).model_dump(mode="json")

    bundle = {
        "structured": structured,
        "graph": graph,
        "graph_validation": graph_validation,
        "canonical_model": canonical_model,
        "computation_validation": computation_validation,
        "schema": schema,
        "roadmap": roadmap,
        "traceability": traceability,
        "computation_graph": computation_graph,
        "api_contracts": api_contracts,
        "variable_registry": variable_registry,
        "canonical_schema": canonical_schema,
        "reconciliation": reconciliation,
        "variable_mapping": variable_mapping,
        "execution_plan": execution_plan,
        "api_bindings": api_bindings,
        "spec_score": spec_score,
        "completeness": completeness,
        "mermaid": mermaid,
        "ddl_sql": source_text["ddl_sql"],
        "embedding_status": embedding_status,
        "system_spec": system_spec,
    }

    return {
        "doc_id": resolved_doc_id,
        "doc_type": "SPECOS_REPO",
        "bundle": bundle,
        "spec_folder_payload": {
            "schema": canonical_schema,
            "api_contracts": api_contracts,
            "computation_graph": computation_graph,
            "execution_plan": execution_plan,
        },
        "counts": {
            "graph_nodes": len(graph["nodes"]),
            "graph_edges": len(graph["edges"]),
            "schema_models": len(schema.get("models", [])),
            "schema_apis": len(schema.get("apis", [])),
            "traceability_rows": len(traceability),
            "metrics": len(computation_graph.get("metrics", [])),
            "apis": len(api_contracts),
            "variables": len(variable_registry.get("variables", [])),
            "reconciliation_issues": len(reconciliation.get("issues", [])),
            "spec_score": spec_score["score"],
            "ready_for_codegen": completeness["ready_for_codegen"],
        },
    }


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / "artifacts" / "spec_os_import_manifest.json"
    if not manifest_path.exists():
        return DEFAULT_IMPORT_MANIFEST
    return _load_json(manifest_path)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _default_doc_id(repo_root: Path, manifest: dict[str, Any], spec_score: dict[str, Any]) -> str:
    recommended = manifest.get("recommended_doc_id")
    if recommended:
        content_hash = spec_score.get("meta", {}).get("content_hash")
        if content_hash:
            return f"{normalize_name(recommended)}_{content_hash[:8]}"
        return normalize_name(recommended)
    return normalize_name(repo_root.name)


def _normalize_api_contracts(payload: dict[str, Any], schema_payload: dict[str, Any]) -> list[dict[str, Any]]:
    model_names = [entity.get("entity_name", "") for entity in schema_payload.get("entities", [])]
    contracts: list[dict[str, Any]] = []
    for endpoint in payload.get("endpoints", []):
        response_model = _guess_response_model(endpoint, model_names)
        contracts.append(
            {
                "endpoint": endpoint.get("path", ""),
                "method": endpoint.get("method", "GET"),
                "request": _build_request_contract(endpoint),
                "response": {"data": response_model} if response_model else {},
                "headers": {"X-SpecOS-Source": "Modelling_Engine_SpecOS"},
                "citations": endpoint.get("requirement_families", []),
                "owner_doc": endpoint.get("owner_doc"),
                "phase_number": endpoint.get("phase_number"),
                "domain_family": endpoint.get("domain_family"),
            }
        )
    return contracts


def _build_request_contract(endpoint: dict[str, Any]) -> dict[str, Any]:
    method = endpoint.get("method", "GET").upper()
    request_contract: dict[str, Any] = {"planning_context": "required"}
    if method == "GET":
        request_contract["query"] = {"companyId": "uuid", "scenarioId": "uuid|null", "versionId": "uuid|null"}
    else:
        request_contract["body"] = {"planning_context": "object", "payload": "object"}
    return request_contract


def _guess_response_model(endpoint: dict[str, Any], model_names: list[str]) -> str | None:
    normalized_models = {normalize_name(name): name for name in model_names if name}
    path_tokens = [
        normalize_name(token)
        for token in endpoint.get("path", "").replace(":", "").split("/")
        if token and token not in {"api", "v1"}
    ]
    best_match = ""
    best_score = 0
    for normalized, original in normalized_models.items():
        score = len(set(path_tokens) & set(normalized.split("_")))
        if score > best_score:
            best_match = original
            best_score = score

    if best_match:
        return best_match

    fallback_by_family = {
        "context": "planning_context",
        "scope": "scope_bundles",
        "decisions": "decision_logs",
        "assumptions": "assumption_sets",
        "compute": "compute_runs",
        "financials": "pnl_projections",
        "analysis": "analysis_views",
        "confidence": "dqi_scores",
        "governance": "approval_workflows",
        "reference": "reference_data",
        "ai": "ai_sessions",
    }
    family = endpoint.get("domain_family", "")
    fallback = fallback_by_family.get(family)
    if fallback and fallback in normalized_models:
        return normalized_models[fallback]
    if family == "context":
        return "planning_context"
    return None


def _normalize_schema(
    payload: dict[str, Any],
    api_contracts: list[dict[str, Any]],
    variable_registry: dict[str, Any],
) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    planning_context = payload.get("planning_context", {})
    required_fields = planning_context.get("required_fields", [])
    if required_fields:
        models.append(
            {
                "name": "planning_context",
                "fields": [
                    {
                        "name": field["name"],
                        "data_type": _format_type(field.get("type")),
                        "nullable": _is_nullable(field.get("type")),
                    }
                    for field in required_fields
                ],
            }
        )

    for entity in payload.get("entities", []):
        models.append(
            {
                "name": entity.get("entity_name"),
                "fields": [
                    {"name": field_name, "data_type": "text", "nullable": True}
                    for field_name in entity.get("fields", [])
                ],
                "phase_number": entity.get("phase_number"),
                "requirement_families": entity.get("requirement_families", []),
            }
        )

    schema = {
        "models": models,
        "apis": [
            {
                "endpoint": api.get("endpoint"),
                "method": api.get("method"),
                "group": api.get("domain_family"),
            }
            for api in api_contracts
        ],
        "variables": variable_registry.get("variables", []),
        "planning_context": planning_context,
    }
    return enrich_schema_types(schema)


def _normalize_variable_registry(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "variables": [
            {
                "name": variable.get("name"),
                "raw_name": variable.get("name"),
                "variable_type": variable.get("class", "unknown"),
                "mapped_table": variable.get("mapped_table"),
            }
            for variable in payload.get("variables", [])
        ],
        "metrics": [
            {
                "metric": metric.get("id"),
                "formula": metric.get("formula"),
                "phase_number": metric.get("phase_number"),
                "requirement_families": metric.get("requirement_families", []),
                "owner_doc": metric.get("owner_doc"),
            }
            for metric in payload.get("metrics", [])
        ],
    }


def _normalize_canonical_schema(
    schema: dict[str, Any],
    variable_registry: dict[str, Any],
    canonical_schema_payload: dict[str, Any],
) -> dict[str, Any]:
    source_entities = {item.get("entity_name"): item for item in canonical_schema_payload.get("entities", [])}
    entities = []
    for model in schema.get("models", []):
        source_entity = source_entities.get(model.get("name"), {})
        entities.append(
            {
                "name": model.get("name"),
                "fields": model.get("fields", []),
                "model_type": model.get("model_type", "unknown"),
                "phase_number": source_entity.get("phase_number"),
                "requirement_families": source_entity.get("requirement_families", []),
            }
        )
    return {"entities": entities, "variables": variable_registry.get("variables", [])}


def _normalize_execution_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return ExecutionPlanModel.model_validate(
        {
            "execution_steps": [
                {"step": index, "compute": name, "inputs": []}
                for index, name in enumerate(payload.get("execution_plan", []), start=1)
            ],
            "issues": [],
            "status": "ok",
        }
    ).model_dump(mode="json")


def _normalize_computation_graph(
    payload: dict[str, Any],
    variable_registry: dict[str, Any],
    variable_mapping_payload: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, Any]:
    related_metrics: dict[str, list[str]] = {}
    for mapping in variable_mapping_payload.get("mappings", []):
        for metric in mapping.get("related_metrics", []):
            related_metrics.setdefault(metric, []).append(mapping.get("variable_name", ""))

    metrics = []
    for metric in variable_registry.get("metrics", []):
        metric_name = metric.get("metric", "")
        dependencies = related_metrics.get(metric_name, [])
        if not dependencies:
            dependencies = _extract_formula_dependencies(metric.get("formula", ""))
        metrics.append(
            {
                "metric": metric_name,
                "depends_on": dependencies,
                "formula": metric.get("formula"),
                "phase_number": metric.get("phase_number"),
            }
        )

    return {
        "metrics": metrics,
        "graph": payload.get("graph", {}),
        "execution_plan": execution_plan.get("execution_steps", []),
        "freshness_rule": payload.get("freshness_rule"),
    }


def _extract_formula_dependencies(formula: str) -> list[str]:
    if not formula:
        return []
    tokens = [token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula) if token.lower() not in {"weighted_average"}]
    return [normalize_name(token) for token in tokens]


def _normalize_graph(payload: dict[str, Any]) -> dict[str, Any]:
    graph = payload.get("graph", {})
    nodes = [
        {"id": node, "type": "ComputeNode", "name": node}
        for node in graph.get("nodes", [])
    ]
    edges = [
        {"from": edge[0], "to": edge[1], "type": "DEPENDS_ON"}
        for edge in graph.get("edges", [])
    ]
    return {"nodes": nodes, "edges": edges, "source": "modelling_engine_specos"}


def _normalize_graph_validation(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "issues": payload.get("issues", []),
        "status": "ok" if payload.get("overall_status") == "pass" else "invalid",
        "node_count": payload.get("node_count"),
        "edge_count": payload.get("edge_count"),
    }


def _normalize_computation_validation(payload: dict[str, Any]) -> dict[str, Any]:
    issues = [check for check in payload.get("checks", []) if check.get("status") != "pass"]
    return {
        "issues": issues,
        "status": "ok" if payload.get("overall_status") == "pass" else "invalid",
    }


def _normalize_reconciliation(
    payload: dict[str, Any],
    issue_catalog_payload: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()

    for check in payload.get("checks", []):
        if check.get("status") == "pass":
            continue
        issue_type = f"RECON_{normalize_name(check.get('check'))}".upper()
        if issue_type in seen:
            continue
        seen.add(issue_type)
        issues.append({"type": issue_type, "model": check.get("note") or check.get("check")})

    for issue in issue_catalog_payload.get("issues", []):
        if issue.get("severity") == "info":
            continue
        issue_type = issue.get("id")
        if not issue_type or issue_type in seen:
            continue
        seen.add(issue_type)
        issues.append({"type": issue_type, "model": issue.get("category")})

    return ReconciliationModel.model_validate(
        {"issues": issues, "status": "ok" if not issues else "needs_review"}
    ).model_dump(mode="json")


def _normalize_spec_score(payload: dict[str, Any]) -> dict[str, Any]:
    ratio = payload.get("overall_score", 0)
    score = round(ratio * 100, 2) if isinstance(ratio, (int, float)) and ratio <= 1 else ratio
    return {
        "score": score,
        "score_ratio": ratio,
        "warnings": payload.get("warnings", 0),
        "blocking_issues": payload.get("blocking_issues", 0),
        "status": payload.get("meta", {}).get("status"),
    }


def _normalize_completeness(
    completeness_payload: dict[str, Any],
    spec_score_payload: dict[str, Any],
    issue_catalog_payload: dict[str, Any],
) -> dict[str, Any]:
    blocking = [
        issue.get("message")
        for issue in issue_catalog_payload.get("issues", [])
        if issue.get("severity") in {"error", "fatal"}
    ]
    warnings = [
        issue.get("message")
        for issue in issue_catalog_payload.get("issues", [])
        if issue.get("severity") == "warning"
    ]
    actual = completeness_payload.get("actual_counts", {})
    return {
        "blocking_issues": blocking,
        "warnings": warnings,
        "ready_for_codegen": bool(spec_score_payload.get("ready_for_codegen", False)),
        "completeness": {
            "variables": actual.get("variables", 0),
            "schema": actual.get("schema_entities", 0),
            "apis": actual.get("apis", 0),
            "metrics": actual.get("metrics", 0),
            "screens": actual.get("screens", 0),
            "routes": actual.get("routes", 0),
        },
        "source_authoritative_counts": completeness_payload.get("authoritative_counts", {}),
        "deltas": completeness_payload.get("deltas", {}),
        "notes": completeness_payload.get("notes", []),
    }


def _normalize_variable_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        normalize_name(item.get("variable_name")): {
            "table": item.get("mapped_table"),
            "field": "value",
            "display_name": item.get("variable_name"),
            "source_phase": item.get("source_phase"),
            "related_metrics": item.get("related_metrics", []),
        }
        for item in payload.get("mappings", [])
        if item.get("variable_name")
    }


def _normalize_canonical_model(
    payload: dict[str, Any],
    canonical_schema_payload: dict[str, Any],
    variable_registry: dict[str, Any],
    api_contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    entities = [
        {
            "name": entity.get("entity_name"),
            "type": "DataModel",
            "phase_number": entity.get("phase_number"),
            "requirement_families": entity.get("requirement_families", []),
            "fields": entity.get("fields", []),
        }
        for entity in canonical_schema_payload.get("entities", [])
    ]
    entities.extend(
        {
            "name": api.get("endpoint"),
            "type": "API",
            "endpoint": api.get("endpoint"),
            "method": api.get("method"),
            "citations": api.get("citations", []),
        }
        for api in api_contracts
    )
    return {
        "stages": payload.get("canonical_stage_model", []),
        "requirement_families": payload.get("requirement_families", []),
        "entities": entities,
        "variables": variable_registry.get("variables", []),
        "metrics": variable_registry.get("metrics", []),
        "shared_planning_context": payload.get("shared_planning_context", {}),
        "governance_state_machine": payload.get("governance_state_machine", {}),
        "api_namespace_model": payload.get("api_namespace_model", {}),
    }


def _normalize_traceability(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for collection_name in ("apis", "routes", "entities", "metrics", "screens"):
        for item in payload.get(collection_name, []):
            rows.append(
                TraceabilityRowModel.model_validate(
                    {
                        "source_section": item.get("ownerDoc") or collection_name,
                        "artifact_type": item.get("artifactType", collection_name[:-1]),
                        "artifact_name": item.get("artifactName"),
                        "status": "imported",
                        "citations": [
                            {"source_tag": citation, "text": citation}
                            for citation in item.get("citations", [])
                        ],
                    }
                ).model_dump(mode="json")
            )
    return rows


def _normalize_roadmap(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("waves", [])


def _build_source_documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"source": path, "doc_type": "PHASE_SPEC"} for path in manifest.get("phase_specs", [])]


def _format_type(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value or "text")


def _is_nullable(value: Any) -> bool:
    if isinstance(value, list):
        return "null" in value
    return value == "null"
