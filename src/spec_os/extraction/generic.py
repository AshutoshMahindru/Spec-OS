"""Generic (fallback) graph extractor -- headings only."""

from __future__ import annotations

from spec_os.graph import add_edge, make_node_registry


def extract_generic_graph(structured: list[dict], doc_id: str) -> dict:
    nodes, node_index, edges = make_node_registry(doc_id)
    doc_node_id = f"doc_{doc_id}"

    for i, sec in enumerate(structured):
        if sec["type"] == "heading":
            section_id = f"sec_{doc_id}_{i}"
            node = {"id": section_id, "type": "Section", "title": sec["text"], "level": sec.get("level", 1)}
            nodes.append(node)
            node_index[section_id] = node
            add_edge(edges, doc_node_id, section_id, "HAS_SECTION")

    return {"nodes": nodes, "edges": edges}
