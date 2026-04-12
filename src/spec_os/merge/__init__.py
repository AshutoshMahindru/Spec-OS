"""Multi-document merge: graphs, variable registries, and schemas.

Change E: merge functions now detect and report conflicts instead of
silently swallowing them.  ``merge_schemas`` deduplicates APIs, detects
field-type conflicts, and returns a ``conflicts`` list alongside the
merged data.  ``merge_all_docs`` passes these conflicts through to
reconciliation.
"""

from __future__ import annotations

from spec_os.api.contracts import build_api_contracts_from_graph
from spec_os.computation.dag import build_computation_graph, build_execution_plan
from spec_os.helpers import normalize_name
from spec_os.validation.reconciliation import reconcile_spec


def merge_graphs(graphs: list[dict]) -> dict:
    merged_nodes: dict[tuple, dict] = {}
    merged_edges: list[dict] = []

    for graph in graphs:
        for n in graph.get("nodes", []):
            raw = n.get("name") or n.get("id") or ""
            canonical = normalize_name(raw)
            key = (n.get("type"), canonical)
            if key not in merged_nodes:
                merged_nodes[key] = n
            else:
                for k, v in n.items():
                    if k not in merged_nodes[key] or not merged_nodes[key][k]:
                        merged_nodes[key][k] = v

        for e in graph.get("edges", []):
            if e not in merged_edges:
                merged_edges.append(e)

    return {"nodes": list(merged_nodes.values()), "edges": merged_edges}


def merge_variable_registries(registries: list[dict]) -> dict:
    merged: dict[str, dict] = {}
    for reg in registries:
        for v in reg.get("variables", []):
            name = normalize_name(v.get("name"))
            if not name:
                continue
            if name not in merged:
                merged[name] = {**v, "name": name}
            else:
                for k, val in v.items():
                    if k not in merged[name] or not merged[name][k]:
                        merged[name][k] = val
    return {"variables": list(merged.values())}


def merge_schemas(schemas: list[dict]) -> tuple[dict, list[dict]]:
    """Merge schemas and return ``(merged_schema, conflicts)``.

    Change E: detects field-type conflicts and deduplicates APIs.
    """
    merged: dict = {"models": [], "apis": [], "variables": []}
    model_map: dict[str, dict] = {}
    conflicts: list[dict] = []

    for s in schemas:
        for m in s.get("models", []):
            name = normalize_name(m.get("name"))
            if not name:
                continue
            if name not in model_map:
                model_map[name] = {**m, "name": name}
            else:
                existing_fields = {f.get("name"): f for f in model_map[name].get("fields", [])}
                for f in m.get("fields", []):
                    fname = f.get("name")
                    if fname not in existing_fields:
                        model_map[name].setdefault("fields", []).append(f)
                    else:
                        # Change E: detect field-type conflicts.
                        existing = existing_fields[fname]
                        if (
                            f.get("data_type") != existing.get("data_type")
                            or f.get("nullable") != existing.get("nullable")
                        ):
                            conflicts.append({
                                "type": "CONFLICTING_FIELD_TYPE",
                                "model": name,
                                "field": fname,
                                "existing": {
                                    "data_type": existing.get("data_type"),
                                    "nullable": existing.get("nullable"),
                                },
                                "incoming": {
                                    "data_type": f.get("data_type"),
                                    "nullable": f.get("nullable"),
                                },
                            })

        # Change E: deduplicate APIs by (endpoint, method).
        seen_apis: set[tuple[str, str]] = set()
        for existing_api in merged.get("apis", []):
            key = (normalize_name(existing_api.get("endpoint", "")), existing_api.get("method", "GET"))
            seen_apis.add(key)

        for api in s.get("apis", []):
            api_key = (normalize_name(api.get("endpoint", "")), api.get("method", "GET"))
            if api_key in seen_apis:
                conflicts.append({
                    "type": "DUPLICATE_API",
                    "endpoint": api.get("endpoint"),
                    "method": api.get("method", "GET"),
                })
            else:
                merged["apis"].append(api)
                seen_apis.add(api_key)

        merged["variables"].extend(s.get("variables", []))

    merged["models"] = list(model_map.values())
    return merged, conflicts


def merge_all_docs(doc_results: list[dict]) -> dict:
    """Merge individual doc results into a unified spec.

    Each element must have keys ``graph``, ``schema``, ``variable_registry``.
    """
    graphs = [d["graph"] for d in doc_results]
    schemas = [d["schema"] for d in doc_results]
    registries = [d["variable_registry"] for d in doc_results]

    merged_graph = merge_graphs(graphs)
    merged_registry = merge_variable_registries(registries)
    merged_schema, merge_conflicts = merge_schemas(schemas)

    computation_graph = build_computation_graph(merged_graph)
    execution_plan = build_execution_plan(computation_graph)
    api_contracts = build_api_contracts_from_graph(merged_graph)
    reconciliation = reconcile_spec(
        merged_graph,
        merged_schema,
        merged_registry,
        api_contracts,
        merge_conflicts=merge_conflicts,
    )

    return {
        "graph": merged_graph,
        "schema": merged_schema,
        "variable_registry": merged_registry,
        "computation_graph": computation_graph,
        "execution_plan": execution_plan,
        "api_contracts": api_contracts,
        "reconciliation": reconciliation,
        "merge_conflicts": merge_conflicts,
    }
