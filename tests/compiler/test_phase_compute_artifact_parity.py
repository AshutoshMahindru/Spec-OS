"""Parity checks for computation_graph.json and variable_mapping.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from spec_os.compiler.emitters import (
    compile_computation_graph_artifact,
    compile_variable_mapping_artifact,
)
from spec_os.compiler.specos_repo_loader import load_specos_repo_ir

DEFAULT_SPEC_PACK = Path("/tmp/Modelling_Engine_SpecOS_20260403")


def _spec_pack() -> Path:
    path = Path(os.environ.get("SPECOS_SHADOW_REPO", str(DEFAULT_SPEC_PACK))).expanduser()
    if not path.exists():
        pytest.skip(f"SPECOS_SHADOW_REPO not found: {path}")
    return path


def test_computation_graph_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    compiled = compile_computation_graph_artifact(ir)
    source = json.loads((spec_pack / "artifacts" / "computation_graph.json").read_text(encoding="utf-8"))

    assert compiled["graph"] == source["graph"]
    assert compiled["execution_plan"] == source["execution_plan"]
    assert compiled["freshness_rule"] == source["freshness_rule"]
    assert compiled["meta"]["required_nodes"] == source["meta"]["required_nodes"]
    assert compiled["meta"]["actual_nodes"] == source["meta"]["actual_nodes"]
    assert compiled["meta"]["required_edges"] == source["meta"]["required_edges"]
    assert compiled["meta"]["actual_edges"] == source["meta"]["actual_edges"]
    assert compiled["meta"]["required_steps"] == source["meta"]["required_steps"]
    assert compiled["meta"]["actual_steps"] == source["meta"]["actual_steps"]


def test_variable_mapping_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    compiled = compile_variable_mapping_artifact(ir)
    source = json.loads((spec_pack / "artifacts" / "variable_mapping.json").read_text(encoding="utf-8"))

    assert compiled["mappings"] == source["mappings"]
