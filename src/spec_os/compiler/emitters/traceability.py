"""Emit traceability.json from the experimental phase-spec compiler."""

from __future__ import annotations

from spec_os.compiler.emitters.api_contracts import compile_api_contracts_artifact
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


def compile_traceability_artifact(ir: SpecOSRepoIR) -> dict:
    api_contracts = compile_api_contracts_artifact(ir)
    variable_registry = compile_variable_registry_artifact(ir)

    apis = [
        {
            "artifactType": "api",
            "artifactName": endpoint["path"],
            "method": endpoint["method"],
            "requirementFamilies": endpoint["requirement_families"],
            "ownerDoc": endpoint["owner_doc"],
            "citations": [f"phase_{endpoint['phase_number']}"],
        }
        for endpoint in api_contracts["endpoints"]
    ]

    routes = []
    for phase_file, phase_number, default_owner in (
        ("phase_2_planning_spine_inputs.specos.json", 2, "WORKSPACE_FLOW.md"),
        ("phase_3_assumptions_compute.specos.json", 3, "FEATURE_INDEX.md"),
        ("phase_4_financial_outputs.specos.json", 4, "FINANCIAL_MODEL.md"),
        ("phase_5_interpretation_trust.specos.json", 5, "CONFIDENCE_MODEL.md"),
    ):
        phase_doc = ir.phases[phase_file]
        families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        for route in phase_doc.get("routes", []):
            routes.append(
                {
                    "artifactType": "route",
                    "artifactName": route["path"],
                    "surfaceCode": route["surfaceCode"],
                    "legacyScreenIds": route.get("legacyScreenIds", []),
                    "requirementFamilies": families,
                    "ownerDoc": route.get("ownerDoc", default_owner),
                    "citations": [f"phase_{phase_number}"],
                }
            )

    entities = []
    for phase_file, phase_number in (
        ("phase_2_planning_spine_inputs.specos.json", 2),
        ("phase_3_assumptions_compute.specos.json", 3),
        ("phase_4_financial_outputs.specos.json", 4),
        ("phase_5_interpretation_trust.specos.json", 5),
    ):
        phase_doc = ir.phases[phase_file]
        families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        for entity_name in _iter_entity_names(phase_doc):
            entities.append(
                {
                    "artifactType": "entity",
                    "artifactName": entity_name,
                    "requirementFamilies": families,
                    "ownerDoc": _owner_doc_for_phase(phase_number),
                    "citations": [f"phase_{phase_number}"],
                }
            )

    metrics = []
    for metric in variable_registry["metrics"]:
        metrics.append(
            {
                "artifactType": "metric",
                "artifactName": metric["id"],
                "formula": metric["formula"],
                "requirementFamilies": metric["requirement_families"],
                "ownerDoc": metric["owner_doc"],
                "citations": [f"phase_{metric['phase_number']}"],
            }
        )

    screens = []
    for phase_file, phase_number in (
        ("phase_2_planning_spine_inputs.specos.json", 2),
        ("phase_4_financial_outputs.specos.json", 4),
        ("phase_5_interpretation_trust.specos.json", 5),
    ):
        phase_doc = ir.phases[phase_file]
        families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        for screen in phase_doc.get("screens", []):
            if isinstance(screen, dict):
                screens.append(
                    {
                        "artifactType": "screen",
                        "artifactName": screen["future"],
                        "path": screen.get("path"),
                        "requirementFamilies": families,
                        "citations": [f"phase_{phase_number}"],
                    }
                )
            else:
                screens.append(
                    {
                        "artifactType": "screen",
                        "artifactName": screen,
                        "path": None,
                        "requirementFamilies": families,
                        "citations": [f"phase_{phase_number}"],
                    }
                )

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": ir.phases["phase_1_foundation_contracts.specos.json"]["meta"]["target_system"],
            "target_fidelity": ir.phases["phase_1_foundation_contracts.specos.json"]["meta"]["target_fidelity"],
            "doc_type": "TRACEABILITY",
            "api_count": len(apis),
            "route_count": len(routes),
            "entity_count": len(entities),
            "metric_count": len(metrics),
            "screen_count": len(screens),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "apis": apis,
        "routes": routes,
        "entities": entities,
        "metrics": metrics,
        "screens": screens,
    }


def _owner_doc_for_phase(phase_number: int) -> str:
    return {
        2: "WORKSPACE_FLOW.md",
        3: "FEATURE_INDEX.md",
        4: "FINANCIAL_MODEL.md",
        5: "CONFIDENCE_MODEL.md",
    }[phase_number]


def _iter_entity_names(phase_doc: dict) -> list[str]:
    raw_entities = phase_doc.get("entities", {})
    names: list[str] = []

    if isinstance(raw_entities, dict):
        for items in raw_entities.values():
            names.extend(str(item) for item in items)
    elif isinstance(raw_entities, list):
        names.extend(str(item) for item in raw_entities)

    return names
