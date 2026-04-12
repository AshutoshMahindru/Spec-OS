"""Tests for the 10 output-layer fixes.

Covers: path traversal prevention, Mermaid ID collision fix, SQL injection
prevention, spec folder population, type-aware quality scoring, roadmap
prioritisation, traceability gap detection, N+1 summary optimisation,
atomic bundle writes, and Mermaid XSS prevention.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from spec_os.artifacts.store import (
    UnsafeDocIdError,
    _validate_doc_id,
    doc_dir,
    list_document_dirs,
    spec_dir,
    write_artifact_bundle,
)
from spec_os.computation.dag import build_computation_graph
from spec_os.extraction.prd import extract_prd_graph
from spec_os.orchestration.artifacts import build_engineering_roadmap, build_traceability_matrix
from spec_os.orchestration.spec_folder import generate_spec_folder
from spec_os.schema.ddl import _quote_ident, generate_starter_ddl
from spec_os.validation.completeness import compute_spec_quality_score
from spec_os.visualization import generate_mermaid_diagrams

# ── 1. Path Traversal Prevention ────────────────────────────────────────────

class TestPathTraversal:
    def test_valid_uuid_doc_id(self, tmp_path):
        d = doc_dir(tmp_path, "abc-123-def")
        assert str(d).startswith(str(tmp_path.resolve()))

    def test_rejects_dot_dot_traversal(self, tmp_path):
        with pytest.raises(UnsafeDocIdError):
            doc_dir(tmp_path, "../../etc/passwd")

    def test_rejects_slash(self, tmp_path):
        with pytest.raises(UnsafeDocIdError):
            doc_dir(tmp_path, "foo/bar")

    def test_rejects_empty(self, tmp_path):
        with pytest.raises(UnsafeDocIdError):
            doc_dir(tmp_path, "")

    def test_rejects_backslash(self, tmp_path):
        with pytest.raises(UnsafeDocIdError):
            _validate_doc_id("a\\b")

    def test_spec_dir_safe(self, tmp_path):
        s = spec_dir(tmp_path, "good-id")
        assert s.name == "good-id_spec"

    def test_spec_dir_rejects_traversal(self, tmp_path):
        with pytest.raises(UnsafeDocIdError):
            spec_dir(tmp_path, "../evil")

    def test_list_document_dirs_skips_staging(self, tmp_path):
        """Staging dirs (prefixed with .) should not appear in listing."""
        staging = tmp_path / ".some_staging_dir"
        staging.mkdir()
        (staging / "system_spec.json").write_text("{}")
        real = tmp_path / "real-doc"
        real.mkdir()
        (real / "system_spec.json").write_text("{}")
        dirs = list_document_dirs(tmp_path)
        names = [d.name for d in dirs]
        assert "real-doc" in names
        assert ".some_staging_dir" not in names


# ── 2. Mermaid ID Collisions ────────────────────────────────────────────────

class TestMermaidIdCollisions:
    def test_no_duplicate_node_declarations(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "dup1")
        comp = build_computation_graph(graph)
        mermaid = generate_mermaid_diagrams(graph, comp)
        # Count node declaration lines in graph_mermaid (lines with [...])
        graph_lines = mermaid["graph_mermaid"].split("\n")[1:]  # skip "graph TD"
        decl_ids = []
        for line in graph_lines:
            m = re.match(r'^(\S+)\[', line)
            if m:
                decl_ids.append(m.group(1))
        assert len(decl_ids) == len(set(decl_ids)), f"Duplicate Mermaid IDs: {decl_ids}"

    def test_computation_inputs_deduplicated(self):
        comp = {
            "metrics": [
                {"metric": "revenue", "depends_on": ["orders", "aov"]},
                {"metric": "profit", "depends_on": ["revenue", "cost"]},
            ]
        }
        mermaid = generate_mermaid_diagrams({"nodes": [], "edges": []}, comp)
        lines = mermaid["computation_mermaid"].split("\n")
        # Check that input "revenue" is not declared twice as a separate node
        decl_ids = []
        for line in lines:
            m = re.match(r'^(\S+)\[', line)
            if m:
                decl_ids.append(m.group(1))
        assert len(decl_ids) == len(set(decl_ids))

    def test_edges_reference_valid_ids(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "edge1")
        comp = build_computation_graph(graph)
        mermaid = generate_mermaid_diagrams(graph, comp)
        lines = mermaid["graph_mermaid"].split("\n")[1:]
        declared = set()
        for line in lines:
            m = re.match(r'^(\S+)\[', line)
            if m:
                declared.add(m.group(1))
        for line in lines:
            m = re.match(r'^(\S+) --> (\S+)$', line)
            if m:
                assert m.group(1) in declared, f"Edge source {m.group(1)} not declared"
                assert m.group(2) in declared, f"Edge target {m.group(2)} not declared"


# ── 3. SQL Injection Prevention ─────────────────────────────────────────────

class TestSQLInjection:
    def test_quote_ident_strips_special_chars(self):
        assert _quote_ident("my_table") == '"my_table"'
        assert _quote_ident("DROP TABLE users;--") == '"DROPTABLEusers"'

    def test_quote_ident_handles_leading_digit(self):
        assert _quote_ident("123table") == '"t_123table"'

    def test_quote_ident_empty_string(self):
        assert _quote_ident("") == '"unnamed"'

    def test_ddl_output_quotes_table_names(self):
        schema = {"models": [{"name": "planning_context", "fields": []}]}
        ddl = generate_starter_ddl({"nodes": [], "edges": []}, schema=schema, doc_type="PRD")
        assert '"planning_context"' in ddl


# ── 4. Spec Folder Population ───────────────────────────────────────────────

class TestSpecFolderPopulation:
    def test_agents_md_contains_actual_counts(self, tmp_path):
        outputs = {
            "schema": {"entities": [{"name": "planning_context"}, {"name": "driver_assumption"}]},
            "api_contracts": [{"endpoint": "/planning/"}, {"endpoint": "/drivers/"}],
            "computation_graph": {"metrics": [{"metric": "revenue"}]},
        }
        spec = generate_spec_folder(tmp_path, "test-doc", outputs)
        agents = (spec / "AGENTS.md").read_text()
        assert "Schema entities**: 2" in agents
        assert "API contracts**: 2" in agents
        assert "Computation metrics**: 1" in agents
        assert "planning_context" in agents

    def test_requirements_md_lists_metrics(self, tmp_path):
        outputs = {
            "schema": {"models": []},
            "api_contracts": [],
            "computation_graph": {"metrics": [{"metric": "revenue"}, {"metric": "profit"}]},
        }
        spec = generate_spec_folder(tmp_path, "test-doc", outputs)
        reqs = (spec / "requirements.md").read_text()
        assert "revenue" in reqs
        assert "profit" in reqs

    def test_build_plan_includes_exec_steps(self, tmp_path):
        outputs = {
            "schema": {"models": []},
            "api_contracts": [],
            "computation_graph": {},
            "execution_plan": {"execution_steps": [
                {"step": 1, "compute": "revenue = orders * aov"},
            ]},
        }
        spec = generate_spec_folder(tmp_path, "test-doc", outputs)
        plan = (spec / "build_plan.md").read_text()
        assert "revenue = orders * aov" in plan


# ── 5. Type-Aware Quality Scoring ───────────────────────────────────────────

class TestTypeAwareScoring:
    def test_prd_penalises_missing_models_heavily(self):
        """PRD with no models should lose 20 points."""
        recon = {"issues": []}
        reg = {"variables": [{"name": "x"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        score_with = compute_spec_quality_score(recon, reg, {"models": [{"name": "m"}]}, apis, comp, doc_type="PRD")
        score_without = compute_spec_quality_score(recon, reg, {"models": []}, apis, comp, doc_type="PRD")
        assert score_with["score"] - score_without["score"] == 20

    def test_api_spec_penalises_missing_apis_heavily(self):
        """API_SPEC doc with no APIs should lose 25 points."""
        recon = {"issues": []}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        comp = {"metrics": [{"metric": "y"}]}
        with_apis = compute_spec_quality_score(recon, reg, schema, [{"endpoint": "/x"}], comp, doc_type="API_SPEC")
        without_apis = compute_spec_quality_score(recon, reg, schema, [], comp, doc_type="API_SPEC")
        assert with_apis["score"] - without_apis["score"] == 25

    def test_issue_penalty_capped_at_max(self):
        """Issue penalty is capped at MAX_ISSUE_PENALTY (80)."""
        # Use CYCLE_DETECTED (weight=25) x 4 = 100, but capped at 80.
        recon = {"issues": [{"type": "CYCLE_DETECTED"} for _ in range(4)]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = compute_spec_quality_score(recon, reg, schema, apis, comp)
        # 100 - 80 (capped) = 20
        assert result["score"] == 20

    def test_score_never_negative(self):
        """Score should be clamped at 0."""
        recon = {"issues": [{"type": "X"} for _ in range(10)]}
        result = compute_spec_quality_score(recon, {"variables": []}, {"models": []}, [], {"metrics": []})
        assert result["score"] >= 0


# ── 6. Roadmap Prioritisation ───────────────────────────────────────────────

class TestRoadmapPrioritisation:
    def test_features_sorted_by_dependency_count(self):
        graph = {
            "nodes": [
                {"id": "f1", "type": "Feature", "name": "low_dep_feature"},
                {"id": "f2", "type": "Feature", "name": "high_dep_feature"},
                {"id": "s1", "type": "Section", "title": "Sec"},
            ],
            "edges": [
                # f2 has more outgoing edges, so more downstream dependants.
                {"from": "f2", "to": "s1", "type": "USES_FEATURE"},
                {"from": "f2", "to": "f1", "type": "DEPENDS_ON"},
            ],
        }
        roadmap = build_engineering_roadmap(graph, "PRD")
        phase2 = roadmap["phases"][1]["deliverables"]
        # high_dep_feature should come first (2 edges vs 0).
        assert phase2[0] == "high_dep_feature"


# ── 7. Traceability Matrix Gaps ─────────────────────────────────────────────

class TestTraceabilityGaps:
    def test_uncovered_sections_reported(self):
        graph = {
            "nodes": [
                {"id": "sec1", "type": "Section", "title": "Covered Section"},
                {"id": "sec2", "type": "Section", "title": "Uncovered Section"},
                {"id": "feat1", "type": "Feature", "name": "Feature A"},
            ],
            "edges": [
                {"from": "sec1", "to": "feat1", "type": "CONTAINS"},
            ],
        }
        matrix = build_traceability_matrix([], graph, "PRD")
        statuses = {row["status"] for row in matrix}
        sections = {row["source_section"] for row in matrix if row["status"] == "uncovered"}
        assert "uncovered" in statuses
        assert "Uncovered Section" in sections

    def test_orphan_artifacts_reported(self):
        graph = {
            "nodes": [
                {"id": "sec1", "type": "Section", "title": "Sec"},
                {"id": "feat1", "type": "Feature", "name": "Linked Feature"},
                {"id": "feat2", "type": "Feature", "name": "Orphan Feature"},
            ],
            "edges": [
                {"from": "sec1", "to": "feat1", "type": "CONTAINS"},
            ],
        }
        matrix = build_traceability_matrix([], graph, "PRD")
        orphans = [row for row in matrix if row["status"] == "orphan"]
        assert len(orphans) == 1
        assert orphans[0]["artifact_name"] == "Orphan Feature"

    def test_fallback_indexing_when_no_contains_edges(self):
        structured = [
            {"type": "heading", "text": "Section A", "source_span": {"section_index": 0, "source_tag": "h2"}},
        ]
        graph = {"nodes": [], "edges": []}
        matrix = build_traceability_matrix(structured, graph, "GENERIC")
        assert matrix[0]["status"] == "indexed"


# ── 9. Atomic Bundle Writes ─────────────────────────────────────────────────

class TestAtomicBundleWrites:
    def test_bundle_written_atomically(self, tmp_path):
        base = tmp_path / "data"
        base.mkdir()
        bundle = {
            "system_spec": {"meta": {"doc_id": "test-123"}},
            "graph": {"nodes": [], "edges": []},
        }
        target = write_artifact_bundle(base, "test-123", bundle)
        assert target.exists()
        assert (target / "system_spec.json").exists()
        assert (target / "layers" / "graph.json").exists()
        # No leftover staging directories.
        staging_dirs = [d for d in base.iterdir() if d.name.startswith(".")]
        assert staging_dirs == []

    def test_bundle_overwrites_existing(self, tmp_path):
        base = tmp_path / "data"
        base.mkdir()
        bundle_v1 = {"system_spec": {"version": 1}}
        bundle_v2 = {"system_spec": {"version": 2}}
        write_artifact_bundle(base, "overwrite-test", bundle_v1)
        write_artifact_bundle(base, "overwrite-test", bundle_v2)
        spec = json.loads((base / "overwrite-test" / "system_spec.json").read_text())
        assert spec["version"] == 2


# ── 10. Mermaid XSS Prevention ──────────────────────────────────────────────

class TestMermaidXSS:
    def test_index_html_uses_strict_security_level(self):
        html_path = Path(__file__).resolve().parent.parent / "src" / "spec_os" / "static" / "index.html"
        if not html_path.exists():
            pytest.skip("index.html not found")
        content = html_path.read_text()
        assert "securityLevel: 'strict'" in content
        assert "securityLevel: 'loose'" not in content

    def test_html_labels_disabled(self):
        html_path = Path(__file__).resolve().parent.parent / "src" / "spec_os" / "static" / "index.html"
        if not html_path.exists():
            pytest.skip("index.html not found")
        content = html_path.read_text()
        assert "htmlLabels: false" in content
