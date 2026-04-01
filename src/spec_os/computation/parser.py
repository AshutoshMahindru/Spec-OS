"""Expression parser for Spec-OS formulas."""

from __future__ import annotations

from dataclasses import dataclass


class FormulaSyntaxError(ValueError):
    """Raised when a formula cannot be parsed."""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        suffix = f" at position {position}" if position is not None else ""
        super().__init__(f"{message}{suffix}")


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    position: int


@dataclass(frozen=True, slots=True)
class NumberNode:
    value: float


@dataclass(frozen=True, slots=True)
class IdentifierNode:
    name: str


@dataclass(frozen=True, slots=True)
class UnaryOpNode:
    operator: str
    operand: AstNode


@dataclass(frozen=True, slots=True)
class BinaryOpNode:
    operator: str
    left: AstNode
    right: AstNode


@dataclass(frozen=True, slots=True)
class FunctionCallNode:
    name: str
    args: tuple[AstNode, ...]


AstNode = NumberNode | IdentifierNode | UnaryOpNode | BinaryOpNode | FunctionCallNode

_KEYWORD_OPERATORS = {"AND", "OR", "NOT"}
_UNARY_BINDING_POWER = {"+": 70, "-": 70, "NOT": 70}
_BINARY_BINDING_POWER = {
    "OR": (10, 11),
    "AND": (20, 21),
    "==": (30, 31),
    "!=": (30, 31),
    ">": (30, 31),
    ">=": (30, 31),
    "<": (30, 31),
    "<=": (30, 31),
    "+": (40, 41),
    "-": (40, 41),
    "*": (50, 51),
    "/": (50, 51),
}


def tokenize(expression: str) -> list[Token]:
    """Tokenize an arithmetic / boolean expression."""
    tokens: list[Token] = []
    i = 0

    while i < len(expression):
        char = expression[i]

        if char.isspace():
            i += 1
            continue

        if expression.startswith((">=", "<=", "==", "!="), i):
            op = expression[i : i + 2]
            tokens.append(Token("OP", op, i))
            i += 2
            continue

        if char in "+-*/() ,><":
            kind = {
                "(": "LPAREN",
                ")": "RPAREN",
                ",": "COMMA",
            }.get(char, "OP")
            tokens.append(Token(kind, char, i))
            i += 1
            continue

        if char.isdigit() or (char == "." and i + 1 < len(expression) and expression[i + 1].isdigit()):
            start = i
            i += 1
            while i < len(expression) and (expression[i].isdigit() or expression[i] == "."):
                i += 1
            literal = expression[start:i]
            if literal.count(".") > 1:
                raise FormulaSyntaxError("Invalid numeric literal", start)
            tokens.append(Token("NUMBER", literal, start))
            continue

        if char.isalpha() or char == "_":
            start = i
            i += 1
            while i < len(expression) and (expression[i].isalnum() or expression[i] == "_"):
                i += 1
            word = expression[start:i]
            upper = word.upper()
            if upper in _KEYWORD_OPERATORS:
                tokens.append(Token("OP", upper, start))
            else:
                tokens.append(Token("IDENTIFIER", word, start))
            continue

        raise FormulaSyntaxError(f"Unexpected character {char!r}", i)

    tokens.append(Token("EOF", "", len(expression)))
    return tokens


class FormulaParser:
    """Pratt parser for Spec-OS expressions."""

    def __init__(self, expression: str):
        self.expression = expression
        self.tokens = tokenize(expression)
        self.index = 0

    def parse(self) -> AstNode:
        if self.current.kind == "EOF":
            raise FormulaSyntaxError("Expression is empty", 0)
        node = self._parse_expression()
        if self.current.kind != "EOF":
            raise FormulaSyntaxError(f"Unexpected token {self.current.value!r}", self.current.position)
        return node

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def _expect(self, kind: str) -> Token:
        token = self.current
        if token.kind != kind:
            raise FormulaSyntaxError(f"Expected {kind.lower()}", token.position)
        self.index += 1
        return token

    def _parse_expression(self, min_bp: int = 0) -> AstNode:
        token = self._advance()
        left = self._parse_prefix(token)

        while True:
            token = self.current
            if token.kind != "OP":
                break

            binding = _BINARY_BINDING_POWER.get(token.value)
            if binding is None:
                break

            left_bp, right_bp = binding
            if left_bp < min_bp:
                break

            self._advance()
            right = self._parse_expression(right_bp)
            left = BinaryOpNode(token.value, left, right)

        return left

    def _parse_prefix(self, token: Token) -> AstNode:
        if token.kind == "NUMBER":
            return NumberNode(float(token.value))

        if token.kind == "IDENTIFIER":
            if self.current.kind == "LPAREN":
                return self._parse_function_call(token)
            return IdentifierNode(token.value)

        if token.kind == "LPAREN":
            expr = self._parse_expression()
            self._expect("RPAREN")
            return expr

        if token.kind == "OP" and token.value in _UNARY_BINDING_POWER:
            operand = self._parse_expression(_UNARY_BINDING_POWER[token.value])
            return UnaryOpNode(token.value, operand)

        raise FormulaSyntaxError(f"Unexpected token {token.value!r}", token.position)

    def _parse_function_call(self, identifier: Token) -> AstNode:
        self._expect("LPAREN")
        args: list[AstNode] = []

        if self.current.kind != "RPAREN":
            while True:
                args.append(self._parse_expression())
                if self.current.kind == "COMMA":
                    self._advance()
                    continue
                break

        self._expect("RPAREN")
        return FunctionCallNode(identifier.value.upper(), tuple(args))


def parse_expression(expression: str) -> AstNode:
    """Parse *expression* into an AST."""
    return FormulaParser(expression).parse()


def collect_identifiers(node: AstNode) -> list[str]:
    """Collect identifiers referenced by *node* in encounter order."""
    names: list[str] = []
    seen: set[str] = set()

    def visit(current: AstNode) -> None:
        if isinstance(current, IdentifierNode):
            if current.name not in seen:
                seen.add(current.name)
                names.append(current.name)
            return

        if isinstance(current, UnaryOpNode):
            visit(current.operand)
            return

        if isinstance(current, BinaryOpNode):
            visit(current.left)
            visit(current.right)
            return

        if isinstance(current, FunctionCallNode):
            for arg in current.args:
                visit(arg)

    visit(node)
    return names
