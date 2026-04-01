"""Architecture-document graph extractor."""

from __future__ import annotations

import re

from spec_os.graph import add_edge, ensure_node, make_citation, make_node_registry

_FLOW_PATTERNS = [
    (re.compile(r"([A-Za-z][A-Za-z0-9\s/&\-]+?)\s+feeds\s+([A-Za-z][A-Za-z0-9\s/&\-]+)", re.I), "FEEDS"),
    (re.compile(r"([A-Za-z][A-Za-z0-9\s/&\-]+?)\s+uses\s+([A-Za-z][A-Za-z0-9\s/&\-]+)", re.I), "USES"),
    (re.compile(r"([A-Za-z][A-Za-z0-9\s/&\-]+?)\s+outputs\s+to\s+([A-Za-z][A-Za-z0-9\s/&\-]+)", re.I), "OUTPUTS_TO"),
    (re.compile(r"([A-Za-z][A-Za-z0-9\s/&\-]+?)\s+drives\s+([A-Za-z][A-Za-z0-9\s/&\-]+)", re.I), "DRIVES_UI"),
]


def _classify_entity(name: str) -> str:
    lower = name.lower()
    if lower.endswith("layer"):
        return "Layer"
    if "dashboard" in lower or "screen" in lower:
        return "UIComponent"
    return "Service"


def extract_architecture_graph(structured: list[dict], doc_id: str) -> dict:
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

        for layer in re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+Layer)\b", text):
            lid = ensure_node(nodes, node_index, "Layer", "name", layer, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, lid, "CONTAINS")

        for svc in re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+(?:Engine|Service|Gateway|Orchestrator))\b", text):
            sid = ensure_node(nodes, node_index, "Service", "name", svc, citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, sid, "CONTAINS")

        for ui in re.findall(r"\b([A-Z][A-Za-z0-9&/\-]*(?:\s+[A-Z][A-Za-z0-9&/\-]*)*\s+(?:Dashboard|Screen))\b", text):
            uid = ensure_node(nodes, node_index, "UIComponent", "name", ui, component_type="screen", citations=[citation])
            if current_section_id:
                add_edge(edges, current_section_id, uid, "CONTAINS")

        for pattern, relation in _FLOW_PATTERNS:
            for src_raw, dst_raw in pattern.findall(text):
                src_name = " ".join(src_raw.split())
                dst_name = " ".join(dst_raw.split())
                src_id = ensure_node(nodes, node_index, _classify_entity(src_name), "name", src_name, citations=[citation])
                dst_id = ensure_node(nodes, node_index, _classify_entity(dst_name), "name", dst_name, citations=[citation])
                add_edge(edges, src_id, dst_id, relation)

    return {"nodes": nodes, "edges": edges}
