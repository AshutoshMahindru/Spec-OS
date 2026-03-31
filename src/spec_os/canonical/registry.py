"""Variable registry: flat catalogue of all extracted variables."""

from __future__ import annotations

from spec_os.helpers import normalize_name


def build_variable_registry(graph: dict) -> dict:
    """Build ``{variables: [...]}`` from graph Variable nodes."""
    registry: dict[str, dict] = {}
    for n in graph.get("nodes", []):
        if n.get("type") != "Variable":
            continue
        raw_name = n.get("name")
        if not raw_name:
            continue
        name = normalize_name(raw_name)
        registry[name] = {
            "name": name,
            "raw_name": raw_name,
            "variable_type": n.get("variable_type", "unknown"),
            "unit": None,
            "source": "extracted",
        }
    return {"variables": list(registry.values())}
