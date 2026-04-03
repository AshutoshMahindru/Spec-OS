"""Mermaid diagram generation from graph and computation DAG."""

from __future__ import annotations

import re

from spec_os.helpers import normalize_name


def _safe_id(s: str) -> str:
    s = normalize_name(s or "")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return s or "node"


def _safe_label(s: str) -> str:
    if not s:
        return ""
    return str(s).replace('"', '\\"')


def generate_mermaid_diagrams(graph: dict, computation_graph: dict) -> dict:
    """Return ``{graph_mermaid, computation_mermaid}`` strings."""

    # -- Entity-relationship graph
    lines = ["graph TD"]
    node_labels: dict[str, str] = {}
    for n in graph.get("nodes", []):
        nid = _safe_id(n.get("id", ""))
        label = n.get("name") or n.get("endpoint") or n.get("formula") or n.get("title") or n.get("id")
        node_labels[nid] = _safe_label(label)

    for nid, lbl in node_labels.items():
        lines.append(f'{nid}["{lbl}"]')
    for e in graph.get("edges", []):
        lines.append(f"{_safe_id(e.get('from', ''))} --> {_safe_id(e.get('to', ''))}")
    graph_diagram = "\n".join(lines)

    # -- Computation DAG
    lines = ["graph TD"]
    for i, m in enumerate(computation_graph.get("metrics", [])):
        mid = f"m_{i}_{_safe_id(m.get('metric', ''))}"
        lines.append(f'{mid}["{_safe_label(m.get("metric", ""))}"]')
        for inp in m.get("depends_on", []):
            vid = _safe_id(inp)
            lines.append(f'{vid}["{_safe_label(inp)}"]')
            lines.append(f"{vid} --> {mid}")
    computation_diagram = "\n".join(lines)

    return {"graph_mermaid": graph_diagram, "computation_mermaid": computation_diagram}
