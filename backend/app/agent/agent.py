import json

from groq import Groq

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool_as_json,
)
from app.config import get_settings


settings = get_settings()

MAX_TOOL_ITERATIONS = settings.max_tool_iterations


class AnalyticsAgent:

    def __init__(self):
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.groq_api_key
        )

        self.model = settings.groq_model

    def run(
        self,
        user_message: str,
        history: list | None = None,
    ):
        """
        Execute the analytics agent.

        Supports:
        - conversational context
        - single-tool questions
        - multi-tool investigations
        - structured tool results
        - evidence-based synthesis
        """

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        if history:
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        tools_used = []
        tool_results = []

        for _ in range(MAX_TOOL_ITERATIONS):

            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0,
                )
            )

            assistant_message = (
                response.choices[0].message
            )

            messages.append(
                assistant_message
            )

            if not assistant_message.tool_calls:
                return {
                    "answer": assistant_message.content,
                    "tools_used": tools_used,
                    "tool_results": tool_results,
                    "messages": messages,
                }

            for tool_call in (
                assistant_message.tool_calls
            ):
                tool_name = (
                    tool_call.function.name
                )

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                        or "{}"
                    )

                    result = execute_tool_as_json(
                        tool_name,
                        arguments,
                    )

                    tools_used.append(
                        tool_name
                    )

                    try:
                        parsed_result = json.loads(
                            result
                        )
                    except json.JSONDecodeError:
                        parsed_result = result

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "result": parsed_result,
                        }
                    )

                except Exception as error:
                    result = json.dumps(
                        {
                            "error": str(error)
                        }
                    )

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "result": {
                                "error": str(error)
                            },
                        }
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": (
                            tool_call.id
                        ),
                        "name": tool_name,
                        "content": result,
                    }
                )

        raise RuntimeError(
            "Agent exceeded maximum tool-calling iterations."
        )


agent = AnalyticsAgent()