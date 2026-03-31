"""Traceability matrix and engineering roadmap generators."""

from __future__ import annotations


def build_traceability_matrix(structured: list[dict], graph: dict, doc_type: str) -> list[dict]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {n["id"]: n for n in nodes}
    matrix: list[dict] = []

    traceable_types = {
        "Feature", "Constraint", "API", "DataModel", "Metric",
        "Variable", "Workflow", "UIComponent", "Service", "UserRole",
    }

    for edge in edges:
        if edge["type"] != "CONTAINS":
            continue
        src = node_map.get(edge["from"])
        dst = node_map.get(edge["to"])
        if not src or not dst or src.get("type") != "Section":
            continue
        if dst.get("type") in traceable_types:
            matrix.append({
                "source_section": src.get("title"),
                "artifact_type": dst.get("type"),
                "artifact_name": dst.get("name") or dst.get("endpoint") or dst.get("formula") or dst.get("description"),
                "status": "extracted",
            })

    if not matrix:
        for sec in structured:
            if sec.get("type") == "heading":
                matrix.append({
                    "source_section": sec.get("text"),
                    "artifact_type": doc_type,
                    "artifact_name": sec.get("text"),
                    "status": "indexed",
                })

    return matrix


def build_engineering_roadmap(graph: dict, doc_type: str) -> dict:
    nodes = graph.get("nodes", [])
    features = [n.get("name") for n in nodes if n["type"] == "Feature"]
    apis = [n.get("endpoint") for n in nodes if n["type"] == "API"]
    models = [n.get("name") for n in nodes if n["type"] == "DataModel"]
    workflows = [n.get("name") for n in nodes if n["type"] == "Workflow"]

    phase2 = features[:8] or workflows[:8] or ["Core business features from extracted requirements"]
    phase3 = apis[:10] or (
        models[:10]
        if doc_type != "PRD"
        else ["planning_context", "driver_assumption", "computed_metric", "workflow_definition"]
    )

    return {
        "doc_type": doc_type,
        "phases": [
            {
                "phase": "Phase 1 - Foundations",
                "deliverables": [
                    "Document ingestion and classification",
                    "Canonical graph generation",
                    "Baseline schema and DDL starter scripts",
                ],
            },
            {"phase": "Phase 2 - Core domain implementation", "deliverables": phase2},
            {"phase": "Phase 3 - Interface and data contracts", "deliverables": phase3},
            {
                "phase": "Phase 4 - Validation and traceability",
                "deliverables": [
                    "Cross-document reconciliation",
                    "Traceability matrix",
                    "Execution-readiness review",
                ],
            },
        ],
    }
