"""API contract parity checks for the experimental phase-spec compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from spec_os.compiler.emitters import compile_api_contracts_artifact
from spec_os.compiler.specos_repo_loader import load_specos_repo_ir

DEFAULT_SPEC_PACK = Path("/tmp/Modelling_Engine_SpecOS_20260403")


def _spec_pack() -> Path:
    path = Path(os.environ.get("SPECOS_SHADOW_REPO", str(DEFAULT_SPEC_PACK))).expanduser()
    if not path.exists():
        pytest.skip(f"SPECOS_SHADOW_REPO not found: {path}")
    return path


def test_api_contracts_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    compiled = compile_api_contracts_artifact(ir)
    source = json.loads((spec_pack / "artifacts" / "api_contracts.json").read_text(encoding="utf-8"))

    assert compiled["shared_response_envelope"] == source["shared_response_envelope"]
    assert compiled["error_model"] == source["error_model"]
    assert compiled["api_namespace_model"] == source["api_namespace_model"]
    assert compiled["endpoints"] == source["endpoints"]
    assert compiled["meta"]["declared_api_count"] == source["meta"]["declared_api_count"]
    assert compiled["meta"]["actual_api_count"] == source["meta"]["actual_api_count"]
