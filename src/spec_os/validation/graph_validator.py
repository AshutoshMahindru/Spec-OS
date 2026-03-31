"""Graph and computation-graph structural validators."""

from __future__ import annotations


def validate_graph(graph: dict) -> dict:
    """Check for orphan edges, duplicate ids, and missing required fields."""
    issues: list[dict] = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {n.get("id") for n in nodes}

    for e in edges:
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            issues.append({"type": "ORPHAN_EDGE", "edge": e})

    if len(node_ids) != len(nodes):
        issues.append({"type": "DUPLICATE_NODE_ID"})

    for n in nodes:
        if not n.get("id") or not n.get("type"):
            issues.append({"type": "INVALID_NODE", "node": n})

    return {"issues": issues, "status": "ok" if not issues else "invalid"}


def validate_computation_graph(comp: dict) -> dict:
    """Check for empty or duplicate metrics and invalid dependencies."""
    issues: list[dict] = []
    seen: set[str] = set()

    for m in comp.get("metrics", []):
        metric = m.get("metric")
        if not metric:
            issues.append({"type": "EMPTY_METRIC"})
            continue
        if metric in seen:
            issues.append({"type": "DUPLICATE_METRIC", "metric": metric})
        seen.add(metric)

        for dep in m.get("depends_on", []):
            if not dep:
                issues.append({"type": "INVALID_DEPENDENCY", "metric": metric})

    return {"issues": issues, "status": "ok" if not issues else "invalid"}
