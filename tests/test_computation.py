"""Tests for computation module: formula engine, DAG, execution plan."""

from __future__ import annotations

from spec_os.computation.formula import evaluate_formula, tokenize, parse_formula
from spec_os.computation.dag import build_computation_graph, build_execution_plan
from spec_os.extraction.prd import extract_prd_graph


class TestFormulaEngine:
    def test_basic_arithmetic(self):
        assert evaluate_formula("2 + 3", {}) == 5.0
        assert evaluate_formula("10 * 5", {}) == 50.0

    def test_variable_resolution(self):
        result = evaluate_formula("Orders * AOV", {"Orders": 100, "AOV": 25})
        assert result == 2500.0

    def test_function_sum(self):
        result = evaluate_formula("SUM(1, 2, 3)", {})
        assert result == 6.0

    def test_function_min_max(self):
        assert evaluate_formula("MIN(5, 3, 8)", {}) == 3.0
        assert evaluate_formula("MAX(5, 3, 8)", {}) == 8.0

    def test_empty_expression(self):
        """BUG-FIX: original crashed with IndexError on empty stack."""
        assert evaluate_formula("", {}) == 0.0

    def test_division_by_zero(self):
        """BUG-FIX: original raised ZeroDivisionError."""
        result = evaluate_formula("10 / 0", {})
        assert result == float("inf")

    def test_comma_handling_in_functions(self):
        """BUG-FIX: original included comma strings as arguments."""
        result = evaluate_formula("SUM(1, 2, 3)", {})
        assert result == 6.0  # not crashing on comma tokens


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("Orders * AOV")
        assert tokens == ["Orders", "*", "AOV"]

    def test_function_call(self):
        tokens = tokenize("SUM(1, 2)")
        assert "SUM" in tokens
        assert "," in tokens


class TestParseFormula:
    def test_with_equals(self):
        lhs, rhs = parse_formula("Revenue = Orders * AOV")
        assert lhs == "Revenue"
        assert rhs == "Orders * AOV"

    def test_without_equals(self):
        lhs, rhs = parse_formula("Orders * AOV")
        assert lhs == "Orders * AOV"
        assert rhs is None


class TestComputationGraph:
    def test_builds_from_graph(self, finance_structured):
        graph = extract_prd_graph(finance_structured, "cg1")
        comp = build_computation_graph(graph)
        assert len(comp["metrics"]) > 0

    def test_builds_from_canonical(self):
        canonical = {
            "variables": [{"name": "orders"}, {"name": "aov"}],
            "metrics": [{"name": "revenue", "formula": "Orders * AOV = Revenue", "depends_on": ["orders", "aov"]}],
        }
        comp = build_computation_graph(canonical)
        assert len(comp["metrics"]) == 1
        assert comp["metrics"][0]["metric"] == "revenue"


class TestExecutionPlan:
    def test_creates_steps(self):
        comp = {"metrics": [
            {"metric": "revenue", "depends_on": ["orders", "aov"]},
            {"metric": "profit", "depends_on": ["revenue", "cost"]},
        ]}
        plan = build_execution_plan(comp)
        assert len(plan["execution_steps"]) == 2
        assert plan["execution_steps"][0]["step"] == 1
