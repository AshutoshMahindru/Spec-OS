"""API-specification graph extractor."""

from __future__ import annotations

import re

from spec_os.graph import add_edge, ensure_node, make_node_registry


def extract_api_spec_graph(structured: list[dict], doc_id: str) -> dict:
    nodes, node_index, edges = make_node_registry(doc_id)
    doc_node_id = f"doc_{doc_id}"
    current_section_id: str | None = None
    current_group = ""

    for i, sec in enumerate(structured):
        if sec["type"] == "heading":
            current_section_id = f"sec_{doc_id}_{i}"
            title = sec["text"]
            node = {"id": current_section_id, "type": "Section", "title": title, "level": sec.get("level", 1)}
            nodes.append(node)
            node_index[current_section_id] = node
            add_edge(edges, doc_node_id, current_section_id, "HAS_SECTION")
            if title.lower() == "service groups":
                current_group = "service_groups"
            continue

        text = sec.get("text", "")
        text_lower = text.lower()

        match = re.search(r"\b(GET|POST|PUT|DELETE)\s+(/\S+)", text)
        if match:
            method, endpoint = match.groups()
            api_id = ensure_node(nodes, node_index, "API", "endpoint", endpoint, method=method)
            if current_section_id:
                add_edge(edges, current_section_id, api_id, "CONTAINS")

        if text.startswith("/"):
            endpoint = text.split()[0]
            api_id = ensure_node(nodes, node_index, "API", "endpoint", endpoint, group=current_section_id or current_group)
            if current_section_id:
                add_edge(edges, current_section_id, api_id, "CONTAINS")

        if "base path:" in text_lower:
            api_id = ensure_node(nodes, node_index, "API", "endpoint", "/api/v1/", method="*")
            if current_section_id:
                add_edge(edges, current_section_id, api_id, "CONTAINS")

    return {"nodes": nodes, "edges": edges}
