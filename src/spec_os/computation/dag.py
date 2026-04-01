"""Computation DAG and execution plan builders."""

from __future__ import annotations

from spec_os.canonical.model import build_canonical_model
from spec_os.computation.formula import evaluate_formula, extract_formula_dependencies, parse_formula
from spec_os.helpers import normalize_name


def _parse_formula_vars(formula: str) -> list[str]:
    return extract_formula_dependencies(formula)


def build_computation_graph(input_model: dict) -> dict:
    """Build a metric DAG from a canonical model (or raw graph as fallback).

    Accepts both shapes:
    * canonical model: ``{variables, metrics, ...}``
    * raw graph: ``{nodes, edges}``
    """
    if "metrics" in input_model and "variables" in input_model:
        metrics = input_model.get("metrics", [])
        available_inputs = [normalize_name(v.get("name")) for v in input_model.get("variables", []) if v.get("name")]
    else:
        canonical = build_canonical_model(input_model)
        metrics = canonical.get("metrics", [])
        available_inputs = [normalize_name(v.get("name")) for v in canonical.get("variables", []) if v.get("name")]

    dag = [
        {
            "metric": normalize_name(m.get("name")),
            "formula": m.get("formula"),
            "depends_on": list(
                dict.fromkeys(
                    normalize_name(dep)
                    for dep in (m.get("depends_on") or _parse_formula_vars(m.get("formula", "")))
                    if dep
                )
            ),
        }
        for m in metrics
        if m.get("name")
    ]
    return {"metrics": dag, "available_inputs": list(dict.fromkeys(inp for inp in available_inputs if inp))}


def build_execution_plan(computation_graph: dict) -> dict:
    """Topologically order metrics and surface invalid dependency structures."""
    metrics = computation_graph.get("metrics", [])
    declared_inputs = computation_graph.get("available_inputs")
    available_inputs = {normalize_name(dep) for dep in (declared_inputs or []) if dep}

    normalized_metrics: list[dict] = []
    metric_names: set[str] = set()
    issues: list[dict] = []
    original_order: dict[str, int] = {}

    for index, metric in enumerate(metrics):
        name = normalize_name(metric.get("metric"))
        if not name:
            issues.append({"type": "EMPTY_METRIC"})
            continue
        if name in metric_names:
            issues.append({"type": "DUPLICATE_METRIC", "metric": name})
            continue

        dependencies = list(dict.fromkeys(normalize_name(dep) for dep in metric.get("depends_on", []) if dep))
        normalized_metric = {
            "metric": name,
            "formula": metric.get("formula"),
            "depends_on": dependencies,
        }
        normalized_metrics.append(normalized_metric)
        metric_names.add(name)
        original_order[name] = index

    adjacency: dict[str, set[str]] = {metric["metric"]: set() for metric in normalized_metrics}
    indegree: dict[str, int] = {metric["metric"]: 0 for metric in normalized_metrics}

    for metric in normalized_metrics:
        name = metric["metric"]
        for dependency in metric.get("depends_on", []):
            if dependency == name:
                issues.append({"type": "SELF_DEPENDENCY", "metric": name})
                continue
            if dependency in metric_names:
                adjacency[dependency].add(name)
                indegree[name] += 1
                continue
            if declared_inputs is not None and dependency not in available_inputs:
                issues.append(
                    {
                        "type": "UNRESOLVED_DEPENDENCY",
                        "metric": name,
                        "dependency": dependency,
                    }
                )

    ready = sorted((name for name, count in indegree.items() if count == 0), key=lambda item: (original_order[item], item))
    ordered: list[str] = []

    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for dependant in sorted(adjacency[current], key=lambda item: (original_order[item], item)):
            indegree[dependant] -= 1
            if indegree[dependant] == 0:
                ready.append(dependant)
        ready.sort(key=lambda item: (original_order[item], item))

    if len(ordered) != len(normalized_metrics):
        cycle_metrics = [name for name, count in indegree.items() if count > 0]
        issues.append({"type": "CYCLE_DETECTED", "metrics": sorted(cycle_metrics, key=lambda item: (original_order[item], item))})

    metric_lookup = {metric["metric"]: metric for metric in normalized_metrics}
    steps = [
        {
            "step": index,
            "compute": name,
            "inputs": metric_lookup[name].get("depends_on", []),
        }
        for index, name in enumerate(ordered, start=1)
    ]

    return {
        "execution_steps": steps,
        "issues": issues,
        "status": "ok" if not issues else "invalid",
    }


def run_execution(system_spec: dict, driver_inputs: dict) -> dict:
    """Execute the computation graph with concrete driver values."""
    context = dict(driver_inputs)
    results: dict[str, float] = {}

    metrics = {m["metric"]: m for m in system_spec["computation"]["graph"]["metrics"]}
    plan = system_spec["computation"]["execution_plan"]

    if plan.get("status", "ok") != "ok":
        raise ValueError("Execution plan is invalid")

    for step in plan.get("execution_steps", []):
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
