"""Load Modelling_Engine_SpecOS phase files into the experimental IR."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spec_os.compiler.ir import SpecOSRepoIR
from spec_os.compiler.phases.foundation import build_foundation_ir
from spec_os.compiler.phases.inventory import build_inventory_ir

PHASE_FILES = (
    "phase_1_foundation_contracts.specos.json",
    "phase_2_planning_spine_inputs.specos.json",
    "phase_3_assumptions_compute.specos.json",
    "phase_4_financial_outputs.specos.json",
    "phase_5_interpretation_trust.specos.json",
    "phase_6_migration_verification_rollout.specos.json",
)


def load_specos_repo_ir(repo_path: str | Path) -> SpecOSRepoIR:
    repo_root = Path(repo_path).expanduser().resolve()
    specos_root = repo_root / "specos"

    phases: dict[str, dict[str, Any]] = {}
    for filename in PHASE_FILES:
        phase_path = specos_root / filename
        phases[filename] = json.loads(phase_path.read_text(encoding="utf-8"))

    foundation = build_foundation_ir(
        phases["phase_1_foundation_contracts.specos.json"],
        phases["phase_6_migration_verification_rollout.specos.json"],
    )
    inventory = build_inventory_ir(phases)

    return SpecOSRepoIR(
        repo_path=repo_root,
        phases=phases,
        foundation=foundation,
        inventory=inventory,
    )
