"""Generate starter DDL (PostgreSQL) from graph + schema."""

from __future__ import annotations

import re
from collections import defaultdict

_TYPE_MAP = {
    "uuid": "UUID",
    "timestamp": "TIMESTAMP WITH TIME ZONE",
    "decimal": "DECIMAL(19,4)",
    "text": "TEXT",
    "boolean": "BOOLEAN",
}


def _sql_type(dtype: str) -> str:
    return _TYPE_MAP.get(str(dtype).lower(), str(dtype).upper())


def generate_starter_ddl(graph: dict, *, schema: dict | None = None, doc_type: str | None = None) -> str:
    """Return a DDL string suitable for PostgreSQL."""
    blocks: list[str] = [
        "-- Starter DDL generated from ingestion graph",
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
        "",
    ]

    if doc_type == "PRD" and schema:
        _ddl_from_schema_models(blocks, schema)
        blocks.extend([
            "ALTER TABLE driver_assumption ADD CONSTRAINT fk_driver_assumption_context"
            " FOREIGN KEY (planning_context_id) REFERENCES planning_context(id);",
            "ALTER TABLE computed_metric ADD CONSTRAINT fk_computed_metric_context"
            " FOREIGN KEY (planning_context_id) REFERENCES planning_context(id);",
            "CREATE INDEX IF NOT EXISTS idx_planning_context_grain"
            " ON planning_context (tenant_id, company_id, scenario_id, assumption_set_id, planning_period_id);",
        ])
        return "\n".join(blocks)

    if _ddl_from_graph_data_models(blocks, graph):
        return "\n".join(blocks)

    # Fallback
    blocks.extend([
        "CREATE TABLE IF NOT EXISTS planning_item (",
        "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
        "    tenant_id UUID NOT NULL,",
        "    scenario_id UUID,",
        "    planning_period_id UUID,",
        "    name TEXT NOT NULL,",
        "    value DECIMAL(19,4),",
        "    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),",
        "    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
        ");",
        "",
        "CREATE TABLE IF NOT EXISTS api_contract (",
        "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
        "    endpoint TEXT NOT NULL,",
        "    method TEXT,",
        "    group_name TEXT,",
        "    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
        ");",
    ])
    return "\n".join(blocks)


# ── Internal helpers ────────────────────────────────────────────────────────

def _field_line(field: dict) -> str:
    dtype = _sql_type(field.get("data_type") or "TEXT")
    nullable = "" if field.get("nullable", True) else " NOT NULL"
    default = f" DEFAULT {field['default']}" if field.get("default") not in (None, "") else ""
    return f"    {field['name']} {dtype}{nullable}{default},"


def _ddl_from_schema_models(blocks: list[str], schema: dict) -> None:
    for model in schema.get("models", []):
        lines = [f"CREATE TABLE IF NOT EXISTS {model['name']} ("]
        for field in model.get("fields", []):
            lines.append(_field_line(field))
        lines.append("    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),")
        lines.append("    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
        lines.append(");")
        blocks.extend(lines)
        blocks.append("")


def _ddl_from_graph_data_models(blocks: list[str], graph: dict) -> bool:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {n["id"]: n for n in nodes}
    fields_by_model: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["type"] == "HAS_FIELD":
            fields_by_model[edge["from"]].append(edge["to"])

    emitted = False
    for node in nodes:
        if node["type"] != "DataModel":
            continue
        table_name = re.sub(r"[^a-z0-9]+", "_", node.get("name", "model").lower()).strip("_") or "model"
        if re.match(r"^\d", table_name):
            table_name = f"t_{table_name}"
        lines = [f"CREATE TABLE IF NOT EXISTS {table_name} (", "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"]
        for fid in fields_by_model.get(node["id"], []):
            field = node_map.get(fid)
            if field:
                lines.append(_field_line(field))
        lines.append("    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),")
        lines.append("    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
        lines.append(");")
        blocks.extend(lines)
        blocks.append("")
        emitted = True

    return emitted
