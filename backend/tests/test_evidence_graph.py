from app.agent.evidence_graph import build_evidence_graph


def test_build_evidence_graph_creates_claim_nodes():
    claims = [
        {
            "id": "claim_1",
            "claim": "Premium customers generate higher revenue.",
            "evidence_ids": ["evidence_1"],
        }
    ]

    evidence = {
        "evidence_1": {
            "description": "Premium customers generated 62% of total revenue."
        }
    }

    graph = build_evidence_graph(
        claims=claims,
        evidence=evidence,
    )

    assert "nodes" in graph
    assert "edges" in graph

    claim_nodes = [
        node
        for node in graph["nodes"]
        if node["type"] == "claim"
    ]

    assert len(claim_nodes) == 1
    assert claim_nodes[0]["id"] == "claim_1"


def test_build_evidence_graph_creates_evidence_nodes():
    claims = [
        {
            "id": "claim_1",
            "claim": "Premium customers generate higher revenue.",
            "evidence_ids": ["evidence_1"],
        }
    ]

    evidence = {
        "evidence_1": {
            "description": "Premium customers generated 62% of total revenue."
        }
    }

    graph = build_evidence_graph(
        claims=claims,
        evidence=evidence,
    )

    evidence_nodes = [
        node
        for node in graph["nodes"]
        if node["type"] == "evidence"
    ]

    assert len(evidence_nodes) == 1
    assert evidence_nodes[0]["id"] == "evidence_1"


def test_build_evidence_graph_creates_support_relationship():
    claims = [
        {
            "id": "claim_1",
            "claim": "Premium customers generate higher revenue.",
            "evidence_ids": ["evidence_1"],
        }
    ]

    evidence = {
        "evidence_1": {
            "description": "Premium customers generated 62% of total revenue."
        }
    }

    graph = build_evidence_graph(
        claims=claims,
        evidence=evidence,
    )

    assert len(graph["edges"]) == 1

    edge = graph["edges"][0]

    assert edge["source"] == "claim_1"
    assert edge["target"] == "evidence_1"
    assert edge["type"] == "supported_by"


def test_build_evidence_graph_ignores_missing_evidence():
    claims = [
        {
            "id": "claim_1",
            "claim": "Premium customers generate higher revenue.",
            "evidence_ids": [
                "evidence_1",
                "evidence_missing",
            ],
        }
    ]

    evidence = {
        "evidence_1": {
            "description": "Premium customers generated 62% of total revenue."
        }
    }

    graph = build_evidence_graph(
        claims=claims,
        evidence=evidence,
    )

    assert len(graph["edges"]) == 1

    assert graph["edges"][0]["target"] == "evidence_1"


def test_build_evidence_graph_supports_multiple_claims():
    claims = [
        {
            "id": "claim_1",
            "claim": "Premium customers generate higher revenue.",
            "evidence_ids": ["evidence_1"],
        },
        {
            "id": "claim_2",
            "claim": "Premium customers have higher retention.",
            "evidence_ids": ["evidence_2"],
        },
    ]

    evidence = {
        "evidence_1": {
            "description": "Premium customers generated 62% of revenue."
        },
        "evidence_2": {
            "description": "Premium customers have 84% retention."
        },
    }

    graph = build_evidence_graph(
        claims=claims,
        evidence=evidence,
    )

    assert len(graph["nodes"]) == 4
    assert len(graph["edges"]) == 2


def test_build_evidence_graph_handles_empty_input():
    graph = build_evidence_graph(
        claims=[],
        evidence={},
    )

    assert graph == {
        "nodes": [],
        "edges": [],
    }