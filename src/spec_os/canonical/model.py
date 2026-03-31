"""Build the canonical model from an extraction graph.

The canonical model unifies variables, entities, metrics, and relationships
into a single normalised structure that downstream modules depend on.
"""

from __future__ import annotations

import re

from spec_os.helpers import normalize_name


def _parse_formula_vars(formula: str) -> list[str]:
    """Extract RHS variable tokens from a formula string like ``Revenue = Orders * AOV``."""
    if not formula:
        return []
    parts = formula.split("=")
    rhs = parts[-1] if len(parts) > 1 else formula
    tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", rhs)
    return list(dict.fromkeys(tokens))


def build_canonical_model(graph: dict) -> dict:
    """Derive ``{variables, entities, relationships, metrics}`` from *graph*."""
    variables: dict[str, dict] = {}
    entities: dict[str, dict] = {}
    relationships: list[dict] = []
    metrics: dict[str, dict] = {}

    for n in graph.get("nodes", []):
        ntype = n.get("type")

        if ntype == "Variable":
            raw = n.get("name")
            cname = normalize_name(raw)
            if cname not in variables:
                variables[cname] = {
                    "name": cname,
                    "raw_names": [raw],
                    "variable_type": n.get("variable_type", "unknown"),
                }
            else:
                variables[cname]["raw_names"].append(raw)

        elif ntype in {"DataModel", "API", "Service", "UIComponent"}:
            key = normalize_name(n.get("name") or n.get("endpoint") or n.get("id"))
            if key not in entities:
                entities[key] = n

        elif ntype == "Metric":
            formula = n.get("formula")
            if not formula:
                continue
            parts = formula.split("=")
            lhs = normalize_name(parts[0].strip()) if len(parts) > 1 else normalize_name(formula)
            deps = [normalize_name(d) for d in _parse_formula_vars(formula)]
            metrics[lhs] = {
                "name": lhs,
                "formula": formula,
                "depends_on": list(dict.fromkeys(deps)),
            }

    for e in graph.get("edges", []):
        relationships.append(e)

    return {
        "variables": list(variables.values()),
        "entities": list(entities.values()),
        "relationships": relationships,
        "metrics": list(metrics.values()),
    }
