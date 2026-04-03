"""Shadow parity checks for the experimental phase-spec compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from spec_os.compiler.specos_repo_loader import load_specos_repo_ir

DEFAULT_SPEC_PACK = Path("/tmp/Modelling_Engine_SpecOS_20260403")
DEFAULT_BASELINE_JSON = Path(
    "/Users/ashutoshmahindru/Documents/Spec-OS-stabilize-20260403-203448/shadow/baseline/import_result.json"
)


def _path_from_env(name: str, default: Path) -> Path:
    path = Path(os.environ.get(name, str(default))).expanduser()
    if not path.exists():
        pytest.skip(f"{name} not found: {path}")
    return path


def test_inventory_counts_match_source_validation():
    spec_pack = _path_from_env("SPECOS_SHADOW_REPO", DEFAULT_SPEC_PACK)
    ir = load_specos_repo_ir(spec_pack)

    completeness = json.loads((spec_pack / "validation" / "completeness.json").read_text(encoding="utf-8"))
    actual = completeness["actual_counts"]

    assert ir.inventory.counts["apis"] == actual["apis"]
    assert ir.inventory.counts["schema_entities"] == actual["schema_entities"]
    assert ir.inventory.counts["variables"] == actual["variables"]
    assert ir.inventory.counts["metrics"] == actual["metrics"]
    assert ir.inventory.counts["routes"] == actual["routes"]
    assert ir.inventory.counts["screens"] == actual["screens"]

    assert ir.foundation.authoritative_counts["apis"] == 128
    assert ir.foundation.authoritative_counts["schema_entities"] == 51
    assert ir.foundation.authoritative_counts["variables"] == 30
    assert ir.foundation.authoritative_counts["metrics"] == 12


def test_inventory_counts_match_shadow_baseline_import():
    spec_pack = _path_from_env("SPECOS_SHADOW_REPO", DEFAULT_SPEC_PACK)
    baseline_json = _path_from_env("SPECOS_SHADOW_BASELINE_JSON", DEFAULT_BASELINE_JSON)

    ir = load_specos_repo_ir(spec_pack)
    baseline = json.loads(baseline_json.read_text(encoding="utf-8"))

    assert baseline["status"] == "imported"
    assert baseline["doc_type"] == "SPECOS_REPO"

    assert ir.inventory.counts["apis"] == baseline["apis"]
    assert ir.inventory.counts["variables"] == baseline["variables"]
    assert ir.inventory.counts["metrics"] == baseline["metrics"]
