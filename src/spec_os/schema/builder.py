"""Build the data schema from a canonical model (EAV-style core models).

BUG-FIX from original: The original ``build_data_schema`` mixed graph-level
concerns with canonical-model concerns. This module exposes two clear paths:

* ``build_data_schema_from_canonical`` -- derives schema purely from the
  canonical model (preferred, used in the V2 pipeline).
* ``build_data_schema_from_graph`` -- legacy path that inspects the raw graph
  and falls back to fixed PRD models.
"""

from __future__ import annotations

from collections import defaultdict


# ── From canonical model (preferred) ────────────────────────────────────────

def build_data_schema_from_canonical(canonical_model: dict) -> dict:
    """Derive schema purely from canonical variables (EAV + core models)."""
    models = [
        {
            "name": "planning_context",
            "fields": [
                {"name": "id", "data_type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            ],
        },
        {
            "name": "driver_assumption",
            "fields": [
                {"name": "variable_name", "data_type": "text", "nullable": False},
                {"name": "value", "data_type": "decimal", "nullable": True},
            ],
        },
        {
            "name": "computed_metric",
            "fields": [
                {"name": "metric_name", "data_type": "text", "nullable": False},
                {"name": "value", "data_type": "decimal", "nullable": True},
            ],
        },
    ]
    return {
        "models": models,
        "variables": canonical_model.get("variables", []),
    }


# ── From raw graph (legacy compat) ─────────────────────────────────────────

_PRD_MODELS = [
    {
        "name": "planning_context",
        "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            {"name": "tenant_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "company_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "scenario_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "assumption_set_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "planning_period_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "version_status", "data_type": "text", "nullable": False, "default": "'draft'"},
        ],
    },
    {
        "name": "driver_assumption",
        "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            {"name": "planning_context_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "variable_name", "data_type": "text", "nullable": False, "default": None},
            {"name": "value", "data_type": "decimal", "nullable": True, "default": None},
            {"name": "unit", "data_type": "text", "nullable": True, "default": None},
        ],
    },
    {
        "name": "computed_metric",
        "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            {"name": "planning_context_id", "data_type": "uuid", "nullable": False, "default": None},
            {"name": "metric_name", "data_type": "text", "nullable": False, "default": None},
            {"name": "formula", "data_type": "text", "nullable": True, "default": None},
            {"name": "value", "data_type": "decimal", "nullable": True, "default": None},
        ],
    },
    {
        "name": "workflow_definition",
        "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            {"name": "name", "data_type": "text", "nullable": False, "default": None},
            {"name": "description", "data_type": "text", "nullable": True, "default": None},
        ],
    },
]


def build_data_schema_from_graph(graph: dict, doc_type: str) -> dict:
    """Legacy schema builder that inspects raw graph nodes."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {n["id"]: n for n in nodes}

    schema: dict = {"doc_type": doc_type, "models": [], "apis": [], "variables": []}

    if doc_type == "PRD":
        # deep-copy to avoid mutating the module constant
        import copy
        schema["models"] = copy.deepcopy(_PRD_MODELS)
    else:
        fields_by_model: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            if edge["type"] == "HAS_FIELD":
                fields_by_model[edge["from"]].append(edge["to"])
        for node in nodes:
            if node["type"] == "DataModel":
                schema["models"].append({
                    "name": node.get("name"),
                    "fields": [node_map[fid] for fid in fields_by_model.get(node["id"], []) if fid in node_map],
                })

    for node in nodes:
        if node["type"] == "API":
            schema["apis"].append({"endpoint": node.get("endpoint"), "method": node.get("method"), "group": node.get("group")})
        elif node["type"] == "Variable":
            schema["variables"].append({"name": node.get("name"), "variable_type": node.get("variable_type")})

    return schema


# ── Canonical schema wrapper ────────────────────────────────────────────────

def build_canonical_schema(schema: dict, variable_registry: dict) -> dict:
    return {
        "entities": [
            {"name": m.get("name"), "fields": m.get("fields", []), "model_type": m.get("model_type", "unknown")}
            for m in schema.get("models", [])
        ],
        "variables": variable_registry.get("variables", []),
    }
