"""Spec quality score and completeness checks."""

from __future__ import annotations


def compute_spec_quality_score(
    reconciliation: dict,
    variable_registry: dict,
    schema: dict,
    api_contracts: list[dict],
    computation_graph: dict,
) -> dict:
    score = 100
    score -= len(reconciliation.get("issues", [])) * 5
    if not variable_registry.get("variables"):
        score -= 10
    if not schema.get("models"):
        score -= 20
    if not api_contracts:
        score -= 10
    if not computation_graph.get("metrics"):
        score -= 15
    return {"score": max(0, score)}


def build_spec_completeness(
    reconciliation: dict,
    variable_registry: dict,
    schema: dict,
    api_contracts: list[dict],
    computation_graph: dict,
) -> dict:
    blocking: list[str] = []
    warnings: list[str] = []

    for issue in reconciliation.get("issues", []):
        if issue.get("type") == "MISSING_IN_SCHEMA":
            blocking.append(f"Variable {issue.get('variable')} missing in schema")
        else:
            warnings.append(str(issue))

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
