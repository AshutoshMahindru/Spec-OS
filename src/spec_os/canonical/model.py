"""Build the canonical model from an extraction graph.

The canonical model unifies variables, entities, metrics, and relationships
into a single normalised structure that downstream modules depend on.
"""

from __future__ import annotations

from spec_os.computation.formula import extract_formula_dependencies, parse_formula
from spec_os.helpers import normalize_name


def _parse_formula_vars(formula: str) -> list[str]:
    """Extract normalized variable tokens from a formula string."""
    return extract_formula_dependencies(formula)


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
                    "citations": list(n.get("citations", [])),
                }
            else:
                variables[cname]["raw_names"].append(raw)
                for citation in n.get("citations", []):
                    if citation not in variables[cname]["citations"]:
                        variables[cname]["citations"].append(citation)

        elif ntype in {"DataModel", "API", "Service", "UIComponent"}:
            key = normalize_name(n.get("name") or n.get("endpoint") or n.get("id"))
            if key not in entities:
                entities[key] = n
            else:
                for citation in n.get("citations", []):
                    entities[key].setdefault("citations", [])
                    if citation not in entities[key]["citations"]:
                        entities[key]["citations"].append(citation)

        elif ntype == "Metric":
            formula = n.get("formula")
            if not formula:
                continue
            metric_name, expression = parse_formula(formula)
            lhs = normalize_name(metric_name)
            deps = [dep for dep in _parse_formula_vars(formula) if dep and dep != lhs]
            if expression is None:
                expression = formula
            metrics[lhs] = {
                "name": lhs,
                "formula": f"{lhs} = {expression}" if expression else formula,
                "depends_on": list(dict.fromkeys(deps)),
                "citations": list(n.get("citations", [])),
            }

    for e in graph.get("edges", []):
        relationships.append(e)

    return {
        "variables": list(variables.values()),
        "entities": list(entities.values()),
        "relationships": relationships,
        "metrics": list(metrics.values()),
    }
