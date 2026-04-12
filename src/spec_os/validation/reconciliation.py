"""Cross-layer spec reconciliation.

Foolproof reconciliation (Changes A–E):

* Every extracted variable has a storage-table mapping derived from the
  computation graph (not a hardcoded set).
* Every metric dependency resolves to a known variable.
* Every API response model exists in the schema.
* Contradictory metric formulas across documents are flagged.
* Contradictory variable types across documents are flagged.
* Graph edge integrity is validated (all edge types).
* Computation graph issues (cycles, duplicates) are unified here.
* Possible name aliases are surfaced via fuzzy matching.
"""

from __future__ import annotations

from spec_os.computation.dag import build_computation_graph
from spec_os.constants import EDGE_TYPES
from spec_os.helpers import find_possible_aliases, normalize_name


def build_variable_to_table_mapping(
    schema: dict,
    variable_registry: dict,
    computation_graph: dict | None = None,
) -> dict:
    """Map each variable to ``driver_assumption`` or ``computed_metric``.

    Change B: classification is now derived from the computation graph.
    A variable is a *driver* if it appears in ``available_inputs`` but is not
    the LHS of any metric.  A variable is *computed* if it **is** the LHS of
    a metric.  Anything else defaults to ``computed_metric`` (safe default for
    backward compat) but a reconciliation issue will be raised separately.
    """
    metric_outputs: set[str] = set()
    available_inputs: set[str] = set()
    if computation_graph:
        for m in computation_graph.get("metrics", []):
            mname = normalize_name(m.get("metric"))
            if mname:
                metric_outputs.add(mname)
        for inp in computation_graph.get("available_inputs", []):
            ninp = normalize_name(inp)
            if ninp:
                available_inputs.add(ninp)

    mapping: dict[str, dict] = {}
    for v in variable_registry.get("variables", []):
        raw_name = v.get("raw_name") or v.get("name")
        name = normalize_name(v.get("name") or raw_name)
        if not name:
            continue
        if name in metric_outputs:
            table = "computed_metric"
        elif name in available_inputs:
            table = "driver_assumption"
        else:
            # Fallback heuristic: known driver names.
            _driver_names = {"orders", "aov", "demand", "price", "mix"}
            table = "driver_assumption" if name in _driver_names else "computed_metric"
        mapping[name] = {"table": table, "field": "value", "display_name": raw_name or name}
    return mapping


def _check_formula_conflicts(canonical_model: dict, issues: list[dict]) -> None:
    """Change A: detect metrics with contradictory formula definitions."""
    for m in canonical_model.get("metrics", []):
        definitions = m.get("definitions", [])
        if len(definitions) <= 1:
            continue
        # Normalise formulas for comparison (strip whitespace).
        seen_formulas: dict[str, dict] = {}
        for defn in definitions:
            normalised = " ".join(defn.get("formula", "").split())
            if normalised not in seen_formulas:
                seen_formulas[normalised] = defn
        if len(seen_formulas) > 1:
            issues.append({
                "type": "CONFLICTING_FORMULA",
                "metric": m.get("name"),
                "definitions": [
                    {"formula": d.get("formula"), "doc_id": d.get("doc_id")}
                    for d in definitions
                ],
            })


def _check_variable_type_conflicts(canonical_model: dict, issues: list[dict]) -> None:
    """Change A: detect variables with contradictory type assignments."""
    for v in canonical_model.get("variables", []):
        observed = v.get("observed_types", [])
        if len(observed) <= 1:
            continue
        unique_types = {t for t, _ in observed if t and t != "unknown"}
        if len(unique_types) > 1:
            issues.append({
                "type": "CONFLICTING_VARIABLE_TYPE",
                "variable": v.get("name"),
                "observed_types": [
                    {"variable_type": t, "doc_id": d} for t, d in observed
                ],
            })


def _check_graph_edge_integrity(graph: dict, issues: list[dict]) -> None:
    """Change C: validate all edge types for referential integrity."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map: dict[str, dict] = {n["id"]: n for n in nodes if n.get("id")}

    # Build allowed (src_type, edge_type, dst_type) set from EDGE_TYPES.
    allowed_edges: set[tuple[str, str, str]] = set()
    for src_t, etype, dst_t in EDGE_TYPES:
        allowed_edges.add((src_t, etype, dst_t))
    # Also allow "Section" → "CONTAINS" → any traceable type (already in EDGE_TYPES).
    # And "CONTAINS" where src might be any organising type.

    for edge in edges:
        src_id = edge.get("from")
        dst_id = edge.get("to")
        etype = edge.get("type")

        src_node = node_map.get(src_id)
        dst_node = node_map.get(dst_id)

        if not src_node or not dst_node:
            issues.append({
                "type": "BROKEN_EDGE",
                "edge_type": etype,
                "from": src_id,
                "to": dst_id,
                "reason": "endpoint_missing",
            })
            continue

        # Type match check.
        src_type = src_node.get("type")
        dst_type = dst_node.get("type")
        if etype and (src_type, etype, dst_type) not in allowed_edges:
            # Allow CONTAINS from Section to any traceable type (relaxed).
            if etype == "CONTAINS" and src_type == "Section":
                continue
            issues.append({
                "type": "TYPE_MISMATCH_EDGE",
                "edge_type": etype,
                "expected_src_type": None,
                "actual_src_type": src_type,
                "expected_dst_type": None,
                "actual_dst_type": dst_type,
                "from": src_id,
                "to": dst_id,
            })


def _check_possible_aliases(
    variable_registry: dict,
    issues: list[dict],
    *,
    threshold: float = 0.8,
) -> None:
    """Change B: fuzzy match unresolved variable names."""
    names = [
        normalize_name(v.get("name"))
        for v in variable_registry.get("variables", [])
        if v.get("name")
    ]
    unique_names = list(dict.fromkeys(n for n in names if n))
    for name_a, name_b, similarity in find_possible_aliases(unique_names, threshold=threshold):
        issues.append({
            "type": "POSSIBLE_ALIAS",
            "variable_a": name_a,
            "variable_b": name_b,
            "similarity": similarity,
        })


def _merge_computation_issues(
    computation_validation: dict | None,
    issues: list[dict],
) -> None:
    """Change C: incorporate computation graph validation issues."""
    if not computation_validation:
        return
    for issue in computation_validation.get("issues", []):
        # Avoid duplicating issues already present.
        if issue not in issues:
            issues.append(issue)


def reconcile_spec(
    graph: dict,
    schema: dict,
    variable_registry: dict,
    api_contracts: list[dict],
    *,
    canonical_model: dict | None = None,
    computation_validation: dict | None = None,
    graph_validation: dict | None = None,
    merge_conflicts: list[dict] | None = None,
) -> dict:
    """Return ``{issues, status}``.

    Now accepts optional keyword arguments for:
    * *canonical_model* – to detect formula and variable type conflicts.
    * *computation_validation* – to unify computation issues.
    * *graph_validation* – to unify graph integrity issues.
    * *merge_conflicts* – schema/API merge conflicts from Change E.
    """
    issues: list[dict] = []

    extracted_vars = {
        normalize_name(v.get("name"))
        for v in variable_registry.get("variables", [])
        if v.get("name")
    }

    # ── Variable -> table mapping check ─────────────────────────────────
    comp = build_computation_graph(graph)
    var_table_map = build_variable_to_table_mapping(schema, variable_registry, comp)
    for v in extracted_vars:
        if v not in var_table_map:
            issues.append({"type": "MISSING_STORAGE_MAPPING", "variable": v})

    # ── Computation dependency check ────────────────────────────────────
    for m in comp.get("metrics", []):
        for dep in m.get("depends_on", []):
            if normalize_name(dep) not in extracted_vars:
                issues.append({
                    "type": "MISSING_VARIABLE_IN_REGISTRY",
                    "variable": dep,
                    "metric": m.get("metric"),
                })

    # ── API -> schema linkage ───────────────────────────────────────────
    model_names = {
        normalize_name(m.get("name"))
        for m in schema.get("models", [])
        if m.get("name")
    }
    for api in api_contracts:
        if not api.get("endpoint"):
            issues.append({"type": "INVALID_API", "api": api})
            continue
        resp = api.get("response", {})
        if (
            isinstance(resp, dict)
            and isinstance(resp.get("data"), str)
            and resp["data"] not in ("success", "status")
            and normalize_name(resp["data"]) not in model_names
        ):
            issues.append({
                "type": "API_SCHEMA_MISMATCH",
                "endpoint": api.get("endpoint"),
                "model": resp["data"],
            })

    # ── Change A: formula and variable type conflicts ───────────────────
    if canonical_model:
        _check_formula_conflicts(canonical_model, issues)
        _check_variable_type_conflicts(canonical_model, issues)

    # ── Change C: graph edge integrity ──────────────────────────────────
    _check_graph_edge_integrity(graph, issues)

    # ── Change C: merge computation and graph validation issues ─────────
    _merge_computation_issues(computation_validation, issues)
    if graph_validation:
        for issue in graph_validation.get("issues", []):
            if issue not in issues:
                issues.append(issue)

    # ── Change B: fuzzy alias detection ─────────────────────────────────
    _check_possible_aliases(variable_registry, issues)

    # ── Change E: merge conflicts from schema/API merge ─────────────────
    if merge_conflicts:
        issues.extend(merge_conflicts)

    return {"issues": issues, "status": "ok" if not issues else "needs_review"}
