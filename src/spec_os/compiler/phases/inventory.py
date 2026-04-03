"""Inventory extraction for the experimental phase-spec compiler."""

from __future__ import annotations

from typing import Any

from spec_os.compiler.ir import InventoryIR


def build_inventory_ir(phases: dict[str, dict[str, Any]]) -> InventoryIR:
    phase_2 = phases["phase_2_planning_spine_inputs.specos.json"]
    phase_3 = phases["phase_3_assumptions_compute.specos.json"]
    phase_4 = phases["phase_4_financial_outputs.specos.json"]
    phase_5 = phases["phase_5_interpretation_trust.specos.json"]

    return InventoryIR(
        apis=_collect_apis([phase_2, phase_3, phase_4, phase_5]),
        entities=_collect_entities([phase_2, phase_3, phase_4, phase_5]),
        variables=list(phase_3.get("variables", [])),
        metrics=_collect_unique_metric_ids([phase_3, phase_4, phase_5]),
        routes=_collect_routes([phase_2, phase_3, phase_4, phase_5]),
        screens=_collect_screens([phase_2, phase_4, phase_5]),
    )


def _collect_apis(phase_docs: list[dict[str, Any]]) -> list[str]:
    apis: list[str] = []
    for phase_doc in phase_docs:
        api_families = phase_doc.get("api_families", {})
        if isinstance(api_families, dict):
            for items in api_families.values():
                apis.extend(str(item) for item in items)
        elif isinstance(api_families, list):
            apis.extend(str(item) for item in api_families)
    return apis


def _collect_entities(phase_docs: list[dict[str, Any]]) -> list[str]:
    entities: list[str] = []
    for phase_doc in phase_docs:
        raw_entities = phase_doc.get("entities", {})
        if isinstance(raw_entities, dict):
            for items in raw_entities.values():
                entities.extend(str(item) for item in items)
        elif isinstance(raw_entities, list):
            entities.extend(str(item) for item in raw_entities)
    return entities


def _collect_unique_metric_ids(phase_docs: list[dict[str, Any]]) -> list[str]:
    metric_ids: list[str] = []
    seen: set[str] = set()
    for phase_doc in phase_docs:
        for metric in phase_doc.get("metrics", []):
            metric_id = str(metric.get("id", "")).strip()
            if not metric_id or metric_id in seen:
                continue
            seen.add(metric_id)
            metric_ids.append(metric_id)
    return metric_ids


def _collect_routes(phase_docs: list[dict[str, Any]]) -> list[str]:
    routes: list[str] = []
    for phase_doc in phase_docs:
        for route in phase_doc.get("routes", []):
            if isinstance(route, dict):
                routes.append(str(route.get("path", "")))
            else:
                routes.append(str(route))
    return routes


def _collect_screens(phase_docs: list[dict[str, Any]]) -> list[str]:
    screens: list[str] = []
    for phase_doc in phase_docs:
        for screen in phase_doc.get("screens", []):
            if isinstance(screen, str):
                screens.append(screen)
            elif isinstance(screen, dict):
                screens.append(
                    str(
                        screen.get("future")
                        or screen.get("legacy")
                        or screen.get("path")
                        or screen.get("surfaceCode")
                        or "unknown_screen"
                    )
                )
    return screens
