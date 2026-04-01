"""Build API contracts from canonical model or raw graph.

BUG-FIX: The original code defined ``build_api_contracts`` twice with
incompatible signatures.  The second definition shadowed the first, meaning
the canonical-model path was dead code.  The ``ingest_file_path`` pipeline
called ``build_api_contracts(canonical_model)`` which hit the *graph* version
and silently returned ``[]`` because ``canonical_model`` has no ``nodes`` key.

This module provides two clearly-named functions:

* ``build_api_contracts_from_canonical`` -- preferred (V2 pipeline).
* ``build_api_contracts_from_graph`` -- legacy / fallback.
"""

from __future__ import annotations

from spec_os.helpers import normalize_name


def _infer_request_response(endpoint: str) -> dict:
    if "planning" in endpoint:
        return {"request": {"query": {"scenario_id": "uuid"}}, "response": {"data": "planning_context"}}
    if "driver" in endpoint:
        return {"request": {"body": {"variable_name": "string", "value": "decimal"}}, "response": {"status": "success"}}
    if "metric" in endpoint:
        return {"request": {"query": {"metric_name": "string"}}, "response": {"value": "decimal"}}
    return {"request": {}, "response": {}}


def build_api_contracts_from_canonical(canonical_model: dict) -> list[dict]:
    """Derive API contracts from canonical entities of type ``API``."""
    contracts: list[dict] = []
    for ent in canonical_model.get("entities", []):
        if ent.get("type") != "API":
            continue
        endpoint = ent.get("endpoint") or ""
        method = ent.get("method") or "GET"
        inferred = _infer_request_response(endpoint)
        contracts.append({
            "endpoint": endpoint,
            "method": method,
            "request": inferred["request"],
            "response": inferred["response"],
            "headers": {"Authorization": "Bearer <token>"},
        })
    return contracts


def build_api_contracts_from_graph(graph: dict) -> list[dict]:
    """Derive API contracts from raw graph API nodes."""
    contracts: list[dict] = []
    for n in graph.get("nodes", []):
        if n.get("type") != "API":
            continue
        endpoint = n.get("endpoint") or ""
        method = n.get("method") or "GET"
        inferred = _infer_request_response(endpoint)
        contracts.append({
            "endpoint": endpoint,
            "method": method,
            "request": inferred["request"],
            "response": inferred["response"],
            "headers": {"Authorization": "Bearer <token>"},
        })
    return contracts


def bind_api_to_schema(api_contracts: list[dict], schema: dict) -> list[dict]:
    """Map each API endpoint to its backing schema model."""
    schema_models = {normalize_name(model.get("name")): model.get("name") for model in schema.get("models", []) if model.get("name")}
    bindings: list[dict] = []
    for api in api_contracts:
        ep = api.get("endpoint") or ""
        explicit_model = None
        response = api.get("response", {})
        if isinstance(response, dict):
            data_ref = response.get("data")
            if isinstance(data_ref, str):
                explicit_model = data_ref

        if explicit_model:
            model = schema_models.get(normalize_name(explicit_model), normalize_name(explicit_model))
        elif "planning" in ep:
            model = schema_models.get("planning_context", "planning_context")
        elif "driver" in ep:
            model = schema_models.get("driver_assumption", "driver_assumption")
        elif "metric" in ep:
            model = schema_models.get("computed_metric", "computed_metric")
        else:
            model = "unknown"

        bindings.append(
            {
                "endpoint": ep,
                "method": api.get("method"),
                "model": model,
                "status": "bound" if model != "unknown" else "unresolved",
            }
        )
    return bindings
