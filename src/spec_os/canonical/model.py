"""Build the canonical model from an extraction graph.

The canonical model unifies variables, entities, metrics, and relationships
into a single normalised structure that downstream modules depend on.

Change A: metrics now accumulate *all* formula definitions per canonical name
with provenance (``definitions[]``), and variables track all observed
``variable_type`` values so that cross‑document contradictions can be
detected by reconciliation instead of being silently swallowed.
"""

from __future__ import annotations

from spec_os.computation.formula import extract_formula_dependencies, parse_formula
from spec_os.helpers import normalize_name


def _parse_formula_vars(formula: str) -> list[str]:
    """Extract normalized variable tokens from a formula string."""
    return extract_formula_dependencies(formula)


def build_canonical_model(graph: dict) -> dict:
    """Derive ``{variables, entities, relationships, metrics}`` from *graph*.

    Each *variable* now carries:
    * ``observed_types`` – list of ``(variable_type, doc_id)`` tuples seen
      across all contributing documents.

    Each *metric* now carries:
    * ``definitions`` – list of ``{formula, depends_on, citations, doc_id}``
      for every distinct formula contributed.
    * ``formula`` / ``depends_on`` – the *active* definition (latest).
    """
    variables: dict[str, dict] = {}
    entities: dict[str, dict] = {}
    relationships: list[dict] = []
    metrics: dict[str, dict] = {}

    # Derive doc_id from graph if available (Document node).
    graph_doc_id: str | None = None
    for n in graph.get("nodes", []):
        if n.get("type") == "Document":
            graph_doc_id = n.get("id", "").removeprefix("doc_") or None
            break

    for n in graph.get("nodes", []):
        ntype = n.get("type")

        if ntype == "Variable":
            raw = n.get("name")
            cname = normalize_name(raw)
            vtype = n.get("variable_type", "unknown")
            doc_id = n.get("doc_id") or graph_doc_id
            if cname not in variables:
                variables[cname] = {
                    "name": cname,
                    "raw_names": [raw],
                    "variable_type": vtype,
                    "observed_types": [(vtype, doc_id)],
                    "citations": list(n.get("citations", [])),
                }
            else:
                variables[cname]["raw_names"].append(raw)
                # Track every observed type for conflict detection.
                variables[cname]["observed_types"].append((vtype, doc_id))
                # Keep first non-unknown type as active.
                if variables[cname]["variable_type"] == "unknown" and vtype != "unknown":
                    variables[cname]["variable_type"] = vtype
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
            normalised_formula = f"{lhs} = {expression}" if expression else formula
            doc_id = n.get("doc_id") or graph_doc_id

            definition = {
                "formula": normalised_formula,
                "depends_on": list(dict.fromkeys(deps)),
                "citations": list(n.get("citations", [])),
                "doc_id": doc_id,
            }

            if lhs not in metrics:
                metrics[lhs] = {
                    "name": lhs,
                    "formula": normalised_formula,
                    "depends_on": list(dict.fromkeys(deps)),
                    "citations": list(n.get("citations", [])),
                    "definitions": [definition],
                }
            else:
                metrics[lhs]["definitions"].append(definition)
                # Active definition = latest (last writer wins, but now recorded).
                metrics[lhs]["formula"] = normalised_formula
                metrics[lhs]["depends_on"] = list(dict.fromkeys(deps))
                for citation in n.get("citations", []):
                    if citation not in metrics[lhs]["citations"]:
                        metrics[lhs]["citations"].append(citation)

    for e in graph.get("edges", []):
        relationships.append(e)

    return {
        "variables": list(variables.values()),
        "entities": list(entities.values()),
        "relationships": relationships,
        "metrics": list(metrics.values()),
    }
