"""Tests for validation: graph integrity, reconciliation, completeness, scoring."""

from __future__ import annotations

from spec_os.api.contracts import build_api_contracts_from_graph
from spec_os.canonical.registry import build_variable_registry
from spec_os.computation.dag import build_computation_graph
from spec_os.extraction.prd import extract_prd_graph
from spec_os.schema.builder import build_data_schema_from_graph
from spec_os.validation.completeness import build_spec_completeness, compute_spec_quality_score
from spec_os.validation.graph_validator import validate_computation_graph, validate_graph
from spec_os.validation.reconciliation import build_variable_to_table_mapping, reconcile_spec


class TestGraphValidator:
    def test_valid_graph(self):
        graph = {
            "nodes": [{"id": "a", "type": "Document"}, {"id": "b", "type": "Section"}],
            "edges": [{"from": "a", "to": "b", "type": "HAS_SECTION"}],
        }
        result = validate_graph(graph)
        assert result["status"] == "ok"

    def test_orphan_edge(self):
        graph = {
            "nodes": [{"id": "a", "type": "Document"}],
            "edges": [{"from": "a", "to": "missing", "type": "HAS_SECTION"}],
        }
        result = validate_graph(graph)
        assert result["status"] == "invalid"
        assert any(i["type"] == "ORPHAN_EDGE" for i in result["issues"])

    def test_missing_id(self):
        graph = {"nodes": [{"id": "", "type": "Document"}], "edges": []}
        result = validate_graph(graph)
        assert any(i["type"] == "INVALID_NODE" for i in result["issues"])


class TestComputationValidator:
    def test_valid(self):
        comp = {"metrics": [{"metric": "revenue", "depends_on": ["orders"]}]}
        result = validate_computation_graph(comp)
        assert result["status"] == "ok"

    def test_duplicate_metric(self):
        comp = {"metrics": [
            {"metric": "revenue", "depends_on": []},
            {"metric": "revenue", "depends_on": []},
        ]}
        result = validate_computation_graph(comp)
        assert any(i["type"] == "DUPLICATE_METRIC" for i in result["issues"])


class TestReconciliation:
    def test_detects_issues(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "r1")
        schema = build_data_schema_from_graph(graph, "PRD")
        registry = build_variable_registry(graph)
        api = build_api_contracts_from_graph(graph)
        rec = reconcile_spec(graph, schema, registry, api)
        assert "issues" in rec


class TestCompleteness:
    def test_ready_for_codegen(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "c1")
        schema = build_data_schema_from_graph(graph, "PRD")
        registry = build_variable_registry(graph)
        api = build_api_contracts_from_graph(graph)
        comp = build_computation_graph(graph)
        rec = reconcile_spec(graph, schema, registry, api)
        completeness = build_spec_completeness(rec, registry, schema, api, comp)
        assert "ready_for_codegen" in completeness

    def test_score(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "c2")
        schema = build_data_schema_from_graph(graph, "PRD")
        registry = build_variable_registry(graph)
        api = build_api_contracts_from_graph(graph)
        comp = build_computation_graph(graph)
        rec = reconcile_spec(graph, schema, registry, api)
        score = compute_spec_quality_score(rec, registry, schema, api, comp)
        assert "score" in score
        assert 0 <= score["score"] <= 100


class TestVariableTableMapping:
    def test_driver_vars_map_to_driver_table(self):
        registry = {"variables": [{"name": "orders"}, {"name": "demand"}]}
        schema = {}
        mapping = build_variable_to_table_mapping(schema, registry)
        assert mapping["orders"]["table"] == "driver_assumption"
        assert mapping["demand"]["table"] == "driver_assumption"

    def test_computed_vars_map_to_metric_table(self):
        registry = {"variables": [{"name": "revenue"}, {"name": "profit"}]}
        mapping = build_variable_to_table_mapping({}, registry)
        assert mapping["revenue"]["table"] == "computed_metric"
        assert mapping["profit"]["table"] == "computed_metric"

    def test_mapping_normalizes_display_names(self):
        registry = {"variables": [{"name": "Orders Per Day", "raw_name": "Orders Per Day"}]}
        mapping = build_variable_to_table_mapping({}, registry)
        assert "orders_per_day" in mapping
        assert mapping["orders_per_day"]["display_name"] == "Orders Per Day"

    def test_reconciliation_accepts_normalized_mapping_keys(self):
        graph = {
            "nodes": [],
            "edges": [],
        }
        schema = {"models": [{"name": "planning_context"}]}
        registry = {"variables": [{"name": "Orders Per Day", "raw_name": "Orders Per Day"}]}
        api = [{"endpoint": "/planning/", "response": {"data": "Planning Context"}}]
        rec = reconcile_spec(graph, schema, registry, api)
        assert rec["status"] == "ok"
