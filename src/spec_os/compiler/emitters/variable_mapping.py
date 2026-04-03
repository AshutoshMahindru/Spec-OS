"""Emit variable_mapping.json from the experimental phase-spec IR."""

from __future__ import annotations

import re

from spec_os.compiler.emitters.variable_registry import compile_variable_registry_artifact
from spec_os.compiler.ir import SpecOSRepoIR

_PHASE_FILES = [
    "specos/phase_1_foundation_contracts.specos.json",
    "specos/phase_2_planning_spine_inputs.specos.json",
    "specos/phase_3_assumptions_compute.specos.json",
    "specos/phase_4_financial_outputs.specos.json",
    "specos/phase_5_interpretation_trust.specos.json",
    "specos/phase_6_migration_verification_rollout.specos.json",
]

_FORMULA_ALIASES = {
    "confidence_score": {"assumption_confidence_scores"},
}


def compile_variable_mapping_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_3 = ir.phases["phase_3_assumptions_compute.specos.json"]
    variable_registry = compile_variable_registry_artifact(ir)

    mappings = []
    for variable in phase_3.get("variables", []):
        variable_name = variable["name"]
        mappings.append(
            {
                "variable_name": variable_name,
                "class": variable["class"],
                "mapped_table": variable["mapped_table"],
                "source_phase": 3,
                "related_metrics": _related_metrics(variable_name, variable_registry["metrics"]),
            }
        )

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "VARIABLE_MAPPING",
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "mappings": mappings,
    }


def _related_metrics(variable_name: str, metrics: list[dict]) -> list[str]:
    aliases = {variable_name, *_FORMULA_ALIASES.get(variable_name, set())}
    related: list[str] = []

    for metric in metrics:
        tokens = set(_formula_tokens(metric.get("formula", "")))
        if tokens & aliases:
            related.append(metric["id"])

    return related


def _formula_tokens(formula: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)
