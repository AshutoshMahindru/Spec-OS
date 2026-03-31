"""Computation DAG and execution plan builders."""

from __future__ import annotations

import re

from spec_os.canonical.model import build_canonical_model
from spec_os.helpers import normalize_name


def _parse_formula_vars(formula: str) -> list[str]:
    if not formula:
        return []
    parts = formula.split("=")
    rhs = parts[-1] if len(parts) > 1 else formula
    return list(dict.fromkeys(re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", rhs)))


def build_computation_graph(input_model: dict) -> dict:
    """Build a metric DAG from a canonical model (or raw graph as fallback).

    Accepts both shapes:
    * canonical model: ``{variables, metrics, ...}``
    * raw graph: ``{nodes, edges}``
    """
    if "metrics" in input_model and "variables" in input_model:
        metrics = input_model.get("metrics", [])
    else:
        canonical = build_canonical_model(input_model)
        metrics = canonical.get("metrics", [])

    dag = [
        {
            "metric": m.get("name"),
            "formula": m.get("formula"),
            "depends_on": m.get("depends_on", []),
        }
        for m in metrics
    ]
    return {"metrics": dag}


def build_execution_plan(computation_graph: dict) -> dict:
    """Topologically order metrics (simple linear ordering for now)."""
    steps = [
        {"step": idx, "compute": m.get("metric"), "inputs": m.get("depends_on", [])}
        for idx, m in enumerate(computation_graph.get("metrics", []), start=1)
    ]
    return {"execution_steps": steps}


def run_execution(system_spec: dict, driver_inputs: dict) -> dict:
    """Execute the computation graph with concrete driver values."""
    from spec_os.computation.formula import evaluate_formula, parse_formula

    context = dict(driver_inputs)
    results: dict[str, float] = {}

    metrics = {m["metric"]: m for m in system_spec["computation"]["graph"]["metrics"]}

    for step in system_spec["computation"]["execution_plan"]["execution_steps"]:
        name = step["compute"]
        metric = metrics.get(name)
        if not metric:
            continue

        _, rhs = parse_formula(metric["formula"])
        if rhs is None:
            continue
        val = evaluate_formula(rhs, context)
        context[name] = val
        results[name] = val

    return results
