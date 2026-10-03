from app.agent.hypothesis_ranking import rank_hypotheses


def test_hypotheses_are_ranked_by_evidence_coverage():
    hypotheses = [
        {"id": "H1", "statement": "A", "required_investigations": ["a", "b"], "status": "unverified", "evidence": {"a": {}}},
        {"id": "H2", "statement": "B", "required_investigations": ["a"], "status": "unverified", "evidence": {"a": {}}},
    ]
    ranked = rank_hypotheses(hypotheses, {"a": {}})
    assert ranked[0]["id"] == "H2"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["ranking"]["basis"] == "deterministic_evidence_coverage"


def test_hypothesis_ranking_does_not_claim_truth():
    ranked = rank_hypotheses(
        [{"id": "H1", "statement": "A", "required_investigations": ["a"], "status": "unverified", "evidence": {}}],
        {},
    )
    assert ranked[0]["status"] == "unverified"
    assert ranked[0]["ranking"]["score"] == 0.0
