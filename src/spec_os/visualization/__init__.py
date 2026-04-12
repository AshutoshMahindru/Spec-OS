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

    # -- Entity-relationship graph --
    # Use original node IDs as Mermaid identifiers to avoid collisions that
    # occur when normalisation maps different names to the same slug.
    lines = ["graph TD"]
    original_id_to_mermaid: dict[str, str] = {}

    for idx, n in enumerate(graph.get("nodes", [])):
        original_id = n.get("id", "")
        # Create a unique Mermaid-safe ID using the index to prevent collisions.
        safe = _safe_id(original_id) or f"n{idx}"
        mermaid_id = f"n{idx}_{safe}"
        original_id_to_mermaid[original_id] = mermaid_id

        label = (
            n.get("name")
            or n.get("endpoint")
            or n.get("formula")
            or n.get("title")
            or n.get("id")
        )
        lines.append(f'{mermaid_id}["{_safe_label(label)}"]')

    for e in graph.get("edges", []):
        src = original_id_to_mermaid.get(e.get("from", ""))
        dst = original_id_to_mermaid.get(e.get("to", ""))
        if src and dst:
            lines.append(f"{src} --> {dst}")
    graph_diagram = "\n".join(lines)

    # -- Computation DAG --
    lines = ["graph TD"]
    # Track already-declared input variable nodes to avoid duplicate declarations.
    declared_inputs: dict[str, str] = {}

    for i, m in enumerate(computation_graph.get("metrics", [])):
        mid = f"m_{i}_{_safe_id(m.get('metric', ''))}"
        lines.append(f'{mid}["{_safe_label(m.get("metric", ""))}"]')
        for inp in m.get("depends_on", []):
            sid = _safe_id(inp)
            if sid not in declared_inputs:
                vid = f"v_{len(declared_inputs)}_{sid}"
                declared_inputs[sid] = vid
                lines.append(f'{vid}["{_safe_label(inp)}"]')
            else:
                vid = declared_inputs[sid]
            lines.append(f"{vid} --> {mid}")
    computation_diagram = "\n".join(lines)

    return {"graph_mermaid": graph_diagram, "computation_mermaid": computation_diagram}
