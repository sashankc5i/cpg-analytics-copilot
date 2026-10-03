from collections import defaultdict
from copy import deepcopy
from typing import Any


def _build_session() -> dict[str, Any]:
    return {
        "history": [],
        "latest_plan": [],
        "latest_evidence": {},
        "latest_claims": [],
        "latest_confidence": {},
        "latest_answer": "",
        "question": "",
    }


class InvestigationSessionManager:
    def __init__(self):
        self.sessions = defaultdict(_build_session)

    def get_session(self, investigation_id):
        return self.sessions[investigation_id]

    def get_history(self, investigation_id):
        return deepcopy(self.sessions[investigation_id]["history"])

    def add_message(self, investigation_id, message):
        self.sessions[investigation_id]["history"].append(
            deepcopy(message)
        )

    def update_investigation(
        self,
        investigation_id: str,
        *,
        plan: list[str],
        evidence: dict[str, Any],
        claims: list[dict[str, Any]] | None = None,
        confidence: dict[str, Any] | None = None,
        answer: str,
        question: str | None = None,
    ):
        session = self.sessions[investigation_id]
        session["latest_plan"] = deepcopy(plan)
        session["latest_evidence"] = deepcopy(evidence)
        session["latest_claims"] = deepcopy(claims or [])
        session["latest_confidence"] = deepcopy(confidence or {})
        session["latest_answer"] = answer
        if question is not None:
            session["question"] = question

    def get_latest_investigation(self, investigation_id):
        session = self.get_session(investigation_id)
        return {
            "plan": deepcopy(session["latest_plan"]),
            "evidence": deepcopy(session["latest_evidence"]),
            "claims": deepcopy(session["latest_claims"]),
            "confidence": deepcopy(session["latest_confidence"]),
            "answer": session["latest_answer"],
            "question": session["question"],
        }

    def has_investigation(self, investigation_id):
        return investigation_id in self.sessions

    def delete(self, investigation_id):
        if investigation_id not in self.sessions:
            return False
        del self.sessions[investigation_id]
        return True

    def clear(self, investigation_id):
        self.sessions[investigation_id] = _build_session()


investigation_session_manager = InvestigationSessionManager()
