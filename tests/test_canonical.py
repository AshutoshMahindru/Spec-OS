"""Tests for canonical model, variable registry, and ontology."""

from __future__ import annotations

from spec_os.canonical.model import build_canonical_model
from spec_os.canonical.registry import build_variable_registry
from spec_os.extraction.prd import extract_prd_graph
from spec_os.helpers import normalize_name


class TestNormalizeName:
    def test_canonical_aliases(self):
        assert normalize_name("total_revenue") == "revenue"
        assert normalize_name("COGS") == "cost"
        assert normalize_name("avg_order_value") == "aov"

    def test_passthrough(self):
        assert normalize_name("custom_var") == "custom_var"

    def test_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""


class TestCanonicalModel:
    def test_extracts_variables_and_metrics(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "cm1")
        canonical = build_canonical_model(graph)
        assert len(canonical["variables"]) > 0
        assert len(canonical["metrics"]) > 0
        metric = canonical["metrics"][0]
        assert metric["name"] == "revenue"
        assert metric["depends_on"] == ["orders", "aov"]
        assert metric["citations"]

    def test_entities_include_services(self):
        structured = [
            {"type": "heading", "level": 2, "text": "Arch"},
            {"type": "paragraph", "text": "Orders * AOV = Revenue"},
            {"type": "paragraph", "text": "The Computation Engine processes data."},
        ]
        graph = extract_prd_graph(structured, "cm2")
        canonical = build_canonical_model(graph)
        entity_types = {e.get("type") for e in canonical["entities"]}
        assert "Service" in entity_types


class TestVariableRegistry:
    def test_builds_from_graph(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "vr1")
        registry = build_variable_registry(graph)
        assert len(registry["variables"]) > 0
        names = {v["name"] for v in registry["variables"]}
        assert "orders" in names or "aov" in names
