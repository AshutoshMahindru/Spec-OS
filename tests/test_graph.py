"""Tests for graph primitives."""

from __future__ import annotations

from spec_os.graph import add_edge, ensure_node, make_node_registry


class TestMakeNodeRegistry:
    def test_creates_document_root(self):
        nodes, idx, edges = make_node_registry("d1")
        assert len(nodes) == 1
        assert nodes[0]["type"] == "Document"
        assert nodes[0]["id"] == "doc_d1"
        assert edges == []


class TestEnsureNode:
    def test_creates_new_node(self):
        nodes, idx, _ = make_node_registry("d1")
        nid = ensure_node(nodes, idx, "Variable", "name", "Orders", variable_type="financial")
        assert nid in idx
        assert len(nodes) == 2

    def test_deduplicates(self):
        nodes, idx, _ = make_node_registry("d1")
        id1 = ensure_node(nodes, idx, "Variable", "name", "Orders")
        id2 = ensure_node(nodes, idx, "Variable", "name", "Orders")
        assert id1 == id2
        assert len(nodes) == 2  # doc + 1 variable

    def test_upserts_attrs(self):
        nodes, idx, _ = make_node_registry("d1")
        ensure_node(nodes, idx, "Variable", "name", "Orders")
        ensure_node(nodes, idx, "Variable", "name", "Orders", variable_type="financial")
        assert idx[ensure_node(nodes, idx, "Variable", "name", "Orders")].get("variable_type") == "financial"


class TestAddEdge:
    def test_adds_edge(self):
        edges: list[dict] = []
        add_edge(edges, "a", "b", "HAS")
        assert len(edges) == 1

    def test_deduplicates(self):
        edges: list[dict] = []
        add_edge(edges, "a", "b", "HAS")
        add_edge(edges, "a", "b", "HAS")
        assert len(edges) == 1
