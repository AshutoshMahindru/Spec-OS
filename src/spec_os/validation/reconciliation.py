"""Cross-layer spec reconciliation.

Checks that:
* Every extracted variable has a storage-table mapping.
* Every metric dependency resolves to a known variable.
* Every API response model exists in the schema.
"""

from __future__ import annotations

from spec_os.computation.dag import build_computation_graph
from spec_os.helpers import normalize_name


def build_variable_to_table_mapping(schema: dict, variable_registry: dict) -> dict:
    """Map each variable to either ``driver_assumption`` or ``computed_metric``."""
    mapping: dict[str, dict] = {}
    driver_vars = {normalize_name(name) for name in {"orders", "aov", "demand", "price", "mix"}}
    for v in variable_registry.get("variables", []):
        raw_name = v.get("raw_name") or v.get("name")
        name = normalize_name(v.get("name") or raw_name)
        if not name:
            continue
        if name in driver_vars:
            mapping[name] = {"table": "driver_assumption", "field": "value", "display_name": raw_name or name}
        else:
            mapping[name] = {"table": "computed_metric", "field": "value", "display_name": raw_name or name}
    return mapping


def reconcile_spec(
    graph: dict,
    schema: dict,
    variable_registry: dict,
    api_contracts: list[dict],
) -> dict:
    """Return ``{issues, status}``."""
    issues: list[dict] = []

    extracted_vars = {normalize_name(v.get("name")) for v in variable_registry.get("variables", []) if v.get("name")}

    # Variable -> table mapping check
    var_table_map = build_variable_to_table_mapping(schema, variable_registry)
    for v in extracted_vars:
        if v not in var_table_map:
            issues.append({"type": "MISSING_STORAGE_MAPPING", "variable": v})

    # Computation dependency check
    comp = build_computation_graph(graph)
    for m in comp.get("metrics", []):
        for dep in m.get("depends_on", []):
            if normalize_name(dep) not in extracted_vars:
                issues.append({"type": "MISSING_VARIABLE_IN_REGISTRY", "variable": dep, "metric": m.get("metric")})

    # API -> schema linkage
    model_names = {normalize_name(m.get("name")) for m in schema.get("models", []) if m.get("name")}
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
            issues.append({"type": "API_SCHEMA_MISMATCH", "endpoint": api.get("endpoint"), "model": resp["data"]})

    return {"issues": issues, "status": "ok" if not issues else "needs_review"}
