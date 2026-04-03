"""Emit api_contracts.json from the experimental phase-spec IR."""

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

_PHASE_CONFIG = [
    {
        "file": "phase_2_planning_spine_inputs.specos.json",
        "phase_number": 2,
        "phase_name": "Planning Spine and Modeling Inputs",
        "owner_doc": "WORKSPACE_FLOW.md",
    },
    {
        "file": "phase_3_assumptions_compute.specos.json",
        "phase_number": 3,
        "phase_name": "Assumptions and Compute Engine",
        "owner_doc": "FEATURE_INDEX.md",
    },
    {
        "file": "phase_4_financial_outputs.specos.json",
        "phase_number": 4,
        "phase_name": "Financial Output Layer",
        "owner_doc": "FINANCIAL_MODEL.md",
    },
    {
        "file": "phase_5_interpretation_trust.specos.json",
        "phase_number": 5,
        "phase_name": "Interpretation, Confidence, and Governance",
        "owner_doc": "CONFIDENCE_MODEL.md",
    },
]


def compile_api_contracts_artifact(ir: SpecOSRepoIR) -> dict:
    phase_1 = ir.phases["phase_1_foundation_contracts.specos.json"]
    persistent_context_pack = phase_1["persistent_context_pack"]
    endpoints: list[dict] = []

    for config in _PHASE_CONFIG:
        phase_doc = ir.phases[config["file"]]
        requirement_families = phase_doc.get("phase_scope", {}).get("requirement_families", [])
        api_families = phase_doc.get("api_families", {})

        if isinstance(api_families, dict):
            for domain_family, raws in api_families.items():
                for raw in raws:
                    endpoints.append(
                        _build_endpoint(
                            raw=raw,
                            phase_number=config["phase_number"],
                            phase_name=config["phase_name"],
                            domain_family=domain_family,
                            requirement_families=requirement_families,
                            owner_doc=config["owner_doc"],
                            error_registry=persistent_context_pack["error_model"]["registry"],
                        )
                    )
        elif isinstance(api_families, list):
            for raw in api_families:
                endpoints.append(
                    _build_endpoint(
                        raw=raw,
                        phase_number=config["phase_number"],
                        phase_name=config["phase_name"],
                        domain_family=config["phase_name"],
                        requirement_families=requirement_families,
                        owner_doc=config["owner_doc"],
                        error_registry=persistent_context_pack["error_model"]["registry"],
                    )
                )

    return {
        "meta": {
            "status": "release_candidate",
            "generated_from": _PHASE_FILES,
            "target_system": phase_1["meta"]["target_system"],
            "target_fidelity": phase_1["meta"]["target_fidelity"],
            "doc_type": "API_CONTRACTS",
            "declared_api_count": ir.foundation.authoritative_counts.get("apis"),
            "actual_api_count": len(endpoints),
            "compiler_mode": "shadow_phase_spec_compiler",
        },
        "shared_response_envelope": persistent_context_pack["shared_response_envelope"],
        "error_model": persistent_context_pack["error_model"],
        "api_namespace_model": persistent_context_pack["api_namespace_model"],
        "endpoints": endpoints,
    }


def _build_endpoint(
    *,
    raw: str,
    phase_number: int,
    phase_name: str,
    domain_family: str,
    requirement_families: list[str],
    owner_doc: str,
    error_registry: list[str],
) -> dict:
    method, path = raw.split(" ", 1)
    return {
        "phase_number": phase_number,
        "phase_name": phase_name,
        "domain_family": domain_family,
        "method": method,
        "path": path,
        "raw": raw,
        "requirement_families": requirement_families,
        "response_envelope": "shared_response_envelope",
        "error_registry": error_registry,
        "owner_doc": owner_doc,
    }
