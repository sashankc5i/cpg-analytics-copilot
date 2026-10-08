from unittest.mock import patch

from app.agent.challenge import challenge_synthesizer


def test_challenge_synthesizer_returns_answer():

    state = {
        "question": "Why did revenue decline?",
        "original_answer": (
            "Regional performance contributed "
            "to the decline."
        ),
        "hypotheses": [],
        "evidence": {},
        "claims": [
            {
                "id": "C1",
                "claim": (
                    "Regional performance contributed "
                    "to the decline."
                ),
                "type": "causal",
                "investigations": [
                    "regional_performance",
                    "revenue_trend",
                ],
                "status": "partially_supported",
                "supporting_evidence": [
                    "Regional performance differences "
                    "were observed."
                ],
                "contradicting_evidence": [],
                "missing_evidence": [
                    "Evidence establishing causality."
                ],
            }
        ],
        "challenge_plan": [
            "regional_performance",
            "revenue_trend",
        ],
        "challenge_evidence": {},
        "challenge_answer": "",
    }

    class FakeMessage:
        content = (
            "### Challenge\n\n"
            "The conclusion is partially supported.\n\n"
            "### Supporting evidence\n\n"
            "Regional differences are observable.\n\n"
            "### Contradicting evidence\n\n"
            "No direct contradiction was found.\n\n"
            "### Missing evidence\n\n"
            "Causal evidence is missing.\n\n"
            "### Alternative explanations\n\n"
            "Other factors may explain the decline.\n\n"
            "### Bottom line\n\n"
            "Partially supported."
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    with patch(
        "app.agent.challenge.client",
        FakeClient(),
    ):
        result = challenge_synthesizer(state)

    assert "challenge_answer" in result

    assert (
        "Partially supported."
        in result["challenge_answer"]
    )