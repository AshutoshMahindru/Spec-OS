"""PRD-specific graph extractor."""

from __future__ import annotations

import re

from spec_os.constants import FEATURE_SECTION_KEYWORDS, VARIABLE_WHITELIST
from spec_os.graph import add_edge, ensure_node, make_citation, make_node_registry


def extract_prd_graph(structured: list[dict], doc_id: str) -> dict:
    nodes, node_index, edges = make_node_registry(doc_id)
    doc_node_id = f"doc_{doc_id}"
    current_section_id: str | None = None
    current_section_title = ""

    for i, sec in enumerate(structured):
        if sec["type"] == "heading":
            current_section_title = sec["text"]
            current_section_id = f"sec_{doc_id}_{i}"
            node = {
                "id": current_section_id,
                "type": "Section",
                "title": current_section_title,
                "level": sec.get("level", 1),
                "citations": [make_citation(sec, section_title=current_section_title)],
            }
            nodes.append(node)
            node_index[current_section_id] = node
            add_edge(edges, doc_node_id, current_section_id, "HAS_SECTION")

            title_lower = current_section_title.lower()
            if any(k in title_lower for k in FEATURE_SECTION_KEYWORDS):
                feature_id = ensure_node(
                    nodes,
                    node_index,
                    "Feature",
                    "name",
                    current_section_title,
                    citations=[make_citation(sec, section_title=current_section_title)],
                )
                add_edge(edges, current_section_id, feature_id, "CONTAINS")
            continue

        text = sec.get("text", "")
        text_lower = text.lower()
        section_title_lower = current_section_title.lower()
        citation = make_citation(sec, section_title=current_section_title)

        # -- out-of-scope / deferred constraints
        if any(kw in section_title_lower or kw in text_lower for kw in ("out-of-scope", "deferred", "does not belong", "explicitly deferred")):
            constraint_id = ensure_node(
                nodes,
                node_index,
                "Constraint",
                "description",
                text or current_section_title,
                citations=[citation],
            )
            if current_section_id:
                add_edge(edges, current_section_id, constraint_id, "CONTAINS")

        # -- user roles
        if section_title_lower == "primary users":
            role_name = text.split(":", 1)[0].strip()
            if role_name:
                role_id = ensure_node(nodes, node_index, "UserRole", "name", role_name, citations=[citation])
                if current_section_id:
                    add_edge(edges, current_section_id, role_id, "CONTAINS")

        # -- workflows
        if "steps" in text_lower and current_section_title:
            workflow_id = ensure_node(nodes, node_index, "Workflow", "name", current_section_title, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, workflow_id, "CONTAINS")
            feature_id = ensure_node(nodes, node_index, "Feature", "name", current_section_title, citations=[citation])
            add_edge(edges, workflow_id, feature_id, "USES_FEATURE")

        # -- variables from whitelist
        for var in re.findall(r"\b[A-Z][A-Za-z0-9_]+\b", text):
            if var in VARIABLE_WHITELIST:
                variable_type = "display" if section_title_lower in {"screen tiers", "16. dashboard & ux requirements"} else "financial"
                var_id = ensure_node(
                    nodes,
                    node_index,
                    "Variable",
                    "name",
                    var,
                    variable_type=variable_type,
                    citations=[citation],
                )
                if current_section_id:
                    add_edge(edges, current_section_id, var_id, "CONTAINS")

        # -- metrics (formulas with '=')
        if "=" in text and any(k in text_lower for k in ("revenue", "cost", "profit", "margin")):
            metric_id = ensure_node(nodes, node_index, "Metric", "formula", text, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, metric_id, "CONTAINS")
            for var in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", text):
                if var in VARIABLE_WHITELIST:
                    var_id = ensure_node(
                        nodes,
                        node_index,
                        "Variable",
                        "name",
                        var,
                        variable_type="financial",
                        citations=[citation],
                    )
                    add_edge(edges, metric_id, var_id, "DEPENDS_ON")

        # -- services
        for svc in re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+(?:Engine|Service))\b", text):
            svc_id = ensure_node(nodes, node_index, "Service", "name", svc, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, svc_id, "CONTAINS")

        # -- layers
        for layer in re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+Layer)\b", f"{current_section_title} {text}"):
            layer_id = ensure_node(nodes, node_index, "Layer", "name", layer, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, layer_id, "CONTAINS")

        # -- dashboards
        if "dashboard" in text_lower:
            ui_names = re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+Dashboard)\b", text) or ["Dashboard"]
            for ui_name in ui_names:
                ui_id = ensure_node(
                    nodes,
                    node_index,
                    "UIComponent",
                    "name",
                    ui_name,
                    component_type="dashboard",
                    citations=[citation],
                )
                if current_section_id:
                    add_edge(edges, current_section_id, ui_id, "CONTAINS")

    return {"nodes": nodes, "edges": edges}
