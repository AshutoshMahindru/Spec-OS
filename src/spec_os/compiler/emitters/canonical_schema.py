"""Emit canonical_schema.json from the experimental phase-spec IR."""

from __future__ import annotations

from spec_os.compiler.ir import SpecOSRepoIR

_PHASE_FILES = [
    "phase_1_foundation_contracts.specos.json",
    "phase_2_planning_spine_inputs.specos.json",
    "phase_3_assumptions_compute.specos.json",
    "phase_4_financial_outputs.specos.json",
    "phase_5_interpretation_trust.specos.json",
    "phase_6_migration_verification_rollout.specos.json",
]

_PHASE_INFO = {
    "phase_2_planning_spine_inputs.specos.json": (2, "Planning Spine and Modeling Inputs"),
    "phase_3_assumptions_compute.specos.json": (3, "Assumptions and Compute Engine"),
    "phase_4_financial_outputs.specos.json": (4, "Financial Output Layer"),
    "phase_5_interpretation_trust.specos.json": (5, "Interpretation, Confidence, and Governance"),
}


def compile_canonical_schema_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    entities = []

    for phase_file in (
        "phase_2_planning_spine_inputs.specos.json",
        "phase_3_assumptions_compute.specos.json",
        "phase_4_financial_outputs.specos.json",
        "phase_5_interpretation_trust.specos.json",
    ):
        phase_doc = ir.phases[phase_file]
        phase_number, phase_name = _PHASE_INFO[phase_file]
        requirement_families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        entity_contracts = phase_doc.get("entity_contracts", {})
        shared_output_fields = entity_contracts.get("shared_output_fields", [])

        for entity_name in _iter_entity_names(phase_doc):
            if entity_name in entity_contracts and isinstance(entity_contracts[entity_name], list):
                fields = entity_contracts[entity_name]
            elif phase_number == 4:
                fields = shared_output_fields
            else:
                fields = []

            entities.append(
                {
                    "entity_name": entity_name,
                    "phase_number": phase_number,
                    "phase_name": phase_name,
                    "requirement_families": requirement_families,
                    "fields": fields,
                }
            )

    entities = sorted(entities, key=lambda item: item["entity_name"])

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "CANONICAL_SCHEMA",
            "declared_entity_count": ir.foundation.authoritative_counts.get("schema_entities"),
            "actual_entity_count": len(entities),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "entities": entities,
    }


def _iter_entity_names(phase_doc: dict) -> list[str]:
    raw_entities = phase_doc.get("entities", {})
    names: list[str] = []

    if isinstance(raw_entities, dict):
        for items in raw_entities.values():
            names.extend(str(item) for item in items)
    elif isinstance(raw_entities, list):
        names.extend(str(item) for item in raw_entities)

    return names
