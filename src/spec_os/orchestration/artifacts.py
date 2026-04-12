"""Traceability matrix and engineering roadmap generators."""

from __future__ import annotations

from collections import Counter


def build_traceability_matrix(structured: list[dict], graph: dict, doc_type: str) -> list[dict]:
    """Build a traceability matrix that also reports uncovered sections and orphan artifacts."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {n["id"]: n for n in nodes}
    matrix: list[dict] = []

    traceable_types = {
        "Feature", "Constraint", "API", "DataModel", "Metric",
        "Variable", "Workflow", "UIComponent", "Service", "UserRole",
    }

    # Track which sections have traceable links and which artifacts are linked.
    sections_with_links: set[str] = set()
    linked_artifact_ids: set[str] = set()

    for edge in edges:
        if edge["type"] != "CONTAINS":
            continue
        src = node_map.get(edge["from"])
        dst = node_map.get(edge["to"])
        if not src or not dst or src.get("type") != "Section":
            continue
        if dst.get("type") in traceable_types:
            sections_with_links.add(edge["from"])
            linked_artifact_ids.add(edge["to"])
            matrix.append({
                "source_section": src.get("title"),
                "artifact_type": dst.get("type"),
                "artifact_name": dst.get("name") or dst.get("endpoint") or dst.get("formula") or dst.get("description"),
                "status": "extracted",
                "citations": dst.get("citations", src.get("citations", [])),
            })

    # Fallback: if no CONTAINS edges produced entries, index headings.
    if not matrix:
        for sec in structured:
            if sec.get("type") == "heading":
                matrix.append({
                    "source_section": sec.get("text"),
                    "artifact_type": doc_type,
                    "artifact_name": sec.get("text"),
                    "status": "indexed",
                    "citations": [
                        {
                            "section_index": sec.get("source_span", {}).get("section_index"),
                            "source_tag": sec.get("source_span", {}).get("source_tag"),
                            "section_title": sec.get("text"),
                            "text": sec.get("text"),
                        }
                    ],
                })
        return matrix

    # Report uncovered sections (sections with no traceable artifact links).
    for node in nodes:
        if node.get("type") == "Section" and node["id"] not in sections_with_links:
            matrix.append({
                "source_section": node.get("title"),
                "artifact_type": "Section",
                "artifact_name": node.get("title"),
                "status": "uncovered",
                "citations": node.get("citations", []),
            })

    # Report orphan artifacts (traceable nodes not linked from any section).
    for node in nodes:
        if node.get("type") in traceable_types and node["id"] not in linked_artifact_ids:
            matrix.append({
                "source_section": None,
                "artifact_type": node.get("type"),
                "artifact_name": node.get("name") or node.get("endpoint") or node.get("formula") or node.get("description"),
                "status": "orphan",
                "citations": node.get("citations", []),
            })

    return matrix


def build_engineering_roadmap(graph: dict, doc_type: str) -> dict:
    """Build a roadmap with dependency-ranked phase deliverables."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    features = [n for n in nodes if n["type"] == "Feature"]
    apis = [n for n in nodes if n["type"] == "API"]
    models = [n for n in nodes if n["type"] == "DataModel"]
    workflows = [n for n in nodes if n["type"] == "Workflow"]

    # Count downstream dependants per node to prioritise high-impact items.
    dep_count: Counter[str] = Counter()
    for edge in edges:
        dep_count[edge.get("from", "")] += 1

    def _rank(node_list: list[dict]) -> list[str]:
        """Sort nodes by dependency count (desc) and return names."""
        return [
            n.get("name") or n.get("endpoint") or "unnamed"
            for n in sorted(node_list, key=lambda n: dep_count.get(n.get("id", ""), 0), reverse=True)
        ]

    ranked_features = _rank(features)
    ranked_apis = _rank(apis)
    ranked_models = _rank(models)
    ranked_workflows = _rank(workflows)

    phase2 = (ranked_features[:8] if ranked_features
              else ranked_workflows[:8] if ranked_workflows
              else ["Core business features from extracted requirements"])
    phase3 = (ranked_apis[:10] if ranked_apis
              else ranked_models[:10] if ranked_models and doc_type != "PRD"
              else ["planning_context", "driver_assumption", "computed_metric", "workflow_definition"])

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
