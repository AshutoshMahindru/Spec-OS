"""Emit roadmap.json from the experimental phase-spec compiler."""

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


def compile_roadmap_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_6 = ir.phases["phase_6_migration_verification_rollout.specos.json"]

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "ROADMAP",
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "waves": [
            {
                "wave": 1,
                "phases": [1],
                "goal": phase_1["meta"]["primary_goal"],
                "status": "in_progress",
                "priority": "P0",
            },
            {
                "wave": 2,
                "phases": [2, 3],
                "goal": "Planning spine, assumptions, and compute orchestration",
                "status": "pending",
                "priority": "P1",
            },
            {
                "wave": 3,
                "phases": [4, 5],
                "goal": "Financial outputs, analysis, confidence, and governance",
                "status": "pending",
                "priority": "P1",
            },
            {
                "wave": 4,
                "phases": [6],
                "goal": phase_6["meta"]["primary_goal"],
                "status": "pending",
                "priority": "P1",
            },
        ],
        "cutover_phases": phase_6["migration_policy"]["cutover_phases"],
        "acceptance_gates": phase_6["acceptance_gates"],
    }
