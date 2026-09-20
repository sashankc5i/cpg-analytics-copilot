from collections import defaultdict


class ConversationManager:

    def __init__(self):
        self.sessions = defaultdict(list)

    def get_history(self, session_id: str):
        return self.sessions[session_id]

    def add_message(
        self,
        session_id: str,
        message: dict,
    ):
        self.sessions[session_id].append(message)

    def clear(self, session_id: str):
        self.sessions[session_id] = []


conversation_manager = ConversationManager()