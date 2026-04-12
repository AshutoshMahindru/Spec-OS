"""Shared constants: graph schema, ontology, and whitelists."""

from __future__ import annotations

# ── Graph node / edge type registry ─────────────────────────────────────────

NODE_TYPES: dict[str, list[str]] = {
    "Document": ["id", "type", "source", "doc_type"],
    "Section": ["id", "title", "level"],
    "Layer": ["name"],
    "API": ["endpoint", "method", "group"],
    "DataModel": ["name", "source_section"],
    "Field": ["name", "data_type", "nullable", "default"],
    "Metric": ["formula"],
    "Service": ["name"],
    "UIComponent": ["name", "component_type"],
    "Feature": ["name"],
    "Constraint": ["description"],
    "Variable": ["name", "variable_type"],
    "Workflow": ["name"],
    "RoadmapPhase": ["name"],
    "Requirement": ["name"],
    "UserRole": ["name"],
}

EDGE_TYPES: list[tuple[str, str, str]] = [
    ("Document", "HAS_SECTION", "Section"),
    ("Section", "CONTAINS", "Feature"),
    ("Section", "CONTAINS", "Constraint"),
    ("Section", "CONTAINS", "Variable"),
    ("Section", "CONTAINS", "Metric"),
    ("Section", "CONTAINS", "Service"),
    ("Section", "CONTAINS", "Layer"),
    ("Section", "CONTAINS", "UIComponent"),
    ("Section", "CONTAINS", "API"),
    ("Section", "CONTAINS", "DataModel"),
    ("DataModel", "HAS_FIELD", "Field"),
    ("Metric", "DEPENDS_ON", "Variable"),
    ("Layer", "FEEDS", "Service"),
    ("Service", "USES", "Service"),
    ("Service", "OUTPUTS_TO", "Service"),
    ("Service", "DRIVES_UI", "UIComponent"),
    ("UIComponent", "CALLS", "API"),
    ("Feature", "HAS_CONSTRAINT", "Constraint"),
    ("Workflow", "USES_FEATURE", "Feature"),
    ("RoadmapPhase", "DELIVERS", "Feature"),
    ("Requirement", "TRACES_TO", "Feature"),
]

# ── Canonical ontology (alias -> canonical name) ────────────────────────────
# Change B: expanded to cover all VARIABLE_WHITELIST entries and common aliases.

CANONICAL_ONTOLOGY: dict[str, list[str]] = {
    "revenue": ["revenue", "total_revenue", "rev", "net_revenue"],
    "orders": ["orders", "order_count", "num_orders"],
    "aov": ["aov", "avg_order_value", "average_order_value"],
    "cost": ["cost", "total_cost", "cogs"],
    "profit": ["profit", "net_profit", "gross_profit"],
    "margin": ["margin", "gross_margin", "gm", "contribution_margin", "cm"],
    "cash": ["cash", "cash_flow", "net_cash"],
    "capex": ["capex", "capital_expenditure", "cap_ex"],
    "funding": ["funding", "total_funding", "investment"],
    "demand": ["demand", "total_demand", "customer_demand"],
    "price": ["price", "unit_price", "avg_price"],
    "mix": ["mix", "product_mix", "revenue_mix"],
    "labor": ["labor", "labour", "labor_cost", "labour_cost"],
    "opex": ["opex", "operating_expense", "operating_expenses", "op_ex"],
    "kpi": ["kpi", "key_performance_indicator"],
}

# ── PRD variable whitelist ──────────────────────────────────────────────────

VARIABLE_WHITELIST: set[str] = {
    "Orders", "AOV", "Revenue", "Cost", "Profit", "Cash", "Capex",
    "Funding", "CM", "Demand", "Price", "Mix", "Labor", "Opex",
    "COGS", "KPI", "Margin",
}

# ── PRD feature section keywords ────────────────────────────────────────────

FEATURE_SECTION_KEYWORDS: set[str] = {
    "mvp", "functional requirements", "workflow", "ux requirements",
    "planning workflows", "computation engine requirements",
}

# ── Document type enum ──────────────────────────────────────────────────────

DOC_TYPES = ("PRD", "API_SPEC", "DATA_DICTIONARY", "ARCHITECTURE", "WIREFRAME", "GENERIC")

# ── Issue severity classification (Change D) ────────────────────────────────

BLOCKING_ISSUE_TYPES: set[str] = {
    "CYCLE_DETECTED",
    "MISSING_VARIABLE_IN_REGISTRY",
    "MISSING_STORAGE_MAPPING",
    "API_SCHEMA_MISMATCH",
    "CONFLICTING_FORMULA",
    "CONFLICTING_FIELD_TYPE",
    "INVALID_API",
    "BROKEN_EDGE",
    "TYPE_MISMATCH_EDGE",
}

WARNING_ISSUE_TYPES: set[str] = {
    "SELF_DEPENDENCY",
    "UNRESOLVED_DEPENDENCY",
    "DUPLICATE_METRIC",
    "EMPTY_METRIC",
    "POSSIBLE_ALIAS",
    "CONFLICTING_VARIABLE_TYPE",
    "DUPLICATE_API",
    "ORPHAN_EDGE",
    "DUPLICATE_NODE_ID",
    "INVALID_NODE",
    "INVALID_DEPENDENCY",
}

# ── Quality score issue weights (Change D) ──────────────────────────────────

ISSUE_WEIGHTS: dict[str, int] = {
    "CYCLE_DETECTED": 25,
    "CONFLICTING_FORMULA": 15,
    "MISSING_VARIABLE_IN_REGISTRY": 10,
    "API_SCHEMA_MISMATCH": 10,
    "CONFLICTING_FIELD_TYPE": 10,
    "MISSING_STORAGE_MAPPING": 5,
    "BROKEN_EDGE": 5,
    "TYPE_MISMATCH_EDGE": 5,
    "INVALID_API": 5,
    "CONFLICTING_VARIABLE_TYPE": 3,
    "DUPLICATE_API": 3,
    "SELF_DEPENDENCY": 3,
    "UNRESOLVED_DEPENDENCY": 3,
    "DUPLICATE_METRIC": 2,
    "POSSIBLE_ALIAS": 1,
    "EMPTY_METRIC": 1,
}

# Default weight for unknown issue types.
DEFAULT_ISSUE_WEIGHT: int = 3

# Maximum total penalty from reconciliation issues.
MAX_ISSUE_PENALTY: int = 80
