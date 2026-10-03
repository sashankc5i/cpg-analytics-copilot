from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class ConversationNotFoundError(ValueError):
    """
    Raised when a conversation resource does not exist.
    """


def _utc_now() -> str:
    """
    Return the current UTC timestamp as an ISO-8601 string.
    """

    return datetime.now(timezone.utc).isoformat()


def _build_analytical_context() -> dict[str, Any]:
    """
    Create the default analytical context for a conversation.

    Analytical context stores structured analytical state that can
    be reused across conversational turns without replaying the
    entire conversation history to the LLM.
    """

    return {
        "metric": None,
        "filters": {},
        "date_range": {
            "start_date": None,
            "end_date": None,
        },
        "comparison_period": None,
        "selected_entity": None,
        "active_investigation": None,
        "last_tool": None,
    }


def _build_session(
    conversation_id: str,
    title: str = "New Chat",
) -> dict[str, Any]:
    """
    Create the default structure for a conversation.
    """

    now = _utc_now()

    return {
        "conversation_id": conversation_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "archived": False,
        "history": [],
        "analytical_context": _build_analytical_context(),
    }


class ConversationManager:
    """
    Maintains conversational sessions in memory.

    A conversation contains:

    - conversation metadata
    - message history
    - archive state
    - analytical context

    Analytical context stores structured state such as the
    currently active metric, filters, date range, selected
    entity, investigation state, and last executed tool.

    The manager remains in-memory for the current
    development phase. Persistent storage can be
    introduced later without changing the public
    conversation contract.

    Returned conversation state is defensively copied
    so callers cannot accidentally mutate the manager's
    internal state.
    """

    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}

    # ============================================================
    # Conversation lifecycle
    # ============================================================

    def create(
        self,
        conversation_id: str,
        *,
        title: str = "New Chat",
    ) -> dict[str, Any]:
        """
        Create a new conversation.

        If the conversation already exists, return the
        existing conversation unchanged.
        """

        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = _build_session(
                conversation_id=conversation_id,
                title=title,
            )

        return self.sessions[conversation_id]

    def get_session(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Return the internal conversation session.

        A conversation is automatically created when the
        ID has not been seen before.

        This method is intentionally used internally by the
        manager for state mutation. Callers that only need
        readable conversation state should use get_existing(),
        get_history(), or get_conversation().
        """

        if conversation_id not in self.sessions:
            self.create(conversation_id)

        return self.sessions[conversation_id]

    def get_existing(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """
        Return an existing conversation without creating it.

        This method is intended for read-only resource
        lookups where a missing conversation should remain
        missing.

        A defensive copy is returned so callers cannot
        mutate the manager's internal state.
        """

        session = self.sessions.get(
            conversation_id
        )

        if session is None:
            return None

        return deepcopy(session)

    def _require_existing(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Return an existing internal conversation session.

        Unlike get_session(), this method never creates a
        conversation. It raises ConversationNotFoundError
        when the requested resource does not exist.

        This is used by lifecycle operations such as rename,
        archive, and unarchive.
        """

        session = self.sessions.get(
            conversation_id
        )

        if session is None:
            raise ConversationNotFoundError(
                "Conversation not found."
            )

        return session

    def list_sessions(
        self,
        *,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return lightweight conversation metadata.

        Full message history and analytical context are
        intentionally excluded.

        The sidebar only needs conversation metadata.

        A new list containing new metadata dictionaries is
        returned so callers cannot mutate the internal
        session collection through the result.
        """

        sessions = []

        for session in self.sessions.values():
            if (
                session["archived"]
                and not include_archived
            ):
                continue

            sessions.append(
                {
                    "conversation_id": session[
                        "conversation_id"
                    ],
                    "title": session["title"],
                    "created_at": session[
                        "created_at"
                    ],
                    "updated_at": session[
                        "updated_at"
                    ],
                    "archived": session["archived"],
                }
            )

        sessions.sort(
            key=lambda item: item["updated_at"],
            reverse=True,
        )

        return sessions

    def rename(
        self,
        conversation_id: str,
        title: str,
    ) -> dict[str, Any]:
        """
        Rename an existing conversation.
        """

        cleaned_title = title.strip()

        if not cleaned_title:
            raise ValueError(
                "Conversation title cannot be empty."
            )

        if len(cleaned_title) > 200:
            raise ValueError(
                "Conversation title cannot exceed 200 characters."
            )

        session = self._require_existing(
            conversation_id
        )

        session["title"] = cleaned_title
        session["updated_at"] = _utc_now()

        return session

    def archive(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Archive an existing conversation.
        """

        session = self._require_existing(
            conversation_id
        )

        session["archived"] = True
        session["updated_at"] = _utc_now()

        return session

    def unarchive(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Restore an existing archived conversation.
        """

        session = self._require_existing(
            conversation_id
        )

        session["archived"] = False
        session["updated_at"] = _utc_now()

        return session

    def delete(
        self,
        conversation_id: str,
    ) -> bool:
        """
        Permanently delete a conversation.

        Returns True when a conversation existed and
        was deleted. Otherwise returns False.
        """

        if conversation_id not in self.sessions:
            return False

        del self.sessions[conversation_id]

        return True

    # ============================================================
    # Message management
    # ============================================================

    def get_history(
        self,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        """
        Return a defensive copy of the message history.

        The caller receives a snapshot of the current history
        rather than the manager's internal list.

        This prevents external code from accidentally changing
        conversation state by mutating the returned list or
        message dictionaries.
        """

        session = self.get_session(
            conversation_id
        )

        return deepcopy(
            session["history"]
        )

    def add_message(
        self,
        conversation_id: str,
        message: dict[str, str],
    ):
        """
        Add a message to a conversation.

        Adding a message also updates the conversation's
        last-modified timestamp.
        """

        session = self.get_session(
            conversation_id
        )

        session["history"].append(
            deepcopy(message)
        )

        session["updated_at"] = _utc_now()

    # ============================================================
    # Analytical context management
    # ============================================================

    def get_analytical_context(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Return a defensive copy of the analytical context.

        Analytical context describes the current analytical
        scope of the conversation independently from the
        conversational message history.
        """

        session = self.get_session(
            conversation_id
        )

        return deepcopy(
            session["analytical_context"]
        )

    def update_analytical_context(
        self,
        conversation_id: str,
        context: dict[str, Any],
    ):
        """
        Replace the analytical context for a conversation.

        A defensive copy is stored so callers cannot mutate
        internal conversation state after the update.
        """

        session = self.get_session(
            conversation_id
        )

        session["analytical_context"] = deepcopy(
            context
        )

        session["updated_at"] = _utc_now()

    def clear_analytical_context(
        self,
        conversation_id: str,
    ):
        """
        Reset analytical context while preserving conversation
        history and conversation metadata.
        """

        session = self.get_session(
            conversation_id
        )

        session["analytical_context"] = (
            _build_analytical_context()
        )

        session["updated_at"] = _utc_now()

    # ============================================================
    # Conversation retrieval
    # ============================================================

    def get_conversation(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Return a defensive copy of the complete conversation,
        including message history and analytical context.

        The returned object can safely be modified by callers
        without mutating the manager's internal state.

        Internal callers may rely on the existing get-or-create
        behavior through get_session().
        """

        session = self.get_session(
            conversation_id
        )

        return deepcopy(session)

    # ============================================================
    # Reset
    # ============================================================

    def clear(
        self,
        conversation_id: str,
    ):
        """
        Reset a conversation while preserving its ID.

        Both conversational history and analytical context
        are reset.
        """

        session = self.get_session(
            conversation_id
        )

        session["history"] = []
        session["title"] = "New Chat"
        session["archived"] = False
        session["analytical_context"] = (
            _build_analytical_context()
        )
        session["updated_at"] = _utc_now()


conversation_manager = ConversationManager()