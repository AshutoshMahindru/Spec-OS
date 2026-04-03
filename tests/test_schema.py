"""Tests for schema builder, enrichment, and DDL generation."""

from __future__ import annotations

from spec_os.extraction.prd import extract_prd_graph
from spec_os.schema.builder import build_data_schema_from_canonical, build_data_schema_from_graph
from spec_os.schema.ddl import generate_starter_ddl
from spec_os.schema.enrichment import enrich_schema_types


class TestSchemaBuilder:
    def test_prd_uses_canonical_models_not_section_titles(self):
        structured = [
            {"type": "heading", "level": 2, "text": "Business Context Summary"},
            {"type": "paragraph", "text": "This document defines requirements."},
            {"type": "heading", "level": 2, "text": "Finance-First Philosophy"},
            {"type": "paragraph", "text": "Orders * AOV = Revenue"},
        ]
        graph = extract_prd_graph(structured, "s1")
        schema = build_data_schema_from_graph(graph, "PRD")
        model_names = [m["name"] for m in schema["models"]]
        assert "planning_context" in model_names
        assert "Business Context Summary" not in model_names

    def test_canonical_schema_has_core_models(self):
        canonical = {"variables": [{"name": "orders", "raw_names": ["Orders"], "variable_type": "financial"}]}
        schema = build_data_schema_from_canonical(canonical)
        model_names = [m["name"] for m in schema["models"]]
        assert "planning_context" in model_names
        assert "driver_assumption" in model_names
        assert "computed_metric" in model_names


class TestSchemaEnrichment:
    def test_type_tags(self):
        schema = {"models": [
            {"name": "planning_context"},
            {"name": "computed_metric"},
            {"name": "driver_assumption"},
            {"name": "other_table"},
        ]}
        enriched = enrich_schema_types(schema)
        types = {m["name"]: m["model_type"] for m in enriched["models"]}
        assert types["planning_context"] == "dimension"
        assert types["computed_metric"] == "fact"
        assert types["driver_assumption"] == "driver"
        assert types["other_table"] == "generic"


class TestDDLGeneration:
    def test_prd_ddl_contains_canonical_tables(self):
        structured = [
            {"type": "heading", "level": 2, "text": "Finance-First Philosophy"},
            {"type": "paragraph", "text": "Orders * AOV = Revenue"},
        ]
        graph = extract_prd_graph(structured, "d1")
        schema = build_data_schema_from_graph(graph, "PRD")
        ddl = generate_starter_ddl(graph, schema=schema, doc_type="PRD")
        assert "CREATE TABLE IF NOT EXISTS planning_context" in ddl
        assert "CREATE TABLE IF NOT EXISTS driver_assumption" in ddl
        assert "CREATE TABLE IF NOT EXISTS computed_metric" in ddl

    def test_fallback_ddl_for_generic(self):
        graph = {"nodes": [{"id": "doc_1", "type": "Document"}], "edges": []}
        ddl = generate_starter_ddl(graph)
        assert "CREATE TABLE IF NOT EXISTS planning_item" in ddl
