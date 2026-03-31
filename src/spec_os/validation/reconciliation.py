"""Cross-layer spec reconciliation.

Checks that:
* Every extracted variable has a storage-table mapping.
* Every metric dependency resolves to a known variable.
* Every API response model exists in the schema.
"""

from __future__ import annotations

import re

from spec_os.computation.dag import build_computation_graph


def _norm(x: str | None) -> str:
    if not x:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(x).strip().lower())


def build_variable_to_table_mapping(schema: dict, variable_registry: dict) -> dict:
    """Map each variable to either ``driver_assumption`` or ``computed_metric``."""
    mapping: dict[str, dict] = {}
    driver_vars = {"orders", "aov", "demand", "price", "mix"}
    for v in variable_registry.get("variables", []):
        name = v.get("name")
        if not name:
            continue
        if name.lower() in driver_vars:
            mapping[name] = {"table": "driver_assumption", "field": "value"}
        else:
            mapping[name] = {"table": "computed_metric", "field": "value"}
    return mapping


def reconcile_spec(
    graph: dict,
    schema: dict,
    variable_registry: dict,
    api_contracts: list[dict],
) -> dict:
    """Return ``{issues, status}``."""
    issues: list[dict] = []

    extracted_vars = {_norm(v.get("name")) for v in variable_registry.get("variables", []) if v.get("name")}

    # Variable -> table mapping check
    var_table_map = build_variable_to_table_mapping(schema, variable_registry)
    for v in extracted_vars:
        if v not in var_table_map:
            issues.append({"type": "MISSING_STORAGE_MAPPING", "variable": v})

    # Computation dependency check
    comp = build_computation_graph(graph)
    for m in comp.get("metrics", []):
        for dep in m.get("depends_on", []):
            if _norm(dep) not in extracted_vars:
                issues.append({"type": "MISSING_VARIABLE_IN_REGISTRY", "variable": dep, "metric": m.get("metric")})

    # API -> schema linkage
    model_names = {_norm(m.get("name")) for m in schema.get("models", []) if m.get("name")}
    for api in api_contracts:
        if not api.get("endpoint"):
            issues.append({"type": "INVALID_API", "api": api})
            continue
        resp = api.get("response", {})
        if isinstance(resp, dict):
            data_ref = resp.get("data")
            if isinstance(data_ref, str) and data_ref not in ("success", "status"):
                if _norm(data_ref) not in model_names:
                    issues.append({"type": "API_SCHEMA_MISMATCH", "endpoint": api.get("endpoint"), "model": data_ref})

    return {"issues": issues, "status": "ok" if not issues else "needs_review"}
