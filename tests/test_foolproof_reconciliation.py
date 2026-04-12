"""Tests for the foolproof reconciliation changes (A–E).

Covers:
  A  Multi-valued canonical model (formula & variable type provenance)
  B  Graph-derived driver/computed classification, expanded ontology, fuzzy aliases
  C  Unified validation (edge integrity, computation issues merged)
  D  Severity-aware completeness & weighted quality scoring
  E  Schema merge conflict detection (field types, duplicate APIs)
"""

from __future__ import annotations

from spec_os.artifacts import ReconciliationModel
from spec_os.canonical.model import build_canonical_model
from spec_os.computation.dag import build_computation_graph
from spec_os.constants import BLOCKING_ISSUE_TYPES, ISSUE_WEIGHTS, MAX_ISSUE_PENALTY
from spec_os.helpers import find_possible_aliases, levenshtein_ratio, normalize_name
from spec_os.merge import merge_schemas
from spec_os.validation.completeness import build_spec_completeness, compute_spec_quality_score
from spec_os.validation.graph_validator import validate_computation_graph, validate_graph
from spec_os.validation.reconciliation import (
    build_variable_to_table_mapping,
    reconcile_spec,
)

# ═══════════════════════════════════════════════════════════════════════════════
# A: Multi-valued canonical model
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiValuedCanonicalModel:
    """Change A: metrics accumulate definitions[], variables track observed_types."""

    def test_metric_stores_definitions_list(self):
        graph = {
            "nodes": [
                {"id": "doc_t1", "type": "Document"},
                {"id": "m1", "type": "Metric", "formula": "Revenue = Orders * AOV",
                 "citations": [{"text": "formula1"}]},
            ],
            "edges": [],
        }
        canonical = build_canonical_model(graph)
        assert len(canonical["metrics"]) == 1
        metric = canonical["metrics"][0]
        assert metric["name"] == "revenue"
        assert "definitions" in metric
        assert len(metric["definitions"]) == 1
        assert metric["definitions"][0]["doc_id"] == "t1"

    def test_conflicting_formulas_accumulate(self):
        """Two Metric nodes with different formulas for 'revenue' both appear in definitions."""
        graph = {
            "nodes": [
                {"id": "doc_t2", "type": "Document"},
                {"id": "m1", "type": "Metric", "formula": "Revenue = Orders * AOV",
                 "citations": [{"text": "v1"}]},
                {"id": "m2", "type": "Metric", "formula": "Revenue = Orders * AOV * Discount",
                 "citations": [{"text": "v2"}]},
            ],
            "edges": [],
        }
        canonical = build_canonical_model(graph)
        metric = canonical["metrics"][0]
        assert metric["name"] == "revenue"
        assert len(metric["definitions"]) == 2
        formulas = [d["formula"] for d in metric["definitions"]]
        assert any("discount" in f.lower() for f in formulas)

    def test_variable_observed_types_tracked(self):
        graph = {
            "nodes": [
                {"id": "doc_t3", "type": "Document"},
                {"id": "v1", "type": "Variable", "name": "Revenue", "variable_type": "financial",
                 "citations": []},
                {"id": "v2", "type": "Variable", "name": "Revenue", "variable_type": "display",
                 "citations": []},
            ],
            "edges": [],
        }
        canonical = build_canonical_model(graph)
        var = next(v for v in canonical["variables"] if v["name"] == "revenue")
        assert len(var["observed_types"]) == 2
        types = {t for t, _ in var["observed_types"]}
        assert types == {"financial", "display"}

    def test_reconciliation_flags_conflicting_formulas(self):
        graph = {
            "nodes": [
                {"id": "doc_t4", "type": "Document"},
                {"id": "m1", "type": "Metric", "formula": "Revenue = Orders * AOV"},
                {"id": "m2", "type": "Metric", "formula": "Revenue = Orders * Price"},
                {"id": "v1", "type": "Variable", "name": "Orders", "variable_type": "financial"},
                {"id": "v2", "type": "Variable", "name": "AOV", "variable_type": "financial"},
                {"id": "v3", "type": "Variable", "name": "Price", "variable_type": "financial"},
            ],
            "edges": [],
        }
        canonical = build_canonical_model(graph)
        schema = {"models": [{"name": "planning_context"}]}
        registry = {"variables": canonical["variables"]}
        api = []
        rec = reconcile_spec(
            graph, schema, registry, api,
            canonical_model=canonical,
        )
        assert any(i["type"] == "CONFLICTING_FORMULA" for i in rec["issues"])
        conflict = next(i for i in rec["issues"] if i["type"] == "CONFLICTING_FORMULA")
        assert conflict["metric"] == "revenue"
        assert len(conflict["definitions"]) == 2

    def test_reconciliation_flags_conflicting_variable_types(self):
        graph = {
            "nodes": [
                {"id": "doc_t5", "type": "Document"},
                {"id": "v1", "type": "Variable", "name": "Revenue", "variable_type": "financial"},
                {"id": "v2", "type": "Variable", "name": "Revenue", "variable_type": "display"},
            ],
            "edges": [],
        }
        canonical = build_canonical_model(graph)
        schema = {"models": [{"name": "planning_context"}]}
        registry = {"variables": canonical["variables"]}
        rec = reconcile_spec(
            graph, schema, registry, [],
            canonical_model=canonical,
        )
        assert any(i["type"] == "CONFLICTING_VARIABLE_TYPE" for i in rec["issues"])

    def test_pydantic_model_validates_formula_conflict(self):
        """ReconciliationModel accepts CONFLICTING_FORMULA issues."""
        raw = {
            "issues": [{
                "type": "CONFLICTING_FORMULA",
                "metric": "revenue",
                "definitions": [
                    {"formula": "revenue = orders * aov", "doc_id": "d1"},
                    {"formula": "revenue = orders * price", "doc_id": "d2"},
                ],
            }],
            "status": "needs_review",
        }
        model = ReconciliationModel.model_validate(raw)
        assert model.issues[0].type == "CONFLICTING_FORMULA"


# ═══════════════════════════════════════════════════════════════════════════════
# B: Graph-derived classification & expanded ontology
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphDerivedClassification:
    """Change B: driver/computed classification from computation graph."""

    def test_driver_classified_from_computation_graph(self):
        """A variable in available_inputs but not a metric output → driver."""
        registry = {"variables": [{"name": "orders"}, {"name": "revenue"}]}
        comp = {
            "metrics": [{"metric": "revenue", "depends_on": ["orders", "aov"]}],
            "available_inputs": ["orders", "aov"],
        }
        mapping = build_variable_to_table_mapping({}, registry, comp)
        assert mapping["orders"]["table"] == "driver_assumption"
        assert mapping["revenue"]["table"] == "computed_metric"

    def test_unknown_variable_falls_back(self):
        """A variable not in inputs or outputs falls back to heuristic."""
        registry = {"variables": [{"name": "headcount"}]}
        comp = {"metrics": [], "available_inputs": []}
        mapping = build_variable_to_table_mapping({}, registry, comp)
        # Not in the hardcoded driver set → computed_metric.
        assert mapping["headcount"]["table"] == "computed_metric"

    def test_backward_compat_without_computation_graph(self):
        """build_variable_to_table_mapping works without computation_graph."""
        registry = {"variables": [{"name": "orders"}, {"name": "revenue"}]}
        mapping = build_variable_to_table_mapping({}, registry)
        assert mapping["orders"]["table"] == "driver_assumption"
        assert mapping["revenue"]["table"] == "computed_metric"


class TestExpandedOntology:
    """Change B: expanded CANONICAL_ONTOLOGY."""

    def test_margin_aliases(self):
        assert normalize_name("Gross Margin") == "margin"
        assert normalize_name("GM") == "margin"
        assert normalize_name("contribution_margin") == "margin"
        assert normalize_name("CM") == "margin"

    def test_capex_aliases(self):
        assert normalize_name("capital_expenditure") == "capex"
        assert normalize_name("cap_ex") == "capex"

    def test_opex_aliases(self):
        assert normalize_name("operating_expense") == "opex"
        assert normalize_name("op_ex") == "opex"

    def test_labor_aliases(self):
        assert normalize_name("labour") == "labor"
        assert normalize_name("labor_cost") == "labor"

    def test_demand_aliases(self):
        assert normalize_name("customer_demand") == "demand"


class TestFuzzyAliasDetection:
    """Change B: levenshtein-based alias detection."""

    def test_levenshtein_ratio_identical(self):
        assert levenshtein_ratio("abc", "abc") == 1.0

    def test_levenshtein_ratio_completely_different(self):
        assert levenshtein_ratio("abc", "xyz") < 0.5

    def test_levenshtein_ratio_similar(self):
        ratio = levenshtein_ratio("revenue", "revenues")
        assert ratio > 0.8

    def test_find_possible_aliases_substring(self):
        names = ["order_count", "order"]
        pairs = find_possible_aliases(names)
        assert len(pairs) == 1
        assert pairs[0][2] == 1.0  # substring match → 1.0

    def test_find_possible_aliases_no_false_positives(self):
        names = ["revenue", "demand", "capex"]
        pairs = find_possible_aliases(names, threshold=0.8)
        assert pairs == []

    def test_reconciliation_flags_possible_aliases(self):
        """Variables with suspiciously similar names are flagged."""
        graph = {"nodes": [], "edges": []}
        schema = {"models": []}
        # "total_revenue_amount" and "total_revenue" are substrings.
        registry = {"variables": [
            {"name": "total_revenue_amount"},
            {"name": "total_revenue"},
        ]}
        rec = reconcile_spec(graph, schema, registry, [])
        alias_issues = [i for i in rec["issues"] if i["type"] == "POSSIBLE_ALIAS"]
        assert len(alias_issues) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# C: Unified validation (edge integrity, computation issues merged)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnifiedValidation:
    """Change C: reconciliation walks edge types and merges comp validation."""

    def test_broken_edge_detected(self):
        """An edge referencing a missing node ID is flagged."""
        graph = {
            "nodes": [{"id": "doc_c1", "type": "Document"}],
            "edges": [{"from": "doc_c1", "to": "missing_node", "type": "HAS_SECTION"}],
        }
        rec = reconcile_spec(graph, {"models": []}, {"variables": []}, [])
        assert any(i["type"] == "BROKEN_EDGE" for i in rec["issues"])

    def test_type_mismatch_edge_detected(self):
        """An edge with wrong source/target types is flagged."""
        graph = {
            "nodes": [
                {"id": "feat1", "type": "Feature", "name": "F1"},
                {"id": "var1", "type": "Variable", "name": "V1"},
            ],
            # Feature → FEEDS → Variable is not a valid edge type.
            "edges": [{"from": "feat1", "to": "var1", "type": "FEEDS"}],
        }
        rec = reconcile_spec(graph, {"models": []}, {"variables": []}, [])
        assert any(i["type"] == "TYPE_MISMATCH_EDGE" for i in rec["issues"])

    def test_valid_edges_no_integrity_issues(self):
        """Well-formed edges do not produce false positives."""
        graph = {
            "nodes": [
                {"id": "doc_c3", "type": "Document"},
                {"id": "sec1", "type": "Section", "title": "S1"},
                {"id": "feat1", "type": "Feature", "name": "F1"},
            ],
            "edges": [
                {"from": "doc_c3", "to": "sec1", "type": "HAS_SECTION"},
                {"from": "sec1", "to": "feat1", "type": "CONTAINS"},
            ],
        }
        rec = reconcile_spec(graph, {"models": []}, {"variables": []}, [])
        edge_issues = [i for i in rec["issues"] if i["type"] in ("BROKEN_EDGE", "TYPE_MISMATCH_EDGE")]
        assert edge_issues == []

    def test_computation_validation_merged_into_reconciliation(self):
        """Computation validation issues appear in reconciliation output."""
        comp = {
            "metrics": [
                {"metric": "revenue", "depends_on": ["profit"]},
                {"metric": "profit", "depends_on": ["revenue"]},
            ],
            "available_inputs": [],
        }
        comp_validation = validate_computation_graph(comp)
        graph = {"nodes": [], "edges": []}
        rec = reconcile_spec(
            graph, {"models": []}, {"variables": []}, [],
            computation_validation=comp_validation,
        )
        assert any(i["type"] == "CYCLE_DETECTED" for i in rec["issues"])

    def test_graph_validation_merged_into_reconciliation(self):
        """Graph structural issues appear in reconciliation output."""
        graph = {
            "nodes": [{"id": "a", "type": "Document"}],
            "edges": [{"from": "a", "to": "missing", "type": "HAS_SECTION"}],
        }
        graph_val = validate_graph(graph)
        rec = reconcile_spec(
            graph, {"models": []}, {"variables": []}, [],
            graph_validation=graph_val,
        )
        assert any(i["type"] == "ORPHAN_EDGE" for i in rec["issues"])


# ═══════════════════════════════════════════════════════════════════════════════
# D: Severity-aware completeness & weighted quality scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeverityAwareCompleteness:
    """Change D: blocking vs warning classification."""

    def test_cycle_detected_is_blocking(self):
        recon = {"issues": [{"type": "CYCLE_DETECTED", "metrics": ["a", "b"]}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = build_spec_completeness(recon, reg, schema, apis, comp)
        assert result["ready_for_codegen"] is False
        assert any("Circular dependency" in b for b in result["blocking_issues"])

    def test_conflicting_formula_is_blocking(self):
        recon = {"issues": [{"type": "CONFLICTING_FORMULA", "metric": "revenue"}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = build_spec_completeness(recon, reg, schema, apis, comp)
        assert result["ready_for_codegen"] is False

    def test_possible_alias_is_warning_not_blocking(self):
        recon = {"issues": [{"type": "POSSIBLE_ALIAS", "variable_a": "rev", "variable_b": "revenue", "similarity": 0.9}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = build_spec_completeness(recon, reg, schema, apis, comp)
        assert result["ready_for_codegen"] is True
        assert len(result["warnings"]) >= 1

    def test_clean_spec_is_ready_for_codegen(self):
        recon = {"issues": []}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = build_spec_completeness(recon, reg, schema, apis, comp)
        assert result["ready_for_codegen"] is True
        assert result["blocking_issues"] == []

    def test_all_blocking_types_block_codegen(self):
        """Every type in BLOCKING_ISSUE_TYPES prevents codegen readiness."""
        for itype in BLOCKING_ISSUE_TYPES:
            recon = {"issues": [{"type": itype}]}
            reg = {"variables": [{"name": "x"}]}
            schema = {"models": [{"name": "m"}]}
            apis = [{"endpoint": "/x"}]
            comp = {"metrics": [{"metric": "y"}]}
            result = build_spec_completeness(recon, reg, schema, apis, comp)
            assert result["ready_for_codegen"] is False, f"{itype} should be blocking"


class TestWeightedQualityScoring:
    """Change D: per-issue-type weights."""

    def test_cycle_costs_25_points(self):
        base = {"issues": []}
        with_cycle = {"issues": [{"type": "CYCLE_DETECTED"}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        score_clean = compute_spec_quality_score(base, reg, schema, apis, comp)
        score_cycle = compute_spec_quality_score(with_cycle, reg, schema, apis, comp)
        assert score_clean["score"] - score_cycle["score"] == ISSUE_WEIGHTS["CYCLE_DETECTED"]

    def test_possible_alias_costs_1_point(self):
        base = {"issues": []}
        with_alias = {"issues": [{"type": "POSSIBLE_ALIAS"}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        score_clean = compute_spec_quality_score(base, reg, schema, apis, comp)
        score_alias = compute_spec_quality_score(with_alias, reg, schema, apis, comp)
        assert score_clean["score"] - score_alias["score"] == ISSUE_WEIGHTS["POSSIBLE_ALIAS"]

    def test_weighted_penalty_capped(self):
        """Total issue penalty cannot exceed MAX_ISSUE_PENALTY."""
        # 10 CYCLE_DETECTED @ 25 each = 250, capped at 80.
        recon = {"issues": [{"type": "CYCLE_DETECTED"} for _ in range(10)]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        result = compute_spec_quality_score(recon, reg, schema, apis, comp)
        assert result["score"] == 100 - MAX_ISSUE_PENALTY

    def test_score_never_negative(self):
        """Score is clamped at 0 even with extreme penalties."""
        recon = {"issues": [{"type": "CYCLE_DETECTED"} for _ in range(10)]}
        result = compute_spec_quality_score(recon, {"variables": []}, {"models": []}, [], {"metrics": []})
        assert result["score"] >= 0

    def test_unknown_issue_type_uses_default_weight(self):
        """Unknown issue types get DEFAULT_ISSUE_WEIGHT."""
        from spec_os.constants import DEFAULT_ISSUE_WEIGHT
        base = {"issues": []}
        with_unknown = {"issues": [{"type": "NEVER_HEARD_OF_THIS"}]}
        reg = {"variables": [{"name": "x"}]}
        schema = {"models": [{"name": "m"}]}
        apis = [{"endpoint": "/x"}]
        comp = {"metrics": [{"metric": "y"}]}
        s1 = compute_spec_quality_score(base, reg, schema, apis, comp)
        s2 = compute_spec_quality_score(with_unknown, reg, schema, apis, comp)
        assert s1["score"] - s2["score"] == DEFAULT_ISSUE_WEIGHT


# ═══════════════════════════════════════════════════════════════════════════════
# E: Schema merge conflict detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaMergeConflictDetection:
    """Change E: field-type conflicts and API deduplication."""

    def test_field_type_conflict_detected(self):
        s1 = {"models": [{"name": "driver_assumption", "fields": [
            {"name": "value", "data_type": "decimal", "nullable": True},
        ]}], "apis": [], "variables": []}
        s2 = {"models": [{"name": "driver_assumption", "fields": [
            {"name": "value", "data_type": "text", "nullable": False},
        ]}], "apis": [], "variables": []}
        _, conflicts = merge_schemas([s1, s2])
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "CONFLICTING_FIELD_TYPE"
        assert conflicts[0]["model"] == "driver_assumption"
        assert conflicts[0]["field"] == "value"

    def test_compatible_fields_no_conflict(self):
        s1 = {"models": [{"name": "m1", "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False},
        ]}], "apis": [], "variables": []}
        s2 = {"models": [{"name": "m1", "fields": [
            {"name": "id", "data_type": "uuid", "nullable": False},
        ]}], "apis": [], "variables": []}
        _, conflicts = merge_schemas([s1, s2])
        assert conflicts == []

    def test_duplicate_api_detected(self):
        s1 = {"models": [], "apis": [
            {"endpoint": "/planning/", "method": "GET"},
        ], "variables": []}
        s2 = {"models": [], "apis": [
            {"endpoint": "/planning/", "method": "GET"},
        ], "variables": []}
        merged, conflicts = merge_schemas([s1, s2])
        dup_conflicts = [c for c in conflicts if c["type"] == "DUPLICATE_API"]
        assert len(dup_conflicts) == 1
        # Merged APIs should contain only one entry.
        assert len(merged["apis"]) == 1

    def test_different_apis_no_duplicate(self):
        s1 = {"models": [], "apis": [
            {"endpoint": "/planning/", "method": "GET"},
        ], "variables": []}
        s2 = {"models": [], "apis": [
            {"endpoint": "/drivers/", "method": "POST"},
        ], "variables": []}
        merged, conflicts = merge_schemas([s1, s2])
        assert len(merged["apis"]) == 2
        dup_conflicts = [c for c in conflicts if c["type"] == "DUPLICATE_API"]
        assert dup_conflicts == []

    def test_merge_conflicts_flow_into_reconciliation(self):
        """merge_conflicts parameter is incorporated into reconcile_spec."""
        conflicts = [{"type": "CONFLICTING_FIELD_TYPE", "model": "m", "field": "f"}]
        rec = reconcile_spec(
            {"nodes": [], "edges": []},
            {"models": []},
            {"variables": []},
            [],
            merge_conflicts=conflicts,
        )
        assert any(i["type"] == "CONFLICTING_FIELD_TYPE" for i in rec["issues"])

    def test_pydantic_model_validates_field_conflict(self):
        raw = {
            "issues": [{
                "type": "CONFLICTING_FIELD_TYPE",
                "model": "driver_assumption",
                "field": "value",
                "existing": {"data_type": "decimal", "nullable": True},
                "incoming": {"data_type": "text", "nullable": False},
            }],
            "status": "needs_review",
        }
        model = ReconciliationModel.model_validate(raw)
        assert model.issues[0].type == "CONFLICTING_FIELD_TYPE"
        assert model.issues[0].field == "value"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: end-to-end foolproof reconciliation
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndFoolproofReconciliation:
    """Integration tests verifying multiple changes work together."""

    def test_full_pipeline_reconciliation_with_all_checks(self):
        """A graph with known issues should surface them all."""
        graph = {
            "nodes": [
                {"id": "doc_e2e", "type": "Document"},
                {"id": "sec1", "type": "Section", "title": "Finance"},
                # Two conflicting metrics.
                {"id": "m1", "type": "Metric", "formula": "Revenue = Orders * AOV"},
                {"id": "m2", "type": "Metric", "formula": "Revenue = Orders * Price"},
                # Variables.
                {"id": "v1", "type": "Variable", "name": "Orders", "variable_type": "financial"},
                {"id": "v2", "type": "Variable", "name": "AOV", "variable_type": "financial"},
                {"id": "v3", "type": "Variable", "name": "Price", "variable_type": "financial"},
            ],
            "edges": [
                {"from": "doc_e2e", "to": "sec1", "type": "HAS_SECTION"},
                {"from": "sec1", "to": "m1", "type": "CONTAINS"},
            ],
        }
        canonical = build_canonical_model(graph)
        registry = {"variables": canonical["variables"]}
        schema = {"models": [{"name": "planning_context"}]}
        api = [{"endpoint": "/planning/", "response": {"data": "planning_context"}}]
        comp = build_computation_graph(canonical)
        comp_val = validate_computation_graph(comp)
        graph_val = validate_graph(graph)

        rec = reconcile_spec(
            graph, schema, registry, api,
            canonical_model=canonical,
            computation_validation=comp_val,
            graph_validation=graph_val,
        )

        issue_types = {i["type"] for i in rec["issues"]}
        assert "CONFLICTING_FORMULA" in issue_types
        assert rec["status"] == "needs_review"

        # Completeness should reflect the conflict.
        completeness = build_spec_completeness(rec, registry, schema, api, comp)
        assert completeness["ready_for_codegen"] is False

    def test_clean_spec_passes_all_checks(self):
        """A well-formed graph with no issues passes cleanly."""
        graph = {
            "nodes": [
                {"id": "doc_clean", "type": "Document"},
                {"id": "sec1", "type": "Section", "title": "Finance"},
                {"id": "m1", "type": "Metric", "formula": "Revenue = Orders * AOV"},
                {"id": "v1", "type": "Variable", "name": "Orders", "variable_type": "financial"},
                {"id": "v2", "type": "Variable", "name": "AOV", "variable_type": "financial"},
            ],
            "edges": [
                {"from": "doc_clean", "to": "sec1", "type": "HAS_SECTION"},
                {"from": "sec1", "to": "m1", "type": "CONTAINS"},
                {"from": "sec1", "to": "v1", "type": "CONTAINS"},
                {"from": "sec1", "to": "v2", "type": "CONTAINS"},
                {"from": "m1", "to": "v1", "type": "DEPENDS_ON"},
                {"from": "m1", "to": "v2", "type": "DEPENDS_ON"},
            ],
        }
        canonical = build_canonical_model(graph)
        registry = {"variables": canonical["variables"]}
        schema = {"models": [{"name": "planning_context"}]}
        api = [{"endpoint": "/planning/", "response": {"data": "planning_context"}}]
        comp = build_computation_graph(canonical)
        comp_val = validate_computation_graph(comp)
        graph_val = validate_graph(graph)

        rec = reconcile_spec(
            graph, schema, registry, api,
            canonical_model=canonical,
            computation_validation=comp_val,
            graph_validation=graph_val,
        )

        blocking_types = {i["type"] for i in rec["issues"]} & BLOCKING_ISSUE_TYPES
        assert blocking_types == set(), f"Unexpected blocking issues: {blocking_types}"

        completeness = build_spec_completeness(rec, registry, schema, api, comp)
        assert completeness["ready_for_codegen"] is True

    def test_merge_all_docs_carries_conflicts_through(self):
        """merge_all_docs propagates schema conflicts into reconciliation."""
        from spec_os.merge import merge_all_docs

        doc1 = {
            "graph": {
                "nodes": [{"id": "doc_d1", "type": "Document"}],
                "edges": [],
            },
            "schema": {"models": [{"name": "m1", "fields": [
                {"name": "val", "data_type": "decimal", "nullable": True},
            ]}], "apis": [{"endpoint": "/x", "method": "GET"}], "variables": []},
            "variable_registry": {"variables": []},
        }
        doc2 = {
            "graph": {
                "nodes": [{"id": "doc_d2", "type": "Document"}],
                "edges": [],
            },
            "schema": {"models": [{"name": "m1", "fields": [
                {"name": "val", "data_type": "text", "nullable": False},
            ]}], "apis": [{"endpoint": "/x", "method": "GET"}], "variables": []},
            "variable_registry": {"variables": []},
        }
        merged = merge_all_docs([doc1, doc2])
        issue_types = {i["type"] for i in merged["reconciliation"]["issues"]}
        assert "CONFLICTING_FIELD_TYPE" in issue_types
        assert "DUPLICATE_API" in issue_types
