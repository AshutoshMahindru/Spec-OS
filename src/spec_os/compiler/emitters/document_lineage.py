"""Emit document_lineage.json from the experimental phase-spec compiler."""

from __future__ import annotations

from spec_os.compiler.ir import SpecOSRepoIR

_PHASE_FILES = [
    "specos/phase_1_foundation_contracts.specos.json",
    "specos/phase_2_planning_spine_inputs.specos.json",
    "specos/phase_3_assumptions_compute.specos.json",
    "specos/phase_4_financial_outputs.specos.json",
    "specos/phase_5_interpretation_trust.specos.json",
    "specos/phase_6_migration_verification_rollout.specos.json",
]


def compile_document_lineage_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_6 = ir.phases["phase_6_migration_verification_rollout.specos.json"]

    benchmark_docs = phase_1["meta"]["benchmark_docs"]
    source_lineage_rules = phase_6["source_lineage_rules"]

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "DOCUMENT_LINEAGE",
            "expected_source_docs": source_lineage_rules["expected_source_docs"],
            "actual_benchmark_docs": len(benchmark_docs),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "source_repos": phase_1["meta"]["source_repos"],
        "benchmark_docs": benchmark_docs,
        "lineage_rule": source_lineage_rules["lineage_rule"],
        "reconciliation_rule": source_lineage_rules["reconciliation_rule"],
        "artifacts": [
            {
                "artifact": artifact_name,
                "generated_from": _PHASE_FILES,
                "lineage_rule": source_lineage_rules["lineage_rule"],
                "status": "release_candidate",
            }
            for artifact_name in phase_6["artifact_manifest"]
        ],
    }
