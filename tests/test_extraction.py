"""Tests for extraction module."""

from __future__ import annotations

from spec_os.extraction.classifier import classify_document
from spec_os.extraction.prd import extract_prd_graph
from spec_os.extraction.architecture import extract_architecture_graph
from spec_os.extraction.api_spec import extract_api_spec_graph
from spec_os.extraction.data_dictionary import extract_data_dictionary_graph
from spec_os.extraction.wireframe import extract_wireframe_graph
from spec_os.extraction.generic import extract_generic_graph
from spec_os.extraction.router import route_extraction


class TestClassifyDocument:
    def test_prd(self, prd_structured):
        assert classify_document(prd_structured) == "PRD"

    def test_api_spec(self):
        structured = [{"type": "paragraph", "text": "Base Path: /api/v1/"}]
        assert classify_document(structured) == "API_SPEC"

    def test_data_dictionary(self):
        structured = [{"type": "paragraph", "text": "Schema conventions and total tables"}]
        assert classify_document(structured) == "DATA_DICTIONARY"

    def test_architecture(self):
        structured = [{"type": "paragraph", "text": "Layered Architecture overview"}]
        assert classify_document(structured) == "ARCHITECTURE"

    def test_wireframe(self):
        structured = [{"type": "paragraph", "text": "Dashboard screen tiers overview"}]
        assert classify_document(structured) == "WIREFRAME"

    def test_generic_fallback(self):
        structured = [{"type": "paragraph", "text": "Nothing special"}]
        assert classify_document(structured) == "GENERIC"


class TestPrdExtractor:
    def test_metric_dependencies(self):
        structured = [
            {"type": "heading", "level": 2, "text": "Finance-First Philosophy"},
            {"type": "paragraph", "text": "Orders * AOV = Revenue"},
        ]
        graph = extract_prd_graph(structured, "prd1")
        edge_types = {e["type"] for e in graph["edges"]}
        node_types = {n["type"] for n in graph["nodes"]}
        assert "Metric" in node_types
        assert "Variable" in node_types
        assert "DEPENDS_ON" in edge_types

    def test_feature_extraction(self):
        structured = [
            {"type": "heading", "level": 2, "text": "MVP Definition"},
            {"type": "paragraph", "text": "The MVP includes planning workflow support."},
        ]
        graph = extract_prd_graph(structured, "prd2")
        node_types = {n["type"] for n in graph["nodes"]}
        assert "Feature" in node_types


class TestArchitectureExtractor:
    def test_flow_edges(self, architecture_structured):
        graph = extract_architecture_graph(architecture_structured, "arch1")
        edge_types = {e["type"] for e in graph["edges"]}
        assert "FEEDS" in edge_types
        assert "OUTPUTS_TO" in edge_types


class TestDataDictionaryExtractor:
    def test_data_model_and_fields(self, data_dictionary_structured):
        graph = extract_data_dictionary_graph(data_dictionary_structured, "dd1")
        node_types = {n["type"] for n in graph["nodes"]}
        assert "DataModel" in node_types
        assert "Field" in node_types


class TestApiSpecExtractor:
    def test_api_extraction(self, api_structured):
        graph = extract_api_spec_graph(api_structured, "api1")
        node_types = {n["type"] for n in graph["nodes"]}
        assert "API" in node_types


class TestRouter:
    def test_routes_to_prd(self, prd_structured):
        graph = route_extraction(prd_structured, "r1", "PRD")
        assert len(graph["nodes"]) > 1

    def test_routes_to_generic(self):
        structured = [{"type": "heading", "level": 1, "text": "Misc"}]
        graph = route_extraction(structured, "r2", "GENERIC")
        assert any(n["type"] == "Section" for n in graph["nodes"])
