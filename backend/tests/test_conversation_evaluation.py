from app.agent.agent import agent
from app.agent.session import ConversationManager


def test_follow_up_question_uses_context():
    manager = ConversationManager()

    session_id = "evaluation-session"

    first_question = (
        "Which region performs best?"
    )

    first_result = agent.run(
        user_message=first_question,
        history=manager.get_history(
            session_id
        ),
    )

    manager.add_message(
        session_id,
        {
            "role": "user",
            "content": first_question,
        },
    )

    manager.add_message(
        session_id,
        {
            "role": "assistant",
            "content": first_result["answer"],
        },
    )

    second_question = "Why?"

    second_result = agent.run(
        user_message=second_question,
        history=manager.get_history(
            session_id
        ),
    )

    assert second_result["answer"]

    assert second_result["tools_used"]