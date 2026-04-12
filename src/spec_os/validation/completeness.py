"""Spec quality score and completeness checks.

Change D: severity-aware completeness and weighted quality scoring.

* ``build_spec_completeness`` now classifies each reconciliation issue as
  *blocking* or *warning* based on ``BLOCKING_ISSUE_TYPES`` / ``WARNING_ISSUE_TYPES``.
* ``compute_spec_quality_score`` uses per-issue-type weights from
  ``ISSUE_WEIGHTS`` instead of a flat 5-point penalty.
* ``ready_for_codegen`` is ``False`` whenever any blocking issue exists, not
  just when entire artifact categories are absent.
"""

from __future__ import annotations

from spec_os.constants import (
    BLOCKING_ISSUE_TYPES,
    DEFAULT_ISSUE_WEIGHT,
    ISSUE_WEIGHTS,
    MAX_ISSUE_PENALTY,
)

# Per-component missing penalties keyed by doc_type (or default).
# Keys: variables, models, apis, metrics
_TYPE_PENALTIES: dict[str, dict[str, int]] = {
    "PRD": {"variables": 15, "models": 20, "apis": 5, "metrics": 15},
    "API_SPEC": {"variables": 5, "models": 10, "apis": 25, "metrics": 5},
    "DATA_DICTIONARY": {"variables": 10, "models": 25, "apis": 5, "metrics": 5},
    "ARCHITECTURE": {"variables": 5, "models": 10, "apis": 10, "metrics": 5},
    "WIREFRAME": {"variables": 5, "models": 5, "apis": 5, "metrics": 5},
    "__default__": {"variables": 10, "models": 20, "apis": 10, "metrics": 15},
}


def compute_spec_quality_score(
    reconciliation: dict,
    variable_registry: dict,
    schema: dict,
    api_contracts: list[dict],
    computation_graph: dict,
    *,
    doc_type: str | None = None,
) -> dict:
    """Return a quality score (0-100) with weighted, severity-aware penalties."""
    penalties = _TYPE_PENALTIES.get(doc_type or "", _TYPE_PENALTIES["__default__"])

    score = 100

    # Reconciliation issues: weighted by type, capped at MAX_ISSUE_PENALTY.
    issue_penalty = 0
    for issue in reconciliation.get("issues", []):
        itype = issue.get("type", "")
        weight = ISSUE_WEIGHTS.get(itype, DEFAULT_ISSUE_WEIGHT)
        issue_penalty += weight
    score -= min(issue_penalty, MAX_ISSUE_PENALTY)

    if not variable_registry.get("variables"):
        score -= penalties["variables"]
    if not schema.get("models"):
        score -= penalties["models"]
    if not api_contracts:
        score -= penalties["apis"]
    if not computation_graph.get("metrics"):
        score -= penalties["metrics"]

    return {"score": max(0, score)}


def build_spec_completeness(
    reconciliation: dict,
    variable_registry: dict,
    schema: dict,
    api_contracts: list[dict],
    computation_graph: dict,
    *,
    doc_type: str | None = None,
) -> dict:
    """Build completeness report with severity-aware issue classification."""
    blocking: list[str] = []
    warnings: list[str] = []

    for issue in reconciliation.get("issues", []):
        itype = issue.get("type", "")
        # Build a human-readable description.
        if itype == "CONFLICTING_FORMULA":
            desc = f"Metric '{issue.get('metric')}' has conflicting formula definitions"
        elif itype == "CONFLICTING_VARIABLE_TYPE":
            desc = f"Variable '{issue.get('variable')}' has conflicting type assignments"
        elif itype == "CONFLICTING_FIELD_TYPE":
            desc = f"Field '{issue.get('field')}' in model '{issue.get('model')}' has conflicting types"
        elif itype == "MISSING_STORAGE_MAPPING":
            desc = f"Variable '{issue.get('variable')}' has no storage-table mapping"
        elif itype == "MISSING_VARIABLE_IN_REGISTRY":
            desc = f"Metric '{issue.get('metric')}' depends on unregistered variable '{issue.get('variable')}'"
        elif itype == "API_SCHEMA_MISMATCH":
            desc = f"API '{issue.get('endpoint')}' references unknown model '{issue.get('model')}'"
        elif itype == "INVALID_API":
            desc = "API contract has no endpoint"
        elif itype == "CYCLE_DETECTED":
            desc = f"Circular dependency among metrics: {issue.get('metrics', [])}"
        elif itype == "BROKEN_EDGE":
            desc = f"Edge {issue.get('edge_type')} from '{issue.get('from')}' to '{issue.get('to')}' has missing endpoint"
        elif itype == "TYPE_MISMATCH_EDGE":
            desc = f"Edge {issue.get('edge_type')} has unexpected source/target types"
        elif itype == "POSSIBLE_ALIAS":
            desc = f"'{issue.get('variable_a')}' and '{issue.get('variable_b')}' may be aliases (similarity: {issue.get('similarity')})"
        elif itype == "DUPLICATE_API":
            desc = f"Duplicate API endpoint: {issue.get('endpoint')}"
        elif itype == "DUPLICATE_METRIC":
            desc = f"Duplicate metric: {issue.get('metric')}"
        else:
            desc = str(issue)

        if itype in BLOCKING_ISSUE_TYPES:
            blocking.append(desc)
        else:
            warnings.append(desc)

    # Structural completeness checks.
    if not api_contracts:
        blocking.append("No APIs defined")
    if not schema.get("models"):
        blocking.append("No data models defined")
    if not variable_registry.get("variables"):
        blocking.append("No variables extracted")
    if not computation_graph.get("metrics"):
        warnings.append("No computation graph defined")

    return {
        "blocking_issues": blocking,
        "warnings": warnings,
        "ready_for_codegen": len(blocking) == 0,
        "completeness": {
            "variables": len(variable_registry.get("variables", [])),
            "schema": len(schema.get("models", [])),
            "apis": len(api_contracts),
            "metrics": len(computation_graph.get("metrics", [])),
        },
    }
