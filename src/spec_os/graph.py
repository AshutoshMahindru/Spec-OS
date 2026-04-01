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
            if k not in node or node[k] in (None, ""):
                node[k] = v
    return node_id


def add_edge(edges: list[dict], src: str, dst: str, edge_type: str) -> None:
    """Append an edge if it is not already present."""
    edge = {"from": src, "to": dst, "type": edge_type}
    if edge not in edges:
        edges.append(edge)
