from collections import defaultdict
from typing import Any


class InvestigationSessionManager:
    """
    Maintains independent investigation sessions.

    Each investigation session contains its own
    conversational and analytical context.

    This is intentionally in-memory for the current
    development phase. Persistent investigation
    storage can be introduced later.
    """

    def __init__(self):
        self.sessions = defaultdict(
            lambda: {
                "history": [],
                "latest_plan": [],
                "latest_evidence": {},
                "latest_answer": "",
            }
        )


    def get_session(
        self,
        investigation_id: str,
    ) -> dict[str, Any]:
        """
        Return the investigation session.

        A new session is created automatically when
        the investigation ID has not been seen before.
        """

        return self.sessions[
            investigation_id
        ]


    def get_history(
        self,
        investigation_id: str,
    ) -> list[dict[str, str]]:
        """
        Return conversational history for an
        investigation session.
        """

        return self.sessions[
            investigation_id
        ]["history"]


    def add_message(
        self,
        investigation_id: str,
        message: dict[str, str],
    ):
        """
        Add a message to the investigation history.
        """

        self.sessions[
            investigation_id
        ]["history"].append(message)


    def update_investigation(
        self,
        investigation_id: str,
        *,
        plan: list[str],
        evidence: dict[str, Any],
        answer: str,
    ):
        """
        Store the latest investigation result.
        """

        session = self.sessions[
            investigation_id
        ]

        session["latest_plan"] = plan
        session["latest_evidence"] = evidence
        session["latest_answer"] = answer


    def clear(
        self,
        investigation_id: str,
    ):
        """
        Reset a single investigation session.
        """

        self.sessions[
            investigation_id
        ] = {
            "history": [],
            "latest_plan": [],
            "latest_evidence": {},
            "latest_answer": "",
        }


investigation_session_manager = (
    InvestigationSessionManager()
)