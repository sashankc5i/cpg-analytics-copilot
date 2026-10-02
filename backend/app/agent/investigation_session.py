from collections import defaultdict
from copy import deepcopy
from typing import Any


def _build_session() -> dict[str, Any]:
    """
    Create the default structure for an investigation session.
    """

    return {
        "history": [],
        "latest_plan": [],
        "latest_evidence": {},
        "latest_claims": [],
        "latest_answer": "",
    }


class InvestigationSessionManager:
    """
    Maintains independent investigation sessions.

    Each investigation session contains its own
    conversational and analytical context.

    This manager is keyed by conversation/investigation ID.

    The manager intentionally keeps investigation state
    in-memory for the current development phase.

    Public read operations return defensive copies so
    callers cannot accidentally mutate internal state.

    Input objects are also copied when stored so the
    manager owns its internal state independently from
    caller-owned mutable objects.
    """

    def __init__(self):
        self.sessions = defaultdict(_build_session)

    def get_session(
        self,
        investigation_id: str,
    ) -> dict[str, Any]:
        """
        Return the investigation session.

        A new session is created automatically when
        the investigation ID has not been seen before.

        This method remains an internal mutation-oriented
        access point. Read-oriented public methods such as
        get_history() and get_latest_investigation()
        return defensive copies.
        """

        return self.sessions[investigation_id]

    def get_history(
        self,
        investigation_id: str,
    ) -> list[dict[str, str]]:
        """
        Return conversational history for an
        investigation session.

        A defensive copy is returned so callers cannot
        mutate the stored investigation history directly.
        """

        return deepcopy(
            self.sessions[investigation_id]["history"]
        )

    def add_message(
        self,
        investigation_id: str,
        message: dict[str, str],
    ):
        """
        Add a message to the investigation history.

        The message is copied before storage so later
        mutations to the caller-owned dictionary cannot
        modify the stored investigation state.
        """

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
        answer: str,
    ):
        """
        Store the latest investigation result.

        Claims are optional for backward compatibility with
        existing callers that predate claim traceability.

        Mutable inputs are copied before storage so the
        investigation manager owns its internal analytical
        state independently from caller-owned objects.
        """

        session = self.sessions[investigation_id]

        session["latest_plan"] = deepcopy(plan)

        session["latest_evidence"] = deepcopy(evidence)

        session["latest_claims"] = deepcopy(
            claims or []
        )

        session["latest_answer"] = answer

    def get_latest_investigation(
        self,
        investigation_id: str,
    ) -> dict[str, Any]:
        """
        Return the latest analytical investigation
        state without exposing internal mutable state.

        A deep defensive copy is returned because evidence
        and claims can contain nested dictionaries and lists.
        """

        session = self.get_session(
            investigation_id
        )

        return {
            "plan": deepcopy(
                session["latest_plan"]
            ),
            "evidence": deepcopy(
                session["latest_evidence"]
            ),
            "claims": deepcopy(
                session["latest_claims"]
            ),
            "answer": session["latest_answer"],
        }

    def has_investigation(
        self,
        investigation_id: str,
    ) -> bool:
        """
        Return whether an investigation session
        currently exists.
        """

        return investigation_id in self.sessions

    def delete(
        self,
        investigation_id: str,
    ) -> bool:
        """
        Permanently delete an investigation session.

        Returns True when a session existed and was
        deleted. Returns False when the investigation
        ID did not exist.

        Unlike clear(), this removes the investigation
        session completely.
        """

        if investigation_id not in self.sessions:
            return False

        del self.sessions[investigation_id]

        return True

    def clear(
        self,
        investigation_id: str,
    ):
        """
        Reset a single investigation session while
        preserving the investigation ID.
        """

        self.sessions[investigation_id] = _build_session()


investigation_session_manager = InvestigationSessionManager()