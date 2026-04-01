"""Tests for API contracts and bindings."""

from __future__ import annotations

from spec_os.api.contracts import (
    bind_api_to_schema,
    build_api_contracts_from_canonical,
    build_api_contracts_from_graph,
)
from spec_os.extraction.api_spec import extract_api_spec_graph


class TestApiContracts:
    def test_from_graph(self, api_structured):
        graph = extract_api_spec_graph(api_structured, "ac1")
        contracts = build_api_contracts_from_graph(graph)
        assert len(contracts) > 0
        assert all("endpoint" in c for c in contracts)

    def test_from_canonical_with_api_entities(self):
        canonical = {
            "entities": [
                {"type": "API", "endpoint": "/planning/", "method": "GET"},
                {"type": "Service", "name": "Compute"},
            ],
        }
        contracts = build_api_contracts_from_canonical(canonical)
        assert len(contracts) == 1
        assert contracts[0]["endpoint"] == "/planning/"

    def test_from_canonical_without_apis(self):
        canonical = {"entities": [{"type": "Service", "name": "Compute"}]}
        contracts = build_api_contracts_from_canonical(canonical)
        assert contracts == []


class TestBindApiToSchema:
    def test_binds_planning(self):
        apis = [{"endpoint": "/planning/", "method": "GET"}]
        schema = {"models": [{"name": "planning_context"}]}
        bindings = bind_api_to_schema(apis, schema)
        assert bindings[0]["model"] == "planning_context"

    def test_binds_driver(self):
        apis = [{"endpoint": "/driver/", "method": "POST"}]
        bindings = bind_api_to_schema(apis, {})
        assert bindings[0]["model"] == "driver_assumption"
