"""Tests for the visualization (Mermaid) module."""

from __future__ import annotations

from spec_os.computation.dag import build_computation_graph
from spec_os.extraction.prd import extract_prd_graph
from spec_os.visualization import generate_mermaid_diagrams


class TestMermaidDiagrams:
    def test_graph_diagram_starts_with_graph_td(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "m1")
        comp = build_computation_graph(graph)
        mermaid = generate_mermaid_diagrams(graph, comp)
        assert mermaid["graph_mermaid"].startswith("graph TD")
        assert mermaid["computation_mermaid"].startswith("graph TD")

    def test_empty_graph(self):
        mermaid = generate_mermaid_diagrams({"nodes": [], "edges": []}, {"metrics": []})
        assert "graph TD" in mermaid["graph_mermaid"]
