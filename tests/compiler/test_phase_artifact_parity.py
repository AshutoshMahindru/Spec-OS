"""Artifact parity checks for the experimental phase-spec compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from spec_os.compiler.emitters import (
    compile_canonical_schema_artifact,
    compile_variable_registry_artifact,
)
from spec_os.compiler.specos_repo_loader import load_specos_repo_ir

DEFAULT_SPEC_PACK = Path("/tmp/Modelling_Engine_SpecOS_20260403")


def _spec_pack() -> Path:
    path = Path(os.environ.get("SPECOS_SHADOW_REPO", str(DEFAULT_SPEC_PACK))).expanduser()
    if not path.exists():
        pytest.skip(f"SPECOS_SHADOW_REPO not found: {path}")
    return path


def test_variable_registry_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    compiled = compile_variable_registry_artifact(ir)
    source = json.loads((spec_pack / "artifacts" / "variable_registry.json").read_text(encoding="utf-8"))

    assert compiled["variables"] == source["variables"]
    assert compiled["metrics"] == source["metrics"]
    assert compiled["meta"]["declared_variable_count"] == source["meta"]["declared_variable_count"]
    assert compiled["meta"]["actual_variable_count"] == source["meta"]["actual_variable_count"]
    assert compiled["meta"]["declared_metric_count"] == source["meta"]["declared_metric_count"]
    assert compiled["meta"]["actual_metric_count"] == source["meta"]["actual_metric_count"]


def test_canonical_schema_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    compiled = compile_canonical_schema_artifact(ir)
    source = json.loads((spec_pack / "artifacts" / "canonical_schema.json").read_text(encoding="utf-8"))

    assert compiled["entities"] == source["entities"]
    assert compiled["meta"]["declared_entity_count"] == source["meta"]["declared_entity_count"]
    assert compiled["meta"]["actual_entity_count"] == source["meta"]["actual_entity_count"]
