"""Intermediate representation for the experimental phase-spec compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InventoryIR:
    apis: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    variables: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    screens: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "apis": len(self.apis),
            "schema_entities": len(self.entities),
            "variables": len(self.variables),
            "metrics": len(self.metrics),
            "routes": len(self.routes),
            "screens": len(self.screens),
        }


@dataclass
class FoundationIR:
    canonical_stage_model: list[dict[str, Any]] = field(default_factory=list)
    requirement_families: list[dict[str, Any]] = field(default_factory=list)
    authoritative_counts: dict[str, int] = field(default_factory=dict)
    readiness_rule: str = ""


@dataclass
class SpecOSRepoIR:
    repo_path: Path
    phases: dict[str, dict[str, Any]]
    foundation: FoundationIR
    inventory: InventoryIR
