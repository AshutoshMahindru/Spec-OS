"""Emit system_spec.json from the experimental phase-spec compiler."""

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


def compile_system_spec_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_6 = ir.phases["phase_6_migration_verification_rollout.specos.json"]
    context_pack = phase_1["persistent_context_pack"]

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "SYSTEM_SPEC",
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "global_counts": phase_1["meta"]["global_counts"],
        "source_of_truth_hierarchy": phase_1["meta"]["source_of_truth_hierarchy"],
        "foundation": {
            "response_envelope": context_pack["shared_response_envelope"],
            "error_model": context_pack["error_model"],
            "route_metadata_contract": context_pack["route_metadata_contract"],
            "governance_state_machine": context_pack["governance_state_machine"],
            "validation_and_reconciliation": context_pack["validation_and_reconciliation"],
        },
        "phases": [
            {
                "phase_number": 1,
                "phase_name": phase_1["meta"]["phase_name"],
                "status": phase_1["meta"]["status"],
                "primary_goal": phase_1["meta"]["primary_goal"],
                "requirement_families": [item["code"] for item in context_pack["requirement_families"]],
            },
            _phase_summary(ir.phases["phase_2_planning_spine_inputs.specos.json"]),
            _phase_summary(ir.phases["phase_3_assumptions_compute.specos.json"]),
            _phase_summary(ir.phases["phase_4_financial_outputs.specos.json"]),
            _phase_summary(ir.phases["phase_5_interpretation_trust.specos.json"]),
            _phase_summary(ir.phases["phase_6_migration_verification_rollout.specos.json"]),
        ],
        "execution_readiness": phase_6["execution_readiness"],
        "acceptance_gates": phase_6["acceptance_gates"],
        "migration_policy": phase_6["migration_policy"],
        "remaining_gap_policy": phase_6["remaining_gap_policy"],
    }


def _phase_summary(phase_doc: dict) -> dict:
    meta = phase_doc["meta"]
    return {
        "phase_number": meta["phase_number"],
        "phase_name": meta["phase_name"],
        "status": meta["status"],
        "primary_goal": meta["primary_goal"],
        "requirement_families": phase_doc["phase_scope"]["requirement_families"],
    }
