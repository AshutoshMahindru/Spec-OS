"""Tests for the merge module."""

from __future__ import annotations

from spec_os.merge import merge_graphs, merge_schemas, merge_variable_registries


class TestMergeGraphs:
    def test_deduplicates_nodes(self):
        g1 = {"nodes": [{"id": "a", "type": "Variable", "name": "orders"}], "edges": []}
        g2 = {"nodes": [{"id": "a", "type": "Variable", "name": "orders"}], "edges": []}
        merged = merge_graphs([g1, g2])
        assert len(merged["nodes"]) == 1

    def test_merges_edges(self):
        g1 = {"nodes": [], "edges": [{"from": "a", "to": "b", "type": "X"}]}
        g2 = {"nodes": [], "edges": [{"from": "c", "to": "d", "type": "Y"}]}
        merged = merge_graphs([g1, g2])
        assert len(merged["edges"]) == 2


class TestMergeVariableRegistries:
    def test_deduplicates(self):
        r1 = {"variables": [{"name": "orders", "variable_type": "financial"}]}
        r2 = {"variables": [{"name": "orders", "variable_type": "financial"}]}
        merged = merge_variable_registries([r1, r2])
        assert len(merged["variables"]) == 1

    def test_normalizes_equivalent_names(self):
        r1 = {"variables": [{"name": "Orders Per Day", "variable_type": "financial"}]}
        r2 = {"variables": [{"name": "orders_per_day", "variable_type": "financial"}]}
        merged = merge_variable_registries([r1, r2])
        assert len(merged["variables"]) == 1
        assert merged["variables"][0]["name"] == "orders_per_day"


class TestMergeSchemas:
    def test_merges_models(self):
        s1 = {"models": [{"name": "planning_context", "fields": [{"name": "id"}]}], "apis": [], "variables": []}
        s2 = {"models": [{"name": "planning_context", "fields": [{"name": "tenant_id"}]}], "apis": [], "variables": []}
        merged = merge_schemas([s1, s2])
        assert len(merged["models"]) == 1
        field_names = [f["name"] for f in merged["models"][0]["fields"]]
        assert "id" in field_names
        assert "tenant_id" in field_names
