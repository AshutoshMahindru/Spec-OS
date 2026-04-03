"""Low-level graph primitives: node/edge management."""

from __future__ import annotations

from spec_os.helpers import normalize_text, safe_node_id

# ── Registry factory ────────────────────────────────────────────────────────

def make_node_registry(doc_id: str) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """Return ``(nodes, node_index, edges)`` seeded with the Document root."""
    root = {"id": f"doc_{doc_id}", "type": "Document"}
    nodes: list[dict] = [root]
    node_index: dict[str, dict] = {root["id"]: root}
    edges: list[dict] = []
    return nodes, node_index, edges


def make_citation(section: dict, *, section_title: str | None = None, text: str | None = None) -> dict:
    """Build a section-level citation payload from a structured section."""
    source_span = section.get("source_span", {})
    citation = {
        "section_index": source_span.get("section_index"),
        "source_tag": source_span.get("source_tag"),
        "section_title": normalize_text(section_title or ""),
        "text": normalize_text(text or section.get("text") or source_span.get("text") or ""),
    }
    return {key: value for key, value in citation.items() if value not in (None, "")}


def _merge_node_attr(node: dict, key: str, value: object) -> None:
    if key not in node or node[key] in (None, "", []):
        node[key] = value
        return

    if isinstance(node[key], list) and isinstance(value, list):
        for item in value:
            if item not in node[key]:
                node[key].append(item)


def ensure_node(
    nodes: list[dict],
    node_index: dict[str, dict],
    node_type: str,
    key_name: str,
    key_value: str,
    **attrs: object,
) -> str:
    """Upsert a node by ``(type, key_value)``; return its stable id."""
    node_id = safe_node_id(node_type, key_value)
    if node_id not in node_index:
        node = {"id": node_id, "type": node_type, key_name: normalize_text(key_value)}
        node.update(attrs)
        nodes.append(node)
        node_index[node_id] = node
    else:
        node = node_index[node_id]
        for k, v in attrs.items():
            _merge_node_attr(node, k, v)
    return node_id


def add_edge(edges: list[dict], src: str, dst: str, edge_type: str) -> None:
    """Append an edge if it is not already present."""
    edge = {"from": src, "to": dst, "type": edge_type}
    if edge not in edges:
        edges.append(edge)
