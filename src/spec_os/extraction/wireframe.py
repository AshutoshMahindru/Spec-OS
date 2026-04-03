"""Wireframe / UI-spec graph extractor."""

from __future__ import annotations

import re

from spec_os.graph import add_edge, ensure_node, make_citation, make_node_registry


def extract_wireframe_graph(structured: list[dict], doc_id: str) -> dict:
    nodes, node_index, edges = make_node_registry(doc_id)
    doc_node_id = f"doc_{doc_id}"
    current_section_id: str | None = None
    current_section_title = ""

    for i, sec in enumerate(structured):
        if sec["type"] == "heading":
            current_section_id = f"sec_{doc_id}_{i}"
            current_section_title = sec["text"]
            node = {
                "id": current_section_id,
                "type": "Section",
                "title": sec["text"],
                "level": sec.get("level", 1),
                "citations": [make_citation(sec, section_title=current_section_title)],
            }
            nodes.append(node)
            node_index[current_section_id] = node
            add_edge(edges, doc_node_id, current_section_id, "HAS_SECTION")
            continue

        text = sec.get("text", "")
        citation = make_citation(sec, section_title=current_section_title)

        for ui_name in re.findall(
            r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+(?:Dashboard|Screen|Overview|Cockpit))\b",
            text,
        ):
            uid = ensure_node(nodes, node_index, "UIComponent", "name", ui_name, component_type="screen", citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, uid, "CONTAINS")

        for var in ("Demand", "Cost", "Funding", "Revenue", "KPI"):
            if var.lower() in text.lower():
                vid = ensure_node(nodes, node_index, "Variable", "name", var, variable_type="display", citations=[citation])
                if current_section_id:
                    add_edge(edges, current_section_id, vid, "CONTAINS")

    return {"nodes": nodes, "edges": edges}
