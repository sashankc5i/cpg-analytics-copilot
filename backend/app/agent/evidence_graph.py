from typing import Any


def build_evidence_graph(
    *,
    claims: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a lightweight evidence graph connecting claims
    to the evidence that supports them.

    Graph structure:

        claim
          |
          | supported_by
          v
       evidence

    Parameters
    ----------
    claims:
        List of generated claims.

    evidence:
        Evidence collected during the investigation.

    Returns
    -------
    dict
        {
            "nodes": [...],
            "edges": [...]
        }
    """

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    existing_node_ids: set[str] = set()

    # -------------------------------------------------
    # CLAIM NODES
    # -------------------------------------------------

    for index, claim in enumerate(claims):
        claim_id = str(
            claim.get(
                "id",
                f"claim_{index + 1}",
            )
        )

        claim_text = claim.get(
            "claim",
            claim.get(
                "text",
                "",
            ),
        )

        nodes.append(
            {
                "id": claim_id,
                "type": "claim",
                "label": claim_text,
                "data": claim,
            }
        )
        existing_node_ids.add(claim_id)

    # -------------------------------------------------
    # EVIDENCE NODES
    # -------------------------------------------------

    for evidence_id, evidence_item in evidence.items():
        evidence_node_id = str(evidence_id)

        if isinstance(evidence_item, dict):
            label = evidence_item.get(
                "description",
                evidence_item.get(
                    "text",
                    evidence_item.get(
                        "value",
                        evidence_node_id,
                    ),
                ),
            )
        else:
            label = str(evidence_item)

        nodes.append(
            {
                "id": evidence_node_id,
                "type": "evidence",
                "label": label,
                "data": evidence_item,
            }
        )
        existing_node_ids.add(evidence_node_id)

    # -------------------------------------------------
    # CLAIM → TRACEABLE EVIDENCE REFERENCE EDGES
    # -------------------------------------------------

    for claim_index, claim in enumerate(claims):
        claim_id = str(
            claim.get(
                "id",
                f"claim_{claim_index + 1}",
            )
        )

        references = claim.get("evidence_refs", [])
        if not isinstance(references, list):
            continue

        for reference in references:
            if not isinstance(reference, dict):
                continue

            investigation = reference.get("investigation")
            field = reference.get("field")
            entity = reference.get("entity")

            if investigation not in evidence or not field:
                continue

            evidence_id = (
                f"evidence_ref:{investigation}:{field}:"
                f"{entity if entity is not None else 'all'}"
            )

            if evidence_id not in existing_node_ids:
                source = evidence.get(investigation)
                nodes.append(
                    {
                        "id": evidence_id,
                        "type": "evidence",
                        "label": f"{investigation} · {field}"
                        + (f" · {entity}" if entity is not None else ""),
                        "data": {
                            "investigation": investigation,
                            "field": field,
                            "entity": entity,
                            "source": source,
                        },
                    }
                )
                existing_node_ids.add(evidence_id)

            edges.append(
                {
                    "source": claim_id,
                    "target": evidence_id,
                    "type": "supported_by",
                }
            )

    # -------------------------------------------------
    # CLAIM → EVIDENCE EDGES
    # -------------------------------------------------

    for claim_index, claim in enumerate(claims):
        claim_id = str(
            claim.get(
                "id",
                f"claim_{claim_index + 1}",
            )
        )

        supporting_evidence = claim.get(
            "evidence",
            claim.get(
                "evidence_ids",
                [],
            ),
        )

        if not isinstance(
            supporting_evidence,
            list,
        ):
            supporting_evidence = [
                supporting_evidence
            ]

        for evidence_id in supporting_evidence:
            if evidence_id is None:
                continue

            evidence_id = str(evidence_id)

            # Only create an edge when the evidence
            # actually exists in the evidence collection.
            if evidence_id not in evidence:
                continue

            edges.append(
                {
                    "source": claim_id,
                    "target": evidence_id,
                    "type": "supported_by",
                }
            )

    # -------------------------------------------------
    # RETURN GRAPH
    # -------------------------------------------------

    return {
        "nodes": nodes,
        "edges": edges,
    }