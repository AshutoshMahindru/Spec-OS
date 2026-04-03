"""Enrich schema models with semantic type tags."""

from __future__ import annotations


def enrich_schema_types(schema: dict) -> dict:
    """Tag each model with a ``model_type`` (dimension / fact / driver / generic)."""
    for m in schema.get("models", []):
        name = (m.get("name") or "").lower()
        if "context" in name:
            m["model_type"] = "dimension"
        elif "metric" in name:
            m["model_type"] = "fact"
        elif "assumption" in name:
            m["model_type"] = "driver"
        else:
            m["model_type"] = "generic"
    return schema
