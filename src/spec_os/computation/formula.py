"""Safe formula parsing and evaluation -- no ``eval()``."""

from __future__ import annotations

from typing import Any

from spec_os.computation.parser import (
    BinaryOpNode,
    FormulaSyntaxError,
    FunctionCallNode,
    IdentifierNode,
    NumberNode,
    UnaryOpNode,
    collect_identifiers,
    parse_expression,
)
from spec_os.computation.parser import (
    tokenize as tokenize_expression,
)
from spec_os.helpers import normalize_name

__all__ = [
    "FormulaEvaluationError",
    "FormulaSyntaxError",
    "evaluate_formula",
    "extract_formula_dependencies",
    "parse_formula",
    "tokenize",
]


class FormulaEvaluationError(ValueError):
    """Raised when a parsed formula cannot be evaluated."""


def tokenize(expr: str) -> list[str]:
    """Split *expr* into token values for compatibility with older tests."""
    return [token.value for token in tokenize_expression(expr) if token.kind != "EOF"]


def _safe_divide(left: float, right: float) -> float:
    if right == 0:
        if left < 0:
            return float("-inf")
        return float("inf")
    return left / right


def _coerce_number(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise FormulaEvaluationError(f"Expected numeric value, got {value!r}")


def _coerce_integer(value: Any) -> int:
    number = _coerce_number(value)
    if not number.is_integer():
        raise FormulaEvaluationError(f"Expected integer value, got {value!r}")
    return int(number)


def _resolve_identifier(name: str, context: dict[str, Any], normalized_context: dict[str, Any]) -> Any:
    if name in context:
        return context[name]

    upper = name.upper()
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False

    canonical = normalize_name(name)
    if canonical in normalized_context:
        return normalized_context[canonical]

    raise FormulaEvaluationError(f"Unknown identifier {name!r}")


def _call_function(name: str, args: list[Any]) -> Any:
    if name == "SUM":
        return sum(_coerce_number(arg) for arg in args)
    if name == "MIN":
        if not args:
            raise FormulaEvaluationError("MIN requires at least one argument")
        return min(_coerce_number(arg) for arg in args)
    if name == "MAX":
        if not args:
            raise FormulaEvaluationError("MAX requires at least one argument")
        return max(_coerce_number(arg) for arg in args)
    if name == "AVG":
        if not args:
            raise FormulaEvaluationError("AVG requires at least one argument")
        numbers = [_coerce_number(arg) for arg in args]
        return sum(numbers) / len(numbers)
    if name == "ROUND":
        if not args:
            raise FormulaEvaluationError("ROUND requires at least one argument")
        precision = _coerce_integer(args[1]) if len(args) > 1 else 0
        return round(_coerce_number(args[0]), precision)
    if name == "IF":
        if len(args) != 3:
            raise FormulaEvaluationError("IF requires exactly three arguments")
        return args[1] if bool(args[0]) else args[2]
    raise FormulaEvaluationError(f"Unsupported function {name!r}")


def _evaluate_ast(node: Any, context: dict[str, Any], normalized_context: dict[str, Any]) -> Any:
    if isinstance(node, NumberNode):
        return node.value

    if isinstance(node, IdentifierNode):
        return _resolve_identifier(node.name, context, normalized_context)

    if isinstance(node, UnaryOpNode):
        value = _evaluate_ast(node.operand, context, normalized_context)
        if node.operator == "+":
            return _coerce_number(value)
        if node.operator == "-":
            return -_coerce_number(value)
        if node.operator == "NOT":
            return not bool(value)
        raise FormulaEvaluationError(f"Unsupported unary operator {node.operator!r}")

    if isinstance(node, BinaryOpNode):
        left = _evaluate_ast(node.left, context, normalized_context)
        right = _evaluate_ast(node.right, context, normalized_context)

        if node.operator == "+":
            return _coerce_number(left) + _coerce_number(right)
        if node.operator == "-":
            return _coerce_number(left) - _coerce_number(right)
        if node.operator == "*":
            return _coerce_number(left) * _coerce_number(right)
        if node.operator == "/":
            return _safe_divide(_coerce_number(left), _coerce_number(right))
        if node.operator == ">":
            return _coerce_number(left) > _coerce_number(right)
        if node.operator == ">=":
            return _coerce_number(left) >= _coerce_number(right)
        if node.operator == "<":
            return _coerce_number(left) < _coerce_number(right)
        if node.operator == "<=":
            return _coerce_number(left) <= _coerce_number(right)
        if node.operator == "==":
            return left == right
        if node.operator == "!=":
            return left != right
        if node.operator == "AND":
            return bool(left) and bool(right)
        if node.operator == "OR":
            return bool(left) or bool(right)
        raise FormulaEvaluationError(f"Unsupported operator {node.operator!r}")

    if isinstance(node, FunctionCallNode):
        values = [_evaluate_ast(arg, context, normalized_context) for arg in node.args]
        return _call_function(node.name, values)

    raise FormulaEvaluationError(f"Unsupported AST node {node!r}")


def _looks_like_expression(side: str) -> bool:
    stripped = side.strip()
    if not stripped:
        return False
    tokens = tokenize(stripped)
    operator_tokens = {"+", "-", "*", "/", "(", ")", ",", ">", ">=", "<", "<=", "==", "!=", "AND", "OR", "NOT"}
    if any(token in operator_tokens for token in tokens):
        return True
    return len(tokens) > 1


def evaluate_formula(expression: str, context: dict[str, Any]) -> Any:
    """Evaluate *expression* using *context* as the variable store."""
    if not expression or not expression.strip():
        return 0.0

    ast = parse_expression(expression)
    normalized_context = {normalize_name(key): value for key, value in context.items()}
    return _evaluate_ast(ast, context, normalized_context)


def parse_formula(formula: str) -> tuple[str, str | None]:
    if "=" in formula:
        left, right = [part.strip() for part in formula.split("=", 1)]
        left_is_expression = _looks_like_expression(left)
        right_is_expression = _looks_like_expression(right)

        if left_is_expression and not right_is_expression:
            return right, left
        if right_is_expression and not left_is_expression:
            return left, right
        return left, right
    return formula, None


def extract_formula_dependencies(formula: str) -> list[str]:
    """Return the normalized identifiers referenced by *formula* in encounter order."""
    _, expression = parse_formula(formula)
    candidate = expression if expression is not None else formula
    if not candidate or not candidate.strip():
        return []

    ast = parse_expression(candidate)
    dependencies: list[str] = []
    seen: set[str] = set()

    for identifier in collect_identifiers(ast):
        normalized = normalize_name(identifier)
        if normalized and normalized not in seen:
            seen.add(normalized)
            dependencies.append(normalized)

    return dependencies
