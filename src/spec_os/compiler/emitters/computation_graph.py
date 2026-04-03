"""Emit computation_graph.json from the experimental phase-spec IR."""

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


def compile_computation_graph_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    phase_3 = ir.phases["phase_3_assumptions_compute.specos.json"]
    phase_6 = ir.phases["phase_6_migration_verification_rollout.specos.json"]

    graph = phase_3["computation_graph"]
    execution_plan = phase_3["execution_plan"]
    readiness = phase_6["execution_readiness"]

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "COMPUTATION_GRAPH",
            "required_nodes": readiness["required_graph"]["nodes"],
            "actual_nodes": len(graph["nodes"]),
            "required_edges": readiness["required_graph"]["edges"],
            "actual_edges": len(graph["edges"]),
            "required_steps": readiness["required_step_count"],
            "actual_steps": len(execution_plan),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "graph": graph,
        "execution_plan": execution_plan,
        "freshness_rule": _freshness_rule(phase_3),
    }


def _freshness_rule(phase_3: dict) -> str:
    for gate in phase_3.get("acceptance_gates", []):
        if "dependency snapshot hash changes" in gate:
            return "Outputs are invalidated whenever dependency snapshot hash changes."
    raise ValueError("No freshness rule found in phase_3 acceptance_gates")
