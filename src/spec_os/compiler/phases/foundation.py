"""Foundation loading for the experimental phase-spec compiler."""

from __future__ import annotations

from typing import Any

from spec_os.compiler.ir import FoundationIR


def build_foundation_ir(phase_1: dict[str, Any], phase_6: dict[str, Any]) -> FoundationIR:
    context_pack = phase_1.get("persistent_context_pack", {})
    validation_model = phase_6.get("validation_model", {})
    return FoundationIR(
        canonical_stage_model=context_pack.get("canonical_stage_model", []),
        requirement_families=context_pack.get("requirement_families", []),
        authoritative_counts=validation_model.get("authoritative_counts", {}),
        readiness_rule=validation_model.get("readiness_rule", ""),
    )
