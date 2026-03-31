"""Safe formula evaluation engine -- no ``eval()``.

BUG FIXES vs. original:
* Comma tokens are now properly skipped when collecting function arguments.
* Empty-expression guard prevents ``IndexError`` on ``stack[0]``.
* Division-by-zero returns ``float('inf')`` instead of crashing.
"""

from __future__ import annotations

import re
from typing import Any

ALLOWED_FUNCTIONS: dict[str, Any] = {
    "SUM": lambda *args: sum(args),
    "MIN": lambda *args: min(args),
    "MAX": lambda *args: max(args),
    "IF": lambda cond, a, b: a if cond else b,
}


def tokenize(expr: str) -> list[str]:
    """Split *expr* into tokens (identifiers, numbers, operators, parens, commas)."""
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*|[()+\-*/,<>]", expr)


def resolve_token(token: str, context: dict) -> Any:
    if token in context:
        return context[token]
    try:
        return float(token)
    except ValueError:
        return token


def evaluate_formula(expression: str, context: dict) -> float:
    """Evaluate *expression* using *context* as the variable store.

    Supports ``SUM``, ``MIN``, ``MAX``, ``IF`` plus basic ``+-*/``.
    """
    tokens = tokenize(expression)
    if not tokens:
        return 0.0

    stack: list[Any] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.upper() in ALLOWED_FUNCTIONS:
            func = ALLOWED_FUNCTIONS[token.upper()]
            args: list[Any] = []
            i += 2  # skip FUNC and '('
            while i < len(tokens) and tokens[i] != ")":
                if tokens[i] == ",":
                    i += 1  # BUG-FIX: skip comma separators
                    continue
                args.append(resolve_token(tokens[i], context))
                i += 1
            stack.append(func(*args))

        elif token in {"+", "-", "*", "/"}:
            stack.append(token)

        elif token not in {"(", ")", ","}:
            stack.append(resolve_token(token, context))

        i += 1

    # Left-to-right evaluation
    if not stack:
        return 0.0

    result = stack[0]
    idx = 1
    while idx < len(stack) - 1:
        op = stack[idx]
        val = stack[idx + 1]
        if op == "+":
            result += val
        elif op == "-":
            result -= val
        elif op == "*":
            result *= val
        elif op == "/":
            result = result / val if val != 0 else float("inf")  # BUG-FIX
        idx += 2

    return result


def parse_formula(formula: str) -> tuple[str, str | None]:
    if "=" in formula:
        lhs, rhs = formula.split("=", 1)
        return lhs.strip(), rhs.strip()
    return formula, None
