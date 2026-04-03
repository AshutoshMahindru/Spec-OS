"""Tests for computation module: formula engine, DAG, execution plan."""

from __future__ import annotations

import pytest

from spec_os.computation.dag import build_computation_graph, build_execution_plan, run_execution
from spec_os.computation.formula import FormulaSyntaxError, evaluate_formula, parse_formula, tokenize
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

    def test_operator_precedence(self):
        assert evaluate_formula("2 + 3 * 4", {}) == 14.0

    def test_parentheses_override_precedence(self):
        assert evaluate_formula("(2 + 3) * 4", {}) == 20.0

    def test_nested_functions(self):
        result = evaluate_formula("ROUND(AVG(Orders, AOV), 2)", {"Orders": 100, "AOV": 25})
        assert result == 62.5

    def test_comparisons_and_boolean_logic(self):
        result = evaluate_formula("IF(Orders > AOV AND NOT Discounted, 1, 0)", {"Orders": 100, "AOV": 25, "Discounted": False})
        assert result == 1.0

    def test_invalid_expression_raises_syntax_error(self):
        with pytest.raises(FormulaSyntaxError):
            evaluate_formula("2 + * 3", {})


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

    def test_reversed_assignment(self):
        lhs, rhs = parse_formula("Orders * AOV = Revenue")
        assert lhs == "Revenue"
        assert rhs == "Orders * AOV"


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
        comp = {
            "metrics": [
                {"metric": "revenue", "depends_on": ["orders", "aov"]},
                {"metric": "profit", "depends_on": ["revenue", "cost"]},
            ],
            "available_inputs": ["orders", "aov", "cost"],
        }
        plan = build_execution_plan(comp)
        assert len(plan["execution_steps"]) == 2
        assert plan["execution_steps"][0]["step"] == 1

    def test_topological_sort_orders_dependencies_first(self):
        comp = {
            "metrics": [
                {"metric": "profit", "depends_on": ["revenue", "cost"]},
                {"metric": "revenue", "depends_on": ["orders", "aov"]},
            ],
            "available_inputs": ["orders", "aov", "cost"],
        }
        plan = build_execution_plan(comp)
        assert [step["compute"] for step in plan["execution_steps"]] == ["revenue", "profit"]
        assert plan["status"] == "ok"

    def test_detects_missing_dependencies_when_inputs_declared(self):
        comp = {
            "metrics": [{"metric": "revenue", "depends_on": ["orders", "missing_driver"]}],
            "available_inputs": ["orders"],
        }
        plan = build_execution_plan(comp)
        assert any(issue["type"] == "UNRESOLVED_DEPENDENCY" for issue in plan["issues"])
        assert plan["status"] == "invalid"

    def test_detects_cycles(self):
        comp = {
            "metrics": [
                {"metric": "revenue", "depends_on": ["profit"]},
                {"metric": "profit", "depends_on": ["revenue"]},
            ],
            "available_inputs": [],
        }
        plan = build_execution_plan(comp)
        assert any(issue["type"] == "CYCLE_DETECTED" for issue in plan["issues"])
        assert plan["status"] == "invalid"

    def test_run_execution_uses_dependency_order(self):
        system_spec = {
            "computation": {
                "graph": {
                    "metrics": [
                        {"metric": "profit", "formula": "profit = revenue - cost"},
                        {"metric": "revenue", "formula": "Orders * AOV = Revenue"},
                    ],
                },
                "execution_plan": {
                    "status": "ok",
                    "execution_steps": [
                        {"step": 1, "compute": "revenue", "inputs": ["orders", "aov"]},
                        {"step": 2, "compute": "profit", "inputs": ["revenue", "cost"]},
                    ],
                },
            },
        }
        results = run_execution(system_spec, {"orders": 100, "aov": 25, "cost": 500})
        assert results["revenue"] == 2500.0
        assert results["profit"] == 2000.0
