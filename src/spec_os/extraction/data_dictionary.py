"""Data-dictionary graph extractor."""

from __future__ import annotations

from spec_os.graph import add_edge, ensure_node, make_citation, make_node_registry


def extract_data_dictionary_graph(structured: list[dict], doc_id: str) -> dict:
    nodes, node_index, edges = make_node_registry(doc_id)
    doc_node_id = f"doc_{doc_id}"
    current_section_id: str | None = None
    current_model_id: str | None = None
    current_section_title = ""

    for i, sec in enumerate(structured):
        if sec["type"] == "heading":
            current_section_id = f"sec_{doc_id}_{i}"
            title = sec["text"]
            current_section_title = title
            node = {"id": current_section_id, "type": "Section", "title": title, "level": sec.get("level", 1)}
            node["citations"] = [make_citation(sec, section_title=title)]
            nodes.append(node)
            node_index[current_section_id] = node
            add_edge(edges, doc_node_id, current_section_id, "HAS_SECTION")
            if "data model" in title.lower() or "schema" in title.lower():
                current_model_id = ensure_node(
                    nodes,
                    node_index,
                    "DataModel",
                    "name",
                    title,
                    source_section=title,
                    citations=[make_citation(sec, section_title=title)],
                )
                add_edge(edges, current_section_id, current_model_id, "CONTAINS")
            continue

        text = sec.get("text", "")
        text_lower = text.lower()
        citation = make_citation(sec, section_title=current_section_title)

        if "planning grain key" in text_lower:
            current_model_id = ensure_node(
                nodes,
                node_index,
                "DataModel",
                "name",
                "Planning Grain Key",
                source_section="Data Model Summary",
                citations=[citation],
            )
            if current_section_id:
                add_edge(edges, current_section_id, current_model_id, "CONTAINS")
            for fname in ("company_id", "scenario_id", "assumption_set_id", "planning_period_id"):
                fid = ensure_node(
                    nodes,
                    node_index,
                    "Field",
                    "name",
                    fname,
                    data_type="uuid",
                    nullable=False,
                    default=None,
                    citations=[citation],
                )
                add_edge(edges, current_model_id, fid, "HAS_FIELD")

        if "audit fields:" in text_lower:
            current_model_id = ensure_node(
                nodes,
                node_index,
                "DataModel",
                "name",
                "Audit Fields",
                source_section="Data Model Summary",
                citations=[citation],
            )
            if current_section_id:
                add_edge(edges, current_section_id, current_model_id, "CONTAINS")
            for fname in ("created_by", "updated_by", "created_at", "updated_at"):
                dtype = "timestamp" if fname.endswith("_at") else "uuid"
                fid = ensure_node(
                    nodes,
                    node_index,
                    "Field",
                    "name",
                    fname,
                    data_type=dtype,
                    nullable=False,
                    default=None,
                    citations=[citation],
                )
                add_edge(edges, current_model_id, fid, "HAS_FIELD")

        if "tenant_id" in text_lower:
            current_model_id = ensure_node(
                nodes,
                node_index,
                "DataModel",
                "name",
                "Multi-tenancy Base",
                source_section="Data Model Summary",
                citations=[citation],
            )
            fid = ensure_node(
                nodes,
                node_index,
                "Field",
                "name",
                "tenant_id",
                data_type="uuid",
                nullable=False,
                default=None,
                citations=[citation],
            )
            add_edge(edges, current_model_id, fid, "HAS_FIELD")
            if current_section_id:
                add_edge(edges, current_section_id, current_model_id, "CONTAINS")

        if "uuid primary keys" in text_lower:
            current_model_id = ensure_node(
                nodes,
                node_index,
                "DataModel",
                "name",
                "Schema Conventions",
                source_section="Data Model Summary",
                citations=[citation],
            )
            fid = ensure_node(
                nodes,
                node_index,
                "Field",
                "name",
                "id",
                data_type="uuid",
                nullable=False,
                default="gen_random_uuid()",
                citations=[citation],
            )
            add_edge(edges, current_model_id, fid, "HAS_FIELD")

    return {"nodes": nodes, "edges": edges}
