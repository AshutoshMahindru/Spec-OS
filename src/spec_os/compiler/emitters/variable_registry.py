"""Emit variable_registry.json from the experimental phase-spec IR."""

from __future__ import annotations

import re

from spec_os.compiler.ir import SpecOSRepoIR

_PHASE_FILES = [
    "phase_1_foundation_contracts.specos.json",
    "phase_2_planning_spine_inputs.specos.json",
    "phase_3_assumptions_compute.specos.json",
    "phase_4_financial_outputs.specos.json",
    "phase_5_interpretation_trust.specos.json",
    "phase_6_migration_verification_rollout.specos.json",
]


def compile_variable_registry_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_3 = ir.phases["phase_3_assumptions_compute.specos.json"]
    phase_4 = ir.phases["phase_4_financial_outputs.specos.json"]
    phase_5 = ir.phases["phase_5_interpretation_trust.specos.json"]

    metrics = []
    seen: set[str] = set()
    for phase_doc in (phase_3, phase_4, phase_5):
        families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        owner_doc = _default_owner_doc(phase_doc)
        for metric in phase_doc.get("metrics", []):
            metric_id = metric.get("id")
            if not metric_id or metric_id in seen:
                continue
            seen.add(metric_id)
            metrics.append(
                {
                    "id": metric_id,
                    "formula": metric.get("formula"),
                    "phase_number": _phase_number(phase_doc),
                    "requirement_families": metric.get("requirement_families", families),
                    "owner_doc": metric.get("owner_doc", owner_doc),
                }
            )

    variables = []
    for variable in phase_3.get("variables", []):
        variables.append(
            {
                "name": variable.get("name"),
                "class": variable.get("class"),
                "mapped_table": variable.get("mapped_table"),
            }
        )

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "VARIABLE_REGISTRY",
            "declared_variable_count": ir.foundation.authoritative_counts.get("variables"),
            "actual_variable_count": len(variables),
            "declared_metric_count": ir.foundation.authoritative_counts.get("metrics"),
            "actual_metric_count": len(metrics),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "variables": variables,
        "metrics": metrics,
    }


def _phase_number(phase_doc: dict) -> int:
    doc_id = str(phase_doc.get("meta", {}).get("doc_id", ""))
    match = re.search(r"(?:^|_)phase_(\d+)(?:_|$)", doc_id)
    if match:
        return int(match.group(1))

    match = re.search(r"(?:^|_)phase(\d+)(?:_|$)", doc_id)
    if match:
        return int(match.group(1))

    raise ValueError(f"Unable to determine phase number from doc_id: {doc_id!r}")


def _default_owner_doc(phase_doc: dict) -> str:
    phase_number = _phase_number(phase_doc)
    if phase_number == 3:
        return "FEATURE_INDEX.md"
    if phase_number == 4:
        return "FINANCIAL_MODEL.md"
    if phase_number == 5:
        return "FEATURE_INDEX.md"
    return "UNKNOWN.md"
