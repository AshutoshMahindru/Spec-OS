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

CANONICAL_ONTOLOGY: dict[str, list[str]] = {
    "revenue": ["revenue", "total_revenue", "rev", "net_revenue"],
    "orders": ["orders", "order_count", "num_orders"],
    "aov": ["aov", "avg_order_value", "average_order_value"],
    "cost": ["cost", "total_cost", "cogs"],
    "profit": ["profit", "net_profit", "gross_profit"],
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
